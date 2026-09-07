"""Local, ROS-free SO101 transport and simulator-only command limits.

Both containers share the host monotonic clock and a bind-mounted session folder.
This latest-sample mailbox is for teleop, NOT lossless dataset recording.
"""

import json
import math
import os
from pathlib import Path
import tempfile
import time

JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
LIMITS = ((-1.91986, 1.91986), (-1.74533, 1.74533), (-1.69, 1.69),
          (-1.65806, 1.65806), (-2.74385, 2.84121), (-0.174533, 1.74533))
# Clockwise looking from the wrist toward the fingertips: wrist_roll axis in
# the bundled URDF points back toward the arm, so this is a negative rotation.
DEFAULT_ARM_OFFSETS_DEG = (0, 0, 0, 0, -90, 0)


def arm_home(offsets_deg):
    if len(offsets_deg) != 6 or any(not math.isfinite(v) for v in offsets_deg):
        raise ValueError("Expected six finite zero offsets in degrees")
    return [max(lo, min(hi, math.radians(v))) for v, (lo, hi) in zip(offsets_deg, LIMITS)]


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".sample-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_packet(path):
    try:
        with Path(path).open() as stream:
            return json.load(stream)
    except (OSError, ValueError):
        return None


def make_packet(action, session, sequence, connected=True):
    return {"version": 1, "session": session, "sequence": sequence,
            "monotonic": time.monotonic(), "connected": connected,
            "unit": "degrees+gripper_percent", "positions": action}


class ArmTeleop:
    """Explicit clutch, 250 ms sample watchdog, bounded simulator joint targets.

Five body joints use absolute calibrated degrees plus explicit model offsets.
Gripper percent maps to 0..1.5 rad. Signs/zeros require hardware pose validation.
The monotonic clock, not the render-frame count, controls target slew speed.
"""

    def __init__(self, session, signs=(1, 1, 1, 1, 1, 1), timeout=0.25,
                 offsets_deg=DEFAULT_ARM_OFFSETS_DEG, max_speed=3.0):
        if len(signs) != 6 or any(x not in (-1, 1) for x in signs):
            raise ValueError("Expected six joint signs, each +1 or -1")
        if len(offsets_deg) != 6 or any(not math.isfinite(v) for v in offsets_deg):
            raise ValueError("Expected six finite zero offsets in degrees")
        if not math.isfinite(max_speed) or not 0 < max_speed <= 10:
            raise ValueError("Target speed must be in (0, 10] rad/s")
        self.session, self.signs, self.timeout = session, signs, timeout
        self.offsets = [math.radians(v) for v in offsets_deg]
        self.max_speed = max_speed
        self.targets = arm_home(offsets_deg)
        self.goals = self.targets[:]
        self.clipped = []
        self.armed = False
        self.status = "WAITING: leader / press R to arm"
        self.sequence = -1
        self.sample_stamp = -1.0
        self.last_update = None

    def _positions(self, packet, now):
        if not isinstance(packet, dict):
            raise ValueError("No leader sample")
        if (packet.get("version") != 1 or packet.get("session") != self.session
                or packet.get("connected") is not True
                or packet.get("unit") != "degrees+gripper_percent"):
            raise ValueError("Disconnected or incompatible leader")
        stamp, seq = packet["monotonic"], packet["sequence"]
        if (type(stamp) not in (int, float) or not math.isfinite(stamp)
                or not 0 <= now - stamp <= self.timeout or type(seq) is not int
                or seq < 0 or seq < self.sequence or stamp < self.sample_stamp
                or (seq == self.sequence and stamp != self.sample_stamp)):
            raise ValueError("Stale or out-of-order leader sample")
        positions = packet["positions"]
        values = [positions[f"{name}.pos"] for name in JOINTS]
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError("Invalid joint position")
        if any(abs(v) > 360 for v in values[:5]) or not 0 <= values[5] <= 100:
            raise ValueError("Leader position outside expected units/range")
        self.sequence, self.sample_stamp = seq, stamp
        return values

    def update(self, packet, now, actual, arm=False, stop=False):
        elapsed = 0.0 if self.last_update is None else now - self.last_update
        self.last_update = now
        try:
            if not math.isfinite(now) or not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError("Control clock invalid or moved backwards")
            # Rendering can stall while the separate leader reader stays healthy.
            # Check sample freshness, not time since the last rendered frame.
            # The 50 ms slew cap below prevents accumulated catch-up motion.
            values = self._positions(packet, now)
        except (KeyError, TypeError, ValueError) as exc:
            self.armed = False
            self.status = f"STOP: {exc}; press R after recovery"
            return self.targets[:]
        if stop:
            self.armed = False
        if arm and not stop:
            if len(actual) != 6 or any(not math.isfinite(float(v)) for v in actual):
                raise ValueError("Invalid simulated joint state")
            self.targets = [max(lo, min(hi, float(v))) for v, (lo, hi) in zip(actual, LIMITS)]
            # Start smoothly from the actual pose; R never changes the mapping.
            elapsed = 0.0
            self.armed = True
        if not self.armed:
            self.status = "READY: R to follow leader pose"
            return self.targets[:]
        goals = [self.offsets[i] + self.signs[i] * math.radians(values[i])
                 for i in range(5)]
        grip = values[5] if self.signs[5] == 1 else 100 - values[5]
        goals.append(self.offsets[5] + grip * 1.5 / 100)
        # Bound each increment during a slow GUI frame; never catch up a stall.
        step = self.max_speed * min(elapsed, 0.05)
        self.clipped = []
        for i, (goal, (lo, hi)) in enumerate(zip(goals, LIMITS)):
            if not lo <= goal <= hi:
                self.clipped.append(JOINTS[i])
            goal = max(lo, min(hi, goal))
            self.goals[i] = goal
            self.targets[i] += max(-step, min(step, goal - self.targets[i]))
        self.status = "ACTIVE: SO101 absolute pose; SPACE stops"
        if self.clipped:
            self.status += "; LIMIT: " + ", ".join(self.clipped)
        return self.targets[:]
