"""Deterministic tests for TEMPORAL_ANCHOR_AT_CONTEXT / Mechanism I's
TEMPORAL_BOUNDARY classifier and render. No LLM call, no network.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.temporal_anchor_at_context import (  # noqa: E402
    is_temporal_boundary, render_plain, render_with_anchor, session_date)


def test_classifier_accepts_two_event_duration_question() -> None:
    assert is_temporal_boundary(
        "temporal-reasoning",
        "How many days passed between my visit to the museum and the exhibit?")


def test_classifier_accepts_since_when_phrasing() -> None:
    assert is_temporal_boundary(
        "temporal-reasoning",
        "How many days had passed since I started lessons when I visited the tech?")


def test_classifier_rejects_filter_count_shape() -> None:
    assert not is_temporal_boundary(
        "temporal-reasoning", "How many doctor's appointments did I have in March?")


def test_classifier_rejects_wrong_question_type() -> None:
    assert not is_temporal_boundary(
        "single-session-user",
        "How many days did it take to receive my package after I ordered it?")


def test_classifier_rejects_no_unit_word() -> None:
    assert not is_temporal_boundary("temporal-reasoning", "How many times did I visit since June?")


def test_session_date_parses_arena_timestamp_format() -> None:
    assert session_date("2023/05/25 (Thu) 06:04") == "2023-05-25"


def test_render_with_anchor_prefixes_date_and_drops_blanks() -> None:
    raw = [{"memory": "  fact one  ", "metadata": {"timestamp": "2023/05/25 (Thu) 06:04"}},
          {"memory": ""}, {"memory": "fact two", "metadata": {}}]
    assert render_with_anchor(raw) == ["[2023-05-25] fact one", "fact two"]


def test_render_plain_matches_base_shape() -> None:
    raw = [{"memory": "  fact one  "}, {"memory": ""}, {"memory": "fact two"}]
    assert render_plain(raw) == ["fact one", "fact two"]


def test_render_with_anchor_empty_input() -> None:
    assert render_with_anchor([]) == []
