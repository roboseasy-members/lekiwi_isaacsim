"""노트북 한 대 수업의 호스트 실행·업로드 입력 검사. GPU·USB·네트워크 미사용."""
from contextlib import nullcontext
import io
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.mark.parametrize('filename,action', [
    ('02_dataset_list.py', ['dataset', 'list']),
    ('03_convert_dataset.py', ['dataset', 'export']),
    ('04_inspect_dataset.py', ['dataset', 'inspect']),
    ('05_upload_dataset.py', ['dataset', 'upload']),
    ('06_train_act.py', ['act', 'train']),
    ('07_infer_act.py', ['act', 'infer']),
])
def test_student_scripts_work_from_unrelated_directory_without_lesson(tmp_path, filename, action):
    # 실제 자식 프로세스로 학생 파일 → 자기 저장소 실행기 경로와 종료 코드 전파를 검사합니다.
    root = tmp_path / 'checkout with spaces'
    folder = root / 'isaacsim_basic/06_lekiwi_dataset/experiments'
    folder.mkdir(parents=True)
    source = (ROOT / 'isaacsim_basic/06_lekiwi_dataset/experiments' / filename).read_text()
    source = source.replace('episode_ids = [', "episode_ids = ['lekiwi.one/episode.two',")
    source = source.replace("repo_id = 'account/lekiwi_lesson6_01'", "repo_id = 'student/lekiwi_lesson6_01'")
    script = folder / filename
    script.write_text(source)
    launcher = root / 'lekiwi'
    launcher.write_text('#!/usr/bin/python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\nsys.exit(23)\n')
    launcher.chmod(0o755)
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 23, result.stderr
    command = json.loads(result.stdout)
    assert command[:2] == action
    if action[-1] == 'upload':
        assert command[-1] == '--public'


@pytest.mark.parametrize('interactive', [True, False])
def test_upload_reads_hidden_terminal_or_explicit_pipe_without_printing_token(monkeypatch, capsys, interactive):
    from tools.dataset_manager import cli
    secret = 'hf_test_local_only_123456789'
    stream = io.StringIO('' if interactive else secret + '\n')
    monkeypatch.setattr(stream, 'isatty', lambda: interactive)
    monkeypatch.setattr(sys, 'stdin', stream)
    monkeypatch.setattr(sys, 'argv', ['dataset', 'upload', '--name', 'sample',
                                    '--repo-id', 'student/sample', '--public'])
    monkeypatch.setattr(cli.core, 'operation_lock', nullcontext)
    prompts, received = [], []
    monkeypatch.setattr(cli.getpass, 'getpass', lambda text: prompts.append(text) or secret)
    def upload(name, repo, private, token):
        received.append((name, repo, private, token))
        return {'url': 'https://huggingface.co/datasets/student/sample'}
    monkeypatch.setattr(cli.core, 'upload_dataset', upload)
    cli.main()
    assert bool(prompts) == interactive
    assert received == [('sample', 'student/sample', False, secret)]
    output = capsys.readouterr()
    assert secret not in output.out + output.err


def fake_docker_env(tmp_path):
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    docker = bindir / 'docker'
    docker.write_text('''#!/usr/bin/python3
import json, os, sys
args = sys.argv[1:]
if 'config' in args and '--images' in args:
    print('lekiwi-lerobot:fake')
if 'run' in args:
    print('DOCKER_RUN=' + json.dumps({'args': args, 'tty': sys.stdin.isatty(),
                                    'display_mode': os.environ.get('LEKIWI_DISPLAY_MODE'),
                                    'stream_host': os.environ.get('LEKIWI_STREAM_HOST')}), flush=True)
''')
    docker.chmod(0o755)
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ['PATH'],
               LEKIWI_DOCKER_SUDO='0', LEKIWI_DATA_DIR=str(tmp_path / 'data'),
               LEKIWI_DISPLAY_MODE='webrtc', LEKIWI_STREAM_HOST='192.0.2.1')
    env.pop('LEKIWI_CLASSROOM_SESSION', None)
    return env


def test_local_upload_gets_real_terminal_and_disables_implicit_hub_login(tmp_path):
    env = fake_docker_env(tmp_path)
    master, slave = pty.openpty()
    process = subprocess.Popen([str(ROOT / 'lekiwi'), 'dataset', 'upload', '--name', 'sample',
                                '--repo-id', 'student/sample', '--public'],
                               env=env, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    output = b''
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    part = os.read(master, 65536)
                except OSError:
                    break
                if not part:
                    break
                output += part
        assert process.wait(timeout=2) == 0, output.decode()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
    record = json.loads(next(line.partition('=')[2] for line in output.decode().splitlines()
                             if line.startswith('DOCKER_RUN=')))
    assert record['tty'] is True
    assert '-T' not in record['args']
    assert 'HF_HUB_OFFLINE=0' in record['args']
    assert 'HF_HUB_DISABLE_IMPLICIT_TOKEN=1' in record['args']
    assert record['display_mode'] == 'local' and record['stream_host'] is None


def test_local_upload_without_terminal_stops_before_container_launch(tmp_path):
    result = subprocess.run([str(ROOT / 'lekiwi'), 'dataset', 'upload', '--name', 'sample',
                             '--repo-id', 'student/sample', '--public'],
                            env=fake_docker_env(tmp_path), stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert '대화형 터미널' in result.stderr
    assert 'DOCKER_RUN=' not in result.stdout
