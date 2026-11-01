import grade


def test_low_failing_score():
    assert grade.letter_grade(50) == "F"
