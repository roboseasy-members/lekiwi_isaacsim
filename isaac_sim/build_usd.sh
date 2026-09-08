#!/usr/bin/env bash
set -euo pipefail
readonly project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$project_dir/lekiwi" build-assets "$@"
