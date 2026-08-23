"""Operational fit, checked against engines built to break each of its nine checks.

A check that has never failed is not evidence. The mutation check in particular
was added because the frozen contract's version of it could not fail: it ran
after a probe loop that had already drained the store, so the condition it tested
could not arise. Each check here is given an engine that violates it.

None of this touches accuracy. Every engine below answers whatever it likes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena_doubles import EngineDouble  # noqa: E402
from arena.adapter import Cost, Measure, synthetic_fixture  # noqa: E402
from arena.cupmem_adapter import CUPMemAdapter  # noqa: E402
from arena.cupmem_probe import CUPMemStateProbe  # noqa: E402
from arena.operational_fit import WriteSpy, digest, operational_fit  # noqa: E402


def run(engine, **kwargs):
    return operational_fit(
        CUPMemAdapter(engine), synthetic_fixture(),
        probe=CUPMemStateProbe(engine),
        spy_factory=lambda: WriteSpy(engine),
        **kwargs,
    )


# ------------------------------------------------------------------------ the pass


def test_a_conforming_engine_fits() -> None:
    report = run(EngineDouble())
    assert report["fit"], report["failures"]
    assert report["unverifiable"] == []


def test_fit_is_not_a_claim_about_answers() -> None:
    """The engine below answers every probe with the same wrong string."""
    class AlwaysWrong(EngineDouble):
        def answer_query(self, *, query_label, query_text):
            result = super().answer_query(query_label=query_label, query_text=query_text)
            result["answer"]["answer"] = "the moon"
            return result

    assert run(AlwaysWrong())["fit"]


# -------------------------------------------------------------------- ingest wrote


def test_an_ingest_that_changes_no_state_is_caught() -> None:
    """The defect the first live run shipped, now visible from state rather than cost.

    The adapter raises on a zero-turn translation, so this engine accepts the
    turns and quietly stores nothing — the same end state by a different route,
    and the reason the check is on state rather than on the adapter's bookkeeping.
    """
    class Forgetful(EngineDouble):
        def write_session(self, *, session, session_index, session_time):
            self.sessions.append({"index": session_index, "time": session_time,
                                  "turns": len(session)})
            return {}

    report = run(Forgetful())
    assert not report["fit"]
    assert any("ingest changed no state" in f for f in report["failures"])


# ---------------------------------------------------------------- session grouping


def test_records_collapsed_into_one_session_are_caught() -> None:
    """Four records over four times becoming one session is a lost chronology."""
    class Collapsing(CUPMemAdapter):
        def ingest(self, records):
            return super().ingest([dict(r, day=1, timestamp="1") for r in records])

    engine = EngineDouble()
    report = operational_fit(
        Collapsing(engine), synthetic_fixture(),
        probe=CUPMemStateProbe(engine), spy_factory=lambda: WriteSpy(engine),
    )
    assert any("session grouping" in f for f in report["failures"])


def test_a_session_carrying_a_role_their_chunker_drops_is_caught() -> None:
    class WrongRole(CUPMemAdapter):
        def ingest(self, records):
            self._engine.write_session(
                session=[{"role": "assistant", "content": r["text"]} for r in records],
                session_index=0, session_time="1")
            return Cost(Measure(0), Measure(0), Measure(0), Measure(0))

    engine = EngineDouble()
    report = operational_fit(
        WrongRole(engine), synthetic_fixture(),
        probe=CUPMemStateProbe(engine), spy_factory=lambda: WriteSpy(engine),
    )
    assert any("role their chunker drops" in f for f in report["failures"])


# ------------------------------------------------------------------- session_time


def test_a_session_time_that_never_reaches_state_is_caught() -> None:
    """Passing the time and storing it are different events; only one is a memory."""
    class TimeBlind(EngineDouble):
        def write_session(self, *, session, session_index, session_time):
            return super().write_session(session=session, session_index=session_index,
                                         session_time="")

    report = run(TimeBlind())
    assert any("session_time semantics" in f for f in report["failures"])


def test_a_stored_time_the_records_never_carried_is_caught() -> None:
    class TimeInventor(EngineDouble):
        def write_session(self, *, session, session_index, session_time):
            return super().write_session(session=session, session_index=session_index,
                                         session_time="1999-01-01")

    report = run(TimeInventor())
    assert any("not a subset" in f for f in report["failures"])


# ---------------------------------------------------------------- query mutation


def test_a_query_that_writes_state_is_seen_as_a_mutation() -> None:
    report = run(EngineDouble(mutate_on_query=True))
    assert report["observed"]["query_mutation"]["state_changed"] is True
    assert report["observed"]["query_mutation"]["reading"] == "mutates_by_design"


def test_a_read_only_declaration_contradicted_by_state_is_a_failure() -> None:
    class Liar(CUPMemAdapter):
        query_mutates_state = "read_only"

    engine = EngineDouble(mutate_on_query=True)
    report = operational_fit(Liar(engine), synthetic_fixture(),
                             probe=CUPMemStateProbe(engine),
                             spy_factory=lambda: WriteSpy(engine))
    assert any("declared read_only" in f for f in report["failures"])


def test_a_differing_answer_over_unchanged_state_is_read_as_decoding() -> None:
    """The ambiguity the contract's repeat-a-probe check cannot resolve.

    The first live CUPMem run returned `repeated_query_differed: True` and no way
    to tell a learning store from a sampling decoder. State either side of the
    query settles it.
    """
    class Sampling(EngineDouble):
        _draws = 0

        def answer_query(self, *, query_label, query_text):
            result = super().answer_query(query_label=query_label, query_text=query_text)
            Sampling._draws += 1
            result["answer"]["answer"] = f"draw {Sampling._draws}"
            return result

    mutation = run(Sampling())["observed"]["query_mutation"]
    assert mutation["output_differed"] is True
    assert mutation["state_changed"] is False
    assert mutation["reading"] == ("read_only state; output nondeterminism is "
                                  "decoding, not memory")


def test_a_declared_mutator_that_never_mutates_is_a_failure() -> None:
    class Overclaimer(CUPMemAdapter):
        query_mutates_state = "mutates_by_design"

    engine = EngineDouble()
    report = operational_fit(Overclaimer(engine), synthetic_fixture(),
                             probe=CUPMemStateProbe(engine),
                             spy_factory=lambda: WriteSpy(engine))
    assert any("declared mutates_by_design" in f for f in report["failures"])


# ---------------------------------------------------------------------- evidence


def test_an_evidence_id_matching_nothing_stored_is_caught() -> None:
    """Retrieved-and-misused and never-retrieved are different failures.

    An id that names nothing the system holds separates them badly, so it is
    worth catching before a failure matrix is built on top of it.
    """
    class Fabricator(EngineDouble):
        def answer_query(self, *, query_label, query_text):
            result = super().answer_query(query_label=query_label, query_text=query_text)
            result["relevant_context"]["topk_primary_hits"] = [
                {"source": "active", "id": "not_a_real_item", "text": "x", "payload": {}}]
            return result

    report = run(Fabricator())
    assert any("match nothing stored" in f for f in report["failures"])


def test_a_system_returning_no_evidence_at_all_is_caught() -> None:
    class Silent(EngineDouble):
        def answer_query(self, *, query_label, query_text):
            result = super().answer_query(query_label=query_label, query_text=query_text)
            result["relevant_context"] = {}
            return result

    report = run(Silent())
    assert any("evidence observability" in f for f in report["failures"])


# -------------------------------------------------------------------------- reset


def test_state_surviving_a_reset_is_caught() -> None:
    class Sticky(EngineDouble):
        def reset(self) -> None:
            items = list(self.store.items)
            super().reset()
            self.store.items = items

    report = run(Sticky())
    assert any("state leakage" in f for f in report["failures"])


def test_a_counter_surviving_a_reset_is_caught() -> None:
    """Not only the store. A leaked counter renames every later record."""
    class LeakyCounter(EngineDouble):
        def reset(self) -> None:
            counter = self._chunk_counter
            super().reset()
            self._chunk_counter = counter

    assert any("state leakage" in f for f in run(LeakyCounter())["failures"])


# ------------------------------------------------------------- unverifiable ≠ pass


def test_without_a_probe_the_checks_are_recorded_as_unverifiable_not_passed() -> None:
    """`unknown` is not `pass`, and it is never folded into `fit`."""
    engine = EngineDouble()
    report = operational_fit(CUPMemAdapter(engine), synthetic_fixture())
    assert report["state_probe_available"] is False
    assert len(report["unverifiable"]) >= 2
    assert report["observed"]["query_mutation"]["state_changed"] is None
    assert report["observed"]["reset"]["state_returns_to_empty"] is None


def test_a_probe_that_cannot_see_all_the_state_refuses_to_be_built() -> None:
    """A partial fingerprint would keep reporting read-only for a writing system."""
    class Shrunk:
        store = None
        chunk_bank: list = []

    with pytest.raises(AttributeError, match="partial fingerprint"):
        CUPMemStateProbe(Shrunk())


# ----------------------------------------------------------------------- the spy


def test_the_spy_puts_the_method_back() -> None:
    engine = EngineDouble()
    original = engine.write_session
    with WriteSpy(engine):
        pass
    assert engine.write_session == original


def test_the_spy_changes_nothing_it_watches() -> None:
    plain, watched = EngineDouble(), EngineDouble()
    CUPMemAdapter(plain).ingest([{"id": "r1", "text": "a", "day": 1}])
    with WriteSpy(watched):
        CUPMemAdapter(watched).ingest([{"id": "r1", "text": "a", "day": 1}])
    assert digest(plain.store.to_snapshot()) == digest(watched.store.to_snapshot())
