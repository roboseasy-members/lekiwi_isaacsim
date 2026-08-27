#!/usr/bin/env bash
set -euo pipefail

readonly CONTAINER_NAME="lekiwi-usd-build"
readonly IMAGE="nvcr.io/nvidia/isaac-sim:5.1.0"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/tmp/lekiwi_usd_build.log"

python3 "${SCRIPT_DIR}/build_urdf.py"

docker_cmd=(docker)
if ! docker info >/dev/null 2>&1; then
    docker_cmd=(sudo docker)
fi

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
        exit 1
    fi
    "${docker_cmd[@]}" rm "${CONTAINER_NAME}" >/dev/null
fi

echo "Writing USD build output to ${LOG_FILE}."
"${docker_cmd[@]}" run --rm \
    --name "${CONTAINER_NAME}" \
    --gpus all \
    --network host \
    --ipc host \
    --group-add "$(id -g)" \
    -e ACCEPT_EULA=Y \
    -e PRIVACY_CONSENT=Y \
    -e LEKIWI_ASSET_DIR=/workspace/assets/lekiwi_soarm \
    -v "${SCRIPT_DIR}:/workspace:rw" \
    -v lekiwi-isaacsim-kit-cache:/isaac-sim/kit/cache:rw \
    -v lekiwi-isaacsim-ov-cache:/root/.cache/ov:rw \
    -v lekiwi-isaacsim-pip-cache:/root/.cache/pip:rw \
    -v lekiwi-isaacsim-gl-cache:/root/.cache/nvidia/GLCache:rw \
    -v lekiwi-isaacsim-compute-cache:/root/.nv/ComputeCache:rw \
    --entrypoint /bin/bash \
    "${IMAGE}" \
    -lc '/isaac-sim/python.sh /workspace/build_usd.py' \
    2>&1 | tee "${LOG_FILE}"

exit "${PIPESTATUS[0]}"
