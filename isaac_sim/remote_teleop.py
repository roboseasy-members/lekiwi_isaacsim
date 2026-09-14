"""LAN 또는 Tailscale을 통한 리더암 입력 전달. 영상 전송은 WebRTC가 담당합니다.

서버가 발급한 일회용 요청을 받은 뒤 관절을 읽습니다. 서버 자신의 발급 시각으로
유효 기간을 검사하므로 두 PC의 시계를 맞출 필요가 없고 밀린 입력도 재생하지 않습니다.
접속 문구는 메모리에서만 사용하며 HMAC은 입력의 인증·변조 검사용입니다(암호화 아님).
"""
import errno
import getpass
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import sys
import time

from teleop_bridge import (REMOTE_INPUT_TIMEOUT, REMOTE_RECOVERY_WINDOW,
                          atomic_json, make_packet, validate_positions)

PORT = 49101
MAX_PACKET = 4096
MAX_AGE = 0.20  # 늦게 도착한 응답의 수락 한도입니다. 다음 입력 대기 한도와 구분합니다.
NETWORK_ERRORS = {errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ECONNREFUSED,
                  errno.ENETDOWN, errno.EHOSTDOWN, errno.ECONNRESET, errno.ETIMEDOUT,
                  errno.EPERM, errno.EACCES}  # 소켓 전송이 방화벽에서 차단돼도 연결 복구를 기다립니다.


def retryable_network_error(exc):
    if exc.errno not in NETWORK_ERRORS:
        raise exc


def address(value):
    ip = ipaddress.IPv4Address(value)
    if ip.is_unspecified or ip.is_multicast or int(ip) == 0xFFFFFFFF:
        raise ValueError("접속 가능한 데스크탑 IPv4를 지정하세요.")
    return str(ip)


def connection_key():
    if not sys.stdin.isatty():
        raise RuntimeError("접속 문구는 대화형 터미널에서 숨김 입력으로 지정하세요.")
    phrase = getpass.getpass("양쪽 PC에서 같은 접속 문구를 입력하세요(12자 이상, 화면에 표시되지 않음): ")
    if len(phrase) < 12:
        raise ValueError("접속 문구는 12자 이상으로 정하세요. 명령줄이나 문서에 적지 마세요.")
    return hashlib.pbkdf2_hmac("sha256", phrase.encode(), b"lekiwi-lan-v1", 200_000)


def encode(message, key):
    body = json.dumps(message, sort_keys=True, separators=(",", ":"), allow_nan=False)
    signature = hmac.new(key, body.encode(), "sha256").hexdigest()
    return json.dumps({"body": body, "mac": signature}, separators=(",", ":")).encode()


def decode(data, key):
    if len(data) > MAX_PACKET:
        raise ValueError("oversized packet")
    envelope = json.loads(data)
    body, mac = envelope["body"], envelope["mac"]
    if not isinstance(body, str) or not isinstance(mac, str):
        raise ValueError("invalid envelope")
    expected = hmac.new(key, body.encode(), "sha256").hexdigest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("authentication failed")
    message = json.loads(body)
    if not isinstance(message, dict) or message.get("v") != 1:
        raise ValueError("invalid protocol version")
    return message


