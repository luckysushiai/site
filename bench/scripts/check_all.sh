#!/usr/bin/env bash
# Run every M3 proof: placebo test, hidden-marker check, oracle/nop/wrong, dry-run schema.
set -u
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BENCH"
if [ -d "${HOME:-}/.local/bin" ]; then
  export PATH="${HOME}/.local/bin:${PATH}"
fi
fail=0

echo "== placebo =="
if python3 scripts/test_placebo.py; then
  echo "placebo: pass"
else
  echo "placebo: fail"
  fail=1
fi

echo
echo "== hidden =="
if python3 scripts/check_hidden.py; then
  echo "hidden: pass"
else
  echo "hidden: fail"
  fail=1
fi

echo
echo "== layout =="
if python3 scripts/check_layout.py; then
  echo "layout: pass"
else
  echo "layout: fail"
  fail=1
fi

echo
printf '%-32s %-8s %-8s %-8s\n' TASK ORACLE NOP WRONG
printf '%-32s %-8s %-8s %-8s\n' ---- ------ --- -----
for task_dir in tasks/*/; do
  name="$(basename "$task_dir")"
  cells=()
  for agent in oracle nop wrong; do
    verdict="$(python3 scripts/run_trial.py "$name" "$agent")"
    code=$?
    if [ "$code" -eq 2 ]; then
      verdict="error"
    fi
    cells+=("$verdict")
  done
  printf '%-32s %-8s %-8s %-8s\n' "$name" "${cells[0]}" "${cells[1]}" "${cells[2]}"
  if [ "${cells[0]}" != "pass" ] || [ "${cells[1]}" != "fail" ] || [ "${cells[2]}" != "fail" ]; then
    fail=1
    echo "---- $name logs ----"
    python3 scripts/run_trial.py "$name" oracle --log >&2 || true
    python3 scripts/run_trial.py "$name" nop --log >&2 || true
    python3 scripts/run_trial.py "$name" wrong --log >&2 || true
  fi
done

echo
echo "== dry-run record =="
if python3 runs/validate.py runs/dry-run-2026-11-01/run.json --expect-dry-run; then
  echo "dry-run: pass"
else
  echo "dry-run: fail"
  fail=1
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "check_all: pass"
else
  echo "check_all: fail"
fi
exit "$fail"
