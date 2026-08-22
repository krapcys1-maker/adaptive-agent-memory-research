#!/usr/bin/env python3
"""Build and validate the bilingual PMLAB-MAP construction corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


BUILDER_VERSION = "pmlab-map-builder-v0"
REFERENCE_CLOCK = "2026-08-22T12:00:00+03:00"
REFERENCE_TIMEZONE = "Europe/Bucharest"
OPERATORS = {
    "SELECT",
    "FILTER",
    "PROJECT",
    "AGGREGATE",
    "GROUP",
    "SUPERLATIVE",
    "COMPARATIVE",
    "UNION",
    "INTERSECTION",
    "DIFFERENCE",
    "SORT",
    "BOOLEAN",
    "ARITHMETIC",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def entity_scope(raw: str) -> dict[str, Any]:
    if raw.startswith("ambiguous:"):
        return {
            "mention_basis": raw,
            "candidates": [{"id": item, "basis": "surface-collision"} for item in raw.removeprefix("ambiguous:").split(",")],
            "status": "ambiguous",
        }
    if raw.startswith("nil:"):
        return {"mention_basis": raw, "candidates": [], "status": "nil"}
    if raw.startswith("ref:") or raw.startswith("refs:"):
        return {"mention_basis": raw, "candidates": [], "status": "resolved-reference"}
    if raw.startswith("type:"):
        return {"mention_basis": raw, "candidates": [{"type": raw.removeprefix("type:"), "basis": "typed-variable"}], "status": "resolved"}
    return {
        "mention_basis": raw,
        "candidates": [{"id": item, "basis": "gold-catalog"} for item in raw.split("|")],
        "status": "resolved",
    }


def time_scope(raw: str) -> dict[str, Any]:
    if raw.startswith("ambiguous:"):
        status = "ambiguous"
    elif raw.startswith("recurrence:"):
        status = "unbounded"
    elif raw.startswith("inherit:"):
        status = "inherited"
    else:
        status = "resolved"
    return {
        "raw_normalization": raw,
        "reference_clock": REFERENCE_CLOCK,
        "timezone": REFERENCE_TIMEZONE,
        "status": status,
    }


def build_case(group: dict[str, Any], language: str) -> dict[str, Any]:
    query = group["queries"][language]
    nodes = []
    for source_node in group["nodes"]:
        span_text = source_node["span"][language]
        start = query.find(span_text)
        if start < 0:
            raise ValueError(f"{group['template_group']}:{language}:{source_node['id']}: span not in query: {span_text!r}")
        predicate = source_node["predicate"]
        authorization = source_node["authorization"]
        certificate = source_node["certificate"]
        node = {
            "obligation_id": source_node["id"],
            "operator": source_node["op"],
            "natural_spans": [{"start": start, "end": start + len(span_text), "text": span_text}],
            "arguments": source_node.get("depends", []),
            "criticality": group["criticality"],
            "scope": {
                "entity": entity_scope(source_node["entity"]),
                "predicate": {
                    "candidates": [] if predicate is None else [{"id": predicate, "basis": "gold-schema"}],
                    "status": "not-applicable" if predicate is None else "resolved",
                },
                "namespaces": {
                    "candidates": source_node["namespaces"],
                    "status": "not-applicable" if not source_node["namespaces"] else "resolved",
                },
                "valid_time": time_scope(source_node["time"]),
                "authorization": {"principal": "fixture-user", "status": authorization},
            },
            "certificate_query": {
                "status": certificate,
                "predicate": predicate,
                "entity_basis": source_node["entity"],
                "time_basis": source_node["time"],
                "namespaces": source_node["namespaces"],
            },
        }
        nodes.append(node)

    status_map = {
        "supported": "resolved",
        "ambiguous": "ambiguous",
        "nil": "ambiguous",
        "unauthorized": "unauthorized",
        "unsupported": "unsupported_structure",
    }
    return {
        "schema_version": "pmlab-obligation-ir-v0",
        "query_id": f"{group['template_group']}-{language.upper()}",
        "language": language,
        "raw_query": query,
        "reference_clock": {"instant": REFERENCE_CLOCK, "timezone": REFERENCE_TIMEZONE, "source": "case-fixture"},
        "graph": {"nodes": nodes, "edges": [{"from": dep, "to": node["obligation_id"], "label": "depends_on"} for node in nodes for dep in node["arguments"]]},
        "query_status": status_map[group["supportedness"]],
        "provenance": {
            "parser_version": "gold-v0",
            "schema_version": "pmlab-map-fixture-schema-v0",
            "glossary_version": "embedded-schema-v0",
            "entity_catalog_version": "pmlab-map-fixture-entities-v0",
        },
        "evaluation_metadata": {
            "split": group["split"],
            "semantic_template_group": group["template_group"],
            "bilingual_pair_group": group["template_group"],
            "paraphrase_group": group["template_group"],
            "criticality": group["criticality"],
            "supportedness": group["supportedness"],
            "atoms": group["atoms"],
            "composition_signature": group["compound_signature"],
            "strata": group["strata"],
            "schema_family": "pmlab-map-fixture",
        },
    }


def validate_sources(schema: dict[str, Any], entities: dict[str, Any], groups: list[dict[str, Any]]) -> None:
    predicates = {item["id"] for item in schema["predicates"]}
    namespaces = {item["id"] for item in schema["namespaces"]}
    entity_ids = {item["id"] for item in entities["entities"]}
    seen_groups: set[str] = set()
    covered_ops: set[str] = set()

    for group in groups:
        gid = group["template_group"]
        if gid in seen_groups:
            raise ValueError(f"duplicate template group: {gid}")
        seen_groups.add(gid)
        if group["split"] != "construction":
            raise ValueError(f"{gid}: source corpus may only contain construction rows")
        if set(group["queries"]) != {"en", "pl"}:
            raise ValueError(f"{gid}: exactly en/pl query variants are required")
        node_ids: list[str] = []
        for node in group["nodes"]:
            if node["op"] not in OPERATORS:
                raise ValueError(f"{gid}:{node['id']}: unknown operator {node['op']}")
            covered_ops.add(node["op"])
            if node["id"] in node_ids:
                raise ValueError(f"{gid}: duplicate node {node['id']}")
            for dep in node.get("depends", []):
                if dep not in node_ids:
                    raise ValueError(f"{gid}:{node['id']}: dependency {dep} must refer backward")
            node_ids.append(node["id"])
            if node["predicate"] is not None and node["predicate"] not in predicates:
                raise ValueError(f"{gid}:{node['id']}: unknown predicate {node['predicate']}")
            unknown_namespaces = set(node["namespaces"]) - namespaces
            if unknown_namespaces:
                raise ValueError(f"{gid}:{node['id']}: unknown namespaces {sorted(unknown_namespaces)}")
            raw_entity = node["entity"]
            if not raw_entity.startswith(("ambiguous:", "nil:", "ref:", "refs:", "type:")):
                unknown_entities = set(raw_entity.split("|")) - entity_ids
                if unknown_entities:
                    raise ValueError(f"{gid}:{node['id']}: unknown entities {sorted(unknown_entities)}")
            for language in ("en", "pl"):
                if node["span"][language] not in group["queries"][language]:
                    raise ValueError(f"{gid}:{node['id']}:{language}: span missing from query")

        if group["supportedness"] == "unsupported" and group["nodes"]:
            raise ValueError(f"{gid}: unsupported structure must not contain a coerced graph")
        if group["supportedness"] in {"ambiguous", "nil", "unauthorized"}:
            forbidden = {"applicable", "explicit-negative", "requires-complete-scope"}
            if any(node["certificate"] in forbidden for node in group["nodes"]):
                raise ValueError(f"{gid}: unresolved/unauthorized group contains an applicable certificate")

    missing_ops = OPERATORS - covered_ops
    if missing_ops:
        raise ValueError(f"operator coverage missing: {sorted(missing_ops)}")


def validate_equivalence_fixtures(fixtures: list[dict[str, Any]]) -> None:
    counts = Counter(item["class"] for item in fixtures)
    required = {
        "different-structure-same-denotation": 2,
        "same-structure-different-denotation": 2,
    }
    if counts != required:
        raise ValueError(f"equivalence fixture counts must be {required}, got {dict(counts)}")
    ids = [item["fixture_id"] for item in fixtures]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate equivalence fixture id")
    for item in fixtures:
        if not item.get("purpose"):
            raise ValueError(f"{item['fixture_id']}: purpose is required")
        if item["class"] == "different-structure-same-denotation":
            if item["graph_a"] == item["graph_b"] or "fixture_denotation" not in item:
                raise ValueError(f"{item['fixture_id']}: distinct graphs and one denotation are required")
        else:
            if item["grounding_a"] == item["grounding_b"] or item["fixture_denotation_a"] == item["fixture_denotation_b"]:
                raise ValueError(f"{item['fixture_id']}: distinct grounding and denotation are required")


def render_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(row) + "\n" for row in rows)


def build(root: Path) -> tuple[str, str, str]:
    data_dir = root / "data" / "lab" / "pmlab-obligation-mapping-dev-v0"
    schema_path = data_dir / "schema-v0.json"
    entities_path = data_dir / "entities-v0.json"
    groups_path = data_dir / "template-groups.jsonl"
    equivalence_path = data_dir / "equivalence-fixtures.jsonl"
    schema = read_json(schema_path)
    entities = read_json(entities_path)
    groups = read_jsonl(groups_path)
    equivalence_fixtures = read_jsonl(equivalence_path)
    validate_sources(schema, entities, groups)
    validate_equivalence_fixtures(equivalence_fixtures)

    cases = [build_case(group, language) for group in groups for language in ("en", "pl")]
    case_text = render_jsonl(cases)
    model_rows = [
        {
            "query_id": case["query_id"],
            "language": case["language"],
            "raw_query": case["raw_query"],
            "reference_clock": case["reference_clock"],
            "schema_version": case["provenance"]["schema_version"],
            "entity_catalog_version": case["provenance"]["entity_catalog_version"],
        }
        for case in cases
    ]
    model_text = render_jsonl(model_rows)
    operator_counts = Counter(node["operator"] for case in cases for node in case["graph"]["nodes"])
    manifest = {
        "benchmark": "PMLAB-MAP-001",
        "artifact": "construction-dev-v0",
        "status": "authored-construction-not-held-out",
        "builder_version": BUILDER_VERSION,
        "reference_clock": REFERENCE_CLOCK,
        "template_group_count": len(groups),
        "case_count": len(cases),
        "equivalence_fixture_count": len(equivalence_fixtures),
        "equivalence_fixture_counts": dict(sorted(Counter(item["class"] for item in equivalence_fixtures).items())),
        "language_counts": dict(sorted(Counter(case["language"] for case in cases).items())),
        "supportedness_counts": dict(sorted(Counter(group["supportedness"] for group in groups).items())),
        "operator_counts": dict(sorted(operator_counts.items())),
        "hashes": {
            "schema-v0.json": sha256_bytes(schema_path.read_bytes()),
            "entities-v0.json": sha256_bytes(entities_path.read_bytes()),
            "template-groups.jsonl": sha256_bytes(groups_path.read_bytes()),
            "equivalence-fixtures.jsonl": sha256_bytes(equivalence_path.read_bytes()),
            "cases.jsonl": sha256_bytes(case_text.encode("utf-8")),
            "model-cases.jsonl": sha256_bytes(model_text.encode("utf-8")),
        },
        "known_blockers": [
            "not independently reviewed",
            "no held-out challenge",
        ],
    }
    return case_text, model_text, json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify generated artifacts without writing")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "lab" / "pmlab-obligation-mapping-dev-v0"
    expected = {
        data_dir / "cases.jsonl": build(root)[0],
        data_dir / "model-cases.jsonl": build(root)[1],
        data_dir / "manifest.json": build(root)[2],
    }
    if args.check:
        stale = [str(path.relative_to(root)) for path, text in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
        if stale:
            raise SystemExit("stale or missing generated artifacts: " + ", ".join(stale))
    else:
        for path, text in expected.items():
            path.write_text(text, encoding="utf-8", newline="\n")
    manifest = json.loads(expected[data_dir / "manifest.json"])
    print(canonical_json({"case_count": manifest["case_count"], "operator_counts": manifest["operator_counts"], "status": "ok"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
