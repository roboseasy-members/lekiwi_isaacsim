"""저장된 ACT와 전·후처리기를 읽어 같은 서버의 Isaac Sim 요청에 응답합니다."""
import argparse
import json
import math
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'isaac_sim')]
from tools.act.options import contained
from episode_data import ACTION_NAMES, STATE_NAMES, FPS
from policy_bridge import CAMERAS, receive_observation, send_json, vector


def load_contract(run, checkpoint='last'):
    run = Path(run).resolve()
    contract = json.loads((run / 'lekiwi_policy.json').read_text())
    if (contract.get('version') != 1 or contract.get('policy') != 'act' or contract.get('fps') != FPS
            or contract.get('state_names') != STATE_NAMES or contract.get('action_names') != ACTION_NAMES
            or contract.get('units') != ['rad'] * 6 + ['m/s', 'm/s', 'rad/s']):
        raise ValueError('수업용 ACT 학습 스크립트로 만든 모델을 선택하세요.')
    path = contained(run, 'train/checkpoints', checkpoint, 'pretrained_model')
    for name in ('model.safetensors', 'config.json', 'policy_preprocessor.json', 'policy_postprocessor.json'):
        if not (path / name).is_file():
            raise ValueError(f'완성된 체크포인트가 없습니다: {path / name}')
    return contract, path


class ACTModel:
    def __init__(self, checkpoint, contract, device):
        import torch
        from lerobot.policies.act.configuration_act import ACTConfig
        from lerobot.policies.act.modeling_act import ACTPolicy
        from lerobot.policies.factory import make_pre_post_processors
        self.torch = torch
        config = ACTConfig.from_pretrained(checkpoint, local_files_only=True)
        config.device = device
        # 체크포인트에 backbone도 있으므로 ImageNet 가중치를 다시 내려받지 않습니다.
        config.pretrained_backbone_weights = None
        self.shapes = {n: (contract['camera_config']['cameras'][n]['resolution'][1],
                           contract['camera_config']['cameras'][n]['resolution'][0], 3) for n in CAMERAS}
        expected = {'observation.state', *(f'observation.images.{n}' for n in CAMERAS)}
        if (set(config.input_features) != expected or set(config.output_features) != {'action'}
                or tuple(config.input_features['observation.state'].shape) != (9,)
                or tuple(config.output_features['action'].shape) != (9,)):
            raise ValueError('체크포인트의 ACT 입출력과 LeKiwi 규격이 다릅니다.')
        for name, (height, width, _) in self.shapes.items():
            if tuple(config.input_features[f'observation.images.{name}'].shape) != (3, height, width):
                raise ValueError(f'{name}: 체크포인트의 영상 크기가 다릅니다.')
        self.policy = ACTPolicy.from_pretrained(checkpoint, config=config, local_files_only=True)
        self.policy.to(device).eval()
        self.pre, self.post = make_pre_post_processors(config, pretrained_path=checkpoint,
            preprocessor_overrides={'device_processor': {'device': device}, 'normalizer_processor': {'device': device}},
            postprocessor_overrides={'unnormalizer_processor': {'device': device}, 'device_processor': {'device': 'cpu'}})
        self.last_sequence = None
        self.last_time = None

    def predict(self, header, state, images):
        if header['reset']:
            self.policy.reset()
            self.pre.reset()
            self.post.reset()
            self.last_sequence = self.last_time = None
        elif (self.last_sequence is None or header['sequence'] != self.last_sequence + 1
              or not math.isclose(header['simulation_time'] - self.last_time, 1 / FPS, abs_tol=1e-5)):
            raise ValueError('관측 시퀀스가 끊겼습니다. R로 추론을 다시 시작하세요.')
        torch = self.torch
        observation = {'observation.state': torch.from_numpy(state.copy())}
        for name in CAMERAS:
            # 공식 학습 루프와 동일하게 RGB를 CHW float32 [0,1]로 바꾼 뒤 저장된 통계로 정규화합니다.
            observation[f'observation.images.{name}'] = torch.from_numpy(images[name]).permute(2, 0, 1).float() / 255.0
        with torch.inference_mode():
            action = self.post(self.policy.select_action(self.pre(observation)))
        action = vector(action.squeeze(0).cpu().numpy())
        self.last_sequence, self.last_time = header['sequence'], header['simulation_time']
        return action.tolist()


def serve(run, checkpoint, device, directory):
    directory = Path(directory)
    contract, checkpoint_path = load_contract(run, checkpoint)
    model = ACTModel(checkpoint_path, contract, device)
    path = directory / 'policy.sock'
    # 새 실행 폴더만 사용하므로 남아 있는 다른 소켓을 삭제하지 않습니다.
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        path.chmod(0o600)
        server.listen(1)
        ready = directory / 'ready.json'
        temporary = directory / 'ready.partial'
        temporary.write_text(json.dumps(contract, ensure_ascii=False))
        os.replace(temporary, ready)
        print('LEKIWI_ACT_POLICY result=READY', flush=True)
        while True:
            connection, _ = server.accept()
            with connection:
                connection.settimeout(5)
                header = {}
                try:
                    header, state, images = receive_observation(connection, model.shapes)
                    action = model.predict(header, state, images)
                    send_json(connection, {'sequence': header['sequence'], 'simulation_time': header['simulation_time'],
                                           'action': action})
                except (OSError, ValueError, RuntimeError, KeyError) as exc:
                    print(f'LEKIWI_ACT_POLICY request=FAIL error={exc}', flush=True)
                    try:
                        send_json(connection, {'sequence': header.get('sequence'),
                            'simulation_time': header.get('simulation_time'), 'error': str(exc)[:1000]})
                    except OSError:
                        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--checkpoint', default='last')
    parser.add_argument('--device', choices=('cuda', 'cpu'), default='cuda')
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    serve(args.run, args.checkpoint, args.device, args.directory)
