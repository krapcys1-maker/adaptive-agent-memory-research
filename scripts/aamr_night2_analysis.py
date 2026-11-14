"""Deterministic analysis and report for AAMR-NIGHT-2 (SPEC_AAMR_NIGHT2.md, PROTOCOL.md). Written before any experimental call.

Reads only the raw run folder (and NIGHT-1's frozen sessions for the drift check); never calls a model. Every decision rule is
the frozen one from the specification; resolutions of ambiguities are listed in PROTOCOL.md.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experience_pilot_v0 as p0  # noqa: E402
import experience_xfer_v1 as xv  # noqa: E402
import aamr_night1_analysis as an1  # noqa: E402

N1RUN = Path(__file__).resolve().parents[2] / "aamr-night1-2026-11-12" / "run"
DOMAINS = ("VC", "GFS", "TRAVEL")
FUEL = ("fillFuelTank", "cannot fill gas above the tank capacity")


def domain(task):
    n = int(task.rsplit("_", 1)[1])
    return "GFS" if n < 50 else "VC" if n < 100 else "TRADING" if n < 150 else "TRAVEL"


def rows_of(run: Path, name):
    return an1.rows_of(run, name)


def jread(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def solved(row):
    return bool(row["evaluation"]["solved"])


# ----------------------------------------------------------------------------- copy-caused losses (reference: tier_e/n1_04_copy_losses.py)

def _scalars(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _scalars(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _scalars(v)
    elif isinstance(value, bool) or value is None:
        return
    else:
        yield value


def _forms(v):
    if isinstance(v, (int, float)):
        out = {repr(v), str(v)}
        if float(v).is_integer():
            out |= {str(int(v)), f"{int(v)}.0"}
        return {f for f in out if f}
    s = str(v)
    return {s} if len(s) >= 2 else set()


def _present(v, text):
    if isinstance(v, (int, float)):
        return any(re.search(r"(?<![\d.])" + re.escape(f) + r"(?![\d])(?!\.\d)", text) for f in _forms(v))
    low = text.lower()
    return any(f.lower() in low for f in _forms(v))


def _calls(turn):
    return [(si, c) for si, s in enumerate(turn["steps"]) for c in s.get("calls", [])]


def _turn_values(row, i):
    turns = row["episode"]["turns"]
    seen = " ".join(str(c.get("result")) for t in turns[:i] for _, c in _calls(t))
    vals, fns = [], []
    for _, c in _calls(turns[i]):
        if c.get("valid") and c.get("call"):
            name, kw = xv.parse_call(c["call"])
            fns.append(name)
            for v in _scalars(kw):
                vals.append((name, v, seen))
        seen += " " + str(c.get("result"))
    return vals, fns


def copy_evidence(arm_row, n_row):
    """Values or functions used in the arm's first failed turn that N did not use, that are absent from the task's requests and the
    arm's earlier results, and that are present in the memory block shown at the start of that turn."""
    i = arm_row["evaluation"]["first_fail"]
    turns = arm_row["episode"]["turns"]
    if i is None or i >= len(turns):
        return i, [], []
    block = (turns[i].get("memory") or {}).get("block_text", "") or ""
    requests = " ".join(t["request"] for t in turns[:i + 1])
    n_vals, n_fns = _turn_values(n_row, i) if i < len(n_row["episode"]["turns"]) else ([], [])
    n_forms = set().union(*[_forms(v) for _, v, _ in n_vals]) if n_vals else set()
    a_vals, a_fns = _turn_values(arm_row, i)
    copied = []
    for name, v, seen in a_vals:
        if _forms(v) & n_forms or not _forms(v):
            continue
        if _present(v, requests) or _present(v, seen):
            continue
        if _present(v, block):
            copied.append(f"{name}:{v}")
    fns = [f for f in dict.fromkeys(a_fns) if f not in n_fns and f"{f}(" in block]
    return i, sorted(set(copied)), fns


# ----------------------------------------------------------------------------- divergence before/after memory (aamr_night1_followup.py)

def _steps_with_memory(rec):
    out, seen = [], False
    for t in rec["turns"]:
        if (t.get("memory") or {}).get("block_chars"):
            seen = True
        for i, s in enumerate(t["steps"]):
            if "key" not in s:
                continue
            out.append((t["index"], i, s["text"], seen))
            if s.get("notes"):
                seen = True
    return out


