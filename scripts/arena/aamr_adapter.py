"""The reference adapter: AAMR itself, proving the contract is implementable.

A contract nobody has implemented is a wish. This one exists so a contributor
writing an adapter for another system has a worked example, and so the validator
is tested against something real rather than a stub.

It wires the pieces this project already has — deterministic addressing from
`corpus.address_extract`, and the temporal resolver's rules — behind the three
methods the contract requires. No model, so `Cost` is genuinely zero rather than
zero by omission.

It is not expected to score well. `CANDIDATE-0` is a registered negative
artifact whose language-to-address bridge does not transfer, and this adapter
carries that limitation deliberately: the arena should measure the thing that
was frozen, not a quietly improved version of it.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.adapter import Answer, Cost, Measure  # noqa: E402
from corpus.address_extract import extract, extract_query  # noqa: E402


def _elapsed_us(started: float) -> int:
    """Microseconds since ``started``, as an integer.

    Rounded once at the point of measurement rather than at every addition, so
    the arena only ever sums integers.
    """
    return int(round((time.monotonic() - started) * 1_000_000))


def _time_of(record: dict[str, Any]) -> Any:
    """When this record was true, in whatever the arena's records carry.

    The fixture uses an integer `day`; a real corpus uses an ISO `timestamp`.
    Reading only `day` made every real record time zero, which silently switched
    the temporal filter off — the mechanism would then have been measured with
    its temporal half disabled and nothing would have said so.

    Format translation only. Which records the chain admits, and in what order,
    is unchanged.
    """
    for field in ("day", "timestamp", "date", "valid_from"):
        if record.get(field) not in (None, ""):
            return record[field]
    return None


def _not_after(record_time: Any, asked_at: Any) -> bool:
    """Was this record true by the time the question was asked?

    Comparable only when both sides are the same kind. ISO dates order correctly
    as strings and integer days as integers; comparing one against the other is
    not a late record, it is an unanswerable question, so it does not filter.
    """
    if asked_at is None or record_time is None:
        return True
    if isinstance(record_time, str) != isinstance(asked_at, str):
        return True
    return record_time <= asked_at


def _free(started: float) -> Cost:
    """A cost of zero that is genuinely measured, not merely unreported."""
    return Cost(
        model_calls=Measure(0, "native"),
        input_tokens=Measure(0, "native"),
        output_tokens=Measure(0, "native"),
        wall_microseconds=Measure(_elapsed_us(started), "instrumented"),
    )


class AAMRAdapter:
    """Deterministic addressing plus temporal resolution. No model anywhere."""

    #: addressing and chain ordering read the store and never write to it
    query_mutates_state = "read_only"

    name = "AAMR-CANDIDATE-0"

    def __init__(self) -> None:
        self._drawers: dict[str, list[dict[str, Any]]] = {}

    def reset(self) -> None:
        self._drawers = {}

    def ingest(self, records: list[dict[str, Any]]) -> Cost:
        started = time.monotonic()
        for record in records:
            address = extract(record["text"], canonicalise=True)
            if address:
                self._drawers.setdefault(address.canonical, []).append(record)
        # Zero is a claim here, not an unfilled default: this adapter calls no
        # model, so "native" is the honest observability rather than "unobservable".
        return Cost(
            model_calls=Measure(0, "native"),
            input_tokens=Measure(0, "native"),
            output_tokens=Measure(0, "native"),
            wall_microseconds=Measure(_elapsed_us(started), "instrumented"),
        )

    def query(self, question: str, asked_at: Any = None) -> Answer:
        started = time.monotonic()
        address = extract_query(question, canonicalise=True)

        if address is None or address.canonical not in self._drawers:
            # Abstention is a real answer here, not a fallback. A wrong address
            # opens someone else's drawer, which is worse than opening none.
            return Answer(text="", abstained=True, cost=_free(started),
                          system_metadata={"reason": "no address resolved",
                                           "abstention_derivable": True,
                                           "abstention_channel": "explicit: no address resolved"})

        chain = [r for r in self._drawers[address.canonical]
                 if _not_after(_time_of(r), asked_at)]
        if not chain:
            return Answer(text="", abstained=True, cost=_free(started),
                          system_metadata={"reason": "chain empty at query time",
                                           "abstention_derivable": True,
                                           "abstention_channel": "explicit: chain empty at query time"})

        # Newest first. An addressed chain arrives time-ordered, which is why the
        # resolver is a no-op on simple succession — measured in PMLAB-H1-COMPOSE-E1.
        # Newest first. An addressed chain arrives time-ordered, which is why the
        # resolver is a no-op on simple succession — measured in PMLAB-H1-COMPOSE-E1.
        # Sorted by string so an ISO date and an integer day both order, and
        # zero-padded so 9 does not sort above 10.
        chain.sort(key=lambda r: f"{_time_of(r):>020}" if _time_of(r) is not None else "",
                   reverse=True)
        return Answer(
            text=chain[0]["text"],
            evidence_ids=[r["id"] for r in chain],
            context_tokens=sum(len(r["text"].split()) for r in chain),
            abstained=False,
            cost=_free(started),
            system_metadata={"address": address.canonical, "chain_length": len(chain),
                             "abstention_derivable": True,
                             "abstention_channel": "explicit: no address resolved"},
        )
