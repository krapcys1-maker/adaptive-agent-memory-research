"""Small-sample statistics for the memory benchmark: intervals, exact tests, minimum detectable effects, agreement and gap closed.

Everything here is deterministic given its inputs (bootstrap functions take a seed). The task is the unit of analysis: callers pass one decisive
outcome per task; samples, orders and repeats of the same task must be collapsed before they get here and never count as extra n.
"""

from __future__ import annotations

import math
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np
from scipy import stats

Z95 = 1.959964


def wilson(k: int, n: int, z: float = Z95) -> Tuple[float, float]:
    """Wilson score interval for k successes in n trials."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Exact two-sided interval."""
    lo = 0.0 if k == 0 else float(stats.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (lo, hi)


def zero_failure_upper_bound(n: int, alpha: float = 0.05) -> float:
    """One-sided exact upper bound on the failure rate after zero failures in n independent probes (about 3 / n)."""
    return 1.0 - alpha ** (1.0 / n)


def sign_test_p(wins: int, losses: int) -> float:
    """Two-sided exact sign (or McNemar-exact) test on decisive pairs; ties are dropped by the caller."""
    n = wins + losses
    return 1.0 if n == 0 else float(min(1.0, 2 * stats.binom.cdf(min(wins, losses), n, 0.5)))


def _critical(n: int, alpha: float) -> int:
    """Smallest k with P(X >= k | n, 0.5) <= alpha / 2."""
    k = n // 2 + 1
    while k <= n and stats.binom.sf(k - 1, n, 0.5) > alpha / 2:
        k += 1
    return k


def sign_test_power(n: int, p: float, alpha: float = 0.05) -> float:
    """Power of the two-sided exact sign test when the true win rate among decisive tasks is p."""
    k = _critical(n, alpha)
    if k > n:
        return 0.0
    return float(stats.binom.sf(k - 1, n, p) + stats.binom.cdf(n - k, n, p))


def mde_win_rate(n: int, alpha: float = 0.05, power: float = 0.8) -> Optional[float]:
    """Smallest win rate above 0.5 that the sign test on n decisive tasks detects with the given power (None if even a win rate of 1 cannot)."""
    if sign_test_power(n, 1.0, alpha) < power:
        return None
    lo, hi = 0.5, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if sign_test_power(n, mid, alpha) >= power else (mid, hi)
    return round(hi, 4)


def cohen_kappa(a: Sequence, b: Sequence) -> float:
    """Chance-corrected agreement of two raters on the same items (nominal labels)."""
    labels = sorted(set(a) | set(b), key=str)
    n = len(a)
    observed = sum(1 for x, y in zip(a, b) if x == y) / n
    expected = sum((sum(1 for x in a if x == c) / n) * (sum(1 for y in b if y == c) / n) for c in labels)
    return 1.0 if expected == 1.0 else (observed - expected) / (1 - expected)


def krippendorff_alpha_nominal(units: Sequence[Sequence]) -> float:
    """Krippendorff's alpha for nominal labels; each unit is the list of labels given to one item (units with fewer than two labels are skipped)."""
    counts: Dict = {}
    total = 0
    for labels in units:
        m = len(labels)
        if m < 2:
            continue
        total += m
        for i, x in enumerate(labels):
            for j, y in enumerate(labels):
                if i != j:
                    counts[(x, y)] = counts.get((x, y), 0) + 1.0 / (m - 1)
    if total == 0:
        return float("nan")
    cats = sorted({c for pair in counts for c in pair}, key=str)
    marginal = {c: sum(v for (x, _), v in counts.items() if x == c) for c in cats}
    observed = sum(v for (x, y), v in counts.items() if x != y)
    expected = sum(marginal[x] * marginal[y] for x in cats for y in cats if x != y) / (total - 1)
    return 1.0 if expected == 0 else 1.0 - observed / expected


def gap_closed(accuracy: float, floor: float, ceiling: float) -> Optional[float]:
    """(accuracy - floor) / (ceiling - floor); None when there is no headroom to close."""
    return None if ceiling <= floor else (accuracy - floor) / (ceiling - floor)


def paired_bootstrap_ci(differences: Sequence[float], draws: int = 5000, seed: int = 20261101, alpha: float = 0.05) -> Tuple[float, float]:
    """Percentile interval of the mean of per-task paired differences. Not for fewer than about 100 tasks (it under-covers there; use exact tests)."""
    d = np.asarray(differences, dtype=float)
    rng = np.random.default_rng(seed)
    means = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(draws)])
    return (float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2))))


def minimum_detectable_difference(sd: float, n: int, alpha: float = 0.05, power: float = 0.8) -> float:
    """Smallest mean paired difference detectable with a normal approximation, sd being the standard deviation of per-task differences."""
    return (float(stats.norm.ppf(1 - alpha / 2)) + float(stats.norm.ppf(power))) * sd / math.sqrt(n)


