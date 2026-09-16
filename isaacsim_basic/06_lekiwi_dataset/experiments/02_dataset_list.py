"""6장 · 변환할 원본 에피소드와 이미 변환한 데이터셋 목록을 보는 코드.

실행: 저장소 최상위 폴더에서 python3 isaacsim_basic/06_lekiwi_dataset/experiments/02_dataset_list.py
이 파일은 노트북 Python으로 실행하며, 실제 목록 조회는 실행기가 Docker 환경에서 처리합니다.

읽는 순서: launcher로 이 저장소의 lekiwi 위치 찾기 → main()에서 dataset list 호출 → 종료 코드 전달.
수정할 값은 없습니다. 파일 조회만 하며 데이터 생성·삭제·업로드는 하지 않습니다.
출력: episodes에서 원본 id·과제·프레임 수·성공 여부, datasets에서 변환본을 확인합니다.
다음 단계: 본인의 실제 episode id를 03_convert_dataset.py의 episode_ids에 복사합니다.
문법 안내와 실행 흐름: isaacsim_basic/CODE_GUIDE.md"""
from pathlib import Path
import subprocess

# __file__은 이 파일의 위치입니다. 이 위치를 기준으로 저장소의 lekiwi 실행기를 찾습니다.
launcher = Path(__file__).resolve().parents[3] / "lekiwi"


def main():
    # 같은 노트북의 실행기를 통해 LeRobot 컨테이너에서 원본 목록을 읽습니다.
    # 완료된 에피소드의 id·작업 설명·프레임 수와 기존 데이터셋 목록을 출력합니다.
    """위 설정을 프로젝트 실행 명령에 전달하고 실제 작업의 성공·실패 종료 코드를 반환합니다."""
    result = subprocess.run([str(launcher), 'dataset', 'list'])
    # 목록 조회가 실패하면 이 스크립트도 실패로 종료합니다.
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('작업을 중단했습니다. 터미널의 오류와 ./lekiwi status를 확인하세요.')
