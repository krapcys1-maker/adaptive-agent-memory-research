"""Tests for corpus.lifesim.rng (LifeSim D1-A). Standard library and pytest only.

Golden vectors were computed on Python 3.11.13 and 3.12.10 (identical output).
"""

from __future__ import annotations

import ast
import math
import statistics
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus import goalshift as gs  # noqa: E402
from corpus.lifesim import rng as R  # noqa: E402

LIFESIM_DIR = ROOT / "scripts" / "corpus" / "lifesim"
ND = statistics.NormalDist()


# ------------------------------------------------------------------ golden vectors


def test_goalshift_golden_vectors_are_reproduced():
    r = R.Rng(1)
    assert [r.below(1000) for _ in range(6)] == [795, 500, 553, 65, 839, 198]
    r = R.stream(7, "a", "b")
    assert [r.below(1000) for _ in range(6)] == [944, 804, 43, 954, 629, 434]


def test_golden_vector_of_every_operation():
    r = R.stream(42, "life", "s00001")
    assert [x.hex() for x in (r.u(), r.u())] == ["0x1.cbeb39f800000p-1", "0x1.2bade63000000p-1"]
    assert [r.ri(5, 9) for _ in range(6)] == [8, 8, 7, 9, 6, 7]
    assert [r.chance(0.3) for _ in range(6)] == [False, False, True, False, False, False]
    assert [r.choice("abcdefgh") for _ in range(4)] == ["g", "d", "b", "a"]
    items = list(range(8))
    r.shuffle(items)
    assert items == [6, 7, 5, 1, 2, 4, 0, 3]
    assert r.sample(range(20), 5) == [4, 7, 2, 9, 17]
    assert [r.weighted([0.2, 0.3, 0.5]) for _ in range(8)] == [2, 0, 2, 0, 1, 1, 0, 2]
    assert [r.weighted_by([2, 0, 3, 5]) for _ in range(8)] == [2, 0, 3, 3, 3, 3, 3, 2]
    assert [r.normal().hex() for _ in range(3)] == [
        "-0x1.ab74f0415de09p-4", "-0x1.08db86070d3e0p-2", "-0x1.8b25bce63f0f1p+0"]
    assert [r.normal(10.0, 2.0).hex() for _ in range(2)] == [
        "0x1.ef942108dbacfp+2", "0x1.6b3b931cc8e3bp+3"]
    assert [r.poisson(6.0) for _ in range(8)] == [6, 10, 7, 5, 9, 7, 7, 7]
    assert [r.expo(2.0).hex() for _ in range(2)] == ["0x1.f9a0b53001dcap-1", "0x1.aa2425b7fcb70p+0"]
    assert r.state == 10421590150238493947


def test_golden_vector_of_the_math_kit_is_bit_exact():
    assert R.ppnd(0.975).hex() == "0x1.f5c0331eeff82p+0"
    assert R.ppnd(1e-5).hex() == "-0x1.10f3f8843a3dap+2"
    assert R.ppnd(0.3).hex() == "-0x1.0c7e39582c5fap-1"
    assert R.dln(10.0).hex() == "0x1.26bb1bbb55515p+1"
    assert R.dexp(1.5).hex() == "0x1.1ed3fe64fc541p+2"
    assert R.dtanh(0.7).hex() == "0x1.356fb17af2e91p-1"
    assert R.dpow(7.0, -0.6).hex() == "0x1.3e98ba93f1a3ep-2"
    z = R.zipf_probs(50, 0.6)
    assert [x.hex() for x in z[:3]] == [
        "0x1.979574cfa2052p-4", "0x1.0ce7b0418d36ap-4", "0x1.a5abe27ef48f5p-5"]
    assert R.entropy_bits(z).hex() == "0x1.552cce7364d49p+2"


# ------------------------------------------------------- equality with goalshift


KEYS = [(0,), (1, "a"), (7, "a", "b"), (123456789, "life", "s00042"), (2**40 + 5, "cast"),
        (-3, "x", 9), (5000, "channel", "SHUF_TYPE"), (999, "query", "EP1"),
        (42, "verb", "dev"), (0, "gate", "GH")]


