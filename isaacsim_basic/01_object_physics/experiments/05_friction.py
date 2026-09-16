"""1장 · 같은 경사면에서 서로 다른 마찰계수를 비교하는 코드.

목적: 물체의 색상과 물리 재질을 구분하고 미끄러짐의 차이를 관찰합니다.
실행: 저장소 최상위 폴더 터미널에서 ./lekiwi basic --experiment 5

읽는 순서
1. build_scene(): Low/High 두 줄의 설정으로 경사면과 큐브를 한 쌍씩 만듭니다.
2. material(): 정지·동적 마찰계수를 정합니다. 기본 Low=0.05, High=0.8입니다.
3. bind(): 같은 재질을 해당 경사면과 큐브 양쪽에 연결합니다.
4. main(): 새 장면을 열고 Play 입력을 기다립니다.

기본 결과: 15도 경사면에서 마찰이 낮은 쪽이 더 잘 미끄러지는지 확인합니다.
바꿔 볼 값: build_scene() 마지막 주석 3줄을 해제해 Low의 두 마찰계수를 0.8로 맞춥니다.
색상을 바꿔도 마찰계수는 바뀌지 않습니다.
경사각 15도는 경사면·큐브 방향·초기 위치 계산에 함께 사용하므로 한 곳만 바꾸지 않습니다.
초기 위치 계산은 큐브가 경사면에 파고들지 않게 놓기 위한 것이며, 첫 비교에서는 그대로 둡니다.
저장 후 같은 명령으로 재실행합니다. 자세한 코드 읽기: isaacsim_basic/CODE_GUIDE.md"""
import math

def box(stage, path, position, size, color, *, collision=True, mass=None, angle=0):
    """위치(m)·크기(m)·색상으로 상자를 만듭니다. mass=None은 고정 물체, 숫자는 동적 강체입니다."""
    from pxr import Gf, UsdGeom, UsdPhysics, UsdShade
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


def material(stage, name, friction=0.5, restitution=0):
    """마찰과 반발계수가 들어 있는 물리 재질을 만듭니다. 색상 재질과 역할이 다릅니다."""
    from pxr import Gf, UsdGeom, UsdPhysics, UsdShade
    mat = UsdShade.Material.Define(stage, "/World/Materials/" + name)  # 물리 재질을 담을 USD Material 객체를 만듭니다.
    physics = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())  # 재질에 마찰·반발계수를 지정할 물리 속성을 추가합니다.
    physics.CreateStaticFrictionAttr(friction)  # 미끄러지기 시작하는 조건에 영향을 주는 정지 마찰계수입니다.
    physics.CreateDynamicFrictionAttr(friction)  # 이미 미끄러지는 동안의 저항을 정하는 동적 마찰계수입니다.
    physics.CreateRestitutionAttr(restitution)  # 접촉 후 튀는 정도를 정하는 반발계수입니다. 범위는 0~1입니다.
    # 접촉 양쪽에 같은 값을 적용하여 재질 혼합 규칙이 비교를 흐리지 않게 합니다.
    return mat


def bind(prim, mat):
    """만든 물리 재질을 접촉할 물체에 연결합니다. 재질 생성만으로는 물체에 적용되지 않습니다."""
    from pxr import Gf, UsdGeom, UsdPhysics, UsdShade
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat, materialPurpose="physics")  # 재질을 객체에 연결합니다. physics 용도이므로 화면 색상이 아닌 접촉에 적용됩니다.


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
    for name, y, mu, color in (("Low", -.4, .05, (.95, .5, .1)),
                                ("High", .4, .8, (.1, .65, .95))):
        mat = material(stage, name, friction=mu)
        ramp = box(stage, f"/World/Ramp{name}", (0, y, .4),
                   (1.6, .5, .06), (.4, .45, .5), angle=15)
        # 경사면의 접선·법선으로 위치를 구해 처음부터 파고들거나 떨어져 충돌하지 않게 합니다.
        theta = math.radians(15)
        along, normal = -.5, .081
        x = along * math.cos(theta) + normal * math.sin(theta)
        z = .4 - along * math.sin(theta) + normal * math.cos(theta)
        cube = box(stage, f"/World/Cube{name}", (x, y, z), (.1,)*3,
                   color, mass=.1, angle=15)
        bind(ramp, mat)
        bind(cube, mat)

    # 다음 단계: 낮은 마찰도 .8로 바꿔 두 경사면을 비교합니다.
    # low = UsdPhysics.MaterialAPI(stage.GetPrimAtPath("/World/Materials/Low"))
    # low.CreateStaticFrictionAttr(.8)
    # low.CreateDynamicFrictionAttr(.8)


def main():
    # Isaac Sim 모듈은 SimulationApp 생성 뒤에 불러옵니다.
    """앱과 새 장면을 준비하고 화면을 유지합니다. 실험 설정은 build_scene()에서 읽습니다."""
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": False, "width": 1280, "height": 720})  # Isaac Sim 앱을 먼저 시작합니다. 이후에 omni/pxr API를 불러옵니다.
    try:
        import omni.usd
        import omni.timeline
        from isaacsim.core.utils.extensions import enable_extension
        from isaacsim.core.utils.viewports import set_camera_view
        from pathlib import Path
        import tempfile
        context = omni.usd.get_context()
        context.new_stage()  # 비어 있는 새 Stage를 만듭니다. 이전 실행 결과는 별도 저장 폴더에 남습니다.
        stage = context.get_stage()  # 현재 열린 Stage 객체를 가져와 그 안에 물체를 추가합니다.
        build_scene(stage)  # 위에서 정의한 객체·바닥·물리 속성 생성 함수를 실행합니다.
        output = Path(tempfile.mkdtemp(prefix="exercise.", dir=Path.cwd()))
        stage.GetRootLayer().Export(str(output / "scene.usda"))  # 생성된 장면을 새 USD 파일로 내보냅니다. Python 소스를 수정하는 작업은 아닙니다.
        # 첫 Stage를 만든 다음 표준 Physics 편집 메뉴를 활성화합니다.
        enable_extension("omni.physx.bundle")  # 표준 Physics 편집 메뉴를 활성화합니다. 교육 전용 탭은 만들지 않습니다.
        set_camera_view(eye=(2.0, -2.5, 1.7), target=(0, 0, .35))  # 기본 Perspective 관찰 시점과 바라볼 점을 정합니다.
        omni.timeline.get_timeline_interface().stop()  # 물리를 실행 전 상태로 둡니다. 학생이 표준 Play로 실험을 시작합니다.
        print(f"STUDENT_SCRIPT ready file={Path(__file__).name} output={output}", flush=True)
        print("Play: 실행 / Stop: 처음으로. 코드 수정 후 창을 닫고 재실행하세요.", flush=True)
        while app.is_running():
            app.update()  # 창·입력·렌더링을 한 번 갱신합니다. 반복하지 않으면 화면이 반응하지 않습니다.
    except Exception:
        import traceback
        traceback.print_exc()
        raise
    finally:
        app.close()  # Isaac Sim 앱과 렌더링 자원을 종료합니다.


if __name__ == "__main__":
    main()
