// HIDDEN_VERIFIER_ONLY
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const { retryDelay } = require(path.join(process.env.WORKDIR, "retry.js"));
const opts = { baseMs: 100, capMs: 1000, factor: 2 };

test("attempt 1", () => {
  assert.equal(retryDelay(1, opts), 100);
});
test("attempt 2", () => {
  assert.equal(retryDelay(2, opts), 200);
});
test("attempt 4", () => {
  assert.equal(retryDelay(4, opts), 800);
});
test("attempt 5 hits the cap", () => {
  assert.equal(retryDelay(5, opts), 1000);
});
