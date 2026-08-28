"""Interactive PhysX contact-drive test for LeKiwi + SO101 in Isaac Sim."""

from isaacsim import SimulationApp


simulation_app = SimulationApp(
    {
        "headless": False,
        "width": 1440,
        "height": 900,
        "sync_loads": False,
        "extra_args": [
            "--enable",
            "isaacsim.ros2.bridge",
            "--/exts/isaacsim.ros2.bridge/ros_distro=jazzy",
        ],
    }
)

import asyncio
import math
import os
import sys
import traceback

import carb
import carb.input
import numpy as np
import omni.appwindow
import omni.ui as ui
import omni.usd
from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics, Vt

from isaacsim.core.api import World
from isaacsim.core.api.objects.ground_plane import GroundPlane
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot.wheeled_robots.robots import WheeledRobot

from ros_odometry import RosOdometryPublisher


USD_PATH = os.environ.get(
    "LEKIWI_USD", "/workspace/assets/lekiwi_soarm/usd/lekiwi_soarm.usd"
)
CAPTURE_PATH = os.environ.get("LEKIWI_CAPTURE_PATH", "")
GROUND_Z = float(os.environ.get("LEKIWI_GROUND_Z", "-0.021"))
SPAWN_Z = float(os.environ.get("LEKIWI_SPAWN_Z", "0.055"))
LINEAR_SPEED = float(os.environ.get("LEKIWI_LINEAR_SPEED", "0.25"))
ANGULAR_SPEED = float(os.environ.get("LEKIWI_ANGULAR_SPEED", "0.8"))
PHYSICS_DT = float(os.environ.get("LEKIWI_PHYSICS_DT", str(1.0 / 120.0)))
ODOM_PUBLISH_HZ = float(os.environ.get("LEKIWI_ODOM_PUBLISH_HZ", "30.0"))
WHEEL_RADIUS = 0.05078448
ARM_HOLD_STIFFNESS = 10000.0
ARM_HOLD_DAMPING = 200.0
ARM_HOLD_MAX_FORCE = 1000.0
GRID_HALF_SIZE = 5.0
GRID_MINOR_SPACING = 0.1
GRID_MAJOR_SPACING = 0.5
SETTLE_WINDOW_STEPS = 120
SETTLE_MAX_STEPS = 1200
SETTLE_REQUIRED_STABLE_WINDOWS = 2
SETTLE_POSITION_TOLERANCE = 0.0005
SETTLE_YAW_TOLERANCE = 0.0005

WHEEL_JOINT_NAMES = (
    "back_wheel_joint",
    "left_wheel_joint",
    "right_wheel_joint",
)
ARM_JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)
ARM_HOME_POSITIONS = np.zeros(len(ARM_JOINT_NAMES), dtype=np.float32)
ROLLER_JOINT_NAMES = tuple(
    f"{wheel}_roller_{index:02d}_joint"
    for wheel in ("back", "left", "right")
    for index in range(12)
)
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
CONTROL_KEYS = {
    carb.input.KeyboardInput.W,
    carb.input.KeyboardInput.A,
    carb.input.KeyboardInput.S,
    carb.input.KeyboardInput.D,
    carb.input.KeyboardInput.Q,
    carb.input.KeyboardInput.E,
    carb.input.KeyboardInput.P,
    carb.input.KeyboardInput.T,
    carb.input.KeyboardInput.SPACE,
}


def _report_uncaught_exception(exc_type, exc_value, exc_traceback):
    print("LEKIWI_DRIVE result=FATAL", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_traceback)


sys.excepthook = _report_uncaught_exception


def _yaw(quaternion):
    w, x, y, z = (float(value) for value in quaternion)
    return math.atan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z),
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


def _wheel_speeds(drive_vx, drive_vy, wz):
    """Convert base_link velocity directly to the three wheel rates in rad/s."""
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


