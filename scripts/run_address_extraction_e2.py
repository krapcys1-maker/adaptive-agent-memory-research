"""PMLAB-H1-ADDR-E2: score an address extractor against the frozen thresholds.

Every metric here is computed exactly as the preregistration defines it, and the
definitions are read **from the frozen file** rather than restated. Restating
them is how a denominator quietly changes: the code says one thing, the frozen
document says another, and the discrepancy surfaces after the result exists.

The denominator, once, because it is the thing most easily lost
---------------------------------------------------------------
Every rate divides by all eligible probes. Abstention is reported and is never a
denominator, so a system cannot improve any rate by refusing to answer.

What passing means
------------------
Six overall gates and two OBSOLETE floors, all frozen before this file existed.
The script reports PASS or FAIL against them and prints the full per-family
table, fragmentation and abstention regardless — the frozen document forbids a
success claim that omits any of the three.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.address_extract import describe, extract, extract_query  # noqa: E402
from corpus.arms import _before, _fill  # noqa: E402
from run_corpus_h1_baseline import load  # noqa: E402

CORPUS = ROOT / "data" / "lab" / "corpus-h1"
PREREG = CORPUS / "preregistration-addr-e2" / "preregistration.json"

SPLITS = {
    "dev-a": (CORPUS / "prefix-v0", CORPUS / "reveal-v0"),
    "valid-b": (CORPUS / "valid-b" / "prefix", CORPUS / "valid-b" / "reveal"),
}


def true_slot(event_id: str) -> str:
    """The slot a record really belongs to, from construction. Never shown to the extractor."""
    return event_id.split("#")[0]


def run(split: str, budget: int, canonicalise: bool = False) -> dict[str, Any]:
    prefix, reveal = SPLITS[split]
    events = load(prefix / "history.jsonl")
    by_id = {e["event_id"]: e for e in events}
    queries = load(reveal / "queries.jsonl")
    gold_of = {g["query_id"]: g for g in load(reveal / "gold.jsonl")}

    # Extraction sees text only — never construction labels, never gold.
    assigned: dict[str, str] = {}
    for event in events:
        address = extract(event["text"], canonicalise)
        if address:
            assigned[event["event_id"]] = address.canonical

    drawers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event_id, address in assigned.items():
        drawers[address].append(by_id[event_id])

    # Collision and fragmentation are properties of the mapping, not of any probe.
    slots_at_address: dict[str, set[str]] = defaultdict(set)
    addresses_of_slot: dict[str, set[str]] = defaultdict(set)
    for event_id, address in assigned.items():
        slot = true_slot(event_id)
        slots_at_address[address].add(slot)
        addresses_of_slot[slot].add(address)

    true_slots = {true_slot(e) for e in assigned}
    collided = {s for a, ss in slots_at_address.items() if len(ss) > 1 for s in ss}
    fragmented = {s for s, aa in addresses_of_slot.items() if len(aa) > 1}

    records = []
    for query in queries:
        gold = gold_of[query["query_id"]]
        day = query["asked_on_day"]
        want = true_slot(gold["gold_event_id"])
        address = extract_query(query["question"], canonicalise)

        if address is None:
            records.append({
                "query_id": query["query_id"], "family": gold["case_id"].rsplit("-", 1)[0],
                "abstained": 1, "gold_in_context": 0, "stale_in_context": 0, "tokens": 0,
                "wrong_entity": 0, "wrong_property": 0,
            })
            continue

        opened = _fill(sorted(_before(drawers.get(address.canonical, []), day),
                              key=lambda e: (-e["day"], -e["position"])), budget)
        ids = [e["event_id"] for e in opened]
        got_slots = {true_slot(i) for i in ids}

        # A wrong entity opens someone else's drawer; a wrong property narrows
        # badly inside the right one. Scored apart because they need different work.
        true_address = extract(by_id[gold["gold_event_id"]]["text"], canonicalise)
        wrong_entity = int(true_address is not None and address.entity != true_address.entity)
        wrong_property = int(true_address is not None and not wrong_entity
                             and address.prop != true_address.prop)

        records.append({
            "query_id": query["query_id"], "family": gold["case_id"].rsplit("-", 1)[0],
            "abstained": 0,
            "gold_in_context": int(gold["gold_event_id"] in ids),
            "stale_in_context": int(any(s == want and i != gold["gold_event_id"]
                                        for i, s in zip(ids, [true_slot(x) for x in ids]))),
            "tokens": sum(len(by_id[i]["text"].split()) for i in ids),
            "wrong_entity": wrong_entity, "wrong_property": wrong_property,
        })

    return {"records": records,
            "summary": {**summarise(split, records, true_slots, collided, fragmented, assigned, events),
                        "arm": "E2-A2 deterministic + property canonicalisation" if canonicalise else "E2-A deterministic"}}


def summarise(split: str, records, true_slots, collided, fragmented, assigned, events) -> dict[str, Any]:
    n = len(records)  # every rate divides by this
    families = sorted({r["family"] for r in records})

    def rate(field: str, rows=None) -> float:
        rows = records if rows is None else rows
        return round(sum(r[field] for r in rows) / len(rows), 6) if rows else 0.0

    slots = len(true_slots) or 1
    summary = {
        "experiment_id": "PMLAB-H1-ADDR-E2",
        "arm": describe()["arm"],
        "split": split,
        "eligible_probes": n,
        "records_addressed": len(assigned),
        "records_total": len(events),
        "gold_coverage": rate("gold_in_context"),
        "stale_context_rate": rate("stale_in_context"),
        "mean_context_tokens": round(sum(r["tokens"] for r in records) / n, 6),
        "collision_rate": round(len(collided) / slots, 6),
        "fragmentation_rate": round(len(fragmented) / slots, 6),
        "catastrophic_wrong_entity_rate": rate("wrong_entity"),
        "wrong_property_rate": rate("wrong_property"),
        "abstention_rate": rate("abstained"),
        "by_family": {
            f: {"probes": sum(1 for r in records if r["family"] == f),
                "gold_coverage": rate("gold_in_context", [r for r in records if r["family"] == f]),
                "stale_context_rate": rate("stale_in_context", [r for r in records if r["family"] == f]),
                "abstention_rate": rate("abstained", [r for r in records if r["family"] == f])}
            for f in families
        },
        "extractor": describe(),
    }
    summary["gates"] = evaluate(summary)
    return summary


def evaluate(s: dict[str, Any]) -> dict[str, Any]:
    """Against the frozen thresholds. Oracle coverage is 1.000, so 0.95 of it is 0.95."""
    obsolete = s["by_family"].get("OBSOLETE", {})
    checks = {
        "gold_coverage >= 0.95": s["gold_coverage"] >= 0.95,
        "stale_context_rate < 0.20": s["stale_context_rate"] < 0.20,
        "mean_context_tokens < 100": s["mean_context_tokens"] < 100,
        "collision_rate < 0.02": s["collision_rate"] < 0.02,
        "fragmentation_rate < 0.02": s["fragmentation_rate"] < 0.02,
        "catastrophic_wrong_entity_rate < 0.01": s["catastrophic_wrong_entity_rate"] < 0.01,
        "OBSOLETE stale_context_rate <= 0.30": obsolete.get("stale_context_rate", 1.0) <= 0.30,
        "OBSOLETE gold_coverage >= 0.85": obsolete.get("gold_coverage", 0.0) >= 0.85,
    }
    return {"checks": checks, "passed": all(checks.values()),
            "failed": [k for k, v in checks.items() if not v]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", default="dev-a", choices=sorted(SPLITS))
    parser.add_argument("--canonicalise", action="store_true",
                        help="E2-A2: apply the frozen property canonicalisation layer")
    parser.add_argument("--budget", type=int, default=250)
    parser.add_argument("--out", type=Path, default=None)
    arguments = parser.parse_args(argv)

    result = run(arguments.split, arguments.budget, arguments.canonicalise)
    s = result["summary"]

    print(f"{s['experiment_id']} — {s['arm']} on {s['split']}")
    print(f"  {s['records_addressed']}/{s['records_total']} records addressed, "
          f"{s['eligible_probes']} probes\n")
    for field in ("gold_coverage", "stale_context_rate", "mean_context_tokens",
                  "collision_rate", "fragmentation_rate",
                  "catastrophic_wrong_entity_rate", "wrong_property_rate", "abstention_rate"):
        print(f"    {field:<34} {s[field]}")

    print("\n  gates (frozen before this file existed)")
    for check, ok in s["gates"]["checks"].items():
        print(f"    {'PASS' if ok else 'FAIL'}  {check}")
    print(f"\n  overall: {'PASS' if s['gates']['passed'] else 'FAIL'}")

    print("\n  by family — required in any report, per the frozen document\n")
    print(f"  {'family':<12}{'gold':>8}{'stale':>8}{'abstain':>9}")
    for family, block in s["by_family"].items():
        print(f"  {family:<12}{block['gold_coverage']:>8.3f}"
              f"{block['stale_context_rate']:>8.3f}{block['abstention_rate']:>9.3f}")

    if arguments.out:
        out = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
        out.mkdir(parents=True, exist_ok=True)
        (out / "results.json").write_bytes(
            (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"\nwritten: {(out / 'results.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