def divergence(a, n):
    sa, sn = _steps_with_memory(a), _steps_with_memory(n)
    for k in range(min(len(sa), len(sn))):
        if sa[k][2] != sn[k][2] or sa[k][0] != sn[k][0]:
            return {"turn": sa[k][0], "step": sa[k][1], "memory_before": sa[k][3]}
    if len(sa) != len(sn):
        k = min(len(sa), len(sn))
        m = sa[k][3] if k < len(sa) else (sa[-1][3] if sa else False)
        return {"turn": None, "step": None, "memory_before": m, "length_only": True}
    return None


def changes(d, arm, tasks, ref="N"):
    """Gains and losses against ref with cause: copy (losses only), memory, noise_before_memory, no_divergence."""
    out = {"gains": [], "losses": []}
    for t in tasks:
        a, b = d[arm][t], d[ref][t]
        if solved(a) == solved(b):
            continue
        dv = divergence(a["episode"], b["episode"])
        cause = "no_divergence" if dv is None else ("memory" if dv["memory_before"] else "noise_before_memory")
        row = {"task": t, "domain": domain(t), "cause": cause, "first_fail": a["evaluation"]["first_fail"] if not solved(a) else b["evaluation"]["first_fail"]}
        if not solved(a):
            i, vals, fns = copy_evidence(a, b)
            if vals or fns:
                row.update({"cause": "copy", "copied_values": vals, "copied_functions": fns})
            notes = [n for s in a["episode"]["turns"][i]["steps"] for n in s.get("notes", [])] if i is not None and i < len(a["episode"]["turns"]) else []
            row["notes_in_deciding_turn"] = notes
        out["gains" if solved(a) else "losses"].append(row)
    for k in ("gains", "losses"):
        out[k + "_by_cause"] = dict(Counter(r["cause"] for r in out[k]))
    return out


# ----------------------------------------------------------------------------- session blocks

def block(rows, arms_pref, ref="N"):
    d = an1.by_arm(rows)
    arms = [a for a in arms_pref if a in d]
    order = list(dict.fromkeys(r["task"] for r in rows))
    tasks = an1.complete_tasks(d, arms, order) if arms else []
    table = {a: an1.arm_summary(d, a, tasks) for a in arms}
    pairs = {a: an1.paired(d, a, ref, tasks) for a in arms if a != ref and ref in d}
    per_dom = {dom: {a: sum(solved(d[a][t]) for t in tasks if domain(t) == dom) for a in arms} for dom in DOMAINS}
    for dom in DOMAINS:
        per_dom[dom]["tasks"] = sum(1 for t in tasks if domain(t) == dom)
    return d, arms, tasks, table, pairs, per_dom


def _pref_key(arm, solved_n, lost, pref):
    return (solved_n, -lost, pref.index(arm))


def select_e_star(rows):
    """SPEC 3: most solved among R+, M2, M1; tie -> fewer losses against N; tie -> order M1, M2, R+."""
    d, arms, tasks, table, pairs, _ = block(rows, ["N", "R+", "M2", "M1", "N'"])
    cands = [a for a in ("R+", "M2", "M1") if a in table and "N" in table]
    pref = ["R+", "M2", "M1"]                                # later = preferred on a full tie
    if not cands:
        return {"E_star": None, "reason": "no block arm completed"}
    best = max(cands, key=lambda a: _pref_key(a, table[a]["solved"], pairs[a]["lost"], pref))
    return {"E_star": best, "tasks": len(tasks), "solved": {a: table[a]["solved"] for a in table},
            "losses_vs_N": {a: pairs[a]["lost"] for a in cands}}


def select_k(rows):
    """SPEC 5: K = V0 if V0 >= V0q + 2, else V0q; K = V0 when V0q did not run."""
    d, arms, tasks, table, _, _ = block(rows, ["N", "V0", "V0q"])
    if "V0" not in table:
        return {"K": "V0q" if "V0q" in table else None, "reason": "V0 missing"}
    if "V0q" not in table:
        return {"K": "V0", "reason": "V0q did not run", "tasks": len(tasks)}
    k = "V0" if table["V0"]["solved"] >= table["V0q"]["solved"] + 2 else "V0q"
    return {"K": k, "V0": table["V0"]["solved"], "V0q": table["V0q"]["solved"], "tasks": len(tasks)}