def _apply_command(robot, drive_vx, drive_vy, wz):
    robot.apply_wheel_actions(
        ArticulationAction(
            joint_velocities=_wheel_speeds(drive_vx, drive_vy, wz)
        )
    )


def _configure_arm_hold(stage):
    joints = {
        prim.GetName(): prim
        for prim in stage.Traverse()
        if prim.IsA(UsdPhysics.RevoluteJoint)
    }
    for name in ARM_JOINT_NAMES:
        drive = UsdPhysics.DriveAPI(joints[name], "angular")
        if not drive:
            raise RuntimeError(f"Angular drive not found for arm joint: {name}")
        drive.GetStiffnessAttr().Set(ARM_HOLD_STIFFNESS)
        drive.GetDampingAttr().Set(ARM_HOLD_DAMPING)
        drive.GetMaxForceAttr().Set(ARM_HOLD_MAX_FORCE)
        drive.GetTargetPositionAttr().Set(0.0)
        drive.GetTargetVelocityAttr().Set(0.0)


def _hold_arm_home(articulation_controller, arm_indices):
    articulation_controller.apply_action(
        ArticulationAction(
            joint_positions=ARM_HOME_POSITIONS,
            joint_indices=arm_indices,
        )
    )


def _validate_stage(stage):
    articulation_roots = [
        prim
        for prim in stage.Traverse()
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI)
    ]
    if len(articulation_roots) != 1:
        paths = [str(prim.GetPath()) for prim in articulation_roots]
        raise RuntimeError(f"Expected one articulation root, found {paths}")

    revolute_joints = {
        prim.GetName(): prim
        for prim in stage.Traverse()
        if prim.IsA(UsdPhysics.RevoluteJoint)
    }
    required = WHEEL_JOINT_NAMES + ARM_JOINT_NAMES + ROLLER_JOINT_NAMES
    missing = [name for name in required if name not in revolute_joints]
    if missing:
        raise RuntimeError(f"Required joints not found in USD: {missing}")

    roller_names = set(revolute_joints).intersection(ROLLER_JOINT_NAMES)
    if roller_names != set(ROLLER_JOINT_NAMES):
        raise RuntimeError(
            f"Expected 36 passive roller joints, found {len(roller_names)}"
        )

    root_body = stage.GetPrimAtPath("/LeKiwi/base_link/base_link")
    if not root_body.IsValid() or not root_body.HasAPI(UsdPhysics.RigidBodyAPI):
        raise RuntimeError("LeKiwi base rigid body was not found")
    return articulation_roots[0], root_body


def _validate_drive_kinematics():
    forward = _wheel_speeds(1.0, 0.0, 0.0)
    left = _wheel_speeds(0.0, 1.0, 0.0)
    ccw = _wheel_speeds(0.0, 0.0, 1.0)
    if not (
        np.all(np.isfinite(forward))
        and np.all(np.isfinite(left))
        and np.all(np.isfinite(ccw))
        and np.linalg.norm(forward - left) > 1.0
        and np.linalg.norm(left - ccw) > 1.0
    ):
        raise RuntimeError(
            f"Omni-wheel IK validation failed: {forward}, {left}, {ccw}"
        )


def _settle_on_ground(
    robot, articulation_controller, arm_indices, world, root_body
):
    previous_position = None
    previous_yaw = None
    stable_windows = 0
    position_shift = math.inf
    yaw_shift = math.inf

    for step in range(1, SETTLE_MAX_STEPS + 1):
        _apply_command(robot, 0.0, 0.0, 0.0)
        _hold_arm_home(articulation_controller, arm_indices)
        world.step(render=True)
        if step % SETTLE_WINDOW_STEPS != 0:
            continue

        position, orientation = _base_pose(root_body)
        yaw = _yaw(orientation)
        if previous_position is not None:
            position_shift = float(
                np.linalg.norm(position[:2] - previous_position[:2])
            )
            yaw_shift = abs(
                math.atan2(
                    math.sin(yaw - previous_yaw),
                    math.cos(yaw - previous_yaw),
                )
            )
            if (
                position_shift <= SETTLE_POSITION_TOLERANCE
                and yaw_shift <= SETTLE_YAW_TOLERANCE
            ):
                stable_windows += 1
            else:
                stable_windows = 0
            if stable_windows >= SETTLE_REQUIRED_STABLE_WINDOWS:
                return position, orientation, step, position_shift, yaw_shift

        previous_position = position
        previous_yaw = yaw

    raise RuntimeError(
        "LeKiwi did not reach a stable ground pose: "
        f"position_shift={position_shift:.6f} yaw_shift={yaw_shift:.6f}"
    )


