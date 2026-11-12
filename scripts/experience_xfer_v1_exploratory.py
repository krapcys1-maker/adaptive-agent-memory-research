"""EXP-XFER-1 stage S1: exploratory readings written AFTER the S1 results were seen. Not pre-registered, no decision input.

Usage: python scripts/experience_xfer_v1_exploratory.py
"""
from __future__ import annotations

import ast
import json

import experience_pilot_v0 as p0
import experience_xfer_v1 as xf
import experience_xfer_v1_analysis as an


def valid_calls(turn):
    return [c for s in turn["steps"] for c in s.get("calls", []) if c["valid"]]


def main():
    cfg = xf.load_config()
    bfcl = xf.bfcl_from_config(cfg)
    tasks = p0.read_json(xf.PDATA / "split.json")["test"]
    base, _ = an.collect_base()
    arms = [a for a in ("N", "R+", "Tp", "Tr", "G", "T*") if all((t, a) in base for t in tasks)]

    # 1. the unrequested releaseBrakePedal after a successful start (a silent failure: no error is returned)
    start = {}
    for a in arms:
        ok = rel = passed = 0
        for t in tasks:
            rec, ev = base[(t, a)]
            for turn in rec["turns"]:
                cs = valid_calls(turn)
                idx = [k for k, c in enumerate(cs) if xf.fn(c["call"]) == "startEngine" and not c.get("error")]
                if idx:
                    ok += 1
                    rel += any(xf.fn(c["call"]) == "releaseBrakePedal" for c in cs[idx[-1] + 1:])
                    passed += turn["index"] < len(ev["labels"]) and ev["labels"][turn["index"]] == "PASSED"
        start[a] = {"turns_with_successful_start": ok, "brake_released_afterwards": rel, "turns_passed": passed}

    # 2. tasks whose outcome differs between arms, and what changed where N first failed
    matrix = {t: {a: bool(base[(t, a)][1]["solved"]) for a in arms} for t in tasks}
    flips = {a: {"help": [t for t in tasks if matrix[t][a] and not matrix[t]["N"]],
                 "harm": [t for t in tasks if matrix[t]["N"] and not matrix[t][a]]} for a in arms if a != "N"}
    tr_help = []
    if "Tr" in arms:
        for t in flips["Tr"]["help"]:
            ff = base[(t, "N")][1]["first_fail"]
            row = {"task": t, "turn": ff}
            for a in ("N", "Tr"):
                turn = base[(t, a)][0]["turns"][ff]
                row[a] = [("ERR:" if c.get("error") else "") + xf.fn(c["call"]) for c in valid_calls(turn)]
            tr_help.append(row)
    pilot_placebo_harms = [c["task"] for c in p0.read_json(xf.PDATA / "results.json")["harm"]["P"]["cases"]]

    # 3. probe: does the arm fill in the value the user withheld?
    probe = None
    if an.stage_exists("s1d"):
        plan = {e["id"]: e for e in p0.read_json(xf.XDATA / "probe-plan.json")["entries"]}
        run = xf.latest_completed("s1d")
        recs = {(r["task"], r["arm"]): r for r in p0.read_jsonl(run / "episodes.jsonl")}
        evs = {(e["task"], e["arm"]): e for e in p0.read_jsonl(run / "evaluations.jsonl")}
        parms = sorted({a for _, a in evs})
        probe = {a: {"near_exact": [0, 0], "near_other": [0, 0], "far": [0, 0]} for a in parms}
        examples = []
        for pid, e in plan.items():
            k, task = e["probe_turn"], bfcl.probe_tasks[pid]
            seen = "\n".join(q[0]["content"] for q in task["question"][:k + 1])
            hidden = set()
            for c in bfcl.probe_gt[pid][k + 1]:
                node = ast.parse(c, mode="eval").body
                for v in [ast.literal_eval(x) for x in node.args] + [ast.literal_eval(x.value) for x in node.keywords]:
                    hidden |= {s for s in xf._scalar_values(v) if isinstance(s, str) and len(s) >= 3 and s not in seen}
            if not hidden:
                continue
            stratum = "near_exact" if e["near_exact"] else ("near_other" if e["stratum"] == "near" else "far")
            for a in parms:
                if not evs[(pid, a)]["reached"]:
                    continue
                turn = recs[(pid, a)]["turns"][k]
                proposed = {s for st in turn["steps"] for c in st.get("calls", [])
                            for s in xf._scalar_values(c["raw"].get("arguments") if isinstance(c["raw"], dict) else None) if isinstance(s, str)}
                hit = sorted(hidden & proposed)
                probe[a][stratum][0] += bool(hit)
                probe[a][stratum][1] += 1
                if a == "R+" and hit and stratum == "near_exact" and len(examples) < 5:
                    examples.append({"entry": pid, "withheld_values": sorted(hidden), "filled_by_R+": hit,
                                     "in_memory_block": [h for h in hit if h in (turn["memory"].get("block_text") or "")]})
        probe = {"withheld_value_proposed": {a: {s: {"hit": h, "n": n} for s, (h, n) in v.items()} for a, v in probe.items()},
                 "examples_R+_near_exact": examples}

    out = {"note": "Exploratory analysis added after the S1 results were seen; not a pre-registered measure or decision input.",
           "start_engine_turns": start, "task_matrix_where_arms_differ": {t: m for t, m in matrix.items() if len(set(m.values())) > 1},
           "help_and_harm_tasks": flips, "tr_help_cases_at_N_first_failed_turn": tr_help,
           "tasks_broken_by_the_pilot_placebo_block": pilot_placebo_harms, "probe": probe}
    p0.write_json(xf.XDATA / "results-s1-exploratory.json", out)
    print(json.dumps({"start_engine_turns": start, "flips": flips, "pilot_placebo_harms": pilot_placebo_harms,
                      "probe": probe["withheld_value_proposed"] if probe else None}, indent=1))


if __name__ == "__main__":
    main()
