"""Deterministic token count for placebo length matching.

This is the bench's own splitter, not a provider tokenizer. M3 cannot call a
model API, including a countTokens endpoint. A token is one word (``\\w+``) or
one punctuation mark. Whitespace is not a token.
"""

from __future__ import annotations

import re

_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text)


def token_count(text: str) -> int:
    return len(tokenize(text))
