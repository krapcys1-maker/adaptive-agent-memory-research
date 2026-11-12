"""Deterministic analysis and report for AAMR-NIGHT-1 (data/lab/aamr-night1/PROTOCOL.md). Written before any model call.

Reads only the raw run folder; never calls a model. Decision rules are the ones frozen in the protocol.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import experience_pilot_v0 as p0
import experience_xfer_v1 as xv

FUEL = ("fillFuelTank", "cannot fill gas above the tank capacity")


def rows_of(run: Path, name):
    path = run / "sessions" / f"{name}.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]


def jread(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


# ----------------------------------------------------------------------------- per-episode measures

def valid_calls(turn):
    return [c for s in turn["steps"] for c in s.get("calls", []) if c["valid"]]


def error_events(rec):
    n = 0
    for turn in rec["turns"]:
        n += len({xv.fn(c["call"]) for c in valid_calls(turn) if c.get("error")})
    return n


def notes_shown(rec):
    return [n for t in rec["turns"] for s in t["steps"] for n in s.get("notes", [])]


def prompt_tokens(rec):
    return sum(s.get("prompt_eval_count") or 0 for t in rec["turns"] for s in t["steps"])


def eval_tokens(rec):
    return sum(s.get("eval_count") or 0 for t in rec["turns"] for s in t["steps"])


def sig_of(call):
    try:
        _, kw = xv.parse_call(call["call"])
    except Exception:
        return None
    return xv.fn(call["call"]), xv.error_key(call["result"], kw)


def fuel_turns(rec, ev):
    """Turns with the tank-capacity error: passed, fuel read after the error, refill succeeded, stale/capacity compliance."""
    out = []
    labels = ev["labels"]
    for turn in rec["turns"]:
        calls = valid_calls(turn)
        first = next((i for i, c in enumerate(calls) if c.get("error") and sig_of(c) == FUEL), None)
        if first is None:
            continue
        after = calls[first + 1:]
        level, compliance, read = None, None, False
        for c in after:
            if xv.fn(c["call"]) == "displayCarStatus" and "fuel" in c["call"] and not c.get("error"):
                read = True
                m = re.search(r'"fuelLevel":\s*([0-9.]+)', c["result"])
                level = float(m.group(1)) if m else level
            if xv.fn(c["call"]) == "fillFuelTank" and not c.get("error"):
                try:
                    _, kw = xv.parse_call(c["call"])
                    amount = float(kw.get("fuelAmount"))
                except Exception:
                    amount = None
                if level is None or amount is None:
                    compliance = "no_level_read"
                elif abs(amount - (40 - level)) < 0.051:
                    compliance = "stale_40"
                elif abs(amount - (50 - level)) < 0.051:
                    compliance = "capacity_50"
                else:
                    compliance = "other_amount"
                break
        refill = any(xv.fn(c["call"]) == "fillFuelTank" and not c.get("error") for c in after)
        idx = turn["index"]
        out.append({"turn": idx, "passed": idx < len(labels) and labels[idx] == "PASSED", "read_fuel_after": read, "refill_ok": refill,
                    "note_shown": any("fillFuelTank|" in n for s in turn["steps"] for n in s.get("notes", [])), "compliance": compliance})
    return out


def failure_class(rec, ev):
    if ev["solved"]:
        return None
    ff = ev["first_fail"]
    if ff is None or ff >= len(rec["turns"]):
        return "not_reached_or_unlabelled"
    turn = rec["turns"][ff]
    calls = [c for s in turn["steps"] for c in s.get("calls", [])]
    valid = [c for c in calls if c["valid"]]
    if rec["status"] != "completed" and ff == len(rec["turns"]) - 1:
        if rec["status"] == "context_overflow":
            return "limit_context"
        if len([s for s in turn["steps"] if "key" in s]) >= p0.MAX_STEPS:
            return "limit_steps"
    errs = [i for i, c in enumerate(valid) if c.get("error")]
    if errs:
        unresolved = any(not any(xv.fn(c2["call"]) == xv.fn(valid[i]["call"]) and not c2.get("error") for c2 in valid[i + 1:]) for i in errs)
        return "error_unresolved" if unresolved else "error_resolved_turn_still_wrong"
    if any(not c["valid"] for c in calls):
        return "invalid_call_no_env_error"
    if not valid:
        return "no_call"
    return "no_error_wrong_or_extra_action"


# ----------------------------------------------------------------------------- tables and paired tests

def by_arm(rows):
    d = defaultdict(dict)
    for r in rows:
        d[r["arm"]][r["task"]] = r
    return d


def complete_tasks(d, arms, order):
    return [t for t in order if all(t in d.get(a, {}) for a in arms)]


def arm_summary(d, arm, tasks):
    rs = [d[arm][t] for t in tasks]
    ev = [r["evaluation"] for r in rs]
    return {"tasks": len(rs), "solved": sum(e["solved"] for e in ev), "error_events": sum(error_events(r["episode"]) for r in rs),
            "error_results": sum(e["error_results"] for e in ev), "invalid_calls": sum(e["invalid_calls"] for e in ev),
            "invalid_outputs": sum(e["invalid_outputs"] for e in ev), "model_calls": sum(e["model_calls"] for e in ev),
            "prompt_tokens": sum(prompt_tokens(r["episode"]) for r in rs), "eval_tokens": sum(eval_tokens(r["episode"]) for r in rs),
            "notes_shown": sum(len(notes_shown(r["episode"])) for r in rs),
            "statuses": dict(Counter(e["status"] for e in ev))}


def paired(d, x, y, tasks):
    xs = [d[x][t]["evaluation"]["solved"] for t in tasks]
    ys = [d[y][t]["evaluation"]["solved"] for t in tasks]
    m = p0.mcnemar(xs, ys)
    gained = [t for t, a, b in zip(tasks, xs, ys) if a and not b]
    lost = [t for t, a, b in zip(tasks, xs, ys) if b and not a]
    ee_x = sum(error_events(d[x][t]["episode"]) for t in tasks)
    ee_y = sum(error_events(d[y][t]["episode"]) for t in tasks)
    return {"x": x, "y": y, "gained": len(gained), "lost": len(lost), "gained_tasks": gained, "lost_tasks": lost,
            "p_one_sided": m["p_one_sided_x_gt_y"], "p_two_sided": m["p_two_sided"], "diff": sum(xs) - sum(ys),
            "error_events_x": ee_x, "error_events_y": ee_y}


def holm(pvals: dict, alpha=0.05):
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    out, m, stop = {}, len(items), False
    for i, (k, p) in enumerate(items):
        thr = alpha / (m - i)
        rej = (not stop) and p <= thr
        if not rej:
            stop = True
        out[k] = {"p": p, "threshold": thr, "reject": rej}
    return out


def session_block(rows, order, arms_pref, ref="N"):
    d = by_arm(rows)
    arms = [a for a in arms_pref if a in d]
    tasks = complete_tasks(d, arms, order)
    table = {a: arm_summary(d, a, tasks) for a in arms}
    pairs = {a: paired(d, a, ref, tasks) for a in arms if a != ref and ref in d}
    return d, arms, tasks, table, pairs


# ----------------------------------------------------------------------------- the analysis

def fix0(d, tasks, table, pairs, cap_arm="TrO"):
    s = {a: table[a]["solved"] for a in table}
    if not all(a in s for a in ("N", "TrO", "TrP")):
        return {"verdict": "not_computable", "reason": "arms missing"}
    noise = abs(s.get("N'", s["N"]) - s["N"])
    diff = s["TrO"] - s["N"]
    p = pairs["TrO"]["p_one_sided"]
    ft = [x for t in tasks for x in fuel_turns(d[cap_arm][t]["episode"], d[cap_arm][t]["evaluation"])]
    frac = (sum(x["passed"] for x in ft) / len(ft)) if ft else None
    supported = diff >= 5 and p <= 0.05 and s["TrO"] - s["TrP"] >= 3 and frac is not None and frac >= 0.5 and diff > noise
    refuted = diff <= 2 or (frac is not None and frac < 1 / 3) or s["TrO"] - s["TrP"] <= 1
    out = {"N": s["N"], "N_prime": s.get("N'"), "noise_abs_N_prime_minus_N": noise, "TrO_minus_N": diff, "TrO_minus_TrP": s["TrO"] - s["TrP"],
           "mcnemar_TrO_vs_N_one_sided": p, "capacity_turns_in_TrO": len(ft), "capacity_turns_passed_fraction": frac,
           "verdict": "supported" if supported else ("refuted" if refuted else "intermediate")}
    if "Tr" in s:
        out["Tr_minus_N"] = s["Tr"] - s["N"]
        out["Tr_replicated"] = s["Tr"] - s["N"] >= 3
    if "TrW" in s:
        out["TrW"] = s["TrW"]
        out["TrW_close_to_TrO"] = s["TrO"] - s["TrW"] <= 1
        out["TrW_close_to_N"] = s["TrW"] - s["N"] <= 1
    return out


def fuel_table(d, tasks, arms):
    out = {}
    for a in arms:
        ft = [x for t in tasks for x in fuel_turns(d[a][t]["episode"], d[a][t]["evaluation"])]
        out[a] = {"turns": len(ft), "passed": sum(x["passed"] for x in ft), "read_fuel_after": sum(x["read_fuel_after"] for x in ft),
                  "refill_ok": sum(x["refill_ok"] for x in ft), "note_shown": sum(x["note_shown"] for x in ft),
                  "compliance": dict(Counter(x["compliance"] for x in ft if x["compliance"]))}
    return out


def failure_census(d, arm, tasks):
    c = Counter(failure_class(d[arm][t]["episode"], d[arm][t]["evaluation"]) for t in tasks)
    c.pop(None, None)
    failed = sum(c.values())
    err = c.get("error_unresolved", 0) + c.get("error_resolved_turn_still_wrong", 0)
    return {"failed": failed, "classes": dict(c), "error_adjacent": err, "error_adjacent_share": (err / failed) if failed else None}


def costs(run: Path):
    att = [json.loads(l) for l in (run / "attempts.jsonl").read_text(encoding="utf-8").split("\n") if l.strip()] if (run / "attempts.jsonl").exists() else []
    resp = [json.loads(l) for l in (run / "responses.jsonl").read_text(encoding="utf-8").split("\n") if l.strip()] if (run / "responses.jsonl").exists() else []
    fl = [json.loads(l) for l in (run / "flash_ledger.jsonl").read_text(encoding="utf-8").split("\n") if l.strip()] if (run / "flash_ledger.jsonl").exists() else []
    by_bucket = Counter(a["bucket"] for a in att)
    by_model = Counter(a["model"] for a in att)
    retries = sum(1 for a in att if a.get("attempt", 0) > 0)
    secs = defaultdict(float)
    toks = defaultdict(lambda: [0, 0])
    for r in resp:
        secs[r["model"]] += r.get("wall_seconds") or 0
        toks[r["model"]][0] += (r.get("usage") or {}).get("prompt_eval_count") or 0
        toks[r["model"]][1] += (r.get("usage") or {}).get("eval_count") or 0
    times = sorted(a["at"] for a in att)
    res = [r for r in fl if r["event"] == "reserve"]
    use = [r for r in fl if r["event"] == "usage"]
    return {"local_attempts": len(att), "local_by_bucket": dict(by_bucket), "local_by_model": dict(by_model), "local_retries": retries,
            "local_model_seconds": {k: round(v, 1) for k, v in secs.items()}, "local_tokens_prompt_eval": {k: v for k, v in toks.items()},
            "first_attempt_at": times[0] if times else None, "last_attempt_at": times[-1] if times else None,
            "flash_reserved_calls": len(res), "flash_reserved_usd": round(sum(r["usd"] for r in res), 4),
            "flash_usage_upper_usd": round(sum(r["usd_upper"] for r in use), 6), "flash_prompt_tokens": sum(r["prompt_tokens"] for r in use),
            "flash_completion_tokens": sum(r["completion_tokens"] for r in use)}


def writer_costs(run: Path):
    out = {}
    for f in sorted((run / "artifacts").glob("lessons_VC_*.json")) if (run / "artifacts").exists() else []:
        d = jread(f, {})
        out[f.stem] = _wc(d.get("rows", []))
    for dom in ("GFS", "TRAVEL"):
        m = jread(run / "artifacts" / f"memory_{dom}.json")
        if m:
            for s in ("Q", "F"):
                out[f"lessons_{dom}_{s}"] = _wc(m.get(s, {}).get("rows", []))
            out[f"lessons_{dom}_D"] = {"lessons": len(m["deterministic_lessons"]), "calls": 0, "open_problems": len(m["open_problems"])}
    return out


def _wc(rows):
    pt = sum(((r.get("usage") or {}).get("prompt_eval_count") or (r.get("usage") or {}).get("prompt_tokens") or 0) for r in rows)
    ct = sum(((r.get("usage") or {}).get("eval_count") or (r.get("usage") or {}).get("completion_tokens") or 0) for r in rows)
    return {"calls": sum(1 for r in rows if r.get("raw") is not None), "valid": sum(1 for r in rows if r.get("check", {}).get("ok")),
            "of": len(rows), "prompt_tokens": pt, "output_tokens": ct, "usd_upper": round(sum(r.get("usd_upper") or 0 for r in rows), 6)}


def analyze(run: Path, ndata: Path):
    split_vc = json.loads((p0.DATA / "split.json").read_text(encoding="utf-8"))
    state = jread(run / "state.json", {"stages": {}})
    res = {"program": "AAMR-NIGHT-1", "state": state, "done": jread(run / "DONE.json"), "stopped": jread(run / "STOPPED.json"),
           "restarts": jread(run / "restarts.json"), "costs": costs(run), "writer_costs": writer_costs(run)}
    # sA: EXP-FIX-0 plus the writer and harm arms in the same session
    rows = rows_of(run, "sA")
    if rows:
        arms_a = ["N", "N'", "Tr", "TrO", "TrP", "TrW"]
        d, arms, tasks, table, pairs = session_block(rows, split_vc["test"], arms_a)
        res["fix0"] = {"arms": arms, "tasks": len(tasks), "table": table, "paired_vs_N": pairs, "rules": fix0(d, tasks, table, pairs),
                       "fuel": fuel_table(d, tasks, arms), "census_N": failure_census(d, "N", tasks) if "N" in arms else None}
        extra = [a for a in ("TrQ", "TrF", "TrS") if a in d]
        if extra:
            allarms = arms + extra
            d2, arms2, tasks2, table2, pairs2 = session_block(rows, split_vc["test"], allarms)
            comp = {}
            for x, y in (("TrQ", "Tr"), ("TrF", "Tr"), ("TrF", "TrQ"), ("TrS", "TrO"), ("TrS", "Tr"), ("TrF", "TrW"), ("TrQ", "TrW")):
                if x in d2 and y in d2:
                    comp[f"{x}_vs_{y}"] = paired(d2, x, y, tasks2)
            res["sA_all"] = {"arms": arms2, "tasks": len(tasks2), "table": table2, "paired_vs_N": pairs2, "comparisons": comp,
                             "fuel": fuel_table(d2, tasks2, arms2)}
    res["b1"] = jread(run / "artifacts" / "b1_gate.json")
    # sC: replication on the 20 Vehicle Control training tasks
    rows = rows_of(run, "sC")
    if rows:
        d, arms, tasks, table, pairs = session_block(rows, split_vc["train"], ["N", "TrP", "TrO"])
        s = {a: table[a]["solved"] for a in arms}
        rule = None
        if all(a in s for a in ("N", "TrP", "TrO")):
            rule = ("replicated" if s["TrO"] - s["N"] >= 3 and s["TrO"] - s["TrP"] >= 2 else
                    "not_replicated" if s["TrO"] - s["N"] <= 1 else "inconclusive")
        res["sC"] = {"arms": arms, "tasks": len(tasks), "table": table, "paired_vs_N": pairs, "rule": rule,
                     "fuel": fuel_table(d, tasks, arms)}
    # census: failure census on the training tasks of two untouched domains
    rows = rows_of(run, "census")
    if rows:
        d = by_arm(rows)
        res["census"] = {}
        for dom, lo in (("GFS", 0), ("TRAVEL", 150)):
            ts = [t for t in d.get("N", {}) if lo <= xv.task_number(t) < lo + 50]
            res["census"][dom] = {"tasks": len(ts), "solved": sum(d["N"][t]["evaluation"]["solved"] for t in ts),
                                  "model_calls": sum(d["N"][t]["evaluation"]["model_calls"] for t in ts), **failure_census(d, "N", ts)}
        for dom in ("GFS", "TRAVEL"):
            m = jread(run / "artifacts" / f"memory_{dom}.json")
            if m:
                res["census"][dom]["deterministic_lessons"] = len(m["deterministic_lessons"])
                res["census"][dom]["signatures"] = len(m["signatures"])
                res["census"][dom]["open_problems"] = len(m["open_problems"])
                res["census"][dom]["a_plus_rows"] = len(m["a_plus"])
    # sD: transfer to untouched test tasks (confirmatory family)
    rows = rows_of(run, "sD")
    if rows:
        plan = jread(run / "artifacts" / "sD_plan.json", {})
        order = plan.get("tasks") or sorted({r["task"] for r in rows}, key=xv.task_number)
        d, arms, tasks, table, pairs = session_block(rows, order, ["N", "N'", "TrD", "TrQ", "TrF", "R+"])
        noise = abs(table["N'"]["solved"] - table["N"]["solved"]) if "N'" in table and "N" in table else None
        primary = None
        if "TrD" in pairs:
            pr = pairs["TrD"]
            primary = {"TrD_minus_N": pr["diff"], "p_one_sided": pr["p_one_sided"], "noise": noise,
                       "confirmed": pr["p_one_sided"] <= 0.05 and (noise is None or pr["diff"] > noise)}
        fam = holm({a: pairs[a]["p_one_sided"] for a in ("TrD", "TrQ", "TrF", "R+") if a in pairs})
        comp = {}
        for x, y in (("TrF", "TrD"), ("TrQ", "TrD"), ("TrF", "TrQ"), ("R+", "TrD")):
            if x in d and y in d:
                comp[f"{x}_vs_{y}"] = paired(d, x, y, tasks)
        per_dom = {}
        for dom, lo in (("GFS", 0), ("TRAVEL", 150)):
            ts = [t for t in tasks if lo <= xv.task_number(t) < lo + 50]
            per_dom[dom] = {a: sum(d[a][t]["evaluation"]["solved"] for t in ts) for a in arms}
            per_dom[dom]["tasks"] = len(ts)
        res["sD"] = {"arms": arms, "tasks": len(tasks), "table": table, "paired_vs_N": pairs, "primary": primary, "holm_family": fam,
                     "comparisons": comp, "per_domain": per_dom, "plan": {k: plan.get(k) for k in ("arms", "dropped_for_budget", "per_episode")},
                     "census_N": failure_census(d, "N", tasks) if "N" in arms else None}
    # sE: second model
    rows = rows_of(run, "sE")
    if rows:
        d, arms, tasks, table, pairs = session_block(rows, split_vc["test"], ["N", "N'", "Tr", "TrO", "TrP"])
        res["sE"] = {"arms": arms, "tasks": len(tasks), "table": table, "paired_vs_N": pairs, "rules": fix0(d, tasks, table, pairs),
                     "fuel": fuel_table(d, tasks, arms), "census_N": failure_census(d, "N", tasks) if "N" in arms else None}
    res["errors_log_lines"] = (run / "errors.log").read_text(encoding="utf-8").count("\n") if (run / "errors.log").exists() else 0
    (ndata / "results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return res


# ----------------------------------------------------------------------------- report

def _tbl(table, cols=("tasks", "solved", "error_events", "error_results", "invalid_calls", "model_calls", "prompt_tokens", "notes_shown")):
    head = "| Ramię | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols) + "\n"
    return head + "".join(f"| {a} | " + " | ".join(str(v.get(c)) for c in cols) + " |\n" for a, v in table.items())


def _pairs(pairs):
    out = "| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne | zdarzenia błędu (x vs y) |\n|---|---|---|---|---|---|---|\n"
    for k, v in pairs.items():
        out += f"| {v['x']} vs {v['y']} | {v['gained']} | {v['lost']} | {v['diff']:+d} | {v['p_one_sided']:.3f} | {v['p_two_sided']:.3f} | {v['error_events_x']} vs {v['error_events_y']} |\n"
    return out


def write_report(res, ndata: Path, run: Path):
    L = ["# AAMR-NIGHT-1: raport wygenerowany automatycznie", "",
         "Raport powstał deterministycznie z zamrożonych surowych danych (`raw-freeze.json`), według reguł z `PROTOCOL.md`. "
         "Interpretacja i rekomendacja są w osobnym pliku `WNIOSKI.md` (jeśli powstał).", ""]
    st = res.get("state", {}).get("stages", {})
    L += ["## Stan programu", "", "| Etap | Status | Uwagi |", "|---|---|---|"]
    for k, v in st.items():
        L.append(f"| {k} | {v.get('status') or ('w toku (ten raport)' if k == 'final' else None)} | {str(v.get('reason') or '')[:120]} |")
    if res.get("stopped"):
        L += ["", f"**Program zatrzymany:** {res['stopped'].get('reason')}"]
    c = res["costs"]
    L += ["", "## Koszty", "", f"- Lokalne wywołania (próby): {c['local_attempts']} (w tym ponowienia {c['local_retries']}); wg budżetu: {c['local_by_bucket']}; wg modelu: {c['local_by_model']}.",
          f"- Czas modeli lokalnych (s): {c['local_model_seconds']}; okno: {c['first_attempt_at']} – {c['last_attempt_at']}.",
          f"- DeepSeek Flash: {c['flash_reserved_calls']} wywołań, rezerwacja {c['flash_reserved_usd']} USD, górne oszacowanie z użycia {c['flash_usage_upper_usd']} USD "
          f"({c['flash_prompt_tokens']} tokenów wejścia, {c['flash_completion_tokens']} wyjścia).",
          f"- Koszt budowy pamięci (pisarze): `{json.dumps(res.get('writer_costs'), ensure_ascii=False)}`", ""]
    if "fix0" in res:
        f = res["fix0"]
        L += ["## Etap A: EXP-FIX-0 (Vehicle Control, 30 zadań testowych, dane rozwojowe)", "", f"Zadania kompletne we wszystkich ramionach: {f['tasks']}.", "",
              _tbl(f["table"]), _pairs(f["paired_vs_N"]), "", f"**Reguły decyzji (zamrożone):** `{json.dumps(f['rules'], ensure_ascii=False)}`", "",
              "Tury z błędem pojemności baku:", "", "| Ramię | tury | zaliczone | odczyt paliwa po błędzie | udane tankowanie | notatka pokazana | zgodność kwoty |", "|---|---|---|---|---|---|---|"]
        for a, v in f["fuel"].items():
            L.append(f"| {a} | {v['turns']} | {v['passed']} | {v['read_fuel_after']} | {v['refill_ok']} | {v['note_shown']} | {v['compliance']} |")
        if f.get("census_N"):
            L += ["", f"Spis porażek N (pierwsza nieudana tura): `{json.dumps(f['census_N'], ensure_ascii=False)}`"]
        L.append("")
    if res.get("b1"):
        L += ["## Etap B: jakość lekcji na danych treningowych i bramka", "", f"`{json.dumps(res['b1'], ensure_ascii=False)}`", ""]
    if "sA_all" in res:
        s = res["sA_all"]
        L += ["## Etap B i sonda szkody: ramiona TrQ, TrF, TrS w tej samej sesji", "", f"Zadania kompletne: {s['tasks']}.", "", _tbl(s["table"]),
              _pairs(s["paired_vs_N"]), "", "Porównania bezpośrednie:", "", _pairs(s["comparisons"]), ""]
    if "sC" in res:
        s = res["sC"]
        L += ["## Replikacja na 20 zadaniach treningowych Vehicle Control", "", f"Reguła: **{s['rule']}**.", "", _tbl(s["table"]), _pairs(s["paired_vs_N"]), ""]
    if "census" in res:
        L += ["## Spis porażek w nowych domenach (zadania treningowe)", "", f"`{json.dumps(res['census'], ensure_ascii=False)}`", ""]
    if "sD" in res:
        s = res["sD"]
        L += ["## Transfer na nietknięte zadania testowe (system plików, podróże)", "", f"Zadania kompletne: {s['tasks']}. Plan: `{json.dumps(s['plan'], ensure_ascii=False)}`", "",
              _tbl(s["table"]), _pairs(s["paired_vs_N"]), "", f"**Test główny (TrD > N):** `{json.dumps(s['primary'], ensure_ascii=False)}`",
              f"Rodzina Holma: `{json.dumps(s['holm_family'], ensure_ascii=False)}`", "", "Porównania:", "", _pairs(s["comparisons"]),
              f"Wyniki per domena: `{json.dumps(s['per_domain'], ensure_ascii=False)}`", f"Spis porażek N: `{json.dumps(s.get('census_N'), ensure_ascii=False)}`", ""]
    if "sE" in res:
        s = res["sE"]
        L += ["## Drugi model: qwen3.5:9b na 30 zadaniach testowych Vehicle Control", "", _tbl(s["table"]), _pairs(s["paired_vs_N"]), "",
              f"**Reguły (jak EXP-FIX-0):** `{json.dumps(s['rules'], ensure_ascii=False)}`", ""]
    L += ["## Błędy techniczne", "", f"Linie w `errors.log`: {res.get('errors_log_lines')}. Restarty: `{json.dumps(res.get('restarts'))}`.", ""]
    (ndata / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
