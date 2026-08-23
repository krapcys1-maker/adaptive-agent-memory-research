"""Does searching by meaning fix F2, and does it create F3?

The prediction this tests, and why it is not obvious
----------------------------------------------------
`attribute_corpus_h1_failures.py` found that **10 of 13** lexical-arm failures
are `F2` — the index never surfaced the record at all — and **zero** are `F3`.
The corpus holds six services' corrections phrased near-identically, and a word
index cannot separate *billing's* correction from *vault's*.

Meaning-based search is the obvious fix for that, and this project has already
measured the reason it might not be enough. `PMLAB-STALE-E1`:

```
supersession pair cosine   mean 0.816   max 1.000
corpus baseline cosine     mean 0.372
stale version is the nearest neighbour   6 / 9
```

**A superseded fact is maximally similar to the fact that replaced it.** So a
dense retriever should find the correction the lexical one missed — and should
also rank the stale record beside it, because to an embedding they are almost
the same sentence.

The prediction is therefore specific and falsifiable:

    F2 falls sharply  ·  F3 appears where there was none  ·  gold and stale
    arrive together rather than one displacing the other

If dense retrieval simply wins, the prediction is wrong and that is worth as
much as confirming it.

Deliberately retrieval only
---------------------------
No reader, no API cost. The stage attribution shows the interesting difference
is in what reaches the prompt, and that is decidable without paying anyone to
read it. A reader run is worth buying only once this says something.

The model is `paraphrase-multilingual-MiniLM-L12-v2`, 0.22 GB, cached under
`external/models/fastembed-cache`, no network at query time.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.arms import DEFAULT_TOKEN_BUDGET, _before, _fill, supersession_rank  # noqa: E402
from run_corpus_h1_baseline import build_index, load, search  # noqa: E402

CORPUS = ROOT / "data" / "lab" / "corpus-h1"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CACHE = ROOT / "external" / "models" / "fastembed-cache"


def embed_all(texts: list[str]):
    import numpy as np
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=MODEL, cache_dir=str(CACHE), threads=4)
    matrix = np.asarray(list(model.embed(texts)), dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix


def run(corpus: Path) -> dict[str, Any]:
    import numpy as np

    events = load(corpus / "prefix-v0" / "history.jsonl")
    by_id = {e["event_id"]: e for e in events}
    queries = load(corpus / "reveal-v0" / "queries.jsonl")
    gold_of = {g["query_id"]: g for g in load(corpus / "reveal-v0" / "gold.jsonl")}

    labels = load(corpus / "prefix-v0" / "construction-labels.jsonl")
    chains = {r["event_id"]: r["event_id"].split("#")[0] for r in labels
              if {"obsolete-fact", "explicit-correction"} & set(r["properties"])}
    rank = supersession_rank(events, chains)

    order = [e["event_id"] for e in events]
    matrix = embed_all([by_id[i]["text"] for i in order])
    question_matrix = embed_all([q["question"] for q in queries])
    connection = build_index(events)

    records: list[dict[str, Any]] = []
    for index, query in enumerate(queries):
        gold = gold_of[query["query_id"]]
        day = query["asked_on_day"]

        scores = matrix @ question_matrix[index]
        dense_order = [order[i] for i in np.argsort(-scores)]
        dense = _fill(_before([by_id[i] for i in dense_order], day), DEFAULT_TOKEN_BUDGET)
        lexical = _fill(_before([by_id[i] for i in search(connection, query["question"], 60)
                                 if i in by_id], day), DEFAULT_TOKEN_BUDGET)

        record: dict[str, Any] = {"query_id": query["query_id"],
                                  "family": gold["case_id"].rsplit("-", 1)[0]}
        for name, kept in (("dense", dense), ("lexical", lexical)):
            ids = [e["event_id"] for e in kept]
            record[f"{name}_gold"] = int(gold["gold_event_id"] in ids)
            record[f"{name}_stale"] = int(any(rank.get(i, 1) > 1 for i in ids))
            record[f"{name}_both"] = int(record[f"{name}_gold"] and record[f"{name}_stale"])
            # F3 is only possible when both are present; F2 is gold absent.
            record[f"{name}_stage"] = ("F2" if not record[f"{name}_gold"]
                                       else "F3-possible" if record[f"{name}_stale"]
                                       else "clean")
        records.append(record)

    return {"records": records, "summary": summarise(records)}


def summarise(records: list[dict[str, Any]]) -> dict[str, Any]:
    families = sorted({r["family"] for r in records})

    def rate(rows: list[dict[str, Any]], field: str) -> float | None:
        return round(sum(r[field] for r in rows) / len(rows), 6) if rows else None

    obsolete = [r for r in records if r["family"] == "OBSOLETE"]
    return {
        "experiment_id": "PMLAB-H1-DENSE-E1",
        "tier": "E-exploratory",
        "authority": "retrieval only, no reader, no API cost",
        "model": MODEL,
        "network_at_query_time": False,
        "probes": len(records),
        "overall": {
            arm: {
                "gold_reached_the_context": rate(records, f"{arm}_gold"),
                "a_superseded_record_reached_it": rate(records, f"{arm}_stale"),
                "both_present": rate(records, f"{arm}_both"),
                "F2_gold_never_surfaced": round(
                    sum(1 for r in records if r[f"{arm}_stage"] == "F2") / len(records), 6),
            }
            for arm in ("lexical", "dense")
        },
        "obsolete_only": {
            arm: {
                "gold_reached_the_context": rate(obsolete, f"{arm}_gold"),
                "a_superseded_record_reached_it": rate(obsolete, f"{arm}_stale"),
                "both_present": rate(obsolete, f"{arm}_both"),
            }
            for arm in ("lexical", "dense")
        },
        "by_family_gold": {
            family: {arm: rate([r for r in records if r["family"] == family], f"{arm}_gold")
                     for arm in ("lexical", "dense")}
            for family in families
        },
        "reading": (
            "F2 is gold never surfacing. F3-possible is gold and a superseded record both "
            "present, which is the precondition for a selection failure rather than proof of "
            "one — only a reader can turn it into an F3."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--out", type=Path, default=CORPUS / "dense-probe-v0")
    arguments = parser.parse_args(argv)

    result = run(arguments.corpus if arguments.corpus.is_absolute() else ROOT / arguments.corpus)
    s = result["summary"]

    print(f"{s['experiment_id']} — retrieval only, {s['probes']} probes, no API cost\n")
    print(f"  {'':<9}{'gold in ctx':>13}{'stale in ctx':>14}{'both':>8}{'F2':>8}")
    for arm in ("lexical", "dense"):
        b = s["overall"][arm]
        print(f"  {arm:<9}{b['gold_reached_the_context']:>13.3f}"
              f"{b['a_superseded_record_reached_it']:>14.3f}{b['both_present']:>8.3f}"
              f"{b['F2_gold_never_surfaced']:>8.3f}")

    print("\n  OBSOLETE only — the family the prediction is about\n")
    print(f"  {'':<9}{'gold in ctx':>13}{'stale in ctx':>14}{'both':>8}")
    for arm in ("lexical", "dense"):
        b = s["obsolete_only"][arm]
        print(f"  {arm:<9}{b['gold_reached_the_context']:>13.3f}"
              f"{b['a_superseded_record_reached_it']:>14.3f}{b['both_present']:>8.3f}")

    print("\n  gold reaching the context, by family\n")
    print(f"  {'family':<12}{'lexical':>10}{'dense':>10}")
    for family, block in s["by_family_gold"].items():
        print(f"  {family:<12}{block['lexical']:>10.3f}{block['dense']:>10.3f}")

    out = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_bytes(
        (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(f"\nwritten: {(out / 'results.json').relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
