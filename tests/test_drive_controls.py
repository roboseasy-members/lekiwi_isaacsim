"""Base speed commands are checked without opening a simulator or hardware."""

import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "isaac_sim"))
from drive_controls import BaseSpeed


def test_start_at_existing_speed():
    speed = BaseSpeed()
    assert speed.level == 1
    assert speed.velocity(1, 0, 1) == pytest.approx((.25, 0, .8))


@pytest.mark.parametrize("level,scale", [(1, 1), (2, 1.5), (3, 2)])
def test_each_level_scales_translation_and_rotation(level, scale):
    speed = BaseSpeed()
    speed.select(level)
    assert speed.velocity(1, 0, 1) == pytest.approx((.25 * scale, 0, .8 * scale))
    assert speed.velocity(0, -1, -1) == pytest.approx((0, -.25 * scale, -.8 * scale))
    assert speed.velocity(0, 0, 0) == (0, 0, 0)
    vx, vy, _ = speed.velocity(1, 1, 0)
    assert math.hypot(vx, vy) == pytest.approx(.25 * scale)
    assert f"Base {level}:" in speed.label


def test_live_speed_change_and_return_to_normal():
    speed = BaseSpeed(linear=.2, angular=.5)
    for level, scale in ((3, 2), (2, 1.5), (1, 1)):
        speed.select(level)
        assert speed.velocity(-1, 0, -1) == pytest.approx((-.2 * scale, 0, -.5 * scale))
    with pytest.raises(ValueError):
        speed.select(4)
    assert speed.level == 1
