The repository root is `/app`. `/app/parser.py` exports `parse_qs(raw)`.

Decode one `application/x-www-form-urlencoded` string. An empty string returns `{}`. Split pairs on `&` and ignore empty pairs. The first `=` separates the key and the value; further `=` characters stay in the value. A pair with no `=` has an empty value. Duplicate keys keep the last value.

`+` is a space. `%` followed by two hex digits is one decoded byte (the hex digits are case-insensitive). Decode both keys and values.

`/app/tests/test_visible.py` already passes. Keep it passing. The hidden suite checks `+` and percent-encoding. Edit `/app/parser.py` only.
