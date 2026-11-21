#!/usr/bin/env python3
"""Independent reanalysis of ALFWORLD-LADDER-R4-V5B per_unit.csv (issue #230).

No GPU, no model calls. Reads only the published per_unit.csv and reproduces
the lab's primary numbers, then runs the three requested new analyses:
  1. effect decomposition by task type and goal object
  2. gain/loss arms vs per-step format counters
  3. sensitivity of process rates to step versus task weighting
  4. leakage / formatting artefact check

Run:
    python reanalysis.py                      # uses the V5B CSV in this checkout
    python reanalysis.py path/to/per_unit.csv

Every number printed is computed from the CSV; nothing is hard-coded.
"""
import csv
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ARMS = ["none", "placebo", "mismatched_type", "retrieved_task"]


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by = {}
    for r in rows:
        arms = by.setdefault(r["unit"], {})
        if r["arm"] in arms:
            raise ValueError(f"Duplicate unit/arm: {r['unit']}, {r['arm']}")
        arms[r["arm"]] = r
    return rows, by


def paired(by, a, b, field="solved", z=1.96):
    """Paired difference a-b over units; returns (mean, gains, losses, se, lo, hi)."""
    d = []
    for u, arms in by.items():
        if a in arms and b in arms and arms[a][field].strip() and arms[b][field].strip():
            d.append(float(arms[a][field]) - float(arms[b][field]))
    m = statistics.mean(d)
    variance = statistics.pvariance(d) / len(d)
    se = math.sqrt(variance) if variance else 1 / len(d)
    gains = sum(1 for x in d if x > 0)
    losses = sum(1 for x in d if x < 0)
    return m, gains, losses, se, m - z * se, m + z * se


def show_paired(title, by, pairs, z=1.96):
    print(f"\n== {title} ==")
    print(f"{'comparison':32s} {'diff':>8s} {'gains/losses':>13s} {'SE':>7s} {'interval':>24s}")
    for a, b in pairs:
        m, g, l, se, lo, hi = paired(by, a, b, z=z)
        print(f"{a+' - '+b:32s} {m:+8.4f} {str(g)+'/'+str(l):>13s} {se:7.4f} {f'[{lo:+.3f}, {hi:+.3f}]':>24s}")


def task_type(u):
    m = re.search(r"~train/([^-]+)-", u)
    return m.group(1) if m else "unknown"


def goal_object(u):
    m = re.search(r"~train/[^-]+-([^-]+)-", u)
    return m.group(1) if m else "unknown"


def section_by_type(by):
    print("\n== Effect of retrieved_task - placebo by task type ==")
    groups = defaultdict(list)
    for u in by:
        groups[task_type(u)].append(u)
    print(f"{'task type':34s} {'n':>4s} {'diff':>8s} {'95% CI (unadjusted)':>22s} {'g/l':>7s}")
    for t, us in sorted(groups.items(), key=lambda x: -len(x[1])):
        d = [int(by[u]["retrieved_task"]["solved"]) - int(by[u]["placebo"]["solved"]) for u in us]
        m = statistics.mean(d)
        se = statistics.stdev(d) / math.sqrt(len(d))
        g = sum(1 for x in d if x > 0)
        l = sum(1 for x in d if x < 0)
        print(f"{t:34s} {len(us):4d} {m:+8.3f} {f'[{m-1.96*se:+.3f}, {m+1.96*se:+.3f}]':>22s} {str(g)+'/'+str(l):>7s}")

    print("\n== Effect by goal object (objects with n>=8) ==")
    objs = defaultdict(list)
    for u in by:
        objs[goal_object(u)].append(u)
    for o, us in sorted(objs.items(), key=lambda x: -len(x[1])):
        if len(us) < 8:
            continue
        d = [int(by[u]["retrieved_task"]["solved"]) - int(by[u]["placebo"]["solved"]) for u in us]
        print(f"{o:16s} n={len(us):2d} diff={statistics.mean(d):+.3f}")


COUNTERS = ["empty_retries", "invalid_no_action_tag", "invalid_actions", "truncated", "untagged_not_truncated"]


def section_gain_loss(by):
    print("\n== Gain/loss arms vs mean episode counter totals ==")
    groups = {
        "GAIN (placebo=0, retrieved=1)": lambda d: int(d["placebo"]["solved"]) == 0 and int(d["retrieved_task"]["solved"]) == 1,
        "LOSS (placebo=1, retrieved=0)": lambda d: int(d["placebo"]["solved"]) == 1 and int(d["retrieved_task"]["solved"]) == 0,
    }
    for label, pred in groups.items():
        us = [u for u, d in by.items() if pred(d)]
        print(f"\n  {label}: n={len(us)}")
        for c in ["steps", *COUNTERS]:
            p = statistics.mean(int(by[u]["placebo"][c]) for u in us)
            r = statistics.mean(int(by[u]["retrieved_task"][c]) for u in us)
            print(f"    {c:24s} placebo={p:5.2f} retrieved={r:5.2f} delta={r-p:+.2f}")


