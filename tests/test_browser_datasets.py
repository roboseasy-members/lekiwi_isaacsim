"""브라우저 변환 요청, 긴 작업의 수명, 완료 판정을 검사합니다. GPU/USB는 사용하지 않습니다."""
import json
from pathlib import Path
import signal
import subprocess
import sys
import threading
import runpy

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.web_classroom.control import ControlServer, Session
from tools.web_classroom.datasets import dataset_command


class Job:
    def __init__(self, command, **options):
        self.command, self.options = command, options
        self.code, self.signals = None, []
        self.stdin = SecretInput() if options.get('stdin') == subprocess.PIPE else None

    def poll(self):
        return self.code

    def send_signal(self, value):
        self.signals.append(value)

    def wait(self, timeout):
        self.code = 130


class SecretInput:
    def __init__(self):
        self.written, self.closed = '', False
    def write(self, value): self.written += value
    def close(self): self.closed = True


@pytest.fixture
def session(tmp_path):
    return Session(tmp_path, tmp_path / 'data', '192.168.1.2', popen=Job)


@pytest.mark.parametrize('message', [
    {'action': 'upload'}, {'action': 'serve'}, {'action': 'list', 'command': 'sh'},
    {'action': ['list']},
    {'action': 'export', 'episodes': ['../../etc'], 'name': 'ok'},
    {'action': 'export', 'episodes': [], 'name': 'ok'},
    {'action': 'export', 'episodes': ['lekiwi.a/episode.b.partial'], 'name': 'ok'},
    {'action': 'export', 'episodes': ['lekiwi.a/episode.b'] * 2, 'name': 'ok'},
    {'action': 'export', 'episodes': ['lekiwi.a/episode.b'], 'name': '../bad'},
    {'action': 'export', 'episodes': ['lekiwi.a/episode.b'], 'name': 'ok', 'success_only': 'yes'},
    {'action': 'inspect', 'name': '--help'}, {'action': 'inspect', 'name': 'x; touch /tmp/x'},
])
def test_invalid_browser_requests_never_start_process(session, message):
    with pytest.raises(ValueError):
        session.dispatch({'op': 'dataset', **message})
    assert not session.datasets.jobs


def test_multiple_episodes_use_existing_cli():
    assert dataset_command({'op': 'dataset', 'action': 'export',
        'episodes': ['lekiwi.a/episode.b', 'lekiwi.c/episode.d'], 'name': 'basket_01',
        'success_only': True}) == ['export', '--name', 'basket_01',
            '--episode', 'lekiwi.a/episode.b', '--episode', 'lekiwi.c/episode.d', '--success-only']


def test_upload_token_uses_anonymous_stdin_and_never_command_or_environment(session):
    secret = 'hf_test_token_123456789'
    started = session.dispatch({'op': 'dataset', 'action': 'upload', 'name': 'sample',
                                'repo_id': 'student/lekiwi-data', 'private': True, 'token': secret})
    job = session.datasets.jobs[started['job_id']]
    assert job.process.command[-6:] == ['upload', '--name', 'sample', '--repo-id',
                                        'student/lekiwi-data', '--private']
    assert secret not in repr(job.process.command)
    assert secret not in repr(job.process.options['env'])
    assert job.process.stdin.written == secret + '\n' and job.process.stdin.closed
    assert job.process.options['env']['HF_HUB_DISABLE_IMPLICIT_TOKEN'] == '1'


