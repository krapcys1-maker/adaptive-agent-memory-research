#!/usr/bin/env python3
"""AAM-F1: is there learnable signal in an account's real engagement numbers?

Reads the per-note results export of a live account (one JSON object per note: publication time, features known at
publication, a 72 hour measurement and a time series of measurements) and, optionally, the export of its replies. Writes only
aggregates: no text and no identifier of the input is printed or stored.

Questions (the readings are fixed in data/lab/aam-f1-engagement-signal/README.md before the first run on real data):
  resolution  how many notes have any like, reply or restack at 72 hours
  dispersion  whether the like rate varies between notes beyond binomial sampling noise
  skill       whether features known at publication predict an outcome better than the recent past does (rolling origin,
              with a planted-effect control that the instrument must detect)
  early       whether a reading near 6, 12, 24 or 48 hours ranks notes like the 72 hour reading
  power       how many notes per arm a randomised comparison needs at this account's noise level

Usage: python scripts/engagement_signal.py --notes wyniki_notek.jsonl [--replies odpowiedzi.jsonl] [--json OUT.json]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy import stats

LAG = timedelta(hours=72)      # an outcome is known 72 hours after publication
RECENT = 20                    # notes in the recency baseline
MIN_KNOWN = 10                 # known earlier notes needed for a baseline and for a fit
START = 60                     # notes before this index (in time order) are history only
RIDGE = 10.0
SHRINK = 5.0
BLOCK = 5                      # moving-block bootstrap over consecutive evaluation notes
PLANTED = 1.5                  # factor of the planted category effect
SKILL_NEEDED = 0.05
EARLY_HOURS = (6, 12, 24, 48)
POOL = 100                     # most recent notes used as the noise pool of the power simulation
PER_ARM = (20, 40, 80, 160)
EFFECTS = (0.25, 0.5, 1.0)
SEED = 20261101


def load_jsonl(path: str) -> List[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parse_time(text: str) -> datetime:
    when = datetime.fromisoformat(text)
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def note_table(rows: Sequence[dict]) -> List[dict]:
    """Notes with a 72 hour measurement, in time order, with the features known at publication."""
    table = []
    for row in rows:
        m = row.get("pomiar_72h")
        if not m or not row.get("kiedy") or m.get("wyswietlenia") is None or m.get("polubienia") is None:
            continue
        table.append({"t": parse_time(row["kiedy"]), "V": m["wyswietlenia"], "L": m["polubienia"], "R": m.get("odpowiedzi") or 0,
                      "X": m.get("restacki") or 0, "I": m.get("interakcje_razem") or 0, "typ": row.get("typ"), "format": row.get("format"),
                      "forma": row.get("forma"), "pyt": row.get("konczy_pytaniem"), "slow": row.get("slow") or 0, "model": row.get("model"),
                      "series": row.get("seria_h_wysw_lajk_odp_restack_odw_subskr") or []})
    table.sort(key=lambda r: r["t"])
    return table


def reply_table(rows: Sequence[dict]) -> List[dict]:
    """Replies whose last measurement was taken at least 72 hours after they were posted."""
    table = []
    for row in rows:
        m = row.get("ostatni_pomiar")
        if not m or not row.get("kiedy") or not m.get("kiedy") or m.get("wyswietlenia") is None or m.get("polubienia") is None:
            continue
        if parse_time(m["kiedy"]) - parse_time(row["kiedy"]) < LAG:
            continue
        table.append({"t": parse_time(row["kiedy"]), "V": m["wyswietlenia"], "L": m["polubienia"], "R": m.get("odpowiedzi") or 0,
                      "X": m.get("restacki") or 0, "I": m.get("interakcje_razem") or 0})
    table.sort(key=lambda r: r["t"])
    return table


def rounded(values: Sequence[float], digits: int = 4) -> List[float]:
    return [round(float(v), digits) for v in values]


def resolution(table: Sequence[dict]) -> dict:
    n = len(table)
    share = lambda key: round(sum(1 for r in table if (r[key] or 0) >= 1) / n, 4)   # noqa: E731
    return {"notes": n, "views_q25_50_75": rounded(np.percentile([r["V"] for r in table], [25, 50, 75]), 1),
            "likes_q25_50_75": rounded(np.percentile([r["L"] for r in table], [25, 50, 75]), 1),
            "share_likes_ge_1": share("L"), "share_replies_ge_1": share("R"), "share_restacks_ge_1": share("X"),
            "share_interactions_ge_1": share("I")}


def dispersion(table: Sequence[dict], draws: int, seed: int) -> Optional[dict]:
    """Pearson dispersion of likes given views against binomial noise at the pooled like rate (1 means chance alone)."""
    pairs = [(r["V"], r["L"]) for r in table if r["V"] and r["V"] > 0]
    if len(pairs) < 10:
        return None
    v = np.array([p[0] for p in pairs], dtype=np.int64)
    l = np.array([p[1] for p in pairs], dtype=np.int64)
    p = float(l.sum() / v.sum())
    if not 0 < p < 1:
        return None
    denominator = v * p * (1 - p)
    observed = float((((l - v * p) ** 2) / denominator).sum() / (len(v) - 1))
    simulated = np.random.default_rng(seed).binomial(v, p, size=(draws, len(v)))
    null = (((simulated - v * p) ** 2) / denominator).sum(axis=1) / (len(v) - 1)
    return {"notes": len(v), "pooled_like_rate": round(p, 5), "D": round(observed, 3), "null_95": rounded(np.percentile(null, [2.5, 97.5]), 3),
            "p_mc": round(float((1 + (null >= observed).sum()) / (draws + 1)), 4)}


def features(table: Sequence[dict]):
    """One-hot matrix of what is known at publication; the only thing taken from the whole table is the length terciles (no outcome)."""
    lengths = sorted(r["slow"] for r in table)
    low, high = lengths[len(lengths) // 3], lengths[2 * len(lengths) // 3]
    listed = []
    for r in table:
        listed.append(["typ=%s" % r["typ"], "format=%s" % r["format"], "forma=%s" % r["forma"], "pyt=%s" % r["pyt"], "model=%s" % r["model"],
                       "hour=%d" % (r["t"].hour // 6), "weekend=%s" % (r["t"].weekday() >= 5), "length=%d" % ((r["slow"] > low) + (r["slow"] > high))])
    names = sorted({x for f in listed for x in f})
    index = {x: k for k, x in enumerate(names)}
    matrix = np.zeros((len(table), len(names)))
    for i, f in enumerate(listed):
        for x in f:
            matrix[i, index[x]] = 1.0
    return matrix, names


def block_indices(n: int, rng: np.random.Generator) -> np.ndarray:
    starts = rng.integers(0, n - BLOCK + 1, size=math.ceil(n / BLOCK))
    return np.concatenate([np.arange(s, s + BLOCK) for s in starts])[:n]


def evaluate(table: Sequence[dict], key: str, draws: int, seed: int, shift: Optional[np.ndarray] = None) -> dict:
    """Rolling-origin prediction of log(1 + outcome) for every note from START on, using only outcomes known at its publication.

    Predictors: the mean of all known earlier notes; the recency baseline (median of the last RECENT known notes, corrected by the mean
    of its earlier residuals); the baseline plus a shrunk effect of the note type; the baseline plus a ridge fit on every feature. Skill is
    the reduction of squared error against the recency baseline, with a moving-block bootstrap interval.
    """
    y = np.log1p(np.array([r[key] for r in table], dtype=float))
    if shift is not None:
        y = y + shift
    n = len(table)
    t = [r["t"] for r in table]
    matrix, names = features(table)
    typ_columns = [k for k, name in enumerate(names) if name.startswith("typ=")]
    known = [[j for j in range(i) if t[j] + LAG <= t[i]] for i in range(n)]
    base = np.array([float(np.median(y[known[i][-RECENT:]])) if len(known[i]) >= MIN_KNOWN else np.nan for i in range(n)])
    residual = y - base
    rows = []
    for i in range(START, n):
        train = [j for j in known[i] if not np.isnan(base[j])]
        if np.isnan(base[i]) or len(train) < MIN_KNOWN:
            continue
        r_train = residual[train]
        mu = float(r_train.mean())
        centred = r_train - mu
        b0 = base[i] + mu
        x_typ = matrix[train][:, typ_columns]
        effect = (x_typ * centred[:, None]).sum(axis=0) / (x_typ.sum(axis=0) + SHRINK)
        b1 = b0 + float(matrix[i, typ_columns] @ effect)
        a = matrix[train]
        mean_a = a.mean(axis=0)
        ac = a - mean_a
        w = np.linalg.solve(ac.T @ ac + RIDGE * np.eye(a.shape[1]), ac.T @ centred)
        b2 = b0 + float((matrix[i] - mean_a) @ w)
        rows.append((y[i], float(np.mean(y[known[i]])), b0, b1, b2))
    a = np.array(rows)
    squared = (a[:, [0]] - a[:, 1:]) ** 2           # columns: global mean, recency baseline, typ, full
    point = 1.0 - squared.sum(axis=0) / squared[:, 1].sum()
    rng = np.random.default_rng(seed)
    samples = np.empty((draws, squared.shape[1]))
    for d in range(draws):
        s = squared[block_indices(len(squared), rng)].sum(axis=0)
        samples[d] = 1.0 - s / s[1]
    low, high = np.percentile(samples, [2.5, 97.5], axis=0)
    skill = {name: {"value": round(float(point[k]), 4), "ci95": [round(float(low[k]), 4), round(float(high[k]), 4)]}
             for k, name in ((0, "global_mean"), (2, "typ"), (3, "full"))}
    return {"n_eval": len(squared), "mse_recent": round(float(squared[:, 1].mean()), 4), "skill": skill}


def planted_control(table: Sequence[dict], key: str, draws: int, seed: int) -> dict:
    """The same evaluation after multiplying (1 + outcome) by PLANTED for the commonest type: the instrument must see it."""
    counts = Counter(r["typ"] for r in table[START:] if r["typ"] is not None)
    category = counts.most_common(1)[0][0]
    shift = np.array([math.log(PLANTED) if r["typ"] == category else 0.0 for r in table])
    return dict(evaluate(table, key, draws, seed, shift=shift), category=category, factor=PLANTED)


def carries_signal(entry: dict) -> bool:
    return entry["value"] >= SKILL_NEEDED and entry["ci95"][0] > 0


def spearman(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    if len(a) < 10 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return round(float(stats.spearmanr(a, b)[0]), 4)


def early_vs_final(table: Sequence[dict]) -> dict:
    """Rank agreement between the last reading taken between h/2 and h hours after publication and the 72 hour reading."""
    out = {}
    for h in EARLY_HOURS:
        pairs = []
        for r in table:
            points = [p for p in r["series"] if p and p[0] is not None and h / 2 <= p[0] <= h and p[1] is not None and p[2] is not None]
            if points:
                pairs.append((points[-1][1], points[-1][2], r["V"], r["L"]))
        out[str(h)] = {"notes": len(pairs), "views_rho": spearman([p[0] for p in pairs], [p[2] for p in pairs]),
                       "likes_rho": spearman([p[1] for p in pairs], [p[3] for p in pairs])}
    return out


def power(table: Sequence[dict], key: str, sims: int, seed: int) -> dict:
    """Share of simulated randomised comparisons (Mann-Whitney, two-sided, 5%) that find a relative increase of delta in expected count.

    Both arms are drawn with replacement from the last POOL notes; the control arm is binomially thinned by 1 / (1 + delta), so the
    expected ratio is exactly 1 + delta and both arms keep the account's real spread. delta 0 estimates the false positive rate."""
    pool = np.array([r[key] for r in table[-POOL:]], dtype=np.int64)
    rng = np.random.default_rng(seed)
    out: Dict[str, float] = {}
    for delta in (0.0,) + EFFECTS:
        for m in PER_ARM:
            hits = 0
            for _ in range(sims):
                treated = rng.choice(pool, size=m)
                control = rng.choice(pool, size=m)
                if delta > 0:
                    control = rng.binomial(control, 1.0 / (1.0 + delta))
                if np.ptp(np.concatenate([treated, control])) > 0:
                    hits += stats.mannwhitneyu(treated, control, alternative="two-sided").pvalue < 0.05
            out["%g:%d" % (delta, m)] = round(hits / sims, 3)
    return out


