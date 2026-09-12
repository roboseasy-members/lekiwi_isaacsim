"""ACT 학생 설정·학습 수명·시뮬레이션 추론 경계. 실제 GPU나 로봇을 사용하지 않습니다."""
from concurrent.futures import Future
import copy
import json
from pathlib import Path
import runpy
import signal
import socket
import struct
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'isaac_sim')]
from tools.act.options import contained, validate
from tools.act.train import dataset_contract
from tools.act.policy import load_contract
from tools.web_classroom.control import Session, ControlServer, selection
from tools.web_classroom import lesson
from act_inference import InferenceCameras, PolicyControl
from episode_data import STATE_NAMES, ACTION_NAMES
from policy_bridge import query, receive_observation, send_json, receive_json
from robot_cameras import load_camera_config


class Process:
    def __init__(self, command, **options):
        self.command, self.options, self.code = command, options, None
        self.signals = []
    def poll(self): return self.code
    def send_signal(self, sig): self.signals.append(sig)
    def wait(self, timeout): self.code = 130


@pytest.fixture
def session(tmp_path):
    return Session(tmp_path, tmp_path / 'data', '192.168.0.171', popen=Process)


def request(**extra):
    return dict(op='train', action='start', dataset_name='sample', run_name='act_sample',
                steps=1, batch_size=1, pretrained_backbone=False, **extra)


@pytest.mark.parametrize('changes', [
    {'run_name': '../existing'}, {'device': 'cuda;echo x'}, {'steps': True}, {'steps': 0},
    {'batch_size': -1}, {'num_workers': 33}, {'pretrained_backbone': 'false'},
    {'repo_id': 'student/sample'}, {'dataset_name': '/etc'}, {'command': 'sh'},
])
def test_invalid_training_options_never_start(session, changes):
    message = request()
    message.update(changes)
    with pytest.raises(ValueError):
        session.dispatch(message)
    assert not session.training.jobs


def test_train_owns_process_and_needs_completion_report(session):
    state = session.dispatch(request())
    job = session.training.job()
    assert job['process'].command[:3] == [str(session.root / 'lekiwi'), 'act', 'train']
    assert '--no-pretrained-backbone' in job['process'].command
    assert job['process'].options['stdin'] == subprocess.DEVNULL
    with pytest.raises(RuntimeError):
        session.dispatch(request())
    with pytest.raises(RuntimeError):
        session.dispatch({'op': 'run', 'chapter': 6})
    with pytest.raises(RuntimeError):
        session.dispatch({'op': 'infer', 'run_name': 'act_sample'})
    assert session.dispatch({'op': 'stop'})['state'] == 'IDLE'
    assert not job['process'].signals
    job['process'].code = 0
    assert session.training.status()['state'] == 'FAILED'  # 종료 코드만으로 성공 처리하지 않습니다.
    assert session.training.status(state['job_id'])['state'] == 'FAILED'


def test_train_success_report_and_stop_preserve_files(session):
    session.dispatch(request())
    job = session.training.job()
    output = session.data / 'outputs/act_sample'
    output.mkdir(parents=True)
    result = {'result': 'PASS', 'steps': 1, 'checkpoint': '/data/outputs/act_sample/train/checkpoints/000001/pretrained_model'}
    (output / 'training_result.json').write_text(json.dumps(result))
    job['process'].code = 0
    assert session.training.status()['state'] == 'SUCCEEDED'
    with pytest.raises(ValueError, match='기존'):
        session.dispatch(request())
    session.dispatch(dict(request(), run_name='act_second'))
    running = session.training.job()
    assert session.dispatch({'op': 'train', 'action': 'stop'})['state'] == 'STOPPED'
    assert running['process'].signals == [signal.SIGINT]
    assert (output / 'training_result.json').is_file()


def test_inference_uses_session_stop_and_fixed_server(session):
    state = session.dispatch({'op': 'infer', 'run_name': 'act_sample', 'seconds': 20, 'device': 'cpu'})
    assert state['state'] == 'STARTING'
    assert session.process.command[:3] == [str(session.root / 'lekiwi'), 'act', 'infer']
    assert session.process.command[-2:] == ['--host', '192.168.0.171']
    with pytest.raises(RuntimeError):
        session.dispatch(request())
    with pytest.raises(RuntimeError):
        session.dispatch({'op': 'infer', 'run_name': 'act_sample'})
    with pytest.raises(ValueError):
        session.dispatch({'op': 'infer', 'run_name': 'act_sample', 'host': 'other'})
    session.log.write_text('LEKIWI_DRIVE result=READY\n')
    assert session.status()['state'] == 'READY'
    assert session.dispatch({'op': 'stop'})['state'] == 'STOPPED'
    assert session.process.signals == [signal.SIGINT]


