"""학생이 저장한 Python 파일을 실행하는 Docker 진입점. 전용 UI를 만들지 않습니다."""
import argparse
import os
from pathlib import Path
import runpy
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
CHAPTERS = {
    1: "01_object_physics/experiments/01_no_gravity.py",
    2: "02_robot_joints/experiments/01_joint_drive.py",
    3: "03_robot_cameras/experiments/01_camera.py",
    4: "04_teleoperation/experiments/01_joint_input.py",
    5: "05_data_recording/experiments/01_joint_episode.py",
    6: "06_lekiwi_dataset/experiments/01_lekiwi_recording.py",
}
EXPERIMENTS = {1: "01_no_gravity", 2: "02_gravity_only", 3: "03_gravity_collision",
               4: "04_mass_gravity", 5: "05_friction", 6: "06_restitution"}


def script_path(name, root=ROOT):
    path = (root / name).resolve()
    if (not path.is_relative_to(root.resolve()) or path.suffix != ".py"
            or path.parent.name != "experiments" or not path.is_file()):
        raise ValueError("isaacsim_basic/<장>/experiments/ 안의 Python 파일을 지정하세요.")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--chapter", type=int, choices=CHAPTERS)
    selection.add_argument("--script", help="isaacsim_basic 기준 상대 경로")
    selection.add_argument("--experiment", type=int, choices=EXPERIMENTS, help="1장 비교 예제")
    selection.add_argument("--lesson", choices=("blank", "drop", "mass", "friction", "bounce", "basket", "joints", "recording"))
    args = parser.parse_args(argv)
    aliases = {"joints": CHAPTERS[2], "recording": CHAPTERS[5], "drop": "01_object_physics/experiments/03_gravity_collision.py"}
    for lesson, number in (("mass", 4), ("friction", 5), ("bounce", 6)):
        aliases[lesson] = f"01_object_physics/experiments/{EXPERIMENTS[number]}.py"
    if args.lesson in {"blank", "basket"}:
        return legacy_scene(args.lesson)
    name = (args.script or aliases.get(args.lesson) or
            (f"01_object_physics/experiments/{EXPERIMENTS[args.experiment]}.py" if args.experiment else None)
            or CHAPTERS[args.chapter or 1])
    path = script_path(name)
    # 문법 오류면 Isaac Sim을 띄우기 전에 파일·행 번호를 알려줍니다.
    compile(path.read_text(), str(path), "exec")
    parent = Path("/data/isaacsim_basic")
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=path.stem + ".", dir=parent))
    os.chdir(output)
    print(f"STUDENT_SCRIPT source={path} working_directory={output}", flush=True)
    sys.argv = [str(path)]
    sys.path.insert(0, str(ROOT.parent / "isaac_sim"))
    from app_runtime import install_student_streaming
    install_student_streaming()
    runpy.run_path(str(path), run_name="__main__")


def legacy_scene(lesson):
    """기존 빈 장면·바구니 보충 실습. 조작은 표준 Play/Stop만 사용합니다."""
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": False})
    try:
        import omni.usd
        from scenes import new_exercise
        from isaacsim.core.utils.extensions import enable_extension
        from isaacsim.core.utils.viewports import set_camera_view
        path = new_exercise("/data/isaacsim_basic", lesson)
        if not omni.usd.get_context().open_stage(str(path)):
            raise RuntimeError(path)
        enable_extension("omni.physx.bundle")
        set_camera_view(eye=(2, -2.5, 1.7), target=(0, 0, .35))
        while app.is_running():
            app.update()
    finally:
        app.close()


if __name__ == "__main__":
    main()
