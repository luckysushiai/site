The repository root is `/app`. `/app/grade.py` exports `letter_grade(score)`.

Scores from 0 through 100 map to letters: 90-100 A, 80-89 B, 70-79 C, 60-69 D, and 0-59 F. A score outside 0 through 100 raises `ValueError`. Do not modify `/app/grade.py`.

`/app/tests/test_grade.py` has one test. Extend it with module-level `test_*` functions that use `assert` and import only `grade`. The tests must pass on this module and must fail on at least 8 of the 10 hidden mutants. A mutant is a single operator, boundary, or return-value edit. Do not open files or read the source of `grade.py`.
