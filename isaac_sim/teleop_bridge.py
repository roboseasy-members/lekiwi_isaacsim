"""Local, ROS-free SO101 transport and simulator-only command limits.

Both containers share the host monotonic clock and a bind-mounted session folder.
This latest-sample mailbox is for teleop, NOT lossless dataset recording.
"""

import json
import math
import os
from pathlib import Path
import tempfile
import time

JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
LIMITS = ((-1.91986, 1.91986), (-1.74533, 1.74533), (-1.69, 1.69),
          (-1.65806, 1.65806), (-2.74385, 2.84121), (-0.174533, 1.74533))
# Clockwise looking from the wrist toward the fingertips: wrist_roll axis in
# the bundled URDF points back toward the arm, so this is a negative rotation.
DEFAULT_ARM_OFFSETS_DEG = (0, 0, 0, 0, -90, 0)
# 원격 가상 로봇만 짧은 Wi-Fi 지연을 기다립니다. 로컬 USB 입력은 250 ms입니다.
REMOTE_INPUT_TIMEOUT = 0.5
REMOTE_RECOVERY_WINDOW = 2.0
REMOTE_RECOVERY_SAMPLES = 3


class InputGap(ValueError):
    """형식·순서는 정상이지만 다음 입력이 늦은 경우만 구분합니다."""


def arm_home(offsets_deg):
    if len(offsets_deg) != 6 or any(not math.isfinite(v) for v in offsets_deg):
        raise ValueError("Expected six finite zero offsets in degrees")
    return [max(lo, min(hi, math.radians(v))) for v, (lo, hi) in zip(offsets_deg, LIMITS)]


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".sample-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_packet(path):
    try:
        with Path(path).open() as stream:
            return json.load(stream)
    except (OSError, ValueError):
        return None


def make_packet(action, session, sequence, connected=True):
    return {"version": 1, "session": session, "sequence": sequence,
            "monotonic": time.monotonic(), "connected": connected,
            "unit": "degrees+gripper_percent", "positions": action}


def validate_positions(positions):
    if not isinstance(positions, dict):
        raise ValueError("Invalid joint position object")
    values = [positions[f"{name}.pos"] for name in JOINTS]
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError("Invalid joint position")
    if any(abs(v) > 360 for v in values[:5]) or not 0 <= values[5] <= 100:
        raise ValueError("Leader position outside expected units/range")
    return values


