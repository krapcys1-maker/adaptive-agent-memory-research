#!/usr/bin/env python3
"""Freeze the four units every system in the arena pilot will run on.

Four, not thirty-six, and not ten. The pilot exists to find out whether the
pipeline works, what it really costs, and whether there is any signal worth
paying more for — not to produce a leaderboard. Four units is about a tenth of
the available bridge and is what a hard three-dollar cap buys.

Why a new selection rather than the existing bridge
---------------------------------------------------
`longmemeval-bridge-v0` is frozen, and it was frozen for a lexical-retrieval
transfer protocol under a different research question. Reusing a selection
across questions is how a set quietly becomes a development set. So this freezes
its own, from the same public corpus, under its own rule.

The rule, fixed before any system has run
------------------------------------------
Chosen on properties of the data, never on how any system performed. Three of
the four slots stratify by **user turns**, because that is what a memory system
actually ingests and what its cost scales with, and it is measurable without
opening a single answer:

    short    fewest user turns in the universe
    medium   closest to the universe median
    long     most user turns in the universe
    update   the knowledge-update question closest to the median

The fourth slot is the corpus's own name for correction and staleness. It is not
a category invented here: LongMemEval labels it, and it is the regime this
project's whole question turns on. The three size slots take distinct question
types, so four units span four types rather than four sizes of one.

Ties break on ascending `sha256("arena-pilot-v1:" + question_id)`, the same
device the earlier bridge used, so the choice is reproducible and cannot be
nudged.

What leaves this repository
---------------------------
Question IDs, question types and counts. No conversation, no question text, no
answer, no evidence id. The corpus stays in the ignored local cache and is named
by dataset commit and file hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "lab" / "arena"

DATASET_COMMIT = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
SOURCE_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
SOURCE_SIZE = 277_383_467
SOURCE_URL = (
    "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/"
    f"{DATASET_COMMIT}/longmemeval_s_cleaned.json"
)
DEFAULT_SOURCE = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
                  / "longmemeval_s_cleaned.json")

SALT = "arena-pilot-v1:"

#: The corpus's own vocabulary. Nothing here is invented.
QUESTION_TYPES = (
    "single-session-user", "single-session-assistant", "single-session-preference",
    "multi-session", "knowledge-update", "temporal-reasoning",
)

#: The slot whose regime the corpus names for us. Correction and staleness are
#: what this project exists to study, so the pilot must contain one.
UPDATE_TYPE = "knowledge-update"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rank_key(question_id: str) -> str:
    return hashlib.sha256((SALT + question_id).encode("utf-8")).hexdigest()


def measurable(row: dict[str, Any]) -> dict[str, Any]:
    """Everything the rule is allowed to look at. No answers, no gold."""
    sessions = row["haystack_sessions"]
    user_turns = sum(
        1 for session in sessions for turn in session
        if str((turn or {}).get("role", "")).strip() == "user"
        and str((turn or {}).get("content", "")).strip()
    )
    return {
        "question_id": row["question_id"],
        "question_type": row["question_type"],
        "sessions": len(sessions),
        "turns": sum(len(session) for session in sessions),
        "user_turns": user_turns,
        "words": sum(len(str((turn or {}).get("content", "")).split())
                     for session in sessions for turn in session),
        "gold_evidence_sessions": len(row.get("answer_session_ids") or []),
        "rank_key": rank_key(row["question_id"]),
    }


def universe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Answerable, structurally sound, with gold that exists.

    Abstention rows are excluded. They are a separate selective-decision
    question, their answer-session identifiers point at near-miss sessions rather
    than a complete answer set, and four slots cannot carry both regimes without
    representing neither.
    """
    kept: list[dict[str, Any]] = []
    for row in rows:
        if row.get("question_type") not in QUESTION_TYPES:
            continue
        if str(row.get("question_id", "")).endswith("_abs"):
            continue
        if not (len(row["haystack_session_ids"]) == len(row["haystack_dates"])
                == len(row["haystack_sessions"])):
            continue
        tagged = sum(bool(turn.get("has_answer"))
                     for session in row["haystack_sessions"] for turn in session)
        if not row.get("answer_session_ids") or not tagged:
            continue
        kept.append(measurable(row))
    return sorted(kept, key=lambda unit: unit["rank_key"])


