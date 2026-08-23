"""ARENA-0.1: the contract, amended in exactly one place.

ARENA-0 remains in `adapter.py`, unedited, as the historical artefact. Results
produced under it stay labelled with it and must never share a table with these
without an explicit version column.

What changed, and why
---------------------
ARENA-0 decided whether querying mutates memory by asking one probe twice and
comparing the two **answers**. Against a sampling model that inference does not
hold, and it broke in the field:

    a live run fingerprinted everything CUPMem's own reset() clears, either
    side of a query, and got identical digests — the store did not change

    the same contract check, on the next run, reported "declared read_only but
    a repeated query returned different results" and rejected the adapter

    measured directly: deepseek-chat at temperature 0 returned 4 distinct
    outputs in 20 identical free-form requests, and 3 in 20 structured ones

So ARENA-0's `read_only` was silently a conjunction — *read-only* **and**
*reproducible* — which no model-backed system can satisfy. An adapter holding a
proof of the first had to declare `unknown` to stay admissible, and the arena
threw away the very fact it needs in order to keep probes comparable.

ARENA-0.1 splits the conjunction:

    query_mutates_state    read_only | mutates_by_design | unknown
                           decided by observing STATE, through a probe. Never
                           inferred from a difference between two answers.

    output_reproducible    true | false | unknown
                           decided by repeating a request. A property of the
                           decoder, reported beside the systems it affects and
                           never charged to any of them.

The two are independent, and `read_only` with `output_reproducible: false` is
the ordinary case for a memory system driven by a sampling model. It is not a
contradiction and is no longer treated as one.

What did not change
-------------------
`Measure`, `Cost`, `Answer` and the three-method protocol are imported from
ARENA-0 unchanged, so this is an amendment rather than a rewrite, and the two
versions differ in exactly the place named above.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from arena.adapter import (  # noqa: F401  — unchanged from ARENA-0, re-exported
    Answer, Cost, Measure, MUTATION_MODES, OBSERVABILITY, REQUIRED_METHODS,
    synthetic_fixture,
)

CONTRACT_VERSION = "ARENA-0.1"

#: Whether a repeated identical request returns a repeated identical answer.
#: A property of the decoder and the deployment, not of the memory system, and
#: recorded separately so it is never charged to one.
OUTPUT_REPRODUCIBILITY = ("true", "false", "unknown")


def contract_digest() -> str:
    """A digest over this file, so a result can name the contract it ran under."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class StateProbe(Protocol):
    """How a system's state is observed. Supplied per system, never by the adapter."""

    def fingerprint(self) -> str:
        """A digest over everything the system holds. Equal digests, equal state."""


@runtime_checkable
class MemoryAdapter(Protocol):
    """Three methods, and two declarations that are no longer one."""

    name: str

    #: One of ``MUTATION_MODES``, about STATE. `mutates_by_design` is a property
    #: to control for, not a defect; `read_only` contradicted by an observed
    #: state change is a defect. A difference between two answers is not evidence
    #: either way.
    query_mutates_state: str

    def reset(self) -> None:
        """Discard all state. The next ingest must behave like the first."""

    def ingest(self, records: list[dict[str, Any]]) -> Cost:
        """Store records. Returns what storing them cost, including model calls."""

    def query(self, question: str, asked_at: Any = None) -> Answer:
        """Answer from memory alone. Never given the gold, never given the family."""


