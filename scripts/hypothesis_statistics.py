"""Pure statistics for a hypothesis ledger: Holm correction, the smallest usable McNemar sample, and canonical hashing.

Extracted from the AAMR coordinator's hypothesis ledger (coordinator commits c429d82 and 799c356, module
``aamr_coord/lab/hypotheses.py``). Only functions that need no database, clock or file are kept here; the ledger
class itself and its storage stay in the coordinator. The logic is unchanged; docstrings are translated into English
and ``min_discordant`` gained a guard for alpha outside (0, 1) (the original would never return for alpha <= 0).
After an external audit (gpt raport, 2026-11-18) the inputs are validated: ``mcnemar_one_sided`` rejects counts that
are not non-negative integers (it returned p = 0 for (5, -1)), and ``holm`` rejects alpha outside (0, 1) and p-values
that are NaN, infinite or outside [0, 1] (a NaN made the result depend on the input order).
The methodology these functions serve is described in
``docs/11-research-laboratory/hypothesis-ledger-methodology.md``.

Standard library only. Nothing here opens a file or a network connection.
"""
from __future__ import annotations

import hashlib
import json
import math
import numbers
import re
from typing import Any

SCOPE_KEYS = ("mechanism", "variable", "corpus", "direction", "metric")


def canonical(obj: Any) -> str:
    """Deterministic JSON text: sorted keys, no whitespace, non-ASCII kept, unknown types as strings."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(scope: dict) -> str:
    """SHA-256 of the normalised scope (mechanism, variable, corpus, direction, metric). Case and spacing do not matter."""
    norm = {k: re.sub(r"\s+", " ", str(scope.get(k, "")).strip().lower()) for k in SCOPE_KEYS}
    return hashlib.sha256(canonical(norm).encode("utf-8")).hexdigest()


def _count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, numbers.Integral) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}")
    return int(value)


def mcnemar_one_sided(gained: int, lost: int) -> float:
    """Exact one-sided McNemar test: P(X >= gained) with X ~ Binomial(gained + lost, 1/2).

    ``gained`` and ``lost`` are counts of discordant pairs, so anything but a non-negative integer is an error.
    """
    gained, lost = _count(gained, "gained"), _count(lost, "lost")
    n = gained + lost
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(gained, n + 1)) / 2 ** n


def min_discordant(alpha: float) -> int:
    """Smallest number of discordant pairs for which the exact one-sided McNemar test can reach p <= alpha.

    With k discordant pairs the smallest attainable p is 0.5 ** k, so a test with fewer pairs cannot succeed at any
    result and is not worth running.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between 0 and 1")
    k = 1
    while 0.5 ** k > alpha:
        k += 1
    return k


def holm(pvals: dict[str, float | None], alpha: float) -> dict[str, dict]:
    """Holm step-down correction for one family of tests.

    ``None`` (a test that was registered but not run, or that was invalid) counts as p = 1.0, so unexecuted tests make
    the correction stricter, never looser. Ties are broken by the test identifier. For each test the result holds the
    p-value used, its rank, the family size ``m``, the Holm threshold ``alpha / (m - rank + 1)``, the adjusted p-value,
    whether H0 is rejected, and whether the test was executed.

    A p-value that is NaN, infinite, not a number or outside [0, 1] raises ValueError, and so does alpha outside
    (0, 1). A NaN never compares, so it would make the sort, and with it the rejections, depend on the input order.
    """
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0 < alpha < 1:
        raise ValueError(f"alpha must be strictly between 0 and 1, got {alpha!r}")
    for k, p in pvals.items():
        if p is None:
            continue
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError(f"p-value of {k!r} must be a finite number in [0, 1] or None (not run), got {p!r}")
    items = sorted(((1.0 if p is None else float(p), k) for k, p in pvals.items()), key=lambda x: (x[0], x[1]))
    m = len(items)
    out: dict[str, dict] = {}
    running, stop = 0.0, False
    for i, (p, k) in enumerate(items, 1):
        thr = alpha / (m - i + 1)
        running = max(running, min(1.0, (m - i + 1) * p))
        reject = (not stop) and p <= thr
        if not reject:
            stop = True
        out[k] = {"p": p, "rank": i, "m": m, "threshold": thr, "p_holm": running, "reject": reject,
                  "executed": pvals[k] is not None}
    return out
