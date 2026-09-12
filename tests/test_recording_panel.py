"""실제 패널 제어 흐름의 시간 제한, 수동 종료와 설정 고정을 검사한다."""
from collections import deque
from pathlib import Path
from types import SimpleNamespace as NS
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'isaac_sim'))
from recording_panel import RecordingPanel


@pytest.mark.parametrize('override', [None, '', 'Pick up the red cube'])
def test_student_task_description_is_used_unless_explicitly_overridden(tmp_path, monkeypatch, override):
    # 렌더러와 파일 생성만 대체하고 실제 학생 코드의 설정 읽기를 실행합니다.
    settings = NS(set=lambda *a: None, get=lambda *a: False)
    annotator = NS(attach=lambda *a: None)
    rep = NS(orchestrator=NS(set_capture_on_play=lambda *a: None),
             create=NS(render_product=lambda *a: NS(path='/test')),
             AnnotatorRegistry=NS(get_annotator=lambda *a: annotator))
    bindings = NS(_isaacsim_core_nodes=NS(acquire_interface=lambda: None))
    for name, module in {
        'omni': NS(replicator=NS(core=rep)), 'omni.replicator': NS(core=rep),
        'omni.replicator.core': rep, 'carb': NS(settings=NS(get_settings=lambda: settings)),
        'carb.settings': NS(get_settings=lambda: settings),
        'isaacsim.core.nodes.bindings': bindings,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)
    globals_ = RecordingPanel.__init__.__globals__
    monkeypatch.setitem(globals_, 'Path', lambda *_: tmp_path)
    monkeypatch.setitem(globals_, 'task_description', '리더암을 좌우로 움직이기')
    if override is None:
        monkeypatch.delenv('LEKIWI_RECORD_TASK', raising=False)
    else:
        monkeypatch.setenv('LEKIWI_RECORD_TASK', override)
    cameras = {name: {'camera_path': '/test'} for name in ('front', 'wrist')}
    config = {'cameras': {name: {'resolution': [2, 2]} for name in cameras}}
    p = RecordingPanel(cameras, config, 'test', {})
    assert p.task_text == (override or '리더암을 좌우로 움직이기')


def panel(tmp_path, seconds):
    p = RecordingPanel.__new__(RecordingPanel)
    p.duration_seconds = seconds
    p.task_text = "Move forward and stop"
    p.task_succeeded = False
    p.discard_deadline = 0.0
    p.last_status = None
    p.warmup_time = None
    p.warmup_frames = 0
    p.playing = True
    p.resume_frames = 0
    p.mode, p.error = 'READY', ''
    p.writer = p.pending = p.last_saved = p.capture = None
    p.waiting = deque()
    p.directory, p.metadata, p.requests = tmp_path, {}, []
    p.snapshot = lambda world: ({}, {})
    return p


@pytest.mark.parametrize('seconds', [0, 30, 120, 300])
def test_start_captures_setting_and_locks_input(tmp_path, seconds):
    p = panel(tmp_path, seconds)
    p.task_text = "빨간 큐브를 빨간 바구니에 넣기"
    p.requests = ['record']
    p.before_step(NS(current_time=0, is_playing=lambda: True), [0]*9, [0]*9, [0]*7)
    assert p.mode == 'RECORDING'
    assert p.duration_seconds == seconds
    assert p.writer.metadata['max_duration_seconds'] == seconds
    assert p.writer.metadata['task'] == "빨간 큐브를 빨간 바구니에 넣기"
    assert p.duration_seconds == seconds  # 기록 중 모델 값이 바뀌어도 현재 기록의 상한은 유지한다.
    p.requests = ['stop']
    p.before_step(NS(current_time=0, is_playing=lambda: True), [0]*9, [0]*9, [0]*7)
    p.writer.stop_future.result(timeout=2)
    p.finish_if_drained()
    assert p.mode == 'UNSAVED'
    p.requests = ['discard']
    p.before_step(NS(current_time=0, is_playing=lambda: True), [0]*9, [0]*9, [0]*7)
    p.writer.operation_future.result(timeout=2)
    p.poll_io(); p.refresh()
    assert p.mode == 'DISCARDED'


@pytest.mark.parametrize('seconds,count,expected', [
    (30, 899, 'FINISHING'),
    (120, 899, 'RECORDING'),
    (120, 3598, 'RECORDING'),
    (120, 3599, 'FINISHING'),
    (0, 899, 'RECORDING'),
    (0, 90000, 'RECORDING'),
])
def test_configured_boundary_stops_without_saving(tmp_path, seconds, count, expected):
    p = panel(tmp_path, seconds)
    p.duration_seconds, p.mode = seconds, 'RECORDING'
    p.pending = {"simulation_time": 1-1/30}
    writer = NS(count=count, stopped=False)
    def append(*args): writer.count += 1
    def stop(): writer.stopped = True
    writer.append, writer.stop = append, stop
    p.writer = writer
    p.after_step(NS(current_time=1), [0]*9)
    assert p.mode == expected
    assert not writer.stopped  # 마지막 영상이 도착하기 전에는 파일을 닫지 않는다.
    assert len(p.waiting) == 1
    assert p.last_status[0] == expected


