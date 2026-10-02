"""Analytic forward kinematics + numerical inverse kinematics for the LeKiwi
arm (SO-101-style 5DOF: shoulder_pan, shoulder_lift, elbow_flex, wrist_flex,
wrist_roll -> gripper_frame_link). Pure math, no Isaac Sim dependency.

The joint-local offsets/rotations below were measured directly from the
production stage (`lekiwi_arena_3p0x2p0_net_B_4robots_turf.usd`) by reading
each PhysicsRevoluteJoint's localPos0/localRot0 attribute headlessly, not
guessed from a spec sheet. The resulting FK was cross-checked against that
same probe's independently-measured `gripper_frame_link` world position and
matched to 0.2 mm once two things were pinned down empirically (both were
ambiguous from the raw USD dump alone):

  - Gf.Quatd prints as (w, x, y, z), not (x, y, z, w).
  - `state:angular:physics:position` on a PhysicsRevoluteJoint is in
    DEGREES, matching every other joint-angle value already used elsewhere
    in this project (ARM_RELAXED_TARGET_DEG, ARM_MAX_STEP_DEG, etc.) --
    interpreting it as radians gave an 8 cm FK error, interpreting it as
    degrees gave 0.2 mm.

This module solves IK entirely in the robot's own base_footprint-local
frame (X forward / +X faces the arm's working side, matching this
project's "local +X faces the net" convention used elsewhere for
background-robot steering and topdown cameras). The caller is responsible
for transforming a world-frame target into that local frame using the
robot's live base transform, and for adding the live base world pose back
on top of anything this module returns in world-frame contexts (it never
touches world frame itself).
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np

JOINT_ORDER = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll")

# physics:lower/upperLimit read from the same stage, degrees.
JOINT_LIMITS_DEG: Dict[str, Tuple[float, float]] = {
    "shoulder_pan": (-109.9, 109.9),
    "shoulder_lift": (-100.0, 100.0),
    "elbow_flex": (-96.8, 96.8),
    "wrist_flex": (-95.0, 95.0),
    "wrist_roll": (-157.2, 162.8),
}

# Same as ARM_RELAXED_TARGET_DEG in teleoperate_four_switchable.py -- reused
# here purely as an IK redundancy-resolution bias (pulls the elbow toward a
# natural "reaching forward and down" configuration among equally-valid
# solutions), not as a control target in its own right.
NEUTRAL_DEG = {
    "shoulder_pan": 0.0, "shoulder_lift": 45.0, "elbow_flex": 20.0,
    "wrist_flex": 10.0, "wrist_roll": 0.0,
}


def _quat_to_R(w: float, x: float, y: float, z: float) -> np.ndarray:
    n = np.array([w, x, y, z], dtype=float)
    n = n / np.linalg.norm(n)
    w, x, y, z = n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def _T(pos, quat_wxyz) -> np.ndarray:
    M = np.eye(4)
    M[:3, :3] = _quat_to_R(*quat_wxyz)
    M[:3, 3] = pos
    return M


def _Rz(theta_rad: float) -> np.ndarray:
    c, s = math.cos(theta_rad), math.sin(theta_rad)
    M = np.eye(4)
    M[0, 0], M[0, 1] = c, -s
    M[1, 0], M[1, 1] = s, c
    return M


# Measured (localPos0, localRot0-as-w,x,y,z) per joint frame, body0->joint.
# child body origin == joint frame (localPos1=0, localRot1=identity for
# every joint on this stage), so body1_frame = body0_frame * T(...) * Rz(angle).
_J = {
    "base_to_soarm": ((0.0, 0.0, 0.0525), (1.0, 0.0, 0.0, 0.0)),  # soarm_mount_joint (fixed)
    "shoulder_pan": ((0.0388353, -8.97657e-9, 0.0624), (1.6067656e-12, 1.2675908e-6, -1.0, -1.2675908e-6)),
    "shoulder_lift": ((-0.0303992, -0.0182778, -0.0542), (0.4999982, -0.5, -0.5, -0.50000185)),
    "elbow_flex": ((-0.11257, -0.028, 1.73763e-16), (0.7071055, -4.3766727e-16, 1.8055644e-16, 0.7071081)),
    "wrist_flex": ((-0.1349, 0.0052, 3.62355e-17), (0.7071055, 1.7295536e-15, -1.1162413e-15, -0.7071081)),
    "wrist_roll": ((5.55112e-17, -0.0611, 0.0181), (0.01721003, -0.017208178, 0.7068986, 0.70689607)),
    "gripper_frame": ((-0.0079, -0.000218121, -0.0981274), (1.2675908e-6, 0.0, 1.0, 0.0)),  # fixed
}
# base_footprint -> base_link fixed offset (not itself a queried joint prim;
# base_link is the mobile-base rigid body and base_footprint is its own
# tracked frame). Measured as the world-Z delta between the two at a
# near-zero base roll/pitch pose; this project's base only yaws, never
# rolls/pitches, so a pure Z translation is exact for FK purposes here.
_BASE_TO_BASE_LINK = ((0.0, 0.0, 0.0552), (1.0, 0.0, 0.0, 0.0))


def fk_local(angles_deg: Dict[str, float]) -> np.ndarray:
    """4x4 transform of gripper_frame_link relative to this robot's own
    base_footprint frame (i.e. NOT world space)."""
    M = np.eye(4)
    M = M @ _T(*_BASE_TO_BASE_LINK)
    M = M @ _T(*_J["base_to_soarm"])
    M = M @ _T(*_J["shoulder_pan"]) @ _Rz(math.radians(angles_deg["shoulder_pan"]))
    M = M @ _T(*_J["shoulder_lift"]) @ _Rz(math.radians(angles_deg["shoulder_lift"]))
    M = M @ _T(*_J["elbow_flex"]) @ _Rz(math.radians(angles_deg["elbow_flex"]))
    M = M @ _T(*_J["wrist_flex"]) @ _Rz(math.radians(angles_deg["wrist_flex"]))
    M = M @ _T(*_J["wrist_roll"]) @ _Rz(math.radians(angles_deg["wrist_roll"]))
    M = M @ _T(*_J["gripper_frame"])
    return M


def fk_gripper_pos_local(angles_deg: Dict[str, float]) -> np.ndarray:
    return fk_local(angles_deg)[:3, 3]


def _fk_vec(vec5: np.ndarray) -> np.ndarray:
    angles = {k: v for k, v in zip(JOINT_ORDER, vec5)}
    return fk_gripper_pos_local(angles)


def solve_ik(
    target_local: Tuple[float, float, float],
    seed_deg: Dict[str, float],
    iters: int = 60,
    damping: float = 0.02,
    neutral_pull: float = 0.15,
) -> Tuple[Dict[str, float], float]:
    """Damped-least-squares numerical IK for gripper_frame_link position
    (3 targets, 5 joints -- redundant, so this is a position-only solve).
    Orientation is not directly controlled, but the null space of the
    position Jacobian is pulled toward NEUTRAL_DEG every iteration
    (standard redundancy-resolution technique) so repeated solves across a
    multi-step approach (hover -> descend -> lift) settle into a
    consistent "reaching forward and down" configuration instead of
    wandering to an arbitrary orientation each time the target moves --
    without this, headless grasp-attempt testing showed 0/9 successful
    lifts with the arm frequently approaching from an unpredictable angle.
    Returns (angles_deg, residual_error_m). The caller should treat a large
    residual (workspace-edge saturation, e.g. > ~0.03 m) as "unreachable"
    rather than trusting the solution blindly -- this function clips to
    JOINT_LIMITS_DEG every iteration instead of ever exceeding them, so a
    genuinely out-of-reach target saturates a joint and stops improving.
    """
    q = np.array([seed_deg.get(k, NEUTRAL_DEG[k]) for k in JOINT_ORDER], dtype=float)
    neutral = np.array([NEUTRAL_DEG[k] for k in JOINT_ORDER])
    target = np.array(target_local, dtype=float)
    for _ in range(iters):
        p0 = _fk_vec(q)
        err = target - p0
        if np.linalg.norm(err) < 1e-4:
            break
        Jm = np.zeros((3, 5))
        h = 0.5  # degrees, finite-difference step
        for i in range(5):
            dq = q.copy()
            dq[i] += h
            Jm[:, i] = (_fk_vec(dq) - p0) / math.radians(h)  # d(pos)/d(rad)
        JJt = Jm @ Jm.T
        lam = damping * damping
        J_pinv = Jm.T @ np.linalg.inv(JJt + lam * np.eye(3))
        dq_rad = J_pinv @ err
        null_bias_deg = (neutral - q) * neutral_pull
        dq_deg = np.degrees(dq_rad) + (np.eye(5) - J_pinv @ Jm) @ null_bias_deg
        q = q + dq_deg
        for i, k in enumerate(JOINT_ORDER):
            lo, hi = JOINT_LIMITS_DEG[k]
            q[i] = max(lo, min(hi, q[i]))
    final_err = float(np.linalg.norm(target - _fk_vec(q)))
    return {k: float(v) for k, v in zip(JOINT_ORDER, q)}, final_err
