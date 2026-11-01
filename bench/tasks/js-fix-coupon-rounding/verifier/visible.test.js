// HIDDEN_VERIFIER_ONLY
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const { priceAfterCoupon } = require(path.join(process.env.WORKDIR, "price.js"));

test("ten percent of 1000", () => {
  assert.equal(priceAfterCoupon(1000, { type: "percent", value: 10 }), 900);
});
test("fixed coupon", () => {
  assert.equal(priceAfterCoupon(200, { type: "fixed", value: 50 }), 150);
});
test("fixed coupon cannot go below zero", () => {
  assert.equal(priceAfterCoupon(40, { type: "fixed", value: 100 }), 0);
});
test("zero percent", () => {
  assert.equal(priceAfterCoupon(500, { type: "percent", value: 0 }), 500);
});
test("one hundred percent", () => {
  assert.equal(priceAfterCoupon(500, { type: "percent", value: 100 }), 0);
});