def test_snapshot_does_not_change_timeline_and_uses_capture_time(tmp_path):
    import numpy as np
    p = panel(tmp_path, 30)
    p.core_clock = NS(get_sim_time_at_time=lambda ref: 2.0)
    p.sensors = {name: (None, NS(get_data=lambda: np.zeros((2, 2, 4), dtype=np.uint8)),
                       NS(get_data=lambda: {'referenceTimeNumerator': 60, 'referenceTimeDenominator': 30}))
                 for name in ('front', 'wrist')}
    p.providers = {name: NS(set_data_array=lambda *args: None) for name in p.sensors}
    # pause/play/step이 없는 월드에서도 촬영 결과 읽기가 가능해야 한다.
    images, stamps = RecordingPanel.snapshot(p, NS(current_time=2.0))
    assert images['front'].shape == (2, 2, 3)
    assert stamps['wrist']['simulation_time'] == 2.0


def test_snapshot_preserves_delayed_rgb_time(tmp_path):
    import numpy as np
    p = panel(tmp_path, 30)
    p.core_clock = NS(get_sim_time_at_time=lambda ref: 1.0)
    p.sensors = {name: (None, NS(get_data=lambda: np.zeros((2, 2, 4), dtype=np.uint8)),
                       NS(get_data=lambda: {'referenceTimeNumerator': 30, 'referenceTimeDenominator': 30}))
                 for name in ('front', 'wrist')}
    p.providers = {name: NS(set_data_array=lambda *args: None) for name in p.sensors}
    _, stamps = RecordingPanel.snapshot(p, NS(current_time=2.0))
    assert stamps["front"]["simulation_time"] == 1.0  # 현재 2초로 덮어쓰지 않는다.


class Writer:
    def __init__(self):
        self.count, self.rows, self.stopped = 0, [], False
        self.drained = True

    def poll(self):
        pass

    def append(self, row, images):
        self.rows.append((row, images))
        self.count += 1

    def stop(self):
        self.stopped = True


def queued_panel(tmp_path, mode='RECORDING'):
    p = panel(tmp_path, 30)
    p.mode, p.writer = mode, Writer()
    p.last_world_time = 2.1
    p.waiting.extend([{'simulation_time':2.0, 'action':[10]},
                      {'simulation_time':2+1/30, 'action':[20]}])
    return p


def stamps(t):
    return {n:{'simulation_time':t,'render_reference':[round(t*30),30]}
            for n in ('front','wrist')}


def test_delayed_rgb_pairs_with_original_action_and_drains_before_stop(tmp_path):
    p = queued_panel(tmp_path, 'FINISHING')
    p.accept_capture({'front':'old'}, stamps(1.9))
    assert p.writer.count == 0 and len(p.waiting) == 2
    p.accept_capture({'front':'first'}, stamps(2.0))
    assert p.writer.rows[0][0]['action'] == [10]
    assert p.writer.rows[0][1]['front'] == 'first'
    assert p.mode == 'FINISHING' and not p.writer.stopped
    p.accept_capture({}, stamps(2.0))  # 동일 영상은 중복 기록하지 않는다.
    assert p.writer.count == 1
    p.accept_capture({'front':'second'}, stamps(2+1/30))
    assert p.writer.rows[1][0]['action'] == [20]
    assert p.mode == 'UNSAVED' and p.writer.stopped and not p.waiting


def test_missing_rgb_frame_is_rejected(tmp_path):
    p = queued_panel(tmp_path)
    with pytest.raises(ValueError, match='missing'):
        p.accept_capture({}, stamps(2+1/30))
    assert p.writer.count == 0


def test_camera_stall_while_finishing_fails(tmp_path):
    p = queued_panel(tmp_path, 'FINISHING')
    p.last_world_time = 3.1
    with pytest.raises(ValueError, match='stalled'):
        p.accept_capture({}, stamps(1.9))


def test_user_pause_is_preserved_and_marks_episode_incomplete(tmp_path):
    p = queued_panel(tmp_path)
    p.snapshot = lambda world: ({}, stamps(1.9))
    p.before_step(NS(current_time=2.1, is_playing=lambda: False), [0]*9, [0]*9, [0]*7)
    assert p.mode == 'ERROR' and p.writer.stopped and not p.waiting
    assert 'paused' in p.error


def test_capture_queue_cannot_grow_without_bound(tmp_path):
    p = queued_panel(tmp_path)
    p.waiting.extend([{'simulation_time':2.0}]*28)
    p.pending = {'simulation_time':3.0}
    p.after_step(NS(current_time=3+1/30), [0]*9)
    assert p.mode == 'ERROR' and p.writer.stopped and not p.waiting


