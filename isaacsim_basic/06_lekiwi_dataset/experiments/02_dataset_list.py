"""브라우저 VS Code 터미널에서 python3 02_dataset_list.py로 실행합니다."""
import shutil
import subprocess


def main():
    # lesson은 브라우저 편집기와 서버의 LeRobot 실행기를 연결하는 명령입니다.
    if shutil.which('lesson') is None:
        raise SystemExit('이 파일은 브라우저 VS Code의 터미널에서 실행하세요.')
    # 완료된 에피소드의 id·작업 설명·프레임 수와 기존 데이터셋 목록을 출력합니다.
    result = subprocess.run(['lesson', 'dataset', 'list'])
    # 목록 조회가 실패하면 이 스크립트도 실패로 종료합니다.
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('화면 대기를 종료했습니다. 서버 작업은 lesson dataset status로 확인하세요.')
