"""실행 중 가상 장면 초기화와 두 뷰포트 배치. 실제 장치는 조작하지 않는다."""
import asyncio
import math

import numpy as np


def reset_allowed(recorder):
    return recorder is None or (recorder.mode in {"READY", "SAVED", "DISCARDED"}
                                and not recorder.requests)


def randomize_layout(layout):
    from collection_course import generate_layout
    from color_course import generate_color_layout
    if layout["version"] == 2:
        return generate_color_layout(block=layout["task"]["block"], basket=layout["task"]["basket"])
    return generate_layout(start_count=sum(o["zone"] == "start" for o in layout["objects"]),
                           middle_count=sum(o["zone"] == "middle" for o in layout["objects"]))


class SceneReset:
    def __init__(self, robot, bodies):
        self.robot = robot
        self.robot_pose = tuple(np.array(v, copy=True) for v in robot.get_world_pose())
        self.joints = robot.get_joint_positions().copy()
        self.bodies = bodies
        self.poses = [tuple(np.array(v, copy=True) for v in body.get_world_pose()) for body in bodies]

    def restore(self, layout=None):
        poses = self.poses
        if layout is not None:
            poses = [(np.asarray(o["position"]), np.array([math.cos(math.radians(o["yaw_deg"]) / 2),
                      0, 0, math.sin(math.radians(o["yaw_deg"]) / 2)])) for o in layout["objects"]]
            if len(poses) != len(self.bodies):
                raise ValueError("Reset object count changed")
        self.robot.set_world_pose(*self.robot_pose)
        self.robot.set_joint_positions(self.joints.copy())
        self.robot.set_joint_velocities(np.zeros_like(self.joints))
        self.robot.set_linear_velocity(np.zeros(3))
        self.robot.set_angular_velocity(np.zeros(3))
        for body, pose in zip(self.bodies, poses):
            body.set_world_pose(*pose)
            body.set_linear_velocity(np.zeros(3))
            body.set_angular_velocity(np.zeros(3))


class SplitView:
    def __init__(self, camera_path):
        import omni.kit.app
        import omni.ui as ui
        from omni.kit.viewport.utility import get_active_viewport_window, create_viewport_window

        main = get_active_viewport_window()
        if main is None:
            raise RuntimeError("Perspective viewport is not available")
        self.main_window = main
        self.main = main.viewport_api
        self.main.camera_path = "/OmniverseKit_Persp"
        self.front = create_viewport_window("LeKiwi Front Camera", width=640, height=480,
                                            camera_path=camera_path)
        if self.front is None:
            raise RuntimeError("Front camera viewport could not be created")

        async def dock():
            # Stage 도킹과 새 창 생성이 반영된 뒤 화면 영역을 반으로 나눈다.
            for _ in range(5):
                await omni.kit.app.get_app().next_update_async()
            target = ui.Workspace.get_window(main.title)
            front = ui.Workspace.get_window(self.front.title)
            if target is None or front is None:
                raise RuntimeError("Viewport docking targets are unavailable")
            front.dock_in(target, ui.DockPosition.RIGHT, 0.5)
            print("LEKIWI_DRIVE view_layout=PERSPECTIVE_LEFT_FRONT_RIGHT", flush=True)

        self.task = asyncio.ensure_future(dock())

    def close(self):
        if not self.task.done():
            self.task.cancel()
        self.front.destroy()
