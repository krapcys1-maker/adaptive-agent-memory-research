#!/usr/bin/env python3
"""Localize first and co-occurring PMLAB-MAP challenge failures by stage."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE = ROOT / "data" / "lab" / "pmlab-obligation-mapping-challenge-v0"
OUTPUT_DIR = CHALLENGE / "stage-failure-analysis-v0"
ANALYZER_VERSION = "pmlab-map-stage-failure-analysis-v0"


def load_scorer():
    path = ROOT / "scripts" / "run_obligation_mapping_construction.py"
    spec = importlib.util.spec_from_file_location("map_scorer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def classify(row: dict[str, Any], contract_invalid: bool) -> tuple[str, list[str]]:
    failures: list[str] = []
    if contract_invalid:
        failures.append("contract")
    if not row["status_exact"]:
        failures.append("status")
    if row["obligation_recall"] < 1.0 or not row["structure_exact"]:
        failures.append("graph")
    denominator = row["link_denominator"]
    if denominator:
        links = row["link_correct"]
        if links.get("entity", 0) < denominator:
            failures.append("entity")
        if links.get("predicate", 0) < denominator:
            failures.append("predicate")
        if links.get("namespaces", 0) < denominator:
            failures.append("namespace")
        if links.get("time", 0) < denominator:
            failures.append("time")
        if links.get("authorization", 0) < denominator:
            failures.append("authorization")
        if links.get("certificate", 0) < denominator:
            failures.append("certificate")
    if row["false_closure"]:
        failures.append("false-closure")
    ordered = [
        "contract", "status", "graph", "entity", "predicate", "namespace",
        "time", "authorization", "certificate", "false-closure",
    ]
    unique = [stage for stage in ordered if stage in failures]
    return (unique[0] if unique else "pass"), unique


def build_outputs() -> dict[Path, str]:
    scorer = load_scorer()
    cases = {item["query_id"]: item for item in read_jsonl(CHALLENGE / "cases.jsonl")}
    deterministic_rows = [
        item for item in read_jsonl(CHALLENGE / "deterministic-artifacts" / "results.jsonl")
        if item["arm"] == "qdmr_rules_pipeline"
    ]
    model_dir = ROOT / "data" / "lab" / "pmlab-obligation-mapping-deepseek-challenge-v0"
    model_rows = read_jsonl(model_dir / "scored-results.jsonl")
    model_errors = {item["query_id"] for item in read_jsonl(model_dir / "errors.jsonl") if item.get("query_id")}
    rows = []
    for arm, source_rows in (("qdmr_rules_pipeline", deterministic_rows), ("deepseek_v4_flash", model_rows)):
        for row in source_rows:
            qid = row["query_id"]
            first, failures = classify(row, arm == "deepseek_v4_flash" and qid in model_errors)
            rows.append(
                {
                    "query_id": qid,
                    "language": cases[qid]["language"],
                    "semantic_group": cases[qid]["evaluation_metadata"]["semantic_template_group"],
                    "critical": row["critical"],
                    "arm": arm,
                    "first_failure": first,
                    "failure_stages": failures,
                    "false_closure": row["false_closure"],
                    "end_to_end_exact": row["end_to_end_exact"],
                }
            )
    summaries = {}
    for arm in ("qdmr_rules_pipeline", "deepseek_v4_flash"):
        items = [row for row in rows if row["arm"] == arm]
        first = Counter(row["first_failure"] for row in items)
        any_stage = Counter(stage for row in items for stage in row["failure_stages"])
        summaries[arm] = {
            "case_count": len(items),
            "first_failure_counts": dict(first),
            "any_failure_counts": dict(any_stage),
            "cases_with_multiple_failure_stages": sum(len(row["failure_stages"]) > 1 for row in items),
            "critical_failures": sum(row["critical"] and not row["end_to_end_exact"] for row in items),
            "false_closure_count": sum(row["false_closure"] for row in items),
        }
    rows_text = "".join(canonical_json(row) + "\n" for row in rows)
    summary_text = json.dumps(summaries, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    report = [
        "# PMLAB-MAP challenge stage-failure localization",
        "",
        "Status: post-hoc diagnostic on a spent post-freeze challenge; not a new benchmark result",
        "",
        "Stages are ordered as contract, query status, graph, entity, predicate, namespace, time, authorization, certificate, and false closure. `first_failure` is descriptive, not causal: most failed cases contain multiple errors.",
        "",
        "| Arm | First contract | First status | First graph | First entity | Pass | Multi-stage | Critical failures | False closure |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm, item in summaries.items():
        counts = item["first_failure_counts"]
        report.append(
            f"| `{arm}` | {counts.get('contract', 0)} | {counts.get('status', 0)} | {counts.get('graph', 0)} | "
            f"{counts.get('entity', 0)} | {counts.get('pass', 0)} | {item['cases_with_multiple_failure_stages']} | "
            f"{item['critical_failures']} | {item['false_closure_count']} |"
        )
    report.extend(
        [
            "",
            "A single end-to-end score cannot identify the repair. Contract, unresolved-status, graph, and grounding errors co-occur. The next experiment must use stage-specific inputs and oracle isolation rather than tune an integrated parser on these 28 cases.",
            "",
        ]
    )
    report_text = "\n".join(report)
    manifest = {
        "analysis": "PMLAB-MAP-stage-failure-localization",
        "status": "post-hoc-spent-challenge-diagnostic",
        "analyzer_version": ANALYZER_VERSION,
        "challenge_freeze_commit": "adc540f",
        "challenge_result_commit": "6bcb8ab",
        "case_arm_rows": len(rows),
        "hashes": {
            "rows.jsonl": hashlib.sha256(rows_text.encode("utf-8")).hexdigest(),
            "summary.json": hashlib.sha256(summary_text.encode("utf-8")).hexdigest(),
            "report.md": hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        },
        "limitations": ["post-hoc", "first failure is not causal", "same-process challenge labels"],
    }
    return {
        OUTPUT_DIR / "rows.jsonl": rows_text,
        OUTPUT_DIR / "summary.json": summary_text,
        OUTPUT_DIR / "report.md": report_text,
        OUTPUT_DIR / "manifest.json": json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
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
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for path, content in expected.items():
            path.write_text(content, encoding="utf-8", newline="\n")
    print(canonical_json(json.loads(expected[OUTPUT_DIR / "summary.json"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
