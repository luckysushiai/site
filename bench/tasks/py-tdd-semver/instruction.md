The repository root is `/app`. Implement `cmp_semver(left, right)` in `/app/cmp_semver.py`. It returns `-1`, `0`, or `1`.

Accept only `MAJOR.MINOR.PATCH` with an optional pre-release after one `-`. Each core field is a decimal integer with no leading zero (`0` is allowed). Pre-release identifiers are split on `.`. A numeric identifier is digits with no leading zero. Any other identifier is non-empty ASCII letters, digits, and hyphens. `+` build metadata is rejected with `ValueError`. Invalid strings raise `ValueError`.

Compare core fields numerically. A version with a pre-release is lower than the same core without one. Pre-release identifiers are compared left to right: numeric identifiers as integers, non-numeric identifiers as ASCII text, and a numeric identifier is lower than a non-numeric one. If every compared identifier is equal, the longer pre-release is higher.

Examples: `cmp_semver("1.0.0", "1.0.0")` is `0`, `cmp_semver("1.0.1", "1.0.0")` is `1`, `cmp_semver("1.0.0", "1.0.0-alpha")` is `1`, and `cmp_semver("1.10.0", "1.2.0")` is `1`. `/app/tests/test_visible.py` covers those examples. The hidden suite covers pre-release fields and rejected strings.
