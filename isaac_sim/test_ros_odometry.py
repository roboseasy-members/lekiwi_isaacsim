import math
import unittest

from ros_odometry import (
    body_twist,
    relative_planar_pose,
    time_components,
    wrap_angle,
)


class PlanarOdometryTest(unittest.TestCase):
    def test_initial_pose_is_odom_origin(self):
        pose = relative_planar_pose(1.2, -0.4, 0.7, 1.2, -0.4, 0.7)
        self.assertAlmostEqual(pose[0], 0.0)
        self.assertAlmostEqual(pose[1], 0.0)
        self.assertAlmostEqual(pose[2], 0.0)

    def test_initial_robot_forward_becomes_odom_positive_x(self):
        pose = relative_planar_pose(
            2.0, 3.0, math.pi / 2.0, 2.0, 4.0, math.pi / 2.0
        )
        self.assertAlmostEqual(pose[0], 1.0)
        self.assertAlmostEqual(pose[1], 0.0)
        self.assertAlmostEqual(pose[2], 0.0)

    def test_odom_velocity_is_rotated_into_current_base_frame(self):
        previous = (0.0, 0.0, math.pi / 2.0)
        current = (0.0, 0.2, math.pi / 2.0)
        vx, vy, wz = body_twist(previous, current, 0.2)
        self.assertAlmostEqual(vx, 1.0)
        self.assertAlmostEqual(vy, 0.0)
        self.assertAlmostEqual(wz, 0.0)

    def test_yaw_rate_wraps_across_pi(self):
        previous = (0.0, 0.0, math.radians(179.0))
        current = (0.0, 0.0, math.radians(-179.0))
        _, _, wz = body_twist(previous, current, 0.5)
        self.assertAlmostEqual(wz, math.radians(4.0))
        self.assertAlmostEqual(wrap_angle(math.pi), -math.pi)

    def test_simulation_time_conversion_handles_nanosecond_carry(self):
        self.assertEqual(time_components(12.25), (12, 250_000_000))
        self.assertEqual(time_components(1.9999999996), (2, 0))


if __name__ == "__main__":
    unittest.main()
