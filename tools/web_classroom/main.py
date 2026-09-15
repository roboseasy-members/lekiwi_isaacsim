"""데스크탑의 브라우저 편집기와 실습 제어를 한 터미널에서 유지합니다."""
import fcntl
import os
from pathlib import Path
import pwd
import shlex
import subprocess
import tempfile
import threading
import time
import urllib.request
import uuid

from tools.web_classroom.control import CHAPTERS, ControlServer, Session

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "lekiwi-editor:0.1.0"


def docker_command():
    if os.geteuid() == 0:
        raise RuntimeError("전체 실행기를 sudo로 실행하지 마세요. 필요한 Docker 명령만 인증합니다.")
    if os.environ.get("DOCKER_HOST") or os.environ.get("DOCKER_CONTEXT"):
        raise RuntimeError("편집기는 이 PC의 기본 Docker Engine을 사용합니다.")
    context = subprocess.check_output(["docker", "context", "show"], text=True).strip()
    if context != "default":
        raise RuntimeError("편집기는 기본 Docker context에서 실행하세요.")
    endpoint = subprocess.check_output(["docker", "context", "inspect", "default", "--format",
                                       "{{.Endpoints.docker.Host}}"], text=True).strip()
    if endpoint != "unix:///var/run/docker.sock":
        raise RuntimeError("기본 Docker context가 로컬 시스템 Engine을 가리키지 않습니다.")
    if os.environ.get("LEKIWI_DOCKER_SUDO") != "1" and subprocess.run(
            ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        return ["docker"]
    subprocess.run(["sudo", "-v"], check=True)
    subprocess.run(["sudo", "-n", "docker", "info"], check=True, stdout=subprocess.DEVNULL)
    os.environ["LEKIWI_DOCKER_SUDO"] = "1"
    return ["sudo", "-n", "docker"]


def build_editor(dock=None):
    dock = dock or docker_command()
    subprocess.run(dock + ["build", "-t", os.environ.get("LEKIWI_EDITOR_IMAGE", IMAGE),
                          "-f", str(ROOT / "docker/Dockerfile.editor"), str(ROOT)], check=True)


def editor_command(dock, root, data, runtime, host, port, identity):
    name = f"lekiwi-editor-{os.getuid()}-{identity[:8]}"
    args = dock + ["run", "--rm", "--init", "--name", name,
        "--label", f"lekiwi.editor.session={identity}", "--user", f"{os.getuid()}:{os.getgid()}",
        "--publish", f"127.0.0.1:{port}:8080",
        "--mount", f"type=bind,src={data / 'web_classroom/home'},dst=/home/coder",
        "--mount", f"type=bind,src={runtime},dst=/run/lekiwi,readonly",
        "--mount", f"type=bind,src={root / 'isaacsim_basic'},dst=/workspace/isaacsim_basic,readonly",
        "--mount", f"type=bind,src={root / 'docs'},dst=/workspace/docs,readonly",
        "--mount", f"type=bind,src={root / 'README.md'},dst=/workspace/README.md,readonly",
        "--mount", f"type=bind,src={data / 'isaacsim_basic'},dst=/results/basic,readonly",
        "--mount", f"type=bind,src={data / 'recordings'},dst=/results/recordings,readonly",
        "--mount", f"type=bind,src={data / 'datasets'},dst=/results/datasets,readonly",
        "--mount", f"type=bind,src={data / 'outputs'},dst=/results/outputs,readonly"]
    for chapter in CHAPTERS:
        relative = f"isaacsim_basic/{chapter}/experiments"
        args += ["--mount", f"type=bind,src={root / relative},dst=/workspace/{relative}"]
    args.append(os.environ.get("LEKIWI_EDITOR_IMAGE", IMAGE))
    return name, args


def healthy(url):
    try:
        with urllib.request.urlopen(url + "/healthz", timeout=1) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def run_workspace(args):
    from tools.remote_classroom.main import stop_owned, check_stream_port
    from isaac_sim.remote_teleop import address
    host = address(args.host)
    if not 1024 <= args.port <= 65535:
        raise ValueError("편집기 포트는 1024~65535입니다.")
    if os.environ.get("ACCEPT_EULA") != "Y":
        raise RuntimeError("Isaac Sim 라이선스 동의 후 export ACCEPT_EULA=Y를 실행하세요.")
    check_stream_port("127.0.0.1", args.port)
    dock = docker_command()
    data = Path(os.environ.get("LEKIWI_DATA_DIR", ROOT / "data")).resolve()
    state = data / "web_classroom"
    for folder in (state / "home", data / "isaacsim_basic", data / "recordings", data / "datasets", data / "outputs"):
        folder.mkdir(parents=True, exist_ok=True)
    with (state / "workspace.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("이 데이터 폴더의 브라우저 수업이 이미 실행 중입니다.")
        if subprocess.run(dock + ["image", "inspect", os.environ.get("LEKIWI_EDITOR_IMAGE", IMAGE)],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            build_editor(dock)
        session = Session(ROOT, data, host)
        with tempfile.TemporaryDirectory(prefix=f"lekiwi-editor-{os.getuid()}-") as temporary:
            runtime = Path(temporary)
            controller = ControlServer(runtime / "control.sock", session)
            worker = threading.Thread(target=controller.serve_forever, daemon=True)
            worker.start()
            identity = uuid.uuid4().hex
            name, command = editor_command(dock, ROOT, data, runtime, host, args.port, identity)
            url = f"http://127.0.0.1:{args.port}"
            log_path = state / f"editor.{identity[:8]}.log"
            process = None
            try:
                with log_path.open("w") as log:
                    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                               stderr=subprocess.STDOUT, start_new_session=False)
                print(f"LEKIWI_WORKSPACE starting url={url} log={log_path}", flush=True)
                started = refreshed = time.monotonic()
                ready = False
                while process.poll() is None:
                    if not ready:
                        ready = healthy(url)
                        if ready:
                            print(f"LEKIWI_WORKSPACE ready url={url}", flush=True)
                            account = pwd.getpwuid(os.getuid()).pw_name
                            target = shlex.quote(f"{account}@{host}")
                            print("1. 본 노트북의 새 로컬 터미널에서 아래 명령을 그대로 실행하세요.", flush=True)
                            print(f"ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:{args.port}:127.0.0.1:{args.port} {target}", flush=True)
                            print(f"비밀번호를 물으면 서버 Ubuntu 계정({account})의 비밀번호를 입력하세요.", flush=True)
                            print(f"2. SSH 연결이 오류 없이 대기하면, 본 노트북 브라우저에서 {url} 을 여세요.", flush=True)
                            print("127.0.0.1은 본 노트북 자신을 뜻하므로 SSH 연결이 먼저 필요합니다. 수업 동안 두 터미널을 유지합니다.", flush=True)
                        elif time.monotonic() - started > 120:
                            raise RuntimeError(f"편집기가 2분 내 준비되지 않았습니다. {log_path}")
                    if dock[0] == "sudo" and time.monotonic() - refreshed >= 60:
                        # 실행기가 열린 동안만 같은 터미널의 이미 승인된 자격을 유지합니다.
                        subprocess.run(["sudo", "-n", "-v"], check=True)
                        refreshed = time.monotonic()
                    with session.lock:
                        session.status()
                    time.sleep(0.5)
                if process.returncode:
                    raise RuntimeError(f"편집기 종료 코드 {process.returncode}. {log_path}를 확인하세요.")
            finally:
                controller.shutdown()
                worker.join(timeout=3)
                controller.server_close()
                try:
                    with session.lock:
                        try:
                            session.stop()
                        finally:
                            try:
                                session.datasets.close()
                            finally:
                                session.training.close()
                finally:
                    if process is not None:
                        stop_owned(dock, name, "lekiwi.editor.session", identity)
                        process.wait(timeout=30)
                print("LEKIWI_WORKSPACE stopped", flush=True)
