"""K1: offline checks of the risks behind the technical choices T1-T11 and of the approval coverage (D6, D11).
No model, no Ollama. Reads NIGHT-2 responses/sessions (known data; only token counts, call counts and memory items),
the pilot's stim/ (not sealed/, not run/), and the prepared K1 base.
 R1 (T6)  are NIGHT-2 prompt_eval_count values full prompt counts or cache remainders?
 R2 (T3/T4/T5) how often does the T-length (b) gate fail by chance on 10 blocks, if P tokens were exactly proportional
          to characters? (sweep of the unknown prose tokens/char; per-block noise of the prose ratio)
 R3 (T2)  how representative are the 12 m-measurement tasks? (calls/episode in NIGHT-2 at temperature 0)
 R4 (D6/D11) K1 stimuli vs the pilot's stimuli: same tasks, pools, plans
Run: python -I -X utf8 -B tests/t_risks_T.py"""
from __future__ import annotations

import collections
import json
import math
import random
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "code"))
import k1_lib as kl  # noqa: E402

BASE = HERE.parent / "base"
PILOT = Path("D:/aamr-audit-2026-11-13/pilot-nm/stim")
out, ok = [], {}
P = lambda *a: (print(*a, flush=True), out.append(" ".join(map(str, a))))
stim = BASE / "stim"
idx = kl.task_index(kl.read_json(stim / "k1_tasks.json"))
tok = kl.read_json(stim / "k1_tokref.json")
tl = kl.read_json(stim / "k1_T_tasks.json")
corpus = kl.read_json(stim / "k1_corpus_P.json")["sentences"]
n2, p0, xv, n1 = kl.import_harness()

# ---------------------------------------------------------------- R1 prompt_eval_count: full or cached remainder?
KEY = re.compile(r'"key": "(E3|E1):(N|E\*|R\+):(multi_turn_base_\d+):t(\d+):s(\d+)"')
pec, req_sha = {}, {}
for r in kl.rows(kl.NRESP):
    m = KEY.search(json.dumps({"key": r["key"]}))
    if m:
        pec[m.groups()] = (r.get("usage") or {}).get("prompt_eval_count")
        req_sha[m.groups()] = r["request_sha256"]
grow, total = 0, 0
for (st, arm, t, ti, si), v in pec.items():
    nxt = pec.get((st, arm, t, ti, str(int(si) + 1)))
    if v is not None and nxt is not None:
        total += 1
        grow += nxt > v
same_req = [(k, pec[k], pec[k2]) for k in pec for k2 in [(k[0], "N", k[2], k[3], k[4])]
            if k[1] != "N" and k2 in pec and req_sha[k] == req_sha[k2]]
eq = sum(a == b for _, a, b in same_req)
small = sum(1 for v in pec.values() if v is not None and v < 500)
P(f"R1 NIGHT-2 prompt_eval_count: step s+1 larger than step s in {grow}/{total} consecutive pairs (full counts grow with the "
  f"history; cache remainders would be small); identical requests in two arms (empty M block) with equal counts {eq}/{len(same_req)}; "
  f"counts below 500 tokens {small}/{len(pec)}")
ok["R1"] = total > 1000 and grow == total and len(same_req) > 0 and eq == len(same_req)

# ---------------------------------------------------------------- R2 T-length (b) on 10 blocks
plans = kl.plan_turns(kl.read_json(stim / "k1_plans_M.json"), idx)
pools = {d: kl.read_json(stim / f"k1_pool_{d}.json") for d in kl.DOMAINS}
by_id = {p0.pool_row_id(r): r for d in kl.DOMAINS for r in pools[d]}
mblock = {t: p0.render_block([by_id[i] for i in plans[t][0]]) for t in tok["m_t0_tokens"]}


