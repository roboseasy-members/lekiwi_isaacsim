"""5장 · 빨주노초 맵에서 두 카메라와 상태·명령을 수집하는 공통 코드.

기존 실행기와 연결되어 있어 파일 위치는 06_lekiwi_dataset에 유지합니다.
실행 위치: 같은 노트북의 저장소 최상위 폴더 터미널.
키보드 기록 검사: ./lekiwi record
리더 집기 시연: 5장 README의 실제 USB 경로를 넣은 teleop 명령에 --record를 추가합니다.
기존 ./lekiwi basic --chapter 6도 키보드 기록 예제로 유지합니다.

읽는 순서
1. task_description / __init__의 duration_seconds: 과제와 최대 기록 시간을 정합니다.
2. handle_key(): F5 시작·F6 종료·F7 연습 저장·F9 성공 저장·F10 두 번 폐기를 요청합니다.
3. before_step()/after_step(): 30 Hz의 명령 전 상태와 명령 적용 뒤 상태를 연결합니다.
4. snapshot()/accept_capture(): front·wrist의 실제 촬영 시각을 확인하고 같은 시각의 상태와 묶습니다.
5. EpisodeWorker / poll_io(): 파일 쓰기를 처리하고 완료되면 SAVED로 바꿉니다.

바꿔 볼 값: 과제 설명과 기록 길이. LEKIWI_RECORD_TASK/SECONDS 환경변수가 코드 기본값보다 우선합니다.
화면: READY → F5 → RECORDING → F6 → FINISHING → UNSAVED → F7/F9 → SAVED.
결과: data/recordings/ 아래 manifest.json·frames.jsonl·images/front·images/wrist.
시간 정렬·오류 검사 코드는 기록 품질을 지키므로 첫 실습에서는 그대로 둡니다.
RecordingPanel이라는 이름은 기록 상태를 관리하는 클래스이며 별도 패널 클릭을 요구하지 않습니다.
자세한 코드 읽기: isaacsim_basic/CODE_GUIDE.md"""
from collections import deque
import math
from pathlib import Path
import tempfile
import os
import sys
import time

# 이번 시연에서 수행할 작업 설명입니다. 같은 작업을 반복 수집할 때는 같은 문장을 사용합니다.
task_description = "Move forward and stop"
# task_description = "빨간 큐브를 빨간 바구니에 넣기"  # 집기 실습에서는 위 줄 대신 사용합니다.

# 프로젝트 기록 형식·검증·백그라운드 파일 쓰기를 재사용합니다.
SIM_DIRECTORY = Path(__file__).resolve().parents[3] / "isaac_sim"
sys.path.insert(0, str(SIM_DIRECTORY))

import numpy as np
from episode_data import CAMERAS, FPS
from episode_worker import EpisodeWorker


