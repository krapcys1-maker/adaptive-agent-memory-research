"""The CUPMem translation, tested against a double of their return shape.

This cannot test operational fit. Operational fit needs their engine running,
which needs an LLM endpoint, an embedding model on disk and the corpus loaded.
What it tests is that the translation is **total**: every field the contract
requires is either derived from their documented return shape or reported
absent with a reason.

The distinction is the registered two-level one. Structural fit passed by
reading their surface. This is the translation existing. Operational fit remains
untested and is not claimed anywhere.

The engine double returns the shape `answer_query` actually returns, taken from
`query/engine.py`: a dict with `answer`, `relevant_context`, `verdict`,
`parsed_query` and the rest.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.adapter import Answer, Cost, Measure, MemoryAdapter, synthetic_fixture, validate_adapter  # noqa: E402
from arena.cupmem_adapter import CUPMemAdapter, _abstained, _evidence_ids  # noqa: E402


class _Usage:
    def __init__(self) -> None:
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0


class _LLM:
    def __init__(self) -> None:
        self.usage = _Usage()

    def reset_usage_tracking(self) -> None:
        self.usage = _Usage()


class _EngineDouble:
    """Returns the shape query/engine.py returns, and nothing invented."""

    def __init__(self, *, abstain: bool = False, expose_usage: bool = True) -> None:
        self.llm = _LLM() if expose_usage else None
        self.sessions: list[list[dict[str, Any]]] = []
        self._abstain = abstain

    def reset(self) -> None:
        self.sessions = []

    def write_session(self, *, session, session_index, session_time):
        self.sessions.append(session)
        if self.llm:
            self.llm.usage.calls += 1
            self.llm.usage.prompt_tokens += 100
        return {"session_index": session_index, "session_time": session_time}

    def answer_query(self, *, query_label, query_text):
        if self.llm:
            self.llm.usage.calls += 2
            self.llm.usage.prompt_tokens += 50
            self.llm.usage.completion_tokens += 20
        records = [r for s in self.sessions for r in s]
        return {
            "query_label": query_label, "query_text": query_text,
            "parsed_query": {"intent": "current_state"},
            "relevant_context": {"state": [{"id": r["id"], "text": r["text"]} for r in records]},
            "verdict": {"unknown_current": self._abstain},
            "answer": {"text": "" if self._abstain else (records[-1]["text"] if records else "")},
        }


# --------------------------------------------------------------- the translation is total


def test_the_adapter_satisfies_the_protocol() -> None:
    assert isinstance(CUPMemAdapter(_EngineDouble()), MemoryAdapter)


def test_it_passes_the_contract_validator() -> None:
    result = validate_adapter(CUPMemAdapter(_EngineDouble()), synthetic_fixture())
    assert result["admissible"], result["problems"]


def test_evidence_is_extracted_generically_not_by_their_schema() -> None:
    """A hand-written field map would encode their layout into our arena."""
    ids = _evidence_ids({"state": [{"id": "r1"}, {"nested": {"chunk_id": "c9"}}], "n": 3})
    assert ids == ["r1", "c9"]


def test_evidence_is_deduplicated_in_order() -> None:
    assert _evidence_ids([{"id": "a"}, {"id": "b"}, {"id": "a"}]) == ["a", "b"]


def test_abstention_comes_from_their_verdict_not_from_our_inference() -> None:
    assert _abstained({"verdict": {"unknown_current": True}}) is True
    assert _abstained({"verdict": {"unknown_current": False}}) is False


def test_abstention_is_none_when_it_cannot_be_derived() -> None:
    """Unknown is not False. The arena must be able to tell them apart."""
    assert _abstained({"parsed_query": {}}) is None


def test_query_cost_is_the_delta_not_the_cumulative_total() -> None:
    adapter = CUPMemAdapter(_EngineDouble())
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    answer = adapter.query("anything?")
    assert answer.cost.model_calls.value == 2       # the query's own calls
    assert answer.cost.output_tokens.value == 20    # not the ingest's 100 input


def test_ingest_cost_reports_their_model_calls() -> None:
    adapter = CUPMemAdapter(_EngineDouble())
    adapter.reset()
    cost = adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    assert cost.model_calls.value == 1
    assert cost.input_tokens.value == 100


def test_an_unreportable_cost_is_marked_unmeasured_not_free() -> None:
    """Zero because none, and zero because unmeasurable, are different facts.

    Without this the cheapest system in the table would be the one that cannot
    count, and ignorance of cost would read as an advantage.
    """
    adapter = CUPMemAdapter(_EngineDouble(expose_usage=False))
    adapter.reset()
    cost = adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    answer = adapter.query("anything?")

    assert cost.model_calls.value is None
    assert cost.model_calls.observability == "unobservable"
    assert answer.cost.fully_known is False
    assert answer.system_metadata["cost_observability"]["calls"] == "unobservable"


def test_a_reportable_cost_is_marked_measured() -> None:
    adapter = CUPMemAdapter(_EngineDouble(expose_usage=True))
    adapter.reset()
    assert adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}]).fully_known is True
    assert adapter.query("anything?").system_metadata["cost_observability"]["calls"] == "native"


def test_a_measured_part_plus_an_unmeasurable_one_is_a_floor_not_a_rejection() -> None:
    """The contradiction a single boolean produced, and why it is gone.

    A measured ingest plus an unmeasurable query is neither inconsistent nor
    zero. It is "at least twelve calls, total unknown", and the twelve was
    really measured. A single flag forced a choice between rejecting the sum
    and discarding the twelve.
    """
    measured = Cost(Measure(12), Measure(40000), Measure(500), Measure(1_800_000))
    blind = Cost(Measure(None, "unobservable"), Measure(None, "unobservable"),
                 Measure(None, "unobservable"), Measure(400_000, "instrumented"))
    total = measured + blind

    assert total.model_calls.value == 12
    assert total.model_calls.lower_bound is True
    assert total.fully_known is False
    assert total.is_lower_bound is True


def test_two_fully_measured_costs_sum_to_a_total_not_a_floor() -> None:
    measured = Cost(Measure(12), Measure(40000), Measure(500), Measure(1_800_000))
    assert (measured + measured).fully_known is True
    assert (measured + measured).is_lower_bound is False


def test_a_system_may_know_its_calls_and_not_its_tokens() -> None:
    """One flag over the whole Cost would hide a figure the system does have."""
    partial = Cost(Measure(17, "native"), Measure(None, "unobservable"))
    assert partial.model_calls.value == 17
    assert partial.input_tokens.value is None
    assert partial.fully_known is False


def test_the_validator_reports_whether_cost_was_measured_at_all() -> None:
    measurable = validate_adapter(CUPMemAdapter(_EngineDouble()), synthetic_fixture())
    blind = validate_adapter(CUPMemAdapter(_EngineDouble(expose_usage=False)), synthetic_fixture())
    assert measurable["cost_fully_known"] is True
    assert blind["cost_fully_known"] is False
    # Both still obey the contract: being unable to report cost is a property to
    # record, not grounds for exclusion from the arena.
    assert measurable["admissible"] and blind["admissible"]


def test_an_observability_outside_the_vocabulary_is_rejected() -> None:
    class Nonsense:
        name = "nonsense"
        def reset(self): pass
        def ingest(self, records): return Cost(Measure(5, "probably"))
        def query(self, question, asked_at=None): return Answer(text="x")

    result = validate_adapter(Nonsense(), synthetic_fixture())
    assert not result["admissible"]
    assert any("observability" in p for p in result["problems"])


def test_being_unable_to_report_cost_is_recorded_not_disqualifying() -> None:
    blind = validate_adapter(CUPMemAdapter(_EngineDouble(expose_usage=False)),
                             synthetic_fixture())
    assert blind["cost_fully_known"] is False
    assert blind["admissible"], blind["problems"]


def test_an_abstaining_engine_reports_no_text() -> None:
    """The validator rejects abstained-with-text, so translation must not produce it."""
    adapter = CUPMemAdapter(_EngineDouble(abstain=True))
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    answer = adapter.query("anything?")
    assert answer.abstained and answer.text == ""


def test_reset_clears_their_state_too() -> None:
    engine = _EngineDouble()
    adapter = CUPMemAdapter(engine)
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    adapter.reset()
    assert engine.sessions == []
    assert adapter.query("anything?").evidence_ids == []


def test_session_index_increments_across_ingests() -> None:
    """Their writer is per session; ours is per record list. The bridge must count."""
    engine = _EngineDouble()
    adapter = CUPMemAdapter(engine)
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "a", "timestamp": "d1"}])
    adapter.ingest([{"id": "r2", "text": "b", "timestamp": "d2"}])
    assert len(engine.sessions) == 2


def test_the_adapter_never_emits_a_failure_type() -> None:
    """Interpretation belongs to the harness. An adapter grading itself is void."""
    adapter = CUPMemAdapter(_EngineDouble())
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    answer = adapter.query("anything?")
    forbidden = {"failure_type", "failure_stage", "success", "correct"}
    assert not (forbidden & set(answer.system_metadata))


def test_their_verdict_is_passed_through_unconverted() -> None:
    adapter = CUPMemAdapter(_EngineDouble(abstain=True))
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    verdict = adapter.query("anything?").system_metadata["verdict"]
    assert verdict == {"unknown_current": True}
