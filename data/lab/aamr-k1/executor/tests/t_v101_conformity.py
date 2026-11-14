"""K1: conformity of the executor with the frozen v1.0.1 (errata E1-E4 = owner's decisions C1-C4, 2026-11-13), and the data
of the C2 annex. No model. Reads the prepared base (stim/), the executor's code and k1/v1.0.1/FREEZE.json.
 F   stimuli k1_draws_SX.json and k1_tokref.json byte-identical to the external references pinned in v1.0.1 FREEZE.json
 E4  secondary answer (7.6) NIEWAŻNY when block A is NIEUKOŃCZONY (behaviour: run_tests.py U16)
 C1  rho = sum of block tokens / sum of block characters (v1.0 sec. 2): token reference and stage T use block characters.
 C2  D12 tolerance. Chosen method (owner): logarithmic rule of the frozen prototype t_d9_length.py (|ln(pred/target)| <= ln 1.2).
     Checks that the frozen draws equal the draws regenerated with that rule, and measures: bounds, draws that change under the
     literal linear +-20%, draws that differ from the prototype's own basis (chars + 2, i.e. before C1), predicted per-task
     length imbalance, and the share of true content effects that rule LEN would withhold (as t_d9_length.py part B).
 C3  WR5 later turns: content characters (v1.0 sec. 7.5).
 C4  block A after a second error / hard limit: NIEUKOŃCZONY (behaviour tested in run_tests.py U16).
Run: python -I -X utf8 -B tests/t_v10_conformity.py"""
from __future__ import annotations

import inspect
import math
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
sys.path.insert(0, str(CODE))
import k1_length as klen  # noqa: E402
import k1_lib as kl  # noqa: E402
from k1_v04_reading import state  # noqa: E402

stim = HERE.parent / "base" / "stim"
cfg = kl.load_cfg()
n2, p0, xv, n1 = kl.import_harness()
idx = kl.task_index(kl.read_json(stim / "k1_tasks.json"))
turns = kl.plan_turns(kl.read_json(stim / "k1_plans_M.json"), idx)
pools = {d: kl.read_json(stim / f"k1_pool_{d}.json") for d in kl.DOMAINS}
by_id = {p0.pool_row_id(r): r for d in kl.DOMAINS for r in pools[d]}
tok = kl.read_json(stim / "k1_tokref.json")
draws = kl.read_json(stim / "k1_draws_SX.json")
NXT = cfg["x_domain_map"]
HDR = len(kl.HEADER) + 1
out, ok = [], {}
P = lambda *a: (print(*a, flush=True), out.append(" ".join(map(str, a))))

# ---------------------------------------------------------------- C1
lit = all(tok["m_t0_chars"][t] == len(p0.render_block([by_id[i] for i in turns[t][0]])) for t in tok["m_t0_chars"])
src_w = (CODE / "worker.py").read_text(encoding="utf-8")
c1 = lit and "chars = len(pb)  " in src_w and "len(pb) + 2" not in src_w and "len(block) + 2" not in (CODE / "draw_worker.py").read_text(encoding="utf-8")
P(f"C1 token reference uses block characters for {len(tok['m_t0_chars'])} blocks: {lit}; stage T uses block characters: {c1}")
ok["C1"] = c1

# ---------------------------------------------------------------- C3
import analyze as an  # noqa: E402
c3 = "len(kl.content(txt))" in inspect.getsource(an.stimulus_chars)
P(f"C3 WR5 uses content characters for every turn (turn-0 tokens exact, rho per content character): {c3}")
ok["C3"] = c3
src_a = inspect.getsource(an.final)
e4 = "NIEWAŻNY: blok A NIEUKOŃCZONY" in src_a and 'A_INCOMPLETE.json' in src_a
P(f"E4 analysis gives block A NIEUKOŃCZONY and the secondary answer the state NIEWAŻNY: {e4}")
ok["E4"] = e4
import hashlib, json  # noqa: E401,E402
fz = json.loads(Path("D:/aamr-audit-2026-11-13/k1/v1.0.1/FREEZE.json").read_text(encoding="utf-8"))
pinned = {k: v for k, v in fz["external_references"].items() if k.endswith((".json",))}
same_f = {Path(k).name: hashlib.sha256(Path(k).read_bytes()).hexdigest() == v for k, v in pinned.items()}
P(f"F stimuli identical to the hashes pinned in v1.0.1 FREEZE.json: {same_f}")
ok["F"] = len(same_f) == 2 and all(same_f.values())

