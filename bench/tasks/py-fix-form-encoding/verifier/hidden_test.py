# HIDDEN_VERIFIER_ONLY
import os
import sys

sys.path.insert(0, os.environ["WORKDIR"])
import parser as form

failures = 0


def expect(name, got, want):
    global failures
    if got != want:
        print("%s: %r != %r" % (name, got, want))
        failures += 1


def main():
    expect("plus", form.parse_qs("a+b=c+d"), {"a b": "c d"})
    expect("space", form.parse_qs("q=hello%20world"), {"q": "hello world"})
    expect("literal plus", form.parse_qs("a=%2B"), {"a": "+"})
    expect("plus key", form.parse_qs("%2B=ok"), {"+": "ok"})
    expect("last wins", form.parse_qs("a=1&a=2"), {"a": "2"})
    if failures:
        raise SystemExit(1)
    print("hidden ok")


if __name__ == "__main__":
    main()
