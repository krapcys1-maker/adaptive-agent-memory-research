"""CUPMem adapter. Translates their surface to the arena contract, nothing more.

    contract            CUPMem
    reset()             CupMemEngine.reset()  +  LLMClient.reset_usage_tracking()
    ingest(records)     write_session(session=…, session_index=…, session_time=…)
    query(question)     answer_query(query_label=…, query_text=…)

The one rule, restated because it is the rule the whole arena rests on:
**translate, never interpret.** Their `verdict` carries a premise judgement and
their `relevant_context` carries what they retrieved. Both are reported as-is.
Deciding that a wrong answer was a *state failure* rather than a *retrieval
failure* is the harness's job, and an adapter that made that call would be
grading its own exam.

What contact with the real system corrected
-------------------------------------------
Every mapping below was originally written from a reading of their surface and
checked against a double built from that same reading. Five were wrong, and the
double could not say so because it had been built from the adapter's
assumptions rather than from their code:

- **ingest wrote nothing.** Their chunker keeps only `role == "user"` messages
  with non-empty `content` and drops the rest silently. Our record shape was
  dropped entirely, and the system then answered every probe from an empty
  store while the validator reported *admissible*.
- **a mixed-time record list lost its chronology.** All records went into one
  session carrying the first record's time. Every other time was discarded — a
  loss in precisely the dimension this system exists to exploit.
- **cost was reported unobservable and is native.** The adapter probed
  `llm.usage`, an attribute that does not exist. `LLMClient` exposes
  `get_usage_summary()` and `get_call_records()`, with calls, tokens, cache
  hits, and a split by phase and by query label. Reporting *unobservable* for a
  system that reports per-phase usage understates a competitor on the exact axis
  this project insists on keeping separate from capability.
- **abstention was read from fields that do not exist.** `PremiseVerdict` has no
  `unknown_current`; its status vocabulary is SUPPORTED / OUTDATED / UNRESOLVED,
  and `unknown_current` is a section of the *store*, not of the verdict.
  `AnswerResult` has `answer` and `brief_rationale`, not `text`.
- **context tokens were not comparable with any other adapter.** They counted
  whitespace tokens of the serialised context structure — scores, bundles,
  nesting and punctuation — against the reference adapter's count over record
  text. A column mixing the two would compare two different quantities.

Where a field cannot be derived
--------------------------------
It is reported as `None` with a reason in `system_metadata`, never inferred and
never silently zeroed. A cost of zero and a cost that was not measurable are
different facts, and the arena needs to tell them apart.
"""

from __future__ import annotations

import time
from typing import Any

from arena.adapter import Answer, Cost, Measure


#: CUPMem has no abstention channel. Their answer composer is instructed to
#: always produce something, down to "still give the safest bounded
#: recommendation available", so the only decline the system can express is an
#: empty composed answer. Their premise verdict is reported raw and never
#: converted into abstention: UNRESOLVED judges the question's premise, and a
#: system that answers a question whose premise it doubts has not abstained.
ABSTENTION_CHANNEL = "empty-composed-answer"

#: Identifier keys their retrieved hits actually carry. `id` is the hit-level
#: reference their retrieval assembles; the rest are here because the walk is
#: generic, and a hand-written map per system is how an arena acquires five
#: private schemas.
_ID_KEYS = frozenset({"id", "uid", "chunk_id", "session_id", "record_id",
                      "memory_id", "item_id"})

_TEXT_KEYS = frozenset({"text"})


def _elapsed_us(started: float) -> int:
    """Microseconds since ``started``, as an integer.

    Rounded once at the point of measurement rather than at every addition, so
    the arena only ever sums integers.
    """
    return int(round((time.monotonic() - started) * 1_000_000))


def _walk_strings(node: Any, keys: frozenset[str]) -> list[str]:
    """Every string stored under one of ``keys``, in encounter order.

    Deliberately not a schema mapping. A hand-written field list would encode
    their internal layout into our arena, and the next system would need another
    one. This walks the structure and takes what it finds, which is translation
    rather than modelling.
    """
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and key in keys:
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(node)
    return found


def _evidence_ids(relevant_context: Any) -> list[str]:
    """Which records reached their reader, deduplicated in order.

    Order-preserving dedup: the arena cares which records reached the reader,
    not how often one was mentioned inside their structure.
    """
    return list(dict.fromkeys(_walk_strings(relevant_context, _ID_KEYS)))


def _context_tokens(relevant_context: Any) -> int:
    """Whitespace tokens of the distinct record texts they put before the reader.

    Counted over text, not over the serialised structure. The first version
    counted ``len(str(relevant_context).split())``, which folded braces, scores,
    bundle wrappers and repeated nesting into the figure — so CUPMem's context
    cost and the reference adapter's were different quantities printed in one
    column.

    Distinct texts, because their context repeats one hit under
    ``query_topk_results``, ``topk_primary_hits`` and ``topk_hit_bundles``,
    while the reader is shown a single copy.
    """
    seen = dict.fromkeys(_walk_strings(relevant_context, _TEXT_KEYS))
    return sum(len(text.split()) for text in seen)


