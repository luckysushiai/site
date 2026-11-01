#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
python3 - "$ROOT" <<'PY'
import json, sys
from pathlib import Path
Path(sys.argv[1], "answer.json").write_text(
    json.dumps({"file": "receipt.js", "line": 8, "category": "swapped-arguments"}) + "\n"
)
PY