def t_length(d, cal, chk, rho_p, noise, rng, label=("cal", "len")):
    """Simulated stage T with P tokens = rho_p * chars * (1 + noise_block); returns rel of the domain sum."""
    f = lambda: 1 + rng.gauss(0, noise)
    cal_tok = cal_chr = 0.0
    for t in cal:
        pb = kl.build_p(mblock[t], corpus, 1.0, (t, 0, label[0]))
        cal_tok += rho_p * len(pb) * f()                        # C1: block characters
        cal_chr += len(pb)
    c = tok["rho_dom"][d] / (cal_tok / cal_chr)
    ptok = sum(rho_p * len(kl.build_p(mblock[t], corpus, c, (t, 0, label[1]))) * f() for t in chk)
    return ptok / sum(tok["m_t0_tokens"][t] for t in chk) - 1


rows = []
for rho_p in (0.20, 0.23, 0.26, 0.29):
    for noise in (0.0, 0.03):
        rng = random.Random(11)
        det = {d: t_length(d, tl["cal"][d], tl["len"][d], rho_p, noise, rng) for d in kl.DOMAINS}
        fails, sims = collections.Counter(), 300
        for s in range(sims):
            for d in kl.DOMAINS:
                ts = [t for t in tok["m_t0_tokens"] if idx[t][1] == d]
                pick = rng.sample(ts, 20)
                if abs(t_length(d, pick[:10], pick[10:], rho_p, noise, rng)) > 0.05:
                    fails[d] += 1
        rows.append((rho_p, noise, det, {d: fails[d] / sims for d in kl.DOMAINS}))
        P(f"R2 prose tokens/char {rho_p:.2f}, per-block prose noise sd {noise:.0%}: frozen T tasks rel " +
          ", ".join(f"{d} {100 * v:+.1f}%" for d, v in det.items()) + "; random 10+10 splits failing +-5%: " +
          ", ".join(f"{d} {100 * v:.0f}%" for d, v in rows[-1][3].items()))
worst_frozen = max(abs(v) for r in rows for v in r[2].values())
P(f"R2 worst |rel| on the frozen T task lists over the sweep: {100 * worst_frozen:.1f}% (gate 5%)")
ok["R2"] = worst_frozen <= 0.05

# ---------------------------------------------------------------- R3 m tasks
calls = collections.defaultdict(dict)
for sess in ("E3", "E1"):
    for r in kl.rows(kl.NRUN / "sessions" / f"{sess}.jsonl"):
        if r["arm"] in ("N", kl.NIGHT2_M_ARM[sess]):
            calls[r["arm"] if r["arm"] == "N" else "M"][r["task"]] = sum(1 for tu in r["episode"]["turns"] for s in tu["steps"] if "key" in s)
m12 = [calls["N"][t] for t in tl["m_tasks"]]
allN, allM = list(calls["N"].values()), list(calls["M"].values())
trainN = [calls["N"][t] for t in idx if idx[t][0] == "E1"]
rng = random.Random(3)
sub = [statistics.mean(rng.sample(trainN, 12)) for _ in range(5000)]
ratio = statistics.mean(allN + allM) / statistics.mean(m12)
P(f"R3 NIGHT-2 (temperature 0) calls/episode: 12 m tasks {statistics.mean(m12):.2f}; N on 60 training {statistics.mean(trainN):.2f}; "
  f"N on 148 {statistics.mean(allN):.2f}; N+M on 148 {statistics.mean(allN + allM):.2f}; random 12 of 60 training: 5-95% "
  f"{sorted(sub)[250]:.2f}-{sorted(sub)[4750]:.2f}; the 1.10 margin covers an underestimate of {100 * (ratio - 1):+.1f}% for these 12 tasks")
ok["R3"] = len(m12) == 12

# ---------------------------------------------------------------- R4 K1 vs pilot stimuli
same = {}
for f in ("k1_tasks.json", "k1_plans_M.json", "k1_pool_VC.json", "k1_pool_GFS.json", "k1_pool_TRAVEL.json"):
    same[f] = kl.read_json(stim / f) == kl.read_json(PILOT / f)
P(f"R4 K1 stimuli equal (parsed JSON) to the pilot's frozen stimuli: {same}")
ok["R4"] = all(same.values())
P(f"RESULT RISKS T: {'PASS' if all(ok.values()) else 'FAIL'} {ok}")
(HERE / "WYNIKI_RYZYKA_T.out").write_text("\n".join(out) + "\n", encoding="utf-8")
