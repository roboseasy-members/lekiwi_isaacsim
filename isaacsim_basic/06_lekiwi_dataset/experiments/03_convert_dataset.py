"""6장 · 선택한 원본 시연을 LeRobot 학습용 데이터셋으로 변환하는 설정 코드.

실행: 저장소 최상위 폴더에서 python3 isaacsim_basic/06_lekiwi_dataset/experiments/03_convert_dataset.py
준비: 5장 SAVED 완료 → 02_dataset_list.py로 실제 id 확인.

읽는 순서
1. episode_ids: 변환할 원본 id 목록. 따옴표·쉼표를 사용하고 주석 #을 지웁니다.
2. dataset_name: 새 출력 폴더 이름. success_only: 성공 표시 기록만 포함할지 선택합니다.
3. main(): 설정 검사 → dataset export 명령 구성 → Docker 변환기 실행 → 종료 코드 전달.

변환기는 두 카메라 PNG를 MP4로, 상태·명령을 Parquet로 만들고 메타데이터·통계와 함께 검사합니다.
출력: data/datasets/<dataset_name>/ 전체. 기존 같은 이름은 덮어쓰지 않습니다.
F7 연습 기록으로 형식 확인을 할 때는 success_only=False를 사용합니다.
집기 학습은 같은 과제의 적합한 시연을 고릅니다. 형식 변환과 시연 품질 평가는 별개입니다.
다음 단계: 04_inspect_dataset.py에서 같은 dataset_name을 지정합니다.
문법 안내와 실행 흐름: isaacsim_basic/CODE_GUIDE.md"""
from pathlib import Path
import subprocess

# __file__은 이 파일의 위치입니다. 이 위치를 기준으로 저장소의 lekiwi 실행기를 찾습니다.
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
    """위 설정을 프로젝트 실행 명령에 전달하고 실제 작업의 성공·실패 종료 코드를 반환합니다."""
    if not isinstance(episode_ids, list) or not episode_ids:
        raise SystemExit('02_dataset_list.py로 목록을 확인하고 이 파일의 episode_ids를 채운 뒤 저장하세요.')
    if any(not isinstance(value, str) for value in episode_ids):
        raise SystemExit('episode_ids의 각 항목은 따옴표로 감싼 에피소드 id여야 합니다.')
    if not isinstance(dataset_name, str) or type(success_only) is not bool:
        raise SystemExit('dataset_name은 문자열, success_only는 True 또는 False로 설정하세요.')
    # 위에서 수정한 설정을 실행기에 전달합니다. 학생이 터미널 인자를 작성할 필요는 없습니다.
    # 리스트의 각 항목이 터미널 명령의 한 인자입니다. 아래 실행기가 실제 작업을 수행합니다.
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