# ----------------------------------------------------------------------------- E2 tournament (SPEC 4)

def tournament(by_src, order):
    none = by_src.get("none", {})
    if not none:
        return None, {}
    base_res, base_pass = sum(r["resolved"] for r in none.values()), sum(r["turn_passed"] for r in none.values())
    table = {"none": {"states": len(none), "resolved": base_res, "passed": base_pass}}
    for src in order:
        rows = by_src.get(src)
        if not rows:
            continue
        if any(k not in rows for k in none):
            table[src] = {"admissible": False, "reason": "not evaluated on every state"}
            continue
        reg = [k for k in none if none[k]["turn_passed"] and not rows[k]["turn_passed"]]
        res = sum(rows[k]["resolved"] for k in none)
        pas = sum(rows[k]["turn_passed"] for k in none)
        table[src] = {"states": len(none), "resolved": res, "passed": pas, "regressions": len(reg),
                      "admissible": not reg and res >= base_res and pas >= base_pass}
    adm = [s for s in order if table.get(s, {}).get("admissible")]
    if not adm:
        return None, table
    return max(adm, key=lambda s: (table[s]["passed"], table[s]["resolved"], -order.index(s))), table


def _by_sig(rows):
    g = defaultdict(lambda: defaultdict(dict))
    texts = defaultdict(dict)
    for r in rows:
        sk = (r["domain"], r["function"], r["error_key"])
        g[sk][r["source"]][(r["task"], r["turn"], r["step"])] = r
        if r.get("note_text"):
            texts[sk][r["source"]] = r["note_text"]
    return g, texts


def e2_selection(rows, det_by_domain, q_by_domain):
    g, texts = _by_sig(rows)
    sets = {d: [] for d in DOMAINS}
    per_sig, f_cmp = [], {"signatures_with_F": 0, "F_would_win": 0, "detail": []}
    for sk in sorted(g):
        dom, fn_, key = sk
        best, table = tournament(g[sk], ["D", "X", "Q", "G0"])
        per_sig.append({"domain": dom, "signature": f"{fn_}|{key}", "selected": best, "table": table,
                        "x_created": "X" in g[sk], "states": len(g[sk].get("none", {}))})
        if best:
            sets[dom].append({"function": fn_, "error_key": key, "text": texts[sk][best], "source": best})
        if "F" in g[sk]:
            f_cmp["signatures_with_F"] += 1
            order = ([best] if best else []) + ["F"]
            w, _ = tournament(g[sk], order)
            f_cmp["F_would_win"] += w == "F"
            f_cmp["detail"].append({"signature": f"{dom}:{fn_}|{key}", "local_best": best, "winner_vs_F": w})
    fuel = g.get(("VC",) + FUEL)
    if fuel:
        w, t = tournament(fuel, ["O", "S", "P", "Q", "F"])
        valid = w in ("O", "F") and not t.get("S", {}).get("admissible", False)
        tool = {"winner": w, "table": t, "valid": valid}
    else:
        tool = {"winner": None, "table": {}, "valid": False, "reason": "no fuel states"}
    if tool["valid"]:
        used, final = "T", sets
    else:
        used, final = "fallback_D_else_Q", {}
        for d in DOMAINS:
            dl = [{"function": l["function"], "error_key": l["error_key"], "text": xv.note_text(l), "source": "D"} for l in det_by_domain[d]]
            have = {(l["function"], l["error_key"]) for l in dl}
            final[d] = dl + [dict(l, source="Q") for l in q_by_domain[d] if (l["function"], l["error_key"]) not in have]
    return {"sets": final, "set_used": used, "tournament_sets": sets, "tool_control": tool, "per_signature": per_sig, "F_vs_local": f_cmp}


# ----------------------------------------------------------------------------- rules

