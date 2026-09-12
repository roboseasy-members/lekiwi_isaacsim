"""브라우저 ACT 학습 작업. 화면 대기와 서버 학습 프로세스의 수명을 분리합니다."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import uuid

from tools.act.options import cli_args, contained, validate
from tools.web_classroom.datasets import tail


class TrainingJobs:
    def __init__(self, root, data, popen=subprocess.Popen):
        self.root, self.data, self.popen = root, data, popen
        self.jobs, self.latest = {}, None

    def job(self, identity=None):
        identity = identity or self.latest
        if identity is None:
            return None
        if not isinstance(identity, str) or identity not in self.jobs:
            raise ValueError('이 편집기에서 만든 학습 작업 ID가 아닙니다.')
        return self.jobs[identity]

    def status(self, identity=None):
        job = self.job(identity)
        if job is None:
            return {'state': 'IDLE'}
        if job.get('finished'):
            return job['finished']
        state = {'job_id': job['directory'].name, 'run_name': job['options']['run_name'],
                 'state': 'RUNNING', 'elapsed_seconds': round(time.monotonic() - job['started'], 1)}
        code = job['process'].poll()
        if code is None:
            return state
        state.update(state='STOPPED' if job.get('stopped') else 'FAILED', exit_code=code)
        if code == 0 and not job.get('stopped'):
            try:
                path = contained(self.data / 'outputs', job['options']['run_name'], 'training_result.json')
                result = json.loads(path.read_text())
                if result.get('result') != 'PASS' or result.get('steps') != job['options']['steps']:
                    raise ValueError('학습 완료 결과가 요청과 일치하지 않습니다.')
                state.update(state='SUCCEEDED', result=result)
            except (OSError, ValueError) as exc:
                state['error'] = str(exc)
        elif not job.get('stopped'):
            state['error'] = '학습이 중단됐습니다. lesson train logs로 원인을 확인하세요.'
        job['finished'] = state
        (job['directory'] / 'status.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return state

    def start(self, message):
        options = validate({k: v for k, v in message.items() if k not in ('op', 'action')}, 'train')
        if self.status()['state'] == 'RUNNING':
            raise RuntimeError('학습이 실행 중입니다. lesson train status로 확인하세요.')
        if contained(self.data / 'outputs', options['run_name']).exists():
            raise ValueError('기존 학습 결과가 있습니다. 새 run_name을 사용하세요.')
        parent = self.data / 'web_classroom/training'
        parent.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix='train.', dir=parent))
        with (directory / 'run.log').open('w') as log:
            process = self.popen([str(self.root / 'lekiwi'), 'act', 'train', *cli_args(options)],
                cwd=self.root, env=dict(os.environ, LEKIWI_DATA_DIR=str(self.data),
                    LEKIWI_CLASSROOM_SESSION=uuid.uuid4().hex), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=False)
        self.latest = directory.name
        self.jobs[self.latest] = dict(process=process, directory=directory, options=options, started=time.monotonic())
        return self.status()

    def stop(self, identity=None):
        job = self.job(identity)
        if job and job['process'].poll() is None:
            job['stopped'] = True
            job['process'].send_signal(signal.SIGINT)
            try:
                job['process'].wait(timeout=50)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError('학습 종료가 지연됩니다. 로그를 확인하세요.') from exc
        return self.status(identity)

    def dispatch(self, message):
        action = message.get('action')
        if action == 'start':
            return self.start(message)
        if action not in ('status', 'logs', 'stop') or set(message) - {'op', 'action', 'job_id'}:
            raise ValueError('학습 start·status·logs·stop만 지원합니다.')
        job = self.job(message.get('job_id'))
        if action == 'logs':
            return {'log': tail(job['directory'] / 'run.log') if job else ''}
        if action == 'stop':
            return self.stop(message.get('job_id'))
        return self.status(message.get('job_id'))

    def close(self):
        for identity in self.jobs:
            self.stop(identity)
