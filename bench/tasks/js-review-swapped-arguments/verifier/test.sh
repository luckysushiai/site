#!/usr/bin/env bash
# HIDDEN_VERIFIER_ONLY
set -u
ROOT="${WORKDIR:-/app}"
HERE="$(cd "$(dirname "$0")" && pwd)"
export WORKDIR="$ROOT"
export VERIFIER_DIR="$HERE"

write_reward() {
  local dest=""
  if [ -n "${REWARD_PATH:-}" ]; then
    dest="$REWARD_PATH"
  elif [ -d /logs/verifier ]; then
    dest="/logs/verifier/reward.txt"
  fi
  if [ -n "$dest" ]; then
    mkdir -p "$(dirname "$dest")"
    printf '%s\n' "$1" > "$dest"
  fi
}

if node "$HERE/check.js"; then
  write_reward 1
  exit 0
fi
write_reward 0
exit 1