@pytest.mark.parametrize("key", KEYS)
def test_stream_equals_goalshift_stream_for_identical_keys(key):
    mine, theirs = R.stream(*key), gs.stream(*key)
    assert mine.state == theirs.state
    for n in (2, 3, 10, 1000, 65537, 2**31):
        assert mine.below(n) == theirs.below(n)
    assert mine.u() == theirs.uniform()
    assert [mine.chance(p) for p in (0.0, 0.1, 0.5, 0.9, 1.0)] == \
        [theirs.chance(p) for p in (0.0, 0.1, 0.5, 0.9, 1.0)]
    seq = list("abcdefghij")
    assert mine.choice(seq) == theirs.choice(seq)
    a, b = list(range(30)), list(range(30))
    mine.shuffle(a)
    theirs.shuffle(b)
    assert a == b
    assert mine.sample(range(40), 7) == theirs.sample(range(40), 7)
    probs = [0.05, 0.15, 0.3, 0.5]
    assert [mine.weighted(probs) for _ in range(20)] == [theirs.weighted(probs) for _ in range(20)]
    assert mine.state == theirs.state  # no hidden extra draws


@pytest.mark.parametrize("seed", [0, 1, 2**63, 2**64 - 1, 2**64, 2**70 + 3, -1, -12345])
def test_constructor_equals_goalshift_lcg_for_odd_seeds(seed):
    mine, theirs = R.Rng(seed), gs.Lcg(seed)
    assert mine.state == theirs.state
    assert [mine.below(10**6) for _ in range(5)] == [theirs.below(10**6) for _ in range(5)]


# ----------------------------------------------------------------- stream independence


def test_adding_a_label_or_a_stream_shifts_no_other_stream():
    base = [R.stream(5, "life", "s1").below(10**6) for _ in range(1)]
    first = R.stream(5, "life", "s1")
    seq_alone = [first.below(10**6) for _ in range(20)]
    # create and consume many unrelated streams first
    for label in ("s2", "s3", "s10"):
        other = R.stream(5, "life", label)
        [other.u() for _ in range(50)]
    R.stream(5, "life").u()
    R.stream(5, "cast").u()
    again = R.stream(5, "life", "s1")
    assert [again.below(10**6) for _ in range(20)] == seq_alone
    assert base[0] == seq_alone[0]


def test_streams_with_different_keys_differ_and_label_order_matters():
    firsts = {tuple(R.stream(*k).below(10**9) for _ in range(3)) for k in (
        (5, "a"), (5, "b"), (5, "a", "b"), (5, "b", "a"), (6, "a"), (5, "a", "b", "c"), (5,))}
    assert len(firsts) == 7


def test_label_types_are_stringified_and_pipe_collides_as_in_goalshift():
    assert R.stream(5, "life", 1).state == R.stream(5, "life", "1").state
    assert R.stream(5, "a|b").state == R.stream(5, "a", "b").state  # documented caveat


def test_per_event_streams_make_deletion_byte_clean():
    def draw(event_ids):
        return {e: [R.stream(11, "life", e).ri(0, 999) for _ in range(1)] +
                [R.stream(11, "life", e).normal()] for e in event_ids}
    full = draw(["s1", "s2", "s3", "s4"])
    without_s3 = draw(["s1", "s2", "s4"])
    assert {k: v for k, v in full.items() if k != "s3"} == without_s3


def test_clone_is_an_independent_copy_at_the_same_position():
    r = R.stream(3, "x")
    r.u()
    c = r.clone()
    assert [c.below(100) for _ in range(5)] == [r.below(100) for _ in range(5)]
    c.u()
    assert c.state != r.state


# --------------------------------------------------------- distribution sanity


def test_below_is_uniform_and_in_range():
    r = R.stream(1, "below")
    counts = [0] * 7
    for _ in range(70000):
        counts[r.below(7)] += 1
    expected = 10000.0
    chi2 = sum((c - expected) ** 2 / expected for c in counts)
    assert chi2 < 22.5  # chi-square, 6 degrees of freedom, p = 0.001
    assert all(R.stream(2, "b").below(1) == 0 for _ in range(3))
    with pytest.raises(ValueError):
        R.stream(2, "b").below(0)


def test_ri_is_inclusive_on_both_ends():
    r = R.stream(1, "ri")
    seen = {r.ri(3, 6) for _ in range(2000)}
    assert seen == {3, 4, 5, 6}
    assert {r.ri(-2, 0) for _ in range(500)} == {-2, -1, 0}
    assert r.ri(5, 5) == 5
    with pytest.raises(ValueError):
        r.ri(6, 3)


def test_chance_edges_and_rate():
    r = R.stream(1, "chance")
    assert not any(r.chance(0.0) for _ in range(1000))
    assert not any(r.chance(-0.5) for _ in range(1000))
    assert all(r.chance(1.0) for _ in range(1000))
    assert all(r.chance(7.0) for _ in range(1000))
    rate = sum(r.chance(0.3) for _ in range(100000)) / 100000
    assert abs(rate - 0.3) < 0.01


