"""Build the PMLAB-REV-V0 temporal fixture.

Deterministic, authored, model-free. Every event uses the real version-2 event
shape so the experiment tests the shipped schema rather than a mock of it.

What this fixture is for
------------------------
Schema version 2 claims that separating transaction time from valid time lets
the store answer questions version 1 could not. That claim is untested. This
fixture can falsify it: if a bitemporal resolver does not beat a
transaction-only one on these histories, the schema change bought nothing.

Three query types, which is the whole point
-------------------------------------------
``current``        what is true now
``valid_at(T)``    what was true at time T in the world
``as_known_at(T)`` what we believed at time T, using only records written by then

The third is the one that separates the designs. Answering it requires
transaction time, and answering it *without leaking* requires never consulting a
record created after T. A single-timestamp store cannot express the question at
all; a valid-time-only store answers it with information from the future.

Authoring note
--------------
Cases are authored by the same agent that implemented the schema, which is a
real limitation and is recorded in the report rather than hidden. It is
mitigated only by the arms being blind to the expected answers and by the oracle
being derived from the case definition rather than from any resolver's output.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "lab" / "pmlab-revision-v0"


def event(
    identifier: str,
    subject: str,
    claim: str,
    created_at: str,
    valid_from: str,
    supersedes: str | None = None,
    supersession_kind: str | None = None,
    claim_class: str = "state",
) -> dict[str, Any]:
    """One canonical event in the shipped version-2 shape."""
    return {
        "schema_version": 2,
        "id": identifier,
        "operation": "supersede" if supersedes else "create",
        "kind": "finding",
        "title": claim,
        "summary": f"{subject}: {claim}",
        "body": "",
        "tags": [subject],
        "source_refs": [f"fixture/{subject}.md"],
        "confidence": "high",
        "status": "active",
        "created_at": created_at,
        "valid_from": valid_from,
        "claim_class": claim_class,
        "supersedes": supersedes,
        "supersession_kind": supersession_kind,
        "related_ids": [],
        **({"supersession_reason": "fixture revision"} if supersedes else {}),
    }


def build() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []

    # ---------------------------------------------------------------- C1 late correction
    # Believed brown until March. In June we learn it was actually black all
    # along. The world never changed; our record was wrong.
    events += [
        event("C1-a", "c1", "hair is brown", "2026-01-10T00:00:00Z", "2026-01-01T00:00:00Z"),
        event("C1-b", "c1", "hair is black", "2026-06-10T00:00:00Z", "2026-01-01T00:00:00Z",
              supersedes="C1-a", supersession_kind="correction"),
    ]
    queries += [
        {"case": "C1", "type": "current", "subject": "c1", "expected": "hair is black",
         "note": "a correction replaces the belief outright"},
        {"case": "C1", "type": "valid_at", "at": "2026-02-01T00:00:00Z", "subject": "c1",
         "expected": "hair is black",
         "note": "it was always black; only our record was wrong"},
        {"case": "C1", "type": "as_known_at", "at": "2026-02-01T00:00:00Z", "subject": "c1",
         "expected": "hair is brown",
         "note": "in February we believed brown; the correction did not exist yet"},
    ]

    # ---------------------------------------------------------------- C2 succession
    # Brown, then dyed green in June. Both were true, at different times.
    events += [
        event("C2-a", "c2", "hair is brown", "2026-01-10T00:00:00Z", "2026-01-01T00:00:00Z"),
        event("C2-b", "c2", "hair is green", "2026-06-10T00:00:00Z", "2026-06-01T00:00:00Z",
              supersedes="C2-a", supersession_kind="succession"),
    ]
    queries += [
        {"case": "C2", "type": "current", "subject": "c2", "expected": "hair is green"},
        {"case": "C2", "type": "valid_at", "at": "2026-03-01T00:00:00Z", "subject": "c2",
         "expected": "hair is brown",
         "note": "brown was genuinely true in March; a succession closes an interval"},
        {"case": "C2", "type": "as_known_at", "at": "2026-03-01T00:00:00Z", "subject": "c2",
         "expected": "hair is brown"},
    ]

    # ---------------------------------------------------------------- C3 future-effective rule
    # Written in January, takes effect in September.
    events += [
        event("C3-a", "c3", "rate is 5 percent", "2026-01-10T00:00:00Z", "2026-01-01T00:00:00Z"),
        event("C3-b", "c3", "rate is 7 percent", "2026-01-15T00:00:00Z", "2026-09-01T00:00:00Z",
              supersedes="C3-a", supersession_kind="succession"),
    ]
    queries += [
        {"case": "C3", "type": "valid_at", "at": "2026-05-01T00:00:00Z", "subject": "c3",
         "expected": "rate is 5 percent",
         "note": "the new rule was recorded but not yet in force"},
        {"case": "C3", "type": "as_known_at", "at": "2026-05-01T00:00:00Z", "subject": "c3",
         "expected": "rate is 5 percent",
         "note": "a store ordering by write time alone answers 7 and is wrong"},
    ]

    # ---------------------------------------------------------------- C4 correction of a correction
    events += [
        event("C4-a", "c4", "weight is 70 kg", "2026-02-01T00:00:00Z", "2026-02-01T00:00:00Z"),
        event("C4-b", "c4", "weight is 60 kg", "2026-03-01T00:00:00Z", "2026-02-01T00:00:00Z",
              supersedes="C4-a", supersession_kind="correction"),
        event("C4-c", "c4", "weight is 68 kg", "2026-04-01T00:00:00Z", "2026-02-01T00:00:00Z",
              supersedes="C4-b", supersession_kind="correction"),
    ]
    queries += [
        {"case": "C4", "type": "current", "subject": "c4", "expected": "weight is 68 kg"},
        {"case": "C4", "type": "as_known_at", "at": "2026-03-15T00:00:00Z", "subject": "c4",
         "expected": "weight is 60 kg",
         "note": "the middle belief must be reconstructable, not just the first and last"},
        {"case": "C4", "type": "as_known_at", "at": "2026-02-15T00:00:00Z", "subject": "c4",
         "expected": "weight is 70 kg"},
    ]

    # ---------------------------------------------------------------- C5 future-information leakage
    # The critical case. Asking what we knew in January must never return a
    # record written in December.
    events += [
        event("C5-a", "c5", "status is open", "2026-01-05T00:00:00Z", "2026-01-01T00:00:00Z"),
        event("C5-b", "c5", "status is closed", "2026-12-01T00:00:00Z", "2026-01-01T00:00:00Z",
              supersedes="C5-a", supersession_kind="correction"),
    ]
    queries += [
        {"case": "C5", "type": "as_known_at", "at": "2026-02-01T00:00:00Z", "subject": "c5",
         "expected": "status is open", "critical": True,
         "note": "returning 'closed' is future-information leakage and blocks V1-V3"},
        {"case": "C5", "type": "current", "subject": "c5", "expected": "status is closed"},
    ]

    # ---------------------------------------------------------------- C6 concurrent writers
    # Two records one second apart. A store with only a coarse timestamp cannot
    # order them and may pick a silent winner.
    events += [
        event("C6-a", "c6", "owner is alice", "2026-05-01T12:00:00Z", "2026-05-01T12:00:00Z"),
        event("C6-b", "c6", "owner is bob", "2026-05-01T12:00:01Z", "2026-05-01T12:00:01Z",
              supersedes="C6-a", supersession_kind="succession"),
    ]
    queries += [
        {"case": "C6", "type": "current", "subject": "c6", "expected": "owner is bob"},
        {"case": "C6", "type": "valid_at", "at": "2026-05-01T12:00:00Z", "subject": "c6",
         "expected": "owner is alice",
         "note": "one second of resolution must still separate them"},
    ]

    # ---------------------------------------------------------------- C7 unrevised fact
    events += [event("C7-a", "c7", "city is Warsaw", "2026-03-01T00:00:00Z", "2026-03-01T00:00:00Z",
                     claim_class="dispositional")]
    queries += [
        {"case": "C7", "type": "current", "subject": "c7", "expected": "city is Warsaw"},
        {"case": "C7", "type": "as_known_at", "at": "2026-01-01T00:00:00Z", "subject": "c7",
         "expected": None,
         "note": "nothing was known about c7 in January; a store that answers anyway is leaking"},
        {"case": "C7", "type": "valid_at", "at": "2026-01-01T00:00:00Z", "subject": "c7",
         "expected": None},
    ]

    return events, queries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    arguments = parser.parse_args(argv)

    events, queries = build()
    destination = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
    destination.mkdir(parents=True, exist_ok=True)

    for name, rows in (("events.jsonl", events), ("queries.jsonl", queries)):
        payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
        (destination / name).write_bytes(payload.encode("utf-8"))

    critical = sum(1 for q in queries if q.get("critical"))
    print(
        json.dumps(
            {
                "events": len(events),
                "queries": len(queries),
                "cases": len({q["case"] for q in queries}),
                "critical_queries": critical,
                "by_type": {
                    t: sum(1 for q in queries if q["type"] == t)
                    for t in ("current", "valid_at", "as_known_at")
                },
                "out": destination.relative_to(ROOT).as_posix(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
