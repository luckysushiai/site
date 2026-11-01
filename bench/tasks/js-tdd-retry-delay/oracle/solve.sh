#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
HERE="$(cd "$(dirname "$0")" && pwd)"
cp "$HERE/retry.js" "$ROOT/retry.js"
