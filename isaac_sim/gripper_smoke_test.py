"""실제 로봇 자산의 닫기·가상 팔 이동·놓기 검사. USB를 사용하지 않는다."""

from isaacsim import SimulationApp

app = SimulationApp(
    {"headless": True, "limit_cpu_threads": 16, "width": 640, "height": 480}
)
import math
from pathlib import Path
import numpy as np
import omni.usd
from pxr import Usd, UsdGeom, UsdPhysics, PhysxSchema, Gf
from isaacsim.core.api import World
from isaacsim.core.api.objects import DynamicCuboid, GroundPlane
from isaacsim.core.api.materials import PhysicsMaterial
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot.wheeled_robots.robots import WheeledRobot
from teleop_bridge import JOINTS
from arm_control import restore_arm_position_gains
from gripper_contacts import configure_gripper_collisions


def main():
    world = World(physics_dt=1 / 120, rendering_dt=1 / 60, stage_units_in_meters=1.0)
    stage = omni.usd.get_context().get_stage()
    robots = []
    world.scene.add(GroundPlane("/World/Ground", z_position=-0.021, size=10.0))
    cases = [(0, 0), (20, 0), (-20, 0), (45, 0), (0, 0.003), (0, -0.003)]
    for i, (yaw, offset) in enumerate(cases):
        case_name = f"yaw={yaw},offset={offset}"
        root = "/Robot" + str(i)
        robot = world.scene.add(
            WheeledRobot(
                prim_path=root,
                name="robot" + str(i),
                create_robot=True,
                wheel_dof_names=[
                    "back_wheel_joint",
                    "left_wheel_joint",
                    "right_wheel_joint",
                ],
                usd_path=str(
                    Path(__file__).resolve().parent
                    / "assets/lekiwi_soarm/usd/lekiwi_soarm.usd"
                ),
                position=np.array([i * 0.8, 0, 0.055]),
            )
        )
        configure_gripper_collisions(stage, root + "/base_link")
        for prim in stage.Traverse():
            if (
                str(prim.GetPath()).startswith(root + "/")
                and prim.GetName() in JOINTS
                and prim.IsA(UsdPhysics.RevoluteJoint)
            ):
                drive = UsdPhysics.DriveAPI(prim, "angular")
                drive.GetStiffnessAttr().Set(10000)
                drive.GetDampingAttr().Set(200)
                drive.GetMaxForceAttr().Set(1000)
        cube = world.scene.add(
            DynamicCuboid(
                root + "/ProbeCube",
                name="cube" + str(i),
                position=np.array([i * 0.8, 0.5, 0.4]),
                size=0.04,
                mass=0.035,
                physics_material=PhysicsMaterial(
                    root + "/CubeMaterial",
                    static_friction=0.8,
                    dynamic_friction=0.6,
                    restitution=0.0,
                ),
            )
        )
        gravity_api = PhysxSchema.PhysxRigidBodyAPI.Apply(
            stage.GetPrimAtPath(root + "/ProbeCube")
        )
        # 시험 배치 중에만 중력을 끈다. 닫은 뒤 이동·유지·놓기는 중력을 켠다.
        # 바닥 접근이나 전체 집기 작업의 성공률을 측정하는 시험은 아니다.
        gravity_api.CreateDisableGravityAttr(True)
        robots.append((case_name, root, robot, cube, gravity_api))
    world.reset()
    controls = []
    for case_name, root, robot, cube, gravity_api in robots:
        indices = np.array([robot.get_dof_index(n) for n in JOINTS], dtype=np.int32)
        controller = robot.get_articulation_controller()
        restore_arm_position_gains(controller, indices)
        targets = np.array([0, 0, 0, 0, -math.pi / 2, math.pi / 3])
        robot.set_joint_positions(targets, joint_indices=indices)
        controls.append((indices, controller, targets))

    def step():
        for (case_name, root, robot, cube, gravity_api), (
            indices,
            controller,
            targets,
        ) in zip(robots, controls):
            controller.apply_action(
                ArticulationAction(joint_positions=targets, joint_indices=indices)
            )
            robot.apply_wheel_actions(ArticulationAction(joint_velocities=np.zeros(3)))
        world.step(render=False)

    def transform(root):
        return UsdGeom.Xformable(
            stage.GetPrimAtPath(root + "/base_link/gripper_link")
        ).ComputeLocalToWorldTransform(Usd.TimeCode.Default())

    def relative(root, cube):
        return np.array(
            transform(root)
            .GetInverse()
            .Transform(Gf.Vec3d(*cube.get_world_pose()[0].astype(float)))
        )

    # 원격 조작 입력 없이 바퀴와 팔을 안정시킨다.
    for _ in range(360):
        step()
    for i, (case_name, root, robot, cube, gravity_api) in enumerate(robots):
        yaw, offset = cases[i]
        matrix = transform(root)
        rotation = (
            Gf.Transform(matrix).GetRotation().GetQuat()
            * Gf.Rotation(Gf.Vec3d(0, 0, 1), yaw).GetQuat()
        )
        cube.set_world_pose(
            np.array(matrix.Transform(Gf.Vec3d(0.014 + offset, 0, -0.08))),
            np.array([rotation.GetReal(), *rotation.GetImaginary()]),
        )
        cube.set_linear_velocity(np.zeros(3))
        cube.set_angular_velocity(np.zeros(3))
        print("ROBOT_START", case_name, cube.get_world_pose()[0].tolist(), flush=True)
    for k in range(240):
        for indices, controller, targets in controls:
            targets[5] = max(0.0, math.pi / 3 * (1 - k / 180))
        step()
    closed_poses = []
    for i, (case_name, root, robot, cube, gravity_api) in enumerate(robots):
        closed = relative(root, cube)
        # 비스듬한 큐브가 닫히며 정렬되는 이동과, 잡은 후의 미끄럼을 구분한다.
        # 닫힌 큐브는 손가락 사이에 남아 있어야 한다.
        assert np.linalg.norm(closed - [0.014 + cases[i][1], 0, -0.08]) < 0.025
        closed_poses.append(closed)
        print("ROBOT_CLOSE", case_name, closed.tolist(), flush=True)
        gravity_api.GetDisableGravityAttr().Set(False)
    # 어깨 회전과 손목 회전을 2초 동안 적용한 뒤 4초간 유지한다.
    for k in range(720):
        for indices, controller, targets in controls:
            targets[0] = 0.35 * min(1, k / 240)
            targets[4] = -math.pi / 2 + 0.25 * min(1, k / 240)
        step()
    for i, (case_name, root, robot, cube, gravity_api) in enumerate(robots):
        delta = np.linalg.norm(relative(root, cube) - closed_poses[i])
        print("GRIP_HOLD", case_name, "slip_m", delta, flush=True)
        assert delta < 0.005, (case_name, delta)
    # 집게를 열면 실제 중력에 의해 분리돼야 한다. 큐브를 부착하지 않는다.
    for indices, controller, targets in controls:
        targets[5] = 1.1
    for _ in range(180):
        step()
    for case_name, root, robot, cube, gravity_api in robots:
        distance = np.linalg.norm(relative(root, cube) - [0.014, 0, -0.08])
        print("GRIP_RELEASE", case_name, "distance_m", distance, flush=True)
        assert distance > 0.08, (case_name, distance)
    print("LEKIWI_GRIP_TEST result=PASS", flush=True)


try:
    main()
finally:
    app.close()
