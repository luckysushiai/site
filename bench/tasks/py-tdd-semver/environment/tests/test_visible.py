import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("WORKDIR") or str(Path(__file__).resolve().parents[1]))
from cmp_semver import cmp_semver


def test_equal():
    assert cmp_semver("1.0.0", "1.0.0") == 0


def test_patch():
    assert cmp_semver("1.0.1", "1.0.0") == 1


def test_release_beats_prerelease():
    assert cmp_semver("1.0.0", "1.0.0-alpha") == 1


def test_minor_is_numeric():
    assert cmp_semver("1.10.0", "1.2.0") == 1


if __name__ == "__main__":
    test_equal()
    test_patch()
    test_release_beats_prerelease()
    test_minor_is_numeric()
    print("visible ok")
