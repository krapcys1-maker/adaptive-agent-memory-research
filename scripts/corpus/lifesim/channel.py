"""Channel H for LifeSim: the heartbeat-like measurement of arousal and its control arms.

What this module provides
-------------------------
* ``make_channel(world, arm, reliability, nu, seed, need=None)`` -> ``Channel``: one reading
  per observation, in stream order. The reference arm TRUE is
  ``H = clip(g_w((1 - nu) A + nu X) + sigma e, 0, 1)`` where ``A`` is the arousal of the
  line (a retelling line, one whose mentions are all 'recall' or whose frame is 'retell',
  has ``retell_a_factor`` times its situation's arousal), ``X`` is a nuisance activity series
  (bursts at ``x_burst_rate`` per day that decay over ~90 minutes: stairs, coffee), ``g_w`` is
  a random strictly increasing piecewise-linear map per (channel seed): ranks transfer,
  levels do not, and ``e`` is unit-variance noise made exactly orthogonal to the rank of A.
* ``solve_sigma(world, target_corr, seed, nu=None)``: the noise scale ``sigma`` for which the
  realised rank correlation corr(H, A) equals the target reliability (within 0.03; usually
  within 0.005). Reliability is the SPEARMAN correlation, because a monotone map keeps ranks
  but not Pearson correlation. A target above what the nuisance share allows even at
  ``sigma = 0`` is reached by shrinking the nuisance share (``nu_eff``, reported in
  ``Channel.meta``); a target of 0 removes the signal and keeps noise with the signal's own
  SD. ``solve_channel`` returns (sigma, nu_eff, achieved).
* The control arms. SHUF_TYPE: permutation of the TRUE readings within observation kind (scene
  of the hosting situation, retellings apart), exact marginal per kind. SHUF_LIFE: global
  permutation, exact marginal. TIME_SHIFT: circular shift in stream order (keeps the
  autocorrelation). RANDOM: independent resample from the TRUE marginal. CONST: the mean of
  TRUE for every line. INVERTED: 1 - H. NUISANCE_ONLY: A replaced by its mean, same sigma.
  LAG: the reading of an earlier line. ABSENT: no reading (all None). ORACLE: exactly A.
  LEAKY: mostly the later-need label (``need`` = oids that evidence some query) plus a little
  TRUE; it exists only as a positive control for the leakage gate.
* ``obs_arousal``, ``obs_kind``, ``is_retell``, ``realised_corr``, ``restrict_channel`` (keep
  the readings of the surviving lines after ``delete_events``) and ``with_faults`` (dropout
  and sign reversal).

ASSUMED constants of this module: the nuisance burst shape (amplitude 0.3-1.0, ~90 minute decay), the
six-segment random monotone map, ``LEAK_SHARE`` = 0.8 and ``channel_lag_lines`` (6, see
``scenes.EXTRA_PARAMS``).

All channel randomness uses streams ('channel', ...) keyed by the channel ``seed``; the nuisance
series, the map and the noise do not depend on the arm, so surrogates share the TRUE channel's
ingredients. The channel never touches World.digest().

What this module does NOT do: it reads no text, uses no future information in TRUE (LEAKY and
ORACLE exist to be detected), makes no claim that reliability 0.7 is realistic (the whole
ladder is a dial), and uses neither numpy nor scipy.
"""

from __future__ import annotations

import bisect
import math
from typing import Iterable, Sequence

from .appraisal import clip01, pearson, ranks
from .rng import Rng, dexp, q, stream
from .scenes import param
from .schema import CHANNEL_ARMS, Channel, ObsSpec, World

__all__ = [
    "make_channel", "solve_sigma", "solve_channel", "obs_arousal", "obs_kind", "is_retell",
    "realised_corr", "restrict_channel", "with_faults", "nuisance_series", "monotone_map",
    "ARMS", "LEAK_SHARE",
]

ARMS = CHANNEL_ARMS
#: ASSUMED share of the LEAKY reading that is the later-need label.
LEAK_SHARE = 0.8
_SIGMA_MAX = 64.0
_TAU_MINUTES = 90.0
_KNOTS = 6
_CACHE: dict = {}


# ------------------------------------------------------------------- per-line quantities


def is_retell(spec: ObsSpec) -> bool:
    """A retelling: every mention is a 'recall', or the frame says 'retell'."""
    return spec.frame == "retell" or (bool(spec.mentions) and all(m.role == "recall" for m in spec.mentions))


