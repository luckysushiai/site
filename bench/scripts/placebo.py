"""Length-matched placebo skill text.

The placebo arm gives the agent a skill-shaped document with the same token
count as the real skill and none of the task vocabulary. Generation is a pure
function of ``skill_id`` and the source text: same inputs, same output, no
network and no clock.

Tokens are drawn from a fixed word list. The list is disjoint from the task
denylist, so the placebo cannot smuggle review, test, or debugging advice.
"""

from __future__ import annotations

import hashlib
import random

from tokens import tokenize

# Task vocabulary that must not appear as a placebo token. Matched whole-token,
# case-insensitive. Keep this list aligned with test_placebo.py.
DENYLIST = frozenset(
    {
        "assert",
        "assertion",
        "branch",
        "bug",
        "bugs",
        "code",
        "codes",
        "coverage",
        "debug",
        "debugging",
        "diff",
        "diffs",
        "error",
        "errors",
        "exception",
        "fail",
        "failing",
        "fails",
        "failure",
        "fix",
        "fixed",
        "fixture",
        "function",
        "functions",
        "import",
        "javascript",
        "line",
        "lines",
        "mutant",
        "mutants",
        "mutation",
        "null",
        "oracle",
        "parse",
        "parser",
        "patch",
        "python",
        "pytest",
        "review",
        "reviews",
        "spec",
        "suite",
        "test",
        "testing",
        "tests",
        "tdd",
        "undefined",
        "unittest",
        "verifier",
    }
)

# Unrelated concrete nouns. Every entry is a single lowercase word.
WORDLIST = (
    "apricot",
    "basalt",
    "birch",
    "cacao",
    "canoe",
    "cedar",
    "chalk",
    "cinder",
    "clover",
    "cobalt",
    "copper",
    "daisy",
    "dune",
    "estuary",
    "feldspar",
    "flannel",
    "flint",
    "fog",
    "granite",
    "hammock",
    "hazel",
    "heather",
    "honey",
    "iris",
    "ivory",
    "jasper",
    "juniper",
    "kettle",
    "linen",
    "lupin",
    "marble",
    "meadow",
    "mica",
    "mist",
    "moss",
    "nutmeg",
    "oak",
    "obsidian",
    "olive",
    "orchid",
    "otter",
    "pebble",
    "pine",
    "plum",
    "pond",
    "quartz",
    "quince",
    "raft",
    "reed",
    "river",
    "saffron",
    "sand",
    "spruce",
    "stone",
    "thistle",
    "tide",
    "timber",
    "tulip",
    "umber",
    "valley",
    "violet",
    "willow",
    "wool",
    "yarn",
)


def _check_wordlist() -> None:
    for word in WORDLIST:
        if not word.isalpha() or word != word.lower():
            raise RuntimeError(f"wordlist entry must be a lowercase word: {word}")
        if word in DENYLIST:
            raise RuntimeError(f"wordlist entry is task vocabulary: {word}")


_check_wordlist()


def generate_placebo(source: str, skill_id: str) -> str:
    """Return placebo text with the same token count as ``source``.

    ``skill_id`` is mixed into the seed so two skills that happen to share a
    body still get different filler. The source body is not copied.
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if not isinstance(skill_id, str) or skill_id.strip() == "":
        raise ValueError("skill_id must be a non-empty string")
    count = len(tokenize(source))
    if count == 0:
        return ""
    digest = hashlib.sha256(f"{skill_id}\n{source}".encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest, "big"))
    return " ".join(rng.choice(WORDLIST) for _ in range(count))