def h14(table, pairs, copy_losses):
    if "R+" not in table:
        return {"verdict": "not_computable"}
    ms = [a for a in ("M2", "M1") if a in table]
    if not ms:
        return {"verdict": "not_computable"}
    pref = ["M2", "M1"]
    m = max(ms, key=lambda a: (table[a]["solved"], -pairs[a]["lost"], pref.index(a)))
    lr, lm = pairs["R+"]["lost"], pairs[m]["lost"]
    sr, sm = table["R+"]["solved"], table[m]["solved"]
    if lm <= lr - 3 and sm >= sr - 1:
        v = "supported"
    elif (lr >= 4 and lm >= lr - 1) or sm <= sr - 3:
        v = "refuted"
    elif lr < 4:
        v = "untestable"
    else:
        v = "inconclusive"
    return {"verdict": v, "M": m, "solved_R+": sr, "solved_M": sm, "losses_R+": lr, "losses_M": lm,
            "copy_losses": copy_losses}


def main_test(table, pairs, per_dom):
    if not all(a in table for a in ("N", "V0")):
        return {"verdict": "not_computable"}
    n, v = table["N"]["solved"], table["V0"]["solved"]
    noise = abs(table["N'"]["solved"] - n) if "N'" in table else 0
    p, lost = pairs["V0"]["p_one_sided"], pairs["V0"]["lost"]
    dom_ge = all(per_dom[d]["V0"] >= per_dom[d]["N"] for d in DOMAINS if per_dom[d]["tasks"])
    dom_gt = sum(1 for d in DOMAINS if per_dom[d]["tasks"] and per_dom[d]["V0"] > per_dom[d]["N"])
    sup = v - n >= 9 and p <= 0.01 and lost <= 4 and dom_ge and dom_gt >= 2 and v - n > 2 * noise
    ref = v - n <= 4 or lost >= 8
    return {"verdict": "supported" if sup else ("refuted" if ref else "intermediate"), "V0": v, "N": n, "diff": v - n, "p_one_sided": p,
            "losses": lost, "noise_abs_Nprime_minus_N": noise, "domains_V0_ge_N": dom_ge, "domains_V0_gt_N": dom_gt}


def secondary(d, tasks, table, pairs, copy_losses, tool_valid):
    pv, out = {}, {}

    def pair(x, y):
        return an1.paired(d, x, y, tasks)
    if all(a in table for a in ("V0", "E*", "TrT")):
        a, b = pair("V0", "E*"), pair("V0", "TrT")
        pv["V0_vs_E*"], pv["V0_vs_TrT"] = a["p_one_sided"], b["p_one_sided"]
        best = max(table["E*"]["solved"], table["TrT"]["solved"])
        v0 = table["V0"]["solved"]
        out["H15"] = {"verdict": "supported" if v0 >= best + 3 else ("refuted" if v0 <= best else "inconclusive"),
                      "V0": v0, "E*": table["E*"]["solved"], "TrT": table["TrT"]["solved"], "pairs": {"V0_vs_E*": a, "V0_vs_TrT": b}}
    if all(a in table for a in ("TrT", "TrQ")):
        a = pair("TrT", "TrQ")
        pv["TrT_vs_TrQ"] = a["p_one_sided"]
        tt, tq = table["TrT"]["solved"], table["TrQ"]["solved"]
        lt, lq = pairs["TrT"]["lost"], pairs["TrQ"]["lost"]
        v = "supported" if tt >= tq + 2 and lt <= lq else ("refuted" if tt <= tq - 2 else "inconclusive")
        if not tool_valid:
            v = "tool_invalid_at_this_number_of_states"
        out["H16"] = {"verdict": v, "TrT": tt, "TrQ": tq, "losses_TrT": lt, "losses_TrQ": lq, "pair": a}
    if all(a in table for a in ("E*", "R+")):
        a = pair("E*", "R+")
        pv["E*_vs_R+"] = a["p_one_sided"]
        ce, cr = copy_losses.get("E*", 0), copy_losses.get("R+", 0)
        es, rs = table["E*"]["solved"], table["R+"]["solved"]
        out["H14_repeat"] = {"verdict": "supported" if ce <= cr - 3 and es >= rs - 1 else ("refuted" if es <= rs - 3 else "inconclusive"),
                             "copy_losses_E*": ce, "copy_losses_R+": cr, "E*": es, "R+": rs, "pair": a}
    else:
        out["H14_repeat"] = {"verdict": "not_applicable (E* = R+)"}
    out["holm"] = an1.holm(pv) if pv else {}
    return out


