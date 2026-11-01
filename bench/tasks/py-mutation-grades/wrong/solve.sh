#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
HERE="$(cd "$(dirname "$0")" && pwd)"
cp "$HERE/test_grade.py" "$ROOT/tests/test_grade.py"
