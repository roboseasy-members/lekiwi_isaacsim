"""LAN 입력의 인증·시간 기준·단절 복구와 원격 실행 설정을 검사합니다. USB 미사용."""
import importlib.util
import json
from pathlib import Path
import socket
import sys
import threading
import time
from types import SimpleNamespace
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "isaac_sim"))
from remote_teleop import Receiver, Sender, decode, encode, receive_loop, MAX_AGE
from teleop_bridge import JOINTS, ArmTeleop, read_packet
from app_runtime import StreamConnection, launch_config, install_student_streaming, stream_host

KEY = b"unit-test-key-not-a-real-credential"
CLIENT = "a" * 32
PEER = ("127.0.0.1", 32001)


@pytest.fixture
def receiver(tmp_path):
    clock = [500.0]
    result = Receiver(tmp_path / "state.json", "test-session", KEY, lambda: clock[0])
    result.test_clock = clock
    return result


def hello(receiver, request=1, client=CLIENT, peer=PEER):
    request = {"v": 1, "kind": "hello", "client": client, "request": request}
    response = receiver.handle(encode(request, KEY), peer)
    return decode(response, KEY) if response else None


def sample(receiver, challenge, positions=None, peer=PEER):
    message = {"v": 1, "kind": "sample", "client": challenge["client"],
               "session": challenge["session"], "challenge": challenge["challenge"],
               "positions": positions if positions is not None else dict.fromkeys((n + ".pos" for n in JOINTS), 0.0)}
    data = encode(message, KEY)
    return receiver.handle(data, peer), data


def test_only_fresh_authenticated_sample_becomes_local_clock_packet(receiver):
    challenge = hello(receiver)
    receiver.test_clock[0] += 0.03
    response, raw = sample(receiver, challenge)
    assert decode(response, KEY)["kind"] == "accepted"
    packet = read_packet(receiver.state)
    assert packet["monotonic"] == 500.0  # 클라이언트 시간을 받아 적지 않습니다.
    assert packet["remote_peer"] == CLIENT + ":1"
    assert packet["session"] == "test-session"
    assert receiver.handle(raw, PEER) is None
    assert read_packet(receiver.state) == packet


def test_authentication_failure_and_malformed_packets_do_not_create_input(receiver):
    message = {"v": 1, "kind": "hello", "client": CLIENT, "request": 1}
    for packet in (encode(message, b"wrong"), b"bad", b"[]", b"{}", b"\xff", b"x" * 5000):
        assert receiver.handle(packet, PEER) is None
    assert receiver.peer is None
    assert not receiver.state.exists()


def test_only_one_active_client_and_ordered_hello(receiver):
    first = hello(receiver)
    assert hello(receiver) is None
    assert hello(receiver, 2, "b" * 32, ("127.0.0.1", 32002)) is None
    second = hello(receiver, 2)
    assert sample(receiver, first)[0] is None
    assert sample(receiver, second)[0] is not None


def test_delayed_reply_and_wrong_session_never_refresh_input(receiver):
    challenge = hello(receiver)
    receiver.test_clock[0] += MAX_AGE + 0.01
    assert sample(receiver, challenge)[0] is None
    assert not receiver.state.exists()
    challenge = hello(receiver, 2)
    challenge["session"] = "previous-server"
    assert sample(receiver, challenge)[0] is None


@pytest.mark.parametrize("values", [{}, {"shoulder_pan.pos": 10},
    dict.fromkeys((n + ".pos" for n in JOINTS), True),
    dict.fromkeys((n + ".pos" for n in JOINTS), 361),
    dict.fromkeys((n + ".pos" for n in JOINTS), -1)])
def test_bad_joint_units_are_rejected(receiver, values):
    assert sample(receiver, hello(receiver), values)[0] is None
    assert not receiver.state.exists()


def test_hello_without_new_samples_cannot_keep_input_alive(receiver):
    sample(receiver, hello(receiver))
    receiver.test_clock[0] += 0.15
    hello(receiver, 2)
    receiver.test_clock[0] += 0.10
    receiver.expire()
    assert read_packet(receiver.state)["connected"] is False


def test_reconnect_requires_rearming_even_if_simulator_missed_disconnect(receiver):
    sample(receiver, hello(receiver))
    arm = ArmTeleop("test-session")
    arm.update(read_packet(receiver.state), 500.0, [0] * 6)
    arm.update(read_packet(receiver.state), 500.01, [0] * 6, arm=True)
    assert arm.armed
    receiver.test_clock[0] += 0.3
    sample(receiver, hello(receiver, 2))
    assert read_packet(receiver.state)["remote_peer"].endswith(":2")
    arm.update(read_packet(receiver.state), 500.3, [0] * 6, arm=True)
    assert not arm.armed  # 연결 변경과 같은 프레임에 남아 있던 R도 무시합니다.
    arm.update(read_packet(receiver.state), 500.31, [0] * 6, arm=True)
    assert arm.armed


