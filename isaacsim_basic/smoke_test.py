"""Exercise real PhysX contacts, material comparisons and an open basket."""
from isaacsim import SimulationApp

app = SimulationApp({"headless": True})
try:
    import tempfile
    import omni.usd
    import math
    from pxr import Usd, UsdGeom, UsdPhysics, UsdLux
    from isaacsim.core.api import World
    from scenes import new_exercise
    from experiments import load_experiment, DIRECTORY, SCRIPTS
    from pathlib import Path
    import runpy

    def position(stage, name):
        return UsdGeom.Xformable(stage.GetPrimAtPath("/World/" + name)).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()).ExtractTranslation()

    with tempfile.TemporaryDirectory(prefix="isaacsim-basic-test-") as directory:
        for number in (1, 2, 3):
            omni.usd.get_context().new_stage()
            load_experiment(number)(omni.usd.get_context().get_stage())
            world = World(physics_dt=1/120, rendering_dt=1/60, stage_units_in_meters=1.0,
                          physics_prim_path="/World/PhysicsScene")
            stage = omni.usd.get_context().get_stage()
            world.reset()
            for _ in range(120):
                world.step(render=False)
            z = position(stage, "PracticeCube")[2]
            if number == 1:
                assert abs(z - .7) < .001, z
            elif number == 2:
                assert z < -1, z
            else:
                assert abs(z - .05) < .005, z
            world.stop()
            # 같은 장면을 다시 Play했을 때 시작 위치부터 재현돼야 한다.
            world.reset()
            assert abs(position(stage, "PracticeCube")[2] - .7) < .005
            print(f"ISAACSIM_BASIC_TEST experiment={number} z_after_1s={z:.4f} reset=PASS", flush=True)
            world.stop()
            World.clear_instance()
        for lesson in ("drop", "mass", "friction", "bounce", "basket", "joints"):
            number = {"mass": 4, "friction": 5, "bounce": 6}.get(lesson)
            if number:
                omni.usd.get_context().new_stage()
                load_experiment(number)(omni.usd.get_context().get_stage())
            else:
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
                    assert abs(position(stage, "CubeLight")[2] - position(stage, "CubeHeavy")[2]) < .002
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
                assert stage.GetPrimAtPath("/World/Light").IsA(UsdLux.DomeLight)
                assert all(abs(position(stage, name)[2] - .05) < .005 for name in ("CubeLight", "CubeHeavy"))
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
        # 학생이 실제로 변경하는 값이 낙하·접촉 결과까지 바꾸는지 확인한다.
        for lesson, number, modified in (
            ("mass", 4, {"gravity_m_s2": 1.62, "light_mass_kg": .2, "heavy_mass_kg": 2.0}),
            ("mass", 4, {"gravity_m_s2": 0}),
            ("friction", 5, {"low_friction": .8}),
            ("bounce", 6, {"high_restitution": .3}),
        ):
            settings = modified
            path = new_exercise(directory, lesson, settings)
            assert omni.usd.get_context().open_stage(str(path))
            # 자동 검사 기본값이 학생이 설정한 중력 1.62/0을 덮어쓰지 않게 한다.
            world = World(physics_dt=1/120, rendering_dt=1/60, stage_units_in_meters=1.0,
                          physics_prim_path="/World/PhysicsScene", set_defaults=False)
            stage = omni.usd.get_context().get_stage()
            world.reset()
            initial = position(stage, "CubeLow") if lesson == "friction" else None
            contacted, rebound = False, 0.0
            for step in range(30 if lesson == "mass" else 240):
                world.step(render=False)
                if lesson == "bounce":
                    z = position(stage, "BallHigh")[2]
                    contacted = contacted or z < .17
                    if contacted:
                        rebound = max(rebound, z)
            if lesson == "mass":
                z = position(stage, "CubeLight")[2]
                print(f"ISAACSIM_BASIC_TEST edited_mass settings={settings} z={z:.6f} "
                      f"scene_g={UsdPhysics.Scene(stage.GetPrimAtPath('/World/PhysicsScene')).GetGravityMagnitudeAttr().Get()}", flush=True)
                assert abs(z - position(stage, "CubeHeavy")[2]) < .002
                assert abs(UsdPhysics.Scene(stage.GetPrimAtPath("/World/PhysicsScene")).GetGravityMagnitudeAttr().Get()
                           - settings["gravity_m_s2"]) < .0001
                # World.reset도 물리 스텝을 수행하므로 적분·초기화 여유를 둔다.
                assert abs(z - (1 - .5 * settings["gravity_m_s2"] * .25**2)) < .012, z
                result = f"g={settings['gravity_m_s2']} z_after_30_steps={z:.4f}"
            elif lesson == "friction":
                distance = (position(stage, "CubeLow") - initial).GetLength()
                assert distance < .04, distance
                result = f"low_friction=0.8 distance={distance:.4f}"
            else:
                assert contacted and .18 < rebound < .35, rebound
                result = f"high_restitution=0.3 rebound_z={rebound:.4f}"
            print(f"ISAACSIM_BASIC_TEST edited_experiment={number} {result} PASS", flush=True)
            world.stop()
            World.clear_instance()
    # 1장 실제 주석을 바꿨을 때 중력+접촉으로 정지하는지 검사합니다.
    source = (DIRECTORY / SCRIPTS[1]).read_text()
    source = source.replace('    body.CreateDisableGravityAttr(True)', '    # body.CreateDisableGravityAttr(True)')
    source = source.replace('    # body.CreateDisableGravityAttr(False)', '    body.CreateDisableGravityAttr(False)')
    source = source.replace('    # UsdPhysics.CollisionAPI.Apply(cube.GetPrim())', '    UsdPhysics.CollisionAPI.Apply(cube.GetPrim())')
    values = {'__name__': 'test_student'}
    exec(compile(source, 'student-edited.py', 'exec'), values)
    omni.usd.get_context().new_stage()
    stage = omni.usd.get_context().get_stage()
    values['build_scene'](stage)
    world = World(physics_dt=1/120, rendering_dt=1/60, set_defaults=False, physics_prim_path='/World/PhysicsScene')
    world.reset()
    for _ in range(120): world.step(render=False)
    assert abs(position(stage, 'PracticeCube')[2] - .05) < .005
    world.stop(); World.clear_instance()
    for chapter, filename in [('02_robot_joints', '01_joint_drive.py'), ('03_robot_cameras', '01_camera.py'),
                              ('04_teleoperation', '01_joint_input.py'), ('05_data_recording', '01_joint_episode.py')]:
        values = runpy.run_path(str(DIRECTORY.parents[1] / chapter / 'experiments' / filename))
        omni.usd.get_context().new_stage()
        stage = omni.usd.get_context().get_stage()
        values['build_scene'](stage)
        if chapter.startswith('03'):
            camera = UsdGeom.Camera(stage.GetPrimAtPath('/World/Camera'))
            assert camera.GetFocalLengthAttr().Get() == 24
            assert camera.GetClippingRangeAttr().Get()[0] > 0
        else:
            from isaacsim.core.prims import SingleArticulation
            from isaacsim.core.utils.types import ArticulationAction
            import numpy as np
            world = World(physics_dt=1/60, rendering_dt=1/60, set_defaults=False, physics_prim_path='/World/PhysicsScene')
            robot = world.scene.add(SingleArticulation(prim_path='/World/Hinge/FixedBase', name='student_hinge'))
            world.reset()
            if chapter.startswith('05'):
                with tempfile.TemporaryDirectory() as output:
                    saved = values['record'](world, robot, app, Path(output))
                    values['replay'](world, robot, app, saved)
                    import json
                    rows = json.loads(saved.read_text())['Isaac Sim Data']
                    assert len(rows) == 180
                    assert all(rows[i]['data']['next_observation'] == rows[i+1]['data']['observation'] for i in range(179))
            else:
                robot.apply_action(ArticulationAction(joint_positions=np.array([np.pi/6])))
                for _ in range(120): world.step(render=False)
                assert abs(float(robot.get_joint_positions()[0]) - np.pi/6) < .02
            world.stop(); World.clear_instance()
        print(f'STUDENT_API_TEST chapter={chapter} PASS', flush=True)
    print("ISAACSIM_BASIC_TEST result=PASS", flush=True)
except Exception:
    import traceback
    traceback.print_exc()
    raise
finally:
    app.close()
