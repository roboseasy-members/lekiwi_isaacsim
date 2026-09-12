"""Interactive PhysX contact-drive test for LeKiwi + SO101 in Isaac Sim."""

import os

from isaacsim import SimulationApp
from app_runtime import launch_config, enable_streaming


simulation_app = SimulationApp(
    launch_config({
        "headless": False,
        "width": 1440,
        "height": 900,
        "sync_loads": False,
        # 녹화 중 프레임을 건너뛰는 비동기 렌더 전환을 막습니다.
        "extra_args": ["--/exts/isaacsim.core.throttling/enable_async=false",
                       "--/app/hydraEngine/waitIdle=1",
                       "--/app/updateOrder/checkForHydraRenderComplete=1000"]
            if os.environ.get("LEKIWI_RECORDING") == "1" else [],
    })
)
stream_connection = enable_streaming(simulation_app)

import asyncio
import math
import sys
import traceback
import time
from pathlib import Path

import carb
import carb.input
import numpy as np
import omni.appwindow
import omni.usd
from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics, Vt

from isaacsim.core.api import World
from isaacsim.core.api.objects.ground_plane import GroundPlane
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot.wheeled_robots.robots import WheeledRobot
from teleop_bridge import ArmTeleop, DEFAULT_ARM_OFFSETS_DEG, arm_home, atomic_json, read_packet
from arm_control import restore_arm_position_gains
from drive_controls import BaseSpeed
from drive_hotkeys import SpaceStopBinding, RecordingKeyBinding
from robot_cameras import attach_cameras, load_camera_config
from scene_tools import SceneReset, SplitView, reset_allowed, randomize_layout
from gripper_contacts import configure_gripper_collisions

USD_PATH = os.environ.get(
    "LEKIWI_USD",
    str(Path(__file__).resolve().parent / "assets/lekiwi_soarm/usd/lekiwi_soarm.usd"),
)
CAPTURE_PATH = os.environ.get("LEKIWI_CAPTURE_PATH", "")
TELEOP_STATE = os.environ.get("LEKIWI_TELEOP_STATE", "")
TELEOP_SESSION = os.environ.get("LEKIWI_TELEOP_SESSION", "")
COURSE_LAYOUT = os.environ.get("LEKIWI_COURSE_LAYOUT", "")
RECORDING = os.environ.get("LEKIWI_RECORDING", "0") == "1"
GROUND_Z = float(os.environ.get("LEKIWI_GROUND_Z", "-0.021"))
SPAWN_Z = float(os.environ.get("LEKIWI_SPAWN_Z", "0.055"))
LINEAR_SPEED = float(os.environ.get("LEKIWI_LINEAR_SPEED", "0.25"))
ANGULAR_SPEED = float(os.environ.get("LEKIWI_ANGULAR_SPEED", "0.8"))
PHYSICS_DT = float(os.environ.get("LEKIWI_PHYSICS_DT", str(1.0 / 120.0)))
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
ARM_OFFSETS_DEG = tuple(float(v) for v in os.environ.get(
    "LEKIWI_ARM_OFFSETS_DEG", ",".join(map(str, DEFAULT_ARM_OFFSETS_DEG))).split(","))
