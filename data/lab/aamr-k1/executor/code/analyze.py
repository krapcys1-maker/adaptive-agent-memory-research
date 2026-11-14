"""K1 analysis (separate process, after the checker; spec sec. 7, 8, 11). Frozen before the first experimental call.

Uses the frozen prototypes of v0.4 unchanged: t_w6_cells (missing cells, INVALID, block A), k1_length (WR5, rule LEN),
k1_v04_reading (states and the reading). The dependence diagnostic (7.4) re-implements t_w5_dependence on the frozen graph
of shared M traces (stim/k1_shared_graph.json); the tests check it against the published NIGHT-2 values (T-analiza-b).
Writes report/results.json and report/K1_RAPORT.md. Exit 2 if a forbidden sentence would be printed.
Usage: python -I -X utf8 -B analyze.py --base DIR --final"""
from __future__ import annotations

import collections
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from scipy import stats

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import k1_length as klen  # noqa: E402
import k1_lib as kl  # noqa: E402
import k1_v04_reading as rd  # noqa: E402
import t_w6_cells as cells  # noqa: E402

ARMS5 = kl.ARMS5
CONTR = {"MP": "P", "MX": "X", "MS": "S"}
# Owner's condition to D1 (2026-11-13), printed with every reading; not part of the frozen v0.4 reading code.
D1_RULE = ("ZASADA INTERPRETACJI (D1): próg 10 pp służy wyłącznie pytaniu, czy efekt sięga 10 pp. Efekty mniejsze niż 10 pp "
           "mogą być rzeczywiste i użyteczne. Brak wykazania efektu 10 pp ani brak wykrycia efektu nie są dowodem braku "
           "korzyści z pamięci.")


# ----------------------------------------------------------------------------- small statistics

def t_iv(v, level):
    v = np.asarray(v, float)
    n = len(v)
    if n < 2:
        return float("nan"), (float("nan"), float("nan"))
    h = stats.t.ppf(1 - (1 - level) / 2, n - 1) * v.std(ddof=1) / math.sqrt(n)
    return float(v.mean()), (float(v.mean() - h), float(v.mean() + h))


def boot_iv(v, strata, level, B, seed):
    v, s = np.asarray(v, float), np.asarray(strata)
    rng = np.random.default_rng(seed)
    tot = np.zeros(B)
    for st in np.unique(s):
        ix = np.where(s == st)[0]
        tot += v[ix[rng.integers(0, len(ix), (B, len(ix)))]].sum(1)
    b = tot / len(v)
    a = (1 - level) / 2
    return float(np.percentile(b, 100 * a)), float(np.percentile(b, 100 * (1 - a)))


def cluster_iv(v, groups, level):
    g = collections.defaultdict(list)
    for x, k in zip(v, groups):
        g[k].append(x)
    means = [np.mean(x) for x in g.values()]
    return len(means), t_iv(means, level)[1]


def sign_flip_p(v, perms, seed):
    v = np.asarray(v, float)
    rng = np.random.default_rng(seed)
    obs = abs(v.mean())
    flips = rng.choice((-1.0, 1.0), (perms, len(v)))
    return float(np.mean(np.abs((flips * v).mean(1)) >= obs - 1e-12))


class Dependence:
    """Spec 7.4 diagnostic (t_w5_dependence.py) on a given graph: tasks -> {stratum, traces}."""

    def __init__(self, graph, tasks):
        self.tasks = tasks
        ix = {t: k for k, t in enumerate(tasks)}
        st = collections.defaultdict(list)
        for t in tasks:
            st[tuple(graph[t]["stratum"])].append(ix[t])
        self.strata = [np.array(v) for v in st.values()]
        tr = {t: set(graph[t]["traces"]) for t in tasks}
        self.pairs = np.array([(a, b) for s in self.strata for i, a in enumerate(s) for b in s[i + 1:]
                               if tr[tasks[a]] & tr[tasks[b]]])
        self.L2n = 2 * len(self.pairs) / len(tasks)

    def rho_hat(self, D):
        Z = np.zeros_like(D, dtype=float)
        for s in self.strata:
            x = D[..., s]
            m = x.mean(-1, keepdims=True)
            v = x.var(-1, keepdims=True)
            Z[..., s] = np.where(v > 0, (x - m) / np.sqrt(np.where(v > 0, v, 1)), 0)
        return (Z[..., self.pairs[:, 0]] * Z[..., self.pairs[:, 1]]).mean(-1)

    def diag(self, d, perms, seed):
        rng = np.random.default_rng(seed)
        d = np.asarray(d, float)
        obs = float(self.rho_hat(d))
        Pm = np.repeat(d[None, :], perms, 0)
        for s in self.strata:
            Pm[:, s] = rng.permuted(Pm[:, s], axis=1)
        null = self.rho_hat(Pm)
        rt = obs - float(null.mean())
        return {"rho_hat": obs, "null_mean": float(null.mean()), "null_sd": float(null.std()), "rho_tilde": rt,
                "p": float(np.mean(null >= obs)), "widening": math.sqrt(1 + max(0.0, rt) * self.L2n)}

    def rho_star(self, est, half):
        s0 = rd.state(est - half, est + half)
        f = lambda r: math.sqrt(1 + r * self.L2n)
        lo, hi = 0.0, 1.0
        if rd.state(est - half * f(hi), est + half * f(hi)) == s0:
            return None
        for _ in range(60):
            mid = (lo + hi) / 2
            if rd.state(est - half * f(mid), est + half * f(mid)) == s0:
                lo = mid
            else:
                hi = mid
        return hi


