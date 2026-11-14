"""EXPLORATORY. Task groups and what happens in them. Groups defined on NIGHT-2 (independent data) or on K1 (then marked)."""
import sys, pickle
sys.path.insert(0, '.')
from common import *
idx = tasks_index(); tasks = sorted(idx)
Rall = pickle.load(open("turns.pkl", "rb"))
R = [r for r in Rall if r["block"] != "A"]
Yd = Y(); y = ymeans(Yd, idx)
rng = np.random.default_rng(5)
atrisk = lambda r: r["label"] in ("PASSED", "FAILED")
passed = lambda r: r["label"] == "PASSED"
byT = collections.defaultdict(list)
for r in R:
    byT[r["task"]].append(r)

# ---- contamination excess with task-cluster bootstrap
def cont_rate(ts, arm, kind):
    k = "cont_own" if arm in "MSX" else "cont_m"
    num = den = 0
    for t in ts:
        for r in byT[t]:
            if r["arm"] == arm and atrisk(r) and r[k] is not None and r["has_mblock"]:
                den += 1; num += r[k][kind] > 0
    return num / den if den else np.nan
ta = np.array(tasks)
for kind in ("vals", "fns"):
    for base in ("N", "P"):
        est = cont_rate(tasks, "M", kind) - cont_rate(tasks, base, kind); v = []
        for _ in range(2000):
            s = list(ta[rng.integers(0, len(ta), len(ta))]); v.append(cont_rate(s, "M", kind) - cont_rate(s, base, kind))
        print(f"contamination excess ({kind}) M - {base}(counterfactual M block): {100*est:+.1f} pp [{np.percentile(v,2.5)*100:.1f}; {np.percentile(v,97.5)*100:.1f}]")

# ---- NIGHT-2 groups
NRUN = Path("[machine-local path omitted]")
n2 = {}
for sess in ("E3", "E1"):
    for r in rows(NRUN / "sessions" / f"{sess}.jsonl"):
        n2[(r["task"], r["arm"])] = int(bool(r["evaluation"]["solved"]))
MARM = {"E3": "E*", "E1": "R+"}
gain = [t for t in tasks if n2[(t, MARM[idx[t][0]])] > n2[(t, "N")]]
loss = [t for t in tasks if n2[(t, MARM[idx[t][0]])] < n2[(t, "N")]]
EV = {}
for b in BLOCKS:
    EV.update({(t, a, b): e for (t, a), e in load_eval(b).items()})
key = {(r["task"], r["arm"], r["block"], r["turn"]): r for r in R}


def cov_of(f):
    if f is None or f["cov"] is None:
        return "no block/empty gold"
    if f["hit"] > 0:
        return "exact gold line"
    if f["cov"] >= 1:
        return "all gold fns"
    if f["cov"] > 0:
        return "some gold fns"
    return "no gold fn"


def cat(r):
    if r["status"] == "forced_termination" and r["n_steps"] >= 8:
        return "step limit"
    if r["n_calls"] == 0:
        return "no valid call"
    if r["missing_f"] and r["extra_f"]:
        return "missing+extra fn"
    if r["missing_f"]:
        return "missing gold fn"
    if r["extra_f"]:
        return "extra fn"
    return "right fns, wrong args/count"


print("\n== NIGHT-2 GAIN tasks (n=%d): the turn where N first fails (sampled episodes where N fails) and what M does on that same turn/block" % len(gain))
c_cat = collections.Counter(); c_cov = collections.Counter(); m_same = collections.Counter(); dom = collections.Counter(idx[t][1] for t in gain)
copy_gold = [0, 0]
for t in gain:
    for b in BLOCKS:
        e = EV[(t, "N", b)]
        if outcome(e):
            continue
        ff = e["first_fail"]; rn = key.get((t, "N", b, ff)); rm = key.get((t, "M", b, ff))
        if rn is None:
            continue
        c_cat[cat(rn)] += 1; c_cov[cov_of(rn["mfeat"])] += 1
        if rm is not None and atrisk(rm):
            m_same["M passes that turn" if passed(rm) else "M fails that turn"] += 1
            if passed(rm):
                copy_gold[1] += 1; copy_gold[0] += rm["cont_own"]["exact_copy"] > 0 if rm["cont_own"] else 0
        else:
            m_same["M not at risk there (failed earlier / not reached)"] += 1
print(" domains:", dict(dom)); print(" N failure category:", dict(c_cat)); print(" M-block property on N's failing turn:", dict(c_cov)); print(" M on the same turn:", dict(m_same))
print(f" of M-passing turns, M emitted an exact copy of a block call line in {copy_gold[0]}/{copy_gold[1]}")
print(" N first-fail turn index:", dict(collections.Counter(EV[(t, 'N', b)]['first_fail'] for t in gain for b in BLOCKS if not outcome(EV[(t, 'N', b)]))))

print("\n== NIGHT-2 LOSS tasks (n=%d): the turn where M first fails (sampled episodes where M fails) vs N on the same turn/block" % len(loss))
c_cat = collections.Counter(); c_cov = collections.Counter(); n_same = collections.Counter(); cont = collections.Counter(); contN = collections.Counter(); dom = collections.Counter(idx[t][1] for t in loss)
for t in loss:
    for b in BLOCKS:
        e = EV[(t, "M", b)]
        if outcome(e):
            continue
        ff = e["first_fail"]; rm = key.get((t, "M", b, ff)); rn = key.get((t, "N", b, ff))
        if rm is None:
            continue
        c_cat[cat(rm)] += 1; c_cov[cov_of(rm["mfeat"])] += 1
        co = rm["cont_own"] or {"vals": 0, "fns": 0}
        cont["block-only value used"] += co["vals"] > 0; cont["non-gold fn from block"] += co["fns"] > 0; cont["either"] += (co["vals"] > 0 or co["fns"] > 0); cont["n"] += 1
        if rn is not None and atrisk(rn):
            n_same["N passes that turn" if passed(rn) else "N fails that turn"] += 1
            cn = rn["cont_m"] or {"vals": 0, "fns": 0}
            contN["block-only value used"] += cn["vals"] > 0; contN["non-gold fn from block"] += cn["fns"] > 0; contN["either"] += (cn["vals"] > 0 or cn["fns"] > 0); contN["n"] += 1
        else:
            n_same["N not at risk there"] += 1
