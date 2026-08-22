#!/usr/bin/env python3
"""Verify and deterministically select the public LongMemEval bridge v0.

The script never copies conversations, answers, or gold evidence into Git.  It
commits only version metadata and selected public question IDs.  The bridge is
a separately reported transfer set, not hidden confirmation evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "lab" / "longmemeval-bridge-v0"
DATASET_COMMIT = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
SOURCE_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
SOURCE_SIZE = 277_383_467
SOURCE_URL = (
    "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/"
    f"{DATASET_COMMIT}/longmemeval_s_cleaned.json"
)
DEFAULT_SOURCE = ROOT / "external" / "datasets" / "longmemeval-cleaned-98d7416c24c7" / "longmemeval_s_cleaned.json"
QUESTION_TYPES = [
    "single-session-user", "single-session-assistant", "single-session-preference",
    "multi-session", "knowledge-update", "temporal-reasoning",
]
ABSTENTION_QUOTAS = {
    "single-session-user": 1, "multi-session": 2,
    "knowledge-update": 2, "temporal-reasoning": 1,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rank(question_id: str) -> str:
    return hashlib.sha256(f"pmlab-longmemeval-bridge-v0:{question_id}".encode()).hexdigest()


def validate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    required = {
        "question_id", "question_type", "question", "answer", "question_date",
        "haystack_session_ids", "haystack_dates", "haystack_sessions", "answer_session_ids",
    }
    if len(rows) != 500 or len({row.get("question_id") for row in rows}) != 500:
        raise ValueError("LongMemEval-S must contain 500 unique question IDs")
    type_counts = Counter()
    abstention_counts = Counter()
    abstention_tagged_turn_counts = Counter()
    has_answer_turns = 0
    for row in rows:
        if set(row) != required:
            raise ValueError(f"{row.get('question_id')}: unexpected source schema")
        if row["question_type"] not in QUESTION_TYPES:
            raise ValueError(f"{row['question_id']}: unknown question type")
        if not (len(row["haystack_session_ids"]) == len(row["haystack_dates"]) == len(row["haystack_sessions"])):
            raise ValueError(f"{row['question_id']}: haystack arrays differ in length")
        type_counts[row["question_type"]] += 1
        is_abs = row["question_id"].endswith("_abs")
        abstention_counts[row["question_type"]] += int(is_abs)
        tagged = sum(bool(turn.get("has_answer")) for session in row["haystack_sessions"] for turn in session)
        has_answer_turns += tagged
        if is_abs:
            abstention_tagged_turn_counts[tagged] += 1
        if not is_abs and (not row["answer_session_ids"] or not tagged):
            raise ValueError(f"{row['question_id']}: answerable case lacks evidence labels")
    return {
        "rows": len(rows), "question_type_counts": dict(sorted(type_counts.items())),
        "abstention_counts": dict(sorted(abstention_counts.items())),
        "abstention_tagged_turn_count_distribution": {str(k): v for k, v in sorted(abstention_tagged_turn_counts.items())},
        "has_answer_turns": has_answer_turns,
    }


def select(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for question_type in QUESTION_TYPES:
        candidates = [row for row in rows if row["question_type"] == question_type and not row["question_id"].endswith("_abs")]
        selected.extend(sorted(candidates, key=lambda row: rank(row["question_id"]))[:5])
    selected_base_ids = {row["question_id"] for row in selected}
    for question_type, quota in ABSTENTION_QUOTAS.items():
        candidates = [
            row for row in rows
            if row["question_type"] == question_type
            and row["question_id"].endswith("_abs")
            and row["question_id"].removesuffix("_abs") not in selected_base_ids
        ]
        selected.extend(sorted(candidates, key=lambda row: rank(row["question_id"]))[:quota])
    if len(selected) != 36 or len({row["question_id"] for row in selected}) != 36:
        raise ValueError("bridge selection must contain 36 unique questions")
    return sorted(selected, key=lambda row: row["question_id"])


def public_selection(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in select(rows):
        tagged = sum(bool(turn.get("has_answer")) for session in row["haystack_sessions"] for turn in session)
        output.append({
            "question_id": row["question_id"], "question_type": row["question_type"],
            "answerable": not row["question_id"].endswith("_abs"),
            "haystack_session_count": len(row["haystack_sessions"]),
            "retrieval_gold_defined": not row["question_id"].endswith("_abs"),
            "gold_evidence_session_count": None if row["question_id"].endswith("_abs") else len(row["answer_session_ids"]),
            "gold_evidence_turn_count": None if row["question_id"].endswith("_abs") else tagged,
            "near_miss_session_count": len(row["answer_session_ids"]) if row["question_id"].endswith("_abs") else 0,
            "near_miss_tagged_turn_count": tagged if row["question_id"].endswith("_abs") else 0,
            "selection_rank_sha256": rank(row["question_id"]),
        })
    return output


def build_outputs(source: Path) -> dict[Path, str]:
    if source.stat().st_size != SOURCE_SIZE:
        raise ValueError("LongMemEval-S byte size differs from frozen source")
    actual_hash = sha256_file(source)
    if actual_hash != SOURCE_SHA256:
        raise ValueError("LongMemEval-S SHA-256 differs from frozen source")
    with source.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    audit = validate_rows(rows)
    selection = public_selection(rows)
    selection_text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in selection)
    selected_types = Counter(row["question_type"] for row in selection)
    selected_answerability = Counter("answerable" if row["answerable"] else "abstention" for row in selection)
    manifest = {
        "bridge_id": "longmemeval-bridge-v0", "status": "selection-frozen-before-backend-execution",
        "source": {
            "dataset": "xiaowu0162/longmemeval-cleaned", "dataset_commit": DATASET_COMMIT,
            "file": "longmemeval_s_cleaned.json", "bytes": SOURCE_SIZE, "sha256": SOURCE_SHA256,
            "license_declared_by_dataset_card": "MIT", "url": SOURCE_URL,
        },
        "official_code": {"repository": "xiaowu0162/LongMemEval", "commit_observed": "9e0b455f4ef0e2ab8f2e582289761153549043fc"},
        "selection": {
            "algorithm": "within-stratum ascending sha256('pmlab-longmemeval-bridge-v0:' + question_id)",
            "answerable_quota_per_question_type": 5, "abstention_quotas": ABSTENTION_QUOTAS,
            "count": len(selection), "question_type_counts": dict(sorted(selected_types.items())),
            "answerability_counts": dict(sorted(selected_answerability.items())),
            "base_question_pair_overlap": len({row["question_id"] for row in selection if row["answerable"]} & {row["question_id"].removesuffix("_abs") for row in selection if not row["answerable"]}),
            "selection_sha256": hashlib.sha256(selection_text.encode()).hexdigest(),
        },
        "source_audit": audit,
        "authority": "public transfer bridge only; not hidden test data and never merged into PMLAB score",
        "backend_run_permitted": False,
        "unlock": "freeze shared retrieval adapter and PMLAB lexical protocol first; then report bridge transfer separately",
        "known_limitations": [
            "public questions and evidence labels may be present in model training data",
            "histories are synthetic/compiled conversations rather than this project's natural work log",
            "official retrieval evaluation excludes abstention because no complete answer location exists",
            "abstention answer_session_ids identify near-miss sessions and must not be treated as positive retrieval gold",
            "end-to-end QA requires a reader and judge and must remain separate from retrieval scoring",
        ],
    }
    report = f"""# LongMemEval public bridge v0

