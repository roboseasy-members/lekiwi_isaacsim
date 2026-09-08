"""6편의 두 카메라 미리보기와 에피소드 수집 창. 실물 장치를 열지 않는다."""
from pathlib import Path
import tempfile

import numpy as np
from episode_data import CAMERAS, FPS, EpisodeWriter


class RecordingPanel:
    def __init__(self, camera_paths, config, source, layout):
        import omni.ui as ui
        import omni.replicator.core as rep

        self.ui = ui
        self.rep = rep
        rep.orchestrator.set_capture_on_play(False)
        self.sensors = {}
        for name in CAMERAS:
            product = rep.create.render_product(camera_paths[name]["camera_path"],
                                                tuple(config["cameras"][name]["resolution"]))
            rgb = rep.AnnotatorRegistry.get_annotator("rgb")
            reference = rep.AnnotatorRegistry.get_annotator("ReferenceTime")
            rgb.attach([product.path])
            reference.attach([product.path])
            self.sensors[name] = (product, rgb, reference)
        parent = Path("/data/recordings")
        parent.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix="lekiwi.", dir=parent))
        self.metadata = {"robot_type": "lekiwi_sim", "source": source,
                         "camera_config": config, "course_layout": layout,
                         "timing": "RGB and state at t; action applied over [t, t+1/30); next state at t+1/30"}
        self.writer = None
        self.pending = None
        self.requests = []
        self.mode = "WARMING UP"
        self.last_saved = None
        self.error = ""
        self.duration_seconds = 30
        self.providers = {name: ui.ByteImageProvider() for name in CAMERAS}
        self.window = ui.Window("Lesson 6 - LeKiwi Recording", width=580, height=580)
        with self.window.frame:
            with ui.ScrollingFrame():
                with ui.VStack(spacing=5):
                    ui.Label("Front + wrist RGB | 30 Hz simulation time", height=23)
                    with ui.HStack(height=120, spacing=8):
                        for name in CAMERAS:
                            with ui.VStack():
                                ui.Label(name.upper(), height=18)
                                ui.ImageWithProvider(self.providers[name], fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT)
                    ui.Label("Task (select before Record)", height=20)
                    self.task = ui.ComboBox(0, "Move forward and stop", "Move a block to its matching basket", height=26)
                    with ui.HStack(height=26):
                        ui.Label("Max seconds (0 = no limit)", width=240)
                        self.duration = ui.IntField(min=0)
                        self.duration.model.set_value(self.duration_seconds)
                    with ui.HStack(height=30):
                        self.record = ui.Button("1. Record", clicked_fn=lambda: self.requests.append("record"))
                        self.stop = ui.Button("2. Stop recording", clicked_fn=lambda: self.requests.append("stop"))
                    with ui.HStack(height=30):
                        self.save = ui.Button("3. Save episode", clicked_fn=lambda: self.requests.append("save"))
                        self.discard = ui.Button("Discard unsaved", clicked_fn=lambda: self.requests.append("discard"))
                    with ui.HStack(height=22):
                        self.success = ui.CheckBox(width=22)
                        ui.Label("Task succeeded (check after reviewing)")
                    self.status = ui.Label("WARMING UP", height=24)
                    self.detail = ui.Label("Waiting for both cameras", height=40, word_wrap=True)
                    self.output = ui.Label(str(self.directory), height=52, word_wrap=True)
                    ui.Label("Save keeps this pose. New Record starts here; no scene reset.", height=28, word_wrap=True)
                    ui.Label("Mounts: " + ("calibrated" if config["calibrated"] else "provisional - inspect wrist occlusion"), height=25)
        self.window.deferred_dock_in("Stage", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)
        print(f"LEKIWI_RECORD directory={self.directory}", flush=True)

    def snapshot(self, world):
        sim_time, step = world.current_time, world.current_time_step_index
        playing = world.is_playing()
        world.pause()
        try:
            self.rep.orchestrator.step(delta_time=0.0, rt_subframes=2, pause_timeline=True)
        finally:
            if playing:
                world.play()
        if world.current_time_step_index != step or abs(world.current_time - sim_time) > 1e-6:
            raise ValueError("Physics advanced during RGB capture")
        images, stamps = {}, {}
        references = []
        for name, (_, rgb, reference) in self.sensors.items():
            rgba = np.asarray(rgb.get_data())
            data = reference.get_data()
            if rgba.ndim != 3 or rgba.shape[2] != 4 or not data:
                raise ValueError(f"{name}: waiting for RGB")
            ref = [int(data["referenceTimeNumerator"]), int(data["referenceTimeDenominator"])]
            references.append(ref)
            images[name] = rgba[:, :, :3].copy()
            stamps[name] = {"simulation_time": float(sim_time), "render_reference": ref}
            self.providers[name].set_data_array(rgba.reshape(-1).copy(), [rgba.shape[1], rgba.shape[0]])
        if references[0] != references[1]:
            raise ValueError("Front and wrist render references differ")
        return images, stamps

    def before_step(self, world, state, action, base_pose):
        # 두 render product를 물리 진행 없이 함께 캡처한 뒤에만 명령을 실행한다.
        try:
            sim_time = world.current_time
            images, stamps = self.snapshot(world)
            if self.mode == "WARMING UP":
                self.mode = "READY"
            for request in self.requests:
                if request == "record" and self.mode in {"READY", "SAVED", "DISCARDED"}:
                    choice = self.task.model.get_item_value_model().as_int
                    task = ("Move forward and stop", "Move a block to its matching basket")[choice]
                    self.duration_seconds = max(0, self.duration.model.as_int)
                    self.duration.model.set_value(self.duration_seconds)
                    self.writer = EpisodeWriter(self.directory, dict(
                        self.metadata, task=task, max_duration_seconds=self.duration_seconds))
                    self.mode, self.error = "RECORDING", ""
                    self.success.model.set_value(False)
                elif request == "stop" and self.mode == "RECORDING":
                    self.writer.stop()
                    self.mode = "UNSAVED"
                elif request == "save" and self.mode == "UNSAVED":
                    self.last_saved = self.writer.save(self.success.model.as_bool)
                    self.mode = "SAVED"
                    print(f"LEKIWI_RECORD saved={self.last_saved} frames={self.writer.count}", flush=True)
                elif request == "discard" and self.mode in {"RECORDING", "UNSAVED", "ERROR"}:
                    if self.writer and not self.writer.saved:
                        self.writer.discard()
                    self.writer = None
                    self.mode, self.error = "DISCARDED", ""
            self.requests.clear()
            if self.mode == "RECORDING":
                if not world.is_playing():
                    raise ValueError("Simulation paused: discard this take and start after Play")
                self.pending = ({"simulation_time": float(sim_time),
                                 "observation.state": state, "action": action,
                                 "base_pose": base_pose, "cameras": stamps}, images)
        except Exception as exc:
            self.requests.clear()
            if self.mode == "WARMING UP":
                self.error = str(exc)
            else:
                self.fail(exc)
        self.refresh()

    def after_step(self, world, next_state):
        if self.pending is None:
            return
        row, images = self.pending
        self.pending = None
        try:
            row.update({"next_observation.state": next_state, "next_simulation_time": float(world.current_time)})
            self.writer.append(row, images)
            if self.duration_seconds > 0 and self.writer.count >= self.duration_seconds * FPS:
                self.writer.stop()
                self.mode = "UNSAVED"
        except Exception as exc:
            self.fail(exc)
        self.refresh()

    def fail(self, exc):
        self.pending = None
        if self.writer:
            self.writer.stop()
        if self.mode != "ERROR":
            print(f"LEKIWI_RECORD error={exc}", flush=True)
        self.mode, self.error = "ERROR", str(exc)

    def refresh(self):
        count = self.writer.count if self.writer else 0
        seconds = self.duration.model.as_int if self.writer is None else self.duration_seconds
        limit = f"{seconds} s max" if seconds > 0 else "no limit"
        self.status.text = f"{self.mode} | {count} frames | {count/FPS:.2f} s / {limit}"
        self.detail.text = self.error or ("Saved and verified. Export with ./lekiwi export-dataset." if self.mode == "SAVED"
                                        else "Record > drive in Viewport > Stop recording > review > Save")
        self.output.text = str(self.last_saved or self.directory)
        self.record.enabled = self.mode in {"READY", "SAVED", "DISCARDED"}
        self.stop.enabled = self.mode == "RECORDING"
        self.save.enabled = self.mode == "UNSAVED" and bool(self.writer and self.writer.count)
        self.discard.enabled = self.mode in {"RECORDING", "UNSAVED", "ERROR"}
        self.task.enabled = self.mode in {"READY", "SAVED", "DISCARDED"}
        self.duration.enabled = self.task.enabled
        self.success.enabled = self.mode == "UNSAVED"

    def close(self):
        if self.writer and not self.writer.saved:
            self.writer.stop()
            print(f"LEKIWI_RECORD incomplete={self.writer.path}", flush=True)
        # 이 창은 앱과 함께 종료된다. render product는 SimulationApp이 해제한다.
