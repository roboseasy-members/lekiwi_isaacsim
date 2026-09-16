"""1~3장 · 마우스로 장면을 만들기 위한 빈 Isaac Sim 창.

목적: 학생이 World·조명·바닥·물체를 직접 추가할 시작 화면을 엽니다.
실행 위치: 같은 노트북의 저장소 최상위 폴더에 있는 터미널.
실행: ./lekiwi basic --script 01_object_physics/experiments/00_empty_stage.py

읽는 순서
1. main(): SimulationApp으로 앱을 연 뒤 omni 모듈을 가져옵니다.
2. context.new_stage(): 새 장면을 열고 기본 Physics 편집 메뉴를 준비합니다.
3. app.update(): 창을 닫을 때까지 화면과 입력 처리를 계속합니다.

이 파일은 큐브·바닥을 자동으로 만들지 않습니다. 실행 직후 빈 Stage가 정상입니다.
만든 장면은 File → Save As로 /data/isaacsim_basic/에 직접 저장합니다.
다른 실습용 코드와 비교하는 방법은 isaacsim_basic/CODE_GUIDE.md를 참고하세요."""


def main():
    """마우스 실습용 새 Stage와 편집 메뉴를 준비하고 창이 닫힐 때까지 화면을 유지합니다."""
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": False, "width": 1280, "height": 720})
    try:
        import omni.timeline
        import omni.usd
        from pxr import UsdGeom, UsdPhysics
        from isaacsim.core.utils.extensions import enable_extension
        from isaacsim.core.utils.viewports import set_camera_view

        context = omni.usd.get_context()
        context.new_stage()
        stage = context.get_stage()
        # 교재의 길이·질량·위쪽 방향만 정합니다. 장면은 학생이 메뉴로 만듭니다.
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
        enable_extension("omni.physx.bundle")
        set_camera_view(eye=(2, -2.5, 1.7), target=(0, 0, .35))
        omni.timeline.get_timeline_interface().stop()
        print("STUDENT_SCRIPT ready | 빈 편집 화면: 교재의 직접 만들기 순서로 진행하세요.", flush=True)
        print("종료 전 File > Save As로 새 USD에 저장하세요. Python 파일은 바뀌지 않습니다.", flush=True)
        while app.is_running():
            app.update()
    finally:
        app.close()


if __name__ == "__main__":
    main()
