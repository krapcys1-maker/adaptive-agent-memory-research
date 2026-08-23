"""Hindsight adapter. Translates their HTTP surface to the arena contract.

    contract            Hindsight
    reset()             DELETE /v1/default/banks/{bank}/memories
    ingest(records)     POST   /v1/default/banks/{bank}/memories
    query(question)     POST   /v1/default/banks/{bank}/memories/recall

Spoken over plain HTTP rather than through their generated client, so what this
file translates is the wire shape their server actually returns rather than a
second party's model of it. That is the same reason the CUPMem double was
rebuilt from their code: a description of a shape is not the shape.

The two things this system does that the others do not
-------------------------------------------------------
**Retain is asynchronous by design.** Their server accepts a batch and processes
it on a worker. An adapter that returned the moment the POST did would report an
ingest that had not happened, and a query issued straight after would read an
empty store while every number downstream stayed plausible — the exact defect
CUPMem's first run shipped. So `ingest` submits synchronously and, when the
server defers anyway, waits until the bank's memory count stops moving before
returning.

**Cost is not theirs to report and not ours to read directly.** Hindsight runs in
its own process and builds its own provider client, so neither the contract's
`Cost` nor any counter inside it can see the spend. Its model calls are pointed
at the arena's metering proxy, which is where every figure here comes from, and
the observability is recorded as `instrumented` rather than `native`.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
import urllib.error
import urllib.request
from typing import Any

from arena.adapter import Answer, Cost, Measure

BANK = "arena-pilot"

ANSWER_CHANNEL = "top recalled memory; this system retrieves and does not compose"


def _elapsed_us(started: float) -> int:
    return int(round((time.monotonic() - started) * 1_000_000))


#: The corpus writes session dates as `2022/09/01 (Thu) 00:10`. Their server takes
#: ISO and rejects anything else with a 422, so the same instant is handed over in
#: the form this system can use. Format translation, and the alternative is worse:
#: sending no timestamp would silently disable the temporal reasoning this system
#: is partly built on, and every number after it would still look plausible — the
#: defect already found once in the reference adapter's clock.
_DATE_FORMATS = (
    "%Y/%m/%d (%a) %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)


def _iso_timestamp(value: Any) -> str | None:
    """The instant this record carries, in ISO, or None if it carries none.

    `None` rather than a guess: a fabricated date would put a memory somewhere on
    their timeline that the corpus never claimed.
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return None


class HindsightHTTP:
    """The smallest client that can speak to their server, and no model of it."""

    def __init__(self, base_url: str = "http://127.0.0.1:8801", timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def call(self, method: str, path: str, payload: Any = None) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as failure:
            body = failure.read()
            raise RuntimeError(
                f"Hindsight {method} {path} -> {failure.code}: {body[:400]!r}") from failure
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"raw": body.decode(errors="replace")}


def _results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        found = payload.get("results")
        return [item for item in (found or []) if isinstance(item, dict)]
    return []


