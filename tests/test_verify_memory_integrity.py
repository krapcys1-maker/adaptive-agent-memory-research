"""Mutation tests for the I0 mechanical memory gate.

The independence ladder states that an I0 tier is measured by mutation testing:
inject a registered set of defects and require detection. This module is that
measurement. Each registered mutation must be caught, and the unmutated canonical
log must pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import verify_memory_integrity as verifier  # noqa: E402

CANONICAL_EVENTS = REPOSITORY_ROOT / "memory" / "events.jsonl"


def _write_events(directory: Path, events: list[dict]) -> Path:
    path = directory / "events.jsonl"
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )
    return path


def _valid_pair() -> list[dict]:
    first = {
        "schema_version": 1,
        "id": "PM-20260101-aaaaaaaa",
        "operation": "create",
        "kind": "finding",
        "title": "First finding",
        "summary": "A finding with provenance.",
        "body": "",
        "created_at": "2026-01-01T00:00:00Z",
        "confidence": "high",
        "status": "active",
        "source_refs": ["docs/00-project/methodology.md"],
        "related_ids": [],
        "tags": ["test"],
        "supersedes": "",
    }
    second = {
        "schema_version": 1,
        "id": "PM-20260102-bbbbbbbb",
        "operation": "supersede",
        "kind": "finding",
        "title": "Revised finding",
        "summary": "The prior finding is withdrawn.",
        "body": "",
        "created_at": "2026-01-02T00:00:00Z",
        "confidence": "high",
        "status": "active",
        "source_refs": ["docs/00-project/methodology.md"],
        "related_ids": ["PM-20260101-aaaaaaaa"],
        "tags": ["test"],
        "supersedes": "PM-20260101-aaaaaaaa",
        "supersession_reason": "The measurement was label-leaked.",
    }
    return [first, second]


def test_canonical_log_passes_every_invariant() -> None:
    violations, summary = verifier.verify(CANONICAL_EVENTS)
    assert violations == [], [str(item) for item in violations]
    assert summary["events"] > 0
    assert summary["active"] + summary["superseded"] == summary["unique_ids"]


def test_valid_synthetic_pair_passes(tmp_path: Path) -> None:
    path = _write_events(tmp_path, _valid_pair())
    violations, summary = verifier.verify(path)
    assert violations == []
    assert summary == {
        "events": 2,
        "unique_ids": 2,
        "superseded": 1,
        "active": 1,
        "violations": 0,
    }


def _mutation_missing_field(events: list[dict]) -> list[dict]:
    del events[0]["confidence"]
    return events


def _mutation_duplicate_id(events: list[dict]) -> list[dict]:
    events[1]["id"] = events[0]["id"]
    return events


def _mutation_malformed_id(events: list[dict]) -> list[dict]:
    events[0]["id"] = "PM-2026-01-01-XYZ"
    return events


def _mutation_bad_operation(events: list[dict]) -> list[dict]:
    events[0]["operation"] = "delete"
    return events


def _mutation_bad_kind(events: list[dict]) -> list[dict]:
    events[0]["kind"] = "vibe"
    return events


def _mutation_bad_confidence(events: list[dict]) -> list[dict]:
    events[0]["confidence"] = "very high"
    return events


def _mutation_bad_timestamp(events: list[dict]) -> list[dict]:
    events[0]["created_at"] = "01/01/2026"
    return events


def _mutation_non_monotonic_time(events: list[dict]) -> list[dict]:
    events[1]["created_at"] = "2025-12-31T00:00:00Z"
    return events


def _mutation_dangling_supersedes(events: list[dict]) -> list[dict]:
    events[1]["supersedes"] = "PM-20259999-cccccccc"
    return events


def _mutation_forward_supersedes(events: list[dict]) -> list[dict]:
    events[0]["supersedes"] = events[1]["id"]
    events[0]["supersession_reason"] = "points forward"
    events[0]["operation"] = "supersede"
    return events


def _mutation_missing_supersession_reason(events: list[dict]) -> list[dict]:
    events[1]["supersession_reason"] = "   "
    return events


def _mutation_missing_supersedes_target(events: list[dict]) -> list[dict]:
    events[1]["supersedes"] = ""
    return events


def _mutation_evidence_without_provenance(events: list[dict]) -> list[dict]:
    events[0]["source_refs"] = []
    return events


def _mutation_supersedes_as_list(events: list[dict]) -> list[dict]:
    events[1]["supersedes"] = ["PM-20260101-aaaaaaaa"]
    return events


def _mutation_dangling_related_id(events: list[dict]) -> list[dict]:
    events[0]["related_ids"] = ["PM-20250101-dddddddd"]
    return events


def _mutation_tags_not_a_list(events: list[dict]) -> list[dict]:
    events[0]["tags"] = "test"
    return events


REGISTERED_MUTATIONS = [
    ("missing-field", _mutation_missing_field),
    ("duplicate-id", _mutation_duplicate_id),
    ("malformed-id", _mutation_malformed_id),
    ("bad-operation", _mutation_bad_operation),
    ("bad-kind", _mutation_bad_kind),
    ("bad-confidence", _mutation_bad_confidence),
    ("bad-timestamp", _mutation_bad_timestamp),
    ("non-monotonic-time", _mutation_non_monotonic_time),
    ("dangling-supersedes", _mutation_dangling_supersedes),
    ("forward-supersedes", _mutation_forward_supersedes),
    ("missing-supersession-reason", _mutation_missing_supersession_reason),
    ("missing-supersedes", _mutation_missing_supersedes_target),
    ("missing-provenance", _mutation_evidence_without_provenance),
    ("bad-type", _mutation_supersedes_as_list),
    ("dangling-related-id", _mutation_dangling_related_id),
    ("bad-type", _mutation_tags_not_a_list),
]


@pytest.mark.parametrize(
    "expected_rule,mutate",
    REGISTERED_MUTATIONS,
    ids=[f"{index:02d}-{name}" for index, (name, _) in enumerate(REGISTERED_MUTATIONS)],
)
def test_registered_mutation_is_detected(expected_rule, mutate, tmp_path: Path) -> None:
    path = _write_events(tmp_path, mutate(_valid_pair()))
    violations, _ = verifier.verify(path)
    rules = {item.rule for item in violations}
    assert expected_rule in rules, f"expected {expected_rule}, observed {sorted(rules)}"


def test_invalid_json_line_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"id": "PM-20260101-aaaaaaaa"\n', encoding="utf-8")
    violations, _ = verifier.verify(path)
    assert any(item.rule == "invalid-json" for item in violations)


def test_blank_lines_are_ignored(tmp_path: Path) -> None:
    events = _valid_pair()
    path = tmp_path / "events.jsonl"
    path.write_text(
        json.dumps(events[0]) + "\n\n" + json.dumps(events[1]) + "\n\n",
        encoding="utf-8",
    )
    violations, summary = verifier.verify(path)
    assert violations == []
    assert summary["events"] == 2


def test_cli_reports_failure_exit_code(tmp_path: Path) -> None:
    path = _write_events(tmp_path, _mutation_bad_kind(_valid_pair()))
    assert verifier.main(["--events", str(path), "--format", "json"]) == 1


def test_cli_reports_success_exit_code() -> None:
    assert verifier.main(["--events", str(CANONICAL_EVENTS), "--format", "json"]) == 0