def competitor_rule(table, pairs):
    cs = [c for c in ("C-RB", "C-G") if c in table]
    if "K" not in table or not cs:
        return {"verdict": "not_computable"}
    c = max(cs, key=lambda a: (table[a]["solved"], -pairs[a]["lost"], -cs.index(a)))
    k, cv = table["K"]["solved"], table[c]["solved"]
    lk, lc = pairs["K"]["lost"], pairs[c]["lost"]
    v = "K_ahead" if k - cv >= 4 and lk <= lc + 1 else ("K_not_ahead" if k - cv <= 1 else "inconclusive")
    return {"verdict": v, "C": c, "K": k, "C_solved": cv, "losses_K": lk, "losses_C": lc, "K_minus_N": k - table["N"]["solved"] if "N" in table else None}


def e5_rule(table, pairs):
    if not all(a in table for a in ("N", "K")):
        return {"verdict": "not_computable"}
    diff, lost = table["K"]["solved"] - table["N"]["solved"], pairs["K"]["lost"]
    v = "repeated" if diff >= 5 and lost <= 4 else ("not_repeated" if diff <= 2 else "inconclusive")
    return {"verdict": v, "K_minus_N": diff, "losses": lost, "K": table["K"]["solved"], "N": table["N"]["solved"],
            "N'": table.get("N'", {}).get("solved")}


def recommendation(main, comp, e5):
    mv = main.get("verdict")
    if mv == "refuted":
        return "WRÓCIĆ DO SKŁADNIKÓW"
    ready = (mv == "supported" and (comp.get("K_minus_N") or 0) >= 6 and comp.get("verdict") == "K_ahead" and e5.get("verdict") == "repeated")
    if ready:
        return "GOTOWE DO EGZAMINU"
    return "POPRAWIĆ NAJSŁABSZY SKŁADNIK"


def drift(e3_rows):
    """SPEC 5: N of E3 must agree with NIGHT-1's N (sA for VC, sD for GFS and TRAVEL) on at least 84 of 88 tasks."""
    old = {}
    for s in ("sA", "sD"):
        for r in an1.rows_of(N1RUN, s):
            if r["arm"] == "N":
                old[r["task"]] = solved(r)
    new = {r["task"]: solved(r) for r in e3_rows if r["arm"] == "N"}
    common = [t for t in new if t in old]
    agree = sum(new[t] == old[t] for t in common)
    return {"tasks": len(common), "agree": agree, "ok": agree >= 84 if len(common) == 88 else agree >= len(common) - 4,
            "flipped": [t for t in common if new[t] != old[t]]}


# ----------------------------------------------------------------------------- the analysis

def costs_all(run: Path):
    c = an1.costs(run)
    smoke = run.parent / "smoke-run"
    c["smoke_attempts"] = sum(1 for _ in (smoke / "attempts.jsonl").open(encoding="utf-8")) if (smoke / "attempts.jsonl").exists() else 0
    c["total_local_with_smoke"] = c["local_attempts"] + c["smoke_attempts"]
    c["paid_calls"] = 0
    return c


def session_section(run, name, arms_pref):
    rows = rows_of(run, name)
    if not rows:
        return None
    d, arms, tasks, table, pairs, per_dom = block(rows, arms_pref)
    ch = {a: changes(d, a, tasks) for a in arms if a != "N" and "N" in d}
    copy_losses = {a: ch[a]["losses_by_cause"].get("copy", 0) for a in ch}
    return {"rows": rows, "d": d, "arms": arms, "tasks": tasks, "table": table, "pairs": pairs, "per_domain": per_dom,
            "changes": ch, "copy_losses": copy_losses}


def strip(sec):
    if sec is None:
        return None
    return {k: v for k, v in sec.items() if k not in ("rows", "d")}


