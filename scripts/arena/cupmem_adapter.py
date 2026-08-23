"""CUPMem adapter. Translates their surface to the arena contract, nothing more.

    contract            CUPMem
    reset()             CupMemEngine.reset()
    ingest(records)     write_session(session=…, session_index=…, session_time=…)
    query(question)     answer_query(query_label=…, query_text=…)

The one rule, restated because it is the rule the whole arena rests on:
**translate, never interpret.** Their `verdict` carries a premise judgement and
their `relevant_context` carries what they retrieved. Both are reported as-is.
Deciding that a wrong answer was a *state failure* rather than a *retrieval
failure* is the harness's job, and an adapter that made that call would be
grading its own exam.

What is verified here, and what is not
--------------------------------------
**Verified:** the translation is total — every field the contract requires is
either derivable from their return shape or reported absent. `answer_query`
returns a dict whose `answer` key holds a composed answer, `relevant_context`
holds retrieved state, and `verdict` holds a premise judgement. Their engine
exposes `reset_usage_tracking`, so per-query model cost is obtainable.

**Not verified:** anything requiring their engine to actually run. That needs an
LLM endpoint, an embedding model on disk and the STALE corpus loaded, none of
which is configured here. So this file establishes that a translation *exists*;
it does not establish operational fit, which the registered two-level
distinction says only a live run can.

Where a field cannot be derived
--------------------------------
It is reported as `None` with a reason in `system_metadata`, never inferred and
never silently zeroed. A cost of zero and a cost that was not measurable are
different facts, and the arena needs to tell them apart — a system reporting no
model calls because it makes none is not the same as one that cannot say.
"""

from __future__ import annotations

import time
from typing import Any

from arena.adapter import Answer, Cost, Measure


def _elapsed_us(started: float) -> int:
    """Microseconds since ``started``, as an integer.

    Rounded once at the point of measurement rather than at every addition, so
    the arena only ever sums integers.
    """
    return int(round((time.monotonic() - started) * 1_000_000))


def _evidence_ids(relevant_context: Any) -> list[str]:
    """Whatever identifiers their retrieved context carries, extracted generically.

    Deliberately not a schema mapping. A hand-written field list would encode
    their internal layout into our arena, and the next system would need another
    one. This walks the structure and takes anything that looks like a record
    identifier, which is translation rather than modelling.
    """
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and key in {"id", "uid", "chunk_id",
                                                      "session_id", "record_id", "memory_id"}:
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(relevant_context)
    # Order-preserving dedup: the arena cares which records reached the reader,
    # not how often one was mentioned inside their structure.
    return list(dict.fromkeys(found))


def _abstained(result: dict[str, Any]) -> bool | None:
    """Did they decline, in their own terms?

    CUPMem carries an UnknownCurrent type and a premise verdict, so declining is
    expressible in their model rather than something we impute. If neither field
    is present the honest answer is None — unknown, not False.
    """
    verdict = result.get("verdict")
    if isinstance(verdict, dict):
        for key in ("unknown_current", "is_unknown", "abstained", "declined"):
            if key in verdict:
                return bool(verdict[key])
    answer = result.get("answer")
    if isinstance(answer, dict) and "text" in answer:
        return not str(answer.get("text") or "").strip()
    return None


def _answer_text(result: dict[str, Any]) -> str:
    answer = result.get("answer")
    if isinstance(answer, dict):
        for key in ("text", "answer", "content", "final_answer"):
            value = answer.get(key)
            if isinstance(value, str):
                return value
    return str(answer or "")