# ----------------------------------------------------------------------------- data

def load(L, block):
    """{(task, arm): record} for one block: status from the episode, solved/technical error from the checker."""
    ses = L["run"] / "sessions" / f"{block}.jsonl"
    ev = L["eval"] / f"{block}.jsonl"
    if not ses.exists() or not ev.exists():
        return {}, {}
    E = {(e["task"], e["arm"]): e for e in map(json.loads, ev.read_text(encoding="utf-8").splitlines())}
    out, recs = {}, {}
    for r in map(json.loads, ses.read_text(encoding="utf-8").splitlines()):
        k = (r["task"], r["arm"])
        e = E.get(k)
        st = r["episode"]["status"]
        if e is None or e.get("eval_status") != "ok":
            out[k] = {"status": "technical_error"}
        else:
            out[k] = {"status": st, "solved": bool(e.get("solved"))}
        recs[k] = r
    return out, recs


def night2_outcomes():
    """NIGHT-2 at temperature 0: (task, K1 arm N|M) -> solved; E3 N/E*, E1 N/R+ (known data, spec 7.7 drift control)."""
    out = {}
    for sess in ("E3", "E1"):
        for r in kl.rows(kl.NRUN / "sessions" / f"{sess}.jsonl"):
            if r["arm"] == "N":
                out[(r["task"], "N", sess)] = int(bool(r["evaluation"]["solved"]))
            elif r["arm"] == kl.NIGHT2_M_ARM[sess]:
                out[(r["task"], "M", sess)] = int(bool(r["evaluation"]["solved"]))
    return out


def night2_counts(idx):
    """T-analiza-b: gains/losses of M against N in NIGHT-2 (E3: E* - N on 88 test; E1: R+ - N on 60 training)."""
    o = night2_outcomes()
    res = {}
    for sess in ("E3", "E1"):
        ts = [t for t, v in idx.items() if v[0] == sess]
        d = [o[(t, "M", sess)] - o[(t, "N", sess)] for t in ts]
        res[sess] = {"tasks": len(ts), "gains": sum(x > 0 for x in d), "losses": sum(x < 0 for x in d)}
    return res


def stimulus_chars(n2, p0, L, idx, c_d, blocks_inst):
    """Content characters (block without the header line, v1.0 sec. 2 and 7.5; C3) of every arm, task and turn, from the
    frozen stimuli (not from the episodes)."""
    stim = L["stim"]
    provs = kl.make_providers(n2, p0, stim, c_d)
    tasks_file = {}
    for line in kl.TASKS_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip() and kl.not_trading(line):
            r = json.loads(line)
            tasks_file[r["id"]] = [q[0]["content"] for q in r["question"]]
    plans = kl.plan_turns(kl.read_json(stim / "k1_plans_M.json"), idx)
    out = {}
    for inst in blocks_inst:
        fns = {a: provs[a](inst) for a in ("M", "P", "X", "S")}
        for t, (_, d, part) in idx.items():
            for ti in sorted(plans[t]):
                for a, f in fns.items():
                    txt = f[part][d](t, ti, tasks_file[t][ti])[0]
                    out[(inst, t, ti, a)] = len(kl.content(txt)) if txt else 0
    return out, plans


