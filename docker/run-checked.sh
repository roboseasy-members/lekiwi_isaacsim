#!/usr/bin/env bash
# Kit can terminate with exit code zero during shutdown even after a Python
# exception. Require the task's completion marker as well as a zero exit code.
set -euo pipefail
marker="$1"
shift
log_dir="${LEKIWI_LOG_DIR:-/data/logs/sim}"
mkdir -p "$log_dir"
run_log="$(mktemp "$log_dir/check.XXXXXXXX.log")"
status=0
"$@" 2>&1 | tee "$run_log" || status=$?
if ((status == 0)) && ! grep -Fxq -- "$marker" "$run_log"; then
    echo "Required completion marker was not emitted: $marker (log: $run_log)" >&2
    status=1
fi
exit "$status"
