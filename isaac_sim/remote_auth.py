"""SSH와 같은 UID의 Linux 메모리 소켓으로 임시 teleop 키를 전달합니다."""
import os
import re
import shlex
import socket
import struct
import subprocess
import threading

from remote_teleop import address


def socket_name(name):
    # Linux abstract socket: 파일·공개 TCP 포트를 만들지 않습니다.
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", name):
        raise ValueError("리더 인증 소켓 이름이 올바르지 않습니다.")
    return f"\0lekiwi-teleop-key-v1:{os.getuid()}:{name}"


def peer_uid(sock):
    return struct.unpack("3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1]


class KeyServer:
    """이 실행의 키를 같은 Ubuntu 사용자에게만 제공하고 종료 시 소켓을 닫습니다."""
    def __init__(self, name, key):
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError("리더 인증 키가 올바르지 않습니다.")
        self.name, self.key = socket_name(name), key
        self.stopped = threading.Event()

    def __enter__(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.sock.bind(self.name)
            self.sock.listen(4)
            self.sock.settimeout(0.1)
            self.worker = threading.Thread(target=self.serve, daemon=True)
            self.worker.start()
        except BaseException:
            self.sock.close()
            raise
        return self

    def serve(self):
        while not self.stopped.is_set():
            try:
                client, _ = self.sock.accept()
            except socket.timeout:
                continue
            with client:
                client.settimeout(1)
                try:
                    if peer_uid(client) == os.getuid():
                        client.sendall(self.key)
                except OSError:
                    # 취소된 SSH 연결이 실습 수신기를 종료시키지 않게 합니다.
                    pass

    def __exit__(self, *_):
        self.stopped.set()
        self.worker.join(timeout=2)
        self.sock.close()
        self.key = None


def local_key(name):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(5)
        sock.connect(socket_name(name))
        if peer_uid(sock) != os.getuid():
            raise RuntimeError("리더 인증 소켓의 사용자가 일치하지 않습니다.")
        with sock.makefile("rb") as stream:
            key = stream.read(33)
    if len(key) != 32:
        raise RuntimeError("리더 인증 키를 받지 못했습니다.")
    return key


def ssh_command(host, user=None):
    host = address(host)
    if user is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*\$?", user):
        raise ValueError("서버 Ubuntu 계정 이름이 올바르지 않습니다.")
    # 서버 체크아웃 경로와 무관하게 표준 Python만 사용합니다. stdout은 호출자가 받습니다.
    script = (
        "import os,socket,struct,sys\n"
        "try:\n"
        " with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:\n"
        "  s.settimeout(5)\n"
        f"  s.connect('\\0lekiwi-teleop-key-v1:'+str(os.getuid())+':'+{host!r})\n"
        "  if struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))[1]!=os.getuid(): raise ValueError()\n"
        "  with s.makefile('rb') as f: key=f.read(33)\n"
        "  if len(key)!=32: raise ValueError()\n"
        " sys.stdout.buffer.write(key)\n"
        "except (OSError,ValueError):\n"
        " sys.stderr.write('실행 중인 teleop 서버가 없습니다. 서버 계정과 lesson run 6 --teleop 상태를 확인하세요.\\n')\n"
        " sys.exit(1)\n"
    )
    target = f"{user}@{host}" if user else host
    return ["ssh", "-T", "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=30",
            target, "python3 -c " + shlex.quote(script)]


def fetch_key(host, user=None):
    command = ssh_command(host, user)
    print("서버에 SSH로 인증합니다. 필요하면 서버 Ubuntu 비밀번호를 입력하세요.", flush=True)
    # SSH는 인증 입력을 /dev/tty에서 읽습니다. 키 출력만 파이프로 받아 화면에 노출하지 않습니다.
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
    if result.returncode or len(result.stdout) != 32:
        raise RuntimeError("리더 자동 인증 실패: 서버 주소·Ubuntu 계정·teleop 실행 상태를 확인하세요.")
    print("LEKIWI_REMOTE auth=READY", flush=True)
    return result.stdout
