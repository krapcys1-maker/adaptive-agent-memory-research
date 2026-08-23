"""Where did an answer come from, and what lost to it?

An arm comparison says *how often* a system is wrong. It never says *why this
answer and not another one*, and without that a failure is a number rather than
something anyone can fix.

This reconstructs the whole path for one probe, mechanically:

    every candidate in the corpus that could have supported an answer
      ↓  what the arm actually retained, and in what order
      ↓  which retained record supports the answer that was given
      ↓  which competing records were present and lost, and to what

Nothing here calls a model. Every step is decidable from the stored run, the
corpus and the arm's own ordering, so a trace cannot flatter the system that
produced it.

Why "what lost" is the interesting half
---------------------------------------
Two systems can retrieve the same right record and differ entirely in what else
they put beside it. ``PMLAB-H1-READ-E1`` measured retrieval answering 0.845 while
answering from the trapped record on 0.119, and the trapped record was *present
in the context every single time*. The failure was never retrieval; it was that
nothing marked one record as superseded by another. A trace showing "the answer
came from a record ranked N2 while its N1 successor was also present" turns that
from a statistic into a diagnosis.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.arms import supersession_rank  # noqa: E402
from run_corpus_h1_reader import _present  # noqa: E402

CORPUS = ROOT / "data" / "lab" / "corpus-h1"


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def supports(text: str, fragments: list[str]) -> list[str]:
    """Which required fragments this record could have supplied."""
    lowered = text.lower()
    return [f for f in fragments if _present(f, lowered)]


def trace(arm: str, query_id: str, corpus: Path) -> dict[str, Any]:
    events = load(corpus / "prefix-v0" / "history.jsonl")
    by_id = {e["event_id"]: e for e in events}
    gold = {g["query_id"]: g for g in load(corpus / "reveal-v0" / "gold.jsonl")}[query_id]
    query = {q["query_id"]: q for q in load(corpus / "reveal-v0" / "queries.jsonl")}[query_id]

    run = json.loads((corpus / f"reader-v0-{arm}" / "results.json").read_text(encoding="utf-8"))
    record = next(r for r in run["records"] if r["query_id"] == query_id)

    labels = {row["event_id"]: row["properties"] for row in
              load(corpus / "prefix-v0" / "construction-labels.jsonl")}
    chains = {i: i.split("#")[0] for i, p in labels.items()
              if {"obsolete-fact", "explicit-correction"} & set(p)}
    rank = supersession_rank(events, chains)

    required = gold["answer_contains"]
    markers = gold.get("answer_must_not_contain") or []

    # Everything in the corpus that could have supplied part of the answer, or
    # part of the wrong answer. This is the field the arm was choosing from.
    candidates = []
    for event in events:
        if event["day"] > query["asked_on_day"]:
            continue
        gives = supports(event["text"], required)
        traps = supports(event["text"], markers)
        if gives or traps:
            candidates.append({
                "event_id": event["event_id"],
                "day": event["day"],
                "rank_in_chain": rank.get(event["event_id"]),
                "supplies": gives,
                "supplies_trap": traps,
                "text": event["text"],
            })

    retained = record.get("retained_ids")
    if retained is None:
        # Recorded before retained_ids was stored. Every arm is a deterministic
        # function of the corpus, so the selection is recoverable exactly —
        # which is a property worth having and not one to rely on silently, so
        # newer runs store the list.
        from corpus.arms import DEFAULT_TOKEN_BUDGET, rank_demoted, _before, _fill
        from corpus.history_family_spec import _lcg
        from run_corpus_h1_baseline import build_index, search
        from corpus.arms import ARMS

        connection = build_index(events)
        budget = run["summary"]["token_budget"]
        day = query["asked_on_day"]
        if arm == "rank-oracle":
            ids = [e for e in search(connection, query["question"], 60) if e in by_id]
            kept = rank_demoted(events, query["question"], day, budget,
                                ranked_ids=ids, rank=rank)
        elif arm == "fts5":
            ranked_events = [by_id[e] for e in search(connection, query["question"], 60) if e in by_id]
            kept = _fill(_before(ranked_events, day), budget)
        else:
            kept = ARMS[arm](events, query["question"], day, budget,
                             _lcg(hash(query_id) & 0xFFFFFFFF))
        retained = [e["event_id"] for e in kept]
    position = {e: n for n, e in enumerate(retained, start=1)}

    answer = record["answer"]
    answered_from = [c for c in candidates
                     if c["event_id"] in position and supports(answer, c["supplies"])]
    trapped_from = [c for c in candidates
                    if c["event_id"] in position and c["supplies_trap"]
                    and supports(answer, c["supplies_trap"])]

    return {
        "query_id": query_id,
        "arm": arm,
        "question": query["question"],
        "asked_on_day": query["asked_on_day"],
        "answer": answer,
        "outcome": {k: record[k] for k in ("answered", "leaked", "abstained", "empty") if k in record},
        "gold_event_id": gold["gold_event_id"],
        "forbidden_event_id": gold["forbidden_event_id"],
        "candidates_in_the_corpus": len(candidates),
        "candidates_retained": sum(1 for c in candidates if c["event_id"] in position),
        "trace": [
            {
                **c,
                "retained_at_position": position.get(c["event_id"]),
                "role": (
                    "gold" if c["event_id"] == gold["gold_event_id"]
                    else "forbidden" if c["event_id"] == gold["forbidden_event_id"]
                    else "other"
                ),
            }
            for c in sorted(candidates, key=lambda c: (position.get(c["event_id"], 10**6), -c["day"]))
        ],
        "answer_supported_by": [c["event_id"] for c in answered_from],
        "answer_trapped_by": [c["event_id"] for c in trapped_from],
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        f"{result['query_id']}   arm={result['arm']}   asked on day {result['asked_on_day']}",
        f"  Q: {result['question']}",
        f"  A: {result['answer'][:160]}",
        f"  outcome: {result['outcome']}",
        "",
        f"  {result['candidates_in_the_corpus']} records in the corpus could have supplied "
        f"part of an answer; the arm retained {result['candidates_retained']}.",
        "",
        f"  {'pos':<5}{'day':<5}{'rank':<6}{'role':<11}{'supplies':<22}record",
    ]
    for item in result["trace"]:
        position = item["retained_at_position"]
        lines.append(
            f"  {(str(position) if position else '—'):<5}{item['day']:<5}"
            f"{('N' + str(item['rank_in_chain']) if item['rank_in_chain'] else '—'):<6}"
            f"{item['role']:<11}"
            f"{(','.join(item['supplies']) or '(trap: ' + ','.join(item['supplies_trap']) + ')')[:21]:<22}"
            f"{item['text'][:60]}"
        )
    lines += ["",
              f"  the answer was supported by : {result['answer_supported_by'] or '—'}",
              f"  the answer was trapped by   : {result['answer_trapped_by'] or '—'}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("query_id")
    parser.add_argument("--arm", default="fts5")
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    arguments = parser.parse_args(argv)

    corpus = arguments.corpus if arguments.corpus.is_absolute() else ROOT / arguments.corpus
    result = trace(arguments.arm, arguments.query_id, corpus)
    print(json.dumps(result, indent=2, ensure_ascii=False) if arguments.format == "json"
          else render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
