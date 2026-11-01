import grade


def test_below_range():
    try:
        grade.letter_grade(-1)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_above_range():
    try:
        grade.letter_grade(101)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_zero():
    assert grade.letter_grade(0) == "F"


def test_low_failing_score():
    assert grade.letter_grade(50) == "F"


def test_fifty_nine():
    assert grade.letter_grade(59) == "F"


def test_sixty():
    assert grade.letter_grade(60) == "D"


def test_seventy():
    assert grade.letter_grade(70) == "C"


def test_eighty():
    assert grade.letter_grade(80) == "B"


def test_ninety():
    assert grade.letter_grade(90) == "A"


def test_hundred():
    assert grade.letter_grade(100) == "A"


def test_high_a():
    assert grade.letter_grade(95) == "A"
