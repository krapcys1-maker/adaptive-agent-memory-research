#!/usr/bin/env python3
"""Build a gold-free independent adjudication packet and private triage index."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1"
PACKET_DIR = CORPUS_DIR / "independent-adjudication-v1"
BLIND_DIR = PACKET_DIR / "blind"
CASES_PATH = CORPUS_DIR / "cases.jsonl"
QUEUE_PATH = CORPUS_DIR / "independent-review-queue.jsonl"
SCHEMA_PATH = CORPUS_DIR / "case-schema-v1.json"
AMENDMENT_PATH = CORPUS_DIR / "case-schema-amendment-v1.json"
ENTITY_PATH = CORPUS_DIR / "entity-catalog-v1.json"
PREDICATE_PATH = CORPUS_DIR / "predicate-catalog-v1.json"
FIRST_COMPARISON = ROOT / "data" / "lab" / "api-screening" / "deepseek-v4-flash-map-stage-advisory-review-20260822" / "comparison.jsonl"
SECOND_COMPARISON = ROOT / "data" / "lab" / "api-screening" / "deepseek-v4-flash-map-stage-remaining-review-20260822" / "comparison.jsonl"
CORPUS_FREEZE_COMMIT = "fc9b212"
BUILDER_VERSION = "mapper-independent-adjudication-packet-v1.1"
FORBIDDEN_BLIND_KEYS = {"gold", "criticality", "split", "stratum", "provenance", "evaluation_metadata", "advisory_label", "exact_agreement"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(canonical(row) + "\n" for row in rows)


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def recursive_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(value)
        for child in value.values():
            keys.update(recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(recursive_keys(child))
    return keys


def select_groups(cases: list[dict[str, Any]]) -> tuple[set[str], dict[str, str]]:
    meta: dict[str, tuple[str, str]] = {}
    for case in cases:
        meta[case["semantic_group_id"]] = (case["stage"], case["criticality"])
    critical = {group for group, (_, level) in meta.items() if level == "critical"}
    ordinary_by_stage: dict[str, list[str]] = defaultdict(list)
    for group, (stage, level) in meta.items():
        if level == "ordinary":
            ordinary_by_stage[stage].append(group)
    ordinary_sample = {
        min(groups, key=lambda group: hashlib.sha256(group.encode("utf-8")).hexdigest())
        for groups in ordinary_by_stage.values()
    }
    selected = critical | ordinary_sample
    reasons = {group: "all-critical" if group in critical else "deterministic-ordinary-stage-sample" for group in selected}
    return selected, reasons


def build_outputs() -> dict[Path, str]:
    cases = read_jsonl(CASES_PATH)
    queue = read_jsonl(QUEUE_PATH)
    selected, reasons = select_groups(cases)
    case_meta = {case["case_id"]: case for case in cases}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in queue:
        group = row["case_id"].rsplit("-", 1)[0]
        if group in selected:
            public = {key: value for key, value in row.items() if key != "review_fields"}
            if recursive_keys(public) & FORBIDDEN_BLIND_KEYS:
                raise ValueError(f"blind leakage in {row['case_id']}")
            grouped[group].append(public)
    jobs = []
    forms = []
    for group in sorted(selected):
        rows = sorted(grouped[group], key=lambda row: row["language"])
        if len(rows) != 2 or {row["language"] for row in rows} != {"en", "pl"}:
            raise ValueError(f"{group}: incomplete language pair")
        jobs.append({"semantic_group_id": group, "stage": rows[0]["stage"], "cases": rows})
        forms.append(
            {
                "semantic_group_id": group,
                "source_commit": CORPUS_FREEZE_COMMIT,
                "reviewer_id_or_pseudonym": None,
                "reviewer_family_or_affiliation": None,
                "reviewed_at": None,
                "independent_labels": {"en": None, "pl": None},
                "language_equivalent": None,
                "stage_isolation": None,
                "disputed_or_underspecified_fields": [],
                "confidence": None,
                "exclude_recommendation": None,
                "rationale": None,
                "attestation_id": None,
            }
        )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    amendment = json.loads(AMENDMENT_PATH.read_text(encoding="utf-8"))
    contract = {
        "schema_version": schema["schema_version"],
        "stage_outputs": schema["stage_outputs"],
        "review_label_contracts": {
            "contract_span": {"decision": "enum", "reject_reason": "enum"},
            "obligation_graph": {
                "query_status": "enum excluding unauthorized in isolated review",
                "nodes": [{"obligation_id": "O#", "operator": "enum", "source_span": "exact string", "depends": ["prior O#"]}],
            },
            "entity_linking": {
                "action": "enum",
                "candidate_ids": ["entity ID strings"],
                "selected_id": "entity ID, ref:O#, or null",
                "selected_ids": ["entity ID strings; [] unless true multi-entity selection"],
            },
            "predicate_linking": {
                "action": "enum",
                "ranked_predicates": ["predicate ID strings only"],
                "selected_predicate": "predicate ID or null",
                "selected_namespaces": ["namespace ID strings"],
            },
            "time_authorization": {
                "time_status": "enum", "authorization_status": "enum", "raw_span": "exact string",
                "normalized_time": "canonical string", "timezone": "IANA zone", "reference_clock": "input string",
                "principal": "input string", "policy_basis": "explicit string",
                "authorized_namespaces": ["namespace strings"], "denied_namespaces": ["namespace strings"],
            },
            "certificate_routing": {"certificate_status": "enum", "action": "enum", "basis": "nonempty evidence/failure string"},
        },
        "non_exercisable_under_isolated_stage_input": amendment["non_exercisable_under_isolated_stage_input"],
        "review_note": "Use review-manual-v1.md canonical rules; do not inspect author labels.",
    }
    attestation = {
        "attestation_id": None,
        "reviewer_id_or_pseudonym": None,
        "reviewer_family_or_affiliation": None,
        "review_started_at": None,
        "review_completed_at": None,
        "source_commit": CORPUS_FREEZE_COMMIT,
        "packet_manifest_sha256": None,
        "statements": {
            "did_not_inspect_author_gold": None,
            "did_not_inspect_advisory_predictions_or_scores": None,
            "did_not_inspect_candidate_implementations": None,
            "labeled_each_language_before_reveal": None,
            "disclosed_conflicts_or_prior_exposure": None,
        },
        "conflict_or_prior_exposure_notes": None,
        "signature_or_verifiable_acknowledgement": None,
    }
    first_rows = {row["case_id"]: row for row in read_jsonl(FIRST_COMPARISON)}
    second_rows = {row["case_id"]: row for row in read_jsonl(SECOND_COMPARISON)}
    comparisons = {**first_rows, **second_rows}
    priority = []
    for group in sorted(selected):
        source_cases = [case for case in cases if case["semantic_group_id"] == group]
        prior = [comparisons[case["case_id"]] for case in source_cases]
        invalid = any(row.get("prediction_status") == "schema_invalid_after_retries" for row in prior)
        disagreement = any(not row.get("exact_agreement", False) for row in prior)
        criticality = source_cases[0]["criticality"]
        level = "P0" if criticality == "critical" and (invalid or disagreement) else "P1" if criticality == "critical" or disagreement else "P2"
        priority.append(
            {
                "semantic_group_id": group,
                "stage": source_cases[0]["stage"],
                "criticality": criticality,
                "stratum": source_cases[0]["evaluation_metadata"]["stratum"],
                "selection_reason": reasons[group],
                "priority": level,
                "prior_advisory_schema_invalid": invalid,
                "prior_advisory_exact_disagreement": disagreement,
                "case_ids": [case["case_id"] for case in source_cases],
                "release_boundary": "do-not-show-before-independent-label-freeze",
            }
        )
    selection_audit = {
        "corpus_groups": 77,
        "critical_groups_selected": sum(row["criticality"] == "critical" for row in priority),
        "ordinary_groups_selected": sum(row["criticality"] == "ordinary" for row in priority),
        "selected_groups": len(priority),
        "selected_rows": len(jobs) * 2,
        "ordinary_sampling": "minimum sha256(semantic_group_id) within each stage",
        "stage_counts": dict(sorted(Counter(row["stage"] for row in priority).items())),
        "priority_counts": dict(sorted(Counter(row["priority"] for row in priority).items())),
        "warning": "This file reveals selection/priority metadata and is not part of the blind reviewer packet.",
    }
    outputs = {
        BLIND_DIR / "jobs.jsonl": jsonl(jobs),
        BLIND_DIR / "review-form.jsonl": jsonl(forms),
        BLIND_DIR / "stage-output-contract-v1.json": pretty(contract),
        BLIND_DIR / "entity-catalog-v1.json": ENTITY_PATH.read_text(encoding="utf-8"),
        BLIND_DIR / "predicate-catalog-v1.json": PREDICATE_PATH.read_text(encoding="utf-8"),
        BLIND_DIR / "attestation.json": pretty(attestation),
        PACKET_DIR / "selection-audit.json": pretty(selection_audit),
        PACKET_DIR / "internal-priority-index.jsonl": jsonl(priority),
    }
    manual_path = BLIND_DIR / "review-manual-v1.md"
    if not manual_path.exists():
        raise ValueError("blind review manual is missing")
    blind_hashes = {path.name: sha_bytes(content.encode("utf-8")) for path, content in outputs.items() if path.parent == BLIND_DIR}
    blind_hashes[manual_path.name] = sha_bytes(manual_path.read_bytes())
    manifest = {
        "packet": "PMLAB-MAP-STAGE-001-independent-adjudication-v1",
        "packet_revision": "1.1-pre-review-concrete-label-contracts",
        "status": "blank-blind-packet-awaiting-independent-reviewer",
        "builder_version": BUILDER_VERSION,
        "corpus_freeze_commit": CORPUS_FREEZE_COMMIT,
        "selected_semantic_groups": len(jobs),
        "selected_rows": len(jobs) * 2,
        "critical_groups": selection_audit["critical_groups_selected"],
        "ordinary_groups": selection_audit["ordinary_groups_selected"],
        "ordinary_fraction_of_corpus_ordinary": selection_audit["ordinary_groups_selected"] / 16,
        "all_six_stages_represented": len(selection_audit["stage_counts"]) == 6,
        "blind_forbidden_fields_absent": True,
        "gold_or_advisory_labels_in_blind_packet": False,
        "reviewer": None,
        "completed_review_form_hash": None,
        "independent_review_status": "not-started",
        "blind_hashes": dict(sorted(blind_hashes.items())),
        "authority": "packet preparation only; does not confer independent review",
    }
    outputs[BLIND_DIR / "manifest.json"] = pretty(manifest)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build_outputs()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, content in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        if stale:
            raise SystemExit("stale or missing packet artifacts: " + ", ".join(stale))
    else:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    manifest = json.loads(outputs[BLIND_DIR / "manifest.json"])
    print(canonical({"groups": manifest["selected_semantic_groups"], "rows": manifest["selected_rows"], "status": manifest["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
