import sys, re, random; sys.path.insert(0, '.')
from common import *
from scipy import stats
idx = tasks_index(); tasks = sorted(idx)
Yd = Y(); y = ymeans(Yd, idx)
HDR = "EXPERIENCE FROM EARLIER TASKS (it may or may not be relevant; use it only if it helps):"
INST = {"S1": 1, "S2": 2, "S3": 3}
S = {}
for b in BLOCKS:
    for r in rows(BASE / f"run/sessions/{b}.jsonl"):
        S[(r["task"], r["arm"], b)] = r
plans = json.load(open(BASE / "stim/k1_plans_M.json", encoding="utf-8"))
pl = {}
for part in plans:
    for d in plans[part]:
        for k, ids in plans[part][d].items():
            t, ti = k.rsplit(":", 1); pl.setdefault(t, {})[int(ti)] = ids
draws = json.load(open(BASE / "stim/k1_draws_SX.json", encoding="utf-8"))
corpus = json.load(open(BASE / "stim/k1_corpus_P.json", encoding="utf-8"))["sentences"]
c_d = json.load(open(BASE / "run/c_d.json", encoding="utf-8"))["c_d"]
# per-trace rendered body from recorded blocks: content = "[1] " + body1 + "\n[2] " + body2 ...
body = {}
for (t, a, b), r in S.items():
    for tu in r["episode"]["turns"]:
        ids = tu["memory"]["items"] or []; txt = tu["memory"].get("block_text") or ""
        if a in "MSX" and ids:
            content = txt[len(HDR) + 1:]
            parts = re.split(r"(?:^|\n)\[\d+\] ", content)[1:]
            assert len(parts) == len(ids), (t, a, b, len(parts), len(ids))
            for i, p in zip(ids, parts):
                assert body.get(i, p) == p; body[i] = p
print("traces with known rendering:", len(body))
def trace_len(ids):
    return sum(len(f"[{k+1}] ") + len(body[i]) for k, i in enumerate(ids)) + max(0, len(ids) - 1)
def build_p_len(m_len, c, seed):
    if not m_len: return 0
    target = round(c * m_len); rng = random.Random(repr(seed)); order = list(range(len(corpus))); rng.shuffle(order)
    out, k = "", 0
    while True:
        s = corpus[order[k % len(order)]]; k += 1
        cand = (out + " " + s) if out else s
        if len(cand) <= target:
            out = cand
            if len(out) == target: break
            continue
        best = cand; words = s.rstrip(".").split(" ")
        for j in range(1, len(words)):
            piece = " ".join(words[:j]) + "."; alt = (out + " " + piece) if out else piece
            if abs(len(alt) - target) < abs(len(best) - target): best = alt
        if out and abs(len(out) - target) <= abs(len(best) - target): best = out
        out = best; break
    return len(out)
chars = {}; unknown = 0
for inst in (1, 2, 3):
    for t in tasks:
        d = idx[t][1]
        for ti, ids in pl[t].items():
            try: m = trace_len(ids) if ids else 0
            except KeyError: m = None; unknown += 1
            chars[(inst, t, ti, "M")] = m
            chars[(inst, t, ti, "P")] = build_p_len(m, c_d[d], (t, ti, inst)) if m is not None else None
            for a in "SX":
                ids2 = draws[a][str(inst)].get(f"{t}:{ti}", [])
                try: chars[(inst, t, ti, a)] = trace_len(ids2) if ids2 else 0
                except KeyError: chars[(inst, t, ti, a)] = None; unknown += 1
print("cells with unknown trace rendering:", unknown)
# validate against recorded cells
bad = n = 0
for (t, a, b), r in S.items():
    if a == "N": continue
    for tu in r["episode"]["turns"]:
        txt = tu["memory"].get("block_text") or ""; rec = len(txt) - len(HDR) - 1 if txt else 0
        n += 1; bad += chars[(INST[b], t, tu["index"], a)] != rec
print("reconstructed chars vs recorded:", n - bad, "equal of", n)
pec0 = {(b, t, a): r["episode"]["turns"][0]["steps"][0]["prompt_eval_count"] for (t, a, b), r in S.items()}
tok0 = collections.Counter(); chr0 = collections.Counter(); exact = {}
for (b, t, a), p in pec0.items():
    if a == "N": continue
    c = chars[(INST[b], t, 0, a)]
    if c: exact[(b, t, a)] = p - pec0[(b, t, "N")]; tok0[(a, idx[t][1])] += exact[(b, t, a)]; chr0[(a, idx[t][1])] += c
rho = {k: tok0[k] / chr0[k] for k in tok0}
T = collections.defaultdict(list)
for b in BLOCKS:
    for t in tasks:
        for a in "MPXS":
            tot = 0.0
            for ti in pl[t]:
                c = chars[(INST[b], t, ti, a)]
                tot += exact[(b, t, a)] if ti == 0 and (b, t, a) in exact else c * rho[(a, idx[t][1])]
            T[(t, a)].append(tot)
lvl = 1 - 0.05 / 3
def wr5(d, x):
    n = len(d); X = np.column_stack([np.ones(n), x]); XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ d; e = d - X @ b
    h = np.einsum("ij,jk,ik->i", X, XtXi, X); cov = XtXi @ (X.T * (e / (1 - h)) ** 2) @ X @ XtXi; q = stats.t.ppf(1 - (1 - lvl) / 2, n - 2); se = np.sqrt(np.diag(cov))
    return b, se, q, h
XI = {}
for C in "PXS":
    x = np.array([math.log(np.mean(T[(t, "M")]) / np.mean(T[(t, C)])) for t in tasks]); XI[C] = x
    d = np.array([100 * (y[t]["M"] - y[t][C]) for t in tasks])
    b, se, q, h = wr5(d, x)
    print(f"M-{C}: mean_x={x.mean():.6f} q05/50/95 {(100*(np.exp(np.percentile(x,[5,50,95]))-1)).round(2)} sd_x={x.std(ddof=1):.4f} alpha={b[0]:.3f} adj=[{b[0]-q*se[0]:.3f}; {b[0]+q*se[0]:.3f}] beta={b[1]:.2f} [{b[1]-q*se[1]:.1f}; {b[1]+q*se[1]:.1f}] max leverage {h.max():.3f}; n|x|<=ln1.1: {(np.abs(x)<=math.log(1.1)).sum()}")
    o = np.argsort(-np.abs(x - x.mean()))[:4]
    print("      most extreme x:", [(tasks[i].split('_')[-1], round(float(x[i]), 3), round(float(d[i]), 0)) for i in o])
    # robustness: drop top-3 leverage points
    keep = np.ones(len(x), bool); keep[np.argsort(-h)[:3]] = False
    b2, se2, q2, _ = wr5(d[keep], x[keep])
    print(f"      without 3 highest-leverage tasks: alpha={b2[0]:.2f} adj=[{b2[0]-q2*se2[0]:.2f}; {b2[0]+q2*se2[0]:.2f}] beta={b2[1]:.1f} [{b2[1]-q2*se2[1]:.0f}; {b2[1]+q2*se2[1]:.0f}]")
    # classical OLS SE (non-robust) for comparison
    n = len(d); X = np.column_stack([np.ones(n), x]); e = d - X @ b; s2 = e @ e / (n - 2); seo = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    print(f"      classical-SE interval for alpha: [{b[0]-q*seo[0]:.2f}; {b[0]+q*seo[0]:.2f}]; HC3 se alpha {se[0]:.2f} vs classical {seo[0]:.2f}")
np.save("xi.npy", np.array([XI[C] for C in "PXS"]))
