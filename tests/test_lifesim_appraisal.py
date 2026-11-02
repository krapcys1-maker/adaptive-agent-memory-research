"""Tests for LifeSim appraisal (corpus.lifesim.appraisal): mappings, caps, monotonicity,
surprisal, mood and the small statistics helpers. Standard library and pytest only."""

from __future__ import annotations

import dataclasses
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import appraisal as ap  # noqa: E402
from corpus.lifesim.rng import stream  # noqa: E402
from corpus.lifesim.schema import Feats, Prior, TierCfg  # noqa: E402

CFG = TierCfg()
QUIET = dataclasses.replace(CFG, m1_eps_sd=0.0, m3_noise_sd=0.0)  # deterministic mappings
HAND = Feats(goal_rel=0.6, surprisal_bits=4.0, stakes=0.8, bond=0.5, control=0.5, norm=-0.4,
             conduciveness=-0.5)


def _rng():
    return stream(3, "appraisal-test")


def _random_feats(rng):
    return Feats(goal_rel=rng.u(), surprisal_bits=8.0 * rng.u(), stakes=rng.u(), bond=rng.u(),
                 control=rng.u(), norm=2.0 * rng.u() - 1.0, conduciveness=2.0 * rng.u() - 1.0)


# ------------------------------------------------------------------ hand-computed values


def test_m1_hand_value():
    # 0.30*0.6 + 0.25*0.5 + 0.25*0.8 + 0.15*0.5*0.6 + 0.05*(1-0.5) = 0.575, below the cap 0.74
    a, v = ap.appraise(HAND, "M1", _rng(), QUIET)
    assert a == 0.575
    assert v == pytest.approx(math.tanh(1.5 * -0.5 + 0.3 * -0.4), abs=1e-6)


def test_m2_hand_value_is_noisy_or_of_the_five_terms():
    # 1 - (1-.5*.5)(1-.6*.6)(1-.5*.3)(1-.4*.4)(1-.6*.48)
    expected = 1.0 - 0.75 * 0.64 * 0.85 * 0.84 * 0.712
    a, _ = ap.appraise(HAND, "M2", _rng(), QUIET)
    assert a == pytest.approx(expected, abs=1e-6)
    assert abs(a - 0.755983) < 1e-6


def test_m3_is_prediction_error_only():
    a, _ = ap.appraise(HAND, "M3", _rng(), QUIET)
    assert a == pytest.approx(0.5 * (0.4 + 0.6 * 0.5), abs=1e-9)  # n * (0.4 + 0.6 |c|)
    # goals, stakes, bond and coping potential do not enter
    other = dataclasses.replace(HAND, goal_rel=0.0, stakes=0.0, bond=1.0, control=0.0, norm=0.9)
    assert ap.appraise(other, "M3", _rng(), QUIET)[0] == a


def test_valence_formula_signs_and_bounds():
    rng = _rng()
    for _ in range(300):
        f = _random_feats(rng)
        _, v = ap.appraise(f, "M1", rng, CFG)
        assert -1.0 <= v <= 1.0
        assert v == ap.valence(f, CFG)
        assert v == pytest.approx(math.tanh(1.5 * f.conduciveness + 0.3 * f.norm), abs=2e-6)
    pos = Feats(conduciveness=0.8)
    neg = Feats(conduciveness=-0.8)
    assert ap.valence(pos) > 0.8 and ap.valence(neg) < -0.8 and ap.valence(Feats()) == 0.0


def test_unknown_mapping_is_rejected():
    with pytest.raises(ValueError):
        ap.appraise(HAND, "M9", _rng(), CFG)


# --------------------------------------------------------------------------- properties


def test_one_normal_draw_is_consumed_whatever_the_mapping():
    for mapping in ("M1", "M2", "M3"):
        r1, r2 = stream(5, "x"), stream(5, "x")
        ap.appraise(HAND, mapping, r1, CFG)
        r2.normal()
        assert r1.state == r2.state, mapping


def test_m1_is_capped_by_goal_relevance_and_novelty_alone_stays_moderate():
    rng = _rng()
    for _ in range(4000):
        f = _random_feats(rng)
        a, _ = ap.appraise(f, "M1", rng, CFG)
        assert 0.0 <= a <= CFG.m1_cap_base + CFG.m1_cap_slope * f.goal_rel + 1e-6
    novelty = Feats(goal_rel=0.0, surprisal_bits=8.0, stakes=0.0)
    for _ in range(200):
        assert ap.appraise(novelty, "M1", rng, CFG)[0] <= 0.35 + 1e-9  # moderate, never high
    relevant = Feats(goal_rel=1.0, surprisal_bits=8.0, stakes=1.0, bond=1.0, control=0.0, conduciveness=-1.0)
    assert ap.appraise(relevant, "M1", rng, QUIET)[0] == 1.0


def _monotone(mapping, field, increasing):
    rng = _rng()
    steps = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    for _ in range(300):
        f = _random_feats(rng)
        series = []
        for x in steps:
            val = x * 8.0 if field == "surprisal_bits" else x
            g = dataclasses.replace(f, **{field: val})
            series.append(ap.appraise(g, mapping, _rng(), QUIET)[0])
        pairs = list(zip(series, series[1:]))
        assert all((b >= a - 1e-9) if increasing else (b <= a + 1e-9) for a, b in pairs), (mapping, field, series)


