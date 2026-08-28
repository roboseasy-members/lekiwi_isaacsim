"""ROS 2 ground-truth odometry publishing for the Isaac LeKiwi drive test."""

import math


ODOM_FRAME = "odom"
BASE_FOOTPRINT_FRAME = "base_footprint"
PLANAR_POSE_COVARIANCE = [0.0] * 36
PLANAR_TWIST_COVARIANCE = [0.0] * 36
for _index, _variance in (
    (0, 1e-6),
    (7, 1e-6),
    (14, 1e6),
    (21, 1e6),
    (28, 1e6),
    (35, 1e-6),
):
    PLANAR_POSE_COVARIANCE[_index] = _variance
for _index, _variance in (
    (0, 1e-4),
    (7, 1e-4),
    (14, 1e6),
    (21, 1e6),
    (28, 1e6),
    (35, 1e-4),
):
    PLANAR_TWIST_COVARIANCE[_index] = _variance


def wrap_angle(angle):
    """Wrap an angle to [-pi, pi)."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def relative_planar_pose(initial_x, initial_y, initial_yaw, x, y, yaw):
    """Express a world planar pose in an odom frame fixed at the initial pose."""
    dx = x - initial_x
    dy = y - initial_y
    cosine = math.cos(initial_yaw)
    sine = math.sin(initial_yaw)
    return (
        cosine * dx + sine * dy,
        -sine * dx + cosine * dy,
        wrap_angle(yaw - initial_yaw),
    )


def body_twist(previous_pose, current_pose, dt):
    """Return vx, vy in the current child frame and planar angular velocity."""
    if previous_pose is None or dt <= 0.0:
        return 0.0, 0.0, 0.0

    vx_odom = (current_pose[0] - previous_pose[0]) / dt
    vy_odom = (current_pose[1] - previous_pose[1]) / dt
    yaw = current_pose[2]
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    return (
        cosine * vx_odom + sine * vy_odom,
        -sine * vx_odom + cosine * vy_odom,
        wrap_angle(yaw - previous_pose[2]) / dt,
    )


def time_components(seconds):
    """Convert non-negative floating-point seconds to ROS sec/nanosec fields."""
    whole_seconds = math.floor(seconds)
    nanoseconds = round((seconds - whole_seconds) * 1_000_000_000)
    if nanoseconds == 1_000_000_000:
        whole_seconds += 1
        nanoseconds = 0
    return int(whole_seconds), int(nanoseconds)


class RosOdometryPublisher:
    """Publish planar Isaac ground truth as nav_msgs/Odometry and dynamic TF."""

    def __init__(self, initial_position, initial_yaw):
        import rclpy
        from geometry_msgs.msg import TransformStamped
        from nav_msgs.msg import Odometry
        from rosgraph_msgs.msg import Clock
        from tf2_ros import TransformBroadcaster

        self._rclpy = rclpy
        self._transform_type = TransformStamped
        self._odometry_type = Odometry
        self._clock_type = Clock
        self._owns_context = not rclpy.ok()
        if self._owns_context:
            rclpy.init(args=[])

        self._node = rclpy.create_node("lekiwi_isaac_odometry")
        self._odometry_publisher = self._node.create_publisher(
            Odometry, "/odom", 10
        )
        self._clock_publisher = self._node.create_publisher(Clock, "/clock", 10)
        self._transform_broadcaster = TransformBroadcaster(self._node)
        self._initial_x = float(initial_position[0])
        self._initial_y = float(initial_position[1])
        self._initial_yaw = float(initial_yaw)
        self._previous_pose = None
        self._previous_sim_time = None

    def _stamp(self, sim_time):
        stamp = self._node.get_clock().now().to_msg()
        stamp.sec, stamp.nanosec = time_components(float(sim_time))
        return stamp

    def publish_clock(self, sim_time):
        clock = self._clock_type()
        clock.clock = self._stamp(sim_time)
        self._clock_publisher.publish(clock)
        self._rclpy.spin_once(self._node, timeout_sec=0.0)

    def publish(self, position, yaw, sim_time):
        pose = relative_planar_pose(
            self._initial_x,
            self._initial_y,
            self._initial_yaw,
            float(position[0]),
            float(position[1]),
            float(yaw),
        )
        dt = (
            0.0
            if self._previous_sim_time is None
            else float(sim_time) - self._previous_sim_time
        )
        vx, vy, wz = body_twist(self._previous_pose, pose, dt)
        stamp = self._stamp(sim_time)
        half_yaw = 0.5 * pose[2]
        quaternion_z = math.sin(half_yaw)
        quaternion_w = math.cos(half_yaw)

        odometry = self._odometry_type()
        odometry.header.stamp = stamp
        odometry.header.frame_id = ODOM_FRAME
        odometry.child_frame_id = BASE_FOOTPRINT_FRAME
        odometry.pose.pose.position.x = pose[0]
        odometry.pose.pose.position.y = pose[1]
        odometry.pose.pose.position.z = 0.0
        odometry.pose.pose.orientation.z = quaternion_z
        odometry.pose.pose.orientation.w = quaternion_w
        odometry.pose.covariance = PLANAR_POSE_COVARIANCE
        odometry.twist.twist.linear.x = vx
        odometry.twist.twist.linear.y = vy
        odometry.twist.twist.angular.z = wz
        odometry.twist.covariance = PLANAR_TWIST_COVARIANCE
        self._odometry_publisher.publish(odometry)

        transform = self._transform_type()
        transform.header.stamp = stamp
        transform.header.frame_id = ODOM_FRAME
        transform.child_frame_id = BASE_FOOTPRINT_FRAME
        transform.transform.translation.x = pose[0]
        transform.transform.translation.y = pose[1]
        transform.transform.translation.z = 0.0
        transform.transform.rotation.z = quaternion_z
        transform.transform.rotation.w = quaternion_w
        self._transform_broadcaster.sendTransform(transform)
        self._rclpy.spin_once(self._node, timeout_sec=0.0)

        self._previous_pose = pose
        self._previous_sim_time = float(sim_time)
        return pose, (vx, vy, wz)

    def close(self):
        if self._node is not None:
            self._node.destroy_node()
            self._node = None
        if self._owns_context and self._rclpy.ok():
            self._rclpy.shutdown()
