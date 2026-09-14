"""브라우저 터미널에서 python3 07_infer_act.py 실행. 준비 후 WebRTC 화면에서 R로 시작합니다."""
import shutil
import subprocess

# 06_train_act.py에서 지정한 학습 결과 이름입니다.
run_name = 'act_lesson6_01'
checkpoint = 'last'  # 마지막 저장 모델. 특정 단계 예: '001000'.
device = 'cuda'
seconds = 30  # R을 누를 때마다 실행할 최대 시뮬레이션 시간입니다.


def main():
    if shutil.which('lesson') is None:
        raise SystemExit('이 파일은 브라우저 VS Code의 터미널에서 실행하세요.')
    if (not isinstance(run_name, str) or not isinstance(checkpoint, str)
            or type(seconds) is not int or device not in ('cuda', 'cpu')):
        raise SystemExit('run_name·checkpoint는 문자열, seconds는 정수, device는 cuda 또는 cpu입니다.')
    # 준비 완료 뒤 WebRTC 화면에 연결하고 R로 시작합니다. SPACE 정지, F8 초기화.
    # 모델과 정규화 통계, 카메라 설정은 같은 학습 결과에서 읽습니다.
    command = ['lesson', 'infer', '--run-name', run_name, '--checkpoint', checkpoint,
               '--device', device, '--seconds', str(seconds)]
    raise SystemExit(subprocess.run(command).returncode)


if __name__ == '__main__':
    main()
