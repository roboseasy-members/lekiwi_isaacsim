"""학생 편집기 실행 범위·중복 실행·종료·인증 전달을 검사합니다. GPU/USB 미사용."""
import io
import json
from pathlib import Path
import runpy
import signal
import socket
import subprocess
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.web_classroom.control import CHAPTERS, ControlServer, Session, selection
from tools.web_classroom.lesson import request
from tools.web_classroom.main import editor_command


@pytest.fixture
def course(tmp_path):
    for chapter in CHAPTERS:
        folder = tmp_path / "isaacsim_basic" / chapter / "experiments"
        folder.mkdir(parents=True)
        (folder / "student.py").write_text("color = [1, 0, 0]\n")
    return tmp_path


@pytest.mark.parametrize("chapter", range(1, 7))
def test_select_chapter_and_file(course, chapter):
    assert selection({"chapter": chapter}, course)["chapter"] == chapter
    relative = f"{CHAPTERS[chapter - 1]}/experiments/student.py"
    assert selection({"script": "/workspace/isaacsim_basic/" + relative}, course)["script"] == relative


@pytest.mark.parametrize("message", [
    {}, {"chapter": True}, {"chapter": 7}, {"experiment": 0},
    {"chapter": 1, "experiment": 2}, {"chapter": 1, "command": "shell"},
    {"script": "../../outside.py"}, {"script": 1},
    {"script": "01_object_physics/README.md"},
    {"chapter": 1, "teleop": True}, {"chapter": 6, "teleop": "yes"},
    {"chapter": 6, "teleop": True, "phrase": "short"},
    {"chapter": 6, "phrase": "unexpected phrase"},
])
def test_reject_invalid_selection(course, message):
    with pytest.raises(ValueError):
        selection(message, course)


def test_cannot_follow_symlink_outside_student_folder(course):
    outside = course / "outside.py"
    outside.write_text("pass\n")
    link = course / "isaacsim_basic" / CHAPTERS[0] / "experiments/link.py"
    link.symlink_to(outside)
    with pytest.raises(ValueError):
        selection({"script": f"{CHAPTERS[0]}/experiments/link.py"}, course)


def test_bad_python_is_rejected_before_gpu_launch(course):
    path = course / "isaacsim_basic" / CHAPTERS[0] / "experiments/student.py"
    path.write_text("if\n")
    session = Session(course, course / "data", "192.168.1.2", popen=lambda *a, **k: pytest.fail("spawned"))
    with pytest.raises(SyntaxError):
        session.dispatch({"op": "run", "script": f"{CHAPTERS[0]}/experiments/student.py"})


class Pipe(io.BytesIO):
    def close(self):
        self.payload = self.getvalue()
        super().close()


class Child:
    def __init__(self, command, **kwargs):
        self.command, self.options, self.stdin = command, kwargs, Pipe()
        self.code, self.signals = None, []

    def poll(self):
        return self.code

    def send_signal(self, value):
        self.signals.append(value)

    def wait(self, timeout):
        self.code = 0
        return self.code


def test_secret_in_pipe_and_duplicate_start_cannot_replace_session(course):
    session = Session(course, course / "data", "192.168.1.2", popen=Child)
    phrase = "unit-test-not-a-real-secret"
    assert session.dispatch({"op": "run", "chapter": 6, "teleop": True, "phrase": phrase})["state"] == "STARTING"
    child = session.process
    assert json.loads(child.stdin.payload)["phrase"] == phrase
    assert phrase not in str(child.command) + str(child.options)
    assert phrase not in session.log.read_text()
    with pytest.raises(RuntimeError, match="lesson stop"):
        session.dispatch({"op": "run", "chapter": 2})
    assert session.process is child
    session.log.write_text("STUDENT_SCRIPT ready file=student.py\n")
    assert session.dispatch({"op": "status"})["state"] == "READY"
    assert session.dispatch({"op": "stop"})["state"] == "STOPPED"
    assert child.signals == [signal.SIGINT]
    assert session.dispatch({"op": "run", "chapter": 2})["state"] == "STARTING"


def test_failed_and_stuck_child_are_not_reported_as_success(course):
    session = Session(course, course / "data", "192.168.1.2", popen=Child)
    session.start({"chapter": 1})
    session.process.code = 1
    assert session.status()["state"] == "FAILED"
    session.start({"chapter": 2})
    def timeout(**kwargs):
        raise subprocess.TimeoutExpired("owned-child", kwargs["timeout"])
    session.process.wait = timeout
    with pytest.raises(RuntimeError, match="종료가 지연"):
        session.stop()
    with pytest.raises(RuntimeError, match="실행 중"):
        session.start({"chapter": 3})


