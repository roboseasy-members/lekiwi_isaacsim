"""Headless contact-drive regression for the LeKiwi passive-roller asset."""

from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})

import math
import os
import sys
import traceback

import numpy as np
import omni.usd
from pxr import Usd, UsdGeom, UsdPhysics

from isaacsim.core.api import World
from isaacsim.core.api.objects.ground_plane import GroundPlane
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot.wheeled_robots.robots import WheeledRobot


USD_PATH = os.environ.get(
    "LEKIWI_USD", "/workspace/assets/lekiwi_soarm/usd/lekiwi_soarm.usd"
)
GROUND_Z = -0.021
SPAWN_Z = float(os.environ.get("LEKIWI_SPAWN_Z", "0.055"))
PHYSICS_DT = 1.0 / 120.0
WHEEL_RADIUS = 0.05078448
DISABLE_ROLLER_COLLISION = os.environ.get(
    "LEKIWI_DISABLE_ROLLER_COLLISION", "0"
) == "1"
WHEEL_NAMES = [
    "back_wheel_joint",
    "left_wheel_joint",
    "right_wheel_joint",
]
WHEEL_CENTERS = (
    (0.077570012931, -0.135211953961),
    (-0.151363294628, 0.000428794341),
    (0.077035499782, 0.132567385288),
)
WHEEL_ROLL_DIRECTIONS = (
    (-0.866033022300, -0.499986804112),
    (0.000015237232, 0.999999999884),
    (0.866017785068, -0.500013195772),
)


def _report_uncaught_exception(exc_type, exc_value, exc_traceback):
    print("LEKIWI_PHYSICS_SMOKE result=FATAL", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_traceback)


sys.excepthook = _report_uncaught_exception


def _yaw(quaternion):
    w, x, y, z = (float(value) for value in quaternion)
    return math.atan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z),
    )


def _rpy(quaternion):
    w, x, y, z = (float(value) for value in quaternion)
    roll = math.atan2(
        2.0 * (w * x + y * z),
        1.0 - 2.0 * (x * x + y * y),
    )
    pitch = math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))
    return roll, pitch, _yaw(quaternion)


def _wheel_speeds(drive_vx, drive_vy, wz):
    base_vx = drive_vx
    base_vy = drive_vy
    speeds = []
    for (x, y), (roll_x, roll_y) in zip(
        WHEEL_CENTERS, WHEEL_ROLL_DIRECTIONS
    ):
        wheel_vx = base_vx - wz * y
        wheel_vy = base_vy + wz * x
        speeds.append(
            (roll_x * wheel_vx + roll_y * wheel_vy) / WHEEL_RADIUS
        )
    return np.asarray(speeds, dtype=np.float32)


def _command(robot, drive_vx, drive_vy, wz):
    robot.apply_wheel_actions(
        ArticulationAction(joint_velocities=_wheel_speeds(drive_vx, drive_vy, wz))
    )


def _base_pose(root_body):
    matrix = UsdGeom.Xformable(root_body).ComputeLocalToWorldTransform(
        Usd.TimeCode.Default()
    )
    position = np.asarray(matrix.ExtractTranslation(), dtype=float)
    quaternion = matrix.ExtractRotation().GetQuat()
    orientation = np.array(
        [quaternion.GetReal(), *quaternion.GetImaginary()], dtype=float
    )
    return position, orientation


def _step(world, robot, root_body, command, frames, diagnostic_prefix=None):
    for frame in range(frames):
        _command(robot, *command)
        world.step(render=False)
        if diagnostic_prefix and frame % 30 == 0:
            position, orientation = _base_pose(root_body)
            roll, pitch, yaw = _rpy(orientation)
            print(
                f"LEKIWI_PHYSICS_SMOKE {diagnostic_prefix} frame={frame:03d} "
                f"x={position[0]:+.5f} y={position[1]:+.5f} "
                f"z={position[2]:+.5f} roll={roll:+.4f} "
                f"pitch={pitch:+.4f} yaw={yaw:+.4f}",
                flush=True,
            )
    position, orientation = _base_pose(root_body)
    return np.asarray(position, dtype=float), _yaw(orientation)


def _projection(delta, heading):
    return float(delta[0] * math.cos(heading) + delta[1] * math.sin(heading))


