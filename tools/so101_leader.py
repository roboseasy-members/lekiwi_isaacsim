"""Interactive SO101 calibration and read-only position streaming (LeRobot 0.6.1).

No torque-enable or Goal_Position commands are issued. LeRobot connect/configure
does disable torque and write configuration: user confirmation precedes it.
"""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "isaac_sim"))
from teleop_bridge import JOINTS, atomic_json, make_packet


def choose_calibration(path, ask=input):
    """Always ask for an existing file, including when hardware already matches."""
    if not path.is_file():
        print(f"No calibration file found. Running new calibration: {path}")
        return True
    while True:
        answer = ask(
            f"Press ENTER to use provided calibration file associated with the id {path.stem}, "
            "or type 'c' and press ENTER to run calibration: "
        ).strip().lower()
        if answer == "c":
            return True
        if answer == "":
            return False
        if answer in ("q", "quit"):
            raise RuntimeError("사용자가 취소했습니다")
        print("Press ENTER to reuse, c to recalibrate, or q to cancel.")


def confirm_connection(ask=input):
    """Keep the pre-torque-release safety gate, without a typed confirmation word."""
    while True:
        answer = ask(
            "Support the SO101 leader arm and make sure power can be disconnected.\n"
            "Press ENTER to connect, disable torque and configure the motors (Ctrl+C to cancel)..."
        )
        if not answer.strip():
            return
        if answer.strip().lower() in ("q", "quit"):
            raise RuntimeError("사용자가 취소했습니다")
        print("Press ENTER to continue, or Ctrl+C to cancel.")


def validate_calibration(path):
    with path.open() as stream:
        data = json.load(stream)
    if set(data) != set(JOINTS):
        raise ValueError("Calibration must contain the six SO101 joints")
    for i, name in enumerate(JOINTS, 1):
        c = data[name]
        if (c.get("id") != i or c.get("drive_mode") not in (0, 1)
                or type(c.get("homing_offset")) is not int
                or type(c.get("range_min")) is not int or type(c.get("range_max")) is not int
                or not 0 <= c["range_min"] < c["range_max"] <= 4095):
            raise ValueError(f"Invalid SO101 calibration for {name}")
    return data


def verify_ready(leader):
    if not leader.is_calibrated:
        raise RuntimeError("Motor calibration read-back does not match; stopping")
    torque = leader.bus.sync_read("Torque_Enable", normalize=False)
    if set(torque) != set(JOINTS) or any(v != 0 for v in torque.values()):
        raise RuntimeError("Leader torque is not confirmed OFF; stopping")


def prepare(leader, path, recalibrate):
    """Preserve old files; LeRobot writes new calibration to a staging path."""
    if not recalibrate:
        validate_calibration(path)
        leader.bus.write_calibration(leader.calibration)
        verify_ready(leader)
    else:
        fd, temporary = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".json", dir=path.parent)
        os.close(fd)
        staged = Path(temporary)
        previous = leader.calibration_fpath
        try:
            leader.calibration = {}  # Avoid LeRobot's second, implicit reuse prompt.
            leader.calibration_fpath = staged
            leader.calibrate()
            validate_calibration(staged)
            verify_ready(leader)
            if path.exists():
                fd, backup = tempfile.mkstemp(prefix=f"{path.stem}.backup-", suffix=".json", dir=path.parent)
                os.close(fd)
                shutil.copy2(path, backup)
                print(f"기존 보정 백업: {backup}")
            os.replace(staged, path)
        finally:
            leader.calibration_fpath = previous
            staged.unlink(missing_ok=True)
    print(f"SO101 calibration=READY torque=OFF file={path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/so101")
    parser.add_argument("--id", required=True)
    parser.add_argument("--calibration-dir", type=Path, default=Path("/data/calibration/so101_leader"))
    parser.add_argument("--calibrate-only", action="store_true")
    parser.add_argument("--state", type=Path)
    parser.add_argument("--session")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.id):
        parser.error("id must contain only letters, digits, underscore or hyphen")
    if not args.calibrate_only and (not args.state or not args.session):
        parser.error("streaming requires --state and --session")
    if not sys.stdin.isatty():
        raise RuntimeError("Interactive terminal required; calibration choices cannot be skipped")
    args.calibration_dir.mkdir(parents=True, exist_ok=True)
    path = args.calibration_dir / f"{args.id}.json"
    # Lock for the whole connection, including prompts. No concurrent writer.
    with (args.calibration_dir / ".connection.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        recalibrate = choose_calibration(path)
        if not recalibrate:
            validate_calibration(path)  # Fail before touching hardware on corrupt files.
        confirm_connection()
        from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig

        # For recalibration, avoid loading a corrupt old file in the constructor.
        with tempfile.TemporaryDirectory(prefix="so101-calibration-") as empty:
            config = SO101LeaderConfig(port=args.port, id=args.id, use_degrees=True,
                                       num_read_retries=0,
                                       calibration_dir=Path(empty) if recalibrate else args.calibration_dir)
            leader = SO101Leader(config)
            leader.calibration_fpath = path
            sequence = 0
            try:
                leader.connect(calibrate=False)
                prepare(leader, path, recalibrate)
                if args.calibrate_only:
                    return
                print("리더 위치 전송 시작. Isaac 화면에서 자세/방향을 확인하고 R로 활성화하세요. Ctrl+C 종료.", flush=True)
                while True:
                    started = time.monotonic()
                    action = leader.get_action()
                    atomic_json(args.state, make_packet(action, args.session, sequence))
                    sequence += 1
                    time.sleep(max(0.0, 1 / 30 - (time.monotonic() - started)))
            finally:
                try:
                    if args.state:
                        atomic_json(args.state, make_packet({}, args.session, sequence, connected=False))
                except OSError as exc:
                    print(f"정지 상태 기록 실패: {exc}; 수신 측 watchdog으로 정지합니다.", file=sys.stderr)
                if leader.is_connected:
                    try:
                        torque = leader.bus.sync_read("Torque_Enable", normalize=False)
                        print(f"종료 시 Torque_Enable: {torque}", flush=True)
                    except Exception as exc:
                        print(f"토크 상태 확인 불가: {exc}. 상태를 추측하지 말고 장비를 확인하세요.", file=sys.stderr)
                    leader.disconnect()


def interrupted(*_):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except KeyboardInterrupt:
        print("SO101 stopped", flush=True)
    except Exception as exc:
        print(f"SO101 result=FAIL: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
