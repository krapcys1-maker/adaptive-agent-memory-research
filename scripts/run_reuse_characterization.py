#!/usr/bin/env python3
"""Run PMLAB-REUSE-CHAR-001 without promoting an architecture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import sqlite3
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "lab" / "pmlab-reuse-characterization-v0"
DEFAULT_OUTPUT = SOURCE / "execution-v0"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "faf4aa4225822f3bc6376869cb1164e8e3feedd0"
TOP_K = 5
CANDIDATE_DEPTH = 10
RRF_K = 60
PACK_BUDGET = 768
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
BUCKETS = ("current", "supporting", "stale_conflicting")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def directory_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def validate_inputs(
    corpus: list[dict[str, Any]], queries: list[dict[str, Any]], evidence_path: Path
) -> dict[str, Any]:
    if len(corpus) != 36 or len(queries) != 20:
        raise ValueError("frozen fixture must contain 36 records and 20 queries")
    record_ids = [row["record_id"] for row in corpus]
    query_ids = [row["query_id"] for row in queries]
    if len(set(record_ids)) != len(record_ids) or len(set(query_ids)) != len(query_ids):
        raise ValueError("record and query IDs must be unique")
    known = set(record_ids)
    lines = evidence_path.read_text(encoding="utf-8").splitlines()
    citation_hashes: dict[str, str] = {}
    for row in corpus:
        if row["context_bucket"] not in BUCKETS or row["trust"] not in {"reviewed", "untrusted"}:
            raise ValueError(f"invalid pack metadata: {row['record_id']}")
        if row["source_path"] != evidence_path.relative_to(ROOT).as_posix():
            raise ValueError(f"unexpected source path: {row['record_id']}")
        start, end = row["line_start"], row["line_end"]
        if start < 1 or end < start or end > len(lines):
            raise ValueError(f"citation outside source: {row['record_id']}")
        cited = "\n".join(lines[start - 1 : end])
        if cited != row["search_text"]:
            raise ValueError(f"citation text mismatch: {row['record_id']}")
        citation_hashes[row["record_id"]] = sha256_bytes(cited.encode("utf-8"))
    for query in queries:
        required = set(query["required_ids"])
        forbidden = set(query["forbidden_ids"])
        if not required <= known or not forbidden <= known or required & forbidden:
            raise ValueError(f"invalid labels: {query['query_id']}")
        if query["answerable"] != bool(required):
            raise ValueError(f"answerability/required mismatch: {query['query_id']}")
    return {"citation_hashes": citation_hashes, "evidence_lines": len(lines)}


def query_terms(query: str) -> list[str]:
    return list(dict.fromkeys(token.casefold() for token in TOKEN_RE.findall(query) if len(token) > 1))


class FTS5Retriever:
    name = "B2_FTS5"

    def __init__(self, corpus: list[dict[str, Any]], database: Path) -> None:
        self.database = database
        self.connection = sqlite3.connect(database)
        self.connection.execute(
            "CREATE VIRTUAL TABLE docs USING fts5(record_id UNINDEXED, search_text, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        self.connection.executemany(
            "INSERT INTO docs(record_id, search_text) VALUES (?, ?)",
            [(row["record_id"], row["search_text"]) for row in corpus],
        )
        self.connection.commit()

    def retrieve(self, query: str, limit: int) -> list[str]:
        terms = query_terms(query)
        if not terms:
            return []
        expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
        rows = self.connection.execute(
            "SELECT record_id, bm25(docs) AS score FROM docs WHERE docs MATCH ? "
            "ORDER BY score ASC, record_id ASC LIMIT ?",
            (expression, limit),
        ).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        self.connection.close()


class FastEmbedRetriever:
    name = "C0_FASTEMBED"

    def __init__(self, corpus: list[dict[str, Any]], cache_dir: Path) -> None:
        import numpy as np
        from fastembed import TextEmbedding

        self.np = np
        started = time.perf_counter()
        self.model = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(cache_dir), threads=4)
        self.model_load_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        vectors = list(self.model.embed([row["search_text"] for row in corpus], batch_size=16))
        matrix = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self.matrix = matrix / np.maximum(norms, np.finfo(np.float32).eps)
        self.record_ids = [row["record_id"] for row in corpus]
        self.embedding_ms = (time.perf_counter() - started) * 1000
        self.vector_bytes = int(self.matrix.nbytes)

    def retrieve(self, query: str, limit: int) -> list[str]:
        vector = self.np.asarray(next(self.model.query_embed(query)), dtype=self.np.float32)
        norm = self.np.linalg.norm(vector)
        if norm:
            vector = vector / norm
        scores = self.matrix @ vector
        ordered = sorted(
            range(len(self.record_ids)), key=lambda index: (-float(scores[index]), self.record_ids[index])
        )
        return [self.record_ids[index] for index in ordered[:limit]]


def rrf(rankings: list[list[str]], limit: int, k: int = RRF_K) -> list[str]:
    scores: defaultdict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, record_id in enumerate(ranking, 1):
            scores[record_id] += 1.0 / (k + rank)
    return [record_id for record_id, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def citation(row: dict[str, Any]) -> str:
    return f"{row['source_path']}:{row['line_start']}-{row['line_end']}"


def append_under_budget(lines: list[str], text: str, budget: int) -> bool:
    candidate = "\n".join([*lines, text])
    if len(candidate.encode("utf-8")) > budget:
        return False
    lines.append(text)
    return True


def build_pack(
    mode: str,
    ranked: list[str],
    records: dict[str, dict[str, Any]],
    budget: int = PACK_BUDGET,
) -> dict[str, Any]:
    lines: list[str] = []
    included: list[str] = []
    omitted: list[dict[str, str]] = []
    placements: dict[str, str] = {}
    if mode in {"raw", "cited"}:
        for record_id in ranked:
            row = records[record_id]
            item = row["search_text"] if mode == "raw" else f"{row['search_text']} [{citation(row)}]"
            if append_under_budget(lines, item, budget):
                included.append(record_id)
            else:
                omitted.append({"record_id": record_id, "reason": "utf8_byte_budget"})
    elif mode == "bucketed":
        for bucket in BUCKETS:
            header = {"current": "## Current", "supporting": "## Supporting", "stale_conflicting": "## Stale/conflicting"}[bucket]
            bucket_ids = [record_id for record_id in ranked if records[record_id]["context_bucket"] == bucket]
            bucket_lines: list[tuple[str, str]] = []
            for record_id in bucket_ids:
                row = records[record_id]
                if row["trust"] == "untrusted":
                    omitted.append({"record_id": record_id, "reason": "untrusted"})
                    continue
                bucket_lines.append((record_id, f"- {row['search_text']} [{citation(row)}]"))
            if not bucket_lines:
                continue
            header_added = False
            for record_id, item in bucket_lines:
                additions = [header, item] if not header_added else [item]
                candidate = "\n".join([*lines, *additions])
                if len(candidate.encode("utf-8")) <= budget:
                    lines.extend(additions)
                    header_added = True
                    included.append(record_id)
                    placements[record_id] = bucket
                else:
                    omitted.append({"record_id": record_id, "reason": "utf8_byte_budget"})
    else:
        raise ValueError(f"unknown pack mode: {mode}")
    text = "\n".join(lines)
    return {
        "mode": mode,
        "text": text,
        "included": included,
        "omitted": omitted,
        "placements": placements,
        "utf8_bytes": len(text.encode("utf-8")),
        "budget": budget,
    }


def score_retrieval(query: dict[str, Any], ranked: list[str]) -> dict[str, Any]:
    required = set(query["required_ids"])
    forbidden = set(query["forbidden_ids"])
    at_five = ranked[:TOP_K]
    ranks = [rank for rank, record_id in enumerate(at_five, 1) if record_id in required]
    return {
        "recall_at_5": len(required & set(at_five)) / len(required) if required else None,
        "all_required_at_5": required <= set(at_five) if required else None,
        "mrr_at_5": 1.0 / min(ranks) if ranks else (0.0 if required else None),
        "forbidden_intrusion_at_5": bool(forbidden & set(at_five)),
        "candidate_null": not at_five if not required else None,
    }


def summarize_retrieval(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for arm in sorted({row["arm"] for row in rows}):
        selected = [row for row in rows if row["arm"] == arm]
        answerable = [row for row in selected if row["answerable"]]
        unanswerable = [row for row in selected if not row["answerable"]]
        category_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in answerable:
            category_rows[row["category"]].append(row)
        output[arm] = {
            "queries": len(selected),
            "macro_recall_at_5": statistics.mean(row["recall_at_5"] for row in answerable),
            "all_required_at_5": statistics.mean(row["all_required_at_5"] for row in answerable),
            "mrr_at_5": statistics.mean(row["mrr_at_5"] for row in answerable),
            "forbidden_intrusion_rate_at_5": statistics.mean(row["forbidden_intrusion_at_5"] for row in selected),
            "unanswerable_candidate_null": statistics.mean(row["candidate_null"] for row in unanswerable),
            "p50_query_latency_ms": statistics.median(row["latency_ms"] for row in selected),
            "p95_query_latency_ms": percentile([row["latency_ms"] for row in selected], 0.95),
            "recall_at_5_by_category": {
                category: statistics.mean(row["recall_at_5"] for row in category_rows[category])
                for category in sorted(category_rows)
            },
        }
    return output


def summarize_packs(
    rows: list[dict[str, Any]], records: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, bool]]:
    summary: dict[str, Any] = {}
    all_cited_valid = True
    all_budget_valid = True
    stale_leakage = False
    untrusted_exposed = False
    for mode in ("raw", "cited", "bucketed"):
        selected = [row for row in rows if row["mode"] == mode]
        answerable = [row for row in selected if row["answerable"]]
        summary[mode] = {
            "packs": len(selected),
            "mean_required_retained": statistics.mean(row["required_retained"] for row in answerable),
            "mean_utf8_bytes": statistics.mean(row["utf8_bytes"] for row in selected),
            "total_omitted": sum(len(row["omitted"]) for row in selected),
            "citation_coverage": statistics.mean(row["citation_coverage"] for row in selected),
        }
        all_budget_valid &= all(row["utf8_bytes"] <= PACK_BUDGET for row in selected)
        all_cited_valid &= all(row["citations_valid"] for row in selected)
        if mode == "bucketed":
            for row in selected:
                for record_id, placement in row["placements"].items():
                    stale_leakage |= records[record_id]["context_bucket"] == "stale_conflicting" and placement != "stale_conflicting"
                    untrusted_exposed |= records[record_id]["trust"] == "untrusted"
    gates = {
        "all_packed_citations_valid": all_cited_valid,
        "all_packs_within_utf8_budget": all_budget_valid,
        "zero_stale_to_current_supporting_leakage": not stale_leakage,
        "zero_untrusted_exposure_in_bucketed_pack": not untrusted_exposed,
    }
    return summary, gates


def validate_packed_citations(pack: dict[str, Any], records: dict[str, dict[str, Any]], mode: str) -> tuple[bool, float]:
    if mode == "raw":
        return True, 0.0
    included = pack["included"]
    valid = all(f"[{citation(records[record_id])}]" in pack["text"] for record_id in included)
    return valid, 1.0 if included and valid else (1.0 if not included else 0.0)


def run(output: Path, with_fastembed: bool, cache_dir: Path) -> dict[str, Any]:
    corpus_path = SOURCE / "corpus.jsonl"
    queries_path = SOURCE / "queries.jsonl"
    evidence_path = SOURCE / "evidence.md"
    corpus = load_jsonl(corpus_path)
    queries = load_jsonl(queries_path)
    input_validation = validate_inputs(corpus, queries, evidence_path)
    records = {row["record_id"]: row for row in corpus}
    retrieval_rows: list[dict[str, Any]] = []
    pack_rows: list[dict[str, Any]] = []
    rankings: dict[str, dict[str, list[str]]] = defaultdict(dict)
    build: dict[str, Any] = {}
    unavailable: dict[str, str] = {}

    with tempfile.TemporaryDirectory(prefix="pmlab-reuse-char-") as temp:
        database = Path(temp) / "fts5.sqlite3"
        started = time.perf_counter()
        fts = FTS5Retriever(corpus, database)
        build[fts.name] = {
            "build_ms": round((time.perf_counter() - started) * 1000, 6),
            "index_bytes": database.stat().st_size,
        }
        dense = None
        if with_fastembed:
            try:
                dense = FastEmbedRetriever(corpus, cache_dir)
                build[dense.name] = {
                    "model_load_ms": round(dense.model_load_ms, 6),
                    "embedding_ms": round(dense.embedding_ms, 6),
                    "vector_bytes": dense.vector_bytes,
                    "cache_bytes": directory_bytes(cache_dir),
                }
            except Exception as exc:
                unavailable["C0_FASTEMBED"] = f"{type(exc).__name__}: {exc}"
                unavailable["C2_RRF"] = "dense component unavailable"
        else:
            unavailable["C0_FASTEMBED"] = "run without --with-fastembed"
            unavailable["C2_RRF"] = "dense component unavailable"

        try:
            for query in queries:
                started = time.perf_counter()
                sparse_depth = fts.retrieve(query["query"], CANDIDATE_DEPTH)
                sparse_ms = (time.perf_counter() - started) * 1000
                rankings[fts.name][query["query_id"]] = sparse_depth[:TOP_K]
                arm_values = [(fts.name, sparse_depth[:TOP_K], sparse_ms)]
                if dense is not None:
                    started = time.perf_counter()
                    dense_depth = dense.retrieve(query["query"], CANDIDATE_DEPTH)
                    dense_ms = (time.perf_counter() - started) * 1000
                    hybrid = rrf([sparse_depth, dense_depth], TOP_K)
                    rankings[dense.name][query["query_id"]] = dense_depth[:TOP_K]
                    rankings["C2_RRF"][query["query_id"]] = hybrid
                    arm_values.extend([(dense.name, dense_depth[:TOP_K], dense_ms), ("C2_RRF", hybrid, sparse_ms + dense_ms)])
                for arm, ranked, latency_ms in arm_values:
                    score = score_retrieval(query, ranked)
                    retrieval_rows.append(
                        {
                            "arm": arm,
                            "query_id": query["query_id"],
                            "category": query["category"],
                            "answerable": query["answerable"],
                            "ranked": ranked,
                            "latency_ms": round(latency_ms, 6),
                            **score,
                        }
                    )
                    for mode in ("raw", "cited", "bucketed"):
                        pack = build_pack(mode, ranked, records)
                        required = set(query["required_ids"])
                        citations_valid, coverage = validate_packed_citations(pack, records, mode)
                        pack_rows.append(
                            {
                                "arm": arm,
                                "query_id": query["query_id"],
                                "answerable": query["answerable"],
                                "mode": mode,
                                "included": pack["included"],
                                "omitted": pack["omitted"],
                                "placements": pack["placements"],
                                "utf8_bytes": pack["utf8_bytes"],
                                "required_retained": len(required & set(pack["included"])) / len(required) if required else 1.0,
                                "citations_valid": citations_valid,
                                "citation_coverage": coverage,
                            }
                        )
        finally:
            fts.close()

    retrieval_summary = summarize_retrieval(retrieval_rows)
    pack_summary, pack_gates = summarize_packs(pack_rows, records)
    ranking_payload = {arm: rankings[arm] for arm in sorted(rankings)}
    ranking_bytes = (json.dumps(ranking_payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    gates = {
        "all_corpus_citations_exact": len(input_validation["citation_hashes"]) == len(corpus),
        "rrf_reference_example_exact": rrf([["A", "B"], ["B", "C"]], 3) == ["B", "A", "C"],
        **pack_gates,
    }
    summary = {
        "experiment_id": "PMLAB-REUSE-CHAR-001",
        "status": "completed-synthetic-development-characterization",
        "architecture_selection_allowed": False,
        "retrieval": retrieval_summary,
        "packaging": pack_summary,
        "characterization_gates": gates,
        "all_characterization_gates_pass": all(gates.values()),
        "unavailable_arms": unavailable,
        "build": build,
        "rankings_sha256": sha256_bytes(ranking_bytes),
    }
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "sqlite": sqlite3.sqlite_version,
        "fastembed_requested": with_fastembed,
        "fastembed_model": MODEL_NAME if with_fastembed else None,
        "fastembed_model_revision": MODEL_REVISION if with_fastembed else None,
        "network_model_calls": 0,
    }
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "retrieval-results.jsonl", retrieval_rows)
    write_jsonl(output / "pack-results.jsonl", pack_rows)
    write_json(output / "rankings.json", ranking_payload)
    write_json(output / "summary.json", summary)
    write_json(output / "environment-lock.json", environment)
    write_json(
        output / "execution-manifest.json",
        {
            "experiment_id": summary["experiment_id"],
            "protocol": "docs/11-research-laboratory/reuse-characterization-benchmark-protocol-v0.md",
            "corpus_sha256": sha256_file(corpus_path),
            "queries_sha256": sha256_file(queries_path),
            "evidence_sha256": sha256_file(evidence_path),
            "runner_sha256": sha256_file(Path(__file__)),
            "rankings_sha256": summary["rankings_sha256"],
            "top_k": TOP_K,
            "candidate_depth": CANDIDATE_DEPTH,
            "rrf_k": RRF_K,
            "pack_budget_utf8_bytes": PACK_BUDGET,
            "model_api_calls": 0,
            "architecture_selection_allowed": False,
        },
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--with-fastembed", action="store_true")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "tmp" / "fastembed-cache")
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.with_fastembed, args.cache_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
