The repository root is `/app`. `/app/access.py` exports `access_decision(user, resource)`. Do not modify it.

`/app/tests/test_access.py` has two tests. Add more module-level `test_*` functions in that file until line coverage is at least 90% and branch coverage is at least 80%.

Line coverage counts statements in `access.py`. Branch coverage counts each `if` statement as two outcomes, the true body and the false body. A boolean `and` or `or` inside a condition is not a separate branch. Import only `access`. Use `assert`. Do not open files or read the source of `access.py`.
