"""설정을 저장하고 노트북 터미널에서 python3 03_convert_dataset.py로 실행합니다."""
from pathlib import Path
import subprocess

launcher = Path(__file__).resolve().parents[3] / "lekiwi"

# 1. 02_dataset_list.py의 출력에서 변환할 에피소드 id를 복사합니다.
# 여러 에피소드를 묶으려면 쉼표로 구분하여 한 줄씩 추가합니다.
episode_ids = [
    # 'lekiwi.SESSION/episode.EPISODE',  # 예시: 실제 목록의 id로 바꾸고 앞의 #을 지웁니다.
]

# 2. 새 데이터셋 이름입니다. 같은 이름의 기존 데이터는 덮어쓰지 않습니다.
dataset_name = 'lekiwi_lesson6_01'

# 3. False는 선택한 연습·성공 기록 모두, True는 F9로 성공 표시한 기록만 변환합니다.
success_only = False


def main():
    # 변환 자체는 같은 노트북의 LeRobot 컨테이너에서 실행합니다.
    # 아직 에피소드를 선택하지 않았으면 원본이나 출력 폴더를 건드리지 않습니다.
    if not isinstance(episode_ids, list) or not episode_ids:
        raise SystemExit('02_dataset_list.py로 목록을 확인하고 이 파일의 episode_ids를 채운 뒤 저장하세요.')
    if any(not isinstance(value, str) for value in episode_ids):
        raise SystemExit('episode_ids의 각 항목은 따옴표로 감싼 에피소드 id여야 합니다.')
    if not isinstance(dataset_name, str) or type(success_only) is not bool:
        raise SystemExit('dataset_name은 문자열, success_only는 True 또는 False로 설정하세요.')
    # 위에서 수정한 설정을 실행기에 전달합니다. 학생이 터미널 인자를 작성할 필요는 없습니다.
    command = [str(launcher), 'dataset', 'export', '--name', dataset_name]
    for episode_id in episode_ids:
        command += ['--episode', episode_id]
    if success_only:
        command.append('--success-only')
    # 원본 검사 → 두 카메라 영상 변환 → 상태·영상 재열기 검사 순서로 실행합니다.
    result = subprocess.run(command)
    # 터미널에 표시된 진행 상태와 완료 결과를 확인하고, 실패 코드는 그대로 전달합니다.
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('작업을 중단했습니다. 터미널의 오류와 ./lekiwi status를 확인하세요.')
