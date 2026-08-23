"""PMLAB-XLANG-E1: can project memory be retrieved in the maintainer's language?

Tier E exploratory experiment. Model-free, no network, no weights downloaded,
no API cost.

The problem, demonstrated rather than inferred
----------------------------------------------
Two questions whose answers had been written into memory the same day returned
zero memories when asked in Polish and one and four when asked in English. The
repository stores durable findings in English by policy, the maintainer works in
Polish, and FTS5 matches tokens, so the owner's own queries retrieve nothing.

Design
------
Language is isolated as the only variable. For each sampled memory:

- the **English** query is its title *verbatim*;
- the **Polish** query is a natural translation of the same title.

The target is that memory's own id, known by construction, so no relevance
judgement is authored. English recall is expected to be near perfect precisely
because the query is the target's own text — that is the control, and it makes
the gap attributable to language alone.

Arms
----
``B1_FTS5``      the current system: lexical search only.
``B2_GRAPH``     B1 fused with the association graph from PMLAB-ASSOC-E2 by RRF.
``B3_GLOSSARY``  B1 with the Polish query expanded through a hand-built
                 domain glossary before it reaches FTS5.

B2 is the interesting arm. ``PMLAB-ASSOC-E2`` explicitly registered
cross-language as untested, because its corpus was predominantly English. A
graph hop can reach a memory that shares no token with the query, which is
exactly this failure mode.

What this cannot answer
-----------------------
Local dense retrieval is the obvious remedy and is **not** tested here. Config
and tokenizer files are cached under ``external/models`` but the weights are
absent, so running it would mean downloading roughly two gigabytes and adding an
inference runtime. That is a resource decision for the maintainer, not something
an exploratory run should take unilaterally.
"""

from __future__ import annotations

import argparse
import collections
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
    MEMORY_KINDS,
    RRF_K,
    SEED_COUNT,
    build_typed_edges,
    graph_ranking,
    load_events,
    rrf,
)

FIXTURE = ROOT / "data" / "lab" / "pmlab-xlang-e1"
BOOTSTRAP_RESAMPLES = 10000
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def expand(query: str, glossary: dict[str, str]) -> str:
    """Append English glossary terms for any Polish word that has one."""
    additions: list[str] = []
    for token in WORD.findall(query.lower()):
        english = glossary.get(token)
        if english:
            additions.extend(english.split())
    if not additions:
        return query
    seen: set[str] = set()
    ordered = [term for term in additions if not (term in seen or seen.add(term))]
    return f"{query} {' '.join(ordered)}"


def bootstrap(paired: list[tuple[int, int]], resamples: int) -> dict[str, float]:
    if not paired:
        return {"mean": 0.0, "low": 0.0, "high": 0.0, "n": 0}
    size = len(paired)
    observed = sum(b - a for a, b in paired) / size
    state = 0x243F6A8885A308D3
    diffs: list[float] = []
    for _ in range(resamples):
        total = 0
        for _ in range(size):
            state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            left, right = paired[(state >> 33) % size]
            total += right - left
        diffs.append(total / size)
    diffs.sort()
    return {
        "mean": round(observed, 6),
        "low": round(diffs[int(0.025 * resamples)], 6),
        "high": round(diffs[int(0.975 * resamples) - 1], 6),
        "n": size,
    }


def run(root: Path) -> dict[str, Any]:
    store = MemoryStore(root)
    store.rebuild_index()
    active, all_events = load_events(root)

    typed = build_typed_edges(active, all_events)
    graph: dict[str, set[str]] = collections.defaultdict(set)
    for edges in typed.values():
        for left, right in edges:
            if left in active and right in active:
                graph[left].add(right)
                graph[right].add(left)

    pairs = json.loads((FIXTURE / "queries.json").read_text(encoding="utf-8"))["pairs"]
    glossary = json.loads((FIXTURE / "glossary.json").read_text(encoding="utf-8"))["terms"]

    records: list[dict[str, Any]] = []
    for pair in pairs:
        target = pair["id"]
        event = active.get(target)
        if event is None:
            continue
        queries = {"en": event.get("title", ""), "pl": pair["pl"]}
        for language, text in queries.items():
            if not text.strip():
                continue
            hits = [h["id_or_path"] for h in store.search(text, limit=50, kinds=MEMORY_KINDS)]
            order = graph_ranking(graph, hits[:SEED_COUNT], set())
            fused5, fused10 = rrf([hits, order], 5), rrf([hits, order], 10)

            expanded = expand(text, glossary) if language == "pl" else text
            gloss_hits = [
                h["id_or_path"] for h in store.search(expanded, limit=50, kinds=MEMORY_KINDS)
            ] if expanded != text else hits

            records.append(
                {
                    "target": target,
                    "language": language,
                    "query": text,
                    "expanded_query": expanded if expanded != text else None,
                    "b1_hit@5": int(target in hits[:5]),
                    "b1_hit@10": int(target in hits[:10]),
                    "b2_hit@5": int(target in fused5),
                    "b2_hit@10": int(target in fused10),
                    "b3_hit@5": int(target in gloss_hits[:5]),
                    "b3_hit@10": int(target in gloss_hits[:10]),
                    "b1_rank": hits.index(target) + 1 if target in hits else None,
                    "b1_candidates": len(hits),
                }
            )

    def summarize(subset: list[dict[str, Any]]) -> dict[str, Any]:
        if not subset:
            return {"queries": 0}
        n = len(subset)
        out: dict[str, Any] = {"queries": n}
        for arm in ("b1", "b2", "b3"):
            for depth in (5, 10):
                out[f"{arm}_recall@{depth}"] = round(
                    sum(r[f"{arm}_hit@{depth}"] for r in subset) / n, 6
                )
        out["mean_candidates"] = round(sum(r["b1_candidates"] for r in subset) / n, 3)
        out["zero_candidate_queries"] = sum(1 for r in subset if r["b1_candidates"] == 0)
        return out

    polish = [r for r in records if r["language"] == "pl"]
    english = [r for r in records if r["language"] == "en"]

    summary = {
        "experiment_id": "PMLAB-XLANG-E1",
        "tier": "E-exploratory",
        "authority": "development measurement only; not confirmatory, not independently reviewed",
        "model_free": True,
        "weights_downloaded": False,
        "active_events": len(active),
        "graph_edges": sum(len(v) for v in graph.values()) // 2,
        "english": summarize(english),
        "polish": summarize(polish),
        "polish_graph_gain@10": bootstrap(
            [(r["b1_hit@10"], r["b2_hit@10"]) for r in polish], BOOTSTRAP_RESAMPLES
        ),
        "polish_glossary_gain@10": bootstrap(
            [(r["b1_hit@10"], r["b3_hit@10"]) for r in polish], BOOTSTRAP_RESAMPLES
        ),
        "not_tested": "local dense retrieval; weights are absent and downloading them is a maintainer decision",
    }
    return {"summary": summary, "records": records}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)

    payload = run(ROOT)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True, ensure_ascii=False))

    if arguments.output:
        destination = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        )
        print(f"\nwritten: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
