"""Restore mixed arm-position / wheel-velocity control after World.reset()."""

import math


def restore_arm_position_gains(controller, arm_indices, stiffness=10000.0, damping=200.0):
    # Isaac 5.1 WheeledRobot.post_reset() switches ALL DOFs to velocity mode,
    # zeroing the arm's proportional gains even if USD drives were configured.
    # Only restore arm gains; leave wheels and passive rollers unchanged.
    # USD angular gains are per degree; the live PhysX tensor API uses radians.
    stiffness, damping = math.degrees(stiffness), math.degrees(damping)
    kps, kds = controller.get_gains()
    kps, kds = kps.copy(), kds.copy()
    for index in arm_indices:
        kps[index] = stiffness
        kds[index] = damping
    controller.set_gains(kps=kps, kds=kds)
    actual_kps, actual_kds = controller.get_gains()
    for index in arm_indices:
        if (not math.isclose(float(actual_kps[index]), stiffness, rel_tol=1e-6, abs_tol=0.001)
                or not math.isclose(float(actual_kds[index]), damping, rel_tol=1e-6, abs_tol=0.001)):
            raise RuntimeError(f"Arm position gains did not apply to DOF {index}")