def test_camera_failure_does_not_block_discard_or_overwrite_original_error(tmp_path):
    p = panel(tmp_path, 30)
    p.requests = ['record']
    world = NS(current_time=0, is_playing=lambda: True)
    p.before_step(world, [0]*9, [0]*9, [0]*7)
    partial = p.writer.path
    p.fail(ValueError('original capture failure'))
    def unavailable(world):
        raise AssertionError('Do not depend on a failed camera for recovery')
    p.snapshot = unavailable
    p.before_step(world, [], [], [])
    assert p.error == 'original capture failure'
    p.requests = ['discard']
    p.before_step(world, [], [], [])
    p.writer.operation_future.result(timeout=2)
    p.poll_io()
    assert p.mode == 'DISCARDED' and p.writer is None and p.pending is None
    assert not partial.exists()


def test_ready_clears_camera_warmup_message(tmp_path):
    p = panel(tmp_path, 30)
    p.mode, p.error = 'WARMING UP', 'front: waiting for RGB'
    p.snapshot = lambda world: ({}, stamps(world.current_time))
    for i in range(6):
        p.before_step(NS(current_time=i/30, is_playing=lambda: True), [], [], [])
    assert p.mode == 'READY' and p.error == ''
    assert p.last_status[2] == ''


def test_paused_preview_does_not_query_camera_clock(tmp_path):
    p = panel(tmp_path, 30)
    def forbidden(world):
        raise AssertionError('No camera clock lookup while paused')
    p.snapshot = forbidden
    p.before_step(NS(current_time=2, is_playing=lambda: False), [], [], [])
    assert p.mode == 'READY' and not p.playing
    assert p.error == ''


def test_error_without_writer_can_be_discarded(tmp_path):
    p = panel(tmp_path, 30)
    p.mode, p.error, p.requests = 'ERROR', 'camera failed', ['discard']
    p.before_step(NS(), [], [], [])
    assert p.mode == 'DISCARDED' and p.writer is None


def test_resume_waits_for_fresh_render_clock_samples(tmp_path):
    p = panel(tmp_path, 30)
    p.playing = False
    snapshots = []
    p.snapshot = lambda world: (snapshots.append(world.current_time) or {}, {})
    for i in range(3):
        p.before_step(NS(current_time=i/30, is_playing=lambda: True), [], [], [])
    assert snapshots == []
    p.before_step(NS(current_time=.1, is_playing=lambda: True), [], [], [])
    assert snapshots == [.1]


def test_keyboard_save_requires_unsaved_and_records_outcome(tmp_path):
    p = panel(tmp_path, 30)
    p.handle_key("F9")
    assert p.requests == []
    p.mode = "UNSAVED"
    p.handle_key("F9")
    assert p.requests == ["save"] and p.task_succeeded
    p.requests.clear()
    p.handle_key("F7")
    assert p.requests == ["save"] and not p.task_succeeded


def test_discard_requires_two_deliberate_presses(tmp_path, monkeypatch):
    p = panel(tmp_path, 30)
    p.mode = "UNSAVED"
    p.handle_key("F10")
    assert p.requests == []
    p.handle_key("F10")
    assert p.requests == ["discard"]
    p.requests.clear()
    p.discard_deadline = 0.0
    p.handle_key("F10")
    p.discard_deadline = 0.0  # 기한이 지난 첫 입력은 폐기를 승인하지 않습니다.
    p.handle_key("F10")
    assert p.requests == []


def test_warmup_restarts_after_missing_camera_frame(tmp_path):
    p = panel(tmp_path, 30)
    p.mode = "WARMING UP"
    p.snapshot = lambda world: ({}, stamps(world.current_time))
    for i in [0, 1, 2, 4, 5, 6, 7, 8]:
        p.before_step(NS(current_time=i/30, is_playing=lambda: True), [], [], [])
    assert p.mode == "WARMING UP" and p.warmup_frames == 5
    p.before_step(NS(current_time=9/30, is_playing=lambda: True), [], [], [])
    assert p.mode == "READY"


def test_zero_delay_rgb_is_kept_until_next_state_is_known(tmp_path):
    p = panel(tmp_path, 30)
    p.mode, p.writer = "RECORDING", Writer()
    p.snapshot = lambda world: ({"front": "at_t", "wrist": "at_t"}, stamps(world.current_time))
    p.before_step(NS(current_time=2.0, is_playing=lambda: True), [1]*9, [2]*9, [0]*7)
    assert p.writer.count == 0
    p.after_step(NS(current_time=2+1/30), [3]*9)
    assert p.writer.count == 1 and not p.waiting
    row, images = p.writer.rows[0]
    assert row["simulation_time"] == row["cameras"]["front"]["simulation_time"] == 2.0
    assert row["next_observation.state"] == [3]*9
    assert row["action"] == [2]*9 and images["front"] == "at_t"
