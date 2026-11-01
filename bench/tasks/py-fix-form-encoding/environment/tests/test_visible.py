# Visible checks. They pass on the current decoder and on a correct one.
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("WORKDIR") or str(Path(__file__).resolve().parents[1]))
import parser as form


def main():
    assert form.parse_qs("") == {}
    assert form.parse_qs("a=b&c=d") == {"a": "b", "c": "d"}
    assert form.parse_qs("flag") == {"flag": ""}
    assert form.parse_qs("a=b=c") == {"a": "b=c"}
    print("visible ok")


if __name__ == "__main__":
    main()