ARM_HOME_POSITIONS = np.asarray(arm_home(ARM_OFFSETS_DEG), dtype=np.float32)
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
        rendering_dt=1.0 / (30.0 if RECORDING else 60.0),
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
    if not COURSE_LAYOUT:
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
    if COURSE_LAYOUT:
        from collection_course import generate_layout, read_layout, save_course, attach_course, validate_layout
        if COURSE_LAYOUT == "prepared":
            import json
            layout = validate_layout(json.loads(os.environ["LEKIWI_COURSE_JSON"]))
        elif COURSE_LAYOUT == "random":
            from color_course import generate_color_layout
            layout = generate_color_layout()
        elif COURSE_LAYOUT == "generate":
            seed = os.environ.get("LEKIWI_COURSE_SEED")
            layout = generate_layout(None if seed is None else int(seed),
                                     int(os.environ.get("LEKIWI_COURSE_START_COUNT", "2")),
                                     int(os.environ.get("LEKIWI_COURSE_MIDDLE_COUNT", "3")))
        else:
            layout = read_layout(COURSE_LAYOUT)
        directory = save_course(layout)
        attach_course(stage, directory)
        print(f"LEKIWI_COURSE saved={directory} seed={layout['seed']} objects={len(layout['objects'])}", flush=True)
    articulation_root, root_body = _validate_stage(stage)
    _validate_drive_kinematics()
    _configure_arm_hold(stage)
    finger_colliders = configure_gripper_collisions(stage)
    print(f"LEKIWI_GRIP collision=convexDecomposition fingers={len(finger_colliders)}", flush=True)
    if not COURSE_LAYOUT:
        _create_ground_grid(stage)
    _create_lighting(stage)
    camera_config = load_camera_config(os.environ.get("LEKIWI_CAMERA_CONFIG"))
    robot_cameras = attach_cameras(stage, camera_config)
    for name, info in robot_cameras.items():
        print(f"LEKIWI_CAMERA name={name} path={info['camera_path']} optical_frame={info['optical_frame']}", flush=True)
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
    restore_arm_position_gains(articulation_controller, arm_indices,
                               ARM_HOLD_STIFFNESS, ARM_HOLD_DAMPING)
    _hold_arm_home(articulation_controller, arm_indices)

    # Wait for passive roller contacts to settle before accepting input.
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
    if COURSE_LAYOUT:
        from isaacsim.core.utils.viewports import set_camera_view
        set_camera_view(eye=(-6.0, 0, 7.0) if layout["version"] == 2 else (.0, -4.2, 3.5),
                        target=(0, 0, .05) if layout["version"] == 2 else (1.7, 0, .05),
                        camera_prim_path="/OmniverseKit_Persp")

    pressed = set()
    base_speed = BaseSpeed(LINEAR_SPEED, ANGULAR_SPEED)
    arm_requested = False
    arm_control = None
    if TELEOP_STATE:
        if not TELEOP_SESSION:
            raise RuntimeError("SO101 teleop requires an isolated session ID")
        signs = tuple(int(v) for v in os.environ.get("LEKIWI_ARM_SIGNS", "1,1,1,1,1,1").split(","))
        offsets = ARM_OFFSETS_DEG
        speed = float(os.environ.get("LEKIWI_ARM_MAX_SPEED", "3.0"))
        arm_control = ArmTeleop(TELEOP_SESSION, signs=signs, offsets_deg=offsets, max_speed=speed,
                               remote=os.environ.get("LEKIWI_TELEOP_REMOTE") == "1")
        print(f"LEKIWI_DRIVE absolute_mapping signs={signs} offsets_deg={offsets} "
              f"max_speed_rad_s={speed} input_timeout_ms={arm_control.timeout * 1000:.0f}", flush=True)
    capture_requested = False
    reset_requested = False
    recorder = None
    camera_tracking = False
    camera_view = "overview"
    split_view = None
    from omni.kit.viewport.utility import get_active_viewport
    main_viewport = get_active_viewport()

    def _request_reset():
        nonlocal reset_requested
        reset_requested = True

    def _select_camera(name):
        nonlocal camera_view, camera_tracking
        if main_viewport is None:
            carb.log_warn("No viewport available for camera selection")
            return
        main_viewport.camera_path = ("/OmniverseKit_Persp" if name == "overview"
                                     else robot_cameras[name]["camera_path"])
        camera_view = name
        camera_tracking = False
        print(f"LEKIWI_DRIVE camera_view={name}", flush=True)

    speed_keys = {carb.input.KeyboardInput.KEY_1: 1,
                  carb.input.KeyboardInput.KEY_2: 2,
                  carb.input.KeyboardInput.KEY_3: 3,
                  carb.input.KeyboardInput.NUMPAD_1: 1,
                  carb.input.KeyboardInput.NUMPAD_2: 2,
                  carb.input.KeyboardInput.NUMPAD_3: 3}

    def _on_keyboard_event(event):
        nonlocal camera_tracking, capture_requested, arm_requested
        if stream_connection and not stream_connection.input_allowed:
            return True
        if event.type == carb.input.KeyboardEventType.KEY_PRESS:
            key_name = event.input.name
            if key_name == "F8":
                _request_reset()
                return True
            if recorder and key_name in {"F5", "F6", "F7", "F9", "F10"}:
                recorder.handle_key(key_name)
                return True
        if event.input in speed_keys:
            if event.type == carb.input.KeyboardEventType.KEY_PRESS:
                base_speed.select(speed_keys[event.input])
                print(f"LEKIWI_DRIVE {base_speed.label}", flush=True)
            return True
        if event.input == carb.input.KeyboardInput.R:
            if event.type == carb.input.KeyboardEventType.KEY_PRESS:
                arm_requested = True
            return True
        if event.input == carb.input.KeyboardInput.P:
            if event.type == carb.input.KeyboardEventType.KEY_PRESS:
                capture_requested = True
            return True
        if event.input == carb.input.KeyboardInput.T:
            if event.type == carb.input.KeyboardEventType.KEY_PRESS:
                if camera_view != "overview":
                    _select_camera("overview")
                camera_tracking = not camera_tracking
                mode = "TRACKING" if camera_tracking else "FREE"
                print(f"LEKIWI_DRIVE camera_mode={mode}", flush=True)
            return True
        if event.input == carb.input.KeyboardInput.C:
            if event.type == carb.input.KeyboardEventType.KEY_PRESS:
                choices = ("overview", "front", "wrist")
                _select_camera(choices[(choices.index(camera_view) + 1) % len(choices)])
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

    print("LEKIWI_CONTROLS W/S 앞뒤 A/D 좌우 Q/E 회전 | 1/2/3 속도 | SPACE 정지 | R 팔 활성화", flush=True)
    print("LEKIWI_CONTROLS F8 장면 초기화/큐브 재배치 | C 카메라 | T 추적 | P 화면 저장", flush=True)
    print("LEKIWI_CONTROLS 기록: F5 시작 F6 종료 F7 연습 저장 F9 성공 저장 F10 두 번 폐기", flush=True)

    # 사용자가 시점을 전환하기 전에 세 카메라의 렌더링을 준비한다.
    for name in ("front", "wrist", "overview"):
        _select_camera(name)
        for _ in range(3):
            world.step(render=True)

    bodies = []
    if COURSE_LAYOUT:
        from isaacsim.core.prims import SingleRigidPrim
        from collection_course import ROOT as COURSE_ROOT
        for obj in layout["objects"]:
            body = SingleRigidPrim(COURSE_ROOT + "/Objects/" + obj["id"],
                                   name="reset_" + obj["id"], reset_xform_properties=False)
            body.initialize()
            bodies.append(body)
    scene_reset = SceneReset(robot, bodies)
    split_view = SplitView(robot_cameras["front"]["camera_path"])
    main_viewport = split_view.main

    recorder = None
    recording_overlay = None
    if RECORDING:
        from recording_panel import RecordingPanel
        from recording_overlay import RecordingOverlay
        recorder = RecordingPanel(robot_cameras, camera_config,
                                  "so101_leader_keyboard" if arm_control else "keyboard_home_hold",
                                  layout if COURSE_LAYOUT else None)
        recorder.metadata["gripper_collision_approximation"] = "convexDecomposition"
        recording_overlay = RecordingOverlay(split_view.main_window)
        recording_overlay.update(recorder, arm_control)

    def recording_state():
        # 베이스 속도는 world 좌표에서 로봇의 수평 base 좌표로 변환한다.
        pos, quat = _base_pose(root_body)
        heading = _yaw(quat)
        linear = robot.get_linear_velocity()
        angular = robot.get_angular_velocity()
        state = [float(v) for v in robot.get_joint_positions(joint_indices=arm_indices)]
        state += [float(math.cos(heading) * linear[0] + math.sin(heading) * linear[1]),
                  float(-math.sin(heading) * linear[0] + math.cos(heading) * linear[1]), float(angular[2])]
        return state, [float(v) for v in (*pos, *quat)]

    position = settled_position
    orientation = settled_orientation
    last_command = None
    last_arm_status = None
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
        f"LEKIWI_DRIVE arm_control={'SO101_LEADER' if arm_control else 'HOME_HOLD'} "
        f"joints={len(arm_indices)} stiffness={ARM_HOLD_STIFFNESS:.1f} "
        f"damping={ARM_HOLD_DAMPING:.1f} max_force={ARM_HOLD_MAX_FORCE:.1f}",
        flush=True,
    )
    print(
        "LEKIWI_DRIVE course=READY lane_direction=base_link+X" if COURSE_LAYOUT else
        "LEKIWI_DRIVE ground_grid=PASS minor=0.1m major=0.5m forward_guide=base_link+X",
        flush=True,
    )
    print(
        "LEKIWI_DRIVE controls=W/S forward/back, A/D left/right, "
        "Q/E CCW/CW, 1/2/3 base speed, SPACE stop, P capture, T tracking, C camera, window-close exit",
        flush=True,
    )
    print("LEKIWI_DRIVE camera_mode=FREE", flush=True)
    print(f"LEKIWI_DRIVE {base_speed.label}", flush=True)
    print("LEKIWI_DRIVE result=READY", flush=True)

    from omni.kit.hotkeys.core import KeyCombination, get_hotkey_registry
    space_binding = SpaceStopBinding(get_hotkey_registry(), KeyCombination(carb.input.KeyboardInput.SPACE, 0))
    # F7 저장·F10 폐기가 기본 UI 숨기기·스크린샷과 함께 실행되지 않도록 합니다.
    recording_key_bindings = [
        RecordingKeyBinding(get_hotkey_registry(), KeyCombination(key, 0))
        for key in (carb.input.KeyboardInput.F7, carb.input.KeyboardInput.F10)
    ] if RECORDING else []
    print(f"LEKIWI_DRIVE space_stop_only={len(space_binding.removed)}", flush=True)
    print(f"LEKIWI_DRIVE recording_keys_only={sum(len(binding.removed) for binding in recording_key_bindings)}", flush=True)
    try:
        while simulation_app.is_running():
            frame += 1
            if stream_connection:
                changed = stream_connection.consume_reset()
                if changed or not stream_connection.input_allowed:
                    pressed.clear()
                    arm_requested = False
                    if arm_control:
                        arm_control.armed = False
            if split_view.task.done():
                split_view.task.result()
            if reset_requested:
                reset_requested = False
                if not reset_allowed(recorder):
                    print("LEKIWI_RESET blocked: F6으로 기록을 끝내고 F7/F9 저장 또는 F10 두 번 폐기 후 기다리세요.", flush=True)
                else:
                    pressed.clear()
                    arm_requested = False
                    _apply_command(robot, 0.0, 0.0, 0.0)
                    new_layout = randomize_layout(layout) if COURSE_LAYOUT else None
                    if new_layout:
                        directory = save_course(new_layout)
                    scene_reset.restore(new_layout)
                    if new_layout:
                        layout = new_layout
                        stage.GetPrimAtPath(COURSE_ROOT).SetCustomDataByKey("seed", str(layout["seed"]))
                        if recorder:
                            recorder.metadata["course_layout"] = layout
                            recorder.resume_frames = 3
                        print(f"LEKIWI_COURSE saved={directory} seed={layout['seed']} reset=True", flush=True)
                    if arm_control:
                        arm_control.armed = False
                        arm_control.targets = scene_reset.joints[arm_indices].tolist()
                        arm_control.goals = arm_control.targets[:]
                        arm_control.last_update = None
                    restore_arm_position_gains(articulation_controller, arm_indices,
                                               ARM_HOLD_STIFFNESS, ARM_HOLD_DAMPING)
                    print("LEKIWI_RESET ready. Teleop은 R로 다시 활성화하세요.", flush=True)
                    print("LEKIWI_DRIVE scene_reset=PASS teleop_disarmed=True", flush=True)
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
            if arm_control:
                targets = arm_control.update(
                    read_packet(TELEOP_STATE), time.monotonic(),
                    robot.get_joint_positions(joint_indices=arm_indices),
                    arm=arm_requested, stop=carb.input.KeyboardInput.SPACE in pressed,
                )
                arm_requested = False
                if not arm_control.armed:
                    # Require a fresh key press after watchdog/SPACE/recovery.
                    pressed.clear()
                    forward = left = ccw = 0.0
            if carb.input.KeyboardInput.SPACE in pressed:
                forward = 0.0
                left = 0.0
                ccw = 0.0

            vx, vy, wz = base_speed.velocity(forward, left, ccw)
            wheel_speeds = _wheel_speeds(vx, vy, wz)
            _apply_command(robot, vx, vy, wz)
            if arm_control:
                articulation_controller.apply_action(ArticulationAction(
                    joint_positions=np.asarray(targets, dtype=np.float32), joint_indices=arm_indices,
                ))
            else:
                _hold_arm_home(articulation_controller, arm_indices)
            if recorder:
                state, pose = recording_state()
                action = [float(v) for v in (targets if arm_control else ARM_HOME_POSITIONS)] + [vx, vy, wz]
                recorder.before_step(world, state, action, pose)
            world.step(render=True)
            if not simulation_app.is_running():
                break
            if recorder:
                recorder.after_step(world, recording_state()[0])
                recording_overlay.update(recorder, arm_control)

            if arm_control:
                if arm_control.status != last_arm_status:
                    print(f"LEKIWI_DRIVE SO101 {arm_control.status}", flush=True)
                    last_arm_status = arm_control.status
                if frame % 30 == 0:
                    atomic_json(Path(TELEOP_STATE).with_name("sim.json"), {
                        "session": TELEOP_SESSION, "monotonic": time.monotonic(),
                        "armed": arm_control.armed, "status": arm_control.status,
                        "joint_names": list(ARM_JOINT_NAMES), "unit": "radians",
                        "targets": arm_control.targets,
                        "goals": arm_control.goals, "clipped": arm_control.clipped,
                        "base_speed_level": base_speed.level,
                        "base_command": {"vx_m_s": vx, "vy_m_s": vy, "wz_rad_s": wz},
                        "actual": [float(v) for v in robot.get_joint_positions(joint_indices=arm_indices)],
                    })

            position, orientation = _base_pose(root_body)
            yaw = _yaw(orientation)
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

    finally:
        pressed.clear()
        if recording_overlay:
            recording_overlay.close()
        if recorder:
            try:
                recorder.close()
            except Exception as exc:
                carb.log_warn(f"Could not close recording resources: {exc}")
        try:
            _apply_command(robot, 0.0, 0.0, 0.0)
            if arm_control:
                articulation_controller.apply_action(ArticulationAction(
                    joint_positions=np.asarray(arm_control.targets, dtype=np.float32), joint_indices=arm_indices,
                ))
            else:
                _hold_arm_home(articulation_controller, arm_indices)
            world.step(render=False)
            world.stop()
        except Exception as exc:
            carb.log_warn(f"Could not stop LeKiwi cleanly: {exc}")
        input_interface.unsubscribe_to_keyboard_events(keyboard, keyboard_subscription)
        space_binding.close()
        for binding in recording_key_bindings:
            binding.close()
        if split_view:
            split_view.close()
        if stream_connection:
            stream_connection.close()


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
