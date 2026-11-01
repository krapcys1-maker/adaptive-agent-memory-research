"""Deterministic tests for HYDE_QUERY_REFORMULATION (Mechanism H).
No LLM call, no network.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.hyde_query_reformulation import (  # noqa: E402
    HYDE_PROMPT, hyde_prompt_hash, hyde_user_message, render_top10)


def test_render_top10_strips_blanks_and_whitespace() -> None:
    raw = [{"id": "a", "memory": "  fact one  "}, {"id": "b", "memory": ""},
          {"id": "c", "memory": "fact two"}, {"id": "d"}]
    assert render_top10(raw) == ["fact one", "fact two"]


def test_render_top10_empty_input() -> None:
    assert render_top10([]) == []


def test_render_top10_preserves_order() -> None:
    raw = [{"id": "z", "memory": "third"}, {"id": "a", "memory": "first"}]
    assert render_top10(raw) == ["third", "first"]


def test_hyde_user_message_format() -> None:
    assert hyde_user_message("How many cats?") == "Question: How many cats?"


def test_hyde_prompt_hash_stable_and_matches_prompt() -> None:
    import hashlib
    assert hyde_prompt_hash() == hashlib.sha256(HYDE_PROMPT.encode()).hexdigest()


def test_hyde_prompt_is_frozen_nonempty_text() -> None:
    assert isinstance(HYDE_PROMPT, str) and len(HYDE_PROMPT) > 20
