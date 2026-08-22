#!/usr/bin/env python3
"""Measure whether agreement between local lexical backends predicts safe retrieval."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts.run_memory_benchmark import (
        FTS5Retriever,
        RipgrepRetriever,
        load_jsonl,
        query_tokens,
        score_query,
        sha256_file,
        validate,
    )
except ModuleNotFoundError:  # Direct execution.
    from run_memory_benchmark import (
        FTS5Retriever,
        RipgrepRetriever,
        load_jsonl,
        query_tokens,
        score_query,
        sha256_file,
        validate,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "lab" / "pmlab-v0-dev"
DEFAULT_OUTPUT = ROOT / "data" / "lab" / "pmlab-backend-agreement-v0"
TOP_K = 5


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def jaccard(left: list[str], right: list[str]) -> float:
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 1.0


def lexical_coverage(query: str, retrieved: list[str], records: dict[str, dict[str, Any]]) -> float:
    tokens = query_tokens(query)
    if not tokens or not retrieved:
        return 0.0
    text = " ".join(
        f"{records[evidence_id]['title']} {records[evidence_id]['body']}".casefold()
        for evidence_id in retrieved
    )
    return sum(token in text for token in tokens) / len(tokens)


def safe_retrieval(query: dict[str, Any], retrieved: list[str]) -> bool:
    score = score_query(query, retrieved)
    if query["answerable"]:
        return score["recall_at_5"] == 1.0 and not score["forbidden_intrusion"]
    return bool(score["abstained_correctly"])


def strategy_metrics(queries: list[dict[str, Any]], retrieved_by_id: dict[str, list[str]]) -> dict[str, Any]:
    scored = []
    for query in queries:
        retrieved = retrieved_by_id[query["example_id"]]
        score = score_query(query, retrieved)
        scored.append((query, retrieved, score, safe_retrieval(query, retrieved)))
    accepted = [row for row in scored if row[1]]
    answerable = [row for row in scored if row[0]["answerable"]]
    unsafe_accepted = [row for row in accepted if not row[3]]
    return {
        "cases": len(scored),
        "answer_coverage": len(accepted) / len(scored),
        "selective_retrieval_risk": len(unsafe_accepted) / len(accepted) if accepted else 0.0,
        "safe_action_accuracy": sum(row[3] for row in scored) / len(scored),
        "macro_recall_at_5_answerable": statistics.mean(row[2]["recall_at_5"] for row in answerable),
        "forbidden_intrusion_rate": statistics.mean(row[2]["forbidden_intrusion"] for row in scored),
        "unanswerable_abstention_rate": statistics.mean(
            row[2]["abstained_correctly"] for row in scored if not row[0]["answerable"]
        ),
    }


def risk_coverage_curve(observations: list[dict[str, Any]], signal: str) -> dict[str, Any]:
    thresholds = sorted({row[signal] for row in observations}, reverse=True)
    points = []
    for threshold in thresholds:
        accepted = [
            row for row in observations if row["fts5_retrieved"] and row[signal] >= threshold
        ]
        if not accepted:
            continue
        points.append(
            {
                "threshold": threshold,
                "coverage": len(accepted) / len(observations),
                "risk": sum(not row["fts5_safe"] for row in accepted) / len(accepted),
                "accepted": len(accepted),
            }
        )
    ordered = sorted(points, key=lambda point: point["coverage"])
    area = 0.0
    previous_coverage = 0.0
    previous_risk = ordered[0]["risk"] if ordered else 0.0
    for point in ordered:
        area += (point["coverage"] - previous_coverage) * (previous_risk + point["risk"]) / 2
        previous_coverage = point["coverage"]
        previous_risk = point["risk"]
    return {"signal": signal, "descriptive_trapezoid_area": area, "points": ordered}


def agreement_gate(observations: list[dict[str, Any]], threshold: float) -> dict[str, list[str]]:
    return {
        row["example_id"]: (
            row["fts5_retrieved"]
            if row["backend_jaccard"] >= threshold and row["top1_agreement"]
            else []
        )
        for row in observations
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Local-backend agreement as a metamemory signal",
        "",
        "Status: post-hoc exploratory analysis on the existing PMLAB development corpus; not held out",
        "",
        "## Main result",
        "",
        f"Ripgrep and FTS5 both failed the same safe-retrieval criterion on {summary['joint_unsafe_cases']} of {summary['case_count']} cases. "
        f"Among the {summary['top1_agree_cases']} cases where their top result agreed, {summary['top1_agree_unsafe_cases']} were still unsafe. "
        "Backend agreement is therefore not independent evidence when both systems share lexical features and the same corpus.",
        "",
        "| Strategy | Answer coverage | Selective retrieval risk | Safe action accuracy | Recall@5 | Forbidden intrusion | Abstention |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("ripgrep", "fts5", "intersection", "union", "agreement_gate_0.8"):
        metric = summary["strategies"][name]
        lines.append(
            f"| {name} | {metric['answer_coverage']:.3f} | {metric['selective_retrieval_risk']:.3f} | "
            f"{metric['safe_action_accuracy']:.3f} | {metric['macro_recall_at_5_answerable']:.3f} | "
            f"{metric['forbidden_intrusion_rate']:.3f} | {metric['unanswerable_abstention_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The agreement gate accepts FTS5 only when top-1 IDs match and set Jaccard similarity is at least 0.8. It is a frozen descriptive rule, not an optimized policy.",
            "",
            "## Valid interpretation",
            "",
            "This analysis uses real local backend outputs, but the corpus is authored development data, labels were visible, and the analysis was designed after earlier benchmark results existed. It can falsify the idea that lexical-backend agreement is independent confirmation on this corpus; it cannot estimate deployment calibration or validate typed control.",
            "",
            "Next: add a genuinely different cue family (temporal/entity normalization or bilingual retrieval), freeze its outputs before labels are used for policy fitting, and obtain independent review of the acceptance criterion.",
            "",
        ]
    )
    return "\n".join(lines)


def run(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    corpus_path = source / "corpus.jsonl"
    queries_path = source / "queries.jsonl"
    corpus = load_jsonl(corpus_path)
    queries = load_jsonl(queries_path)
    validate(corpus, queries)
    records = {row["evidence_id"]: row for row in corpus}

    with tempfile.TemporaryDirectory(prefix="pmlab-backend-agreement-") as temporary:
        temp = Path(temporary)
        ripgrep = RipgrepRetriever(corpus, temp / "rg-docs")
        fts5 = FTS5Retriever(corpus, temp / "fts5.sqlite3")
        try:
            observations = []
            for query in queries:
                rg_ids = ripgrep.retrieve(query["query"], TOP_K)
                fts_ids = fts5.retrieve(query["query"], TOP_K)
                set_agreement = jaccard(rg_ids, fts_ids)
                top1 = bool(rg_ids and fts_ids and rg_ids[0] == fts_ids[0])
                cue = lexical_coverage(query["query"], fts_ids, records)
                observations.append(
                    {
                        "example_id": query["example_id"],
                        "category": query["category"],
                        "answerable": query["answerable"],
                        "ripgrep_retrieved": rg_ids,
                        "fts5_retrieved": fts_ids,
                        "ripgrep_safe": safe_retrieval(query, rg_ids),
                        "fts5_safe": safe_retrieval(query, fts_ids),
                        "backend_jaccard": set_agreement,
                        "top1_agreement": top1,
                        "lexical_cue_coverage": cue,
                        "combined_agreement": (set_agreement + float(top1) + cue) / 3,
                    }
                )
        finally:
            fts5.close()

    rg_map = {row["example_id"]: row["ripgrep_retrieved"] for row in observations}
    fts_map = {row["example_id"]: row["fts5_retrieved"] for row in observations}
    intersection = {
        row["example_id"]: [item for item in row["fts5_retrieved"] if item in row["ripgrep_retrieved"]]
        for row in observations
    }
    union = {
        row["example_id"]: list(dict.fromkeys(row["fts5_retrieved"] + row["ripgrep_retrieved"]))[:TOP_K]
        for row in observations
    }
    strategies = {
        "ripgrep": strategy_metrics(queries, rg_map),
        "fts5": strategy_metrics(queries, fts_map),
        "intersection": strategy_metrics(queries, intersection),
        "union": strategy_metrics(queries, union),
        "agreement_gate_0.8": strategy_metrics(queries, agreement_gate(observations, 0.8)),
    }
    top1_rows = [row for row in observations if row["top1_agreement"]]
    summary = {
        "experiment_id": "PMLAB-META-BACKEND-AGREE-001",
        "status": "completed-posthoc-exploratory",
        "case_count": len(queries),
        "joint_unsafe_cases": sum(not row["ripgrep_safe"] and not row["fts5_safe"] for row in observations),
        "top1_agree_cases": len(top1_rows),
        "top1_agree_unsafe_cases": sum(not row["fts5_safe"] for row in top1_rows),
        "strategies": strategies,
        "risk_coverage": {
            signal: risk_coverage_curve(observations, signal)
            for signal in ("backend_jaccard", "lexical_cue_coverage", "combined_agreement")
        },
        "interpretation_boundary": "post-hoc authored development analysis; no calibration or architecture claim",
    }
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "observations.jsonl", observations)
    write_json(output / "summary.json", summary)
    try:
        source_label = source.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        source_label = source.as_posix()
    write_json(
        output / "manifest.json",
        {
            "experiment_id": summary["experiment_id"],
            "source_dataset": source_label,
            "source_corpus_sha256": sha256_file(corpus_path),
            "source_queries_sha256": sha256_file(queries_path),
            "runner": "scripts/analyze_backend_agreement.py",
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "top_k": TOP_K,
            "network_or_model_calls": 0,
            "limitations": [
                "post-hoc analysis after prior benchmark inspection",
                "authored development corpus and visible labels",
                "both backends share lexical cues corpus and storage",
            ],
        },
    )
    (output / "report.md").write_text(render_report(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
