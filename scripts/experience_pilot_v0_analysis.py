"""EXP-PILOT-0 analysis: measures (SPEC v1 9), paired tests (10) and the pre-registered decision rules (11). No model calls."""
from __future__ import annotations

import json
from collections import Counter

import experience_pilot_v0 as xp

PAIRS_ONE_SIDED = [("R", "N"), ("S", "N")]
PAIRS_TWO_SIDED = [("P", "N"), ("S", "R"), ("R+", "R"), ("S", "R+"), ("R+", "N")]


def load_runs(stage: str):
    """All runs of a stage (completed and aborted), oldest first, as (manifest, episodes, evaluations)."""
    base = xp.WORK / "raw" / stage
    out = []
    if base.exists():
        for m in sorted(base.glob("*/manifest.json")):
            out.append((xp.read_json(m), xp.read_jsonl(m.parent / "episodes.jsonl"), xp.read_jsonl(m.parent / "evaluations.jsonl")))
    return out


def collect():
    """{(task, arm): (record, evaluation)} from the latest E2 run, the N' completion and E3; plus run bookkeeping."""
    episodes, runs = {}, []
    for stage in ("e2", "e2n", "e3"):
        stage_runs = load_runs(stage)
        for m, recs, evs in stage_runs:
            runs.append({"stage": stage, "run_id": m["run_id"], "status": m["status"], "episodes": len(evs), "error": m.get("error")})
        if stage_runs:
            m, recs, evs = stage_runs[-1]
            for r, e in zip(recs, evs):
                episodes[(e["task"], e["arm"])] = (r, e)
    return episodes, runs


def texts(record):
    return [s.get("text") for t in record["turns"] for s in t["steps"]]


def reached_and_passed(ev):
    out = []
    for i in range(ev["n_turns"]):
        reached = i < ev["turns_started"] and (i == 0 or ev["labels"][i - 1] == "PASSED")
        out.append((reached, reached and ev["labels"][i] == "PASSED"))
    return out


def layer_table(episodes, tasks, x, y, strata, exposure):
    """Paired turn table: turns reached in both arms x and y, by stratum (SPEC v1 9.3)."""
    rows = []
    for t in tasks:
        ex, ey = episodes[(t, x)][1], episodes[(t, y)][1]
        for i, ((rx, px), (ry, py)) in enumerate(zip(reached_and_passed(ex), reached_and_passed(ey))):
            if rx and ry:
                key = f"{t}:{i}"
                rows.append({"key": key, "x": px, "y": py, **strata[key], "exposure_x": exposure[key].get(x, "none")})
    table = {}
    for field, values in (("mem_layer", "ABC"), ("gt_layer", "ABC"), ("c_rule", (True,)), ("exposure_x", ("exact", "skeleton", "none", "empty")),
                          ("same_world", (True, False)), ("random_dependent", (True,))):
        for v in values:
            sub = [r for r in rows if r[field] == v]
            n = len(sub)
            table[f"{field}={v}"] = {"n": n, "x_pass": sum(r["x"] for r in sub), "y_pass": sum(r["y"] for r in sub),
                                     "x_rate": sum(r["x"] for r in sub) / n if n else None, "y_rate": sum(r["y"] for r in sub) / n if n else None,
                                     "diff_pp": 100 * (sum(r["x"] for r in sub) - sum(r["y"] for r in sub)) / n if n else None}
    return table


