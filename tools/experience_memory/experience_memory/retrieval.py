"""Goal-similarity retrieval, the rule of the measured V5B ``retrieved_task`` arm.

Rule (program ALFWORLD-LADDER-R4-V5B, instrument ``tools/alfworld_ladder/agent.py``, ``choose_memory``):

1. Tokenise a goal: lower-case it, take every maximal run of ``a``-``z`` letters, drop the stop words in
   :data:`STOPWORDS`. The result is a set of content words.
2. Score every bank item by the Jaccard index of the content-word sets of the query goal and the item goal
   (``|A & B| / max(1, |A | B|)``).
3. Order the items by score, highest first. Ties are broken by a number drawn from ``random.Random(s)``, where
   ``s`` is the integer value of the first 12 hex digits of ``sha256("<query_id>|<seed>|ret")``. One number is
   drawn per bank item, in bank order, before any item is excluded.
4. Drop the items the query must not see (same family as the query, or flagged as test data), keep the first k.

With k = 2 and a bank without excluded items this is byte-for-byte the V5B selection
(``tools/experience_memory/parity/check_v5b_parity.py`` checks it against the instrument code). Drawing the
tie-break numbers before the exclusion means that excluding an item never changes the relative order of the others.
"""
from __future__ import annotations

import hashlib
import operator
import random
import re
from dataclasses import dataclass

from .bank import ExperienceBank, LeakageError, Trajectory

STOPWORDS = frozenset("a an the some put in on to and of with it then your is".split())
_WORD = re.compile(r"[a-z]+")


def content_words(text: str) -> frozenset[str]:
    """The content-word set of a goal (V5B ``words``)."""
    return frozenset(w for w in _WORD.findall(text.lower()) if w not in STOPWORDS)


def goal_jaccard(goal: str, other: str) -> float:
    """Content-word Jaccard index of two goals (V5B ``jaccard``)."""
    a, b = content_words(goal), content_words(other)
    return len(a & b) / max(1, len(a | b))


def stable_hash(*parts: object) -> int:
    """sha256 of the '|'-joined parts, first 12 hex digits as an integer (V5B ``_h``). Not Python's ``hash()``."""
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


@dataclass(frozen=True)
class Pick:
    item: Trajectory
    score: float


@dataclass(frozen=True)
class Retrieval:
    """What a retriever chose for one query, with enough to log and audit it."""

    query_id: str
    seed: int
    picks: tuple[Pick, ...]
    excluded_ids: tuple[str, ...]
    top1_similarity: float  # best score among the items the query may see (V5B: the whole bank; equal there)

    @property
    def items(self) -> tuple[Trajectory, ...]:
        return tuple(p.item for p in self.picks)

    @property
    def item_ids(self) -> tuple[str, ...]:
        return tuple(p.item.item_id for p in self.picks)


class GoalSimilarityRetriever:
    """Top-k bank items by content-word Jaccard of the goal; k = 2 is the measured setting."""

    def __init__(self, k: int = 2) -> None:
        if k < 1:
            raise ValueError("k must be at least 1")
        self.k = k

    def retrieve(self, bank: ExperienceBank, goal: str, *, query_id: str, query_family: str | None,
                 seed: int = 0) -> Retrieval:
        """Choose ``k`` items for a query.

        ``query_id`` and ``seed`` only break ties (V5B used the ALFWorld game path and the episode seed).
        ``query_family`` is the query's own family: its items are never shown. It is required on purpose; pass
        ``None`` only if the query belongs to no family that the bank could contain.
        """
        if not isinstance(query_id, str) or not query_id:
            raise ValueError("query_id must be a non-empty string")
        if query_family is not None and (not isinstance(query_family, str) or not query_family.strip()):
            raise ValueError("query_family must be a non-empty string or None")
        if isinstance(seed, bool):
            raise TypeError("seed must be an int, not a bool")  # True would hash differently from 1
        seed = operator.index(seed)  # an integer type (numpy too) becomes int; 0.0 or "0" raise TypeError
        gw = content_words(goal)
        rng = random.Random(stable_hash(query_id, seed, "ret"))
        scored = []
        for index, item in enumerate(bank):
            iw = content_words(item.goal)
            score = len(gw & iw) / max(1, len(gw | iw))
            scored.append((-score, rng.random(), index, item))
        scored.sort(key=lambda t: (t[0], t[1], t[2]))
        excluded: list[str] = []
        kept: list[tuple[float, Trajectory]] = []
        for neg_score, _tie, _index, item in scored:
            if item.is_test:  # cannot enter through ExperienceBank.add; checked again in case of a subclass
                raise LeakageError(f"bank item {item.item_id!r} is flagged as test data")
            if (query_family is not None and item.family_id == query_family) or item.item_id == query_id:
                excluded.append(item.item_id)
                continue
            kept.append((-neg_score, item))
        picks = tuple(Pick(item=it, score=s) for s, it in kept[: self.k])
        top1 = kept[0][0] if kept else 0.0
        return Retrieval(query_id=query_id, seed=seed, picks=picks, excluded_ids=tuple(excluded),
                         top1_similarity=top1)