@pytest.mark.parametrize('flag,private', [('--private', True), ('--public', False)])
def test_upload_cli_reaches_server_with_selected_visibility(session, monkeypatch, capsys, flag, private):
    from tools.web_classroom import lesson
    secret = 'hf_test_token_123456789'
    monkeypatch.setattr(lesson.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(lesson.getpass, 'getpass', lambda _: secret)

    def request(message):
        state = session.dispatch(message)
        if message.get('action') == 'upload':
            job = session.datasets.jobs[state['job_id']]
            job.output.write_text(json.dumps({'private': private, 'url': 'https://huggingface.co/datasets/student/sample'}))
            job.process.code = 0
            return session.datasets.status()
        return state

    monkeypatch.setattr(lesson, 'request', request)
    lesson.main(['dataset', 'upload', '--name', 'sample', '--repo-id', 'student/sample', flag])
    job = session.datasets.jobs[session.datasets.latest]
    assert job.process.command[-1] == flag
    assert job.process.stdin.written == secret + '\n' and job.process.stdin.closed
    output = capsys.readouterr()
    assert 'LEKIWI_DATASET_JOB result=PASS' in output.out
    assert secret not in output.out + output.err


def test_long_job_is_nonblocking_and_does_not_replace_simulation(session):
    started = session.dispatch({'op': 'dataset', 'action': 'list'})
    assert started['state'] == 'RUNNING'
    assert session.dispatch({'op': 'status'})['state'] == 'IDLE'
    assert session.dispatch({'op': 'stop'})['state'] == 'IDLE'
    job = session.datasets.jobs[started['job_id']]
    assert job.process.signals == []
    assert job.process.command[-2:] == ['dataset', 'list']
    assert job.process.options['env']['LEKIWI_DATA_DIR'] == str(session.data)
    assert job.process.options['env']['LEKIWI_CLASSROOM_SESSION']
    assert job.process.options['stdin'] == subprocess.DEVNULL
    with pytest.raises(RuntimeError, match='진행 중'):
        session.dispatch({'op': 'dataset', 'action': 'list'})
    # 새 브라우저 터미널에서 같은 작업을 확인해도 다시 실행되지 않습니다.
    assert session.dispatch({'op': 'dataset', 'action': 'status'})['job_id'] == started['job_id']
    job.output.write_text(json.dumps({'episodes': [], 'datasets': []}))
    job.process.code = 0
    finished = session.dispatch({'op': 'dataset', 'action': 'status', 'job_id': started['job_id']})
    assert finished['state'] == 'SUCCEEDED' and finished['result']['episodes'] == []
    session.dispatch({'op': 'dataset', 'action': 'list'})
    assert session.dispatch({'op': 'dataset', 'action': 'status', 'job_id': started['job_id']}) == finished


@pytest.mark.parametrize('code,output', [(1, '{}'), (0, 'not JSON'), (0, '[]')])
def test_failure_is_not_reported_as_success(session, code, output):
    state = session.dispatch({'op': 'dataset', 'action': 'inspect', 'name': 'example'})
    job = session.datasets.jobs[state['job_id']]
    job.output.write_text(output)
    job.log.write_text('디스크 공간을 확인하세요.\n')
    job.process.code = code
    state = session.dispatch({'op': 'dataset', 'action': 'status'})
    assert state['state'] == 'FAILED' and 'error' in state
    assert '디스크' in session.dispatch({'op': 'dataset', 'action': 'logs'})['log']


def test_workspace_shutdown_stops_only_owned_dataset_job(session):
    state = session.dispatch({'op': 'dataset', 'action': 'list'})
    job = session.datasets.jobs[state['job_id']]
    session.datasets.close()
    assert job.process.signals == [signal.SIGINT]
    assert session.datasets.status()['state'] == 'FAILED'


def test_invalid_status_ids_and_options_rejected(session):
    for message in ({'action': 'status', 'job_id': '../other'},
                    {'action': 'logs', 'command': 'anything'}):
        with pytest.raises(ValueError):
            session.dispatch({'op': 'dataset', **message})


def test_cli_wait_reports_error_and_ctrl_c_only_detaches(monkeypatch, capsys):
    from tools.web_classroom import lesson
    messages = []
    def request(message):
        messages.append(message)
        if len(messages) == 1:
            return {'state': 'RUNNING', 'job_id': 'dataset.test', 'elapsed_seconds': 0}
        return {'state': 'FAILED', 'job_id': 'dataset.test', 'error': 'conversion failed'}
    monkeypatch.setattr(lesson, 'request', request)
    monkeypatch.setattr(lesson.time, 'sleep', lambda _: None)
    with pytest.raises(RuntimeError, match='conversion failed'):
        lesson.main(['dataset', 'export', '--episode', 'lekiwi.a/episode.b', '--name', 'sample'])
    assert messages[0]['episodes'] == ['lekiwi.a/episode.b']
    messages.clear()
    def interrupt(_):
        raise KeyboardInterrupt
    monkeypatch.setattr(lesson.time, 'sleep', interrupt)
    lesson.main(['dataset', 'list'])
    assert len(messages) == 1
    assert '계속' in capsys.readouterr().out


def test_browser_cli_over_real_socket_and_server_subprocess(tmp_path):
    # Docker 대신 작은 실행기를 사용하되 CLI → 소켓 → 실제 자식 → JSON 결과 경로는 그대로 검사합니다.
    script = tmp_path / 'lekiwi'
    script.write_text('#!/usr/bin/python3\nimport json, sys, time\n'
                      'assert sys.argv[1:] == ["dataset", "list"]\n'
                      'time.sleep(0.1)\nprint(json.dumps({"episodes": [], "datasets": []}))\n')
    script.chmod(0o755)
    session = Session(tmp_path, tmp_path / 'data', '192.168.1.2')
    path = tmp_path / 'control.sock'
    server = ControlServer(path, session)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        import os
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] /
            'tools/web_classroom/lesson.py'), 'dataset', 'list'],
            env=dict(os.environ, LEKIWI_CONTROL_SOCKET=str(path)), text=True, capture_output=True, timeout=10)
        assert result.returncode == 0, result.stderr
        assert 'result=PASS' in result.stdout and '"episodes": []' in result.stdout
        assert len(session.datasets.jobs) == 1
    finally:
        server.shutdown()
        worker.join(3)
        server.server_close()
        session.datasets.close()


