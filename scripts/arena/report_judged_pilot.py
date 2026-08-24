#!/usr/bin/env python3
"""Unblind the judged pilot and lay the results out: quality, cost, and the gap.

Run after `judge_pilot.py`. Everything here is arithmetic over artefacts that
already exist — no provider call, no new measurement, nothing that could quietly
become a second experiment.

Three things it is careful about:

**It compares the two metrics rather than replacing one with the other.** The
substring proxy was used to decide the pilot showed a signal; if it disagrees
with the benchmark's own judge, that is a finding about the earlier number and
it is printed per answer, not averaged away.

**It does not rank.** Four units per system. `PROMOTE`/`HOLD`/`DROP` is a
spending decision that reads cost, query behaviour, context volume and
operational state together, and a system can be worth more money for having a
profile nobody else has while scoring the same as everyone else.

**Per type means n=1.** Four units, four types, one each. The per-type column is
an observation about one question and is labelled as such wherever it appears.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARENA = ROOT / "data/lab/arena"

#: From each system's own pilot artefact. Restated here only so the table can be
#: read without opening five files; the artefacts remain the source.
PILOT_COST = {"aamr": 0.0, "mem0": 0.2939, "cupmem": 1.5892, "hindsight": 1.8123}
LABEL = {"aamr": "AAMR", "mem0": "Mem0", "cupmem": "CUPMem", "hindsight": "Hindsight"}
ORDER = ("aamr", "mem0", "cupmem", "hindsight")


def substring_results() -> dict[tuple[str, str], bool | None]:
    out: dict[tuple[str, str], bool | None] = {}
    for system in ORDER:
        record = json.loads((ARENA / f"pilot-{system}.json").read_text(encoding="utf-8"))
        for unit in record.get("units", []):
            if unit.get("status") == "complete":
                out[(system, unit["question_id"])] = (unit.get("task") or {}).get(
                    "crude_substring_match")
    return out


def memory_profile() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for system in ORDER:
        record = json.loads((ARENA / f"pilot-{system}.json").read_text(encoding="utf-8"))
        units = [u for u in record.get("units", []) if u.get("status") == "complete"]
        memories = [u.get("memory") or {} for u in units]
        out[system] = {
            "query_calls": sum((u.get("query") or {}).get("model_calls", 0) or 0
                               for u in units),
            "query_usd": round(sum((u.get("query") or {}).get("usd", 0.0) for u in units), 4),
            "ingest_usd": round(sum(u["ingest"].get("usd", 0.0) for u in units), 4),
            "context_tokens": [m.get("context_tokens") for m in memories],
            "evidence_ids": [m.get("evidence_ids") for m in memories],
            "abstained": sum(1 for m in memories if m.get("abstained")),
            "mutation": sorted({str(m.get("query_mutates_state")) for m in memories}),
            "reproducible": sorted({str(m.get("output_reproducible")) for m in memories}),
            "stored_items": [u.get("stored_items") for u in units],
        }
    return out


#: The spending decision, written out rather than computed. A formula over
#: accuracy would have dropped the only system that answered the temporal unit
#: and kept the one that answered nothing, and neither is what a screen is for.
VERDICT = {
    "hindsight": {
        "verdict": "PROMOTE",
        "because": [
            "the only system that answered the temporal-reasoning unit, and the only "
            "one whose judged score exceeded its substring proxy",
            "no model call at query time, so extending it multiplies ingestion cost "
            "only and the query column stays flat",
            "delivers 3,200-3,300 context tokens against Mem0's 100: a different "
            "operating point, not a better score at the same one",
            "evidence is 159-188 ids per probe and every one traceable to something "
            "it stores",
        ],
        "against": [
            "the most expensive ingestion measured, $1.79 for four units",
            "one unit reported mutates_by_design, and the probe cannot say whether "
            "the query or their background consolidation worker caused it",
        ],
    },
    "mem0": {
        "verdict": "PROMOTE",
        "because": [
            "six times cheaper than either other model-backed system and scored the "
            "same as CUPMem",
            "cost per session is FLAT while CUPMem's more than doubles as the store "
            "fills, so it is the only system whose price at 20 units follows from "
            "its price at 4",
            "zero model calls at query time",
            "a 20-unit run projects to about $1.50",
        ],
        "against": [
            "no answer channel: its score is its top retrieved memory, so a QA metric "
            "is reading a store as though it were a reader",
            "smallest context of any system, 93-112 tokens",
        ],
    },
    "cupmem": {
        "verdict": "HOLD",
        "because": [
            "matched Mem0's score at 5.4 times the cost, and is the only system paying "
            "4-8 model calls per query on top",
            "ingestion cost grows with the store, so 20 units is not five times the "
            "four-unit figure and any projection is a floor",
            "the only system whose output was not reproducible on any unit",
        ],
        "against_dropping": [
            "it is the only system that composes an answer rather than returning a "
            "record, which is a different task and may be why an extraction metric "
            "scores it badly",
            "its premise verdict and current/historical/transition model are the "
            "mechanism this project came to compare, and none of that was measured",
        ],
    },
    "aamr": {
        "verdict": "HOLD",
        "because": [
            "0 of 4, and it stored nothing at all: 996 user turns produced zero "
            "addresses, so the retrieval half never ran",
            "as a scored competitor it is finished, which was already on the record "
            "as a registered negative",
        ],
        "against_dropping": [
            "it costs nothing and it is the arena's floor. Without it the judge's "
            "empty-response defect would not have been found",
            "a zero-cost arm on every future run is how the next metric artefact "
            "gets caught",
        ],
    },
    "graphiti": {
        "verdict": "HOLD",
        "because": ["BLOCKED on deployment; not measured on anything"],
        "against_dropping": [
            "its temporal model is why it is in this arena, and Hindsight answering "
            "the temporal unit is exactly the signal that makes a temporal-graph "
            "system worth reaching for",
            "unblocking it costs infrastructure, not benchmark spend",
        ],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judged", default=str(ARENA / "pilot-judged.json"))
    parser.add_argument("--blinding", default=str(ARENA / "pilot-judge-blinding.json"))
    parser.add_argument("--out", default=str(ARENA / "pilot-judged-report.json"))
    args = parser.parse_args()

    judged = json.loads(Path(args.judged).read_text(encoding="utf-8"))
    blinding = json.loads(Path(args.blinding).read_text(encoding="utf-8"))["mapping"]
    reverse = {label: system for system, label in blinding.items()}

    substring = substring_results()
    profile = memory_profile()

    rows: dict[str, dict[str, Any]] = {s: {"correct": 0, "total": 0, "per_probe": {}}
                                       for s in ORDER}
    disagreements: list[dict[str, Any]] = []
    for entry in judged["judgements"]:
        # Unblinded here and nowhere earlier.
        system = reverse[entry["candidate"]]
        rows[system]["total"] += 1
        rows[system]["correct"] += int(entry["label"])
        rows[system]["per_probe"][entry["question_id"]] = {
            "slot": entry["slot"], "type": entry["question_type"],
            "judge": entry["label"], "stable": entry["stable"],
            "disputed": entry["disputed"],
            "substring": substring.get((system, entry["question_id"])),
        }
        proxy = substring.get((system, entry["question_id"]))
        if proxy is not None and proxy != entry["label"]:
            disagreements.append({
                "system": system, "question_id": entry["question_id"],
                "type": entry["question_type"], "slot": entry["slot"],
                "judge": entry["label"], "substring": proxy,
                "kind": "substring false negative" if entry["label"]
                        else "substring false positive",
            })

    units = sorted({e["question_id"] for e in judged["judgements"]},
                   key=lambda q: next(e["slot"] for e in judged["judgements"]
                                      if e["question_id"] == q))
    slot_of = {e["question_id"]: (e["slot"], e["question_type"])
               for e in judged["judgements"]}

    report = {
        "artifact": "arena-pilot-judged-report",
        "selection": judged["selection"],
        "protocol": judged["protocol"],
        "judge_model": judge_model_summary(judged),
        "judge_cost_usd": judged["cost"]["usd"],
        "judge_stability": {
            "answers": len(judged["judgements"]),
            "stable_across_two_passes": sum(1 for e in judged["judgements"] if e["stable"]),
            "needed_a_third_pass": sum(1 for e in judged["judgements"] if e["disputed"]),
        },
        "is_a_leaderboard": False,
        "why_not": ("four units per system, one question per type, and a binary judge. "
                    "These are observed outcomes on a frozen sample, not estimates of "
                    "anything"),
        "systems": {
            system: {
                "judged_score": f"{rows[system]['correct']}/{rows[system]['total']}",
                "substring_score": (
                    f"{sum(1 for q in rows[system]['per_probe'].values() if q['substring'])}"
                    f"/{rows[system]['total']}"),
                "pilot_cost_usd": PILOT_COST[system],
                "usd_per_correct": (round(PILOT_COST[system] / rows[system]["correct"], 4)
                                    if rows[system]["correct"] else None),
                **profile[system],
                "per_probe": rows[system]["per_probe"],
            }
            for system in ORDER
        },
        "substring_versus_judge": {
            "disagreements": disagreements,
            "false_negatives": sum(1 for d in disagreements
                                   if d["kind"] == "substring false negative"),
            "false_positives": sum(1 for d in disagreements
                                   if d["kind"] == "substring false positive"),
        },
        "per_type_caveat": ("one question per type. A per-type column here is a single "
                           "observation, not a rate"),
        "spending_decision": VERDICT,
        "decision_basis": ("not accuracy alone. At four units accuracy separates almost "
                           "nothing, so the decision reads cost, query behaviour, "
                           "context volume, evidence behaviour, cost shape and "
                           "operational state together"),
    }
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")

    print(f"judge: {judged['protocol']['source']} @ "
          f"{judged['protocol']['commit'][:8]}, model {judged['judge_model']['model']}, "
          f"${judged['cost']['usd']:.4f}")
    print(f"stability: {report['judge_stability']['stable_across_two_passes']}/"
          f"{report['judge_stability']['answers']} stable, "
          f"{report['judge_stability']['needed_a_third_pass']} disputed\n")

    head = f"{'system':10s} | {'judged':7s} | {'substring':9s} | {'cost':8s} | {'$/correct':9s}"
    print(head)
    print("-" * len(head))
    for system in ORDER:
        entry = report["systems"][system]
        print(f"{LABEL[system]:10s} | {entry['judged_score']:7s} | "
              f"{entry['substring_score']:9s} | ${entry['pilot_cost_usd']:<7.4f} | "
              f"{('$' + format(entry['usd_per_correct'], '.4f')) if entry['usd_per_correct'] is not None else '-':>9s}")

    print(f"\n{'probe':22s} | " + " | ".join(f"{LABEL[s]:9s}" for s in ORDER))
    for qid in units:
        slot, qtype = slot_of[qid]
        marks = " | ".join(
            f"{('CORRECT' if report['systems'][s]['per_probe'][qid]['judge'] else 'wrong'):9s}"
            for s in ORDER)
        print(f"{slot + '/' + qtype:22.22s} | {marks}")

    print()
    for system, entry in VERDICT.items():
        print(f"{LABEL.get(system, system.title()):10s} {entry['verdict']}")

    print(f"\nsubstring vs judge: {report['substring_versus_judge']['false_negatives']} "
          f"false negatives, {report['substring_versus_judge']['false_positives']} "
          f"false positives")
    for entry in disagreements:
        print(f"  {LABEL[entry['system']]:10s} {entry['slot']:7s} {entry['kind']}")
    return 0


def judge_model_summary(judged: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in judged["judge_model"].items()}


if __name__ == "__main__":
    raise SystemExit(main())
