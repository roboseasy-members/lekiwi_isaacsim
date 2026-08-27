#!/usr/bin/env bash
set -euo pipefail

readonly CONTAINER_NAME="lekiwi-keyboard-drive"
readonly IMAGE="nvcr.io/nvidia/isaac-sim:5.1.0"
readonly PROJECT_DIR="/home/ysj/youn_ws/lekiwi_urdf_after"
readonly ASSET_USD="${PROJECT_DIR}/isaac_sim/assets/lekiwi_soarm/usd/lekiwi_soarm.usd"
readonly XAUTH_FILE="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"
readonly XAUTH_COPY="/tmp/lekiwi_isaacsim.Xauthority"
readonly LOG_FILE="/tmp/lekiwi_keyboard_drive.log"
readonly CAPTURE_DIR="${PROJECT_DIR}/isaac_sim/captures"

if [[ ! -S /tmp/.X11-unix/X0 ]]; then
    echo "X11 display socket /tmp/.X11-unix/X0 was not found." >&2
    exit 1
fi

if [[ ! -r "${XAUTH_FILE}" ]]; then
    echo "Xauthority file is not readable: ${XAUTH_FILE}" >&2
    exit 1
fi

if [[ ! -f "${ASSET_USD}" ]]; then
    echo "Generated LeKiwi + SO101 USD was not found: ${ASSET_USD}" >&2
    echo "Run ./isaac_sim/build_usd.sh first." >&2
    exit 1
fi

install -m 0640 "${XAUTH_FILE}" "${XAUTH_COPY}"
mkdir -p "${CAPTURE_DIR}"
trap 'rm -f "${XAUTH_COPY}"' EXIT

docker_cmd=(docker)
if ! docker info >/dev/null 2>&1; then
    docker_cmd=(sudo docker)
fi

# Docker creates named-volume roots as root. Isaac Sim runs as uid/gid 1234,
# so initialize each cache once without recursively touching warm caches later.
"${docker_cmd[@]}" run --rm --user 0:0 \
    -v lekiwi-isaacsim-kit-cache:/cache/kit \
    -v lekiwi-isaacsim-ov-cache:/cache/ov \
    -v lekiwi-isaacsim-pip-cache:/cache/pip \
    -v lekiwi-isaacsim-gl-cache:/cache/gl \
    -v lekiwi-isaacsim-compute-cache:/cache/compute \
    --entrypoint /bin/bash "${IMAGE}" -lc '
        for cache_dir in /cache/kit /cache/ov /cache/pip /cache/gl /cache/compute; do
            marker="${cache_dir}/.lekiwi-owner-1234"
            if [[ ! -e "${marker}" ]]; then
                chown -R 1234:1234 "${cache_dir}"
                touch "${marker}"
                chown 1234:1234 "${marker}"
            fi
        done
    ' >/dev/null

if "${docker_cmd[@]}" ps -a --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
    if "${docker_cmd[@]}" ps --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
        echo "Container ${CONTAINER_NAME} is already running." >&2
        echo "Stop that exact container before retrying." >&2
        exit 1
    fi
    echo "Removing stopped temporary container ${CONTAINER_NAME}."
    "${docker_cmd[@]}" rm "${CONTAINER_NAME}" >/dev/null
fi

echo "Writing complete run output to ${LOG_FILE}."
"${docker_cmd[@]}" run --rm \
    --name "${CONTAINER_NAME}" \
    --gpus all \
    --network host \
    --ipc host \
    --hostname ysj \
    --group-add "$(id -g)" \
    -e ACCEPT_EULA=Y \
    -e PRIVACY_CONSENT=Y \
    -e DISPLAY="${DISPLAY:-:0}" \
    -e XAUTHORITY=/isaac-sim/.Xauthority \
    -e LEKIWI_USD=/workspace/assets/lekiwi_soarm/usd/lekiwi_soarm.usd \
    -e LEKIWI_CAPTURE_PATH=/captures/lekiwi_viewport.png \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v "${XAUTH_COPY}:/isaac-sim/.Xauthority:ro" \
    -v "${PROJECT_DIR}/isaac_sim:/workspace:ro" \
    -v "${CAPTURE_DIR}:/captures:rw" \
    -v lekiwi-isaacsim-kit-cache:/isaac-sim/kit/cache:rw \
    -v lekiwi-isaacsim-ov-cache:/root/.cache/ov:rw \
    -v lekiwi-isaacsim-pip-cache:/root/.cache/pip:rw \
    -v lekiwi-isaacsim-gl-cache:/root/.cache/nvidia/GLCache:rw \
    -v lekiwi-isaacsim-compute-cache:/root/.nv/ComputeCache:rw \
    --entrypoint /bin/bash \
    "${IMAGE}" \
    -lc '/isaac-sim/python.sh /workspace/keyboard_drive.py' \
    2>&1 | tee "${LOG_FILE}"

exit "${PIPESTATUS[0]}"
