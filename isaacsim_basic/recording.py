"""한 관절의 실제 PhysX 상태·명령을 기록하고 재생하는 5편 실습. USB 미사용."""
import argparse
import json
import math
from pathlib import Path
import tempfile

FPS = 60
FRAME_COUNT = 180


def can_reset_model(mode):
    return mode in {"READY", "SAVED", "REPLAYED", "DISCARDED"}


def check_frames(frames):
    """빈 기록·프레임 누락·비정상 값·상태 연결 오류를 저장 전에 검사한다."""
    if not frames:
        raise ValueError("기록이 비어 있습니다")
    previous = None
    for i, frame in enumerate(frames):
        data = frame["data"]
        if data["frame_index"] != i:
            raise ValueError("프레임 번호가 연속하지 않습니다")
        numbers = [frame["current_time"], data["episode_time"], data["next_time"]]
        numbers += [data[k][n][0] for k, n in (
            ("observation", "joint_position_rad"), ("action", "joint_target_rad"),
            ("next_observation", "joint_position_rad"))]
        if not all(type(v) in (int, float) and math.isfinite(v) for v in numbers):
            raise ValueError("유효하지 않은 수치입니다")
        if abs(data["episode_time"] - i / FPS) > 1e-6:
            raise ValueError("에피소드 시각이 일정하지 않습니다")
        if abs(data["next_time"] - frame["current_time"] - 1 / FPS) > 1e-6:
            raise ValueError("관측 간격이 1/60초가 아닙니다")
        if previous is not None:
            if (frame["current_time_step"] != previous["current_time_step"] + 1
                    or abs(frame["current_time"] - previous["data"]["next_time"]) > 1e-6):
                raise ValueError("물리 스텝이 누락되었습니다")
            if data["observation"] != previous["data"]["next_observation"]:
                raise ValueError("연속 프레임의 상태가 연결되지 않습니다")
        previous = frame
    return {"frames": len(frames), "fps": FPS, "duration_s": len(frames) / FPS}


