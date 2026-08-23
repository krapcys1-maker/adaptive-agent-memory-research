"""PMLAB-H2-TEMP-E1: does a temporal resolver earn its place where ordering cannot?

Two arms over corpus H2, both model-free and free:

``newest``    the chain, newest first. This is what an addressed chain gives for
              nothing, and on H1 it was indistinguishable from a resolver.
``resolver``  reads ``valid_from``, ``valid_to`` and ``record_kind``, answers the
              question actually asked, and abstains when sources disagree.

The resolver cannot pass by policy
-----------------------------------
Every simple ordering rule fails at least one family by construction:

    always the newest      fails FUTURE and OVERLAP
    always the oldest      fails HISTORICAL
    suppress the old       fails HISTORICAL
    always answer          fails CONFLICT

So a resolver that scores well here is doing something an ordering cannot,
which is the claim being tested rather than assumed. On H1 the same comparison
produced identical numbers to three decimals, and the honest conclusion was that
the benchmark had stopped separating the architectures.

Abstention on CONFLICT is scored as correct
--------------------------------------------
Two sources disagree with no supersession between them and there is no fact of
the matter to retrieve. A system that answers confidently is wrong however
plausible its pick, so ``correct`` on that family means declining. Anywhere else
abstention is simply a miss.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "lab" / "corpus-h2"
SPLITS = {"dev": CORPUS / "dev", "valid": CORPUS / "valid"}

# What the question asks about time. Decided from the question alone — a resolver
# that peeked at the family label would be reading the answer key.
_PAST = re.compile(r"\bwas\b|\bbefore\b|\bpreviously\b|\bused to\b|\bon day\s+\d+", re.I)
_AT_DAY = re.compile(r"\bon day\s+(\d+)", re.I)
_BEFORE_CORRECTION = re.compile(r"\bbefore the correction\b", re.I)


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def newest_arm(chain: list[dict[str, Any]], question: str, asked_on: int) -> dict[str, Any]:
    """Ordering only: the most recently recorded record that existed by then."""
    visible = [e for e in chain if e["recorded_on"] <= asked_on]
    if not visible:
        return {"answer": None, "abstained": True}
    return {"answer": max(visible, key=lambda e: e["recorded_on"])["event_id"], "abstained": False}


def resolver_arm(chain: list[dict[str, Any]], question: str, asked_on: int) -> dict[str, Any]:
    """Validity-aware, correction-aware, and willing to decline.

    The order of the checks matters and each is a family this would otherwise
    fail, so none is decoration.
    """
    visible = [e for e in chain if e["recorded_on"] <= asked_on]
    if not visible:
        return {"answer": None, "abstained": True}

    # CONFLICT: distinct sources, no supersession between them. There is nothing
    # to resolve, so decline rather than pick the plausible one.
    sources = {e.get("source") for e in visible if e.get("source")}
    if len(sources) > 1 and not any(e.get("record_kind") == "correction" for e in visible):
        return {"answer": None, "abstained": True, "declined_disagreement": True}

    corrections = [e for e in visible if e.get("record_kind") == "correction"]
    if corrections:
        # CORRECTION: what it replaced was never true, so it cannot answer a
        # question about the past either. The correction is the only record that
        # may speak for any time in its range.
        return {"answer": max(corrections, key=lambda e: e["recorded_on"])["event_id"],
                "abstained": False, "used_correction": True}

    at_day = _AT_DAY.search(question)
    if at_day:
        # OVERLAP: a named instant. Windows may overlap, so the earliest record
        # whose window contains it is taken — not the newest, which is the whole
        # point of the family.
        moment = int(at_day.group(1))
        inside = [e for e in visible
                  if e.get("valid_from", 0) <= moment <= e.get("valid_to", 10 ** 9)]
        if inside:
            return {"answer": min(inside, key=lambda e: e["valid_from"])["event_id"],
                    "abstained": False, "used_validity_window": True}

    if _PAST.search(question):
        # HISTORICAL: the superseded record is the answer. Suppressing old
        # records would fail here, which is why nothing suppresses them.
        in_force = [e for e in visible if e.get("valid_from", 0) <= asked_on]
        if len(in_force) > 1:
            return {"answer": sorted(in_force, key=lambda e: e["valid_from"])[-2]["event_id"],
                    "abstained": False, "used_history": True}

    # FUTURE: newest in force *now*, which is not the newest recorded when a
    # record was written ahead of its own start date.
    in_force = [e for e in visible if e.get("valid_from", 0) <= asked_on]
    if not in_force:
        return {"answer": None, "abstained": True}
    return {"answer": max(in_force, key=lambda e: e["valid_from"])["event_id"],
            "abstained": False, "used_validity": True}


ARMS = {"newest": newest_arm, "resolver": resolver_arm}


def run(split: str) -> dict[str, Any]:
    root = SPLITS[split]
    events = load(root / "events.jsonl")
    queries = {q["query_id"]: q for q in load(root / "queries.jsonl")}
    gold = load(root / "gold.jsonl")

    chains: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        chains[event["case_id"]].append(event)

    out: dict[str, Any] = {}
    for name, arm in ARMS.items():
        records = []
        for row in gold:
            query = queries[row["query_id"]]
            result = arm(chains[row["case_id"]], query["question"], query["asked_on"])
            if row["expects_disagreement"]:
                correct = int(result["answer"] is None)
            else:
                correct = int(result["answer"] == row["gold_event_id"])
            records.append({
                "query_id": row["query_id"], "family": row["family"],
                "correct": correct,
                "took_the_wrong_record": int(result["answer"] == row["wrong_event_id"]
                                             and row["wrong_event_id"] is not None),
                "abstained": int(bool(result.get("abstained"))),
            })
        out[name] = {"records": records, "summary": summarise(name, split, records)}
    return out


def summarise(arm: str, split: str, records) -> dict[str, Any]:
    families = sorted({r["family"] for r in records})

    def rate(field, rows=None):
        rows = records if rows is None else rows
        return round(sum(r[field] for r in rows) / len(rows), 6) if rows else 0.0

    return {
        "experiment_id": "PMLAB-H2-TEMP-E1", "arm": arm, "split": split,
        "model": None, "api_cost_usd": 0.0, "probes": len(records),
        "correct": rate("correct"),
        "took_the_wrong_record": rate("took_the_wrong_record"),
        "abstention_rate": rate("abstained"),
        "by_family": {f: rate("correct", [r for r in records if r["family"] == f])
                      for f in families},
        "conflict_note": "on TEMP-CONFLICT, correct means declining to answer",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", default="dev", choices=sorted(SPLITS))
    parser.add_argument("--out", type=Path, default=None)
    arguments = parser.parse_args(argv)

    result = run(arguments.split)
    families = sorted(result["newest"]["summary"]["by_family"])

    print(f"PMLAB-H2-TEMP-E1 — {arguments.split}, model-free, no API cost\n")
    print(f"  {'arm':<11}{'correct':>9}{'wrong rec':>11}{'abstain':>9}   " +
          "".join(f"{f.replace('TEMP-','')[:7]:>9}" for f in families))
    for arm in ARMS:
        s = result[arm]["summary"]
        print(f"  {arm:<11}{s['correct']:>9.3f}{s['took_the_wrong_record']:>11.3f}"
              f"{s['abstention_rate']:>9.3f}   " +
              "".join(f"{s['by_family'][f]:>9.3f}" for f in families))

    if arguments.out:
        destination = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "results.json").write_bytes(
            (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"\nwritten: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