def section_rate_weighting(by):
    print("\n== Process rates: step weighting vs equal task weighting ==")
    arms = ("placebo", "retrieved_task")
    steps = {arm: [int(pair[arm]["steps"]) for pair in by.values()] for arm in arms}
    if any(n <= 0 for lengths in steps.values() for n in lengths):
        raise ValueError("Process-rate comparison requires positive steps in both arms")
    print("Total steps: " + ", ".join(f"{arm}={sum(steps[arm])}" for arm in arms))

    for counter in ("invalid_no_action_tag", "invalid_actions"):
        counts = {arm: [int(pair[arm][counter]) for pair in by.values()] for arm in arms}
        pooled = [sum(counts[arm]) / sum(steps[arm]) for arm in arms]
        rates = {
            arm: [count / length for count, length in zip(counts[arm], steps[arm])]
            for arm in arms
        }
        differences = [retrieved - placebo for placebo, retrieved in zip(*(rates[arm] for arm in arms))]
        rng = random.Random(20261116)
        replicates = 10_000
        bootstrap = sorted(
            statistics.mean(rng.choices(differences, k=len(differences)))
            for _ in range(replicates)
        )
        tail = replicates // 40
        lower, upper = bootstrap[tail], bootstrap[-tail - 1]
        print(f"  {counter}:")
        print(f"    step-weighted: {pooled[0]:.3%} -> {pooled[1]:.3%}, "
              f"delta={(pooled[1] - pooled[0]) * 100:+.2f} pp")
        print(f"    task-weighted: {statistics.mean(rates['placebo']):.3%} -> "
              f"{statistics.mean(rates['retrieved_task']):.3%}, "
              f"delta={statistics.mean(differences) * 100:+.2f} pp, "
              f"95% paired bootstrap [{lower * 100:+.2f}, {upper * 100:+.2f}] pp")


def section_token_match(by):
    print("\n== Token-matching check ==")
    for a, b in [("placebo", "retrieved_task"), ("placebo", "mismatched_type")]:
        absd, reld = [], []
        for u, arms in by.items():
            pa, pb = int(arms[a]["memory_tokens"]), int(arms[b]["memory_tokens"])
            absd.append(abs(pa - pb))
            reld.append(abs(pa - pb) / max(pa, pb))
        print(f"  {a} vs {b}: per-unit |delta tokens| mean={statistics.mean(absd):.1f} max={max(absd)}; "
              f"relative mean={statistics.mean(reld)*100:.2f}% max={max(reld)*100:.2f}%")


def section_leakage(rows):
    print("\n== Leakage / artefact checks ==")
    for c in ["overlap_with_retrieved", "memory_similarity", "top1_similarity", "error"]:
        vals = [(r["arm"], r[c]) for r in rows if r[c].strip()]
        print(f"  {c}: filled by arm {dict(sorted(Counter(arm for arm, _ in vals).items()))}")
        nums = [float(v) for _, v in vals]
        nz = sum(1 for v in nums if v != 0)
        print(f"  {c:24s} filled={len(vals):3d}/{len(rows)} nonzero={nz:3d} "
              f"min={min(nums) if nums else None} max={max(nums) if nums else None}")


def main():
    default_csv = Path(__file__).resolve().parents[2] / "lab/autolab-alfworld-ladder-r4-v5b/per_unit.csv"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_csv
    rows, by = load(path)
    print(f"Loaded {len(rows)} rows, {len(by)} units, arms={sorted({r['arm'] for r in rows})}")
    if len(rows) != 804 or len(by) != 201 or any(set(arms) != set(ARMS) for arms in by.values()):
        raise ValueError("Expected 201 units with exactly four arms each")
    if {(row["seed"], row["cycle"]) for row in rows} != {("0", "1")}:
        raise ValueError("Expected seed 0 and cycle 1 throughout")
    if any(row["solved"] not in {"0", "1"} for row in rows):
        raise ValueError("Expected a binary solved value for every row")
    show_paired("Replication of published contrasts (stopping-look z=2.7777)", by,
                [("mismatched_type", "placebo"), ("retrieved_task", "placebo"),
                 ("mismatched_type", "none"), ("placebo", "none"), ("retrieved_task", "none")], z=2.7777)
    section_token_match(by)
    section_by_type(by)
    section_gain_loss(by)
    section_rate_weighting(by)
    section_leakage(rows)


if __name__ == "__main__":
    main()
