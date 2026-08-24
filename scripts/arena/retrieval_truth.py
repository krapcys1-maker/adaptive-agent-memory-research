"""Did the evidence a system surfaced come from a session that holds the answer?

The pilot could not ask this. Each system's `evidence_ids` live in its own id
space — CUPMem's profile items, Mem0's memory uuids, Hindsight's fact ids,
Graphiti's edge uuids — and none of them names anything the arena ingested.

The mapping used here is mechanical and narrow: **the session timestamp**. Every
record handed to a system carries its session's date, both systems store that
date on the memory they derive, and both return it on recall. So a retrieved
memory maps to a session by matching dates, with no semantic guessing about which
passage a memory came from.

Where it does not hold, it says so
-----------------------------------
- a unit whose haystack repeats a date cannot support the mapping at all, because
  one date names two sessions. One of the ten units is like that, and its
  retrieval metrics are UNOBSERVABLE rather than approximated.
- a memory a system derived from several sessions has one date and several
  sources; this counts it once, at the date it kept.
- **stale and conflicting memory counts are UNOBSERVABLE everywhere.** The corpus
  labels which sessions contain the answer; it does not label which contain a
  superseded version of it, and inferring that from the text is exactly the
  semantic guessing this module refuses to do.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

UNOBSERVABLE = "UNOBSERVABLE"

_FORMATS = ("%Y/%m/%d (%a) %H:%M", "%Y/%m/%d %H:%M", "%Y/%m/%d",
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def canonical_time(value: Any) -> str | None:
    """One spelling for a moment, so two systems' dates compare.

    The corpus writes `2022/09/01 (Thu) 00:10`; Hindsight returns
    `2022-09-01T00:10:00+00:00`; Mem0 returns whatever it was handed. All three
    are the same instant and must land on the same key.
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).replace(tzinfo=None).isoformat()
    except ValueError:
        pass
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return None


def session_map(unit: dict[str, Any]) -> dict[str, int] | None:
    """date -> session index, or None when dates do not identify sessions."""
    dates = unit.get("haystack_dates") or []
    keys = [canonical_time(d) for d in dates]
    if not keys or any(k is None for k in keys) or len(set(keys)) != len(keys):
        return None
    return {key: index for index, key in enumerate(keys)}


def gold_session_indices(unit: dict[str, Any]) -> set[int]:
    ids = list(unit.get("haystack_session_ids") or [])
    gold = set(unit.get("answer_session_ids") or [])
    return {index for index, sid in enumerate(ids) if sid in gold}


def measure(unit: dict[str, Any], evidence_times: list[Any]) -> dict[str, Any]:
    """Retrieval quality against the corpus's own gold sessions.

    `gold_rank` is 1-based over the retrieved list in the order the system
    returned it, and is None when no gold session was retrieved — None, not zero,
    because rank zero would read as "found it first".
    """
    mapping = session_map(unit)
    gold = gold_session_indices(unit)
    if mapping is None:
        return {
            "observable": False,
            "why": "haystack dates do not uniquely identify sessions in this unit",
            "gold_sessions": len(gold),
            "gold_in_context": UNOBSERVABLE,
            "gold_rank": UNOBSERVABLE,
            "precision_at_k": UNOBSERVABLE,
            "evidence_mapped": UNOBSERVABLE,
            "stale_or_conflicting": UNOBSERVABLE,
        }

    resolved = [mapping.get(canonical_time(t)) for t in evidence_times]
    hits = [index for index, session in enumerate(resolved, start=1)
            if session is not None and session in gold]
    mapped = [s for s in resolved if s is not None]

    return {
        "observable": True,
        "gold_sessions": len(gold),
        "retrieved": len(evidence_times),
        "evidence_mapped": len(mapped),
        "evidence_unmapped": len(evidence_times) - len(mapped),
        "gold_in_context": bool(hits),
        "gold_rank": hits[0] if hits else None,
        "gold_hits": len(hits),
        "precision_at_k": (round(len(hits) / len(evidence_times), 4)
                           if evidence_times else None),
        "distinct_sessions_retrieved": len(set(mapped)),
        # The corpus labels sessions that hold the answer. It does not label
        # sessions holding a superseded version, and reading that off the text
        # would be the semantic guessing this module exists to avoid.
        "stale_or_conflicting": UNOBSERVABLE,
        "stale_why": ("the corpus marks answer sessions, not superseded ones; "
                      "labelling staleness would require reading the passages"),
    }