def analyze(run: Path, out: Path):
    res = {"program": "AAMR-NIGHT-2", "state": jread(run / "state.json", {}), "done": (run / "DONE.json").exists(),
           "stopped": jread(run / "STOPPED.json"), "restarts": jread(run / "restarts.json"), "costs": costs_all(run)}
    art = run / "artifacts"
    e1 = session_section(run, "E1", ["N", "R+", "M2", "M1", "N'"])
    if e1:
        res["E1"] = strip(e1)
        res["E1"]["E_star"] = jread(art / "e_star.json")
        res["E1"]["H14"] = h14(e1["table"], e1["pairs"], e1["copy_losses"])
    e2rows = rows_of(run, "E2")
    nt = jread(art / "notes_T.json")
    if nt:
        res["E2"] = {"forks": len(e2rows), "by_source": dict(Counter(r["source"] for r in e2rows)), "set_used": nt["set_used"],
                     "tool_control": nt["tool_control"], "per_signature": nt["per_signature"], "F_vs_local": nt["F_vs_local"],
                     "selected_sources": {d: dict(Counter(l["source"] for l in nt["sets"][d])) for d in DOMAINS},
                     "selected_texts": nt["sets"]}
    e3 = session_section(run, "E3", ["N", "V0", "N'", "E*", "TrT", "V0q", "TrQ", "R+"])
    k = jread(art / "k.json")
    if e3:
        tool_valid = bool(nt and nt["tool_control"]["valid"])
        res["E3"] = strip(e3)
        res["E3"]["drift"] = drift(e3["rows"])
        res["E3"]["main"] = main_test(e3["table"], e3["pairs"], e3["per_domain"])
        res["E3"]["secondary"] = secondary(e3["d"], e3["tasks"], e3["table"], e3["pairs"], e3["copy_losses"], tool_valid)
        res["E3"]["K"] = k
        if k and k.get("K") in e3["d"]:
            karm = k["K"]
            res["E3"]["K_failures"] = an1.failure_census(e3["d"], karm, e3["tasks"])
            res["E3"]["K_open_problems"] = an1.open_problems(e3["d"], karm, e3["tasks"])
            res["E3"]["N_open_problems"] = an1.open_problems(e3["d"], "N", e3["tasks"])
            res["E3"]["K_lost_tasks"] = e3["changes"][karm]["losses"]
    e4 = session_section(run, "E4", ["N", "K", "C-RB", "C-G"])
    if e4:
        res["E4"] = strip(e4)
        res["E4"]["competitors"] = competitor_rule(e4["table"], e4["pairs"])
    e5 = session_section(run, "E5", ["N", "K", "N'"])
    if e5:
        res["E5"] = strip(e5)
        res["E5"]["rule"] = e5_rule(e5["table"], e5["pairs"])
    res["build_costs"] = build_costs(run, k)
    main = (res.get("E3") or {}).get("main", {})
    comp = (res.get("E4") or {}).get("competitors", {})
    r5 = (res.get("E5") or {}).get("rule", {})
    res["recommendation"] = recommendation(main, comp, r5) if main else "NIE OBLICZONO (brak E3)"
    res["weakest_component"] = weakest(res)
    res["hypotheses"] = hypotheses(res)
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return res


def build_costs(run: Path, k):
    att = Counter()
    if (run / "attempts.jsonl").exists():
        for line in (run / "attempts.jsonl").open(encoding="utf-8"):
            a = json.loads(line)
            key = a["key"]
            att["E2_forks" if key.startswith("e2:") else "C-RB" if key.startswith("crb:") else "C-G" if key.startswith("cg:") else "other"] += 1
    kk = (k or {}).get("K")
    return {"attempts": dict(att), "K": kk,
            "K_build_calls": att["E2_forks"] if kk == "V0" else 0,
            "K_note": "V0: tournament forks of E2; V0q: notes Q written in NIGHT-1 (20 local writer calls there)",
            "C-RB_build_calls": att["C-RB"], "C-G_build_calls": att["C-G"]}


def weakest(res):
    """Mechanical pointer for the rule 'POPRAWIĆ NAJSŁABSZY SKŁADNIK': which failure class or loss cause dominates for K."""
    e3 = res.get("E3") or {}
    if not e3.get("K_failures"):
        return None
    cls = e3["K_failures"]["classes"]
    losses = Counter(r["cause"] for r in e3.get("K_lost_tasks", []))
    return {"K_failure_classes": cls, "K_loss_causes": dict(losses), "largest_failure_class": max(cls, key=cls.get) if cls else None}


def hypotheses(res):
    e1 = (res.get("E1") or {}).get("H14", {})
    sec = (res.get("E3") or {}).get("secondary", {})
    comp = (res.get("E4") or {}).get("competitors", {})
    return {"H14 (E1)": e1.get("verdict"), "H14 (E3 repeat)": (sec.get("H14_repeat") or {}).get("verdict"),
            "H15": (sec.get("H15") or {}).get("verdict"), "H16": (sec.get("H16") or {}).get("verdict"),
            "H10 (rozwojowo, E4)": comp.get("verdict"), "test główny v0": ((res.get("E3") or {}).get("main") or {}).get("verdict"),
            "drugi model (E5)": ((res.get("E5") or {}).get("rule") or {}).get("verdict")}


