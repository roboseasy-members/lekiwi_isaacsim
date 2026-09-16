"""6장 · 검사한 데이터셋을 ACT 학습기에 전달하는 설정 코드.

실행: 저장소 최상위 폴더에서 python3 isaacsim_basic/06_lekiwi_dataset/experiments/06_train_act.py
준비: 변환·검사 완료, 기존 Isaac Sim·teleop 종료.

읽는 순서
1. dataset_name 또는 repo_id: 로컬 변환본과 공개 Hub 입력 중 하나를 선택합니다.
2. run_name: 새 학습 결과 이름. steps/batch_size/device는 계산량과 계산 장치 설정입니다.
3. main(): 설정 검사 → act train 명령 구성 → Docker의 공식 LeRobot ACT 학습기 실행.

학습기는 카메라 영상·상태를 입력으로 받고 시연 action을 예측하도록 모델 가중치를 조정합니다.
기본 steps=1, batch_size=1은 학습 계산·결과 저장이 실행되는지 확인하는 설정입니다.
완료 기준: LEKIWI_ACT_TRAIN result=PASS와 data/outputs/<run_name>/의 실제 모델·training_result.json.
1회 실행 모델의 집기 성능은 확인 기준이 아닙니다. 본 학습은 새 run_name과 충분한 데이터·횟수로 진행합니다.
다음 단계: 07_infer_act.py의 run_name에 이번 학습 결과 이름을 넣습니다.
문법 안내와 실행 흐름: isaacsim_basic/CODE_GUIDE.md"""
from pathlib import Path
import subprocess

# __file__은 이 파일의 위치입니다. 이 위치를 기준으로 저장소의 lekiwi 실행기를 찾습니다.
launcher = Path(__file__).resolve().parents[3] / "lekiwi"

# 로컬 변환 데이터를 사용합니다. 공개 Hub 데이터를 쓰려면 dataset_name=None으로 바꿉니다.
dataset_name = 'lekiwi_lesson6_01'
repo_id = None  # 예: 'SJun99/leader-practice-test-20260912'

# 새 학습 결과 이름입니다. 기존 결과는 덮어쓰지 않습니다.
run_name = 'act_lesson6_check_01'
steps = 1  # 수업 기본값: 학습 계산·모델 저장이 실행되는지 1회 확인합니다.
batch_size = 1
num_workers = 0
device = 'cuda'  # GPU 환경을 준비한 뒤 사용합니다. CPU 실행은 'cpu'.
pretrained_backbone = False  # 실행 검사에서는 초기 ResNet18 가중치 다운로드를 생략합니다.
# 본 학습 예: 새 run_name, steps=1000, batch_size=4, pretrained_backbone=True.
# 1회 학습 모델로 집기 성공을 기대하지 않습니다. 과제 수행은 별도 리허설에서 확인합니다.


def main():
    """위 설정을 프로젝트 실행 명령에 전달하고 실제 작업의 성공·실패 종료 코드를 반환합니다."""
    if (dataset_name is None) == (repo_id is None):
        raise SystemExit('dataset_name 또는 repo_id 중 하나만 지정하고 나머지는 None으로 바꾸세요.')
    if (not isinstance(run_name, str) or any(type(v) is not int for v in (steps, batch_size, num_workers))
            or type(pretrained_backbone) is not bool or device not in ('cuda', 'cpu')):
        raise SystemExit('학습 설정의 자료형을 확인하세요. 횟수는 정수, pretrained_backbone은 True/False입니다.')
    source = ['--dataset-name', dataset_name] if dataset_name is not None else ['--repo-id', repo_id]
    if not isinstance(source[1], str):
        raise SystemExit('데이터셋 이름 또는 repo_id는 문자열이어야 합니다.')
    # 리스트의 각 항목이 터미널 명령의 한 인자입니다. 아래 실행기가 실제 작업을 수행합니다.
    command = [str(launcher), 'act', 'train', *source, '--run-name', run_name, '--steps', str(steps),
               '--batch-size', str(batch_size), '--num-workers', str(num_workers), '--device', device,
               '--pretrained-backbone' if pretrained_backbone else '--no-pretrained-backbone']
    raise SystemExit(subprocess.run(command).returncode)


if __name__ == '__main__':
    main()
