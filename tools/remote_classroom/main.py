"""동일 LAN의 실습 서버와 Ubuntu 노트북 연결 도구."""
import argparse
import http.server
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "isaac_sim"))
from remote_teleop import PORT, Receiver, Sender, address, connection_key, receive_loop
from teleop_bridge import JOINTS


def docker():
    if os.environ.get("LEKIWI_DOCKER_SUDO") == "1":
        subprocess.run(["sudo", "-v"], check=True)
        return ["sudo", "docker"]
    return ["docker"]


def stop_owned(dock, name, label, identity):
    """정확한 실행 라벨이 있는 컨테이너만 정상 종료합니다."""
    result = subprocess.run(dock + ["inspect", "--format", "{{json .Config.Labels}}", name],
                            text=True, capture_output=True)
    if result.returncode:
        return False
    labels = json.loads(result.stdout)
    if not isinstance(labels, dict) or labels.get(label) != identity:
        return False
    subprocess.run(dock + ["stop", "--time", "10", name], check=True,
                   stdout=subprocess.DEVNULL)
    return True


def bundle(path):
    files = ["lekiwi", "tools/remote_classroom/main.py", "tools/so101_leader.py",
             "isaac_sim/remote_teleop.py", "isaac_sim/teleop_bridge.py",
             "docker/Dockerfile.leader", "docs/remote-classroom.md", ".dockerignore"]
    # 목록에 지정한 소스만 포함합니다. data·보정·인증정보·작업 백업은 제외합니다.
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".zip") as staged:
        with zipfile.ZipFile(staged.name, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in files:
                archive.write(ROOT / name, "lekiwi-client/" + name)
        # 내려받는 도중 파일 내용이 바뀌지 않도록 완성된 ZIP만 교체합니다.
        import shutil
        temporary = path.with_suffix(".ready.zip")
        shutil.copyfile(staged.name, temporary)
        os.replace(temporary, path)


def serve_bundle(host, path):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/client.zip":
                self.send_error(404)
                return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_):
            pass
    server = http.server.ThreadingHTTPServer((host, 8766), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"노트북 테스트 파일: http://{host}:8766/client.zip", flush=True)
    return server


