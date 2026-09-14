"""로그인 비밀번호를 익명 표준 입력으로 받아 파일에 쓰지 않고 code-server를 시작합니다."""
import json
import os
import sys

options = json.loads(sys.stdin.buffer.readline(8193))
password = options["password"]
if not isinstance(password, str) or not 12 <= len(password) <= 512:
    raise SystemExit("편집기 비밀번호는 12~512자입니다.")
os.umask(0o077)
os.environ["PASSWORD"] = password
del password, options
os.execv("/usr/bin/entrypoint.sh", ["/usr/bin/entrypoint.sh", "--config", "/opt/lekiwi-editor/editor.yaml",
    "/opt/lekiwi-editor/lekiwi.code-workspace"])
