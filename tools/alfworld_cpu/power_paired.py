"""Simulated power of a paired comparison of two arms on the same task list.

Model: every task has its own success probability p_i ~ Beta, with mean `--mean`, and
with spread chosen so that two identical runs disagree on a share `--flip` of the tasks
(the measured noise: about 0.13 for plain retries in Reflexion's logs, 0.20 between
two numeric precisions of Qwen3-4B on 20 ALFWorld tasks). The treatment shifts every
task's logit by the same amount, so that the mean rises by `delta` points; this
uniform effect is an optimistic assumption. Test: sign-flip permutation of the
per-task differences (mean over seeds), one-sided, alpha 0.05.

Usage:
    python power_paired.py [--sims 600] [--mean 0.65]
"""
from __future__ import annotations

import argparse

import numpy as np


def beta_params(mean: float, flip: float) -> tuple[float, float]:
    # E[2p(1-p)] = flip  =>  E[p^2] = mean - flip/2 ;  var = E[p^2] - mean^2
    var = (mean - flip / 2) - mean * mean
    k = mean * (1 - mean) / var - 1
    return mean * k, (1 - mean) * k


def power(rng, n: int, seeds: int, delta_pts: float, flip: float, mean: float, sims: int, alpha: float = 0.05) -> float:
    a, b = beta_params(mean, flip)
    hits = 0
    for _ in range(sims):
        p = rng.beta(a, b, n)
        logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
        lo, hi = 0.0, 5.0
        for _ in range(30):  # bisection for the logit shift that adds delta to the mean
            mid = (lo + hi) / 2
            if (1 / (1 + np.exp(-(logit + mid)))).mean() - p.mean() < delta_pts / 100:
                lo = mid
            else:
                hi = mid
        q = 1 / (1 + np.exp(-(logit + lo)))
        arm_a = rng.random((seeds, n)) < p
        arm_b = rng.random((seeds, n)) < q
        d = arm_b.mean(0) - arm_a.mean(0)
        null = (rng.choice([-1, 1], size=(400, n)) * d).mean(1)
        hits += np.mean(null >= d.mean()) < alpha
    return hits / sims


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sims", type=int, default=600)
    ap.add_argument("--mean", type=float, default=0.65)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    print("flip | tasks | seeds | power for +5 / +10 / +15 points")
    for flip in (0.13, 0.20):
        for n in (60, 134, 274):
            for seeds in (1, 3):
                pw = [power(rng, n, seeds, d, flip, args.mean, args.sims) for d in (5, 10, 15)]
                print(f"{flip:.2f} | {n} | {seeds} | " + " / ".join(f"{x:.2f}" for x in pw))


if __name__ == "__main__":
    main()
