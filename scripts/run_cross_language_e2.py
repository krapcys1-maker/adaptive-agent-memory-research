"""PMLAB-XLANG-E2: does local dense retrieval remove language as a variable?

Tier E exploratory experiment. Local model, no network at query time, no API
cost. Follows `PMLAB-XLANG-E1`, which measured the collapse and tested only
model-free remedies.

What E1 established
-------------------
Across 45 paired Polish and English queries against this English memory,
Recall@10 fell from 1.000 to 0.156 with only the language changed, and 26 of 45
Polish queries returned no candidates at all. The association graph contributed
exactly 0.0000 with a confidence interval of [0, 0], because graph expansion is
seeded from lexical hits and there were no seeds. A hand-built glossary lifted
recall to 0.867 but is unweighted, cannot handle paraphrase, and covers only
vocabulary someone thought of.

What this adds
--------------
``B4_DENSE``   nearest neighbour over multilingual sentence embeddings.
``B5_HYBRID``  lexical and dense fused by reciprocal rank fusion at k=60.

The hypothesis is that a multilingual embedding places a Polish question and its
English answer near each other, so language stops being a variable rather than
being translated around it. Measured directly: "pamiec projektu" and "project
memory" sit at cosine 0.675, while "pamiec projektu" and an unrelated Polish
phrase sit at 0.177.

Model
-----
``sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2``, 0.22 GB, the
model this project already pinned and used in ``PMLAB-REUSE-CHAR-001``. Weights
are cached locally under ``external/models/fastembed-cache``.

``fastembed`` is an optional dependency and is deliberately **not** in
``requirements-dev.txt``: adding it would make CI download an inference runtime
and model weights on every run. This script skips with a clear message when it
is absent, so the test suite stays light.

The safety caveat that must travel with any dense result
--------------------------------------------------------
``PMLAB-REUSE-CHAR-001`` measured dense forbidden intrusion at 0.200 against
FTS5's 0.050 — four times worse. Semantic neighbours include things that are
similar but wrong, and the worst case is structural: **a superseded fact is
maximally similar to its replacement**. This experiment measures recall only.
A recall gain here is not a licence to adopt dense retrieval.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from tools.project_memory.memory_store import MemoryStore  # noqa: E402
from run_association_graph_e2 import MEMORY_KINDS, load_events, rrf  # noqa: E402
from run_cross_language_e1 import FIXTURE, bootstrap, expand  # noqa: E402

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CACHE = ROOT / "external" / "models" / "fastembed-cache"
BOOTSTRAP_RESAMPLES = 10000


def embed_text(event: dict[str, Any]) -> str:
    return f"{event.get('title', '')} {event.get('summary', '')}".strip()


def run(root: Path) -> dict[str, Any]:
    try:
        import numpy as np
        from fastembed import TextEmbedding
    except ImportError as error:
        raise SystemExit(
            f"fastembed is required for this experiment and is an optional dependency: {error}\n"
            "install it with: python -m pip install fastembed"
        ) from error

    store = MemoryStore(root)
    store.rebuild_index()
    active, _ = load_events(root)

    order = sorted(active)
    model = TextEmbedding(model_name=MODEL, cache_dir=str(CACHE), threads=4)
    matrix = np.asarray(list(model.embed([embed_text(active[i]) for i in order])), dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)

    pairs = json.loads((FIXTURE / "queries.json").read_text(encoding="utf-8"))["pairs"]
    glossary = json.loads((FIXTURE / "glossary.json").read_text(encoding="utf-8"))["terms"]

    records: list[dict[str, Any]] = []
    for pair in pairs:
        target = pair["id"]
        event = active.get(target)
        if event is None:
            continue
        for language, text in (("en", event.get("title", "")), ("pl", pair["pl"])):
            if not text.strip():
                continue
            lexical = [h["id_or_path"] for h in store.search(text, limit=50, kinds=MEMORY_KINDS, expand=False)]
            gloss = [
                h["id_or_path"]
                for h in store.search(expand(text, glossary), limit=50, kinds=MEMORY_KINDS, expand=False)
            ]

            vector = np.asarray(next(model.query_embed(text)), dtype=np.float32)
            vector /= np.linalg.norm(vector)
            ranked = np.argsort(-(matrix @ vector))
            dense = [order[i] for i in ranked[:50]]

            hybrid5, hybrid10 = rrf([lexical, dense], 5), rrf([lexical, dense], 10)
            records.append(
                {
                    "target": target,
                    "language": language,
                    "b1_hit@5": int(target in lexical[:5]),
                    "b1_hit@10": int(target in lexical[:10]),
                    "b3_hit@5": int(target in gloss[:5]),
                    "b3_hit@10": int(target in gloss[:10]),
                    "b4_hit@5": int(target in dense[:5]),
                    "b4_hit@10": int(target in dense[:10]),
                    "b5_hit@5": int(target in hybrid5),
                    "b5_hit@10": int(target in hybrid10),
                    "b4_rank": dense.index(target) + 1 if target in dense else None,
                }
            )

    def summarize(subset: list[dict[str, Any]]) -> dict[str, Any]:
        if not subset:
            return {"queries": 0}
        n = len(subset)
        out: dict[str, Any] = {"queries": n}
        for arm in ("b1", "b3", "b4", "b5"):
            for depth in (5, 10):
                out[f"{arm}_recall@{depth}"] = round(sum(r[f"{arm}_hit@{depth}"] for r in subset) / n, 6)
        ranks = [r["b4_rank"] for r in subset if r["b4_rank"]]
        out["dense_mean_rank_when_found"] = round(sum(ranks) / len(ranks), 3) if ranks else None
        return out

    polish = [r for r in records if r["language"] == "pl"]
    english = [r for r in records if r["language"] == "en"]

    return {
        "summary": {
            "experiment_id": "PMLAB-XLANG-E2",
            "tier": "E-exploratory",
            "authority": "development measurement only; recall only, no safety metric",
            "model": MODEL,
            "model_size_gb": 0.22,
            "network_at_query_time": False,
            "api_cost_usd": 0.0,
            "active_events": len(active),
            "english": summarize(english),
            "polish": summarize(polish),
            "polish_dense_gain@10": bootstrap(
                [(r["b1_hit@10"], r["b4_hit@10"]) for r in polish], BOOTSTRAP_RESAMPLES
            ),
            "polish_dense_over_glossary@10": bootstrap(
                [(r["b3_hit@10"], r["b4_hit@10"]) for r in polish], BOOTSTRAP_RESAMPLES
            ),
            "polish_hybrid_gain@10": bootstrap(
                [(r["b1_hit@10"], r["b5_hit@10"]) for r in polish], BOOTSTRAP_RESAMPLES
            ),
            "safety_caveat": (
                "PMLAB-REUSE-CHAR-001 measured dense forbidden intrusion at 0.200 against "
                "FTS5's 0.050. A superseded fact is maximally similar to its replacement. "
                "This run measures recall only and is not a licence to adopt dense retrieval."
            ),
        },
        "records": records,
    }


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
