"""Every detector must demonstrably fire.

On the live corpus, evaluated as of the day the log was last written, this
module raised nothing until the arena records were added; the few questions it
raises now are listed in KNOWN_OPEN_QUESTIONS. Silence on real data is a
correct result and not evidence the detectors work.

Shipping five detectors that have never once fired would repeat a mistake made
earlier the same day, when six test methods existed and were never collected.
Each detector therefore has a constructed case proving it fires, and a companion
case proving it stays silent when it should.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import detect_memory_questions as detector  # noqa: E402

NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)

# The age-based detectors compare each record's age with "now". Against the wall
# clock the live-corpus test below failed on every run once the log turned a week
# old, which says something about the log and nothing about the detectors. The
# corpus is therefore evaluated as of a fixed instant: the day it was last written.
LIVE_CORPUS_AS_OF = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

# Questions the detectors legitimately raise on the records written with the arena
# campaign: four cite sources that are not tracked in this repository (three
# research notes that exist only in a working tree, one git-ignored dataset) and
# three cite records that were later superseded. They are questions for the owner,
# not detector defects. Resolve one by committing the cited file or by appending a
# supersession; this set may only shrink.
KNOWN_OPEN_QUESTIONS = frozenset(
    {
        ("cited-superseded", "PM-20260824-bc15991a", "PM-20260824-aba1b1f7"),
        ("cited-superseded", "PM-20260824-c76d8a96", "PM-20260824-d07d2a4b"),
        ("cited-superseded", "PM-20260824-f0918718", "PM-20260824-d07d2a4b"),
        (
            "dangling-source",
            "PM-20260824-169683b7",
            "external/datasets/longmemeval-cleaned-98d7416c24c7/longmemeval_s_cleaned.json",
        ),
        ("dangling-source", "PM-20260824-c56f7e3a", "docs/research/RELATED_WORK_RED_TEAM_2026-08-24.md"),
        ("dangling-source", "PM-20260824-fe6990ce", "docs/research/CROSS_PAPER_HYPOTHESIS_MAP_2026-08-24.md"),
        (
            "dangling-source",
            "PM-20260824-fe6990ce",
            "docs/research/GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md",
        ),
    }
)


def write_log(root: Path, events: list[dict]) -> Path:
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "memory" / "events.jsonl").write_bytes(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in events).encode("utf-8")
    )
    return root


def event(**overrides) -> dict:
    base = {
        "schema_version": 2,
        "id": "PM-20260101-aaaaaaaa",
        "operation": "create",
        "kind": "finding",
        "title": "A finding",
        "summary": "Summary.",
        "body": "",
        "created_at": "2026-01-01T00:00:00Z",
        "valid_from": "2026-01-01T00:00:00Z",
        "claim_class": "unclassified",
        "confidence": "high",
        "status": "active",
        "source_refs": [],
        "related_ids": [],
        "tags": [],
        "supersedes": None,
        "supersession_kind": None,
    }
    base.update(overrides)
    return base


def detectors_firing(root: Path) -> set[str]:
    return {q["detector"] for q in detector.detect(root, NOW)}


# --------------------------------------------------------------------------- each fires


def test_dangling_source_fires_when_a_cited_path_is_gone(tmp_path: Path) -> None:
    write_log(tmp_path, [event(source_refs=["docs/deleted-yesterday.md"])])
    assert "dangling-source" in detectors_firing(tmp_path)


def test_unreferenced_decision_fires_after_a_week(tmp_path: Path) -> None:
    old = (NOW - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_log(tmp_path, [event(kind="decision", created_at=old, valid_from=old)])
    assert "unreferenced-decision" in detectors_firing(tmp_path)


def test_stale_hypothesis_fires_when_nothing_ever_linked_to_it(tmp_path: Path) -> None:
    old = (NOW - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_log(tmp_path, [event(kind="hypothesis", created_at=old, valid_from=old)])
    assert "stale-hypothesis" in detectors_firing(tmp_path)


def test_cited_superseded_fires_when_an_active_record_leans_on_a_withdrawn_one(tmp_path: Path) -> None:
    write_log(
        tmp_path,
        [
            event(id="PM-20260101-aaaaaaaa"),
            event(
                id="PM-20260101-bbbbbbbb",
                operation="supersede",
                supersedes="PM-20260101-aaaaaaaa",
                supersession_kind="succession",
            ),
            event(
                id="PM-20260101-cccccccc",
                summary="This builds directly on PM-20260101-aaaaaaaa and assumes it holds.",
            ),
        ],
    )
    assert "cited-superseded" in detectors_firing(tmp_path)


def test_unclassified_revision_fires_on_a_v2_supersession_that_does_not_say(tmp_path: Path) -> None:
    write_log(
        tmp_path,
        [
            event(id="PM-20260101-aaaaaaaa"),
            event(
                id="PM-20260101-bbbbbbbb",
                operation="supersede",
                supersedes="PM-20260101-aaaaaaaa",
                supersession_kind="unclassified",
            ),
        ],
    )
    assert "unclassified-revision" in detectors_firing(tmp_path)


# --------------------------------------------------------------------------- each stays quiet


def test_a_resolving_source_is_not_flagged(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "present.md").write_text("here", encoding="utf-8")
    write_log(tmp_path, [event(source_refs=["docs/present.md"])])
    assert "dangling-source" not in detectors_firing(tmp_path)


def test_a_url_source_is_never_treated_as_a_missing_path(tmp_path: Path) -> None:
    write_log(tmp_path, [event(source_refs=["https://example.org/paper", "doi:10.1/x"])])
    assert "dangling-source" not in detectors_firing(tmp_path)


def test_a_referenced_decision_is_not_flagged(tmp_path: Path) -> None:
    old = (NOW - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_log(
        tmp_path,
        [
            event(id="PM-20260101-aaaaaaaa", kind="decision", created_at=old, valid_from=old),
            event(id="PM-20260101-bbbbbbbb", related_ids=["PM-20260101-aaaaaaaa"]),
        ],
    )
    assert "unreferenced-decision" not in detectors_firing(tmp_path)


def test_a_recent_decision_is_not_flagged(tmp_path: Path) -> None:
    recent = (NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_log(tmp_path, [event(kind="decision", created_at=recent, valid_from=recent)])
    assert "unreferenced-decision" not in detectors_firing(tmp_path)


def test_a_classified_revision_is_not_flagged(tmp_path: Path) -> None:
    write_log(
        tmp_path,
        [
            event(id="PM-20260101-aaaaaaaa"),
            event(
                id="PM-20260101-bbbbbbbb",
                operation="supersede",
                supersedes="PM-20260101-aaaaaaaa",
                supersession_kind="correction",
            ),
        ],
    )
    assert "unclassified-revision" not in detectors_firing(tmp_path)


def test_a_successor_is_not_flagged_for_citing_what_it_supersedes(tmp_path: Path) -> None:
    """Superseding a record is the one legitimate reason to name it."""
    write_log(
        tmp_path,
        [
            event(id="PM-20260101-aaaaaaaa"),
            event(
                id="PM-20260101-bbbbbbbb",
                operation="supersede",
                supersedes="PM-20260101-aaaaaaaa",
                supersession_kind="correction",
            ),
        ],
    )
    assert "cited-superseded" not in detectors_firing(tmp_path)


# --------------------------------------------------------------------------- it never writes


def test_detection_never_modifies_the_log(tmp_path: Path) -> None:
    """Stage 1 detects only. Writing would be Stage 2, which is gated."""
    write_log(tmp_path, [event(source_refs=["docs/gone.md"])])
    log = tmp_path / "memory" / "events.jsonl"
    before = log.read_bytes()
    detector.detect(tmp_path, NOW)
    assert log.read_bytes() == before


def test_the_live_corpus_raises_no_question_beyond_the_known_ones() -> None:
    """A new question on the live corpus is either real work or a detector regression.

    The detectors exist to keep asking questions as a log grows, so demanding
    silence from a growing log is not a stable test. The date is pinned so the
    result does not depend on when the suite runs, and the questions already
    raised are listed above so that a new one fails the build while a resolved
    one only shrinks the list.
    """
    raised = {
        (item["detector"], item["memory_id"], item["evidence"])
        for item in detector.detect(ROOT, LIVE_CORPUS_AS_OF)
    }
    assert sorted(raised - KNOWN_OPEN_QUESTIONS) == []
