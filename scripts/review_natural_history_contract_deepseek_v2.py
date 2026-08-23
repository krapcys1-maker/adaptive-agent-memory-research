#!/usr/bin/env python3
"""Compact frozen M1 advisory after the preserved oversized v1 failure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import review_natural_history_contract_deepseek as base


base.RUN_ID = "deepseek-v4-flash-natural-history-contract-review-v2-20260823"
base.RUN_DIR = base.ROOT / "data" / "lab" / "api-screening" / base.RUN_ID
base.RUN_CAP = 0.03
base.SYSTEM_PROMPT = """You are a concise adversarial reviewer of a pre-builder natural-history retrieval data contract. Return one JSON object and no prose. Find only the highest-value contract defects. Check schema-versus-rule enforcement, historical Git leakage, stable IDs, Markdown/row canonicalization, duplicate collapse, private query receipts, and development/test sequencing.

This is an author-operated DeepSeek M1 advisory, not independent review. It cannot unlock a builder or backend run. The prior oversized review failed and is not included.

Return exactly:
{"verdict":"admit_for_independent_review|needs_revision|invalid","fatal":["string"],"repairs":[{"severity":"major|minor","artifact":"string","issue":"string","required_test":"string"}],"schema_mismatches":["string"],"privacy_or_leakage_attacks":["string"],"builder_locked":true,"confidence":0.0}

Return at most 8 repairs, 5 schema mismatches, and 5 attacks. Each string must be one sentence."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_job() -> dict[str, Any]:
    root = base.ROOT
    source_schema_path = root / "data/lab/pmlab-natural-history-v0/source-unit-contract-v0.schema.json"
    query_schema_path = root / "data/lab/pmlab-natural-history-v0/query-log-contract-v0.schema.json"
    policy = json.loads((root / "data/lab/pmlab-natural-history-v0/corpus-eligibility-policy-v0.json").read_text(encoding="utf-8"))
    return {
        "job_id": "PMLAB-NATURAL-RET-001-CONTRACT-M1-COMPACT",
        "timing": "No builder, corpus, backend output, or result exists.",
        "source_unit_schema": json.loads(source_schema_path.read_text(encoding="utf-8")),
        "query_log_schema": json.loads(query_schema_path.read_text(encoding="utf-8")),
        "policy_digest": {
            "status": policy["status"], "snapshot_rule": policy["snapshot_rule"],
            "unitization": policy["unitization"], "historical_tree_controls": policy["historical_tree_controls"],
            "query_privacy": policy["query_privacy"], "backend_visible_fields": policy["primary_backend_visible_fields"],
            "pending_before_execution": policy["pending_before_execution"],
        },
        "registered_rules": [
            "Historical files come only from the cutoff Git tree, never the working tree.",
            "Unit IDs exclude snapshot commit and include version, type, path, locator, and search-text hash.",
            "Markdown search text contains CommonMark heading path plus direct body; child bodies are separate.",
            "CSV uses historical headers and source order; JSONL requires I-JSON plus RFC 8785 JCS.",
            "Symlinks, gitlinks, binary, non-UTF-8, and malformed rows fail closed.",
            "Unkeyed private-origin hashes are forbidden; private text and mappings stay local-restricted.",
            "Exact duplicates collapse deterministically with aliases; near duplicates remain.",
            "Independent review and label-free size/token feasibility remain required before builder authorization.",
        ],
        "artifact_hashes": {
            "source_schema": digest(source_schema_path), "query_schema": digest(query_schema_path),
            "policy": digest(root / "data/lab/pmlab-natural-history-v0/corpus-eligibility-policy-v0.json"),
        },
        "authority": "M1 advisory only; builder must remain locked.",
    }


def validate(value: dict[str, Any]) -> dict[str, Any]:
    expected = {"verdict", "fatal", "repairs", "schema_mismatches", "privacy_or_leakage_attacks", "builder_locked", "confidence"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("review differs from exact compact schema")
    if value["verdict"] not in {"admit_for_independent_review", "needs_revision", "invalid"}:
        raise ValueError("invalid verdict")
    for field, limit in (("fatal", 8), ("schema_mismatches", 5), ("privacy_or_leakage_attacks", 5)):
        if not isinstance(value[field], list) or len(value[field]) > limit or any(not isinstance(item, str) or not item.strip() for item in value[field]):
            raise ValueError(f"invalid compact list: {field}")
    if not isinstance(value["repairs"], list) or len(value["repairs"]) > 8:
        raise ValueError("too many repairs")
    for item in value["repairs"]:
        if set(item) != {"severity", "artifact", "issue", "required_test"} or item["severity"] not in {"major", "minor"}:
            raise ValueError("invalid repair")
    if value["builder_locked"] is not True:
        raise ValueError("M1 cannot unlock builder")
    if not isinstance(value["confidence"], (int, float)) or not 0 <= value["confidence"] <= 1:
        raise ValueError("invalid confidence")
    return value


def finalize() -> dict[str, Any]:
    manifest = base.verify()
    if manifest["status"] != "api-run-complete":
        raise ValueError("API review is not complete")
    result = validate(json.loads((base.RUN_DIR / "review-result.json").read_text(encoding="utf-8")))
    lines = [
        "# Compact DeepSeek M1 review of natural-history contracts", "",
        "Status: finalized author-operated advisory; not independent review and builder remains locked", "",
        f"Verdict: `{result['verdict']}` at confidence {result['confidence']:.2f}.", "",
        "## Fatal issues", "", *([f"- {item}" for item in result["fatal"]] or ["- None reported."]), "",
        "## Repair candidates", "", *([f"- **{item['severity']} — {item['artifact']}**: {item['issue']} Test: {item['required_test']}" for item in result["repairs"]] or ["- None reported."]), "",
        "## Authority boundary", "", "The review supplies candidates for deterministic disposition only and cannot authorize a builder or backend run.", "",
    ]
    (base.RUN_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    manifest.update({"status": "review-finalized", "review_result_sha256": base.sha256(base.RUN_DIR / "review-result.json")})
    base.shared.write_json(base.RUN_DIR / "manifest.json", manifest)
    return {"status": manifest["status"], "verdict": result["verdict"], "repairs": len(result["repairs"])}


base.build_job = build_job
base.validate = validate
base.finalize = finalize


if __name__ == "__main__":
    raise SystemExit(base.main())
