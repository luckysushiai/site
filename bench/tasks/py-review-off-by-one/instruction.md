The repository root is `/app`. Read `/app/paginate.py` and the diff in `/app/changes.diff`.

One bug was introduced by that diff. Write `/app/answer.json` with these fields:

- `file`: the path of the buggy file relative to the repository root
- `line`: the 1-based line number of the buggy line, as a JSON integer
- `category`: one of `off-by-one`, `swapped-arguments`, `inverted-condition`, `missing-guard`, `wrong-rounding`

Do not modify `paginate.py`. A 1-based page of `page_size` items must not include an extra element.
