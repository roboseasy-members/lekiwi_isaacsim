#!/usr/bin/env bash
# SO-101 Leader 팔의 관절값을 30 Hz 로 읽어 ZMQ 로 보낸다 (텔레옵 전에 먼저 띄운다).
# 이 프로세스는 ROS 를 쓰지 않고 로컬 ZMQ 만 쓴다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-}"
CONDA="${CONDA_EXE:-$HOME/miniforge3/bin/conda}"
ENV_NAME="${LEROBOT_ENV:-lerobot_so102_b601}"

if [[ -z "$PORT" ]]; then
    echo "사용법: $0 /dev/ttyACM1" >&2
    exit 2
fi
if [[ ! -e "$PORT" ]]; then
    echo "시리얼 포트가 없다: $PORT" >&2
    exit 1
fi

echo "Leader 포트: $PORT"
echo "송신: tcp://127.0.0.1:5557 at 30 Hz"

env \
    -u ROS_DISTRO -u ROS_VERSION -u ROS_PYTHON_VERSION \
    -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH \
    -u PYTHONPATH -u LD_LIBRARY_PATH \
    "$CONDA" run --no-capture-output -n "$ENV_NAME" \
    python "$ROOT/scripts/leader_sender.py" \
    --port "$PORT" --leader-id leader --endpoint tcp://127.0.0.1:5557
