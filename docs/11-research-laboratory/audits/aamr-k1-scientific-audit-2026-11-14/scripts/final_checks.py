"""EXPLORATORY final checks."""
import sys, pickle
sys.path.insert(0, '.')
from common import *
from scipy import stats
idx = tasks_index(); tasks = sorted(idx)
Yd = Y(); y = ymeans(Yd, idx)
R = [r for r in pickle.load(open("turns.pkl", "rb")) if r["block"] != "A"]
atrisk = lambda r: r["label"] in ("PASSED", "FAILED")


def ci(v, lvl=0.95):
    v = np.array(v, float); n = len(v); se = v.std(ddof=1) / math.sqrt(n); q = stats.t.ppf(1 - (1 - lvl) / 2, n - 1)
    return f"{v.mean():+.1f} [{v.mean()-q*se:.1f}; {v.mean()+q*se:.1f}]"


print("== by domain (95%, uncorrected, 3 domains x several contrasts: exploratory)")
for d in ("GFS", "VC", "TRAVEL"):
    ts = [t for t in tasks if idx[t][1] == d]
    print(d, len(ts), " | ".join(f"{a}-{b} {ci([100*(y[t][a]-y[t][b]) for t in ts])}" for a, b in (("M", "N"), ("S", "N"), ("M", "S"), ("P", "N"), ("X", "N"))))
for s in ("E3", "E1"):
    ts = [t for t in tasks if idx[t][0] == s]
    print(s, len(ts), " | ".join(f"{a}-{b} {ci([100*(y[t][a]-y[t][b]) for t in ts])}" for a, b in (("M", "N"), ("S", "N"), ("M", "S"), ("M", "P"), ("M", "X"))))
# interaction domain x (M-N): one-way ANOVA on d_i
for a, b in (("M", "N"), ("M", "S"), ("S", "N")):
    groups = [[y[t][a] - y[t][b] for t in tasks if idx[t][1] == d] for d in ("GFS", "VC", "TRAVEL")]
    print(f"   ANOVA domain effect on {a}-{b}: p={stats.f_oneway(*groups)[1]:.3f}; Kruskal p={stats.kruskal(*groups)[1]:.3f}")

print("== arm order: chi-square of arm x position table (uniform shuffle expected)")
recs = {}
for b in BLOCKS:
    for r in rows(BASE / f"run/sessions/{b}.jsonl"):
        recs[(r["task"], r["arm"], b)] = r["episode"]["started_at"]
tab = np.zeros((5, 5))
for b in BLOCKS:
    for t in tasks:
        for i, a in enumerate(sorted(ARMS, key=lambda a: recs[(t, a, b)])):
            tab[ARMS.index(a), i] += 1
print(tab.astype(int).tolist(), "chi2 p =", round(stats.chi2_contingency(tab)[1], 4))
# mean position per arm and adjusted contrast (regress outcome on arm + position with task fixed effects) -> simple check: contrast within position strata
pos = {}
for b in BLOCKS:
    for t in tasks:
        for i, a in enumerate(sorted(ARMS, key=lambda a: recs[(t, a, b)])):
            pos[(t, a, b)] = i
print("   mean position:", {a: round(np.mean([pos[(t, a, b)] for t in tasks for b in BLOCKS]), 2) for a in ARMS})
print("   solve rate by arm when run first (pos 0) vs later:", {a: (round(100*np.mean([Yd[(t, a, b)] for t in tasks for b in BLOCKS if pos[(t, a, b)] == 0]), 1), round(100*np.mean([Yd[(t, a, b)] for t in tasks for b in BLOCKS if pos[(t, a, b)] > 0]), 1)) for a in ARMS})

print("== finite-population precision (declared estimand: these 148 tasks, frozen stimuli; only sampling noise random)")
lvl = 1 - 0.05 / 3
for C in "PXS":
    D = np.array([[Yd[(t, "M", b)] - Yd[(t, C, b)] for b in BLOCKS] for t in tasks], float)
    vrep = D.var(axis=1, ddof=1).mean(); se_fp = math.sqrt(vrep / 3 / 148) * 100; est = 100 * D.mean()
    q = stats.norm.ppf(1 - (1 - lvl) / 2)
    se_sp = 100 * D.mean(1).std(ddof=1) / math.sqrt(148)
    print(f"M-{C}: est {est:+.2f}; SE finite-pop {se_fp:.2f} pp -> 98.33% [{est-q*se_fp:.1f}; {est+q*se_fp:.1f}]   (pre-registered t interval uses SE {se_sp:.2f})")

print("== per-trace association (M plan traces): tasks showing the trace vs mean M-N and M-S of those tasks (n>=6)")
graph = json.load(open(BASE / "stim/k1_shared_graph.json", encoding="utf-8"))
bytr = collections.defaultdict(list)
for t in tasks:
    for tr in graph[t]["traces"]:
        bytr[tr].append(t)
rows_ = []
for tr, ts in bytr.items():
    if len(ts) >= 6:
        rows_.append((np.mean([y[t]["M"] - y[t]["N"] for t in ts]), np.mean([y[t]["M"] - y[t]["S"] for t in ts]), len(ts), tr, idx[ts[0]][1]))
rows_.sort()
print(" traces with n>=6:", len(rows_), "of", len(bytr))
for r in rows_[:6]:
    print(f"   worst: {r[3]:28s} {r[4]:6s} n={r[2]:2d}  M-N {100*r[0]:+.0f} pp  M-S {100*r[1]:+.0f} pp")
for r in rows_[-6:]:
    print(f"   best:  {r[3]:28s} {r[4]:6s} n={r[2]:2d}  M-N {100*r[0]:+.0f} pp  M-S {100*r[1]:+.0f} pp")

print("== contamination excess (block-only value used) by domain: M own block vs N counterfactual M block; and fail rates")
for d in ("GFS", "VC", "TRAVEL"):
    m = [r for r in R if r["arm"] == "M" and atrisk(r) and r["has_mblock"] and idx[r["task"]][1] == d]
    n = [r for r in R if r["arm"] == "N" and atrisk(r) and r["has_mblock"] and idx[r["task"]][1] == d]
    print(f" {d}: VALUE M {100*np.mean([r['cont_own']['vals']>0 for r in m]):.1f}% vs N-baseline {100*np.mean([r['cont_m']['vals']>0 for r in n]):.1f}% | FUNCTION M {100*np.mean([r['cont_own']['fns']>0 for r in m]):.1f}% vs {100*np.mean([r['cont_m']['fns']>0 for r in n]):.1f}% | turn-0 pass M {100*np.mean([r['label']=='PASSED' for r in m if r['turn']==0]):.1f}% N {100*np.mean([r['label']=='PASSED' for r in n if r['turn']==0]):.1f}%")
print("== fragility of the M-S 'excludes 8.1 pp' sentence: upper bounds")
d = np.array([100 * (y[t]["M"] - y[t]["S"]) for t in tasks]); se = d.std(ddof=1) / math.sqrt(148)
print("  main 98.33% U =", round(d.mean() + stats.t.ppf(1 - (1 - lvl) / 2, 147) * se, 2), "| threshold 8.108 | widened x1.23 U =", round(d.mean() + 1.2299 * stats.t.ppf(1 - (1 - lvl) / 2, 147) * se, 2))
