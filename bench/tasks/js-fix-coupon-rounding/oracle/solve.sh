#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
HERE="$(cd "$(dirname "$0")" && pwd)"
cp "$HERE/price.js" "$ROOT/price.js"