# ----------------------------------------------------------------------------- report

COLS = ("tasks", "solved", "error_events", "error_results", "invalid_calls", "model_calls", "prompt_tokens", "notes_shown")


def _tbl(table):
    L = ["| Ramię | " + " | ".join(COLS) + " |", "|---|" + "---|" * len(COLS)]
    for a, v in table.items():
        L.append(f"| {a} | " + " | ".join(str(v.get(c)) for c in COLS) + " |")
    return L


def _pairs(pairs):
    L = ["| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne |", "|---|---|---|---|---|---|"]
    for a, p in pairs.items():
        L.append(f"| {p['x']} vs {p['y']} | {p['gained']} | {p['lost']} | {p['diff']:+d} | {p['p_one_sided']:.4f} | {p['p_two_sided']:.4f} |")
    return L


def _changes(ch):
    L = ["| Ramię | zyski wg przyczyny | straty wg przyczyny |", "|---|---|---|"]
    for a, c in ch.items():
        L.append(f"| {a} | {c['gains_by_cause']} | {c['losses_by_cause']} |")
    return L


def _dom(per_dom):
    arms = [k for k in next(iter(per_dom.values())) if k != "tasks"]
    L = ["| Domena | zadania | " + " | ".join(arms) + " |", "|---|---|" + "---|" * len(arms)]
    for d in DOMAINS:
        L.append(f"| {d} | {per_dom[d]['tasks']} | " + " | ".join(str(per_dom[d][a]) for a in arms) + " |")
    return L


def js(x):
    return "`" + json.dumps(x, ensure_ascii=False, default=str) + "`"


