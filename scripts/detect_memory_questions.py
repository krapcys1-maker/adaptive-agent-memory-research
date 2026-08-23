"""Stage 1 of the idle reflection loop: find what the memory does not know.

Issue #27. Deterministic, model-free, no network, no API cost.

Why questions and not syntheses
-------------------------------
A reflection loop that emits *facts* creates memory without new evidence. A weak
finding restated as a clean sentence launders uncertainty into confidence, and
nothing distinguishes a real insight from a fabricated one afterwards. That risk
is registered and is why Stage 2 is gated behind this.

A loop that emits *questions and detected contradictions* carries no such risk,
because every output is checkable against the log. This module only detects; it
never asserts, never summarises, and never writes to memory. It prints what a
person or a later stage may choose to record as a ``question``.

The gap it addresses
--------------------
The store held 200 events with 73 findings, 48 decisions and **one** question.
The project asserts in roughly 70% of its records and almost never writes down
what it does not know.

Detectors
---------
Each is decidable from the log alone.

``dangling-source``      a finding or failure whose cited repository path no longer exists
``unreferenced-decision`` a decision no later event cites, links to, or supersedes
``stale-hypothesis``     a hypothesis older than a threshold with no linked outcome
``cited-superseded``     an active record citing a memory that has since been superseded
``unclassified-revision`` a supersession that does not say whether the world changed

Why there is no contradiction detector here
-------------------------------------------
A polarity-lexicon version was written and **removed after measurement**. On this
corpus it produced four hits and all four were false positives: a ``failure`` and
the ``decision`` repairing it cite the same source with opposite-sounding
wording, which is a problem and its fix rather than a disagreement.

The cause is not a poor word list. This project's prose is saturated with
negation — "does not show", "cannot", "not supported" — precisely because it is
disciplined about stating limits. A polarity heuristic therefore fires
constantly and means nothing here.

The line this draws is worth keeping: **Stage 1 contains only exact detectors.**
Contradiction is a semantic judgement, so it belongs to Stage 2 with a model and
its budget, not to a heuristic pretending to be mechanical.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

STALE_HYPOTHESIS_DAYS = 30

ID_IN_TEXT = re.compile(r"\bPM-\d{8}-[0-9a-f]{8}\b")


def load(root: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (root / "memory" / "events.jsonl").read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def _text(event: dict[str, Any]) -> str:
    return f"{event.get('title','')} {event.get('summary','')} {event.get('body','')}"


def _parse(stamp: str) -> datetime | None:
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def detect(root: Path, now: datetime) -> list[dict[str, Any]]:
    events = load(root)
    superseded = {str(e["supersedes"]) for e in events if e.get("supersedes")}
    active = [e for e in events if e["id"] not in superseded]
    by_id = {e["id"]: e for e in events}

    # Every mention of a memory id anywhere, so "referenced" means what a reader
    # would call referenced rather than only a populated related_ids field.
    referenced: set[str] = set()
    for event in events:
        for identifier in ID_IN_TEXT.findall(_text(event) + " ".join(event.get("source_refs") or [])):
            if identifier != event["id"]:
                referenced.add(identifier)
        for identifier in event.get("related_ids") or []:
            referenced.add(str(identifier))
        if event.get("supersedes"):
            referenced.add(str(event["supersedes"]))

    questions: list[dict[str, Any]] = []

    def ask(detector: str, event: dict[str, Any], question: str, evidence: str) -> None:
        questions.append(
            {
                "detector": detector,
                "memory_id": event["id"],
                "kind": event.get("kind"),
                "title": event.get("title", "")[:80],
                "question": question,
                "evidence": evidence,
            }
        )

    for event in active:
        kind = event.get("kind")

        if kind in {"finding", "failure"}:
            for reference in event.get("source_refs") or []:
                if reference.startswith(("http://", "https://", "doi:", "arXiv:", "paper:")):
                    continue
                bare = reference.split("#", 1)[0].strip()
                if bare and re.search(r"[/.]", bare) and not (root / bare).exists():
                    ask(
                        "dangling-source",
                        event,
                        f"Does this claim still have evidence? Its source {bare} no longer exists.",
                        bare,
                    )

        if kind == "decision" and event["id"] not in referenced:
            created = _parse(event.get("created_at", ""))
            if created and (now - created) > timedelta(days=7):
                ask(
                    "unreferenced-decision",
                    event,
                    "Is this decision still in force? Nothing recorded since has cited it.",
                    f"recorded {event.get('created_at')}",
                )

        if kind == "hypothesis":
            created = _parse(event.get("created_at", ""))
            if created and (now - created) > timedelta(days=STALE_HYPOTHESIS_DAYS):
                if event["id"] not in referenced:
                    ask(
                        "stale-hypothesis",
                        event,
                        f"Was this ever tested? It is over {STALE_HYPOTHESIS_DAYS} days old "
                        f"with no linked finding or failure.",
                        f"recorded {event.get('created_at')}",
                    )

        for identifier in set(ID_IN_TEXT.findall(_text(event))) | {
            str(i) for i in (event.get("related_ids") or [])
        }:
            if identifier in superseded and identifier != event.get("supersedes"):
                ask(
                    "cited-superseded",
                    event,
                    f"Does this still hold? It cites {identifier}, which has since been superseded.",
                    identifier,
                )

    for event in events:
        if event.get("operation") == "supersede" and event.get("schema_version", 1) >= 2:
            if event.get("supersession_kind") == "unclassified":
                ask(
                    "unclassified-revision",
                    event,
                    "Did the world change, or was the record wrong? The revision does not say, "
                    "so no valid_to can be derived.",
                    f"supersedes {event.get('supersedes')}",
                )

    return questions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--detector", action="append", default=None)
    arguments = parser.parse_args(argv)

    questions = detect(ROOT, datetime.now(timezone.utc))
    if arguments.detector:
        questions = [q for q in questions if q["detector"] in set(arguments.detector)]

    if arguments.format == "json":
        print(json.dumps(questions, indent=2, sort_keys=True))
        return 0

    counts: dict[str, int] = {}
    for question in questions:
        counts[question["detector"]] = counts.get(question["detector"], 0) + 1
    print(f"questions detected: {len(questions)}")
    for name, count in sorted(counts.items()):
        print(f"  {name:<24} {count}")
    if questions:
        print("\ndetail:")
        for question in questions[:40]:
            print(f"  [{question['detector']}] {question['memory_id']}")
            print(f"      {question['question']}")
            print(f"      evidence: {question['evidence'][:96]}")
        if len(questions) > 40:
            print(f"  … {len(questions) - 40} more; use --format json")
    print("\nThis detects only. Nothing was written to memory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
