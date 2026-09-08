#!/usr/bin/env bash
set -euo pipefail

readonly sim_dir=/opt/lekiwi/isaac_sim
readonly checked=/opt/lekiwi/docker/run-checked.sh
command_name="${1:-keyboard}"
if (($#)); then shift; fi

if [[ "$command_name" != validate-assets && "${ACCEPT_EULA:-N}" != Y ]]; then
    echo 'Isaac Sim requires license acceptance. Read the license linked in README, then set ACCEPT_EULA=Y.' >&2
    exit 2
fi
mkdir -p "${HOME}" "${XDG_CACHE_HOME:-${HOME}/.cache}" /data/captures

case "$command_name" in
    basic) exec /isaac-sim/python.sh /opt/lekiwi/isaacsim_basic/run.py "$@" ;;
    basic-test) exec "$checked" 'ISAACSIM_BASIC_TEST result=PASS' /isaac-sim/python.sh /opt/lekiwi/isaacsim_basic/smoke_test.py "$@" ;;
    keyboard) exec /isaac-sim/python.sh "$sim_dir/keyboard_drive.py" "$@" ;;
    course) exec /isaac-sim/python.sh "$sim_dir/course_demo.py" "$@" ;;
    course-test) exec "$checked" 'LEKIWI_COURSE_TEST result=PASS' /isaac-sim/python.sh "$sim_dir/course_smoke_test.py" "$@" ;;
    validate-assets) exec "$checked" 'LEKIWI_VALIDATE result=PASS' /isaac-sim/python.sh "$sim_dir/validate_asset.py" "$@" ;;
    validate-usd) exec "$checked" 'LEKIWI_USD_VALIDATE result=PASS' /isaac-sim/python.sh "$sim_dir/validate_usd.py" "$@" ;;
    physics-test) exec "$checked" 'LEKIWI_PHYSICS_SMOKE result=PASS' /isaac-sim/python.sh "$sim_dir/physics_smoke_test.py" "$@" ;;
    arm-test) exec "$checked" 'SO101_ARM_TEST result=PASS' /isaac-sim/python.sh "$sim_dir/arm_smoke_test.py" "$@" ;;
    build-assets)
        # Build into a fresh output directory; never overwrite shipped assets.
        build_dir="$(mktemp -d /data/asset-build.XXXXXXXX)"
        cp -a "$sim_dir/assets/lekiwi_soarm/." "$build_dir/"
        export LEKIWI_ASSET_DIR="$build_dir"
        /isaac-sim/python.sh "$sim_dir/build_urdf.py"
        "$checked" 'LEKIWI_USD_BUILD result=PASS' /isaac-sim/python.sh "$sim_dir/build_usd.py"
        export LEKIWI_USD="$build_dir/usd/lekiwi_soarm.usd"
        "$checked" 'LEKIWI_USD_VALIDATE result=PASS' /isaac-sim/python.sh "$sim_dir/validate_usd.py"
        echo "Generated bundle: $build_dir"
        ;;
    *) echo "Unknown simulation command: $command_name" >&2; exit 2 ;;
esac