def _abstained(result: dict[str, Any]) -> bool | None:
    """Did they decline, in their own terms?

    Their composed answer is the only place a decline can appear, because their
    verdict vocabulary judges the question's premise rather than their own
    ability to answer. If the answer field is absent entirely, the honest result
    is None — unknown, not False.
    """
    answer = result.get("answer")
    if isinstance(answer, dict):
        for key in ("answer", "text", "content", "final_answer"):
            if key in answer:
                return not str(answer.get(key) or "").strip()
    if isinstance(answer, str):
        return not answer.strip()
    return None


def _answer_text(result: dict[str, Any]) -> str:
    answer = result.get("answer")
    if isinstance(answer, dict):
        for key in ("answer", "text", "content", "final_answer"):
            value = answer.get(key)
            if isinstance(value, str):
                return value
    return str(answer or "")


def _time_key(record: dict[str, Any], preferred: str) -> str:
    for field in (preferred, "timestamp", "day", "date", "valid_from"):
        if record.get(field) not in (None, ""):
            return str(record[field])
    return ""


class CUPMemAdapter:
    """Requires a constructed CupMemEngine. This file does not build one.

    Construction needs an LLM client, an embedding model path and their runtime
    config, which belong to whoever runs the arena rather than to the
    translation. Passing the engine in keeps this file free of their
    configuration surface and keeps the adapter testable against a double.
    """

    #: Their query path reads the store and never writes it: no `apply_update`,
    #: no `chunk_bank` append and no counter advance appears anywhere under
    #: `query/`. That is an argument from construction, and the operational-fit
    #: run turns it into a measurement by fingerprinting engine state either side
    #: of a query.
    #:
    #: It stays `unknown` rather than `read_only` because the contract's check
    #: for `read_only` compares two query *outputs*, and their answers are drawn
    #: from a sampling model. Declaring `read_only` would be rejected for
    #: nondeterminism the declaration was never about. The state proof is carried
    #: in the operational-fit record instead of being asserted here.
    query_mutates_state = "unknown"

    name = "CUPMem"

    def __init__(self, engine: Any, session_time_field: str = "timestamp",
                 text_field: str = "text") -> None:
        self._engine = engine
        self._session_time_field = session_time_field
        self._text_field = text_field
        self._sessions_written = 0
        self._ingested_turns = 0
        self._refuse_a_discounted_cost()

    # ------------------------------------------------------------------ guards

    def _refuse_a_discounted_cost(self) -> None:
        """A response cache would make this system's cost incomparable.

        Their client caches completions on disk when given a ``cache_dir``, and
        records a cache hit as zero *billed* usage. One system running with a
        warm cache against four running cold is not a cost comparison, and the
        discount would be invisible in the totals.

        Refused at construction rather than detected in the numbers, because a
        property that can be guaranteed by construction should not be left to a
        check that fires only once the run is already contaminated.
        """
        cache_dir = getattr(getattr(self._engine, "llm", None), "cache_dir", None)
        if cache_dir is not None:
            raise ValueError(
                f"{self.name}: the engine's LLM client has cache_dir={cache_dir!r}. "
                "Cached completions are billed as zero, so the arena would record a "
                "discount no other system gets. Construct the client without a cache "
                "for arena runs."
            )

    # ----------------------------------------------------------------- contract

    def reset(self) -> None:
        self._engine.reset()
        self._sessions_written = 0
        self._ingested_turns = 0
        tracker = getattr(self._engine, "llm", None)
        if hasattr(tracker, "reset_usage_tracking"):
            tracker.reset_usage_tracking()

    def ingest(self, records: list[dict[str, Any]]) -> Cost:
        """Hand the records over as sessions, one per distinct record time.

        Their unit is a session with a time; ours is a list of records that each
        carry their own. Collapsing a mixed-time list into one session keeps the
        first record's time and drops every other — not a translation but a loss,
        and a loss in exactly the dimension this system is built to exploit.
        Grouping is a no-op on the native case, where a caller hands over one
        session whose turns share a timestamp.

        Groups appear in first-appearance order, never sorted. The arena fixes
        ingestion order across systems, and sorting here would hand CUPMem a
        chronology the other adapters were not given.
        """
        started = time.monotonic()
        before = self._usage()

        groups: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            groups.setdefault(_time_key(record, self._session_time_field), []).append(record)

        # Their chunker keeps only messages with role == "user" and a non-empty
        # "content", and silently drops everything else. Handing it our record
        # shape ingested nothing at all, and the system then answered every probe
        # from an empty store — the adapter reported admissible while measuring
        # pure confabulation. Translating the shape is the adapter's job;
        # noticing that nothing survived translation is the contract's.
        kept_total = 0
        for session_time, group in groups.items():
            session = [
                {"role": "user", "content": str(record.get(self._text_field, "")).strip()}
                for record in group
            ]
            kept = [turn for turn in session if turn["content"]]
            kept_total += len(kept)
            if not kept:
                continue
            self._engine.write_session(
                session=session,
                session_index=self._sessions_written,
                session_time=session_time,
            )
            self._sessions_written += 1

        if records and not kept_total:
            raise ValueError(
                f"{self.name}: ingest translated {len(records)} records into zero "
                "usable turns. Answering probes after this would measure the "
                "model's priors, not the system's memory."
            )
        self._ingested_turns += kept_total

        return self._cost_since(before, started)

    def query(self, question: str, asked_at: Any = None) -> Answer:
        started = time.monotonic()
        before = self._usage()

        result = self._engine.answer_query(query_label=str(asked_at or "probe"),
                                           query_text=question)

        abstained = _abstained(result)
        context = result.get("relevant_context")
        evidence = _evidence_ids(context)
        verdict = result.get("verdict")

        return Answer(
            text="" if abstained else _answer_text(result),
            evidence_ids=evidence,
            context_tokens=_context_tokens(context),
            abstained=bool(abstained),
            cost=self._cost_since(before, started),
            system_metadata={
                # Their premise verdict is reported, never converted into one of
                # our failure types. That conversion is the harness's job.
                "verdict": verdict,
                "premise_status": verdict.get("status") if isinstance(verdict, dict) else None,
                # bool(None) is False and the contract's field cannot hold a third
                # value, so the raw result is carried beside it. Unknown ≠ False.
                "abstained_raw": abstained,
                "abstention_derivable": abstained is not None,
                "abstention_channel": ABSTENTION_CHANNEL,
                "cost_observability": self._cost_observability(),
                "evidence_observability": "native" if evidence else "none-returned",
                "context_tokens_basis": (
                    "distinct `text` fields of their reported relevant_context, "
                    "whitespace-split; their second-pass fallback evidence never "
                    "enters that structure, so this is a floor"
                ),
                "context_tokens_is_floor": True,
            },
        )

    # ----------------------------------------------------------------- helpers

    def _summary(self) -> dict[str, Any] | None:
        """Their own usage accounting, or None if this engine has none.

        The distinction the arena depends on: a system making no model calls and
        a system unable to count them both produce zeros, and only one of them is
        cheap.
        """
        getter = getattr(getattr(self._engine, "llm", None), "get_usage_summary", None)
        if not callable(getter):
            return None
        summary = getter()
        return summary if isinstance(summary, dict) else None

    def _usage(self) -> dict[str, int] | None:
        summary = self._summary()
        if summary is None:
            return None
        billed = summary.get("billed_usage") or {}
        logical = summary.get("logical_usage") or {}
        return {
            "calls": int(summary.get("total_calls", 0) or 0),
            "prompt_tokens": int(billed.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(billed.get("completion_tokens", 0) or 0),
            "logical_prompt_tokens": int(logical.get("prompt_tokens", 0) or 0),
            "logical_completion_tokens": int(logical.get("completion_tokens", 0) or 0),
            "cache_hits": int(summary.get("cache_hits", 0) or 0),
        }

    def _cost_observability(self) -> dict[str, str]:
        native = self._summary() is not None
        return {field: ("native" if native else "unobservable")
                for field in ("calls", "prompt_tokens", "completion_tokens")}

    def _cost_since(self, before: dict[str, int] | None, started: float) -> Cost:
        """What this operation consumed, as the difference in their own counters.

        A delta rather than a total: their tracker accumulates across a run, and
        the contract prices ingestion and query separately.
        """
        after = self._usage()
        if before is None or after is None:
            unknown = Measure(None, "unobservable")
            return Cost(unknown, unknown, unknown,
                        Measure(_elapsed_us(started), "instrumented"))

        if after["cache_hits"] > before["cache_hits"]:
            # Construction already refuses a cache, so reaching here means one
            # appeared underneath us. Billed and logical usage have diverged, and
            # the cheaper of the two is a discount rather than a measurement.
            raise ValueError(
                f"{self.name}: {after['cache_hits'] - before['cache_hits']} cached "
                "completions were served during an arena operation. Billed usage is "
                "zero for those and no longer measures what the mechanism costs."
            )

        def delta(field: str) -> Measure:
            return Measure(max(0, after[field] - before[field]), "native")

        return Cost(
            model_calls=delta("calls"),
            input_tokens=delta("prompt_tokens"),
            output_tokens=delta("completion_tokens"),
            # Theirs is a token ledger, not a clock. The wall figure is ours.
            wall_microseconds=Measure(_elapsed_us(started), "instrumented"),
        )
