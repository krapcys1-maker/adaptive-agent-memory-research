#!/usr/bin/env python3
"""Freeze `arena-expansion-v1`: the pilot's four, plus six chosen to test one claim.

**This is a confirmatory sample, designed after seeing the pilot result, and it
must never be described as a random sample of LongMemEval.** The pilot produced
exactly one difference between two systems — Hindsight answered the single
temporal-reasoning unit and nobody else did — and one observation is not a
finding. So temporal-reasoning is deliberately over-represented here, three units
against a corpus proportion of one in six.

That design buys statistical power on the one question worth asking and costs the
right to call the overall accuracy an estimate of anything. Both halves of that
trade are recorded in the manifest.

The rule, fixed before any system ran on it
--------------------------------------------
    keep     the four units of `arena-pilot-v1`, unchanged and reused
    add      2 temporal-reasoning   the claim under test
             2 knowledge-update     the one thing every system solved
             1 multi-session        a retrieval unit nobody solved
             1 single-session-user  the other retrieval unit nobody solved

    giving   3 temporal-reasoning, 3 knowledge-update, 2 multi-session,
             2 single-session-user

Within each type the pick is by ascending `sha256("arena-expansion-v1:" + qid)`
over the same universe the pilot drew from, excluding units already selected. No
system's answers, scores, costs or behaviour enter the choice — none of them
could, because the ordering is fixed by a hash of a public question id.

Why these four types and not others
------------------------------------
They are the four the pilot ran, so the ten units contain no type whose
apparatus has not already been exercised. `single-session-assistant` and
`single-session-preference` are left out deliberately: adding an untried type to
a confirmatory run mixes a new question into an experiment designed to answer an
old one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/lab/arena"
PILOT = OUT / "pilot-selection.json"

DATASET_COMMIT = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
SOURCE_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
DEFAULT_SOURCE = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
                  / "longmemeval_s_cleaned.json")

SALT = "arena-expansion-v1:"

#: What to add on top of the pilot's four, by the corpus's own type names.
QUOTAS = {
    "temporal-reasoning": 2,
    "knowledge-update": 2,
    "multi-session": 1,
    "single-session-user": 1,
}

QUESTION_TYPES = (
    "single-session-user", "single-session-assistant", "single-session-preference",
    "multi-session", "knowledge-update", "temporal-reasoning",
)


def rank_key(question_id: str) -> str:
    return hashlib.sha256((SALT + question_id).encode("utf-8")).hexdigest()


def measurable(row: dict[str, Any]) -> dict[str, Any]:
    """Everything the rule may look at: counts, never content, never answers."""
    sessions = row["haystack_sessions"]
    dates = row.get("haystack_dates") or []
    return {
        "question_id": row["question_id"],
        "question_type": row["question_type"],
        "sessions": len(sessions),
        "turns": sum(len(s) for s in sessions),
        "user_turns": sum(
            1 for s in sessions for t in s
            if str((t or {}).get("role", "")).strip() == "user"
            and str((t or {}).get("content", "")).strip()),
        "words": sum(len(str((t or {}).get("content", "")).split())
                     for s in sessions for t in s),
        "gold_evidence_sessions": len(row.get("answer_session_ids") or []),
        # Whether a retrieved memory can be traced back to a session by its date
        # alone. Recorded per unit because the retrieval metrics depend on it and
        # a unit with repeated dates cannot support them.
        "dates_unique": len(set(map(str, dates))) == len(dates) and bool(dates),
        "rank_key": rank_key(row["question_id"]),
    }


def universe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Answerable, structurally sound, gold that exists. Same filter as the pilot."""
    kept = []
    for row in rows:
        if row.get("question_type") not in QUESTION_TYPES:
            continue
        if str(row.get("question_id", "")).endswith("_abs"):
            continue
        if not (len(row["haystack_session_ids"]) == len(row["haystack_dates"])
                == len(row["haystack_sessions"])):
            continue
        tagged = sum(bool(t.get("has_answer"))
                     for s in row["haystack_sessions"] for t in s)
        if not row.get("answer_session_ids") or not tagged:
            continue
        kept.append(measurable(row))
    return sorted(kept, key=lambda u: u["rank_key"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(OUT / "expansion-selection.json"))
    args = parser.parse_args()

    with Path(args.source).open(encoding="utf-8") as handle:
        rows = json.load(handle)

    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    pilot_ids = {u["question_id"] for u in pilot["units"]}
    by_id = {row["question_id"]: row for row in rows}

    kept = [dict(measurable(by_id[u["question_id"]]),
                 slot=u["slot"], origin="arena-pilot-v1")
            for u in pilot["units"]]

    pool = [u for u in universe(rows) if u["question_id"] not in pilot_ids]
    added: list[dict[str, Any]] = []
    for qtype, quota in QUOTAS.items():
        candidates = [u for u in pool if u["question_type"] == qtype][:quota]
        if len(candidates) < quota:
            raise SystemExit(f"only {len(candidates)} available for {qtype}, need {quota}")
        for index, unit in enumerate(candidates):
            added.append(dict(unit, slot=f"{qtype}-{index + 1}", origin="arena-expansion-v1"))

    units = kept + added
    composition = Counter(u["question_type"] for u in units)

    manifest = {
        "artifact": "arena-expansion-selection",
        "selection_id": "arena-expansion-v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "frozen before either system ran on the six new units",
        "purpose": ("test one claim from the four-unit pilot: that Hindsight answers "
                    "temporal-reasoning questions the other systems do not"),
        "confirmatory_not_representative": (
            "DESIGNED AFTER SEEING THE PILOT RESULT. temporal-reasoning is deliberately "
            "over-represented at 3 of 10 against a corpus proportion near 1 in 6. That "
            "buys power on the question worth asking and forfeits the right to read the "
            "overall accuracy as an estimate of LongMemEval performance. It must never "
            "be presented as a random sample"),
        "source": {
            "corpus": "LongMemEval-S cleaned",
            "dataset_commit": DATASET_COMMIT,
            "sha256": SOURCE_SHA256,
            "location": "ignored local cache; nothing from it is committed",
        },
        "rule": {
            "salt": SALT,
            "tie_break": "ascending sha256(salt + question_id)",
            "kept_from": "arena-pilot-v1, all four, unchanged",
            "added_quotas": QUOTAS,
            "universe": ("answerable rows of a known type, matching session/date/id "
                         "lengths, at least one has_answer turn, non-empty "
                         "answer_session_ids — the pilot's filter, unchanged"),
            "blind_to": ("every system's answers, scores, costs and behaviour. The "
                         "ordering is a hash of a public question id"),
            "types_left_out": ("single-session-assistant and single-session-preference. "
                               "Adding an untried type to a confirmatory run mixes a new "
                               "question into an experiment designed to answer an old one"),
        },
        "composition": dict(composition),
        "reuse": {
            "units_reused": len(kept),
            "units_new": len(added),
            "why_reuse_is_sound": (
                "each unit is an independent observation: the runner resets the system "
                "and ingests one unit's haystack from empty before querying it, so a "
                "unit's result does not depend on which other units ran. The apparatus "
                "is unchanged from the runs that produced them"),
            "apparatus_unchanged_since": (
                "Mem0 was rerun with the full-paging state probe, and Hindsight ran "
                "with the ISO timestamp normalisation on both retain and recall. Both "
                "fixes predate the results being reused"),
        },
        "units": units,
        "totals": {
            "units": len(units),
            "sessions": sum(u["sessions"] for u in units),
            "user_turns": sum(u["user_turns"] for u in units),
            "words": sum(u["words"] for u in units),
            "units_with_unique_session_dates": sum(1 for u in units if u["dates_unique"]),
        },
        "withheld": "no conversation, question text, answer or evidence id leaves the cache",
    }
    manifest["selection_sha256"] = hashlib.sha256(
        json.dumps(sorted(u["question_id"] for u in units)).encode()).hexdigest()
    manifest["new_units_sha256"] = hashlib.sha256(
        json.dumps(sorted(u["question_id"] for u in added)).encode()).hexdigest()

    Path(args.out).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"arena-expansion-v1: {len(units)} units "
          f"({len(kept)} reused, {len(added)} new)")
    for unit in units:
        print(f"  {unit['origin'][-2:]:>2s} {unit['slot']:22.22s} {unit['question_id']:14s} "
              f"{unit['question_type']:24s} {unit['sessions']:3d}s {unit['user_turns']:4d}t "
              f"gold={unit['gold_evidence_sessions']} dates_unique={unit['dates_unique']}")
    print(f"  composition: {dict(composition)}")
    print(f"  totals: {manifest['totals']}")
    print(f"  selection sha256 {manifest['selection_sha256']}")
    print(f"  new units sha256 {manifest['new_units_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