# ---------------------------------------------------------------- C2
cch = lambda ids: max(0, len(p0.render_block([by_id[i] for i in ids])) - HDR) if ids else 0
rho_proto = {}
for d in kl.DOMAINS:                                                  # prototype basis (chars + 2), i.e. before C1
    ts = [t for t in tok["m_t0_tokens"] if idx[t][1] == d]
    rho_proto[d] = sum(tok["m_t0_tokens"][t] for t in ts) / sum(tok["m_t0_chars"][t] + 2 for t in ts)
rho_task_proto = {t: tok["m_t0_tokens"][t] / (tok["m_t0_chars"][t] + 2) for t in tok["m_t0_tokens"]}


def draw(rule, rho_dom, rho_task):
    res, fb = {"X": {}, "S": {}}, {"X": 0, "S": 0}
    ratios = {"X": [], "S": []}
    for inst in (1, 2, 3):
        for t, (st, d, part) in sorted(idx.items()):
            mine = {i for ids in turns[t].values() for i in ids}
            avail = [p0.pool_row_id(r) for r in pools[d] if r["source_task"] != t and p0.pool_row_id(r) not in mine]
            xpool = [p0.pool_row_id(r) for r in pools[NXT[d]]]
            rM = rho_task.get(t, rho_dom[d])
            used = set()
            for ti in sorted(turns[t]):
                ids = turns[t][ti]
                if not ids:
                    continue
                target = cch(ids) * rM
                for arm, cand_pool, rho, u in (("S", avail, rho_dom[d], used), ("X", xpool, rho_dom[NXT[d]], None)):
                    best, bestv, pick = None, None, None
                    for att in range(200):
                        r = random.Random(f"{arm}|{t}|{ti}|{inst}|{att}")
                        cand = [i for i in cand_pool if not u or i not in u]
                        pk = r.sample(cand if len(cand) >= len(ids) else cand_pool, len(ids))
                        ratio = max(1, cch(pk)) * rho / target
                        v = abs(math.log(ratio)) if rule == "log" else abs(ratio - 1)
                        if v <= (math.log(1.2) if rule == "log" else 0.2):
                            pick = pk
                            break
                        if bestv is None or v < bestv:
                            best, bestv = pk, v
                    if pick is None:
                        fb[arm] += 1
                        pick = best
                    ratios[arm].append(max(1, cch(pick)) * rho / target)
                    res[arm][f"{t}:{ti}:{inst}"] = pick
                    if arm == "S":
                        used.update(pick)
    return res, fb, ratios


def xs(res, rho_dom, rho_task):
    o = {"X": [], "S": []}
    for t, (st, d, part) in sorted(idx.items()):
        TM = sum(cch(ids) for ids in turns[t].values()) * rho_task.get(t, rho_dom[d])
        if TM == 0:
            continue
        for arm in ("X", "S"):
            TC = sum(cch(res[arm].get(f"{t}:{ti}:{i}", [])) * rho_dom[d if arm == "S" else NXT[d]] for i in (1, 2, 3) for ti in turns[t]) / 3
            o[arm].append(math.log(TM / TC))
    return {a: np.array(v) for a, v in o.items()}


