"""ACT 학습 컨테이너와 시뮬레이션 추론 세션의 수명을 관리하는 호스트 실행기."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.act.options import arguments, cli_args, contained, validate
from tools.remote_classroom.main import stop_owned


def docker_command():
    if os.environ.get('LEKIWI_DOCKER_SUDO') == '1':
        refresh = ['sudo', '-n', '-v'] if os.environ.get('LEKIWI_CLASSROOM_SESSION') else ['sudo', '-v']
        subprocess.run(refresh, check=True)
        # Compose가 사용하는 현재 사용자의 환경만 보존합니다. HOME은 바꾸지 않습니다.
        return ['sudo', '--preserve-env=LEKIWI_UID,LEKIWI_GID,LEKIWI_DATA_DIR,LEKIWI_LEROBOT_IMAGE,LEKIWI_SIM_IMAGE,ACCEPT_EULA', 'docker']
    return ['docker']


def stop_process(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('ACT 실행기 종료가 지연됩니다. 로그를 확인하세요.') from exc


def run(mode, options, host=None):
    options = validate(options, mode)
    data = Path(os.environ.get('LEKIWI_DATA_DIR', ROOT / 'data')).resolve()
    if not Path(os.environ.get('LEKIWI_DATA_DIR', str(data))).is_absolute():
        raise ValueError('LEKIWI_DATA_DIR는 절대 경로여야 합니다.')
    output = contained(data / 'outputs', options['run_name'])
    if mode == 'train' and output.exists():
        raise FileExistsError('기존 학습 결과를 보존했습니다. 새 run_name을 사용하세요.')
    if mode == 'infer' and not (output / 'lekiwi_policy.json').is_file():
        raise ValueError('학습 결과가 없습니다. 06_train_act.py의 run_name을 확인하세요.')
    if host is not None:
        from isaac_sim.app_runtime import stream_host
        host = stream_host(host)
    for folder in ('outputs', 'datasets', 'home/lerobot', 'cache/huggingface', 'cache/lerobot', 'policy'):
        (data / folder).mkdir(parents=True, exist_ok=True)
    # 같은 서버 데이터 폴더의 학습·추론을 중복 실행하지 않습니다.
    with (data / 'policy/act.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('ACT 작업이 이미 실행 중입니다. 상태를 확인하세요.') from exc
        dock = docker_command()
        subprocess.run(dock + ['info'], check=True, stdout=subprocess.DEVNULL)
        project = os.environ.get('LEKIWI_PROJECT_NAME', 'lekiwi')
        active = subprocess.check_output(dock + ['ps', '-q', '--filter',
            f'label=com.docker.compose.project={project}', '--filter', 'label=com.docker.compose.service=sim'], text=True).strip()
        if active:
            raise RuntimeError('실행 중인 Isaac Sim 창을 닫고 ./lekiwi status로 종료를 확인한 뒤 시작하세요.')
        compose = dock + ['compose', '--project-directory', str(ROOT), '--project-name', project,
                         '-f', str(ROOT / 'compose.yaml')]
        image = subprocess.check_output(compose + ['config', '--images', 'lerobot'], text=True).strip()
        if subprocess.run(dock + ['image', 'inspect', image], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode:
            raise RuntimeError('ACT 실행 이미지가 없습니다. ./lekiwi setup lerobot으로 준비하세요.')
        identity = uuid.uuid4().hex
        container = f'{project}-act-{identity[:12]}'
        process = sim = None
        env = dict(os.environ, LEKIWI_DATA_DIR=str(data), LEKIWI_CLASSROOM_SESSION=identity)
        base = compose + ['run', '--rm', '--no-deps', '-T', '--name', container,
                          '--label', f'lekiwi.act.run={identity}', '-e', 'HF_HUB_DISABLE_IMPLICIT_TOKEN=1',
                          '-e', 'HF_HUB_DISABLE_TELEMETRY=1']
        try:
            if mode == 'train':
                if options.get('dataset_name'):
                    base += ['--volume', f'{data / "datasets"}:/data/datasets:ro']
                process = subprocess.Popen(base + ['lerobot', 'python', '/opt/lekiwi/tools/act/train.py',
                                                  *cli_args(options)], env=env, stdin=subprocess.DEVNULL)
                code = process.wait()
                if code:
                    raise RuntimeError(f'ACT 학습 종료 코드: {code}')
                return
            directory = Path(tempfile.mkdtemp(prefix='act.', dir=data / 'policy'))
            inside = '/data/policy/' + directory.name
            print(f'ACT 모델 로그: {directory / "policy.log"}', flush=True)
            with (directory / 'policy.log').open('w') as log:
                process = subprocess.Popen(base + ['-e', 'HF_HUB_OFFLINE=1', 'lerobot', 'python',
                    '/opt/lekiwi/tools/act/policy.py', '--run', '/data/outputs/' + options['run_name'],
                    '--checkpoint', options['checkpoint'], '--device', options['device'], '--directory', inside],
                    env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 180
            while not (directory / 'ready.json').is_file():
                if process.poll() is not None:
                    raise RuntimeError(f'ACT 모델 로딩 실패. {directory / "policy.log"}를 확인하세요.')
                if time.monotonic() > deadline:
                    raise RuntimeError(f'ACT 모델 로딩 시간 초과. {directory / "policy.log"}를 확인하세요.')
                time.sleep(0.2)
            contract = json.loads((directory / 'ready.json').read_text())
            (directory / 'camera.json').write_text(json.dumps(contract['camera_config']))
            # 리더·기록 설정을 이어받지 않습니다. 학습 때 사용한 카메라 장착 설정을 재사용합니다.
            for key in ('LEKIWI_TELEOP_STATE', 'LEKIWI_TELEOP_SESSION', 'LEKIWI_TELEOP_REMOTE'):
                env.pop(key, None)
            env.update(LEKIWI_POLICY_DIR=inside, LEKIWI_POLICY_SECONDS=str(options['seconds']),
                       LEKIWI_CAMERA_CONFIG=inside + '/camera.json', LEKIWI_RECORDING='0',
                       LEKIWI_COURSE_LAYOUT='random')
            if host:
                env.update(LEKIWI_DISPLAY_MODE='webrtc', LEKIWI_STREAM_HOST=host)
            else:
                env.update(LEKIWI_DISPLAY_MODE='local')
                env.pop('LEKIWI_STREAM_HOST', None)
            sim = subprocess.Popen([str(ROOT / 'lekiwi'), 'sim'], env=env, stdin=subprocess.DEVNULL)
            while sim.poll() is None:
                if process.poll() is not None:
                    raise RuntimeError('ACT 모델 프로세스가 종료되어 추론 세션을 중단합니다.')
                time.sleep(0.2)
            if sim.returncode:
                raise RuntimeError(f'Isaac Sim 종료 코드: {sim.returncode}')
        finally:
            # 이 호출의 라벨이 일치하는 컨테이너만 정리합니다.
            try:
                if sim is not None:
                    stop_owned(dock, project + '-sim', 'lekiwi.classroom.session', identity)
                    stop_process(sim)
            finally:
                if process is not None:
                    stop_owned(dock, container, 'lekiwi.act.run', identity)
                    stop_process(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    for mode in ('train', 'infer'):
        child = commands.add_parser(mode)
        arguments(child, mode)
        if mode == 'infer':
            child.add_argument('--host', help='브라우저 WebRTC 서버 IPv4 주소. 생략하면 로컬 창.')
    options = vars(parser.parse_args())
    mode, host = options.pop('mode'), options.pop('host', None)
    run(mode, options, host)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        main()
    except KeyboardInterrupt:
        print('ACT 세션을 종료했습니다.', flush=True)
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'중단: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
