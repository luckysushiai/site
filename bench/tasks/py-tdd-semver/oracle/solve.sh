#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
HERE="$(cd "$(dirname "$0")" && pwd)"
cp "$HERE/cmp_semver.py" "$ROOT/cmp_semver.py"
