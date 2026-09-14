"""실습 인자 처리와 WebRTC 래퍼를 거쳐도 공통 프로파일러 설정이 적용되는지 검사합니다."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("mode", ["local", "webrtc"])
@pytest.mark.parametrize("backend", [None, "tracy"])
def test_launcher_survives_student_argv_reset_and_restores_sdk(tmp_path, mode, backend):
    (tmp_path / "isaacsim.py").write_text('''
class SimulationApp:
    def __init__(self, config, experience=""):
        import isaacsim
        assert isaacsim.SimulationApp is type(self)
        self.config = config
        self.experience = experience
''')
    lesson = tmp_path / "student files"
    lesson.mkdir()
    (lesson / "sibling.py").write_text("VALUE = 42\n")
    script = lesson / "student.py"
    script.write_text('''
import argparse, json, sys
from sibling import VALUE
import app_runtime
parser = argparse.ArgumentParser()
parser.add_argument("--label")
parser.add_argument("--backend")
args = parser.parse_args()
sys.argv = [__file__]  # 1~6장 실행기가 학생 파일을 넘길 때 하는 동작입니다.
app_runtime.enable_streaming = lambda app: setattr(app, "streaming", True)
app_runtime.install_student_streaming()
import isaacsim
source = {"headless": False, "extra_args": ["--recording-setting"]}
if args.backend:
    source["profiler_backend"] = [args.backend]
app = isaacsim.SimulationApp(launch_config=source, experience="test.kit")
assert source["extra_args"] == ["--recording-setting"]
print(json.dumps(dict(config=app.config, label=args.label, sibling=VALUE,
                     experience=app.experience, streaming=getattr(app, "streaming", False))))
''')
    command = [sys.executable, str(ROOT / "isaac_sim/sim_launcher.py"), str(script), "--label", "test with spaces"]
    if backend:
        command += ["--backend", backend]
    result = subprocess.run(command, capture_output=True, text=True, env=dict(
        os.environ, PYTHONPATH=str(tmp_path), LEKIWI_DISPLAY_MODE=mode,
        LEKIWI_STREAM_HOST="192.168.0.81"))
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout.splitlines()[-1])
    assert data["label"] == "test with spaces" and data["sibling"] == 42
    assert data["experience"] == "test.kit"
    assert data["streaming"] is (mode == "webrtc")
    extra = data["config"]["extra_args"]
    assert extra[-1] == "--recording-setting"
    if backend:
        assert data["config"]["profiler_backend"] == [backend]
        assert "--/app/profilerBackend=nvtx" not in extra
    else:
        assert extra.count("--/app/profilerBackend=nvtx") == 1
        assert "--/app/profileFromStart=false" in extra


def test_launcher_preserves_explicit_kit_options(tmp_path):
    (tmp_path / "isaacsim.py").write_text('''
class SimulationApp:
    def __init__(self, config):
        self.config = config
''')
    script = tmp_path / "explicit.py"
    script.write_text('''
import isaacsim, json
app = isaacsim.SimulationApp({"extra_args": ["--/app/profileFromStart=true"]})
print(json.dumps(app.config))
''')
    result = subprocess.run([sys.executable, str(ROOT / "isaac_sim/sim_launcher.py"),
        str(script), "--/app/profilerBackend=tracy"], capture_output=True, text=True,
        env=dict(os.environ, PYTHONPATH=str(tmp_path)))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["extra_args"] == ["--/app/profileFromStart=true"]