def obs_arousal(world: World) -> list[float]:
    """Arousal of every line in stream order (retellings at ``retell_a_factor`` x the situation's)."""
    f = world.cfg.retell_a_factor
    out = []
    for spec in world.obs_specs:
        a = world.situation(spec.sid).A
        out.append(a * f if is_retell(spec) else a)
    return out


def obs_kind(world: World, spec: ObsSpec) -> str:
    """Observation kind for SHUF_TYPE: the hosting scene, with retellings as their own kind."""
    scene = world.situation(spec.sid).scene
    return scene + "/retell" if is_retell(spec) else scene


# ---------------------------------------------------------------- nuisance and the map


def nuisance_series(world: World, seed: int) -> list[float]:
    """Nuisance activity X in [0, 1] at every line: Poisson bursts (``x_burst_rate`` per day,
    amplitude 0.3-1.0) decaying with a ~90 minute time constant. Independent of A."""
    rng = stream(seed, "channel", "nuisance")
    specs = world.obs_specs
    if not specs:
        return []
    last_day = max(s.t_obs for s in specs) // 1440 + 1
    bursts: list[tuple[int, float]] = []
    for day in range(last_day):
        for _ in range(rng.poisson(world.cfg.x_burst_rate)):
            bursts.append((day * 1440 + rng.below(1440), 0.3 + 0.7 * rng.u()))
    bursts.sort()
    starts = [b[0] for b in bursts]
    out = []
    for spec in specs:
        t = spec.t_obs
        j = bisect.bisect_right(starts, t)
        total = 0.0
        i = j - 1
        while i >= 0 and t - starts[i] <= 10 * _TAU_MINUTES:
            total += bursts[i][1] * dexp(-(t - starts[i]) / _TAU_MINUTES)
            i -= 1
        out.append(min(1.0, total))
    return out


def monotone_map(rng: Rng) -> tuple[float, ...]:
    """Knots of a strictly increasing piecewise-linear map of [0, 1] onto [0, 1]."""
    steps = [0.15 + rng.expo(1.0) for _ in range(_KNOTS)]
    total = sum(steps)
    knots = [0.0]
    acc = 0.0
    for s in steps:
        acc += s
        knots.append(acc / total)
    knots[-1] = 1.0
    return tuple(knots)


def _apply_map(knots: Sequence[float], u: float) -> float:
    k = len(knots) - 1
    u = clip01(u)
    j = min(k - 1, int(u * k))
    t = u * k - j
    return knots[j] + t * (knots[j + 1] - knots[j])


def _orthogonal_noise(rng: Rng, ra: Sequence[float]) -> list[float]:
    """Unit-variance, zero-mean noise with exactly zero Pearson correlation to the ranks ``ra``."""
    n = len(ra)
    z = [rng.normal() for _ in range(n)]
    if n < 3:
        return z
    mean_r = sum(ra) / n
    sd_r = math.sqrt(sum((r - mean_r) * (r - mean_r) for r in ra) / n)
    mz = sum(z) / n
    z = [v - mz for v in z]
    if sd_r > 0.0:
        r = [(x - mean_r) / sd_r for x in ra]
        beta = sum(a * b for a, b in zip(z, r)) / n
        z = [a - beta * b for a, b in zip(z, r)]
    sd = math.sqrt(sum(v * v for v in z) / n)
    return [v / sd for v in z] if sd > 0.0 else z


def _rho(h: Sequence[float], ra: Sequence[float]) -> float:
    return pearson(ranks(h), ra)


# ------------------------------------------------------------------------- the solver


class _Ingredients:
    """Everything the TRUE channel is made of, computed once per (world, seed)."""

    def __init__(self, world: World, seed: int) -> None:
        self.a = obs_arousal(world)
        self.ra = ranks(self.a)
        self.x = nuisance_series(world, seed)
        self.knots = monotone_map(stream(seed, "channel", "gw"))
        self.e = _orthogonal_noise(stream(seed, "channel", "eps"), self.ra)

    def lat(self, nu: float, a: Sequence[float] | None = None) -> list[float]:
        a = self.a if a is None else a
        return [_apply_map(self.knots, (1.0 - nu) * ai + nu * xi) for ai, xi in zip(a, self.x)]

    def reading(self, lat: Sequence[float], sigma: float) -> list[float]:
        return [q(clip01(l + sigma * e)) for l, e in zip(lat, self.e)]


