#!/usr/bin/env bash
set -euo pipefail
ROOT="${WORKDIR:-/app}"
mkdir -p "$ROOT/tests"
cat > "$ROOT/tests/normalize.test.js" <<'JS'
const test = require("node:test");
const assert = require("node:assert/strict");
const { normalizeTag } = require("../labels.js");

test("trims and lowercases", () => {
  assert.equal(normalizeTag("  AbC  "), "abc");
});

test("collapses internal whitespace", () => {
  assert.equal(normalizeTag("a\t\tb"), "a b");
});

test("blank is empty", () => {
  assert.equal(normalizeTag("   "), "");
});
JS
