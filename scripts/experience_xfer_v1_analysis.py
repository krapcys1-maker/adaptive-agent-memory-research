"""EXP-XFER-1 stage S1 analysis: measures (SPEC 9), paired tests (11), gates (8.2). No model calls.

S1 is the development stage on Vehicle Control. Nothing computed here is a confirmatory result about lessons.
"""
from __future__ import annotations

import json
from collections import Counter

import experience_pilot_v0 as p0
import experience_pilot_v0_analysis as pa
import experience_xfer_v1 as xf


# ----------------------------------------------------------------------------- loading

def load_run(stage: str):
    run = xf.latest_completed(stage)
    recs = {(r["task"], r["arm"]): r for r in p0.read_jsonl(run / "episodes.jsonl")}
    evs = {(e["task"], e["arm"]): e for e in p0.read_jsonl(run / "evaluations.jsonl")}
    return run.name, recs, evs


def stage_exists(stage: str) -> bool:
    try:
        xf.latest_completed(stage)
        return True
    except RuntimeError:
        return False


def collect_base():
    """{(task, arm): (record, evaluation)} for the 30 test tasks. N and R+ come from the frozen pilot run when S1a allowed it."""
    s1a = p0.read_json(xf.XDATA / "s1a.json")
    out, sources = {}, {}
    if s1a["reuse_pilot_N_and_Rplus"]:
        recs, evs = xf.pilot_episodes()
        for arm in ("N", "R+"):
            for (t, a), r in recs.items():
                if a == arm:
                    out[(t, a)] = (r, evs[(t, a)])
            sources[arm] = "pilot e2 " + xf.PILOT_E2.name
    run, recs, evs = load_run("s1c")
    for k, r in recs.items():
        out[k] = (r, evs[k])
        sources[k[1]] = "s1c " + run
    if stage_exists("s1e"):
        run, recs, evs = load_run("s1e")
        for k, r in recs.items():
            out[k] = (r, evs[k])
            sources[k[1]] = "s1e " + run
    return out, sources


# ----------------------------------------------------------------------------- environment errors (SPEC 9.2)

def turn_errors(turn):
    """Counter: function -> number of executed calls that returned an error in this turn."""
    c = Counter()
    for s in turn["steps"]:
        for call in s.get("calls", []):
            if call["valid"] and call.get("error"):
                c[xf.fn(call["call"])] += 1
    return c


def error_measures(record, n_turns=None):
    turns = record["turns"] if n_turns is None else record["turns"][:n_turns]
    events = raw = 0
    for t in turns:
        c = turn_errors(t)
        events += len(c)
        raw += sum(c.values())
    return {"events": events, "raw": raw, "repeat": raw - events}


def sign_test(x, y):
    """Per-task values; one-sided exact sign test for x < y, ties dropped."""
    less = sum(1 for a, b in zip(x, y) if a < b)
    more = sum(1 for a, b in zip(x, y) if a > b)
    n = less + more
    return {"x_lower": less, "x_higher": more, "ties": len(x) - n, "p_one_sided_x_lt_y": p0.binom_tail_ge(less, n),
            "p_two_sided": min(1.0, 2 * min(p0.binom_tail_ge(less, n), p0.binom_tail_ge(more, n))) if n else 1.0}


def paired_errors(base, tasks, x, y):
    """M2 (events), M2s (raw), M2p (repeat) summed per task over the turns started in both arms."""
    out = {}
    per = {"events": ([], []), "raw": ([], []), "repeat": ([], [])}
    turns = 0
    for t in tasks:
        rx, ry = base[(t, x)][0], base[(t, y)][0]
        n = min(len(rx["turns"]), len(ry["turns"]))
        turns += n
        mx, my = error_measures(rx, n), error_measures(ry, n)
        for k in per:
            per[k][0].append(mx[k])
            per[k][1].append(my[k])
    for k, (a, b) in per.items():
        out[k] = {"x_sum": sum(a), "y_sum": sum(b), "ratio": (sum(a) / sum(b)) if sum(b) else None, **sign_test(a, b)}
    out["common_turns"] = turns
    return out


