"""Task / camera-view presets for single-camera teleop recording.

Pure data, no Isaac Sim imports, so it can be read by the teleop script, the
verifier and documentation tools alike. Coordinates are world metres on the
B-plan turf arena: Z-up, centre (0, 0, 0), net on X=0 (top at 0.30 m),
Blue half X>0, Red half X<0, red basket centre (-0.18, -0.40), blue basket
centre (+0.18, +0.40), outer walls at X=+-1.5 / Y=+-1.0.

A task only selects the recording preset and the output label. It never
implies automatic grasping, success detection or scoring.
"""

# task -> allowed views (order = documentation order)
TASKS = {
    "white_over_net": ("net", "robot_top", "gripper", "arena"),
    "red_over_net": ("net", "robot_top", "gripper", "arena"),
    "white_opponent_basket": ("opponent_basket", "robot_top", "gripper", "arena"),
    "yellow_own_basket": ("own_basket", "robot_top", "gripper", "arena"),
}

TASK_DESCRIPTIONS = {
    "white_over_net": "White ball: approach, grasp, lift, pass over the net onto the red floor.",
    "red_over_net": "Red ball: approach, grasp, lift, pass over the net onto the red floor.",
    "white_opponent_basket": "White ball: grasp, drop into the opponent (red) basket across the net.",
    "yellow_own_basket": "Yellow ball: grasp, drop into the own (blue) basket.",
}

# view -> preset. "camera" is the internal recording camera key in
# teleoperate_four_switchable.py. kind:
#   fixed          -> eye/target/focal/clip are the whole definition
#   follow_base    -> tracks Blue 1's base position + yaw (TopdownCam_Blue1)
#   follow_gripper -> world-axis offset from Blue 1's gripper frame position
VIEWS = {
    "arena": {
        "camera": "top",
        "kind": "fixed",
        "eye": (0.25, -3.4, 5.7),
        "target": (0.0, 0.0, 0.05),
        "focal_mm": 28.0,
        "clip": (0.02, 100.0),
        "description": "Fixed high oblique view of the whole arena: net, both baskets, all four robots.",
    },
    # Fixed cameras sit INSIDE the outer walls (|y| < 1.0, |x| < 1.5): a
    # first pass placed them outside and the wall filled half the frame.
    "net": {
        "camera": "net",
        "kind": "fixed",
        # User direction (2026-09-11): low camera at the arena centre looking
        # ALONG the net toward the -Y wall, net-top height -- Blue 1 on the
        # left, the net running away from the lens, the red basket on the
        # right (not the earlier high diagonal from the wall side).
        # Eye exactly on the net plane (x=0) so the net runs straight up the
        # middle of the frame, and just above the net top (0.30 m) so the
        # mesh does not cut through the lens.
        "eye": (0.0, 0.45, 0.36),
        "target": (0.0, -1.0, 0.28),
        "focal_mm": 14.0,
        "clip": (0.02, 100.0),
        "description": "Low view from the arena centre along the net toward the -Y wall at net-top "
                       "height: Blue 1 on the left, net receding down the middle, red basket on the right.",
    },
    "opponent_basket": {
        "camera": "opponent_basket",
        "kind": "fixed",
        "eye": (0.9, -0.85, 1.5),
        "target": (-0.18, -0.40, 0.12),
        "focal_mm": 28.0,
        "clip": (0.02, 100.0),
        "description": "High diagonal view from Blue's side onto the red basket across the net: "
                       "net top, gripper approach, basket opening and interior.",
    },
    "own_basket": {
        "camera": "own_basket",
        "kind": "fixed",
        "eye": (0.95, 0.9, 1.3),
        "target": (0.18, 0.40, 0.12),
        "focal_mm": 28.0,
        "clip": (0.02, 100.0),
        "description": "High three-quarter view of the blue basket: opening and interior visible, "
                       "gripper approach from Blue's half, ball drop.",
    },
    "robot_top": {
        "camera": "blue1_topdown",
        "kind": "follow_base",
        "focal_mm": 16.0,
        "clip": (0.05, 100.0),
        "description": "Near-overhead chase view above Blue 1 (RecordCam_RobotTop, same base "
                       "tracking as the viewport top-down camera, own framing): follows base "
                       "position and yaw only, screen-up = robot forward; whole base, arm, gripper "
                       "and the workspace ahead of the robot.",
    },
    "gripper": {
        "camera": "blue1_gripper",
        "kind": "follow_gripper",
        "focal_mm": 24.0,
        "clip": (0.02, 100.0),
        "description": "Close diagonal view of Blue 1's wrist/gripper and the target ball, "
                       "world-axis offset from the gripper frame (never swings behind the arm).",
    },
}

VIEW_ORDER = ("arena", "net", "opponent_basket", "own_basket", "robot_top", "gripper")


def validate(task, view):
    """Return (ok, message). message lists the allowed combinations on error."""
    if task not in TASKS:
        return False, (f"unknown --record-task {task!r}. Tasks: {', '.join(TASKS)}")
    if view not in TASKS[task]:
        return False, (f"view {view!r} is not valid for task {task!r}. "
                       f"Allowed: {', '.join(TASKS[task])}")
    return True, ""


def combinations():
    return [(t, v) for t, views in TASKS.items() for v in views]


def format_listing():
    lines = ["Recording tasks and views (task -> views):"]
    for task, views in TASKS.items():
        lines.append(f"  {task:24s} {', '.join(views)}")
        lines.append(f"  {'':24s} {TASK_DESCRIPTIONS[task]}")
    lines.append("")
    lines.append("Views:")
    for view in VIEW_ORDER:
        lines.append(f"  {view:16s} [{VIEWS[view]['kind']}] {VIEWS[view]['description']}")
    return "\n".join(lines)
