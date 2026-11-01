#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
mkdir -p "$ROOT/tests"
cat > "$ROOT/tests/test_split_bill.py" <<'PY'
from money import split_bill


def test_records_the_truncated_split():
    assert split_bill(100, 3) == [33, 33, 33]
PY
