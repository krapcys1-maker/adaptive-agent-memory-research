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

    def reset(self) -> None:
        try:
            self._memory.delete_all(user_id=self._bank)
        except Exception:  # noqa: BLE001
            # An empty scope raises in some backends. Nothing to clear is the
            # state reset is for, so it is not an error — but it is also not
            # silently assumed: the state probe checks the digest returned.
            pass

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