def main():
    world = World(
        physics_dt=PHYSICS_DT,
        rendering_dt=1.0 / 60.0,
        stage_units_in_meters=1.0,
    )
    robot = world.scene.add(
        WheeledRobot(
            prim_path="/LeKiwi",
            name="lekiwi",
            wheel_dof_names=WHEEL_NAMES,
            create_robot=True,
            usd_path=USD_PATH,
            position=np.array([0.0, 0.0, SPAWN_Z]),
        )
    )
    world.scene.add(
        GroundPlane(
            prim_path="/World/PhysicsGround",
            z_position=GROUND_Z,
            size=10.0,
            color=np.array([0.32, 0.34, 0.38]),
        )
    )
    stage = omni.usd.get_context().get_stage()
    root_body = stage.GetPrimAtPath("/LeKiwi/base_link/base_link")
    pre_reset_matrix = UsdGeom.Xformable(root_body).ComputeLocalToWorldTransform(
        Usd.TimeCode.Default()
    )
    print(
        "LEKIWI_PHYSICS_SMOKE pre_reset_root_body "
        f"position={tuple(pre_reset_matrix.ExtractTranslation())} "
        f"rotation={pre_reset_matrix.ExtractRotation().GetQuat()}",
        flush=True,
    )
    if DISABLE_ROLLER_COLLISION:
        disabled = 0
        for prim in stage.Traverse():
            if "_roller_" not in str(prim.GetPath()):
                continue
            collision = UsdPhysics.CollisionAPI(prim)
            if not collision:
                continue
            collision.GetCollisionEnabledAttr().Set(False)
            disabled += 1
        print(
            f"LEKIWI_PHYSICS_SMOKE roller_collisions_disabled={disabled}",
            flush=True,
        )
    world.reset()

    initial_position, initial_orientation = _base_pose(root_body)
    initial_rpy = _rpy(initial_orientation)
    print(
        "LEKIWI_PHYSICS_SMOKE initial "
        f"x={initial_position[0]:+.5f} y={initial_position[1]:+.5f} "
        f"z={initial_position[2]:+.5f} "
        f"rpy=({initial_rpy[0]:+.4f},{initial_rpy[1]:+.4f},"
        f"{initial_rpy[2]:+.4f})",
        flush=True,
    )

    settled_position, settled_yaw = _step(
        world,
        robot,
        root_body,
        (0.0, 0.0, 0.0),
        240,
        diagnostic_prefix="settling",
    )
    print(
        "LEKIWI_PHYSICS_SMOKE settled "
        f"x={settled_position[0]:+.5f} y={settled_position[1]:+.5f} "
        f"z={settled_position[2]:+.5f} yaw={settled_yaw:+.5f}",
        flush=True,
    )
    if not np.all(np.isfinite(settled_position)):
        raise RuntimeError("non-finite settled pose")
    if not 0.02 < settled_position[2] < 0.09:
        raise RuntimeError(f"invalid settled height: {settled_position[2]}")
    if np.linalg.norm(settled_position[:2]) > 0.03:
        raise RuntimeError(f"excessive idle drift: {settled_position[:2]}")

    before = settled_position
    before_yaw = settled_yaw
    after_forward, forward_yaw = _step(
        world, robot, root_body, (0.12, 0.0, 0.0), 240
    )
    _step(world, robot, root_body, (0.0, 0.0, 0.0), 120)
    forward_delta = after_forward - before
    forward_heading = before_yaw
    forward_along = _projection(forward_delta, forward_heading)
    forward_cross = _projection(forward_delta, forward_heading + math.pi / 2.0)
    print(
        "LEKIWI_PHYSICS_SMOKE forward "
        f"dx={forward_delta[0]:+.5f} dy={forward_delta[1]:+.5f} "
        f"along={forward_along:+.5f} cross={forward_cross:+.5f} "
        f"dyaw={forward_yaw - before_yaw:+.5f}",
        flush=True,
    )

    before, before_orientation = _base_pose(root_body)
    before_yaw = _yaw(before_orientation)
    after_left, left_yaw = _step(
        world, robot, root_body, (0.0, 0.12, 0.0), 240
    )
    _step(world, robot, root_body, (0.0, 0.0, 0.0), 120)
    left_delta = after_left - before
    left_heading = before_yaw + math.pi / 2.0
    left_along = _projection(left_delta, left_heading)
    left_cross = _projection(left_delta, left_heading + math.pi / 2.0)
    print(
        "LEKIWI_PHYSICS_SMOKE left "
        f"dx={left_delta[0]:+.5f} dy={left_delta[1]:+.5f} "
        f"along={left_along:+.5f} cross={left_cross:+.5f} "
        f"dyaw={left_yaw - before_yaw:+.5f}",
        flush=True,
    )

    _, before_orientation = _base_pose(root_body)
    before_yaw = _yaw(before_orientation)
    _, rotate_yaw = _step(
        world, robot, root_body, (0.0, 0.0, 0.4), 240
    )
    _step(world, robot, root_body, (0.0, 0.0, 0.0), 120)
    rotate_delta = math.atan2(
        math.sin(rotate_yaw - before_yaw), math.cos(rotate_yaw - before_yaw)
    )
    print(
        f"LEKIWI_PHYSICS_SMOKE ccw dyaw={rotate_delta:+.5f}",
        flush=True,
    )

    if forward_along <= 0.03 or abs(forward_cross) > abs(forward_along) * 0.5:
        raise RuntimeError("forward contact drive direction failed")
    if left_along <= 0.03 or abs(left_cross) > abs(left_along) * 0.5:
        raise RuntimeError("lateral contact drive direction failed")
    if rotate_delta <= 0.15:
        raise RuntimeError("counter-clockwise contact drive failed")

    print("LEKIWI_PHYSICS_SMOKE result=PASS", flush=True)


failed = False
try:
    main()
except Exception:
    failed = True
    print("LEKIWI_PHYSICS_SMOKE result=FAIL", flush=True)
    traceback.print_exc()
finally:
    simulation_app.close()

if failed:
    sys.exit(1)
