"""Operational fit: does the real system confirm what the adapter assumed?

Structural fit asks whether the three methods exist and whether every contract
field is derivable from a documented return shape. It is answered by reading,
costs nothing, and was answered *yes* for CUPMem while five of its mappings were
wrong. Operational fit is the other question, and only a live run answers it.

Nine things are checked, and accuracy is not among them. A wrong answer does not
fail this run:

    reset semantics          the next ingest behaves like the first
    state leakage            nothing survives a reset, byte for byte
    session grouping         records become the sessions the adapter claims
    session_time semantics   the record's time reaches stored state
    answer return shape      types, not plausibility
    abstention mapping       derivable, and from which channel
    evidence observability   which records reached the reader, and are they real
    cost observability       per field, native / instrumented / unobservable
    query mutation           does asking change what a later ask sees

Why a state fingerprint and not a repeated query
-------------------------------------------------
The frozen contract detects mutation by asking one probe twice and comparing the
answers. Against a sampling model that check cannot separate *the store changed*
from *the decoder drew different tokens*, and CUPMem's first live run returned
exactly that ambiguity.

A fingerprint over the system's own state settles it by construction: serialise
everything the engine holds, hash it, query, hash again. Equal digests mean the
query wrote nothing, whatever the text did. Where a property can be established
by construction, the project's rule is to establish it rather than to test for it
probabilistically — the same rule that replaced rounded-float cost accumulation
with integers.

The fingerprint is the one system-specific part, supplied as a probe. Everything
else here works against any adapter.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Protocol

from arena.adapter import Answer, Cost


class StateProbe(Protocol):
    """The system-specific window this module needs, and nothing more.

    An adapter must not expose internals — it translates. So the probe is a
    separate object, used only by operational fit and never by a scored run.
    """

    def fingerprint(self) -> str:
        """A digest over everything the system holds. Equal digests, equal state."""

    def stored_times(self) -> list[str]:
        """The session time recorded on each stored item, as the system kept it."""

    def stored_ids(self) -> list[str]:
        """Identifiers of everything currently stored, for checking evidence is real."""


def digest(value: Any) -> str:
    """A stable digest over anything JSON can be talked into representing.

    `sort_keys` because dict ordering is not part of the state, and `default=str`
    because a fingerprint that raises on an unexpected object would turn an
    unknown into a crash rather than into a recorded unknown.
    """
    encoded = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class WriteSpy:
    """Records every session handed to the system, without altering any of them.

    Session grouping is the adapter's decision and therefore the adapter's
    claim. A claim checked only against the adapter's own bookkeeping is checked
    against itself, so this watches the boundary the adapter does not control.
    """

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._original = engine.write_session
        self.writes: list[dict[str, Any]] = []
        engine.write_session = self._spy  # type: ignore[method-assign]

    def _spy(self, *, session: list[dict[str, Any]], session_index: int,
             session_time: str) -> Any:
        self.writes.append({
            "session_index": session_index,
            "session_time": session_time,
            "turns": len(session),
            "roles": sorted({str(turn.get("role", "")) for turn in session}),
        })
        return self._original(session=session, session_index=session_index,
                              session_time=session_time)

    def release(self) -> None:
        self._engine.write_session = self._original  # type: ignore[method-assign]

    def __enter__(self) -> "WriteSpy":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.release()


def _shape_problems(answer: Any) -> list[str]:
    """Type conformance of one Answer. Plausibility is not checked and never is."""
    problems: list[str] = []
    if not isinstance(answer, Answer):
        return [f"query returned {type(answer).__name__}, expected Answer"]
    if not isinstance(answer.text, str):
        problems.append(f"text is {type(answer.text).__name__}, expected str")
    if not isinstance(answer.evidence_ids, list) or any(
            not isinstance(i, str) for i in answer.evidence_ids):
        problems.append("evidence_ids must be a list of str")
    if not isinstance(answer.context_tokens, int) or answer.context_tokens < 0:
        problems.append("context_tokens must be a non-negative int")
    if not isinstance(answer.abstained, bool):
        problems.append("abstained must be a bool")
    if not isinstance(answer.cost, Cost):
        problems.append("cost must be a Cost")
    if answer.abstained and answer.text.strip():
        problems.append("abstained=True with non-empty text")
    return problems


def operational_fit(
    adapter: Any,
    fixture: dict[str, Any],
    *,
    probe: StateProbe | None = None,
    spy_factory: Callable[[], WriteSpy] | None = None,
) -> dict[str, Any]:
    """Run the nine checks and return what happened, interpreting none of it.

    Returns a verdict per dimension. `failures` is what the adapter got wrong;
    `unverifiable` is what could not be established with the access available,
    which is a different thing and is never folded into a pass.
    """
    failures: list[str] = []
    unverifiable: list[str] = []
    observed: dict[str, Any] = {}

    # ---------------------------------------------------------- reset semantics
    adapter.reset()
    empty_digest = probe.fingerprint() if probe else None
    if probe is None:
        unverifiable.append("no state probe: reset and mutation checked by proxy only")

    # ------------------------------------------------- session grouping + ingest
    spy = spy_factory() if spy_factory else None
    started = time.monotonic()
    try:
        ingest_cost = adapter.ingest(fixture["records"])
    finally:
        if spy:
            spy.release()
    ingest_wall = time.monotonic() - started

    observed["session_writes"] = spy.writes if spy else None
    expected_groups = len({
        str(r.get("timestamp", r.get("day", ""))) for r in fixture["records"]
    })
    if spy is not None:
        if len(spy.writes) != expected_groups:
            failures.append(
                f"session grouping: {len(fixture['records'])} records over "
                f"{expected_groups} distinct times became {len(spy.writes)} sessions"
            )
        if any(w["roles"] != ["user"] for w in spy.writes):
            failures.append("session grouping: a session carried a role their chunker drops")
        indices = [w["session_index"] for w in spy.writes]
        if indices != sorted(set(indices)) or (indices and indices[0] != 0):
            failures.append(f"session grouping: session_index sequence is {indices}")
    else:
        unverifiable.append("no write spy: session grouping is the adapter's own account")

    filled_digest = probe.fingerprint() if probe else None
    if probe is not None and filled_digest == empty_digest:
        failures.append("ingest changed no state: the store is identical to before ingest")

    # ------------------------------------------------------- session_time landed
    if probe is not None:
        record_times = {str(r.get("timestamp", r.get("day", ""))) for r in fixture["records"]}
        stored = [t for t in probe.stored_times() if t]
        observed["stored_session_times"] = sorted(set(stored))
        observed["record_times"] = sorted(record_times)
        if not stored:
            failures.append(
                "session_time semantics: nothing stored carries a session time, so the "
                "record's time did not reach state"
            )
        elif not set(stored) <= record_times:
            failures.append(
                f"session_time semantics: stored times {sorted(set(stored))} are not a "
                f"subset of the times the records carried {sorted(record_times)}"
            )
    else:
        unverifiable.append("no state probe: session_time cannot be traced into state")

    # ----------------------------------------------------------- query mutation
    first_probe = fixture["probes"][0]
    before_query = probe.fingerprint() if probe else None
    first = adapter.query(first_probe["question"], first_probe.get("asked_at"))
    after_query = probe.fingerprint() if probe else None
    second = adapter.query(first_probe["question"], first_probe.get("asked_at"))
    after_repeat = probe.fingerprint() if probe else None

    output_differed = (first.text, first.evidence_ids) != (second.text, second.evidence_ids)
    state_changed = None if probe is None else not (
        before_query == after_query == after_repeat
    )
    observed["query_mutation"] = {
        "state_changed": state_changed,
        "output_differed": output_differed,
        # The two together say what neither says alone. Unchanged state with a
        # differing answer is a sampling decoder, not a learning store.
        "reading": (
            "unknown — no state probe" if state_changed is None else
            "mutates_by_design" if state_changed else
            "read_only state; output nondeterminism is decoding, not memory"
            if output_differed else "read_only state and reproducible output"
        ),
    }
    declared = getattr(adapter, "query_mutates_state", "unknown")
    observed["declared_mutation_mode"] = declared
    if state_changed and declared == "read_only":
        failures.append("declared read_only but querying changed stored state")
    if state_changed is False and declared == "mutates_by_design":
        failures.append("declared mutates_by_design but querying changed nothing")

    # ---------------------------------------- shape, abstention, evidence, cost
    answers: list[Answer] = [first, second]
    for entry in fixture["probes"]:
        answers.append(adapter.query(entry["question"], entry.get("asked_at")))
    for index, answer in enumerate(answers):
        for problem in _shape_problems(answer):
            failures.append(f"answer shape (probe {index}): {problem}")

    metadata = [a.system_metadata for a in answers if isinstance(a, Answer)]
    derivable = [m.get("abstention_derivable") for m in metadata]
    observed["abstention"] = {
        "derivable_on_every_probe": all(bool(d) for d in derivable),
        "channel": next((m.get("abstention_channel") for m in metadata), None),
        "raw": [m.get("abstained_raw") for m in metadata],
        "premise_status": [m.get("premise_status") for m in metadata],
        "abstained": [a.abstained for a in answers],
    }
    if not any(derivable):
        failures.append(
            "abstention mapping: not derivable on any probe, so the harness cannot "
            "tell a refusal from an answer"
        )

    stored_ids = set(probe.stored_ids()) if probe else set()
    surfaced = [i for a in answers for i in a.evidence_ids]
    unreal = sorted({i for i in surfaced if stored_ids and i not in stored_ids})
    observed["evidence"] = {
        "ids_per_probe": [len(a.evidence_ids) for a in answers],
        "any_evidence": bool(surfaced),
        "stored_id_count": len(stored_ids) or None,
        "ids_not_matching_any_stored_record": unreal,
    }
    if not surfaced:
        failures.append(
            "evidence observability: no probe returned an evidence id, so retrieved-"
            "and-misused cannot be separated from never-retrieved"
        )
    if unreal:
        failures.append(
            f"evidence observability: {len(unreal)} surfaced ids match nothing stored"
        )
    contradictory = [index for index, answer in enumerate(answers)
                     if answer.evidence_ids and not answer.context_tokens]
    observed["evidence"]["context_tokens_per_probe"] = [a.context_tokens for a in answers]
    if contradictory:
        failures.append(
            f"context cost: probes {contradictory} surfaced evidence and reported zero "
            "context tokens. Records reached the reader, so the zero is a measurement "
            "that failed, not a query that was free"
        )

    observed["cost"] = {
        "ingest": ingest_cost.summary() if isinstance(ingest_cost, Cost) else None,
        "ingest_wall_seconds": round(ingest_wall, 3),
        "per_query": [a.cost.summary() for a in answers],
        "observability": next((m.get("cost_observability") for m in metadata), None),
    }
    if not isinstance(ingest_cost, Cost):
        failures.append("cost observability: ingest did not return a Cost")
    elif not ingest_cost.model_calls.value and ingest_wall > 0.5:
        failures.append(
            f"cost observability: ingest took {ingest_wall:.1f}s and reported "
            f"{ingest_cost.model_calls.value} model calls"
        )

    # ----------------------------------------------- reset again, and leakage
    adapter.reset()
    reset_digest = probe.fingerprint() if probe else None
    after_reset = adapter.query(first_probe["question"], first_probe.get("asked_at"))
    observed["reset"] = {
        "state_returns_to_empty": None if probe is None else reset_digest == empty_digest,
        "evidence_after_reset": after_reset.evidence_ids,
        "context_tokens_after_reset": after_reset.context_tokens,
    }
    if probe is not None and reset_digest != empty_digest:
        failures.append(
            "state leakage: after reset the state digest differs from the pre-ingest "
            "one, so the next arm does not start where the first did"
        )
    if after_reset.evidence_ids:
        failures.append("state leakage: evidence returned from a store that was reset")

    return {
        "adapter": getattr(adapter, "name", "?"),
        "fit": not failures,
        "failures": failures,
        # Never folded into `fit`. A check that could not run is not a check that
        # passed, and the distinction is the whole reason this record exists.
        "unverifiable": unverifiable,
        "state_probe_available": probe is not None,
        "observed": observed,
        "note": ("operational fit is about the adapter's assumptions, not the system's "
                 "answers. Accuracy is deliberately not scored here"),
    }
