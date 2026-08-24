#!/usr/bin/env python3
"""The fixed-reader comparison, and where each probe actually failed.

Arithmetic over frozen artefacts. No provider call.

The decomposition is the point. "Mem0 scored x and Hindsight scored y" says
nothing about why, and the arena was built to separate *never retrieved* from
*retrieved and misused*. With one reader over both contexts plus a memoryless
baseline, each probe falls into classes that name its failure:

    RETRIEVAL_FAILURE          the gold session never reached the context
    RETRIEVED_READER_WRONG     it did, and the answer was still wrong
    MEMORY_ASSISTED_SUCCESS    the baseline failed and memory carried it
    MEMORY_INTERFERENCE        the baseline succeeded and memory broke it
    BOTH_MEMORY_ARMS_CORRECT   / BOTH_MEMORY_ARMS_WRONG
    UNKNOWN                    not decidable from what was measured

`UNKNOWN` is used rather than the nearest plausible label. A probe whose
retrieval is unobservable, or whose arm never ran, cannot be attributed.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARENA = ROOT / "data/lab/arena"
ARMS = ("mem0", "hindsight", "baseline")
UNKNOWN = "UNKNOWN"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def classify(probe: dict[str, Any]) -> list[str]:
    """Every class this probe belongs to. Never guesses past the measurement."""
    out: list[str] = []
    mem0, hind, base = (probe["arms"].get(arm, {}) for arm in ARMS)
    memory_arms = [arm for arm in (mem0, hind) if isinstance(arm.get("correct"), bool)]
    if not memory_arms:
        return [UNKNOWN]

    for arm, name in ((mem0, "mem0"), (hind, "hindsight")):
        if not isinstance(arm.get("correct"), bool):
            continue
        gold = arm.get("gold_in_context")
        if gold is False:
            out.append(f"RETRIEVAL_FAILURE:{name}")
        elif gold is True and arm["correct"] is False:
            out.append(f"RETRIEVED_READER_WRONG:{name}")
        elif gold is not True:
            out.append(f"UNKNOWN:{name}")

    correct = [arm["correct"] for arm in memory_arms]
    if all(correct):
        out.append("BOTH_MEMORY_ARMS_CORRECT")
    elif not any(correct):
        out.append("BOTH_MEMORY_ARMS_WRONG")

    if isinstance(base.get("correct"), bool):
        if base["correct"] is False and any(correct):
            out.append("MEMORY_ASSISTED_SUCCESS")
        if base["correct"] is True and not any(correct):
            out.append("MEMORY_INTERFERENCE")
    else:
        out.append("UNKNOWN:baseline")
    return out or [UNKNOWN]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", default=str(ARENA / "expansion-selection.json"))
    parser.add_argument("--judged", default=str(ARENA / "fixed-reader-judged.json"))
    parser.add_argument("--blinding", default=str(ARENA / "fixed-reader-judge-blinding.json"))
    parser.add_argument("--reader", default=str(ARENA / "fixed-reader.json"))
    parser.add_argument("--metrics", default=str(ARENA / "rerun-{system}.json"))
    parser.add_argument("--out", default=str(ARENA / "fixed-reader-report.json"))
    args = parser.parse_args()

    selection = load(Path(args.selection))
    units = {u["question_id"]: u for u in selection["units"]}
    reader = load(Path(args.reader)) or {}
    judged, blinding = load(Path(args.judged)), load(Path(args.blinding))
    if judged is None or blinding is None:
        raise SystemExit("no judged fixed-reader artefact yet")
    reverse = {label: arm for arm, label in blinding["mapping"].items()}

    labels: dict[tuple[str, str], bool] = {}
    for entry in judged["judgements"]:
        arm = reverse.get(entry["candidate"], entry["candidate"])
        labels[(arm, entry["question_id"])] = entry["label"]

    retrieval: dict[tuple[str, str], dict[str, Any]] = {}
    context: dict[tuple[str, str], dict[str, Any]] = {}
    for system in ("mem0", "hindsight"):
        record = load(Path(args.metrics.replace("{system}", system)))
        for unit in (record or {}).get("units", []):
            if unit.get("status") != "complete":
                continue
            retrieval[(system, unit["question_id"])] = unit.get("retrieval") or {}
            context[(system, unit["question_id"])] = unit.get("memory") or {}

    probes: list[dict[str, Any]] = []
    per_type: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for qid, unit in units.items():
        entry: dict[str, Any] = {"question_id": qid, "slot": unit["slot"],
                                 "type": unit["question_type"], "arms": {}}
        for arm in ARMS:
            correct = labels.get((arm, qid))
            cell: dict[str, Any] = {"correct": correct if correct is not None else UNKNOWN}
            if arm in ("mem0", "hindsight"):
                found = retrieval.get((arm, qid), {})
                delivered = context.get((arm, qid), {})
                cell |= {
                    "gold_in_context": found.get("gold_in_context", UNKNOWN),
                    "gold_rank": found.get("gold_rank", UNKNOWN),
                    "precision_at_k": found.get("precision_at_k", UNKNOWN),
                    "context_tokens": delivered.get("context_tokens", UNKNOWN),
                    "evidence": delivered.get("evidence_ids", UNKNOWN),
                }
            entry["arms"][arm] = cell
            if isinstance(correct, bool):
                per_type[unit["question_type"]][arm].append(correct)
        entry["classes"] = classify(entry)
        probes.append(entry)

    def numbers(cells: list[dict[str, Any]], key: str) -> list[float]:
        return [c[key] for c in cells if isinstance(c.get(key), (int, float))]

    def total(arm: str) -> dict[str, Any]:
        cells = [p["arms"][arm] for p in probes
                 if isinstance(p["arms"][arm].get("correct"), bool)]
        correct = sum(1 for c in cells if c["correct"])
        observable = [c for c in cells if isinstance(c.get("gold_in_context"), bool)]
        found = [c for c in observable if c["gold_in_context"]]
        ranks = numbers(found, "gold_rank")
        precision = numbers(cells, "precision_at_k")
        tokens = numbers(cells, "context_tokens")
        return {
            "correct": f"{correct}/{len(cells)}" if cells else UNKNOWN,
            "accuracy": round(correct / len(cells), 3) if cells else UNKNOWN,
            "gold_in_context": f"{len(found)}/{len(observable)}" if observable else UNKNOWN,
            "mean_gold_rank": round(sum(ranks) / len(ranks), 2) if ranks else UNKNOWN,
            "mean_precision_at_k": (round(sum(precision) / len(precision), 3)
                                    if precision else UNKNOWN),
            "mean_context_tokens": (round(sum(tokens) / len(tokens), 1)
                                    if tokens else UNKNOWN),
        }

    counts: dict[str, int] = defaultdict(int)
    for probe in probes:
        for name in probe["classes"]:
            counts[name] += 1

    report = {
        "artifact": "arena-fixed-reader-report",
        "selection": selection["selection_sha256"],
        "reader": reader.get("reader"),
        "cost_usd": {"reader": (reader.get("cost") or {}).get("usd"),
                     "judging": (judged.get("cost") or {}).get("usd")},
        "judge_stability": {
            "answers": len(judged["judgements"]),
            "stable": sum(1 for e in judged["judgements"] if e["stable"]),
            "disputed": sum(1 for e in judged["judgements"] if e["disputed"]),
        },
        "totals": {arm: total(arm) for arm in ARMS},
        "per_type": {t: {"n": max(len(v[a]) for a in ARMS)}
                     | {a: (f"{sum(v[a])}/{len(v[a])}" if v[a] else UNKNOWN) for a in ARMS}
                     for t, v in sorted(per_type.items())},
        "failure_decomposition": dict(sorted(counts.items())),
        "per_probe": probes,
        "is_a_leaderboard": False,
        "caveat": ("ten units, one reader generation per context, a binary judge and a "
                   "confirmatory sample. Any single output that carries a conclusion is "
                   "marked as needing replication rather than treated as a rate"),
    }
    Path(args.out).write_text(json.dumps(report, indent=2, default=str) + "\n",
                              encoding="utf-8")

    head = (f"{'arm':11s} | {'correct':8s} | {'gold-in-ctx':11s} | {'rank':>5s} | "
            f"{'p@k':>6s} | {'ctx tok':>8s}")
    print(head)
    print("-" * len(head))
    for arm in ARMS:
        entry = report["totals"][arm]
        print(f"{arm:11s} | {str(entry['correct']):8s} | "
              f"{str(entry['gold_in_context']):11s} | {str(entry['mean_gold_rank']):>5s} | "
              f"{str(entry['mean_precision_at_k']):>6s} | "
              f"{str(entry['mean_context_tokens']):>8s}")

    print(f"\n{'type':22s} | {'n':>2s} | {'Mem0':>7s} | {'Hind':>7s} | {'base':>7s}")
    for qtype, row in report["per_type"].items():
        print(f"{qtype:22s} | {row['n']:>2d} | {row['mem0']:>7s} | "
              f"{row['hindsight']:>7s} | {row['baseline']:>7s}")

    print("\nfailure decomposition")
    for name, count in report["failure_decomposition"].items():
        print(f"  {name:34s} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
