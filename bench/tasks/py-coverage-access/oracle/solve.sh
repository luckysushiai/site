#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
HERE="$(cd "$(dirname "$0")" && pwd)"
cp "$HERE/test_access.py" "$ROOT/tests/test_access.py"
