"""3장 · 카메라를 생성하고 위치·시선·렌즈를 비교하는 코드.

목적: 물체를 보는 카메라의 자세와 화각을 코드로 지정합니다.
실행: 저장소 최상위 폴더 터미널에서 ./lekiwi basic --chapter 3

읽는 순서
1. build_scene(): 바닥과 관찰용 큐브를 만들고 /World/Camera를 생성합니다.
2. SetLookAt(eye, target, up): 카메라 위치·바라볼 점·위쪽 방향으로 시선을 정합니다.
3. GetInverse(): 보기 변환을 장면에 놓을 카메라 자세로 바꿉니다.
4. FocalLength/Aperture/ClippingRange: 렌즈·영상 가로 폭·보이는 거리 범위를 정합니다.

실행 후 Viewport의 카메라 목록에서 /World/Camera를 선택해야 이 카메라의 화면을 봅니다.
기본값: FocalLength=24. 바꿔 볼 값: 해당 줄 대신 48 줄을 켜고 같은 카메라 시점을 비교합니다.
관찰용 큐브는 정적이므로 Play를 눌러도 떨어지지 않습니다. 렌즈 비교에는 물리 실행이 필요 없습니다.
이 파일은 카메라 속성 예제이며 영상 데이터셋 저장은 5장의 기록기로 진행합니다.
저장 후 같은 명령으로 재실행합니다. 자세한 코드 읽기: isaacsim_basic/CODE_GUIDE.md"""

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
    cube = UsdGeom.Cube.Define(stage, "/World/PracticeCube")  # 지정한 Stage 경로에 육면체를 만듭니다. 경로 이름으로 객체를 다시 찾습니다.
    cube.CreateSizeAttr(.1)  # 한 변 10 cm
    cube.AddTranslateOp().Set(Gf.Vec3d(0, 0, .7))  # 부모 좌표계 기준 위치 X/Y/Z를 m로 지정합니다.
    cube.CreateDisplayColorAttr([Gf.Vec3f(.2, .6, .95)])  # 기본: 파랑
    # cube.CreateDisplayColorAttr([Gf.Vec3f(.95, .25, .1)])  # 위 줄 대신: 주황
    # USD 카메라는 -Z 방향을 보고 +Y가 위입니다. SetLookAt의 역행렬로 자세를 만듭니다.
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")  # 카메라 객체를 만듭니다. Viewport의 카메라 목록에서 선택할 수 있습니다.
    pose = Gf.Matrix4d().SetLookAt(Gf.Vec3d(1.2, -1.6, 1.1),  # eye에서 target을 보는 카메라 자세를 계산합니다. 역행렬을 카메라의 변환으로 사용합니다.
                                 Gf.Vec3d(0, 0, .35), Gf.Vec3d(0, 0, 1)).GetInverse()
    camera.AddTransformOp().Set(pose)  # 계산한 위치·회전을 하나의 4×4 변환 행렬로 적용합니다.
    camera.CreateFocalLengthAttr(24)  # 기본 렌즈
    # camera.CreateFocalLengthAttr(48)  # 위 줄 대신: 망원, 더 좁은 화각
    camera.CreateHorizontalApertureAttr(20.955)  # 렌즈의 수평 필름 폭입니다. 초점거리와 같은 USD 렌즈 단위를 사용합니다.
    camera.CreateClippingRangeAttr(Gf.Vec2f(.01, 100))  # 단위 m


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