def serve(args, *, control_key=None):
    host = address(args.host)
    if args.teleop and (args.chapter != 6 or args.script or args.experiment):
        raise ValueError("--teleop은 LeKiwi를 사용하는 --chapter 6에서만 지정하세요.")
    data = Path(os.environ.get("LEKIWI_DATA_DIR", ROOT / "data"))
    if not data.is_absolute():
        raise ValueError("LEKIWI_DATA_DIR must be absolute")
    # 이미지·sudo 준비는 접속 문구 입력과 수신 서버 개방보다 먼저 합니다.
    dock = docker()
    subprocess.run(dock + ["info"], check=True, stdout=subprocess.DEVNULL)
    active = subprocess.check_output(dock + ["ps", "-q", "--filter",
        f"label=com.docker.compose.project={os.environ.get('LEKIWI_PROJECT_NAME', 'lekiwi')}",
        "--filter", "label=com.docker.compose.service=sim"], text=True).strip()
    if active:
        raise RuntimeError("이미 실행 중인 실습을 정상 종료한 뒤 다시 실행하세요.")
    # 다른 체크아웃에서 열린 영상 서버도 덮어쓰지 않습니다.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 49100))
    key = (control_key if control_key is not None else connection_key()) if args.teleop else None
    if args.teleop and (not isinstance(key, bytes) or len(key) != 32):
        raise ValueError("리더 입력 인증 키가 올바르지 않습니다.")
    parent = data / "remote"
    parent.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="session.", dir=parent))
    session = directory.name
    state = directory / "leader.json"
    env = dict(os.environ, LEKIWI_DISPLAY_MODE="webrtc", LEKIWI_STREAM_HOST=host,
               LEKIWI_CLASSROOM_SESSION=uuid.uuid4().hex, LEKIWI_DATA_DIR=str(data))
    # 환경에 남아 있는 예전 로컬 리더 파일을 원격 실행에 사용하지 않습니다.
    env.pop("LEKIWI_TELEOP_STATE", None)
    env.pop("LEKIWI_TELEOP_SESSION", None)
    env.pop("LEKIWI_TELEOP_REMOTE", None)
    if args.teleop:
        env.update(LEKIWI_TELEOP_STATE=f"/data/remote/{session}/leader.json",
                   LEKIWI_TELEOP_SESSION=session, LEKIWI_TELEOP_REMOTE="1")
    command = [str(ROOT / "lekiwi"), "basic"]
    if args.script:
        command += ["--script", args.script]
    elif args.experiment:
        command += ["--experiment", str(args.experiment)]
    else:
        command += ["--chapter", str(args.chapter)]
    receiver = Receiver(state, session, key)
    stopped = threading.Event()
    errors = []
    process = None
    web = None
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((host, PORT))
        def receive():
            try:
                receive_loop(sock, receiver, stopped)
            except Exception as exc:
                errors.append(exc)
                stopped.set()
        worker = threading.Thread(target=receive, daemon=True)
        worker.start()
        try:
            if args.share_client:
                path = directory / "client.zip"
                bundle(path)
                web = serve_bundle(host, path)
            print(f"LEKIWI_REMOTE server={host} control_udp={PORT} chapter={args.chapter} teleop={args.teleop}", flush=True)
            print(f"Isaac 로그: {directory / 'sim.log'}", flush=True)
            print("Ctrl+C로 이 실습을 종료합니다. 화면 준비 후 노트북 클라이언트에서 접속하세요.", flush=True)
            with (directory / "sim.log").open("w") as log:
                process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL, start_new_session=False)
                cursor = 0
                ready = False
                while process.poll() is None:
                    if errors:
                        raise RuntimeError("리더 입력 수신기가 종료되었습니다") from errors[0]
                    with (directory / "sim.log").open() as output:
                        output.seek(cursor)
                        for line in output:
                            if any(marker in line for marker in ("LEKIWI_STREAM", "STUDENT_SCRIPT ready", "LEKIWI_DRIVE result=", "Traceback", "result=FAIL")):
                                print(line.rstrip(), flush=True)
                            if "STUDENT_SCRIPT ready" in line or "LEKIWI_DRIVE result=READY" in line:
                                ready = True
                        cursor = output.tell()
                    time.sleep(0.25)
                if process.returncode != 0:
                    raise RuntimeError(f"Isaac 종료 코드 {process.returncode}. {directory / 'sim.log'}를 확인하세요.")
                if not ready:
                    raise RuntimeError(f"실습 준비를 확인하지 못했습니다. {directory / 'sim.log'}를 확인하세요.")
        finally:
            stopped.set()
            worker.join(timeout=2)
            if web:
                web.shutdown()
                web.server_close()
            if process is not None:
                # 이 실행의 세션 라벨과 일치하는 컨테이너만 종료합니다.
                name = os.environ.get("LEKIWI_PROJECT_NAME", "lekiwi") + "-sim"
                for _ in range(30):
                    if stop_owned(dock, name, "lekiwi.classroom.session", env["LEKIWI_CLASSROOM_SESSION"]):
                        break
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                else:
                    process.terminate()
                if process.poll() is None:
                    try:
                        process.wait(timeout=35)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(timeout=10)
            print(f"LEKIWI_REMOTE samples={receiver.accepted} rejected={receiver.rejected} max_roundtrip_ms={receiver.max_rtt_ms:.1f}", flush=True)


def check(host):
    host = address(host)
    results = {}
    try:
        with socket.create_connection((host, 49100), timeout=3):
            results["stream_tcp"] = "PASS"
    except OSError as exc:
        results["stream_tcp"] = f"FAIL: {exc}"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(3)
            sock.connect((host, PORT))
            sock.send(b"LEKIWI_LAN_CHECK_V1")
            results["control_udp"] = "PASS" if sock.recv(128) == b"LEKIWI_LAN_OK_V1" else "FAIL"
    except OSError as exc:
        results["control_udp"] = f"FAIL: {exc}"
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("이 검사는 영상 수신 성공을 뜻하지 않습니다. WebRTC 클라이언트에서 화면도 확인하세요.")
    return 0 if all(value == "PASS" for value in results.values()) else 1


def demo(args):
    sender = Sender(args.host, connection_key())
    count = 0
    started = time.monotonic()
    try:
        # USB를 열지 않고 홈 자세에 가까운 일정한 값으로 통신만 검사합니다.
        values = dict.fromkeys((f"{name}.pos" for name in JOINTS), 0.0)
        while time.monotonic() - started < args.seconds:
            tick = time.monotonic()
            count += bool(sender.sample(lambda: dict(values)))
            time.sleep(max(0, 1 / 30 - (time.monotonic() - tick)))
    finally:
        sender.close()
    print(f"LEKIWI_REMOTE_DEMO accepted={count} result={'PASS' if count else 'FAIL'}")
    return 0 if count else 1


def setup_client():
    dock = docker()
    image = os.environ.get("LEKIWI_LEADER_IMAGE", "lekiwi-leader:0.1.0")
    subprocess.run(dock + ["build", "-t", image, "-f", str(ROOT / "docker/Dockerfile.leader"), str(ROOT)], check=True)


