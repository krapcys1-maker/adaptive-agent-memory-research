"""Deterministic tests for CURRENT_STATE_OVER_HISTORY (Mechanism B). No LLM
call, no network -- pure function tests against the 12 preregistered probes'
fact shapes (data/lab/arena/mechanism-b-state-supersession-v1/
preregistration.json).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.state_supersession import current_state_over_history, detect_state_key  # noqa: E402


def test_clean_supersession_latest_wins_as_current() -> None:
    ctx = ["Started a new job at Microsoft", "Left Microsoft and started working at Google"]
    times = ["2023-01-15", "2023-06-20"]
    rendered, trace = current_state_over_history(ctx, times)
    assert rendered == [
        "Current state:",
        "[2023-06-20] Left Microsoft and started working at Google",
        "History (superseded):",
        "[2023-01-15] Started a new job at Microsoft (superseded by a later update)",
    ]
    assert trace["groups"]["EMPLOYER"]["action"] == "current_history_split"
    assert trace["groups"]["EMPLOYER"]["current_index"] == 1
    assert trace["inert"] is False


def test_return_regime_third_occurrence_wins() -> None:
    ctx = ["Started working at Acme Corp", "Left Acme Corp for a role at Globex",
           "Rejoined Acme Corp"]
    times = ["2022-02-01", "2022-11-15", "2023-08-01"]
    rendered, trace = current_state_over_history(ctx, times)
    assert rendered[0] == "Current state:"
    assert "Rejoined Acme Corp" in rendered[1]
    assert trace["groups"]["EMPLOYER"]["current_index"] == 2
    assert set(trace["groups"]["EMPLOYER"]["history_indices"]) == {0, 1}


def test_r4_control_two_pets_never_collapsed() -> None:
    """The adversarial control: two distinct entities sharing surface vocabulary
    must NOT be treated as one superseded state key."""
    ctx = ["Adopted a cat named Whiskers", "Adopted a second cat named Luna"]
    rendered, trace = current_state_over_history(ctx, ["2022-04-01", "2023-02-10"])
    assert rendered == ctx  # byte-identical to BASE -- nothing grouped
    assert trace["inert"] is True
    assert trace["groups"]["PET:Whiskers"]["action"] == "single_item_passthrough"
    assert trace["groups"]["PET:Luna"]["action"] == "single_item_passthrough"


def test_r4_control_two_languages_never_collapsed() -> None:
    ctx = ["I'm learning Spanish", "I also started learning Japanese"]
    rendered, trace = current_state_over_history(ctx, ["2022-06-01", "2023-03-15"])
    assert rendered == ctx
    assert trace["inert"] is True


def test_r4_control_home_vs_work_address_never_collapsed() -> None:
    ctx = ["My home address is 12 Oak Street", "My work address is 500 Market Street"]
    rendered, trace = current_state_over_history(ctx, ["2022-05-01", "2023-01-01"])
    assert rendered == ctx
    assert trace["inert"] is True


def test_zero_key_matches_is_byte_identical_to_base() -> None:
    ctx = ["I like pizza", "The sky is blue"]
    rendered, trace = current_state_over_history(ctx, ["2022-01-01", "2022-01-02"])
    assert rendered == ctx
    assert trace["inert"] is True
    assert trace["zero_match"] is True


def test_timestamp_tie_falls_back_to_base_equivalent_no_guessing() -> None:
    ctx = ["Started a new job at Microsoft", "Left Microsoft and started working at Google"]
    rendered, trace = current_state_over_history(ctx, ["2023-06-20", "2023-06-20"])
    assert rendered == ctx
    assert trace["inert"] is True
    assert "EMPLOYER" in trace["ties"]


def test_missing_timestamp_falls_back_to_base_equivalent() -> None:
    ctx = ["Started a new job at Microsoft", "Left Microsoft and started working at Google"]
    rendered, trace = current_state_over_history(ctx, ["2023-01-15", ""])
    assert rendered == ctx
    assert trace["inert"] is True


def test_unmatched_items_interleave_before_the_two_blocks() -> None:
    ctx = ["Likes hiking on weekends", "Started a new job at Microsoft",
           "Left Microsoft and started working at Google"]
    times = ["2022-01-01", "2023-01-15", "2023-06-20"]
    rendered, _ = current_state_over_history(ctx, times)
    assert rendered[0] == "Likes hiking on weekends"
    assert rendered[1] == "Current state:"


def test_revocation_negation_still_groups_under_gym_key() -> None:
    ctx = ["Signed up for a gym membership at PowerFit",
           "Canceled my PowerFit gym membership"]
    times = ["2022-05-01", "2023-04-18"]
    rendered, trace = current_state_over_history(ctx, times)
    assert rendered[0] == "Current state:"
    assert "Canceled" in rendered[1]
    assert trace["groups"]["GYM_MEMBERSHIP:PowerFit"]["action"] == "current_history_split"


def test_detect_state_key_none_for_unrelated_text() -> None:
    assert detect_state_key("I like pizza") is None