def test_health_check_does_not_grant_control(receiver):
    assert receiver.handle(b"LEKIWI_LAN_CHECK_V1", PEER) == b"LEKIWI_LAN_OK_V1"
    assert not receiver.state.exists()
    assert receiver.peer is None


def test_stream_disconnect_clears_keys_before_accepting_new_input():
    stream = StreamConnection()
    assert not stream.input_allowed
    stream.consume_reset()
    assert not stream.input_allowed
    stream.set_connected(True)
    assert not stream.input_allowed
    assert stream.consume_reset()
    assert stream.input_allowed
    stream.set_connected(False)
    assert not stream.input_allowed
    assert stream.consume_reset()


def test_remote_configuration_keeps_recording_flags_and_local_scripts(monkeypatch):
    source = {"headless": False, "extra_args": ["--recording-setting"], "width": 1280}
    assert launch_config(source) == source
    monkeypatch.setenv("LEKIWI_DISPLAY_MODE", "webrtc")
    monkeypatch.setenv("LEKIWI_STREAM_HOST", "192.168.0.81")
    modified = launch_config(source)
    assert modified["headless"] and not modified["hide_ui"]
    assert modified["extra_args"] == source["extra_args"]
    assert source["headless"] is False


@pytest.mark.parametrize("host", ["", "0.0.0.0", "224.0.0.1", "255.255.255.255", "::1", "localhost"])
def test_invalid_stream_host(host):
    with pytest.raises(ValueError):
        stream_host(host)


def test_student_bootstrap_restores_original_sdk_before_creating_app(monkeypatch):
    import app_runtime
    calls = []
    def original(config):
        assert sdk.SimulationApp is original
        calls.append(config)
        return SimpleNamespace()
    sdk = SimpleNamespace(SimulationApp=original)
    monkeypatch.setitem(sys.modules, "isaacsim", sdk)
    monkeypatch.setenv("LEKIWI_DISPLAY_MODE", "webrtc")
    monkeypatch.setenv("LEKIWI_STREAM_HOST", "192.168.0.81")
    monkeypatch.setattr(app_runtime, "enable_streaming", lambda app: calls.append("enabled"))
    install_student_streaming()
    sdk.SimulationApp(launch_config={"headless": False})
    assert calls == [{"headless": True, "hide_ui": False, "window_width": 1280, "window_height": 720}, "enabled"]


def test_real_udp_roundtrip_and_timeout_without_usb(tmp_path):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", 0))
    except PermissionError:
        if sock:
            sock.close()
        pytest.skip("sandbox disallows socket binding; run this test on the host")
    stopped = threading.Event()
    receiver = Receiver(tmp_path / "state.json", "loopback", KEY)
    worker = threading.Thread(target=receive_loop, args=(sock, receiver, stopped))
    worker.start()
    sender = Sender("127.0.0.1", KEY, port=sock.getsockname()[1])
    reads = []
    def reader():
        reads.append(time.monotonic())
        return dict.fromkeys((n + ".pos" for n in JOINTS), 0.0)
    try:
        for _ in range(5):
            assert sender.sample(reader)
        assert len(reads) == 5 and receiver.accepted == 5
        assert read_packet(receiver.state)["connected"]
        deadline = time.monotonic() + 1
        while read_packet(receiver.state)["connected"] and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not read_packet(receiver.state)["connected"]
    finally:
        sender.close()
        stopped.set()
        worker.join(2)
        sock.close()


def test_client_bundle_contains_only_explicit_sources(tmp_path):
    spec = importlib.util.spec_from_file_location("remote_main", ROOT / "tools/remote_classroom/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "client.zip"
    module.bundle(output)
    with zipfile.ZipFile(output) as archive:
        assert len(archive.namelist()) == 8
        assert not any("/data/" in name or ".." in name for name in archive.namelist())
        assert "lekiwi-client/isaac_sim/remote_teleop.py" in archive.namelist()


def test_connection_phrase_cannot_fall_back_to_echoed_input(monkeypatch):
    import remote_teleop
    monkeypatch.setattr(remote_teleop.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    monkeypatch.setattr(remote_teleop.getpass, "getpass", lambda *_: pytest.fail("must not prompt"))
    with pytest.raises(RuntimeError, match="숨김"):
        remote_teleop.connection_key()


@pytest.mark.parametrize("owner,should_stop", [("ours", True), ("another-session", False), (None, False)])
def test_cleanup_stops_only_owned_container(monkeypatch, owner, should_stop):
    spec = importlib.util.spec_from_file_location("remote_cleanup", ROOT / "tools/remote_classroom/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0 if owner else 1, stdout=json.dumps({"run": owner}))
    monkeypatch.setattr(module.subprocess, "run", run)
    assert module.stop_owned(["docker"], "test-sim", "run", "ours") is should_stop
    assert any("stop" in args for args in calls) is should_stop
