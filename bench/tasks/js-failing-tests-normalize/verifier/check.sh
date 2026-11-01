#!/usr/bin/env bash
# HIDDEN_VERIFIER_ONLY
set -u
ROOT="${WORKDIR:-/app}"
HERE="$(cd "$(dirname "$0")" && pwd)"
TEST="$ROOT/tests/normalize.test.js"
if [ ! -f "$TEST" ]; then
  echo "missing tests/normalize.test.js" >&2
  exit 1
fi
if ! grep -q "labels.js" "$TEST"; then
  echo "tests must load labels.js" >&2
  exit 1
fi
run() {
  node --test "$TEST"
}
cp "$HERE/buggy_labels.js" "$ROOT/labels.js"
if run; then
  echo "tests passed on the buggy module" >&2
  exit 1
fi
cp "$HERE/fixed_a.js" "$ROOT/labels.js"
if ! run; then
  echo "tests failed on fixed_a" >&2
  exit 1
fi
cp "$HERE/fixed_b.js" "$ROOT/labels.js"
if ! run; then
  echo "tests failed on fixed_b" >&2
  exit 1
fi
exit 0
