"""노트북 터미널에서 python3 07_infer_act.py 실행. 열린 Isaac Sim 창에서 R로 시작합니다."""
from pathlib import Path
import subprocess

launcher = Path(__file__).resolve().parents[3] / "lekiwi"

# 06_train_act.py에서 지정한 학습 결과 이름입니다.
run_name = 'act_lesson6_01'
checkpoint = 'last'  # 마지막 저장 모델. 특정 단계 예: '001000'.
device = 'cuda'
seconds = 30  # R을 누를 때마다 실행할 최대 시뮬레이션 시간입니다.


def main():
    if (not isinstance(run_name, str) or not isinstance(checkpoint, str)
            or type(seconds) is not int or device not in ('cuda', 'cpu')):
        raise SystemExit('run_name·checkpoint는 문자열, seconds는 정수, device는 cuda 또는 cpu입니다.')
    # Isaac Sim 창이 열리면 뷰포트를 클릭하고 R로 시작합니다. SPACE 정지, F8 초기화.
    # 모델과 정규화 통계, 카메라 설정은 같은 학습 결과에서 읽습니다.
    command = [str(launcher), 'act', 'infer', '--run-name', run_name, '--checkpoint', checkpoint,
               '--device', device, '--seconds', str(seconds)]
    raise SystemExit(subprocess.run(command).returncode)


if __name__ == '__main__':
    main()