def smallest_per_arm(table: Dict[str, float], delta: float) -> Optional[int]:
    for m in PER_ARM:
        if table["%g:%d" % (delta, m)] >= 0.8:
            return m
    return None


def notes_per_day(table: Sequence[dict]) -> float:
    last = table[-1]["t"]
    return round(sum(1 for r in table if last - r["t"] < timedelta(days=30)) / 30, 2)


def analyse(notes: Sequence[dict], replies: Optional[Sequence[dict]], draws: int, sims: int, seed: int) -> dict:
    table = note_table(notes)
    result = {"notes": len(table), "period": [table[0]["t"].date().isoformat(), table[-1]["t"].date().isoformat()],
              "notes_per_day_last_30_days": notes_per_day(table), "resolution": resolution(table),
              "dispersion": dispersion(table, draws * 5, seed), "early": early_vs_final(table), "skill": {}, "planted": {}, "power": {}}
    for name, key in (("views", "V"), ("likes", "L")):
        result["skill"][name] = evaluate(table, key, draws, seed)
        result["planted"][name] = planted_control(table, key, draws, seed)
        result["power"][name] = power(table, key, sims, seed)
    if replies is not None:
        rt = reply_table(replies)
        result["replies"] = {"resolution": resolution(rt), "dispersion": dispersion(rt, draws * 5, seed)} if len(rt) >= 10 else {"replies": len(rt)}
    result["readings"] = readings(result)
    return result


