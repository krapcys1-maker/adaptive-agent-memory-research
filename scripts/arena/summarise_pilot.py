#!/usr/bin/env python3
"""Read every pilot artefact and lay them beside each other, without ranking them.

At four units, with a substring proxy for correctness and a decoder that is
measurably not reproducible, "system A beat system B" is a sentence this data
cannot support. So this prints a table and refuses to sort it by score.

What four units *can* settle is the part that does not depend on n:

    a system that will not run at all
    a cost that differs by a factor, not by a few percent
    a query path that calls a model against one that does not
    a store that reports its own usage against one that cannot
    two systems that fail on different units

Those are screening outcomes, and they are what decides where the next money
goes. The score column is printed last and carries its caveat in the header.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARENA = ROOT / "data/lab/arena"

#: Printed with every table that shows the score column.
SCORE_CAVEAT = ("score = substring containment of the gold answer over 4 units, not "
                "LongMemEval's model judge. It under-counts every correct paraphrase. "
                "It is a signal check, and at n=4 a difference of one unit is noise")


def load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def blocked(path: Path) -> dict[str, Any] | None:
    return load(path)


def row(record: dict[str, Any]) -> dict[str, Any]:
    units = [u for u in record.get("units", []) if u.get("status") == "complete"]
    ingest = sum(u["ingest"].get("usd", 0.0) for u in units)
    query = sum((u.get("query") or {}).get("usd", 0.0) for u in units)
    calls = sum(u["ingest"].get("model_calls", 0) or 0 for u in units)
    query_calls = sum((u.get("query") or {}).get("model_calls", 0) or 0 for u in units)
    memories = [u.get("memory") or {} for u in units]
    tasks = [u.get("task") or {} for u in units]
    matched = [t.get("crude_substring_match") for t in tasks]

    def one(values: list[Any]) -> Any:
        """A single value if every unit agreed, else the set. Never an average."""
        distinct = {json.dumps(v, sort_keys=True, default=str) for v in values}
        return json.loads(distinct.pop()) if len(distinct) == 1 else sorted(distinct)

    return {
        "system": record.get("system", "?"),
        "status": record.get("status"),
        "units_complete": len(units),
        "score": f"{sum(1 for m in matched if m is True)}/{len(units)}" if units else "-",
        "ingest_usd": round(ingest, 4),
        "query_usd": round(query, 4),
        "total_usd": round(record.get("spend_usd", ingest + query), 4),
        "ingest_calls": calls,
        "query_calls": query_calls,
        "ingest_wall_s": round(sum(u["ingest"].get("wall_seconds", 0.0) for u in units)),
        "context_tokens": one([m.get("context_tokens") for m in memories]),
        "evidence_ids": one([m.get("evidence_ids") for m in memories]),
        "evidence_traceable": one([m.get("evidence_all_traceable") for m in memories]),
        "cost_observability": one([
            (u.get("query") or {}).get("observability", {}).get("model_calls") for u in units]),
        "mutation": one([m.get("query_mutates_state") for m in memories]),
        "reproducible": one([m.get("output_reproducible") for m in memories]),
        "abstained": one([m.get("abstained") for m in memories]),
        "abstention_derivable": one([m.get("abstention_derivable") for m in memories]),
        "stored_items": one([u.get("stored_items") for u in units]),
        "contract": record.get("contract_version"),
        "selection": (record.get("selection") or "")[:12],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ARENA / "pilot-summary.json"))
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for path in sorted(ARENA.glob("pilot-*.json")):
        if path.name in {"pilot-selection.json", "pilot-summary.json",
                         "pilot-cost-projection.json"} or "calibration" in path.name:
            continue
        record = load(path)
        if record is None:
            continue
        if record.get("artifact", "").endswith("-blocked"):
            blockers.append(record)
            continue
        if record.get("superseded_by"):
            # Kept on disk, kept out of the table. A superseded measurement is
            # evidence of what went wrong, not a second row for the same system.
            continue
        rows.append(row(record) | {"artifact": path.name})

    # Ordered by what a screen acts on — total cost — and explicitly not by score.
    rows.sort(key=lambda r: r["total_usd"])

    summary = {
        "artifact": "arena-pilot-summary",
        "selection": "arena-pilot-v1, four frozen LongMemEval-S units",
        "is_a_leaderboard": False,
        "why_not": ("n=4, one run per system, a substring proxy for correctness, and a "
                    "decoder measured at 3 to 4 distinct outputs in 20 identical "
                    "requests. This screens; it does not rank"),
        "score_caveat": SCORE_CAVEAT,
        "ordered_by": "total cost, ascending — deliberately not by score",
        "systems": rows,
        "blocked": blockers,
    }
    Path(args.out).write_text(json.dumps(summary, indent=2, default=str) + "\n",
                              encoding="utf-8")

    head = ["system", "score", "ingest_usd", "query_usd", "total_usd", "ingest_calls",
            "query_calls", "context_tokens", "evidence_ids", "mutation",
            "reproducible", "cost_observability"]
    widths = {h: max(len(h), *(len(str(r.get(h, ""))) for r in rows)) if rows else len(h)
              for h in head}
    print(" | ".join(h.ljust(widths[h]) for h in head))
    print("-+-".join("-" * widths[h] for h in head))
    for record in rows:
        print(" | ".join(str(record.get(h, "")).ljust(widths[h]) for h in head))
    print()
    print(SCORE_CAVEAT)
    for entry in blockers:
        print(f"BLOCKED {entry.get('system')}: {entry.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
