"""LAN 입력의 인증·시간 기준·단절 복구와 원격 실행 설정을 검사합니다. USB 미사용."""
import importlib.util
import errno
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


def test_stream_port_check_allows_time_wait_after_video_disconnect():
    from tools.remote_classroom.main import check_stream_port
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.listen()
        with socket.create_connection(("127.0.0.1", port)) as client:
            peer, _ = listener.accept()
            peer.close()  # 서버 쪽에 실제 TIME_WAIT 상태를 만듭니다.
            assert client.recv(1) == b""
    with socket.socket() as old_probe:
        with pytest.raises(OSError) as failure:
            old_probe.bind(("127.0.0.1", port))
        assert failure.value.errno == errno.EADDRINUSE
    check_stream_port("127.0.0.1", port)


@pytest.mark.parametrize("host", ["127.0.0.1", "0.0.0.0"])
def test_stream_port_check_still_rejects_active_video_server(host):
    from tools.remote_classroom.main import check_stream_port
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, 0))
        listener.listen()
        with pytest.raises(OSError) as failure:
            check_stream_port("127.0.0.1", listener.getsockname()[1])
        assert failure.value.errno == errno.EADDRINUSE


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
    receiver.test_clock[0] += 0.40
    hello(receiver, 2)
    receiver.test_clock[0] += 0.11
    receiver.expire()
    assert receiver.waiting
    assert read_packet(receiver.state)["monotonic"] == 500.0
    receiver.test_clock[0] = 502.0
    hello(receiver, 3)
    assert read_packet(receiver.state)["connected"] is False


@pytest.mark.parametrize("gap", [0.201, 0.251, 0.499, 0.500])
def test_remote_input_waits_up_to_500ms_without_disarming(receiver, gap):
    sample(receiver, hello(receiver))
    arm = ArmTeleop("test-session", remote=True)
    arm.update(read_packet(receiver.state), 500.0, arm.targets)
    arm.update(read_packet(receiver.state), 500.0, arm.targets, arm=True)
    receiver.test_clock[0] = 500.0 + gap
    receiver.expire()
    packet = read_packet(receiver.state)
    assert packet["connected"]
    arm.update(packet, receiver.test_clock[0], arm.targets)
    assert arm.armed
    sample(receiver, hello(receiver, 2))
    assert receiver.generation == 1


def test_remote_input_stops_after_500ms_then_requires_three_new_samples(receiver):
    sample(receiver, hello(receiver))
    arm = ArmTeleop("test-session", remote=True)
    arm.update(read_packet(receiver.state), 500.0, arm.targets)
    arm.update(read_packet(receiver.state), 500.0, arm.targets, arm=True)
    held = arm.targets[:]
    receiver.test_clock[0] = 500.501
    # 수신 루프가 늦어져도 시뮬레이터가 독립적으로 만료된 입력을 차단합니다.
    arm.update(read_packet(receiver.state), 500.501, held)
    assert not arm.armed and arm.recovering and arm.targets == held
    receiver.expire()
    for request in (2, 3, 4):
        receiver.test_clock[0] += 0.04
        sample(receiver, hello(receiver, request))
        arm.update(read_packet(receiver.state), receiver.test_clock[0], held)
        assert arm.armed is (request == 4)
        if request != 4:
            for _ in range(4):
                arm.update(read_packet(receiver.state), receiver.test_clock[0], held)
                assert not arm.armed  # 같은 최신 표본을 여러 번 렌더링해도 세지 않습니다.
    assert arm.resumed and not arm.recovering
    assert arm.targets == held  # 재개 프레임은 실제 자세에서 시작하고 밀린 목표로 뛰지 않습니다.
    assert receiver.generation == 1


@pytest.mark.parametrize("dropped_kind", ["challenge", "accepted"])
def test_one_lost_reply_recovers_before_input_expires(receiver, monkeypatch, dropped_kind):
    """응답 한 개가 유실돼도 새 관절값을 읽어 입력 만료 전에 회복해야 합니다."""
    import remote_teleop

    class LossySocket:
        drop = None
        def __init__(self, *args):
            self.responses = []
        def connect(self, address):
            pass
        def settimeout(self, timeout):
            self.timeout = timeout
        def send(self, data):
            response = receiver.handle(data, PEER)
            if response and decode(response, KEY)["kind"] == self.drop:
                self.drop = None
            elif response:
                self.responses.append(response)
        def recv(self, size):
            if self.responses:
                return self.responses.pop(0)
            receiver.test_clock[0] += self.timeout
            raise socket.timeout()

    monkeypatch.setattr(remote_teleop.socket, "socket", LossySocket)
    monkeypatch.setattr(remote_teleop.time, "monotonic", lambda: receiver.test_clock[0])
    sender = Sender("127.0.0.1", KEY)
    reader = lambda: dict.fromkeys((n + ".pos" for n in JOINTS), 0.0)
    assert sender.sample(reader)
    assert receiver.generation == 1
    sender.sock.drop = dropped_kind
    assert not sender.sample(reader)
    receiver.test_clock[0] += 1 / 30  # 다음 수집 주기에 새 관절값을 요청합니다.
    assert sender.sample(reader)
    assert receiver.generation == 1  # 안전 정지 후 자동 재활성화로 우회하지 않습니다.
    assert read_packet(receiver.state)["connected"]


