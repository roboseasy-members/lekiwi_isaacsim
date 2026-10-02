from __future__ import annotations

import argparse
import signal
import sys
import time

import zmq
from lerobot.teleoperators.so_leader import (
    SO101Leader,
    SO101LeaderConfig,
)

from lekiwi_protocol import (
    JOINT_KEYS,
    LeaderMessage,
    encode_leader_message,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read an SO-101 Leader and publish its joint "
            "targets over ZeroMQ."
        )
    )
    parser.add_argument(
        "--port",
        required=True,
        metavar="<PORT>",
        help=(
            "Serial port the SO-101 leader arm is connected to "
            "(e.g. /dev/ttyACM0 on Linux, COM3 on Windows). "
            "Machine-specific -- run `ls /dev/ttyACM*` (Linux/Mac) "
            "or check Device Manager (Windows) to find yours."
        ),
    )
    parser.add_argument(
        "--leader-id",
        default="leader",
    )
    parser.add_argument(
        "--endpoint",
        default="tcp://127.0.0.1:5557",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
    )
    return parser.parse_args()


def normalize_leader_action(
    raw_action: dict[str, float],
) -> dict[str, float]:
    """Normalize LeRobot action keys to the wire protocol."""
    normalized: dict[str, float] = {}

    for protocol_key in JOINT_KEYS:
        candidates = (
            protocol_key,
            protocol_key.removesuffix(".pos"),
            f"arm_{protocol_key}",
            f"arm_{protocol_key.removesuffix('.pos')}",
        )

        for candidate in candidates:
            if candidate in raw_action:
                normalized[protocol_key] = float(
                    raw_action[candidate]
                )
                break
        else:
            raise KeyError(
                f"Leader action is missing {protocol_key}. "
                f"Available keys: {sorted(raw_action)}"
            )

    return normalized


def main() -> int:
    args = parse_args()

    if args.fps <= 0:
        raise ValueError("--fps must be positive")

    stop_requested = False

    def request_stop(*_: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    config = SO101LeaderConfig(
        port=args.port,
        id=args.leader_id,
    )
    leader = SO101Leader(config)

    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.setsockopt(zmq.LINGER, 0)
    publisher.bind(args.endpoint)

    period = 1.0 / args.fps
    sequence = 0

    try:
        leader.connect()

        if not leader.is_connected:
            raise RuntimeError(
                "SO-101 Leader failed to connect"
            )

        print(
            "SO-101 Leader connected:",
            args.port,
            f"(id={args.leader_id})",
        )
        print(
            "Publishing at",
            args.endpoint,
            f"({args.fps:g} Hz)",
        )

        while not stop_requested:
            started = time.perf_counter()

            raw_action = leader.get_action()
            joints = normalize_leader_action(raw_action)

            message = LeaderMessage(
                timestamp=time.time(),
                sequence=sequence,
                joints=joints,
            )
            publisher.send(
                encode_leader_message(message)
            )
            sequence += 1

            remaining = (
                period
                - (time.perf_counter() - started)
            )
            if remaining > 0:
                time.sleep(remaining)

        return 0

    finally:
        try:
            if leader.is_connected:
                leader.disconnect()
        finally:
            publisher.close()
            context.term()


if __name__ == "__main__":
    sys.exit(main())