def write_report(res, out: Path):
    L = ["# AAMR-NIGHT-2: raport wygenerowany automatycznie", "",
         "Raport powstał deterministycznie z zamrożonych surowych danych (`raw-freeze.json`), według reguł z `SPEC_AAMR_NIGHT2.md` i "
         "`PROTOCOL.md`. Wszystkie wyniki mają status rozwojowy. Interpretacja jest w osobnym pliku `WNIOSKI.md` (jeśli powstał).", "",
         "## Stan programu", "", "| Etap | Status | Uwagi |", "|---|---|---|"]
    for s, st in (res["state"].get("stages") or {}).items():
        L.append(f"| {s} | {st.get('status')} | {st.get('reason') or ''} |")
    c = res["costs"]
    L += ["", "## Koszty", "",
          f"- Lokalne próby w programie: {c['local_attempts']} (ponowienia {c['local_retries']}), test techniczny {c['smoke_attempts']}, razem "
          f"{c['total_local_with_smoke']} (limit 21 500). Wywołania płatne: 0.",
          f"- Według budżetu: {c['local_by_bucket']}; według modelu: {c['local_by_model']}.",
          f"- Czas modeli (s): {c['local_model_seconds']}; okno {c['first_attempt_at']} – {c['last_attempt_at']}.",
          f"- Budowa pamięci: {js(res['build_costs'])}", ""]
    if res.get("E1"):
        e = res["E1"]
        L += ["## E1 (EXP-MASK-0): pamięć sukcesów z maskowaniem, 60 zadań treningowych", "", f"Zadania kompletne: {len(e['tasks'])}.", ""]
        L += _tbl(e["table"]) + [""] + _pairs(e["pairs"]) + [""] + _changes(e["changes"]) + [""] + _dom(e["per_domain"])
        L += ["", f"**Wybór E\\*:** {js(e['E_star'])}", "", f"**H14:** {js(e['H14'])}", ""]
    if res.get("E2"):
        e = res["E2"]
        L += ["## E2 (EXP-NOTE-SEL): turniej notatek na stanach treningowych", "",
              f"Rozwidlenia: {e['forks']} ({e['by_source']}). Użyty zestaw: **{e['set_used']}**.", "",
              f"**Kontrola narzędzia (błąd baku, {{O, S, P, Q, F}}):** {js({k: v for k, v in e['tool_control'].items() if k != 'table'})}",
              "", "Tabela kontroli: " + js(e["tool_control"].get("table")), "",
              "| Domena | Sygnatura | stany | X powstał | wybrany | oceny (stany/rozwiązane/zaliczone/regresje/dopuszczalny) |", "|---|---|---|---|---|---|"]
        for p in e["per_signature"]:
            cells = "; ".join(f"{s}: {v.get('resolved')}/{v.get('passed')}/{v.get('regressions', '-')}/{v.get('admissible', '-')}"
                              for s, v in p["table"].items())
            L.append(f"| {p['domain']} | {p['signature'][:60]} | {p['states']} | {p['x_created']} | {p['selected']} | {cells} |")
        L += ["", f"Wybrane źródła notatek: {js(e['selected_sources'])}",
              f"Flash wobec najlepszego kandydata lokalnego (tylko porównanie): {js({k: v for k, v in e['F_vs_local'].items() if k != 'detail'})}", ""]
    if res.get("E3"):
        e = res["E3"]
        L += ["## E3 (EXP-V0-1): system złożony, 88 zadań rozwojowych-testowych, 14B", "", f"Zadania kompletne: {len(e['tasks'])}.", ""]
        L += _tbl(e["table"]) + [""] + _pairs(e["pairs"]) + [""] + _dom(e["per_domain"]) + [""] + _changes(e["changes"])
        L += ["", f"**Kontrola dryfu (N wobec NIGHT-1):** {js(e['drift'])}", "",
              f"**Test główny:** {js(e['main'])}", ""]
        sec = e["secondary"]
        for h in ("H15", "H16", "H14_repeat"):
            if h in sec:
                L.append(f"- **{h}:** {js({k: v for k, v in sec[h].items() if k not in ('pairs', 'pair')})}")
        L += [f"- Rodzina Holma: {js(sec.get('holm'))}", "", f"**Konfiguracja K:** {js(e.get('K'))}", ""]
        if e.get("K_failures"):
            L += [f"Spis porażek K (taksonomia NIGHT-1): {js(e['K_failures'])}", "",
                  f"Otwarte problemy K: {js(e['K_open_problems'])}", f"Otwarte problemy N: {js(e['N_open_problems'])}", "",
                  "Zadania stracone przez K wobec N (tura rozstrzygająca, przyczyna):", ""]
            for r in e["K_lost_tasks"]:
                L.append(f"- {r['task']} ({r['domain']}), tura {r['first_fail']}: {r['cause']}"
                         + (f"; skopiowane {r.get('copied_values')} {r.get('copied_functions')}" if r["cause"] == "copy" else "")
                         + (f"; notatki w turze {r['notes_in_deciding_turn']}" if r.get("notes_in_deciding_turn") else ""))
            L.append("")
    if res.get("E4"):
        e = res["E4"]
        L += ["## E4 (EXP-V0-1C): ramiona w stylu konkurentów", "", f"Zadania kompletne: {len(e['tasks'])}.", ""]
        L += _tbl(e["table"]) + [""] + _pairs(e["pairs"]) + [""] + _dom(e["per_domain"]) + [""] + _changes(e["changes"])
        L += ["", f"**Reguła konkurentów:** {js(e['competitors'])}", ""]
    if res.get("E5"):
        e = res["E5"]
        L += ["## E5: drugi model (qwen3.5:9b)", "", f"Zadania kompletne: {len(e['tasks'])}.", ""]
        L += _tbl(e["table"]) + [""] + _pairs(e["pairs"]) + [""] + _dom(e["per_domain"]) + [""] + _changes(e["changes"])
        L += ["", f"**Reguła:** {js(e['rule'])}", ""]
    L += ["## Tabela hipotez (aktualizacja)", "", "| Hipoteza | Werdykt w NIGHT-2 (rozwojowo) |", "|---|---|"]
    for h, v in res["hypotheses"].items():
        L.append(f"| {h} | {v} |")
    L += ["", "## Reguła rekomendacji egzaminu (decyzja należy do właściciela)", "", f"**{res['recommendation']}**", "",
          f"Wskazanie składnika (mechanicznie): {js(res.get('weakest_component'))}", "",
          "Egzaminu na TradingBot program nie uruchamia.", ""]
    (out / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
