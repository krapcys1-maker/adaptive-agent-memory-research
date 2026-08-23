"""PMLAB-H1-COMPOSE-E1: does joining two measured mechanisms keep both gains?

    raw query → deterministic address → derived chain → temporal resolution → context

Both halves have been measured separately and neither result transfers
automatically to their composition.

``PMLAB-H1-ADDR-E2`` arm A3 assigns addresses with 1.000 gold coverage on dev-a
and valid-b, no model, 33 tokens of context. It fails the frozen stale gate at
0.286 because an addressing layer returns the whole chain and something else is
supposed to choose within it.

``PMLAB-H1-READ-E1`` measured that something else: demoting records below N1
takes the OBSOLETE leak from 0.833 to 0.000. **But it did so over oracle
chains.** The chain map was handed to it.

So the composition is the first configuration in which nothing is handed over.
The chain is derived from text by A3 and the rank is computed within that
derived chain, which means a wrong address now corrupts the resolver's input
rather than merely widening the context. Two mechanisms that each work can still
fail together, and that is what this measures.

Model-free. The reader arm costs money and is only worth buying once this says
the retrieval side composes.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.address_extract import extract, extract_query  # noqa: E402
from corpus.arms import _before, _fill  # noqa: E402
from run_corpus_h1_baseline import load  # noqa: E402

CORPUS = ROOT / "data" / "lab" / "corpus-h1"
SPLITS = {"dev-a": (CORPUS / "prefix-v0", CORPUS / "reveal-v0"),
          "valid-b": (CORPUS / "valid-b" / "prefix", CORPUS / "valid-b" / "reveal")}


def run(split: str, budget: int, resolve: bool) -> dict[str, Any]:
    prefix, reveal = SPLITS[split]
    events = load(prefix / "history.jsonl")
    by_id = {e["event_id"]: e for e in events}
    queries = load(reveal / "queries.jsonl")
    gold_of = {g["query_id"]: g for g in load(reveal / "gold.jsonl")}

    drawers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        address = extract(event["text"], canonicalise=True)
        if address:
            drawers[address.canonical].append(event)

    records = []
    for query in queries:
        gold = gold_of[query["query_id"]]
        day = query["asked_on_day"]
        address = extract_query(query["question"], canonicalise=True)

        if address is None:
            records.append({"query_id": query["query_id"],
                            "family": gold["case_id"].rsplit("-", 1)[0],
                            "abstained": 1, "gold": 0, "stale": 0, "tokens": 0, "candidates": 0})
            continue

        chain = _before(drawers.get(address.canonical, []), day)
        chain.sort(key=lambda e: (-e["day"], -e["position"]))

        # Rank within the DERIVED chain, not an oracle one. N1 is the newest
        # record the derived address collected; everything below it is demoted.
        if resolve and chain:
            newest = chain[0]["event_id"]
            chain = sorted(chain, key=lambda e: e["event_id"] != newest)

        kept = _fill(chain, budget)
        ids = [e["event_id"] for e in kept]
        stale = [i for i in ids if i != gold["gold_event_id"]
                 and i.split("#")[0] == gold["gold_event_id"].split("#")[0]]

        records.append({
            "query_id": query["query_id"], "family": gold["case_id"].rsplit("-", 1)[0],
            "abstained": 0,
            "gold": int(gold["gold_event_id"] in ids),
            "gold_first": int(bool(ids) and ids[0] == gold["gold_event_id"]),
            "stale": int(bool(stale)),
            "tokens": sum(len(by_id[i]["text"].split()) for i in ids),
            "candidates": len(ids),
        })

    return {"records": records, "summary": summarise(split, records, resolve)}


def summarise(split: str, records, resolve: bool) -> dict[str, Any]:
    n = len(records)
    families = sorted({r["family"] for r in records})

    def rate(field, rows=None):
        rows = records if rows is None else rows
        return round(sum(r.get(field, 0) for r in rows) / len(rows), 6) if rows else 0.0

    return {
        "experiment_id": "PMLAB-H1-COMPOSE-E1",
        "configuration": ("address + temporal resolution" if resolve else "address only"),
        "split": split, "model": None, "api_cost_usd": 0.0,
        "eligible_probes": n,
        "gold_coverage": rate("gold"),
        "gold_ranked_first": rate("gold_first"),
        "stale_context_rate": rate("stale"),
        "abstention_rate": rate("abstained"),
        "mean_context_tokens": round(sum(r["tokens"] for r in records) / n, 6),
        "mean_candidates": round(sum(r["candidates"] for r in records) / n, 6),
        "by_family": {
            f: {"gold": rate("gold", [r for r in records if r["family"] == f]),
                "gold_first": rate("gold_first", [r for r in records if r["family"] == f]),
                "stale": rate("stale", [r for r in records if r["family"] == f])}
            for f in families
        },
        "chains_are_derived_not_oracle": (
            "PMLAB-H1-READ-E1 measured rank demotion over oracle chains. Here the chain comes from "
            "A3's derived address, so a wrong address corrupts the resolver's input rather than only "
            "widening the context"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", default="dev-a", choices=sorted(SPLITS))
    parser.add_argument("--budget", type=int, default=250)
    parser.add_argument("--out", type=Path, default=None)
    arguments = parser.parse_args(argv)

    print("PMLAB-H1-COMPOSE-E1 — model-free, no API cost\n")
    print(f"  {'configuration':<28}{'gold':>8}{'first':>8}{'stale':>8}{'cand':>7}{'tokens':>8}")
    out = {}
    for resolve in (False, True):
        result = run(arguments.split, arguments.budget, resolve)
        s = result["summary"]
        out["resolved" if resolve else "address_only"] = result
        print(f"  {s['configuration']:<28}{s['gold_coverage']:>8.3f}{s['gold_ranked_first']:>8.3f}"
              f"{s['stale_context_rate']:>8.3f}{s['mean_candidates']:>7.1f}{s['mean_context_tokens']:>8.1f}")

    s = out["resolved"]["summary"]
    print(f"\n  with resolution, by family ({arguments.split})\n")
    print(f"  {'family':<12}{'gold':>8}{'first':>8}{'stale':>8}")
    for family, block in s["by_family"].items():
        print(f"  {family:<12}{block['gold']:>8.3f}{block['gold_first']:>8.3f}{block['stale']:>8.3f}")

    if arguments.out:
        destination = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "results.json").write_bytes(
            (json.dumps(out, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"\nwritten: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
