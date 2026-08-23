"""Verify the canonical append-only project-memory log.

This is an I0 mechanical gate: it needs no reviewer, no model, and no network.
It checks only properties that are decidable from the bytes of
``memory/events.jsonl`` itself. Anything requiring judgement belongs to a
higher independence tier and is deliberately out of scope here.

Exit code 0 means every checked invariant holds. Exit code 1 means at least one
violation was found and the log must not be treated as canonical until repaired.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "schema_version",
    "id",
    "operation",
    "kind",
    "title",
    "summary",
    "created_at",
    "confidence",
    "status",
)

ALLOWED_OPERATIONS = {"create", "supersede"}

ALLOWED_KINDS = {
    "candidate",
    "constraint",
    "decision",
    "failure",
    "finding",
    "hypothesis",
    "procedure",
    "question",
    "session",
}

ALLOWED_CONFIDENCE = {"unknown", "low", "medium", "high"}

LIST_FIELDS = ("source_refs", "related_ids", "tags")

ID_PATTERN = re.compile(r"^PM-\d{8}-[0-9a-f]{8}$")

TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# Kinds that assert something about the world rather than about intent.
# The project rule is that these carry provenance.
EVIDENCE_KINDS = {"finding", "failure"}


class Violation:
    def __init__(self, line: int, event_id: str, rule: str, detail: str) -> None:
        self.line = line
        self.event_id = event_id
        self.rule = rule
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {
            "line": self.line,
            "event_id": self.event_id,
            "rule": self.rule,
            "detail": self.detail,
        }

    def __str__(self) -> str:
        return f"line {self.line} [{self.event_id or '<no id>'}] {self.rule}: {self.detail}"


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def verify(events_path: Path) -> tuple[list[Violation], dict[str, Any]]:
    violations: list[Violation] = []
    events: list[tuple[int, dict[str, Any]]] = []

    raw = events_path.read_text(encoding="utf-8-sig")
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            violations.append(Violation(line_number, "", "invalid-json", str(exc)))
            continue
        if not isinstance(value, dict):
            violations.append(
                Violation(line_number, "", "invalid-json", "event must be a JSON object")
            )
            continue
        events.append((line_number, value))

    seen_ids: dict[str, int] = {}
    previous_timestamp: datetime | None = None

    for line_number, event in events:
        event_id = str(event.get("id", ""))

        for field in REQUIRED_FIELDS:
            if field not in event or event[field] in (None, ""):
                violations.append(
                    Violation(line_number, event_id, "missing-field", f"'{field}' is required")
                )

        if event_id and not ID_PATTERN.match(event_id):
            violations.append(
                Violation(
                    line_number,
                    event_id,
                    "malformed-id",
                    "id must match PM-YYYYMMDD-xxxxxxxx with lowercase hex",
                )
            )

        if event_id in seen_ids:
            violations.append(
                Violation(
                    line_number,
                    event_id,
                    "duplicate-id",
                    f"id already used on line {seen_ids[event_id]}",
                )
            )
        elif event_id:
            seen_ids[event_id] = line_number

        operation = event.get("operation")
        if operation not in ALLOWED_OPERATIONS:
            violations.append(
                Violation(
                    line_number,
                    event_id,
                    "bad-operation",
                    f"operation must be one of {sorted(ALLOWED_OPERATIONS)}, got {operation!r}",
                )
            )

        kind = event.get("kind")
        if kind not in ALLOWED_KINDS:
            violations.append(
                Violation(line_number, event_id, "bad-kind", f"unknown kind {kind!r}")
            )

        confidence = event.get("confidence")
        if confidence not in ALLOWED_CONFIDENCE:
            violations.append(
                Violation(
                    line_number,
                    event_id,
                    "bad-confidence",
                    f"confidence must be one of {sorted(ALLOWED_CONFIDENCE)}, got {confidence!r}",
                )
            )

        created_at = str(event.get("created_at", ""))
        if not TIMESTAMP_PATTERN.match(created_at):
            violations.append(
                Violation(
                    line_number,
                    event_id,
                    "bad-timestamp",
                    "created_at must be ISO-8601 UTC as YYYY-MM-DDTHH:MM:SSZ",
                )
            )
        else:
            parsed = _parse_timestamp(created_at)
            if parsed is None:
                violations.append(
                    Violation(line_number, event_id, "bad-timestamp", "created_at is not a real time")
                )
            else:
                if previous_timestamp is not None and parsed < previous_timestamp:
                    violations.append(
                        Violation(
                            line_number,
                            event_id,
                            "non-monotonic-time",
                            "created_at is earlier than the preceding event; the log is append-only",
                        )
                    )
                previous_timestamp = parsed

        for field in LIST_FIELDS:
            if field in event and not isinstance(event[field], list):
                violations.append(
                    Violation(line_number, event_id, "bad-type", f"'{field}' must be a list")
                )

        if kind in EVIDENCE_KINDS:
            refs = event.get("source_refs")
            if not isinstance(refs, list) or not refs:
                violations.append(
                    Violation(
                        line_number,
                        event_id,
                        "missing-provenance",
                        f"kind '{kind}' asserts evidence and requires at least one source_ref",
                    )
                )

        if operation == "supersede":
            if not event.get("supersedes"):
                violations.append(
                    Violation(
                        line_number,
                        event_id,
                        "missing-supersedes",
                        "a supersede operation must name the prior event id",
                    )
                )
            if not str(event.get("supersession_reason", "")).strip():
                violations.append(
                    Violation(
                        line_number,
                        event_id,
                        "missing-supersession-reason",
                        "a supersede operation must record why the revision was required",
                    )
                )

    # Reference integrity is resolved after the full pass so that ordering is not
    # confused with existence.
    id_to_line = dict(seen_ids)
    for line_number, event in events:
        event_id = str(event.get("id", ""))

        target = event.get("supersedes")
        if target:
            if not isinstance(target, str):
                violations.append(
                    Violation(
                        line_number,
                        event_id,
                        "bad-type",
                        "'supersedes' must be a single event id string",
                    )
                )
            elif target not in id_to_line:
                violations.append(
                    Violation(
                        line_number,
                        event_id,
                        "dangling-supersedes",
                        f"supersedes unknown event {target}",
                    )
                )
            elif id_to_line[target] >= line_number:
                violations.append(
                    Violation(
                        line_number,
                        event_id,
                        "forward-supersedes",
                        f"supersedes {target} which appears later in the log",
                    )
                )
            elif target == event_id:
                violations.append(
                    Violation(line_number, event_id, "self-supersedes", "an event cannot supersede itself")
                )

        related = event.get("related_ids")
        if isinstance(related, list):
            for related_id in related:
                if not isinstance(related_id, str):
                    violations.append(
                        Violation(line_number, event_id, "bad-type", "related_ids entries must be strings")
                    )
                elif related_id not in id_to_line:
                    violations.append(
                        Violation(
                            line_number,
                            event_id,
                            "dangling-related-id",
                            f"related_ids references unknown event {related_id}",
                        )
                    )

    superseded = {
        str(event["supersedes"])
        for _, event in events
        if isinstance(event.get("supersedes"), str) and event.get("supersedes")
    }

    summary = {
        "events": len(events),
        "unique_ids": len(seen_ids),
        "superseded": len(superseded & set(seen_ids)),
        "active": len(seen_ids) - len(superseded & set(seen_ids)),
        "violations": len(violations),
    }
    return violations, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--events",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "memory" / "events.jsonl",
        help="path to the canonical events log",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    arguments = parser.parse_args(argv)

    if not arguments.events.is_file():
        print(f"canonical memory log not found: {arguments.events}", file=sys.stderr)
        return 1

    violations, summary = verify(arguments.events)

    if arguments.format == "json":
        print(
            json.dumps(
                {"summary": summary, "violations": [item.as_dict() for item in violations]},
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            f"events={summary['events']} active={summary['active']} "
            f"superseded={summary['superseded']} violations={summary['violations']}"
        )
        for item in violations:
            print(f"  {item}")

    if violations:
        print(f"\nFAILED: {len(violations)} integrity violation(s).", file=sys.stderr)
        return 1
    print("\nOK: canonical memory log satisfies every mechanical invariant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
