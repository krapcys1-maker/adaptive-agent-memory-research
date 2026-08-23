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

from tools.project_memory.memory_store import SCHEMA_VERSION
from tools.project_memory.upcast import (
    UPCASTERS,
    V1_REQUIRED,
    UpcastError,
    derive_temporal_view,
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


def test_canonical_log_may_hold_several_versions_at_once() -> None:
    """A mixed-version log is the intended steady state, not a defect.

    This test previously asserted the log held only version 1, which encoded an
    assumption the design deliberately broke: upcasting exists precisely so old
    events stay on disk as written while new ones are written at the current
    version. It failed the moment the first version-2 event was appended, which
    is the test working — it just pinned the wrong invariant.

    What actually matters is that every version present is known to the reader
    and none is newer than it can handle.
    """
    versions = describe_versions(load_canonical())
    assert versions, "canonical log must not be empty"
    assert set(versions) <= set(range(1, SCHEMA_VERSION + 1)), (
        f"log holds a version this reader does not know: {versions}"
    )
    assert max(versions) <= SCHEMA_VERSION, "log is newer than the reader"


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


# --------------------------------------------------------------------------- v2 bitemporal shape


def test_v1_to_v2_adds_all_four_temporal_fields() -> None:
    """#34 corrected the design: four fields on two axes, not two beside created_at."""
    result = v1_to_v2(v1_event(created_at="2026-03-04T05:06:07Z"))
    assert result["schema_version"] == 2
    assert result["valid_from"] == "2026-03-04T05:06:07Z"
    assert result["valid_to"] is None
    assert result["expired_at"] is None
    assert result["claim_class"] == "unclassified"


def test_a_v1_supersession_is_unclassified_not_guessed() -> None:
    """Version 1 recorded that a conclusion changed, never whether the world did."""
    superseded = v1_event(
        id="PM-20260101-bbbbbbbb",
        operation="supersede",
        supersedes="PM-20260101-aaaaaaaa",
        supersession_reason="the measurement was label-leaked",
    )
    assert v1_to_v2(superseded)["supersession_kind"] == "unclassified"
    assert v1_to_v2(v1_event())["supersession_kind"] is None


# --------------------------------------------------------------------------- derived, not stored


def _succeeding(kind: str) -> list[dict]:
    first = v1_event(created_at="2026-01-01T00:00:00Z")
    second = v1_event(
        id="PM-20260201-bbbbbbbb",
        operation="supersede",
        supersedes=first["id"],
        created_at="2026-02-01T00:00:00Z",
        supersession_reason="revised",
    )
    second["supersession_kind"] = kind
    return [first, second]


def test_succession_derives_both_ends_from_the_successor(tmp_path: Path) -> None:
    view = {event["id"]: event for event in derive_temporal_view(_succeeding("succession"))}
    prior = view["PM-20260101-aaaaaaaa"]
    assert prior["expired_at"] == "2026-02-01T00:00:00Z", "record withdrawn when the successor was written"
    assert prior["valid_to"] == "2026-02-01T00:00:00Z", "the fact stopped being true when the next began"


def test_correction_expires_the_record_without_ending_the_fact() -> None:
    """A correction means the record was wrong, so nothing about the world changed."""
    view = {event["id"]: event for event in derive_temporal_view(_succeeding("correction"))}
    prior = view["PM-20260101-aaaaaaaa"]
    assert prior["expired_at"] == "2026-02-01T00:00:00Z"
    assert prior["valid_to"] is None


def test_an_unclassified_supersession_derives_no_valid_to() -> None:
    """Every version-1 supersession is unclassified; inventing an interval would fabricate evidence."""
    view = {event["id"]: event for event in derive_temporal_view(_succeeding("unclassified"))}
    prior = view["PM-20260101-aaaaaaaa"]
    assert prior["expired_at"] == "2026-02-01T00:00:00Z"
    assert prior["valid_to"] is None


def test_a_record_with_no_successor_keeps_both_ends_open() -> None:
    view = derive_temporal_view([v1_event()])
    assert view[0]["valid_to"] is None
    assert view[0]["expired_at"] is None


def test_the_real_log_derives_without_error_and_ends_only_superseded_records() -> None:
    events = load_canonical()
    view = derive_temporal_view(events)
    assert len(view) == len(events)

    superseded = {
        str(event["supersedes"]) for event in events if event.get("supersedes")
    }
    for event in view:
        if event["id"] in superseded:
            assert event["expired_at"] is not None, f"{event['id']} was superseded but never expired"
        else:
            assert event["expired_at"] is None, f"{event['id']} has no successor but was expired"
        # No v1 supersession is classified, so no valid_to may be derived yet.
        assert event["valid_to"] is None
