#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
mkdir -p "$ROOT/tests"
cat > "$ROOT/tests/test_split_bill.py" <<'PY'
from money import split_bill


def test_remainder_goes_to_the_earlier_people():
    assert split_bill(100, 3) == [34, 33, 33]


def test_two_people_odd_total():
    assert split_bill(5, 2) == [3, 2]


def test_zero_total():
    assert split_bill(0, 4) == [0, 0, 0, 0]


def test_people_must_be_positive():
    try:
        split_bill(10, 0)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
PY
