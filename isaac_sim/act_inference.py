"""ACT 추론 상태와 RGB 수신. 모델 계산 중 물리 시간을 멈추고 UI는 계속 갱신합니다."""
from concurrent.futures import ThreadPoolExecutor
import math
import time

import numpy as np

from episode_data import FPS
from policy_bridge import CAMERAS, query, vector
from teleop_bridge import LIMITS


class PolicyControl:
    def __init__(self, path, seconds=30, infer=query, clock=time.monotonic):
        self.path, self.seconds, self.infer, self.clock = path, seconds, infer, clock
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='act-policy')
        self.future = None
        self.armed = False
        self.sequence = 0
        self.reset = True
        self.steps = 0
        self.status = 'READY: R 시작 / SPACE 정지'
        self.hold = None
        self.wait_started = None
        self.started = None
        self.discard_pending = False

    def stop(self, reason='STOPPED: R로 다시 시작'):
        self.armed = False
        self.reset = True
        self.hold = None
        self.wait_started = None
        self.status = reason
        self.discard_pending = self.future is not None

    def update(self, state, simulation_time, snapshot, *, start=False, stop=False, playing=True):
        state = vector(state)
        if stop or not playing:
            self.stop('STOPPED: R로 다시 시작')
        if self.hold is None:
            self.hold = state[:6].copy()
        neutral = np.r_[self.hold, [0., 0., 0.]].astype(np.float32)
        if self.discard_pending:
            if not self.future.done():
                return neutral, True
            self.future = None
            self.discard_pending = False
        if start and playing and not stop and not self.armed:
            self.armed, self.reset, self.steps = True, True, 0
            self.wait_started = self.clock()
        if not self.armed:
            return neutral, True
        if self.steps >= self.seconds * FPS:
            self.stop('FINISHED: 지정 시간 완료 / R로 다시 시작')
            return neutral, True
        try:
            if self.future is None:
                images = snapshot()
                if images is None:
                    if self.clock() - self.wait_started > 10:
                        raise RuntimeError('현재 시각의 두 카메라 영상을 받지 못했습니다.')
                    self.status = 'WARMING UP: 두 카메라 준비 중'
                    return neutral, self.steps == 0
                self.sequence += 1
                self.started = self.clock()
                self.future = self.executor.submit(self.infer, self.path, self.sequence,
                    simulation_time, state.tolist(), images, self.reset)
                self.reset = False
                self.status = 'RUNNING'
                return neutral, False
            if self.clock() - self.started > 5:
                raise RuntimeError('ACT 응답 시간이 초과됐습니다.')
            if not self.future.done():
                return neutral, False
            action = vector(self.future.result())
            self.future = None
            # 기록과 동일한 절대 관절각(rad), base_link 속도(m/s, rad/s)입니다.
            bounds = np.asarray(LIMITS)
            targets = np.clip(action[:6], bounds[:, 0], bounds[:, 1])
            targets = self.hold + np.clip(targets - self.hold, -3.0 / FPS, 3.0 / FPS)
            action[:6] = np.clip(targets, bounds[:, 0], bounds[:, 1])
            speed = np.linalg.norm(action[6:8])
            if speed > 0.5:
                action[6:8] *= 0.5 / speed
            action[8] = np.clip(action[8], -1.6, 1.6)
            self.hold = action[:6].copy()
            self.steps += 1
            self.wait_started = self.clock()
            return action, True
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            self.stop(f'ERROR: {exc} / R로 다시 시작')
            return neutral, True

    def close(self):
        self.stop()
        self.executor.shutdown(wait=False, cancel_futures=True)


class InferenceCameras:
    def __init__(self, camera_paths, config):
        import omni.replicator.core as rep
        from isaacsim.core.nodes.bindings import _isaacsim_core_nodes
        import carb.settings
        self.rep, self.sensors = rep, {}
        self.clock = _isaacsim_core_nodes.acquire_interface()
        settings = carb.settings.get_settings()
        settings.set('/app/asyncRendering', False)
        settings.set('/omni/replicator/asyncRendering', False)
        rep.orchestrator.set_capture_on_play(True)
        for name in CAMERAS:
            product = rep.create.render_product(camera_paths[name]['camera_path'],
                tuple(config['cameras'][name]['resolution']))
            rgb = rep.AnnotatorRegistry.get_annotator('rgb')
            reference = rep.AnnotatorRegistry.get_annotator('ReferenceTime')
            rgb.attach([product.path])
            reference.attach([product.path])
            self.sensors[name] = product, rgb, reference

    def snapshot(self, world):
        images, references = {}, []
        for name, (_, rgb, reference) in self.sensors.items():
            rgba, stamp = np.asarray(rgb.get_data()), reference.get_data()
            if rgba.ndim != 3 or rgba.shape[-1] != 4 or rgba.dtype != np.uint8 or not stamp:
                return None
            ref = (int(stamp['referenceTimeNumerator']), int(stamp['referenceTimeDenominator']))
            if ref[1] <= 0:
                raise ValueError('카메라 렌더 시각이 올바르지 않습니다.')
            captured = float(self.clock.get_sim_time_at_time(ref))
            if not math.isfinite(captured) or not math.isclose(captured, world.current_time, abs_tol=1e-5):
                return None
            images[name] = rgba[:, :, :3].copy()
            references.append(ref)
        return images if references[0] == references[1] else None

    def close(self):
        for product, rgb, reference in self.sensors.values():
            rgb.detach([product.path])
            reference.detach([product.path])
            product.destroy()
