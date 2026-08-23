"""ARENA-0: the adapter contract every memory system must satisfy.

Buildable and verifiable with no benchmark, no infrastructure and no spend. An
adapter can be written, validated and accepted before a single paid run.

The one rule that decides whether the arena means anything
-----------------------------------------------------------
**An adapter reports raw signals. It never interprets them.**

If each adapter decided for itself what counts as a *retrieval failure*, every
system would grade its own exam, and the failure-type matrix — the whole point of
the comparison — would be an artefact of five different opinions. So an adapter
returns what happened, and this repository's harness decides what it means.

    adapter says   "I answered X, from these records, in N tokens"
    harness says   "that is a state_failure, attributed to retrieval"

Cost is part of the mechanism, not preparation
-----------------------------------------------
A system whose ingestion calls a model per item is not free just because the
call happens before query time. Hindsight's extraction is one structured call
per content item; at STALE's 400 scenarios that is a real cost belonging to the
mechanism.

So `ingest` and `query` both return their model calls, tokens and wall time
separately, and

    90% accuracy with paid ingestion
    88% accuracy with no model calls at all

is not obviously a win for the first. The table has to be able to say so.

What an adapter must not do
---------------------------
- decide its own failure taxonomy
- see the gold answer, at any point
- persist state between `reset()` calls
- vary any condition the frozen contract fixes
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Cost:
    """What one operation consumed. Zero is a claim, not a default."""

    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    wall_seconds: float = 0.0

    def __add__(self, other: "Cost") -> "Cost":
        return Cost(
            self.model_calls + other.model_calls,
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            round(self.wall_seconds + other.wall_seconds, 6),
        )


@dataclass(frozen=True)
class Answer:
    """Everything an adapter reports, and nothing it concludes.

    ``evidence_ids`` is what the system actually put in front of its reader —
    not what it stored and not what it considered. The harness needs it to
    separate *never retrieved* from *retrieved and misused*, which are different
    failures needing different work.
    """

    text: str
    evidence_ids: list[str] = field(default_factory=list)
    context_tokens: int = 0
    abstained: bool = False
    cost: Cost = field(default_factory=Cost)
    system_metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class MemoryAdapter(Protocol):
    """Three methods. Anything more is the harness's job.

    Deliberately minimal: a contributor can implement this against a system they
    know without understanding this project, and the validator accepts or rejects
    it mechanically.
    """

    name: str

    def reset(self) -> None:
        """Discard all state. The next ingest must behave like the first."""

    def ingest(self, records: list[dict[str, Any]]) -> Cost:
        """Store records. Returns what storing them cost, including model calls."""

    def query(self, question: str, asked_at: Any = None) -> Answer:
        """Answer from memory alone. Never given the gold, never given the family."""


# --------------------------------------------------------------------------- validation


REQUIRED_METHODS = ("reset", "ingest", "query")


def validate_adapter(adapter: Any, fixture: dict[str, Any]) -> dict[str, Any]:
    """Run an adapter against a synthetic fixture and check it obeys the contract.

    No benchmark and no spend. It answers whether an adapter is *admissible*,
    never whether it is good — and rejecting a non-conforming adapter here costs
    nothing, while discovering it mid-run costs the run.
    """
    problems: list[str] = []

    for method in REQUIRED_METHODS:
        if not callable(getattr(adapter, method, None)):
            problems.append(f"missing method: {method}")
    if not getattr(adapter, "name", None):
        problems.append("missing attribute: name")
    if problems:
        return {"admissible": False, "problems": problems}

    adapter.reset()
    started = time.monotonic()
    ingest_cost = adapter.ingest(fixture["records"])
    elapsed = time.monotonic() - started

    if not isinstance(ingest_cost, Cost):
        problems.append("ingest must return a Cost")
    elif ingest_cost.wall_seconds == 0.0 and elapsed > 0.5:
        # Not fatal: a fast adapter legitimately reports ~0. But a slow one
        # reporting 0 is under-reporting, and cost is part of the mechanism.
        problems.append("ingest took over 0.5s and reported zero wall time")

    answers = []
    for probe in fixture["probes"]:
        answer = adapter.query(probe["question"], probe.get("asked_at"))
        if not isinstance(answer, Answer):
            problems.append(f"query returned {type(answer).__name__}, expected Answer")
            break
        answers.append(answer)
        if answer.abstained and answer.text.strip():
            problems.append("abstained=True with non-empty text; the harness cannot score both")
        if answer.context_tokens < 0:
            problems.append("negative context_tokens")

    # Reset must actually reset. An adapter that keeps state between runs makes
    # every later arm dependent on the order the arena happened to run them in.
    adapter.reset()
    after_reset = adapter.query(fixture["probes"][0]["question"],
                                fixture["probes"][0].get("asked_at"))
    if after_reset.evidence_ids:
        problems.append("reset() did not clear state: evidence returned from an empty store")

    return {
        "admissible": not problems,
        "problems": problems,
        "adapter": getattr(adapter, "name", "?"),
        "probes_answered": len(answers),
        "ingest_cost": vars(ingest_cost) if isinstance(ingest_cost, Cost) else None,
        "mean_context_tokens": (
            round(sum(a.context_tokens for a in answers) / len(answers), 3) if answers else None
        ),
        "abstentions": sum(1 for a in answers if a.abstained),
        "note": ("admissible means the adapter obeys the contract, never that the system is good. "
                 "Rejecting one here costs nothing; discovering it mid-run costs the run"),
    }


# --------------------------------------------------------------------------- fixture


def synthetic_fixture() -> dict[str, Any]:
    """A tiny corpus exercising each thing the contract cares about.

    Deliberately not a benchmark. It contains a superseded fact, an exact literal
    that must not be fuzzy-matched, two near-identical entities, and a question
    with no answer — enough to catch an adapter that abstains wrongly, corrupts a
    literal, or merges distinct entities, before any of that costs money.
    """
    return {
        "records": [
            {"id": "r1", "day": 1, "text": "The billing staging host is https://a.internal:8443."},
            {"id": "r2", "day": 2, "text": "The vault staging host is https://b.internal:8443."},
            {"id": "r3", "day": 9, "text": "Correction: billing staging is now https://c.internal:8443."},
            {"id": "r4", "day": 3, "text": "Run the contract suite with --dist=no, never --dist=yes."},
        ],
        "probes": [
            {"id": "p1", "asked_at": 20, "question": "Which host should a billing deploy target?"},
            {"id": "p2", "asked_at": 20, "question": "Which flag does the contract suite need?"},
            {"id": "p3", "asked_at": 20, "question": "What is the roster staging host?"},
        ],
        "what_each_probe_is_for": {
            "p1": "supersession — r3 is the answer, r1 is the trap",
            "p2": "literal exactness — --dist=no must not become --dist=yes",
            "p3": "no answer exists; a system that answers confidently is wrong",
        },
    }
