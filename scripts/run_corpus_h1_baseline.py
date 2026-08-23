"""PMLAB-H1-BASE-E1: what does plain lexical retrieval do on corpus H1?

Issues #41 and #38. Deterministic, model-free, no network, no API cost.

Why this run exists
-------------------
Corpus H1 has 84 probes and has never been run against anything. A corpus whose
difficulty is unknown is not yet a benchmark: if a plain FTS5 index answers
every probe, the corpus is too easy and the compaction arms would all score
alike; if it answers none, the corpus is broken rather than hard.

This establishes the floor before any arm is built, using the same SQLite FTS5
engine the project's memory already uses.

What is measured, and why recall alone is not enough
----------------------------------------------------
``recall@k``          did the gold event appear in the top k
``intrusion@k``       did the *forbidden* event appear — the superseded,
                      poisoned or outweighed record whose retrieval in place of
                      the gold is the specific failure each family is built
                      around
``forbidden_above_gold``  did the forbidden record outrank the gold. This is the
                      number that matters: a system retrieving both looks fine
                      on recall and is wrong in practice
``recall_per_1k``     critical recall per 1000 retrieved tokens (#38), so a
                      system cannot buy recall with unlimited context

A retrieved token here is a whitespace token of an event's text that would enter
a prompt at the depth being scored — not the whole candidate set the backend
considered. The two differ by a lot at depth 10, and the choice is stated rather
than left implicit.

What this deliberately does not do
-----------------------------------
It does not answer the questions. Scoring *delayed supported task success* needs
a reader model, which is what still blocks PMLAB-COMP-C1 through C7. This
measures retrieval only, and the report says so.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "lab" / "corpus-h1"
DEFAULT_OUT = CORPUS / "baseline-v0"

DEPTHS = (1, 5, 10)

# FTS5 treats these as syntax. A question containing a bare colon or a quote
# raises rather than returning nothing, which would silently drop probes.
FTS_UNSAFE = re.compile(r"[^\w\s]", re.UNICODE)


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def tokens(text: str) -> int:
    return len(text.split())


def build_index(events: list[dict[str, Any]]) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE VIRTUAL TABLE events USING fts5(event_id UNINDEXED, text)")
    connection.executemany(
        "INSERT INTO events (event_id, text) VALUES (?, ?)",
        [(event["event_id"], event["text"]) for event in events],
    )
    connection.commit()
    return connection


def search(connection: sqlite3.Connection, question: str, limit: int) -> list[str]:
    """Rank by bm25. Punctuation is stripped rather than escaped.

    Escaping would preserve more of the query, but a question mark and a colon
    carry no retrieval signal here, and a malformed match expression raises
    instead of returning nothing — which would drop probes silently and make
    the corpus look harder than it is.
    """
    cleaned = FTS_UNSAFE.sub(" ", question).strip()
    terms = [term for term in cleaned.split() if len(term) > 1]
    if not terms:
        return []
    expression = " OR ".join(terms)
    rows = connection.execute(
        "SELECT event_id FROM events WHERE events MATCH ? ORDER BY bm25(events) LIMIT ?",
        (expression, limit),
    ).fetchall()
    return [row[0] for row in rows]


def run(corpus: Path) -> dict[str, Any]:
    events = load(corpus / "prefix-v0" / "history.jsonl")
    queries = load(corpus / "reveal-v0" / "queries.jsonl")
    gold_rows = load(corpus / "reveal-v0" / "gold.jsonl")

    text_of = {event["event_id"]: event["text"] for event in events}
    gold_of = {row["query_id"]: row for row in gold_rows}

    connection = build_index(events)
    deepest = max(DEPTHS)

    records: list[dict[str, Any]] = []
    for query in queries:
        gold = gold_of[query["query_id"]]
        ranked = search(connection, query["question"], deepest)

        record: dict[str, Any] = {
            "query_id": query["query_id"],
            "family": gold["case_id"].rsplit("-", 1)[0],
            "results": len(ranked),
        }
        for depth in DEPTHS:
            window = ranked[:depth]
            record[f"recall@{depth}"] = int(gold["gold_event_id"] in window)
            record[f"intrusion@{depth}"] = (
                int(gold["forbidden_event_id"] in window) if gold["forbidden_event_id"] else None
            )
            record[f"retrieved_tokens@{depth}"] = sum(tokens(text_of[e]) for e in window)

        if gold["forbidden_event_id"] and gold["forbidden_event_id"] in ranked:
            forbidden_rank = ranked.index(gold["forbidden_event_id"])
            gold_rank = ranked.index(gold["gold_event_id"]) if gold["gold_event_id"] in ranked else None
            record["forbidden_above_gold"] = int(gold_rank is None or forbidden_rank < gold_rank)
        elif gold["forbidden_event_id"]:
            record["forbidden_above_gold"] = 0
        else:
            record["forbidden_above_gold"] = None

        records.append(record)

    return {"records": records, "summary": summarise(records, len(events))}


def _mean(values: list[int]) -> float | None:
    """None rather than 0.0 when there is nothing to average.

    Reporting 0.0 for an empty set claims a measurement that was never made.
    The same rule the decorrelation harness follows for a constant vector.
    """
    return round(sum(values) / len(values), 6) if values else None


def summarise(records: list[dict[str, Any]], corpus_events: int) -> dict[str, Any]:
    families = sorted({record["family"] for record in records})
    summary: dict[str, Any] = {
        "experiment_id": "PMLAB-H1-BASE-E1",
        "tier": "E-exploratory",
        "authority": "development measurement only; retrieval only, no reader, no API cost",
        "corpus_events": corpus_events,
        "queries": len(records),
        "arm": "fts5-bm25-or-terms",
    }

    for depth in DEPTHS:
        summary[f"recall@{depth}"] = _mean([r[f"recall@{depth}"] for r in records])
        intrusions = [r[f"intrusion@{depth}"] for r in records if r[f"intrusion@{depth}"] is not None]
        summary[f"intrusion@{depth}"] = _mean(intrusions)
        summary[f"mean_retrieved_tokens@{depth}"] = _mean(
            [r[f"retrieved_tokens@{depth}"] for r in records]
        )
        recall = summary[f"recall@{depth}"]
        spent = summary[f"mean_retrieved_tokens@{depth}"]
        # Undefined rather than infinite when nothing was retrieved (#38).
        summary[f"recall_per_1k_tokens@{depth}"] = (
            round(recall / spent * 1000, 6) if recall is not None and spent else None
        )

    above = [r["forbidden_above_gold"] for r in records if r["forbidden_above_gold"] is not None]
    summary["probes_with_a_forbidden_event"] = len(above)
    summary["forbidden_above_gold"] = _mean(above)

    summary["by_family"] = {
        family: {
            "queries": sum(1 for r in records if r["family"] == family),
            "recall@5": _mean([r["recall@5"] for r in records if r["family"] == family]),
            "recall@10": _mean([r["recall@10"] for r in records if r["family"] == family]),
            "forbidden_above_gold": _mean(
                [r["forbidden_above_gold"] for r in records
                 if r["family"] == family and r["forbidden_above_gold"] is not None]
            ),
        }
        for family in families
    }

    summary["retrieved_token_definition"] = (
        "whitespace tokens of the event texts that would enter a prompt at the depth being "
        "scored, not the full candidate set the backend considered"
    )
    summary["not_measured"] = (
        "whether an arm could answer the question from what it retrieved; that is delayed "
        "supported task success and needs a reader model"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--no-write", action="store_true")
    arguments = parser.parse_args(argv)

    result = run(arguments.corpus if arguments.corpus.is_absolute() else ROOT / arguments.corpus)
    summary = result["summary"]

    print(f"{summary['experiment_id']} — {summary['arm']}")
    print(f"  corpus {summary['corpus_events']} events, {summary['queries']} probes\n")
    for depth in DEPTHS:
        print(f"  recall@{depth:<3} {summary[f'recall@{depth}']:<10} "
              f"intrusion@{depth:<3} {summary[f'intrusion@{depth}']:<10} "
              f"tokens {summary[f'mean_retrieved_tokens@{depth}']:<8} "
              f"recall/1k {summary[f'recall_per_1k_tokens@{depth}']}")
    print(f"\n  forbidden outranks gold  {summary['forbidden_above_gold']} "
          f"over {summary['probes_with_a_forbidden_event']} probes")
    print("\n  by family")
    for family, block in summary["by_family"].items():
        above = block["forbidden_above_gold"]
        print(f"    {family:<12} n={block['queries']:<3} recall@5={block['recall@5']:<10} "
              f"recall@10={block['recall@10']:<10} forbidden>gold={above}")

    if arguments.no_write:
        return 0

    out = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_bytes(
        (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(f"\nwritten: {(out / 'results.json').relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
