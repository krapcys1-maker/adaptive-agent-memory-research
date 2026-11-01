"""Deterministic tests for RETRIEVAL_CONFIDENCE_SIGNAL (Mechanism D). No LLM
call, no network.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.retrieval_confidence_signal import (  # noqa: E402
    retrieval_confidence_signal, MARGIN_THRESHOLD, CONFIDENCE_NOTE,
)


def test_flags_when_margin_below_threshold() -> None:
    ctx = ["a", "b", "c"]
    rendered, trace = retrieval_confidence_signal(ctx, [0.70, 0.65, 0.20])
    assert trace["margin"] == 0.05 < MARGIN_THRESHOLD
    assert trace["flagged"] is True
    assert rendered == ctx + [CONFIDENCE_NOTE]


def test_inert_when_margin_at_or_above_threshold() -> None:
    ctx = ["a", "b", "c"]
    rendered, trace = retrieval_confidence_signal(ctx, [0.80, 0.60, 0.20])
    assert trace["margin"] == 0.20 >= MARGIN_THRESHOLD
    assert trace["flagged"] is False
    assert rendered == ctx


def test_exactly_at_threshold_is_not_flagged() -> None:
    """>= threshold means confident; the boundary itself does not flag."""
    ctx = ["a", "b"]
    rendered, trace = retrieval_confidence_signal(ctx, [0.60, 0.50])
    assert trace["margin"] == MARGIN_THRESHOLD
    assert trace["flagged"] is False
    assert rendered == ctx


def test_inert_with_fewer_than_two_items() -> None:
    rendered, trace = retrieval_confidence_signal(["only one"], [0.9])
    assert rendered == ["only one"]
    assert trace["inert"] is True


def test_inert_with_zero_items() -> None:
    rendered, trace = retrieval_confidence_signal([], [])
    assert rendered == []
    assert trace["inert"] is True


def test_inert_when_scores_missing_or_none() -> None:
    ctx = ["a", "b", "c"]
    rendered, trace = retrieval_confidence_signal(ctx, [None, None, None])
    assert rendered == ctx
    assert trace["inert"] is True


def test_inert_when_only_one_score_provided() -> None:
    ctx = ["a", "b"]
    rendered, trace = retrieval_confidence_signal(ctx, [0.9])
    assert rendered == ctx
    assert trace["inert"] is True


def test_note_is_fixed_text_never_references_content() -> None:
    ctx = ["Works at Microsoft", "Left Microsoft and started at Google"]
    _, trace1 = retrieval_confidence_signal(ctx, [0.5, 0.45])
    rendered, _ = retrieval_confidence_signal(ctx, [0.5, 0.45])
    assert rendered[-1] == CONFIDENCE_NOTE
    assert "Microsoft" not in CONFIDENCE_NOTE and "Google" not in CONFIDENCE_NOTE
