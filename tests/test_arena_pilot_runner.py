"""The pilot runner's pure parts: what it hands the system, and what it claims.

The paid loop cannot be tested here. What can be tested is the translation into
arena records and the honesty of the correctness proxy, both of which decide what
the artefact means.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.run_arena_pilot import as_records, crude_match  # noqa: E402

SESSION = [
    {"role": "user", "content": "I moved to Lisbon in March."},
    {"role": "assistant", "content": "That is a big change."},
    {"role": "user", "content": "  "},
    {"role": "user", "content": "The flat is near Alfama."},
]


def test_only_user_turns_become_records() -> None:
    """Their chunker drops the rest silently, so the adapter must not send them.

    An adapter that hands over turns it knows will vanish is reporting an ingest
    it did not make — the defect that let a whole run measure an empty store.
    """
    records = as_records(SESSION, "2023-03-04", 7)
    assert [r["text"] for r in records] == ["I moved to Lisbon in March.",
                                            "The flat is near Alfama."]


def test_every_record_of_a_session_carries_that_session_date() -> None:
    """One session, one time. The adapter groups on it, so it must be the same."""
    records = as_records(SESSION, "2023-03-04", 7)
    assert {r["timestamp"] for r in records} == {"2023-03-04"}


def test_record_ids_locate_a_turn_within_a_session() -> None:
    records = as_records(SESSION, "2023-03-04", 7)
    assert [r["id"] for r in records] == ["s7_t0", "s7_t3"]


def test_a_session_with_no_date_falls_back_to_its_index() -> None:
    """A blank time would collapse every dateless session into one group."""
    records = as_records(SESSION, "", 7)
    assert {r["timestamp"] for r in records} == {"7"}


def test_a_session_of_only_assistant_turns_yields_nothing() -> None:
    """The caller skips it rather than calling ingest, which would raise."""
    assert as_records([{"role": "assistant", "content": "hello"}], "d", 0) == []


def test_the_correctness_proxy_is_containment_and_nothing_cleverer() -> None:
    assert crude_match("The answer is Lisbon, I believe.", "Lisbon") is True
    assert crude_match("The answer is Porto.", "Lisbon") is False


def test_the_proxy_undercounts_a_correct_paraphrase() -> None:
    """Stated as a test because any number derived from it must carry the caveat.

    LongMemEval's own metric is a model judge. This is not that, and a pilot that
    quietly reported the proxy as accuracy would be overclaiming by construction.
    """
    assert crude_match("They relocated to the Portuguese capital.", "Lisbon") is False


def test_no_gold_is_unknown_rather_than_wrong() -> None:
    assert crude_match("anything", "") is None


def test_the_committed_artefact_carries_no_corpus_text() -> None:
    """Question text, gold answers and composed answers go to an ignored sibling.

    Checked against the real artefact when one exists, because the rule is about
    what actually reaches git, not about what the writer intended.
    """
    artefact = ROOT / "data/lab/arena/pilot-cupmem.json"
    # Skipped, never silently passed. A check that reports success when its
    # subject is absent is worse than no check.
    if not artefact.exists():
        pytest.skip("no pilot artefact yet")
    record = json.loads(artefact.read_text(encoding="utf-8"))
    forbidden = {"question", "answer", "gold", "answer_text", "haystack_sessions"}
    for unit in record.get("units", []):
        assert not (forbidden & set(unit)), unit.get("question_id")


def test_the_artefact_says_it_is_not_a_leaderboard() -> None:
    artefact = ROOT / "data/lab/arena/pilot-cupmem.json"
    if not artefact.exists():
        pytest.skip("no pilot artefact yet")
    record = json.loads(artefact.read_text(encoding="utf-8"))
    assert "not_a_leaderboard" in record
    assert record["contract_version"] == "ARENA-0.1"
