"""A unit whose own haystack dates are ambiguous is UNOBSERVABLE, not FAIL.

The defect this pins, measured rather than imagined: stage2_build_and_audit.py's
contamination check compared `gold_state(...).get("foreign_from_other_units")
== 0`. When a unit's own `session_map()` returns None (its haystack dates do
not uniquely identify sessions -- the same condition documented throughout
this project for 69fee5aa), `gold_state()` returns the UNOBSERVABLE branch,
which carries no `foreign_from_other_units` key at all. `None == 0` is False,
so the check flagged two genuinely-clean, merely-unobservable fresh Stage 2
units (0977f2af, 0bb5a684) as contamination failures and stopped the run.

No provider call in this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.stage2_build_and_audit import contamination_status, gold_state  # noqa: E402


def test_unobservable_unit_is_not_a_contamination_failure() -> None:
    """A unit with non-unique own haystack dates must read UNOBSERVABLE, not FAIL."""
    row = {
        "haystack_dates": ["2023-01-01", "2023-01-01"],  # duplicate -> session_map() is None
        "haystack_session_ids": ["s0", "s1"], "answer_session_ids": ["s0"],
    }
    gs = gold_state(row, ["2023-01-01"])
    assert gs["observable"] is False
    assert gs["gold_in_context"] == "UNOBSERVABLE"
    # The old, buggy check compared this key with == 0. It must not exist as a
    # number at all when the unit is unobservable, so a caller cannot silently
    # treat missing-and-ambiguous as clean.
    assert "foreign_from_other_units" not in gs


def test_observable_unit_with_no_foreign_evidence_passes() -> None:
    row = {
        "haystack_dates": ["2023-01-01", "2023-01-02"],
        "haystack_session_ids": ["s0", "s1"], "answer_session_ids": ["s0"],
    }
    gs = gold_state(row, ["2023-01-01", "2023-01-02"])
    assert gs["observable"] is True
    assert gs["foreign_from_other_units"] == 0


def test_observable_unit_with_foreign_evidence_is_flagged() -> None:
    row = {
        "haystack_dates": ["2023-01-01", "2023-01-02"],
        "haystack_session_ids": ["s0", "s1"], "answer_session_ids": ["s0"],
    }
    gs = gold_state(row, ["2023-01-01", "2099-12-31"])  # a date outside this unit's own haystack
    assert gs["observable"] is True
    assert gs["foreign_from_other_units"] == 1


def test_contamination_status_distinguishes_unobservable_from_fail() -> None:
    """The actual regression: `gs.get(...) == 0` on a missing key silently read as failure."""
    unobservable_row = {"haystack_dates": ["2023-01-01", "2023-01-01"],
                        "haystack_session_ids": ["s0", "s1"], "answer_session_ids": ["s0"]}
    clean_row = {"haystack_dates": ["2023-01-01", "2023-01-02"],
                "haystack_session_ids": ["s0", "s1"], "answer_session_ids": ["s0"]}
    contaminated_row = clean_row

    assert contamination_status(gold_state(unobservable_row, ["2023-01-01"])) == "UNOBSERVABLE"
    assert contamination_status(gold_state(clean_row, ["2023-01-01", "2023-01-02"])) == "PASS"
    assert contamination_status(gold_state(contaminated_row, ["2023-01-01", "2099-12-31"])) == "FAIL"