def _memory_text(item: dict[str, Any]) -> str:
    for key in ("content", "memory", "text", "fact", "summary"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


class HindsightAdapter:
    """Requires a running server. This file does not start one.

    Its configuration — provider, model, embedder, database — belongs to whoever
    runs the arena, because those are conditions the comparison holds constant
    rather than properties of the translation.
    """

    #: Their recall path is answered by the state probe on a live run, never by
    #: comparing two answers. It stays `unknown` until that measurement exists —
    #: and their server consolidates on a background worker, so a change observed
    #: after a query is not necessarily caused by it. That ambiguity is recorded
    #: rather than resolved in the system's favour.
    query_mutates_state = "unknown"

    name = "Hindsight"

    def __init__(self, http: HindsightHTTP, meter: Any = None, *, bank: str = BANK,
                 text_field: str = "text", settle_seconds: float = 120.0) -> None:
        self._http = http
        self._meter = meter
        self._bank = bank
        self._text_field = text_field
        self._settle_seconds = settle_seconds
        #: Records whose corpus date could not be parsed into their format.
        #: Reported rather than absorbed: each one is a memory with no place on
        #: their timeline.
        self.unparsed_timestamps = 0
        self._ensure_bank()

    # ------------------------------------------------------------------- setup

    def _ensure_bank(self) -> None:
        try:
            self._http.call("PUT", f"/v1/default/banks/{self._bank}", {})
        except RuntimeError:
            # Already present. Creating it is idempotent from the arena's side;
            # the reset below is what actually guarantees an empty store.
            pass

    def _count(self) -> int:
        payload = self._http.call("GET", f"/v1/default/banks/{self._bank}/memories/list?limit=1")
        if isinstance(payload, dict):
            for key in ("total", "count", "total_count"):
                if isinstance(payload.get(key), int):
                    return payload[key]
            return len(_results(payload))
        return 0

    # ---------------------------------------------------------------- contract

    def reset(self) -> None:
        self._http.call("DELETE", f"/v1/default/banks/{self._bank}/memories")

    def ingest(self, records: list[dict[str, Any]]) -> Cost:
        started = time.monotonic()
        before = self._meter_snapshot()

        items = []
        undated = 0
        for record in records:
            content = str(record.get(self._text_field, "")).strip()
            if not content:
                continue
            stamp = _iso_timestamp(record.get("timestamp"))
            undated += stamp is None and bool(record.get("timestamp"))
            items.append({"content": content,
                          "timestamp": stamp or "unset"})
        if undated:
            # Loud, not silent. A record whose date could not be read is a record
            # placed nowhere on their timeline, and that is a fact about this run.
            self.unparsed_timestamps += undated
        if records and not items:
            raise ValueError(
                f"{self.name}: ingest translated {len(records)} records into zero "
                "usable items. Answering probes after this would measure the "
                "model's priors, not the system's memory."
            )

        # `async: False` asks their server to finish before answering. It is asked
        # for rather than assumed, and the settle below covers the case where the
        # server defers anyway.
        self._http.call("POST", f"/v1/default/banks/{self._bank}/memories",
                        {"items": items, "async": False})
        self._settle()
        return self._cost_since(before, started)

    def _settle(self) -> None:
        """Wait until the bank's memory count stops moving.

        An ingest that returns before the worker has finished is an ingest that
        did not happen, and every number measured after it stays plausible. Two
        consecutive equal counts, with a deadline, because waiting forever on a
        stuck worker is its own failure.
        """
        deadline = time.monotonic() + self._settle_seconds
        previous = -1
        stable = 0
        while time.monotonic() < deadline:
            current = self._count()
            stable = stable + 1 if current == previous else 0
            previous = current
            if stable >= 2:
                return
            time.sleep(1.0)

    def query(self, question: str, asked_at: Any = None) -> Answer:
        started = time.monotonic()
        before = self._meter_snapshot()

        payload: dict[str, Any] = {"query": question, "max_tokens": 4096}
        if asked_at:
            payload["query_timestamp"] = str(asked_at)
        result = self._http.call(
            "POST", f"/v1/default/banks/{self._bank}/memories/recall", payload)

        results = _results(result)
        texts = [t for t in (_memory_text(item) for item in results) if t]

        return Answer(
            text=texts[0] if texts else "",
            evidence_ids=[str(item.get("id", "")) for item in results if item.get("id")],
            context_tokens=sum(len(text.split()) for text in dict.fromkeys(texts)),
            abstained=not texts,
            cost=self._cost_since(before, started),
            system_metadata={
                "answer_channel": ANSWER_CHANNEL,
                "retrieved": len(results),
                "scores": [item.get("score") for item in results][:10],
                "abstention_derivable": True,
                "abstention_channel": "empty result set",
                "cost_observability": self._cost_observability(),
                "context_tokens_basis": "distinct recalled memory texts, whitespace-split",
                "context_tokens_is_floor": False,
                "context_tokens_measurable": True,
                "unparsed_timestamps": self.unparsed_timestamps,
            },
        )

    # ----------------------------------------------------------------- helpers

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
