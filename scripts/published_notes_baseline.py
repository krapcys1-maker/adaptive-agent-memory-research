#!/usr/bin/env python3
"""Baseline profile of an agent's own published texts: how much it repeats itself, how often it refers back, and how much there is to remember.

Part B of docs/11-research-laboratory/live-memory-shadow-audit-spec-draft-v0.md, extended with a semantic measure after the first
real snapshot showed that lexical repetition sits at the floor. Reads one JSONL file (id, date, text, optional title), writes only
aggregates to standard output (and optionally a JSON file): no text, no id and no excerpt of the input is ever printed or stored.

The lexical part is standard library only. The semantic part (--embed) needs the optional `sentence-transformers` package and a
local copy of the model; it runs offline. Everything is deterministic for a given input and model.

Usage: python scripts/published_notes_baseline.py items.jsonl [--embed] [--model sentence-transformers/all-MiniLM-L6-v2]
                                                  [--tasks 200 400] [--json OUT.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from statistics import mean, median, pstdev
from typing import Dict, List, Optional, Sequence

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shadow_baseline_measures as sbm  # noqa: E402

PERCENTILES = (50, 75, 90, 95, 99)
Z = 2.8   # (z for 5% two-sided) + (z for 80% power), rounded as in the shadow-audit specification


def percentiles(values: Sequence[float]) -> Dict[str, float]:
    ordered = sorted(values)
    return {str(p): round(ordered[min(len(ordered) - 1, int(p / 100 * len(ordered)))], 4) for p in PERCENTILES}


def cadence(items: Sequence[sbm.Item]) -> dict:
    per_day: Dict = {}
    for item in items:
        per_day[item.day] = per_day.get(item.day, 0) + 1
    words = [len(item.text.split()) for item in items]
    return {"items": len(items), "days_with_items": len(per_day), "first": str(items[0].day), "last": str(items[-1].day),
            "items_per_day": {"mean": round(mean(per_day.values()), 2), "median": median(per_day.values()),
                              "min": min(per_day.values()), "max": max(per_day.values())},
            "words": {"mean": round(mean(words), 1), "median": median(words), "min": min(words), "max": max(words)},
            "exact_duplicate_texts": len(items) - len({item.text for item in items})}


def lexical_profile(items: Sequence[sbm.Item], grams: Sequence[int] = (3, 4, 5), windows: Sequence[int] = (7, 30, 9999),
                    thresholds: Sequence[float] = (0.1, 0.2, 0.3, 0.5)) -> Dict[str, dict]:
    """Share of an item's n-grams that one earlier item (on an earlier day, within the window) already contains."""
    out: Dict[str, dict] = {}
    for n in grams:
        for window in windows:
            overlap = [sbm.repetition_overlap(items, k, window, n) for k in range(len(items))]
            out["n=%d,window=%dd" % (n, window)] = {
                "mean": round(mean(overlap), 4), "percentiles": percentiles(overlap),
                "share_at_least": {str(t): round(sum(o >= t for o in overlap) / len(overlap), 4) for t in thresholds}}
    return out


def callback_profile(items: Sequence[sbm.Item]) -> dict:
    flagged = sum(1 for k in range(len(items)) if sbm.is_callback(items, k, 9999))
    return {"strict_definition": "callback phrase, or an earlier title quoted in full", "count": flagged, "rate": round(flagged / len(items), 4)}


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def continuous_icc(groups: Sequence[Sequence[float]]) -> float:
    """One-way ANOVA estimator of the intraclass correlation of a continuous measure over days, clamped to [0, 1]."""
    groups = [g for g in groups if g]
    total, k = sum(len(g) for g in groups), len(groups)
    if k < 2 or total <= k:
        raise ValueError("need at least two groups and more observations than groups")
    grand = sum(sum(g) for g in groups) / total
    msb = sum(len(g) * (mean(g) - grand) ** 2 for g in groups) / (k - 1)
    msw = sum(sum((x - mean(g)) ** 2 for x in g) for g in groups) / (total - k)
    n0 = (total - sum(len(g) ** 2 for g in groups) / total) / (k - 1)
    denominator = msb + (n0 - 1) * msw
    return 0.0 if denominator <= 0 else max(0.0, min(1.0, (msb - msw) / denominator))


def mde_mean_shift(sd: float, tasks: float, exposure: float) -> float:
    """Smallest detectable difference of means (5% two-sided, 80% power) with `exposure` of the tasks in the memory arm."""
    return Z * sd * (1 / (tasks * (1 - exposure)) + 1 / (tasks * exposure)) ** 0.5


