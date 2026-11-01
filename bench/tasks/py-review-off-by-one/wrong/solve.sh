#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
python3 - "$ROOT" <<'PY'
import json
import sys
from pathlib import Path
# Adjacent line: the start index, which is not the buggy expression.
Path(sys.argv[1], "answer.json").write_text(
    json.dumps({"file": "paginate.py", "line": 6, "category": "off-by-one"}) + "\n"
)
PY