def length_x(idx, recs_by_block, inst_of, chars, plans):
    """WR5 measure (spec 7.5): x_i(C) = ln(T_i(M) / T_i(C)), T_i(a) = mean over the used sampled blocks of the summed block
    tokens of all turns; turn 0 exact from the run (prompt_eval_count of the arm minus N, turn 0, same block); later
    turns: characters x tokens per character of the arm and domain measured at turn 0."""
    tok0, chr0 = collections.Counter(), collections.Counter()
    exact = {}
    for b, recs in recs_by_block.items():
        inst = inst_of[b]
        for (t, a), r in recs.items():
            if a == "N":
                continue
            n = recs.get((t, "N"))
            pec = lambda rr: (rr["episode"]["turns"][0]["steps"][0].get("prompt_eval_count")
                              if rr and rr["episode"]["turns"] and rr["episode"]["turns"][0]["steps"] else None)
            pa, pn = pec(r), pec(n)
            c = chars.get((inst, t, 0, a), 0)
            if pa is not None and pn is not None and c:
                exact[(b, t, a)] = pa - pn
                tok0[(a, idx[t][1])] += pa - pn
                chr0[(a, idx[t][1])] += c
    rho = {k: tok0[k] / chr0[k] for k in tok0 if chr0[k]}
    T = collections.defaultdict(list)
    for b in recs_by_block:
        inst = inst_of[b]
        for t, (_, d, _) in idx.items():
            for a in ("M", "P", "X", "S"):
                r_ad = rho.get((a, d))
                if r_ad is None:
                    continue
                tot = 0.0
                for ti in plans[t]:
                    c = chars.get((inst, t, ti, a), 0)
                    tot += exact[(b, t, a)] if ti == 0 and (b, t, a) in exact else c * r_ad
                T[(t, a)].append(tot)
    x = {}
    for C in ("P", "X", "S"):
        x[C] = {t: math.log(np.mean(T[(t, "M")]) / np.mean(T[(t, C)])) for t in idx
                if T.get((t, "M")) and T.get((t, C)) and np.mean(T[(t, C)]) > 0 and np.mean(T[(t, "M")]) > 0}
    return x, {f"{a}/{d}": v for (a, d), v in rho.items()}, exact, rho


def postrun_leak(idx, recs_by_block, inst_of, stim, src_of, train_set):
    """L1/L3 re-checked on what the episodes actually recorded (turn.memory.items) against the frozen stimuli."""
    plans = kl.plan_turns(kl.read_json(stim / "k1_plans_M.json"), idx)
    draws = kl.read_json(stim / "k1_draws_SX.json")
    bad, checked = [], 0
    for b, recs in recs_by_block.items():
        inst = inst_of[b]
        for (t, a), r in recs.items():
            for tu in r["episode"]["turns"]:
                items = tu["memory"]["items"] or []
                ti = tu["index"]
                want = {"N": [], "P": [], "M": plans[t].get(ti, [])}.get(a)
                if a in ("X", "S"):
                    want = draws[a][str(inst)].get(f"{t}:{ti}", [])
                if list(items) != list(want):
                    bad.append(f"{b}/{a}/{t}:{ti} items differ from the frozen stimulus")
                if a in ("N", "P") and (items or (a == "N" and tu["memory"]["block_chars"])):
                    bad.append(f"{b}/{a}/{t}:{ti} block without sources expected")
                for i in items:
                    checked += 1
                    if src_of.get(i) == t or src_of.get(i) not in train_set:
                        bad.append(f"{b}/{a}/{t}:{ti} source {src_of.get(i)}")
    return bad, checked


def l9(idx, stim, inst_list):
    """Descriptive L9: share of shown call lines (first 8 steps of each trace, whitespace removed) identical to a gold call
    of the current task; mean over tasks and over turn blocks. Gold is read here (analysis process, after the run)."""
    gold = {}
    for line in kl.GOLD.read_text(encoding="utf-8").splitlines():
        if line.strip() and kl.not_trading(line):
            r = json.loads(line)
            gold[r["id"]] = {re.sub(r"\s+", "", c) for turn in r["ground_truth"] for c in turn}
    plans = kl.plan_turns(kl.read_json(stim / "k1_plans_M.json"), idx)
    draws = kl.read_json(stim / "k1_draws_SX.json")
    rows = {}
    for d in kl.DOMAINS:
        for r in kl.read_json(stim / f"k1_pool_{d}.json"):
            rows[f"{r['source_task']}:t{r['turn']}"] = r
    out = {}
    for arm in ("M", "S", "X"):
        per_task, per_block = collections.defaultdict(list), []
        for inst in (inst_list if arm != "M" else [None]):
            for t in idx:
                for ti, ids in plans[t].items():
                    ids = ids if arm == "M" else draws[arm][str(inst)].get(f"{t}:{ti}", [])
                    lines = [re.sub(r"\s+", "", s["call"]) for i in ids for s in rows[i]["steps"][:8] if s.get("call")]
                    if not lines:
                        continue
                    hit = [ln in gold[t] for ln in lines]
                    per_task[t] += hit
                    per_block.append(np.mean(hit))
        out[arm] = {"by_task_pct": 100 * float(np.mean([np.mean(v) for v in per_task.values()])) if per_task else None,
                    "by_turn_block_pct": 100 * float(np.mean(per_block)) if per_block else None}
    return out


