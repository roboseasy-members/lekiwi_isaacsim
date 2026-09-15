"""임시 키 전달·회수와 인증 실패 검증. GPU나 USB를 열지 않습니다."""
import importlib.util
import os
from pathlib import Path
import secrets
import shlex
import socket
import subprocess
import sys
import threading
from types import SimpleNamespace
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "isaac_sim"))
import remote_auth as auth
from remote_teleop import Receiver, Sender, receive_loop
from teleop_bridge import JOINTS


def test_memory_socket_rotation_cleanup_and_duplicate_owner():
    name = "test:" + uuid.uuid4().hex
    first, second = secrets.token_bytes(32), secrets.token_bytes(32)
    with auth.KeyServer(name, first):
        assert auth.local_key(name) == first
        with pytest.raises(OSError):
            with auth.KeyServer(name, second):
                pytest.fail("must not replace an active server")
        assert auth.local_key(name) == first
    with pytest.raises(OSError):
        auth.local_key(name)
    with auth.KeyServer(name, second):
        assert auth.local_key(name) == second and first != second


def test_key_server_denies_other_uid(monkeypatch):
    name = "test:" + uuid.uuid4().hex
    monkeypatch.setattr(auth, "peer_uid", lambda _: os.getuid() + 1)
    with auth.KeyServer(name, secrets.token_bytes(32)):
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(2)
            sock.connect(auth.socket_name(name))
            assert sock.recv(33) == b""


def test_local_client_rejects_other_uid_server(monkeypatch):
    name = "test:" + uuid.uuid4().hex
    with auth.KeyServer(name, secrets.token_bytes(32)):
        monkeypatch.setattr(auth, "peer_uid", lambda _: os.getuid() + 1)
        with pytest.raises(RuntimeError, match="사용자"):
            auth.local_key(name)


def test_ssh_payload_and_key_drive_real_udp_without_prompt(tmp_path, monkeypatch, capsys):
    host = "127.0.0.1"
    key = secrets.token_bytes(32)
    actual_run = subprocess.run
    commands = []

    def ssh(command, **kwargs):
        commands.append(command)
        assert command[0] == "ssh" and command[-2] == "student@127.0.0.1"
        assert kwargs["stdin"] == subprocess.DEVNULL
        # SSH가 전달할 정확한 Python 명령을 별도 프로세스에서 실행합니다.
        return actual_run(shlex.split(command[-1]), **kwargs)

    monkeypatch.setattr(auth.subprocess, "run", ssh)
    with auth.KeyServer(host, key):
        received = auth.fetch_key(host, "student")
    assert received == key and len(commands) == 1
    output = capsys.readouterr()
    assert "auth=READY" in output.out
    assert repr(key) not in output.out + output.err and key.hex() not in str(commands)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((host, 0))
        receiver = Receiver(tmp_path / "state.json", "auth-test", key)
        stopped = threading.Event()
        worker = threading.Thread(target=receive_loop, args=(sock, receiver, stopped))
        worker.start()
        sender = Sender(host, received, port=sock.getsockname()[1])
        try:
            assert sender.sample(lambda: dict.fromkeys((name + ".pos" for name in JOINTS), 0.0))
            assert receiver.accepted == 1
        finally:
            sender.close()
            stopped.set()
            worker.join(2)


@pytest.mark.parametrize("code,data", [(1, b"secret-error-output"), (0, b""), (0, b"a" * 31), (0, b"a" * 33)])
def test_failed_ssh_or_bad_response_never_exposes_stdout(monkeypatch, capsys, code, data):
    monkeypatch.setattr(auth.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=code, stdout=data))
    with pytest.raises(RuntimeError, match="자동 인증 실패") as error:
        auth.fetch_key("127.0.0.1", "student")
    output = capsys.readouterr()
    if data:
        assert data.decode() not in output.out + output.err + str(error.value)
    assert "auth=READY" not in output.out


@pytest.mark.parametrize("user", ["-oProxyCommand=bad", "student;echo bad", "student@elsewhere", "a\nb"])
def test_ssh_username_rejects_options_and_shell_input(user):
    with pytest.raises(ValueError):
        auth.ssh_command("127.0.0.1", user)


def test_missing_server_fails_without_returning_a_key():
    command = auth.ssh_command("127.99.98.97")
    result = subprocess.run(shlex.split(command[-1]), capture_output=True)
    assert result.returncode == 1 and result.stdout == b""
    assert "실행 중인 teleop 서버" in result.stderr.decode()


def test_leader_auth_failure_precedes_calibration_and_hardware(monkeypatch):
    spec = importlib.util.spec_from_file_location("auth_leader_tool", ROOT / "tools/so101_leader.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "argv", ["leader", "--id", "test", "--remote-host", "127.0.0.1",
                                     "--remote-key-socket", "test-missing"])
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(module, "choose_calibration", lambda *_: pytest.fail("must stop before calibration"))
    monkeypatch.setattr(module, "confirm_connection", lambda: pytest.fail("must stop before hardware"))
    with pytest.raises(OSError):
        module.main()
