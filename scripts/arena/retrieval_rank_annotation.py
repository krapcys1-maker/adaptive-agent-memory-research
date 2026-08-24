#!/usr/bin/env python3
"""RETRIEVAL_RANK_ANNOTATION: read-side, deterministic render transform for
Mechanism F. Explicit response to the campaign lesson recorded in Ledger
Entries I and J: narrow, threshold-gated preconditions (RETRIEVAL_CONFIDENCE_
SIGNAL's margin<0.10 gate, SAME_CATEGORY_ENTITY_ENUMERATION's 2+-entity gate)
both produced regime-mismatch nulls on modest fresh samples -- the mechanism
had nothing to act on more often than not. RAW_PROVENANCE (the one validated
mechanism) has a UNIVERSAL precondition: Mem0 always compresses, so there is
always a top-1 session to append.

This mechanism has an equally universal precondition by construction: EVERY
retrieved item gets its rank and Mem0 relevance score rendered, always, no
threshold gate. Hypothesis: explicit per-item retrieval-confidence metadata
helps the reader appropriately weight evidence on every unit, not just
ambiguous ones -- unlike Mechanism D's conditional warning note (fired on
only some units and, when it did, changed no answers), this gives the reader
the SAME quantitative information unconditionally and lets it decide how to
use it, rather than a fixed rule pre-deciding which units need a nudge.
"""

from __future__ import annotations


def retrieval_rank_annotation(context_texts: list[str],
                              scores: list[float | None]) -> tuple[list[str], dict]:
    """Returns (rendered_context, trace). Always renders one prefix per item
    (rank + score if available, rank only otherwise) -- never inert by
    construction, since rank is defined for every non-empty retrieval."""
    n = len(context_texts)
    padded_scores = list(scores) + [None] * (n - len(scores))
    rendered = []
    for i, (text, score) in enumerate(zip(context_texts, padded_scores), start=1):
        if isinstance(score, (int, float)):
            rendered.append(f"[rank {i}/{n}, relevance {score:.2f}] {text}")
        else:
            rendered.append(f"[rank {i}/{n}] {text}")
    trace = {"n_items": n, "n_scored": sum(1 for s in padded_scores if isinstance(s, (int, float))),
             "always_fires": n > 0, "inert": n == 0}
    return rendered, trace


def _self_check() -> None:
    ctx = ["fact a", "fact b", "fact c"]
    rendered, trace = retrieval_rank_annotation(ctx, [0.85, 0.60, 0.30])
    assert rendered == ["[rank 1/3, relevance 0.85] fact a",
                        "[rank 2/3, relevance 0.60] fact b",
                        "[rank 3/3, relevance 0.30] fact c"]
    assert trace["always_fires"] is True

    rendered2, trace2 = retrieval_rank_annotation(ctx, [])
    assert rendered2 == ["[rank 1/3] fact a", "[rank 2/3] fact b", "[rank 3/3] fact c"]

    rendered3, trace3 = retrieval_rank_annotation([], [])
    assert rendered3 == [] and trace3["inert"] is True

    print("self-check OK: 3/3 cases correct (scored, unscored, empty)")


if __name__ == "__main__":
    _self_check()
