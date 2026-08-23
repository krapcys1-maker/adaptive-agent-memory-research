#!/usr/bin/env python3
"""Execute frozen PMLAB-PACK-002 over fixed candidates and byte budgets."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "lab" / "pmlab-pack-characterization-v0"
DEFAULT_OUTPUT = ROOT / "data" / "lab" / "pmlab-pack-characterization-v1" / "execution-v0"
FREEZE_COMMIT = "96c901fef3f4829ddbeac7e731bd2a526548d0a4"
BUDGETS = [512, 768, 1024, 1536]
FORMAT_ARMS = ["T0_TEXT_ONLY", "C0_FULL_INLINE", "C1_SOURCE_FOOTER"]
ORDER_ARMS = ["O0_RETRIEVAL", "O1_GOVERNED", "O2_REQUIRED_ORACLE"]
BUCKET_ORDER = {"current": 0, "supporting": 1, "stale_conflicting": 2}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locator(record: dict[str, Any]) -> str:
    return f"{record['source_path']}:{record['line_start']}-{record['line_end']}"


def validate_fixture(corpus: list[dict[str, Any]], cases: list[dict[str, Any]]) -> None:
    if len(corpus) != 36 or len(cases) != 24:
        raise ValueError("frozen fixture shape changed")
    records = {row["record_id"]: row for row in corpus}
    if len(records) != len(corpus):
        raise ValueError("duplicate record ID")
    for record in corpus:
        lines = (ROOT / record["source_path"]).read_text(encoding="utf-8").splitlines()
        resolved = "\n".join(lines[record["line_start"] - 1 : record["line_end"]])
        if resolved != record["text"]:
            raise ValueError(f"source mismatch for {record['record_id']}")
    for case in cases:
        if len(case["candidate_ids"]) != 7 or len(set(case["candidate_ids"])) != 7:
            raise ValueError(f"candidate shape changed for {case['case_id']}")
        if not set(case["required_ids"]) <= set(case["candidate_ids"]):
            raise ValueError(f"required item absent for {case['case_id']}")
        for record_id in case["required_ids"]:
            if records[record_id]["trust"] != "reviewed" or records[record_id]["bucket"] == "stale_conflicting":
                raise ValueError(f"unsafe required label for {case['case_id']}")


def order_ids(case: dict[str, Any], records: dict[str, dict[str, Any]], arm: str) -> list[str]:
    trusted = [record_id for record_id in case["candidate_ids"] if records[record_id]["trust"] == "reviewed"]
    original_rank = {record_id: rank for rank, record_id in enumerate(case["candidate_ids"])}
    required = set(case["required_ids"])
    if arm == "O0_RETRIEVAL":
        return trusted
    if arm == "O1_GOVERNED":
        return sorted(trusted, key=lambda record_id: (BUCKET_ORDER[records[record_id]["bucket"]], original_rank[record_id]))
    if arm == "O2_REQUIRED_ORACLE":
        return sorted(
            trusted,
            key=lambda record_id: (
                0 if record_id in required else (2 if records[record_id]["bucket"] == "stale_conflicting" else 1),
                original_rank[record_id],
            ),
        )
    raise ValueError(f"unknown order arm {arm}")


def serialize(format_arm: str, included: list[str], records: dict[str, dict[str, Any]]) -> tuple[str, dict[str, str]]:
    if not included:
        return "", {}
    if format_arm == "T0_TEXT_ONLY":
        lines = [f"<{records[record_id]['bucket']}> {records[record_id]['text']}" for record_id in included]
        return "\n".join(lines) + "\n", {}
    if format_arm == "C0_FULL_INLINE":
        lines = [
            f"[{locator(records[record_id])}] <{records[record_id]['bucket']}> {records[record_id]['text']}"
            for record_id in included
        ]
        return "\n".join(lines) + "\n", {}
    if format_arm == "C1_SOURCE_FOOTER":
        source_handles: dict[str, str] = {}
        for record_id in included:
            source_path = records[record_id]["source_path"]
            if source_path not in source_handles:
                source_handles[source_path] = f"S{len(source_handles) + 1:02d}"
        lines = [
            f"[{source_handles[records[record_id]['source_path']]}:L{records[record_id]['line_start']}-L{records[record_id]['line_end']}] "
            f"<{records[record_id]['bucket']}> {records[record_id]['text']}"
            for record_id in included
        ]
        lines.append("SOURCES")
        lines.extend(f"[{handle}]={source_path}" for source_path, handle in source_handles.items())
        return "\n".join(lines) + "\n", {handle: source_path for source_path, handle in source_handles.items()}
    raise ValueError(f"unknown format arm {format_arm}")


def build_pack(
    case: dict[str, Any],
    records: dict[str, dict[str, Any]],
    format_arm: str,
    order_arm: str,
    budget: int,
) -> dict[str, Any]:
    ordered = order_ids(case, records, order_arm)
    included: list[str] = []
    omitted = [
        {"record_id": record_id, "reason": "untrusted-pre-filter"}
        for record_id in case["candidate_ids"]
        if records[record_id]["trust"] != "reviewed"
    ]
    for record_id in ordered:
        candidate_text, _ = serialize(format_arm, included + [record_id], records)
        if len(candidate_text.encode("utf-8")) <= budget:
            included.append(record_id)
        else:
            omitted.append({"record_id": record_id, "reason": "byte-budget"})
    text, source_map = serialize(format_arm, included, records)
    required = set(case["required_ids"])
    critical = set(case["critical_required_ids"])
    required_retained = len(required & set(included)) / len(required)
    critical_retained = None if not critical else len(critical & set(included)) / len(critical)
    citation_errors: list[str] = []
    evidence_errors: list[str] = []
    stale_marker_errors: list[str] = []
    for record_id in included:
        record = records[record_id]
        if record["text"] not in text:
            evidence_errors.append(record_id)
        if record["bucket"] == "stale_conflicting" and "<stale_conflicting>" not in text:
            stale_marker_errors.append(record_id)
        if format_arm == "C0_FULL_INLINE" and f"[{locator(record)}]" not in text:
            citation_errors.append(record_id)
        if format_arm == "C1_SOURCE_FOOTER":
            matching = [handle for handle, source_path in source_map.items() if source_path == record["source_path"]]
            if len(matching) != 1:
                citation_errors.append(record_id)
            else:
                handle = matching[0]
                if f"[{handle}:L{record['line_start']}-L{record['line_end']}]" not in text:
                    citation_errors.append(record_id)
                if f"[{handle}]={record['source_path']}" not in text:
                    citation_errors.append(record_id)
    expected_omitted = set(case["candidate_ids"]) - set(included)
    reported_omitted = {row["record_id"] for row in omitted}
    untrusted_exposed = any(records[record_id]["trust"] != "reviewed" for record_id in included)
    return {
        "experiment_id": "PMLAB-PACK-002",
        "case_id": case["case_id"],
        "format_arm": format_arm,
        "order_arm": order_arm,
        "budget_utf8": budget,
        "included_ids": included,
        "omitted": omitted,
        "pack_text": text,
        "utf8_bytes": len(text.encode("utf-8")),
        "required_retention": required_retained,
        "all_required_retained": required_retained == 1.0,
        "critical_retention": critical_retained,
        "required_position": case["required_position"],
        "required_count": case["required_count"],
        "required_source_reuse": case["required_source_reuse"],
        "required_locator_class": case["required_locator_class"],
        "source_map": source_map,
        "citation_errors": sorted(set(citation_errors)),
        "evidence_errors": sorted(set(evidence_errors)),
        "stale_marker_errors": sorted(set(stale_marker_errors)),
        "untrusted_exposed": untrusted_exposed,
        "omission_ledger_complete": expected_omitted == reported_omitted,
        "budget_compliant": len(text.encode("utf-8")) <= budget,
    }


def mean(rows: list[dict[str, Any]], field: str) -> float:
    return statistics.mean(float(row[field]) for row in rows)


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for budget in BUDGETS:
        for format_arm in FORMAT_ARMS:
            for order_arm in ORDER_ARMS:
                selected = [
                    row for row in rows
                    if row["budget_utf8"] == budget and row["format_arm"] == format_arm and row["order_arm"] == order_arm
                ]
                critical_rows = [row for row in selected if row["critical_retention"] is not None]
                output.append(
                    {
                        "budget_utf8": budget,
                        "format_arm": format_arm,
                        "order_arm": order_arm,
                        "packs": len(selected),
                        "macro_required_retention": mean(selected, "required_retention"),
                        "all_required_rate": statistics.mean(row["all_required_retained"] for row in selected),
                        "critical_retention": mean(critical_rows, "critical_retention"),
                        "mean_included_records": statistics.mean(len(row["included_ids"]) for row in selected),
                        "mean_utf8_bytes": mean(selected, "utf8_bytes"),
                        "integrity_pass": all(
                            not row["citation_errors"]
                            and not row["evidence_errors"]
                            and not row["stale_marker_errors"]
                            and not row["untrusted_exposed"]
                            and row["omission_ledger_complete"]
                            and row["budget_compliant"]
                            for row in selected
                        ),
                    }
                )
    return output


def metric(rows: list[dict[str, Any]], format_arm: str, order_arm: str | None, budget: int, stratum=None) -> float:
    selected = [
        row for row in rows
        if row["format_arm"] == format_arm
        and row["budget_utf8"] == budget
        and (order_arm is None or row["order_arm"] == order_arm)
        and (stratum is None or stratum(row))
    ]
    return mean(selected, "required_retention")


def summarize(rows: list[dict[str, Any]], aggregates: list[dict[str, Any]]) -> dict[str, Any]:
    full_768 = metric(rows, "C0_FULL_INLINE", None, 768)
    compact_768 = metric(rows, "C1_SOURCE_FOOTER", None, 768)
    long_delta = metric(rows, "C1_SOURCE_FOOTER", None, 768, lambda row: row["required_locator_class"] == "long") - metric(
        rows, "C0_FULL_INLINE", None, 768, lambda row: row["required_locator_class"] == "long"
    )
    reuse_delta = metric(rows, "C1_SOURCE_FOOTER", None, 768, lambda row: row["required_source_reuse"]) - metric(
        rows, "C0_FULL_INLINE", None, 768, lambda row: row["required_source_reuse"]
    )
    order_differences = []
    for budget in BUDGETS:
        for format_arm in ("C0_FULL_INLINE", "C1_SOURCE_FOOTER"):
            difference = metric(rows, format_arm, "O1_GOVERNED", budget) - metric(rows, format_arm, "O0_RETRIEVAL", budget)
            order_differences.append({"budget_utf8": budget, "format_arm": format_arm, "governed_minus_retrieval": difference})
    integrity_pass = all(row["integrity_pass"] for row in aggregates)
    return {
        "experiment_id": "PMLAB-PACK-002",
        "status": "completed-synthetic-development-characterization",
        "architecture_selection_allowed": False,
        "packs": len(rows),
        "integrity_pass": integrity_pass,
        "primary_768": {
            "C0_FULL_INLINE_macro_required_retention": full_768,
            "C1_SOURCE_FOOTER_macro_required_retention": compact_768,
            "compact_minus_full": compact_768 - full_768,
        },
        "strata_768": {"long_locator_compact_minus_full": long_delta, "source_reuse_compact_minus_full": reuse_delta},
        "order_differences": order_differences,
        "hypotheses": {
            "H_PACK2_01": integrity_pass and compact_768 - full_768 >= 0.05,
            "H_PACK2_02": long_delta > 0 and reuse_delta > 0,
            "H_PACK2_03": any(abs(row["governed_minus_retrieval"]) >= 0.05 for row in order_differences),
        },
        "reader_stage_numeric_gate": integrity_pass and (
            abs(compact_768 - full_768) >= 0.05
            or sum(
                1
                for budget in BUDGETS
                if metric(rows, "C1_SOURCE_FOOTER", None, budget) - metric(rows, "C0_FULL_INLINE", None, budget) >= 0.05
            ) >= 2
        ),
        "authority": "visible authored serialization fixture; no reader or architecture claim",
    }


def report(summary: dict[str, Any], aggregates: list[dict[str, Any]]) -> str:
    lines = [
        "# Exact source-handle citation and pack-order run v1",
        "",
        "Status: completed synthetic development characterization",
        "",
        "## Primary comparison",
        "",
        "| Metric at 768 bytes | Value |",
        "|---|---:|",
        f"| Full inline required retention | {summary['primary_768']['C0_FULL_INLINE_macro_required_retention']:.3f} |",
        f"| Compact source-footer required retention | {summary['primary_768']['C1_SOURCE_FOOTER_macro_required_retention']:.3f} |",
        f"| Compact minus full | {summary['primary_768']['compact_minus_full']:+.3f} |",
        f"| Long-locator delta | {summary['strata_768']['long_locator_compact_minus_full']:+.3f} |",
        f"| Source-reuse delta | {summary['strata_768']['source_reuse_compact_minus_full']:+.3f} |",
        "",
        f"Integrity gates: `{'pass' if summary['integrity_pass'] else 'fail'}`. Reader-stage numeric gate: `{'pass' if summary['reader_stage_numeric_gate'] else 'fail'}`.",
        "",
        "## Registered hypotheses",
        "",
        *[f"- `{name}`: `{'pass' if value else 'fail'}`" for name, value in summary["hypotheses"].items()],
        "",
        "## Boundaries",
        "",
        "The fixture is authored and visible. The result measures serialization capacity only. It does not validate evidence truth, bucket inference, reader use, trust classification, compression models, or architecture selection.",
        "",
    ]
    return "\n".join(lines)


def run(output: Path) -> dict[str, Any]:
    corpus = load_jsonl(FIXTURE / "corpus.jsonl")
    cases = load_jsonl(FIXTURE / "cases.jsonl")
    validate_fixture(corpus, cases)
    records = {row["record_id"]: row for row in corpus}
    rows = [
        build_pack(case, records, format_arm, order_arm, budget)
        for case in cases
        for format_arm in FORMAT_ARMS
        for order_arm in ORDER_ARMS
        for budget in BUDGETS
    ]
    aggregates = aggregate(rows)
    summary = summarize(rows, aggregates)
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "packs.jsonl", rows)
    write_json(output / "aggregates.json", aggregates)
    write_json(output / "summary.json", summary)
    (output / "report.md").write_text(report(summary, aggregates), encoding="utf-8", newline="\n")
    execution_manifest = {
        "experiment_id": "PMLAB-PACK-002",
        "protocol_freeze_commit": FREEZE_COMMIT,
        "runner": "scripts/run_pack_characterization.py",
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": "Python standard library only",
        "input_hashes": {"corpus.jsonl": sha256(FIXTURE / "corpus.jsonl"), "cases.jsonl": sha256(FIXTURE / "cases.jsonl")},
        "output_hashes": {
            "packs.jsonl": sha256(output / "packs.jsonl"),
            "aggregates.json": sha256(output / "aggregates.json"),
            "summary.json": sha256(output / "summary.json"),
        },
        "packs": len(rows),
        "api_calls": 0,
        "api_cost_usd": 0,
    }
    write_json(output / "execution-manifest.json", execution_manifest)
    return {"summary": summary, "manifest": execution_manifest}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    result = run(output)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
