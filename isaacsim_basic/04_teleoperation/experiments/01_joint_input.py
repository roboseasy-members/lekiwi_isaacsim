"""보충 예제 · 키보드 입력이 단일 관절 목표가 되는 과정을 읽는 코드.

4장 본 수업은 README의 빨주노초 맵 teleop입니다. 이 파일은 회색 바닥과 한 관절 모형을 엽니다.
보충 실행: 저장소 최상위 폴더 터미널에서 ./lekiwi basic --chapter 4

읽는 순서
1. build_scene(): 2장과 같은 고정 받침·회전 팔·Drive를 만듭니다.
2. main()의 on_key(): J/L/K 입력을 받아 target이라는 목표 숫자를 바꿉니다.
3. 반복문: ArticulationAction으로 목표를 보내고 world.step()으로 실제 움직임을 계산합니다.

화면 조작: Viewport 클릭 → J=+30도, L=-30도, K=0도. 실제 USB 리더는 열지 않습니다.
바꿔 볼 값: on_key()의 np.deg2rad(30) 안 숫자를 15로 바꿔 작은 목표와 비교합니다.
키 값은 도로 읽기 쉽게 쓰고 deg2rad로 라디안으로 바꿉니다. 제어기 입력 단위는 rad입니다.
목표를 지정하는 것과 실제 관절이 그 위치에 도달하는 것은 다릅니다.
저장 후 같은 명령으로 재실행합니다. 자세한 코드 읽기: isaacsim_basic/CODE_GUIDE.md"""

def box(stage, path, position, size, color, *, collision=True, mass=None, angle=0):
    """위치(m)·크기(m)·색상으로 상자를 만듭니다. mass=None은 고정 물체, 숫자는 동적 강체입니다."""
    from pxr import Gf, UsdGeom, UsdPhysics
    cube = UsdGeom.Cube.Define(stage, path)  # 지정한 Stage 경로에 육면체를 만듭니다. 경로 이름으로 객체를 다시 찾습니다.
    cube.CreateSizeAttr(1.0)  # 육면체의 기본 한 변 길이를 지정합니다. Scale을 곱하면 최종 크기가 됩니다.
    cube.AddTranslateOp().Set(Gf.Vec3d(*position))  # 부모 좌표계 기준 위치 X/Y/Z를 m로 지정합니다.
    cube.AddRotateXYZOp().Set(Gf.Vec3f(0, angle, 0))  # X/Y/Z 순서의 회전각을 degree로 지정합니다.
    cube.AddScaleOp().Set(Gf.Vec3f(*size))  # 세 축의 배율을 지정합니다. 기본 크기 1인 Cube에서는 최종 변 길이가 됩니다.
    cube.CreateDisplayColorAttr([Gf.Vec3f(*color)])  # 표시 색상 RGB를 각각 0~1로 설정합니다. 물리 마찰에는 영향이 없습니다.
    if collision:
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())  # 형상을 접촉 계산에 포함합니다. 접촉하는 상대 물체에도 Collider가 필요합니다.
    if mass is not None:
        UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())  # 객체에 동적 강체 속성을 추가해 중력·외력으로 움직일 수 있게 합니다.
        UsdPhysics.MassAPI.Apply(cube.GetPrim()).CreateMassAttr(mass)  # 강체 질량을 kg로 지정합니다. 0은 중력 OFF가 아니라 자동 계산 의미입니다.
    return cube.GetPrim()


