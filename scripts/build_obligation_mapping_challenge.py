#!/usr/bin/env python3
"""Build and validate the post-freeze PMLAB-MAP challenge corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_obligation_mapping_dev_corpus as base  # noqa: E402


BUILDER_VERSION = "pmlab-map-challenge-builder-v0"
DATA_DIR = ROOT / "data" / "lab" / "pmlab-obligation-mapping-challenge-v0"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate(schema: dict[str, Any], entities: dict[str, Any], groups: list[dict[str, Any]]) -> None:
    predicates = {item["id"] for item in schema["predicates"]}
    namespaces = {item["id"] for item in schema["namespaces"]}
    entity_ids = {item["id"] for item in entities["entities"]}
    seen: set[str] = set()
    construction_signatures = {
        item["compound_signature"]
        for item in base.read_jsonl(ROOT / "data" / "lab" / "pmlab-obligation-mapping-dev-v0" / "template-groups.jsonl")
    }
    for group in groups:
        gid = group["template_group"]
        if gid in seen or group["split"] != "post-freeze-challenge":
            raise ValueError(f"{gid}: duplicate group or invalid split")
        seen.add(gid)
        if set(group["queries"]) != {"en", "pl"}:
            raise ValueError(f"{gid}: paired en/pl variants are required")
        if group["compound_signature"] in construction_signatures:
            raise ValueError(f"{gid}: complete composition signature overlaps construction")
        previous: list[str] = []
        for node in group["nodes"]:
            if node["id"] != f"O{len(previous) + 1}" or node["op"] not in base.OPERATORS:
                raise ValueError(f"{gid}: invalid ordered node or operator")
            if any(dep not in previous for dep in node.get("depends", [])):
                raise ValueError(f"{gid}:{node['id']}: dependency must refer backward")
            previous.append(node["id"])
            if node["predicate"] is not None and node["predicate"] not in predicates:
                raise ValueError(f"{gid}:{node['id']}: unknown predicate")
            if set(node["namespaces"]) - namespaces:
                raise ValueError(f"{gid}:{node['id']}: unknown namespace")
            raw_entity = node["entity"]
            if not raw_entity.startswith(("ambiguous:", "nil:", "ref:", "refs:", "type:")):
                if set(raw_entity.split("|")) - entity_ids:
                    raise ValueError(f"{gid}:{node['id']}: unknown entity")
            for language in ("en", "pl"):
                if node["span"][language] not in group["queries"][language]:
                    raise ValueError(f"{gid}:{node['id']}:{language}: span missing")
        if group["supportedness"] == "unsupported" and group["nodes"]:
            raise ValueError(f"{gid}: unsupported query must have no graph")
        if group["supportedness"] in {"ambiguous", "nil", "unauthorized"}:
            if any(node["certificate"] in {"applicable", "explicit-negative", "requires-complete-scope"} for node in group["nodes"]):
                raise ValueError(f"{gid}: unsafe unresolved certificate")


def build() -> dict[Path, str]:
    schema_path = DATA_DIR / "schema-v0.json"
    entities_path = DATA_DIR / "entities-v0.json"
    groups_path = DATA_DIR / "template-groups.jsonl"
    schema = base.read_json(schema_path)
    entities = base.read_json(entities_path)
    groups = base.read_jsonl(groups_path)
    validate(schema, entities, groups)
    cases = []
    for group in groups:
        for language in ("en", "pl"):
            case = base.build_case(group, language)
            case["provenance"]["schema_version"] = schema["schema_version"]
            case["provenance"]["glossary_version"] = schema["schema_version"]
            case["provenance"]["entity_catalog_version"] = entities["catalog_version"]
            case["evaluation_metadata"]["schema_family"] = "pmlab-map-challenge"
            cases.append(case)
    model_cases = [
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
    cases_text = base.render_jsonl(cases)
    model_text = base.render_jsonl(model_cases)
    construction_schema = base.read_json(ROOT / "data" / "lab" / "pmlab-obligation-mapping-dev-v0" / "schema-v0.json")
    construction_entities = base.read_json(ROOT / "data" / "lab" / "pmlab-obligation-mapping-dev-v0" / "entities-v0.json")
    challenge_predicates = {item["id"] for item in schema["predicates"]}
    challenge_namespaces = {item["id"] for item in schema["namespaces"]}
    challenge_entities = {item["id"] for item in entities["entities"]}
    assert challenge_predicates.isdisjoint({item["id"] for item in construction_schema["predicates"]})
    assert challenge_namespaces.isdisjoint({item["id"] for item in construction_schema["namespaces"]})
    assert challenge_entities.isdisjoint({item["id"] for item in construction_entities["entities"]})
    manifest = {
        "benchmark": "PMLAB-MAP-001",
        "artifact": "post-freeze-challenge-v0",
        "status": "authored-post-arm-challenge-not-independently-reviewed",
        "builder_version": BUILDER_VERSION,
        "construction_corpus_freeze_commit": "4b6c47e",
        "deterministic_runner_freeze_commit": "6a82bd8",
        "optional_model_prompt_freeze_commit": "6a288f6",
        "optional_model_adapter_freeze_commit": "8913667",
        "template_group_count": len(groups),
        "case_count": len(cases),
        "language_counts": dict(sorted(Counter(case["language"] for case in cases).items())),
        "supportedness_counts": dict(sorted(Counter(group["supportedness"] for group in groups).items())),
        "max_graph_nodes": max(len(case["graph"]["nodes"]) for case in cases),
        "unseen_schema": {
            "predicate_count": len(challenge_predicates),
            "namespace_count": len(challenge_namespaces),
            "entity_count": len(challenge_entities),
            "all_ids_disjoint_from_construction": True,
        },
        "hashes": {
            "schema-v0.json": sha256_bytes(schema_path.read_bytes()),
            "entities-v0.json": sha256_bytes(entities_path.read_bytes()),
            "template-groups.jsonl": sha256_bytes(groups_path.read_bytes()),
            "cases.jsonl": sha256_bytes(cases_text.encode("utf-8")),
            "model-cases.jsonl": sha256_bytes(model_text.encode("utf-8")),
        },
        "known_blockers": ["labels authored by the same research process", "no independent review", "small synthetic corpus"],
    }
    return {
        DATA_DIR / "cases.jsonl": cases_text,
        DATA_DIR / "model-cases.jsonl": model_text,
        DATA_DIR / "manifest.json": json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, text in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
        if stale:
            raise SystemExit("stale or missing generated artifacts: " + ", ".join(stale))
    else:
        for path, content in expected.items():
            path.write_text(content, encoding="utf-8", newline="\n")
    manifest = json.loads(expected[DATA_DIR / "manifest.json"])
    print(base.canonical_json({"case_count": manifest["case_count"], "groups": manifest["template_group_count"], "status": "ok"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
