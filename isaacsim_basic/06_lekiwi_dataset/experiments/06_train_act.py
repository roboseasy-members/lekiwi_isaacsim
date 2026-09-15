"""설정을 저장한 뒤 노트북 터미널에서 python3 06_train_act.py로 실행합니다."""
from pathlib import Path
import subprocess

launcher = Path(__file__).resolve().parents[3] / "lekiwi"

# 로컬 변환 데이터를 사용합니다. 공개 Hub 데이터를 쓰려면 dataset_name=None으로 바꿉니다.
dataset_name = 'lekiwi_lesson6_01'
repo_id = None  # 예: 'SJun99/leader-practice-test-20260912'

# 새 학습 결과 이름입니다. 기존 결과는 덮어쓰지 않습니다.
run_name = 'act_lesson6_01'
steps = 1000
batch_size = 4
num_workers = 0
device = 'cuda'  # GPU 환경을 준비한 뒤 사용합니다. CPU 실행은 'cpu'.
pretrained_backbone = True  # 처음에는 ResNet18 가중치를 다운로드합니다.
# 실행 검사만 할 때: steps=1, batch_size=1, pretrained_backbone=False.


def main():
    if (dataset_name is None) == (repo_id is None):
        raise SystemExit('dataset_name 또는 repo_id 중 하나만 지정하고 나머지는 None으로 바꾸세요.')
    if (not isinstance(run_name, str) or any(type(v) is not int for v in (steps, batch_size, num_workers))
            or type(pretrained_backbone) is not bool or device not in ('cuda', 'cpu')):
        raise SystemExit('학습 설정의 자료형을 확인하세요. 횟수는 정수, pretrained_backbone은 True/False입니다.')
    source = ['--dataset-name', dataset_name] if dataset_name is not None else ['--repo-id', repo_id]
    if not isinstance(source[1], str):
        raise SystemExit('데이터셋 이름 또는 repo_id는 문자열이어야 합니다.')
    command = [str(launcher), 'act', 'train', *source, '--run-name', run_name, '--steps', str(steps),
               '--batch-size', str(batch_size), '--num-workers', str(num_workers), '--device', device,
               '--pretrained-backbone' if pretrained_backbone else '--no-pretrained-backbone']
    raise SystemExit(subprocess.run(command).returncode)


if __name__ == '__main__':
    main()
