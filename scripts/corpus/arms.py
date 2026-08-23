"""Retention arms for corpus H1, all held to one token budget.

The fairness control that makes this a comparison
--------------------------------------------------
The protocol requires the *same active-context token budget* across arms. Without
it a comparison measures context size, not memory: an arm handed twice the budget
answers more and has demonstrated nothing about what it chose to keep.

So every arm here returns events until a shared budget is spent, and the arm's
only freedom is **which events, in what order**. That is exactly the question the
project is asking.

The arms
--------
``recency``      the last events before the probe. What naive compaction does.
``frequency``    events whose text recurs most. What a repetition-weighted
                 retention policy does, and the policy the OBSOLETE family is
                 built to destroy — the obsolete host is stated three times and
                 its correction once.
``fts5``         lexical retrieval against the question. Needs the question,
                 which the other two do not: it is a retriever, not a retention
                 policy, and that difference is the point rather than a flaw.
``random``       a seeded sample at the same budget. Present because a floor
                 that no arm beats is the most useful negative result available,
                 and because "better than nothing" is a claim that needs a
                 nothing to compare against.

Two of these cannot see the question and two can. That is not an oversight to be
corrected by handing everyone the question — it is the distinction between
deciding what to keep and deciding what to fetch, and the protocol treats them as
different arms for that reason.

Tokens
------
Whitespace words, not a model tokenizer. The budget is therefore approximate in
absolute terms and exact in relative terms, which is what a comparison needs.
Using a real tokenizer would tie the corpus to one vendor's vocabulary and change
every frozen number when that vocabulary changed.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator

# One budget for every arm. Roughly the retrieval depth the baseline used, so
# the arms are comparable with PMLAB-H1-BASE-E1 as well as with each other.
DEFAULT_TOKEN_BUDGET = 250


def _cost(event: dict[str, Any]) -> int:
    return len(event["text"].split())


def _fill(ordered: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    """Take events in the arm's order until the shared budget is spent.

    An event that would overshoot is skipped rather than ending the fill, so an
    arm is not punished for ranking one long event highly. Every arm gets the
    same rule.
    """
    kept, spent = [], 0
    for event in ordered:
        price = _cost(event)
        if spent + price > budget:
            continue
        kept.append(event)
        spent += price
    return kept


def _before(events: list[dict[str, Any]], day: int) -> list[dict[str, Any]]:
    """Only what existed when the probe was asked. Anything later is a leak."""
    return [event for event in events if event["day"] <= day]


def recency(events: list[dict[str, Any]], question: str, day: int,
            budget: int, stream: Iterator[int] | None = None) -> list[dict[str, Any]]:
    visible = _before(events, day)
    return _fill(sorted(visible, key=lambda e: (-e["day"], -e["position"])), budget)


def frequency(events: list[dict[str, Any]], question: str, day: int,
              budget: int, stream: Iterator[int] | None = None) -> list[dict[str, Any]]:
    visible = _before(events, day)
    counts: dict[str, int] = {}
    for event in visible:
        key = " ".join(event["text"].split()[:8]).lower()
        counts[key] = counts.get(key, 0) + 1

    def weight(event: dict[str, Any]) -> tuple[int, int]:
        key = " ".join(event["text"].split()[:8]).lower()
        return (-counts[key], -event["day"])

    return _fill(sorted(visible, key=weight), budget)


def random_sample(events: list[dict[str, Any]], question: str, day: int,
                  budget: int, stream: Iterator[int] | None = None) -> list[dict[str, Any]]:
    """Seeded, so the floor is reproducible rather than a different floor each run."""
    visible = _before(events, day)
    if stream is None:
        return _fill(visible, budget)
    keyed = sorted(visible, key=lambda e: (next(stream), e["position"]))
    return _fill(keyed, budget)


# fts5 needs an index, so it is supplied by the runner rather than built here.
ARMS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "recency": recency,
    "frequency": frequency,
    "random": random_sample,
}

ARM_NOTES = {
    "recency": "keeps the most recent events; cannot see the question",
    "frequency": "keeps the most repeated events; cannot see the question",
    "random": "seeded sample at the same budget; the floor",
    "fts5": "lexical retrieval against the question; sees the question",
}