def readings(result: dict) -> dict:
    """The readings of the preregistration, applied mechanically."""
    d = result["dispersion"]
    early = result["early"].get("24", {})
    out = {"likes_usable_per_note": result["resolution"]["share_likes_ge_1"] >= 0.5,
           "like_rate_varies_beyond_chance": bool(d and d["D"] >= 1.5 and d["p_mc"] < 0.01),
           "features_carry_signal": {}, "instrument_detects_planted_effect": {}, "early_24h_stands_in": {}, "per_arm_for_80_percent_power": {}}
    for name in ("views", "likes"):
        out["features_carry_signal"][name] = {"typ": carries_signal(result["skill"][name]["skill"]["typ"]),
                                              "full": carries_signal(result["skill"][name]["skill"]["full"])}
        out["instrument_detects_planted_effect"][name] = carries_signal(result["planted"][name]["skill"]["typ"])
        out["per_arm_for_80_percent_power"][name] = {"%g" % delta: smallest_per_arm(result["power"][name], delta) for delta in EFFECTS}
        out["power_false_positive_rate_" + name] = {"%d" % m: result["power"][name]["0:%d" % m] for m in PER_ARM}
    out["early_24h_stands_in"] = {"views": bool(early.get("notes", 0) >= 30 and (early.get("views_rho") or 0) >= 0.9),
                                  "likes": bool(early.get("notes", 0) >= 30 and (early.get("likes_rho") or 0) >= 0.8)}
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--notes", required=True)
    parser.add_argument("--replies")
    parser.add_argument("--json")
    parser.add_argument("--draws", type=int, default=2000, help="bootstrap draws (the dispersion test uses five times as many)")
    parser.add_argument("--sims", type=int, default=1000, help="simulated comparisons per cell of the power table")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)
    result = analyse(load_jsonl(args.notes), load_jsonl(args.replies) if args.replies else None, args.draws, args.sims, args.seed)
    text = json.dumps(result, indent=1, sort_keys=True)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
