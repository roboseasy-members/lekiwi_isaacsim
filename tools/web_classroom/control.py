"""같은 사용자의 Unix 소켓으로 실습과 로컬 데이터셋 작업을 받습니다."""
import json
import os
from pathlib import Path
import signal
import socketserver
import subprocess
import sys
import tempfile
import threading

from tools.web_classroom.datasets import DatasetJobs

CHAPTERS = ("01_object_physics", "02_robot_joints", "03_robot_cameras",
            "04_teleoperation", "05_data_recording", "06_lekiwi_dataset")
MAX_REQUEST = 8192


def selection(message, root):
    if set(message) - {"op", "chapter", "experiment", "script", "teleop", "phrase"}:
        raise ValueError("지원하지 않는 실행 옵션입니다.")
    chapter, experiment, script = (message.get(k) for k in ("chapter", "experiment", "script"))
    if sum(v is not None for v in (chapter, experiment, script)) != 1:
        raise ValueError("장·실험·학생 파일 중 하나만 지정하세요.")
    for value in (chapter, experiment):
        if value is not None and (type(value) is not int or value not in range(1, 7)):
            raise ValueError("장과 실험 번호는 1~6입니다.")
    if script is not None:
        if not isinstance(script, str):
            raise ValueError("학생 파일 경로가 올바르지 않습니다.")
        prefix = "/workspace/isaacsim_basic/"
        relative = script[len(prefix):] if script.startswith(prefix) else script
        path = (root / "isaacsim_basic" / relative).resolve()
        allowed = [root / "isaacsim_basic" / name / "experiments" for name in CHAPTERS]
        if path.parent not in allowed or path.suffix != ".py" or not path.is_file():
            raise ValueError("각 장 experiments 폴더의 Python 파일만 실행할 수 있습니다.")
        if path.parent == allowed[-1] and path.name in (
                '02_dataset_list.py', '03_convert_dataset.py', '04_inspect_dataset.py',
                '05_upload_dataset.py'):
            raise ValueError(f'이 파일은 브라우저 터미널에서 python3 {path.name}로 실행하세요. Isaac 실습을 시작하지 않았습니다.')
        compile(path.read_text(), str(path), "exec")
        script = str(path.relative_to(root / "isaacsim_basic"))
    teleop = message.get("teleop", False)
    if type(teleop) is not bool or (teleop and chapter != 6):
        raise ValueError("리더 입력은 6장에서만 사용할 수 있습니다.")
    phrase = message.get("phrase")
    if teleop and (not isinstance(phrase, str) or not 12 <= len(phrase) <= 512):
        raise ValueError("리더 접속 문구는 12~512자입니다.")
    if not teleop and phrase is not None:
        raise ValueError("리더 입력을 사용하지 않는 실습입니다.")
    return dict(chapter=chapter or 1, experiment=experiment, script=script, teleop=teleop, phrase=phrase)


class Session:
    def __init__(self, root, data, host, popen=subprocess.Popen):
        self.root, self.data, self.host, self.popen = root.resolve(), data, host, popen
        self.process = None
        self.log = None
        self.ready = False
        self.label = None
        self.stopped = False
        self.lock = threading.Lock()
        self.datasets = DatasetJobs(self.root, data, popen)

    def tail(self):
        if not self.log or not self.log.exists():
            return ""
        with self.log.open("rb") as stream:
            stream.seek(max(0, self.log.stat().st_size - 24_000))
            return stream.read().decode(errors="replace")

    def status(self):
        if self.process is None:
            return {"state": "IDLE", "server": self.host}
        self.ready |= any(m in self.tail() for m in ("STUDENT_SCRIPT ready", "LEKIWI_DRIVE result=READY"))
        code = self.process.poll()
        state = ("READY" if self.ready else "STARTING") if code is None else (
            "STOPPED" if self.stopped or code == 0 else "FAILED")
        return {"state": state, "server": self.host, "selection": self.label, "exit_code": code}

    def start(self, message):
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError("현재 실습이 실행 중입니다. 저장 후 lesson stop으로 종료하세요.")
        options = selection(message, self.root)
        options["host"] = self.host
        parent = self.data / "web_classroom" / "sessions"
        parent.mkdir(parents=True, exist_ok=True)
        self.log = Path(tempfile.mkdtemp(prefix="lesson.", dir=parent)) / "run.log"
        self.ready = self.stopped = False
        self.label = options["script"] or (f"실험 {options['experiment']}" if options["experiment"] else f"{options['chapter']}장")
        with self.log.open("w") as output:
            # 같은 제어 터미널을 유지하여 이미 확인한 sudo 자격을 사용합니다.
            self.process = self.popen([sys.executable, "-B", "-u", str(self.root / "tools/web_classroom/runner.py")],
                cwd=self.root, env=dict(os.environ, LEKIWI_DATA_DIR=str(self.data)),
                stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT, start_new_session=False)
        self.process.stdin.write(json.dumps(options).encode() + b"\n")
        self.process.stdin.close()
        return self.status()

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=50)
            except subprocess.TimeoutExpired:
                raise RuntimeError("실습 종료가 지연됩니다. 서버 로그를 확인하세요. 새 실습은 시작하지 않았습니다.")
            self.stopped = True
        return self.status()

    def dispatch(self, message):
        if not isinstance(message, dict):
            raise ValueError("JSON 객체가 필요합니다.")
        with self.lock:
            op = message.get("op")
            if op == "run":
                return self.start(message)
            if op == "dataset":
                return self.datasets.dispatch(message)
            if set(message) != {"op"}:
                raise ValueError("지원하지 않는 요청입니다.")
            if op == "status":
                return self.status()
            if op == "logs":
                return {"log": self.tail()}
            if op == "stop":
                return self.stop()
            raise ValueError("실습 실행·종료·상태·로그와 데이터셋 작업만 지원합니다.")


class ControlServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def __init__(self, path, session):
        self.session = session
        super().__init__(str(path), Handler)
        Path(path).chmod(0o600)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        try:
            data = self.rfile.readline(MAX_REQUEST + 1)
            if len(data) > MAX_REQUEST or not data.endswith(b"\n"):
                raise ValueError("요청이 너무 크거나 완성되지 않았습니다.")
            result = {"ok": True, "result": self.server.session.dispatch(json.loads(data))}
        except (OSError, ValueError, RuntimeError, SyntaxError) as exc:
            result = {"ok": False, "error": str(exc)}
        try:
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode() + b"\n")
        except OSError:
            pass  # 브라우저 터미널이 닫혀도 서버의 실습 수명은 유지합니다.
