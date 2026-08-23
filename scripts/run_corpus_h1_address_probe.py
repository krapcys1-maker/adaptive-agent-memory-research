"""Arm D: address the slot instead of searching for it. No model, no cost.

The hypothesis, in falsifiable form
------------------------------------
    Similarity retrieval degrades when semantically homogeneous memories differ
    primarily by identity. Explicit entity-property addressing may recover
    information inaccessible to lexical or dense retrieval under a fixed context
    budget.

The number it has to beat is **0.929** — the oracle ceiling over lexical and
dense on this corpus, at this budget, with this configuration. That is not an
absolute retrieval ceiling; it is the union of those two specific channels,
78 of 84. Exceeding it means the gain cannot be explained by choosing perfectly
between them, which is the whole point of measuring it first.

Why the six unreachable probes should yield to this
----------------------------------------------------
Twelve services each contribute three stale records and one correction, so 48
near-identical records match "which staging host, which port". Both retrievers
rank the gold in the twenties and thirties while the budget admits about twenty.
Neither misunderstands the query; the candidate space is saturated with
near-clones that differ only by *which service*.

`billing.host` is unique. Addressing it needs no similarity at all.

What is oracle here, and what is not
-------------------------------------
The **address** is oracle: the query is mapped to its slot by construction
rather than derived from text. Deriving it is issue #47 and is the expensive
part.

The **temporal resolution** is not oracle. Once the chain is open, choosing the
record in force is done by the same rule a real system would use, and it can get
it wrong.

If arm D fails even with a perfect address, the idea is refuted for the cost of
running this file.

Measure the context, not only the answer
-----------------------------------------
Addressing should also make the context smaller — a chain of three versions
instead of twenty candidates. Recall that costs 250 tokens and recall that costs
30 are not the same result, and reporting only the first would hide the more
interesting half.
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


def address_of(query_id: str) -> str:
    """The slot a probe concerns.

    Oracle: taken from the case identity rather than parsed from the question.
    One slot is one entity-and-property pair — `billing.staging_host` — so a
    change of employer would not renumber addresses.
    """
    return query_id.replace("Q-", "", 1)


def run(corpus: Path, budget: int) -> dict[str, Any]:
    events = load(corpus / "prefix-v0" / "history.jsonl")
    by_id = {e["event_id"]: e for e in events}
    queries = load(corpus / "reveal-v0" / "queries.jsonl")
    gold_of = {g["query_id"]: g for g in load(corpus / "reveal-v0" / "gold.jsonl")}

    labels = load(corpus / "prefix-v0" / "construction-labels.jsonl")
    chains = {r["event_id"]: r["event_id"].split("#")[0] for r in labels
              if {"obsolete-fact", "explicit-correction"} & set(r["properties"])}
    rank = supersession_rank(events, chains)

    # Every event grouped by the slot it belongs to. A real system derives this;
    # here it is the case identity.
    slots: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        slots.setdefault(event["event_id"].split("#")[0], []).append(event)

    connection = build_index(events)
    records: list[dict[str, Any]] = []

    for query in queries:
        gold = gold_of[query["query_id"]]
        day = query["asked_on_day"]

        # Arm D: open the slot, take its versions newest first, resolve in time.
        # No similarity is computed anywhere in this path.
        chain = _before(slots.get(address_of(query["query_id"]), []), day)
        chain.sort(key=lambda e: (-e["day"], -e["position"]))
        addressed = _fill(chain, budget)

        # Arm A for the same probe, so the token comparison is like for like.
        lexical = _fill(_before([by_id[i] for i in search(connection, query["question"], 60)
                                 if i in by_id], day), budget)

        record: dict[str, Any] = {
            "query_id": query["query_id"],
            "family": gold["case_id"].rsplit("-", 1)[0],
        }
        for name, kept in (("addressed", addressed), ("lexical", lexical)):
            ids = [e["event_id"] for e in kept]
            record[f"{name}_gold"] = int(gold["gold_event_id"] in ids)
            record[f"{name}_stale"] = int(any(rank.get(i, 1) > 1 for i in ids))
            record[f"{name}_candidates"] = len(ids)
            record[f"{name}_tokens"] = sum(len(by_id[i]["text"].split()) for i in ids)
        records.append(record)

    return {"records": records, "summary": summarise(records, budget)}


def summarise(records: list[dict[str, Any]], budget: int) -> dict[str, Any]:
    families = sorted({r["family"] for r in records})

    def mean(rows: list[dict[str, Any]], field: str) -> float | None:
        return round(sum(r[field] for r in rows) / len(rows), 6) if rows else None

    obsolete = [r for r in records if r["family"] == "OBSOLETE"]
    return {
        "experiment_id": "PMLAB-H1-ADDR-E1",
        "tier": "E-exploratory",
        "authority": "retrieval only, no model anywhere, no API cost",
        "probes": len(records),
        "token_budget": budget,
        "oracle_router_ceiling_to_beat": 0.928571,
        "ceiling_note": (
            "the union of lexical and dense on this corpus at this budget, 78 of 84. "
            "Not an absolute retrieval ceiling — a bound on any router over those two channels"
        ),
        "arms": {
            arm: {
                "gold_reached_the_context": mean(records, f"{arm}_gold"),
                "a_superseded_record_reached_it": mean(records, f"{arm}_stale"),
                "mean_candidates": mean(records, f"{arm}_candidates"),
                "mean_retrieved_tokens": mean(records, f"{arm}_tokens"),
                "gold_per_1k_retrieved_tokens": (
                    round(mean(records, f"{arm}_gold") / mean(records, f"{arm}_tokens") * 1000, 6)
                    if mean(records, f"{arm}_tokens") else None
                ),
            }
            for arm in ("lexical", "addressed")
        },
        "obsolete_only": {
            arm: {"gold": mean(obsolete, f"{arm}_gold"),
                  "stale_present": mean(obsolete, f"{arm}_stale"),
                  "tokens": mean(obsolete, f"{arm}_tokens")}
            for arm in ("lexical", "addressed")
        },
        "by_family_gold": {
            family: {arm: mean([r for r in records if r["family"] == family], f"{arm}_gold")
                     for arm in ("lexical", "addressed")}
            for family in families
        },
        "gold_recall_is_tautological": (
            "the addressed arm reaches 1.000 by construction, not by measurement: the oracle "
            "address is the case identity and the gold event belongs to that case, so opening "
            "the slot always contains it. The figure shows only that nothing blocks addressing. "
            "The informative results are the context collapse and the stale rate, which the "
            "construction does not determine"
        ),
        "what_is_oracle": (
            "the address only. Temporal resolution over the opened chain uses the same rule a "
            "real system would and can be wrong. Deriving the address from text is issue #47"
        ),
    }



def _display(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise.

    ``Path.relative_to`` raises for a path outside the repository, and this
    project has now hit that three times — a print statement is not worth
    aborting a run that already wrote its output.
    """
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--budget", type=int, default=DEFAULT_TOKEN_BUDGET)
    parser.add_argument("--out", type=Path, default=CORPUS / "address-probe-v0")
    arguments = parser.parse_args(argv)

    result = run(arguments.corpus if arguments.corpus.is_absolute() else ROOT / arguments.corpus,
                 arguments.budget)
    s = result["summary"]

    print(f"{s['experiment_id']} — no model anywhere, {s['probes']} probes\n")
    print(f"  {'arm':<11}{'gold':>8}{'stale':>8}{'candidates':>12}{'tokens':>9}{'gold/1k':>10}")
    for arm in ("lexical", "addressed"):
        b = s["arms"][arm]
        print(f"  {arm:<11}{b['gold_reached_the_context']:>8.3f}"
              f"{b['a_superseded_record_reached_it']:>8.3f}{b['mean_candidates']:>12.1f}"
              f"{b['mean_retrieved_tokens']:>9.1f}{b['gold_per_1k_retrieved_tokens']:>10.2f}")

    print(f"\n  oracle router ceiling to beat: {s['oracle_router_ceiling_to_beat']:.3f}")
    beat = s["arms"]["addressed"]["gold_reached_the_context"] > s["oracle_router_ceiling_to_beat"]
    print(f"  addressed arm {'EXCEEDS' if beat else 'does not exceed'} it")
    print("  — but its 1.000 is tautological: an oracle address is the case identity and the")
    print("    gold belongs to that case, so the slot always contains it. Read the tokens.")

    print("\n  OBSOLETE only — where both retrievers failed\n")
    print(f"  {'arm':<11}{'gold':>8}{'stale':>8}{'tokens':>9}")
    for arm in ("lexical", "addressed"):
        b = s["obsolete_only"][arm]
        print(f"  {arm:<11}{b['gold']:>8.3f}{b['stale_present']:>8.3f}{b['tokens']:>9.1f}")

    print("\n  gold reaching the context, by family\n")
    print(f"  {'family':<12}{'lexical':>10}{'addressed':>12}")
    for family, block in s["by_family_gold"].items():
        print(f"  {family:<12}{block['lexical']:>10.3f}{block['addressed']:>12.3f}")

    out = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_bytes(
        (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(f"\nwritten: {_display((out / 'results.json'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
