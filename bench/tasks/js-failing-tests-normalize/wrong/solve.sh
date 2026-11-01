#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
mkdir -p "$ROOT/tests"
cat > "$ROOT/tests/normalize.test.js" <<'JS'
const test = require("node:test");
const assert = require("node:assert/strict");
const { normalizeTag } = require("../labels.js");

test("keeps the padding the current function emits", () => {
  assert.equal(normalizeTag("  AbC  "), " abc ");
});
JS
