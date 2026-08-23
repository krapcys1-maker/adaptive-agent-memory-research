"""PMLAB-ASSOC-E3: does the association graph help once the leak is closed?

Tier E exploratory experiment. Model-free, no network, no API cost.

Why this run exists
-------------------
`PMLAB-ASSOC-E2` reported +0.0542 Recall@5 and was **retracted**. Its leakage
control removed only the direct edge between a held-out pair, leaving every
other event citing the same source connected to both endpoints, so the group
that defined the gold reassembled over two hops. Reproduction found 67.5% of
graph-reachable targets reachable only that way, and neutralising those
recoveries reversed the difference to −0.0644 at depth 5.

This run repairs the control and asks the question honestly. A negative or null
answer is the expected outcome and is the point.

The corrected control
---------------------
When a pair `(A, B)` is held out, identify every group — a shared source, or a
shared rare tag — that contains both endpoints. Those are the groups that
*defined the gold*. An edge is then removed if **every** group generating it is
one of those; an edge that also arises from an independent group survives,
because that group is a genuine alternative mechanism rather than the gold
reassembling.

Removing all group-generated edges unconditionally would be too strong and would
delete legitimate structure. Removing only the direct edge, as E2 did, is far too
weak. This is the middle that actually tests transitivity.

Two further repairs to E2
-------------------------
**Displacement is reported again.** E1 measured the cost in lexical positions
surrendered; E2 dropped the metric and therefore published only the favourable
half. `PMLAB-XLANG-E1` later measured that cost directly: graph fusion took
English Recall@5 from 1.000 to 0.711 on queries lexical already answered.

**No post-hoc pooling.** E2 decided to pool strata after seeing them, then leaned
on the pooled interval. Here the mechanical stratum — the only one whose gold is
not authored by the agent running the experiment — is the primary result, and
the tag stratum is reported beside it, labelled. There is no pooled headline.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from tools.project_memory.memory_store import MemoryStore  # noqa: E402
from run_association_graph_e2 import (  # noqa: E402
    EXPERIMENT_ID,
    FOLDS,
    MECHANICAL_TYPES,
    MEMORY_KINDS,
    RARE_TAG_MAX,
    SEED_COUNT,
    fold_of,
    graph_ranking,
    load_events,
    rrf,
)
from run_cross_language_e1 import bootstrap  # noqa: E402

BOOTSTRAP_RESAMPLES = 10000


def build_groups(active: dict[str, dict[str, Any]], all_events: list[dict[str, Any]]):
    """Every group whose membership generates edges, keyed by (type, name)."""
    groups: dict[tuple[str, str], set[str]] = {}

    by_source: dict[str, set[str]] = collections.defaultdict(set)
    by_experiment: dict[str, set[str]] = collections.defaultdict(set)
    by_tag: dict[str, set[str]] = collections.defaultdict(set)
    counts: collections.Counter = collections.Counter()

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
            counts[tag] += 1
    for identifier, event in active.items():
        for tag in event.get("tags") or []:
            if 2 <= counts[tag] <= RARE_TAG_MAX:
                by_tag[tag].add(identifier)

    for name, members in by_source.items():
        if len(members) > 1:
            groups[("shares_source", name)] = members
    for name, members in by_experiment.items():
        if len(members) > 1:
            groups[("same_experiment", name)] = members
    for name, members in by_tag.items():
        if len(members) > 1:
            groups[("shared_rare_tag", name)] = members

    # Supersession is pairwise rather than a group; model each link as its own.
    for event in all_events:
        target = event.get("supersedes")
        if isinstance(target, str) and target and target in active and event["id"] in active:
            groups[("supersession", f"{target}->{event['id']}")] = {target, event["id"]}

    edge_groups: dict[tuple[str, str], set[tuple[str, str]]] = collections.defaultdict(set)
    for key, members in groups.items():
        for left, right in itertools.combinations(sorted(members), 2):
            edge_groups[(left, right)].add(key)
    return groups, dict(edge_groups)


def run(root: Path) -> dict[str, Any]:
    store = MemoryStore(root)
    store.rebuild_index()
    active, all_events = load_events(root)
    groups, edge_groups = build_groups(active, all_events)

    all_pairs = sorted(edge_groups)
    folds: dict[int, list[tuple[str, str]]] = collections.defaultdict(list)
    for pair in all_pairs:
        folds[fold_of(pair)].append(pair)

    records: list[dict[str, Any]] = []
    for fold in range(FOLDS):
        for left, right in folds.get(fold, []):
            gold_groups = edge_groups[(left, right)]
            stratum = (
                "mechanical"
                if any(kind in MECHANICAL_TYPES for kind, _ in gold_groups)
                else "tag_only"
            )

            # Corrected control: drop an edge only when every group generating it
            # is one of the groups that defined this gold pair.
            graph: dict[str, set[str]] = collections.defaultdict(set)
            removed = 0
            for pair in all_pairs:
                if edge_groups[pair] <= gold_groups:
                    removed += 1
                    continue
                graph[pair[0]].add(pair[1])
                graph[pair[1]].add(pair[0])

            for source, target in ((left, right), (right, left)):
                event = active.get(source)
                if event is None:
                    continue
                text = f"{event.get('title','')} {event.get('summary','')}".strip()
                if not text:
                    continue
                lexical = [
                    h["id_or_path"]
                    for h in store.search(text, limit=50, kinds=MEMORY_KINDS, expand=False)
                    if h["id_or_path"] != source
                ]
                order = graph_ranking(graph, lexical[:SEED_COUNT], {source})
                fused10 = rrf([lexical, order], 10)
                records.append(
                    {
                        "fold": fold,
                        "stratum": stratum,
                        "query": source,
                        "target": target,
                        "edges_removed": removed,
                        "b1_hit@5": int(target in lexical[:5]),
                        "b2_hit@5": int(target in rrf([lexical, order], 5)),
                        "b1_hit@10": int(target in lexical[:10]),
                        "b2_hit@10": int(target in fused10),
                        "graph_reachable": int(target in order),
                        # Restored from E1: how many lexical positions the graph took.
                        "displaced@10": len([i for i in fused10 if i not in lexical[:10]]),
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
            "mean_displaced@10": round(sum(r["displaced@10"] for r in subset) / n, 4),
            "queries_harmed@10": sum(1 for r in subset if r["b2_hit@10"] < r["b1_hit@10"]),
            "queries_helped@10": sum(1 for r in subset if r["b2_hit@10"] > r["b1_hit@10"]),
        }

    mechanical = [r for r in records if r["stratum"] == "mechanical"]
    return {
        "summary": {
            "experiment_id": "PMLAB-ASSOC-E3",
            "tier": "E-exploratory",
            "authority": "development measurement only; primary stratum is mechanical, no pooled headline",
            "supersedes": "PMLAB-ASSOC-E2, retracted for insufficient leakage control",
            "leakage_control": (
                "an edge is removed when every group generating it is one of the groups that "
                "defined the held-out gold pair; an edge with an independent generating group "
                "survives"
            ),
            "active_events": len(active),
            "groups": len(groups),
            "edges": len(all_pairs),
            "primary_mechanical": summarize(mechanical),
            "secondary_tag_only_authored_gold": summarize(
                [r for r in records if r["stratum"] == "tag_only"]
            ),
            "mean_edges_removed_per_holdout": round(
                sum(r["edges_removed"] for r in records) / max(1, len(records)), 3
            ),
        },
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)

    payload = run(ROOT)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))

    if arguments.output:
        destination = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
        print(f"\nwritten: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
