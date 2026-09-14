"""Hardware-free checks: never instantiate or connect a real motor bus."""

import importlib.util
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "isaac_sim"))
from teleop_bridge import (ArmTeleop, JOINTS, LIMITS, DEFAULT_ARM_OFFSETS_DEG,
                          arm_home, atomic_json, make_packet, read_packet)
from arm_control import restore_arm_position_gains

spec = importlib.util.spec_from_file_location("so101_leader", ROOT / "tools/so101_leader.py")
leader_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(leader_tool)


def sample(seq=0, now=10.0, values=None):
    values = values or [0] * 6
    packet = make_packet(dict(zip((f"{n}.pos" for n in JOINTS), values)), "test", seq)
    packet["monotonic"] = now
    return packet


def calibration():
    return {n: dict(id=i, drive_mode=0, homing_offset=0, range_min=100, range_max=4000)
            for i, n in enumerate(JOINTS, 1)}


def test_post_reset_restores_only_arm_gains_not_wheels_or_rollers():
    controller = SimpleNamespace(kps=[0.0] * 12, kds=[625.0] * 3 + [200.0] * 6 + [0.0001] * 3)
    controller.get_gains = lambda: (controller.kps, controller.kds)
    def set_gains(kps, kds):
        controller.kps, controller.kds = kps, kds
    controller.set_gains = set_gains
    original_kps, original_kds = controller.kps[:], controller.kds[:]
    restore_arm_position_gains(controller, range(3, 9))
    assert controller.kps[3:9] == pytest.approx([math.degrees(10000.0)] * 6)
    assert controller.kds[3:9] == pytest.approx([math.degrees(200.0)] * 6)
    for i in (0, 1, 2, 9, 10, 11):
        assert (controller.kps[i], controller.kds[i]) == (original_kps[i], original_kds[i])


def test_post_reset_gain_readback_failure_is_not_silenced():
    controller = SimpleNamespace(get_gains=lambda: ([0.0] * 6, [0.0] * 6),
                                 set_gains=lambda **_: None)
    with pytest.raises(RuntimeError, match="did not apply"):
        restore_arm_position_gains(controller, range(6))


@pytest.mark.parametrize("answers,result", [(["c"], True), ([""], False), (["bad", "C"], True)])
def test_existing_calibration_always_requires_explicit_choice(tmp_path, answers, result):
    path = tmp_path / "leader.json"
    path.write_text(json.dumps(calibration()))
    prompts = []
    pending = iter(answers)
    def ask(prompt):
        prompts.append(prompt)
        return next(pending)
    assert leader_tool.choose_calibration(path, ask) is result
    assert len(prompts) == len(answers)
    assert "Press ENTER to use provided calibration file" in prompts[0]
    assert json.loads(path.read_text()) == calibration()


def test_connection_confirmation_accepts_enter_without_typing_ready():
    prompts = []
    def ask(prompt):
        prompts.append(prompt)
        return ""
    leader_tool.confirm_connection(ask)
    assert len(prompts) == 1
    assert "Support the SO101 leader arm" in prompts[0]
    assert "Press ENTER" in prompts[0]


@pytest.mark.parametrize("failure", [EOFError, KeyboardInterrupt])
def test_connection_confirmation_does_not_proceed_on_closed_input_or_cancel(failure):
    def ask(_):
        raise failure
    with pytest.raises(failure):
        leader_tool.confirm_connection(ask)


def test_no_file_requires_new_calibration_and_quit_preserves_file(tmp_path):
    path = tmp_path / "leader.json"
    assert leader_tool.choose_calibration(path, lambda _: pytest.fail("No reuse choice without file"))
    path.write_text("old")
    with pytest.raises(RuntimeError, match="취소"):
        leader_tool.choose_calibration(path, lambda _: "q")
    assert path.read_text() == "old"
    with pytest.raises(EOFError):
        leader_tool.choose_calibration(path, lambda _: (_ for _ in ()).throw(EOFError()))


class FakeLeader:
    def __init__(self, path, fail=False):
        self.calibration_fpath = path
        self.calibration = calibration()
        self.is_calibrated = True
        self.fail = fail
        self.calls = []
        self.bus = SimpleNamespace(write_calibration=lambda c: self.calls.append(("write", c)),
                                   sync_read=lambda *a, **kw: dict.fromkeys(JOINTS, 0))

    def calibrate(self):
        assert self.calibration == {}  # Suppress ONLY the upstream duplicate prompt.
        self.calls.append("calibrate")
        self.calibration_fpath.write_text(json.dumps(calibration()))
        if self.fail:
            raise RuntimeError("interrupted calibration")


def test_reuse_writes_existing_values_without_new_calibration(tmp_path):
    path = tmp_path / "leader.json"
    path.write_text(json.dumps(calibration()))
    leader = FakeLeader(path)
    leader_tool.prepare(leader, path, False)
    assert leader.calls == [("write", calibration())]
    assert not list(tmp_path.glob("*.backup-*"))