def _ingredients(world: World, seed: int) -> _Ingredients:
    key = ("ing", world.digest(), seed, world.cfg.retell_a_factor, world.cfg.x_burst_rate)
    if key not in _CACHE:
        if len(_CACHE) > 200:
            _CACHE.clear()
        _CACHE[key] = _Ingredients(world, seed)
    return _CACHE[key]


def solve_channel(world: World, target_corr: float, seed: int, nu: float | None = None) -> tuple[float, float, float]:
    """(sigma, nu_eff, achieved rank correlation) for the TRUE channel at a target reliability."""
    nu = world.cfg.nu if nu is None else nu
    key = ("solve", world.digest(), seed, q(target_corr), q(nu), world.cfg.retell_a_factor,
           world.cfg.x_burst_rate)
    if key not in _CACHE:
        _CACHE[key] = _solve_uncached(world, target_corr, seed, nu)
    return _CACHE[key]


def _solve_uncached(world: World, target_corr: float, seed: int, nu: float) -> tuple[float, float, float]:
    ing = _ingredients(world, seed)
    n = len(ing.a)
    if n < 4:
        return 0.0, nu, 0.0
    ra = ing.ra
    if target_corr <= 0.02:  # no signal: noise with the SD of a working channel's latent signal
        lat = ing.lat(nu)
        mean = sum(lat) / n
        sd = math.sqrt(sum((v - mean) * (v - mean) for v in lat) / n)
        h = [q(clip01(mean + sd * e)) for e in ing.e]
        return q(sd), nu, _rho(h, ra)
    lat = ing.lat(nu)
    nu_eff = nu
    if _rho(ing.reading(lat, 0.0), ra) < target_corr:  # ceiling reached: shrink the nuisance
        lo, hi = 0.0, nu
        for _ in range(0 if target_corr >= 0.999 else 40):  # reliability 1.0 means no nuisance at all
            mid = (lo + hi) / 2.0
            if _rho(ing.reading(ing.lat(mid), 0.0), ra) >= target_corr:
                lo = mid
            else:
                hi = mid
        nu_eff = lo
        lat = ing.lat(nu_eff)
        return 0.0, q(nu_eff), _rho(ing.reading(lat, 0.0), ra)
    lo, hi = 0.0, 0.5
    while _rho(ing.reading(lat, hi), ra) > target_corr and hi < _SIGMA_MAX:
        lo, hi = hi, hi * 2.0
    best = (abs(_rho(ing.reading(lat, lo), ra) - target_corr), lo)
    for _ in range(40):
        mid = (lo + hi) / 2.0
        r = _rho(ing.reading(lat, mid), ra)
        if abs(r - target_corr) < best[0]:
            best = (abs(r - target_corr), mid)
        if best[0] < 1e-3:
            break
        if r > target_corr:
            lo = mid
        else:
            hi = mid
    sigma = best[1]
    return q(sigma), q(nu_eff), _rho(ing.reading(lat, q(sigma)), ra)


def solve_sigma(world: World, target_corr: float, seed: int, nu: float | None = None) -> float:
    """The noise scale of the TRUE channel that realises ``target_corr`` (see the module doc)."""
    return solve_channel(world, target_corr, seed, nu)[0]


# ------------------------------------------------------------------------------ arms


def realised_corr(world: World, channel: Channel) -> float:
    """Spearman correlation between a channel's readings and the line arousal (None skipped)."""
    a = obs_arousal(world)
    pairs = [(h, ai) for h, ai in zip(channel.h, a) if h is not None]
    if len(pairs) < 3:
        return 0.0
    return pearson(ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs]))


def _permute_within(rng: Rng, groups: Sequence[Sequence[int]], values: Sequence[float]) -> list[float]:
    out = list(values)
    for idx in groups:
        vals = [values[i] for i in idx]
        rng.shuffle(vals)
        for i, v in zip(idx, vals):
            out[i] = v
    return out


