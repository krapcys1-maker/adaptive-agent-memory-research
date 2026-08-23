"""PMLAB-ASSOC-E1: does a deterministic association graph help lexical retrieval?

Tier E exploratory experiment. Model-free, no network, no API cost, run on the
project's own memory rather than an authored fixture. It cannot support a
confirmatory or architecture claim and is not independently reviewed.

Question
--------
Two memory events that cite the same ``source_ref`` are related by
construction. Materializing those co-citations gives a ``shares_source`` graph.
Does one hop over that graph recover related memories that lexical search alone
misses?

Design
------
Gold is derived mechanically, never authored. Each ``shares_source`` edge is a
known-related pair. Edges are split into five deterministic folds by SHA-256 of
the pair, so every edge is held out exactly once. For a held-out edge (A, B) the
graph is rebuilt from the other four folds only, so the direct A-B link is
absent and the graph can only help through transitivity.

Arms
----
B1  lexical only: FTS5 over active memory events.
B2  lexical + graph, fused with reciprocal rank fusion at k=60, matching the
    project's already-registered choice of equal-input RRF as the first hybrid.

Both arms return the same number of candidates, so B2 buys graph positions by
giving up lexical ones. That trade is the point of the measurement.

Reporting
---------
Recall@5 and Recall@10 with a paired stratified bootstrap, the 2-hop
reachability ceiling that bounds any possible graph gain, and the displacement
cost in lexical positions surrendered. A negative result is a result.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.project_memory.memory_store import MemoryStore  # noqa: E402

FOLDS = 5
SPLIT_KEY = b"pmlab-assoc-e1-v0"
RRF_K = 60
SEED_COUNT = 3
BOOTSTRAP_RESAMPLES = 10000

MEMORY_KINDS = [
    "memory:candidate",
    "memory:constraint",
    "memory:decision",
    "memory:failure",
    "memory:finding",
    "memory:hypothesis",
    "memory:procedure",
    "memory:question",
    "memory:session",
]


def load_active_events(root: Path) -> dict[str, dict[str, Any]]:
    events = [
        json.loads(line)
        for line in (root / "memory" / "events.jsonl").read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    superseded = {event["supersedes"] for event in events if event.get("supersedes")}
    return {event["id"]: event for event in events if event["id"] not in superseded}


def build_edges(active: dict[str, dict[str, Any]]) -> dict[tuple[str, str], set[str]]:
    source_to_events: dict[str, set[str]] = collections.defaultdict(set)
    for identifier, event in active.items():
        for reference in event.get("source_refs") or []:
            if isinstance(reference, str) and reference.strip():
                source_to_events[reference].add(identifier)

    pair_sources: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for reference, identifiers in source_to_events.items():
        if len(identifiers) < 2:
            continue
        for left, right in itertools.combinations(sorted(identifiers), 2):
            pair_sources[(left, right)].add(reference)
    return dict(pair_sources)


def fold_of(pair: tuple[str, str]) -> int:
    digest = hashlib.sha256(SPLIT_KEY + "|".join(pair).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % FOLDS


def adjacency(pairs: list[tuple[str, str]]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = collections.defaultdict(set)
    for left, right in pairs:
        graph[left].add(right)
        graph[right].add(left)
    return graph


def graph_ranking(graph: dict[str, set[str]], seeds: list[str], exclude: set[str]) -> list[str]:
    """Order candidates by hop distance from the seeds, then by seed support."""
    reached: dict[str, tuple[int, int]] = {}
    first_hop: collections.Counter = collections.Counter()
    for seed in seeds:
        for neighbour in graph.get(seed, ()):
            if neighbour in exclude:
                continue
            first_hop[neighbour] += 1
    for candidate, support in first_hop.items():
        reached[candidate] = (1, -support)
    return [item for item, _ in sorted(reached.items(), key=lambda entry: (entry[1], entry[0]))]


def reciprocal_rank_fusion(rankings: list[list[str]], limit: int) -> list[str]:
    scores: dict[str, float] = collections.defaultdict(float)
    for ranking in rankings:
        for position, item in enumerate(ranking, start=1):
            scores[item] += 1.0 / (RRF_K + position)
    ordered = sorted(scores.items(), key=lambda entry: (-entry[1], entry[0]))
    return [item for item, _ in ordered[:limit]]


def query_text(event: dict[str, Any]) -> str:
    return f"{event.get('title', '')} {event.get('summary', '')}".strip()


def bootstrap_difference(paired: list[tuple[int, int]], resamples: int) -> dict[str, float]:
    if not paired:
        return {"mean": 0.0, "low": 0.0, "high": 0.0}
    size = len(paired)
    observed = sum(b - a for a, b in paired) / size
    state = 0x243F6A8885A308D3
    differences: list[float] = []
    for _ in range(resamples):
        total = 0
        for _ in range(size):
            state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            index = (state >> 33) % size
            left, right = paired[index]
            total += right - left
        differences.append(total / size)
    differences.sort()
    return {
        "mean": observed,
        "low": differences[int(0.025 * resamples)],
        "high": differences[int(0.975 * resamples) - 1],
    }


def run(root: Path, depth: int) -> dict[str, Any]:
    store = MemoryStore(root)
    store.rebuild_index()
    active = load_active_events(root)
    pair_sources = build_edges(active)
    all_pairs = sorted(pair_sources)

    folds: dict[int, list[tuple[str, str]]] = collections.defaultdict(list)
    for pair in all_pairs:
        folds[fold_of(pair)].append(pair)

    records: list[dict[str, Any]] = []
    ceiling_hits = 0

    for fold in range(FOLDS):
        held_out = folds.get(fold, [])
        kept = [pair for other, pairs in folds.items() if other != fold for pair in pairs]
        graph = adjacency(kept)

        for left, right in held_out:
            # Each edge is evaluated in both directions; the query side is A.
            for source, target in ((left, right), (right, left)):
                event = active.get(source)
                if event is None:
                    continue
                text = query_text(event)
                if not text:
                    continue
                hits = store.search(text, limit=50, kinds=MEMORY_KINDS)
                lexical = [hit["id_or_path"] for hit in hits if hit["id_or_path"] != source]

                seeds = lexical[:SEED_COUNT]
                exclude = {source}
                graph_order = graph_ranking(graph, seeds, exclude)
                reachable = target in graph_order

                fused = reciprocal_rank_fusion([lexical, graph_order], limit=depth)
                lexical_only = lexical[:depth]

                displaced = len([item for item in fused if item not in lexical_only])
                records.append(
                    {
                        "fold": fold,
                        "query": source,
                        "target": target,
                        "b1_hit@5": int(target in lexical[:5]),
                        "b2_hit@5": int(target in reciprocal_rank_fusion([lexical, graph_order], 5)),
                        "b1_hit@10": int(target in lexical[:10]),
                        "b2_hit@10": int(target in reciprocal_rank_fusion([lexical, graph_order], 10)),
                        "graph_reachable": int(reachable),
                        "displaced_positions": displaced,
                        "lexical_rank": lexical.index(target) + 1 if target in lexical else None,
                    }
                )
                ceiling_hits += int(reachable)

    def mean(field: str) -> float:
        return sum(record[field] for record in records) / len(records) if records else 0.0

    paired5 = [(record["b1_hit@5"], record["b2_hit@5"]) for record in records]
    paired10 = [(record["b1_hit@10"], record["b2_hit@10"]) for record in records]

    summary = {
        "experiment_id": "PMLAB-ASSOC-E1",
        "tier": "E-exploratory",
        "authority": "development measurement only; not confirmatory, not independently reviewed",
        "active_events": len(active),
        "shared_source_references": len({reference for sources in pair_sources.values() for reference in sources}),
        "edges": len(all_pairs),
        "queries": len(records),
        "folds": FOLDS,
        "rrf_k": RRF_K,
        "seed_count": SEED_COUNT,
        "graph_reachability_ceiling": round(ceiling_hits / len(records), 6) if records else 0.0,
        "b1_recall@5": round(mean("b1_hit@5"), 6),
        "b2_recall@5": round(mean("b2_hit@5"), 6),
        "b1_recall@10": round(mean("b1_hit@10"), 6),
        "b2_recall@10": round(mean("b2_hit@10"), 6),
        "paired_difference@5": {k: round(v, 6) for k, v in bootstrap_difference(paired5, BOOTSTRAP_RESAMPLES).items()},
        "paired_difference@10": {k: round(v, 6) for k, v in bootstrap_difference(paired10, BOOTSTRAP_RESAMPLES).items()},
        "mean_displaced_positions@10": round(mean("displaced_positions"), 6),
    }
    payload = {"summary": summary, "records": records}
    payload["summary"]["records_sha256"] = hashlib.sha256(
        json.dumps(records, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--depth", type=int, default=10)
    arguments = parser.parse_args(argv)

    payload = run(ROOT, arguments.depth)
    summary = payload["summary"]

    print(json.dumps(summary, indent=2, sort_keys=True))

    if arguments.output:
        destination = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"\nwritten: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
