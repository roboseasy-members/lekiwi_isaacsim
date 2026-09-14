"""실습 실행기의 자식 프로세스. 접속 문구는 익명 파이프로만 받아 메모리에서 사용합니다."""
import hashlib
import json
from pathlib import Path
import signal
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.remote_classroom.main import serve


def main():
    options = json.loads(sys.stdin.buffer.readline(8193))
    phrase = options.pop("phrase", None)
    key = hashlib.pbkdf2_hmac("sha256", phrase.encode(), b"lekiwi-lan-v1", 200_000) if phrase else None
    del phrase
    options["share_client"] = False
    serve(SimpleNamespace(**options), control_key=key)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"중단: {exc}", file=sys.stderr)
        sys.exit(1)
