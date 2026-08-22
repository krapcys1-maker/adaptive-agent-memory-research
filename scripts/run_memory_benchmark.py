#!/usr/bin/env python3
"""Run the PMLAB development retrieval comparison (B0, ripgrep, SQLite FTS5)."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sqlite3
import statistics
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


TOKEN_RE = re.compile(r"[^\W_]+(?:-[^\W_]+)*", re.UNICODE)
STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "because", "did", "do", "does",
    "for", "from", "had", "has", "how", "in", "inside", "is", "it", "of",
    "on", "or", "that", "the", "this", "to", "was", "were", "what", "when",
    "where", "which", "who", "why", "with", "bez", "do", "gdzie", "i", "jak",
    "jest", "na", "się", "w", "z",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def query_tokens(text: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for token in TOKEN_RE.findall(text.casefold()):
        if len(token) < 3 or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1)
    return ordered[max(index, 0)]


class NoMemory:
    name = "B0-no-memory"

    def retrieve(self, query: str, top_k: int) -> list[str]:
        del query, top_k
        return []


class RipgrepRetriever:
    name = "B1-ripgrep"

    def __init__(self, records: list[dict[str, Any]], docs_dir: Path) -> None:
        executable = shutil.which("rg")
        if not executable:
            raise RuntimeError("B1 requires ripgrep (`rg`) on PATH")
        self.executable = executable
        self.record_count = len(records)
        self.docs_dir = docs_dir
        docs_dir.mkdir(parents=True, exist_ok=True)
        expected = set()
        for record in records:
            evidence_id = record["evidence_id"]
            expected.add(f"{evidence_id}.txt")
            text = f"{record['title']}\n{record['body']}\n"
            (docs_dir / f"{evidence_id}.txt").write_text(text, encoding="utf-8")
        for path in docs_dir.glob("*.txt"):
            if path.name not in expected:
                path.unlink()

    def retrieve(self, query: str, top_k: int) -> list[str]:
        scores: dict[str, float] = defaultdict(float)
        for token in query_tokens(query):
            completed = subprocess.run(
                [self.executable, "--json", "--ignore-case", "--fixed-strings", "--", token, str(self.docs_dir)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            matches: set[str] = set()
            for line in completed.stdout.splitlines():
                event = json.loads(line)
                if event.get("type") != "match":
                    continue
                matches.add(Path(event["data"]["path"]["text"]).stem)
            if matches:
                weight = math.log((self.record_count + 1) / (len(matches) + 1)) + 1
                for evidence_id in matches:
                    scores[evidence_id] += weight
        return [item[0] for item in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]]


class FTS5Retriever:
    name = "B2-sqlite-fts5"

    def __init__(self, records: list[dict[str, Any]], database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        if database_path.exists():
            database_path.unlink()
        self.connection = sqlite3.connect(database_path)
        try:
            self.connection.execute(
                "CREATE VIRTUAL TABLE memory_fts USING fts5(evidence_id UNINDEXED, title, body, tokenize='unicode61')"
            )
        except sqlite3.OperationalError as exc:
            raise RuntimeError("This Python SQLite build does not include FTS5") from exc
        self.connection.executemany(
            "INSERT INTO memory_fts(evidence_id, title, body) VALUES (?, ?, ?)",
            [(row["evidence_id"], row["title"], row["body"]) for row in records],
        )
        self.connection.commit()

    def retrieve(self, query: str, top_k: int) -> list[str]:
        tokens = query_tokens(query)
        if not tokens:
            return []
        match_query = " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens)
        rows = self.connection.execute(
            "SELECT evidence_id, bm25(memory_fts) AS score FROM memory_fts "
            "WHERE memory_fts MATCH ? ORDER BY score, evidence_id LIMIT ?",
            (match_query, top_k),
        ).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        self.connection.close()


def score_query(query: dict[str, Any], retrieved: list[str]) -> dict[str, Any]:
    gold = query["gold_evidence_ids"]
    forbidden = set(query["forbidden_stale_ids"])
    positions = {evidence_id: index + 1 for index, evidence_id in enumerate(retrieved)}
    if query["answerable"]:
        recall = sum(1 for evidence_id in gold if evidence_id in positions) / len(gold)
        ranks = [positions[evidence_id] for evidence_id in gold if evidence_id in positions]
        reciprocal_rank = 1 / min(ranks) if ranks else 0.0
        abstained_correctly = None
    else:
        recall = None
        reciprocal_rank = None
        abstained_correctly = not retrieved
    return {
        "recall_at_5": recall,
        "reciprocal_rank": reciprocal_rank,
        "forbidden_intrusion": bool(forbidden.intersection(retrieved)),
        "abstained_correctly": abstained_correctly,
    }


def run_backend(
    backend: Any,
    queries: list[dict[str, Any]],
    top_k: int,
    clock: Callable[[], float] = time.perf_counter,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results = []
    latencies = []
    for query in queries:
        started = clock()
        retrieved = backend.retrieve(query["query"], top_k)
        latency_ms = (clock() - started) * 1000
        latencies.append(latency_ms)
        row = {
            "backend": backend.name,
            "example_id": query["example_id"],
            "category": query["category"],
            "retrieved": retrieved,
            "latency_ms": round(latency_ms, 6),
        }
        row.update(score_query(query, retrieved))
        results.append(row)

    answerable = [row for row in results if row["recall_at_5"] is not None]
    unanswerable = [row for row in results if row["abstained_correctly"] is not None]
    categories: dict[str, list[float]] = defaultdict(list)
    for row in answerable:
        categories[row["category"]].append(row["recall_at_5"])
    summary = {
        "backend": backend.name,
        "queries": len(results),
        "answerable_queries": len(answerable),
        "macro_recall_at_5_answerable": statistics.mean(row["recall_at_5"] for row in answerable),
        "mean_reciprocal_rank": statistics.mean(row["reciprocal_rank"] for row in answerable),
        "forbidden_intrusion_rate": statistics.mean(row["forbidden_intrusion"] for row in results),
        "unanswerable_abstention_rate": statistics.mean(row["abstained_correctly"] for row in unanswerable),
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "recall_by_category": {name: statistics.mean(values) for name, values in sorted(categories.items())},
    }
    return results, summary


def validate(records: list[dict[str, Any]], queries: list[dict[str, Any]]) -> None:
    evidence_ids = [row["evidence_id"] for row in records]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Duplicate evidence_id in corpus")
    known = set(evidence_ids)
    example_ids = [row["example_id"] for row in queries]
    if len(example_ids) != len(set(example_ids)):
        raise ValueError("Duplicate example_id in queries")
    for query in queries:
        gold = set(query["gold_evidence_ids"])
        forbidden = set(query["forbidden_stale_ids"])
        if not gold.issubset(known) or not forbidden.issubset(known):
            raise ValueError(f"Unknown evidence id in {query['example_id']}")
        if query["answerable"] != bool(gold):
            raise ValueError(f"answerable/gold mismatch in {query['example_id']}")
        if gold.intersection(forbidden):
            raise ValueError(f"Gold evidence is also forbidden in {query['example_id']}")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("data/lab/pmlab-v0-dev"))
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.top_k != 5:
        raise SystemExit("This development comparison is frozen at top-k=5")

    corpus_path = args.dataset / "corpus.jsonl"
    queries_path = args.dataset / "queries.jsonl"
    records = load_jsonl(corpus_path)
    queries = load_jsonl(queries_path)
    validate(records, queries)

    artifacts = args.dataset / "artifacts"
    manifest = {
        "status": "instrument-development-only",
        "corpus_records": len(records),
        "queries": len(queries),
        "top_k": args.top_k,
        "corpus_sha256": sha256_file(corpus_path),
        "queries_sha256": sha256_file(queries_path),
        "tokenization": "Unicode words length >=3; frozen English/Polish stopword list; no expansion or synonyms",
        "backends": ["B0-no-memory", "B1-ripgrep", "B2-sqlite-fts5"],
        "limitations": "Authored development slice; not independently annotated; not held out; no architecture claims",
    }
    write_json(artifacts / "manifest.json", manifest)

    backends = [
        NoMemory(),
        RipgrepRetriever(records, artifacts / "rg-docs"),
        FTS5Retriever(records, artifacts / "fts5.sqlite"),
    ]
    all_results = []
    summaries = []
    try:
        for backend in backends:
            results, summary = run_backend(backend, queries, args.top_k)
            all_results.extend(results)
            summaries.append(summary)
    finally:
        for backend in backends:
            close = getattr(backend, "close", None)
            if close:
                close()

    with (artifacts / "results.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in all_results:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    write_json(artifacts / "summary.json", {"manifest": manifest, "results": summaries})
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
