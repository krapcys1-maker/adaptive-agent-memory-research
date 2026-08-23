#!/usr/bin/env python3
"""Frozen DeepSeek semantic challenge of the blind Foundation contract packet."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_natural_history_contract_deepseek as base


base.RUN_ID = "deepseek-v4-flash-foundation-contract-semantic-review-20260823"
base.RUN_DIR = base.ROOT / "data" / "lab" / "api-screening" / base.RUN_ID
base.RUN_CAP = 0.10
base.GLOBAL_CAP = 10.0
BLIND = base.ROOT / "data" / "lab" / "pmlab-foundation-v0" / "independent-contract-review-v0" / "blind"

base.SYSTEM_PROMPT = """You are an adversarial semantic reviewer of two local-first LLM-memory research contracts: canonical evidence plus F0-F5 diagnostic receipts, and delayed future-task reveal plus leakage controls. Return exactly one JSON object and no prose. Use only the supplied blind packet and subject artifacts. Treat absent controls as absent. Do not infer that any construction test passed.

Attack evidence identity, time, correction, authorization, privacy, retention, provenance, concurrency, receipt semantics, correlated probes, physical-loss diagnosis, process isolation, counterfactual-fork strength, reader/gold separation, same-author bias, and external validity. Shared words are not automatically leakage; low lexical overlap is not proof of independence.

You are an author-operated DeepSeek cross-family challenge, not a human, storage expert, security auditor, statistician, institutionally independent reviewer, or second fixture author. You cannot authorize the parent benchmark or product architecture. The parent_experiment gate must be deny.

Return exactly:
{"findings":[{"question_id":"A01","verdict":"pass|conditional|fail|not_assessable","severity":"none|minor|major|blocking","evidence_locators":["artifact:locator"],"rationale":"string","required_change":"string or null"}],"overall_verdict":"admit_for_second_author_pilot|needs_revision|invalid","gate_recommendations":{"canonical_contract":"deny|conditional|admit_for_unseen_fixture","delayed_reveal_contract":"deny|conditional|admit_for_unseen_fixture","parent_experiment":"deny"},"blocking_findings":["Axx"],"residual_risks":["string"],"overall_rationale":"string"}

Return all A01-A12 findings exactly once and in order. A pass needs a precise locator. Keep each rationale and required change concise. Do not claim independence."""


def build_job() -> dict[str, Any]:
    manifest = json.loads((BLIND / "packet-manifest.json").read_text(encoding="utf-8"))
    questions = json.loads((BLIND / "questions.json").read_text(encoding="utf-8"))
    return {
        "job_id": "PMLAB-FOUNDATION-CONTRACT-REVIEW-M1",
        "packet_id": manifest["packet_id"],
        "review_manual": (BLIND / "review-manual.md").read_text(encoding="utf-8"),
        "questions": questions["questions"],
        "subject_artifacts": {
            path: (base.ROOT / path).read_text(encoding="utf-8")
            for path in manifest["subject_artifacts"]
        },
        "artifact_hashes": manifest["subject_artifacts"],
        "timing": "The packet supplies contracts and authored fixtures only. No construction result, invalid mutation set, prior review, project-memory summary, or preferred architecture is included.",
        "authority_boundary": "Author-operated cross-family semantic challenge only; cannot satisfy second-author or institutional independence and parent experiment must remain denied.",
        "data_boundary": "Synthetic public repository artifacts only; no secrets, personal data, credentials, private queries, or chain of thought.",
    }


def validate(value: dict[str, Any]) -> dict[str, Any]:
    expected = {"findings", "overall_verdict", "gate_recommendations", "blocking_findings", "residual_risks", "overall_rationale"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("review differs from exact schema")
    findings = value["findings"]
    if not isinstance(findings, list) or [row.get("question_id") for row in findings] != [f"A{i:02d}" for i in range(1, 13)]:
        raise ValueError("findings must contain A01-A12 in order")
    for row in findings:
        if set(row) != {"question_id", "verdict", "severity", "evidence_locators", "rationale", "required_change"}:
            raise ValueError("finding fields")
        if row["verdict"] not in {"pass", "conditional", "fail", "not_assessable"}:
            raise ValueError("finding verdict")
        if row["severity"] not in {"none", "minor", "major", "blocking"}:
            raise ValueError("finding severity")
        if not isinstance(row["evidence_locators"], list) or any(not isinstance(x, str) or not x.strip() for x in row["evidence_locators"]):
            raise ValueError("finding locators")
        if not isinstance(row["rationale"], str) or not row["rationale"].strip():
            raise ValueError("finding rationale")
        if row["required_change"] is not None and (not isinstance(row["required_change"], str) or not row["required_change"].strip()):
            raise ValueError("finding required change")
        if row["verdict"] == "pass" and not row["evidence_locators"]:
            raise ValueError("pass lacks locator")
    if value["overall_verdict"] not in {"admit_for_second_author_pilot", "needs_revision", "invalid"}:
        raise ValueError("overall verdict")
    gates = value["gate_recommendations"]
    if set(gates) != {"canonical_contract", "delayed_reveal_contract", "parent_experiment"}:
        raise ValueError("gate fields")
    if gates["canonical_contract"] not in {"deny", "conditional", "admit_for_unseen_fixture"} or gates["delayed_reveal_contract"] not in {"deny", "conditional", "admit_for_unseen_fixture"}:
        raise ValueError("contract gate")
    if gates["parent_experiment"] != "deny":
        raise ValueError("model cannot unlock parent")
    ids = {row["question_id"] for row in findings}
    if not isinstance(value["blocking_findings"], list) or not set(value["blocking_findings"]) <= ids:
        raise ValueError("blocking findings")
    if any(not isinstance(x, str) or not x.strip() for x in value["residual_risks"]):
        raise ValueError("residual risks")
    if not isinstance(value["overall_rationale"], str) or not value["overall_rationale"].strip():
        raise ValueError("overall rationale")
    return value


def finalize() -> dict[str, Any]:
    manifest = base.verify()
    if manifest["status"] != "api-run-complete":
        raise ValueError("API review is not complete")
    result = validate(json.loads((base.RUN_DIR / "review-result.json").read_text(encoding="utf-8")))
    lines = [
        "# DeepSeek semantic challenge of Foundation contracts", "",
        "Status: finalized author-operated cross-family challenge; not independent review", "",
        f"Overall verdict: `{result['overall_verdict']}`.", "",
        "## Findings", "",
    ]
    for row in result["findings"]:
        lines += [f"### {row['question_id']} — {row['verdict']} / {row['severity']}", "", row["rationale"], "", f"Required change: {row['required_change'] or 'none'}", ""]
    lines += [
        "## Authority boundary", "",
        "This model review can propose repairs or deny advancement. It cannot satisfy a human/different-team review, create an unseen second-author fixture, authorize PMLAB-FOUNDATION-001, or select architecture.", "",
    ]
    (base.RUN_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    manifest.update({"status": "review-finalized", "review_result_sha256": base.sha256(base.RUN_DIR / "review-result.json")})
    base.shared.write_json(base.RUN_DIR / "manifest.json", manifest)
    return {"status": manifest["status"], "overall_verdict": result["overall_verdict"], "blocking_findings": result["blocking_findings"], "gates": result["gate_recommendations"]}


base.build_job = build_job
base.validate = validate
base.finalize = finalize


if __name__ == "__main__":
    raise SystemExit(base.main())
