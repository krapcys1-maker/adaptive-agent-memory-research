"""Mem0 adapter. Translates their surface to the arena contract, nothing more.

    contract            Mem0
    reset()             Memory.delete_all(user_id=…)
    ingest(records)     Memory.add(messages=…, user_id=…, metadata=…)
    query(question)     Memory.search(query=…, user_id=…)

The structural finding, stated before any number
-------------------------------------------------
**Mem0 has no answer channel.** `search` returns memories with scores; nothing in
it composes a reply. CUPMem runs a chain of model calls and returns composed
prose; Mem0 returns the records it retrieved and stops.

That is a real difference between the systems and not a defect in either, so the
translation states it rather than hiding it. The top retrieved memory is reported
as `text`, exactly as the reference adapter reports the newest record in its
chain, and `system_metadata["answer_channel"]` says where it came from. A harness
comparing an extract-and-retrieve system against a compose-an-answer system on a
single accuracy column would be comparing two different tasks, and the field is
there so it can decline to.

Cost is instrumented, not native
---------------------------------
Mem0 exposes no usage counter. Its model calls go through the arena's metering
proxy, which prices them exactly, so cost here is `instrumented` where CUPMem's
is `native`. Both figures are real; only one of them the system could have told
us itself, and the arena keeps that distinction because *capability* and
*observability* are different axes.
"""

from __future__ import annotations

import time
from typing import Any

from arena.adapter import Answer, Cost, Measure

#: One bank per run. Mem0 scopes memories by id rather than by store, so reset
#: means emptying this scope rather than dropping a database.
BANK = "arena-pilot"

ANSWER_CHANNEL = "top retrieved memory; this system composes nothing"


def _elapsed_us(started: float) -> int:
    return int(round((time.monotonic() - started) * 1_000_000))


