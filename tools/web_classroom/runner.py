"""실습 실행기의 자식 프로세스. 실행 옵션을 익명 파이프로 받습니다."""
import json
from pathlib import Path
import signal
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.remote_classroom.main import serve


def main():
    options = json.loads(sys.stdin.buffer.readline(8193))
    options["share_client"] = False
    serve(SimpleNamespace(**options))


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"중단: {exc}", file=sys.stderr)
        sys.exit(1)
