#!/usr/bin/env python3
"""Post-run, same-author completion receipt for PMLAB-PACK-READER-001.

This audit does not create independent validation. It checks that the committed
construction, prompt, authorization, raw-response, scoring, and budget evidence
actually proves the first-reader branch was executed under its frozen contract.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-pack-reader-v0"
RUN_DIR = BASE / "execution-deepseek-v4-flash-v0"
OUTPUT = RUN_DIR / "completion-audit.json"

FIXTURE_COMMIT = "365c0b6c0ae159b1517fbc87941aa33a8e369da2"
PROMPT_COMMIT = "d870741e8bba6257d12288b23d1e8f367571ae6e"
AUTH_COMMIT = "5f98277"
RAW_COMMIT = "1df509b7b71f144fb924ba3737ec6c919de5857e"
SCORE_COMMIT = "b114865"

FIXTURE_PATHS = [
    "data/lab/pmlab-pack-reader-v0/blind/schedule.jsonl",
    "data/lab/pmlab-pack-reader-v0/cases.jsonl",
    "data/lab/pmlab-pack-reader-v0/corpus.jsonl",
    "data/lab/pmlab-pack-reader-v0/internal/condition-map.jsonl",
    "data/lab/pmlab-pack-reader-v0/internal/construction-audit.json",
    "data/lab/pmlab-pack-reader-v0/internal/gold.jsonl",
    "data/lab/pmlab-pack-reader-v0/internal/groups.jsonl",
    "data/lab/pmlab-pack-reader-v0/sources/english/evidence.md",
    "data/lab/pmlab-pack-reader-v0/sources/polish/evidence.md",
    "scripts/audit_pack_reader_fixture.py",
    "scripts/build_pack_reader_fixture.py",
    "scripts/freeze_pack_reader_fixture.py",
]
PROMPT_PATHS = [
    "data/lab/pmlab-pack-reader-v0/execution-deepseek-v4-flash-v0/prompt-packets.jsonl",
    "data/lab/pmlab-pack-reader-v0/execution-deepseek-v4-flash-v0/prompt-audit.json",
    "data/lab/pmlab-pack-reader-v0/execution-deepseek-v4-flash-v0/system-prompt.txt",
    "scripts/run_pack_reader_benchmark.py",
]
RAW_PATHS = [
    "data/lab/pmlab-pack-reader-v0/execution-deepseek-v4-flash-v0/calls.jsonl",
    "data/lab/pmlab-pack-reader-v0/execution-deepseek-v4-flash-v0/raw-responses.jsonl",
    "data/lab/pmlab-pack-reader-v0/execution-deepseek-v4-flash-v0/responses.jsonl",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_ok(*args: str) -> bool:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=False
    ).returncode == 0


def paths_match_commit(commit: str, paths: list[str]) -> bool:
    return git_ok("diff", "--quiet", commit, "HEAD", "--", *paths)


def build_audit() -> dict[str, Any]:
    construction = load_json(BASE / "manifest.json")
    construction_audit = load_json(BASE / "internal" / "construction-audit.json")
    execution = load_json(RUN_DIR / "manifest.json")
    authorization = (RUN_DIR / "PRE_RUN_AUTHORIZATION.md").read_text(encoding="utf-8")
    preflight = load_json(RUN_DIR / "preflight.json")
    prompt_audit = load_json(RUN_DIR / "prompt-audit.json")
    pre_run_prompt_audit = load_json(RUN_DIR / "pre-run-prompt-audit.json")
    result_audit = load_json(RUN_DIR / "result-audit.json")
    summary = load_json(RUN_DIR / "summary.json")
    cases = load_jsonl(BASE / "cases.jsonl")
    corpus = load_jsonl(BASE / "corpus.jsonl")
    groups = load_jsonl(BASE / "internal" / "groups.jsonl")
    gold = load_jsonl(BASE / "internal" / "gold.jsonl")
    calls = load_jsonl(RUN_DIR / "calls.jsonl")
    responses = load_jsonl(RUN_DIR / "responses.jsonl")
    ledger = load_jsonl(ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl")

    corpus_by_case: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in corpus:
        corpus_by_case.setdefault((row["group_id"], row["language"]), {})[row["local_id"]] = row
    case_by_id = {row["case_id"]: row for row in cases}
    required_buckets: list[str] = []
    required_positions: list[list[int]] = []
    for truth in gold:
        case = case_by_id[truth["case_id"]]
        records = corpus_by_case[(truth["group_id"], truth["language"])]
        required_buckets.extend(records[item]["bucket"] for item in truth["required_local_ids"])
        required_positions.append(
            [case["retrieval_order"].index(item) + 1 for item in truth["required_local_ids"]]
        )

    pack_ledger = [
        row for row in ledger
        if row.get("run_id") == execution["run_id"]
    ]
    call_ids = [row["condition_id"] for row in calls]
    response_ids = [row["condition_id"] for row in responses]
    response_receipts = [row["response_id"] for row in calls]

    checks = {
        "construction_manifest_is_preserved_pre_run_snapshot": (
            construction["status"] == "fixture-and-opaque-schedule-frozen-before-runner"
            and construction["api_authorized"] is False
            and construction["runner"] == "not-built"
        ),
        "fixture_and_construction_audit_pass": (
            construction_audit["passed"] is True
            and all(construction_audit["checks"].values())
            and construction_audit["counts"]
            == {"groups": 16, "cases": 32, "records": 256, "conditions": 128}
        ),
        "registered_fixture_coverage_present": (
            {row["answer_count"] for row in groups} == {1, 2, 3}
            and {"current", "supporting"}.issubset(set(required_buckets))
            and all(any(3 <= position <= 6 for position in positions) for positions in required_positions)
            and {row["language"] for row in cases} == {"en", "pl"}
            and all(row["trust"] == "reviewed" for row in corpus)
            and set(row["bucket"] for row in corpus)
            == {"current", "supporting", "stale_conflicting", "distractor"}
        ),
        "fixture_bytes_match_freeze_commit": paths_match_commit(FIXTURE_COMMIT, FIXTURE_PATHS),
        "prompt_runner_bytes_match_freeze_commit": paths_match_commit(PROMPT_COMMIT, PROMPT_PATHS),
        "raw_bytes_match_pre_score_freeze_commit": paths_match_commit(RAW_COMMIT, RAW_PATHS),
        "freeze_authorize_run_score_commit_order": (
            git_ok("merge-base", "--is-ancestor", FIXTURE_COMMIT, PROMPT_COMMIT)
            and git_ok("merge-base", "--is-ancestor", PROMPT_COMMIT, AUTH_COMMIT)
            and git_ok("merge-base", "--is-ancestor", AUTH_COMMIT, RAW_COMMIT)
            and git_ok("merge-base", "--is-ancestor", RAW_COMMIT, SCORE_COMMIT)
        ),
        "prompt_and_leakage_audits_pass": (
            prompt_audit["passed"] is True
            and prompt_audit["same_record_ids_and_text_across_arms"] is True
            and prompt_audit["treatment_or_gold_names_absent_from_packets"] is True
            and pre_run_prompt_audit["passed"] is True
            and pre_run_prompt_audit["gold_joined"] is False
            and pre_run_prompt_audit["locators_resolved_exactly"] == 1024
        ),
        "model_and_decoding_match_protocol": (
            execution["model"] == "deepseek-v4-flash"
            and execution["temperature"] == 0
            and execution["thinking"] == "disabled"
            and execution["conditions"] == 128
            and "API execution authorized" in authorization
        ),
        "preflight_passes_experiment_and_global_caps": (
            preflight["passes"] is True
            and preflight["one_attempt_usd"] < preflight["run_cap_usd"]
            and preflight["all_conditions_retry_usd"] < preflight["run_cap_usd"]
            and preflight["global_spent_before_usd"] + preflight["all_conditions_retry_usd"]
            < preflight["global_cap_usd"]
        ),
        "exactly_one_successful_call_per_condition_and_no_retry": (
            len(calls) == len(responses) == 128
            and len(set(call_ids)) == len(set(response_ids)) == 128
            and set(call_ids) == set(response_ids)
            and Counter(row["attempt"] for row in calls) == {1: 128}
            and len(set(response_receipts)) == 128
            and all(row["schema_valid"] is True and not row["errors"] for row in responses)
        ),
        "budget_ledger_has_exact_call_receipts_and_cost": (
            len(pack_ledger) == 128
            and {row["condition_id"] for row in pack_ledger} == set(call_ids)
            and {row["response_id"] for row in pack_ledger} == set(response_receipts)
            and abs(sum(row["conservative_cost_usd"] for row in pack_ledger) - 0.04026) < 1e-12
            and execution["run_cost_usd"] < execution["run_budget_usd"]
        ),
        "declared_prompt_raw_and_score_hashes_match": (
            all(sha256(RUN_DIR / name) == digest for name, digest in execution["hashes"].items())
            and all(sha256(RUN_DIR / name) == digest for name, digest in execution["raw_hashes"].items())
            and sha256(RUN_DIR / "scored.jsonl") == execution["scored_sha256"]
            and sha256(RUN_DIR / "summary.json") == execution["summary_sha256"]
        ),
        "deterministic_result_audit_and_all_registered_gates_pass": (
            result_audit["passed"] is True
            and all(result_audit["checks"].values())
            and summary["all_compatibility_gates_passed"] is True
            and all(row["passed"] for row in summary["gates"])
        ),
        "claim_boundary_and_exception_preserved": (
            result_audit["exception_count"] == 1
            and result_audit["exceptions"][0]["case_id"] == "PRG-14-PL"
            and "no retrieval, natural-history, cross-family, or architecture claim"
            in summary["claim_boundary"]
        ),
    }

    return {
        "experiment_id": "PMLAB-PACK-READER-001",
        "audit_type": "post-run same-author completion audit",
        "passed": all(checks.values()),
        "checks": checks,
        "milestones": {
            "fixture_freeze_commit": FIXTURE_COMMIT,
            "prompt_runner_freeze_commit": PROMPT_COMMIT,
            "authorization_commit": AUTH_COMMIT,
            "raw_response_freeze_commit": RAW_COMMIT,
            "score_and_result_commit": SCORE_COMMIT,
        },
        "observed": {
            "semantic_groups": 16,
            "bilingual_cases": 32,
            "conditions": 128,
            "http_calls": len(calls),
            "retries": sum(row["attempt"] - 1 for row in calls),
            "run_cost_usd": round(sum(row["conservative_cost_usd"] for row in pack_ledger), 8),
            "result_exception_count": result_audit["exception_count"],
        },
        "completion_decision": (
            "First-reader build/freeze/authorize/execute/score/audit branch complete. "
            "Fixture is spent; full and compact formats remain candidates, governed order is not promoted."
        ),
        "remaining_external_validity_gate": (
            "Unchanged cross-family replication or independently reviewed natural-history development is required "
            "before any format/order recommendation."
        ),
        "limitations": [
            "This completion receipt is deterministic but same-author; it is not independent review.",
            "It proves committed artifact continuity and registered gates, not natural-history validity or architecture superiority.",
            "The construction manifest intentionally remains the pre-run snapshot; execution status lives in the run manifest and this receipt.",
        ],
    }


def main() -> None:
    report = build_audit()
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
