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


OBSERVABILITY = ("native", "instrumented", "unobservable")


@dataclass(frozen=True)
class Measure:
    """One quantity, and how we came to know it.

    ``value is None`` means the system cannot report this quantity. Zero means it
    reported zero. Those are different facts and a single number cannot hold
    both.

    Values are integers. Durations are microseconds, converted to seconds only
    for display, because integer addition is exactly associative and rounded
    float addition is not — and a cost table that varies with summation order
    over identical data would read as a property of the system under test.
    """

    value: int | None = 0
    observability: str = "native"
    lower_bound: bool = False

    @property
    def known(self) -> bool:
        """Fully known. A lower bound carries a number and is not this."""
        return self.value is not None and not self.lower_bound

    def __add__(self, other: "Measure") -> "Measure":
        # Weakest observability wins: a total is only as trustworthy as its least
        # trustworthy part.
        rank = {"native": 0, "instrumented": 1, "unobservable": 2}
        weakest = max((self.observability, other.observability), key=lambda o: rank[o])

        if self.value is not None and other.value is not None:
            # Integers throughout, so addition is exactly associative rather
            # than approximately so. Rounding each float sum to microseconds was
            # tried first and is not a guarantee: a targeted search near the
            # half-microsecond boundary found 17,338 associativity violations in
            # 54,872 triples, while 400,000 random triples found none. Random
            # values almost never land on the boundary, so the property test
            # passed while the property did not hold.
            return Measure(self.value + other.value, weakest,
                           self.lower_bound or other.lower_bound)

        # One side is unknown. The known side is a real measurement and throwing
        # it away would lose information, so it is kept and flagged as a floor.
        #
        # A first version returned it without the flag, and `fully_known` then
        # reported True for a partial total — the same aggregation-destroys-
        # provenance error this class exists to prevent, committed inside the
        # fix for it.
        present = [m for m in (self, other) if m.value is not None]
        if not present:
            return Measure(None, "unobservable")

        floor = sum(m.value for m in present)
        if not floor:
            # A floor of zero carries no information, so adding a known zero to
            # an unknown must leave it unknown. Otherwise `A + ZERO == A` fails
            # for unknowns, and a run total would depend on how many zero-cost
            # operations happened to be summed — the cost table would vary with
            # summation order over identical data.
            return Measure(None, "unobservable")
        return Measure(floor, "unobservable", lower_bound=True)


@dataclass(frozen=True)
class Cost:
    """What one operation consumed, per field, with how each was known.

    A single ``measured`` flag was tried first and produced a contradiction. It
    forced a sum of a measured ingest and an unmeasured query either to be
    rejected as inconsistent, or to discard the ingest figure that had genuinely
    been measured. Neither is acceptable: the honest reading of

        ingest  12 calls, 40,000 tokens, measured
        query   unmeasurable

    is *at least 12 calls and at least 40,000 tokens, total unknown* — a lower
    bound, not a contradiction and not a zero.

    Per-field observability also carries a distinction one flag cannot. A system
    may know perfectly well that it called a model 17 times and still not expose
    token usage, and reporting the whole cost as unmeasured would hide a figure
    it actually has.
    """

    model_calls: Measure = field(default_factory=Measure)
    input_tokens: Measure = field(default_factory=Measure)
    output_tokens: Measure = field(default_factory=Measure)
    wall_microseconds: Measure = field(default_factory=Measure)

    _FIELDS = ("model_calls", "input_tokens", "output_tokens", "wall_microseconds")

    @property
    def wall_seconds(self) -> float | None:
        """Presentation only. Every stored quantity is an integer."""
        value = self.wall_microseconds.value
        return None if value is None else value / 1_000_000

    def __add__(self, other: "Cost") -> "Cost":
        return Cost(**{f: getattr(self, f) + getattr(other, f) for f in Cost._FIELDS})

    @property
    def fully_known(self) -> bool:
        """Every field reported. Only then is a total a total."""
        return all(getattr(self, f).known for f in Cost._FIELDS)

    @property
    def is_lower_bound(self) -> bool:
        """Any field carries a floor rather than a total."""
        return any(getattr(self, f).lower_bound for f in Cost._FIELDS)

    def summary(self) -> dict[str, Any]:
        return {
            f: {"value": getattr(self, f).value,
                "observability": getattr(self, f).observability,
                "lower_bound": getattr(self, f).lower_bound}
            for f in Cost._FIELDS
        } | {"fully_known": self.fully_known, "is_lower_bound": self.is_lower_bound}


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


# Whether querying changes stored state. Declared by the adapter, checked by the
# validator, and never inferred — a system that learns during recall is not
# broken, but an arena that does not know which systems do cannot keep probes
# comparable.
MUTATION_MODES = ("read_only", "mutates_by_design", "unknown")


@runtime_checkable
class MemoryAdapter(Protocol):
    """Three methods. Anything more is the harness's job.

    Deliberately minimal: a contributor can implement this against a system they
    know without understanding this project, and the validator accepts or rejects
    it mechanically.
    """

    name: str

    #: One of ``MUTATION_MODES``. ``mutates_by_design`` is a property to control
    #: for, not a defect; ``read_only`` contradicted by behaviour is a defect.
    query_mutates_state: str

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
    elif any(getattr(ingest_cost, f).observability not in OBSERVABILITY
             for f in Cost._FIELDS):
        problems.append("a cost field declares an observability outside the vocabulary")
    elif not ingest_cost.wall_microseconds.value and elapsed > 0.5:
        # Not fatal: a fast adapter legitimately reports ~0. But a slow one
        # reporting 0 is under-reporting, and cost is part of the mechanism.
        problems.append("ingest took over 0.5s and reported zero wall time")

    # Does querying change what a later query sees? Asked by querying twice and
    # comparing, then judged against what the adapter declared.
    #
    # Mutation is not itself a failure. A system that learns during recall has a
    # property the arena must control for — repeat a probe, or fix probe order —
    # and only an undeclared mutation is a defect, because the harness would then
    # be comparing probes that are not comparable.
    declared = getattr(adapter, "query_mutates_state", "unknown")
    if declared not in MUTATION_MODES:
        problems.append(f"query_mutates_state must be one of {MUTATION_MODES}")

    probe = fixture["probes"][0]
    first = adapter.query(probe["question"], probe.get("asked_at"))
    second = adapter.query(probe["question"], probe.get("asked_at"))
    observed_mutation = (first.text, first.evidence_ids) != (second.text, second.evidence_ids)
    if observed_mutation and declared == "read_only":
        problems.append(
            "declared read_only but a repeated query returned different results; "
            "either the declaration is wrong or the system is nondeterministic"
        )

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
        "ingest_cost": ingest_cost.summary() if isinstance(ingest_cost, Cost) else None,
        "cost_fully_known": (
            isinstance(ingest_cost, Cost) and ingest_cost.fully_known
            and all(a.cost.fully_known for a in answers)
        ),
        "cost_is_lower_bound": (
            isinstance(ingest_cost, Cost)
            and (ingest_cost.is_lower_bound or any(a.cost.is_lower_bound for a in answers))
        ),
        "mean_context_tokens": (
            round(sum(a.context_tokens for a in answers) / len(answers), 3) if answers else None
        ),
        "abstentions": sum(1 for a in answers if a.abstained),
        "query_mutates_state": declared,
        "repeated_query_differed": observed_mutation,
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