def leader(args):
    if not sys.stdin.isatty():
        raise RuntimeError("리더암 연결에는 대화형 터미널이 필요합니다.")
    port = Path(args.port).resolve()
    import re
    if not re.fullmatch(r"/dev/tty(?:ACM|USB)\d+", str(port)) or not port.is_char_device():
        raise ValueError("실제 리더암의 /dev/serial/by-id/... 경로를 지정하세요.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.id):
        raise ValueError("id에는 영문, 숫자, 밑줄, 하이픈만 사용하세요.")
    data = Path(os.environ.get("LEKIWI_DATA_DIR", ROOT / "data")).resolve()
    data.mkdir(parents=True, exist_ok=True)
    dock = docker()
    image = os.environ.get("LEKIWI_LEADER_IMAGE", "lekiwi-leader:0.1.0")
    subprocess.run(dock + ["image", "inspect", image], check=True, stdout=subprocess.DEVNULL)
    args_to_send = ["--id", args.id]
    if args.command == "calibrate":
        args_to_send += ["--calibrate-only"]
    else:
        args_to_send += ["--remote-host", address(args.host)]
    # 기존 로컬 teleop과 같은 장치 잠금으로 중복 연결을 막습니다.
    import fcntl
    lock_dir = Path(f"/tmp/lekiwi-device-locks-{os.getuid()}")
    lock_dir.mkdir(mode=0o700, exist_ok=True)
    if lock_dir.is_symlink() or lock_dir.stat().st_uid != os.getuid():
        raise ValueError("Unsafe device lock directory")
    device = port.stat()
    lock_path = lock_dir / f"{os.major(device.st_rdev):x}-{os.minor(device.st_rdev):x}.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        identity = uuid.uuid4().hex
        name = f"lekiwi-remote-leader-{os.getuid()}-{identity[:8]}"
        process = subprocess.Popen(dock + ["run", "--rm", "-it", "--init", "--network", "host",
            "--user", f"{os.getuid()}:{os.getgid()}", "--group-add", str(device.st_gid),
            "--device", f"{port}:/dev/so101:rw", "-v", f"{data}:/data", "-e", "HOME=/data/home/leader",
            "--name", name, "--label", f"lekiwi.remote.leader={identity}", image] + args_to_send)
        try:
            result = process.wait()
            if result:
                raise RuntimeError(f"리더암 프로그램 종료 코드: {result}")
        finally:
            for _ in range(30):
                if stop_owned(dock, name, "lekiwi.remote.leader", identity):
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    workspace = commands.add_parser("workspace", help="데스크탑: 브라우저 코드 편집기와 실습 실행 연결")
    workspace.add_argument("--host", required=True, type=address)
    workspace.add_argument("--port", type=int, default=8080)
    workspace.add_argument("--password-stdin", action="store_true", help="자동 검사: 비밀번호를 표준 입력으로 전달")
    commands.add_parser("setup-editor", help="데스크탑: 브라우저 편집기 이미지 빌드")
    server = commands.add_parser("serve", help="데스크탑: 장별 헤드리스 실습 실행")
    server.add_argument("--host", required=True, type=address)
    selection = server.add_mutually_exclusive_group()
    selection.add_argument("--chapter", type=int, choices=range(1, 7), default=1)
    selection.add_argument("--script")
    selection.add_argument("--experiment", type=int, choices=range(1, 7))
    server.add_argument("--teleop", action="store_true")
    server.add_argument("--share-client", action="store_true", help="테스트용 노트북 파일만 HTTP 8766으로 공유")
    commands.add_parser("setup-client", help="노트북: CPU 전용 리더 이미지 빌드")
    checker = commands.add_parser("check", help="노트북: USB 없이 서버 통신 검사")
    checker.add_argument("--host", required=True, type=address)
    fake = commands.add_parser("demo", help="노트북: USB 없이 가상 관절 값 전송")
    fake.add_argument("--host", required=True, type=address)
    fake.add_argument("--seconds", type=float, default=10)
    for command in ("leader", "calibrate"):
        child = commands.add_parser(command)
        child.add_argument("--port", required=True)
        child.add_argument("--id", required=True)
        if command == "leader":
            child.add_argument("--host", required=True, type=address)
    args = parser.parse_args(argv)
    if args.command in {"workspace", "setup-editor"}:
        sys.path.insert(0, str(ROOT))
        from tools.web_classroom.main import run_workspace, build_editor
        return build_editor() if args.command == "setup-editor" else run_workspace(args)
    if args.command == "serve":
        return serve(args)
    if args.command == "check":
        return check(args.host)
    if args.command == "demo":
        if not 0 < args.seconds <= 300:
            parser.error("seconds must be in (0, 300]")
        return demo(args)
    if args.command == "setup-client":
        return setup_client()
    return leader(args)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        print("원격 실습 연결을 종료했습니다.")
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"중단: {exc}", file=sys.stderr)
        sys.exit(1)
