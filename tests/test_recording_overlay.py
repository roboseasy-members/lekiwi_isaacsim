"""화면 표시가 기록의 시간·저장 완료 상태를 과장하지 않는지 검사합니다."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "isaac_sim"))
from recording_overlay import clock_text, recording_view


def recorder(mode="READY", frames=0, limit=30, **kwargs):
    return NS(mode=mode, writer=NS(count=frames), duration_seconds=limit,
              playing=True, error="", **kwargs)


@pytest.mark.parametrize("frames,text", [(0, "00:00.0"), (45, "00:01.5"),
    (422, "00:14.1"), (1799, "01:00.0"), (3600, "02:00.0")])
def test_timer_uses_episode_frames(frames, text):
    assert clock_text(frames) == text


def test_f6_stop_and_pending_save_are_not_reported_as_saved():
    for mode in ("FINISHING", "UNSAVED", "SAVING"):
        view = recording_view(recorder(mode, 422))
        assert view.tone == "pending"
        assert view.title != "SAVED"
        assert view.timer == "00:14.1  /  00:30.0"
    assert "F7" in recording_view(recorder("UNSAVED")).hint
    assert recording_view(recorder("SAVED", 422)).title == "SAVED"


def test_unlimited_recording_and_restarting_episode():
    p = recorder("RECORDING", 3000, limit=0)
    view = recording_view(p)
    assert view.timer == "01:40.0  /  NO LIMIT"
    assert view.tone == "recording" and "F6" in view.hint
    p.writer.count = 0
    assert recording_view(p).timer == "00:00.0  /  NO LIMIT"


def test_error_and_arm_stop_are_visible_while_recording():
    p = recorder("RECORDING", 90)
    assert "Stopped" in recording_view(p, NS(armed=False)).arm
    assert "Following" in recording_view(p, NS(armed=True)).arm
    assert recording_view(p).arm == ""
    p.mode, p.error = "ERROR", "Front and wrist render references differ"
    view = recording_view(p)
    assert view.title == "RECORDING ERROR" and view.detail == p.error
    assert "F10" in view.hint


def test_ready_without_writer_and_user_pause():
    p = recorder()
    p.writer = None
    p.playing = False
    view = recording_view(p)
    assert view.timer.startswith("00:00.0")
    assert "Play" in view.hint