def test_shuffle_is_a_uniform_permutation():
    r = R.stream(1, "shuffle")
    first_pos = [0] * 6
    perms = set()
    for _ in range(60000):
        items = list(range(6))
        r.shuffle(items)
        assert sorted(items) == list(range(6))
        first_pos[items[0]] += 1
        perms.add(tuple(items))
    assert len(perms) == 720
    assert all(abs(c / 60000 - 1 / 6) < 0.01 for c in first_pos)
    one, none = [9], []
    r.shuffle(one)
    r.shuffle(none)
    assert one == [9] and none == []


def test_sample_gives_distinct_members_and_leaves_input_alone():
    r = R.stream(1, "sample")
    pool = list(range(10))
    for k in (0, 1, 5, 10):
        s = r.sample(pool, k)
        assert len(s) == k and len(set(s)) == k and set(s) <= set(pool)
    assert pool == list(range(10))
    with pytest.raises(ValueError):
        r.sample(pool, 11)
    with pytest.raises(ValueError):
        r.sample(pool, -1)


def test_weighted_and_weighted_by_follow_their_weights():
    r = R.stream(1, "w")
    counts = [0, 0, 0, 0]
    for _ in range(80000):
        counts[r.weighted([0.1, 0.0, 0.3, 0.6])] += 1
    assert counts[1] == 0
    for c, p in zip(counts, (0.1, 0.0, 0.3, 0.6)):
        assert abs(c / 80000 - p) < 0.01
    counts = [0, 0, 0, 0]
    for _ in range(80000):
        counts[r.weighted_by([1.0, 0.0, 3.0, 6.0])] += 1  # sums to 10, not 1
    assert counts[1] == 0
    for c, p in zip(counts, (0.1, 0.0, 0.3, 0.6)):
        assert abs(c / 80000 - p) < 0.01
    # the last index absorbs a shortfall (goalshift rule), never IndexError
    assert {r.weighted([0.1, 0.1]) for _ in range(500)} == {0, 1}
    with pytest.raises(ValueError):
        r.weighted_by([0.0, 0.0])
    with pytest.raises(ValueError):
        r.weighted_by([1.0, -1.0])


def test_normal_moments_quantiles_and_range():
    r = R.stream(3, "n")
    xs = [r.normal() for _ in range(200000)]
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / len(xs)
    assert abs(mean) < 0.01 and abs(var - 1.0) < 0.02
    within1 = sum(abs(x) < 1 for x in xs) / len(xs)
    within2 = sum(abs(x) < 2 for x in xs) / len(xs)
    assert abs(within1 - 0.682689) < 0.005 and abs(within2 - 0.954500) < 0.004
    assert abs(sum(x < 0 for x in xs) / len(xs) - 0.5) < 0.005
    assert max(abs(x) for x in xs) < 6.3
    ys = [r.normal(10.0, 2.0) for _ in range(100000)]
    my = sum(ys) / len(ys)
    sy = math.sqrt(sum((y - my) ** 2 for y in ys) / len(ys))
    assert abs(my - 10.0) < 0.03 and abs(sy - 2.0) < 0.03


class Scripted(R.Rng):
    """An Rng whose raw 31-bit draws are scripted, to pin exact boundary behaviour."""

    def __init__(self, *draws):
        self.draws = [0, 0, 0, 0]  # the constructor warms the generator up with four draws
        super().__init__(0)
        self.draws = list(draws)

    def _next(self):
        return self.draws.pop(0)


def test_exact_boundaries_with_scripted_draws():
    top = (1 << 31) - 1
    assert Scripted(0).u() == 0.0 and Scripted(top).u() == top / 2.0 ** 31 < 1.0
    assert Scripted(0).below(7) == 0 and Scripted(top).below(7) == 6
    assert Scripted(0).ri(3, 6) == 3 and Scripted(top).ri(3, 6) == 6
    # chance is strictly "draw < p * 2**31"
    assert Scripted(644245094).chance(0.3) and not Scripted(644245095).chance(0.3)
    assert Scripted((1 << 30) - 1).chance(0.5) and not Scripted(1 << 30).chance(0.5)
    # weighted: a draw exactly on a cumulative boundary belongs to the next bucket
    assert Scripted((1 << 30) - 1).weighted([0.5, 0.5]) == 0 and Scripted(1 << 30).weighted([0.5, 0.5]) == 1
    assert Scripted(top).weighted([0.5, 0.25]) == 1  # a shortfall goes to the last index
    assert Scripted((1 << 30) - 1).weighted_by([1, 1]) == 0 and Scripted(1 << 30).weighted_by([1, 1]) == 1
    # normal: the extreme uniforms are 0.5 / 2**31 and its mirror image
    lo, hi = Scripted(0).normal(), Scripted(top).normal()
    assert lo == -hi and -6.3 < lo < -6.1
    assert 0.0 < Scripted(1 << 30).normal() < 1e-8
    # poisson: the draw is compared with the cumulative pmf
    assert Scripted(0).poisson(6.0) == 0 and 20 <= Scripted(top).poisson(6.0) <= 40
    # shuffle with all-zero draws swaps every element with the first one (Fisher-Yates)
    items = [0, 1, 2, 3]
    Scripted(0, 0, 0).shuffle(items)
    assert items == [1, 2, 3, 0]


