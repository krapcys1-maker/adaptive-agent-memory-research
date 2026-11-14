"""K1 v0.4 (D9, owner's condition): per-task length imbalance between M and each control arm, the pre-registered balance
criterion, the length sensitivity analysis WR5 and the rule that forbids attributing an effect to memory content when
length differences may explain it. Frozen code; used by the reading (k1_v04_reading.read(..., length=...)).

Measure. For task i and control arm C in {P, X, S}: T_i(a) = mean over the sampled blocks of the summed block tokens of
all turns of the task (stimuli are frozen, so this does not depend on how far the episode got). Turn-0 tokens are exact
from the run: prompt_eval_count(a, t0, s0) - prompt_eval_count(N, t0, s0) in the same block. Later turns: content
characters x rho(a, d), where rho(a, d) = sum of exact turn-0 tokens / sum of turn-0 characters of arm a in domain d.
Imbalance x_i(C) = ln(T_i(M) / T_i(C)) (positive: the memory block is longer).

Pre-registered criterion of acceptable imbalance, per contrast M - C:
  B1  |mean_i x_i(C)| <= ln(1.05)       (mean token length within 5%; for P this is also the T-length gate per domain)
  B2  share of tasks with |x_i(C)| > ln(1.25) is reported (no threshold; distribution in the report)
WR5 (length sensitivity, per contrast): ordinary least squares d_i = alpha + beta * x_i, HC3 standard errors, two-sided
t intervals at 98.33% with n - 2 df; alpha = contrast at equal length. Balanced subset |x_i| <= ln(1.10): estimate and
98.33% t interval (descriptive).
Rule LEN (length may explain the result) for a contrast, true if any of:
  L1  B1 fails;
  L2  the state of the alpha interval differs from the state of the main interval;
  L3  the beta interval excludes 0 and |beta * mean x| >= 0.5 * |main estimate|.
If LEN: the contrast sentence carries the length caveat, and no sentence attributes any effect of that contrast to memory
content (composites A and B that rest on it are withheld; D is withheld if the alpha interval reaches 10 pp).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

LEVEL = 1 - 0.05 / 3
B1 = math.log(1.05)
BIG = math.log(1.25)
BAL = math.log(1.10)


def t_interval(v, level=LEVEL):
    v = np.asarray(v, float)
    n = len(v)
    h = stats.t.ppf(1 - (1 - level) / 2, n - 1) * v.std(ddof=1) / math.sqrt(n)
    return v.mean() - h, v.mean() + h


def wr5(d, x, level=LEVEL):
    """d: per-task contrast differences in pp; x: per-task log imbalance. Returns the WR5 summary."""
    d, x = np.asarray(d, float), np.asarray(x, float)
    n = len(d)
    X = np.column_stack([np.ones(n), x])
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ d
    e = d - X @ b
    h = np.einsum("ij,jk,ik->i", X, XtXi, X)
    cov = XtXi @ (X.T * (e / (1 - h)) ** 2) @ X @ XtXi           # HC3
    q = stats.t.ppf(1 - (1 - level) / 2, n - 2)
    se = np.sqrt(np.diag(cov))
    bal = np.abs(x) <= BAL
    out = {"mean_x": float(x.mean()), "share_big": float(np.mean(np.abs(x) > BIG)), "alpha": float(b[0]),
           "adj": (float(b[0] - q * se[0]), float(b[0] + q * se[0])), "beta": float(b[1]),
           "beta_ci": (float(b[1] - q * se[1]), float(b[1] + q * se[1])), "est": float(d.mean()), "n_bal": int(bal.sum())}
    out["balanced"] = t_interval(d[bal], level) if bal.sum() >= 10 else None
    return out


def len_rule(w, main_interval, state_fn):
    """Returns (flag, reasons). w: wr5() output; main_interval: (L, U) of the contrast; state_fn: interval -> state."""
    reasons = []
    if abs(w["mean_x"]) > B1:
        reasons.append(f"średnia nierównowaga długości {100 * (math.exp(w['mean_x']) - 1):+.1f}% (dopuszczalne ±5%)")
    s_main, s_adj = state_fn(*main_interval), state_fn(*w["adj"])
    if s_adj != s_main:
        reasons.append(f"po korekcie długości stan {s_adj} zamiast {s_main}")
    lo, hi = w["beta_ci"]
    if (lo > 0 or hi < 0) and abs(w["beta"] * w["mean_x"]) >= 0.5 * abs(w["est"]):
        reasons.append("zależność wyniku od różnicy długości tłumaczy co najmniej połowę estymaty")
    return bool(reasons), reasons
