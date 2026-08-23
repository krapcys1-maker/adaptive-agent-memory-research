"""Tests for schema evolution by upcasting.

Two properties matter more than any individual case and are checked against the
real canonical log rather than a fixture:

* an upcaster is **total** — defined for every event the previous version
  permitted, so migration cannot silently skip records;
* an upcaster **never drops a field**, so migration cannot silently lose data.

Both are the failure modes that make schema migration frightening. Testing them
on the actual 180-plus event log is what makes the guarantee real.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.project_memory.upcast import (
    UPCASTERS,
    V1_REQUIRED,
    UpcastError,
    describe_versions,
    upcast_all,
    upcast_event,
    v1_to_v2,
)

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "memory" / "events.jsonl"


def load_canonical() -> list[dict]:
    return [
        json.loads(line)
        for line in CANONICAL.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def v1_event(**overrides) -> dict:
    event = {
        "schema_version": 1,
        "id": "PM-20260101-aaaaaaaa",
        "operation": "create",
        "kind": "finding",
        "title": "A finding",
        "summary": "Summary.",
        "body": "",
        "created_at": "2026-01-01T00:00:00Z",
        "confidence": "high",
        "status": "active",
        "source_refs": ["docs/example.md"],
        "related_ids": [],
        "tags": ["example"],
        "supersedes": "",
    }
    event.update(overrides)
    return event


# --------------------------------------------------------------------------- totality


def test_every_canonical_event_upcasts() -> None:
    events = load_canonical()
    assert events, "canonical log must not be empty"
    upcast = upcast_all(events, target=2)
    assert len(upcast) == len(events)
    assert all(item["schema_version"] == 2 for item in upcast)


def test_upcasting_the_canonical_log_drops_no_field() -> None:
    for original in load_canonical():
        result = upcast_event(original, target=2)
        for key, value in original.items():
            if key == "schema_version":
                continue
            assert key in result, f"{original['id']}: upcast dropped {key!r}"
            assert result[key] == value, f"{original['id']}: upcast altered {key!r}"


def test_canonical_log_is_currently_single_version() -> None:
    versions = describe_versions(load_canonical())
    assert set(versions) == {1}, f"expected only version 1 today, saw {versions}"


# --------------------------------------------------------------------------- v1 to v2


def test_v1_to_v2_defaults_valid_from_to_transaction_time() -> None:
    result = v1_to_v2(v1_event(created_at="2026-03-04T05:06:07Z"))
    assert result["schema_version"] == 2
    assert result["valid_from"] == "2026-03-04T05:06:07Z"


def test_v1_to_v2_leaves_the_interval_open() -> None:
    """A version-1 log never recorded when a fact stopped being true."""
    assert v1_to_v2(v1_event())["valid_to"] is None


def test_v1_to_v2_does_not_close_the_interval_of_a_superseded_event() -> None:
    """Supersession records when a revision was written, not when the world changed.

    Inferring an end time from it would fabricate a date and put a guess into
    what reads as recorded evidence.
    """
    superseded = v1_event(
        id="PM-20260101-bbbbbbbb",
        operation="supersede",
        supersedes="PM-20260101-aaaaaaaa",
        supersession_reason="the measurement was label-leaked",
    )
    result = v1_to_v2(superseded)
    assert result["valid_to"] is None
    assert result["supersession_reason"] == "the measurement was label-leaked"


def test_v1_to_v2_does_not_guess_the_claim_class() -> None:
    assert v1_to_v2(v1_event())["claim_class"] == "unclassified"


def test_v1_to_v2_preserves_every_required_field() -> None:
    original = v1_event()
    result = v1_to_v2(original)
    for field in V1_REQUIRED:
        if field == "schema_version":
            continue
        assert result[field] == original[field]


def test_upcast_is_idempotent_at_the_target_version() -> None:
    once = upcast_event(v1_event(), target=2)
    twice = upcast_event(once, target=2)
    assert once == twice


def test_upcast_does_not_mutate_its_input() -> None:
    original = v1_event()
    snapshot = json.dumps(original, sort_keys=True)
    upcast_event(original, target=2)
    assert json.dumps(original, sort_keys=True) == snapshot


# --------------------------------------------------------------------------- refusals


def test_an_event_newer_than_the_reader_is_refused() -> None:
    """A future log must not be silently misread by an old reader."""
    with pytest.raises(UpcastError, match="too old for this log"):
        upcast_event(v1_event(schema_version=5), target=2)


def test_a_missing_version_is_refused() -> None:
    event = v1_event()
    del event["schema_version"]
    with pytest.raises(UpcastError, match="no integer schema_version"):
        upcast_event(event, target=2)


def test_a_gap_in_the_upcaster_chain_is_refused() -> None:
    with pytest.raises(UpcastError, match="no upcaster registered"):
        upcast_event(v1_event(), target=max(UPCASTERS) + 3)


def test_registered_upcasters_form_a_contiguous_chain() -> None:
    """A gap would make some version unreachable and migration would stall."""
    versions = sorted(UPCASTERS)
    assert versions == list(range(1, len(versions) + 1))
