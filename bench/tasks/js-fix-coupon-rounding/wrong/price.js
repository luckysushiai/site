function priceAfterCoupon(cents, coupon) {
  if (!Number.isInteger(cents) || cents < 0) {
    throw new TypeError("cents must be a non-negative integer");
  }
  if (!coupon || (coupon.type !== "percent" && coupon.type !== "fixed")) {
    throw new TypeError("coupon type must be percent or fixed");
  }
  if (!Number.isInteger(coupon.value) || coupon.value < 0) {
    throw new TypeError("coupon value must be a non-negative integer");
  }
  if (coupon.type === "percent") {
    if (coupon.value > 100) {
      throw new TypeError("percent must be from 0 to 100");
    }
    return Math.ceil((cents * (100 - coupon.value)) / 100);
  }
  return Math.max(0, cents - coupon.value);
}

module.exports = { priceAfterCoupon };
