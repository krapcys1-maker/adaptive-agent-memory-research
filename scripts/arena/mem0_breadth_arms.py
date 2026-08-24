#!/usr/bin/env python3
"""Build Mem0's breadth arms from one clean run, and read them beside Hindsight's.

Mem0's advantage question is symmetric to the one already answered for Hindsight:
its context was cut down and accuracy fell 7 -> 6 -> 6 -> 4. Here Mem0's own
ranking is *extended* to the same budgets. If it climbs the same curve, breadth
generalises across systems; if it stays flat while Hindsight climbs, breadth is
not sufficient and the difference is in the kind of item each system stores.

Everything is built from `clean-mem0.json` and its persisted contexts. The native
arm is Mem0's own `limit=10` result; the wider arms are prefixes of a deeper slice
of the *same* ranking, so no arm reorders anything and none is chosen using gold.

Nothing here calls a provider. The reader and judge are invoked separately.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.retrieval_truth import canonical_time, gold_session_indices, session_map  # noqa: E402

ARENA = ROOT / "data/lab/arena"
CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")

#: Frozen in the manifest before the run.
BUDGETS = (500, 1000, 3000)


def truncate(items: list[str], budget: int) -> list[str]:
    """Whole items, original order, while the next still fits."""
    kept: list[str] = []
    used = 0
    for item in items:
        size = len(item.split())
        if used + size > budget:
            continue
        kept.append(item)
        used += size
    return kept


def gold_state(row: dict[str, Any], times: list[str]) -> dict[str, Any]:
    mapping = session_map(row)
    if mapping is None:
        return {"observable": False, "gold_in_context": "UNOBSERVABLE",
                "gold_rank": "UNOBSERVABLE", "precision_at_k": "UNOBSERVABLE"}
    gold = gold_session_indices(row)
    hits = [i for i, t in enumerate(times, start=1)
            if mapping.get(canonical_time(t)) in gold]
    return {"observable": True, "gold_in_context": bool(hits),
            "gold_rank": hits[0] if hits else None,
            "precision_at_k": round(len(hits) / len(times), 4) if times else None,
            "foreign_from_other_units": sum(
                1 for t in times if mapping.get(canonical_time(t)) is None)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default=str(ARENA / "clean-mem0.json"))
    parser.add_argument("--raw", default=str(ARENA / "raw/arena-expansion-v1/mem0.json"))
    parser.add_argument("--out", default=str(ARENA / "mem0-breadth-arms.json"))
    args = parser.parse_args()

    sel = json.loads((ARENA / "expansion-selection.json").read_text(encoding="utf-8"))
    units = {u["question_id"]: u for u in sel["units"]}
    with CORPUS.open(encoding="utf-8") as handle:
        corpus = {r["question_id"]: r for r in json.load(handle) if r["question_id"] in units}
    raw = {e["question_id"]: e for e in
           json.loads(Path(args.raw).read_text(encoding="utf-8"))}

    arms: list[dict[str, Any]] = []
    for qid, unit in units.items():
        entry, row = raw.get(qid) or {}, corpus[qid]
        native = entry.get("context_texts") or []
        native_times = entry.get("evidence_times") or []
        deep = entry.get("deep_context_texts") or []
        deep_times = entry.get("deep_evidence_times") or []

        if deep and deep[:len(native)] != native:
            # The whole curve rests on the deep slice extending the native one.
            raise SystemExit(
                f"{qid}: the deep slice is not a prefix of the native slice, so a "
                "wider budget would be measuring a different ranking")

        arms.append({"arm": "mem0_original", "question_id": qid, "slot": unit["slot"],
                     "question_type": unit["question_type"],
                     "question": row["question"], "gold": str(row.get("answer", "")),
                     "context": native, "budget": "native limit 10",
                     "context_tokens": sum(len(t.split()) for t in native),
                     **gold_state(row, native_times)})
        for budget in BUDGETS:
            keep = truncate(deep, budget)
            times = deep_times[:len(keep)]
            arms.append({"arm": f"mem0_{budget}", "question_id": qid,
                         "slot": unit["slot"], "question_type": unit["question_type"],
                         "question": row["question"], "gold": str(row.get("answer", "")),
                         "context": keep, "budget": budget,
                         "context_tokens": sum(len(t.split()) for t in keep),
                         **gold_state(row, times)})

    Path(args.out).write_text(json.dumps(
        {"artifact": "arena-mem0-breadth-arms",
         "source_run": Path(args.run).name,
         "budgets": ["native limit 10", *BUDGETS],
         "truncation": "whole items, original ranked order, no gold-aware selection",
         "prefix_property_verified": True,
         "arms": arms}, indent=2, default=str) + "\n", encoding="utf-8")

    for name in ("mem0_original", *(f"mem0_{b}" for b in BUDGETS)):
        rows = [a for a in arms if a["arm"] == name]
        toks = [a["context_tokens"] for a in rows]
        kept = [a["gold_in_context"] for a in rows if isinstance(a["gold_in_context"], bool)]
        print(f"  {name:16s} mean tok {round(sum(toks)/len(toks),1):>7}  "
              f"items {round(sum(len(a['context']) for a in rows)/len(rows),1):>5}  "
              f"gold {sum(kept)}/{len(kept)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