class RecordingPanel:
    """기록 요청·영상 시각·상태 전환·저장 완료를 관리합니다. 로봇 조작은 호출하는 실행기가 담당합니다."""
    def __init__(self, camera_paths, config, source, layout):
        """두 카메라 센서와 저장 위치를 준비하고, 초기 영상이 연속으로 도착할 때까지 기다립니다."""
        import omni.replicator.core as rep

        from isaacsim.core.nodes.bindings import _isaacsim_core_nodes

        self.core_clock = _isaacsim_core_nodes.acquire_interface()
        import carb.settings
        # 5.1 공식 Replicator 문제 해결: 비동기 렌더에서 프레임을 건너뛰지 않도록 동기로 고정합니다.
        # 앱 시작 시 enable_async=false도 지정해 타임라인 정지 후 자동 전환을 막습니다.
        settings = carb.settings.get_settings()
        settings.set("/app/asyncRendering", False)
        settings.set("/omni/replicator/asyncRendering", False)
        print(f"LEKIWI_RECORD async_rendering={settings.get('/app/asyncRendering')}", flush=True)
        rep.orchestrator.set_capture_on_play(True)  # 물리가 재생될 때 Render Product의 영상 생성을 활성화합니다.
        self.sensors = {}
        for name in CAMERAS:
            product = rep.create.render_product(camera_paths[name]["camera_path"],  # 카메라와 출력 픽셀 해상도를 연결한 Render Product를 만듭니다.
                                                tuple(config["cameras"][name]["resolution"]))
            rgb = rep.AnnotatorRegistry.get_annotator("rgb")  # 카메라의 RGBA 픽셀을 CPU로 읽을 annotator를 가져옵니다.
            reference = rep.AnnotatorRegistry.get_annotator("ReferenceTime")  # 영상이 실제로 렌더된 시각 표식을 읽습니다. 현재 시각으로 대신하지 않습니다.
            rgb.attach([product.path])  # RGB annotator를 해당 Render Product에 연결합니다.
            reference.attach([product.path])  # 촬영 시각 annotator도 같은 Render Product에 연결합니다.
            self.sensors[name] = (product, rgb, reference)
        parent = Path("/data/recordings")
        parent.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix="lekiwi.", dir=parent))
        self.metadata = {"robot_type": "lekiwi_sim", "source": source,
                         "camera_config": config, "course_layout": layout,
                         "timing": "RGB and state at t; action applied over [t, t+1/30); next state at t+1/30"}
        self.writer = None
        self.pending = None
        self.capture = None  # 명령 직전 영상은 후속 상태가 계산될 때까지 보관합니다.
        self.waiting = deque()
        self.requests = []
        self.mode = "WARMING UP"
        self.last_saved = None
        self.error = ""
        self.interruption = ""
        self.duration_seconds = 30  # 기본: 최대 30초
        # self.duration_seconds = 120  # 다음 실습: 위 줄 대신 2분
        # self.duration_seconds = 0  # 다음 실습: 수동 F6 종료까지 무제한
        # 터미널에서 지정한 값이 있으면 코드 기본값보다 우선합니다.
        self.duration_seconds = int(os.environ.get("LEKIWI_RECORD_SECONDS") or self.duration_seconds)
        if self.duration_seconds < 0:
            raise ValueError("LEKIWI_RECORD_SECONDS는 0 이상의 정수입니다.")
        # 비어 있지 않은 환경변수만 우선하며, 설명은 에피소드와 학습 데이터의 task 항목으로 저장됩니다.
        self.task_text = os.environ.get("LEKIWI_RECORD_TASK") or task_description
        self.task_succeeded = False
        self.discard_deadline = 0.0
        self.last_status = None
        self.warmup_time = None
        self.warmup_frames = 0
        self.playing = True
        self.resume_frames = 0
        print(f"LEKIWI_RECORD directory={self.directory}", flush=True)

    def snapshot(self, world):
        """두 카메라의 RGB와 실제 촬영 시각을 읽습니다. 서로 다른 시각의 영상이면 기록을 진행하지 않습니다."""
        images, stamps = {}, {}
        references = []
        for name, (_, rgb, reference) in self.sensors.items():
            rgba = np.asarray(rgb.get_data())  # 가장 최근 도착한 RGBA 배열을 읽습니다. 물리보다 늦게 도착할 수 있습니다.
            data = reference.get_data()  # 이 영상의 촬영 시각 분자/분모를 읽습니다.
            if rgba.ndim != 3 or rgba.shape[2] != 4 or not data:
                raise ValueError(f"{name}: waiting for RGB")
            ref = [int(data["referenceTimeNumerator"]), int(data["referenceTimeDenominator"])]
            references.append(ref)
            captured = float(self.core_clock.get_sim_time_at_time(tuple(ref)))  # 렌더 시각 표식을 물리 시뮬레이션 초로 환산합니다.
            if not math.isfinite(captured) or captured < 0 or captured > world.current_time + 1e-6:
                raise ValueError(f"{name}: invalid RGB capture time")
            images[name] = rgba[:, :, :3].copy()  # 알파 채널을 제외한 RGB를 복사해 다음 렌더링에 덮어쓰이지 않게 합니다.
            stamps[name] = {"simulation_time": captured, "render_reference": ref}
        if (references[0] != references[1]
                or abs(stamps["front"]["simulation_time"] - stamps["wrist"]["simulation_time"]) > 1e-6):
            raise ValueError("Front and wrist render references differ")
        return images, stamps

    def interrupt(self, reason):
        """통신 단절 전까지의 기록을 마감합니다. 저장은 사용자가 F7로 확인합니다."""
        self.requests = [request for request in self.requests if request != "record"]
        if self.mode in {"RECORDING", "FINISHING"}:
            if not self.interruption:
                print(f"LEKIWI_RECORD interrupted={reason}; F7 연습 저장 또는 F10 두 번 폐기", flush=True)
            self.interruption = reason
            self.task_succeeded = False
            self.pending = None
            self.mode = "FINISHING"

    def before_step(self, world, state, action, base_pose, *, control_ready=True):
        # 같은 시각의 영상과 명령을 연결합니다. 지연 영상도 촬영 시각으로 검증합니다.
        """명령 직전의 상태·행동·영상을 준비하고, 키보드가 요청한 기록 시작·종료·저장을 처리합니다."""
        self.capture = None
        try:
            # 카메라 오류가 계속돼도 미완료 기록을 버릴 수 있어야 한다.
            if "discard" in self.requests and self.mode in {"RECORDING", "FINISHING", "UNSAVED", "ERROR"}:
                if self.writer and not self.writer.saved:
                    self.writer.discard()  # 현재 미저장 기록의 폐기를 요청합니다. 이미 저장된 에피소드는 유지합니다.
                    self.mode = "DISCARDING"
                else:
                    if self.writer:
                        self.writer.close()  # 이 기록 작업자의 남은 작업과 자원을 정리합니다.
                    self.writer = None
                    self.mode = "DISCARDED"
                self.pending = None
                self.waiting.clear()
                self.error = ""
                self.requests.clear()
                self.refresh()
                return
            if self.mode == "ERROR":
                self.requests.clear()
                self.refresh()
                return
            self.poll_io()
            sim_time = self.last_world_time = world.current_time
            was_playing = self.playing
            self.playing = world.is_playing()
            if self.playing and not was_playing:
                self.resume_frames = 3
            if not self.playing and self.mode in {"RECORDING", "FINISHING"}:
                raise ValueError("Simulation paused: discard this take and start after Play")
            # 일시정지 중에는 새로운 물리 시각 표식이 없으므로 영상 시각을 조회하지 않습니다.
            if self.playing and self.resume_frames:
                self.resume_frames -= 1
            elif self.playing:
                images, stamps = self.snapshot(world)
                self.capture = (images, stamps)
                if self.mode == "WARMING UP":
                    # 첫 영상 한 장으로 기록을 시작하지 않습니다. 셰이더 준비 중 시각이 건너뛸 수 있습니다.
                    captured = stamps["front"]["simulation_time"]
                    continuous = (self.warmup_time is not None and
                                  math.isclose(captured - self.warmup_time, 1/FPS, abs_tol=1e-6))
                    self.warmup_frames = self.warmup_frames + 1 if continuous else 1
                    self.warmup_time = captured
                    if self.warmup_frames >= 6:
                        self.mode, self.error = "READY", ""
                self.accept_capture(images, stamps)
            self.finish_if_drained()
            for request in self.requests:
                if request == "record" and self.mode in {"READY", "SAVED", "DISCARDED"}:
                    if not self.playing or self.resume_frames or not control_ready:
                        continue
                    if self.writer:
                        self.writer.close()  # 이 기록 작업자의 남은 작업과 자원을 정리합니다.
                    self.writer = EpisodeWorker(self.directory, dict(
                        self.metadata, task=self.task_text, max_duration_seconds=self.duration_seconds))
                    self.waiting.clear()
                    self.mode, self.error = "RECORDING", ""
                    self.interruption = ""
                    self.task_succeeded = False
                elif request == "stop" and self.mode == "RECORDING":
                    self.mode = "FINISHING"
                    self.finish_if_drained()
                elif request == "save" and self.mode == "UNSAVED":
                    self.writer.save(self.task_succeeded and not self.interruption)
                    self.mode = "SAVING"
            self.requests.clear()
            if self.mode == "RECORDING":
                self.pending = {"simulation_time": float(sim_time),
                                "observation.state": state, "action": action, "base_pose": base_pose}
        except Exception as exc:
            self.requests.clear()
            if self.mode == "WARMING UP":
                self.error = str(exc)
            else:
                self.fail(exc)
        self.refresh()

    def after_step(self, world, next_state):
        """명령 적용 뒤 상태를 추가합니다. 1/30초 간격을 확인하고 같은 시각 영상과 연결합니다."""
        if self.pending is None:
            return
        row, self.pending = self.pending, None
        try:
            row.update({"next_observation.state": next_state, "next_simulation_time": float(world.current_time)})
            if not math.isclose(row["next_simulation_time"] - row["simulation_time"], 1/FPS, abs_tol=1e-6):
                raise ValueError("Simulation frame gap: expected 1/30 s")
            self.waiting.append(row)
            if len(self.waiting) > FPS:
                raise ValueError("RGB capture stalled: more than 1 s of observations waiting")
            if self.duration_seconds > 0 and self.writer.count + len(self.waiting) >= self.duration_seconds * FPS:
                self.mode = "FINISHING"
            if self.capture is not None:
                # 동기 렌더의 t 영상은 이미 before_step에서 읽었습니다. t+dt 상태와 합칩니다.
                self.accept_capture(*self.capture)
        except Exception as exc:
            self.fail(exc)
        self.refresh()

    def accept_capture(self, images, stamps):
        """가장 오래 기다린 상태와 영상의 촬영 시각이 일치할 때 한 프레임을 저장 작업자에게 넘깁니다."""
        if not self.waiting or self.mode not in {"RECORDING", "FINISHING"}:
            return
        row = self.waiting[0]
        captured = stamps["front"]["simulation_time"]
        if captured < row["simulation_time"] - 1e-6:
            # 초기 지연 또는 같은 렌더 결과: 현재 시각으로 덮어쓰지 않는다.
            if self.mode == "FINISHING" and self.last_world_time - row["simulation_time"] > 1.0:
                raise ValueError("RGB capture stalled while finishing")
            return
        if abs(captured - row["simulation_time"]) > 1e-6:
            raise ValueError(f"RGB frame missing for queued observation time: expected={row['simulation_time']:.6f} captured={captured:.6f}")
        row["cameras"] = stamps
        self.writer.append(row, images)  # 촬영 시각이 일치한 상태·명령·RGB를 저장 작업자에게 전달합니다.
        self.waiting.popleft()
        self.finish_if_drained()

    def finish_if_drained(self):
        """종료 요청 뒤 남은 프레임과 파일 쓰기가 끝나면 사용자의 저장 결정을 기다립니다."""
        if self.mode == "FINISHING" and not self.waiting:
            self.writer.stop()  # 새 프레임 입력을 끝내고 대기 중 파일 쓰기가 완료되도록 합니다.
            if self.writer.drained:
                self.mode = "UNSAVED"

    def poll_io(self):
        """비동기 파일 작업 결과를 확인합니다. 저장 요청과 실제 SAVED 완료를 구분합니다."""
        if not self.writer:
            return
        self.writer.poll()  # 백그라운드 저장 완료 또는 오류를 확인합니다. 긴 파일 작업으로 UI를 막지 않습니다.
        if self.mode == "SAVING" and self.writer.saved:
            self.last_saved = self.writer.path
            self.mode = "SAVED"
            print(f"LEKIWI_RECORD saved={self.last_saved} frames={self.writer.count}", flush=True)
        elif self.mode == "DISCARDING" and self.writer.discarded:
            self.writer.close()  # 이 기록 작업자의 남은 작업과 자원을 정리합니다.
            self.writer = None
            self.mode, self.error = "DISCARDED", ""

    def fail(self, exc):
        """오류 뒤 새 프레임 입력을 멈추고 ERROR 상태를 알립니다. 정상 데이터로 자동 저장하지 않습니다."""
        self.pending = None
        self.waiting.clear()
        if self.writer:
            self.writer.stop()  # 새 프레임 입력을 끝내고 대기 중 파일 쓰기가 완료되도록 합니다.
        if self.mode != "ERROR":
            print(f"LEKIWI_RECORD error={exc}", flush=True)
        self.mode, self.error = "ERROR", str(exc)

    def handle_key(self, key):
        """입력 콜백은 요청만 넣습니다. 물리/파일 작업은 주 반복문에서 처리합니다."""
        if key == "F5":
            self.requests.append("record")
        elif key == "F6":
            self.requests.append("stop")
        elif key in {"F7", "F9"} and self.mode == "UNSAVED":
            if key == "F9" and self.interruption:
                print("LEKIWI_RECORD 통신으로 중단된 기록은 F7 연습 저장 또는 F10 두 번 폐기하세요.", flush=True)
                return
            self.task_succeeded = key == "F9"
            self.requests.append("save")
        elif key == "F10" and self.mode in {"RECORDING", "FINISHING", "UNSAVED", "ERROR"}:
            now = time.monotonic()
            if now < self.discard_deadline:
                self.requests.append("discard")
                self.discard_deadline = 0.0
            else:
                self.discard_deadline = now + 3.0
                print("LEKIWI_RECORD 미저장 기록을 폐기하려면 3초 안에 F10을 다시 누르세요.", flush=True)

    def refresh(self):
        """상태가 바뀌거나 기록 시간이 늘었을 때 터미널 진행 상황을 갱신합니다."""
        count = self.writer.count if self.writer else 0
        # 프레임마다 출력하면 조작이 느려지므로 상태 변화 또는 시뮬레이션 1초마다 출력합니다.
        status = (self.mode, count // FPS, self.error)
        if status != self.last_status:
            limit = f"{self.duration_seconds} s max" if self.duration_seconds else "no limit"
            print(f"LEKIWI_RECORD state={self.mode} frames={count} seconds={count/FPS:.2f} "
                  f"limit={limit} error={self.error}", flush=True)
            self.last_status = status

    def close(self):
        """저장 작업을 마무리하고 미완료 기록이 남으면 경로를 알립니다."""
        if self.writer:
            self.writer.close()  # 이 기록 작업자의 남은 작업과 자원을 정리합니다.
            self.writer.poll()  # 백그라운드 저장 완료 또는 오류를 확인합니다. 긴 파일 작업으로 UI를 막지 않습니다.
            if not self.writer.saved and not self.writer.discarded:
                print(f"LEKIWI_RECORD incomplete={self.writer.path}", flush=True)
        # render product는 SimulationApp 종료 때 해제됩니다.


if __name__ == "__main__":
    import runpy
    os.environ["LEKIWI_RECORDING"] = "1"
    sys.argv = [str(SIM_DIRECTORY / "course_demo.py")]
    runpy.run_path(sys.argv[0], run_name="__main__")
