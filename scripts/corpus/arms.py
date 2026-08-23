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
    "rank-oracle": "retrieval, then records superseded within their chain are demoted; "
                   "chains supplied by an oracle, so this is an upper bound",
    "recency": "keeps the most recent events; cannot see the question",
    "frequency": "keeps the most repeated events; cannot see the question",
    "random": "seeded sample at the same budget; the floor",
    "fts5": "lexical retrieval against the question; sees the question",
}


# --------------------------------------------------------------------------- rank


def supersession_rank(events: list[dict[str, Any]],
                      chains: dict[str, str]) -> dict[str, int]:
    """n1 for the newest record in a chain, n2 for the one it replaced, and so on.

    The idea, in the form it was proposed: if Kuba lived on Ossowskiego and moved
    to Norwida, Norwida becomes n1 and Ossowskiego n2. Move again and the new
    address is n1, Norwida n2, Ossowskiego n3. Asked *where does he live*, answer
    n1. Asked *where did he live*, n2 and below.

    Two things this rank is not, both measured elsewhere in this project.

    It is **not validity**. ``PMLAB-REV-V0`` case C3: a rate recorded on 15
    January but valid only from 1 September is the newest record and is not the
    answer on 1 May. Rank orders writes, not truth. A system that answered n1
    unconditionally would leak the future.

    It is **not free**. ``chains`` says which records concern the same slot, and
    deriving that is the hard part — "Kuba's address" and "Kuba's phone" are two
    chains, and nothing in the text announces which is which. Here the chain map
    is supplied by an **oracle**, so this measures whether the idea works when
    the grouping is perfect. If it fails under an oracle it fails, and that is
    worth knowing before anyone builds the grouping.
    """
    order: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        chain = chains.get(event["event_id"])
        if chain:
            order.setdefault(chain, []).append(event)

    rank: dict[str, int] = {}
    for members in order.values():
        newest_first = sorted(members, key=lambda e: (-e["day"], -e["position"]))
        for position, event in enumerate(newest_first, start=1):
            rank[event["event_id"]] = position
    return rank


def rank_demoted(events: list[dict[str, Any]], question: str, day: int,
                 budget: int, stream: Iterator[int] | None = None, *,
                 ranked_ids: list[str] | None = None,
                 rank: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """Retrieval, then anything below n1 in its chain is pushed to the back.

    Deliberately a demotion rather than a filter. Dropping n2 outright would
    answer *where does he live* well and make *where did he live* unanswerable,
    and the corpus contains both kinds of question. Demoted records still enter
    the context if the budget reaches them.
    """
    rank = rank or {}
    by_id = {event["event_id"]: event for event in events}
    ordered = [by_id[i] for i in (ranked_ids or []) if i in by_id]
    visible = _before(ordered, day)
    return _fill(sorted(visible, key=lambda e: rank.get(e["event_id"], 1) > 1), budget)
