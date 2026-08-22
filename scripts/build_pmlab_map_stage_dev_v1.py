#!/usr/bin/env python3
"""Build and validate authored PMLAB-MAP stage-dev-v1 corpus tranches."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import copy
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1"
BUILDER_VERSION = "pmlab-map-stage-dev-builder-v2"
SOURCE_PATHS = [
    DATA_DIR / "contract-entity-groups-v1.jsonl",
    DATA_DIR / "graph-predicate-groups-v1.jsonl",
    DATA_DIR / "time-certificate-groups-v1.jsonl",
    DATA_DIR / "supplemental-coverage-groups-v1.jsonl",
]
CATALOG_PATH = DATA_DIR / "entity-catalog-v1.json"
PREDICATE_CATALOG_PATH = DATA_DIR / "predicate-catalog-v1.json"
SCHEMA_PATH = DATA_DIR / "case-schema-v1.json"
ALLOCATION_PATH = DATA_DIR / "case-allocation-v1.csv"
AMENDMENT_PATH = DATA_DIR / "case-schema-amendment-v1.json"
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


def validate_graph_group(group: dict[str, Any], schema: dict[str, Any]) -> None:
    gid = group["semantic_group_id"]
    gold = group["gold"]
    if gold.get("query_status") not in schema["stage_outputs"]["obligation_graph"]["query_status"]:
        raise ValueError(f"{gid}: invalid graph status")
    nodes = gold.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError(f"{gid}: graph nodes must be an array")
    if gold["query_status"] in {"unsupported_structure", "ambiguous"} and nodes:
        raise ValueError(f"{gid}: unresolved graph fixture must not force nodes")
    if gold["query_status"] == "resolved" and not nodes:
        raise ValueError(f"{gid}: resolved graph requires nodes")
    previous: list[str] = []
    for index, node in enumerate(nodes, start=1):
        if set(node) != {"obligation_id", "operator", "source_span", "depends"}:
            raise ValueError(f"{gid}: graph node fields differ from contract")
        if node["obligation_id"] != f"O{index}" or any(dep not in previous for dep in node["depends"]):
            raise ValueError(f"{gid}: graph IDs or dependencies are invalid")
        if node["operator"] not in ALLOWED_OPERATORS:
            raise ValueError(f"{gid}: invalid graph operator")
        if set(node["source_span"]) != {"en", "pl"}:
            raise ValueError(f"{gid}: graph source span must be bilingual")
        for language, variant in group["variants"].items():
            span = node["source_span"][language]
            if not span or span not in variant["raw_query"]:
                raise ValueError(f"{gid}:{language}: graph span is not exact: {span}")
        previous.append(node["obligation_id"])


def validate_predicate_group(group: dict[str, Any], predicate_catalog: dict[str, Any], schema: dict[str, Any]) -> None:
    gid = group["semantic_group_id"]
    ids = {item["id"] for item in predicate_catalog["predicates"]}
    namespaces = set(predicate_catalog["namespaces"])
    gold = group["gold"]
    action = gold.get("action")
    if action not in schema["stage_outputs"]["predicate_linking"]["action"]:
        raise ValueError(f"{gid}: invalid predicate action")
    ranked = gold.get("ranked_predicates")
    selected = gold.get("selected_predicate")
    selected_namespaces = gold.get("selected_namespaces")
    if not isinstance(ranked, list) or set(ranked) - ids:
        raise ValueError(f"{gid}: unknown predicate candidate")
    if not isinstance(selected_namespaces, list) or set(selected_namespaces) - namespaces:
        raise ValueError(f"{gid}: unknown namespace")
    for language, variant in group["variants"].items():
        if not variant.get("span") or variant["span"] not in variant["raw_query"]:
            raise ValueError(f"{gid}:{language}: predicate span is not exact")
    if action == "linked":
        if selected not in ids or selected not in ranked or not selected_namespaces:
            raise ValueError(f"{gid}: linked predicate requires selected candidate and namespace")
    elif selected is not None:
        raise ValueError(f"{gid}: unresolved predicate cannot select top1")
    if action == "ambiguous_schema" and len(ranked) < 2:
        raise ValueError(f"{gid}: schema ambiguity requires at least two candidates")
    if action == "unsupported_predicate" and (ranked or selected_namespaces):
        raise ValueError(f"{gid}: unsupported predicate cannot invent candidates or namespaces")


def validate_time_authorization_group(group: dict[str, Any], schema: dict[str, Any]) -> None:
    gid = group["semantic_group_id"]
    fixture = group.get("fixture", {})
    gold = group["gold"]
    contract = schema["stage_outputs"]["time_authorization"]
    if gold.get("time_status") not in contract["time_status"]:
        raise ValueError(f"{gid}: invalid time status")
    if gold.get("authorization_status") not in contract["authorization_status"]:
        raise ValueError(f"{gid}: invalid authorization status")
    if set(gold.get("raw_span", {})) != {"en", "pl"}:
        raise ValueError(f"{gid}: bilingual time span missing")
    for language, variant in group["variants"].items():
        if variant.get("raw_span") != gold["raw_span"][language] or variant["raw_span"] not in variant["raw_query"]:
            raise ValueError(f"{gid}:{language}: time span is not exact or differs from gold")
    for field in ("reference_clock", "timezone", "principal"):
        if not fixture.get(field) or fixture[field] != gold.get(field):
            raise ValueError(f"{gid}: {field} is missing or differs between input and gold")
    if not isinstance(gold.get("normalized_time"), str) or not gold["normalized_time"]:
        raise ValueError(f"{gid}: normalized time must be explicit")
    authorized = gold.get("authorized_namespaces")
    denied = gold.get("denied_namespaces")
    if not isinstance(authorized, list) or not isinstance(denied, list) or set(authorized) & set(denied):
        raise ValueError(f"{gid}: authorization namespace partition is invalid")
    authorization = gold["authorization_status"]
    if authorization == "denied" and (authorized or not denied):
        raise ValueError(f"{gid}: denied scope must expose nothing and name denied scope")
    if authorization == "partial" and (not authorized or not denied):
        raise ValueError(f"{gid}: partial scope requires allowed and denied namespaces")
    if authorization == "allowed" and denied:
        raise ValueError(f"{gid}: allowed scope cannot contain denied namespaces")
    if gold["time_status"] == "ambiguous" and not gold["normalized_time"].startswith("ambiguous:"):
        raise ValueError(f"{gid}: ambiguous time must remain typed")
    if gold["time_status"] == "unbounded" and not gold["normalized_time"].startswith("unbounded:"):
        raise ValueError(f"{gid}: unbounded time must remain typed")
    if gold["time_status"] == "unsupported" and not gold["normalized_time"].startswith("unsupported:"):
        raise ValueError(f"{gid}: unsupported time must remain typed")
    if gold["time_status"] == "inherited":
        if not fixture.get("parent_scopes") or gold["authorization_status"] != "inherited":
            raise ValueError(f"{gid}: inherited time requires parent scopes and inherited authorization")


def validate_certificate_group(group: dict[str, Any], schema: dict[str, Any]) -> None:
    gid = group["semantic_group_id"]
    fixture = group.get("fixture", {})
    gold = group["gold"]
    contract = schema["stage_outputs"]["certificate_routing"]
    if gold.get("certificate_status") not in contract["certificate_status"]:
        raise ValueError(f"{gid}: invalid certificate status")
    if gold.get("action") not in contract["action"] or not gold.get("basis"):
        raise ValueError(f"{gid}: invalid certificate action or missing basis")
    for language, variant in group["variants"].items():
        if not variant.get("proposition_span") or variant["proposition_span"] not in variant["raw_query"]:
            raise ValueError(f"{gid}:{language}: proposition span is not exact")
    collection = fixture.get("collection", {})
    insertion = fixture.get("insertion", {})
    status = gold["certificate_status"]
    if status == "explicit_negative" and fixture.get("evidence_state") != "explicit_negative_record":
        raise ValueError(f"{gid}: explicit negative requires proposition-level evidence")
    if status == "requires_complete_scope":
        if not (collection.get("fresh") and collection.get("complete") and collection.get("scope_match")):
            raise ValueError(f"{gid}: collection absence requires fresh exact completeness")
        if insertion.get("present") and insertion.get("matches_scope"):
            raise ValueError(f"{gid}: matching insertion invalidates collection absence")
    if insertion.get("present") and insertion.get("matches_scope") and status != "inapplicable":
        raise ValueError(f"{gid}: insertion counterexample must invalidate certificate")
    if fixture.get("mapping_status") != "resolved" and status not in {"ambiguous", "inapplicable"}:
        raise ValueError(f"{gid}: unresolved mapping cannot receive a conclusive certificate")
    safe_answer = {"applicable", "derived", "explicit_negative", "requires_complete_scope"}
    if gold["action"] == "answer" and status not in safe_answer:
        raise ValueError(f"{gid}: unsafe answer action")
    if status == "ambiguous" and gold["action"] != "clarify":
        raise ValueError(f"{gid}: ambiguous certificate requires clarification")


def validate_group_sources(
    groups: list[dict[str, Any]],
    catalog: dict[str, Any],
    predicate_catalog: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    ids = catalog_ids(catalog)
    seen: set[str] = set()
    counts = Counter((group["stage"], group["stratum"]) for group in groups)
    expected = {
        ("contract_span", "valid_nested_contract"): 2,
        ("contract_span", "wrong_valid_contract"): 2,
        ("contract_span", "invalid_serialization_or_fields"): 2,
        ("contract_span", "dependency_and_id_integrity"): 2,
        ("obligation_graph", "atomic_and_coordination"): 3,
        ("obligation_graph", "coreference_and_projection"): 3,
        ("obligation_graph", "set_and_numeric_composition"): 4,
        ("obligation_graph", "unsupported_and_ambiguous_structure"): 3,
        ("obligation_graph", "denotation_structure_dissociation"): 3,
        ("entity_linking", "exact_alias_and_paraphrase"): 3,
        ("entity_linking", "in_catalog_collision"): 3,
        ("entity_linking", "missing_entity"): 3,
        ("entity_linking", "non_entity_phrase"): 3,
        ("entity_linking", "coreference_and_multi_entity"): 2,
        ("predicate_linking", "exact_alias_and_description"): 3,
        ("predicate_linking", "synonym_and_name_mismatch"): 3,
        ("predicate_linking", "near_neighbor_ambiguity"): 3,
        ("predicate_linking", "implicit_schema_context"): 3,
        ("predicate_linking", "unsupported_predicate"): 2,
        ("time_authorization", "absolute_relative_and_event_anchor"): 3,
        ("time_authorization", "recurrence_unbounded_and_ambiguous"): 3,
        ("time_authorization", "allowed_denied_partial"): 2,
        ("time_authorization", "inherited_multi_parent_scope"): 2,
        ("certificate_routing", "applicable_and_derived"): 2,
        ("certificate_routing", "explicit_negative_vs_absence"): 3,
        ("certificate_routing", "stale_incomplete_or_wrong_scope"): 3,
        ("certificate_routing", "insertion_counterexample"): 2,
        ("contract_span", "supplemental_declared_label_coverage"): 1,
        ("entity_linking", "supplemental_declared_label_coverage"): 1,
        ("time_authorization", "supplemental_declared_label_coverage"): 1,
        ("certificate_routing", "supplemental_declared_label_coverage"): 2,
    }
    if counts != expected:
        raise ValueError(f"source allocation mismatch: {dict(counts)}")
    expected_critical = {
        ("contract_span", "valid_nested_contract"): 1,
        ("contract_span", "wrong_valid_contract"): 2,
        ("contract_span", "invalid_serialization_or_fields"): 1,
        ("contract_span", "dependency_and_id_integrity"): 2,
        ("obligation_graph", "atomic_and_coordination"): 1,
        ("obligation_graph", "coreference_and_projection"): 3,
        ("obligation_graph", "set_and_numeric_composition"): 3,
        ("obligation_graph", "unsupported_and_ambiguous_structure"): 3,
        ("obligation_graph", "denotation_structure_dissociation"): 1,
        ("entity_linking", "exact_alias_and_paraphrase"): 1,
        ("entity_linking", "in_catalog_collision"): 3,
        ("entity_linking", "missing_entity"): 3,
        ("entity_linking", "non_entity_phrase"): 2,
        ("entity_linking", "coreference_and_multi_entity"): 2,
        ("predicate_linking", "exact_alias_and_description"): 1,
        ("predicate_linking", "synonym_and_name_mismatch"): 2,
        ("predicate_linking", "near_neighbor_ambiguity"): 3,
        ("predicate_linking", "implicit_schema_context"): 2,
        ("predicate_linking", "unsupported_predicate"): 2,
        ("time_authorization", "absolute_relative_and_event_anchor"): 2,
        ("time_authorization", "recurrence_unbounded_and_ambiguous"): 3,
        ("time_authorization", "allowed_denied_partial"): 2,
        ("time_authorization", "inherited_multi_parent_scope"): 2,
        ("certificate_routing", "applicable_and_derived"): 1,
        ("certificate_routing", "explicit_negative_vs_absence"): 3,
        ("certificate_routing", "stale_incomplete_or_wrong_scope"): 3,
        ("certificate_routing", "insertion_counterexample"): 2,
        ("contract_span", "supplemental_declared_label_coverage"): 1,
        ("entity_linking", "supplemental_declared_label_coverage"): 1,
        ("time_authorization", "supplemental_declared_label_coverage"): 1,
        ("certificate_routing", "supplemental_declared_label_coverage"): 2,
    }
    actual_critical = Counter(
        (group["stage"], group["stratum"])
        for group in groups
        if group["criticality"] == "critical"
    )
    if actual_critical != expected_critical:
        raise ValueError(f"critical allocation mismatch: {dict(actual_critical)}")
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
        elif group["stage"] == "entity_linking":
            gold = group["gold"]
            action = gold["action"]
            if action not in schema["stage_outputs"]["entity_linking"]["action"]:
                raise ValueError(f"{gid}: invalid entity action")
            for language, variant in group["variants"].items():
                span = variant["mention_span"]
                if action == "mention_not_detected":
                    if span is not None:
                        raise ValueError(f"{gid}:{language}: missing-mention control must use null span")
                elif not span or span not in variant["raw_query"]:
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
        elif group["stage"] == "obligation_graph":
            validate_graph_group(group, schema)
        elif group["stage"] == "predicate_linking":
            validate_predicate_group(group, predicate_catalog, schema)
        elif group["stage"] == "time_authorization":
            validate_time_authorization_group(group, schema)
        elif group["stage"] == "certificate_routing":
            validate_certificate_group(group, schema)
        else:
            raise ValueError(f"{gid}: source validator not implemented for {group['stage']}")


def gold_for_language(group: dict[str, Any], language: str) -> dict[str, Any]:
    gold = copy.deepcopy(group["gold"])
    if group["stage"] == "obligation_graph":
        for node in gold["nodes"]:
            node["source_span"] = node["source_span"][language]
    elif group["stage"] == "time_authorization":
        gold["raw_span"] = gold["raw_span"][language]
    return gold


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


def declared_label_coverage(cases: list[dict[str, Any]], schema: dict[str, Any]) -> dict[str, Any]:
    declarations = {
        "contract_span.decision": schema["stage_outputs"]["contract_span"]["decision"],
        "contract_span.reject_reason": schema["stage_outputs"]["contract_span"]["reject_reason"],
        "obligation_graph.query_status": schema["stage_outputs"]["obligation_graph"]["query_status"],
        "entity_linking.action": schema["stage_outputs"]["entity_linking"]["action"],
        "predicate_linking.action": schema["stage_outputs"]["predicate_linking"]["action"],
        "time_authorization.time_status": schema["stage_outputs"]["time_authorization"]["time_status"],
        "time_authorization.authorization_status": schema["stage_outputs"]["time_authorization"]["authorization_status"],
        "certificate_routing.certificate_status": schema["stage_outputs"]["certificate_routing"]["certificate_status"],
        "certificate_routing.action": schema["stage_outputs"]["certificate_routing"]["action"],
    }
    result = {}
    for key, declared in declarations.items():
        stage, field = key.split(".", 1)
        observed = sorted({case["gold"].get(field) for case in cases if case["stage"] == stage and case["gold"].get(field) is not None})
        result[key] = {
            "declared": declared,
            "observed": observed,
            "uncovered": sorted(set(declared) - set(observed)),
        }
    return result


def build_outputs() -> dict[Path, str]:
    groups = [group for path in SOURCE_PATHS for group in read_jsonl(path)]
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    predicate_catalog = json.loads(PREDICATE_CATALOG_PATH.read_text(encoding="utf-8"))
    amendment = json.loads(AMENDMENT_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validate_group_sources(groups, catalog, predicate_catalog, schema)
    cases: list[dict[str, Any]] = []
    model_cases: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    for group in groups:
        for language in ("en", "pl"):
            case_id = f"{group['semantic_group_id']}-{language.upper()}"
            stage_input = {**group["variants"][language], **copy.deepcopy(group.get("fixture", {}))}
            if group["stage"] in {"contract_span", "entity_linking"}:
                stage_input["catalog_version"] = catalog["catalog_version"]
            elif group["stage"] == "predicate_linking":
                stage_input["schema_version"] = predicate_catalog["schema_version"]
            elif group["stage"] == "obligation_graph":
                stage_input["graph_contract_version"] = schema["schema_version"]
            elif group["stage"] in {"time_authorization", "certificate_routing"}:
                stage_input["stage_contract_version"] = schema["schema_version"]
            case = {
                "case_id": case_id,
                "semantic_group_id": group["semantic_group_id"],
                "stage": group["stage"],
                "language": language,
                "criticality": group["criticality"],
                "split": "stage-dev-v1",
                "input": stage_input,
                "gold": gold_for_language(group, language),
                "provenance": {
                    "author_id": "Codex-same-process",
                    "authored_at": AUTHORED_AT,
                    "schema_or_catalog_version": (
                        predicate_catalog["schema_version"]
                        if group["stage"] == "predicate_linking"
                        else schema["schema_version"]
                        if group["stage"] == "obligation_graph"
                        else schema["schema_version"]
                        if group["stage"] in {"time_authorization", "certificate_routing"}
                        else catalog["catalog_version"]
                    ),
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
    coverage = declared_label_coverage(cases, schema)
    non_exercisable = amendment["non_exercisable_under_isolated_stage_input"]
    unresolved_coverage = {
        key: value["uncovered"]
        for key, value in coverage.items()
        if value["uncovered"]
        and any(f"{key}={label}" not in non_exercisable for label in value["uncovered"])
    }
    manifest = {
        "benchmark": "PMLAB-MAP-STAGE-001",
        "artifact": "stage-dev-v1-complete-six-stage-corpus",
        "status": "authored-unreviewed-development-data",
        "builder_version": BUILDER_VERSION,
        "annotation_contract_freeze_commit": "794c9e3",
        "semantic_group_count": len(groups),
        "base_allocation_semantic_group_count": 72,
        "supplemental_coverage_semantic_group_count": amendment["supplemental_development_groups"],
        "case_count": len(cases),
        "stage_counts": dict(sorted(Counter(case["stage"] for case in cases).items())),
        "language_counts": dict(sorted(Counter(case["language"] for case in cases).items())),
        "critical_group_count": sum(group["criticality"] == "critical" for group in groups),
        "review_status": "not-reviewed",
        "declared_label_coverage": coverage,
        "uncovered_declared_labels": {
            key: value["uncovered"] for key, value in coverage.items() if value["uncovered"]
        },
        "non_exercisable_declared_labels": non_exercisable,
        "unresolved_coverage_gaps": unresolved_coverage,
        "hashes": {
            **{path.name: sha256_bytes(path.read_bytes()) for path in SOURCE_PATHS},
            "entity-catalog-v1.json": sha256_bytes(CATALOG_PATH.read_bytes()),
            "predicate-catalog-v1.json": sha256_bytes(PREDICATE_CATALOG_PATH.read_bytes()),
            "case-schema-v1.json": sha256_bytes(SCHEMA_PATH.read_bytes()),
            "case-allocation-v1.csv": sha256_bytes(ALLOCATION_PATH.read_bytes()),
            "case-schema-amendment-v1.json": sha256_bytes(AMENDMENT_PATH.read_bytes()),
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
        "blockers": ["independent label review not completed", "advisory review of the complete corpus not completed", "no candidate implementation may use future challenge rows"],
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
