"""Corpus H2: five families where ordering by recency is not enough.

Why a second corpus
-------------------
H1 exercises **succession** and nothing else — A then B then C, where the newest
record is the answer. ``PMLAB-H1-COMPOSE-E1`` showed a temporal resolver is a
no-op there, because an addressed chain already arrives newest-first. That is a
real simplification, and it is also the limit of what H1 can say: the benchmark
stopped distinguishing the architectures under test.

Every family here is a case where **N1 is not the answer**, so a resolver either
earns its place or is refuted.

``TEMP-FUTURE``      written newest, in force later. Asked before that date the
                     previous record is correct. This is ``PMLAB-REV-V0`` case
                     C3, which the store's own resolver got wrong.
``TEMP-CORRECTION``  the earlier record was never true. Invalidated, not
                     historical, so it must not answer *what was it before?*
``TEMP-HISTORICAL``  ordinary succession asked about the past. The superseded
                     record **is** the answer.
``TEMP-OVERLAP``     two records with overlapping validity. Recency picks one
                     arbitrarily.
``TEMP-CONFLICT``    two sources disagree with no supersession between them.
                     Surfacing the disagreement is correct; picking is not.

Two of those are traps for the resolver rather than for the retriever.
``TEMP-HISTORICAL`` blocks a resolver that passes by suppressing everything old,
and ``TEMP-CONFLICT`` blocks one that answers confidently whenever asked. A
mechanism that always prefers the newest fails FUTURE and OVERLAP; one that
always prefers the oldest fails HISTORICAL. There is no ordering policy that
passes all five, which is the point of building it.

Determinism and schema
----------------------
Same LCG as H1, no clock and no ``random``. Events carry ``recorded_on`` and
``valid_from`` as separate fields — the distinction H1 collapsed into one ``day``
and the whole reason these families are decidable at all.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.history_family_spec import _lcg  # noqa: E402

DEFAULT_SEED = 20260824
DEFAULT_INSTANCES = 14
BLOCK = 14

SUBJECTS = (
    "orders", "billing", "search", "ingest", "notify", "ledger", "roster",
    "vault", "invoicing", "dispatch", "catalog", "identity", "telemetry", "payouts",
    "scheduler", "archive", "shipping", "pricing", "consent", "routing", "clearing",
    "onboarding", "reconcile", "settlement", "custody", "escrow", "fulfilment", "provisioning",
)

FAMILIES = ("TEMP-FUTURE", "TEMP-CORRECTION", "TEMP-HISTORICAL", "TEMP-OVERLAP", "TEMP-CONFLICT")


def _subject(instance: int, seed: int) -> str:
    """Disjoint blocks per split, as in H1. A shared subject is a shared question."""
    block = 0 if seed == DEFAULT_SEED else 1
    return SUBJECTS[block * BLOCK + instance % BLOCK]


def _case(kind: str, instance: int, seed: int, stream: Iterator[int]) -> dict[str, Any]:
    subject = _subject(instance, seed)
    old = 5 + next(stream) % 8
    new = 13 + next(stream) % 9
    case_id = f"{kind}-{instance:02d}"

    if kind == "TEMP-FUTURE":
        return {
            "case_id": case_id, "family": kind, "subject": subject,
            "events": [
                {"recorded_on": 3, "valid_from": 3, "record_kind": "state",
                 "text": f"The {subject} retention window is {old} days."},
                {"recorded_on": 10, "valid_from": 40, "record_kind": "state",
                 "text": f"From day 40 the {subject} retention window becomes {new} days."},
            ],
            "probe": {"asked_on": 20,
                      "question": f"What is the {subject} retention window right now?",
                      "gold_index": 0, "wrong_index": 1,
                      "why": "the newest record comes into force on day 40; on day 20 the earlier one holds"},
        }

    if kind == "TEMP-CORRECTION":
        return {
            "case_id": case_id, "family": kind, "subject": subject,
            "events": [
                {"recorded_on": 4, "valid_from": 4, "record_kind": "state",
                 "text": f"The {subject} retention window is {old} days."},
                {"recorded_on": 12, "valid_from": 4, "record_kind": "correction",
                 "text": f"Correction: the {subject} retention window was never {old} days. "
                         f"It has been {new} days since day 4."},
            ],
            "probe": {"asked_on": 25,
                      "question": f"What was the {subject} retention window before the correction?",
                      "gold_index": 1, "wrong_index": 0,
                      "why": "the earlier record was never true, so it is invalidated rather than "
                             "historical and must not answer a question about the past either"},
        }

    if kind == "TEMP-HISTORICAL":
        return {
            "case_id": case_id, "family": kind, "subject": subject,
            "events": [
                {"recorded_on": 4, "valid_from": 4, "record_kind": "state",
                 "text": f"The {subject} retention window is {old} days."},
                {"recorded_on": 16, "valid_from": 16, "record_kind": "state",
                 "text": f"The {subject} retention window is now {new} days."},
            ],
            "probe": {"asked_on": 25,
                      "question": f"What was the {subject} retention window before it changed?",
                      "gold_index": 0, "wrong_index": 1,
                      "why": "ordinary succession asked about the past: the superseded record IS the "
                             "answer, so a resolver cannot pass by suppressing everything old"},
        }

    if kind == "TEMP-OVERLAP":
        return {
            "case_id": case_id, "family": kind, "subject": subject,
            "events": [
                {"recorded_on": 5, "valid_from": 5, "valid_to": 30, "record_kind": "state",
                 "text": f"Between day 5 and day 30 the {subject} retention window is {old} days."},
                {"recorded_on": 9, "valid_from": 20, "valid_to": 45, "record_kind": "state",
                 "text": f"Between day 20 and day 45 the {subject} retention window is {new} days."},
            ],
            "probe": {"asked_on": 12,
                      "question": f"What was the {subject} retention window on day 12?",
                      "gold_index": 0, "wrong_index": 1,
                      "why": "the windows overlap between days 20 and 30; day 12 falls inside the "
                             "first only, and recency alone would take the second"},
        }

    return {
        "case_id": case_id, "family": kind, "subject": subject,
        "events": [
            {"recorded_on": 6, "valid_from": 6, "record_kind": "state", "source": "runbook",
             "text": f"Per the runbook the {subject} retention window is {old} days."},
            {"recorded_on": 7, "valid_from": 6, "record_kind": "state", "source": "dashboard",
             "text": f"Per the dashboard the {subject} retention window is {new} days."},
        ],
        "probe": {"asked_on": 22,
                  "question": f"What is the {subject} retention window?",
                  "gold_index": None, "wrong_index": None,
                  "why": "two sources disagree with no supersession between them; surfacing the "
                         "disagreement is correct and any confident single answer is wrong"},
    }


def build(seed: int, instances: int):
    events: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []

    for offset, kind in enumerate(FAMILIES):
        stream = _lcg(seed + 7919 * (offset + 1))
        for instance in range(instances):
            case = _case(kind, instance, seed, stream)
            identifiers = []
            for index, event in enumerate(case["events"]):
                identifier = f"{case['case_id']}#{index:03d}"
                identifiers.append(identifier)
                events.append({"event_id": identifier, "case_id": case["case_id"],
                               "subject": case["subject"], **event})
            probe = case["probe"]
            queries.append({"query_id": f"Q-{case['case_id']}",
                            "asked_on": probe["asked_on"], "question": probe["question"]})
            gold.append({
                "query_id": f"Q-{case['case_id']}", "case_id": case["case_id"],
                "family": case["family"],
                "gold_event_id": identifiers[probe["gold_index"]] if probe["gold_index"] is not None else None,
                "wrong_event_id": identifiers[probe["wrong_index"]] if probe["wrong_index"] is not None else None,
                "expects_disagreement": probe["gold_index"] is None,
                "why": probe["why"],
            })

    events.sort(key=lambda e: (e["recorded_on"], e["event_id"]))
    return events, queries, gold


def _write(path: Path, rows) -> str:
    payload = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    data = payload.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--instances", type=int, default=DEFAULT_INSTANCES)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "lab" / "corpus-h2" / "dev")
    arguments = parser.parse_args(argv)

    events, queries, gold = build(arguments.seed, arguments.instances)
    out = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out

    digests = {
        "events_sha256": _write(out / "events.jsonl", events),
        "queries_sha256": _write(out / "queries.jsonl", queries),
        "gold_sha256": _write(out / "gold.jsonl", gold),
    }
    manifest = {
        "corpus_id": "H2-TEMPORAL", "seed": arguments.seed,
        "instances_per_family": arguments.instances, "families": list(FAMILIES),
        "events": len(events), "probes": len(queries), **digests,
        "generator": "scripts/build_temporal_corpus_h2.py",
        "why": ("H1 exercises succession only, where an addressed chain arrives newest-first and a "
                "resolver is a no-op. Every family here is a case where N1 is not the answer, so a "
                "resolver either earns its place or is refuted"),
        "no_ordering_policy_passes_all_five": (
            "always-newest fails FUTURE and OVERLAP; always-oldest fails HISTORICAL; suppressing old "
            "records fails HISTORICAL; answering confidently always fails CONFLICT"),
    }
    (out / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))

    print(f"corpus H2 written: {len(events)} events, {len(queries)} probes")
    for family in FAMILIES:
        print(f"  {family:<18} {sum(1 for g in gold if g['family'] == family)} probes")
    print(f"  events sha256 {digests['events_sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