def main(cfg):
    split = xp.read_json(xp.DATA / "split.json")
    build = xp.read_json(xp.DATA / "build.json")
    strata = xp.read_json(xp.DATA / "strata.json")["turns"]
    exposure = xp.read_json(xp.DATA / "exposure.json")["exposure"]
    bfcl = xp.bfcl_from_config(cfg)
    episodes, runs = collect()
    test = split["test"]
    arms_present = sorted({a for _, a in episodes})
    main_arms = [a for a in ["N", "P", "R", "R+", "S", "O"] if a in arms_present]
    complete = [t for t in test if all((t, a) in episodes for a in xp.E2_ARMS)]
    incomplete = [t for t in test if t not in complete]
    # determinism (8.3)
    np_tasks = [t for t in test if (t, "N'") in episodes]
    det_diff = [t for t in np_tasks if texts(episodes[(t, "N")][0]) != texts(episodes[(t, "N'")][0])]
    full_nprime = len(np_tasks) == len(test)
    deterministic = len(det_diff) == 0
    noise = sum(1 for t in np_tasks if episodes[(t, "N")][1]["solved"] != episodes[(t, "N'")][1]["solved"]) if full_nprime else 0
    solved = {a: [bool(episodes[(t, a)][1]["solved"]) for t in complete] for a in main_arms if all((t, a) in episodes for t in complete)}
    # per arm summaries
    per_arm = {}
    for a in main_arms + (["N'"] if np_tasks else []):
        evs = [episodes[(t, a)][1] for t in test if (t, a) in episodes]
        recs = [episodes[(t, a)][0] for t in test if (t, a) in episodes]
        steps = [s for r in recs for tt in r["turns"] for s in tt["steps"] if "key" in s]
        mem_turns = [tt for r in recs for tt in r["turns"]]
        per_arm[a] = {"episodes": len(evs), "solved": sum(e["solved"] for e in evs), "state_all": sum(e["state_all"] for e in evs),
                      "mean_progress": sum(e["progress"] for e in evs) / len(evs) if evs else None,
                      "error_results": sum(e["error_results"] for e in evs), "invalid_calls": sum(e["invalid_calls"] for e in evs),
                      "invalid_outputs": sum(e["invalid_outputs"] for e in evs), "steps": sum(e["steps"] for e in evs),
                      "model_calls": sum(e["model_calls"] for e in evs), "prompt_eval_sum": sum(s.get("prompt_eval_count") or 0 for s in steps),
                      "eval_sum": sum(s.get("eval_count") or 0 for s in steps), "wall_seconds": sum(s.get("wall_seconds") or 0 for s in steps),
                      "status": dict(Counter(e["status"] for e in evs)), "checker_errors": dict(Counter(e["checker_error_type"] for e in evs if not e["solved"])),
                      "replay_mismatch": sum(e["replay_mismatch"] for e in evs),
                      "turns_started": len(mem_turns), "turns_injected": sum(bool(tt["memory"]["items"]) for tt in mem_turns),
                      "mean_block_chars": (sum(tt["memory"]["block_chars"] for tt in mem_turns) / len(mem_turns)) if mem_turns else None}
    # paired tests (10)
    pairs = {}
    for (x, y), one in [(p, True) for p in PAIRS_ONE_SIDED] + [(p, False) for p in PAIRS_TWO_SIDED] + ([(("N", "N'"), False)] if full_nprime else []):
        if x in solved and y in solved or (y == "N'" and full_nprime):
            xs = solved[x] if x in solved else None
            ys = solved[y] if y in solved else [bool(episodes[(t, "N'")][1]["solved"]) for t in complete]
            r = xp.mcnemar(xs, ys)
            r["test"] = "exact McNemar, one-sided x>y" if one else "exact McNemar, two-sided"
            r["diff"] = sum(xs) - sum(ys)
            pairs[f"{x}-{y}"] = r
    # harm / help (9.2)
    base_ok = {t: episodes[(t, "N")][1]["solved"] and (episodes[(t, "N'")][1]["solved"] if full_nprime else True) for t in complete}
    base_fail = {t: (not episodes[(t, "N")][1]["solved"]) and ((not episodes[(t, "N'")][1]["solved"]) if full_nprime else True) for t in complete}
    harm = {}
    for a in [a for a in main_arms if a != "N"]:
        if a not in solved:
            continue
        cases = []
        for t in complete:
            r, e = episodes[(t, a)]
            if base_ok[t] and not e["solved"]:
                i = e["first_fail"] if e["first_fail"] is not None else max(0, e["turns_started"] - 1)
                gt_names = {c.split("(")[0] for c in bfcl.gt[t][i]} if i < len(bfcl.gt[t]) else set()
                agent = sorted({c["call"].split("(")[0] for s in r["turns"][i]["steps"] for c in s.get("calls", []) if c["valid"]}) if i < len(r["turns"]) else []
                cases.append({"task": t, "turn": i, "checker_error": e["checker_error_type"], "status": e["status"],
                              "agent_functions_not_in_gold": [f for f in agent if f not in gt_names],
                              "memory_shown": r["turns"][i]["memory"]["items"] if i < len(r["turns"]) else []})
        injected = per_arm[a]["turns_injected"]
        harm[a] = {"harm": len(cases), "help": sum(1 for t in complete if base_fail[t] and episodes[(t, a)][1]["solved"]),
                   "harm_per_100_injected_turns": 100 * len(cases) / injected if injected else None, "cases": cases}
    s_no_injection = (1 - per_arm["S"]["turns_injected"] / per_arm["S"]["turns_started"]) if "S" in per_arm and per_arm["S"]["turns_started"] else None
    # layers (9.3), paired vs N
    layers = {x: layer_table(episodes, complete, x, "N", strata, exposure) for x in ["R", "R+", "S", "P", "O"] if x in solved}
    # decision rules (11)
    d = {a: sum(solved[a]) - sum(solved["N"]) for a in solved}
    p_one = {a: pairs.get(f"{a}-N", {}).get("p_one_sided_x_gt_y") for a in ("R", "S")}
    works_arms = [a for a in ("R", "S") if a in d and d[a] >= 6 and p_one[a] is not None and p_one[a] <= 0.05 and d[a] > noise]
    works = bool(works_arms) and d.get("P", 99) <= 2
    h3 = {}
    for a in works_arms or [a for a in ("R", "S") if a in layers]:
        lb, lc = layers[a]["mem_layer=B"], layers[a]["mem_layer=C"]
        decidable = lb["n"] >= 15 and lc["n"] >= 10
        h3[a] = {"B": lb, "C": lc, "decidable": decidable,
                 "beats_N_by_10pp_in_B_and_C": decidable and lb["diff_pp"] >= 10 and lc["diff_pp"] >= 10}
    rows = []
    if works:
        rows.append("Memory works")
        if not all(h3[a]["beats_N_by_10pp_in_B_and_C"] for a in works_arms):
            rows.append("Memorisation only" + ("" if all(h3[a]["decidable"] for a in works_arms) else " (H3 undecidable in the pilot: too few M-B or M-C turns)"))
    if d.get("P", 0) >= 3:
        rows.append("Prompt effect")
    if "S" in harm and "R" in harm and harm["S"]["harm"] < harm["R"]["harm"] and sum(solved["S"]) >= sum(solved["R"]) - 1:
        rows.append("Selection helps")
    o_condition = max(d.get("R", 0), d.get("S", 0)) < 3
    if "O" in d:
        if d.get("R", 0) <= 2 and d.get("S", 0) <= 2 and d["O"] >= 6:
            rows.append("No effect, ceiling exists")
        if d.get("R", 0) <= 2 and d.get("S", 0) <= 2 and d["O"] <= 2:
            rows.append("No effect, no ceiling")
    elif o_condition:
        rows.append("(v1) O skipped" if not any(r["stage"] == "e3" for r in runs) else "O incomplete")
    if d.get("R", 0) <= -3 or d.get("S", 0) <= -3:
        rows.append("Memory harms")
    if d.get("R+", 0) >= 6 and not works:
        rows.append("(v1) R+ only")
    h4 = {"filter_R+_minus_R_harm": harm["R+"]["harm"] - harm["R"]["harm"] if "R+" in harm and "R" in harm else None,
          "gate_S_minus_R+_harm": harm["S"]["harm"] - harm["R+"]["harm"] if "S" in harm and "R+" in harm else None}
    result = {"experiment": "EXP-PILOT-0", "primary_metric": build["gates"]["primary_metric"], "test_tasks": len(test),
              "complete_tasks": len(complete), "incomplete_tasks": incomplete, "runs": runs, "ledger": xp.ledger(),
              "determinism": {"checked_tasks": np_tasks, "tasks_with_different_text": det_diff, "deterministic": deterministic,
                              "full_nprime": full_nprime, "noise_threshold": noise},
              "per_arm": per_arm, "solved_minus_N": d, "pairs": pairs, "perturbation_discordance_P_vs_N":
                  sum(1 for a, b in zip(solved.get("P", []), solved["N"]) if a != b) if "P" in solved else None,
              "harm": harm, "s_turns_without_injection": s_no_injection, "h4_decomposition": h4, "layers_vs_N": layers, "h3": h3,
              "o_condition_met": o_condition, "decision_rows": rows}
    xp.write_json(xp.DATA / "results.json", result)
    print(json.dumps({k: result[k] for k in ("complete_tasks", "solved_minus_N", "decision_rows", "determinism")}, indent=2))
    print(json.dumps({a: {k: v[k] for k in ("solved", "state_all", "mean_progress", "model_calls", "error_results", "invalid_calls")} for a, v in per_arm.items()}, indent=2))
    return result