def validate_adapter(adapter: Any, fixture: dict[str, Any], *,
                     probe: StateProbe | None = None) -> dict[str, Any]:
    """Does this adapter obey ARENA-0.1? Admissible, never good.

    With a probe, mutation is observed. Without one it is `unknown`, which is
    recorded and is not a failure — a system that cannot expose its state is a
    system whose comparability must be controlled for another way, not one that
    is thrown out.
    """
    problems: list[str] = []

    for method in REQUIRED_METHODS:
        if not callable(getattr(adapter, method, None)):
            problems.append(f"missing method: {method}")
    if not getattr(adapter, "name", None):
        problems.append("missing attribute: name")
    if problems:
        return {"contract_version": CONTRACT_VERSION, "admissible": False,
                "problems": problems}

    adapter.reset()
    empty_state = probe.fingerprint() if probe else None

    started = time.monotonic()
    ingest_cost = adapter.ingest(fixture["records"])
    elapsed = time.monotonic() - started

    if not isinstance(ingest_cost, Cost):
        problems.append("ingest must return a Cost")
    elif any(getattr(ingest_cost, f).observability not in OBSERVABILITY
             for f in Cost._FIELDS):
        problems.append("a cost field declares an observability outside the vocabulary")
    elif not ingest_cost.wall_microseconds.value and elapsed > 0.5:
        problems.append("ingest took over 0.5s and reported zero wall time")

    declared = getattr(adapter, "query_mutates_state", "unknown")
    if declared not in MUTATION_MODES:
        problems.append(f"query_mutates_state must be one of {MUTATION_MODES}")

    # -- the amendment, in code ------------------------------------------------
    # Two measurements where ARENA-0 took one. State first, because that is the
    # question the declaration answers.
    entry = fixture["probes"][0]
    before = probe.fingerprint() if probe else None
    first = adapter.query(entry["question"], entry.get("asked_at"))
    after = probe.fingerprint() if probe else None
    second = adapter.query(entry["question"], entry.get("asked_at"))
    after_repeat = probe.fingerprint() if probe else None

    observed_mutation = (None if probe is None
                         else not (before == after == after_repeat))
    reproducible = ("true" if (first.text, first.evidence_ids)
                    == (second.text, second.evidence_ids) else "false")

    if observed_mutation is True and declared == "read_only":
        problems.append("declared read_only but querying changed stored state")
    if observed_mutation is False and declared == "mutates_by_design":
        problems.append("declared mutates_by_design but querying changed no state")
    # Deliberately absent: any rule that turns `reproducible == "false"` into a
    # problem. That was ARENA-0's defect, and reinstating it here in another
    # spelling would undo the amendment.

    answers: list[Answer] = []
    for entry in fixture["probes"]:
        answer = adapter.query(entry["question"], entry.get("asked_at"))
        if not isinstance(answer, Answer):
            problems.append(f"query returned {type(answer).__name__}, expected Answer")
            break
        answers.append(answer)
        if answer.abstained and answer.text.strip():
            problems.append("abstained=True with non-empty text; the harness cannot score both")
        if answer.context_tokens < 0:
            problems.append("negative context_tokens")

    adapter.reset()
    reset_state = probe.fingerprint() if probe else None
    after_reset = adapter.query(fixture["probes"][0]["question"],
                                fixture["probes"][0].get("asked_at"))
    if after_reset.evidence_ids:
        problems.append("reset() did not clear state: evidence returned from an empty store")
    if probe is not None and reset_state != empty_state:
        problems.append("reset() did not restore the pre-ingest state digest")

    return {
        "contract_version": CONTRACT_VERSION,
        "contract_digest": contract_digest(),
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

        "query_mutates_state": {
            "declared": declared,
            "observed": ("unknown" if observed_mutation is None
                         else "mutates_by_design" if observed_mutation else "read_only"),
            "how": ("state fingerprint either side of a query" if probe
                    else "no state probe supplied"),
        },
        "output_reproducible": {
            "observed": reproducible,
            "how": "one probe issued twice, answers and evidence compared",
            "note": ("a property of the decoder and the deployment. It is reported "
                     "here because it bounds what a single run can claim, and it is "
                     "never charged to the memory system"),
        },
        "note": ("admissible means the adapter obeys ARENA-0.1, never that the system "
                 "is good. Results under this version must not share a table with "
                 "ARENA-0 results without a version column"),
    }