def first_attempts(record, tools):
    """[(turn, tool, first call errored)] for every turn in which the arm called a tool that has a lesson."""
    out = []
    for t in record["turns"]:
        seen = set()
        for s in t["steps"]:
            for call in s.get("calls", []):
                f = xf.fn(call["call"]) if call["valid"] else None
                if f in tools and f not in seen:
                    seen.add(f)
                    out.append((t["index"], f, bool(call.get("error"))))
    return out


# ----------------------------------------------------------------------------- layers, harm, lessons in use

def layer_table(base, tasks, x, y, strata):
    rows = []
    for t in tasks:
        ex, ey = base[(t, x)][1], base[(t, y)][1]
        for i, ((rx, px), (ry, py)) in enumerate(zip(pa.reached_and_passed(ex), pa.reached_and_passed(ey))):
            if rx and ry:
                rows.append({"x": px, "y": py, **strata[f"{t}:{i}"]})
    table = {}
    for field, values in (("mem_layer", "ABC"), ("gt_layer", "ABC"), ("l_turn", (True, False))):
        for v in values:
            sel = [r for r in rows if r[field] == v]
            n, xs, ys = len(sel), sum(r["x"] for r in sel), sum(r["y"] for r in sel)
            table[f"{field}={v}"] = {"n": n, "x_pass": xs, "y_pass": ys, "diff_pp": 100 * (xs - ys) / n if n else None}
    return table


def harm_cases(base, tasks, x, gt):
    cases = []
    for t in tasks:
        rx, ex = base[(t, x)]
        if base[(t, "N")][1]["solved"] and not ex["solved"]:
            ff = ex["first_fail"]
            turn = rx["turns"][ff] if ff is not None and ff < len(rx["turns"]) else None
            called = sorted({xf.fn(c["call"]) for s in turn["steps"] for c in s.get("calls", []) if c["valid"]}) if turn else []
            gold = {xf.fn(c) for c in gt[t][ff]} if turn else set()
            cases.append({"task": t, "turn": ff, "checker_error": ex["checker_error_type"], "status": ex["status"],
                          "agent_functions_not_in_gold": [f for f in called if f not in gold],
                          "memory_shown": turn["memory"]["items"] if turn else []})
    return cases


def ok_functions(turn):
    return [xf.fn(c["call"]) for s in turn["steps"] for c in s.get("calls", []) if c["valid"] and not c.get("error")]


def over_application(base, tasks, x, lessons, l_turn):
    """Turns that need no tool with a lesson, where the arm ran a fix call from a lesson that N did not run in that turn."""
    fix = {xf.fn(c) for l in lessons for c in l["fix_calls"]}
    hits, turns = [], 0
    for t in tasks:
        rx, rn = base[(t, x)][0], base[(t, "N")][0]
        for i in range(min(len(rx["turns"]), len(rn["turns"]))):
            if l_turn[f"{t}:{i}"]:
                continue
            turns += 1
            extra = (set(ok_functions(rx["turns"][i])) & fix) - set(ok_functions(rn["turns"][i]))
            if extra:
                hits.append({"task": t, "turn": i, "functions": sorted(extra)})
    return {"turns_without_lesson_tool": turns, "turns_with_unneeded_fix_call": len(hits), "cases": hits}


def lesson_usage(base, tasks, arm, lessons):
    """SPEC 9.5: one row per (turn, lesson) where the lesson was shown or its tool was called."""
    rows = []
    for t in tasks:
        rec, ev = base[(t, arm)]
        for turn in rec["turns"]:
            i = turn["index"]
            calls = [c for s in turn["steps"] for c in s.get("calls", []) if c["valid"]]
            noted = {n for s in turn["steps"] for n in s.get("notes", [])}
            for les in lessons:
                lid = xf.lesson_id(les)
                shown = lid in (turn["memory"]["items"] or []) or lid in noted
                idx = next((k for k, c in enumerate(calls) if xf.fn(c["call"]) == les["function"]), None)
                if not shown and idx is None:
                    continue
                row = {"task": t, "turn": i, "arm": arm, "lesson": lid, "shown": shown, "tool_called": idx is not None,
                       "label": ev["labels"][i] if i < len(ev["labels"]) else None}
                if idx is not None:
                    before = {xf.fn(c["call"]) for c in calls[:idx] if not c.get("error")}
                    first = calls[idx]
                    row["fix_calls_before_first_call"] = all(xf.fn(c) in before for c in les["fix_calls"])
                    row["first_call_error"] = bool(first.get("error"))
                    row["first_call_error_is_this_lesson"] = bool(first.get("error")) and xf.error_key(
                        first["result"], xf.parse_call(first["call"])[1]) == les["error_key"]
                rows.append(row)
    return rows


