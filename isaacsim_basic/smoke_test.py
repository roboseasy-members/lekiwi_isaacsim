"""Exercise real PhysX contacts, material comparisons and an open basket."""
from isaacsim import SimulationApp

app = SimulationApp({"headless": True})
try:
    import tempfile
    import omni.usd
    import math
    from pxr import Usd, UsdGeom, UsdPhysics
    from isaacsim.core.api import World
    from scenes import new_exercise

    def position(stage, name):
        return UsdGeom.Xformable(stage.GetPrimAtPath("/World/" + name)).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()).ExtractTranslation()

    with tempfile.TemporaryDirectory(prefix="isaacsim-basic-test-") as directory:
        for lesson in ("drop", "mass", "friction", "bounce", "basket", "joints"):
            path = new_exercise(directory, lesson)
            assert omni.usd.get_context().open_stage(str(path))
            world = World(physics_dt=1/120, rendering_dt=1/60, stage_units_in_meters=1.0,
                          physics_prim_path="/World/PhysicsScene")
            stage = omni.usd.get_context().get_stage()
            world.reset()
            initial_high = position(stage, "CubeHigh") if lesson == "friction" else None
            rebound = {"Low": 0.0, "High": 0.0}
            contacted = {"Low": False, "High": False}
            for step in range(240):
                world.step(render=False)
                if lesson == "mass" and step == 20:
                    assert abs(position(stage, "Light")[2] - position(stage, "Heavy")[2]) < .002
                if lesson == "bounce":
                    for name in rebound:
                        z = position(stage, "Ball" + name)[2]
                        if z < .17:
                            contacted[name] = True
                        if contacted[name]:
                            rebound[name] = max(rebound[name], z)
            if lesson == "drop":
                assert abs(position(stage, "VisualOnly")[2] - .7) < .001
                assert position(stage, "RigidOnly")[2] < -1
                assert abs(position(stage, "RigidCollider")[2] - .05) < .005
            elif lesson == "mass":
                assert all(abs(position(stage, name)[2] - .05) < .005 for name in ("Light", "Heavy"))
            elif lesson == "friction":
                assert (position(stage, "CubeHigh") - initial_high).GetLength() < .04
                assert position(stage, "CubeLow")[0] > initial_high[0] + .25
            elif lesson == "bounce":
                assert all(contacted.values()), contacted
                assert rebound["High"] > rebound["Low"] + .2, rebound
            elif lesson == "basket":
                assert abs(position(stage, "Cube")[2] - .04) < .005
                assert abs(position(stage, "Cube")[0]) < .02
            elif lesson == "joints":
                drive = UsdPhysics.DriveAPI(stage.GetPrimAtPath("/World/Hinge/Shoulder"), "angular")
                # Check both directions and a command beyond the joint limit.
                for target, expected in ((30, 30), (-30, -30), (80, 60)):
                    drive.GetTargetPositionAttr().Set(target)
                    for _ in range(240):
                        world.step(render=False)
                    actual = position(stage, "Hinge/Arm")
                    angle = math.degrees(math.atan2(actual[0], actual[2] - .3))
                    assert abs(angle - expected) < 1, (target, angle)
                    assert (position(stage, "Hinge/Base") - (0, 0, .15)).GetLength() < .001
                    print(f"ISAACSIM_BASIC_TEST joint_target={target} actual_deg={angle:.3f}", flush=True)
            print(f"ISAACSIM_BASIC_TEST lesson={lesson} PASS", flush=True)
            world.stop()
            World.clear_instance()
    print("ISAACSIM_BASIC_TEST result=PASS", flush=True)
finally:
    app.close()
