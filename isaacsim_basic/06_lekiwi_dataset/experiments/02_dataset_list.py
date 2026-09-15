"""노트북 터미널에서 python3 02_dataset_list.py로 실행합니다."""
from pathlib import Path
import subprocess

launcher = Path(__file__).resolve().parents[3] / "lekiwi"


def main():
    # 같은 노트북의 실행기를 통해 LeRobot 컨테이너에서 원본 목록을 읽습니다.
    # 완료된 에피소드의 id·작업 설명·프레임 수와 기존 데이터셋 목록을 출력합니다.
    result = subprocess.run([str(launcher), 'dataset', 'list'])
    # 목록 조회가 실패하면 이 스크립트도 실패로 종료합니다.
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('작업을 중단했습니다. 터미널의 오류와 ./lekiwi status를 확인하세요.')