def test_train_browser_socket_and_real_child(tmp_path):
    # 실제 소켓·자식 수명은 사용하되, GPU 학습 대신 결과 파일을 만드는 실행기로 검사합니다.
    executable = tmp_path / 'lekiwi'
    executable.write_text(f'#!{sys.executable}\n' + '''
import json, os, pathlib, sys
assert sys.argv[1:3] == ['act', 'train']
path = pathlib.Path(os.environ['LEKIWI_DATA_DIR']) / 'outputs/act_sample'
path.mkdir(parents=True)
(path / 'training_result.json').write_text(json.dumps({'result':'PASS','steps':1}))
print('finite loss')
''')
    executable.chmod(0o755)
    session = Session(tmp_path, tmp_path / 'data', '192.168.0.171')
    server = ControlServer(tmp_path / 'control.sock', session)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        import os
        completed = subprocess.run([sys.executable, str(ROOT / 'tools/web_classroom/lesson.py'),
            'train', 'start', '--dataset-name', 'sample', '--run-name', 'act_sample', '--steps', '1'],
            env=dict(os.environ, LEKIWI_CONTROL_SOCKET=str(tmp_path / 'control.sock')),
            capture_output=True, text=True, timeout=10)
        assert completed.returncode == 0, completed.stderr
        assert 'LEKIWI_TRAIN_JOB result=PASS' in completed.stdout
        assert 'finite loss' in session.training.dispatch({'action': 'logs'})['log']
    finally:
        server.shutdown()
        thread.join(3)
        server.server_close()
        session.training.close()


@pytest.mark.parametrize('filename', ['06_train_act.py', '07_infer_act.py'])
def test_student_python_settings_reach_lesson(monkeypatch, filename):
    script = ROOT / 'isaacsim_basic/06_lekiwi_dataset/experiments' / filename
    module = runpy.run_path(str(script), run_name='student_test')
    settings = module['main'].__globals__
    settings['run_name'] = 'act_changed'
    monkeypatch.setattr(settings['shutil'], 'which', lambda _: '/usr/local/bin/lesson')
    calls = []
    def run(command):
        calls.append(command)
        return type('Result', (), {'returncode': 0})()
    monkeypatch.setattr(settings['subprocess'], 'run', run)
    with pytest.raises(SystemExit) as exc:
        module['main']()
    assert exc.value.code == 0
    assert calls[0][calls[0].index('--run-name') + 1] == 'act_changed'
    with pytest.raises(ValueError, match='python3'):
        selection({'script': str(script)}, ROOT)


def test_training_ctrl_c_only_detaches(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(lesson, 'request', lambda msg: calls.append(msg) or {'state': 'RUNNING', 'job_id': 'train.x'})
    def interrupt(_): raise KeyboardInterrupt
    monkeypatch.setattr(lesson.time, 'sleep', interrupt)
    lesson.main(['train', 'start', '--dataset-name', 'sample', '--run-name', 'new'])
    assert len(calls) == 1
    assert '학습은 계속' in capsys.readouterr().out


def info():
    return {'codebase_version': 'v3.0', 'robot_type': 'lekiwi_sim', 'fps': 30,
        'features': {'observation.state': {'dtype': 'float32', 'shape': [9], 'names': STATE_NAMES},
                     'action': {'dtype': 'float32', 'shape': [9], 'names': ACTION_NAMES},
                     **{f'observation.images.{n}': {'dtype': 'video', 'shape': [480,640,3]} for n in ('front','wrist')}}}


def test_dataset_contract_catches_order_and_units_mismatch():
    assert dataset_contract(info(), load_camera_config())['units'][-1] == 'rad/s'
    changed = copy.deepcopy(info())
    changed['features']['action']['names'].reverse()
    with pytest.raises(ValueError, match='순서'):
        dataset_contract(changed, load_camera_config())
    changed = info()
    changed['fps'] = 60
    with pytest.raises(ValueError, match='30 FPS'):
        dataset_contract(changed, load_camera_config())


def test_paths_and_checkpoint_symlinks_stay_inside_run(tmp_path):
    run = tmp_path / 'outputs/act_sample'
    run.mkdir(parents=True)
    (run / 'lekiwi_policy.json').write_text(json.dumps(dataset_contract(info(), load_camera_config())))
    checkpoint = run / 'train/checkpoints/000001/pretrained_model'
    checkpoint.mkdir(parents=True)
    for filename in ('config.json','model.safetensors','policy_preprocessor.json','policy_postprocessor.json'):
        (checkpoint / filename).write_text('{}')
    (checkpoint.parents[1] / 'last').symlink_to('000001')
    assert load_contract(run)[1] == checkpoint
    (checkpoint.parents[1] / 'bad').symlink_to(tmp_path)
    with pytest.raises(ValueError, match='밖'):
        load_contract(run, 'bad')
    with pytest.raises(ValueError):
        contained(run, '../other')


def test_rgb_and_actions_round_trip_on_real_unix_socket(tmp_path):
    shapes = {'front': (16,20,3), 'wrist': (12,16,3)}
    images = {key: np.arange(np.prod(shape), dtype=np.uint8).reshape(shape) for key,shape in shapes.items()}
    path = str(tmp_path / 'policy.sock')
    errors = []
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(path)
        server.listen(1)
        def worker():
            try:
                with server.accept()[0] as connection:
                    header, state, received = receive_observation(connection, shapes)
                    assert header['reset'] is True
                    for name in images:
                        np.testing.assert_array_equal(received[name], images[name])
                    np.testing.assert_array_equal(state, np.arange(9))
                    send_json(connection, {'sequence': header['sequence'], 'simulation_time': header['simulation_time'],
                                           'action': [.25] * 9})
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=worker)
        thread.start()
        action = query(path, 1, 2.0, list(range(9)), images, True)
        thread.join(2)
    assert not errors
    np.testing.assert_allclose(action, [.25] * 9)


