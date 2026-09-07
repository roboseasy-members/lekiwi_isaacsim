"""Real PhysX course check: robot spawn, ground objects and open basket. No USB."""
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})

from pathlib import Path
import tempfile
import traceback
import numpy as np
import omni.usd
from pxr import Gf, Usd, UsdGeom, UsdPhysics
from isaacsim.core.api import World
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot.wheeled_robots.robots import WheeledRobot
from collection_course import ROOT, EDGE, GROUND_Z, save_course, attach_course
from color_course import COLORS, RING_RADIUS, generate_color_layout
from teleop_bridge import JOINTS, DEFAULT_ARM_OFFSETS_DEG, arm_home
from arm_control import restore_arm_position_gains


def main():
    world = World(physics_dt=1 / 120, rendering_dt=1 / 60, stage_units_in_meters=1.0)
    stage = omni.usd.get_context().get_stage()
    layout = generate_color_layout(42, "green", "red")
    with tempfile.TemporaryDirectory(prefix="course-test-") as parent:
        directory = save_course(layout, parent)
        attach_course(stage, directory)
        robot = world.scene.add(WheeledRobot(
            prim_path="/LeKiwi", name="lekiwi", create_robot=True,
            wheel_dof_names=["back_wheel_joint", "left_wheel_joint", "right_wheel_joint"],
            usd_path=str(Path(__file__).parent / "assets/lekiwi_soarm/usd/lekiwi_soarm.usd"),
            position=np.array([0., 0., .055]),
        ))
        # Drop a separate probe into the basket: a solid-box collider would fail.
        probes = []
        for basket in layout["baskets"]:
            center = basket["position"][:2]
            probe = UsdGeom.Cube.Define(stage, ROOT + "/Probe_" + basket["id"])
            probe.CreateSizeAttr(EDGE)
            probe.AddTranslateOp().Set(Gf.Vec3d(*center, .45))
            UsdPhysics.CollisionAPI.Apply(probe.GetPrim())
            UsdPhysics.RigidBodyAPI.Apply(probe.GetPrim())
            UsdPhysics.MassAPI.Apply(probe.GetPrim()).CreateMassAttr(.035)
            probes.append((probe, center))
        ring_probes = []
        for i in range(8):
            angle = 2 * np.pi * i / 8
            center = [RING_RADIUS * np.cos(angle), RING_RADIUS * np.sin(angle)]
            probe = UsdGeom.Cube.Define(stage, ROOT + f"/RingProbe_{i}")
            probe.CreateSizeAttr(EDGE)
            probe.AddTranslateOp().Set(Gf.Vec3d(*center, .15))
            UsdPhysics.CollisionAPI.Apply(probe.GetPrim())
            UsdPhysics.RigidBodyAPI.Apply(probe.GetPrim())
            UsdPhysics.MassAPI.Apply(probe.GetPrim()).CreateMassAttr(.035)
            ring_probes.append((probe, center))
        world.reset()
        indices = np.array([robot.get_dof_index(n) for n in JOINTS], dtype=np.int32)
        home = np.array(arm_home(DEFAULT_ARM_OFFSETS_DEG))
        robot.set_joint_positions(home, joint_indices=indices)
        controller = robot.get_articulation_controller()
        restore_arm_position_gains(controller, indices)
        for _ in range(600):
            robot.apply_wheel_actions(ArticulationAction(joint_velocities=np.zeros(3)))
            controller.apply_action(ArticulationAction(joint_positions=home, joint_indices=indices))
            world.step(render=False)
        def position(path):
            return np.array(UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(
                Usd.TimeCode.Default()).ExtractTranslation())
        for o in layout["objects"]:
            actual = position(ROOT + "/Objects/" + o["id"])
            assert np.all(np.isfinite(actual))
            assert abs(actual[2] - (GROUND_Z + EDGE / 2)) < .004, (o["id"], actual)
            assert np.linalg.norm(actual[:2] - o["position"][:2]) < .01
        for probe, center in probes:
            basket_probe = position(str(probe.GetPath()))
            assert np.linalg.norm(basket_probe[:2] - center) < .03
            assert abs(basket_probe[2] - (GROUND_Z + .015 + EDGE / 2)) < .004, basket_probe
        for probe, center in ring_probes:
            actual = position(str(probe.GetPath()))
            assert np.linalg.norm(actual[:2] - center) < .01
            assert abs(actual[2] - (GROUND_Z + EDGE / 2)) < .004, actual
        base = position("/LeKiwi/base_link/base_link")
        assert .02 < base[2] < .09 and np.linalg.norm(base[:2]) < .03, base
        print(f"LEKIWI_COURSE_TEST objects={len(layout['objects'])} open_baskets={len(probes)} "
              f"ring_contacts={len(ring_probes)} base={base}", flush=True)
        world.stop()
    print("LEKIWI_COURSE_TEST result=PASS", flush=True)


try:
    main()
except Exception:
    print("LEKIWI_COURSE_TEST result=FAIL", flush=True)
    traceback.print_exc()
finally:
    app.close()
