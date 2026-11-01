#!/usr/bin/env python3
"""SECOND_HOP_ASSOCIATIVE_EXPANSION: Mechanism G. A live, on-demand second
Mem0 search() call seeded by the top-1 retrieved item's own text, appending
any genuinely NEW item (not already in the compact top-10) as an associated
second-hop result.

Source: A-MEM (agiresearch/A-mem, NeurIPS 2025)'s link-expansion pattern,
adapted to Mem0's existing search() API rather than a precomputed link graph
-- no new dependency, no write-side change. Targets RAW_PROVENANCE's own
documented single-hop limitation (`078150f1`-class misses, Ledger Entry H):
RAW_PROVENANCE only ever reaches the ONE session behind Mem0's top-1 hit;
this reaches a genuinely different memory item via a live associative query,
laterally rather than vertically.

Precondition verified at $0 before any paid call (docs/research/
EXTERNAL_DISCOVERY_CANDIDATE_POOL_V2.md): compact top-10 retrieval already
spans 2-7 distinct sessions per unit on its own; a second-hop query seeded
from the top-1 hit's own text surfaces a genuinely new item beyond the top-10
in ~25% of already-ingested units checked -- real, moderate, not the
near-zero rate that sank Mechanisms D and E.

The second Mem0 search() call is free in provider terms (Mem0's search makes
zero model calls, confirmed in this arena's own adapter docstring) -- this
mechanism's only cost is the same reader+judge pattern every other AAMR
mechanism already pays for.
"""

from __future__ import annotations

from typing import Any, Callable


def second_hop_expansion(top10_items: list[dict[str, Any]],
                         search_fn: Callable[[str, int], list[dict[str, Any]]],
                         max_new: int = 1) -> tuple[list[str], dict]:
    """`top10_items`: the compact retrieval's raw result dicts (with 'id' and
    'memory' keys, as Mem0's search() returns them -- NOT yet reduced to bare
    text). `search_fn(query, limit)`: a callable performing a second live
    Mem0 search (adapter-provided, so this module stays test-injectable and
    has no direct Mem0 dependency). Returns (rendered_context, trace).

    Inert (byte-identical to the plain top-10 text list) when top10_items is
    empty or the second-hop search returns nothing new.
    """
    base_texts = [str(item.get("memory", "")).strip() for item in top10_items
                 if str(item.get("memory", "")).strip()]
    trace = {"n_compact": len(base_texts), "hop2_fired": False,
             "hop2_new_items": 0, "inert": True}
    if not top10_items:
        return base_texts, trace

    top10_ids = {item.get("id") for item in top10_items if item.get("id")}
    seed_text = str(top10_items[0].get("memory", "")).strip()
    if not seed_text:
        return base_texts, trace

    hop2_results = search_fn(seed_text, 3) or []
    new_items = [r for r in hop2_results
                if r.get("id") not in top10_ids and str(r.get("memory", "")).strip()]
    trace["hop2_fired"] = True
    trace["hop2_new_items"] = len(new_items)
    if not new_items:
        return base_texts, trace

    trace["inert"] = False
    appended = [f"[associated] {str(item['memory']).strip()}" for item in new_items[:max_new]]
    return base_texts + appended, trace


def _self_check() -> None:
    top10 = [{"id": "a", "memory": "seed fact"}, {"id": "b", "memory": "other fact"}]

    def search_hits(query: str, limit: int) -> list[dict[str, Any]]:
        assert query == "seed fact"
        return [{"id": "a", "memory": "seed fact"}, {"id": "c", "memory": "new associated fact"}]

    rendered, trace = second_hop_expansion(top10, search_hits)
    assert rendered == ["seed fact", "other fact", "[associated] new associated fact"]
    assert trace["hop2_new_items"] == 1 and trace["inert"] is False

    def search_nothing_new(query: str, limit: int) -> list[dict[str, Any]]:
        return [{"id": "a", "memory": "seed fact"}, {"id": "b", "memory": "other fact"}]

    rendered2, trace2 = second_hop_expansion(top10, search_nothing_new)
    assert rendered2 == ["seed fact", "other fact"]
    assert trace2["inert"] is True

    rendered3, trace3 = second_hop_expansion([], lambda q, l: [])
    assert rendered3 == [] and trace3["inert"] is True

    print("self-check OK: 3/3 cases correct (new item, no new item, empty compact)")


if __name__ == "__main__":
    _self_check()
