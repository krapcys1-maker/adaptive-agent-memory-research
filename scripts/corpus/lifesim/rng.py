"""Deterministic random streams and platform-independent arithmetic for LifeSim.

What this module provides
-------------------------
* ``Rng``: a 64-bit linear congruential generator (Knuth MMIX constants) whose draw
  semantics are a copy of ``corpus.goalshift.Lcg`` for ``below``, ``u`` (goalshift
  calls it ``uniform``), ``chance``, ``choice``, ``shuffle``, ``sample`` and
  ``weighted``; plus ``ri``, ``normal``, ``poisson``, ``poisson_between``, ``expo``
  and ``weighted_by``.
* ``stream(seed, *labels)``: an independent ``Rng`` per (seed, labels), keyed through
  SHA-256 exactly as ``goalshift.stream`` is, so identical keys give identical
  sequences (pinned by a golden-vector test that also compares with goalshift).
  Adding a stream, or a label, never shifts any other stream.
* A small deterministic math kit (``dln``, ``dlog2``, ``dexp``, ``dpow``, ``dtanh``,
  ``ppnd``, ``zipf_probs``, ``entropy_bits``) built from IEEE basic operations,
  ``sqrt``, ``frexp`` and ``ldexp`` only. ``math.log`` / ``exp`` / ``tanh`` / ``pow``
  / ``cos`` come from the platform C library and may differ in the last bit between
  Windows and Linux, which would change a world digest; these do not.
* ``q(x, nd=6)``: the quantiser applied to every float that enters a stored object.

Stream naming convention (the first label is the stream name)::

    stream(seed, "cast")              people, places, shops, jobs
    stream(seed, "habits")            routine models (breakfast prior, ...)
    stream(seed, "life", event_id)    one stream per situation: delete/swap operators
    stream(seed, "news")              third-party stories
    stream(seed, "character")         stances, goals, turning points
    stream(seed, "host")              situation-first hosting of facts
    stream(seed, "mention")           which lines mention which facts
    stream(seed, "channel", arm)      heartbeat channel per arm
    stream(seed, "query", family)     query sampling per family
    stream(seed, "verb", partition)   verbalisation per partition
    stream(seed, "gate", policy)      gate policies

What this module does NOT do: it never uses ``random``, the clock or ``hash()``; it is
not cryptographic; it does not validate stream names (a typo silently makes a new,
valid stream); labels are joined with ``|`` so a label that itself contains ``|`` can
collide with a longer label list (same as goalshift); ``below(n)`` is only meant for
``n <= 2**31`` because the generator yields 31 usable bits per step.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Sequence

__all__ = [
    "Rng", "stream", "STREAMS", "q", "dln", "dlog2", "dexp", "dpow", "dtanh", "ppnd",
    "zipf_probs", "entropy_bits",
]

STREAMS = ("cast", "habits", "life", "news", "character", "host", "mention", "channel",
           "query", "verb", "gate")

_MASK = (1 << 64) - 1
_MUL = 6364136223846793005
_INC = 1442695040888963407
_TWO31 = float(1 << 31)


# --------------------------------------------------------------------------- the generator


class Rng:
    """A 64-bit LCG. Same draw semantics as ``goalshift.Lcg``; see the module docstring."""

    __slots__ = ("state",)

    MASK = _MASK

    def __init__(self, seed: int) -> None:
        self.state = seed & _MASK
        for _ in range(4):
            self._next()

    def _next(self) -> int:
        self.state = (self.state * _MUL + _INC) & _MASK
        return self.state >> 33  # 31 usable bits

    def clone(self) -> "Rng":
        """An independent copy at the same position (for look-ahead without consuming)."""
        other = Rng(0)
        other.state = self.state
        return other

    # -- uniform draws (one LCG step each) ------------------------------------------

    def u(self) -> float:
        """Uniform float in [0, 1)."""
        return self._next() / _TWO31

    def below(self, n: int) -> int:
        """Uniform integer in [0, n)."""
        if n < 1:
            raise ValueError("below(n) needs n >= 1, got %r" % (n,))
        return (self._next() * n) >> 31

    def ri(self, a: int, b: int) -> int:
        """Uniform integer in [a, b], both ends included."""
        if b < a:
            raise ValueError("ri(a, b) needs a <= b, got %r, %r" % (a, b))
        return a + self.below(b - a + 1)

    def chance(self, p: float) -> bool:
        """True with probability p (p <= 0 never, p >= 1 always)."""
        return self._next() < p * (1 << 31)

    def choice(self, seq: Sequence[Any]) -> Any:
        return seq[self.below(len(seq))]

    # -- permutations -----------------------------------------------------------------

    def shuffle(self, items: list) -> None:
        """In-place Fisher-Yates shuffle (len(items) - 1 steps)."""
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]

    def sample(self, seq: Sequence[Any], k: int) -> list:
        """k distinct elements in random order (a shuffled copy, cut to k)."""
        if k < 0 or k > len(seq):
            raise ValueError("sample(seq, k) needs 0 <= k <= len(seq)")
        pool = list(seq)
        self.shuffle(pool)
        return pool[:k]

    # -- weighted draws -----------------------------------------------------------------

    def weighted(self, probs: Sequence[float]) -> int:
        """Index drawn with probabilities ``probs`` (which should sum to 1).

        Exactly the goalshift rule: the last index absorbs any rounding shortfall."""
        x = self._next() / _TWO31
        acc = 0.0
        for i, p in enumerate(probs):
            acc += p
            if x < acc:
                return i
        return len(probs) - 1

    def weighted_by(self, weights: Sequence[float]) -> int:
        """Index drawn proportionally to non-negative ``weights`` (any positive sum)."""
        total = 0.0
        for w in weights:
            if w < 0:
                raise ValueError("negative weight")
            total += w
        if not total > 0.0:
            raise ValueError("weights must have a positive sum")
        x = (self._next() / _TWO31) * total
        acc = 0.0
        for i, w in enumerate(weights):
            acc += w
            if x < acc:
                return i
        return len(weights) - 1

    # -- continuous and count distributions (one LCG step each) -------------------------

    def normal(self, mu: float = 0.0, sd: float = 1.0) -> float:
        """Normal variate by inverse CDF of one uniform (``ppnd``); bit-reproducible.

        The uniform is (k + 0.5) / 2**31 for the 31-bit draw k, so it is never 0 or 1
        and the largest possible |z| is about 6.2."""
        return mu + sd * ppnd((self._next() + 0.5) / _TWO31)

    def poisson(self, lam: float) -> int:
        """Poisson variate by inversion of one uniform; 0 <= lam <= 100."""
        if lam < 0 or lam > 100:
            raise ValueError("poisson(lam) needs 0 <= lam <= 100")
        x = self._next() / _TWO31
        if lam == 0:
            return 0
        p = dexp(-lam)
        acc = p
        k = 0
        while x >= acc and k < 1000:
            k += 1
            p = p * lam / k
            acc += p
        return k

    def poisson_between(self, lam: float, lo: int, hi: int) -> int:
        """Poisson variate conditioned on lo <= k <= hi (truncation by rejection, e.g.
        'about 6 observations a day, Poisson 3-10'). Uses a variable number of steps."""
        if lo > hi:
            raise ValueError("poisson_between needs lo <= hi")
        k = lo
        for _ in range(64):
            k = self.poisson(lam)
            if lo <= k <= hi:
                return k
        return min(max(k, lo), hi)

    def expo(self, mean: float = 1.0) -> float:
        """Exponential variate with the given mean."""
        return -mean * dln(1.0 - self.u())


def stream(seed: int, *labels: Any) -> Rng:
    """An independent random stream per (seed, labels); same keying as goalshift.stream."""
    key = "|".join([str(seed)] + [str(x) for x in labels]).encode("utf-8")
    return Rng(int.from_bytes(hashlib.sha256(key).digest()[:8], "big"))


# --------------------------------------------------------------------- quantiser


def q(x: float, nd: int = 6) -> float:
    """Round to ``nd`` decimals (default 6) and normalise -0.0 to 0.0.

    Every float stored in a LifeSim object passes through this (the schema dataclasses
    do it on construction), so the last bit of a library result can never reach a
    digest. ``round`` uses correctly rounded decimal conversion, identical on every
    platform."""
    return round(x, nd) + 0.0


# ---------------------------------------------------- deterministic math kit

_LN2 = 0.6931471805599453
_LN2_HI = 6.93147180369123816490e-01  # fdlibm split of ln 2: k * _LN2_HI is exact
_LN2_LO = 1.90821492927058770002e-10
_INV_LN2 = 1.4426950408889634
_SQRT_HALF = 0.7071067811865476
_ODD_RECIP = tuple(1.0 / k for k in range(1, 24, 2))  # 1/1, 1/3, ..., 1/23


def dln(x: float) -> float:
    """Natural logarithm of x > 0 from IEEE basic operations only (error ~1e-16)."""
    if not (x > 0.0) or x == math.inf:
        raise ValueError("dln needs a finite x > 0, got %r" % (x,))
    m, e = math.frexp(x)  # x = m * 2**e exactly, 0.5 <= m < 1
    if m < _SQRT_HALF:
        m *= 2.0
        e -= 1
    z = (m - 1.0) / (m + 1.0)  # |z| <= 0.1716; ln m = 2 atanh z
    w = z * z
    s = 0.0
    for c in reversed(_ODD_RECIP[:11]):  # Horner over 1/21 ... 1/1
        s = s * w + c
    return e * _LN2 + 2.0 * z * s


def dlog2(x: float) -> float:
    """Base-2 logarithm of x > 0 (surprisal in bits is ``-dlog2(p)``)."""
    return dln(x) / _LN2


def _expm1_small(r: float) -> float:
    """exp(r) - 1 for |r| <= 1 by its Taylor series, summed from the small terms."""
    term = r
    total = r
    for n in range(2, 24):
        term = term * r / n
        total += term
    return total


def dexp(x: float) -> float:
    """exp(x) from IEEE basic operations and ldexp (relative error ~1e-15)."""
    if x != x:
        raise ValueError("dexp of nan")
    if x > 709.0:
        raise OverflowError("dexp overflow")
    if x < -745.0:
        return 0.0
    k = math.floor(x * _INV_LN2 + 0.5)
    r = (x - k * _LN2_HI) - k * _LN2_LO  # |r| <= 0.347
    return math.ldexp(1.0 + _expm1_small(r), k)


def dpow(x: float, y: float) -> float:
    """x ** y for x > 0 (Zipf weights use ``dpow(rank, -s)``)."""
    return dexp(y * dln(x))


def dtanh(x: float) -> float:
    """Hyperbolic tangent, accurate near 0 and saturating beyond |x| = 20."""
    ax = abs(x)
    if ax > 20.0:
        return math.copysign(1.0, x)
    if ax <= 0.5:
        e1 = _expm1_small(2.0 * ax)
    else:
        e1 = dexp(2.0 * ax) - 1.0
    t = e1 / (e1 + 2.0)
    return t if x >= 0 else -t


def ppnd(p: float) -> float:
    """Inverse standard normal CDF, 0 < p < 1 (Wichura 1988, algorithm AS241 PPND16).

    The coefficients are those of the published algorithm; the only change is that the
    tail logarithm is ``dln``, so the result is bit-identical on every platform."""
    if not (0.0 < p < 1.0):
        raise ValueError("ppnd needs 0 < p < 1, got %r" % (p,))
    qq = p - 0.5
    if abs(qq) <= 0.425:
        r = 0.180625 - qq * qq
        num = (((((((2.50908_09287_30122_6727e+3 * r +
                     3.34305_75583_58812_8105e+4) * r +
                     6.72657_70927_00870_0853e+4) * r +
                     4.59219_53931_54987_1457e+4) * r +
                     1.37316_93765_50946_1125e+4) * r +
                     1.97159_09503_06551_4427e+3) * r +
                     1.33141_66789_17843_7745e+2) * r +
                     3.38713_28727_96366_6080e+0) * qq
        den = (((((((5.22649_52788_52854_5610e+3 * r +
                     2.87290_85735_72194_2674e+4) * r +
                     3.93078_95800_09271_0610e+4) * r +
                     2.12137_94301_58659_5867e+4) * r +
                     5.39419_60214_24751_1077e+3) * r +
                     6.87187_00749_20579_0830e+2) * r +
                     4.23133_30701_60091_1252e+1) * r +
                     1.0)
        return num / den
    r = p if qq <= 0.0 else 1.0 - p
    r = math.sqrt(-dln(r))
    if r <= 5.0:
        r = r - 1.6
        num = (((((((7.74545_01427_83414_07640e-4 * r +
                     2.27238_44989_26918_45833e-2) * r +
                     2.41780_72517_74506_11770e-1) * r +
                     1.27045_82524_52368_38258e+0) * r +
                     3.64784_83247_63204_60504e+0) * r +
                     5.76949_72214_60691_40550e+0) * r +
                     4.63033_78461_56545_29590e+0) * r +
                     1.42343_71107_49683_57734e+0)
        den = (((((((1.05075_00716_44416_84324e-9 * r +
                     5.47593_80849_95344_94600e-4) * r +
                     1.51986_66563_61645_71966e-2) * r +
                     1.48103_97642_74800_74590e-1) * r +
                     6.89767_33498_51000_04550e-1) * r +
                     1.67638_48301_83803_84940e+0) * r +
                     2.05319_16266_37758_82187e+0) * r +
                     1.0)
    else:
        r = r - 5.0
        num = (((((((2.01033_43992_92288_13265e-7 * r +
                     2.71155_55687_43487_57815e-5) * r +
                     1.24266_09473_88078_43860e-3) * r +
                     2.65321_89526_57612_30930e-2) * r +
                     2.96560_57182_85048_91230e-1) * r +
                     1.78482_65399_17291_33580e+0) * r +
                     5.46378_49111_64114_36990e+0) * r +
                     6.65790_46435_01103_77720e+0)
        den = (((((((2.04426_31033_89939_78564e-15 * r +
                     1.42151_17583_16445_88870e-7) * r +
                     1.84631_83175_10054_68180e-5) * r +
                     7.86869_13114_56132_59100e-4) * r +
                     1.48753_61290_85061_48525e-2) * r +
                     1.36929_88092_27358_05310e-1) * r +
                     5.99832_20655_58879_37690e-1) * r +
                     1.0)
    x = num / den
    return -x if qq < 0.0 else x


def zipf_probs(n: int, s: float) -> tuple[float, ...]:
    """Zipf probabilities 1/rank**s for ranks 1..n, normalised to sum 1 (s in 0.5-0.7)."""
    if n < 1:
        raise ValueError("zipf_probs needs n >= 1")
    w = [dpow(float(i + 1), -s) for i in range(n)]
    total = 0.0
    for x in w:
        total += x
    return tuple(x / total for x in w)


def entropy_bits(probs: Sequence[float]) -> float:
    """Shannon entropy in bits of a probability vector (zeros contribute nothing)."""
    h = 0.0
    for p in probs:
        if p > 0.0:
            h -= p * dlog2(p)
    return h
