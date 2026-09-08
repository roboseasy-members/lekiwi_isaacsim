"""Headless six-joint tracking regression with synthetic leader input; no USB."""

from isaacsim import SimulationApp

app = SimulationApp({"headless": True})

import math
from pathlib import Path
import traceback

import numpy as np
import omni.usd
from pxr import UsdPhysics
from isaacsim.core.api import World
from isaacsim.core.api.objects.ground_plane import GroundPlane
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot.wheeled_robots.robots import WheeledRobot
from teleop_bridge import ArmTeleop, JOINTS, make_packet
from arm_control import restore_arm_position_gains


def main():
    dt = 1 / 120
    world = World(physics_dt=dt, rendering_dt=1 / 60, stage_units_in_meters=1.0)
    robot = world.scene.add(WheeledRobot(
        prim_path="/LeKiwi", name="lekiwi", create_robot=True,
        wheel_dof_names=["back_wheel_joint", "left_wheel_joint", "right_wheel_joint"],
        usd_path=str(Path(__file__).resolve().parent / "assets/lekiwi_soarm/usd/lekiwi_soarm.usd"),
        position=np.array([0., 0., .055]),
    ))
    world.scene.add(GroundPlane(prim_path="/World/Ground", z_position=-.021, size=10.0))
    for prim in omni.usd.get_context().get_stage().Traverse():
        if prim.GetName() in JOINTS and prim.IsA(UsdPhysics.RevoluteJoint):
            drive = UsdPhysics.DriveAPI(prim, "angular")
            drive.GetStiffnessAttr().Set(10000)
            drive.GetDampingAttr().Set(200)
            drive.GetMaxForceAttr().Set(1000)
    world.reset()
    indices = np.array([robot.get_dof_index(n) for n in JOINTS], dtype=np.int32)
    controller = robot.get_articulation_controller()
    print(f"SO101_ARM_TEST pre_restore_kp={controller.get_gains()[0][indices]}", flush=True)
    restore_arm_position_gains(controller, indices)
    print(f"SO101_ARM_TEST post_restore_kp={controller.get_gains()[0][indices]}", flush=True)
    control = ArmTeleop("smoke")
    home = np.array(control.targets)
    robot.set_joint_positions(home, joint_indices=indices)
    sequence = 0
    now = 0.0

    def step(values, arm=False, wall_dt=dt):
        nonlocal sequence, now
        # Synthetic clock lets fast headless runs reproduce GUI frame rates.
        now += wall_dt
        packet = make_packet(dict(zip((f"{n}.pos" for n in JOINTS), values)), "smoke", sequence)
        packet["monotonic"] = now
        actual = robot.get_joint_positions(joint_indices=indices)
        target = control.update(packet, now, actual, arm=arm)
        controller.apply_action(ArticulationAction(joint_positions=np.array(target), joint_indices=indices))
        robot.apply_wheel_actions(ArticulationAction(joint_velocities=np.zeros(3)))
        world.step(render=False)
        sequence += 1

    # Hold the rotated home even before R, then use the GUI's absolute mapping.
    for _ in range(360):
        step([0] * 6)
    actual = robot.get_joint_positions(joint_indices=indices)
    assert np.max(np.abs(actual - home)) < .04
    print(f"SO101_ARM_TEST rotated_home wrist_roll={actual[4]:.4f}", flush=True)
    step([0] * 6, arm=True)
    for index, name in enumerate(JOINTS):
        values = [0] * 6
        values[index] = math.degrees(.12) if index < 5 else 8.0
        for _ in range(120):
            step(values)
        actual = robot.get_joint_positions(joint_indices=indices)
        error = np.max(np.abs(actual - control.targets))
        if not np.all(np.isfinite(actual)) or error > .04 or actual[index] - home[index] < .06:
            raise AssertionError(f"{name}: actual={actual}, target={control.targets}, error={error}")
        print(f"SO101_ARM_TEST joint={name} actual={actual[index]:.4f} error={error:.4f}", flush=True)
        for _ in range(120):
            step([0] * 6)
    # Nonzero pose at R must track absolute values, including model-limit clipping.
    # One physics step per 30 Hz GUI frame matches the current interactive loop.
    values = [-1.89, -97.93, 96.97, 36.09, -.92, 1.33]
    step(values, arm=True, wall_dt=1 / 30)
    for _ in range(60):
        step(values, wall_dt=1 / 30)
    actual = robot.get_joint_positions(joint_indices=indices)
    error = np.max(np.abs(actual - control.goals))
    expected = [math.radians(v) for v in values[:5]] + [values[5] * .015]
    expected[2] = 1.69  # URDF upper elbow limit.
    expected[4] -= math.pi / 2  # Clockwise 90-degree default wrist orientation.
    if (not control.armed or not np.all(np.isfinite(actual)) or error > .04
            or not np.allclose(control.targets, expected, atol=1e-6)):
        raise AssertionError(f"absolute pose: actual={actual}, goals={control.goals}, error={error}")
    print(f"SO101_ARM_TEST absolute_30fps error={error:.4f} clipped={control.clipped}", flush=True)
    # Delayed GUI + fresh leader must remain armed, with no accumulated jump.
    values[0] += 45
    held = np.array(control.targets)
    step(values, wall_dt=.3)
    assert control.armed
    assert np.max(np.abs(np.array(control.targets) - held)) <= .150001
    for _ in range(60):
        step(values, wall_dt=1 / 30)
    actual = robot.get_joint_positions(joint_indices=indices)
    error = np.max(np.abs(actual - control.goals))
    assert control.armed and np.all(np.isfinite(actual)) and error < .04
    print(f"SO101_ARM_TEST delayed_gui_fresh_leader error={error:.4f}", flush=True)
    # A stale packet still stops after the same GUI delay and requires R.
    stale = make_packet(dict(zip((f"{n}.pos" for n in JOINTS), values)), "smoke", sequence)
    stale["monotonic"] = now
    held = control.targets[:]
    control.update(stale, now + .3, actual)
    assert not control.armed and control.targets == held
    now += .3
    step(values)
    assert not control.armed and control.targets == held
    print("SO101_ARM_TEST stale_leader_requires_rearm=PASS", flush=True)
    world.stop()
    print("SO101_ARM_TEST result=PASS", flush=True)


try:
    main()
except Exception:
    print("SO101_ARM_TEST result=FAIL", flush=True)
    traceback.print_exc()
finally:
    app.close()
