"""SSH 터널을 통해 접속하는 수업용 code-server를 시작합니다."""
import os

os.umask(0o077)
os.execv("/usr/bin/entrypoint.sh", ["/usr/bin/entrypoint.sh", "--config", "/opt/lekiwi-editor/editor.yaml",
    "/opt/lekiwi-editor/lekiwi.code-workspace"])