# ----------------------------------------------------------------------------- main analysis

def final(L, cfg):
    diff = kl.verify_manifest(L)
    if diff:
        raise SystemExit(f"L8: files changed since preparation: {diff[:3]}")
    A_ = cfg["analysis"]
    level, thr = A_["level"], A_["threshold_pp"]
    stim = L["stim"]
    tasks_ = kl.read_json(stim / "k1_tasks.json")
    idx = kl.task_index(tasks_)
    tasks = sorted(idx)
    strata = [f"{idx[t][0]}-{idx[t][1]}" for t in tasks]
    graph = kl.read_json(stim / "k1_shared_graph.json")
    train_set = {t for t, v in idx.items() if v[0] == "E1"}
    n2, p0, xv, n1 = kl.import_harness()
    src_of = {p0.pool_row_id(r): r["source_task"] for d in kl.DOMAINS for r in kl.read_json(stim / f"k1_pool_{d}.json")}
    c_d = kl.read_json(L["run"] / "c_d.json")["c_d"]
    res = {"tasks": len(tasks), "blocks": {}, "gates": {}, "caveats": []}
    if (L["meta"] / "provenance.json").exists():                         # spec sec. 11, pt 1: L1-L4b with checked sources
        res["preparation_checks"] = {k: v for k, v in kl.read_json(L["meta"] / "provenance.json").items() if k != "draws"}
    for f in ("T.json", "c_d.json", "P_check.json", "T_m.json", "gate_A.json", "S_SKIPPED.json"):
        if (L["run"] / f).exists():
            v = kl.read_json(L["run"] / f)
            res["gates"][f] = {k: v[k] for k in v if k not in ("probes", "domains")} if isinstance(v, dict) else v
    for b in kl.SAMPLED:
        st =("done" if (L["run"] / f"{b}_DONE.json").exists() else "aborted (second error)" if (L["run"] / f"{b}_ABORTED.json").exists()
              else "incomplete (hard limit)" if (L["run"] / f"{b}_INCOMPLETE.json").exists() else "skipped or not run")
        res["blocks"][b] = st
        if (L["run"] / f"gate_{b}.json").exists():
            res["gates"][f"gate_{b}"] = kl.read_json(L["run"] / f"gate_{b}.json")
    # ---- data
    Y, recs_by_block, inst_of = {}, {}, {}
    for b in kl.SAMPLED:
        if res["blocks"][b] != "done":
            continue
        y, r = load(L, b)
        recs_by_block[b], inst_of[b] = r, cfg["blocks"][b]["instance"]
        Y.update({(t, a, b): v for (t, a), v in y.items()})
    a_incomplete = (L["run"] / "A_INCOMPLETE.json").exists() or not (L["run"] / "A_DONE.json").exists()
    res["blocks"]["A"] = "NIEUKOŃCZONY" if a_incomplete else "done"
    YA, recA = load(L, "A")
    if a_incomplete:                                                   # C4: an incomplete block A never enters any analysis
        YA = {}
    # ---- post-run leak check (L1/L3 on the recorded items)
    leak, checked = postrun_leak(idx, {**recs_by_block, **({"A": recA} if recA else {})}, {**inst_of, "A": 0}, stim, src_of, train_set)
    res["postrun_leak"] = {"violations": len(leak), "checked_sources": checked, "examples": leak[:10]}
    stopped_by = "L1/L3 (po przebiegu)" if leak or checked == 0 else None
    an = cells.analyse_sampled(Y, tasks, stopped_by=stopped_by)
    res["completed_sampled_blocks"] = an["completed"]
    res["excluded_tasks"] = an["excluded"]
    invalid = an["invalid"]
    y = an["y"]
    use = [t for t in tasks if t in y]
    # ---- descriptive M - N and P - N (always), ladder, strata
    def desc(a, b_, ts):
        v = [100 * (y[t][a] - y[t][b_]) for t in ts]
        m, iv = t_iv(v, 0.95)
        return {"estimate": m, "ci95": iv, "tasks": len(v)}

    fmt = lambda e: f"{rd.fmt(e['estimate'])} pp (95%: {rd.fmt(e['ci95'][0])}; {rd.fmt(e['ci95'][1])})" if use else "brak danych"
    if use:
        res["ladder"] = {k: desc(a, b_, use) for k, (a, b_) in
                         {"P-N": ("P", "N"), "X-P": ("X", "P"), "S-X": ("S", "X"), "M-S": ("M", "S"), "M-N": ("M", "N")}.items()}
        res["ladder_by_stratum"] = {s: {k: desc(a, b_, [t for t in use if f"{idx[t][0]}-{idx[t][1]}" == s])
                                        for k, (a, b_) in {"P-N": ("P", "N"), "X-P": ("X", "P"), "S-X": ("S", "X"),
                                                            "M-N": ("M", "N")}.items()} for s in sorted(set(strata))}
        res["rates"] = {a: 100 * float(np.mean([y[t][a] for t in use])) for a in ARMS5}
    est_desc = {"MN": fmt(res["ladder"]["M-N"]) if use else "brak danych", "PN": fmt(res["ladder"]["P-N"]) if use else "brak danych"}
    # ---- contrasts, WR1-WR5, dependence
    intervals, length, contrasts = {}, {}, {}
    if invalid is None:
        dep = Dependence(graph, use)
        chars, plans = stimulus_chars(n2, p0, L, idx, c_d, sorted(set(inst_of.values())))
        xlen, rho_arm, exact0, rho_ad = length_x(idx, {b: recs_by_block[b] for b in an["completed"]}, inst_of, chars, plans)
        res["tokens_per_char_turn0"] = rho_arm
        q = lambda v: [float(x) for x in np.percentile(v, [5, 50, 95])] if len(v) else None
        # spec sec. 11, pt 8: P/M token ratio per block (turn 0, exact) and S/M, X/M length ratio per turn (predicted tokens)
        pm = [exact0[(b, t, "P")] / exact0[(b, t, "M")] for (b, t, a) in exact0 if a == "M" and exact0[(b, t, a)] > 0
              and (b, t, "P") in exact0]
        per_turn = {C: [] for C in ("S", "X")}
        for (inst, t, ti, a), c in chars.items():
            if a in per_turn and c and chars.get((inst, t, ti, "M")) and inst in set(inst_of.values()):
                d_ = idx[t][1]
                if (a, d_) in rho_ad and ("M", d_) in rho_ad:
                    per_turn[a].append(c * rho_ad[(a, d_)] / (chars[(inst, t, ti, "M")] * rho_ad[("M", d_)]))
        res["length_ratios"] = {"P/M per block, turn 0 (exact tokens), q05/50/95": q(pm), "c_d": c_d,
                                "S/M per turn (predicted tokens), q05/50/95": q(per_turn["S"]),
                                "X/M per turn (predicted tokens), q05/50/95": q(per_turn["X"])}
        for k, C in CONTR.items():
            d = np.array([100 * (y[t]["M"] - y[t][C]) for t in use])
            m, iv = t_iv(d, level)
            intervals[k] = iv
            s_ = [f"{idx[t][0]}-{idx[t][1]}" for t in use]
            dg = dep.diag(d, A_["perm"], A_["perm_seed"])
            half = (iv[1] - iv[0]) / 2
            rstar = dep.rho_star(m, half)
            test_d = [100 * (y[t]["M"] - y[t][C]) for t in use if idx[t][0] == "E3"]
            m4, iv4 = t_iv(test_d, level)
            ng, iv2 = cluster_iv(d, [graph[t]["first_group"] for t in use], level)
            xi = np.array([xlen[C].get(t, np.nan) for t in use])
            ok_x = ~np.isnan(xi)
            w = klen.wr5(d[ok_x], xi[ok_x], level) if ok_x.sum() > 10 else None
            flag, why = klen.len_rule(w, iv, rd.state) if w else (True, ["brak pomiaru długości"])
            length[k] = {"flag": flag, "reasons": why, "adj": w["adj"] if w else (float("nan"), float("nan"))}
            contrasts[k] = {
                "estimate_pp": m, "interval": iv, "level": level, "state": rd.state(*iv), "tasks": len(d),
                "answers": {"positive": {"V1": "tak", "V2": "tak", "V3": "tak", "V6": "nie (ujemny)"}.get(rd.state(*iv), "nierozstrzygnięte"),
                            "at_least_10pp": {"V1": "tak", "V3": "nie", "V5": "nie", "V6": "nie"}.get(rd.state(*iv), "nierozstrzygnięte")},
                "dependence": dict(dg, rho_star=rstar, L2n=dep.L2n, pairs=len(dep.pairs)),
                "WR1_bootstrap": boot_iv(d, s_, level, A_["boot"], A_["boot_seed"]),
                "WR2_first_trace_groups": {"groups": ng, "interval": iv2},
                "WR3_sign_flip_p": sign_flip_p(d, A_["perm"], A_["perm_seed"]),
                "WR4_test_only": {"tasks": len(test_d), "estimate_pp": m4, "interval": iv4, "state": rd.state(*iv4) if not math.isnan(iv4[0]) else None},
                "WR5": dict(w or {}, LEN=flag, LEN_reasons=why, per_task_imbalance_q05_50_95_pct=
                            [float(100 * (math.exp(q) - 1)) for q in np.percentile(xi[ok_x], [5, 50, 95])] if ok_x.any() else None),
            }
            if dg["rho_tilde"] > 0 and dg["p"] < 0.05:
                wide = (m - half * dg["widening"], m + half * dg["widening"])
                res["caveats"].append(f"PRZENOSZALNOŚĆ (nie zmienia stanu głównego): {rd.CONTRASTS[k][0]}: wykryto zależność przez "
                                      f"wspólne ślady (ρ̃ = {dg['rho_tilde']:+.3f}, p = {dg['p']:.3f}); stan przy przedziale "
                                      f"poszerzonym x{dg['widening']:.2f}: {rd.state(*wide)}.")
            for s in sorted(set(s_)):
                sub = [100 * (y[t]["M"] - y[t][C]) for t in use if f"{idx[t][0]}-{idx[t][1]}" == s]
                ms, ivs = t_iv(sub, 0.95)
                if not math.isnan(ivs[0]) and (ivs[0] > 0 or ivs[1] < 0) and np.sign(ms) != np.sign(m) and m != 0:
                    res["caveats"].append(f"{rd.CONTRASTS[k][0]}: zależny od domeny (warstwa {s}: {rd.fmt(ms)} pp, 95% wyklucza 0 "
                                          "ze znakiem przeciwnym).")
    res["contrasts"] = contrasts
    # ---- block A (secondary answer at temperature 0) and drift
    if a_incomplete:
        res["block_A"] = {"status": "NIEUKOŃCZONY", "M-P": {"state": "NIEWAŻNY: blok A NIEUKOŃCZONY (7.2, 7.6; errata E4)"},
                          "note": "blok A nieukończony: odpowiedź drugorzędna NIEWAŻNA, brak kontroli dryfu"}
        res["caveats"].append("Blok A NIEUKOŃCZONY (errata E4): odpowiedź drugorzędna przy temperaturze 0 ma stan NIEWAŻNY; "
                              "brak kontroli dryfu.")
    if YA:
        ba = cells.analyse_block_a(YA, tasks)
        dA = [100 * v for v in ba["d"].values()]
        mA, ivA = t_iv(dA, A_["block_a_level"])
        res["block_A"] = {"M-P": {"estimate_pp": mA, "interval95": ivA, "tasks": len(dA),
                                  "state": "NIEWAŻNY: " + ba["invalid"] if ba["invalid"] else rd.state(*ivA)},
                          "excluded": len(ba["excluded"])}
        o2 = night2_outcomes()
        oc = lambda k: cells.outcome(YA[k]) if k in YA else None
        drift = {}
        for sess, need in (("E3", cfg["drift"]["test_min_agree"]), ("E1", cfg["drift"]["train_min_agree"])):
            ts = [t for t in tasks if idx[t][0] == sess]
            for a in ("N", "M"):
                agree = sum(1 for t in ts if oc((t, a)) is not None and oc((t, a)) == o2[(t, a, sess)])
                drift[f"{sess}/{a}"] = {"agree": agree, "of": len(ts), "min": need, "ok": agree >= need}
            for a in ("P", "M"):
                drift[f"{sess}/{a}-vs-N discordant"] = sum(1 for t in ts if oc((t, a)) is not None and oc((t, "N")) is not None
                                                          and oc((t, a)) != oc((t, "N")))
        drift["NIGHT-2 M-vs-N discordant (E3 34/88, E1 20/60)"] = "reference"
        res["drift_block_A"] = drift
        if not all(v["ok"] for v in drift.values() if isinstance(v, dict)):
            res["caveats"].append("Kontrola dryfu bloku A niespełniona (zgodność N lub M z NIGHT-2 poniżej progu); stany z bloków "
                                  "próbkowanych pozostają ważne.")
        if invalid is None and "MP" in contrasts and not math.isnan(mA) and mA != 0 and \
                np.sign(mA) != np.sign(contrasts["MP"]["estimate_pp"]) and contrasts["MP"]["estimate_pp"] != 0:
            res["caveats"].append("M - P: zależny od reżimu próbkowania (znak w bloku A przeciwny do analizy głównej).")
    # ---- noise (7.7)
    if len(an["completed"]) >= 2 and use:
        comp = an["completed"]
        pairs_b = [(comp[i], comp[j]) for i in range(len(comp)) for j in range(i + 1, len(comp))]
        oc = lambda t, a, b: cells.outcome(Y[(t, a, b)]) if (t, a, b) in Y else None
        res["noise"] = {"w": {a: float(np.mean([np.mean([oc(t, a, b1) != oc(t, a, b2) for t in use
                                                          if oc(t, a, b1) is not None and oc(t, a, b2) is not None])
                                                 for b1, b2 in pairs_b])) for a in ARMS5},
                        "b": {f"M,{C}": float(np.mean([np.mean([oc(t, "M", b) != oc(t, C, b) for t in use
                                                                 if oc(t, "M", b) is not None and oc(t, C, b) is not None]) for b in comp]))
                              for C in ("N", "P", "X", "S")}}
        need = {}
        for k, C in CONTR.items():
            per = [[oc(t, "M", b) - oc(t, C, b) for b in an["used_blocks"][t]] for t in use]
            s_rep = float(np.mean([np.var(v, ddof=1) if len(v) > 1 else 0.0 for v in per]))
            dd = np.array([np.mean(v) for v in per])
            R = len(comp)
            s_task = max(0.0, float(np.var(dd, ddof=1)) - s_rep / R)
            z = stats.norm.ppf(1 - (1 - level) / 2)
            need[k] = {"var_rep": s_rep, "var_task": s_task,
                       "tasks_needed": {f"half {h} pp, R={r}": math.ceil((z * 100 * math.sqrt(s_task + s_rep / r) / h) ** 2)
                                        for h in (2.5, 5.0) for r in (1, 3, 5)}}
        res["noise"]["variance"] = need
        wm = float(np.mean(list(res["noise"]["w"].values())))
        bm = float(np.mean(list(res["noise"]["b"].values())))
        res["noise"]["vs_simulation"] = {"w_measured": wm, "w_assumed": [0.02, 0.28], "b_measured": bm, "b0_columns": [0.20, 0.30, 0.38],
                                         "column": min((0.20, 0.30, 0.38), key=lambda c: abs(c - bm)),
                                         "pilot_measured_spec_9_0": {"w": 0.159, "b": 0.307, "detect_10pp": 0.643,
                                                                     "exclude_10pp_at_0": 0.615},
                                         "note": "2 bloki" if len(comp) == 2 else "3 bloki"}
    # ---- descriptive extras
    if recs_by_block:
        allr = [(b, k, r) for b, rr in recs_by_block.items() for k, r in rr.items()]
        res["prompt_tokens_per_call"] = {a: float(np.mean([s["prompt_eval_count"] for b, k, r in allr if k[1] == a
                                                            for tu in r["episode"]["turns"] for s in tu["steps"]
                                                            if s.get("prompt_eval_count") is not None] or [np.nan])) for a in ARMS5}
        pm_ = res["prompt_tokens_per_call"].get("M")
        res["prompt_tokens_vs_M_flag_over_10pct"] = {a: (v / pm_ - 1, abs(v / pm_ - 1) > 0.10) for a, v in res["prompt_tokens_per_call"].items()
                                                     if pm_ and a != "M"}
        bfcl = kl.make_bfcl_k1(p0, xv, n1)(kl.BFCL)
        fnames = {t: {f["name"] for f in bfcl.functions(bfcl.tasks[t])} for t in idx}
        res["invalid_and_unknown_calls"] = {a: {
            "invalid_outputs": sum(1 for b, k, r in allr if k[1] == a for tu in r["episode"]["turns"] for s in tu["steps"] if s.get("invalid_output")),
            "invalid_calls": sum(1 for b, k, r in allr if k[1] == a for tu in r["episode"]["turns"] for s in tu["steps"]
                                 for c in s.get("calls", []) if not c.get("valid")),
            "nonexistent_functions": sum(1 for b, k, r in allr if k[1] == a for tu in r["episode"]["turns"] for s in tu["steps"]
                                         for c in s.get("calls", []) if not c.get("valid") and isinstance(c.get("raw"), dict)
                                         and c["raw"].get("name") not in fnames[k[0]])} for a in ARMS5}
        res["calls_per_episode"] = {a: float(np.mean([r["calls"] for b, k, r in allr if k[1] == a])) for a in ARMS5}
        if use:
            res["gains_losses_vs_N"] = {a: {"gains": sum(y[t][a] > y[t]["N"] for t in use), "losses": sum(y[t][a] < y[t]["N"] for t in use)}
                                        for a in ("P", "X", "S", "M")}
        res["L9"] = l9(idx, stim, sorted(set(inst_of.values())))
    # ---- reading (generated by the frozen code)
    if invalid is None and set(intervals) != set(CONTR):
        invalid = "brak przedziałów kontrastów"
    reading = rd.read(intervals, est_desc, invalid, length if invalid is None else None)
    reading += res["caveats"]
    hits = rd.forbidden_hits(reading)
    res["reading"] = reading
    res["interpretation_rule_D1"] = D1_RULE
    res["invalid"] = invalid
    res["forbidden_hits"] = hits
    return res


