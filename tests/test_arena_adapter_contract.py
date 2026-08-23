"""The adapter contract must reject a non-conforming system before it costs anything.

Rejecting an adapter here is free. Discovering it mid-run costs the run, and on
an arena with five systems, paid ingestion and an external benchmark, that is the
expensive failure this file exists to prevent.

The contract's one rule is that an adapter reports raw signals and never
interprets them. If each adapter decided what counts as a retrieval failure, the
failure-type matrix would be an artefact of five different opinions rather than a
measurement.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.adapter import Answer, Cost, Measure, MemoryAdapter, synthetic_fixture, validate_adapter  # noqa: E402
from arena.aamr_adapter import AAMRAdapter  # noqa: E402


class _Conforming:
    name = "conforming"

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.records = []

    def ingest(self, records):
        self.records = list(records)
        return Cost(Measure(len(records)), Measure(10 * len(records)))

    def query(self, question, asked_at=None):
        if not self.records:
            return Answer(text="", abstained=True)
        first = self.records[0]
        return Answer(text=first["text"], evidence_ids=[first["id"]],
                      context_tokens=len(first["text"].split()))


# --------------------------------------------------------------- the contract admits


def test_a_conforming_adapter_is_admissible() -> None:
    result = validate_adapter(_Conforming(), synthetic_fixture())
    assert result["admissible"], result["problems"]
    assert result["probes_answered"] == 3


def test_the_reference_adapter_is_admissible() -> None:
    """A contract nobody has implemented is a wish."""
    assert validate_adapter(AAMRAdapter(), synthetic_fixture())["admissible"]


def test_admissible_does_not_mean_good() -> None:
    """The reference adapter obeys the contract and abstains on everything.

    That separation is the point: CANDIDATE-0's language-to-address bridge does
    not transfer, and the arena must be able to admit a system in order to
    measure it failing.
    """
    result = validate_adapter(AAMRAdapter(), synthetic_fixture())
    assert result["admissible"]
    assert result["abstentions"] == 3


# --------------------------------------------------------------- and the contract rejects


def test_a_missing_method_is_rejected() -> None:
    class NoQuery:
        name = "broken"
        def reset(self): pass
        def ingest(self, records): return Cost()

    result = validate_adapter(NoQuery(), synthetic_fixture())
    assert not result["admissible"]
    assert any("query" in p for p in result["problems"])


def test_an_unnamed_adapter_is_rejected() -> None:
    class Anonymous(_Conforming):
        name = ""

    assert not validate_adapter(Anonymous(), synthetic_fixture())["admissible"]


def test_ingest_not_returning_a_cost_is_rejected() -> None:
    """Cost is part of the mechanism, not hidden data preparation."""
    class NoCost(_Conforming):
        def ingest(self, records):
            return None

    result = validate_adapter(NoCost(), synthetic_fixture())
    assert not result["admissible"]
    assert any("Cost" in p for p in result["problems"])


def test_abstaining_while_also_answering_is_rejected() -> None:
    """The harness cannot score both; the adapter must commit to one."""
    class Both(_Conforming):
        def query(self, question, asked_at=None):
            return Answer(text="an answer", abstained=True)

    result = validate_adapter(Both(), synthetic_fixture())
    assert not result["admissible"]
    assert any("abstained" in p for p in result["problems"])


def test_a_reset_that_does_not_reset_is_rejected() -> None:
    """State surviving reset makes every arm depend on the order the arena ran."""
    class Sticky(_Conforming):
        def reset(self):
            pass  # keeps its records

    result = validate_adapter(Sticky(), synthetic_fixture())
    assert not result["admissible"]
    assert any("reset" in p for p in result["problems"])


def test_negative_context_tokens_are_rejected() -> None:
    class Negative(_Conforming):
        def query(self, question, asked_at=None):
            return Answer(text="x", context_tokens=-1)

    assert not validate_adapter(Negative(), synthetic_fixture())["admissible"]


# --------------------------------------------------------------- cost accounting


def test_costs_add_per_field() -> None:
    total = (Cost(Measure(1), Measure(10), Measure(2), Measure(500_000))
             + Cost(Measure(2), Measure(20), Measure(3), Measure(250_000)))
    assert (total.model_calls.value, total.input_tokens.value,
            total.output_tokens.value) == (3, 30, 5)
    assert total.wall_microseconds.value == 750_000
    assert total.fully_known and not total.is_lower_bound


def test_a_zero_cost_is_a_claim_not_a_default() -> None:
    """The reference adapter calls no model, so its zero is measured, not absent.

    "native" here is the whole point: a system reporting zero because it makes
    no calls and one reporting zero because it cannot count must not look alike.
    """
    result = validate_adapter(AAMRAdapter(), synthetic_fixture())
    assert result["ingest_cost"]["model_calls"]["value"] == 0
    assert result["ingest_cost"]["model_calls"]["observability"] == "native"
    assert result["cost_fully_known"] is True


# --------------------------------------------------------------- the fixture is honest


def test_the_fixture_exercises_what_the_contract_cares_about() -> None:
    fixture = synthetic_fixture()
    purposes = " ".join(fixture["what_each_probe_is_for"].values())
    assert "supersession" in purposes
    assert "literal" in purposes
    assert "no answer exists" in purposes


def test_the_fixture_contains_a_probe_with_no_answer() -> None:
    """A system that answers it confidently is wrong, and must be catchable."""
    fixture = synthetic_fixture()
    subjects = " ".join(r["text"] for r in fixture["records"]).lower()
    unanswerable = fixture["probes"][2]["question"].lower()
    assert "roster" in unanswerable and "roster" not in subjects


def test_the_protocol_is_structural_not_nominal() -> None:
    assert isinstance(AAMRAdapter(), MemoryAdapter)
    assert isinstance(_Conforming(), MemoryAdapter)
