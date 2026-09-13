"""마우스로 환경을 만드는 빈 편집 화면. 물체·바닥·관절은 자동 생성하지 않습니다."""


def main():
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
