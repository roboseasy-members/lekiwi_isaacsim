"""학생 PC에서 실제 코스·두 RGB·짧은 기록을 검사한다. USB를 사용하지 않는다."""
from isaacsim import SimulationApp
app = SimulationApp({'extra_args': ["--/exts/isaacsim.core.throttling/enable_async=false",
                       "--/app/hydraEngine/waitIdle=1",
                       "--/app/updateOrder/checkForHydraRenderComplete=1000"], 'headless': True, 'width': 640, 'height': 480})

import json
import math
from pathlib import Path
import tempfile
import time
import traceback
import numpy as np
import omni.usd
from pxr import UsdLux
from PIL import Image
from isaacsim.core.api import World
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot.wheeled_robots.robots import WheeledRobot
from arm_control import restore_arm_position_gains
from collection_course import attach_course, save_course
from color_course import generate_color_layout
from episode_data import validate_episode
from recording_panel import RecordingPanel
from robot_cameras import attach_cameras, load_camera_config
from teleop_bridge import JOINTS, DEFAULT_ARM_OFFSETS_DEG, arm_home


def main():
    world = World(physics_dt=1/120, rendering_dt=1/30, stage_units_in_meters=1.0)
    stage = omni.usd.get_context().get_stage()
    layout = generate_color_layout(42, 'red', 'red')
    base = Path('/data/setup')
    base.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='camera-check.', dir=base))
    attach_course(stage, save_course(layout, output))
    robot = world.scene.add(WheeledRobot(
        prim_path='/LeKiwi', name='lekiwi', create_robot=True,
        wheel_dof_names=['back_wheel_joint', 'left_wheel_joint', 'right_wheel_joint'],
        usd_path=str(Path(__file__).parent/'assets/lekiwi_soarm/usd/lekiwi_soarm.usd'),
        position=np.array([0., 0., .055])))
    light = UsdLux.DomeLight.Define(stage, '/World/SetupLight')
    light.CreateIntensityAttr(1000)
    config = load_camera_config()
    cameras = attach_cameras(stage, config)
    world.reset()
    indices = np.array([robot.get_dof_index(n) for n in JOINTS], dtype=np.int32)
    home = np.array(arm_home(DEFAULT_ARM_OFFSETS_DEG))
    robot.set_joint_positions(home, joint_indices=indices)
    controller = robot.get_articulation_controller()
    restore_arm_position_gains(controller, indices)
    recorder = RecordingPanel(cameras, config, 'setup_check_home_hold', layout)
    # 진단 기록은 학습 시연 폴더와 구분하고 원본·요약·샘플을 함께 남긴다.
    empty = recorder.directory
    recorder.directory = output
    empty.rmdir()
    recorder.duration_seconds = 2
    started = time.monotonic()
    step_times = []

    def state():
        pos, quat = robot.get_world_pose()
        w, x, y, z = quat
        yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
        linear = robot.get_linear_velocity()
        angular = robot.get_angular_velocity()
        values = [float(v) for v in robot.get_joint_positions(joint_indices=indices)]
        values += [float(math.cos(yaw)*linear[0]+math.sin(yaw)*linear[1]),
                   float(-math.sin(yaw)*linear[0]+math.cos(yaw)*linear[1]), float(angular[2])]
        return values, [float(v) for v in (*pos, *quat)]

    try:
        while time.monotonic()-started < 180:
            tick = time.monotonic()
            if recorder.mode == 'READY':
                recorder.requests.append('record')
            if recorder.mode == 'UNSAVED':
                recorder.requests.append('save')
            controller.apply_action(ArticulationAction(joint_positions=home, joint_indices=indices))
            robot.apply_wheel_actions(ArticulationAction(joint_velocities=np.zeros(3)))
            values, pose = state()
            recorder.before_step(world, values, home.tolist()+[0., 0., 0.], pose)
            world.step(render=True)
            recorder.after_step(world, state()[0])
            step_times.append(time.monotonic()-tick)
            if recorder.mode == 'ERROR':
                raise RuntimeError(recorder.error)
            if recorder.mode == 'SAVED':
                break
        if recorder.mode != 'SAVED':
            raise RuntimeError(f'180초 내 검사가 완료되지 않았습니다: {recorder.mode} {recorder.error}')
        episode = Path(recorder.last_saved)
        metadata, rows = validate_episode(episode)
        assert len(rows) == 60 and metadata['camera_config'] == config
        for name in ('front', 'wrist'):
            sample = episode/rows[len(rows)//2]['cameras'][name]['path']
            with Image.open(sample) as im:
                pixels = np.asarray(im)
                assert np.ptp(pixels.astype(np.int16)) > 10, f'{name}: 단색 영상'
            (output/(name+'.png')).write_bytes(sample.read_bytes())
        report = {'complete': True, 'frames': len(rows), 'camera_config': config,
                  'elapsed_seconds': time.monotonic()-started,
                  'step_p95_seconds': float(np.percentile(step_times, 95)),
                  'episode': str(episode),
                  'scope': '실제 LeKiwi 코스·두 RGB·60프레임 저장 검사. GUI·장시간 수집·학습 성능은 별도 검증.'}
        (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(f'LEKIWI_CAMERA_TEST report={output}/report.json', flush=True)
        print('LEKIWI_CAMERA_TEST result=PASS', flush=True)
    finally:
        recorder.close()
        world.stop()


failed = False
try:
    main()
except Exception:
    failed = True
    traceback.print_exc()
finally:
    app.close()
if failed:
    raise SystemExit(1)