# ------------------------------------------------------------------------------------------------------ resampling stream (WMB-R1)
#
# The splitmix64 stream of scripts/analyze_writer_memory_sim.bootstrap_indices, vectorised. Pick p of draw d of a resample of size n is output number d * n + p
# (from 0) of the stream, and output k depends only on seed + (k + 1) * GAMMA modulo 2**64, so any block of the stream can be generated on its own: that is what lets
# 100,000 draws of 214 (171 MB as one int64 array) be produced and consumed 2,048 draws at a time. Nothing here depends on the numpy or Python version.

MASK64 = (1 << 64) - 1
SPLITMIX_GAMMA, SPLITMIX_MIX1, SPLITMIX_MIX2 = 0x9E3779B97F4A7C15, 0xBF58476D1CE4E5B9, 0x94D049BB133111EB
CHUNK_DRAWS = 2048


def splitmix_block(seed: int, first: int, count: int, modulus: int) -> np.ndarray:
    """Outputs `first` .. `first + count - 1` (counting from 0) of the splitmix64 stream of `seed`, each reduced modulo `modulus`, as int64."""
    if modulus <= 0:
        raise ValueError("modulus must be positive")
    with np.errstate(over="ignore"):                                  # unsigned 64-bit arithmetic wraps by design
        k = np.arange(first + 1, first + count + 1, dtype=np.uint64)
        state = np.uint64(seed & MASK64) + k * np.uint64(SPLITMIX_GAMMA)
        z = (state ^ (state >> np.uint64(30))) * np.uint64(SPLITMIX_MIX1)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(SPLITMIX_MIX2)
        z = z ^ (z >> np.uint64(31))
        return (z % np.uint64(modulus)).astype(np.int64)


def bootstrap_chunks(n: int, draws: int, seed: int, chunk_draws: int = CHUNK_DRAWS) -> Iterator[np.ndarray]:
    """The resamples (rows of `n` indices into range(n)) in blocks of at most `chunk_draws` rows; stacked they are bootstrap_indices(n, draws, seed)."""
    done = 0
    while done < draws:
        rows = min(chunk_draws, draws - done)
        yield splitmix_block(seed, done * n, rows * n, n).reshape(rows, n)
        done += rows


def bootstrap_indices(n: int, draws: int, seed: int) -> np.ndarray:
    """(draws, n) int64, row d = resample d: the same values as scripts/analyze_writer_memory_sim.bootstrap_indices (a test pins them). Whole at once it is
    draws * n * 8 bytes, so the analysis consumes bootstrap_chunks instead."""
    out = np.empty((draws, n), dtype=np.int64)
    row = 0
    for block in bootstrap_chunks(n, draws, seed):
        out[row: row + len(block)] = block
        row += len(block)
    return out


def multiplicity(indices: np.ndarray, size: int) -> np.ndarray:
    """(rows, size) counts: how often each of `size` units occurs in each row of `indices`."""
    rows = indices.shape[0]
    flat = (np.arange(rows, dtype=np.int64)[:, None] * size + indices).ravel()
    return np.bincount(flat, minlength=rows * size).reshape(rows, size)


def day_groups(days: Sequence[str]) -> Tuple[List[str], np.ndarray]:
    """The distinct days in ascending order and, for every task position, the index of its day."""
    names = sorted(set(days))
    lookup = {d: k for k, d in enumerate(names)}
    return names, np.array([lookup[d] for d in days], dtype=np.int64)


def day_block_indices(days: Sequence[str], draws: int, seed: int) -> List[np.ndarray]:
    """Day-block bootstrap, spelled out: the days are resampled with `bootstrap_indices(number of days, draws, seed)` and a resample is the tasks of the picked days,
    a day's tasks kept together (ascending position), days in the order they were picked. Resample sizes differ. Materialised: for tests and small draws only."""
    names, of_task = day_groups(days)
    members = [np.flatnonzero(of_task == k) for k in range(len(names))]
    out: List[np.ndarray] = []
    for block in bootstrap_chunks(len(names), draws, seed):
        for picks in block:
            out.append(np.concatenate([members[k] for k in picks]) if len(picks) else np.zeros(0, dtype=np.int64))
    return out


def fire_size(q: float, n: int) -> int:
    """ceil(q * n) tasks fire; the product is rounded to 9 places first so that 0.2 * 215 = 43.00000000000001 is 43, not 44."""
    return int(math.ceil(round(q * n, 9)))


def interval_positions(draws: int, alpha: float = 0.05) -> Tuple[int, int]:
    """0-based positions in the sorted draws: floor(alpha/2 * draws) and ceil((1 - alpha/2) * draws) - 1 (exact arithmetic, products rounded to 9 places)."""
    return int(math.floor(round(alpha / 2 * draws, 9))), int(math.ceil(round((1 - alpha / 2) * draws, 9))) - 1


def interval_of(values: Sequence[float], alpha: float = 0.05) -> Tuple[float, float]:
    """The README interval of bootstrap draws: [sorted(D*)[floor(0.025 * draws)], sorted(D*)[ceil(0.975 * draws) - 1]]."""
    ordered = np.sort(np.asarray(values))
    lo, hi = interval_positions(len(ordered), alpha)
    return float(ordered[lo]), float(ordered[hi])
