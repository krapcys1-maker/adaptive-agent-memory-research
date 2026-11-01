#!/usr/bin/env python3
"""arena-base-plus-x-v2 (E1): read-side temporal-anchor / source-tag micro-grid.

Builds +TIME, +SRC and +BOTH treatment arms from the already-frozen, already-
paid-for clean Mem0 breadth arms (mem0_original = native, mem0_3000 = wide).
No ingest, no retrieval, no provider call in this file: every item, its
order, and its positionally-aligned session timestamp already exist on disk.

TEMPORAL_ANCHOR_AT_CONTEXT (+TIME)
-----------------------------------
Each item becomes "[YYYY-MM-DD] {fact}". The date is read ONLY from the
item's own positionally-corresponding `evidence_times` entry (verified this
session: native times align 1:1 with `context_texts`; wide times are the
matching prefix of `deep_evidence_times`, itself a verified prefix of the
deep ranking). Converted through the same `canonical_time()` already used
project-wide for date normalisation -- not a new parser, not an LLM, not
inferred, not gold. This is a SESSION TIMESTAMP ANCHOR (when the memory was
formed), not a resolved event date.

SOURCE_TAG_AT_CONTEXT (+SRC)
------------------------------
Each item becomes "(source: user's message) {fact}". Uniform across every
item in this store: `arena/run_arena_pilot.py::as_records` only ever ingests
user-role turns, so every stored Mem0 fact in this selection genuinely
originates from a user message -- this tag states SOURCE (where the fact was
extracted from), never SUBJECT (who or what the fact is about), and needs no
per-item inference.

+BOTH combines both prefixes: "[YYYY-MM-DD] (source: user's message) {fact}".

Nothing about item order, selection, ranking, or item content (the fact
string itself) is touched. Item order == BASE arm order == frozen ranking.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.retrieval_truth import canonical_time  # noqa: E402

ARENA = ROOT / "data/lab/arena"
OPERATING_POINTS = {"native": "mem0_original", "wide": "mem0_3000"}


def session_date(raw_timestamp: str) -> str:
    """'2023/05/25 (Thu) 06:04' -> '2023-05-25'. Deterministic, no inference."""
    iso = canonical_time(raw_timestamp)
    if iso is None:
        raise SystemExit(f"could not parse a session timestamp deterministically: {raw_timestamp!r}")
    return iso[:10]


def build() -> dict[str, Any]:
    raw_mem0 = {e["question_id"]: e for e in
               json.loads((ARENA / "raw/arena-expansion-v1/mem0.json").read_text(encoding="utf-8"))}
    base_arms = {(a["arm"], a["question_id"]): a for a in
                json.loads((ARENA / "mem0-breadth-arms.json").read_text(encoding="utf-8"))["arms"]}

    arms: list[dict[str, Any]] = []
    for point, base_arm_name in OPERATING_POINTS.items():
        for (arm_name, qid), base in base_arms.items():
            if arm_name != base_arm_name:
                continue
            entry = raw_mem0.get(qid) or {}
            context = base["context"]
            if point == "native":
                times = entry.get("evidence_times") or []
            else:
                times = (entry.get("deep_evidence_times") or [])[:len(context)]
            if len(times) != len(context):
                raise SystemExit(
                    f"evidence_times alignment ambiguous for {qid}/{point}: "
                    f"{len(context)} context items vs {len(times)} times -- STOP")
            dates = [session_date(t) for t in times]

            time_ctx = [f"[{d}] {fact}" for d, fact in zip(dates, context)]
            src_ctx = [f"(source: user's message) {fact}" for fact in context]
            both_ctx = [f"[{d}] (source: user's message) {fact}" for d, fact in zip(dates, context)]
            placebo_ctx = [f"[item-{i + 1:03d}] {fact}" for i, fact in enumerate(context)]

            common = {"question_id": qid, "slot": base["slot"], "question_type": base["question_type"],
                     "question": base["question"], "gold": base["gold"], "operating_point": point,
                     "base_arm": base_arm_name}
            for suffix, ctx in (("time", time_ctx), ("src", src_ctx), ("both", both_ctx),
                               ("placebo", placebo_ctx)):
                arms.append({**common, "arm": f"mem0_{point}_{suffix}", "context": ctx,
                            "context_tokens": sum(len(t.split()) for t in ctx),
                            "base_context_tokens": base["context_tokens"]})

    return {"artifact": "arena-base-plus-x-v2-e1-arms",
            "mechanism_names": {"time": "TEMPORAL_ANCHOR_AT_CONTEXT", "src": "SOURCE_TAG_AT_CONTEXT",
                               "both": "TEMPORAL_ANCHOR_AT_CONTEXT+SOURCE_TAG_AT_CONTEXT",
                               "placebo": "TOKEN_OVERHEAD_PLACEBO"},
            "date_source": "evidence_times, positionally aligned, canonical_time()-normalised to YYYY-MM-DD; session timestamp, not resolved event date",
            "source_tag": "(source: user's message) -- uniform, every item in this store originates from a user-role turn (as_records filters role=='user')",
            "no_provider_call_in_this_file": True,
            "arms": arms}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ARENA / "base-plus-x-v2/e1-arms.json"))
    parser.add_argument("--only", default=None,
                        help="comma-separated arm-name suffixes to include, e.g. time,src (default: all)")
    args = parser.parse_args()

    record = build()
    if args.only:
        keep = set(args.only.split(","))
        record["arms"] = [a for a in record["arms"] if a["arm"].rsplit("_", 1)[-1] in keep]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from collections import Counter
    print(Counter(a["arm"] for a in record["arms"]))
    print(f"wrote {len(record['arms'])} arm entries to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
