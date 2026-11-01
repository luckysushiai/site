// HIDDEN_VERIFIER_ONLY
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const { priceAfterCoupon } = require(path.join(process.env.WORKDIR, "price.js"));

test("half up on a half cent", () => {
  assert.equal(priceAfterCoupon(15, { type: "percent", value: 10 }), 14);
});
test("half up does not ceil a .4", () => {
  assert.equal(priceAfterCoupon(3, { type: "percent", value: 20 }), 2);
});