def build_scene(stage):
    """넘겨받은 Stage 안에 이 실험의 객체와 속성을 만듭니다. 앱 시작은 main()이 담당합니다."""
    from pxr import Gf, UsdGeom, UsdLux, UsdPhysics, UsdShade, PhysxSchema
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)  # 길이: m
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)  # 장면의 위쪽을 +Z로 지정합니다. 바닥은 XY 평면입니다.
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)  # 질량: kg
    world = UsdGeom.Xform.Define(stage, "/World")  # 위치·회전을 가질 부모 좌표계를 만듭니다. Xform 자체에는 보이는 형상이 없습니다.
    stage.SetDefaultPrim(world.GetPrim())  # 이 USD를 다른 장면에서 참조할 때 사용할 대표 객체를 지정합니다.
    scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")  # 중력 등 장면 전체 물리 설정을 보관할 PhysicsScene을 만듭니다.
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))  # 중력이 작용할 방향을 지정합니다. (0, 0, -1)은 아래쪽입니다.
    scene.CreateGravityMagnitudeAttr(9.81)  # 지구: m/s²
    # scene.CreateGravityMagnitudeAttr(1.62)  # 위 줄을 주석 처리 → 달 중력
    UsdLux.DomeLight.Define(stage, "/World/Light").CreateIntensityAttr(800)  # 장면 전체를 비추는 돔 조명을 만들고 밝기를 설정합니다.
    floor = UsdGeom.Cube.Define(stage, "/World/Ground")  # 지정한 Stage 경로에 육면체를 만듭니다. 경로 이름으로 객체를 다시 찾습니다.
    floor.CreateSizeAttr(1.0)  # 육면체의 기본 한 변 길이를 지정합니다. Scale을 곱하면 최종 크기가 됩니다.
    floor.AddTranslateOp().Set(Gf.Vec3d(0, 0, -.05))  # 부모 좌표계 기준 위치 X/Y/Z를 m로 지정합니다.
    floor.AddScaleOp().Set(Gf.Vec3f(6, 4, .1))  # 세 축의 배율을 지정합니다. 기본 크기 1인 Cube에서는 최종 변 길이가 됩니다.
    floor.CreateDisplayColorAttr([Gf.Vec3f(.18, .21, .25)])  # 표시 색상 RGB를 각각 0~1로 설정합니다. 물리 마찰에는 영향이 없습니다.
    UsdPhysics.CollisionAPI.Apply(floor.GetPrim())  # 고정 바닥: Collider만 적용
    # 크기 변경은 자식 Shape에만 적용하여 관절 기준 좌표계의 m 단위를 유지합니다.
    for name, z, size, color, mass in (
        ("Base", .15, (.18, .18, .3), (.15, .55, .8), 1.0),
        ("Arm", .45, (.06, .06, .3), (.95, .5, .1), .1),
    ):
        body = UsdGeom.Xform.Define(stage, "/World/Hinge/" + name)  # 위치·회전을 가질 부모 좌표계를 만듭니다. Xform 자체에는 보이는 형상이 없습니다.
        body.AddTranslateOp().Set(Gf.Vec3d(0, 0, z))  # 부모 좌표계 기준 위치 X/Y/Z를 m로 지정합니다.
        UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())  # 객체에 동적 강체 속성을 추가해 중력·외력으로 움직일 수 있게 합니다.
        UsdPhysics.MassAPI.Apply(body.GetPrim()).CreateMassAttr(mass)  # 강체 질량을 kg로 지정합니다. 0은 중력 OFF가 아니라 자동 계산 의미입니다.
        box(stage, str(body.GetPath()) + "/Shape", (0, 0, 0), size, color)
    fixed = UsdPhysics.FixedJoint.Define(stage, "/World/Hinge/FixedBase")  # 두 물체의 상대 위치·회전을 고정하는 관절을 만듭니다.
    fixed.CreateBody1Rel().SetTargets(["/World/Hinge/Base"])  # 관절의 두 번째 연결 강체입니다. FixedJoint의 반대 Body가 없으면 월드에 고정됩니다.
    fixed.CreateLocalPos0Attr(Gf.Vec3f(0, 0, .15))  # 첫 번째 Body 기준 관절 접점 위치입니다. Body가 없으면 월드 기준이며 단위는 m입니다.
    UsdPhysics.ArticulationRootAPI.Apply(fixed.GetPrim())  # 연결된 강체들을 하나의 로봇 관절 계통으로 해석하는 시작점을 지정합니다.
    joint = UsdPhysics.RevoluteJoint.Define(stage, "/World/Hinge/Shoulder")  # 한 축으로만 회전할 수 있는 관절을 만듭니다.
    joint.CreateBody0Rel().SetTargets(["/World/Hinge/Base"])  # 관절의 첫 번째 연결 강체 경로를 지정합니다.
    joint.CreateBody1Rel().SetTargets(["/World/Hinge/Arm"])  # 관절의 두 번째 연결 강체입니다. FixedJoint의 반대 Body가 없으면 월드에 고정됩니다.
    joint.CreateLocalPos0Attr(Gf.Vec3f(0, 0, .15))  # 첫 번째 Body 기준 관절 접점 위치입니다. Body가 없으면 월드 기준이며 단위는 m입니다.
    joint.CreateLocalPos1Attr(Gf.Vec3f(0, 0, -.15))  # 두 번째 Body 기준 관절 접점 위치입니다. 두 접점이 월드에서 만나도록 지정합니다.
    joint.CreateAxisAttr("Y")  # 관절이 회전할 로컬 축을 지정합니다. 여기서는 Y축입니다.
    joint.CreateLowerLimitAttr(-60)  # 회전 가능한 최소 각도입니다. USD 관절의 각도 단위는 degree입니다.
    joint.CreateUpperLimitAttr(60)  # 회전 가능한 최대 각도입니다. 이보다 큰 목표를 줘도 제한을 받습니다.
    joint.CreateCollisionEnabledAttr(False)  # 이 관절로 연결된 두 Body 사이의 자기 충돌을 켜거나 끕니다.
    drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")  # 회전 관절에 목표를 추종하는 angular Drive를 추가합니다.
    drive.CreateTypeAttr("force")  # Drive가 힘/토크로 작용하도록 force 모드를 선택합니다.
    drive.CreateStiffnessAttr(1000)  # 목표 위치 오차에 대한 복원 반응입니다. 낮추면 처짐·느린 응답이 생길 수 있습니다.
    # drive.CreateStiffnessAttr(20)  # 위 줄 대신: 약한 복원력
    drive.CreateDampingAttr(50)  # 움직임의 속도에 비례한 감쇠입니다. 흔들림과 응답 속도에 영향을 줍니다.
    drive.CreateMaxForceAttr(100)  # 구동 상한입니다. 이 회전 관절에서는 토크 상한(N·m)으로 해석합니다.
    drive.CreateTargetPositionAttr(0)  # 기본: 0도
    # drive.CreateTargetPositionAttr(30)  # 위 줄 대신: +30도
    # drive.CreateTargetPositionAttr(-30)  # 위 줄 대신: -30도
    # drive.CreateTargetPositionAttr(80)  # 위 줄 대신: 상한 60도 확인
    drive.CreateTargetVelocityAttr(0)  # Drive의 목표 각속도입니다. 0은 목표 위치에서 정지하도록 합니다.

