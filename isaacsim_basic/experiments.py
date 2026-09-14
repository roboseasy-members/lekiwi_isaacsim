"""1장 학생 파일 목록. 실제 장면 코드는 각 파일의 build_scene에 있습니다."""
from pathlib import Path
import runpy

SCRIPTS = {1: "01_no_gravity.py", 2: "02_gravity_only.py", 3: "03_gravity_collision.py",
           4: "04_mass_gravity.py", 5: "05_friction.py", 6: "06_restitution.py"}
DIRECTORY = Path(__file__).parent / "01_object_physics" / "experiments"


def load_experiment(number, directory=DIRECTORY):
    """GPU 검사에서 main/SimulationApp을 중복 실행하지 않고 장면 함수를 읽습니다."""
    if number not in SCRIPTS:
        raise ValueError("1장 실험 번호는 1~6입니다.")
    return runpy.run_path(str(directory / SCRIPTS[number]), run_name="student_test")["build_scene"]
