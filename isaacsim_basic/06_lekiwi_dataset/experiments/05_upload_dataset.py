"""설정을 저장하고 브라우저 터미널에서 python3 05_upload_dataset.py로 실행합니다."""
import shutil
import subprocess
import re

# 1. 03_convert_dataset.py에서 만들고 04_inspect_dataset.py로 검사한 로컬 이름입니다.
dataset_name = 'lekiwi_lesson6_01'

# 2. 본인의 Hugging Face 계정명/새 데이터셋 저장소 이름을 적습니다.
repo_id = 'account/lekiwi_lesson6_01'

# 3. 기본값 False는 공개 저장소입니다. 비공개 업로드가 필요하면 True로 바꾸세요.
private = False


def main():
    # lesson은 토큰을 저장하지 않고 서버의 LeRobot 컨테이너에 한 번만 전달합니다.
    if shutil.which('lesson') is None:
        raise SystemExit('이 파일은 브라우저 VS Code의 터미널에서 실행하세요.')
    if (not isinstance(dataset_name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', dataset_name)
            or not isinstance(repo_id, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}', repo_id)
            or type(private) is not bool):
        raise SystemExit('dataset_name·repo_id는 문자열, private은 True 또는 False로 설정하세요.')
    if repo_id == 'account/lekiwi_lesson6_01':
        raise SystemExit('repo_id의 account를 본인의 Hugging Face 계정명으로 바꾸고 저장하세요.')
    command = ['lesson', 'dataset', 'upload', '--name', dataset_name, '--repo-id', repo_id,
               '--private' if private else '--public']
    # 실행 중 쓰기 토큰을 숨김 입력합니다. 토큰은 이 파일이나 명령행에 기록되지 않습니다.
    result = subprocess.run(command)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('화면 대기를 종료했습니다. 서버 작업은 lesson dataset status로 확인하세요.')