def test_each_draw_consumes_exactly_one_step():
    for call in (lambda r: r.normal(), lambda r: r.poisson(4.0), lambda r: r.expo(),
                 lambda r: r.u(), lambda r: r.below(9), lambda r: r.chance(0.5),
                 lambda r: r.weighted_by([1, 2]), lambda r: r.poisson(0.0)):
        a, b = R.stream(8, "step"), R.stream(8, "step")
        for _ in range(5):
            call(a)
            b.u()
        assert a.state == b.state


def test_poisson_matches_its_pmf():
    r = R.stream(3, "p")
    lam, n = 6.0, 200000
    counts = {}
    for _ in range(n):
        k = r.poisson(lam)
        counts[k] = counts.get(k, 0) + 1
    mean = sum(k * c for k, c in counts.items()) / n
    var = sum((k - mean) ** 2 * c for k, c in counts.items()) / n
    assert abs(mean - lam) < 0.03 and abs(var - lam) < 0.1
    for k in range(0, 16):
        pmf = math.exp(-lam) * lam ** k / math.factorial(k)
        assert abs(counts.get(k, 0) / n - pmf) < 0.004
    assert R.stream(1, "p").poisson(0.0) == 0
    for bad in (-1.0, 101.0):
        with pytest.raises(ValueError):
            R.stream(1, "p").poisson(bad)
    big = [R.stream(s, "p").poisson(100.0) for s in range(50)]
    assert 60 < min(big) and max(big) < 140


def test_poisson_between_is_a_truncated_poisson():
    r = R.stream(4, "pb")
    lam, lo, hi, n = 6.0, 3, 10, 100000
    xs = [r.poisson_between(lam, lo, hi) for _ in range(n)]
    assert min(xs) == lo and max(xs) == hi
    pmf = {k: math.exp(-lam) * lam ** k / math.factorial(k) for k in range(lo, hi + 1)}
    z = sum(pmf.values())
    for k in range(lo, hi + 1):
        assert abs(xs.count(k) / n - pmf[k] / z) < 0.006, k
    assert R.stream(1, "pb").poisson_between(6.0, 5, 5) == 5
    assert 100 == R.stream(1, "pb").poisson_between(0.5, 100, 100)  # fallback clips
    with pytest.raises(ValueError):
        R.stream(1, "pb").poisson_between(6.0, 4, 3)


def test_expo_mean():
    r = R.stream(3, "e")
    xs = [r.expo(2.5) for _ in range(100000)]
    assert min(xs) >= 0.0 and abs(sum(xs) / len(xs) - 2.5) < 0.05


# ------------------------------------------------------------- the math kit


def test_ppnd_matches_the_standard_library_inverse_cdf():
    ps = [10.0 ** e for e in range(-300, -1, 7)] + [i / 1000 for i in range(1, 1000)]
    ps += [1 - 10.0 ** (-e) for e in range(2, 15)]
    for p in ps:
        assert abs(R.ppnd(p) - ND.inv_cdf(p)) < 1e-9 * max(1.0, abs(ND.inv_cdf(p))), p
    for p in (0.001, 0.02, 0.1, 0.3, 0.45):
        assert abs(R.ppnd(1 - p) + R.ppnd(p)) < 1e-12
    assert R.ppnd(0.5) == 0.0
    assert abs(R.ppnd(0.975) - 1.959963984540054) < 1e-12
    for bad in (0.0, 1.0, -0.1, 1.5, float("nan")):
        with pytest.raises(ValueError):
            R.ppnd(bad)