def test_real_unix_socket_protocol(course):
    path = course / "control.sock"
    session = Session(course, course / "data", "192.168.1.2", popen=Child)
    try:
        server = ControlServer(path, session)
    except PermissionError:
        pytest.skip("호스트 소켓 권한에서 실행 필요")
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        assert path.stat().st_mode & 0o777 == 0o600
        assert request({"op": "status"}, str(path))["state"] == "IDLE"
        assert request({"op": "run", "chapter": 1}, str(path))["state"] == "STARTING"
        assert request({"op": "stop"}, str(path))["state"] == "STOPPED"
        for raw in (b"[]\n", b"invalid\n", b"x" * 8193 + b"\n"):
            with socket.socket(socket.AF_UNIX) as client:
                client.connect(str(path))
                client.sendall(raw)
                assert not json.loads(client.makefile("rb").readline())["ok"]
        with pytest.raises(RuntimeError):
            request({"op": "exec", "command": "anything"}, str(path))
    finally:
        server.shutdown()
        worker.join(3)
        server.server_close()


def test_editor_mounts_only_student_files_for_editing(course):
    _, command = editor_command(["docker"], course, course / "data", course / "runtime", "192.168.1.2", 8443, "test")
    mounts = [command[i + 1] for i, arg in enumerate(command) if arg == "--mount"]
    assert len([m for m in mounts if "dst=/workspace/" in m and not m.endswith("readonly")]) == 6
    assert all("/experiments" in m for m in mounts if "dst=/workspace/" in m and not m.endswith("readonly"))
    assert all(m.endswith("readonly") for m in mounts if "dst=/results/" in m)
    assert not any("docker.sock" in arg or "PASSWORD=" in arg or "privileged" in arg for arg in command)
    assert "127.0.0.1:8443:8080" in command
    assert not any(arg.startswith("192.168.1.2:") for arg in command)



def test_editor_entrypoint_starts_without_reading_a_password(monkeypatch):
    import os
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"")))
    monkeypatch.setattr(os, "umask", lambda mask: None)
    launches = []
    monkeypatch.setattr(os, "execv", lambda path, args: launches.append((path, args)))
    entrypoint = Path(__file__).resolve().parents[1] / "tools/web_classroom/editor_entrypoint.py"
    runpy.run_path(str(entrypoint), run_name="__main__")
    assert launches == [("/usr/bin/entrypoint.sh", ["/usr/bin/entrypoint.sh", "--config",
        "/opt/lekiwi-editor/editor.yaml", "/opt/lekiwi-editor/lekiwi.code-workspace"])]


def test_workspace_ready_without_password_input(course, monkeypatch, capsys):
    from types import SimpleNamespace
    import pwd
    import shlex
    import tools.remote_classroom.main as remote
    import tools.web_classroom.main as workspace
    monkeypatch.setattr(workspace, "ROOT", course)
    monkeypatch.setenv("LEKIWI_DATA_DIR", str(course / "data"))
    monkeypatch.setenv("ACCEPT_EULA", "Y")
    monkeypatch.setenv("USER", "unrelated-environment-user")
    monkeypatch.setattr(pwd, "getpwuid", lambda uid: SimpleNamespace(pw_name="classroom-user"))
    monkeypatch.setattr(workspace, "docker_command", lambda: ["docker"])
    monkeypatch.setattr(workspace.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 0))
    children, stopped = [], []

    class Editor:
        returncode = 0

        def __init__(self, command, **kwargs):
            self.command, self.options = command, kwargs
            self.polls = iter([None, 0])
            children.append(self)

        def poll(self):
            return next(self.polls)

        def wait(self, timeout):
            return 0

    monkeypatch.setattr(workspace.subprocess, "Popen", Editor)
    monkeypatch.setattr(workspace, "healthy", lambda url: True)
    monkeypatch.setattr(workspace.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(remote, "stop_owned", lambda *args: stopped.append(args))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    workspace.run_workspace(SimpleNamespace(host="192.168.1.2", port=port))
    assert len(children) == 1
    assert children[0].options["stdin"] == subprocess.DEVNULL
    assert "-i" not in children[0].command
    assert f"127.0.0.1:{port}:8080" in children[0].command
    assert len(stopped) == 1
    output = capsys.readouterr().out
    assert "LEKIWI_WORKSPACE ready" in output
    assert "LEKIWI_WORKSPACE stopped" in output
    command = next(line for line in output.splitlines() if line.startswith("ssh -N "))
    assert shlex.split(command) == ["ssh", "-N", "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=30", "-L", f"127.0.0.1:{port}:127.0.0.1:{port}",
        "classroom-user@192.168.1.2"]
    assert "사용자명@" not in output


def test_workspace_cli_has_no_password_option(monkeypatch, capsys):
    import tools.remote_classroom.main as remote
    import tools.web_classroom.main as workspace
    calls = []
    monkeypatch.setattr(workspace, "run_workspace", calls.append)
    remote.main(["workspace", "--host", "192.168.1.2"])
    assert len(calls) == 1
    assert not hasattr(calls[0], "password_stdin")
    with pytest.raises(SystemExit) as failure:
        remote.main(["workspace", "--host", "192.168.1.2", "--password-stdin"])
    assert failure.value.code == 2
    assert len(calls) == 1
