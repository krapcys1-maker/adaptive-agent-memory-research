#!/usr/bin/env python3
"""RETRIEVAL_CONFIDENCE_SIGNAL: the read-side, deterministic render transform
for Mechanism D. Uses Mem0's own retrieval scores (already returned by
`Memory.search()`, zero additional cost) to detect when the top-1 and top-2
retrieved items are near-tied in relevance, and appends one fixed,
content-free note when they are.

Target failure: reader over-trusts the single most-prominent retrieved item
when retrieval itself was ambiguous (top candidates near-tied), rather than
checking whether a less-prominent item answers the specific question better.
Distinct axis from RAW_PROVENANCE (content absence) and CURRENT_STATE_OVER_
HISTORY (temporal-validity/state) -- this is about retrieval CONFIDENCE, not
content completeness or temporal ordering.

Threshold fixed at 0.10 (absolute score-margin, Mem0's own cosine-similarity-
based score in its native 0-1-ish range), chosen from the natural spread
observed in already-collected retrieval scores (range ~0.025-0.34 across the
8 RAW_PROVENANCE fresh-replication units, a already-paid-for, zero-marginal-
cost score inspection) as a round, non-degenerate cutpoint BEFORE this
mechanism's own probe set was selected or run -- not fit to this experiment's
own results.
"""

from __future__ import annotations

MARGIN_THRESHOLD = 0.10

CONFIDENCE_NOTE = (
    "Note: the top-ranked memories above have similar relevance scores. "
    "Before answering, check whether a less prominent item above answers "
    "the specific question more directly, rather than defaulting to the "
    "most prominent one."
)


def retrieval_confidence_signal(context_texts: list[str],
                                scores: list[float | None]) -> tuple[list[str], dict]:
    """Returns (rendered_context, trace). Inert (byte-identical to input) when
    fewer than 2 scored items exist, or when the top1-top2 margin is at or
    above MARGIN_THRESHOLD -- no note is ever added except in the single,
    fixed low-margin condition."""
    trace = {"n_items": len(context_texts), "top1_score": None, "top2_score": None,
             "margin": None, "flagged": False}
    usable_scores = [s for s in scores[:2] if isinstance(s, (int, float))]
    if len(context_texts) < 2 or len(usable_scores) < 2:
        trace["inert"] = True
        return list(context_texts), trace

    top1, top2 = usable_scores[0], usable_scores[1]
    margin = round(top1 - top2, 6)
    trace.update({"top1_score": top1, "top2_score": top2, "margin": margin})

    if margin >= MARGIN_THRESHOLD:
        trace["inert"] = True
        return list(context_texts), trace

    trace["flagged"] = True
    trace["inert"] = False
    return list(context_texts) + [CONFIDENCE_NOTE], trace


def _self_check() -> None:
    ctx = ["fact a", "fact b", "fact c"]
    rendered, trace = retrieval_confidence_signal(ctx, [0.80, 0.78, 0.30])
    assert rendered == ctx + [CONFIDENCE_NOTE] and trace["flagged"]
    rendered2, trace2 = retrieval_confidence_signal(ctx, [0.90, 0.50, 0.30])
    assert rendered2 == ctx and trace2["inert"] and not trace2["flagged"]
    rendered3, trace3 = retrieval_confidence_signal(["only one"], [0.90])
    assert rendered3 == ["only one"] and trace3["inert"]
    rendered4, trace4 = retrieval_confidence_signal(ctx, [None, None, None])
    assert rendered4 == ctx and trace4["inert"]
    print("self-check OK: 4/4 cases correct (flag, no-flag, single-item, missing-scores)")


if __name__ == "__main__":
    _self_check()
