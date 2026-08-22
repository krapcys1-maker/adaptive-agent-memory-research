#!/usr/bin/env python3
"""Discover candidate literature through OpenAlex and build a deduplicated catalog.

Discovery results are leads, not evidence. Read primary sources before moving a
paper into papers-curated.csv or the evidence ledger.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError


ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "catalogs" / "papers-discovered.csv"
SNAPSHOT_DIR = ROOT / "data" / "snapshots"

QUERIES = [
    ("human-working-memory", "human working memory attention maintenance interference"),
    ("human-episodic-memory", "human episodic memory context source temporal binding"),
    ("human-semantic-memory", "semantic memory schema consolidation generalization"),
    ("human-procedural-memory", "procedural memory skill habit sequence learning"),
    ("human-consolidation", "memory systems consolidation hippocampus neocortex replay"),
    ("human-reconsolidation", "memory reconsolidation reactivation updating"),
    ("human-forgetting", "adaptive forgetting interference retrieval failure inhibition"),
    ("human-retrieval", "retrieval practice spacing encoding specificity source memory"),
    ("human-salience", "memory prediction error novelty reward emotional arousal"),
    ("human-metamemory", "metamemory prospective memory confidence source monitoring"),
    ("comparative-episodic", "comparative animal episodic-like memory what where when"),
    ("animal-spatial", "animal spatial memory navigation food caching"),
    ("animal-procedural", "animal procedural memory skill habit motor learning"),
    ("animal-consolidation", "animal memory consolidation reconsolidation updating"),
    ("motor-memory", "human motor memory skill consolidation interference relearning"),
    ("skeletal-muscle-memory", "skeletal muscle epigenetic myonuclear memory hypertrophy retraining"),
    ("immune-memory", "adaptive immune memory clonal persistence recall response"),
    ("trained-immunity", "trained innate immunity hematopoietic stem cell epigenetic memory"),
    ("cellular-transcriptional", "cellular epigenetic transcriptional memory priming reactivation"),
    ("non-neural-learning", "non-neural learning habituation single cell organism memory"),
    ("prokaryotic-memory", "bacterial CRISPR acquired immune memory spacer history"),
    ("collective-memory", "collective animal memory stigmergy externalized memory"),
    ("agent-memory-survey", "large language model agent memory survey"),
    ("agent-episodic", "LLM agent episodic memory long term"),
    ("agent-consolidation", "LLM agent memory consolidation semantic procedural"),
    ("agent-forgetting", "LLM agent adaptive forgetting retention policy"),
    ("agent-retrieval", "LLM agent memory retrieval temporal causal graph"),
    ("agent-learning", "LLM agent experience learning reflection skill memory"),
    ("agent-local-memory", "local first persistent memory AI agents"),
    ("memory-evaluation", "LLM agent memory benchmark evaluation"),
    ("memory-utility", "future utility memory retention learned policy agents"),
    ("memory-safety", "agent memory security privacy poisoning prompt injection"),
    ("computational-associative-memory", "associative memory attractor pattern completion pattern separation"),
    ("continual-learning-replay", "continual learning experience replay stability plasticity catastrophic forgetting"),
    ("semantic-memory-compression", "episodic memory semantic compression rate distortion information bottleneck"),
    ("memory-allocation-engram", "memory allocation engram excitability synaptic tagging capture"),
    ("sleep-awake-replay", "hippocampal replay sleep awake memory consolidation reactivation"),
    ("neuromodulated-memory", "norepinephrine dopamine reward prediction error emotional memory consolidation"),
    ("prospective-memory-offloading", "prospective memory intention cognitive offloading external reminders metacognition"),
    ("memory-metacognition", "metamemory confidence feeling of knowing retrieval control abstention"),
    ("metamemory-monitoring", "metamemory feeling of knowing judgment of learning confidence monitoring"),
    ("retrieval-control", "memory retrieval control monitoring search decision cognitive control"),
    ("source-monitoring-confidence", "source monitoring memory confidence calibration recognition recall"),
    ("storage-crash-consistency", "storage crash consistency journaling checksums atomic durable recovery"),
    ("temporal-provenance-storage", "temporal database provenance event sourcing append only versioned records"),
    ("distributed-shared-memory", "distributed shared memory consistency provenance concurrent agents"),
    ("information-thermodynamics", "information thermodynamics erasure Landauer memory physical limits"),
]


def inverted_index_to_text(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indexes in index.items():
        positions.extend((index_value, word) for index_value in indexes)
    return " ".join(word for _, word in sorted(positions))


def fetch(query: str, per_page: int, email: str | None, max_attempts: int = 6) -> dict:
    params = {
        "search": query,
        "per-page": str(per_page),
        "sort": "relevance_score:desc",
        "select": ",".join(
            [
                "id",
                "doi",
                "title",
                "publication_year",
                "publication_date",
                "type",
                "authorships",
                "primary_location",
                "open_access",
                "cited_by_count",
                "abstract_inverted_index",
            ]
        ),
    }
    if email:
        params["mailto"] = email
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "adaptive-agent-memory-research/0.1"},
    )
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code != 429 and not 500 <= exc.code < 600:
                raise
            if attempt == max_attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After", "")
            try:
                server_delay = float(retry_after)
            except ValueError:
                server_delay = 0.0
            time.sleep(max(server_delay, min(60.0, 2.0**attempt)))
    raise RuntimeError("OpenAlex request retry loop ended unexpectedly")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-query", type=int, default=30)
    parser.add_argument("--email", default=None, help="Optional polite-pool email for OpenAlex")
    parser.add_argument("--request-delay", type=float, default=0.25)
    args = parser.parse_args()

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    raw: dict[str, object] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "queries": {},
    }
    deduplicated: dict[str, dict[str, object]] = {}

    for label, query in QUERIES:
        payload = fetch(query, args.per_query, args.email)
        raw["queries"][label] = {"query": query, "response": payload}  # type: ignore[index]
        for work in payload.get("results", []):
            key = work.get("doi") or work.get("id") or work.get("title")
            if not key:
                continue
            existing = deduplicated.setdefault(
                key,
                {
                    "openalex_id": work.get("id", ""),
                    "doi": work.get("doi", ""),
                    "title": work.get("title", ""),
                    "year": work.get("publication_year", ""),
                    "date": work.get("publication_date", ""),
                    "type": work.get("type", ""),
                    "authors": "; ".join(
                        a.get("author", {}).get("display_name", "")
                        for a in work.get("authorships", [])[:12]
                    ),
                    "venue": (work.get("primary_location") or {}).get("source", {}).get("display_name", "")
                    if (work.get("primary_location") or {}).get("source")
                    else "",
                    "landing_page": (work.get("primary_location") or {}).get("landing_page_url", ""),
                    "pdf_url": (work.get("primary_location") or {}).get("pdf_url", ""),
                    "open_access": (work.get("open_access") or {}).get("is_oa", False),
                    "cited_by_count": work.get("cited_by_count", 0),
                    "abstract": inverted_index_to_text(work.get("abstract_inverted_index")),
                    "discovery_queries": set(),
                },
            )
            existing["discovery_queries"].add(label)  # type: ignore[union-attr]
        time.sleep(max(0.0, args.request_delay))

    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = SNAPSHOT_DIR / f"openalex-{timestamp}.json"
    snapshot_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    fields = [
        "openalex_id",
        "doi",
        "title",
        "year",
        "date",
        "type",
        "authors",
        "venue",
        "landing_page",
        "pdf_url",
        "open_access",
        "cited_by_count",
        "discovery_queries",
        "abstract",
    ]
    rows = sorted(
        deduplicated.values(),
        key=lambda row: (int(row.get("year") or 0), int(row.get("cited_by_count") or 0)),
        reverse=True,
    )
    with CATALOG_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row["discovery_queries"] = ";".join(sorted(row["discovery_queries"]))
            writer.writerow(row)

    print(f"Discovered {len(rows)} unique works")
    print(f"Catalog: {CATALOG_PATH}")
    print(f"Snapshot: {snapshot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
