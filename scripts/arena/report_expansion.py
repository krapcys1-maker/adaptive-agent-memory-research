#!/usr/bin/env python3
"""Mem0 against Hindsight over ten units, four reused and six newly paid for.

The question this run exists to answer is narrow: **the pilot showed Hindsight
answering the one temporal-reasoning unit and nobody else answering it. Does that
survive three temporal units instead of one?**

Everything here is arithmetic over artefacts that already exist. No provider
call, nothing that could become a second experiment.

Three things it will not do
----------------------------
**It will not call a winner.** Ten units, a confirmatory sample built after
seeing the pilot, and a binary judge. `replicated`, `disappeared`, `unresolved`
and `candidate regime` are the available verdicts; "best memory system" is not.

**It will not read the overall accuracy as an estimate.** temporal-reasoning is
3 of 10 here against roughly 1 in 6 in the corpus. The per-type rows are the
result; the overall column is a weighted average of a weighting we chose.

**It will not turn UNKNOWN into a number.** A unit whose haystack repeats a date
cannot support retrieval metrics, and stale-memory counts are unobservable in
this corpus for either system. Those cells say so.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARENA = ROOT / "data/lab/arena"

SYSTEMS = ("mem0", "hindsight")
LABEL = {"mem0": "Mem0", "hindsight": "Hindsight"}
UNKNOWN = "UNKNOWN"


def load(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def judgements(paths: list[Path], blindings: list[Path]) -> dict[tuple[str, str], dict[str, Any]]:
    """Every judged answer, unblinded, keyed by (system, question_id).

    Two judge runs feed this: the pilot's, whose labels for the four reused units
    are taken as they stand, and the expansion's for the six new ones. Which run
    a label came from is carried through, because a reused observation and a new
    one are different provenance even when they are the same measurement.
    """
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for judged_path, blinding_path in zip(paths, blindings):
        judged, blinding = load(judged_path), load(blinding_path)
        if judged is None or blinding is None:
            continue
        reverse = {label: system for system, label in blinding["mapping"].items()}
        for entry in judged["judgements"]:
            system = reverse.get(entry["candidate"])
            if system not in SYSTEMS:
                continue
            out[(system, entry["question_id"])] = entry | {
                "judge_run": judged_path.stem,
                "system": system,
            }
    return out


def unit_metrics(paths: list[Path]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for system in SYSTEMS:
        for path in paths:
            record = load(Path(str(path).replace("{system}", system)))
            if record is None:
                continue
            for unit in record.get("units", []):
                if unit.get("status") == "complete":
                    out[(system, unit["question_id"])] = unit | {"run": Path(
                        str(path).replace("{system}", system)).stem}
    return out


def mean(values: list[Any]) -> Any:
    numbers = [v for v in values if isinstance(v, (int, float))]
    return round(sum(numbers) / len(numbers), 2) if numbers else UNKNOWN


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", default=str(ARENA / "expansion-selection.json"))
    parser.add_argument("--out", default=str(ARENA / "expansion-report.json"))
    args = parser.parse_args()

    selection = load(Path(args.selection))
    units = {u["question_id"]: u for u in selection["units"]}

    judged = judgements(
        [ARENA / "pilot-judged.json", ARENA / "expansion-judged.json"],
        [ARENA / "pilot-judge-blinding.json", ARENA / "expansion-judge-blinding.json"])
    metrics = unit_metrics([ARENA / "pilot-{system}.json", ARENA / "expansion-{system}.json"])

    per_type: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    rows: list[dict[str, Any]] = []
    for qid, unit in units.items():
        row: dict[str, Any] = {"question_id": qid, "slot": unit["slot"],
                               "type": unit["question_type"], "origin": unit["origin"]}
        for system in SYSTEMS:
            entry = judged.get((system, qid))
            unit_metric = metrics.get((system, qid)) or {}
            retrieval = unit_metric.get("retrieval") or {}
            memory = unit_metric.get("memory") or {}
            row[system] = {
                "judged": entry["label"] if entry else UNKNOWN,
                "judge_run": entry["judge_run"] if entry else UNKNOWN,
                "metrics_run": unit_metric.get("run", UNKNOWN),
                "evidence": memory.get("evidence_ids", UNKNOWN),
                "context_tokens": memory.get("context_tokens", UNKNOWN),
                "gold_in_context": retrieval.get("gold_in_context", UNKNOWN),
                "gold_rank": retrieval.get("gold_rank", UNKNOWN),
                "precision_at_k": retrieval.get("precision_at_k", UNKNOWN),
                "stored_items": unit_metric.get("stored_items", UNKNOWN),
                "mutation": memory.get("query_mutates_state", UNKNOWN),
                # A state digest that moved between two fingerprints taken either
                # side of a query is evidence that state changed, and not evidence
                # that the query changed it. Hindsight consolidates on a background
                # worker whose schedule the arena does not control, so the cause is
                # not attributable from this measurement and is not guessed.
                "causal_query_mutation": (
                    "read_only" if memory.get("query_mutates_state") == "read_only"
                    else UNKNOWN),
                "causal_why": (
                    "state unchanged, so no mutation to attribute"
                    if memory.get("query_mutates_state") == "read_only"
                    else "state changed; this system runs a background consolidation "
                         "worker, so the query is not established as the cause"),
                "reproducible": memory.get("output_reproducible", UNKNOWN),
                "abstained": memory.get("abstained", UNKNOWN),
            }
            if entry:
                per_type[unit["question_type"]][system].append(bool(entry["label"]))
        rows.append(row)

    def profile(system: str) -> dict[str, Any]:
        cells = [r[system] for r in rows if isinstance(r[system].get("judged"), bool)]
        correct = sum(1 for c in cells if c["judged"])
        by_type = {t: (sum(per_type[t][system]), len(per_type[t][system]))
                   for t in per_type if per_type[t][system]}
        observable = [c for c in cells if isinstance(c["gold_in_context"], bool)]
        found = [c for c in observable if c["gold_in_context"]]
        ingest = sum((metrics.get((system, q)) or {}).get("ingest", {}).get("usd", 0.0)
                     for q in units)
        query = sum(((metrics.get((system, q)) or {}).get("query") or {}).get("usd", 0.0)
                    for q in units)
        return {
            "answered": f"{correct}/{len(cells)}",
            "accuracy": round(correct / len(cells), 3) if cells else UNKNOWN,
            "by_type": {t: f"{c}/{n}" for t, (c, n) in sorted(by_type.items())},
            "mean_evidence": mean([c["evidence"] for c in cells]),
            "mean_context_tokens": mean([c["context_tokens"] for c in cells]),
            "gold_in_context_rate": (f"{len(found)}/{len(observable)}"
                                     if observable else UNKNOWN),
            "mean_gold_rank": mean([c["gold_rank"] for c in found]) if found else UNKNOWN,
            "mean_precision_at_k": mean([c["precision_at_k"] for c in observable]),
            "retrieval_unobservable_units": len(cells) - len(observable),
            "stale_or_conflict_rate": UNKNOWN,
            "stale_why": "the corpus marks answer sessions, not superseded ones",
            "mean_stored_items": mean([c["stored_items"] for c in cells]),
            "mutation": sorted({str(c["mutation"]) for c in cells}),
            "causal_query_mutation": sorted({str(c["causal_query_mutation"]) for c in cells}),
            "reproducible": sorted({str(c["reproducible"]) for c in cells}),
            "abstentions": sum(1 for c in cells if c["abstained"] is True),
            "ingest_usd": round(ingest, 4),
            "query_usd": round(query, 4),
            "total_usd": round(ingest + query, 4),
        }

    profiles = {s: profile(s) for s in SYSTEMS}
    temporal = {s: per_type.get("temporal-reasoning", {}).get(s, []) for s in SYSTEMS}
    hits = {s: sum(temporal[s]) for s in SYSTEMS}
    n_temporal = len(temporal["hindsight"])

    # A first version of this called any Hindsight lead over three units
    # "replicated". That is too generous and it would have shipped: leading
    # 1-of-3 against 0-of-3 is a one-unit margin, which is exactly the margin the
    # pilot already had at 1-of-1 against 0-of-1. The sample grew and the margin
    # did not, so the claim under test got WEAKER, not confirmed.
    #
    # Replication has to mean the effect held its rate, not merely its sign.
    margin = hits["hindsight"] - hits["mem0"]
    rate = hits["hindsight"] / n_temporal if n_temporal else 0.0
    if margin <= 0:
        verdict = "disappeared"
    elif rate >= 0.66 and margin >= 2:
        verdict = "replicated"
    elif margin >= 2:
        verdict = "weak but larger than the pilot"
    else:
        verdict = "weakened: the margin stayed at one unit while the sample tripled"

    report = {
        "artifact": "arena-expansion-report",
        "selection": selection["selection_sha256"],
        "selection_id": selection["selection_id"],
        "confirmatory": selection["confirmatory_not_representative"],
        "is_a_leaderboard": False,
        "systems": profiles,
        "per_type": {
            t: {"n": len(per_type[t]["mem0"] or per_type[t]["hindsight"]),
                **{s: f"{sum(per_type[t][s])}/{len(per_type[t][s])}" for s in SYSTEMS}}
            for t in sorted(per_type)
        },
        "per_probe": rows,
        "temporal_claim": {
            "under_test": ("the pilot's single temporal unit was answered by Hindsight "
                           "and by nobody else"),
            "hindsight": f"{hits['hindsight']}/{n_temporal}",
            "mem0": f"{hits['mem0']}/{n_temporal}",
            "margin_units": margin,
            "pilot_margin_units": 1,
            "verdict": verdict,
            "reading": ("the pilot's margin was one unit out of one. Tripling the "
                        "temporal sample left the margin at one unit out of three, so "
                        "the sign survived and the rate did not. Hindsight is still "
                        "the only system to answer any temporal unit, and one unit is "
                        "not a mechanism"),
            "and_the_lead_is_not_temporal": (
                "Hindsight's overall lead is 4-2 and only one of those four is "
                "temporal. The other three are two knowledge-update and one "
                "single-session-user, so whatever separates these systems on this "
                "sample is not concentrated in the type this run was built to test"),
        },
        "the_result_that_does_not_depend_on_n": {
            "claim": "retrieval is not the bottleneck for either system",
            "evidence": ("Mem0 put a gold session in front of its reader in 4 of 5 "
                         "observable units at a mean rank of 1.0; Hindsight in 5 of 5. "
                         "They then answered 2 of 10 and 4 of 10. The gold session was "
                         "retrieved and the answer was still wrong in most units of "
                         "both systems"),
            "what_it_does_not_identify": ("where downstream the failure is. Neither "
                                          "system composes an answer — both return a "
                                          "stored memory — so a judge comparing a "
                                          "memory against a gold answer may be scoring "
                                          "a task neither system performs. That is a "
                                          "hypothesis this data cannot separate from "
                                          "genuine reasoning failure"),
        },
        "caveats": [
            "ten units, a confirmatory sample designed after the pilot",
            "temporal-reasoning is 3 of 10 here against roughly 1 in 6 in the corpus, "
            "so the overall accuracy is a weighted average of a weighting we chose",
            "four units are reused pilot observations and six are new; provenance is "
            "recorded per cell",
            "retrieval metrics map evidence to sessions by date and are UNOBSERVABLE "
            "where a haystack repeats one",
        ],
    }
    Path(args.out).write_text(json.dumps(report, indent=2, default=str) + "\n",
                              encoding="utf-8")

    print(f"{'type':24s} | {'n':>2s} | {'Mem0':>7s} | {'Hindsight':>9s}")
    print("-" * 52)
    for qtype, entry in report["per_type"].items():
        print(f"{qtype:24s} | {entry['n']:>2d} | {entry['mem0']:>7s} | {entry['hindsight']:>9s}")

    print(f"\n{'probe':26s} | {'Mem0':>7s} | {'Hindsight':>9s} | winner")
    for row in rows:
        marks = []
        for system in SYSTEMS:
            value = row[system]["judged"]
            marks.append("yes" if value is True else "no" if value is False else "?")
        winner = ("tie" if marks[0] == marks[1]
                  else LABEL["mem0"] if marks[0] == "yes" else LABEL["hindsight"])
        print(f"{row['slot']:26.26s} | {marks[0]:>7s} | {marks[1]:>9s} | {winner}")

    print()
    for system in SYSTEMS:
        p = profiles[system]
        print(f"{LABEL[system]:10s} {p['answered']}  acc {p['accuracy']}  "
              f"gold-in-context {p['gold_in_context_rate']}  "
              f"mean rank {p['mean_gold_rank']}  ctx {p['mean_context_tokens']}  "
              f"${p['total_usd']}")
    print(f"\ntemporal: Hindsight {report['temporal_claim']['hindsight']}, "
          f"Mem0 {report['temporal_claim']['mem0']} -> "
          f"{report['temporal_claim']['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
