"""확인할 이름을 저장하고 노트북 터미널에서 python3 04_inspect_dataset.py로 실행합니다."""
from pathlib import Path
import subprocess

launcher = Path(__file__).resolve().parents[3] / "lekiwi"

# 변환할 때 사용한 dataset_name과 동일하게 적습니다.
dataset_name = 'lekiwi_lesson6_01'


def main():
    # 이 파일은 데이터를 수정하지 않고 같은 노트북에서 상태·영상 파일을 다시 읽어 검사합니다.
    if not isinstance(dataset_name, str):
        raise SystemExit('dataset_name은 따옴표로 감싼 데이터셋 이름으로 설정하세요.')
    # 성공하면 프레임·에피소드 수와 노트북의 학습 입력 경로가 출력됩니다.
    result = subprocess.run([str(launcher), 'dataset', 'inspect', '--name', dataset_name])
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('작업을 중단했습니다. 터미널의 오류와 ./lekiwi status를 확인하세요.')