def _create_lighting(stage):
    sun = UsdLux.DistantLight.Define(stage, "/World/KeyboardDriveSun")
    sun.CreateIntensityAttr(1000.0)
    sun.CreateAngleAttr(0.53)
    UsdGeom.XformCommonAPI(sun).SetRotate((45.0, 0.0, 35.0))

    fill = UsdLux.DomeLight.Define(stage, "/World/KeyboardDriveFill")
    fill.CreateIntensityAttr(150.0)


def _create_line_set(stage, path, segments, color, width):
    curves = UsdGeom.BasisCurves.Define(stage, path)
    curves.CreateTypeAttr(UsdGeom.Tokens.linear)
    curves.CreateWrapAttr(UsdGeom.Tokens.nonperiodic)
    curves.CreateCurveVertexCountsAttr(Vt.IntArray([2] * len(segments)))
    points = []
    for start, end in segments:
        points.extend((Gf.Vec3f(*start), Gf.Vec3f(*end)))
    curves.CreatePointsAttr(Vt.Vec3fArray(points))
    curves.CreateWidthsAttr(Vt.FloatArray([width]))
    curves.SetWidthsInterpolation(UsdGeom.Tokens.constant)
    curves.CreateDisplayColorAttr(Vt.Vec3fArray([Gf.Vec3f(*color)]))


def _create_ground_grid(stage):
    grid_z = GROUND_Z + 0.001
    minor_segments = []
    minor_count = round(GRID_HALF_SIZE / GRID_MINOR_SPACING)
    for index in range(-minor_count, minor_count + 1):
        if index % 5 == 0:
            continue
        coordinate = index * GRID_MINOR_SPACING
        minor_segments.extend(
            (
                (
                    (coordinate, -GRID_HALF_SIZE, grid_z),
                    (coordinate, GRID_HALF_SIZE, grid_z),
                ),
                (
                    (-GRID_HALF_SIZE, coordinate, grid_z),
                    (GRID_HALF_SIZE, coordinate, grid_z),
                ),
            )
        )
    _create_line_set(
        stage,
        "/World/DriveGrid/Minor",
        minor_segments,
        color=(0.36, 0.40, 0.48),
        width=0.0015,
    )

    major_segments = []
    major_count = round(GRID_HALF_SIZE / GRID_MAJOR_SPACING)
    for index in range(-major_count, major_count + 1):
        coordinate = index * GRID_MAJOR_SPACING
        major_segments.extend(
            (
                (
                    (coordinate, -GRID_HALF_SIZE, grid_z + 0.0002),
                    (coordinate, GRID_HALF_SIZE, grid_z + 0.0002),
                ),
                (
                    (-GRID_HALF_SIZE, coordinate, grid_z + 0.0002),
                    (GRID_HALF_SIZE, coordinate, grid_z + 0.0002),
                ),
            )
        )
    _create_line_set(
        stage,
        "/World/DriveGrid/Major",
        major_segments,
        color=(0.62, 0.67, 0.78),
        width=0.004,
    )

    _create_line_set(
        stage,
        "/World/DriveGrid/ForwardGuide",
        [
            (
                (-GRID_HALF_SIZE, 0.0, grid_z + 0.0004),
                (GRID_HALF_SIZE, 0.0, grid_z + 0.0004),
            )
        ],
        color=(1.0, 0.72, 0.05),
        width=0.009,
    )


