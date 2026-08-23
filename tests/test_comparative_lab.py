"""The comparison must refuse bad input and must never invent a correlation.

Three things would silently void this track, and each has a test.

**Runs produced under different conditions.** Two deltas measured at different
token budgets are not on the same scale, and adding them means nothing.

**A constant vector reported as zero correlation.** PMLAB-DECORR-E1 closed
because two roles of one model produced constant error vectors. Architectural
difference does not guarantee variance either — a system that never commits a
failure type still yields a constant vector, and phi does not exist for it.

**An interaction read by eye.** "+6 and +8 giving +14" is additive and "+17" is
synergy, but only a formula says so consistently.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import comparative_lab as lab  # noqa: E402


def _contract(**overrides):
    base = {f: "same" for f in lab.CONTRACT}
    base["token_budget"] = 250
    base.update(overrides)
    return base


def _run(system, outcomes, **contract):
    return {
        "system": system,
        "contract": _contract(**contract),
        "records": [
            {"probe_id": f"p{i}", "system": system, "success": ok,
             "abstained": False, "failure_stage": "none" if ok else stage,
             "failure_type": None if ok else ftype, "retrieved_tokens": 100}
            for i, (ok, stage, ftype) in enumerate(outcomes)
        ],
    }


# --------------------------------------------------------------- the contract is enforced


def test_differing_token_budgets_are_refused() -> None:
    runs = {"A": _run("A", [(True, "", "")] * 3),
            "B": _run("B", [(True, "", "")] * 3, token_budget=500)}
    with pytest.raises(SystemExit, match="token_budget"):
        lab.validate(runs)


def test_a_missing_contract_field_is_refused() -> None:
    runs = {"A": _run("A", [(True, "", "")] * 3), "B": _run("B", [(True, "", "")] * 3)}
    del runs["B"]["contract"]["judge"]
    with pytest.raises(SystemExit, match="judge"):
        lab.validate(runs)


def test_a_different_probe_set_is_refused() -> None:
    runs = {"A": _run("A", [(True, "", "")] * 4), "B": _run("B", [(True, "", "")] * 3)}
    with pytest.raises(SystemExit, match="different probe set"):
        lab.validate(runs)


def test_a_record_missing_a_required_field_is_refused() -> None:
    runs = {"A": _run("A", [(True, "", "")] * 3), "B": _run("B", [(True, "", "")] * 3)}
    del runs["B"]["records"][0]["retrieved_tokens"]
    with pytest.raises(SystemExit, match="retrieved_tokens"):
        lab.validate(runs)


def test_matching_runs_are_accepted() -> None:
    lab.validate({"A": _run("A", [(True, "", "")] * 3), "B": _run("B", [(True, "", "")] * 3)})


# --------------------------------------------------------------- phi never invents a number


def test_a_constant_vector_yields_undefined_not_zero() -> None:
    assert lab.phi([0, 0, 0, 0], [0, 1, 0, 1]) is None
    assert lab.phi([1, 1, 1, 1], [0, 1, 0, 1]) is None


def test_identical_error_vectors_correlate_perfectly() -> None:
    assert lab.phi([1, 0, 1, 0], [1, 0, 1, 0]) == pytest.approx(1.0)


def test_opposite_error_vectors_correlate_negatively() -> None:
    assert lab.phi([1, 0, 1, 0], [0, 1, 0, 1]) == pytest.approx(-1.0)


def test_a_failure_type_no_system_commits_is_reported_undefined() -> None:
    """The case architectural difference does not rule out."""
    runs = {
        "A": _run("A", [(False, "retrieval", "retrieval_failure")] * 4),
        "B": _run("B", [(False, "retrieval", "retrieval_failure")] * 4),
    }
    lab.validate(runs)
    report = lab.correlate(runs)
    cell = report["pairs"]["A vs B"]["by_failure_type"]["conflict_failure"]
    assert cell["phi"] is None
    assert "constant" in cell["undefined_because"]


def test_systems_can_share_an_error_rate_and_diverge_by_type() -> None:
    """The reason failure types get their own vectors instead of one number."""
    runs = {
        "A": _run("A", [(False, "address", "address_failure"),
                        (False, "address", "address_failure"),
                        (True, "", ""), (True, "", "")]),
        "B": _run("B", [(False, "state", "state_failure"),
                        (False, "state", "state_failure"),
                        (True, "", ""), (True, "", "")]),
    }
    lab.validate(runs)
    pair = lab.correlate(runs)["pairs"]["A vs B"]
    assert pair["phi_any_failure"] == pytest.approx(1.0)
    assert pair["by_failure_type"]["address_failure"]["phi"] is None
    assert pair["by_failure_type"]["state_failure"]["phi"] is None


# --------------------------------------------------------------- the interaction term


@pytest.mark.parametrize("sab,expected", [
    (0.14, "additive"), (0.08, "redundant"), (0.17, "synergistic"),
])
def test_the_interaction_term_reads_the_three_cases(sab: float, expected: str) -> None:
    result = lab.interaction(s0=0.0, sa=0.06, sb=0.08, sab=sab)
    assert expected in result["reading"]


def test_the_interaction_is_the_formula_not_an_impression() -> None:
    result = lab.interaction(s0=0.50, sa=0.56, sb=0.58, sab=0.67)
    assert result["delta_a"] == pytest.approx(0.06)
    assert result["delta_b"] == pytest.approx(0.08)
    assert result["interaction"] == pytest.approx(0.03)