print(" domains:", dict(dom)); print(" M failure category:", dict(c_cat)); print(" M-block property on M's failing turn:", dict(c_cov)); print(" N on the same turn:", dict(n_same))
print(" contamination markers in M's failing turn:", dict(cont), "| same markers in N on that turn (chance baseline):", dict(contN))
print(" M first-fail turn index:", dict(collections.Counter(EV[(t, 'M', b)]['first_fail'] for t in loss for b in BLOCKS if not outcome(EV[(t, 'M', b)]))))

# ---- K1-defined groups (descriptive; selection and description on the same data)
def grp_counts(name, cond):
    ts = [t for t in tasks if cond(t)]
    print(f"\n{name}: {len(ts)} tasks; domains {dict(collections.Counter(idx[t][1] for t in ts))}; split {dict(collections.Counter(idx[t][0] for t in ts))}")
    return ts
g1 = grp_counts("K1: M beats both N and P by >= 2/3", lambda t: y[t]["M"] - max(y[t]["N"], y[t]["P"]) >= 0.66)
g2 = grp_counts("K1: M loses to N or P by >= 2/3", lambda t: max(y[t]["N"], y[t]["P"]) - y[t]["M"] >= 0.66)
g2b = grp_counts("K1: M loses to both N and P by >= 2/3", lambda t: min(y[t]["N"], y[t]["P"]) - y[t]["M"] >= 0.66)
g3 = grp_counts("K1: S beats M by >= 2/3", lambda t: y[t]["S"] - y[t]["M"] >= 0.66)
g3b = grp_counts("K1: M beats S by >= 2/3", lambda t: y[t]["M"] - y[t]["S"] >= 0.66)
g4 = grp_counts("K1: |M - S| <= 1/3", lambda t: abs(y[t]["M"] - y[t]["S"]) <= 0.34)
g5 = grp_counts("K1: never solved in 15 episodes", lambda t: sum(y[t].values()) == 0)
g6 = grp_counts("K1: M = S = 0 while N or P > 0", lambda t: y[t]["M"] == 0 and y[t]["S"] == 0 and max(y[t]["N"], y[t]["P"]) > 0)
print("  expected counts under pure sampling noise (same per-task p in both arms, p = pooled task rate), simulation:")
p_pool = np.array([np.mean([y[t][a] for a in ARMS]) for t in tasks])
sim = []
for _ in range(4000):
    a_ = rng.binomial(3, p_pool) / 3; b_ = rng.binomial(3, p_pool) / 3
    sim.append(((a_ - b_) >= 0.66).sum())
print(f"   pairs differing by >= 2/3 in one direction: mean {np.mean(sim):.1f} (95% {np.percentile(sim,2.5):.0f}-{np.percentile(sim,97.5):.0f}); observed M>S {len(g3b)}, S>M {len(g3)}")
print("  NIGHT-2 pattern of the K1 groups: M>N,P:", collections.Counter(("gain" if t in gain else "loss" if t in loss else "tie") for t in g1), " M<N or P:", collections.Counter(("gain" if t in gain else "loss" if t in loss else "tie") for t in g2))

print("\n== never-solved tasks: where and how all arms fail")
ff = collections.Counter(); cc = collections.Counter(); same_turn = 0; covc = collections.Counter()
for t in g5:
    f = [EV[(t, a, b)]["first_fail"] for a in ARMS for b in BLOCKS]
    same_turn += len(set(f)) == 1
    ff[collections.Counter(f).most_common(1)[0][0]] += 1
    for a in ARMS:
        for b in BLOCKS:
            r = key.get((t, a, b, EV[(t, a, b)]["first_fail"]))
            if r:
                cc[(a, cat(r))] += 1
                if a == "M":
                    covc[cov_of(r["mfeat"])] += 1
print(" tasks where all 15 episodes fail at the same turn:", same_turn, "of", len(g5), "| modal first-fail turn:", dict(ff))
for a in ARMS:
    print("  ", a, {k[1]: v for k, v in cc.items() if k[0] == a})
print(" M-block property at M's failing turn (never-solved tasks):", dict(covc))
# M - S on turns where S block lacks gold fns but M block has all (information advantage)
num = collections.Counter(); den = collections.Counter()
for r in R:
    if r["arm"] == "S" and atrisk(r) and r["own"] and r["mfeat"] and r["own"]["cov"] is not None:
        rm = key.get((r["task"], "M", r["block"], r["turn"]))
        if rm is None or not atrisk(rm):
            continue
        adv = "M block covers all gold fns, S block does not" if (r["mfeat"]["cov"] >= 1 and r["own"]["cov"] < 1) else "S covers all, M does not" if (r["own"]["cov"] >= 1 and r["mfeat"]["cov"] < 1) else "same coverage class"
        den[adv] += 1; num[(adv, "M")] += passed(rm); num[(adv, "S")] += passed(r)
print("\n== paired at-risk turns (both M and S at risk), pass rate by information advantage:")
for k in den:
    print(f"  {k}: n={den[k]}  M {100*num[(k,'M')]/den[k]:.1f}%  S {100*num[(k,'S')]/den[k]:.1f}%")
