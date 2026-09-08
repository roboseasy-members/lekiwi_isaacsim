"""느린 저장장치·저장 실패·종료 시 미완료 에피소드를 완료 처리하지 않는지 검사한다."""
from threading import Event
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'isaac_sim'))
from episode_worker import EpisodeWorker
from episode_data import validate_episode
from test_episode_data import metadata, sample, images


def drained(worker):
    worker.stop()
    worker.stop_future.result(timeout=3)
    assert worker.drained


def test_slow_storage_is_bounded_and_owns_sensor_buffers(tmp_path, monkeypatch):
    worker = EpisodeWorker(tmp_path, metadata())
    entered, release = Event(), Event()
    original = worker.writer.append
    def slow(row, rgb):
        entered.set()
        assert release.wait(3)
        original(row, rgb)
    monkeypatch.setattr(worker.writer, 'append', slow)
    try:
        row, rgb = sample(0), images()
        worker.append(row, rgb)
        assert entered.wait(1)  # append returned while disk work is still blocked.
        row['action'][0] = 999
        rgb['front'][:] = 255
        for i in range(1, worker.MAX_PENDING):
            worker.append(sample(i), images())
        with pytest.raises(RuntimeError, match='Storage cannot keep up'):
            worker.append(sample(worker.MAX_PENDING), images())
        assert worker.count == worker.MAX_PENDING
        release.set()
        drained(worker)
        worker.save()
        worker.operation_future.result(timeout=3)
        worker.poll()
        assert worker.saved
        _, rows = validate_episode(worker.path)
        assert rows[0]['action'][0] == .1
        from PIL import Image
        with Image.open(worker.path / rows[0]['cameras']['front']['path']) as im:
            assert im.getpixel((0, 0)) == (20, 20, 20)
    finally:
        release.set()
        worker.close()


def test_save_completion_is_published_only_after_validation(tmp_path, monkeypatch):
    worker = EpisodeWorker(tmp_path, metadata())
    worker.append(sample(0), images())
    drained(worker)
    entered, release = Event(), Event()
    original = worker.writer.save
    def slow(success):
        entered.set()
        assert release.wait(3)
        return original(success)
    monkeypatch.setattr(worker.writer, 'save', slow)
    try:
        worker.save(True)
        assert entered.wait(1)
        worker.poll()
        assert not worker.saved and worker.path.name.endswith('.partial')
        with pytest.raises(RuntimeError, match='Cannot discard'):
            worker.discard()
        release.set()
        worker.operation_future.result(timeout=3)
        worker.poll()
        assert worker.saved and not worker.path.name.endswith('.partial')
    finally:
        release.set()
        worker.close()


def test_write_failure_is_reported_and_can_be_discarded(tmp_path, monkeypatch):
    worker = EpisodeWorker(tmp_path, metadata())
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(worker.writer, 'append', fail)
    try:
        worker.append(sample(0), images())
        with pytest.raises(OSError, match='disk full'):
            worker.pending[0].result(timeout=3)
        with pytest.raises(OSError, match='disk full'):
            worker.poll()
        worker.discard()
        worker.operation_future.result(timeout=3)
        worker.poll()
        assert worker.discarded and not worker.path.exists() and not worker.saved
    finally:
        worker.close()


def test_failed_validation_is_not_saved_and_can_be_discarded(tmp_path):
    worker = EpisodeWorker(tmp_path, metadata())
    try:
        worker.append(sample(0), images())
        drained(worker)
        (worker.path / 'images/front/000000.png').write_bytes(b'corrupt')
        worker.save()
        with pytest.raises(ValueError, match='checksum'):
            worker.operation_future.result(timeout=3)
        with pytest.raises(ValueError, match='checksum'):
            worker.poll()
        assert not worker.saved and not (worker.path / 'manifest.json').exists()
        worker.discard()
        worker.operation_future.result(timeout=3)
        worker.poll()
        assert worker.discarded
    finally:
        worker.close()


def test_discard_waits_for_queued_writes_and_preserves_saved_take(tmp_path):
    first = EpisodeWorker(tmp_path, metadata())
    first.append(sample(0), images())
    drained(first)
    first.save()
    first.operation_future.result(timeout=3)
    first.poll()
    first.close()
    second = EpisodeWorker(tmp_path, metadata())
    try:
        second.append(sample(0), images())
        second.discard()
        second.operation_future.result(timeout=3)
        second.poll()
        assert not second.path.exists()
        validate_episode(first.path)
    finally:
        second.close()


def test_close_finishes_requested_save_before_app_shutdown(tmp_path):
    worker = EpisodeWorker(tmp_path, metadata())
    worker.append(sample(0), images())
    drained(worker)
    worker.save(True)
    worker.close()
    worker.poll()
    assert worker.saved
    meta, _ = validate_episode(worker.path)
    assert meta['success'] is True


def test_flush_error_prevents_ready_to_save(tmp_path, monkeypatch):
    worker = EpisodeWorker(tmp_path, metadata())
    original = worker.writer.stop
    def fail_flush():
        original()
        raise OSError('flush failed')
    monkeypatch.setattr(worker.writer, 'stop', fail_flush)
    try:
        worker.append(sample(0), images())
        worker.stop()
        with pytest.raises(OSError, match='flush failed'):
            worker.stop_future.result(timeout=3)
        with pytest.raises(OSError, match='flush failed'):
            _ = worker.drained
        assert not worker.saved
    finally:
        worker.close()
