"""Retrieval measured against the corpus's own gold, and the cases it refuses.

The pilot could not ask whether a system retrieved the right session, because
every system's evidence ids live in its own space. Session date is the one key
both the corpus and the systems carry, and these tests pin what it can and
cannot support.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.retrieval_truth import UNOBSERVABLE, canonical_time, measure  # noqa: E402

UNIT = {
    "haystack_session_ids": ["s0", "s1", "s2"],
    "haystack_dates": ["2022/09/01 (Thu) 00:10", "2022/09/05 (Mon) 12:00",
                       "2022/09/09 (Fri) 08:30"],
    "answer_session_ids": ["s1"],
}


def test_three_spellings_of_one_moment_land_on_one_key() -> None:
    """The corpus, Hindsight and Mem0 each write it differently."""
    corpus = canonical_time("2022/09/01 (Thu) 00:10")
    hindsight = canonical_time("2022-09-01T00:10:00+00:00")
    assert corpus == hindsight == "2022-09-01T00:10:00"


def test_an_unreadable_date_is_none_rather_than_a_guess() -> None:
    assert canonical_time("last Tuesday") is None
    assert canonical_time("") is None


def test_gold_retrieved_first_ranks_one() -> None:
    result = measure(UNIT, ["2022/09/05 (Mon) 12:00", "2022/09/01 (Thu) 00:10"])
    assert result["gold_in_context"] is True
    assert result["gold_rank"] == 1
    assert result["precision_at_k"] == 0.5


def test_gold_retrieved_late_ranks_late() -> None:
    result = measure(UNIT, ["2022/09/01 (Thu) 00:10", "2022/09/09 (Fri) 08:30",
                            "2022/09/05 (Mon) 12:00"])
    assert result["gold_rank"] == 3
    assert result["gold_hits"] == 1


def test_gold_never_retrieved_has_no_rank_rather_than_rank_zero() -> None:
    """Rank zero would read as 'found it first'. None is the honest value."""
    result = measure(UNIT, ["2022/09/01 (Thu) 00:10", "2022/09/09 (Fri) 08:30"])
    assert result["gold_in_context"] is False
    assert result["gold_rank"] is None
    assert result["precision_at_k"] == 0.0


def test_evidence_whose_date_matches_nothing_is_counted_as_unmapped() -> None:
    """Unmapped is a number, not a silent drop: it bounds how much was measured."""
    result = measure(UNIT, ["2022/09/05 (Mon) 12:00", "1999-01-01"])
    assert result["evidence_mapped"] == 1
    assert result["evidence_unmapped"] == 1


def test_a_unit_with_repeated_dates_is_unobservable_not_approximated() -> None:
    """One date naming two sessions cannot support the mapping at all."""
    unit = dict(UNIT, haystack_dates=["2022/09/01 (Thu) 00:10",
                                      "2022/09/01 (Thu) 00:10",
                                      "2022/09/09 (Fri) 08:30"])
    result = measure(unit, ["2022/09/01 (Thu) 00:10"])
    assert result["observable"] is False
    assert result["gold_in_context"] == UNOBSERVABLE
    assert result["gold_rank"] == UNOBSERVABLE


def test_retrieving_nothing_is_not_the_same_as_retrieving_wrongly() -> None:
    result = measure(UNIT, [])
    assert result["retrieved"] == 0
    assert result["gold_in_context"] is False
    assert result["precision_at_k"] is None


def test_staleness_is_unobservable_everywhere_and_says_why() -> None:
    """The corpus marks answer sessions, not superseded ones."""
    result = measure(UNIT, ["2022/09/05 (Mon) 12:00"])
    assert result["stale_or_conflicting"] == UNOBSERVABLE
    assert "superseded" in result["stale_why"]
