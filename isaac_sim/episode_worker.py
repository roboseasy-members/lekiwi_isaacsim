"""프레임 수를 제한한 순차 파일 처리. 작업 스레드는 Isaac Sim과 UI에 접근하지 않는다."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from episode_data import EpisodeWriter


class EpisodeWorker:
    MAX_PENDING = 4

    def __init__(self, parent, metadata):
        self.writer = EpisodeWriter(parent, metadata)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="episode-io")
        self.pending = deque()
        self.count = 0
        self.accepting = True
        self.stop_future = None
        self.operation = None
        self.operation_future = None
        self.discarded = False
        self.saved = False
        self.error = None

    @property
    def path(self):
        return self.writer.path

    @property
    def metadata(self):
        return self.writer.metadata

    def poll(self):
        while self.pending and self.pending[0].done():
            try:
                self.pending.popleft().result()
            except Exception as exc:
                self.error = exc
                self.accepting = False
        if self.stop_future is not None and self.stop_future.done():
            try:
                self.stop_future.result()
            except Exception as exc:
                self.error = exc
        if self.operation_future is not None and self.operation_future.done():
            try:
                self.operation_future.result()
                if self.operation == "save":
                    self.saved = self.error is None
                if self.operation == "discard":
                    self.discarded = True
                    self.error = None
            except Exception as exc:
                self.error = exc
        if self.error is not None and self.operation != "discard":
            raise self.error
        if self.operation == "discard" and self.operation_future.done() and not self.discarded:
            raise self.error

    @property
    def drained(self):
        self.poll()
        return not self.pending and self.stop_future is not None and self.stop_future.done()

    def append(self, row, images):
        self.poll()
        if not self.accepting:
            raise RuntimeError("Episode is closed")
        if len(self.pending) >= self.MAX_PENDING:
            raise RuntimeError("Storage cannot keep up: discard this take; no frames were silently dropped")
        # UI·센서 버퍼와 중첩 시각 정보가 다음 프레임에 재사용될 수 있어 복사한다.
        row = deepcopy(row)
        images = {name: image.copy() for name, image in images.items()}
        self.pending.append(self.executor.submit(self.writer.append, row, images))
        self.count += 1

    def stop(self):
        self.accepting = False
        if self.stop_future is None:
            self.stop_future = self.executor.submit(self.writer.stop)

    def save(self, success=False):
        self.poll()
        if not self.drained or self.operation is not None:
            raise RuntimeError("Episode is not ready to save")
        self.operation = "save"
        self.operation_future = self.executor.submit(self.writer.save, success)

    def discard(self):
        if self.saved or (self.operation == "save" and not self.operation_future.done()):
            raise RuntimeError("Cannot discard a saved or saving episode")
        self.stop()
        self.operation = "discard"
        self.operation_future = self.executor.submit(self.writer.discard)

    def close(self):
        self.stop()
        # 완료된 기록을 교체하거나 앱을 종료할 때만 기다린다.
        self.executor.shutdown(wait=True)
