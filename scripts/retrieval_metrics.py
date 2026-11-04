"""Shared recall per 1,000 retrieved whitespace tokens (issue 38).

Count only item text at the scored depth, never all backend candidates. This is
a content-word cost estimate, excluding query/prompt wrappers and metadata; it
is not a model tokenizer count or the kernel's characters/4 estimate. Recall is
gold-event ID recall, not independently measured downstream answer usefulness.
Aggregate as the ratio of means, never the mean of per-query ratios. Zero total
tokens and an empty sample are undefined (None), including zero-hit samples.
"""
from __future__ import annotations

import math

TOKEN_DEFINITION = "whitespace tokens of item text shown at the scored depth; excludes other candidates, metadata and query/prompt wrappers"
AGGREGATION = "ratio of means: 1000 * sum(per-query recall) / sum(per-query retrieved tokens)"
NUMERATOR = "gold-event ID recall; no separate usefulness or critical-evidence weighting unless the runner declares it"


def token_count(text: str) -> int:
    if not isinstance(text, str):
        raise TypeError("retrieved text must be a string")
    return len(text.split())


def definition(text_fields="event text") -> dict:
    return {"token_definition": TOKEN_DEFINITION, "text_fields": text_fields,
            "recall_definition": NUMERATOR, "aggregation": AGGREGATION,
            "zero_tokens": "undefined (null), not infinity"}


def efficiency(recalls, retrieved_tokens) -> dict:
    recall, tokens = list(recalls), list(retrieved_tokens)
    if len(recall) != len(tokens):
        raise ValueError("recall and cost must cover the same queries")
    if any(not isinstance(x, (int, float)) or not math.isfinite(x) or not 0 <= x <= 1 for x in recall):
        raise ValueError("recall must be finite and between zero and one")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in tokens):
        raise ValueError("token costs must be finite and non-negative")
    n = len(recall)
    hits, spent = math.fsum(recall), math.fsum(tokens)
    return {"queries": n, "recall": round(hits / n, 6) if n else None,
            "mean_retrieved_tokens": round(spent / n, 6) if n else None,
            "recall_per_1k_tokens": round(1000.0 * hits / spent, 6) if spent else None}


def event_text(event) -> str:
    """Complete text fields of a project-memory record, not its embedding input."""
    values = [event.get(name, "") for name in ("title", "summary", "body")]
    if any(not isinstance(value, str) for value in values):
        raise TypeError("memory text fields must be strings")
    return "\n".join(value for value in values if value)


def snapshot_costs(rankings, events) -> dict:
    """rankings = {arm: {depth: IDs actually shown}}; missing text is an error."""
    out = {}
    for arm, depths in rankings.items():
        for depth, ids in depths.items():
            ids = list(ids)
            if len(ids) > depth:
                raise ValueError("ranking exceeds its declared depth")
            out[f"{arm}_retrieved_ids@{depth}"] = ids
            out[f"{arm}_retrieved_tokens@{depth}"] = sum(token_count(event_text(events[i])) for i in ids)
    return out


def arm_summary(records, arm, depth) -> dict:
    values = efficiency([r[f"{arm}_hit@{depth}"] for r in records],
                        [r[f"{arm}_retrieved_tokens@{depth}"] for r in records])
    return {f"{arm}_mean_retrieved_tokens@{depth}": values["mean_retrieved_tokens"],
            f"{arm}_recall_per_1k_tokens@{depth}": values["recall_per_1k_tokens"]}
