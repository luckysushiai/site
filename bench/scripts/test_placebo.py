"""Tests for the length-matched placebo generator."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from placebo import DENYLIST, WORDLIST, generate_placebo
from tokens import tokenize


SAMPLE_SKILL = """---
name: sample-review
description: Review a diff and write a failing test when a bug remains.
---

# Review

When you review code, write a failing test that exposes the bug before you fix it.
Check coverage and mutation score. Use pytest.
"""


class PlaceboTests(unittest.TestCase):
    def test_wordlist_has_no_task_vocabulary(self):
        for word in WORDLIST:
            self.assertNotIn(word, DENYLIST)
            self.assertEqual(tokenize(word), [word])

    def test_equal_token_length(self):
        placebo = generate_placebo(SAMPLE_SKILL, "sample/skill")
        self.assertEqual(len(tokenize(placebo)), len(tokenize(SAMPLE_SKILL)))

    def test_deterministic(self):
        first = generate_placebo(SAMPLE_SKILL, "owner/slug")
        second = generate_placebo(SAMPLE_SKILL, "owner/slug")
        self.assertEqual(first, second)

    def test_skill_id_changes_the_text(self):
        self.assertNotEqual(
            generate_placebo(SAMPLE_SKILL, "owner/one"),
            generate_placebo(SAMPLE_SKILL, "owner/two"),
        )

    def test_no_task_relevant_tokens(self):
        placebo = generate_placebo(SAMPLE_SKILL, "owner/slug")
        for token in tokenize(placebo):
            self.assertIn(token, WORDLIST)
            self.assertNotIn(token.lower(), DENYLIST)

    def test_does_not_copy_source_words(self):
        placebo = generate_placebo(SAMPLE_SKILL, "owner/slug")
        source_words = {tok.lower() for tok in tokenize(SAMPLE_SKILL) if tok.isalpha()}
        leaked = source_words & {tok.lower() for tok in tokenize(placebo)}
        self.assertEqual(leaked, set())

    def test_empty_source(self):
        self.assertEqual(generate_placebo("", "owner/slug"), "")

    def test_length_tracks_source(self):
        short = generate_placebo("one two three", "owner/slug")
        long = generate_placebo("one two three four five", "owner/slug")
        self.assertEqual(len(tokenize(short)), 3)
        self.assertEqual(len(tokenize(long)), 5)


if __name__ == "__main__":
    unittest.main()