def main():
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": False, "width": 1280, "height": 720})  # Isaac Sim 앱을 먼저 시작합니다. 이후에 omni/pxr API를 불러옵니다.
    try:
        import omni.usd
        import numpy as np
        from isaacsim.core.api import World
        from isaacsim.core.prims import SingleArticulation
        from isaacsim.core.utils.types import ArticulationAction
        from isaacsim.core.utils.viewports import set_camera_view
        context = omni.usd.get_context()
        context.new_stage()  # 비어 있는 새 Stage를 만듭니다. 이전 실행 결과는 별도 저장 폴더에 남습니다.
        build_scene(context.get_stage())  # 현재 열린 Stage 객체를 가져와 그 안에 물체를 추가합니다.
        # 직접 만든 2장 USD를 쓰려면 위 new_stage/build_scene 두 줄 대신 아래를 사용합니다.
        # if not context.open_stage("/data/isaacsim_basic/my_joint.usda"):
        #     raise RuntimeError("직접 만든 관절 USD를 열 수 없습니다. 저장 경로를 확인하세요.")
        world = World(physics_dt=1/60, rendering_dt=1/60, set_defaults=False,
                      physics_prim_path="/World/PhysicsScene")
        robot = world.scene.add(SingleArticulation(prim_path="/World/Hinge/FixedBase", name="hinge"))
        world.reset()  # 모형을 초기 상태로 돌리고 PhysX 관절 핸들을 초기화합니다.
        set_camera_view(eye=(1.05, -1.6, .9), target=(0, 0, .3))  # 기본 Perspective 관찰 시점과 바라볼 점을 정합니다.
        import carb.input
        import omni.appwindow
        keyboard = omni.appwindow.get_default_app_window().get_keyboard()
        inputs = carb.input.acquire_input_interface()
        target = 0.0
        def on_key(event, *_):
            nonlocal target
            if event.type != carb.input.KeyboardEventType.KEY_PRESS:
                return True
            # ArticulationAction의 각도는 rad입니다. 2장의 USD Drive는 degree입니다.
            if event.input == carb.input.KeyboardInput.J:
                target = np.deg2rad(30)
                # target = np.deg2rad(15)  # 위 줄 대신: 작은 각도
            elif event.input == carb.input.KeyboardInput.L:
                target = np.deg2rad(-30)
            elif event.input == carb.input.KeyboardInput.K:
                target = 0.0
            print(f"JOINT target_rad={target:+.3f}", flush=True)
            return True
        subscription = inputs.subscribe_to_keyboard_events(keyboard, on_key)
        print("STUDENT_SCRIPT ready | Viewport 클릭 → J:+30도 L:-30도 K:0도. 가상 모형만 움직입니다.", flush=True)
        try:
            while app.is_running():
                if world.is_playing():
                    robot.apply_action(ArticulationAction(joint_positions=np.array([target])))  # 목표 관절각을 제어기에 전달합니다. ArticulationAction은 rad 단위이며 순간이동이 아닙니다.
                    # 위 줄을 주석 처리하면 키 입력은 찍혀도 새 목표가 관절에 전달되지 않습니다.
                world.step(render=True)  # 설정된 물리 시간만큼 진행하고 화면도 갱신합니다.
        finally:
            inputs.unsubscribe_to_keyboard_events(keyboard, subscription)
    except Exception:
        import traceback
        traceback.print_exc()
        raise
    finally:
        app.close()  # Isaac Sim 앱과 렌더링 자원을 종료합니다.


if __name__ == "__main__":
    main()