def _set_camera(position, yaw):
    try:
        from isaacsim.core.utils.viewports import set_camera_view

        heading = yaw
        forward_x = math.cos(heading)
        forward_y = math.sin(heading)
        set_camera_view(
            eye=(
                float(position[0] - 0.85 * forward_x),
                float(position[1] - 0.85 * forward_y),
                0.58,
            ),
            target=(
                float(position[0] + 0.08 * forward_x),
                float(position[1] + 0.08 * forward_y),
                0.17,
            ),
            camera_prim_path="/OmniverseKit_Persp",
        )
    except Exception as exc:
        carb.log_warn(f"Could not set camera view: {exc}")


def main():
    print(f"LEKIWI_DRIVE opening_stage={USD_PATH}", flush=True)
    world = World(
        physics_dt=PHYSICS_DT,
        rendering_dt=1.0 / 60.0,
        stage_units_in_meters=1.0,
    )
    robot = world.scene.add(
        WheeledRobot(
            prim_path="/LeKiwi",
            name="lekiwi",
            wheel_dof_names=WHEEL_JOINT_NAMES,
            create_robot=True,
            usd_path=USD_PATH,
            position=np.array([0.0, 0.0, SPAWN_Z]),
        )
    )
    world.scene.add(
        GroundPlane(
            prim_path="/World/KeyboardDriveGround",
            z_position=GROUND_Z,
            size=10.0,
            color=np.array([0.25, 0.27, 0.31]),
        )
    )

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("USD stage was not created")
    articulation_root, root_body = _validate_stage(stage)
    _validate_drive_kinematics()
    _configure_arm_hold(stage)
    _create_ground_grid(stage)
    _create_lighting(stage)
    world.reset()

    arm_indices = np.asarray(
        [robot.get_dof_index(name) for name in ARM_JOINT_NAMES],
        dtype=np.int32,
    )
    robot.set_joint_positions(ARM_HOME_POSITIONS, joint_indices=arm_indices)
    robot.set_joint_velocities(
        np.zeros(len(ARM_JOINT_NAMES), dtype=np.float32),
        joint_indices=arm_indices,
    )
    articulation_controller = robot.get_articulation_controller()
    _hold_arm_home(articulation_controller, arm_indices)

    # Do not define odom until the passive rollers reach a stable ground pose.
    (
        settled_position,
        settled_orientation,
        settle_steps,
        settle_position_shift,
        settle_yaw_shift,
    ) = _settle_on_ground(
        robot, articulation_controller, arm_indices, world, root_body
    )
    settled_yaw = _yaw(settled_orientation)
    if not 0.02 < settled_position[2] < 0.09:
        raise RuntimeError(
            f"LeKiwi did not settle on its wheels: z={settled_position[2]}"
        )
    _set_camera(settled_position, settled_yaw)
    odometry_publisher = RosOdometryPublisher(
        settled_position, settled_yaw
    )
    odometry_publish_interval = max(
        1, round(1.0 / (PHYSICS_DT * ODOM_PUBLISH_HZ))
    )
    odometry_publisher.publish_clock(world.current_time)
    odometry_publisher.publish(
        settled_position, settled_yaw, world.current_time
    )

    pressed = set()
    capture_requested = False
    camera_tracking = False

    def _on_keyboard_event(event):
        nonlocal camera_tracking, capture_requested
        if event.input == carb.input.KeyboardInput.P:
            if event.type == carb.input.KeyboardEventType.KEY_PRESS:
                capture_requested = True
            return True
        if event.input == carb.input.KeyboardInput.T:
            if event.type == carb.input.KeyboardEventType.KEY_PRESS:
                camera_tracking = not camera_tracking
                mode = "TRACKING" if camera_tracking else "FREE"
                camera_mode_label.text = f"camera: {mode} (T to toggle)"
                print(f"LEKIWI_DRIVE camera_mode={mode}", flush=True)
            return True
        if event.input not in CONTROL_KEYS:
            return True
        if event.type in (
            carb.input.KeyboardEventType.KEY_PRESS,
            carb.input.KeyboardEventType.KEY_REPEAT,
        ):
            pressed.add(event.input)
        elif event.type == carb.input.KeyboardEventType.KEY_RELEASE:
            pressed.discard(event.input)
        return True

    app_window = omni.appwindow.get_default_app_window()
    keyboard = app_window.get_keyboard()
    input_interface = carb.input.acquire_input_interface()
    keyboard_subscription = input_interface.subscribe_to_keyboard_events(
        keyboard, _on_keyboard_event
    )

    control_window = ui.Window(
        "LeKiwi + SO101 Physical Drive", width=455, height=285
    )
    with control_window.frame:
        with ui.VStack(spacing=5):
            ui.Label("PhysX contact drive: 36 passive omni rollers", height=24)
            ui.Label("SO101: holding six joints at the home pose")
            ui.Label("Grid: 0.1 m minor / 0.5 m major / yellow W guide")
            ui.Label("Click the viewport, then hold a movement key.")
            ui.Label("W / S : forward / backward")
            ui.Label("A / D : left / right translation")
            ui.Label("Q / E : counter-clockwise / clockwise")
            ui.Label("SPACE : stop    P : save viewport    T : camera mode")
            ui.Label("Close the Isaac window to exit")
            camera_mode_label = ui.Label("camera: FREE (T to toggle)")
            status_label = ui.Label("command: STOP", height=24)

    position = settled_position
    orientation = settled_orientation
    last_command = None
    frame = 0
    capture_task = None
    auto_capture_frame = 180 if CAPTURE_PATH else -1

    print(f"LEKIWI_DRIVE stage={stage.GetRootLayer().identifier}", flush=True)
    print(
        f"LEKIWI_DRIVE articulation_root={articulation_root.GetPath()} "
        "wheel_joints=3 passive_roller_joints=36 arm_joints=6",
        flush=True,
    )
    print(
        "LEKIWI_DRIVE base_control=PHYSX_WHEEL_CONTACT "
        f"ground_z={GROUND_Z:+.4f} settled_z={position[2]:+.4f} "
        "forward_axis=base_link+X",
        flush=True,
    )
    print(
        "LEKIWI_DRIVE settle=STABLE "
        f"steps={settle_steps} position_shift={settle_position_shift:.6f} "
        f"yaw_shift={settle_yaw_shift:.6f}",
        flush=True,
    )
    print(
        "LEKIWI_DRIVE arm_control=HOME_HOLD "
        f"joints={len(arm_indices)} stiffness={ARM_HOLD_STIFFNESS:.1f} "
        f"damping={ARM_HOLD_DAMPING:.1f} max_force={ARM_HOLD_MAX_FORCE:.1f}",
        flush=True,
    )
    print(
        "LEKIWI_DRIVE ground_grid=PASS minor=0.1m major=0.5m "
        "forward_guide=base_link+X",
        flush=True,
    )
    print(
        "LEKIWI_DRIVE ros_odometry=READY topics=/clock,/odom "
        "tf=odom->base_footprint source=ISAAC_GROUND_TRUTH "
        f"simulation_rate_hz={ODOM_PUBLISH_HZ:.1f}",
        flush=True,
    )
    print(
        "LEKIWI_DRIVE controls=W/S forward/back, A/D left/right, "
        "Q/E CCW/CW, SPACE stop, P capture, T camera, window-close exit",
        flush=True,
    )
    print("LEKIWI_DRIVE camera_mode=FREE", flush=True)
    print("LEKIWI_DRIVE result=READY", flush=True)

    try:
        while simulation_app.is_running():
            frame += 1
            if frame == auto_capture_frame:
                capture_requested = True

            if CAPTURE_PATH and capture_requested and (
                capture_task is None or capture_task.done()
            ):
                capture_requested = False
                from omni.kit.viewport.utility import (
                    capture_viewport_to_file,
                    get_active_viewport,
                )

                viewport = get_active_viewport()
                if viewport is None:
                    print("LEKIWI_DRIVE capture=NO_ACTIVE_VIEWPORT", flush=True)
                else:

                    async def _capture_viewport():
                        await capture_viewport_to_file(
                            viewport, file_path=CAPTURE_PATH, is_hdr=False
                        ).wait_for_result()
                        print(
                            f"LEKIWI_DRIVE capture={CAPTURE_PATH}", flush=True
                        )

                    capture_task = asyncio.ensure_future(_capture_viewport())

            forward = float(carb.input.KeyboardInput.W in pressed) - float(
                carb.input.KeyboardInput.S in pressed
            )
            left = float(carb.input.KeyboardInput.A in pressed) - float(
                carb.input.KeyboardInput.D in pressed
            )
            ccw = float(carb.input.KeyboardInput.Q in pressed) - float(
                carb.input.KeyboardInput.E in pressed
            )
            if carb.input.KeyboardInput.SPACE in pressed:
                forward = 0.0
                left = 0.0
                ccw = 0.0

            linear_norm = math.hypot(forward, left)
            if linear_norm > 1.0:
                forward /= linear_norm
                left /= linear_norm

            vx = LINEAR_SPEED * forward
            vy = LINEAR_SPEED * left
            wz = ANGULAR_SPEED * ccw
            wheel_speeds = _wheel_speeds(vx, vy, wz)
            _apply_command(robot, vx, vy, wz)
            _hold_arm_home(articulation_controller, arm_indices)
            world.step(render=True)

            position, orientation = _base_pose(root_body)
            yaw = _yaw(orientation)
            odometry_publisher.publish_clock(world.current_time)
            if frame % odometry_publish_interval == 0:
                odometry_publisher.publish(
                    position, yaw, world.current_time
                )
            if camera_tracking and frame % 4 == 0:
                _set_camera(position, yaw)

            command = (int(forward), int(left), int(ccw))
            if command != last_command:
                print(
                    f"LEKIWI_DRIVE command forward={command[0]} "
                    f"left={command[1]} ccw={command[2]} "
                    "wheel_rad_s="
                    + ",".join(f"{value:+.2f}" for value in wheel_speeds),
                    flush=True,
                )
                last_command = command

            if command != (0, 0, 0) and frame % 30 == 0:
                print(
                    "LEKIWI_DRIVE physical_pose "
                    f"x={position[0]:+.4f} y={position[1]:+.4f} "
                    f"z={position[2]:+.4f} yaw_deg={math.degrees(yaw):+.2f}",
                    flush=True,
                )

            if command == (0, 0, 0):
                status_label.text = "command: STOP (PhysX active)"
            else:
                status_label.text = (
                    f"vx={vx:+.2f}  vy={vy:+.2f}  wz={wz:+.2f}  "
                    f"wheel={wheel_speeds[0]:+.1f},"
                    f"{wheel_speeds[1]:+.1f},{wheel_speeds[2]:+.1f}"
                )
    finally:
        pressed.clear()
        try:
            _apply_command(robot, 0.0, 0.0, 0.0)
            _hold_arm_home(articulation_controller, arm_indices)
            world.step(render=False)
            world.stop()
        except Exception as exc:
            carb.log_warn(f"Could not stop LeKiwi cleanly: {exc}")
        keyboard_subscription = None
        odometry_publisher.close()


failed = False
try:
    main()
except Exception:
    failed = True
    print("LEKIWI_DRIVE result=FAIL", flush=True)
    traceback.print_exc()
finally:
    simulation_app.close()

if failed:
    sys.exit(1)
