The repository root is `/app`. `split_bill` in `/app/money.py` divides a bill in integer cents across people.

The contract is: each person owes `total_cents // people` cents, and the first `total_cents % people` people owe one extra cent. `people <= 0` raises `ValueError`. Example: `split_bill(100, 3)` is `[34, 33, 33]`.

The current implementation drops the remainder. Do not modify `/app/money.py`. Add `/app/tests/test_split_bill.py` with module-level functions named `test_*` that use `assert`. Import `split_bill` from `money`. Do not use fixtures, classes, or any import other than `money`.

Your tests must fail on the current implementation and pass on a corrected one.