def cost(base, tasks, arm):
    recs = [base[(t, arm)][0] for t in tasks]
    steps = [s for r in recs for t in r["turns"] for s in t["steps"] if "key" in s]
    turns = [t for r in recs for t in r["turns"]]
    return {"model_calls": len(steps), "prompt_eval_sum": sum(s.get("prompt_eval_count") or 0 for s in steps),
            "eval_sum": sum(s.get("eval_count") or 0 for s in steps), "wall_seconds": sum(s.get("wall_seconds") or 0 for s in steps),
            "turns_started": len(turns), "mean_block_chars": sum(t["memory"]["block_chars"] for t in turns) / len(turns) if turns else 0.0,
            "status": dict(Counter(r["status"] for r in recs))}


# ----------------------------------------------------------------------------- probe (SPEC 9.3)

def probe_tables(plan):
    run, recs, evs = load_run("s1d")
    entries = {e["id"]: e for e in plan["entries"]}
    arms = sorted({a for _, a in evs})
    strata = {"all": lambda e: True, "near": lambda e: e["stratum"] == "near", "far": lambda e: e["stratum"] == "far",
              "near_exact": lambda e: e["near_exact"], "same_turn_shown": lambda e: e["same_turn_shown"]}
    per_arm, paired = {}, {}
    for a in arms:
        per_arm[a] = {}
        for name, keep in strata.items():
            rows = [evs[(i, a)] for i, e in entries.items() if keep(e)]
            got = [r for r in rows if r["reached"]]
            n = len(got)
            per_arm[a][name] = {"entries": len(rows), "reached": n,
                                "uar": sum(r["proposed"] for r in got) / n if n else None,
                                "uar_executed": sum(r["executed"] for r in got) / n if n else None,
                                "uar_state": sum(r["state_changed"] for r in got) / n if n else None,
                                "imported_argument": sum(r["imported_argument"] for r in got),
                                "invalid_outputs": sum(r["invalid_outputs"] for r in got),
                                "proposed": sum(r["proposed"] for r in got)}
        per_arm[a]["cost"] = {"model_calls": sum(r["model_calls"] for (i, x), r in evs.items() if x == a),
                              "prompt_eval_sum": sum(r["prompt_eval_sum"] for (i, x), r in evs.items() if x == a),
                              "wall_seconds": sum(r["wall_seconds"] for (i, x), r in evs.items() if x == a)}
    for a in arms:
        if a == "N":
            continue
        paired[f"{a}-N"] = {}
        for name, keep in strata.items():
            ids = [i for i, e in entries.items() if keep(e) and evs[(i, a)]["reached"] and evs[(i, "N")]["reached"]]
            m = p0.mcnemar([evs[(i, a)]["proposed"] for i in ids], [evs[(i, "N")]["proposed"] for i in ids])
            ux = sum(evs[(i, a)]["proposed"] for i in ids) / len(ids) if ids else None
            un = sum(evs[(i, "N")]["proposed"] for i in ids) / len(ids) if ids else None
            paired[f"{a}-N"][name] = {"pairs": len(ids), "uar_x": ux, "uar_N": un,
                                      "excess_pp": 100 * (ux - un) if ids else None, **m}
    return {"run_id": run, "arms": arms, "per_arm": per_arm, "paired_vs_N": paired, "counts": plan["counts"]}


# ----------------------------------------------------------------------------- main

