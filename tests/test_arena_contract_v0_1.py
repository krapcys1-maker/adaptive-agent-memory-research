"""ARENA-0.1: the amendment, and proof that it is the only thing that changed.

The defect being repaired is specific. ARENA-0 decided whether querying mutates
memory by comparing two answers, so its `read_only` silently meant *read-only and
reproducible*. A system whose state digest was identical either side of a query
was rejected for a decoder that drew different tokens.

Every test here is written so that it fails against ARENA-0, or fails if the
amendment is quietly undone.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena_doubles import EngineDouble  # noqa: E402
from arena import adapter as arena_0  # noqa: E402
from arena import adapter_v0_1 as arena_01  # noqa: E402
from arena.cupmem_adapter import CUPMemAdapter  # noqa: E402
from arena.cupmem_probe import CUPMemStateProbe  # noqa: E402


class _Sampling(EngineDouble):
    """Read-only over state, and a different answer every time.

    The ordinary case for a memory system driven by a sampling model, and the
    case ARENA-0 could not express.
    """

    _draws = 0

    def answer_query(self, *, query_label, query_text):
        result = super().answer_query(query_label=query_label, query_text=query_text)
        _Sampling._draws += 1
        result["answer"]["answer"] = f"draw {_Sampling._draws}"
        return result


class _ReadOnly(CUPMemAdapter):
    query_mutates_state = "read_only"


def _fixture():
    return arena_01.synthetic_fixture()


def _prepared(engine):
    adapter = _ReadOnly(engine)
    return adapter, CUPMemStateProbe(engine)


# ------------------------------------------------------------------ the amendment


def test_arena_0_rejects_a_read_only_system_whose_decoder_wanders() -> None:
    """The behaviour being amended, pinned so the amendment has something to be about."""
    result = arena_0.validate_adapter(_ReadOnly(_Sampling()), _fixture())
    assert not result["admissible"]
    assert any("read_only" in problem for problem in result["problems"])


def test_arena_0_1_admits_it_and_reports_both_facts_separately() -> None:
    engine = _Sampling()
    adapter, probe = _prepared(engine)
    result = arena_01.validate_adapter(adapter, _fixture(), probe=probe)

    assert result["admissible"], result["problems"]
    assert result["query_mutates_state"]["observed"] == "read_only"
    assert result["output_reproducible"]["observed"] == "false"


def test_irreproducible_output_is_never_by_itself_a_problem() -> None:
    """Reinstating that rule in another spelling would undo the amendment."""
    engine = _Sampling()
    adapter, probe = _prepared(engine)
    result = arena_01.validate_adapter(adapter, _fixture(), probe=probe)
    assert not any("reproduc" in problem.lower() for problem in result["problems"])


def test_mutation_is_read_from_state_not_from_a_difference_in_answers() -> None:
    engine = EngineDouble(mutate_on_query=True)
    adapter, probe = _prepared(engine)
    result = arena_01.validate_adapter(adapter, _fixture(), probe=probe)

    assert result["query_mutates_state"]["observed"] == "mutates_by_design"
    assert any("changed stored state" in problem for problem in result["problems"])
    assert not result["admissible"]


def test_a_declared_mutator_that_never_writes_is_caught() -> None:
    class Overclaimer(CUPMemAdapter):
        query_mutates_state = "mutates_by_design"

    engine = EngineDouble()
    result = arena_01.validate_adapter(Overclaimer(engine), _fixture(),
                                       probe=CUPMemStateProbe(engine))
    assert any("changed no state" in problem for problem in result["problems"])


def test_without_a_probe_mutation_is_unknown_and_that_is_not_a_failure() -> None:
    """A system that cannot expose state must be controlled for, not excluded."""
    result = arena_01.validate_adapter(_ReadOnly(EngineDouble()), _fixture())
    assert result["admissible"], result["problems"]
    assert result["query_mutates_state"]["observed"] == "unknown"
    assert result["query_mutates_state"]["how"] == "no state probe supplied"


def test_a_reproducible_system_says_so() -> None:
    engine = EngineDouble()
    adapter, probe = _prepared(engine)
    result = arena_01.validate_adapter(adapter, _fixture(), probe=probe)
    assert result["output_reproducible"]["observed"] == "true"


# --------------------------------------------------------------------- everything else


def test_the_state_digest_must_return_to_where_it_started() -> None:
    class Sticky(EngineDouble):
        def reset(self) -> None:
            items = list(self.store.items)
            super().reset()
            self.store.items = items

    engine = Sticky()
    result = arena_01.validate_adapter(_ReadOnly(engine), _fixture(),
                                       probe=CUPMemStateProbe(engine))
    assert any("pre-ingest state digest" in problem for problem in result["problems"])


def test_the_contract_names_its_version_and_its_digest() -> None:
    """Results from two contract versions must never share a table unlabelled."""
    engine = EngineDouble()
    result = arena_01.validate_adapter(_ReadOnly(engine), _fixture(),
                                       probe=CUPMemStateProbe(engine))
    assert result["contract_version"] == "ARENA-0.1"
    assert result["contract_digest"] == arena_01.contract_digest()
    assert len(result["contract_digest"]) == 64


def test_arena_0_is_left_alone() -> None:
    """It is the historical artefact. Amending in place would erase what was run."""
    assert not hasattr(arena_0, "CONTRACT_VERSION")
    assert not hasattr(arena_0, "OUTPUT_REPRODUCIBILITY")
    source = (ROOT / "scripts/arena/adapter.py").read_text(encoding="utf-8")
    assert "declared read_only but a repeated query returned different results" in source


def test_the_shared_types_are_the_same_objects_not_copies() -> None:
    """An amendment, not a fork. A second Cost would drift from the first."""
    assert arena_01.Cost is arena_0.Cost
    assert arena_01.Measure is arena_0.Measure
    assert arena_01.Answer is arena_0.Answer
    assert arena_01.MUTATION_MODES == arena_0.MUTATION_MODES


def test_the_reproducibility_vocabulary_is_three_valued() -> None:
    """`unknown` is not `false`, exactly as `unknown` is not zero for cost."""
    assert arena_01.OUTPUT_REPRODUCIBILITY == ("true", "false", "unknown")


def test_a_missing_method_is_still_rejected() -> None:
    class NoQuery:
        name = "half"
        query_mutates_state = "unknown"
        def reset(self): pass
        def ingest(self, records): return arena_01.Cost()

    result = arena_01.validate_adapter(NoQuery(), _fixture())
    assert not result["admissible"]
    assert "missing method: query" in result["problems"]


def test_an_undeclared_mutation_mode_is_still_rejected() -> None:
    class Silent(CUPMemAdapter):
        query_mutates_state = "sometimes"

    result = arena_01.validate_adapter(Silent(EngineDouble()), _fixture())
    assert any("query_mutates_state must be one of" in p for p in result["problems"])


def test_abstaining_while_also_answering_is_still_rejected() -> None:
    class Both(CUPMemAdapter):
        def query(self, question, asked_at=None):
            answer = super().query(question, asked_at)
            return arena_01.Answer(text="but I did answer", abstained=True,
                                   cost=answer.cost)

    result = arena_01.validate_adapter(Both(EngineDouble()), _fixture())
    assert any("abstained=True" in problem for problem in result["problems"])
