"""브라우저가 요청한 로컬 데이터셋 작업을 서버의 기존 LeRobot 실행기로 연결합니다."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
import uuid


def dataset_command(message):
    action = message.get('action')
    allowed = {'list': set(), 'export': {'episodes', 'name', 'success_only'}, 'inspect': {'name'},
               'upload': {'name', 'repo_id', 'private', 'token'}}
    if not isinstance(action, str) or action not in allowed or set(message) - {'op', 'action'} - allowed[action]:
        raise ValueError('데이터 목록·변환·검사·업로드 옵션만 사용할 수 있습니다.')
    args = [action]
    if action != 'list':
        name = message.get('name')
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', name):
            raise ValueError('데이터셋 이름은 영문·숫자로 시작하고 영문·숫자·점·밑줄·하이픈만 사용하세요.')
        args += ['--name', name]
    if action == 'export':
        episodes = message.get('episodes')
        if (not isinstance(episodes, list) or not episodes or
                any(not isinstance(e, str) or not re.fullmatch(r'lekiwi\.[\w-]+/episode\.[\w-]+', e)
                    or e.endswith('.partial') for e in episodes) or len(set(episodes)) != len(episodes)):
            raise ValueError('완료된 에피소드 ID를 중복 없이 하나 이상 지정하세요.')
        if type(message.get('success_only', False)) is not bool:
            raise ValueError('성공 에피소드 선택 값이 올바르지 않습니다.')
        for episode in episodes:
            args += ['--episode', episode]
        if message.get('success_only'):
            args.append('--success-only')
    if action == 'upload':
        repo_id, private, token = (message.get(key) for key in ('repo_id', 'private', 'token'))
        if not isinstance(repo_id, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}', repo_id):
            raise ValueError('Hugging Face 저장소는 계정명/데이터셋명 형식으로 적으세요.')
        if type(private) is not bool:
            raise ValueError('공개 범위는 True 또는 False로 설정하세요.')
        if not isinstance(token, str) or not 16 <= len(token) <= 512 or not re.fullmatch(r'hf_[A-Za-z0-9_-]+', token):
            raise ValueError('Hugging Face 쓰기 토큰 형식을 확인하세요.')
        args += ['--repo-id', repo_id, '--private' if private else '--public']
    return args


def tail(path):
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size - 20_000))
        return stream.read().decode(errors='replace')


@dataclass
class Job:
    process: object
    directory: Path
    action: str
    started: float
    finished: dict | None = None

    @property
    def output(self):
        return self.directory / 'output.json'

    @property
    def log(self):
        return self.directory / 'run.log'

    def status(self):
        if self.finished is not None:
            return self.finished
        code = self.process.poll()
        state = {'job_id': self.directory.name, 'operation': self.action,
                 'state': 'RUNNING', 'elapsed_seconds': round(time.monotonic() - self.started, 1)}
        if code is None:
            return state
        state.update(state='FAILED', exit_code=code)
        try:
            if code:
                raise ValueError(f'데이터셋 작업이 종료 코드 {code}로 중단됐습니다. lesson dataset logs로 원인을 확인하세요.')
            if self.output.stat().st_size > 4_000_000:
                raise ValueError('결과가 너무 큽니다. 서버의 작업 로그를 확인하세요.')
            # 최초 이미지 준비 메시지 이후 CLI가 출력한 마지막 JSON 객체를 읽습니다.
            text = self.output.read_text().strip()
            offset = text.rfind('\n{')
            result = json.loads(text[offset + 1:] if offset >= 0 else text)
            if not isinstance(result, dict):
                raise ValueError('데이터셋 실행기가 완료 결과를 반환하지 않았습니다.')
            state.update(state='SUCCEEDED', result=result)
        except (OSError, ValueError) as exc:
            state['error'] = str(exc)
        self.finished = state
        (self.directory / 'status.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return state


class DatasetJobs:
    def __init__(self, root, data, popen=subprocess.Popen):
        self.root, self.data, self.popen = root, data, popen
        self.jobs = {}
        self.latest = None

    def start(self, message):
        args = dataset_command(message)
        token = message.get('token') if message.get('action') == 'upload' else None
        if self.latest and self.status()['state'] == 'RUNNING':
            raise RuntimeError('데이터셋 작업이 진행 중입니다. lesson dataset status로 확인하세요.')
        parent = self.data / 'web_classroom' / 'datasets'
        parent.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix='dataset.', dir=parent))
        with (directory / 'output.json').open('w') as output, (directory / 'run.log').open('w') as log:
            process = self.popen([str(self.root / 'lekiwi'), 'dataset', *args], cwd=self.root,
                env=dict(os.environ, LEKIWI_DATA_DIR=str(self.data),
                         LEKIWI_CLASSROOM_SESSION=uuid.uuid4().hex, PYTHONUNBUFFERED='1',
                         HF_HUB_DISABLE_IMPLICIT_TOKEN='1', HF_HUB_DISABLE_TELEMETRY='1'),
                stdin=subprocess.PIPE if token is not None else subprocess.DEVNULL,
                stdout=output, stderr=log, start_new_session=False, text=True)
        if token is not None:
            try:
                process.stdin.write(token + '\n')
                process.stdin.close()
            except (BrokenPipeError, OSError):
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
                raise RuntimeError('업로드 실행기에 토큰을 전달하지 못했습니다.') from None
            finally:
                token = None
        self.latest = directory.name
        self.jobs[self.latest] = Job(process, directory, args[0], time.monotonic())
        return self.status()

    def job(self, identity=None):
        identity = identity or self.latest
        if identity is None:
            return None
        if not isinstance(identity, str) or identity not in self.jobs:
            raise ValueError('이 편집기 실행에서 만든 데이터셋 작업 ID가 아닙니다.')
        return self.jobs[identity]

    def status(self, identity=None):
        job = self.job(identity)
        return job.status() if job else {'state': 'IDLE'}

    def dispatch(self, message):
        action = message.get('action')
        if action in ('status', 'logs'):
            if set(message) - {'op', 'action', 'job_id'}:
                raise ValueError('지원하지 않는 작업 조회 옵션입니다.')
            job = self.job(message.get('job_id'))
            if action == 'logs':
                return {'log': tail(job.log) + '\n' + tail(job.output) if job else ''}
            return self.status(message.get('job_id'))
        return self.start(message)

    def close(self):
        # Ctrl+C로 닫힌 브라우저 터미널과 달리, 서버 편집기 종료 시에는 소유 작업을 정리합니다.
        for job in self.jobs.values():
            if job.process.poll() is None:
                job.process.send_signal(signal.SIGINT)
                try:
                    job.process.wait(timeout=50)
                except subprocess.TimeoutExpired:
                    raise RuntimeError('데이터셋 작업 종료가 지연됩니다. 서버의 작업 로그를 확인하세요.')
            job.status()
