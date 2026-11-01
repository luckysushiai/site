// HIDDEN_VERIFIER_ONLY
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const { retryDelay } = require(path.join(process.env.WORKDIR, "retry.js"));

test("half up", () => {
  assert.equal(retryDelay(3, { baseMs: 10, capMs: 1000, factor: 1.5 }), 23);
});
test("stays at the cap", () => {
  assert.equal(retryDelay(8, { baseMs: 100, capMs: 1000, factor: 2 }), 1000);
});
test("attempt must be at least 1", () => {
  assert.throws(() => retryDelay(0, { baseMs: 100, capMs: 1000, factor: 2 }), TypeError);
});
test("factor below 1 is rejected", () => {
  assert.throws(() => retryDelay(1, { baseMs: 100, capMs: 1000, factor: 0.5 }), TypeError);
});
