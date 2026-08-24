#!/usr/bin/env python3
"""TEMPORAL_ANCHOR_AT_CONTEXT, restricted to the TEMPORAL_BOUNDARY regime
("Mechanism I" -- third confirmatory test, narrowly scoped).

Same render as the original E1/Stage-2 mechanism (Ledger Entries A/B):
each retrieved fact becomes "[YYYY-MM-DD] {fact}", using the item's own
positionally-aligned session timestamp. Nothing else about item order,
selection, or content changes.

Why a third attempt, narrowly scoped, rather than a new external candidate:
E1 (exploratory) showed a real positive effect. Stage 2 (fresh replication,
10 units, 70/30 temporal/control mix) FAILED its own pre-registered gate
overall (net -1: 3 regressions vs 2 repairs, 0 repairs in the predicted
TEMPORAL_POSITIVE bucket) -- but within that same sample, the 2-unit
TEMPORAL_BOUNDARY sub-regime (duration/arithmetic between two named events)
showed a clean, unbroken 2/2 positive signal with 0 regressions. Stage 2's
own report flagged this narrower regime as the natural next confirmatory
target and left it unscheduled. Independently, Mechanism H's own fresh
gold-blind draw (Campaign V2) surfaced a third naturally-occurring case of
this exact failure shape (`4dfccbf7`), and a project-wide tally found
temporal-representation loss ("today" never resolved to an absolute date)
is now the single largest failure cluster in this project (4/13 BASE-wrong
units). This transplant is AAMR-internal-measured evidence (twice already,
ranked above external literature per this project's own evidence
hierarchy), not a new external-discovery pick and not a retry of DROPped
work -- Ledger Entry A's status is SUPPORTED/qualified, not DROP.

The known negative-transfer trap (Ledger Entry B, `00ca467f`): many-item
filter/count questions where several facts share one later recap-session
timestamp that diverges from each fact's own in-text event date. This
selection's classifier structurally avoids that shape by construction --
every matched question asks for a single duration/arithmetic value between
(at most) two named events, never a filtered count across many items.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.retrieval_truth import canonical_time  # noqa: E402

#: Fixed before any selection was built. Matches "how many/long ... days/
#: weeks/months ..." combined with a two-event relation word -- deliberately
#: excludes filter/count-many-items shapes (Ledger Entry B's trap).
DURATION_RE = re.compile(r"how (many|long)\b", re.I)
UNIT_RE = re.compile(r"\b(days?|weeks?|months?)\b", re.I)
RELATION_RE = re.compile(
    r"\b(since|between|after|before|had passed|has passed|did it take|"
    r"took (me|us)|from .* to)\b", re.I)
BOUNDARY_TYPES = {"temporal-reasoning", "multi-session"}


def is_temporal_boundary(question_type: str, question: str) -> bool:
    """Gold-blind: question_type + question text only, never gold/answer."""
    if question_type not in BOUNDARY_TYPES:
        return False
    return bool(DURATION_RE.search(question) and UNIT_RE.search(question)
               and RELATION_RE.search(question))


def session_date(raw_timestamp: str) -> str:
    """'2023/05/25 (Thu) 06:04' -> '2023-05-25'. Deterministic, no inference."""
    iso = canonical_time(raw_timestamp)
    if iso is None:
        raise SystemExit(f"could not parse a session timestamp deterministically: {raw_timestamp!r}")
    return iso[:10]


def render_with_anchor(raw_results: list[dict[str, Any]]) -> list[str]:
    """Mem0 search() results (with 'memory' and 'metadata.timestamp') -> the
    +TIME context: "[YYYY-MM-DD] {fact}", blanks dropped, order preserved."""
    out = []
    for r in raw_results:
        text = str(r.get("memory", "")).strip()
        if not text:
            continue
        ts = str((r.get("metadata") or {}).get("timestamp", "") or "")
        date = session_date(ts) if ts else None
        out.append(f"[{date}] {text}" if date else text)
    return out


def render_plain(raw_results: list[dict[str, Any]]) -> list[str]:
    return [str(r.get("memory", "")).strip() for r in raw_results
           if str(r.get("memory", "")).strip()]


def _self_check() -> None:
    assert is_temporal_boundary(
        "temporal-reasoning",
        "How many days had passed since I bought shoes when I noticed my sneakers broke?")
    assert not is_temporal_boundary(
        "temporal-reasoning", "How many doctor's appointments did I have in March?")
    assert not is_temporal_boundary(
        "single-session-user", "How many days did it take to receive my package after I ordered it?")
    assert session_date("2023/05/25 (Thu) 06:04") == "2023-05-25"
    raw = [{"memory": "  fact one  ", "metadata": {"timestamp": "2023/05/25 (Thu) 06:04"}},
          {"memory": ""}, {"memory": "fact two", "metadata": {}}]
    assert render_with_anchor(raw) == ["[2023-05-25] fact one", "fact two"]
    assert render_plain(raw) == ["fact one", "fact two"]
    print("self-check OK: 6/6 cases correct")


if __name__ == "__main__":
    _self_check()
