"""장별 로컬 실행과 중복 실행·종료 세션 보호를 검사한다."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("classroom", ROOT / "tools/classroom/main.py")
classroom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classroom)


@pytest.mark.parametrize("lesson", classroom.LESSONS)
def test_each_lesson_has_local_command_and_textbook(lesson):
    args = classroom.command(lesson)
    assert args[0] == str(ROOT / "lekiwi")
    assert args[1] in {"basic", "scene", "record", "dataset"}
    assert "teleop" not in args and "calibrate" not in args
    assert (ROOT / "isaacsim_basic" / classroom.LESSONS[lesson][1] / "README.md").is_file()


def test_applied_lessons_open_course_recording_and_read_only_inventory():
    commands = {name[:2]: classroom.command(name)[1:] for name in classroom.LESSONS}
    assert commands['4장'] == ['scene']
    assert commands['5장'] == ['record']
    # 설정 전 학습·업로드나 실물 연결을 자동 시작하지 않습니다.
    assert commands['6장'] == ['dataset', 'list']


def test_session_guards_duplicate_start_and_stop_uses_launch_identity(tmp_path, monkeypatch):
    calls = []
    class Process:
        returncode = None
        def poll(self): return self.returncode
    def popen(args, **kwargs):
        calls.append((args, kwargs))
        return Process()
    monkeypatch.setattr(classroom.subprocess, "Popen", popen)
    session = classroom.Session(tmp_path)
    session.start(["lekiwi", "basic"])
    token = calls[0][1]["env"]["LEKIWI_CLASSROOM_SESSION"]
    with pytest.raises(RuntimeError):
        session.start(["lekiwi", "scene"])
    session.stop()
    session.stop()
    assert len(calls) == 2
    assert calls[1][0] == [str(ROOT / "lekiwi"), "stop"]
    assert calls[1][1]["env"]["LEKIWI_CLASSROOM_SESSION"] == token
    session.process.returncode = 0
    with pytest.raises(RuntimeError):
        session.start(["lekiwi", "scene"])