def main(cfg=None):
    cfg = cfg or xf.load_config()
    bfcl = xf.bfcl_from_config(cfg)
    split = p0.read_json(xf.PDATA / "split.json")
    tasks = split["test"]
    lessons, lessons_sha = xf.load_lessons()
    tools = {l["function"] for l in lessons}
    pilot_strata = p0.read_json(xf.PDATA / "strata.json")["turns"]
    l_turn = p0.read_json(xf.XDATA / "strata-s1.json")["l_turn"]
    strata = {k: {"mem_layer": v["mem_layer"], "gt_layer": v["gt_layer"], "l_turn": l_turn[k]} for k, v in pilot_strata.items()}
    base, sources = collect_base()
    arms = [a for a in ("N", "R+", "Tp", "Tr", "G", "T*") if all((t, a) in base for t in tasks)]
    incomplete = sorted({a for (t, a) in base} - set(arms))

    per_arm = {}
    for a in arms:
        evs = [base[(t, a)][1] for t in tasks]
        errs = [error_measures(base[(t, a)][0]) for t in tasks]
        fa = [x for t in tasks for x in first_attempts(base[(t, a)][0], tools)]
        per_arm[a] = {"source": sources.get(a), "solved": sum(e["solved"] for e in evs), "state_all": sum(e["state_all"] for e in evs),
                      "mean_progress": sum(e["progress"] for e in evs) / len(evs),
                      "error_events": sum(e["events"] for e in errs), "error_results": sum(e["raw"] for e in errs),
                      "repeat_errors": sum(e["repeat"] for e in errs),
                      "first_attempt_turns": len(fa), "first_attempt_errors": sum(x[2] for x in fa),
                      "first_attempt_error_rate": (sum(x[2] for x in fa) / len(fa)) if fa else None,
                      "invalid_calls": sum(e["invalid_calls"] for e in evs), "invalid_outputs": sum(e["invalid_outputs"] for e in evs),
                      "replay_mismatch": sum(e["replay_mismatch"] for e in evs), "cost": cost(base, tasks, a)}

    pairs = {}
    for x, y in [(a, "N") for a in arms if a != "N"] + [(a, b) for a, b in (("Tp", "R+"), ("Tr", "Tp"), ("G", "Tp"), ("T*", "Tp")) if a in arms and b in arms]:
        sx, sy = [base[(t, x)][1]["solved"] for t in tasks], [base[(t, y)][1]["solved"] for t in tasks]
        pairs[f"{x}-{y}"] = {"solved": {**p0.mcnemar(sx, sy), "diff": sum(sx) - sum(sy)}, "errors": paired_errors(base, tasks, x, y),
                             "layers": layer_table(base, tasks, x, y, strata)}

    harm = {a: {"harm": len(c := harm_cases(base, tasks, a, bfcl.gt)),
                "help": sum(1 for t in tasks if base[(t, a)][1]["solved"] and not base[(t, "N")][1]["solved"]), "cases": c}
            for a in arms if a != "N"}
    over = {a: over_application(base, tasks, a, lessons, l_turn) for a in ("Tp", "Tr", "G") if a in arms}
    usage = [row for a in ("Tp", "Tr") if a in arms for row in lesson_usage(base, tasks, a, lessons)]
    xf.write_jsonl(xf.XDATA / "lesson-usage.jsonl", usage)
    usage_summary = {}
    for a in ("Tp", "Tr"):
        rows = [r for r in usage if r["arm"] == a and r["tool_called"]]
        usage_summary[a] = {"turns_tool_called": len(rows), "lesson_shown_before_or_at_error": sum(r["shown"] for r in rows),
                            "fix_calls_before_first_call": sum(r.get("fix_calls_before_first_call", False) for r in rows),
                            "first_call_error": sum(r.get("first_call_error", False) for r in rows)}

    probe = probe_tables(p0.read_json(xf.XDATA / "probe-plan.json")) if stage_exists("s1d") else None

    # gates (SPEC 8.2)
    n_rate, tp_rate = per_arm["N"]["first_attempt_error_rate"], per_arm.get("Tp", {}).get("first_attempt_error_rate")
    gates = {"A_channel_works": {"N_rate": n_rate, "Tp_rate": tp_rate,
                                 "pass": tp_rate is not None and n_rate is not None and tp_rate <= 0.5 * n_rate},
             "B_no_gross_harm": {"N": per_arm["N"]["solved"], "Tp": per_arm.get("Tp", {}).get("solved"),
                                 "pass": "Tp" in per_arm and per_arm["Tp"]["solved"] >= per_arm["N"]["solved"] - 2}}
    if probe:
        u = probe["per_arm"]["N"]["all"]["uar"]
        gates["C_probe_discriminates"] = {"UAR_N": u, "pass": u is not None and 0.10 <= u <= 0.90}
    if "G" in per_arm:
        gates["D_llm_writer_not_clearly_better"] = {"G": per_arm["G"]["solved"], "Tp": per_arm["Tp"]["solved"],
                                                   "pass": per_arm["G"]["solved"] <= per_arm["Tp"]["solved"] + 2}
    else:
        gates["D_llm_writer_not_clearly_better"] = {"pass": True, "note": "arm G not run"}
    gates["s2_may_start"] = all(gates[k]["pass"] for k in ("A_channel_works", "B_no_gross_harm", "D_llm_writer_not_clearly_better"))
    gates["s2_with_probe"] = bool(probe) and gates["C_probe_discriminates"]["pass"]
    gates["tstar_triggered"] = "Tp" in per_arm and per_arm["Tp"]["solved"] < per_arm["N"]["solved"] + 3

    # development readings of the secondary rules (SPEC 12.2); not confirmatory
    rules = {}
    if "Tr" in arms:
        e = pairs["Tr-N"]["errors"]
        rules["tr_helps"] = {"repeat_ratio_Tr_over_N": e["repeat"]["ratio"], "p_one_sided": e["repeat"]["p_one_sided_x_lt_y"],
                             "solved_Tr": per_arm["Tr"]["solved"], "solved_N": per_arm["N"]["solved"],
                             "met": e["repeat"]["ratio"] is not None and e["repeat"]["ratio"] <= 0.70 and e["repeat"]["p_one_sided_x_lt_y"] <= 0.05
                             and per_arm["Tr"]["solved"] >= per_arm["N"]["solved"] - 2}
        if "Tp" in arms:
            d_tr = pairs["Tr-N"]["errors"]["raw"]["y_sum"] - pairs["Tr-N"]["errors"]["raw"]["x_sum"]
            d_tp = pairs["Tp-N"]["errors"]["raw"]["y_sum"] - pairs["Tp-N"]["errors"]["raw"]["x_sum"]
            rules["tr_suffices"] = {"raw_error_drop_Tr": d_tr, "raw_error_drop_Tp": d_tp,
                                    "met": d_tp > 0 and d_tr >= 0.5 * d_tp and per_arm["Tr"]["solved"] >= per_arm["Tp"]["solved"] - 2}
    for a in ("Tp", "R+"):
        if a in arms:
            lay = pairs[f"{a}-N"]["layers"]
            rules[f"{a}_layers_vs_N"] = {k: lay[k] for k in ("mem_layer=A", "mem_layer=B", "mem_layer=C", "l_turn=True", "l_turn=False")}

    out = {"experiment": "EXP-XFER-1", "stage": "S1 (development, Vehicle Control; not confirmatory)", "test_tasks": len(tasks),
           "arms": arms, "incomplete_arms": incomplete, "sources": sources, "lessons_sha256": lessons_sha,
           "lesson_tools": sorted(tools), "ledger": xf.ledger(), "s1a": p0.read_json(xf.XDATA / "s1a.json"),
           "per_arm": per_arm, "pairs": pairs, "harm": harm, "over_application": over, "lesson_usage": usage_summary,
           "probe": probe, "gates": gates, "secondary_rules_development": rules}
    p0.write_json(xf.XDATA / "results-s1.json", out)
    brief = {"per_arm": {a: {k: per_arm[a][k] for k in ("solved", "error_events", "error_results", "repeat_errors", "first_attempt_errors",
                                                        "first_attempt_turns")} for a in arms},
             "gates": gates,
             "probe_uar": {a: probe["per_arm"][a]["all"]["uar"] for a in probe["arms"]} if probe else None}
    print(json.dumps(brief, indent=2, default=str))
    return out


if __name__ == "__main__":
    main()
