"""확인할 이름을 저장하고 브라우저 터미널에서 python3 04_inspect_dataset.py로 실행합니다."""
import shutil
import subprocess

# 변환할 때 사용한 dataset_name과 동일하게 적습니다.
dataset_name = 'lekiwi_lesson6_01'


def main():
    # 이 파일은 데이터를 수정하지 않고 서버에서 상태·영상 파일을 다시 읽어 검사합니다.
    if shutil.which('lesson') is None:
        raise SystemExit('이 파일은 브라우저 VS Code의 터미널에서 실행하세요.')
    if not isinstance(dataset_name, str):
        raise SystemExit('dataset_name은 따옴표로 감싼 데이터셋 이름으로 설정하세요.')
    # 성공하면 프레임·에피소드 수와 서버의 학습 입력 경로가 출력됩니다.
    result = subprocess.run(['lesson', 'dataset', 'inspect', '--name', dataset_name])
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('화면 대기를 종료했습니다. 서버 작업은 lesson dataset status로 확인하세요.')