def choose(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply the rule. Deterministic, and blind to every system's behaviour."""
    median = statistics.median(unit["user_turns"] for unit in pool)
    chosen: list[dict[str, Any]] = []
    used_types: set[str] = set()

    def take(slot: str, candidates: list[dict[str, Any]], key) -> None:
        # Distinct question types across slots, so four units span four regimes
        # rather than four sizes of one. `rank_key` is the final tie-break and
        # the pool is already sorted by it, so `min` is stable and reproducible.
        eligible = [u for u in candidates if u["question_type"] not in used_types]
        pick = min(eligible or candidates, key=key)
        used_types.add(pick["question_type"])
        chosen.append(dict(pick, slot=slot))

    updates = [u for u in pool if u["question_type"] == UPDATE_TYPE]
    take("update", updates, key=lambda u: (abs(u["user_turns"] - median), u["rank_key"]))

    rest = [u for u in pool if u["question_id"] not in {c["question_id"] for c in chosen}]
    take("short", rest, key=lambda u: (u["user_turns"], u["rank_key"]))
    rest = [u for u in rest if u["question_id"] not in {c["question_id"] for c in chosen}]
    take("medium", rest, key=lambda u: (abs(u["user_turns"] - median), u["rank_key"]))
    rest = [u for u in rest if u["question_id"] not in {c["question_id"] for c in chosen}]
    take("long", rest, key=lambda u: (-u["user_turns"], u["rank_key"]))

    order = {"short": 0, "medium": 1, "long": 2, "update": 3}
    return sorted(chosen, key=lambda u: order[u["slot"]])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(OUT / "pilot-selection.json"))
    parser.add_argument("--skip-hash", action="store_true",
                        help="skip the 277 MB file hash; the manifest then says so")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"corpus not found: {source}")

    observed_sha = None if args.skip_hash else sha256_file(source)
    if observed_sha is not None and observed_sha != SOURCE_SHA256:
        raise SystemExit(
            f"corpus hash {observed_sha} does not match the pinned "
            f"{SOURCE_SHA256}; the selection would name a different file"
        )

    with source.open(encoding="utf-8") as handle:
        rows = json.load(handle)

    pool = universe(rows)
    chosen = choose(pool)

    manifest = {
        "artifact": "arena-pilot-selection",
        "selection_id": "arena-pilot-v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "frozen before any system ran on it",
        "purpose": ("about a tenth of the bridge, sized to a hard $3 cap. The pilot "
                    "tests the pipeline, the real cost, and whether any signal "
                    "justifies spending more. It is not a leaderboard and four "
                    "units cannot be one"),
        "why_not_bridge_v0": ("that selection is frozen for a lexical-retrieval "
                              "transfer protocol under a different research question. "
                              "Reusing a set across questions is how it becomes a "
                              "development set"),
        "source": {
            "corpus": "LongMemEval-S cleaned",
            "dataset_commit": DATASET_COMMIT,
            "url": SOURCE_URL,
            "bytes": SOURCE_SIZE,
            "sha256": observed_sha or f"not verified this run; pinned {SOURCE_SHA256}",
            "location": "ignored local cache; nothing from it is committed",
        },
        "rule": {
            "salt": SALT,
            "tie_break": "ascending sha256(salt + question_id)",
            "stratify_on": "user turns, because that is what a memory system ingests",
            "slots": {
                "short": "fewest user turns in the universe",
                "medium": "closest to the universe median user turns",
                "long": "most user turns in the universe",
                "update": (f"the {UPDATE_TYPE} question closest to the median; the "
                           "corpus's own name for correction and staleness"),
            },
            "distinct_question_types": True,
            "universe": ("answerable rows of a known question type, with matching "
                         "session/date/session-id lengths, at least one has_answer "
                         "turn and non-empty answer_session_ids. Abstention rows "
                         "excluded: a separate selective-decision question whose "
                         "answer_session_ids name near-miss sessions"),
            "blind_to": "every system's behaviour; nothing had run when this froze",
        },
        "universe_size": len(pool),
        "universe_user_turns_median": statistics.median(u["user_turns"] for u in pool),
        "units": [
            {k: v for k, v in unit.items() if k != "rank_key"} | {"rank_key": unit["rank_key"][:16]}
            for unit in chosen
        ],
        "totals": {
            "units": len(chosen),
            "sessions": sum(u["sessions"] for u in chosen),
            "turns": sum(u["turns"] for u in chosen),
            "user_turns": sum(u["user_turns"] for u in chosen),
            "words": sum(u["words"] for u in chosen),
        },
        "withheld": ("no conversation, question text, answer or evidence id leaves "
                     "the ignored cache. Only public question ids and counts"),
    }
    manifest["selection_sha256"] = hashlib.sha256(
        json.dumps([u["question_id"] for u in chosen], sort_keys=True).encode()
    ).hexdigest()

    Path(args.out).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"universe {len(pool)} answerable units, median {manifest['universe_user_turns_median']} user turns")
    for unit in chosen:
        print(f"  {unit['slot']:7s} {unit['question_id']:12s} {unit['question_type']:28s} "
              f"{unit['sessions']:3d} sessions  {unit['user_turns']:4d} user turns")
    print(f"  totals: {manifest['totals']['sessions']} sessions, "
          f"{manifest['totals']['user_turns']} user turns, "
          f"{manifest['totals']['words']} words")
    print(f"  selection sha256 {manifest['selection_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