class Receiver:
    """한 학생의 최신 입력만 같은 호스트의 기존 JSON 우편함에 씁니다."""
    def __init__(self, state, session, key, clock=time.monotonic):
        self.state, self.session, self.key, self.clock = state, session, key, clock
        self.peer = None
        self.peer_id = None
        self.peer_seen = -1.0
        self.request = -1
        self.challenge = None
        self.issued = -1.0
        self.sample_stamp = -1.0
        self.sequence = 0
        self.connected = False
        self.waiting = False
        self.accepted = 0
        self.rejected = 0
        self.max_rtt_ms = 0.0
        self.generation = 0
        self.gap_stamp = None

    def stop(self):
        packet = make_packet({}, self.session, self.sequence, connected=False)
        self.sequence += 1
        atomic_json(self.state, packet)
        if self.connected:
            print("LEKIWI_REMOTE input=STOP; 복구 후 Isaac 화면에서 R로 다시 시작하세요.", flush=True)
        self.connected = False
        self.waiting = False

    def expire(self):
        now = self.clock()
        if self.connected:
            if now - self.sample_stamp >= REMOTE_RECOVERY_WINDOW:
                self.stop()
            elif now - self.sample_stamp > REMOTE_INPUT_TIMEOUT and not self.waiting:
                # 표본 시각을 갱신하지 않습니다. 시뮬레이터도 500 ms에서 독립적으로 멈춥니다.
                self.waiting = True
                self.gap_stamp = self.sample_stamp
                print("LEKIWI_REMOTE input=RECONNECTING; 새 입력을 기다립니다.", flush=True)
        # 잠시 끊긴 같은 송신기는 유지합니다. 새 프로세스는 이후 새 연결로 받습니다.
        if self.peer is not None and now - self.peer_seen >= REMOTE_RECOVERY_WINDOW:
            self.peer = self.peer_id = self.challenge = None
            self.request = -1

    def handle(self, data, peer):
        self.expire()
        now = self.clock()
        if data == b"LEKIWI_LAN_CHECK_V1":
            return b"LEKIWI_LAN_OK_V1"  # 상태 확인에는 제어 권한이 없습니다.
        if self.key is None:
            return None
        try:
            message = decode(data, self.key)
            kind, client = message.get("kind"), message.get("client")
            if not isinstance(client, str) or len(client) != 32:
                raise ValueError("invalid client")
            if self.peer is not None and (peer, client) != (self.peer, self.peer_id):
                raise ValueError("another client is active")
            if kind == "hello":
                request = message.get("request")
                if type(request) is not int or request <= self.request:
                    raise ValueError("old request")
                self.peer, self.peer_id, self.peer_seen = peer, client, now
                self.request = request
                self.challenge, self.issued = secrets.token_hex(16), now
                return encode({"v": 1, "kind": "challenge", "client": client,
                               "request": request, "session": self.session,
                               "challenge": self.challenge}, self.key)
            if self.peer is None or message.get("session") != self.session:
                raise ValueError("no matching connection")
            if (kind != "sample" or not self.challenge
                    or message.get("challenge") != self.challenge
                    or not 0 <= now - self.issued <= MAX_AGE):
                raise ValueError("expired or repeated challenge")
            positions = message.get("positions")
            validate_positions(positions)
            if not self.connected:
                self.generation += 1
            packet = make_packet(positions, self.session, self.sequence)
            packet.update(monotonic=self.issued, remote_peer=f"{client}:{self.generation}",
                          input_gap_stamp=self.gap_stamp)
            self.sequence += 1
            atomic_json(self.state, packet)
            self.max_rtt_ms = max(self.max_rtt_ms, (now - self.issued) * 1000)
            self.accepted += 1
            self.sample_stamp = self.issued
            self.challenge = None  # 같은 sample의 재전송은 반영하지 않습니다.
            if not self.connected:
                print("LEKIWI_REMOTE input=READY; Isaac 화면에서 자세를 확인하고 R로 시작하세요.", flush=True)
            self.connected = True
            self.waiting = False
            return encode({"v": 1, "kind": "accepted", "client": client,
                           "request": self.request, "session": self.session}, self.key)
        except (ValueError, KeyError, TypeError, UnicodeError, OverflowError):
            self.rejected += 1
            return None


def receive_loop(sock, receiver, stopped):
    sock.settimeout(0.05)
    receiver.stop()
    try:
        while not stopped.is_set():
            try:
                data, peer = sock.recvfrom(MAX_PACKET + 1)
            except socket.timeout:
                receiver.expire()
                continue
            except OSError as exc:
                retryable_network_error(exc)
                receiver.expire()
                stopped.wait(0.05)
                continue
            response = receiver.handle(data, peer)
            if response is not None:
                try:
                    sock.sendto(response, peer)
                except OSError as exc:
                    retryable_network_error(exc)
    finally:
        receiver.stop()


class Sender:
    """challenge 수신 후에만 reader를 호출합니다. 이전 관절값을 캐시하지 않습니다."""
    def __init__(self, host, key, port=PORT, timeout=0.05):
        self.key = key
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((address(host), port))
        # 50 ms는 수신 확인 주기입니다. WAN 응답이 늦어도 200 ms 한도까지 기다립니다.
        self.timeout = timeout
        self.sock.settimeout(timeout)
        self.client = secrets.token_hex(16)
        self.request = 0

    def sample(self, reader):
        self.request += 1
        deadline = time.monotonic() + MAX_AGE
        try:
            self.sock.send(encode({"v": 1, "kind": "hello", "client": self.client,
                                   "request": self.request}, self.key))
        except OSError as exc:
            retryable_network_error(exc)
            return False
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            self.sock.settimeout(min(self.timeout, remaining))
            try:
                data = self.sock.recv(MAX_PACKET + 1)
            except socket.timeout:
                continue
            except OSError as exc:
                retryable_network_error(exc)
                return False
            if time.monotonic() >= deadline:
                return False
            message = decode(data, self.key)
            if message.get("client") != self.client or message.get("request") != self.request:
                continue
            if message.get("kind") == "accepted":
                return True
            if message.get("kind") != "challenge":
                continue
            positions = reader()
            validate_positions(positions)
            try:
                self.sock.send(encode({"v": 1, "kind": "sample", "client": self.client,
                                       "session": message["session"], "challenge": message["challenge"],
                                       "positions": positions}, self.key))
            except OSError as exc:
                retryable_network_error(exc)
                return False

    def close(self):
        # 새 요청을 보내지 않고 서버의 짧은 입력 watchdog으로 추종을 해제합니다.
        self.sock.close()
