"""수업용 데이터 검증 → 공식 ACT 학습 → 모델 경로 기록. LeRobot 컨테이너 전용."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'isaac_sim')]
from tools.act.options import arguments, contained, validate
from episode_data import ACTION_NAMES, CAMERAS, FPS, STATE_NAMES
from robot_cameras import load_camera_config


def dataset_contract(info, camera_config):
    features = info['features']
    if info.get('codebase_version') != 'v3.0' or info.get('robot_type') != 'lekiwi_sim' or info.get('fps') != FPS:
        raise ValueError('이 스크립트는 30 FPS LeKiwi 시뮬레이션 v3.0 데이터셋용입니다.')
    for key, names in [('observation.state', STATE_NAMES), ('action', ACTION_NAMES)]:
        feature = features.get(key, {})
        if feature.get('dtype') != 'float32' or list(feature.get('shape', [])) != [9] or feature.get('names') != names:
            raise ValueError(f'{key}: 수집 코드의 9개 값과 순서가 다릅니다.')
    for name in CAMERAS:
        feature = features.get('observation.images.' + name, {})
        width, height = camera_config['cameras'][name]['resolution']
        if feature.get('dtype') != 'video' or list(feature.get('shape', [])) != [height, width, 3]:
            raise ValueError(f'{name}: 카메라 규격과 데이터셋 영상 크기가 다릅니다.')
    return {'version': 1, 'policy': 'act', 'fps': FPS, 'state_names': STATE_NAMES,
            'action_names': ACTION_NAMES, 'units': ['rad'] * 6 + ['m/s', 'm/s', 'rad/s'],
            'camera_config': camera_config}


def train(options, data=Path('/data')):
    options = validate(options, 'train')
    output = contained(data / 'outputs', options['run_name'])
    if output.exists():
        raise FileExistsError(f'학습 결과가 이미 있습니다. 새 run_name을 사용하세요: {output}')
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    import torch
    local = options.get('dataset_name')
    dataset_root = contained(data / 'datasets', local) if local else None
    if dataset_root is not None and not (dataset_root / 'meta/info.json').is_file():
        raise ValueError(f'변환된 로컬 데이터셋이 없습니다: {dataset_root}')
    report = {}
    if dataset_root is not None:
        report = json.loads((dataset_root / 'recording_report.json').read_text())
        if report.get('complete') is not True:
            raise ValueError('완료 검사를 통과한 변환 데이터셋을 사용하세요.')
    repo_id = report.get('repo_id') if local else options['repo_id']
    if not repo_id:
        raise ValueError('변환 결과의 repo_id가 없습니다.')
    dataset = LeRobotDataset(repo_id=repo_id, root=dataset_root, video_backend='pyav')
    camera_config = report.get('camera_config') or load_camera_config()
    contract = dataset_contract(dataset.meta.info, camera_config)
    if len(dataset) < options['batch_size']:
        raise ValueError('프레임 수보다 batch_size가 큽니다.')
    for index in sorted({0, len(dataset) // 2, len(dataset) - 1}):
        row = dataset[index]
        for key in ('observation.state', 'action', *(f'observation.images.{n}' for n in CAMERAS)):
            if not torch.isfinite(row[key]).all():
                raise ValueError(f'{index} 프레임 {key}에 유효하지 않은 값이 있습니다.')
    if options['device'] == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA를 사용할 수 없습니다. 학습 환경 또는 device 설정을 확인하세요.')
    contract.update(dataset_repo_id=repo_id, frames=len(dataset), episodes=dataset.num_episodes,
                    camera_source='recording_report' if report else 'bundled_default')
    # 공식 학습기가 사용할 train/은 아직 만들지 않습니다. 기존 출력은 항상 보존합니다.
    output.mkdir(parents=True, exist_ok=False)
    (output / 'lekiwi_policy.json').write_text(json.dumps(contract, ensure_ascii=False, indent=2))
    (output / 'lesson_config.json').write_text(json.dumps(options, ensure_ascii=False, indent=2))
    command = ['lerobot-train', '--policy.type=act', f"--policy.device={options['device']}",
               '--policy.push_to_hub=false', '--wandb.enable=false', '--env_eval_freq=0',
               f'--dataset.repo_id={repo_id}', '--dataset.video_backend=pyav',
               f'--output_dir={output / "train"}', f"--steps={options['steps']}",
               f"--batch_size={options['batch_size']}", f"--num_workers={options['num_workers']}",
               f"--log_freq={min(10, options['steps'])}", f"--save_freq={min(1000, options['steps'])}"]
    if dataset_root is not None:
        command.append(f'--dataset.root={dataset_root}')
    if not options['pretrained_backbone']:
        command.append('--policy.pretrained_backbone_weights=null')
    print(f'LEKIWI_ACT_TRAIN stage=TRAINING frames={len(dataset)} output={output}', flush=True)
    # 출력과 종료 코드를 공식 학습기로부터 그대로 받습니다. 자동 재시도하지 않습니다.
    subprocess.run(command, check=True)
    checkpoint = contained(output, 'train/checkpoints/last/pretrained_model')
    for name in ('model.safetensors', 'config.json', 'policy_preprocessor.json', 'policy_postprocessor.json'):
        if not (checkpoint / name).is_file():
            raise RuntimeError(f'학습 종료 후 저장 파일을 확인하지 못했습니다: {name}')
    result = {'run_name': options['run_name'], 'steps': options['steps'], 'checkpoint': str(checkpoint),
              'result': 'PASS', 'validation': 'Training command completed and checkpoint files exist; task performance not evaluated.'}
    (output / 'training_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print('LEKIWI_ACT_TRAIN result=PASS', flush=True)
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    arguments(parser, 'train')
    try:
        train(vars(parser.parse_args()))
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'LEKIWI_ACT_TRAIN result=FAIL error={exc}', file=sys.stderr, flush=True)
        sys.exit(1)
