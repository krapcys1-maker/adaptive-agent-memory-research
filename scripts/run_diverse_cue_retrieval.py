#!/usr/bin/env python3
"""Run the frozen diverse-cue development protocol on PMLAB v0."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

try:
    from scripts.run_memory_benchmark import (
        FTS5Retriever,
        load_jsonl,
        score_query,
        sha256_file,
        validate,
    )
except ModuleNotFoundError:
    from run_memory_benchmark import FTS5Retriever, load_jsonl, score_query, sha256_file, validate


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "lab" / "pmlab-v0-dev"
DEFAULT_OUTPUT = ROOT / "data" / "lab" / "pmlab-diverse-cues-v0"
TOP_K = 5
CANDIDATE_K = 10

# Frozen, authored development glossary. Phrase components are deliberately
# explicit so the transformation remains inspectable and provider-neutral.
GLOSSARY_PAIRS = (
    ("awaryjny", "emergency"),
    ("pakiet", "package"),
    ("wycofania", "rollback"),
    ("wdrożenia", "deployment"),
    ("backup", "kopii zapasowej"),
    ("encryption", "szyfrowania"),
    ("key", "klucz"),
    ("stored", "zapisano"),
    ("where", "gdzie"),
    ("located", "znajduje się"),
)
ARMS = {
    "raw": (False, False, False),
    "time": (True, False, False),
    "trust": (False, True, False),
    "bilingual": (False, False, True),
    "time_trust": (True, True, False),
    "time_trust_bilingual": (True, True, True),
}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def expand_bilingual(query: str) -> str:
    folded = query.casefold()
    additions: list[str] = []
    for left, right in GLOSSARY_PAIRS:
        if left.casefold() in folded:
            additions.append(right)
        if right.casefold() in folded:
            additions.append(left)
    return " ".join([query, *dict.fromkeys(additions)])


def valid_on(record: dict[str, Any], query_time: str) -> bool:
    query_date = date.fromisoformat(query_time[:10])
    valid_from = date.fromisoformat(record["valid_from"])
    valid_to = date.fromisoformat(record["valid_to"]) if record["valid_to"] else None
    return valid_from <= query_date and (valid_to is None or query_date <= valid_to)


def filter_candidates(
    retrieved: list[str],
    records: dict[str, dict[str, Any]],
    query_time: str,
    *,
    use_time: bool,
    use_trust: bool,
) -> list[str]:
    kept = []
    for evidence_id in retrieved:
        record = records[evidence_id]
        if use_time and not valid_on(record, query_time):
            continue
        if use_trust and record["trust"] == "untrusted":
            continue
        kept.append(evidence_id)
    return kept[:TOP_K]


def retrieve_arm(
    backend: FTS5Retriever,
    query: dict[str, Any],
    records: dict[str, dict[str, Any]],
    arm: str,
) -> tuple[str, list[str]]:
    use_time, use_trust, use_bilingual = ARMS[arm]
    transformed = expand_bilingual(query["query"]) if use_bilingual else query["query"]
    depth = CANDIDATE_K if use_time or use_trust else TOP_K
    retrieved = backend.retrieve(transformed, depth)
    if use_time or use_trust:
        retrieved = filter_candidates(
            retrieved,
            records,
            query["query_time"],
            use_time=use_time,
            use_trust=use_trust,
        )
    return transformed, retrieved


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    arms = {}
    for arm in ARMS:
        selected = [row for row in rows if row["arm"] == arm]
        answerable = [row for row in selected if row["answerable"]]
        unanswerable = [row for row in selected if not row["answerable"]]
        accepted = [row for row in selected if row["retrieved"]]
        unsafe_accepted = [row for row in accepted if not row["safe_action"]]
        cross_language = [row for row in answerable if row["category"] == "cross_language"]
        arms[arm] = {
            "cases": len(selected),
            "answer_coverage": len(accepted) / len(selected),
            "selective_retrieval_risk": len(unsafe_accepted) / len(accepted) if accepted else 0.0,
            "safe_action_accuracy": statistics.mean(row["safe_action"] for row in selected),
            "macro_recall_at_5_answerable": statistics.mean(row["recall_at_5"] for row in answerable),
            "forbidden_intrusion_rate": statistics.mean(row["forbidden_intrusion"] for row in selected),
            "unanswerable_abstention_rate": statistics.mean(row["abstained_correctly"] for row in unanswerable),
            "cross_language_recall_at_5": statistics.mean(row["recall_at_5"] for row in cross_language),
            "candidate_depth": CANDIDATE_K if ARMS[arm][0] or ARMS[arm][1] else TOP_K,
            "fts_calls_per_query": 1,
        }
    raw = arms["raw"]
    full = arms["time_trust_bilingual"]
    gates = {
        "safe_action_gain_at_least_15_points": full["safe_action_accuracy"] - raw["safe_action_accuracy"] >= 0.15,
        "forbidden_intrusion_at_most_0.05": full["forbidden_intrusion_rate"] <= 0.05,
        "cross_language_gain_at_least_0.50": full["cross_language_recall_at_5"] - raw["cross_language_recall_at_5"] >= 0.50,
        "unanswerable_abstention_at_least_0.50": full["unanswerable_abstention_rate"] >= 0.50,
    }
    return {
        "experiment_id": "PMLAB-META-DIVERSE-CUE-001",
        "status": "completed-development-after-freeze",
        "arms": arms,
        "candidate_gates": gates,
        "all_candidate_gates_pass": all(gates.values()),
        "interpretation_boundary": "authored inspected development corpus and tailored glossary; not confirmatory",
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Diverse-cue retrieval development run v0",
        "",
        "Status: protocol and runner frozen before execution; source corpus was previously inspected and is not held out",
        "",
        "| Arm | Safe action | Selective risk | Recall@5 | Forbidden | Abstention | Cross-language recall | Depth |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        metric = summary["arms"][arm]
        lines.append(
            f"| {arm} | {metric['safe_action_accuracy']:.3f} | {metric['selective_retrieval_risk']:.3f} | "
            f"{metric['macro_recall_at_5_answerable']:.3f} | {metric['forbidden_intrusion_rate']:.3f} | "
            f"{metric['unanswerable_abstention_rate']:.3f} | {metric['cross_language_recall_at_5']:.3f} | "
            f"{metric['candidate_depth']} |"
        )
    lines.extend(["", "## Frozen candidate gates", ""])
    for gate, passed in summary["candidate_gates"].items():
        lines.append(f"- `{gate}`: {'PASS' if passed else 'FAIL'}")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            summary["interpretation_boundary"],
            "A failed abstention gate means the bundle is not a complete metamemory controller even if validity, trust, and bilingual retrieval improve.",
            "",
        ]
    )
    return "\n".join(lines)


def git_freeze_commit() -> str:
    completed = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", "scripts/run_diverse_cue_retrieval.py", "docs/11-research-laboratory/diverse-cue-retrieval-protocol-v0.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def run(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    corpus_path = source / "corpus.jsonl"
    queries_path = source / "queries.jsonl"
    corpus = load_jsonl(corpus_path)
    queries = load_jsonl(queries_path)
    validate(corpus, queries)
    records = {row["evidence_id"]: row for row in corpus}

    rows = []
    with tempfile.TemporaryDirectory(prefix="pmlab-diverse-cues-") as temporary:
        backend = FTS5Retriever(corpus, Path(temporary) / "fts5.sqlite3")
        try:
            for arm in ARMS:
                for query in queries:
                    transformed, retrieved = retrieve_arm(backend, query, records, arm)
                    score = score_query(query, retrieved)
                    safe = (
                        score["recall_at_5"] == 1.0 and not score["forbidden_intrusion"]
                        if query["answerable"]
                        else bool(score["abstained_correctly"])
                    )
                    rows.append(
                        {
                            "arm": arm,
                            "example_id": query["example_id"],
                            "category": query["category"],
                            "answerable": query["answerable"],
                            "transformed_query": transformed,
                            "retrieved": retrieved,
                            "safe_action": safe,
                            **score,
                        }
                    )
        finally:
            backend.close()

    summary = summarize(rows)
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "results.jsonl", rows)
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "experiment_id": summary["experiment_id"],
            "protocol": "docs/11-research-laboratory/diverse-cue-retrieval-protocol-v0.md",
            "freeze_commit": git_freeze_commit(),
            "source_dataset": "data/lab/pmlab-v0-dev",
            "source_corpus_sha256": sha256_file(corpus_path),
            "source_queries_sha256": sha256_file(queries_path),
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "arms": list(ARMS),
            "top_k": TOP_K,
            "candidate_k": CANDIDATE_K,
            "network_or_model_calls": 0,
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
