#!/usr/bin/env bash
# LeKiwi 4대 텔레옵 (키보드 1개 + SO-101 Leader 팔 1개, T/F 로 조종 대상 전환).
#
# 경로는 이 스크립트 위치 기준으로 잡으므로 저장소를 어디에 두든 동작한다.
# Isaac Sim 환경과 ROS 환경을 섞으면 깨지므로 ROS 변수를 벗겨낸 뒤 conda 환경으로 넘긴다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE="${STAGE:-$ROOT/stages/lekiwi_arena_3p0x2p0_net_R_4robots_turf_grip.usd}"
CONDA="${CONDA_EXE:-$HOME/miniforge3/bin/conda}"
ENV_NAME="${ISAACSIM_ENV:-isaacsim-6.0.1}"

if [[ ! -f "$STAGE" ]]; then
    echo "스테이지가 없다: $STAGE" >&2
    echo "arena/ 의 생성 스크립트로 다시 만들거나 STAGE= 로 지정하라" >&2
    exit 1
fi

echo "스테이지: $STAGE"
echo "조작: T/F 로봇 전환 · W/S/A/D 이동 · Z/X 회전 · Q 정지 · Esc 종료"

env \
    -u ROS_DISTRO -u ROS_VERSION -u ROS_PYTHON_VERSION \
    -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH \
    -u PYTHONPATH -u LD_LIBRARY_PATH \
    ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-72}" \
    OMNI_KIT_ACCEPT_EULA=YES \
    "$CONDA" run --no-capture-output -n "$ENV_NAME" \
    python "$ROOT/scripts/teleoperate_four_switchable.py" --stage "$STAGE" "$@"
