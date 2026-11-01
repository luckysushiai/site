# HIDDEN_VERIFIER_ONLY
import os
import sys

sys.path.insert(0, os.environ["WORKDIR"])
from cmp_semver import cmp_semver


def test_numeric_prerelease_field():
    assert cmp_semver("1.0.0-rc.10", "1.0.0-rc.2") == 1


def test_numeric_prerelease_lower():
    assert cmp_semver("1.0.0-alpha.2", "1.0.0-alpha.10") == -1


def test_build_metadata_rejected():
    try:
        cmp_semver("1.0.0+build", "1.0.0")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_leading_zero_rejected():
    try:
        cmp_semver("01.0.0", "1.0.0")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


if __name__ == "__main__":
    test_numeric_prerelease_field()
    test_numeric_prerelease_lower()
    test_build_metadata_rejected()
    test_leading_zero_rejected()
    print("hidden ok")
