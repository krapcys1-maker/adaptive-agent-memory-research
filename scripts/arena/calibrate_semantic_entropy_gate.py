#!/usr/bin/env python3
"""SEMANTIC_ENTROPY_SUFFICIENCY_SIGNAL calibration -- responds to ResearchOS
candidate rmc-2026-08-24-001 and AAMR's own research request
arr-2026-08-24-001 (compact-vs-raw sufficiency gate, GAP-005).

Does NOT ingest anything new and does NOT select any fresh gold-blind
units. Reuses the already-persisted RAW_PROVENANCE fresh-replication-v1
store (banks rawprov-{qid}) and its already-known ground truth (which
units had a sufficient vs. insufficient compact context, from
data/lab/arena/raw-provenance-fresh-replication-v1/results.json) to check,
at near-zero cost, whether black-box semantic entropy (sample M generations
at temperature>0, embed with the same local MiniLM checkpoint Mem0 itself
uses, cluster by cosine similarity, compute entropy over cluster
proportions) separates the two known groups at all -- a precondition/
signal-quality calibration, NOT a causal test and NOT evidence of efficacy
(per this project's own "calibration is not evidence of effect" discipline).

Preregistration: PM-20260825-41d5d71e.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

RAWPROV_RESULTS = ROOT / "data/lab/arena/raw-provenance-fresh-replication-v1/results.json"
CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")


def _results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [i for i in (payload.get("results") or []) if isinstance(i, dict)]
    if isinstance(payload, list):
        return [i for i in payload if isinstance(i, dict)]
    return []


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def greedy_cluster(vectors: list[list[float]], threshold: float = 0.85) -> list[int]:
    """Single-link greedy clustering: assign each vector to the first
    existing cluster whose representative (first member) it is within
    `threshold` cosine similarity of, else start a new cluster. Returns a
    cluster-id per input vector, in order."""
    reps: list[list[float]] = []
    labels: list[int] = []
    for v in vectors:
        assigned = None
        for i, rep in enumerate(reps):
            if cosine(v, rep) >= threshold:
                assigned = i
                break
        if assigned is None:
            reps.append(v)
            assigned = len(reps) - 1
        labels.append(assigned)
    return labels


def semantic_entropy(labels: list[int]) -> float:
    n = len(labels)
    if n == 0:
        return 0.0
    counts: dict[int, int] = {}
    for l in labels:
        counts[l] = counts.get(l, 0) + 1
    h = 0.0
    for c in counts.values():
        p = c / n
        h -= p * math.log2(p)
    return h


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--sample-temperature", type=float, default=0.7)
    parser.add_argument("--cluster-threshold", type=float, default=0.85)
    parser.add_argument("--cap-usd", type=float, default=0.08)
    parser.add_argument("--total-cap-usd", type=float, default=0.08)
    parser.add_argument("--cap-scope", default="sem-entropy-calib-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/raw-provenance-fresh-v1-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/semantic-entropy-sufficiency-calibration-v1/calibration.json"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    ground_truth = json.loads(RAWPROV_RESULTS.read_text(encoding="utf-8"))
    known_units = {
        r["question_id"]: {
            "question_type": r["question_type"],
            "compact_sufficient": bool(r["arms"]["mem0_compact"]["correct"]),
        }
        for r in ground_truth["results"]
    }
    qids = list(known_units.keys())
    assert len(qids) == 8, f"expected 8 known units, found {len(qids)}"

    with CORPUS.open(encoding="utf-8") as fh:
        corpus = {row["question_id"]: row for row in json.load(fh) if row["question_id"] in qids}
    assert len(corpus) == 8

    from arena.spend_ledger import SpendLedger, TotalCapReached
    from arena.decoding import SpendCapReached
    from arena.run_pilot import build_mem0, load_key

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))

    total_calls = len(qids) * args.samples
    print("=== COST GATE (before first paid call) ===")
    print("RESEARCH_QUESTION: does black-box semantic entropy (sample-and-cluster over "
          "M generations, local-embedding-only) separate known compact-sufficient from "
          "known compact-insufficient units, at all -- a precondition calibration for "
          "the ResearchOS-proposed compact-vs-raw sufficiency gate (rmc-2026-08-24-001, "
          "arr-2026-08-24-001, GAP-005)")
    print("WHY_THIS_CALL_IS_NEEDED: RAW_PROVENANCE dependency now resolved (Entry H "
          "REPLICATED_VALIDATED_TRANSPLANT); the specific transfer this signal needs "
          "(single-turn retrieve-or-not -> persistent-memory compact-vs-raw escalation) "
          "is untested anywhere per the candidate's own admission; this is the cheapest "
          "possible check before designing a real causal test")
    print("EXPECTED_INFORMATION_GAIN: does entropy separate the 2 known groups at all "
          "(TEST/DON'T-TEST for a future causal gate experiment) -- NOT evidence of "
          "mechanism efficacy, a precondition/signal-quality check only")
    print("CHEAPEST_ALTERNATIVE: none -- this already reuses already-persisted, "
          "already-labeled data and free local embeddings; the only cost is sampling "
          "the reader M times instead of once")
    print(f"PROJECTED_CALLS: {total_calls} reader calls ({args.samples} samples x "
          f"{len(qids)} units), 0 ingest, 0 judge")
    print(f"STAGE_CAP: ${args.total_cap_usd:.2f}")
    if args.project_only:
        return 0

    run_id = f"{args.cap_scope}run"
    assert run_id.startswith(args.cap_scope)
    ledger = SpendLedger(total_cap_usd=args.total_cap_usd, run_id=run_id,
                         cap_scope=args.cap_scope)
    before_scope = ledger.scoped_usd()
    print(f"GLOBAL_SPEND_SO_FAR (this scope): ${before_scope:.6f}")
    print(f"GLOBAL_REMAINING (this scope cap): ${args.total_cap_usd - before_scope:.6f}")
    print("=== END COST GATE -- proceeding ===\n")

    built = build_mem0(args, ledger)
    adapter = built["adapter"]
    memory = adapter._memory

    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(str(Path(args.embedding_model_path).resolve()), device="cpu")

    from openai import OpenAI
    from arena.decoding import FixedDecoding
    from arena.fixed_reader import READER_PROMPT, READER_PARAMS, user_message

    # Same brotli/httpx2 decoder fix carried forward from Mechanism J.
    client = FixedDecoding(OpenAI(api_key=load_key(), base_url="https://api.deepseek.com/v1",
                                  default_headers={"Accept-Encoding": "gzip, deflate"}),
                           fixed={"temperature": args.sample_temperature},
                           spend_cap_usd=None, shared_ledger=ledger)

    results = []
    stopped = None
    try:
        for qid in qids:
            row = corpus[qid]
            bank = f"rawprov-{qid}"
            adapter._bank = bank
            stored = adapter.stored_count()
            assert stored > 0, f"{bank}: expected an already-ingested store, found {stored} items"

            top10 = _results(memory.search(query=row["question"], user_id=bank, limit=10))
            context = [str(r.get("memory", "")).strip() for r in top10 if str(r.get("memory", "")).strip()]

            msg = user_message(row["question"], context)
            samples = []
            for _ in range(args.samples):
                resp = client.chat.completions.create(
                    model=args.model,
                    messages=[{"role": "system", "content": READER_PROMPT},
                              {"role": "user", "content": msg}],
                    max_tokens=READER_PARAMS["max_tokens"])
                samples.append((resp.choices[0].message.content or "").strip())

            vectors = embedder.encode(samples, show_progress_bar=False).tolist()
            labels = greedy_cluster(vectors, threshold=args.cluster_threshold)
            entropy = semantic_entropy(labels)

            known = known_units[qid]
            results.append({
                "question_id": qid, "question_type": known["question_type"],
                "question": row["question"], "compact_sufficient_known": known["compact_sufficient"],
                "context_n": len(context), "samples": samples, "cluster_labels": labels,
                "n_clusters": len(set(labels)), "semantic_entropy": entropy,
            })
            print(f"{qid:12s} known_sufficient={known['compact_sufficient']!s:5s}  "
                  f"n_clusters={len(set(labels))}/{args.samples}  entropy={entropy:.3f}  "
                  f"cumulative ${ledger.scoped_usd():.6f}")
    except (SpendCapReached, TotalCapReached) as stop:
        stopped = str(stop)
        print(f"STOPPED BY CAP: {stopped}")

    after_scope = ledger.scoped_usd()
    total_spend = round(after_scope - before_scope, 6)

    sufficient = [r["semantic_entropy"] for r in results if r["compact_sufficient_known"]]
    insufficient = [r["semantic_entropy"] for r in results if not r["compact_sufficient_known"]]
    mean_sufficient = sum(sufficient) / len(sufficient) if sufficient else None
    mean_insufficient = sum(insufficient) / len(insufficient) if insufficient else None

    record = {
        "artifact": "arena-semantic-entropy-sufficiency-calibration-v1",
        "preregistration": "PM-20260825-41d5d71e",
        "responds_to": ["rmc-2026-08-24-001", "arr-2026-08-24-001"],
        "method": ("M generations at temperature>0 per unit, embedded with the local "
                  "MiniLM checkpoint Mem0 itself uses, greedy cosine clustering, "
                  "entropy over cluster-size proportions. Not Kuhn et al.'s full "
                  "bidirectional-NLI-entailment method -- an embedding-similarity "
                  "approximation, as the candidate itself proposed."),
        "samples_per_unit": args.samples, "sample_temperature": args.sample_temperature,
        "cluster_threshold": args.cluster_threshold,
        "results": results,
        "summary": {
            "n_known_sufficient": len(sufficient), "n_known_insufficient": len(insufficient),
            "mean_entropy_sufficient": mean_sufficient, "mean_entropy_insufficient": mean_insufficient,
            "separation": (None if mean_sufficient is None or mean_insufficient is None
                          else round(mean_insufficient - mean_sufficient, 4)),
        },
        "stopped_by_cap": stopped,
        "spend": {"total_usd": total_spend, "cap_usd": args.total_cap_usd,
                  "remaining_usd": round(args.total_cap_usd - total_spend, 6)},
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"\nran {len(results)}/8 units, total spend ${total_spend:.6f} against cap ${args.total_cap_usd:.2f}")
    if mean_sufficient is not None and mean_insufficient is not None:
        print(f"mean entropy: sufficient={mean_sufficient:.3f}  insufficient={mean_insufficient:.3f}  "
              f"separation={mean_insufficient - mean_sufficient:+.3f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
