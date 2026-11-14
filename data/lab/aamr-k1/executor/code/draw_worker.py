"""K1 stimulus process (spec sec. 2 X, S; D12; sec. 5 L6a): token reference table and the S and X draws, under the audit hook.

Reads only: the extracted task lists, pools and M plans (stim/), the K1 config, and NIGHT-2's responses.jsonl for the
prompt_eval_count of turn 0, step 0 of the NIGHT-2 arms N and M (E3: N, E*; E1: N, R+). responses.jsonl holds model
responses and token counts, no ground truth; lines naming TradingBot tasks are skipped before parsing.
Writes stim/k1_tokref.json and stim/k1_draws_SX.json (both hashed in L8 by prepare.py).
argv: stim_dir"""
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import k1_audit_hook as hook  # noqa: E402
import k1_lib as kl  # noqa: E402

STIM = Path(sys.argv[1]).resolve()
hook.install(read_files=[kl.NRESP, kl.CONFIG, STIM / "k1_tasks.json", STIM / "k1_plans_M.json"]
             + [STIM / f"k1_pool_{d}.json" for d in kl.DOMAINS],
             code_roots=[sys.base_prefix, sys.prefix, kl.SCRIPTS, kl.CODE], run_dirs=[STIM])

import collections  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402

sys.path.insert(0, str(kl.SCRIPTS))
import experience_pilot_v0 as p0  # noqa: E402

cfg = kl.load_cfg()
tasks = kl.read_json(STIM / "k1_tasks.json")
idx = kl.task_index(tasks)
plans = kl.read_json(STIM / "k1_plans_M.json")
turns = kl.plan_turns(plans, idx)
pools = {d: kl.read_json(STIM / f"k1_pool_{d}.json") for d in kl.DOMAINS}
by_id = {p0.pool_row_id(r): r for d in kl.DOMAINS for r in pools[d]}
HDR = len(p0.MEMORY_HEADER) + 1
cchars = lambda ids: max(0, len(p0.render_block([by_id[i] for i in ids])) - HDR) if ids else 0

# ---------------------------------------------------------------- token reference (turn 0, step 0, NIGHT-2)
KEY = re.compile(r'"key": "(E3|E1):(N|E\*|R\+):(multi_turn_base_\d+):t0:s0"')
pec = {}
with open(kl.NRESP, encoding="utf-8") as fh:
    for line in fh:
        m = KEY.search(line[:200])
        if not m or not kl.not_trading(line):
            continue
        r = json.loads(line)
        st, arm, t = m.groups()
        if t in idx and idx[t][0] == st:
            pec[(t, "N" if arm == "N" else "M")] = (r.get("usage") or {}).get("prompt_eval_count")
nref, mtok, mchr, rho_task = {}, {}, {}, {}
tok_d, chr_d, n_d = collections.Counter(), collections.Counter(), collections.Counter()
for t, (st, d, part) in sorted(idx.items()):
    if pec.get((t, "N")) is not None:
        nref[t] = pec[(t, "N")]
    ids0 = turns[t].get(0, [])
    if not ids0 or pec.get((t, "M")) is None or t not in nref:
        continue
    block = p0.render_block([by_id[i] for i in ids0])
    tok = pec[(t, "M")] - nref[t]
    mtok[t], mchr[t] = tok, len(block)                       # C1 (owner 2026-11-13): v1.0 sec. 2, block characters
    rho_task[t] = tok / mchr[t]
    tok_d[d] += tok
    chr_d[d] += mchr[t]
    n_d[d] += 1
rho_dom = {d: tok_d[d] / chr_d[d] for d in kl.DOMAINS}
tokref = {"nref": nref, "m_t0_tokens": mtok, "m_t0_chars": mchr, "rho_task": rho_task, "rho_dom": rho_dom,
          "blocks_per_domain": dict(n_d), "basis": "tokens / block characters (v1.0 sec. 2; C1), turn 0 step 0",
          "source": "NIGHT-2 responses.jsonl usage.prompt_eval_count, keys <E3|E1>:<N|E*|R+>:<task>:t0:s0"}
(STIM / "k1_tokref.json").write_text(json.dumps(tokref, sort_keys=True), encoding="utf-8")

# ---------------------------------------------------------------- S and X draws (instances 1-3 = sampled blocks S1-S3)
NXT = cfg["x_domain_map"]
D12 = cfg["d12"]
draws = {"X": {}, "S": {}}
stats = {"X": collections.Counter(), "S": collections.Counter()}
for inst in (1, 2, 3):
    X, S = {}, {}
    for t, (st, d, part) in sorted(idx.items()):
        mine = {i for ids in turns[t].values() for i in ids}
        avail = [p0.pool_row_id(r) for r in pools[d] if r["source_task"] != t and p0.pool_row_id(r) not in mine]
        xpool = [p0.pool_row_id(r) for r in pools[NXT[d]]]
        rM = rho_task.get(t, rho_dom[d])
        used = set()
        for ti in sorted(turns[t]):
            ids = turns[t][ti]
            k = f"{t}:{ti}"
            if not ids:
                X[k], S[k] = [], []
                continue
            if D12["enabled"]:
                target = cchars(ids) * rM
                s, sa, sv = kl.matched_draw(f"S|{t}|{ti}|{inst}", avail, len(ids), target, rho_dom[d], cchars, used,
                                            D12["attempts"], D12["tolerance"])
                x, xa, xv_ = kl.matched_draw(f"X|{t}|{ti}|{inst}", xpool, len(ids), target, rho_dom[NXT[d]], cchars,
                                             None, D12["attempts"], D12["tolerance"])
                stats["S"]["matched" if sa < D12["attempts"] else "closest"] += 1
                stats["X"]["matched" if xa < D12["attempts"] else "closest"] += 1
            else:                                                  # NOT APPROVED variant (v0.4 before D12): count only
                rng = random.Random(f"{t}|{ti}|{inst}")
                s = kl.unmatched_draw(rng, avail, len(ids), used)
                x = kl.unmatched_draw(rng, xpool, len(ids))
            stats["S"]["repeats_within_task"] += len([i for i in s if i in used])
            used.update(s)
            S[k], X[k] = list(s), list(x)
    draws["X"][str(inst)], draws["S"][str(inst)] = X, S
draws["sha256"] = {a: kl.sha_obj(draws[a]) for a in ("X", "S")}
draws["rule"] = ("D12 log rule of the frozen prototype t_d9_length.py: |ln(predicted/target)| <= ln 1.2, i.e. -16.67%..+20%; "
                 "200 attempts, else closest by |ln| (owner choice C2, 2026-11-13; formal status: ANEKS_C2_D12.md)"
                 if D12["enabled"] else "count only (NOT APPROVED variant, D12 off)")
draws["stats"] = {a: dict(c) for a, c in stats.items()}
(STIM / "k1_draws_SX.json").write_text(json.dumps(draws, sort_keys=True), encoding="utf-8")
print("DRAWN", json.dumps({"tokref_tasks": len(nref), "m_t0_blocks": dict(n_d), "stats": draws["stats"]}))