@pytest.mark.parametrize("failure", ["readback", "torque"])
def test_recalibration_does_not_replace_file_if_hardware_verification_fails(tmp_path, failure):
    path = tmp_path / "leader.json"
    path.write_text("original")
    leader = FakeLeader(path)
    if failure == "readback":
        leader.is_calibrated = False
    else:
        leader.bus.sync_read = lambda *a, **kw: dict.fromkeys(JOINTS, 1)
    with pytest.raises(RuntimeError):
        leader_tool.prepare(leader, path, True)
    assert path.read_text() == "original"


@pytest.mark.parametrize("fail", [False, True])
def test_recalibration_stages_output_and_preserves_old_file(tmp_path, fail):
    path = tmp_path / "leader.json"
    path.write_text("old calibration contents")
    leader = FakeLeader(path, fail)
    if fail:
        with pytest.raises(RuntimeError, match="interrupted"):
            leader_tool.prepare(leader, path, True)
        assert path.read_text() == "old calibration contents"
    else:
        leader_tool.prepare(leader, path, True)
        assert json.loads(path.read_text()) == calibration()
        backups = list(tmp_path.glob("*.backup-*"))
        assert len(backups) == 1 and backups[0].read_text() == "old calibration contents"
    assert leader.calibration_fpath == path
    assert not list(tmp_path.glob(".leader-*"))


@pytest.mark.parametrize("error", ["joint", "id", "range", "nan"])
def test_invalid_calibration_is_rejected(tmp_path, error):
    data = calibration()
    if error == "joint":
        data.pop("gripper")
    elif error == "id":
        data["gripper"]["id"] = 1
    elif error == "range":
        data["gripper"]["range_max"] = 50
    else:
        data["gripper"]["homing_offset"] = float("nan")
    path = tmp_path / "leader.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        leader_tool.validate_calibration(path)


def test_r_follows_absolute_pose_without_startup_teleport():
    control = ArmTeleop("test", offsets_deg=(0,) * 6)
    values = [30, -45, 60, 20, -10, 50]
    control.update(sample(values=values), 10, [0] * 6)
    assert not control.armed and control.targets == [0] * 6
    control.update(sample(values=values), 10, [0] * 6, arm=True)
    assert control.armed and control.targets == [0] * 6
    expected = [math.radians(v) for v in values[:5]] + [.75]
    for i in range(1, 31):
        now = 10 + i / 30
        control.update(sample(i, now, values), now, control.targets)
    assert control.targets == pytest.approx(expected)
    # R may restart from the actual simulated pose, but never changes the mapping.
    control.update(sample(31, 11.01, values), 11.01, [.1] * 6, arm=True)
    assert control.targets == pytest.approx([.1] * 6)
    assert control.goals == pytest.approx(expected)