def test_protocol_rejects_oversized_header():
    left, right = socket.socketpair()
    try:
        left.sendall(struct.pack('!I', 1000000))
        with pytest.raises(ValueError, match='크기'):
            receive_json(right)
    finally:
        left.close()
        right.close()


class Deferred:
    def __init__(self): self.calls = []
    def submit(self, *args):
        self.calls.append(args)
        self.future = Future()
        return self.future
    def shutdown(self, **kwargs): pass


@pytest.fixture
def policy():
    controller = PolicyControl('/unused')
    controller.executor.shutdown()
    controller.executor = Deferred()
    yield controller
    controller.close()


def test_policy_waits_for_r_freezes_time_limits_action_and_resets_queue(policy):
    state = [0.] * 9
    action, advance = policy.update(state, 1.0, lambda: {})
    assert advance and not policy.executor.calls
    _, advance = policy.update(state, 1.0, lambda: {}, start=True)
    assert not advance and policy.executor.calls[0][-1] is True
    assert policy.update(state, 1.0, lambda: {})[1] is False
    policy.future.set_result([10.] * 9)
    action, advance = policy.update(state, 1.0, lambda: {})
    assert advance and policy.steps == 1
    np.testing.assert_allclose(action[:6], [.1] * 6)
    assert np.linalg.norm(action[6:8]) <= .500001 and action[8] <= 1.600001
    policy.update(state, 1.0 + 1/30, lambda: {})
    late = policy.future
    action, advance = policy.update(state, 1.0 + 1/30, lambda: {}, stop=True)
    assert advance and not policy.armed and not action[6:].any()
    late.set_result([2.] * 9)
    policy.update(state, 2.0, lambda: {})
    assert policy.future is None and not policy.armed
    policy.update(state, 3.0, lambda: {}, start=True)
    assert policy.executor.calls[-1][-1] is True


@pytest.mark.parametrize('reason', ['nan','timeout','pause','duration'])
def test_policy_stops_on_invalid_action_delay_pause_or_duration(policy, reason):
    now = [0.]
    policy.clock = lambda: now[0]
    policy.update([0.] * 9, 0., lambda: {}, start=True)
    if reason == 'nan': policy.future.set_result([float('nan')] * 9)
    if reason == 'timeout': now[0] = 6.
    if reason == 'duration': policy.steps = policy.seconds * 30
    action, advance = policy.update([0.] * 9, 0., lambda: {}, playing=reason != 'pause')
    assert advance and not policy.armed and not action[6:].any()


def test_camera_wait_does_not_skip_time_after_first_action(policy):
    policy.update([0.] * 9, 0., lambda: None, start=True)
    policy.steps = 1
    assert not policy.update([0.] * 9, 1/30, lambda: None)[1]


@pytest.mark.parametrize('mode', ['current', 'delayed', 'different_reference'])
def test_inference_camera_requires_both_rgb_at_current_physics_time(mode):
    from types import SimpleNamespace
    camera = InferenceCameras.__new__(InferenceCameras)
    camera.clock = SimpleNamespace(get_sim_time_at_time=lambda ref: ref[0] / ref[1])
    pixels = np.full((16, 20, 4), 127, dtype=np.uint8)
    front = {'referenceTimeNumerator': 60, 'referenceTimeDenominator': 30}
    wrist = dict(front)
    if mode == 'delayed':
        front['referenceTimeNumerator'] = wrist['referenceTimeNumerator'] = 59
    if mode == 'different_reference':
        wrist = {'referenceTimeNumerator': 120, 'referenceTimeDenominator': 60}
    camera.sensors = {
        'front': (None, SimpleNamespace(get_data=lambda: pixels), SimpleNamespace(get_data=lambda: front)),
        'wrist': (None, SimpleNamespace(get_data=lambda: pixels), SimpleNamespace(get_data=lambda: wrist))}
    result = camera.snapshot(SimpleNamespace(current_time=2.0))
    if mode != 'current':
        assert result is None
    else:
        assert result['front'].shape == (16, 20, 3)
        pixels[:] = 0
        assert (result['front'] == 127).all()  # 다음 렌더가 추론 입력을 덮어쓰지 않습니다.
