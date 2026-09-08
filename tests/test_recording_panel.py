"""실제 패널 제어 흐름의 시간 제한, 수동 종료와 설정 고정을 검사한다."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'isaac_sim'))
from recording_panel import RecordingPanel


class Model:
    def __init__(self, value):
        self.as_int = value
        self.as_bool = bool(value)

    def set_value(self, value):
        self.as_int = value
        self.as_bool = bool(value)


def panel(tmp_path, seconds):
    p = RecordingPanel.__new__(RecordingPanel)
    p.duration_seconds = 30
    p.duration = NS(model=Model(seconds))
    p.task = NS(model=NS(get_item_value_model=lambda: Model(0)))
    p.success = NS(model=Model(False))
    for name in ('status', 'detail', 'output', 'record', 'stop', 'save', 'discard'):
        setattr(p, name, NS())
    p.mode, p.error = 'READY', ''
    p.writer = p.pending = p.last_saved = None
    p.directory, p.metadata, p.requests = tmp_path, {}, []
    p.snapshot = lambda world: ({}, {})
    return p


@pytest.mark.parametrize('seconds', [0, 30, 120, 300])
def test_start_captures_setting_and_locks_input(tmp_path, seconds):
    p = panel(tmp_path, seconds)
    p.requests = ['record']
    p.before_step(NS(current_time=0, is_playing=lambda: True), [0]*9, [0]*9, [0]*7)
    assert p.mode == 'RECORDING'
    assert p.duration_seconds == seconds
    assert not p.duration.enabled
    assert p.writer.metadata['max_duration_seconds'] == seconds
    p.duration.model.set_value(1)
    assert p.duration_seconds == seconds  # 기록 중 모델 값이 바뀌어도 현재 기록의 상한은 유지한다.
    p.requests = ['stop']
    p.before_step(NS(current_time=0), [0]*9, [0]*9, [0]*7)
    assert p.mode == 'UNSAVED' and not p.duration.enabled
    p.requests = ['discard']
    p.before_step(NS(current_time=0), [0]*9, [0]*9, [0]*7)
    assert p.mode == 'DISCARDED' and p.duration.enabled


@pytest.mark.parametrize('seconds,count,expected', [
    (30, 899, 'UNSAVED'),
    (120, 899, 'RECORDING'),
    (120, 3598, 'RECORDING'),
    (120, 3599, 'UNSAVED'),
    (0, 899, 'RECORDING'),
    (0, 90000, 'RECORDING'),
])
def test_configured_boundary_stops_without_saving(tmp_path, seconds, count, expected):
    p = panel(tmp_path, seconds)
    p.duration_seconds, p.mode = seconds, 'RECORDING'
    p.pending = ({}, {})
    writer = NS(count=count, stopped=False)
    def append(*args): writer.count += 1
    def stop(): writer.stopped = True
    writer.append, writer.stop = append, stop
    p.writer = writer
    p.after_step(NS(current_time=1), [0]*9)
    assert p.mode == expected
    assert writer.stopped == (expected == 'UNSAVED')
    assert ('no limit' if seconds == 0 else f'{seconds} s max') in p.status.text
