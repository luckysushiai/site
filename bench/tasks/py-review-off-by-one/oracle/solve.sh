#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
python3 - "$ROOT" <<'PY'
import json
import sys
from pathlib import Path
Path(sys.argv[1], "answer.json").write_text(
    json.dumps({"file": "paginate.py", "line": 7, "category": "off-by-one"}) + "\n"
)
PY