def make_channel(world: World, arm: str, reliability: float, nu: float | None, seed: int,
                 need: Iterable[str] | None = None) -> Channel:
    """The channel of ``arm`` for a world (see the module docstring for every arm).

    ``reliability`` is the target rank correlation of the TRUE channel (the surrogates inherit
    TRUE's readings); ``nu`` None means ``cfg.nu``; ``need`` (oids that evidence a query) is
    required for LEAKY only. The result is attached with ``world.with_channel(ch)``."""
    if arm not in CHANNEL_ARMS:
        raise ValueError("arm must be one of %s, got %r" % (CHANNEL_ARMS, arm))
    nu = world.cfg.nu if nu is None else nu
    specs = world.obs_specs
    oids = tuple(s.oid for s in specs)
    n = len(oids)
    ing = _ingredients(world, seed)
    sigma, nu_eff, achieved = solve_channel(world, reliability, seed, nu)
    lat = ing.lat(nu_eff)
    if reliability <= 0.02 and n >= 4:  # the no-signal channel of the reliability ladder
        mean = sum(lat) / n
        true = [q(clip01(mean + sigma * e)) for e in ing.e]
    else:
        true = ing.reading(lat, sigma)
    rng = stream(seed, "channel", arm)
    if arm == "TRUE":
        h: list = list(true)
    elif arm == "SHUF_TYPE":
        groups: dict[str, list[int]] = {}
        for i, s in enumerate(specs):
            groups.setdefault(obs_kind(world, s), []).append(i)
        h = _permute_within(rng, list(groups.values()), true)
    elif arm == "SHUF_LIFE":
        h = _permute_within(rng, [list(range(n))], true)
    elif arm == "TIME_SHIFT":
        off = rng.ri(n // 4, max(n // 4, (3 * n) // 4)) if n > 3 else 0
        h = [true[(i + off) % n] for i in range(n)]
    elif arm == "RANDOM":
        h = [true[rng.below(n)] for _ in range(n)] if n else []
    elif arm == "CONST":
        c = q(sum(true) / n) if n else 0.0
        h = [c] * n
    elif arm == "INVERTED":
        h = [q(1.0 - v) for v in true]
    elif arm == "NUISANCE_ONLY":
        mean_a = sum(ing.a) / n if n else 0.0
        h = ing.reading(ing.lat(nu_eff, [mean_a] * n), sigma) if n else []
    elif arm == "LAG":
        lag = int(param(world.cfg, "channel_lag_lines"))
        h = [None if i < lag else true[i - lag] for i in range(n)]
    elif arm == "ABSENT":
        h = [None] * n
    elif arm == "ORACLE":
        h = [q(a) for a in ing.a]
    else:  # LEAKY
        if need is None:
            raise ValueError("arm LEAKY needs `need`, the oids that evidence some query")
        needed = set(need)
        h = [q(clip01((1.0 - LEAK_SHARE) * t + LEAK_SHARE * (1.0 if o in needed else 0.0)))
             for t, o in zip(true, oids)]
    x = tuple(q(v) for v in ing.x)
    ch = Channel(arm=arm, reliability=reliability, nu=nu, seed=seed, oids=oids, h=tuple(h), sigma=sigma,
                 x=x, meta=(("achieved_true", q(achieved)), ("nu_eff", nu_eff)))
    return Channel(arm=arm, reliability=reliability, nu=nu, seed=seed, oids=oids, h=ch.h, sigma=sigma,
                   realised_corr=q(realised_corr(world, ch)), x=x, meta=ch.meta)


def restrict_channel(channel: Channel, keep: Iterable[str]) -> Channel:
    """The channel restricted to the oids in ``keep`` (readings of surviving lines unchanged)."""
    keep_set = set(keep)
    idx = [i for i, o in enumerate(channel.oids) if o in keep_set]
    return Channel(arm=channel.arm, reliability=channel.reliability, nu=channel.nu, seed=channel.seed,
                   oids=tuple(channel.oids[i] for i in idx), h=tuple(channel.h[i] for i in idx),
                   sigma=channel.sigma, realised_corr=channel.realised_corr,
                   x=tuple(channel.x[i] for i in idx) if len(channel.x) == len(channel.oids) else (),
                   meta=channel.meta)


def with_faults(channel: Channel, dropout: float, sign_reversal: float, seed: int) -> Channel:
    """Fault arm: each reading is dropped with probability ``dropout`` (-> None) or, otherwise,
    reversed (1 - h) with probability ``sign_reversal``."""
    rng = stream(seed, "channel", "faults")
    out: list = []
    for v in channel.h:
        u1, u2 = rng.u(), rng.u()
        if v is None or u1 < dropout:
            out.append(None)
        else:
            out.append(q(1.0 - v) if u2 < sign_reversal else v)
    meta = tuple(sorted(dict(channel.meta, dropout=dropout, sign_reversal=sign_reversal).items()))
    return Channel(arm=channel.arm, reliability=channel.reliability, nu=channel.nu, seed=channel.seed,
                   oids=channel.oids, h=tuple(out), sigma=channel.sigma, realised_corr=channel.realised_corr,
                   x=channel.x, meta=meta)