@pytest.mark.parametrize("hz", [20, 30, 60, 120])
def test_target_speed_uses_wall_clock_independent_of_gui_fps(hz):
    control = ArmTeleop("test", offsets_deg=(0,) * 6)
    values = [90] * 5 + [100]
    control.update(sample(values=values), 10, [0] * 6, arm=True)
    for i in range(1, hz // 5 + 1):
        now = 10 + i / hz
        control.update(sample(i, now, values), now, [0] * 6)
    assert control.targets == pytest.approx([.6] * 6)


@pytest.mark.parametrize("delay", [.251, .3, 1.0, 5.0])
def test_gui_delay_with_fresh_leader_keeps_active_without_catchup_jump(delay):
    control = ArmTeleop("test", offsets_deg=(0,) * 6)
    values = [90] * 5 + [100]
    control.update(sample(values=values), 10, [0] * 6, arm=True)
    control.update(sample(1, 10.1, values), 10.1, [0] * 6)
    assert control.targets == pytest.approx([.15] * 6)
    held = control.targets[:]
    now = 10.1 + delay
    control.update(sample(2, now, values), now, [0] * 6)
    assert control.armed
    assert control.targets == pytest.approx([v + .15 for v in held])
    control.update(sample(3, now + .01, values), now + .01, [0] * 6)
    assert control.armed and control.targets == pytest.approx([v + .18 for v in held])


@pytest.mark.parametrize("kind", ["stale", "disconnected", "missing", "space"])
def test_gui_delay_does_not_bypass_real_stop_conditions(kind):
    control = ArmTeleop("test")
    control.update(sample(), 10, control.targets, arm=True)
    held = control.targets[:]
    p = sample(1, 11)
    if kind == "stale": p["monotonic"] = 10.7
    if kind == "disconnected": p["connected"] = False
    if kind == "missing": p = None
    control.update(p, 11, held, stop=kind == "space")
    assert not control.armed and control.targets == held
    control.update(sample(2, 11.01), 11.01, held)
    assert not control.armed and control.targets == held
    control.update(sample(3, 11.02), 11.02, held, arm=True)
    assert control.armed


def test_remote_wait_does_not_extend_local_usb_watchdog():
    local, remote = ArmTeleop("test"), ArmTeleop("test", remote=True)
    assert local.timeout == .25 and remote.timeout == .5
    for control in (local, remote):
        control.update(sample(), 10, control.targets, arm=True)
        control.update(sample(), 10.3, control.targets)
    assert not local.armed
    assert remote.armed
    remote.update(sample(), 10.501, remote.targets)
    assert not remote.armed


@pytest.mark.parametrize("now", [9.9, math.nan, math.inf])
def test_invalid_control_clock_still_disarms(now):
    control = ArmTeleop("test")
    control.update(sample(), 10, control.targets, arm=True)
    held = control.targets[:]
    control.update(sample(1), now, held)
    assert not control.armed and control.targets == held


def test_explicit_offsets_signs_and_clipped_goal_diagnostics():
    control = ArmTeleop("test", signs=(-1, 1, 1, 1, 1, -1),
                        offsets_deg=(10, 20, 0, 0, 0, 5), max_speed=2)
    control.update(sample(values=[30, 0, 360, 0, 0, 100]), 10, [0] * 6, arm=True)
    assert control.goals == pytest.approx([math.radians(-20), math.radians(20),
                                           LIMITS[2][1], 0, 0, math.radians(5)])
    assert control.clipped == ["elbow_flex"]


@pytest.mark.parametrize("kwargs", [{"max_speed": 0}, {"max_speed": math.nan},
    {"max_speed": 11}, {"offsets_deg": [0]}, {"offsets_deg": [math.inf] * 6}])
def test_invalid_mapping_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        ArmTeleop("test", **kwargs)


def test_rotated_home_is_held_before_r_and_preserved_during_leader_tracking():
    control = ArmTeleop("test")
    home = arm_home(DEFAULT_ARM_OFFSETS_DEG)
    assert home == pytest.approx([0, 0, 0, 0, -math.pi / 2, 0])
    assert control.update(None, 9.99, home) == home
    assert control.update(sample(), 10, home) == home
    assert control.update(sample(), 10, home, arm=True) == home
    assert control.goals == pytest.approx(home)
    values = [0, 0, 0, 0, 30, 0]
    for i in range(1, 31):
        now = 10 + i / 30
        control.update(sample(i, now, values), now, control.targets)
    assert control.targets[4] == pytest.approx(math.radians(-60))
    assert control.targets[:4] == [0] * 4 and control.targets[5] == 0


def test_rotated_wrist_still_clamps_at_original_model_limit():
    control = ArmTeleop("test")
    control.update(sample(values=[0, 0, 0, 0, -180, 0]), 10,
                   control.targets, arm=True)
    assert control.goals[4] == LIMITS[4][0]
    assert control.clipped == ["wrist_roll"]


@pytest.mark.parametrize("kind", ["stale", "future", "session", "unit", "missing", "nan", "range", "disconnected", "sequence"])
def test_invalid_sample_disarms_and_holds_last_target(kind):
    control = ArmTeleop("test")
    control.update(sample(1), 10, [0] * 6, arm=True)
    p = sample(2, 10.01, [1] * 6)
    control.update(p, 10.01, [0] * 6)
    held = control.targets[:]
    p = sample(3, 10.02)
    if kind == "stale": p["monotonic"] = 9
    if kind == "future": p["monotonic"] = 11
    if kind == "session": p["session"] = "previous"
    if kind == "unit": p["unit"] = "radians"
    if kind == "missing": p["positions"].pop("gripper.pos")
    if kind == "nan": p["positions"]["gripper.pos"] = float("nan")
    if kind == "range": p["positions"]["gripper.pos"] = 101
    if kind == "disconnected": p["connected"] = False
    if kind == "sequence": p["sequence"] = 0
    assert control.update(p, 10.02, [0] * 6) == held
    assert not control.armed
    control.update(sample(4, 10.03), 10.03, [0] * 6)
    assert not control.armed  # Recovery must not resume automatically.


def test_space_and_joint_signs_limits():
    control = ArmTeleop("test", signs=(-1, 1, 1, 1, 1, -1))
    control.update(sample(), 10, [0] * 6, arm=True)
    for i in range(1, 1000):
        control.update(sample(i, 10 + i / 30, [360] * 5 + [0]), 10 + i / 30, [0] * 6)
    assert control.targets[0] == LIMITS[0][0]
    assert control.targets[1:5] == [limit[1] for limit in LIMITS[1:5]]
    assert control.targets[5] == pytest.approx(1.5)
    control.update(sample(1000, 44), 44, [0] * 6, arm=True, stop=True)
    assert not control.armed


def test_mailbox_rejects_partial_json_and_roundtrips_atomic_samples(tmp_path):
    path = tmp_path / "session/leader.json"
    assert read_packet(path) is None
    p = sample()
    atomic_json(path, p)
    assert read_packet(path) == p
    path.write_text("{")
    assert read_packet(path) is None
    with pytest.raises(ValueError):
        atomic_json(path, {"bad": math.nan})
    assert path.read_text() == "{"
    assert not list(path.parent.glob(".sample-*"))