class ArmTeleop:
    """Explicit clutch, local 250 ms / remote 500 ms input watchdog, bounded targets.

Five body joints use absolute calibrated degrees plus explicit model offsets.
Gripper percent maps to 0..1.5 rad. Signs/zeros require hardware pose validation.
The monotonic clock, not the render-frame count, controls target slew speed.
"""

    def __init__(self, session, signs=(1, 1, 1, 1, 1, 1), timeout=0.25,
                 offsets_deg=DEFAULT_ARM_OFFSETS_DEG, max_speed=3.0, remote=False):
        if len(signs) != 6 or any(x not in (-1, 1) for x in signs):
            raise ValueError("Expected six joint signs, each +1 or -1")
        if len(offsets_deg) != 6 or any(not math.isfinite(v) for v in offsets_deg):
            raise ValueError("Expected six finite zero offsets in degrees")
        if not math.isfinite(max_speed) or not 0 < max_speed <= 10:
            raise ValueError("Target speed must be in (0, 10] rad/s")
        self.session, self.signs = session, signs
        self.timeout = REMOTE_INPUT_TIMEOUT if remote else timeout
        self.remote = remote
        self.offsets = [math.radians(v) for v in offsets_deg]
        self.max_speed = max_speed
        self.targets = arm_home(offsets_deg)
        self.goals = self.targets[:]
        self.clipped = []
        self.armed = False
        self.status = "WAITING: leader / press R to arm"
        self.sequence = -1
        self.sample_stamp = -1.0
        self.last_update = None
        self.remote_peer = None
        self.recovery_deadline = None
        self.recovery_samples = 0
        self.resumed = False
        self.gap_stamp = None
        self.input_valid = False

    @property
    def recovering(self):
        return self.recovery_deadline is not None

    def disarm(self):
        """수동 정지·화면 종료·초기화는 자동 재개 예약도 취소합니다."""
        self.armed = False
        self.recovery_deadline = None
        self.recovery_samples = 0

    def wait_for_input(self, now, stamp=None):
        if self.armed:
            self.recovery_deadline = (self.sample_stamp if stamp is None else stamp) + REMOTE_RECOVERY_WINDOW
        self.armed = False
        self.recovery_samples = 0
        if self.recovering and now < self.recovery_deadline:
            self.status = "RECONNECTING: holding pose; SPACE cancels resume"
        else:
            self.disarm()
            self.status = "STOP: input lost; press R after recovery"

    def _positions(self, packet, now):
        if not isinstance(packet, dict):
            raise ValueError("No leader sample")
        if (packet.get("version") != 1 or packet.get("session") != self.session
                or packet.get("connected") is not True
                or packet.get("unit") != "degrees+gripper_percent"):
            raise ValueError("Disconnected or incompatible leader")
        stamp, seq = packet["monotonic"], packet["sequence"]
        if (type(stamp) not in (int, float) or not math.isfinite(stamp)
                or now - stamp < 0 or type(seq) is not int
                or seq < 0 or seq < self.sequence or stamp < self.sample_stamp
                or (seq == self.sequence and stamp != self.sample_stamp)):
            raise ValueError("Stale or out-of-order leader sample")
        values = validate_positions(packet["positions"])
        if now - stamp > self.timeout:
            raise InputGap("Stale leader sample")
        self.sequence, self.sample_stamp = seq, stamp
        return values

    def update(self, packet, now, actual, arm=False, stop=False):
        self.resumed = False
        self.input_valid = False
        if stop:
            self.disarm()
        if self.recovering and now >= self.recovery_deadline:
            self.disarm()
        elapsed = 0.0 if self.last_update is None else now - self.last_update
        self.last_update = now
        previous_sequence = self.sequence
        try:
            if not math.isfinite(now) or not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError("Control clock invalid or moved backwards")
            # Rendering can stall while the separate leader reader stays healthy.
            # Check sample freshness, not time since the last rendered frame.
            # The 50 ms slew cap below prevents accumulated catch-up motion.
            values = self._positions(packet, now)
        except InputGap as exc:
            if self.remote and self.remote_peer and packet.get("remote_peer") == self.remote_peer:
                self.wait_for_input(now)
            else:
                self.disarm()
                self.status = f"STOP: {exc}; press R after recovery"
            return self.targets[:]
        except (KeyError, TypeError, ValueError) as exc:
            self.disarm()
            self.status = f"STOP: {exc}; press R after recovery"
            return self.targets[:]
        self.input_valid = True
        peer = packet.get("remote_peer")
        if peer != self.remote_peer:
            self.remote_peer = peer
            self.disarm()
            arm = False  # 새 연결과 동시에 들어온 이전 R 입력을 사용하지 않습니다.
        gap_stamp = packet.get("input_gap_stamp")
        if self.remote and gap_stamp != self.gap_stamp:
            self.gap_stamp = gap_stamp
            self.recovery_samples = 0
            # 렌더링 사이에 단절·복구가 모두 일어나도 수신기의 단절 표시를 놓치지 않습니다.
            if self.armed and type(gap_stamp) in (int, float) and math.isfinite(gap_stamp):
                self.wait_for_input(now, gap_stamp)
                arm = False
        if self.recovering:
            if self.sequence != previous_sequence:
                self.recovery_samples += 1
            if self.recovery_samples < REMOTE_RECOVERY_SAMPLES:
                self.status = "RECONNECTING: checking fresh input; SPACE cancels resume"
                return self.targets[:]
            self.resumed = True
            arm = True
        if arm and not stop:
            if len(actual) != 6 or any(not math.isfinite(float(v)) for v in actual):
                raise ValueError("Invalid simulated joint state")
            self.targets = [max(lo, min(hi, float(v))) for v, (lo, hi) in zip(actual, LIMITS)]
            # Start smoothly from the actual pose; R never changes the mapping.
            elapsed = 0.0
            self.recovery_deadline = None
            self.recovery_samples = 0
            self.armed = True
        if not self.armed:
            self.status = "READY: R to follow leader pose"
            return self.targets[:]
        goals = [self.offsets[i] + self.signs[i] * math.radians(values[i])
                 for i in range(5)]
        grip = values[5] if self.signs[5] == 1 else 100 - values[5]
        goals.append(self.offsets[5] + grip * 1.5 / 100)
        # Bound each increment during a slow GUI frame; never catch up a stall.
        step = self.max_speed * min(elapsed, 0.05)
        self.clipped = []
        for i, (goal, (lo, hi)) in enumerate(zip(goals, LIMITS)):
            if not lo <= goal <= hi:
                self.clipped.append(JOINTS[i])
            goal = max(lo, min(hi, goal))
            self.goals[i] = goal
            self.targets[i] += max(-step, min(step, goal - self.targets[i]))
        self.status = "ACTIVE: SO101 absolute pose; SPACE stops"
        if self.clipped:
            self.status += "; LIMIT: " + ", ".join(self.clipped)
        return self.targets[:]