@pytest.mark.parametrize("reply_delay, accepted", [(0.075, True), (0.25, False)])
def test_sender_waits_for_wan_reply_but_never_reads_expired_challenge(
        receiver, monkeypatch, reply_delay, accepted):
    """50ms보다 늦은 정상 응답은 수신하고, 전체 대기 한도를 넘으면 읽지 않습니다."""
    import remote_teleop

    class DelayedSocket:
        def __init__(self, *args):
            self.responses = []
        def connect(self, address):
            pass
        def settimeout(self, timeout):
            self.timeout = timeout
        def send(self, data):
            response = receiver.handle(data, PEER)
            if response:
                self.responses.append((receiver.test_clock[0] + reply_delay, response))
        def recv(self, size):
            end = receiver.test_clock[0] + self.timeout
            if self.responses and self.responses[0][0] <= end:
                receiver.test_clock[0], response = self.responses.pop(0)
                return response
            receiver.test_clock[0] = end
            raise socket.timeout()

    monkeypatch.setattr(remote_teleop.socket, "socket", DelayedSocket)
    monkeypatch.setattr(remote_teleop.time, "monotonic", lambda: receiver.test_clock[0])
    sender = Sender("127.0.0.1", KEY)
    reads = []
    def reader():
        reads.append(receiver.test_clock[0])
        return dict.fromkeys((n + ".pos" for n in JOINTS), 0.0)

    started = receiver.test_clock[0]
    assert sender.sample(reader) is accepted
    assert len(reads) == int(accepted)
    assert receiver.test_clock[0] - started <= MAX_AGE + 1e-9
    if accepted:
        assert receiver.accepted == 1
        assert read_packet(receiver.state)["connected"]
    else:
        assert not receiver.state.exists()


def test_reconnect_requires_rearming_even_if_simulator_missed_disconnect(receiver):
    sample(receiver, hello(receiver))
    arm = ArmTeleop("test-session", remote=True)
    arm.update(read_packet(receiver.state), 500.0, [0] * 6)
    arm.update(read_packet(receiver.state), 500.01, [0] * 6, arm=True)
    assert arm.armed
    receiver.test_clock[0] += 2.001
    sample(receiver, hello(receiver, 2))
    assert read_packet(receiver.state)["remote_peer"].endswith(":2")
    arm.update(read_packet(receiver.state), 502.001, [0] * 6, arm=True)
    assert not arm.armed  # 연결 변경과 같은 프레임에 남아 있던 R도 무시합니다.
    arm.update(read_packet(receiver.state), 502.01, [0] * 6, arm=True)
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
        arm = ArmTeleop('loopback', remote=True)
        arm.update(read_packet(receiver.state), time.monotonic(), arm.targets)
        arm.update(read_packet(receiver.state), time.monotonic(), arm.targets, arm=True)
        deadline = time.monotonic() + 1
        while not receiver.waiting and time.monotonic() < deadline:
            time.sleep(0.02)
        assert receiver.waiting
        arm.update(read_packet(receiver.state), time.monotonic(), arm.targets)
        assert arm.recovering and not arm.armed
        for i in range(3):
            assert sender.sample(reader)
            arm.update(read_packet(receiver.state), time.monotonic(), arm.targets)
            assert arm.armed is (i == 2)
        assert arm.resumed
        deadline = time.monotonic() + 3
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


def armed_remote(receiver):
    sample(receiver, hello(receiver))
    arm = ArmTeleop('test-session', remote=True)
    arm.update(read_packet(receiver.state), 500.0, arm.targets)
    arm.update(read_packet(receiver.state), 500.0, arm.targets, arm=True)
    assert arm.armed
    return arm


