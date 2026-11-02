"""Appraisal for LifeSim: from situation features to arousal A and valence V.

What this module provides
-------------------------
* ``appraise(feats, mapping, rng, cfg)`` -> ``(A, V)``. Three mappings, one drawn per
  world (M1, M2 in development; M3 only in a held-out test cell):

  - M1 additive: ``A = clip(w0 g + w1 n + w2 k + w3 b g + w4 (1-p)[c<0] + eps)`` with
    ``eps ~ N(0, m1_eps_sd^2)``, then capped at ``m1_cap_base + m1_cap_slope * g`` so that
    novelty without goal relevance stays moderate;
  - M2 noisy-OR: ``A = 1 - prod_j (1 - w_j x_j)`` over ``x = (n, g, (1-p) g, v, k g)``;
  - M3 prediction error only, no goals and no stakes: ``A = clip(n (0.4 + 0.6 |c|) + eps)``.

  ``V = tanh(v_gain_c c + v_gain_norm norm)``. Here ``g`` is goal relevance, ``n`` the
  surprise ``clip(surprisal_bits / surprise_bits_scale, 0, 1)``, ``k`` the stakes, ``b`` the
  bond of the main other actor, ``p`` the coping potential, ``c`` the signed
  conduciveness and ``v = |norm|``. Every weight is an ASSUMED field of ``TierCfg``; the
  functional forms borrow only monotonicity in relevance, surprise and stakes and the
  relevance cap from appraisal theory (Scherer, OCC). They define what the benchmark's
  signal is, not what a person's is.
* ``surprisal_bits(prior, value)``: bits of a value under the generator's own routine
  model (a ``Prior``); a value the prior never produces gets ``max_bits``.
* ``mood_step(mood, events, cfg)``: ``M_t = decay M_{t-1} + gain mean_day(V A)`` on days
  with events and ``quiet_decay M_{t-1}`` on quiet days.
* ``pearson``, ``ranks``, ``spearman``, ``summary``: tiny pure-Python statistics used by
  ``world`` (the corr(n, k) gate) and ``channel`` (reliability = rank correlation).

Draw discipline: ``appraise`` consumes exactly ONE normal draw whatever the mapping, so
switching the mapping never shifts the rest of an event's stream.

What this module does NOT do: it draws no features (``scenes`` does), builds no world,
reads no text, uses no mood-congruent arousal (mood is a covariate only), and makes no
claim that any mapping describes human emotion; it uses only the standard library and the
deterministic math kit of ``rng`` for stored floats.
"""

from __future__ import annotations

import math
from typing import Sequence

from .rng import Rng, dlog2, dtanh, q
from .schema import Feats, Prior, TierCfg

__all__ = [
    "appraise", "valence", "surprisal_bits", "mood_step", "clip01", "pearson", "ranks",
    "spearman", "summary", "MAPPING_NAMES",
]

MAPPING_NAMES = ("M1", "M2", "M3")
_DEFAULT_CFG = TierCfg()


def clip01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def valence(feats: Feats, cfg: TierCfg | None = None) -> float:
    """V = tanh(v_gain_c * c + v_gain_norm * signed norm), quantised."""
    cfg = cfg or _DEFAULT_CFG
    return q(dtanh(cfg.v_gain_c * feats.conduciveness + cfg.v_gain_norm * feats.norm))


def appraise(feats: Feats, mapping: str, rng: Rng, cfg: TierCfg | None = None) -> tuple[float, float]:
    """Arousal A in [0, 1] and valence V in [-1, 1] of a situation under a mapping."""
    cfg = cfg or _DEFAULT_CFG
    eps = rng.normal()  # always exactly one draw
    n = feats.surprise(cfg.surprise_bits_scale)
    g, k, b, p, c = feats.goal_rel, feats.stakes, feats.bond, feats.control, feats.conduciveness
    v = abs(feats.norm)
    if mapping == "M1":
        w = cfg.m1_w
        a = (w[0] * g + w[1] * n + w[2] * k + w[3] * b * g
             + w[4] * (1.0 - p) * (1.0 if c < 0.0 else 0.0) + cfg.m1_eps_sd * eps)
        a = min(clip01(a), cfg.m1_cap_base + cfg.m1_cap_slope * g)
    elif mapping == "M2":
        w = cfg.m2_w
        prod = 1.0
        for wj, xj in zip(w, (n, g, (1.0 - p) * g, v, k * g)):
            prod *= 1.0 - wj * xj
        a = 1.0 - prod
    elif mapping == "M3":
        a = clip01(n * (0.4 + 0.6 * abs(c)) + cfg.m3_noise_sd * eps)
    else:
        raise ValueError("mapping must be one of %s, got %r" % (MAPPING_NAMES, mapping))
    return q(clip01(a)), valence(feats, cfg)


def surprisal_bits(prior: Prior, value: str, max_bits: float = 20.0) -> float:
    """-log2 p(value) under a routine model; ``max_bits`` if the prior never yields it."""
    p = prior.p_of(value)
    if p <= 0.0:
        return q(max_bits)
    return q(min(max_bits, -dlog2(p)))


def mood_step(mood: float, events: Sequence[tuple[float, float]], cfg: TierCfg | None = None) -> float:
    """One day of mood: ``events`` are the day's (A, V) pairs; empty means a quiet day."""
    cfg = cfg or _DEFAULT_CFG
    if not events:
        return q(cfg.mood_quiet_decay * mood)
    mean_va = sum(a * v for a, v in events) / len(events)
    return q(cfg.mood_decay * mood + cfg.mood_gain * mean_va)


# ------------------------------------------------------------------ small statistics


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson correlation; 0.0 if either series is constant or shorter than 2."""
    n = len(xs)
    if n != len(ys):
        raise ValueError("pearson needs equally long series")
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) * (x - mx) for x in xs)
    syy = sum((y - my) * (y - my) for y in ys)
    if sxx <= 0.0 or syy <= 0.0:
        return 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def ranks(xs: Sequence[float]) -> list[float]:
    """Average ranks (1-based, ties share the mean rank)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        mean_rank = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            out[order[t]] = mean_rank
        i = j + 1
    return out


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman rank correlation (Pearson of the average ranks)."""
    return pearson(ranks(xs), ranks(ys))


def summary(values: Sequence[float]) -> dict:
    """Mean, SD, share below 0.3 and share at or above 0.7 of a series of arousals."""
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "below_03": 0.0, "at_least_07": 0.0}
    mean = sum(values) / n
    var = sum((x - mean) * (x - mean) for x in values) / n
    return {"n": n, "mean": mean, "sd": math.sqrt(var),
            "below_03": sum(1 for x in values if x < 0.3) / n,
            "at_least_07": sum(1 for x in values if x >= 0.7) / n}
