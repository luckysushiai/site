The repository root is `/app`. Read `/app/receipt.js` and the diff in `/app/changes.diff`.

`formatMoney` takes `(cents, currency)`. One call site in the diff passes those arguments in the wrong order. Write `/app/answer.json` with:

- `file`: path relative to the repository root
- `line`: the 1-based line number of the bad call, as a JSON integer
- `category`: one of `off-by-one`, `swapped-arguments`, `inverted-condition`, `missing-guard`, `wrong-rounding`

Do not modify `receipt.js`.