def _results(payload: Any) -> list[dict[str, Any]]:
    """Their return is `{"results": [...]}` in v1.1+ and a bare list before it."""
    if isinstance(payload, dict):
        found = payload.get("results")
        return [item for item in (found or []) if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _memory_text(item: dict[str, Any]) -> str:
    for key in ("memory", "text", "content"):
        value = item.get(key)
        if isinstance(value, str):
            return value
    return ""


class Mem0Adapter:
    """Requires a constructed `Memory`. This file does not build one.

    Its configuration — which model, which embedder, which vector store — belongs
    to whoever runs the arena, because those are the conditions the arena holds
    constant across systems rather than properties of the translation.
    """

    #: Their search path reads the vector store. Whether it writes is settled by
    #: the state probe on a live run, never by comparing two answers, so this
    #: stays `unknown` until that measurement exists.
    query_mutates_state = "unknown"

    name = "Mem0"

    def __init__(self, memory: Any, meter: Any = None, *, bank: str = BANK,
                 text_field: str = "text", limit: int = 10) -> None:
        self._memory = memory
        #: The arena's metering proxy, or None. Its call log is the only place
        #: this system's cost can be read from.
        self._meter = meter
        self._bank = bank
        self._text_field = text_field
        self._limit = limit

    # ----------------------------------------------------------------- contract

    #: How many delete passes to attempt before giving up. Their `delete_all`
    #: removes at most 100 rows per call and our units held 220-392, so one pass
    #: was never enough; a bound rather than `while True` because a store that
    #: stops shrinking must raise instead of spinning.
    MAX_RESET_PASSES = 64

    def _stored(self) -> int:
        payload = self._memory.get_all(user_id=self._bank, limit=100_000)
        rows = payload.get("results") if isinstance(payload, dict) else payload
        return len(rows or [])

    def reset(self) -> None:
        """Empty the bank, and prove it before returning.

        Their `delete_all` resolves the rows to remove with
        `vector_store.list(filters=...)` and passes no limit, while that method
        defaults to `limit=100`. One call therefore deletes at most a hundred
        memories however many the store holds.

        The first version of this method called it once and wrapped it in
        `try/except Exception: pass`. Both halves were wrong. Every arena unit
        stored 220-392 memories, so every reset left 120-292 behind, and by the
        tenth unit four of ten delivered evidence items belonged to four
        different earlier units — measured, not suspected. Contamination also
        reached the write path: as residue grew, Mem0's reconciliation
        increasingly chose UPDATE or NOOP over ADD, so later units stored fewer
        of their own memories.

        A reset either empties the store or raises. Silence is what let a
        contaminated store produce ten units of results that looked fine.
        """
        for _ in range(self.MAX_RESET_PASSES):
            before = self._stored()
            if not before:
                return
            self._memory.delete_all(user_id=self._bank)
            if self._stored() >= before:
                break  # no progress; a further pass would only spin
        remaining = self._stored()
        if remaining:
            raise RuntimeError(
                f"{self.name}: the bank {self._bank!r} could not be emptied — "
                f"{remaining} memories remain after {self.MAX_RESET_PASSES} delete "
                "passes. Continuing would let this unit's results carry the "
                "previous unit's memories."
            )

    def ingest(self, records: list[dict[str, Any]]) -> Cost:
        started = time.monotonic()
        before = self._meter_snapshot()

        messages = [
            {"role": "user", "content": str(record.get(self._text_field, "")).strip()}
            for record in records
        ]
        kept = [message for message in messages if message["content"]]
        if records and not kept:
            raise ValueError(
                f"{self.name}: ingest translated {len(records)} records into zero "
                "usable messages. Answering probes after this would measure the "
                "model's priors, not the system's memory."
            )

        timestamp = ""
        for record in records:
            for field in ("timestamp", "day", "date"):
                if record.get(field) not in (None, ""):
                    timestamp = str(record[field])
                    break
            if timestamp:
                break

        self._memory.add(messages=kept, user_id=self._bank,
                         metadata={"timestamp": timestamp} if timestamp else None)
        return self._cost_since(before, started)

    def query(self, question: str, asked_at: Any = None) -> Answer:
        started = time.monotonic()
        before = self._meter_snapshot()

        payload = self._memory.search(query=question, user_id=self._bank,
                                      limit=self._limit)
        results = _results(payload)
        texts = [_memory_text(item) for item in results]
        texts = [text for text in texts if text]

        return Answer(
            # Their top hit, reported as the answer because there is nothing else
            # to report. Named in the metadata so a harness can decline to score
            # it against a composed answer.
            text=texts[0] if texts else "",
            evidence_ids=[str(item.get("id", "")) for item in results if item.get("id")],
            context_tokens=sum(len(text.split()) for text in dict.fromkeys(texts)),
            abstained=not texts,
            cost=self._cost_since(before, started),
            system_metadata={
                "answer_channel": ANSWER_CHANNEL,
                "retrieved": len(results),
                "scores": [item.get("score") for item in results][:10],
                # The session timestamp each retrieved memory carries, in the
                # order retrieved. Reported raw so the harness can map evidence
                # back to a corpus session mechanically, by date, rather than by
                # guessing which passage a memory came from.
                # The delivered context itself, not merely its size. Counting
                # tokens and discarding the text made a later experiment
                # impossible: the fixed-reader run needed exactly this and the
                # stores had already been reset per unit, so nothing could be
                # looked up. A measurement that cannot be re-read is a
                # measurement that can only be taken once.
                "context_texts": list(dict.fromkeys(texts)),
                "evidence_times": [
                    str((item.get("metadata") or {}).get("timestamp", "") or "")
                    for item in results],
                # Returning nothing is the only decline this system can express,
                # and it is derivable, so `abstained` is a measurement here.
                "abstention_derivable": True,
                "abstention_channel": "empty result set",
                "cost_observability": self._cost_observability(),
                "context_tokens_basis": "distinct retrieved memory texts, whitespace-split",
                "context_tokens_is_floor": False,
                "context_tokens_measurable": True,
            },
        )

    # ------------------------------------------------------------------ helpers

    def _meter_snapshot(self) -> dict[str, int] | None:
        if self._meter is None:
            return None
        return self._meter.snapshot()

    def _cost_observability(self) -> dict[str, str]:
        source = "instrumented" if self._meter is not None else "unobservable"
        return {field: source for field in ("calls", "prompt_tokens", "completion_tokens")}

    def _cost_since(self, before: dict[str, int] | None, started: float) -> Cost:
        after = self._meter_snapshot()
        if before is None or after is None:
            unknown = Measure(None, "unobservable")
            return Cost(unknown, unknown, unknown,
                        Measure(_elapsed_us(started), "instrumented"))
        return Cost(
            model_calls=Measure(max(0, after["calls"] - before["calls"]), "instrumented"),
            input_tokens=Measure(max(0, after["prompt_tokens"] - before["prompt_tokens"]),
                                 "instrumented"),
            output_tokens=Measure(
                max(0, after["completion_tokens"] - before["completion_tokens"]),
                "instrumented"),
            wall_microseconds=Measure(_elapsed_us(started), "instrumented"),
        )
