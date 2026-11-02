"""Tests for LifeSim channel H (corpus.lifesim.channel): the reliability solver and every
control arm keep their declared invariant and break the dependence they should break.
Standard library and pytest only."""

from __future__ import annotations

import dataclasses
import functools
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import channel as ch  # noqa: E402
from corpus.lifesim.appraisal import pearson, ranks, spearman  # noqa: E402
from corpus.lifesim.schema import (CHANNEL_ARMS, Card, Entity, Mention, ObsSpec, Situation,  # noqa: E402
                                   TierCfg, World)
from corpus.lifesim.world import build_world  # noqa: E402

L1 = TierCfg.for_tier("L1")


@functools.lru_cache(maxsize=None)
def world(seed: int = 0, rehearsal: str = "off") -> World:
    return build_world(seed, dataclasses.replace(L1, rehearsal=rehearsal))


def tiny_world(arousals, frames=None):
    """A hand-built world: one routine situation per line, A given."""
    sits = tuple(Situation(sid="s%05d" % (i + 1), day=i // 4, minute=480 + 10 * (i % 4), scene="routine", A=a)
                 for i, a in enumerate(arousals))
    specs = tuple(ObsSpec(oid="o%05d" % (i + 1), t_obs=s.t + 5, channel="log", sid=s.sid,
                          frame=(frames[i] if frames else ""))
                  for i, s in enumerate(sits))
    return World(seed=1, cfg=TierCfg.for_tier("L0"), entities=(Entity(eid="e0001", kind="person", name="Alma"),),
                 situations=sits, obs_specs=specs, card=Card(name="Alma"))


@functools.lru_cache(maxsize=None)
def world_l0() -> World:
    return build_world(0, TierCfg.for_tier("L0"))


def hs(c):
    return list(c.h)


# ---------------------------------------------------------------------------- solver


@pytest.mark.parametrize("target", [0.1, 0.3, 0.5, 0.7, 0.9])
@pytest.mark.parametrize("nu", [0.0, 0.3, 0.5])
def test_solve_sigma_hits_the_target_within_003(target, nu):
    for seed in (0, 1, 2, 3):
        w = world(seed)
        sigma, nu_eff, achieved = ch.solve_channel(w, target, seed, nu)
        assert abs(achieved - target) <= 0.03, (seed, target, nu, achieved)
        assert 0.0 <= nu_eff <= nu + 1e-6 and sigma >= 0.0
        built = ch.make_channel(w, "TRUE", target, nu, seed)
        assert abs(built.realised_corr - target) <= 0.03
        assert built.sigma == sigma == ch.solve_sigma(w, target, seed, nu)


def test_sigma_falls_as_reliability_rises():
    w = world(2)
    sig = [ch.solve_sigma(w, t, 2) for t in (0.3, 0.5, 0.7, 0.9)]
    assert sig[0] > sig[1] > sig[2] > sig[3] >= 0.0


def test_default_nu_is_the_config_value():
    w = world(1)
    assert ch.solve_channel(w, 0.7, 1) == ch.solve_channel(w, 0.7, 1, w.cfg.nu)
    assert ch.make_channel(w, "TRUE", 0.7, None, 1).nu == w.cfg.nu == 0.3


def test_reliability_one_is_noiseless_and_nuisance_free():
    w = world(0)
    c = ch.make_channel(w, "TRUE", 1.0, 0.3, 5)
    assert c.sigma == 0.0 and dict(c.meta)["nu_eff"] == 0.0  # the nuisance share was shrunk to reach 1.0
    assert c.realised_corr >= 0.999
    a = ch.obs_arousal(w)
    assert spearman(hs(c), a) >= 0.999  # a monotone map keeps ranks
    assert pearson(hs(c), a) < 0.999  # ...but not levels: the map is not the identity
    order = sorted(range(len(a)), key=lambda i: (a[i], i))
    vals = [c.h[i] for i in order]
    assert all(y >= x for x, y in zip(vals, vals[1:]))


def test_ceiling_is_reached_by_shrinking_the_nuisance_share():
    w = world(0)
    sigma, nu_eff, achieved = ch.solve_channel(w, 0.97, 4, 0.5)
    assert sigma == 0.0 and 0.0 < nu_eff < 0.5 and abs(achieved - 0.97) <= 0.03
    # below the ceiling the requested share is kept
    assert ch.solve_channel(w, 0.4, 4, 0.5)[1] == 0.5


def test_reliability_zero_is_uncorrelated_but_keeps_the_scale():
    for seed in (0, 1, 2):
        w = world(seed)
        c = ch.make_channel(w, "TRUE", 0.0, 0.3, seed)
        assert abs(c.realised_corr) <= 0.03
        vals = hs(c)
        assert 0.0 <= min(vals) and max(vals) <= 1.0 and max(vals) - min(vals) > 0.05  # noise, not a constant


def test_nuisance_makes_a_noisy_channel_harder_to_read():
    w = world(0)
    # same sigma, more nuisance, lower correlation with A
    ing = ch._ingredients(w, 3)
    corr = []
    for nu in (0.0, 0.3, 0.6):
        h = ing.reading(ing.lat(nu), 0.05)
        corr.append(pearson(ranks(h), ing.ra))
    assert corr[0] > corr[1] > corr[2]


def test_the_noise_is_exactly_orthogonal_to_the_arousal_ranks():
    ing = ch._ingredients(world(0), 3)
    n = len(ing.e)
    assert abs(sum(ing.e) / n) < 1e-9 and sum(x * x for x in ing.e) / n == pytest.approx(1.0, abs=1e-9)
    assert abs(pearson(ing.e, ing.ra)) < 1e-9


def test_channel_shape_and_lookup():
    w = world(1)
    c = ch.make_channel(w, "TRUE", 0.7, 0.3, 9)
    assert c.oids == tuple(o.oid for o in w.obs_specs) and len(c.h) == len(w.obs_specs) == len(c.x)
    assert all(0.0 <= v <= 1.0 for v in c.h) and all(0.0 <= v <= 1.0 for v in c.x)
    assert c.value(w.obs_specs[5].oid) == c.h[5] and c.value("nope") is None
    assert c.arm == "TRUE" and c.reliability == 0.7 and c.seed == 9 and {"nu_eff", "achieved_true"} <= dict(c.meta).keys()


def test_determinism_and_independence_of_the_world_digest():
    w = world(0)
    a = ch.make_channel(w, "TRUE", 0.7, 0.3, 9)
    b = ch.make_channel(w, "TRUE", 0.7, 0.3, 9)
    assert a == b and a.digest() == b.digest()
    assert ch.make_channel(w, "TRUE", 0.7, 0.3, 10).h != a.h  # another channel seed, another channel
    assert w.with_channel(a).digest() == w.digest()  # channel never enters the structure digest
    assert all(ch.make_channel(w, arm, 0.7, 0.3, 9, need=["o00001"]).seed == 9 for arm in CHANNEL_ARMS)


def test_unknown_arm_and_leaky_without_need_are_rejected():
    w = world(0)
    with pytest.raises(ValueError):
        ch.make_channel(w, "BOGUS", 0.7, 0.3, 1)
    with pytest.raises(ValueError):
        ch.make_channel(w, "LEAKY", 0.7, 0.3, 1)


# --------------------------------------------------------------------------- the arms


def _arms(seed=3, rel=0.7):
    w = world(seed)
    true = ch.make_channel(w, "TRUE", rel, 0.3, 11)
    return w, true


def test_shuf_life_keeps_the_marginal_exactly_and_breaks_the_dependence():
    w, true = _arms()
    s = ch.make_channel(w, "SHUF_LIFE", 0.7, 0.3, 11)
    assert sorted(s.h) == sorted(true.h) and s.h != true.h
    assert abs(s.realised_corr) <= 0.1 and true.realised_corr > 0.65


def test_shuf_type_keeps_every_kinds_marginal_and_breaks_the_dependence_within_kind():
    w, true = _arms()
    s = ch.make_channel(w, "SHUF_TYPE", 0.7, 0.3, 11)
    kinds = {}
    for i, o in enumerate(w.obs_specs):
        kinds.setdefault(ch.obs_kind(w, o), []).append(i)
    assert len(kinds) >= 5
    for idx in kinds.values():
        assert sorted(s.h[i] for i in idx) == sorted(true.h[i] for i in idx)
    a = ch.obs_arousal(w)
    big = max(kinds.values(), key=len)  # the routine lines
    assert spearman([true.h[i] for i in big], [a[i] for i in big]) > 0.4
    assert abs(spearman([s.h[i] for i in big], [a[i] for i in big])) < 0.12
    assert s.h != true.h
    # type base rates survive: the signal that remains is composition only
    assert 0.0 < s.realised_corr < true.realised_corr - 0.2


def test_time_shift_is_a_circular_shift_that_keeps_the_autocorrelation():
    w, true = _arms()
    t = ch.make_channel(w, "TIME_SHIFT", 0.7, 0.3, 11)
    n = len(true.h)
    offs = [o for o in range(1, n) if all(t.h[i] == true.h[(i + o) % n] for i in range(0, n, 37))]
    assert offs and n // 4 <= offs[0] <= 3 * n // 4

    def circ_lag1(v):
        m = sum(v) / n
        return sum((v[i] - m) * (v[(i + 1) % n] - m) for i in range(n)) / sum((x - m) ** 2 for x in v)

    assert circ_lag1(hs(t)) == pytest.approx(circ_lag1(hs(true)), abs=1e-9)
    assert sorted(t.h) == sorted(true.h) and abs(t.realised_corr) <= 0.1


def test_random_resamples_the_marginal_and_breaks_the_dependence():
    w, true = _arms()
    r = ch.make_channel(w, "RANDOM", 0.7, 0.3, 11)
    assert set(r.h) <= set(true.h)
    xs, ys = sorted(true.h), sorted(r.h)
    n = len(xs)
    ks = max(abs(sum(1 for v in xs if v <= t) / n - sum(1 for v in ys if v <= t) / n) for t in set(xs[::7]))
    assert ks < 0.08
    assert abs(sum(r.h) - sum(true.h)) / n < 0.02 and abs(r.realised_corr) <= 0.1


def test_const_is_constant_at_the_mean():
    w, true = _arms()
    c = ch.make_channel(w, "CONST", 0.7, 0.3, 11)
    assert len(set(c.h)) == 1 and c.h[0] == pytest.approx(sum(true.h) / len(true.h), abs=1e-6)
    assert c.realised_corr == 0.0


def test_inverted_mirrors_true():
    w, true = _arms()
    inv = ch.make_channel(w, "INVERTED", 0.7, 0.3, 11)
    assert all(abs(a + b - 1.0) < 2e-6 for a, b in zip(true.h, inv.h))
    assert inv.realised_corr == pytest.approx(-true.realised_corr, abs=1e-3)


def test_nuisance_only_follows_the_nuisance_not_the_arousal():
    w, true = _arms()
    n = ch.make_channel(w, "NUISANCE_ONLY", 0.7, 0.3, 11)
    assert abs(n.realised_corr) <= 0.1
    assert spearman(hs(n), list(n.x)) > 0.1  # it tracks X
    assert abs(spearman(hs(true), list(true.x))) < 0.3 and n.h != true.h


def test_lag_delays_the_reading():
    w, true = _arms()
    lag = ch.make_channel(w, "LAG", 0.7, 0.3, 11)
    k = 6
    assert lag.h[:k] == (None,) * k and lag.h[k:] == true.h[:-k]
    assert abs(lag.realised_corr) < 0.15
    longer = ch.make_channel(dataclasses.replace(w, cfg=w.cfg.with_extra(channel_lag_lines=10)), "LAG", 0.7, 0.3, 11)
    assert longer.h[:10] == (None,) * 10 and longer.h[10:] == true.h[:-10]


def test_absent_has_no_readings():
    w, _ = _arms()
    a = ch.make_channel(w, "ABSENT", 0.7, 0.3, 11)
    assert set(a.h) == {None} and a.value(w.obs_specs[0].oid) is None and a.realised_corr == 0.0


def test_oracle_is_exactly_the_arousal():
    w, _ = _arms()
    o = ch.make_channel(w, "ORACLE", 0.3, 0.3, 11)
    assert all(abs(h - a) < 1e-6 for h, a in zip(o.h, ch.obs_arousal(w))) and o.realised_corr == 1.0


def test_leaky_carries_the_later_need_label():
    w, true = _arms()
    need = {o.oid for i, o in enumerate(w.obs_specs) if i % 11 == 0}
    lk = ch.make_channel(w, "LEAKY", 0.7, 0.3, 11, need=need)
    hot = [h for h, o in zip(lk.h, lk.oids) if o in need]
    cold = [h for h, o in zip(lk.h, lk.oids) if o not in need]
    assert min(hot) >= ch.LEAK_SHARE - 1e-6 and max(cold) <= 1 - ch.LEAK_SHARE + 1e-6
    assert min(hot) > max(cold)  # the label separates the lines perfectly
    assert lk.realised_corr > 0.1  # still correlated with A, far less than with the label


# ------------------------------------------------------------------ pieces and edge cases


def test_obs_arousal_and_retelling_lines():
    w = world(5, "natural")
    a = ch.obs_arousal(w)
    retold = [i for i, o in enumerate(w.obs_specs) if ch.is_retell(o)]
    assert retold, "natural rehearsal must create retelling lines in an L1 life"
    for i, o in enumerate(w.obs_specs):
        base = w.situation(o.sid).A
        assert a[i] == (pytest.approx(0.5 * base) if i in retold else base)
    spec = w.obs_specs[0]
    for frame, mentions, expected in (("retell", (), True), ("", (Mention(fid="f1", role="recall"),), True),
                                      ("", (Mention(fid="f1", role="recall"), Mention(fid="f2", role="assert")), False),
                                      ("", (), False), ("recall", (Mention(fid="f1", role="recall"),), True)):
        assert ch.is_retell(dataclasses.replace(spec, frame=frame, mentions=mentions)) is expected


def test_nuisance_series():
    w = world(0)
    x = ch.nuisance_series(w, 4)
    assert x == ch.nuisance_series(w, 4) and x != ch.nuisance_series(w, 5)
    assert all(0.0 <= v <= 1.0 for v in x) and len(x) == len(w.obs_specs)
    loud = sum(1 for v in x if v > 0.1) / len(x)
    assert 0.03 < loud < 0.5
    assert abs(spearman(x, ch.obs_arousal(w))) < 0.1  # independent of A
    busy = dataclasses.replace(w, cfg=dataclasses.replace(w.cfg, x_burst_rate=3.0))
    assert sum(ch.nuisance_series(busy, 4)) > 2 * sum(x)


def test_monotone_map_is_strictly_increasing_and_differs_per_seed():
    from corpus.lifesim.rng import stream

    k1, k2 = ch.monotone_map(stream(1, "m")), ch.monotone_map(stream(2, "m"))
    for k in (k1, k2):
        assert k[0] == 0.0 and k[-1] == 1.0 and all(b > a for a, b in zip(k, k[1:]))
        grid = [ch._apply_map(k, i / 200) for i in range(201)]
        assert all(b > a for a, b in zip(grid, grid[1:])) and grid[0] == 0.0 and grid[-1] == pytest.approx(1.0)
    assert k1 != k2 and ch._apply_map(k1, -3.0) == 0.0 and ch._apply_map(k1, 5.0) == pytest.approx(1.0)


def test_restrict_channel_keeps_surviving_readings():
    w = world(0)
    c = ch.make_channel(w, "TRUE", 0.7, 0.3, 9)
    keep = [o.oid for i, o in enumerate(w.obs_specs) if i % 3]
    r = ch.restrict_channel(c, keep)
    assert r.oids == tuple(keep) and all(r.value(o) == c.value(o) for o in keep)
    assert len(r.x) == len(keep) and r.arm == c.arm and r.sigma == c.sigma


def test_faults_drop_and_reverse_readings():
    w = world(0)
    c = ch.make_channel(w, "TRUE", 0.7, 0.3, 9)
    f = ch.with_faults(c, 0.1, 0.15, 3)
    assert f == ch.with_faults(c, 0.1, 0.15, 3) and f.h != ch.with_faults(c, 0.1, 0.15, 4).h
    n = len(c.h)
    dropped = sum(1 for v in f.h if v is None) / n
    kept = [(a, b) for a, b in zip(c.h, f.h) if b is not None]
    reversed_ = sum(1 for a, b in kept if abs(a + b - 1.0) < 2e-6 and abs(a - b) > 1e-5) / len(kept)
    assert abs(dropped - 0.1) < 0.03 and abs(reversed_ - 0.15) < 0.04
    assert dict(f.meta)["dropout"] == 0.1
    absent = ch.with_faults(ch.make_channel(w, "ABSENT", 0.7, 0.3, 9), 0.0, 1.0, 3)
    assert set(absent.h) == {None}


def test_tiny_and_degenerate_worlds_do_not_crash():
    empty = tiny_world([])
    for arm in CHANNEL_ARMS:
        c = ch.make_channel(empty, arm, 0.7, 0.3, 1, need=[])
        assert c.h == () and c.oids == ()
    three = tiny_world([0.1, 0.5, 0.2])
    assert ch.solve_sigma(three, 0.7, 1) == 0.0
    for arm in CHANNEL_ARMS:
        c = ch.make_channel(three, arm, 0.7, 0.3, 1, need=["o00002"])
        assert len(c.h) == 3
    flat = tiny_world([0.2] * 12)  # constant arousal: nothing to correlate with
    c = ch.make_channel(flat, "TRUE", 0.7, 0.3, 1)
    assert len(c.h) == 12 and all(0.0 <= v <= 1.0 for v in c.h)

GOLDEN_CHANNELS = {  # L0 seed 0, reliability 0.7, nu 0.3, channel seed 9; identical on Python 3.11 and 3.12
    "TRUE": "bca271bf476b17434135a487f0587bed192fc988e4145cd3d98fbf8e7ac773aa",
    "SHUF_TYPE": "c41056a6a050a3890ee8847f1d06d99d692cec83d63991496c1bc2501b7b5b44",
    "SHUF_LIFE": "135bc570c1049973ebd1481e2a06d3675f32efb6555cbebe9faf1a0014f3f35b",
    "TIME_SHIFT": "f61cf377d8034b6d90a379365882227a5cd032f2d45592e9740c0e4805bef097",
    "RANDOM": "4844f17991b2f492e226f4063e7cecbda66629862d479089acdde04687c0ffbf",
    "CONST": "1fd6c997d469bf2808419afd7c0db7370b2b88ecd8daa3bc64d446d6ad112c3d",
    "INVERTED": "c6d5f9f5e58b062f69c835318d0ce1eb561e4643607ae440f6f4cc1acfd71fe0",
    "NUISANCE_ONLY": "51768a2f286f2500247ffa9325e524930906f5c111529a74f42310729c3f2625",
    "LAG": "421aa15019cdccaa8c5d717e2b906f9e6b1cbd2bda2ff5d52f49b38830ff0d03",
    "ORACLE": "d901fd71a49f30950ce1f09aa9dd45dfa049940c43797a1edba067daf03a09f0",
}


def test_channel_digests_are_pinned():
    w = world_l0()
    for arm, digest in GOLDEN_CHANNELS.items():
        assert ch.make_channel(w, arm, 0.7, 0.3, 9).digest() == digest, arm