def render(res) -> str:
    j = lambda o: json.dumps(o, ensure_ascii=False, default=float)
    lines = ["# K1 (EXP-PLACEBO-0): raport końcowy (generowany z zamrożonych danych)", "",
             f"> {res['interpretation_rule_D1']}", "",
             "## Odczyt (kod `k1_v04_reading.read`)", ""] + [f"- {s}" for s in res["reading"]] + ["",
             "## Stan bloków i bramek", "", f"- bloki próbkowane: `{j(res['blocks'])}`",
             f"- ukończone i użyte: `{j(res.get('completed_sampled_blocks'))}`; wykluczone zadania: {len(res.get('excluded_tasks', []))}",
             f"- bramki i etap T: `{j(res['gates'])}`", f"- kontrola przecieków po przebiegu: `{j(res['postrun_leak'])}`", ""]
    if res.get("contrasts"):
        lines += ["## Kontrasty główne", "", "| kontrast | estymata pp | przedział | stan | ρ̂ | ρ̃ | p | ρ* | WR4 (88) | LEN |", "|---|---|---|---|---|---|---|---|---|---|"]
        for k, c in res["contrasts"].items():
            dg = c["dependence"]
            lines.append(f"| {rd.CONTRASTS[k][0]} | {c['estimate_pp']:+.1f} | [{c['interval'][0]:.1f}; {c['interval'][1]:.1f}] | {c['state']} | "
                         f"{dg['rho_hat']:+.3f} | {dg['rho_tilde']:+.3f} | {dg['p']:.3f} | {'brak' if dg['rho_star'] is None else round(dg['rho_star'], 3)} | "
                         f"{c['WR4_test_only']['state']} | {c['WR5'].get('LEN')} |")
        lines.append("")
    for key, title in (("ladder", "Drabina opisowa (95%)"), ("block_A", "Blok A (temperatura 0)"), ("drift_block_A", "Kontrola dryfu"),
                       ("noise", "Pomiar szumu"), ("tokens_per_char_turn0", "Tokeny na znak (tura 0)"),
                       ("prompt_tokens_per_call", "Tokeny promptu na wywołanie"), ("invalid_and_unknown_calls", "Błędne wywołania"),
                       ("gains_losses_vs_N", "Zyski i straty wobec N"), ("L9", "Miara L9"), ("rates", "Odsetki rozwiązań (%)"),
                       ("length_ratios", "Kontrola długości (sek. 11 pkt 8)"), ("prompt_tokens_vs_M_flag_over_10pct", "Tokeny promptu względem M"),
                       ("preparation_checks", "Kontrole przygotowania L1–L4b, L10")):
        if key in res:
            lines += [f"## {title}", "", "```json", json.dumps(res[key], ensure_ascii=False, indent=1, default=float), "```", ""]
    return "\n".join(lines) + "\n"


def main():
    base = Path(sys.argv[sys.argv.index("--base") + 1])
    L = kl.layout(base)
    cfg = kl.load_cfg()
    res = final(L, cfg)
    L["report"].mkdir(parents=True, exist_ok=True)
    kl.write_json(L["report"] / "results.json", res, indent=1)
    (L["report"] / "K1_RAPORT.md").write_text(render(res), encoding="utf-8")
    if res["forbidden_hits"]:
        print("FORBIDDEN SENTENCES:", res["forbidden_hits"])
        raise SystemExit(2)
    print("FINAL REPORT written;", "INVALID: " + res["invalid"] if res["invalid"] else
          "states " + json.dumps({k: c["state"] for k, c in res["contrasts"].items()}))


if __name__ == "__main__":
    main()
