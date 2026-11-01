"""Deterministic tests for RETRIEVAL_RANK_ANNOTATION (Mechanism F). No LLM
call, no network.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.retrieval_rank_annotation import retrieval_rank_annotation  # noqa: E402


def test_annotates_every_item_with_rank_and_score() -> None:
    ctx = ["a", "b", "c"]
    rendered, trace = retrieval_rank_annotation(ctx, [0.9, 0.5, 0.1])
    assert rendered == ["[rank 1/3, relevance 0.90] a",
                        "[rank 2/3, relevance 0.50] b",
                        "[rank 3/3, relevance 0.10] c"]
    assert trace["always_fires"] is True
    assert trace["n_scored"] == 3


def test_always_fires_even_with_no_scores() -> None:
    ctx = ["a", "b"]
    rendered, trace = retrieval_rank_annotation(ctx, [])
    assert rendered == ["[rank 1/2] a", "[rank 2/2] b"]
    assert trace["always_fires"] is True
    assert trace["n_scored"] == 0


def test_partial_scores_handled() -> None:
    ctx = ["a", "b", "c"]
    rendered, trace = retrieval_rank_annotation(ctx, [0.9])
    assert rendered[0] == "[rank 1/3, relevance 0.90] a"
    assert rendered[1] == "[rank 2/3] b"
    assert rendered[2] == "[rank 3/3] c"


def test_empty_context_is_inert() -> None:
    rendered, trace = retrieval_rank_annotation([], [])
    assert rendered == []
    assert trace["inert"] is True


def test_original_text_preserved_verbatim_after_prefix() -> None:
    ctx = ["Works at Microsoft, left in June"]
    rendered, _ = retrieval_rank_annotation(ctx, [0.7])
    assert rendered[0].endswith("Works at Microsoft, left in June")


def test_rank_total_matches_item_count() -> None:
    ctx = ["a", "b", "c", "d", "e"]
    rendered, _ = retrieval_rank_annotation(ctx, [0.5] * 5)
    assert all(f"/{len(ctx)}" in line for line in rendered)