@pytest.mark.parametrize('cancel', ['space', 'video_or_reset', 'bad_packet', 'deadline', 'new_sender'])
def test_recovery_cancellation_never_rearms_by_itself(receiver, cancel):
    arm = armed_remote(receiver)
    receiver.test_clock[0] = 500.6
    arm.update(read_packet(receiver.state), 500.6, arm.targets)
    assert arm.recovering
    if cancel == 'space':
        arm.update(read_packet(receiver.state), 500.6, arm.targets, stop=True, arm=True)
    elif cancel == 'video_or_reset':
        arm.disarm()
    elif cancel == 'bad_packet':
        bad = read_packet(receiver.state)
        bad['positions'] = {}
        arm.update(bad, 500.6, arm.targets)
    elif cancel == 'deadline':
        receiver.test_clock[0] = 502.0
        arm.update(read_packet(receiver.state), 502.0, arm.targets)
    else:
        receiver.stop()  # 송신기 재시작이나 명시적인 연결 종료는 새로운 세대입니다.
    for request in range(2, 6):
        receiver.test_clock[0] += 0.04
        sample(receiver, hello(receiver, request))
        arm.update(read_packet(receiver.state), receiver.test_clock[0], arm.targets)
        assert not arm.armed and not arm.recovering
    arm.update(read_packet(receiver.state), receiver.test_clock[0], arm.targets, arm=True)
    assert arm.armed


def test_receiver_remembers_short_gap_between_simulator_frames(receiver):
    arm = armed_remote(receiver)
    receiver.test_clock[0] = 500.6
    # 수신 루프만 단절을 관측하고, 시뮬레이터에는 복구된 표본부터 보입니다.
    sample(receiver, hello(receiver, 2))
    assert receiver.generation == 1
    arm.update(read_packet(receiver.state), 500.6, arm.targets)
    assert arm.recovering and not arm.armed
    for request in (3, 4):
        receiver.test_clock[0] += 0.04
        sample(receiver, hello(receiver, request))
        arm.update(read_packet(receiver.state), receiver.test_clock[0], arm.targets)
    assert arm.armed and arm.resumed


def test_recovery_deadline_is_not_extended_by_partial_recovery(receiver):
    arm = armed_remote(receiver)
    receiver.test_clock[0] = 500.6
    arm.update(read_packet(receiver.state), 500.6, arm.targets)
    for request, now in [(2, 501.8), (3, 501.9), (4, 502.0)]:
        receiver.test_clock[0] = now
        sample(receiver, hello(receiver, request))
        arm.update(read_packet(receiver.state), now, arm.targets)
        assert not arm.armed
    assert not arm.recovering


@pytest.mark.parametrize('failure_at', ['hello', 'recv', 'sample', 'reader'])
@pytest.mark.parametrize('error_number', [errno.ENETUNREACH, errno.EPERM, errno.EACCES, errno.ECONNREFUSED])
def test_sender_retries_network_errors_but_propagates_reader_errors(receiver, monkeypatch, failure_at, error_number):
    import remote_teleop

    class InterruptedSocket:
        fail = failure_at
        def __init__(self, *args):
            self.responses = []
        def connect(self, endpoint):
            pass
        def settimeout(self, timeout):
            pass
        def send(self, data):
            if decode(data, KEY)['kind'] == self.fail:
                self.fail = None
                raise OSError(error_number, 'test route unavailable')
            response = receiver.handle(data, PEER)
            if response:
                self.responses.append(response)
        def recv(self, size):
            if self.fail == 'recv':
                self.fail = None
                raise OSError(error_number, 'test route unavailable')
            return self.responses.pop(0)

    monkeypatch.setattr(remote_teleop.socket, 'socket', InterruptedSocket)
    sender = Sender('127.0.0.1', KEY)
    reads = []
    def reader():
        reads.append(True)
        if sender.sock.fail == 'reader':
            raise OSError(error_number, 'test USB reader failure')
        return dict.fromkeys((n + '.pos' for n in JOINTS), 0.0)
    if failure_at == 'reader':
        with pytest.raises(OSError, match='USB reader'):
            sender.sample(reader)
        assert len(reads) == 1
    else:
        assert not sender.sample(reader)
        assert sender.sample(reader)  # 같은 송신기에서 다음 주기의 새 입력으로 복구합니다.
        assert len(reads) == (2 if failure_at == 'sample' else 1)


def test_another_gap_during_recovery_restarts_sample_count_not_deadline(receiver):
    arm = armed_remote(receiver)
    for request, now in [(2, 500.6), (3, 500.7)]:
        receiver.test_clock[0] = now
        sample(receiver, hello(receiver, request))
        arm.update(read_packet(receiver.state), now, arm.targets)
    assert arm.recovery_samples == 2
    for request, now in [(4, 501.3), (5, 501.4), (6, 501.5)]:
        receiver.test_clock[0] = now
        sample(receiver, hello(receiver, request))
        arm.update(read_packet(receiver.state), now, arm.targets)
        assert arm.armed is (request == 6)
        if request != 6:
            assert arm.recovery_deadline == 502.0


def test_manual_arm_stop_does_not_hide_later_input_loss_from_recorder(receiver):
    arm = armed_remote(receiver)
    arm.update(read_packet(receiver.state), 500.1, arm.targets, stop=True)
    assert not arm.armed and arm.input_valid
    arm.update(read_packet(receiver.state), 500.6, arm.targets)
    assert not arm.armed and not arm.recovering and not arm.input_valid
