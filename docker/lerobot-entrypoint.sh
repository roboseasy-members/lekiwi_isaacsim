#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${HOME}" "${HF_HOME:-${HOME}/.cache/huggingface}" \
    /data/datasets /data/outputs /data/calibration
if [[ "${1:-check}" == check ]]; then
    if (($#)); then shift; fi
    exec python /opt/lekiwi/tools/check_runtime.py "$@"
fi
exec "$@"