def test_deterministic_math_agrees_with_libm_to_rounding_error():
    for e in range(-300, 301, 3):
        x = 10.0 ** e * 1.2345
        assert abs(R.dln(x) - math.log(x)) <= 4e-15 * max(1.0, abs(math.log(x)))
    for i in range(-700, 701, 7):
        x = i + 0.37
        assert abs(R.dexp(x) / math.exp(x) - 1.0) < 3e-15
    for i in range(-2000, 2001, 13):
        x = i / 100.0
        assert abs(R.dtanh(x) - math.tanh(x)) < 3e-16 + 1e-15 * abs(math.tanh(x))
    for x in (1e-9, 1e-5, 0.2, 0.5, 0.5000001, 3.0, 19.9):
        assert abs(R.dtanh(x) / math.tanh(x) - 1.0) < 3e-15
    assert R.dtanh(25.0) == 1.0 and R.dtanh(-25.0) == -1.0 and R.dtanh(0.0) == 0.0
    for a, b in ((2.0, 10.0), (50.0, -0.6), (0.5, 0.7), (1234.5, 0.5), (7.0, 0.0)):
        assert abs(R.dpow(a, b) / a ** b - 1.0) < 3e-15
    assert R.dln(1.0) == 0.0 and R.dexp(0.0) == 1.0
    assert abs(R.dlog2(8.0) - 3.0) < 1e-15 and abs(R.dlog2(0.25) + 2.0) < 1e-15
    for bad in (0.0, -1.0, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            R.dln(bad)
    with pytest.raises(OverflowError):
        R.dexp(710.0)
    assert R.dexp(-800.0) == 0.0


def test_zipf_prior_is_flat_enough_for_the_habit_slot_entropy_rule():
    for n in range(40, 61, 5):
        for s in (0.5, 0.6, 0.7):
            p = R.zipf_probs(n, s)
            assert abs(sum(p) - 1.0) < 1e-12
            assert all(p[i] > p[i + 1] for i in range(n - 1))
            assert R.entropy_bits(p) >= 4.5, (n, s)  # spec: prior entropy >= 4.5 bits
            assert sum(p[:3]) < 0.30  # the habit top-3 never dominates
    assert R.zipf_probs(1, 0.6) == (1.0,)
    flat = R.zipf_probs(8, 0.0)
    assert all(abs(x - 0.125) < 1e-15 for x in flat)
    assert abs(R.entropy_bits(flat) - 3.0) < 1e-12
    assert R.entropy_bits([1.0, 0.0]) == 0.0


def test_quantiser():
    assert R.q(0.1234567) == 0.123457
    assert R.q(0.5000004) == 0.5
    assert math.copysign(1.0, R.q(-0.0)) == 1.0
    assert math.copysign(1.0, R.q(-1e-9)) == 1.0
    assert R.q(R.q(0.987654321)) == R.q(0.987654321)
    assert R.q(1.23456789, 3) == 1.235


# ------------------------------------------------------------- source lint


FORBIDDEN_IMPORTS = {"random", "time", "secrets", "uuid", "numpy", "scipy", "pandas",
                     "socket", "requests", "urllib", "http", "subprocess", "openai",
                     "anthropic"}
FORBIDDEN_ATTRS = {"now", "today", "utcnow", "perf_counter", "monotonic", "urandom",
                   "getrandbits", "fromtimestamp"}


GENERATOR_FILES = sorted(LIFESIM_DIR.glob("*.py"))  # every module of the package, whoever owns it


def test_the_package_has_the_foundation_modules():
    names = {p.stem for p in GENERATOR_FILES}
    assert {"__init__", "rng", "schema", "vocab"} <= names


@pytest.mark.parametrize("path", GENERATOR_FILES, ids=lambda p: p.name)
def test_generator_modules_are_stdlib_deterministic_and_python311(path):
    """The project rules: generation and scoring are standard library only (numpy and scipy
    belong to statistics and gate code in the sibling package), never random, the clock or
    hash(), and parse under the Python 3.11 grammar."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, feature_version=(3, 11))
    assert ast.get_docstring(tree), "%s needs a docstring" % path.name
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {a.name.split(".")[0] for a in node.names}
            assert not roots & FORBIDDEN_IMPORTS, (path.name, roots)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in FORBIDDEN_IMPORTS, (path.name, node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"hash", "eval", "exec", "input"}, path.name
        elif isinstance(node, ast.Attribute):
            assert node.attr not in FORBIDDEN_ATTRS, (path.name, node.attr)


@pytest.mark.parametrize("path", GENERATOR_FILES, ids=lambda p: p.name)
def test_docstring_says_what_the_module_does_not_do(path):
    doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))).lower()
    assert "does not" in doc or "do not" in doc or "not do" in doc, path.name


def test_stream_names_of_the_specification_are_listed_and_documented():
    for name in ("cast", "habits", "life", "news", "character", "host", "mention",
                 "channel", "query", "verb", "gate"):
        assert name in R.STREAMS
        assert 'stream(seed, "%s"' % name in R.__doc__
