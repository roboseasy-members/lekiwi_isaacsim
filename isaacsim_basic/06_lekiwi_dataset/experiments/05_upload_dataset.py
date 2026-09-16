"""6장 선택 실습 · 검사한 데이터셋을 Hugging Face에 공유하는 설정 코드.

실행: 저장소 최상위 폴더에서 python3 isaacsim_basic/06_lekiwi_dataset/experiments/05_upload_dataset.py
준비: 04_inspect_dataset.py 검사 완료. 로컬 ACT 학습만 할 때는 이 단계를 생략합니다.

읽는 순서
1. dataset_name은 내 노트북의 변환본 이름, repo_id는 내 Hugging Face 계정/저장소 이름입니다.
2. private=False는 공개, True는 비공개입니다. 본인의 이름과 공개 범위를 정하고 저장합니다.
3. main(): 이름·설정 검사 → dataset upload 명령 → 터미널에서 쓰기 토큰 숨김 입력 → 업로드.

변환 데이터와 카드·형식 버전 태그를 올립니다. 완료 출력의 url에서 결과를 확인합니다.
토큰은 이 코드나 명령줄에 적지 않고 실행 중 요청되는 입력창에 입력합니다.
문법 안내와 실행 흐름: isaacsim_basic/CODE_GUIDE.md"""
from pathlib import Path
import re
import subprocess

# __file__은 이 파일의 위치입니다. 이 위치를 기준으로 저장소의 lekiwi 실행기를 찾습니다.
launcher = Path(__file__).resolve().parents[3] / "lekiwi"

# 1. 03_convert_dataset.py에서 만들고 04_inspect_dataset.py로 검사한 로컬 이름입니다.
dataset_name = 'lekiwi_lesson6_01'

# 2. 본인의 Hugging Face 계정명/새 데이터셋 저장소 이름을 적습니다.
repo_id = 'account/lekiwi_lesson6_01'

# 3. 기본값 False는 공개 저장소입니다. 비공개 업로드가 필요하면 True로 바꾸세요.
private = False


def main():
    # 실행기가 같은 노트북의 LeRobot 컨테이너에서 토큰을 숨김 입력받습니다.
    """위 설정을 프로젝트 실행 명령에 전달하고 실제 작업의 성공·실패 종료 코드를 반환합니다."""
    if (not isinstance(dataset_name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', dataset_name)
            or not isinstance(repo_id, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}', repo_id)
            or type(private) is not bool):
        raise SystemExit('dataset_name·repo_id는 문자열, private은 True 또는 False로 설정하세요.')
    if repo_id == 'account/lekiwi_lesson6_01':
        raise SystemExit('repo_id의 account를 본인의 Hugging Face 계정명으로 바꾸고 저장하세요.')
    # 리스트의 각 항목이 터미널 명령의 한 인자입니다. 아래 실행기가 실제 작업을 수행합니다.
    command = [str(launcher), 'dataset', 'upload', '--name', dataset_name, '--repo-id', repo_id,
               '--private' if private else '--public']
    # 실행 중 쓰기 토큰을 숨김 입력합니다. 토큰은 이 파일이나 명령행에 기록되지 않습니다.
    result = subprocess.run(command)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('작업을 중단했습니다. 터미널의 오류와 ./lekiwi status를 확인하세요.')
