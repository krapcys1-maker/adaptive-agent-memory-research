#!/usr/bin/env python3
"""Fail-closed construction and leakage audit for PMLAB-PACK-READER-001."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-pack-reader-v0"
REPORT = BASE / "internal" / "construction-audit.json"
FORBIDDEN_BLIND_KEYS = {"answer_atoms", "stale_atoms", "required_local_ids", "format_arm", "order_arm", "gold"}
FORBIDDEN_ID_FRAGMENTS = ("full", "compact", "retrieval", "governed", "current", "stale", "gold")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    corpus = load_jsonl(BASE / "corpus.jsonl")
    cases = load_jsonl(BASE / "cases.jsonl")
    groups = load_jsonl(BASE / "internal" / "groups.jsonl")
    gold = load_jsonl(BASE / "internal" / "gold.jsonl")
    conditions = load_jsonl(BASE / "internal" / "condition-map.jsonl")
    schedule = load_jsonl(BASE / "blind" / "schedule.jsonl")
    manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))

    checks: dict[str, bool] = {}
    checks["declared_hashes_match"] = all(
        (ROOT / relative).is_file() and sha256(ROOT / relative) == digest
        for relative, digest in manifest["hashes"].items()
    )
    checks["expected_shape"] = (
        len(groups) == 16 and len(cases) == 32 and len(corpus) == 256
        and len(conditions) == len(schedule) == 128 and len(gold) == 32
    )
    checks["prompt_safe_case_schema"] = all(
        FORBIDDEN_BLIND_KEYS.isdisjoint(case)
        and set(case) == {"case_id", "group_id", "language", "question", "retrieval_order", "all_local_ids"}
        for case in cases
    )
    checks["blind_schedule_schema"] = all(
        set(row) == {"sequence", "condition_id", "case_id"}
        and FORBIDDEN_BLIND_KEYS.isdisjoint(row)
        for row in schedule
    )
    checks["opaque_condition_ids"] = (
        len({row["condition_id"] for row in conditions}) == 128
        and all(re.fullmatch(r"C[0-9a-f]{16}", row["condition_id"]) for row in conditions)
        and all(not any(fragment in row["condition_id"].lower() for fragment in FORBIDDEN_ID_FRAGMENTS) for row in conditions)
    )
    checks["schedule_mapping_complete"] = (
        {row["condition_id"] for row in conditions} == {row["condition_id"] for row in schedule}
        and [row["sequence"] for row in schedule] == list(range(1, 129))
    )

    records_by_case: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in corpus:
        records_by_case[(row["group_id"], row["language"])].append(row)
    gold_by_case = {row["case_id"]: row for row in gold}
    case_checks: list[bool] = []
    atom_checks: list[bool] = []
    source_checks: list[bool] = []
    bilingual: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for case in cases:
        rows = records_by_case[(case["group_id"], case["language"])]
        local = {row["local_id"]: row for row in rows}
        expected_ids = [f"R{i:02d}" for i in range(1, 9)]
        case_checks.append(
            len(rows) == len(local) == 8
            and sorted(local) == expected_ids
            and sorted(case["retrieval_order"]) == expected_ids
            and Counter(row["bucket"] for row in rows) == {
                "current": 2, "supporting": 2, "stale_conflicting": 2, "distractor": 2
            }
        )
        truth = gold_by_case[case["case_id"]]
        answer_atoms = truth["answer_atoms"]
        stale_atoms = truth["stale_atoms"]
        required = truth["required_local_ids"]
        atom_checks.append(
            len(answer_atoms) == len(required)
            and 1 <= len(required) <= 3
            and set(answer_atoms).isdisjoint(stale_atoms)
            and all(atom not in case["question"] for atom in answer_atoms + stale_atoms)
            and all(sum(atom in row["text"] for row in rows) == 1 for atom in answer_atoms + stale_atoms)
            and all(atom in local[record_id]["text"] for atom, record_id in zip(answer_atoms, required))
            and all(local[record_id]["bucket"] in {"current", "supporting"} for record_id in required)
            and all(any(atom in row["text"] and row["bucket"] == "stale_conflicting" for row in rows) for atom in stale_atoms)
        )
        bilingual[case["group_id"]].append((answer_atoms, stale_atoms, required))
        for row in rows:
            lines = (ROOT / row["source_path"]).read_text(encoding="utf-8").splitlines()
            source_checks.append(
                row["line_start"] == row["line_end"]
                and lines[row["line_start"] - 1] == row["text"]
            )

    checks["case_record_invariants"] = all(case_checks)
    checks["gold_atom_and_citation_invariants"] = all(atom_checks)
    checks["source_spans_exact"] = all(source_checks)
    checks["bilingual_pairs_share_gold"] = all(len(signatures) == 2 and signatures[0] == signatures[1] for signatures in bilingual.values())
    condition_counts = Counter(row["case_id"] for row in conditions)
    checks["four_conditions_per_case"] = condition_counts == Counter({case["case_id"]: 4 for case in cases})

    passed = all(checks.values())
    report = {
        "experiment_id": "PMLAB-PACK-READER-001",
        "audit": "pre-run construction and leakage audit",
        "passed": passed,
        "checks": checks,
        "counts": {"groups": len(groups), "cases": len(cases), "records": len(corpus), "conditions": len(conditions)},
        "limitations": [
            "Author-built synthetic fixture; this is not independent validation.",
            "Prompt and runner are not part of this audit and require a separate freeze gate.",
            "Internal gold and treatment maps remain accessible locally but are excluded from prompt-safe schemas.",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
