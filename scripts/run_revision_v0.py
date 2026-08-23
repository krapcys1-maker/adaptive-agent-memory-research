"""PMLAB-REV-V0: does separating valid time from transaction time buy anything?

Tier E exploratory experiment. Deterministic, model-free, no network, no API cost.

The claim under test
--------------------
Schema version 2 separates transaction time (``created_at``, ``expired_at``)
from valid time (``valid_from``, ``valid_to``). That change was made today on
the strength of a comparison with Graphiti and SQL:2011. It has not been
measured. **This run can falsify it**: if a bitemporal resolver does not beat a
transaction-only one, the schema change bought nothing and should be reverted.

Arms
----
``one_timestamp``     only ``created_at``; the latest write wins. What version 1 was.
``transaction_only``  ``created_at`` plus supersession; can answer what was believed when.
``valid_only``        ``valid_from`` plus supersession; can answer what was true when.
``bitemporal``        both axes. What version 2 is.
``oracle``            the expected answer, as a ceiling.

Queries
-------
``current``        what is true now
``valid_at(T)``    what was true at T in the world
``as_known_at(T)`` what we believed at T, using only records written by then

The third separates the designs, and one query is marked **critical**: answering
``as_known_at`` with a record created afterwards is future-information leakage.
The registered threshold blocks V1 through V3 on any critical leak.

Resolvers are deliberately small and blind to the expected answers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "lab" / "pmlab-revision-v0"


def load(name: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (FIXTURE / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _chain(events: list[dict[str, Any]], subject: str) -> list[dict[str, Any]]:
    return [e for e in events if subject in (e.get("tags") or [])]


def _superseded_by(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(e["supersedes"]): e for e in events if e.get("supersedes")}


def resolve_one_timestamp(events, subject, query) -> str | None:
    """Only created_at exists. The latest write wins, whatever the question."""
    chain = _chain(events, subject)
    if not chain:
        return None
    return max(chain, key=lambda e: e["created_at"])["title"]


def resolve_transaction_only(events, subject, query) -> str | None:
    """Transaction time plus supersession: what was believed, and when."""
    chain = _chain(events, subject)
    if query["type"] == "as_known_at":
        visible = [e for e in chain if e["created_at"] <= query["at"]]
    else:
        visible = chain
    if not visible:
        return None
    successor = _superseded_by(visible)
    live = [e for e in visible if e["id"] not in successor]
    return max(live, key=lambda e: e["created_at"])["title"] if live else None


def resolve_valid_only(events, subject, query) -> str | None:
    """Valid time plus supersession: what was true, and when — but no write history."""
    chain = _chain(events, subject)
    at = query.get("at")
    if query["type"] == "current":
        candidates = chain
    else:
        # No transaction axis, so `as_known_at` is answered as `valid_at`. That
        # is exactly the confusion this arm exists to expose.
        candidates = [e for e in chain if e["valid_from"] <= at]
    if not candidates:
        return None
    return max(candidates, key=lambda e: (e["valid_from"], e["created_at"]))["title"]


def resolve_bitemporal(events, subject, query) -> str | None:
    """Both axes, with the ends derived from the successor as the store does."""
    chain = _chain(events, subject)
    kind = query["type"]
    at = query.get("at")

    if kind == "as_known_at":
        # Only records written by T may be consulted. Anything later is future
        # information and must not influence the answer.
        visible = [e for e in chain if e["created_at"] <= at]
        if not visible:
            return None
        successor = _superseded_by(visible)
        live = [e for e in visible if e["id"] not in successor]
        # Among what was live then, take the one in force at that time.
        in_force = [e for e in live if e["valid_from"] <= at] or live
        return max(in_force, key=lambda e: (e["valid_from"], e["created_at"]))["title"]

    visible = chain
    successor = _superseded_by(visible)

    if kind == "current":
        live = [e for e in visible if e["id"] not in successor]
        in_force = [e for e in live if e["valid_from"] <= "9999-12-31T23:59:59Z"]
        return max(in_force, key=lambda e: (e["valid_from"], e["created_at"]))["title"] if in_force else None

    # valid_at: the record in force at T under the latest belief. A correction
    # rewrites what was true then; a succession closes the earlier interval.
    live_at: list[dict[str, Any]] = []
    for candidate in visible:
        if candidate["valid_from"] > at:
            continue
        following = successor.get(candidate["id"])
        if following is None:
            live_at.append(candidate)
            continue
        if following.get("supersession_kind") == "correction":
            continue  # the claim was never true; its corrected form covers this time
        if following["valid_from"] > at:
            live_at.append(candidate)  # succession ends it later than T
    if not live_at:
        return None
    return max(live_at, key=lambda e: (e["valid_from"], e["created_at"]))["title"]


def resolve_oracle(events, subject, query) -> str | None:
    return query["expected"]


ARMS = {
    "one_timestamp": resolve_one_timestamp,
    "transaction_only": resolve_transaction_only,
    "valid_only": resolve_valid_only,
    "bitemporal": resolve_bitemporal,
    "oracle": resolve_oracle,
}


def leaked(events, subject, query, answer) -> bool:
    """Did the answer come from a record written after the asked-about time?"""
    if query["type"] != "as_known_at" or answer is None:
        return False
    return any(
        e["title"] == answer and e["created_at"] > query["at"]
        for e in _chain(events, subject)
    )


def run() -> dict[str, Any]:
    events, queries = load("events.jsonl"), load("queries.jsonl")
    records: list[dict[str, Any]] = []

    for arm, resolve in ARMS.items():
        for query in queries:
            answer = resolve(events, query["subject"], query)
            records.append(
                {
                    "arm": arm,
                    "case": query["case"],
                    "type": query["type"],
                    "critical": bool(query.get("critical")),
                    "expected": query["expected"],
                    "answer": answer,
                    "correct": int(answer == query["expected"]),
                    "leaked": int(leaked(events, query["subject"], query, answer)),
                }
            )

    def summarize(arm: str) -> dict[str, Any]:
        rows = [r for r in records if r["arm"] == arm]
        by_type = {
            t: round(
                sum(r["correct"] for r in rows if r["type"] == t)
                / max(1, sum(1 for r in rows if r["type"] == t)),
                4,
            )
            for t in ("current", "valid_at", "as_known_at")
        }
        return {
            "exact": round(sum(r["correct"] for r in rows) / len(rows), 4),
            "by_query_type": by_type,
            "future_leaks": sum(r["leaked"] for r in rows),
            "critical_failures": sum(
                1 for r in rows if r["critical"] and (not r["correct"] or r["leaked"])
            ),
        }

    return {
        "summary": {
            "experiment_id": "PMLAB-REV-V0-001",
            "tier": "E-exploratory",
            "authority": "development measurement only; corpus authored by the agent that implemented the schema",
            "events": len(events),
            "queries": len(queries),
            "cases": len({q["case"] for q in queries}),
            "registered_threshold": "zero critical future leakage or silent concurrent winner; exact pre-correction reconstruction",
            "arms": {arm: summarize(arm) for arm in ARMS},
        },
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)

    payload = run()
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))

    failures = [
        r for r in payload["records"] if r["arm"] != "oracle" and (not r["correct"] or r["leaked"])
    ]
    if failures:
        print("\nfailures:")
        for r in failures:
            flag = " LEAK" if r["leaked"] else ""
            print(
                f"  {r['arm']:<18}{r['case']} {r['type']:<13}"
                f"expected {str(r['expected'])[:24]:<26} got {str(r['answer'])[:24]}{flag}"
            )

    if arguments.output:
        destination = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"\nwritten: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