def semantic_profile(items: Sequence[sbm.Item], vectors: Sequence[Sequence[float]], thresholds: Sequence[float] = (0.5, 0.6, 0.7, 0.8),
                     recent_days: int = 7, tasks: Sequence[int] = (200, 400), exposures: Sequence[float] = (0.25, 0.5)) -> dict:
    """Top-1 cosine of every item with an EARLIER item (same-day earlier items included: they are in memory by then).
    Vectors must be unit length. The first item has no history and is left out of every share and mean."""
    top, top_recent, partner_gap = [], [], []
    for k in range(1, len(items)):
        sims = [dot(vectors[k], vectors[j]) for j in range(k)]
        best = max(range(k), key=lambda j: sims[j])
        top.append(sims[best])
        partner_gap.append((items[k].day - items[best].day).days)
        recent = [s for j, s in enumerate(sims) if (items[k].day - items[j].day).days <= recent_days]
        top_recent.append(max(recent) if recent else 0.0)
    n = len(top)
    sd = pstdev(top)
    shares = {}
    for t in thresholds:
        related = [g for s, g in zip(top, partner_gap) if s >= t]
        shares[str(t)] = {"any_earlier": round(len(related) / n, 4),
                          "within_%d_days" % recent_days: round(sum(s >= t for s in top_recent) / n, 4),
                          "partner_within_%d_days_of_those" % recent_days: round(sum(g <= recent_days for g in related) / len(related), 4) if related else None,
                          "median_gap_days_of_those": median(related) if related else None}
    by_day: Dict = {}
    for item, s in zip(items[1:], top):
        by_day.setdefault(item.day, []).append(s)
    try:
        continuous = round(continuous_icc(list(by_day.values())), 4)
    except ValueError:
        continuous = None
    binary_icc = {}
    for t in thresholds[1:3]:
        daily = sbm.daily_counts(items[1:], lambda idx, t=t: top[idx] >= t)
        try:
            binary_icc[str(t)] = round(sbm.intraclass_correlation(daily), 4)
        except ValueError:
            binary_icc[str(t)] = None
    return {"items_with_history": n, "top1_cosine": {"mean": round(mean(top), 4), "sd": round(sd, 4), "percentiles": percentiles(top)},
            "top1_cosine_previous_%d_days" % recent_days: {"mean": round(mean(top_recent), 4), "sd": round(pstdev(top_recent), 4)},
            "shares_at_least": shares, "day_icc_binary": binary_icc,
            "day_icc_continuous": continuous,
            "mde_mean_shift_of_top1_cosine": {"%d_tasks_%d%%_in_memory_arm" % (t, round(e * 100)): round(mde_mean_shift(sd, t, e), 4)
                                              for t in tasks for e in exposures}}


def embed_texts(texts: Sequence[str], model: str = "sentence-transformers/all-MiniLM-L6-v2") -> List[List[float]]:
    """Unit-length sentence embeddings from a local copy of the model (offline). Needs the optional sentence-transformers package."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer(model, device="cpu")
    return [list(map(float, row)) for row in encoder.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)]


def profile(items: Sequence[sbm.Item], vectors: Optional[Sequence[Sequence[float]]] = None, tasks: Sequence[int] = (200, 400)) -> dict:
    out = {"cadence": cadence(items), "lexical": lexical_profile(items), "callbacks": callback_profile(items),
           "provisional_repetition_rule": sbm.summarise(items, 30, 5, 0.5, None)["repetition"]}
    out["provisional_repetition_rule"].pop("mde_by_exposure", None)
    if vectors is not None:
        out["semantic"] = semantic_profile(items, vectors, tasks=tasks)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate baseline profile of an agent's own published texts.")
    parser.add_argument("items", help="JSONL file: id, date, text, optional title")
    parser.add_argument("--embed", action="store_true", help="add the semantic profile (needs sentence-transformers, offline model)")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--tasks", type=int, nargs="+", default=[200, 400], help="sizes of planned comparisons for the detectable-shift table")
    parser.add_argument("--json", default=None, help="also write the aggregates to this file")
    args = parser.parse_args(argv)
    try:
        with open(args.items, encoding="utf-8") as handle:
            items = sbm.parse_items(handle)
        if len(items) < 3:
            raise ValueError("need at least three items")
        vectors = embed_texts([i.text for i in items], args.model) if args.embed else None
    except (OSError, UnicodeDecodeError, ValueError, ImportError) as exc:
        print("input error: " + str(exc), file=sys.stderr)
        return 2
    result = profile(items, vectors, args.tasks)
    text = json.dumps(result, indent=1, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
