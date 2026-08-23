"""The CUPMem translation, tested against a double of their return shape.

This cannot test operational fit. Operational fit needs their engine running,
which needs an LLM endpoint, an embedding model on disk and the corpus loaded.
What it tests is that the translation is **total**: every field the contract
requires is either derived from their real return shape or reported absent with
a reason.

The double now lives in `arena_doubles` and quotes their code rather than our
expectations. The previous one was written from the same reading as the adapter
and therefore agreed with it in all five places the adapter was wrong — the
defect that let a run report `admissible: True` while the store was empty.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena_doubles import EngineDouble  # noqa: E402
from arena.adapter import Answer, Cost, Measure, MemoryAdapter, synthetic_fixture, validate_adapter  # noqa: E402
from arena.cupmem_adapter import (  # noqa: E402
    ABSTENTION_CHANNEL, CUPMemAdapter, _abstained, _context_tokens, _evidence_ids,
)


# --------------------------------------------------------------- the translation is total


def test_the_adapter_satisfies_the_protocol() -> None:
    assert isinstance(CUPMemAdapter(EngineDouble()), MemoryAdapter)


def test_it_passes_the_contract_validator() -> None:
    result = validate_adapter(CUPMemAdapter(EngineDouble()), synthetic_fixture())
    assert result["admissible"], result["problems"]


def test_evidence_is_extracted_generically_not_by_their_schema() -> None:
    """A hand-written field map would encode their layout into our arena."""
    ids = _evidence_ids({"state": [{"id": "r1"}, {"nested": {"chunk_id": "c9"}}], "n": 3})
    assert ids == ["r1", "c9"]


def test_evidence_is_deduplicated_in_order() -> None:
    assert _evidence_ids([{"id": "a"}, {"id": "b"}, {"id": "a"}]) == ["a", "b"]


def test_evidence_comes_from_their_real_hit_shape() -> None:
    """Their hits are {source, id, text, payload}; payloads carry `item_id`."""
    adapter = CUPMemAdapter(EngineDouble())
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "billing is at c.internal", "timestamp": "d1"}])
    assert adapter.query("where?").evidence_ids == ["i_00001"]


# ------------------------------------------------------------------------- abstention


def test_abstention_is_read_from_their_answer_not_from_fields_they_lack() -> None:
    """`PremiseVerdict` has no `unknown_current` and `AnswerResult` has no `text`.

    The first adapter looked for both. It therefore never derived abstention
    from anything, and reported `abstained=False` by falling off the end.
    """
    assert _abstained({"answer": {"answer": "", "brief_rationale": ""}}) is True
    assert _abstained({"answer": {"answer": "c.internal", "brief_rationale": ""}}) is False


def test_a_premise_verdict_is_not_an_abstention() -> None:
    """UNRESOLVED judges the question's premise, not the system's willingness."""
    adapter = CUPMemAdapter(EngineDouble(premise_status="UNRESOLVED"))
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    answer = adapter.query("anything?")
    assert answer.abstained is False
    assert answer.system_metadata["premise_status"] == "UNRESOLVED"


def test_abstention_is_none_when_it_cannot_be_derived() -> None:
    """Unknown is not False. The arena must be able to tell them apart."""
    assert _abstained({"parsed_query": {}}) is None


def test_an_underivable_abstention_is_carried_beside_the_boolean() -> None:
    """`abstained` cannot hold three values, so the third is recorded next to it."""
    class NoAnswerKey(EngineDouble):
        def answer_query(self, *, query_label, query_text):
            result = super().answer_query(query_label=query_label, query_text=query_text)
            del result["answer"]
            return result

    adapter = CUPMemAdapter(NoAnswerKey())
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    metadata = adapter.query("anything?").system_metadata
    assert metadata["abstained_raw"] is None
    assert metadata["abstention_derivable"] is False


def test_the_abstention_channel_is_named_not_assumed() -> None:
    adapter = CUPMemAdapter(EngineDouble())
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    assert adapter.query("q?").system_metadata["abstention_channel"] == ABSTENTION_CHANNEL


def test_an_abstaining_engine_reports_no_text() -> None:
    """The validator rejects abstained-with-text, so translation must not produce it."""
    adapter = CUPMemAdapter(EngineDouble(abstain=True))
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    answer = adapter.query("anything?")
    assert answer.abstained and answer.text == ""


# --------------------------------------------------------------------- context tokens


def test_context_tokens_count_text_not_the_serialised_structure() -> None:
    """Two adapters counting different quantities cannot share a column.

    The reference adapter sums whitespace tokens of the record texts it
    delivered. The first CUPMem adapter stringified the whole context dict, so
    braces, scores and bundle wrappers inflated the same column.
    """
    context = {"topk_primary_hits": [{"source": "active", "id": "i_1",
                                      "text": "three word answer",
                                      "payload": {"item_id": "i_1"}}]}
    assert _context_tokens(context) == 3
    assert _context_tokens(context) < len(str(context).split())


def test_a_text_repeated_across_their_views_is_counted_once() -> None:
    """Their context lists one hit under three keys; the reader sees one copy."""
    hit = {"id": "i_1", "text": "three word answer"}
    assert _context_tokens({"a": [hit], "b": [hit], "c": {"primary": hit}}) == 3


# ---------------------------------------------------------------- session translation


def test_records_with_distinct_times_become_distinct_sessions() -> None:
    """Collapsing them keeps the first time and discards the rest.

    That is a loss in the one dimension this system exists to exploit, and it is
    silent: every downstream number still looks plausible.
    """
    engine = EngineDouble()
    adapter = CUPMemAdapter(engine)
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "a", "day": 1},
                    {"id": "r2", "text": "b", "day": 2},
                    {"id": "r3", "text": "c", "day": 9}])
    assert [s["time"] for s in engine.sessions] == ["1", "2", "9"]
    assert [s["index"] for s in engine.sessions] == [0, 1, 2]


def test_records_sharing_a_time_stay_in_one_session() -> None:
    """The native case: one session of turns that share a timestamp."""
    engine = EngineDouble()
    adapter = CUPMemAdapter(engine)
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "a", "timestamp": "2026-01-01"},
                    {"id": "r2", "text": "b", "timestamp": "2026-01-01"}])
    assert len(engine.sessions) == 1 and engine.sessions[0]["turns"] == 2


def test_grouping_never_reorders_what_the_arena_fixed() -> None:
    """Sorting here would hand CUPMem a chronology no other adapter was given."""
    engine = EngineDouble()
    adapter = CUPMemAdapter(engine)
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "a", "day": 9},
                    {"id": "r2", "text": "b", "day": 1}])
    assert [s["time"] for s in engine.sessions] == ["9", "1"]


def test_session_index_increments_across_ingests() -> None:
    """Their writer is per session; ours is per record list. The bridge must count."""
    engine = EngineDouble()
    adapter = CUPMemAdapter(engine)
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "a", "timestamp": "d1"}])
    adapter.ingest([{"id": "r2", "text": "b", "timestamp": "d2"}])
    assert [s["index"] for s in engine.sessions] == [0, 1]


def test_an_ingest_that_stores_nothing_raises_instead_of_returning() -> None:
    """Silent zero-ingest is the defect that made a whole run meaningless.

    Every number downstream of it stayed plausible: three probes answered, zero
    abstentions, `admissible: True` — from an empty store.
    """
    adapter = CUPMemAdapter(EngineDouble())
    adapter.reset()
    with pytest.raises(ValueError, match="zero"):
        adapter.ingest([{"id": "r1", "text": "   ", "timestamp": "d1"}])


def test_an_empty_record_list_is_not_an_error() -> None:
    adapter = CUPMemAdapter(EngineDouble())
    adapter.reset()
    assert isinstance(adapter.ingest([]), Cost)


# ---------------------------------------------------------------------------- cost


def test_cost_is_read_from_their_native_accounting() -> None:
    """`LLMClient.get_usage_summary()` is real; `llm.usage` never was.

    Reporting this system's cost as unobservable understated a competitor on the
    axis this project insists on keeping separate from capability, and forced an
    external instrumentation of the provider client to recover figures CUPMem
    had been reporting all along.
    """
    adapter = CUPMemAdapter(EngineDouble())
    adapter.reset()
    cost = adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    assert cost.model_calls.value == 1
    assert cost.model_calls.observability == "native"
    assert cost.input_tokens.value == 100


def test_query_cost_is_the_delta_not_the_cumulative_total() -> None:
    adapter = CUPMemAdapter(EngineDouble())
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    answer = adapter.query("anything?")
    assert answer.cost.model_calls.value == 2       # the query's own calls
    assert answer.cost.output_tokens.value == 20    # not the ingest's 30


def test_wall_time_is_ours_and_says_so() -> None:
    """They keep a token ledger, not a clock. Claiming native would be a lie."""
    adapter = CUPMemAdapter(EngineDouble())
    adapter.reset()
    cost = adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    assert cost.wall_microseconds.observability == "instrumented"


def test_an_unreportable_cost_is_marked_unmeasured_not_free() -> None:
    """Zero because none, and zero because unmeasurable, are different facts.

    Without this the cheapest system in the table would be the one that cannot
    count, and ignorance of cost would read as an advantage.
    """
    adapter = CUPMemAdapter(EngineDouble(expose_usage=False))
    adapter.reset()
    cost = adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    answer = adapter.query("anything?")

    assert cost.model_calls.value is None
    assert cost.model_calls.observability == "unobservable"
    assert answer.cost.fully_known is False
    assert answer.system_metadata["cost_observability"]["calls"] == "unobservable"


def test_a_reportable_cost_is_marked_measured() -> None:
    adapter = CUPMemAdapter(EngineDouble(expose_usage=True))
    adapter.reset()
    assert adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}]).fully_known is True
    assert adapter.query("anything?").system_metadata["cost_observability"]["calls"] == "native"


def test_a_cached_completion_is_refused_before_it_can_discount_a_run() -> None:
    """Their client bills a cache hit as zero. One warm system is not a comparison.

    Refused at construction rather than caught in the totals, because the
    discount is invisible once it is inside a sum.
    """
    with pytest.raises(ValueError, match="cache_dir"):
        CUPMemAdapter(EngineDouble(cache_dir=Path("/tmp/whatever")))


def test_a_cache_hit_appearing_mid_run_stops_the_run() -> None:
    engine = EngineDouble()
    adapter = CUPMemAdapter(engine)
    adapter.reset()

    class Sneaky(EngineDouble):
        def answer_query(self, *, query_label, query_text):
            self.llm.record(phase="answer_composer", prompt=10, completion=1, cache_hit=True)
            return super().answer_query(query_label=query_label, query_text=query_text)

    sneaky = CUPMemAdapter(Sneaky())
    sneaky.reset()
    sneaky.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    with pytest.raises(ValueError, match="cached completions"):
        sneaky.query("anything?")


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
    measurable = validate_adapter(CUPMemAdapter(EngineDouble()), synthetic_fixture())
    blind = validate_adapter(CUPMemAdapter(EngineDouble(expose_usage=False)),
                             synthetic_fixture())
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
    blind = validate_adapter(CUPMemAdapter(EngineDouble(expose_usage=False)),
                             synthetic_fixture())
    assert blind["cost_fully_known"] is False
    assert blind["admissible"], blind["problems"]


# --------------------------------------------------------------------------- reset


def test_reset_clears_their_state_too() -> None:
    engine = EngineDouble()
    adapter = CUPMemAdapter(engine)
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    adapter.reset()
    assert engine.store.items == []
    assert adapter.query("anything?").evidence_ids == []


def test_reset_clears_their_usage_ledger_too() -> None:
    """Otherwise the first operation after a reset is billed for the last arm."""
    adapter = CUPMemAdapter(EngineDouble())
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    adapter.reset()
    assert adapter.ingest([{"id": "r2", "text": "two", "timestamp": "d2"}]).model_calls.value == 1


# ------------------------------------------------------------------ interpretation


def test_the_adapter_never_emits_a_failure_type() -> None:
    """Interpretation belongs to the harness. An adapter grading itself is void."""
    adapter = CUPMemAdapter(EngineDouble())
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    answer = adapter.query("anything?")
    forbidden = {"failure_type", "failure_stage", "success", "correct"}
    assert not (forbidden & set(answer.system_metadata))


def test_their_verdict_is_passed_through_unconverted() -> None:
    adapter = CUPMemAdapter(EngineDouble(premise_status="OUTDATED"))
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "d1"}])
    verdict = adapter.query("anything?").system_metadata["verdict"]
    assert verdict["status"] == "OUTDATED"
    assert verdict["old_premise_safe"] is True
