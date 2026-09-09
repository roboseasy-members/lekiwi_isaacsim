"""저장 가능한 연속 기록과 누락·수치·상태 짝 오류를 구분한다."""
import copy
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("classroom_recording", Path(__file__).with_name("recording.py"))
recording = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recording)


@pytest.mark.parametrize('mode', ['RECORDING', 'UNSAVED', 'PREPARING', 'REPLAYING', 'ERROR'])
def test_reset_model_does_not_interrupt_unsaved_or_active_work(mode):
    assert not recording.can_reset_model(mode)


@pytest.mark.parametrize('mode', ['READY', 'SAVED', 'REPLAYED', 'DISCARDED'])
def test_reset_model_between_episodes(mode):
    assert recording.can_reset_model(mode)


def sample():
    return [{"current_time": 2+i/60, "current_time_step": 120+i,
             "data": {"frame_index": i, "episode_time": i/60, "next_time": 2+(i+1)/60,
                      "observation": {"joint_position_rad": [i*.01]},
                      "action": {"joint_target_rad": [.1]},
                      "next_observation": {"joint_position_rad": [(i+1)*.01]}}} for i in range(3)]


def test_recording_preserves_input_and_reports_interval_duration():
    frames = sample()
    before = copy.deepcopy(frames)
    assert recording.check_frames(frames) == {"frames": 3, "fps": 60, "duration_s": .05}
    assert frames == before


@pytest.mark.parametrize("kind", ["empty", "gap", "nan", "pair", "time"])
def test_bad_episode_is_rejected_before_save(kind):
    frames = sample()
    if kind == "empty": frames = []
    if kind == "gap": frames[1]["current_time_step"] += 1
    if kind == "nan": frames[0]["data"]["action"]["joint_target_rad"][0] = float("nan")
    if kind == "pair": frames[1]["data"]["observation"]["joint_position_rad"][0] = .5
    if kind == "time": frames[1]["data"]["next_time"] += .1
    with pytest.raises(ValueError): recording.check_frames(frames)
