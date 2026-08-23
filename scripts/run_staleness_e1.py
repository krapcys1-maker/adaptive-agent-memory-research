"""PMLAB-STALE-E1: can content alone separate a superseded fact from its replacement?

Tier E exploratory experiment. Local model, no network at query time, no API cost.

Why this question rather than the obvious one
---------------------------------------------
The obvious test — "does dense retrieval surface stale facts?" — is malformed
against this store, because ``search()`` already excludes superseded records by
metadata: 0 of 9 superseded memories appear in results. Measuring that would
measure the filter, not the risk.

The question that matters is what the filter is *doing for us*, and whether
anything else could:

1. **Separability.** How similar is a superseded memory to the memory that
   replaced it, compared with an ordinary pair? If they sit close to the top of
   the similarity range, no embedding can tell them apart, because they are two
   statements of the same claim at different times.

2. **Consequence.** With the metadata filter removed, how often does the stale
   version outrank its own replacement?

Why this is a claim about the field, not about us
--------------------------------------------------
If content cannot separate them, then supersession must be carried in the
schema, and any memory system lacking it retrieves stale facts as a matter of
course rather than by accident. This project's audit of one such system recorded
that its "schema lacks evidence provenance, valid time, supersession, and
trust". Under this experiment that stops being a missing feature and becomes a
correctness defect.

It also bounds `PMLAB-XLANG-E2`, which measured dense recall at 0.978 and
explicitly deferred the safety question.

Limits stated up front
----------------------
Nine supersession pairs. This produces a qualitative result and an effect
direction, not a confidence interval. It is enough to distinguish "content can
separate them" from "content cannot", which is the decision at hand.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_association_graph_e2 import load_events  # noqa: E402
from run_cross_language_e2 import CACHE, MODEL, embed_text  # noqa: E402


def run(root: Path) -> dict[str, Any]:
    import numpy as np
    from fastembed import TextEmbedding

    events = [
        json.loads(line)
        for line in (root / "memory" / "events.jsonl").read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    by_id = {event["id"]: event for event in events}
    pairs = [
        (event["supersedes"], event["id"])
        for event in events
        if event.get("supersedes") and event["supersedes"] in by_id
    ]

    active, _ = load_events(root)
    # Everything, including superseded records: this experiment deliberately
    # removes the metadata filter to see what content alone would do.
    universe = sorted(by_id)
    model = TextEmbedding(model_name=MODEL, cache_dir=str(CACHE), threads=4)
    matrix = np.asarray(list(model.embed([embed_text(by_id[i]) for i in universe])), dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    position = {identifier: index for index, identifier in enumerate(universe)}

    similarity = matrix @ matrix.T

    # Baseline: every off-diagonal pair in the corpus.
    size = len(universe)
    off_diagonal = [
        float(similarity[i, j]) for i in range(size) for j in range(i + 1, size)
    ]
    baseline_mean = statistics.fmean(off_diagonal)
    baseline_p95 = sorted(off_diagonal)[int(0.95 * len(off_diagonal))]
    baseline_p99 = sorted(off_diagonal)[int(0.99 * len(off_diagonal))]

    records: list[dict[str, Any]] = []
    for old_id, new_id in pairs:
        old_index, new_index = position[old_id], position[new_id]
        pair_similarity = float(similarity[old_index, new_index])

        # Query with the current memory's own text, filter removed.
        query = np.asarray(next(model.query_embed(embed_text(by_id[new_id]))), dtype=np.float32)
        query /= np.linalg.norm(query)
        ranked = [universe[i] for i in np.argsort(-(matrix @ query))]
        ranked_without_self = [i for i in ranked if i != new_id]

        percentile = sum(1 for value in off_diagonal if value < pair_similarity) / len(off_diagonal)
        records.append(
            {
                "superseded": old_id,
                "current": new_id,
                "superseded_title": by_id[old_id].get("title", ""),
                "current_title": by_id[new_id].get("title", ""),
                "cosine": round(pair_similarity, 6),
                "corpus_percentile": round(percentile, 6),
                "stale_rank_unfiltered": ranked_without_self.index(old_id) + 1,
                "stale_is_nearest_neighbour": int(ranked_without_self[0] == old_id),
                "stale_in_top5": int(old_id in ranked_without_self[:5]),
            }
        )

    cosines = [r["cosine"] for r in records]
    return {
        "summary": {
            "experiment_id": "PMLAB-STALE-E1",
            "tier": "E-exploratory",
            "authority": "development measurement only; n=9 supersession pairs, qualitative",
            "model": MODEL,
            "corpus_events": len(universe),
            "active_events": len(active),
            "supersession_pairs": len(records),
            "pair_cosine_mean": round(statistics.fmean(cosines), 6),
            "pair_cosine_min": round(min(cosines), 6),
            "pair_cosine_max": round(max(cosines), 6),
            "corpus_baseline_mean": round(baseline_mean, 6),
            "corpus_baseline_p95": round(baseline_p95, 6),
            "corpus_baseline_p99": round(baseline_p99, 6),
            "pairs_above_corpus_p99": sum(1 for r in records if r["cosine"] > baseline_p99),
            "mean_corpus_percentile": round(statistics.fmean(r["corpus_percentile"] for r in records), 6),
            "stale_is_nearest_neighbour": sum(r["stale_is_nearest_neighbour"] for r in records),
            "stale_in_top5_unfiltered": sum(r["stale_in_top5"] for r in records),
            "median_stale_rank_unfiltered": statistics.median(
                r["stale_rank_unfiltered"] for r in records
            ),
            "filter_is_load_bearing": (
                "search() excludes superseded records by metadata; this run removes that filter "
                "to measure what content alone would do"
            ),
        },
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)

    payload = run(ROOT)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True, ensure_ascii=False))
    print("\nper pair:")
    for record in payload["records"]:
        print(
            f"  cos={record['cosine']:.4f}  pct={record['corpus_percentile']:.4f}  "
            f"stale_rank={record['stale_rank_unfiltered']:<3} {record['current_title'][:52]}"
        )

    if arguments.output:
        destination = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        )
        print(f"\nwritten: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