def main(test=False):
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": test, "width": 1280, "height": 720})
    try:
        import omni.usd
        import omni.ui as ui
        import omni.kit.app
        from pxr import Usd, UsdGeom, UsdPhysics
        from isaacsim.core.api import World
        from isaacsim.core.prims import SingleArticulation
        from isaacsim.core.api.loggers import DataLogger
        from isaacsim.core.utils.viewports import set_camera_view
        from scenes import create_stage

        parent = Path("/data/isaacsim_basic")
        parent.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="recording.", dir=parent))
        create_stage(directory / "scene.usda", "joints")
        assert omni.usd.get_context().open_stage(str(directory / "scene.usda"))
        world = World(physics_dt=1/FPS, rendering_dt=1/FPS,
                      stage_units_in_meters=1.0, physics_prim_path="/World/PhysicsScene")
        stage = omni.usd.get_context().get_stage()
        hinge = world.scene.add(SingleArticulation(prim_path="/World/Hinge/FixedBase", name="teaching_hinge"))
        drive = UsdPhysics.DriveAPI(stage.GetPrimAtPath("/World/Hinge/Shoulder"), "angular")
        logger = DataLogger()
        saved = None
        mode, index = "READY", 0
        replay_frames, errors = [], []
        requests = []
        preparation = None

        def angle():
            p = UsdGeom.Xformable(stage.GetPrimAtPath("/World/Hinge/Arm")).ComputeLocalToWorldTransform(
                Usd.TimeCode.Default()).ExtractTranslation()
            return math.atan2(p[0], p[2] - .3)

        def prepare():
            drive.GetTargetPositionAttr().Set(0)
            world.reset()
            for _ in range(120):
                world.step(render=False)
            world.pause()

        def begin_preparation(next_mode):
            nonlocal mode, preparation
            mode = "PREPARING"
            drive.GetTargetPositionAttr().Set(0)
            hinge.post_reset()
            world.play()
            preparation = [next_mode, 120]

        def prepare_gui_step():
            nonlocal mode, index, preparation
            try:
                # 앱의 주 반복문에서 실행해 asyncio 콜백 안의 중첩 앱 갱신을 피한다.
                for _ in range(min(4, preparation[1])):
                    world.step(render=False)
                    preparation[1] -= 1
                if preparation[1]:
                    return
                next_mode = preparation[0]
                preparation = None
                world.pause()
                if next_mode == "RECORDING":
                    logger.reset()
                    logger.start()
                index, mode = 0, next_mode
                if next_mode != "READY":
                    world.play()
            except Exception as exc:
                mode, preparation = "ERROR", None
                print(f"BASIC_RECORDING prepare_error={exc}", flush=True)

        def frames():
            return [logger.get_data_frame(i).get_dict() for i in range(logger.get_num_of_data_frames())]

        def start_record():
            nonlocal mode, index, preparation
            if mode not in {"READY", "SAVED", "REPLAYED", "DISCARDED"}:
                return
            if not test:
                begin_preparation("RECORDING")
                return
            prepare()
            logger.reset()
            logger.start()
            index, mode = 0, "RECORDING"
            world.play()

        def save():
            nonlocal saved, mode
            if mode != "UNSAVED":
                return
            report = check_frames(frames())
            episode = Path(tempfile.mkdtemp(prefix="episode.", dir=directory))
            temporary = episode / "episode.incomplete.json"
            logger.save(str(temporary))
            # 저장 파일 자체를 다시 읽어 검사하고 마지막에 완료 이름으로 바꾼다.
            check_frames(json.loads(temporary.read_text())["Isaac Sim Data"])
            report.update({"source": "scripted_simulation", "joint": "Shoulder", "units": "rad",
                           "recording": "observation_t, action_t, next_observation_t_plus_dt",
                           "physics_dt_s": 1/FPS, "rgb_recorded": False})
            (episode / "metadata.json").write_text(json.dumps(report, indent=2))
            temporary.rename(episode / "episode.json")
            saved, mode = episode / "episode.json", "SAVED"
            print(f"BASIC_RECORDING saved={saved} frames={report['frames']}", flush=True)

        def replay():
            nonlocal mode, index, replay_frames, errors, preparation
            if mode not in {"READY", "SAVED", "REPLAYED"} or saved is None:
                return
            logger.load(str(saved))
            replay_frames = frames()
            check_frames(replay_frames)
            if not test:
                errors = []
                begin_preparation("REPLAYING")
                return
            prepare()
            index, errors, mode = 0, [], "REPLAYING"
            world.play()

        def tick(render):
            nonlocal mode, index
            if not world.is_playing():
                return
            before, time, step = angle(), world.current_time, world.current_time_step_index
            target = (math.radians(25) * math.sin(2 * math.pi * index / 120)
                      if mode == "RECORDING" else replay_frames[index]["data"]["action"]["joint_target_rad"][0])
            drive.GetTargetPositionAttr().Set(math.degrees(target))
            world.step(render=render)
            after = angle()
            if mode == "RECORDING" and logger.is_started():
                logger.add_data({"frame_index": index, "episode_time": index / FPS,
                                 "observation": {"joint_position_rad": [before]},
                                 "action": {"joint_target_rad": [target]},
                                 "next_observation": {"joint_position_rad": [after]},
                                 "next_time": world.current_time}, step, time)
            else:
                errors.append(abs(after - replay_frames[index]["data"]["next_observation"]["joint_position_rad"][0]))
            index += 1
            end = FRAME_COUNT if mode == "RECORDING" else len(replay_frames)
            if index == end:
                world.pause()
                if mode == "RECORDING":
                    logger.pause()
                    mode = "UNSAVED"
                else:
                    report = {"frames": index, "max_state_error_rad": max(errors)}
                    (saved.parent / "replay_report.json").write_text(json.dumps(report, indent=2))
                    print(f"BASIC_RECORDING replay={report}", flush=True)
                    mode = "REPLAYED"

        prepare()
        set_camera_view(eye=(1.05, -1.6, .9), target=(0, 0, .3))
        if not test:
            from omni.kit.viewport.utility import get_active_viewport
            get_active_viewport().camera_path = "/OmniverseKit_Persp"
        if test:
            start_record()
            while mode == "RECORDING":
                tick(False)
            original = frames()
            assert len(original) == FRAME_COUNT
            assert max(abs(f["data"]["next_observation"]["joint_position_rad"][0]) for f in original) > .3
            save()
            assert json.loads(saved.read_text())["Isaac Sim Data"] == original
            replay()
            while mode == "REPLAYING":
                tick(False)
            assert max(errors) < .01, errors
            preserved = saved.read_bytes()
            start_record()
            for _ in range(10):
                tick(False)
            world.pause()
            logger.reset()
            assert saved.read_bytes() == preserved
            assert logger.get_num_of_data_frames() == 0
            print("BASIC_RECORDING_TEST result=PASS", flush=True)
            return

        window = ui.Window("Lesson 5 - Data Recording", width=540, height=550, style={"font_size": 16})
        with window.frame:
            with ui.VStack(spacing=8):
                ui.Label("Single-joint episode | simulation only", height=26)
                ui.Label("1. Record > 2. Save episode > 3. Replay saved", height=24)
                with ui.HStack(height=36):
                    record_button = ui.Button("1. Record (3 s)", clicked_fn=lambda: requests.append("record"))
                    save_button = ui.Button("2. Save episode", clicked_fn=lambda: requests.append("save"))
                with ui.HStack(height=36):
                    replay_button = ui.Button("3. Replay saved", clicked_fn=lambda: requests.append("replay"))
                    discard_button = ui.Button("Discard unsaved", clicked_fn=lambda: requests.append("discard"))
                reset_button = ui.Button("Reset model (keep saved episodes)", height=32,
                                         clicked_fn=lambda: requests.append("reset"))
                ui.Label("Save or discard unsaved frames before Reset. Saved files are preserved.", height=44, word_wrap=True)
                status = ui.Label("READY", height=26)
                sample = ui.Label("60 Hz simulation time / rad", height=26)
                detail = ui.Label("", height=42, word_wrap=True)
                output = ui.Label(str(directory), height=64, word_wrap=True)
                ui.Label("JSON state/action only | RGB not recorded", height=24)
        # 3·4편의 조작 창과 같은 위치에서 기록 실습을 시작한다.
        window.deferred_dock_in("Stage", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)
        print(f"BASIC_RECORDING ready directory={directory}", flush=True)
        while app.is_running():
            while requests:
                request = requests.pop(0)
                if request == "record": start_record()
                elif request == "save": save()
                elif request == "replay": replay()
                elif request == "reset" and can_reset_model(mode):
                    begin_preparation("READY")
                elif request == "discard" and mode in {"RECORDING", "UNSAVED", "ERROR"}:
                    world.pause()
                    logger.reset()
                    mode, index = "DISCARDED", 0
            if mode == "PREPARING":
                prepare_gui_step()
            active = mode in {"RECORDING", "REPLAYING"}
            if active and world.is_playing():
                tick(True)
            else:
                if not active and mode != "PREPARING" and world.is_playing():
                    world.pause()
                app.update()
            record_button.enabled = mode in {"READY", "SAVED", "REPLAYED", "DISCARDED"}
            save_button.enabled = mode == "UNSAVED"
            replay_button.enabled = mode in {"READY", "SAVED", "REPLAYED"} and saved is not None
            reset_button.enabled = can_reset_model(mode)
            discard_button.enabled = mode in {"RECORDING", "UNSAVED", "ERROR"}
            status.text = f"{mode} | frames: {index}/{FRAME_COUNT}"
            sample.text = f"actual: {angle():+.4f} rad | simulation: {index/FPS:.3f} s"
            detail.text = ("Preparing scene. Please wait." if mode == "PREPARING"
                           else "Preparation failed. Discard unsaved and try again." if mode == "ERROR"
                           else f"Replay max error: {max(errors):.6f} rad" if mode == "REPLAYED"
                           else "UNSAVED: click Save episode to keep this recording." if mode == "UNSAVED"
                           else "Save before closing. Unsaved frames will be discarded.")
            output.text = str(saved or directory)
        world.pause()
    finally:
        app.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    main(parser.parse_args().test)
