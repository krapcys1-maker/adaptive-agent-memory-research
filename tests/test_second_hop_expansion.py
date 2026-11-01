"""Deterministic tests for SECOND_HOP_ASSOCIATIVE_EXPANSION (Mechanism G).
No LLM call, no network -- search_fn is injected/mocked.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.second_hop_expansion import second_hop_expansion  # noqa: E402


def test_appends_genuinely_new_second_hop_item() -> None:
    top10 = [{"id": "a", "memory": "seed fact"}, {"id": "b", "memory": "other fact"}]
    hits = [{"id": "a", "memory": "seed fact"}, {"id": "c", "memory": "new fact"}]
    rendered, trace = second_hop_expansion(top10, lambda q, limit: hits)
    assert rendered == ["seed fact", "other fact", "[associated] new fact"]
    assert trace["inert"] is False
    assert trace["hop2_new_items"] == 1


def test_inert_when_second_hop_returns_nothing_new() -> None:
    top10 = [{"id": "a", "memory": "seed fact"}, {"id": "b", "memory": "other fact"}]
    hits = [{"id": "a", "memory": "seed fact"}, {"id": "b", "memory": "other fact"}]
    rendered, trace = second_hop_expansion(top10, lambda q, limit: hits)
    assert rendered == ["seed fact", "other fact"]
    assert trace["inert"] is True
    assert trace["hop2_new_items"] == 0


def test_inert_with_empty_compact_retrieval() -> None:
    rendered, trace = second_hop_expansion([], lambda q, limit: [])
    assert rendered == []
    assert trace["inert"] is True
    assert trace["hop2_fired"] is False


def test_second_hop_query_is_seeded_by_top1_text() -> None:
    top10 = [{"id": "a", "memory": "the exact seed text"}]
    captured = {}

    def search_fn(query, limit):
        captured["query"] = query
        captured["limit"] = limit
        return []

    second_hop_expansion(top10, search_fn)
    assert captured["query"] == "the exact seed text"
    assert captured["limit"] == 3


def test_caps_new_items_at_max_new() -> None:
    top10 = [{"id": "a", "memory": "seed"}]
    hits = [{"id": "a", "memory": "seed"}, {"id": "b", "memory": "new1"}, {"id": "c", "memory": "new2"}]
    rendered, trace = second_hop_expansion(top10, lambda q, limit: hits, max_new=1)
    assert rendered == ["seed", "[associated] new1"]
    assert trace["hop2_new_items"] == 2  # both counted as found, only 1 rendered


def test_empty_seed_text_does_not_crash_and_is_inert() -> None:
    top10 = [{"id": "a", "memory": ""}]
    rendered, trace = second_hop_expansion(top10, lambda q, limit: [{"id": "z", "memory": "x"}])
    assert trace["inert"] is True
