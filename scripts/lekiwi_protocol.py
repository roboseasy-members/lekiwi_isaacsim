from __future__ import annotations

import json
import math
from dataclasses import dataclass

JOINT_KEYS = (
    "shoulder_pan.pos",
    "shoulder_lift.pos",
    "elbow_flex.pos",
    "wrist_flex.pos",
    "wrist_roll.pos",
    "gripper.pos",
)


@dataclass(frozen=True)
class LeaderMessage:
    timestamp: float
    sequence: int
    joints: dict[str, float]


def _validate(message: LeaderMessage) -> None:
    missing = [key for key in JOINT_KEYS if key not in message.joints]
    if missing:
        raise ValueError(f"missing joints: {missing}")

    if message.sequence < 0:
        raise ValueError("sequence must be non-negative")

    if not math.isfinite(message.timestamp):
        raise ValueError("timestamp must be finite")

    for key in JOINT_KEYS:
        value = float(message.joints[key])
        if not math.isfinite(value):
            raise ValueError(f"joint {key} must be finite")


def encode_leader_message(message: LeaderMessage) -> bytes:
    _validate(message)

    payload = {
        "timestamp": float(message.timestamp),
        "sequence": int(message.sequence),
        "joints": {
            key: float(message.joints[key])
            for key in JOINT_KEYS
        },
    }

    return json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")


def decode_leader_message(payload: bytes) -> LeaderMessage:
    try:
        raw = json.loads(payload.decode("utf-8"))
        message = LeaderMessage(
            timestamp=float(raw["timestamp"]),
            sequence=int(raw["sequence"]),
            joints={
                str(key): float(value)
                for key, value in raw["joints"].items()
            },
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError(
            f"invalid leader message: {exc}"
        ) from exc

    _validate(message)
    return message
