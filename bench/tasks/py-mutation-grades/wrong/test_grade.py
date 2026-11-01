import grade


def test_high_a():
    assert grade.letter_grade(95) == "A"


def test_low_failing_score():
    assert grade.letter_grade(50) == "F"
