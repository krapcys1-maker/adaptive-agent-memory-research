"""EXPLORATORY mechanism tables (sampled blocks S1-S3 only). Cluster = task. Metrics computed by code, same for every arm."""
import sys, pickle
sys.path.insert(0, '.')
from common import *
idx = tasks_index(); tasks = sorted(idx)
R = [r for r in pickle.load(open("turns.pkl", "rb")) if r["block"] != "A"]
rng = np.random.default_rng(11)


def cboot(fn, B=1000):
    est = fn(tasks); v = []
    ta = np.array(tasks)
    for _ in range(B):
        x = fn(list(ta[rng.integers(0, len(ta), len(ta))]))
        if x is not None and not np.isnan(x):
            v.append(x)
    return est, np.percentile(v, 2.5), np.percentile(v, 97.5)


byT = collections.defaultdict(list)
for r in R:
    byT[r["task"]].append(r)


def rate(ts, pred, val):
    num = den = 0
    for t in ts:
        for r in byT[t]:
            if pred(r):
                den += 1; num += val(r)
    return (num / den if den else float("nan")), den


atrisk = lambda r: r["label"] in ("PASSED", "FAILED")
passed = lambda r: r["label"] == "PASSED"

print("== A1. per-turn conditional pass rate (at-risk turns), by arm")
for a in ARMS:
    out = []
    for ti in range(5):
        p, n = rate(tasks, lambda r: r["arm"] == a and r["turn"] == ti and atrisk(r), passed)
        out.append(f"t{ti}: {100*p:.1f}% (n={n})")
    print(a, " | ".join(out))
for a, b in (("M", "N"), ("M", "S"), ("M", "P"), ("S", "N"), ("P", "N"), ("X", "N")):
    f = lambda ts: rate(ts, lambda r: r["arm"] == a and r["turn"] == 0, passed)[0] - rate(ts, lambda r: r["arm"] == b and r["turn"] == 0, passed)[0]
    e, lo, hi = cboot(f)
    print(f"   turn-0 pass {a}-{b}: {100*e:+.1f} pp [{100*lo:.1f}; {100*hi:.1f}]")

print("== first-fail turn distribution (% of episodes) by arm")
EVs = {}
for b in BLOCKS:
    EVs.update({(t, a, b): e for (t, a), e in load_eval(b).items()})
for a in ARMS:
    c = collections.Counter(("solved" if outcome(e) else f"t{e['first_fail']}") for (t, a_, b), e in EVs.items() if a_ == a)
    print(a, {k: round(100 * v / 444, 1) for k, v in sorted(c.items())})


def cov_of(f):
    if f is None or f["cov"] is None:
        return "no block / empty gold"
    if f["hit"] > 0:
        return "exact gold line in block"
    if f["cov"] >= 1:
        return "all gold fns in block"
    if f["cov"] > 0:
        return "some gold fns in block"
    return "no gold fn in block"


cats = ["exact gold line in block", "all gold fns in block", "some gold fns in block", "no gold fn in block", "no block / empty gold"]
print("== A2. at-risk turn pass rate by arm x property of the M block of that (task, turn) [same turn sets for all arms; N = difficulty control]")
for c in cats:
    out = []
    for a in ARMS:
        p, n = rate(tasks, lambda r: r["arm"] == a and atrisk(r) and cov_of(r["mfeat"]) == c, passed)
        out.append(f"{a} {100*p:.1f}% ({n})")
    print(f"  {c:28s}", " | ".join(out))
    line = "      "
    for a, b in (("M", "N"), ("M", "S"), ("S", "N")):
        f = lambda ts: rate(ts, lambda r: r["arm"] == a and atrisk(r) and cov_of(r["mfeat"]) == c, passed)[0] - rate(ts, lambda r: r["arm"] == b and atrisk(r) and cov_of(r["mfeat"]) == c, passed)[0]
        e, lo, hi = cboot(f, 600)
        line += f"  {a}-{b}: {100*e:+.1f} [{100*lo:.1f}; {100*hi:.1f}]"
    print(line)
print("   turn-0 only:")
for c in cats[:4]:
    out = []
    for a in ARMS:
        p, n = rate(tasks, lambda r: r["arm"] == a and r["turn"] == 0 and cov_of(r["mfeat"]) == c, passed)
        out.append(f"{a} {100*p:.1f}% ({n})")
    print(f"  {c:28s}", " | ".join(out))

