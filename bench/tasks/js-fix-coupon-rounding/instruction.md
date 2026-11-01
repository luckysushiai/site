The repository root is `/app`. `/app/price.js` exports `priceAfterCoupon(cents, coupon)`.

`cents` is a non-negative integer. `coupon` is `{ type, value }`. `type` is `"percent"` or `"fixed"`. `value` is a non-negative integer. A percent must be from 0 through 100. Anything else throws `TypeError`.

A fixed coupon subtracts `value` cents and never returns a negative price. A percent coupon charges `cents * (100 - value) / 100`, rounded half up to the nearest cent (a tie of .5 rounds away from zero, which for these non-negative prices means up).

`/app/tests/visible.test.js` already passes. Keep those cases passing. The hidden suite includes amounts that are not exact cents before rounding. Edit `/app/price.js` only.