def student_script(name):
    return runpy.run_path(str(Path(__file__).resolve().parents[1] /
        'isaacsim_basic/06_lekiwi_dataset/experiments' / name), run_name='student_test')


def test_student_conversion_uses_saved_python_settings_without_cli_arguments(monkeypatch):
    student = student_script('03_convert_dataset.py')
    settings = student['main'].__globals__
    calls = []
    def run(command):
        calls.append(command)
        return type('Result', (), {'returncode': 0})()
    monkeypatch.setattr(settings['subprocess'], 'run', run)
    with pytest.raises(SystemExit, match='episode_ids'):
        student['main']()
    assert calls == []
    settings.update(episode_ids=['lekiwi.one/episode.first', 'lekiwi.two/episode.second'],
                    dataset_name='student_pickup', success_only=True)
    with pytest.raises(SystemExit) as result:
        student['main']()
    assert result.value.code == 0
    assert calls == [[str(settings['launcher']), 'dataset', 'export', '--name', 'student_pickup',
                     '--episode', 'lekiwi.one/episode.first', '--episode', 'lekiwi.two/episode.second',
                     '--success-only']]


@pytest.mark.parametrize('file,action', [('02_dataset_list.py', 'list'), ('04_inspect_dataset.py', 'inspect')])
def test_student_scripts_forward_errors_and_do_not_start_gpu(monkeypatch, file, action):
    student = student_script(file)
    settings = student['main'].__globals__
    def run(command):
        assert command[:3] == [str(settings['launcher']), 'dataset', action]
        return type('Result', (), {'returncode': 1})()
    monkeypatch.setattr(settings['subprocess'], 'run', run)
    with pytest.raises(SystemExit) as result:
        student['main']()
    assert result.value.code == 1


def test_student_dataset_script_is_not_started_as_isaac_scene():
    from tools.web_classroom.control import selection
    with pytest.raises(ValueError, match='python3 03_convert_dataset.py'):
        selection({'script': '06_lekiwi_dataset/experiments/03_convert_dataset.py'},
                  Path(__file__).resolve().parents[1])


def test_student_upload_uses_saved_settings_and_local_launcher(monkeypatch):
    student = student_script('05_upload_dataset.py')
    settings = student['main'].__globals__
    calls = []
    monkeypatch.setattr(settings['subprocess'], 'run',
                        lambda command: calls.append(command) or type('Result', (), {'returncode': 0})())
    with pytest.raises(SystemExit, match='account'):
        student['main']()
    settings.update(dataset_name='sample', repo_id='student/lekiwi-data', private=True)
    with pytest.raises(SystemExit) as result:
        student['main']()
    assert result.value.code == 0
    assert calls == [[str(settings['launcher']), 'dataset', 'upload', '--name', 'sample', '--repo-id',
                      'student/lekiwi-data', '--private']]