print("== A2b. arm by property of ITS OWN block, at-risk turns; N on the same (task, turn, block) as control")
key = {(r["task"], r["arm"], r["block"], r["turn"]): r for r in R}
for arm in ("M", "S", "X"):
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in R:
        if r["arm"] != arm or r["own"] is None or r["own"]["cov"] is None:
            continue
        c = cov_of(r["own"])
        n_ = key.get((r["task"], "N", r["block"], r["turn"]))
        if atrisk(r):
            agg[c][0] += passed(r); agg[c][1] += 1
        if n_ and atrisk(n_):
            agg[c][2] += passed(n_); agg[c][3] += 1
    for c in cats[:4]:
        v = agg[c]
        if v[1]:
            print(f"  {arm} | {c:28s} {arm} {100*v[0]/max(v[1],1):.1f}% ({v[1]}) vs N {100*v[2]/max(v[3],1):.1f}% ({v[3]})")

print("== share of shown blocks by coverage category (all turns with a block and non-empty gold)")
for arm in ("M", "S", "X"):
    c = collections.Counter(cov_of(r["own"]) for r in R if r["arm"] == arm and r["own"] and r["own"]["cov"] is not None)
    tot = sum(c.values())
    print(arm, {k: round(100 * c[k] / tot, 1) for k in cats[:4]}, tot)

print("== A3. contamination: model uses values/functions present in the block but absent from requests so far and earlier results (at-risk turns)")
for a in ARMS:
    k = "cont_own" if a in "MSX" else "cont_m"
    rr = [r for r in R if r["arm"] == a and atrisk(r) and r[k] is not None and (r["has_block"] if a in "MSX" else r["has_mblock"])]
    v = np.mean([r[k]["vals"] > 0 for r in rr]); f = np.mean([r[k]["fns"] > 0 for r in rr]); ec = np.mean([r[k]["exact_copy"] > 0 for r in rr])
    fv = np.mean([not passed(r) for r in rr if r[k]["vals"] > 0] or [np.nan]); f0 = np.mean([not passed(r) for r in rr if r[k]["vals"] == 0])
    ff = np.mean([not passed(r) for r in rr if r[k]["fns"] > 0] or [np.nan]); ff0 = np.mean([not passed(r) for r in rr if r[k]["fns"] == 0])
    what = "own block" if a in "MSX" else "COUNTERFACTUAL M block (chance baseline)"
    print(f"{a} ({what}): turns {len(rr)}; block-only VALUE used {100*v:.1f}% (fail with {100*fv:.0f}% vs without {100*f0:.0f}%); "
          f"non-gold FUNCTION that is in block {100*f:.1f}% (fail {100*ff:.0f}% vs {100*ff0:.0f}%); exact copy of a block call line {100*ec:.1f}%")
for a in "SX":
    rr = [r for r in R if r["arm"] == a and atrisk(r) and r["cont_m"] is not None and r["has_mblock"]]
    print(f"   {a} vs counterfactual M block: VALUE {100*np.mean([r['cont_m']['vals'] > 0 for r in rr]):.1f}%  FUNCTION {100*np.mean([r['cont_m']['fns'] > 0 for r in rr]):.1f}%  exact copy {100*np.mean([r['cont_m']['exact_copy'] > 0 for r in rr]):.1f}%")


def cat(r):
    if r["status"] == "forced_termination" and r["n_steps"] >= 8:
        return "step limit (8)"
    if r["n_calls"] == 0:
        return "no valid call (gold has calls)" if not r["gold_empty"] else "no call, gold empty (state/other)"
    if r["gold_empty"]:
        return "acted though gold is empty"
    if r["missing_f"] and r["extra_f"]:
        return "missing + extra functions"
    if r["missing_f"]:
        return "missing gold function"
    if r["extra_f"]:
        return "extra non-gold function"
    return "right functions, wrong args/count"


print("== A4. failure categories of FAILED turns by arm (% of failed turns)")
allc = collections.Counter(); tab = {}
for a in ARMS:
    c = collections.Counter(cat(r) for r in R if r["arm"] == a and r["label"] == "FAILED")
    tab[a] = c; allc.update(c)
for k, _ in allc.most_common():
    print(f"  {k:36s}", " | ".join(f"{a} {100*tab[a][k]/sum(tab[a].values()):5.1f}% ({tab[a][k]})" for a in ARMS))
print("   failed turns per arm:", {a: sum(tab[a].values()) for a in ARMS})
print("== per at-risk turn behaviour by arm")
for a in ARMS:
    rr = [r for r in R if r["arm"] == a and atrisk(r)]
    print(a, "calls/turn", round(np.mean([r["n_calls"] for r in rr]), 2), "| gold/turn", round(np.mean([r["n_gold"] for r in rr]), 2),
          "| extra-fn turns %", round(100 * np.mean([r["extra_f"] > 0 for r in rr]), 1), "| missing-fn turns %", round(100 * np.mean([r["missing_f"] > 0 for r in rr]), 1),
          "| error results/turn", round(np.mean([r["errors"] for r in rr]), 2), "| invalid/turn", round(np.mean([r["invalid"] for r in rr]), 3),
          "| all gold calls exact %", round(100 * np.mean([r["all_gold_exact"] for r in rr]), 1))
