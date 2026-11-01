The repository root is `/app`. `/app/labels.js` exports `normalizeTag`.

The contract: when `tag` is a string, trim both ends, lowercase, and collapse each internal run of whitespace to a single space. A string that is empty after trimming returns `""`. A non-string throws `TypeError`.

Example: `normalizeTag("  AbC  ")` is `"abc"`, and `normalizeTag("a\t\tb")` is `"a b"`.

The current function lowercases and collapses internal whitespace, but it does not trim. Do not modify `/app/labels.js`. Add `/app/tests/normalize.test.js` using `node:test` and `node:assert/strict`. Load the function with `require("../labels.js")`.

Your tests must fail on the current function and pass on a corrected one.
