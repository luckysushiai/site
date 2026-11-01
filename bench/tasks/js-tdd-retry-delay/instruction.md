The repository root is `/app`. Implement `retryDelay(attempt, options)` in `/app/retry.js` and export it.

`options.baseMs` and `options.capMs` are integers, `baseMs >= 0`, and `capMs >= baseMs`. `options.factor` is a finite number `>= 1`. `attempt` is an integer `>= 1`. Anything else throws `TypeError`.

The delay is `baseMs * factor ** (attempt - 1)`, rounded half up to an integer (a fractional part of .5 rounds up), then capped by `capMs`.

With `{ baseMs: 100, capMs: 1000, factor: 2 }`, attempts 1, 2, 4, and 5 return 100, 200, 800, and 1000. `/app/tests/visible.test.js` covers those cases. The hidden suite covers rounding and rejected inputs.
