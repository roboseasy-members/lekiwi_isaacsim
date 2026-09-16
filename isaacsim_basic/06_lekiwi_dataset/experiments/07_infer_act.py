"""6장 · 저장한 ACT 모델을 불러와 빨주노초 맵의 가상 LeKiwi를 조작하는 설정 코드.

실행: 저장소 최상위 폴더에서 python3 isaacsim_basic/06_lekiwi_dataset/experiments/07_infer_act.py
준비: 06_train_act.py의 모델 저장 완료, 기존 학습·teleop 종료.

읽는 순서
1. run_name/checkpoint: 사용할 학습 결과와 저장 시점을 고릅니다.
2. device/seconds: 모델 계산 장치와 실행할 최대 시뮬레이션 시간을 정합니다.
3. main(): act infer 호출 → 저장 모델·정규화·카메라 설정 로드 → 같은 코스의 가상 로봇 실행.

모델은 두 카메라와 상태를 읽고 행동을 예측합니다. 이 단계에서는 모델을 추가 학습하지 않습니다.
화면과 모델 준비 후 Viewport 클릭 → R 시작 / Space 정지 / F8 초기화 후 R 재시작.
실제 리더·follower에는 연결하지 않습니다. CPU 모델 계산을 골라도 Isaac Sim에는 GPU가 필요합니다.
결과 확인: RUNNING·FINISHED·STOPPED 상태와 실제 화면. 로그 위치는 시작 출력에서 확인합니다.
1회 학습 모델은 실행 경로 확인용입니다. 추론 조작은 최종 리허설에서 확인합니다.
문법 안내와 실행 흐름: isaacsim_basic/CODE_GUIDE.md"""
from pathlib import Path
import subprocess

# __file__은 이 파일의 위치입니다. 이 위치를 기준으로 저장소의 lekiwi 실행기를 찾습니다.
launcher = Path(__file__).resolve().parents[3] / "lekiwi"

# 1. 06_train_act.py의 run_name과 같게 적습니다. dataset_name과 구분합니다.
# 호스트 data/outputs/<run_name>/의 모델·정규화·카메라 설정을 함께 읽습니다.
run_name = 'act_lesson6_check_01'
# 2. 마지막 모델 또는 실제 존재하는 단계 폴더 이름을 지정합니다.
checkpoint = 'last'  # 마지막 저장 모델. 특정 단계 예: '001000'.
# 3. 모델 계산 장치. 'cpu'여도 Isaac Sim 화면에는 GPU 환경이 필요합니다.
device = 'cuda'
# 4. R로 시작한 뒤 실행할 최대 시뮬레이션 시간(1~3600초).
seconds = 30


def main():
    """위 설정을 프로젝트 실행 명령에 전달하고 실제 작업의 성공·실패 종료 코드를 반환합니다."""
    if (not isinstance(run_name, str) or not isinstance(checkpoint, str)
            or type(seconds) is not int or device not in ('cuda', 'cpu')):
        raise SystemExit('run_name·checkpoint는 문자열, seconds는 정수, device는 cuda 또는 cpu입니다.')
    # Isaac Sim 창이 열리면 뷰포트를 클릭하고 R로 시작합니다. SPACE 정지, F8 초기화.
    # 모델과 정규화 통계, 카메라 설정은 같은 학습 결과에서 읽습니다.
    # 리스트의 각 항목이 터미널 명령의 한 인자입니다. 아래 실행기가 실제 작업을 수행합니다.
    command = [str(launcher), 'act', 'infer', '--run-name', run_name, '--checkpoint', checkpoint,
               '--device', device, '--seconds', str(seconds)]
    raise SystemExit(subprocess.run(command).returncode)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('추론을 중단했습니다. 실행 터미널과 ./lekiwi status에서 종료를 확인하세요.')