@pytest.mark.parametrize("mapping", ["M1", "M2"])
@pytest.mark.parametrize("field", ["goal_rel", "stakes", "surprisal_bits"])
def test_arousal_is_monotone_in_relevance_stakes_and_surprise(mapping, field):
    _monotone(mapping, field, True)


@pytest.mark.parametrize("mapping", ["M1", "M2"])
def test_arousal_does_not_rise_with_coping_potential(mapping):
    _monotone(mapping, "control", False)


def test_m1_and_m2_actually_respond_to_each_input():
    base = Feats(goal_rel=0.3, surprisal_bits=2.0, stakes=0.3, bond=0.3, control=0.5, norm=0.1, conduciveness=-0.2)
    for mapping in ("M1", "M2"):
        a0 = ap.appraise(base, mapping, _rng(), QUIET)[0]
        for field, big in (("goal_rel", 0.9), ("stakes", 0.9), ("surprisal_bits", 7.0)):
            assert ap.appraise(dataclasses.replace(base, **{field: big}), mapping, _rng(), QUIET)[0] > a0 + 0.05


def test_noise_is_the_only_randomness_and_has_the_configured_sd():
    f = Feats(goal_rel=0.5, surprisal_bits=3.0, stakes=0.3)
    rng = stream(9, "noise")
    xs = [ap.appraise(f, "M1", rng, CFG)[0] for _ in range(6000)]
    mean = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / len(xs))
    assert 0.04 < sd < 0.06  # eps ~ N(0, 0.05^2), nowhere near a clip at these features
    clean = {ap.appraise(f, "M2", stream(i, "n"), CFG)[0] for i in range(20)}
    assert len(clean) == 1  # M2 has no noise


# --------------------------------------------------------------------- surprisal and mood


def test_surprisal_bits():
    prior = Prior(slot="x", values=("a", "b", "c"), probs=(0.5, 0.25, 0.25))
    assert ap.surprisal_bits(prior, "a") == 1.0
    assert ap.surprisal_bits(prior, "b") == 2.0
    assert ap.surprisal_bits(prior, "zzz") == 20.0
    assert ap.surprisal_bits(prior, "zzz", max_bits=9.0) == 9.0
    certain = Prior(slot="y", values=("a",), probs=(1.0,))
    assert ap.surprisal_bits(certain, "a") == 0.0 and str(ap.surprisal_bits(certain, "a")) == "0.0"
    third = Prior(slot="z", values=("a", "b", "c"), probs=(1 / 3, 1 / 3, 1 / 3))
    assert ap.surprisal_bits(third, "b") == pytest.approx(math.log2(3), abs=1e-6)


def test_surprisal_feeds_the_surprise_scale():
    prior = Prior(slot="x", values=tuple("abcdefgh"), probs=(0.125,) * 8)  # 3 bits each
    f = Feats(surprisal_bits=ap.surprisal_bits(prior, "c"))
    assert f.surprise(8.0) == pytest.approx(3 / 8)


def test_mood_step():
    assert ap.mood_step(0.5, [(0.8, 0.5)], CFG) == pytest.approx(0.9 * 0.5 + 0.1 * 0.4)
    assert ap.mood_step(0.5, [], CFG) == pytest.approx(0.97 * 0.5)
    assert ap.mood_step(0.0, [(0.5, 1.0), (0.1, -1.0)], CFG) == pytest.approx(0.1 * (0.5 - 0.1) / 2)
    assert ap.mood_step(-0.6, [(0.0, 1.0)], CFG) == pytest.approx(-0.54)  # zero arousal moves nothing but decay


def test_mood_stays_bounded_and_decays_when_quiet():
    rng = _rng()
    m = 0.0
    for _ in range(2000):
        day = [(rng.u(), 2 * rng.u() - 1) for _ in range(rng.below(4))]
        m = ap.mood_step(m, day, CFG)
        assert -1.0 <= m <= 1.0
    quiet = 0.8
    for _ in range(100):
        quiet = ap.mood_step(quiet, [], CFG)
    assert 0.0 < quiet < 0.05  # 0.8 * 0.97 ** 100


# ------------------------------------------------------------------------ small statistics


def test_pearson_ranks_spearman():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert ap.pearson(xs, [2 * x + 1 for x in xs]) == pytest.approx(1.0)
    assert ap.pearson(xs, [-x for x in xs]) == pytest.approx(-1.0)
    assert ap.pearson(xs, [3.0] * 5) == 0.0
    assert ap.pearson([1.0], [2.0]) == 0.0
    assert ap.pearson([1, 2, 3, 4], [1, 3, 2, 4]) == pytest.approx(0.8)
    assert ap.ranks([10.0, 20.0, 20.0, 30.0]) == [1.0, 2.5, 2.5, 4.0]
    assert ap.ranks([3.0, 1.0, 2.0]) == [3.0, 1.0, 2.0]
    assert ap.spearman(xs, [x ** 3 for x in xs]) == pytest.approx(1.0)  # monotone, not linear
    assert ap.pearson(xs, [x ** 3 for x in xs]) < 0.99
    with pytest.raises(ValueError):
        ap.pearson([1, 2], [1])


def test_summary():
    s = ap.summary([0.1, 0.2, 0.3, 0.8])
    assert s["n"] == 4 and s["mean"] == pytest.approx(0.35)
    assert s["below_03"] == 0.5 and s["at_least_07"] == 0.25
    assert ap.summary([])["n"] == 0