class CUPMemAdapter:
    """Requires a constructed CupMemEngine. This file does not build one.

    Construction needs an LLM client, an embedding model path and their runtime
    config, which belong to whoever runs the arena rather than to the
    translation. Passing the engine in keeps this file free of their
    configuration surface and keeps the adapter testable against a double.
    """

    name = "CUPMem"

    def __init__(self, engine: Any, session_time_field: str = "timestamp") -> None:
        self._engine = engine
        self._session_time_field = session_time_field
        self._sessions_written = 0

    def reset(self) -> None:
        self._engine.reset()
        self._sessions_written = 0
        tracker = getattr(self._engine, "llm", None)
        if hasattr(tracker, "reset_usage_tracking"):
            tracker.reset_usage_tracking()

    def ingest(self, records: list[dict[str, Any]]) -> Cost:
        """Group records into one session and hand it over.

        Their unit is a session with a time; ours is a list of records. Grouping
        is format translation and is the adapter's whole purpose. Records are
        kept in the order given, because reordering would change what their
        writer sees and the arena fixes ingestion order across systems.
        """
        started = time.monotonic()
        session_time = str(records[0].get(self._session_time_field, "")) if records else ""

        self._engine.write_session(
            session=records,
            session_index=self._sessions_written,
            session_time=session_time,
        )
        self._sessions_written += 1

        # Per field, because a system can know it called a model 17 times and
        # still not expose token usage. One flag over the whole Cost would hide
        # the figure it does have.
        return Cost(
            model_calls=self._measure("calls"),
            input_tokens=self._measure("prompt_tokens"),
            output_tokens=self._measure("completion_tokens"),
            wall_microseconds=Measure(_elapsed_us(started), "instrumented"),
        )

    def query(self, question: str, asked_at: Any = None) -> Answer:
        started = time.monotonic()
        before = self._usage("calls"), self._usage("prompt_tokens"), self._usage("completion_tokens")

        result = self._engine.answer_query(query_label=str(asked_at or "probe"), query_text=question)

        abstained = _abstained(result)
        evidence = _evidence_ids(result.get("relevant_context"))
        after = self._usage("calls"), self._usage("prompt_tokens"), self._usage("completion_tokens")

        return Answer(
            text="" if abstained else _answer_text(result),
            evidence_ids=evidence,
            context_tokens=self._context_tokens(result),
            abstained=bool(abstained),
            cost=Cost(
                model_calls=self._delta(before[0], after[0], "calls"),
                input_tokens=self._delta(before[1], after[1], "prompt_tokens"),
                output_tokens=self._delta(before[2], after[2], "completion_tokens"),
                wall_microseconds=Measure(_elapsed_us(started), "instrumented"),
            ),
            system_metadata={
                # Their premise verdict is reported, never converted into one of
                # our failure types. That conversion is the harness's job.
                "verdict": result.get("verdict"),
                "abstention_derivable": abstained is not None,
                "cost_observability": {
                    f: ("native" if self._field_available(f) else "unobservable")
                    for f in ("calls", "prompt_tokens", "completion_tokens")
                },
                "evidence_observability": (
                    "native" if evidence else "none-returned"
                ),
            },
        )

    # ----------------------------------------------------------------- helpers

    def _usage_available(self) -> bool:
        """Can this engine report usage at all?

        The distinction the arena depends on: a system making no model calls and
        a system unable to count them both produce zeros, and only one of them is
        cheap.
        """
        return getattr(getattr(self._engine, "llm", None), "usage", None) is not None

    def _field_available(self, field: str) -> bool:
        """Does their tracker expose this particular field?

        Checked per field rather than per tracker, because exposing usage at all
        and exposing every part of it are different things.
        """
        tracker = getattr(getattr(self._engine, "llm", None), "usage", None)
        if tracker is None:
            return False
        return field in tracker if isinstance(tracker, dict) else hasattr(tracker, field)

    def _usage(self, field: str) -> int:
        tracker = getattr(getattr(self._engine, "llm", None), "usage", None)
        if isinstance(tracker, dict):
            return int(tracker.get(field, 0) or 0)
        return int(getattr(tracker, field, 0) or 0) if tracker is not None else 0

    def _measure(self, field: str) -> Measure:
        if not self._field_available(field):
            return Measure(None, "unobservable")
        return Measure(self._usage(field), "native")

    def _delta(self, before: int, after: int, field: str) -> Measure:
        if not self._field_available(field):
            return Measure(None, "unobservable")
        return Measure(max(0, after - before), "native")

    def _context_tokens(self, result: dict[str, Any]) -> int:
        """What reached their reader, in whitespace tokens.

        Measured from the retrieved context they report rather than from an
        internal counter, so it is comparable with every other adapter under the
        same definition the contract fixes.
        """
        context = result.get("relevant_context")
        return len(str(context).split()) if context else 0
