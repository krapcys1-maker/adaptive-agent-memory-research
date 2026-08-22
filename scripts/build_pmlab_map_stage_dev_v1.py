#!/usr/bin/env python3
"""Build and validate the first PMLAB-MAP stage-dev-v1 corpus tranche."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1"
BUILDER_VERSION = "pmlab-map-stage-dev-builder-v1"
SOURCE_PATH = DATA_DIR / "contract-entity-groups-v1.jsonl"
CATALOG_PATH = DATA_DIR / "entity-catalog-v1.json"
SCHEMA_PATH = DATA_DIR / "case-schema-v1.json"
ALLOCATION_PATH = DATA_DIR / "case-allocation-v1.csv"
AUTHORED_AT = "2026-08-22T00:00:00Z"
ALLOWED_OPERATORS = {
    "SELECT", "FILTER", "PROJECT", "AGGREGATE", "GROUP", "SUPERLATIVE",
    "COMPARATIVE", "UNION", "INTERSECTION", "DIFFERENCE", "SORT", "BOOLEAN", "ARITHMETIC",
}
SAFE_UNRESOLVED_CERTIFICATES = {"ambiguous", "inapplicable"}
CONTRACT_REQUIRED = {
    "obligation_id", "operator", "span_text", "depends", "entity", "predicate",
    "namespaces", "time", "authorization", "certificate",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def render_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(row) + "\n" for row in rows)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def catalog_ids(catalog: dict[str, Any]) -> set[str]:
    return {item["id"] for item in catalog["entities"]}


def validate_entity_expression(value: str, ids: set[str]) -> str | None:
    if value.startswith("type:"):
        return None
    if value.startswith("ref:") or value.startswith("refs:"):
        return None
    if value.startswith("nil:"):
        return None
    if value.startswith("ambiguous:"):
        candidates = value.removeprefix("ambiguous:").split(",")
        return None if len(candidates) >= 2 and not (set(candidates) - ids) else "unknown_catalog_id"
    return None if value in ids else "unknown_catalog_id"


def contract_decision(variant: dict[str, Any], ids: set[str]) -> dict[str, str]:
    if "candidate_text" in variant:
        try:
            payload = json.loads(variant["candidate_text"])
        except json.JSONDecodeError:
            return {"decision": "typed_reject", "reject_reason": "invalid_serialization"}
    else:
        payload = variant.get("candidate_payload")
    if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list) or payload.get("query_status") not in {
        "resolved", "ambiguous", "unauthorized", "unsupported_structure"
    }:
        return {"decision": "typed_reject", "reject_reason": "missing_required_field"}
    raw_query = variant["raw_query"]
    previous: list[str] = []
    for index, node in enumerate(payload["nodes"], start=1):
        if not isinstance(node, dict) or CONTRACT_REQUIRED - set(node):
            return {"decision": "typed_reject", "reject_reason": "missing_required_field"}
        if node["obligation_id"] != f"O{index}" or any(dep not in previous for dep in node["depends"]):
            return {"decision": "typed_reject", "reject_reason": "invalid_dependency"}
        previous.append(node["obligation_id"])
        if node["operator"] not in ALLOWED_OPERATORS:
            return {"decision": "typed_reject", "reject_reason": "missing_required_field"}
        if not isinstance(node["span_text"], str) or not node["span_text"] or node["span_text"] not in raw_query:
            return {"decision": "typed_reject", "reject_reason": "non_source_span"}
        if not isinstance(node["entity"], str) or not node["entity"]:
            return {"decision": "typed_reject", "reject_reason": "missing_required_field"}
        entity_error = validate_entity_expression(node["entity"], ids)
        if entity_error:
            return {"decision": "typed_reject", "reject_reason": entity_error}
        if not isinstance(node["namespaces"], list) or not isinstance(node["depends"], list):
            return {"decision": "typed_reject", "reject_reason": "missing_required_field"}
        if payload["query_status"] in {"ambiguous", "unauthorized"} and node["certificate"] not in SAFE_UNRESOLVED_CERTIFICATES:
            return {"decision": "typed_reject", "reject_reason": "unsafe_unresolved_state"}
    if payload["query_status"] == "unsupported_structure" and payload["nodes"]:
        return {"decision": "typed_reject", "reject_reason": "unsafe_unresolved_state"}
    return {"decision": "accept", "reject_reason": "none"}


def validate_group_sources(groups: list[dict[str, Any]], catalog: dict[str, Any], schema: dict[str, Any]) -> None:
    ids = catalog_ids(catalog)
    seen: set[str] = set()
    counts = Counter((group["stage"], group["stratum"]) for group in groups)
    expected = {
        ("contract_span", "valid_nested_contract"): 2,
        ("contract_span", "wrong_valid_contract"): 2,
        ("contract_span", "invalid_serialization_or_fields"): 2,
        ("contract_span", "dependency_and_id_integrity"): 2,
        ("entity_linking", "exact_alias_and_paraphrase"): 3,
        ("entity_linking", "in_catalog_collision"): 3,
        ("entity_linking", "missing_entity"): 3,
        ("entity_linking", "non_entity_phrase"): 3,
        ("entity_linking", "coreference_and_multi_entity"): 2,
    }
    if counts != expected:
        raise ValueError(f"source allocation mismatch: {dict(counts)}")
    for group in groups:
        gid = group["semantic_group_id"]
        if gid in seen:
            raise ValueError(f"duplicate semantic group: {gid}")
        seen.add(gid)
        if group["stage"] not in schema["allowed_stages"] or set(group["variants"]) != {"en", "pl"}:
            raise ValueError(f"{gid}: invalid stage or language pairing")
        if group["criticality"] not in {"ordinary", "critical"}:
            raise ValueError(f"{gid}: invalid criticality")
        if group["stage"] == "contract_span":
            for language, variant in group["variants"].items():
                actual = contract_decision(variant, ids)
                if actual != group["gold"]:
                    raise ValueError(f"{gid}:{language}: contract oracle {actual} != gold {group['gold']}")
        else:
            gold = group["gold"]
            action = gold["action"]
            if action not in schema["stage_outputs"]["entity_linking"]["action"]:
                raise ValueError(f"{gid}: invalid entity action")
            for language, variant in group["variants"].items():
                span = variant["mention_span"]
                if not span or span not in variant["raw_query"]:
                    raise ValueError(f"{gid}:{language}: mention span is not exact")
            candidate_set = set(gold.get("candidate_ids", []))
            if candidate_set - ids:
                raise ValueError(f"{gid}: gold candidate absent from catalog")
            selected = gold.get("selected_id")
            if action == "linked":
                if selected and not (selected.startswith("ref:") or selected in ids):
                    raise ValueError(f"{gid}: selected entity absent from catalog")
                selected_many = set(gold.get("selected_ids", []))
                if not selected and not selected_many:
                    raise ValueError(f"{gid}: linked action requires selected entity")
                if selected_many - ids:
                    raise ValueError(f"{gid}: selected relation entity absent from catalog")
            elif selected is not None or gold.get("selected_ids"):
                raise ValueError(f"{gid}: unresolved action cannot select entity")
            if action == "ambiguous_in_catalog" and len(candidate_set) < 2:
                raise ValueError(f"{gid}: ambiguous case requires at least two candidates")
            if action in {"missing_entity", "non_entity_phrase", "mention_not_detected"} and candidate_set:
                raise ValueError(f"{gid}: NIL subtype cannot have gold candidates")


def allocation_snapshot(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        grouped[(group["stage"], group["stratum"])].append(group)
    return [
        {
            "stage": stage,
            "stratum": stratum,
            "semantic_groups": len(items),
            "rows": len(items) * 2,
            "critical_groups": sum(item["criticality"] == "critical" for item in items),
        }
        for (stage, stratum), items in sorted(grouped.items())
    ]


def build_outputs() -> dict[Path, str]:
    groups = read_jsonl(SOURCE_PATH)
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validate_group_sources(groups, catalog, schema)
    cases: list[dict[str, Any]] = []
    model_cases: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    for group in groups:
        for language in ("en", "pl"):
            case_id = f"{group['semantic_group_id']}-{language.upper()}"
            stage_input = {
                **group["variants"][language],
                "catalog_version": catalog["catalog_version"],
            }
            case = {
                "case_id": case_id,
                "semantic_group_id": group["semantic_group_id"],
                "stage": group["stage"],
                "language": language,
                "criticality": group["criticality"],
                "split": "stage-dev-v1",
                "input": stage_input,
                "gold": group["gold"],
                "provenance": {
                    "author_id": "Codex-same-process",
                    "authored_at": AUTHORED_AT,
                    "schema_or_catalog_version": catalog["catalog_version"],
                    "source_or_construction_basis": group["construction_basis"],
                    "review_status": "unreviewed",
                },
                "evaluation_metadata": {"stratum": group["stratum"], "paired_language_group": group["semantic_group_id"]},
            }
            cases.append(case)
            public = {"case_id": case_id, "stage": group["stage"], "language": language, "input": stage_input}
            model_cases.append(public)
            review_queue.append(
                {
                    **public,
                    "review_fields": {
                        "independent_label": None,
                        "confidence": None,
                        "rationale": None,
                        "disputed_field": None,
                        "disposition": None,
                    },
                }
            )
    cases_text = render_jsonl(cases)
    model_text = render_jsonl(model_cases)
    review_text = render_jsonl(review_queue)
    allocation = allocation_snapshot(groups)
    allocation_text = json.dumps(allocation, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    manifest = {
        "benchmark": "PMLAB-MAP-STAGE-001",
        "artifact": "stage-dev-v1-contract-entity-tranche",
        "status": "authored-unreviewed-development-data",
        "builder_version": BUILDER_VERSION,
        "annotation_contract_freeze_commit": "794c9e3",
        "semantic_group_count": len(groups),
        "case_count": len(cases),
        "stage_counts": dict(sorted(Counter(case["stage"] for case in cases).items())),
        "language_counts": dict(sorted(Counter(case["language"] for case in cases).items())),
        "critical_group_count": sum(group["criticality"] == "critical" for group in groups),
        "review_status": "not-reviewed",
        "hashes": {
            "contract-entity-groups-v1.jsonl": sha256_bytes(SOURCE_PATH.read_bytes()),
            "entity-catalog-v1.json": sha256_bytes(CATALOG_PATH.read_bytes()),
            "case-schema-v1.json": sha256_bytes(SCHEMA_PATH.read_bytes()),
            "case-allocation-v1.csv": sha256_bytes(ALLOCATION_PATH.read_bytes()),
            "cases.jsonl": sha256_bytes(cases_text.encode("utf-8")),
            "model-cases.jsonl": sha256_bytes(model_text.encode("utf-8")),
            "independent-review-queue.jsonl": sha256_bytes(review_text.encode("utf-8")),
            "allocation-snapshot.json": sha256_bytes(allocation_text.encode("utf-8")),
        },
        "leakage_checks": {
            "gold_absent_from_model_cases": True,
            "criticality_absent_from_model_cases": True,
            "split_and_stratum_absent_from_model_cases": True,
            "candidate_outputs_absent": True,
        },
        "blockers": ["independent label review not completed", "remaining four stage corpora not authored", "no candidate implementation may use future challenge rows"],
    }
    return {
        DATA_DIR / "cases.jsonl": cases_text,
        DATA_DIR / "model-cases.jsonl": model_text,
        DATA_DIR / "independent-review-queue.jsonl": review_text,
        DATA_DIR / "allocation-snapshot.json": allocation_text,
        DATA_DIR / "manifest.json": json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build_outputs()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, content in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        if stale:
            raise SystemExit("stale or missing artifacts: " + ", ".join(stale))
    else:
        for path, content in expected.items():
            path.write_text(content, encoding="utf-8", newline="\n")
    manifest = json.loads(expected[DATA_DIR / "manifest.json"])
    print(canonical_json({"groups": manifest["semantic_group_count"], "cases": manifest["case_count"], "status": manifest["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
