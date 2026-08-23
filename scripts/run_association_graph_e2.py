"""PMLAB-ASSOC-E2: does the association effect survive a second edge type?

Tier E exploratory experiment. Model-free, no network, no API cost, run on the
project's own memory. It cannot support a confirmatory or architecture claim.

Follows PMLAB-ASSOC-E1, which materialized ``shares_source`` co-citation edges
and found the retrieval benefit inconclusive: +0.0392 Recall@10 with a 95%
interval of [-0.0098, 0.0882] over 102 edges. E1's registered next step was a
second deterministic edge type, to enlarge the sample and to test whether any
effect is specific to co-citation.

Edge types
----------
``shares_source``    two events cite the same ``source_ref``
``same_experiment``  two events mention the same ``PMLAB-*`` or ``API-*`` id
``supersession``     an explicit supersedes relation
``shared_rare_tag``  two events share a tag carried by at most four events

Gold stratification, and why it matters
---------------------------------------
The first three are mechanical: citing the same file, naming the same
experiment, or an explicit supersession field. The fourth is not. **Tags in this
repository were authored by the same agent that is running the experiment**, so
using them as gold would measure the author's own judgement of relatedness —
exactly the authored-fixture trap this project keeps falling into and which E1
deliberately avoided.

So results are reported in two strata:

``mechanical``  gold from the first three types
``tag_only``    gold from pairs supported by ``shared_rare_tag`` alone

Tag edges are still allowed *into the graph*. Using authored structure to route
a search is legitimate; using it to define what counts as a correct answer is
not.

Leakage control
---------------
When a pair is held out, **every** direct edge between those two events is
removed from the fold graph, regardless of type. Without that, a pair connected
by both a source and a tag would remain directly linked and the graph would
recover it trivially.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.project_memory.memory_store import MemoryStore  # noqa: E402

FOLDS = 5
SPLIT_KEY = b"pmlab-assoc-e2-v0"
RRF_K = 60
SEED_COUNT = 3
BOOTSTRAP_RESAMPLES = 10000
RARE_TAG_MAX = 4

EXPERIMENT_ID = re.compile(r"\b(PMLAB-[A-Z0-9-]+?-(?:\d{3}|E\d)|API-[A-Z0-9-]+-\d{3})\b")

MECHANICAL_TYPES = ("shares_source", "same_experiment", "supersession")

MEMORY_KINDS = [
    "memory:candidate", "memory:constraint", "memory:decision", "memory:failure",
    "memory:finding", "memory:hypothesis", "memory:procedure", "memory:question",
    "memory:session",
]


def load_events(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    events = [
        json.loads(line)
        for line in (root / "memory" / "events.jsonl").read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    superseded = {event["supersedes"] for event in events if event.get("supersedes")}
    return {e["id"]: e for e in events if e["id"] not in superseded}, events


def _pairs(groups: dict[str, set[str]]) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for identifiers in groups.values():
        if len(identifiers) < 2:
            continue
        for left, right in itertools.combinations(sorted(identifiers), 2):
            out.add((left, right))
    return out


def build_typed_edges(
    active: dict[str, dict[str, Any]], all_events: list[dict[str, Any]]
) -> dict[str, set[tuple[str, str]]]:
    by_source: dict[str, set[str]] = collections.defaultdict(set)
    by_experiment: dict[str, set[str]] = collections.defaultdict(set)
    by_tag: dict[str, set[str]] = collections.defaultdict(set)
    tag_counts: collections.Counter = collections.Counter()

    for identifier, event in active.items():
        for reference in event.get("source_refs") or []:
            if isinstance(reference, str) and reference.strip():
                by_source[reference].add(identifier)
        blob = " ".join(
            [
                event.get("title", ""),
                event.get("summary", ""),
                event.get("body", ""),
                " ".join(event.get("tags") or []),
                " ".join(event.get("source_refs") or []),
            ]
        )
        for match in set(EXPERIMENT_ID.findall(blob)):
            by_experiment[match].add(identifier)
        for tag in event.get("tags") or []:
            tag_counts[tag] += 1

    for identifier, event in active.items():
        for tag in event.get("tags") or []:
            if 2 <= tag_counts[tag] <= RARE_TAG_MAX:
                by_tag[tag].add(identifier)

    supersession: set[tuple[str, str]] = set()
    for event in all_events:
        target = event.get("supersedes")
        if isinstance(target, str) and target:
            supersession.add(tuple(sorted((event["id"], target))))  # type: ignore[arg-type]

    return {
        "shares_source": _pairs(by_source),
        "same_experiment": _pairs(by_experiment),
        "supersession": supersession,
        "shared_rare_tag": _pairs(by_tag),
    }


def fold_of(pair: tuple[str, str]) -> int:
    digest = hashlib.sha256(SPLIT_KEY + "|".join(pair).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % FOLDS


def graph_ranking(graph: dict[str, set[str]], seeds: list[str], exclude: set[str]) -> list[str]:
    support: collections.Counter = collections.Counter()
    for seed in seeds:
        for neighbour in graph.get(seed, ()):
            if neighbour not in exclude:
                support[neighbour] += 1
    return [item for item, _ in sorted(support.items(), key=lambda e: (-e[1], e[0]))]


def rrf(rankings: list[list[str]], limit: int) -> list[str]:
    scores: dict[str, float] = collections.defaultdict(float)
    for ranking in rankings:
        for position, item in enumerate(ranking, start=1):
            scores[item] += 1.0 / (RRF_K + position)
    return [item for item, _ in sorted(scores.items(), key=lambda e: (-e[1], e[0]))[:limit]]


def bootstrap(paired: list[tuple[int, int]], resamples: int) -> dict[str, float]:
    if not paired:
        return {"mean": 0.0, "low": 0.0, "high": 0.0, "n": 0}
    size = len(paired)
    observed = sum(b - a for a, b in paired) / size
    state = 0x243F6A8885A308D3
    differences: list[float] = []
    for _ in range(resamples):
        total = 0
        for _ in range(size):
            state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            left, right = paired[(state >> 33) % size]
            total += right - left
        differences.append(total / size)
    differences.sort()
    return {
        "mean": round(observed, 6),
        "low": round(differences[int(0.025 * resamples)], 6),
        "high": round(differences[int(0.975 * resamples) - 1], 6),
        "n": size,
    }


def run(root: Path) -> dict[str, Any]:
    store = MemoryStore(root)
    store.rebuild_index()
    active, all_events = load_events(root)
    typed = build_typed_edges(active, all_events)

    support: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for name, edges in typed.items():
        for pair in edges:
            if pair[0] in active and pair[1] in active:
                support[pair].add(name)
    all_pairs = sorted(support)

    folds: dict[int, list[tuple[str, str]]] = collections.defaultdict(list)
    for pair in all_pairs:
        folds[fold_of(pair)].append(pair)

    records: list[dict[str, Any]] = []
    for fold in range(FOLDS):
        held_out = folds.get(fold, [])
        held_set = set(held_out)
        # Every direct edge between a held-out pair is removed, whatever its
        # type. Otherwise a pair linked by two mechanisms stays linked.
        graph: dict[str, set[str]] = collections.defaultdict(set)
        for pair in all_pairs:
            if pair in held_set:
                continue
            graph[pair[0]].add(pair[1])
            graph[pair[1]].add(pair[0])

        for left, right in held_out:
            types = support[(left, right)]
            stratum = "mechanical" if types & set(MECHANICAL_TYPES) else "tag_only"
            for source, target in ((left, right), (right, left)):
                event = active.get(source)
                if event is None:
                    continue
                text = f"{event.get('title','')} {event.get('summary','')}".strip()
                if not text:
                    continue
                hits = store.search(text, limit=50, kinds=MEMORY_KINDS)
                lexical = [h["id_or_path"] for h in hits if h["id_or_path"] != source]
                order = graph_ranking(graph, lexical[:SEED_COUNT], {source})
                records.append(
                    {
                        "fold": fold,
                        "stratum": stratum,
                        "types": sorted(types),
                        "query": source,
                        "target": target,
                        "b1_hit@5": int(target in lexical[:5]),
                        "b2_hit@5": int(target in rrf([lexical, order], 5)),
                        "b1_hit@10": int(target in lexical[:10]),
                        "b2_hit@10": int(target in rrf([lexical, order], 10)),
                        "graph_reachable": int(target in order),
                    }
                )

    def summarize(subset: list[dict[str, Any]]) -> dict[str, Any]:
        if not subset:
            return {"queries": 0}
        n = len(subset)
        return {
            "queries": n,
            "reachability_ceiling": round(sum(r["graph_reachable"] for r in subset) / n, 6),
            "b1_recall@5": round(sum(r["b1_hit@5"] for r in subset) / n, 6),
            "b2_recall@5": round(sum(r["b2_hit@5"] for r in subset) / n, 6),
            "b1_recall@10": round(sum(r["b1_hit@10"] for r in subset) / n, 6),
            "b2_recall@10": round(sum(r["b2_hit@10"] for r in subset) / n, 6),
            "difference@5": bootstrap([(r["b1_hit@5"], r["b2_hit@5"]) for r in subset], BOOTSTRAP_RESAMPLES),
            "difference@10": bootstrap([(r["b1_hit@10"], r["b2_hit@10"]) for r in subset], BOOTSTRAP_RESAMPLES),
        }

    summary = {
        "experiment_id": "PMLAB-ASSOC-E2",
        "tier": "E-exploratory",
        "authority": "development measurement only; not confirmatory, not independently reviewed",
        "active_events": len(active),
        "edges_by_type": {name: len(edges) for name, edges in sorted(typed.items())},
        "edges_total_union": len(all_pairs),
        "connected_nodes": len({node for pair in all_pairs for node in pair}),
        "rrf_k": RRF_K,
        "seed_count": SEED_COUNT,
        "rare_tag_max": RARE_TAG_MAX,
        "overall": summarize(records),
        "mechanical": summarize([r for r in records if r["stratum"] == "mechanical"]),
        "tag_only": summarize([r for r in records if r["stratum"] == "tag_only"]),
        "gold_caveat": (
            "tag_only gold derives from tags authored by the same agent running the "
            "experiment and is therefore weaker evidence of relatedness than the "
            "mechanical strata"
        ),
    }
    payload = {"summary": summary, "records": records}
    payload["summary"]["records_sha256"] = hashlib.sha256(
        json.dumps(records, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)

    payload = run(ROOT)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))

    if arguments.output:
        destination = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"\nwritten: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
