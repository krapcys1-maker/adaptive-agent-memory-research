#!/usr/bin/env python3
"""Independent deterministic receipt for the frozen PMLAB-PACK-READER-001 result."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-pack-reader-v0"
RUN_DIR = BASE / "execution-deepseek-v4-flash-v0"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(values: list[str]) -> set[str]:
    return {unicodedata.normalize("NFC", value.strip()) for value in values}


def ratio(a: float, b: float) -> float:
    return a / b if b else 0.0


def main() -> None:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    fixture = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
    responses = load_jsonl(RUN_DIR / "responses.jsonl")
    calls = load_jsonl(RUN_DIR / "calls.jsonl")
    packets = {row["condition_id"]: row for row in load_jsonl(RUN_DIR / "prompt-packets.jsonl")}
    mappings = {row["condition_id"]: row for row in load_jsonl(BASE / "internal" / "condition-map.jsonl")}
    gold = {row["case_id"]: row for row in load_jsonl(BASE / "internal" / "gold.jsonl")}
    cases = {row["case_id"]: row for row in load_jsonl(BASE / "cases.jsonl")}
    summary = json.loads((RUN_DIR / "summary.json").read_text(encoding="utf-8"))

    raw_hashes_ok = all(sha256(RUN_DIR / name) == digest for name, digest in manifest["raw_hashes"].items())
    fixture_hashes_ok = all(sha256(ROOT / name) == digest for name, digest in fixture["hashes"].items())
    response_by_id = {row["condition_id"]: row for row in responses}
    call_counts = Counter(row["condition_id"] for row in calls)
    schema_ok = all(
        row["schema_valid"] is True
        and isinstance(row["value"], dict)
        and set(row["value"]) == {"answer_atoms", "citations", "abstain"}
        for row in responses
    )
    recomputed: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    errors = []
    for condition_id, mapping in mappings.items():
        response = response_by_id[condition_id]
        truth = gold[mapping["case_id"]]
        case = cases[mapping["case_id"]]
        value = response["value"]
        answer, citations = norm(value["answer_atoms"]), norm(value["citations"])
        expected_answer, expected_citations = norm(truth["answer_atoms"]), norm(truth["required_local_ids"])
        stale, valid = norm(truth["stale_atoms"]), set(case["all_local_ids"])
        row = {
            "condition_id": condition_id, "case_id": mapping["case_id"], "group_id": truth["group_id"],
            "language": truth["language"], "exact_answer": answer == expected_answer,
            "citation_tp": len(citations & expected_citations), "citation_required": len(expected_citations),
            "exact_citations": citations == expected_citations, "unresolved": sorted(citations - valid),
            "stale_used": sorted(answer & stale), "abstain": value["abstain"],
            "predicted_citations": sorted(citations), "expected_citations": sorted(expected_citations),
        }
        if not row["exact_answer"] or not row["exact_citations"] or row["unresolved"] or row["stale_used"] or row["abstain"]:
            errors.append(row)
        recomputed[(mapping["format_arm"], mapping["order_arm"])].append(row)

    audit_arms = []
    for key, rows in sorted(recomputed.items()):
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[row["group_id"]].append(row)
        audit_arms.append({
            "format_arm": key[0], "order_arm": key[1], "cases": len(rows),
            "group_exact_answer_count": sum(len(group) == 2 and all(row["exact_answer"] for row in group) for group in groups.values()),
            "case_exact_answer_accuracy": ratio(sum(row["exact_answer"] for row in rows), len(rows)),
            "exact_required_citation_accuracy": ratio(sum(row["exact_citations"] for row in rows), len(rows)),
            "required_citation_recall": ratio(sum(row["citation_tp"] for row in rows), sum(row["citation_required"] for row in rows)),
            "unresolved_citations": sum(len(row["unresolved"]) for row in rows),
            "stale_answer_cases": sum(bool(row["stale_used"]) for row in rows),
            "inappropriate_abstentions": sum(row["abstain"] for row in rows),
        })

    calls_by_id = {row["condition_id"]: row for row in calls}
    mediators = []
    for key in sorted(recomputed):
        ids = [condition_id for condition_id, mapping in mappings.items() if (mapping["format_arm"], mapping["order_arm"]) == key]
        mediators.append({
            "format_arm": key[0], "order_arm": key[1], "conditions": len(ids),
            "mean_serialized_user_utf8_bytes": sum(packets[item]["serialized_utf8_bytes"] for item in ids) / len(ids),
            "mean_provider_prompt_tokens": sum(calls_by_id[item]["prompt_tokens"] for item in ids) / len(ids),
            "mean_latency_ms": sum(calls_by_id[item]["latency_ms"] for item in ids) / len(ids),
            "conservative_cost_usd": round(sum(calls_by_id[item]["conservative_cost_usd"] for item in ids), 8),
        })
    full_bytes = next(row["mean_serialized_user_utf8_bytes"] for row in mediators if row["format_arm"] == "F0_FULL")
    compact_bytes = next(row["mean_serialized_user_utf8_bytes"] for row in mediators if row["format_arm"] == "F1_COMPACT")
    full_tokens = next(row["mean_provider_prompt_tokens"] for row in mediators if row["format_arm"] == "F0_FULL")
    compact_tokens = next(row["mean_provider_prompt_tokens"] for row in mediators if row["format_arm"] == "F1_COMPACT")
    mediator_report = {
        "status": "registered descriptive mediators computed after raw freeze",
        "arms": mediators,
        "compact_minus_full_mean_utf8_bytes": compact_bytes - full_bytes,
        "compact_relative_utf8_reduction": ratio(full_bytes - compact_bytes, full_bytes),
        "compact_minus_full_mean_prompt_tokens": compact_tokens - full_tokens,
        "compact_relative_prompt_token_reduction": ratio(full_tokens - compact_tokens, full_tokens),
        "boundary": "Descriptive provider and serialization costs; not a causal latency claim and not an architecture recommendation.",
    }
    (RUN_DIR / "registered-descriptive-mediators.json").write_text(
        json.dumps(mediator_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )

    summary_core = {
        (row["format_arm"], row["order_arm"]): (
            row["group_exact_answer_count"], row["case_exact_answer_accuracy"],
            row["exact_required_citation_accuracy"], row["required_citation_recall"]
        ) for row in summary["arms"]
    }
    audit_core = {
        (row["format_arm"], row["order_arm"]): (
            row["group_exact_answer_count"], row["case_exact_answer_accuracy"],
            row["exact_required_citation_accuracy"], row["required_citation_recall"]
        ) for row in audit_arms
    }
    checks = {
        "raw_hashes_match_frozen_manifest": raw_hashes_ok,
        "fixture_hashes_match": fixture_hashes_ok,
        "condition_response_call_sets_exact": set(mappings) == set(response_by_id) == set(calls_by_id) == set(packets),
        "one_http_call_per_condition": len(calls) == 128 and set(call_counts.values()) == {1},
        "all_responses_exact_schema": schema_ok,
        "independent_core_metrics_match_frozen_scorer": summary_core == audit_core,
        "all_frozen_gates_reported_passed": summary["all_compatibility_gates_passed"] is True and all(row["passed"] for row in summary["gates"]),
        "local_cost_matches_manifest": abs(sum(row["conservative_cost_usd"] for row in calls) - manifest["run_cost_usd"]) < 1e-9,
    }
    report = {
        "experiment_id": "PMLAB-PACK-READER-001", "passed": all(checks.values()), "checks": checks,
        "recomputed_arms": audit_arms, "exception_count": len(errors), "exceptions": errors,
        "interpretation": [
            "All four arms passed the frozen single-reader compatibility gates.",
            "One compact-governed Polish condition returned correct answers but substituted R03 for required R02; R03 resolved but did not support the requested atom.",
            "The result establishes compatibility for one synthetic fixture and one reader family, not superiority or natural-history validity.",
        ],
    }
    (RUN_DIR / "result-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"passed": report["passed"], "checks": checks, "exception_count": len(errors), "mediators": mediator_report}, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
