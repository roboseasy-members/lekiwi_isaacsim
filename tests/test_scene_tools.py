"""리셋이 녹화 데이터를 보호하고 새 배치·정지 상태를 적용하는지 확인한다."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'isaac_sim'))
from scene_tools import SceneReset, reset_allowed, randomize_layout
from color_course import generate_color_layout, validate_color_layout
from collection_course import generate_layout, validate_layout


@pytest.mark.parametrize('mode', ['RECORDING', 'FINISHING', 'UNSAVED', 'SAVING', 'DISCARDING', 'ERROR', 'WARMING UP'])
def test_reset_protects_unfinished_recording(mode):
    assert not reset_allowed(SimpleNamespace(mode=mode, requests=[]))


@pytest.mark.parametrize('mode', ['READY', 'SAVED', 'DISCARDED'])
def test_reset_allowed_between_episodes_only(mode):
    assert reset_allowed(SimpleNamespace(mode=mode, requests=[]))
    assert not reset_allowed(SimpleNamespace(mode=mode, requests=['record']))
    assert reset_allowed(None)


def test_random_reset_preserves_lanes_baskets_task_and_counts():
    original = generate_color_layout(42, 'yellow', 'green')
    fresh = randomize_layout(original)
    validate_color_layout(fresh)
    assert fresh['seed'] != original['seed']
    assert fresh['objects'] != original['objects']
    assert fresh['baskets'] == original['baskets']
    assert fresh['task'] == original['task']
    original = generate_layout(42, 3, 4)
    fresh = randomize_layout(original)
    validate_layout(fresh)
    assert [o['zone'] for o in fresh['objects']] == [o['zone'] for o in original['objects']]


class Body:
    def __init__(self):
        self.p = np.array([1., 2., 3.])
        self.q = np.array([1., 0., 0., 0.])
        self.j = np.array([.1, .2])
    def get_world_pose(self): return self.p, self.q
    def get_joint_positions(self): return self.j
    def set_world_pose(self, p, q): self.p, self.q = p.copy(), q.copy()
    def set_joint_positions(self, j): self.j = j.copy()
    def set_joint_velocities(self, v): self.jv = v
    def set_linear_velocity(self, v): self.lv = v
    def set_angular_velocity(self, v): self.av = v


def test_reset_restores_robot_and_randomized_object_poses_with_zero_velocity():
    robot = Body()
    bodies = [Body() for _ in range(4)]
    reset = SceneReset(robot, bodies)
    robot.p[:] = 99
    robot.j[:] = 99
    layout = generate_color_layout(42)
    reset.restore(layout)
    np.testing.assert_allclose(robot.p, [1, 2, 3])
    np.testing.assert_allclose(robot.j, [.1, .2])
    assert not robot.jv.any()
    for body, obj in zip(bodies, layout['objects']):
        np.testing.assert_allclose(body.p, obj['position'])
        assert np.isclose(np.linalg.norm(body.q), 1)
    for body in [robot, *bodies]:
        assert not body.lv.any() and not body.av.any()