def len_withheld(x, sims=600, seed=11):
    """t_d9_length.py part B (unchanged model): content effect +15 pp, no length effect; share of detected effects that
    rule LEN withholds, with the per-task imbalance x drawn from this variant."""
    g = np.random.default_rng(seed)
    det = fl = 0
    for _ in range(sims):
        xi = g.choice(x, 148)
        pM = np.clip(g.beta(0.9, 1.1, 148), 0.03, 0.97)
        pC = np.clip(pM - 0.15, 0.01, 0.99)
        d = 100 * ((g.random((3, 148)) < pM).mean(0) - (g.random((3, 148)) < pC).mean(0))
        L, U = klen.t_interval(d)
        if state(L, U) not in ("V1", "V2", "V3"):
            continue
        det += 1
        fl += klen.len_rule(klen.wr5(d, xi), (L, U), state)[0]
    return fl / det if det else float("nan")


frozen = {a: {f"{k}:{i}": v for i, m in draws[a].items() for k, v in m.items() if v} for a in ("X", "S")}
V = {"log, literal rho (chosen; C1 + C2)": draw("log", tok["rho_dom"], tok["rho_task"]),
     "linear +-20%, literal rho (literal v1.0 text)": draw("lin", tok["rho_dom"], tok["rho_task"]),
     "log, prototype rho chars+2 (t_d9_length.py, source of the v1.0 numbers)": draw("log", rho_proto, rho_task_proto)}
chosen = V["log, literal rho (chosen; C1 + C2)"][0]
same = all(chosen[a][k] == frozen[a][k] for a in ("X", "S") for k in frozen[a]) and all(len(frozen[a]) == len(chosen[a]) for a in ("X", "S"))
P(f"C2 bounds: log rule accepts predicted/target in [{1 / 1.2:.4f}; 1.2000] (-16.67% .. +20.00%); linear +-20% accepts [0.8000; 1.2000]. "
  f"Difference: ratios in [0.8000; 0.8333) accepted only by the linear rule")
P(f"C2 frozen stimuli (base/stim/k1_draws_SX.json, rule '{draws['rule']}') equal the draws regenerated with the chosen log rule: {same}")
ok["C2_stimuli"] = same and draws["rule"].startswith("D12")
for name, (res, fb, rat) in V.items():
    x = xs(res, tok["rho_dom"] if "literal" in name else rho_proto, tok["rho_task"] if "literal" in name else rho_task_proto)
    ch = {a: sum(res[a][k] != chosen[a][k] for k in chosen[a]) for a in ("X", "S")}
    imb = {a: 100 * (math.exp(v.mean()) - 1) for a, v in x.items()}
    q = {a: [round(100 * (math.exp(z) - 1), 1) for z in np.percentile(v, [5, 95])] for a, v in x.items()}
    short = {a: float(np.mean([r_ < 1 / 1.2 for r_ in rat[a]])) for a in ("X", "S")}
    wh = {a: len_withheld(x[a]) for a in ("X", "S")}
    P(f"C2 [{name}]: turn draws different from the chosen stimuli X {ch['X']}/{len(chosen['X'])}, S {ch['S']}/{len(chosen['S'])}; "
      f"fallback to the closest X {fb['X']}, S {fb['S']}; accepted ratio below 0.8333 X {short['X']:.1%}, S {short['S']:.1%}; "
      f"mean per-task imbalance M vs X {imb['X']:+.2f}% (5-95% {q['X']}), M vs S {imb['S']:+.2f}% (5-95% {q['S']}); B1 met "
      f"{all(abs(v.mean()) <= klen.B1 for v in x.values())}; LEN withholds true +15 pp effects X {wh['X']:.0%}, S {wh['S']:.0%}")
P(f"RESULT v1.0.1 CONFORMITY: {'PASS' if all(ok.values()) else 'FAIL'} {ok} (E1-E4 of spec v1.0.1)")
(HERE / "WYNIKI_ZGODNOSC_v1.0.1.out").write_text("\n".join(out) + "\n", encoding="utf-8")