Status: 36 public question IDs selected and frozen before backend execution

The source is `LongMemEval-S cleaned` at Hugging Face dataset commit `{DATASET_COMMIT}`. The verified file contains 500 unique questions, 896 answer-tagged turns, and 38-62 sessions per question. Its byte size is `{SOURCE_SIZE}` and SHA-256 is `{SOURCE_SHA256}`.

The bridge selects five answerable questions from each of six official question types and six abstention questions, using only a salted SHA-256 ordering of public question IDs. A base question and its `_abs` counterpart cannot both enter the bridge. No conversations, questions, answers, or evidence IDs are redistributed here. The source remains in the ignored local cache.

This bridge is useful for transfer diagnostics because it exposes evidence sessions/turns, knowledge updates, temporal reasoning, multi-session composition, and abstention. It is not a hidden test: labels are public and contamination is possible. Scores must never be pooled with Project Memory Lab v0.

Abstention is a separate selective-decision metric. Twenty-one of the 30 source abstention rows have zero `has_answer` turns; eight have one and one has two because a required operand is present while another is absent. Their answer-session identifiers point to near-miss sessions, not a complete answer set. Treating those identifiers as ordinary positive retrieval gold would be a scoring bug.

Backends remain locked. After the PMLAB lexical contract freezes, the same adapter may be evaluated here without changing chunking, token budget, query expansion, or fusion based on bridge results.
"""
    return {
        OUT / "selection.jsonl": selection_text,
        OUT / "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        OUT / "report.md": report,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    if not args.source.exists():
        raise SystemExit(f"missing ignored source dataset: {args.source}\nDownload pinned source: {SOURCE_URL}")
    outputs = build_outputs(args.source)
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(OUT), "files": len(outputs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
