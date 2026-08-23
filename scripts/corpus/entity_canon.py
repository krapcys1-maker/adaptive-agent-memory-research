"""E2-A3: recognise the entity in interrogative grammar as well as assertive.

Status: **post-hoc mechanistic follow-up, preregistered before execution.**

Proposed after E2-A2, which fixed property resolution and moved the bottleneck
rather than removing it. On the three families still at 0.000 — DELAYED,
OBSOLETE, POISON — the property resolved every time and the entity returned
None:

    Which staging host should a orders deploy target, and on which port?
      property  endpoint.host   correct
      entity    None

The cause is the same one A2 addressed, on the other field. `E2-A`'s entity
patterns were written against the grammar records use, where the entity is a
possessor or a prepositional object of an assertion:

    Staging for orders deploys to ...
    Deploy log for orders: ...

Questions place it as the subject of a modal, the object of a gerund, or the
object of a locative:

    ... should a orders deploy target ...
    Before deploying orders, ...
    pool exhaustion in orders again

Same entry criterion as the property layer
-------------------------------------------
Each pattern names a **grammatical construction** in which an entity can appear,
not a phrase observed in the corpus. A pattern written until the development set
passes describes the development set. The test of that is transfer: `valid-b`
uses twelve entirely different subject nouns, and the property layer scored
identically on both splits.
"""

from __future__ import annotations

import re
from typing import Any

# Interrogative and gerundive positions, which the assertion-grammar rules miss.
_QUESTION_POSITIONS = (
    # "should a orders deploy target" / "should the orders suite be run"
    re.compile(r"\bshould\s+(?:a|an|the)\s+([a-z][a-z-]{2,})\b", re.I),
    # "Before deploying orders, ..." / "after deploying orders"
    re.compile(r"\bdeploying\s+([a-z][a-z-]{2,})\b", re.I),
    # "pool exhaustion in orders again" / "failures in orders"
    re.compile(r"\b(?:in|for|of)\s+([a-z][a-z-]{2,})\s+(?:again|now|today)\b", re.I),
    # "Why was the orders retry loop removed" — assertion rules require "the X retry loop"
    # exactly; this accepts an intervening modifier.
    re.compile(r"\bwas\s+the\s+([a-z][a-z-]{2,})\b", re.I),
    # "what should happen to the orders audit"
    re.compile(r"\bhappen\s+to\s+the\s+([a-z][a-z-]{2,})\b", re.I),
    # trailing prepositional object: "... exhaustion in orders?"
    re.compile(r"\b(?:in|for)\s+([a-z][a-z-]{2,})[\s,?.]", re.I),
)

# Shared with the assertion layer. A word that is grammatically in an entity
# position and is not an entity must be rejected in both, or the two layers
# disagree about what an entity is.
_NOT_AN_ENTITY = frozenset({
    "the", "a", "an", "this", "that", "our", "your", "its", "their", "all",
    "staging", "production", "prod", "test", "tests", "suite", "deploy",
    "release", "host", "port", "client", "log", "key", "and", "for", "with",
    "what", "which", "where", "when", "why", "how", "before", "after",
    "every", "any", "some", "one", "two", "old", "new", "previous", "current",
})


def canonical_entity(text: str) -> str | None:
    """The entity this text concerns, from interrogative positions, or None."""
    for pattern in _QUESTION_POSITIONS:
        match = pattern.search(text)
        if not match:
            continue
        candidate = match.group(1).lower().strip("-")
        if candidate and candidate not in _NOT_AN_ENTITY and not candidate.isdigit():
            return f"service.{candidate}"
    return None


def describe() -> dict[str, Any]:
    return {
        "arm": "E2-A3 deterministic + property canon + entity canon",
        "status": "post-hoc mechanistic follow-up, preregistered before execution",
        "proposed_after": "E2-A2, where property resolved and entity returned None on three families",
        "model": None,
        "api_cost_usd": 0.0,
        "question_positions": len(_QUESTION_POSITIONS),
        "entry_criterion": (
            "each pattern names a grammatical construction in which an entity can appear, not a "
            "phrase observed in the corpus. Transfer to valid-b is the test of that"
        ),
    }
