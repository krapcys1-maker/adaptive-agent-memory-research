"""Tests for corpus.lifesim.queries (step D1-D): candidate pool, decile quotas, the seven Day-1
families, the independent second solver and the structural memory filter.

The world builder (``world.py``) is written at the same time by someone else, so these tests
use ``WB``, a tiny hand-built world generator that follows the structure described in the
``queries`` docstring. Standard library and pytest only; no model or network calls."""

from __future__ import annotations

import dataclasses
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import queries as Q  # noqa: E402
from corpus.lifesim import rng as R  # noqa: E402
from corpus.lifesim import schema as S  # noqa: E402
from corpus.lifesim import vocab as V  # noqa: E402
from corpus.lifesim.schema import (CELLS, Card, Entity, Fact, Mention, ObsSpec, Prior,  # noqa: E402
                                   Situation, Slot, TierCfg, World)

# --------------------------------------------------------------------------- world builder


class WB:
    """Hand-build a LifeSim world row by row (no randomness unless the caller adds it)."""

    def __init__(self, days: int = 100, **cfg_kw):
        base = dict(days=days, delay_max_days=days - 5)
        base.update(cfg_kw)
        self.cfg = dataclasses.replace(TierCfg.for_tier("L1"), **base)
        self.entities, self.facts, self.sits, self.specs, self.priors = [], [], [], [], []

    def entity(self, kind, name, aliases=()):
        eid = S.new_id("entity", len(self.entities) + 1)
        self.entities.append(Entity(eid=eid, kind=kind, name=name, aliases=tuple(aliases)))
        return eid

    def fact(self, subj, pred, obj, vfrom, vto=None, src="lived", centrality=0.0, supersedes=""):
        fid = S.new_id("fact", len(self.facts) + 1)
        self.facts.append(Fact(fid=fid, subj=subj, pred=pred, obj=obj, vfrom=vfrom, vto=vto, src=src,
                               centrality=centrality, supersedes=supersedes))
        return fid

    def situation(self, day, scene="minor", A=0.2, facts=(), minute=600):
        s = Situation(sid=S.new_id("situation", len(self.sits) + 1), day=day, minute=minute,
                      scene=scene, A=A, facts=tuple(facts))
        self.sits.append(s)
        return s

    def line(self, sit, mentions, slots, channel="diary", offset=0):
        oid = S.new_id("obs", len(self.specs) + 1)
        self.specs.append(ObsSpec(oid=oid, t_obs=sit.day * 1440 + sit.minute + offset, channel=channel,
                                  sid=sit.sid, mentions=tuple(mentions), slots=tuple(slots)))
        return oid

    # -- ready-made scenes
    def breakfast(self, day, dish, A=0.2, subj="me"):
        fid = self.fact(subj, "breakfast", dish, day, day)
        sit = self.situation(day, "routine", A, [fid])
        oid = self.line(sit, [Mention(fid=fid, role="assert")], [Slot(name="breakfast", value=dish, fid=fid)])
        return fid, oid

    def article(self, day, colour, kind, city, A=0.2, decoy=None, n=0):
        fid = self.fact("story%03d" % n, "vehicle_colour", colour, day, src="read")
        sit = self.situation(day, "article", A, [fid])
        slots = [Slot(name="vehicle_colour", value=colour, fid=fid), Slot(name="story_kind", value=kind),
                 Slot(name="city", value=city)]
        if decoy:
            slots.append(Slot(name="decoy_colour", value=decoy))
        return fid, self.line(sit, [Mention(fid=fid, role="assert")], slots, channel="article")

    def event(self, day, person_eid, person_name, colour, A=0.5, retell=0):
        cf = self.fact("me", "companion", person_eid, day, centrality=0.9)
        pf = self.fact("car%03d" % day, "vehicle_colour", colour, day, centrality=0.1)
        sit = self.situation(day, "major", A, [cf, pf])
        ms = [Mention(fid=cf, role="assert"), Mention(fid=pf, role="assert")]
        sl = [Slot(name="companion", value=person_name, fid=cf), Slot(name="vehicle_colour", value=colour, fid=pf)]
        oids = [self.line(sit, ms, sl)]
        for r in range(retell):
            later = self.situation(day + 1 + r, "minor", 0.1)
            oids.append(self.line(later, [Mention(fid=cf, role="recall"), Mention(fid=pf, role="recall")], sl, channel="chat"))
        return cf, pf, oids

    def remark(self, day, shop_eid, shop_name, street_name, time, A=0.01):
        fid = self.fact(shop_eid, "closing_time", time, day)
        sit = self.situation(day, "remark", A, [fid])
        oid = self.line(sit, [Mention(fid=fid, role="assert")],
                        [Slot(name="shop", value=shop_name), Slot(name="street", value=street_name),
                         Slot(name="closing_time", value=time, fid=fid)], channel="chat")
        return fid, oid

    def errand(self, day, what, subj="me", person_name=None, A=0.2):
        fid = self.fact(subj, "errand", what, day, day)
        sit = self.situation(day, "minor", A, [fid])
        sl = [Slot(name="errand", value=what, fid=fid)]
        if person_name:
            sl.append(Slot(name="person", value=person_name))
        return fid, self.line(sit, [Mention(fid=fid, role="assert")], sl)

    def chain(self, pred, slot, values, change_days, A=0.2, restate=0, restate_role="recall"):
        """Version chain of the narrator: values[i] is valid from change_days[i-1] (day 1 for the
        first) to the day before the next change. ``values`` are entity ids or canonical strings."""
        starts = [1] + list(change_days)
        fids, oids = [], []
        for i, val in enumerate(values):
            vto = starts[i + 1] - 1 if i + 1 < len(values) else None
            fid = self.fact("me", pred, val, starts[i], vto, supersedes=fids[-1] if fids else "")
            sit = self.situation(starts[i], "move" if i else "minor", A, [fid])
            name = self.ent_name(val)
            role = "update" if i else "assert"
            oids.append(self.line(sit, [Mention(fid=fid, role=role)], [Slot(name=slot, value=name, fid=fid)]))
            end = vto if vto is not None else self.cfg.days - 2
            for r in range(restate):
                d = starts[i] + 1 + (r * max(1, (end - starts[i]) // (restate + 1)))
                if d <= end:
                    s2 = self.situation(d, "minor", A)
                    oids.append(self.line(s2, [Mention(fid=fid, role=restate_role)],
                                          [Slot(name=slot, value=name, fid=fid)], channel="chat"))
            fids.append(fid)
        return fids, oids

    def ent_name(self, val):
        for e in self.entities:
            if e.eid == val:
                return e.name
        return val

    def filler(self, day, A=0.2, channel="note"):
        return self.line(self.situation(day, "minor", A), [], [], channel=channel)

    def build(self, seed=0, narrator=None, dishes=None, card="Alma"):
        specs = sorted(self.specs, key=lambda o: (o.t_obs, o.oid))
        w = World(seed=seed, cfg=self.cfg, entities=tuple(self.entities), facts=tuple(self.facts),
                  situations=tuple(self.sits), obs_specs=tuple(specs), card=Card(name=card),
                  priors=tuple(self.priors), mapping="M1", partition="dev")
        return w.with_extra("narrator", narrator) if narrator else w


def make_world(seed: int = 1, days: int = 300, n_foods: int = 45, scale: int = 1, **cfg_kw) -> World:
    """A random but deterministic world with every Day-1 family represented (``scale`` multiplies
    the number of articles, events and breakfasts for denser support)."""
    rng = R.stream(seed, "fixture")
    b = WB(days=days, queries_per_world=cfg_kw.pop("queries_per_world", 100), **cfg_kw)
    used: set = set()
    persons = [b.entity("person", n) for n in V.make_names(rng, 30, "dev", "person", used)]
    cities = [b.entity("city", n) for n in V.make_names(rng, 30, "dev", "city", used)]
    city_names = [b.ent_name(e) for e in cities]
    streets = V.make_names(rng, 30, "dev", "street", used)
    shop_bases = V.make_names(rng, 30, "dev", "shop", used)
    shops = [(b.entity("shop", n + " Pharmacy"), n + " Pharmacy") for n in shop_bases]
    orgs = [b.entity("org", n) for n in V.make_names(rng, 12, "dev", "org", used)]
    dishes = rng.sample(V.DISHES, n_foods)
    probs = R.zipf_probs(n_foods, 0.6)
    b.priors.append(Prior(slot="breakfast", values=tuple(dishes), probs=probs))

    def A():
        return R.q(min(1.0, rng.expo(0.22)))

    for d in range(1, days - 2):
        if rng.chance(min(0.95, 0.45 * scale)):
            b.breakfast(d, dishes[rng.weighted(probs)], A())
    for pred, pool, n in (("lives_in", cities, 4 + scale), ("works_as", V.JOBS, 3 + scale),
                          ("works_at", orgs, 3 + scale)):
        vals = rng.sample(list(pool), n)
        cds = sorted(rng.sample(range(20, days - 25), n - 1))
        b.chain(pred, pred, vals, cds, A(), restate=3)
    for p, rel in zip(rng.sample(persons, 12), rng.sample(V.RELATIONS, 12)):
        d = rng.ri(1, days - 5)
        fid = b.fact(p, "relation", rel, d)
        sit = b.situation(d, "minor", A(), [fid])
        b.line(sit, [Mention(fid=fid, role="assert")],
               [Slot(name="relation", value=rel, fid=fid), Slot(name="person", value=b.ent_name(p))])
    for i in range(80 * scale):
        colour = rng.choice(V.COLOURS)
        decoy = rng.choice(V.COLOURS) if rng.chance(0.5) else None
        if decoy == colour:
            decoy = None
        b.article(rng.ri(1, days - 3), colour, rng.choice(V.STORY_KINDS), rng.choice(city_names), A(), decoy, i)
    for d in rng.sample(range(2, days - 6), min(days - 8, 45 * scale)):
        p = rng.choice(persons)
        b.event(d, p, b.ent_name(p), rng.choice(V.COLOURS), A(), retell=1 if rng.chance(0.25) else 0)
    for (e, name), st in zip(rng.sample(shops, 22), streets):
        b.remark(rng.ri(1, days - 20), e, name, st, rng.choice(V.TIMES), R.q(rng.u() * 0.04))
    for what in V.ERRANDS[:6 * scale]:
        for d in rng.sample(range(1, days - 3), rng.ri(2, 9)):
            b.errand(d, what, A=A())
        for d in rng.sample(range(1, days - 3), 3):
            p = rng.choice(persons)
            b.errand(d, what, subj=p, person_name=b.ent_name(p), A=A())
    free = [c for c in cities if c not in {f.obj for f in b.facts if f.pred == "lives_in"}]
    for c in rng.sample(free, 4):
        d = rng.ri(5, days - 10)
        vf = b.fact("me", "visited", c, d)
        who = rng.choice(persons)
        cf = b.fact("me", "companion", who, d, centrality=0.7)
        sit = b.situation(d, "trip", A(), [vf, cf])
        b.line(sit, [Mention(fid=vf, role="assert"), Mention(fid=cf, role="assert")],
               [Slot(name="visited", value=b.ent_name(c), fid=vf),
                Slot(name="companion", value=b.ent_name(who), fid=cf)])
    for _ in range(250):
        b.filler(rng.ri(0, days - 1), A(), rng.choice(("note", "chat", "log")))
    return b.build(seed=seed)


@pytest.fixture(scope="module")
def world():
    return make_world(1)


@pytest.fixture(scope="module")
def built(world):
    return {name: Q.build_queries_ex(world, world.cfg, cell) for name, cell in CELLS.items()}

# ------------------------------------------------------------------------------- helpers


def T(day: int, minute: int = 0) -> int:
    return day * 1440 + minute


def mkq(ask, cue, t_ask, family="EP1", gold="x", kind="entity"):
    return S.Query(qid="q9999", family=family, t_ask=t_ask, text="", fmt="open",
                   gold=S.Gold(kind=kind, value=gold, vocab_id=V.SLOTS[ask]),
                   cue=tuple(Slot(name=k, value=v) for k, v in cue), ask=ask)


def iso(w, day):
    return S.date_of(w.cfg.start_date, day)


class _Cand:
    """A synthetic candidate with just the attributes the quota code reads."""

    def __init__(self, key, A):
        self.key, self.A = key, A


# --------------------------------------------------------------- relative dates, deciles


def test_relative_phrase_and_resolution():
    assert Q.relative_phrase(1) == "yesterday" and Q.relative_phrase(2) == "2 days ago"
    assert Q.relative_phrase(30) == "30 days ago" and Q.relative_phrase(31) is None
    assert Q.relative_phrase(0) is None and Q.relative_phrase(-3) is None
    assert Q.relative_phrase(14, fuzzy=True) == "about two weeks ago"
    assert Q.relative_phrase(7, fuzzy=True) == "7 days ago"
    assert Q.relative_phrase(95, fuzzy=True) == "about three months ago"
    assert Q.resolve_relative("yesterday", 50) == (49, 49)
    assert Q.resolve_relative("3 days ago", 50) == (47, 47)
    assert Q.resolve_relative("about two weeks ago", 50) == (33, 39)
    assert Q.resolve_relative("about one week ago", 50) == (40, 46)
    assert Q.resolve_relative("about three months ago", 200) == (95, 125)
    assert Q.resolve_relative("last tuesday", 50) is None
    assert Q.resolve_relative("about zorp weeks ago", 50) is None


def test_every_fuzzy_phrase_contains_its_own_event_day():
    for ask_day in (400, 1000):
        for delay in range(1, 361):
            lo, hi = Q.resolve_relative(Q.relative_phrase(delay, fuzzy=True), ask_day)
            assert lo <= ask_day - delay <= hi, delay
            if delay <= 30:
                lo, hi = Q.resolve_relative(Q.relative_phrase(delay), ask_day)
                assert lo == hi == ask_day - delay


def test_rank_fraction_and_decile_use_mid_ranks():
    allv = sorted(i / 100.0 for i in range(100))
    assert Q.decile_of(-1.0, allv) == 0 and Q.decile_of(2.0, allv) == 9
    assert Q.decile_of(0.05, allv) == 0 and Q.decile_of(0.95, allv) == 9
    assert Q.rank_fraction(0.5, allv) == pytest.approx(0.505)
    ties = [0.0] * 50 + [1.0] * 50
    assert Q.decile_of(0.0, ties) == 2 and Q.decile_of(1.0, ties) == 7
    assert Q.rank_fraction(0.3, []) == 0.5


# -------------------------------------------------------------------------------- quotas


def test_shape_is_flat_at_the_null_and_hits_the_enrichment_elsewhere():
    kappa, probs, feasible = Q._shape(1.0, 0.0)
    assert kappa == 0.0 and feasible and probs == (0.1,) * 10
    for e in S.E_GRID:
        for mu in S.MU_GRID:
            kappa, probs, feasible = Q._shape(e, mu)
            assert abs(sum(probs) - 1.0) < 1e-9
            if feasible:
                assert abs(probs[9] / 0.1 - e) < 1e-6, (e, mu)
                assert probs[0] + probs[1] >= mu - 1e-9
    for e in (2.0, 4.0):
        p = Q._shape(e, 0.0)[1]
        assert all(a < b for a, b in zip(p, p[1:]))
    for e in (0.2, 0.5):
        p = Q._shape(e, 0.0)[1]
        assert all(a > b for a, b in zip(p, p[1:]))


def test_shape_flags_unreachable_cells():
    assert Q._shape(10.0, 0.0)[2] is False
    assert Q._shape(4.0, 0.6)[2] is False       # 40% in the top decile cannot coexist with mu = 0.6
    assert Q._shape(4.0, 0.3)[2] is True


def test_mu_adds_quiet_critical_mass_without_moving_e():
    base = Q._shape(1.0, 0.0)[1]
    for mu in (0.1, 0.3, 0.6):
        p = Q._shape(1.0, mu)[1]
        assert p[9] / 0.1 == pytest.approx(1.0, abs=1e-6)      # E is solved with mu, not compensated away
        assert p[0] + p[1] > base[0] + base[1]
        assert p[0] + p[1] >= mu


def test_solve_quota_counts_supply_and_shortfall():
    A_all = [i / 99.0 for i in range(100)]
    cands = [_Cand("c%02d" % i, i / 99.0) for i in range(0, 100, 2)]
    qt = Q.solve_quota(CELLS["C0"], A_all, cands, k=40)
    assert qt.counts == (4,) * 10 and qt.supply == (5,) * 10 and qt.shortfall == 0 and qt.feasible
    qt = Q.solve_quota(CELLS["C+"], A_all, cands, k=40)
    assert sum(qt.counts) == 40 and qt.counts[9] == 16 and qt.taken[9] == 5
    assert qt.shortfall == sum(c - t for c, t in zip(qt.counts, qt.taken)) >= 11
    assert all(t <= s for t, s in zip(qt.taken, qt.supply))
    assert qt.expected_e == pytest.approx(4.0, abs=1e-6)
    assert qt.shortfall_share == qt.shortfall / 40
    assert Q.solve_quota(CELLS["C0"], A_all, cands).counts == ()
    assert Q.solve_quota((2.0, 0.0), A_all, [0.1, 0.9]).supply[1] == 1


def test_sample_targets_is_deterministic_order_free_and_prefix_balanced():
    A_all = [i / 999.0 for i in range(1000)]
    pool = [_Cand("c%04d" % i, i / 999.0) for i in range(1000)]
    d1 = Q.sample_targets(pool, 100, CELLS["C+"], 7, A_all, "x")
    d2 = Q.sample_targets(list(reversed(pool)), 100, CELLS["C+"], 7, A_all, "x")
    assert [c.key for c in d1.chosen] == [c.key for c in d2.chosen]
    d3 = Q.sample_targets(pool, 100, CELLS["C+"], 8, A_all, "x")
    assert [c.key for c in d3.chosen] != [c.key for c in d1.chosen]
    assert len(d1.chosen) == len({c.key for c in d1.chosen}) == 100 and d1.shortfall == 0
    assert tuple(d1.deciles.count(j) for j in range(10)) == d1.quota.counts
    for m in (20, 50, 80):                     # truncating keeps the dial
        for j in range(10):
            assert abs(d1.deciles[:m].count(j) - m * d1.quota.probs[j]) <= 1.5, (m, j)


def test_sample_targets_realised_enrichment_on_ample_support():
    A_all = [i / 999.0 for i in range(1000)]
    pool = [_Cand("c%04d" % i, i / 999.0) for i in range(1000)]
    srt = sorted(A_all)
    for e in S.E_GRID:
        d = Q.sample_targets(pool, 200, S.grid_cell(e, 0.0), 3, A_all, "x")
        hit = sum(1 for c in d.chosen if Q.rank_fraction(c.A, srt) >= 0.9)
        assert abs(hit / 200 / 0.1 - e) <= 0.15 * e + 1e-9, (e, hit)
    d = Q.sample_targets(pool, 200, S.Cell("q", 1.0, 0.0, 0.6), 3, A_all, "x")
    assert sum(1 for x in d.deciles if x < 2) / 200 >= 0.6


def test_sample_targets_reports_shortfall_when_the_top_is_thin():
    A_all = [i / 999.0 for i in range(1000)]
    pool = [_Cand("c%04d" % i, i / 999.0) for i in range(0, 900)]       # nothing above the 90th percentile
    d = Q.sample_targets(pool, 100, CELLS["C+"], 1, A_all, "x")
    assert d.quota.supply[9] == 0 and d.shortfall >= 40 and len(d.chosen) == 100 - d.shortfall


# --------------------------------------------------------- candidate pool on hand-built worlds


def test_pool_ep1_needs_one_assert_line_and_flags_habit_days():
    b = WB(days=60)
    b.priors.append(Prior(slot="breakfast", values=("porridge", "croissant", "toast with jam", "fruit salad"),
                          probs=(0.4, 0.3, 0.2, 0.1)))
    f1, o1 = b.breakfast(5, "porridge")
    f2, o2 = b.breakfast(6, "fruit salad")
    f3, _ = b.breakfast(7, "croissant")
    b.line(b.situation(8), [Mention(fid=f3, role="recall")],
           [Slot(name="breakfast", value="croissant", fid=f3)], channel="chat")
    w = b.build(narrator="me")
    ep1 = {c.key: c for c in Q.candidate_pool(w).of("EP1")}
    assert set(ep1) == {f1, f2}                               # f3 was told twice
    assert ep1[f1].get("prior_answerable") == "1" and ep1[f2].get("prior_answerable") == ""
    c = ep1[f2]
    assert (c.value, c.day, c.oids, c.fids, c.t_ready) == ("fruit salad", 6, (o2,), (f2,), T(6, 600))


def test_pool_se_chains_versions_and_identity_facts():
    b = WB(days=80)
    k, v = b.entity("city", "Karmont"), b.entity("city", "Verdton")
    imre = b.entity("person", "Imre")
    b.breakfast(2, "porridge")
    fids, _ = b.chain("lives_in", "lives_in", [k, v], [40], restate=2)
    rf = b.fact(imre, "relation", "neighbour", 3)
    b.line(b.situation(3, "minor", 0.1, [rf]), [Mention(fid=rf, role="assert")],
           [Slot(name="relation", value="neighbour", fid=rf), Slot(name="person", value="Imre")])
    w = b.build(narrator="me")
    pool = Q.candidate_pool(w)
    se4 = {c.key: c for c in pool.of("SE4")}
    assert set(se4) == {"SE4#" + fids[0], "SE4#" + fids[1], "SE4#" + rf}
    assert {c.key for c in pool.of("SE5")} == {"SE5#" + fids[0], "SE5#" + fids[1]}
    c1 = se4["SE4#" + fids[1]]
    assert c1.value == "Verdton" and c1.get("i") == "1" and c1.get("n") == "2" and c1.get("vto") == ""
    assert c1.get("chain") == ",".join(fids) and se4["SE4#" + fids[0]].get("vto") == "39"
    assert se4["SE4#" + rf].value == "neighbour" and se4["SE4#" + rf].get("person") == "Imre"


def test_pool_ep4_needs_exactly_one_central_and_one_peripheral_fact():
    b = WB(days=60)
    mara = b.entity("person", "Mara")
    cf, pf, _ = b.event(10, mara, "Mara", "blue", 0.6)
    sit = b.situation(20, "major", 0.5)                       # a situation with only a companion
    f = b.fact("me", "companion", mara, 20, centrality=0.9)
    sit2 = dataclasses.replace(sit, facts=(f,))
    b.sits[-1] = sit2
    b.line(sit2, [Mention(fid=f, role="assert")], [Slot(name="companion", value="Mara", fid=f)])
    w = b.build(narrator="me")
    ep4 = Q.candidate_pool(w).of("EP4")
    assert len(ep4) == 1 and ep4[0].fids == (cf, pf) and ep4[0].get("cval") == "Mara"
    assert ep4[0].get("pval") == "blue" and ep4[0].day == 10 and ep4[0].A == 0.6


def test_pool_in4_keeps_only_remarks_in_the_lowest_deciles():
    b = WB(days=80)
    s1, s2 = b.entity("shop", "Kalmer Pharmacy"), b.entity("shop", "Tisbo Bakery")
    for i in range(60):
        b.filler(1 + i % 70, A=0.05 + i / 100.0)
    q1, _ = b.remark(10, s1, "Kalmer Pharmacy", "Tisbo Street", "18:00", A=0.0)
    q2, _ = b.remark(11, s2, "Tisbo Bakery", "Tisbo Street", "17:15", A=0.99)
    w = b.build(narrator="me")
    in4 = Q.candidate_pool(w).of("IN4")
    assert [c.key for c in in4] == [q1]
    assert in4[0].get("shop") == "Kalmer Pharmacy" and in4[0].get("street") == "Tisbo Street"
    assert in4[0].value == "18:00" and in4[0].get("decile") in ("0", "1")


def test_pool_ep3c_windows_and_counts():
    b = WB(days=80)
    f = [b.errand(d, "dentist")[0] for d in (5, 12, 20)]
    g = [b.errand(30, "gym")[0], b.errand(30, "gym")[0]]       # two visits on one day: no window can split them
    w = b.build(narrator="me")
    ep = {c.key: c for c in Q.candidate_pool(w).of("EP3c")}
    dent = {k: c for k, c in ep.items() if c.get("errand") == "dentist"}
    assert sorted(c.value for c in dent.values()) == ["1", "1", "1", "2", "2", "3"]
    mid = dent["EP3c#dentist#1-1"]
    assert (mid.get("v_prev"), mid.get("v_first"), mid.get("v_last"), mid.get("v_next")) == ("5", "12", "12", "20")
    assert dent["EP3c#dentist#0-2"].fids == tuple(f) and dent["EP3c#dentist#0-2"].get("v_next") == "-1"
    assert sorted(c.value for k, c in ep.items() if c.get("errand") == "gym") == ["2"]
    assert set(g) <= {fid for c in ep.values() for fid in c.fids}


def test_pool_me1_traps():
    b = WB(days=40)
    for d in (5, 6, 8):
        b.breakfast(d, "porridge")
    s1, s2 = b.entity("shop", "Kalmer Pharmacy"), b.entity("shop", "Tisbo Bakery")
    b.remark(10, s1, "Kalmer Pharmacy", "Tisbo Street", "18:00")
    home, away, other = b.entity("city", "Karmont"), b.entity("city", "Verdton"), b.entity("city", "Dorndam")
    vf = b.fact("me", "visited", away, 12)
    cf = b.fact("me", "companion", b.entity("person", "Mara"), 12, centrality=0.7)
    b.line(b.situation(12, "trip", 0.3, [vf, cf]), [Mention(fid=vf, role="assert"), Mention(fid=cf, role="assert")],
           [Slot(name="visited", value="Verdton", fid=vf), Slot(name="companion", value="Mara", fid=cf)])
    b.fact("me", "lives_in", home, 0)
    w = b.build(narrator="me")
    me1 = Q.candidate_pool(w).of("ME1")
    by_type = {}
    for c in me1:
        by_type.setdefault(c.get("type"), []).append(c)
    assert sorted(int(c.get("day")) for c in by_type["breakfast"]) == [4, 7, 9]
    assert [c.get("city") for c in by_type["trip"]] == ["Dorndam"]    # Karmont is home, Verdton was visited
    assert [c.get("shop") for c in by_type["shop"]] == ["Tisbo Bakery"]
    assert all(c.value == "UNKNOWN" and c.oids == () for c in me1)


# ----------------------------------------------- the independent solver on hand-built worlds


def test_slow_breakfast_semantics():
    b = WB(days=60)
    b.breakfast(10, "fruit salad")
    b.breakfast(11, "porridge")
    w = b.build(narrator="me")
    d10 = iso(w, 10)
    assert Q.slow_answers(w, mkq("breakfast", [("date", d10)], T(20))) == ["fruit salad"]
    assert Q.slow_answers(w, mkq("breakfast", [("relative_day", "10 days ago")], T(20))) == ["fruit salad"]
    assert Q.slow_answers(w, mkq("breakfast", [("relative_day", "yesterday")], T(11, 700))) == ["fruit salad"]
    assert Q.slow_answers(w, mkq("breakfast", [("date", d10)], T(10, 300))) == []        # not yet observed
    assert Q.slow_answers(w, mkq("breakfast", [("date", d10)], T(10, 600))) == []        # the line is at 10:00: strictly before
    assert Q.slow_answers(w, mkq("breakfast", [("date", iso(w, 12))], T(20))) == []
    g = Q.gold_slow(w, mkq("breakfast", [("date", d10)], T(20)))
    assert (g.kind, g.value, g.vocab_id) == ("entity", "fruit salad", "pool:dishes")
    assert Q.gold_slow(w, mkq("breakfast", [("date", iso(w, 12))], T(20))).kind == "unknown"


def test_slow_solver_raises_on_an_ambiguous_cue():
    b = WB(days=30)
    b.breakfast(10, "fruit salad")
    b.breakfast(10, "porridge")
    w = b.build(narrator="me")
    qq = mkq("breakfast", [("date", iso(w, 10))], T(20))
    assert Q.slow_answers(w, qq) == ["fruit salad", "porridge"]
    with pytest.raises(Q.AmbiguousGold):
        Q.gold_slow(w, qq)


def test_slow_state_now_and_as_of():
    b = WB(days=80)
    k, v = b.entity("city", "Karmont"), b.entity("city", "Verdton")
    b.breakfast(2, "porridge")
    b.chain("lives_in", "lives_in", [k, v], [40], restate=2)
    w = b.build(narrator="me")
    now = lambda day, minute=0: Q.slow_answers(w, mkq("lives_in", [], T(day, minute), "SE4"))   # noqa: E731
    asof = lambda d, day, minute=0: Q.slow_answers(w, mkq("lives_in", [("date", iso(w, d))], T(day, minute), "SE5"))  # noqa: E731
    assert now(50) == ["Verdton"] and now(30) == ["Karmont"]
    assert now(39, 1000) == ["Karmont"]            # the update line comes at 10:00 on day 40
    assert now(40, 300) == []                      # Verdton is valid from day 40 but its line comes at 10:00
    assert asof(45, 50) == ["Verdton"] and asof(20, 50) == ["Karmont"]
    assert asof(45, 41) == ["Verdton"]
    assert asof(45, 40, 300) == []                 # valid then, but no line says so yet
    assert Q.slow_answers(w, mkq("lives_in", [("relative_day", "5 days ago")], T(50), "SE5")) == ["Verdton"]
    assert Q.slow_answers(w, mkq("lives_in", [("relative_day", "40 days ago")], T(50), "SE5")) == ["Karmont"]


def test_slow_state_respects_the_narrator_and_relation_lookup():
    b = WB(days=60)
    k = b.entity("city", "Karmont")
    mara = b.entity("person", "Mara")
    b.breakfast(2, "porridge", subj="narrator")
    b.chain("lives_in", "lives_in", [k], [], restate=0)
    other = b.entity("city", "Verdton")
    of = b.fact(mara, "lives_in", other, 1)               # Mara's city is not the narrator's
    b.line(b.situation(5, "minor", 0.1, [of]), [Mention(fid=of, role="assert")], [Slot(name="lives_in", value="Verdton", fid=of)])
    rf = b.fact(mara, "relation", "colleague", 6)
    b.line(b.situation(6, "minor", 0.1, [rf]), [Mention(fid=rf, role="assert")],
           [Slot(name="relation", value="colleague", fid=rf), Slot(name="person", value="Mara")])
    w = b.build()                                            # narrator found from the breakfast facts: 'narrator'
    assert Q.narrator_id(w) == "narrator"
    # the chain facts are subject 'me' here, so nothing is the narrator's: no answer, not Mara's city
    assert Q.slow_answers(w, mkq("lives_in", [], T(30), "SE4")) == []
    assert Q.narrator_id(w.with_extra("narrator", "me")) == "me"
    assert Q.slow_answers(w.with_extra("narrator", "me"), mkq("lives_in", [], T(30), "SE4")) == ["Karmont"]
    assert Q.slow_answers(w, mkq("relation", [("person", "Mara")], T(30), "SE4")) == ["colleague"]
    assert Q.slow_answers(w, mkq("relation", [("person", "Nobody")], T(30), "SE4")) == []


def test_slow_article_cues():
    b = WB(days=60)
    b.breakfast(2, "porridge")
    b.article(10, "red", "flood", "Verdton", n=1)
    b.article(12, "blue", "fire", "Karmont", n=2)
    b.article(14, "green", "flood", "Karmont", n=3)
    w = b.build(narrator="me")
    ans = lambda cue, day=24: Q.slow_answers(w, mkq("vehicle_colour", cue, T(day), "IN1"))   # noqa: E731
    assert ans([("story_kind", "flood"), ("city", "Karmont")]) == ["green"]
    assert ans([("story_kind", "flood")]) == ["red", "green"]
    assert ans([("story_kind", "flood"), ("relative_window", "about two weeks ago")]) == ["red"]      # window days 7-13
    assert ans([("story_kind", "flood"), ("date", iso(w, 14))]) == ["green"]
    assert ans([("story_kind", "flood"), ("city", "Karmont")], day=14) == []                        # read later that day
    assert ans([("story_kind", "storm")]) == []


def test_slow_event_pair_and_trip_semantics():
    b = WB(days=60)
    mara = b.entity("person", "Mara")
    b.breakfast(2, "porridge")
    b.event(30, mara, "Mara", "blue", 0.6)
    b.article(30, "red", "flood", "Verdton", n=1)             # a read article on the same day must not interfere
    away, never = b.entity("city", "Verdton"), b.entity("city", "Dorndam")
    vf = b.fact("me", "visited", away, 40)
    cf = b.fact("me", "companion", b.entity("person", "Imre"), 40, centrality=0.7)
    b.line(b.situation(40, "trip", 0.3, [vf, cf]), [Mention(fid=vf, role="assert"), Mention(fid=cf, role="assert")],
           [Slot(name="visited", value="Verdton", fid=vf), Slot(name="companion", value="Imre", fid=cf)])
    w = b.build(narrator="me")
    d30 = iso(w, 30)
    assert Q.slow_answers(w, mkq("companion", [("date", d30)], T(50), "EP4")) == ["Mara"]
    assert Q.slow_answers(w, mkq("vehicle_colour", [("date", d30)], T(50), "EP4")) == ["blue"]
    assert Q.slow_answers(w, mkq("companion", [("city", "Verdton")], T(50), "ME1")) == ["Imre"]
    assert Q.slow_answers(w, mkq("companion", [("city", "Dorndam")], T(50), "ME1")) == []
    assert Q.slow_answers(w, mkq("companion", [("date", d30)], T(30, 100), "EP4")) == []


def test_slow_closing_time_and_count():
    b = WB(days=80)
    s1, s2 = b.entity("shop", "Kalmer Pharmacy"), b.entity("shop", "Tisbo Bakery")
    b.breakfast(2, "porridge")
    b.remark(10, s1, "Kalmer Pharmacy", "Tisbo Street", "18:00")
    for d in (5, 12, 20, 40):
        b.errand(d, "dentist")
    b.errand(13, "dentist", subj="e0001", person_name="Imre")
    b.errand(14, "gym")
    w = b.build(narrator="me")
    assert Q.slow_answers(w, mkq("closing_time", [("shop", "Kalmer Pharmacy")], T(30), "IN4", kind="time")) == ["18:00"]
    assert Q.slow_answers(w, mkq("closing_time", [("shop", "Tisbo Bakery")], T(30), "IN4", kind="time")) == []
    g = Q.gold_slow(w, mkq("closing_time", [("shop", "Kalmer Pharmacy")], T(30), "IN4", kind="time"))
    assert (g.kind, g.value, g.vocab_id) == ("time", "18:00", "pool:times")

    def count(a, b_, day=60):
        cue = [("errand", "dentist"), ("window_from", iso(w, a)), ("window_to", iso(w, b_))]
        return Q.slow_answers(w, mkq("visit_count", cue, T(day), "EP3c", kind="count"))

    assert count(1, 25) == ["3"] and count(1, 12) == ["2"] and count(13, 19) == ["0"]     # Imre's visit is not mine
    assert count(1, 45) == ["4"] and count(1, 45, day=30) == ["3"]                    # the day-40 line is not yet there
    assert Q.gold_slow(w, mkq("visit_count", [("errand", "dentist"), ("window_from", iso(w, 13)),
                                              ("window_to", iso(w, 19))], T(60), "EP3c", kind="count")).value == "0"


# ----------------------------------------------------------------- random worlds: the builder


def test_candidate_pool_is_cell_independent_and_deterministic(world, built):
    digest = Q.candidate_pool(world).digest()
    assert digest == Q.candidate_pool(make_world(1)).digest()
    assert digest != Q.candidate_pool(make_world(2)).digest()
    assert all(res.pool.digest() == digest for res in built.values())
    assert Q.candidate_pool(world).counts() == built["C0"].pool.counts()


@pytest.mark.parametrize("cell", sorted(CELLS))
def test_build_queries_basic_properties(world, built, cell):
    res = built[cell]
    qs = res.queries
    assert len(qs) > 60
    assert [x.qid for x in qs] == [S.new_id("query", i) for i in range(1, len(qs) + 1)]
    assert [x.t_ask for x in qs] == sorted(x.t_ask for x in qs)
    end = world.cfg.days * 1440
    for x in qs:
        assert 0 < x.t_ask < end
        assert x.text == Q.plain_question(x, world.partition) and x.text
        assert x.tags.partition == world.partition and x.fmt == "open" and x.conf is True
        assert x.family in Q.FAMILY_ORDER and x.ask in V.SLOTS
        assert x.gold.vocab_id == V.SLOTS[x.ask]
        assert all(s.value in x.text for s in x.cue)
        ev = [world.obs_spec(o) for o in x.evidence_oids]
        assert all(o.t_obs < x.t_ask for o in ev)
        assert x.tags.n_evidence == len(ev)
        if ev:
            assert x.tags.delay_days == S.day_of(x.t_ask) - max(o.day for o in ev) >= 1
            assert 0 <= x.tags.arousal_decile <= 9
            assert x.tags.arousal_decile == Q.decile_of(x.tags.target_arousal, sorted(Q.stream_arousal(world)))
        assert x.gold.value not in {nm.value for nm in x.gold.near_miss}
    assert res.report.dropped(reason="mismatch") == 0


def test_gold_slow_equals_gold_fast_on_twenty_seeds():
    n_checked = 0
    for seed in range(20):
        w = make_world(seed, days=160, queries_per_world=60)
        for cell in ("C0", "C+") if seed < 4 else ("C0",):
            res = Q.build_queries_ex(w, w.cfg, cell)
            assert res.report.dropped(reason="mismatch") == 0
            for x in res.queries:
                g = Q.gold_slow(w, x)
                assert (g.kind, g.value) == (x.gold.kind, x.gold.value), (seed, x.family, x.ask, x.cue)
                n_checked += 1
    assert n_checked > 900


def test_every_family_is_present_and_pairs_are_complete(built):
    qs = built["C0"].queries
    fams = {x.family for x in qs}
    assert fams == {"EP1", "SE4", "SE5", "IN1", "EP4", "IN4", "EP3c", "ME1"}
    pairs = {}
    for x in qs:
        if x.family == "EP4":
            pairs.setdefault(x.tags.pair_id, []).append(x)
    assert pairs and all(sorted(y.tags.role for y in v) == ["central", "peripheral"] for v in pairs.values())
    for v in pairs.values():
        a, b2 = v
        assert a.tags.target_arousal == b2.tags.target_arousal and S.day_of(a.t_ask) == S.day_of(b2.t_ask)
        assert {a.ask, b2.ask} == {"companion", "vehicle_colour"}
    assert sum(1 for x in qs if x.family == "EP4") % 2 == 0


def test_evidence_strings_are_in_the_cited_lines(world, built):
    for res in built.values():
        for x in res.queries:
            assert Q.evidence_check(world, x) == [], (x.family, x.cue)


def test_evidence_check_flags_broken_evidence(world, built):
    x = next(y for y in built["C0"].queries if y.family == "IN1")
    bad = dataclasses.replace(x, gold=dataclasses.replace(x.gold, value="xxxxx"))
    assert any("no slot" in p for p in Q.evidence_check(world, bad))
    assert any("not before" in p for p in Q.evidence_check(world, dataclasses.replace(x, t_ask=0)))
    assert Q.evidence_check(world, dataclasses.replace(x, evidence_oids=())) == ["no evidence lines"]
    texts = [S.Obs(oid=o, t_obs=0, channel="diary", text="nothing here") for o in x.evidence_oids]
    assert any("does not contain" in p for p in Q.evidence_check(world, x, texts))
    good = [S.Obs(oid=o, t_obs=0, channel="diary", text="I saw a %s car" % x.gold.value) for o in x.evidence_oids]
    assert Q.evidence_check(world, x, good) == []


def test_abstain_items_are_verified_absent_and_always_have_a_trap(world, built):
    for res in built.values():
        me1 = [x for x in res.queries if x.family == "ME1"]
        assert len(me1) == round(world.cfg.queries_per_world * world.cfg.abstain_share)
        for x in me1:
            assert x.gold.kind == "unknown" and x.gold.value == "UNKNOWN" and x.evidence_oids == ()
            assert Q.slow_answers(world, x) == []
            assert len(x.gold.near_miss) >= 1                                  # near-miss trap for 100%
            assert x.tags.hard and x.tags.n_evidence == 0
            assert Q.evidence_check(world, x) == []


def test_ablated_world_cannot_solve_and_habit_days_are_gone(world, built):
    prior = world.prior("breakfast")
    for res in built.values():
        for x in res.queries:
            if x.family == "ME1":
                continue
            assert x.gold.value in Q.slow_answers(world, x)
            assert x.gold.value not in Q.slow_answers(Q.ablate_lines(world, x.evidence_oids), x)
            if x.ask == "breakfast":
                assert x.gold.value not in prior.top(3) and not x.tags.prior_answerable


def test_blind_constant_guess_is_capped_per_family(built):
    for res in built.values():
        groups = {}
        for x in res.queries:
            if x.family != "ME1":
                groups.setdefault((x.family, x.ask), []).append(x.gold.value)
        for key, vals in groups.items():
            worst = max(vals.count(v) for v in set(vals))
            assert worst <= max(1, math.floor(0.15 * len(vals) + 1e-9)), (key, len(vals), worst)
            if len(vals) >= 14:
                assert worst / len(vals) <= 0.15 + 1e-9


def test_family_sizes_follow_the_mix_when_support_is_ample():
    w = make_world(5, days=360, scale=3, queries_per_world=160)
    res = Q.build_queries_ex(w, w.cfg, "C0")
    counts = {}
    for x in res.queries:
        counts[x.family] = counts.get(x.family, 0) + 1
    assert counts["ME1"] == 13 and counts["IN4"] >= 14
    assert counts["EP4"] % 2 == 0 and counts["EP4"] >= 20
    assert 150 <= len(res.queries) <= 175
    assert res.report.requested["ME1"] == 13 and res.report.drawn["EP1"] >= counts["EP1"] - 5


def test_ask_time_cell_lag_and_per_family_delay_rules(world):
    lag = S.Cell("lag", 1.0, 0.0, 0.0, lag_days=60)
    res = Q.build_queries_ex(world, world.cfg, lag)
    for x in res.queries:
        if x.family in ("EP1", "IN1", "IN4"):
            assert x.tags.delay_days >= 60, x.family
        if x.family == "EP4":                       # a retelling line a few days later is fresher evidence
            assert x.tags.delay_days >= 55
    for x in Q.build_queries(world, world.cfg, "C0"):
        if x.family == "IN4":
            assert x.tags.delay_days >= 14 and x.tags.arousal_decile < 2
            assert {s.name for s in x.cue} >= {"shop"}
        if x.family == "IN1":
            assert x.tags.n_confusers >= world.cfg.in1_min_other_articles


def test_anchor_kinds_and_relative_cues(world):
    cfg = dataclasses.replace(world.cfg, relative_time_share=0.9, anchor_mix=0.0)
    qs = Q.build_queries(world, cfg, "C0")
    rel = [x for x in qs if x.tags.relative_time]
    assert len(rel) > 10 and all(x.tags.anchor_kind == "relative_date" and x.tags.hard for x in rel)
    for x in rel:
        names = {s.name for s in x.cue}
        assert names & {"relative_day", "relative_window"}
    cfg = dataclasses.replace(world.cfg, relative_time_share=0.0, anchor_mix=0.0)
    qs = Q.build_queries(world, cfg, "C0")
    assert not any(x.tags.relative_time for x in qs)
    assert {x.tags.anchor_kind for x in qs if x.family in ("EP1", "SE5", "EP4", "EP3c")} == {"date"}


def test_realised_enrichment_tracks_each_cell_with_ample_support():
    w = make_world(5, days=360, scale=3, queries_per_world=160)
    A_all = Q.stream_arousal(w)
    e10, e25 = {}, {}
    for name in ("C-", "C0", "C-half", "C+"):
        res = Q.build_queries_ex(w, w.cfg, name)
        assert res.report.shortfall_share <= 0.02, (name, res.report.pooled_shortfall)
        e10[name] = Q.realised_enrichment(res.queries, A_all, 0.10)
        e25[name] = Q.realised_enrichment(res.queries, A_all, 0.25)
    assert 0.8 <= e10["C0"] <= 1.2 and 0.8 <= e25["C0"] <= 1.2          # the null passes the G-ARO window
    assert abs(e10["C-half"] - 2.0) <= 0.3 and abs(e10["C+"] - 4.0) <= 0.6      # within 15% of target
    assert abs(e10["C-"] - 0.3) <= 0.075                                # a few items: granularity 1/(0.1 n)
    assert e10["C-"] < e10["C0"] < e10["C-half"] < e10["C+"]
    assert e25["C-"] < e25["C0"] < e25["C+"]


def test_thin_support_is_reported_not_hidden(world, built):
    plus = built["C+"].report
    assert plus.pooled_demand > 0 and plus.shortfall() == plus.pooled_shortfall
    assert built["C0"].report.shortfall_share <= plus.shortfall_share
    strict = dataclasses.replace(world.cfg).with_extra(quota_redistribute=0)
    res = Q.build_queries_ex(world, strict, "C0")
    assert res.report.pooled_shortfall >= built["C0"].report.pooled_shortfall
    assert all(qt.shortfall >= 0 and qt.shortfall == sum(c - t for c, t in zip(qt.counts, qt.taken))
               for qt in res.report.quotas.values())


def test_the_two_null_cells_give_the_same_queries(built):
    assert built["C0"].queries == built["C0r"].queries       # rehearsal is a world setting, not a query one


def test_cells_change_the_arousal_of_the_targets(built):
    mean = {n: sum(x.tags.target_arousal for x in r.queries if x.family != "ME1") / sum(1 for x in r.queries if x.family != "ME1")
            for n, r in built.items()}
    assert mean["C-"] < mean["C0"] < mean["C+"]


def test_build_is_deterministic_and_seeded(world, built):
    again = Q.build_queries_ex(world, world.cfg, "C+")
    assert again.queries == built["C+"].queries
    assert Q.build_queries(make_world(2), None, "C+") != list(built["C+"].queries)
    assert Q.build_queries(world, None, CELLS["C+"]) == list(built["C+"].queries)


def test_render_and_partition_are_injectable(world):
    calls = []

    def render(query, part):
        calls.append((query.qid, part))
        return "T|%s|%s" % (query.qid, part)

    qs = Q.build_queries(world, world.cfg, "C0", render=render, partition="test")
    assert all(x.text == "T|%s|test" % x.qid and x.tags.partition == "test" for x in qs)
    assert len(calls) == len(qs)


def test_choice_forks(world):
    qs = Q.build_queries(world, world.cfg, "C0")
    base = next(x for x in qs if x.family == "EP1")
    fork = Q.make_choice_fork(world, base, 4)
    assert fork.fmt == "choice" and len(fork.options) == 4 and base.gold.value in fork.options
    assert len(set(fork.options)) == 4 and fork.twin_of == base.qid and fork.cue == base.cue
    assert Q.make_choice_fork(world, base, 4) == fork                         # seeded
    assert Q.plain_question(fork, "dev").count(") ") >= 4
    me1 = next(x for x in qs if x.family == "ME1")
    assert Q.make_choice_fork(world, me1) is None
    cnt = next(x for x in qs if x.family == "EP3c")
    fk = Q.make_choice_fork(world, cnt, 4)
    assert cnt.gold.value in fk.options and all(o.isdigit() for o in fk.options)
    forked = Q.build_queries(world, world.cfg.with_extra(choice_fork_share=1.0), "C0")
    open_q = [x for x in forked if x.fmt == "open"]
    assert len(forked) > len(open_q) and {x.twin_of for x in forked if x.fmt == "choice"} <= {x.qid for x in open_q}
    assert [x.qid for x in forked] == [S.new_id("query", i) for i in range(1, len(forked) + 1)]


# ---------------------------------------------------- filter, independence, scoring from structure


def _ep1_world():
    b = WB(days=60)
    b.priors.append(Prior(slot="breakfast", values=("porridge", "croissant", "toast with jam", "fruit salad", "kippers"),
                          probs=(0.4, 0.3, 0.2, 0.06, 0.04)))
    f1, o1 = b.breakfast(10, "porridge")
    f2, o2 = b.breakfast(11, "fruit salad")
    f3, o3 = b.breakfast(12, "kippers")
    o3b = b.line(b.situation(13), [Mention(fid=f3, role="recall")],
                 [Slot(name="breakfast", value="kippers", fid=f3)], channel="chat")
    return b.build(narrator="me"), (f1, o1), (f2, o2), (f3, o3, o3b)


_BQ_N = [0]


def _bq(w, day, value, oids, fids, t_ask=None):
    _BQ_N[0] += 1
    q = mkq("breakfast", [("date", iso(w, day))], t_ask or T(30), "EP1", gold=value)
    return dataclasses.replace(q, qid="q%04d" % _BQ_N[0], evidence_oids=tuple(oids), evidence_fids=tuple(fids))


def test_filter_drops_habit_days_and_unsolvable_ablations():
    w, (f1, o1), (f2, o2), (f3, o3, o3b) = _ep1_world()
    habit = _bq(w, 10, "porridge", [o1], [f1])
    good = _bq(w, 11, "fruit salad", [o2], [f2])
    half = _bq(w, 12, "kippers", [o3], [f3])               # cites one of two lines: ablation leaves the other
    full = _bq(w, 12, "kippers", [o3, o3b], [f3])
    res = Q.structural_memory_filter(w, [habit, good, half, full], max_const_share=1.0)
    assert res.kept == (good, full)
    assert dict(res.dropped) == {habit.qid: "habit_top3", half.qid: "ablated_world_solvable"}
    kept_habit = Q.structural_memory_filter(w, [habit], max_const_share=1.0, drop_prior_answerable=False)
    assert kept_habit.kept == (habit,)
    flagged = dataclasses.replace(habit, tags=dataclasses.replace(habit.tags, prior_answerable=True))
    assert Q.structural_memory_filter(w, [flagged], max_const_share=1.0).kept == ()


def test_filter_drops_wrong_ambiguous_and_present_abstentions():
    w, (f1, o1), (f2, o2), _ = _ep1_world()
    wrong = _bq(w, 11, "kippers", [o2], [f2])
    absent = dataclasses.replace(mkq("breakfast", [("date", iso(w, 20))], T(30), "ME1", gold="UNKNOWN", kind="unknown"))
    present = dataclasses.replace(absent, cue=(Slot(name="date", value=iso(w, 11)),))
    res = Q.structural_memory_filter(w, [wrong, absent, present], max_const_share=1.0)
    assert res.kept == (absent,) and sorted(r for _, r in res.dropped) == ["gold_not_derivable", "me1_not_absent"]
    b = WB(days=30)
    b.breakfast(10, "fruit salad")
    b.breakfast(10, "kippers")
    w2 = b.build(narrator="me")
    amb = mkq("breakfast", [("date", iso(w2, 10))], T(20), gold="fruit salad")
    assert Q.structural_memory_filter(w2, [amb], max_const_share=1.0).dropped == ((amb.qid, "ambiguous"),)


def test_filter_constant_guess_cap_is_a_fixed_point():
    b = WB(days=30)
    q = mkq("visit_count", [("errand", "x")], T(20), "EP3c", gold="3", kind="count")
    w = b.build(narrator="me")
    def fake(i, value):
        return dataclasses.replace(q, qid="q%04d" % i, gold=S.Gold(kind="count", value=value, vocab_id="pool:counts"))
    # 10 identical golds: cap 1 -> 1 kept
    qs = [fake(i, "3") for i in range(10)]
    kept = Q._cap_select(Q._units(qs), 0.15, 10, 10)
    assert len(kept) == 1
    # 20 items, two values: cap 3 -> 6 -> cap 1 -> 2 (the fixed point)
    qs = [fake(i, "3" if i % 2 else "4") for i in range(20)]
    assert len(Q._cap_select(Q._units(qs), 0.15, 20, 20)) == 2
    # 8 distinct values, 3 copies each, n 24: cap 3 holds -> 24 kept
    qs = [fake(i, str(i % 8 + 1)) for i in range(24)]
    assert len(Q._cap_select(Q._units(qs), 0.15, 24, 24)) == 24
    # the cap uses the nominal size, so a smaller final set is capped by the larger cap first
    qs = [fake(i, str(i % 8 + 1)) for i in range(24)]
    assert len(Q._cap_select(Q._units(qs), 0.15, 24, 10)) == 8
    # ME1 is exempt through the public filter
    me = dataclasses.replace(q, family="ME1", ask="breakfast", cue=(Slot(name="date", value=iso(w, 20)),),
                             gold=S.Gold(kind="unknown", value="UNKNOWN", vocab_id="pool:dishes"))
    res = Q.structural_memory_filter(w, [dataclasses.replace(me, qid="q%04d" % i) for i in range(10)])
    assert len(res.kept) == 10


def test_pairs_stand_or_fall_together_under_the_cap():
    b = WB(days=30)
    base = mkq("companion", [("date", "2027-01-05")], T(20), "EP4", gold="Mara")
    def pair(i, who, colour):
        c = dataclasses.replace(base, qid="c%d" % i, gold=S.Gold(kind="entity", value=who, vocab_id="kind:person"),
                                tags=S.Tags(pair_id="s%d" % i, role="central"))
        p = dataclasses.replace(base, qid="p%d" % i, ask="vehicle_colour",
                                gold=S.Gold(kind="entity", value=colour, vocab_id="pool:colours"),
                                tags=S.Tags(pair_id="s%d" % i, role="peripheral"))
        return [c, p]
    qs = [x for i in range(10) for x in pair(i, "Mara" if i < 5 else "Imre", "red" if i % 2 else "blue")]
    units = Q._units(qs)
    assert len(units) == 10 and all(len(u) == 2 for u in units)
    kept = Q._cap_select(units, 0.5, 10, 10)             # cap 5 per value: Mara x5, Imre x5, red x5, blue x5 fits
    assert len(kept) == 10
    kept = Q._cap_select(units, 0.3, 10, 10)             # cap 3 -> at most 6 pairs -> re-capped at n=...
    assert all(len(u) == 2 for u in kept) and len(kept) <= 6


def test_gold_slow_does_not_use_the_fast_path(world, built, monkeypatch):
    qs = list(built["C0"].queries)

    def boom(*a, **k):
        raise AssertionError("gold_slow reached the fast path")

    for name in ("candidate_pool", "sample_targets", "solve_quota", "shuffled_by_decile", "build_queries_ex",
                 "_Index", "_make_query", "_first_consistent", "_try", "_shape"):
        monkeypatch.setattr(Q, name, boom)
    for x in qs:
        g = Q.gold_slow(world, x)
        assert (g.kind, g.value) == (x.gold.kind, x.gold.value)


def test_gold_slow_reads_the_lines_not_the_fact_table():
    """If a line's slot and the fact disagree the slow path follows the line (the text)."""
    b = WB(days=30)
    f = b.fact("me", "breakfast", "porridge", 10, 10)
    b.line(b.situation(10, "routine", 0.2, [f]), [Mention(fid=f, role="assert")], [Slot(name="breakfast", value="kippers", fid=f)])
    w = b.build(narrator="me")
    assert Q.slow_answers(w, mkq("breakfast", [("date", iso(w, 10))], T(20))) == ["kippers"]


def test_answering_from_structure_scores_one_and_hedges_score_zero(world, built):
    from corpus.lifesim import scorers as SC
    scorer = SC.Scorer(world)
    for res in built.values():
        for x in res.queries:
            ans = "UNKNOWN" if x.family == "ME1" else x.gold.value
            rec = scorer.score(x, ans + " CONF: 70")
            assert rec.correct and rec.score == 1.0 and rec.conf == 70 and rec.error_type == "", (x.family, ans)
            if x.family == "ME1":
                assert rec.abstained and rec.cost_weighted == 1.0
                continue
            if x.gold.near_miss:
                nm = x.gold.near_miss[0].value
                hedge = scorer.score(x, "%s or %s" % (ans, nm))
                assert not hedge.correct and hedge.hedged and hedge.error_type == "hedge"
                wrong = scorer.score(x, nm)
                assert not wrong.correct and wrong.error_type == x.gold.near_miss[0].kind
            assert not scorer.score(x, "UNKNOWN").correct
    always = [scorer.score(x, "UNKNOWN") for x in built["C0"].queries]
    share = sum(1 for x in built["C0"].queries if x.family == "ME1") / len(always)
    assert sum(r.correct for r in always) / len(always) == pytest.approx(share)
    assert sum(r.cost_weighted for r in always) / len(always) == pytest.approx(share)


def test_check_query_support_reports_a_world_that_cannot_be_asked():
    empty = World(seed=0, cfg=TierCfg.for_tier("L0"))
    problems = Q.check_query_support(empty)
    assert any("narrator" in p for p in problems) and sum("family" in p for p in problems) == 8
    assert Q.build_queries(empty, None, "C0") == []


def test_pool_digest_changes_with_the_structure(world):
    gone = next(f for f in world.facts if f.pred == "breakfast")
    changed = dataclasses.replace(
        world, facts=tuple(f for f in world.facts if f.fid != gone.fid),
        situations=tuple(dataclasses.replace(s, facts=tuple(x for x in s.facts if x != gone.fid)) for s in world.situations),
        obs_specs=tuple(dataclasses.replace(o, mentions=tuple(m for m in o.mentions if m.fid != gone.fid),
                                            slots=tuple(sl for sl in o.slots if sl.fid != gone.fid))
                        for o in world.obs_specs))
    assert Q.candidate_pool(changed).digest() != Q.candidate_pool(world).digest()


# ---------------------------------------- the predicate names and story entities of world.py


def test_pool_reads_story_entities_and_the_world_builders_other_predicate_names():
    b = WB(days=80)
    flood = b.entity("story", "flood in Verdton")
    closure = b.entity("story", "road closure in Karmont")             # a two-word story kind
    shop = b.entity("shop", "Kalmer Pharmacy")
    street = b.entity("street", "Tisbo Street", aliases=("Tisbo",))
    b.breakfast(2, "porridge")
    for day, story, colour in ((10, flood, "red"), (12, closure, "green")):
        rs = b.fact("me", "read_story", story, day, src="read")
        vf = b.fact(story, "vehicle_colour", colour, day, src="read")
        name = b.ent_name(story)
        b.line(b.situation(day, "article", 0.2, [rs, vf]), [Mention(fid=rs, role="assert"), Mention(fid=vf, role="assert")],
               [Slot(name="story", value=name), Slot(name="story", value=name, fid=rs),
                Slot(name="vehicle_colour", value=colour, fid=vf)], channel="article")
    for i in range(30):
        b.filler(1 + i, A=0.1 + i / 40.0)
    cf = b.fact(shop, "closing_time", "18:00", 20)
    sf = b.fact(shop, "on_street", street, 20)
    b.line(b.situation(20, "remark", 0.0, [cf, sf]), [Mention(fid=cf, role="assert"), Mention(fid=sf, role="assert")],
           [Slot(name="shop", value="Kalmer Pharmacy"), Slot(name="closing_time", value="18:00", fid=cf)], channel="dialogue")
    visits = [b.errand(d, "dentist")[0] for d in (5, 6)]
    for fid in visits:
        w0 = b.facts.index(next(f for f in b.facts if f.fid == fid))
        b.facts[w0] = dataclasses.replace(b.facts[w0], pred="errand_visit")
    w = b.build(narrator="me")
    pool = Q.candidate_pool(w)
    in1 = {c.get("story_kind"): c for c in pool.of("IN1")}
    assert set(in1) == {"flood", "road closure"}
    assert (in1["flood"].get("city"), in1["flood"].value) == ("Verdton", "red")
    assert (in1["road closure"].get("city"), in1["road closure"].value) == ("Karmont", "green")
    assert Q.story_parts("flood in Verdton") == ("flood", "Verdton")
    assert Q.story_parts("road closure in Karmont") == ("road closure", "Karmont")
    assert Q.story_parts("a quiet afternoon") == ("", "") and Q.story_parts("flood in ") == ("", "")
    in4 = pool.of("IN4")
    assert len(in4) == 1 and in4[0].get("street") == "Tisbo Street" and in4[0].get("shop") == "Kalmer Pharmacy"
    assert sorted(c.value for c in pool.of("EP3c")) == ["1", "1", "2"]
    ask = lambda cue: Q.slow_answers(w, mkq("vehicle_colour", cue, T(30), "IN1"))       # noqa: E731
    assert ask([("story_kind", "road closure"), ("city", "Karmont")]) == ["green"]
    assert ask([("story_kind", "flood")]) == ["red"] and ask([("city", "Karmont")]) == ["green"]
    assert ask([("story_kind", "flood"), ("city", "Karmont")]) == []
    cnt = Q.slow_answers(w, mkq("visit_count", [("errand", "dentist"), ("window_from", iso(w, 1)),
                                                ("window_to", iso(w, 9))], T(30), "EP3c", kind="count"))
    assert cnt == ["2"]


def test_peripheral_slot_named_car_colour_is_asked_by_that_name():
    b = WB(days=60)
    mara = b.entity("person", "Mara")
    b.breakfast(2, "porridge")
    cf = b.fact("me", "companion", mara, 20, centrality=0.9)
    pf = b.fact("car020", "car_colour", "silver", 20, centrality=0.1)
    b.line(b.situation(20, "major", 0.6, [cf, pf]), [Mention(fid=cf, role="assert"), Mention(fid=pf, role="assert")],
           [Slot(name="companion", value="Mara", fid=cf), Slot(name="car_colour", value="silver", fid=pf)])
    w = b.build(narrator="me")
    (c,) = Q.candidate_pool(w).of("EP4")
    assert c.get("ppred") == "car_colour"
    assert Q.slow_answers(w, mkq("car_colour", [("date", iso(w, 20))], T(40), "EP4")) == ["silver"]
    assert Q.slow_answers(w, mkq("vehicle_colour", [("date", iso(w, 20))], T(40), "EP4")) == []


# ------------------------------------------------------------ real worlds from world.py

try:
    from corpus.lifesim import world as WORLD_MOD  # noqa: E402
except Exception:                                    # pragma: no cover - another builder's module
    WORLD_MOD = None


@pytest.mark.skipif(WORLD_MOD is None, reason="world.py is not importable")
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_worlds_from_the_world_builder_support_every_family(seed):
    from corpus.lifesim import scorers as SC
    w = WORLD_MOD.build_world(seed, TierCfg.for_tier("L1"))
    assert Q.check_query_support(w) == []
    res = Q.build_queries_ex(w, w.cfg, "C0")
    qs = res.queries
    assert len(qs) >= 150 and {x.family for x in qs} == set(Q.FAMILY_ORDER)
    assert res.report.dropped(reason="mismatch") == 0 and res.report.shortfall_share <= 0.03
    scorer = SC.Scorer(w)
    for x in qs:
        g = Q.gold_slow(w, x)
        assert (g.kind, g.value) == (x.gold.kind, x.gold.value)
        assert Q.evidence_check(w, x) == []
        assert scorer.score(x, "UNKNOWN" if x.family == "ME1" else x.gold.value).correct
    assert 0.8 <= Q.realised_enrichment(qs, Q.stream_arousal(w)) <= 1.2
    assert res.pool.digest() == Q.candidate_pool(w).digest()


@pytest.mark.skipif(WORLD_MOD is None, reason="world.py is not importable")
def test_real_world_questions_render_with_the_real_question_frames():
    try:
        from corpus.lifesim import verbalise as VB
    except Exception:                                # pragma: no cover
        pytest.skip("verbalise.py is not importable")
    w = WORLD_MOD.build_world(3, TierCfg.for_tier("L1"))
    qs = Q.build_queries(w, w.cfg, "C0", render=VB.render_question)
    assert qs and all(x.text and all(s.value in x.text for s in x.cue) for x in qs)
    assert len({x.text for x in qs}) > len(qs) * 0.9
    assert all("CONF" in x.text for x in qs)


# ------------------------------------------------- boundaries found by mutating the module


def test_line_arousal_halves_pure_retellings_only():
    b = WB(days=30)
    f = b.fact("me", "breakfast", "porridge", 5, 5)
    sl = [Slot(name="breakfast", value="porridge", fid=f)]
    o_assert = b.line(b.situation(5, "routine", 0.8, [f]), [Mention(fid=f, role="assert")], sl)
    o_recall = b.line(b.situation(6, "minor", 0.6), [Mention(fid=f, role="recall")], sl, channel="chat")
    o_mixed = b.line(b.situation(7, "minor", 0.6), [Mention(fid=f, role="recall"), Mention(fid=f, role="assert")], sl)
    o_bare = b.filler(8, 0.4)
    w = b.build()
    spec = {o.oid: o for o in w.obs_specs}
    assert Q.line_arousal(w, spec[o_assert]) == 0.8 and Q.line_arousal(w, spec[o_recall]) == 0.3
    assert Q.line_arousal(w, spec[o_mixed]) == 0.6 and Q.line_arousal(w, spec[o_bare]) == 0.4
    quarter = dataclasses.replace(w, cfg=dataclasses.replace(w.cfg, retell_a_factor=0.25))
    assert Q.line_arousal(quarter, spec[o_recall]) == 0.15
    assert Q.line_arousal(w, dataclasses.replace(spec[o_assert], sid="s99999")) == 0.0
    assert Q.stream_arousal(w) == [Q.line_arousal(w, o) for o in w.obs_specs]


def test_pool_in4_decile_boundary_is_exact():
    b = WB(days=80)
    for i in range(1, 99):
        b.filler(1 + i % 70, A=i / 100.0)
    shops = [b.entity("shop", "Shop%d Pharmacy" % i) for i in range(3)]
    for k, a in enumerate((0.095, 0.145, 0.205)):
        b.remark(10 + k, shops[k], "Shop%d Pharmacy" % k, "Tisbo Street", "18:00", A=a)
    w = b.build()
    srt = sorted(Q.stream_arousal(w))
    assert [Q.decile_of(a, srt) for a in (0.095, 0.145, 0.205)] == [0, 1, 2]
    assert sorted(c.get("shop") for c in Q.candidate_pool(w).of("IN4")) == ["Shop0 Pharmacy", "Shop1 Pharmacy"]
    wider = dataclasses.replace(w.cfg, in4_low_deciles=3)
    assert len(Q.candidate_pool(w, wider).of("IN4")) == 3


def test_evidence_must_precede_the_question_strictly():
    w, (f1, o1), (f2, o2), _ = _ep1_world()
    at = _bq(w, 11, "fruit salad", [o2], [f2], t_ask=T(11, 600))
    assert any("not before" in p for p in Q.evidence_check(w, at))
    assert Q.evidence_check(w, _bq(w, 11, "fruit salad", [o2], [f2], t_ask=T(11, 601))) == []


def test_in4_share_is_compensated_in_the_enrichment_of_the_other_families(built):
    res = built["C0"]
    req = res.report.requested
    s_fixed = req["IN4"] / sum(v for f, v in req.items() if f != "ME1")
    assert s_fixed > 0.05
    for fam in ("EP1", "IN1"):
        assert res.report.quotas[fam].e_target == pytest.approx(1.0 / (1.0 - s_fixed))


def test_pool_identity_facts_must_be_stated_exactly_once():
    b = WB(days=40)
    b.breakfast(2, "porridge")
    p1, p2 = b.entity("person", "Mara"), b.entity("person", "Dana")
    f1 = b.fact(p1, "relation", "colleague", 3)
    b.line(b.situation(3, "minor", 0.1, [f1]), [Mention(fid=f1, role="assert")],
           [Slot(name="relation", value="colleague", fid=f1)])
    f2 = b.fact(p2, "relation", "cousin", 4)
    b.line(b.situation(4, "minor", 0.1, [f2]), [Mention(fid=f2, role="assert")],
           [Slot(name="relation", value="cousin", fid=f2)])
    b.line(b.situation(9), [Mention(fid=f2, role="recall")], [Slot(name="relation", value="cousin", fid=f2)], channel="chat")
    w = b.build(narrator="me")
    assert {c.key for c in Q.candidate_pool(w).of("SE4")} == {"SE4#" + f1}


def test_slow_relation_expires_with_its_validity():
    b = WB(days=60)
    mara = b.entity("person", "Mara")
    b.breakfast(2, "porridge")
    rf = b.fact(mara, "relation", "colleague", 3, vto=20)
    b.line(b.situation(3, "minor", 0.1, [rf]), [Mention(fid=rf, role="assert")],
           [Slot(name="relation", value="colleague", fid=rf)])
    w = b.build(narrator="me")
    assert Q.slow_answers(w, mkq("relation", [("person", "Mara")], T(10), "SE4")) == ["colleague"]
    assert Q.slow_answers(w, mkq("relation", [("person", "Mara")], T(30), "SE4")) == []


def test_pool_ep1_excludes_multi_day_and_told_breakfasts():
    b = WB(days=40)
    f1 = b.fact("me", "breakfast", "porridge", 5, 7)                 # valid for three days: not a one-day episode
    b.line(b.situation(5, "routine", 0.2, [f1]), [Mention(fid=f1, role="assert")],
           [Slot(name="breakfast", value="porridge", fid=f1)])
    f2 = b.fact("me", "breakfast", "kippers", 9, 9, src="told")
    b.line(b.situation(9, "routine", 0.2, [f2]), [Mention(fid=f2, role="assert")],
           [Slot(name="breakfast", value="kippers", fid=f2)])
    f3, _ = b.breakfast(11, "fruit salad")
    w = b.build(narrator="me")
    assert [c.key for c in Q.candidate_pool(w).of("EP1")] == [f3]


def test_try_rejects_a_candidate_whose_checks_fail():
    b = WB(days=70)
    for d in range(2, 20):
        b.breakfast(d, V.DISHES[d])
    f_a, _ = b.breakfast(30, "porridge")
    b.breakfast(30, "porridge")                                       # the same dish stated again: not memory dependent
    f_c, _ = b.breakfast(31, "kippers")
    w = b.build(narrator="me")
    pool = {c.key: c for c in Q.candidate_pool(w).of("EP1")}
    report = Q.BuildReport()
    ctx = Q._Ctx(w, Q._Index(w), CELLS["C0"], "dev", report, False)
    st = Q._FamState("EP1", 10, 3, R.stream(1, "try"))
    assert Q._try(ctx, st, pool[f_a]) is False
    assert report.dropped("EP1", "ablated_world_solvable") == 1 and st.units == []
    assert Q._try(ctx, st, pool[f_c]) is True and len(st.units) == 1
    assert st.units[0][0].gold.value == "kippers" and st.value_counts == {("EP1", "breakfast", "kippers"): 1}
    st.cap = 1                                                         # the cap is per (family, ask, value)
    assert Q._try(ctx, st, pool[f_c]) is False and report.dropped("EP1", "constant_guess_cap") == 1


def test_ep4_confusers_are_the_other_events_within_a_week():
    b = WB(days=80, delay_min_days=10)
    people = {n: b.entity("person", n) for n in ("Mara", "Imre", "Dana")}
    b.breakfast(2, "porridge")
    b.event(10, people["Mara"], "Mara", "blue", 0.6)
    b.event(14, people["Imre"], "Imre", "red", 0.5)
    b.event(40, people["Dana"], "Dana", "green", 0.4)
    w = b.build(narrator="me")
    cand = next(c for c in Q.candidate_pool(w).of("EP4") if c.day == 10)
    attempts = Q._build_ep4(Q._Index(w), CELLS["C0"], cand, R.stream(3, "t"), "dev")
    central = next(x for x in attempts if x.tags.role == "central")
    peripheral = next(x for x in attempts if x.tags.role == "peripheral")
    assert central.tags.n_confusers == 1 and [n.value for n in central.gold.near_miss] == ["Imre"]
    assert peripheral.tags.n_confusers == 1 and [n.value for n in peripheral.gold.near_miss] == ["red"]
    assert central.gold.value == "Mara" and peripheral.gold.value == "blue"


def test_delay_bins_are_chosen_uniformly_and_respect_the_range():
    rng = R.stream(5, "bins")
    counts = [0] * 5
    seen = set()
    for _ in range(20000):
        d = Q._pick_delay(rng, 1, 400)
        counts[S.delay_bin(d)] += 1
        seen.add(d)
    assert all(abs(c / 20000 - 0.2) < 0.02 for c in counts), counts
    assert {1, 3, 4, 14, 15, 60, 61, 180, 181} <= seen            # both edges of every bin are reachable
    assert Q._pick_delay(rng, 5, 5) == 5 and Q._pick_delay(rng, 10, 9) is None
    assert all(7 <= Q._pick_delay(rng, 7, 20) <= 20 for _ in range(200))
    only_late = {S.delay_bin(Q._pick_delay(rng, 100, 400)) for _ in range(400)}
    assert only_late == {3, 4}


def test_choice_forks_do_not_always_put_the_gold_first():
    w = make_world(1)
    qs = [x for x in Q.build_queries(w, w.cfg, "C0") if x.family in ("EP1", "IN1", "EP4")]
    pos = []
    for x in qs:
        fk = Q.make_choice_fork(w, x, 4)
        if fk is not None:
            pos.append(fk.options.index(x.gold.value))
    assert len(pos) > 30 and set(pos) == {0, 1, 2, 3}
    assert max(pos.count(i) for i in range(4)) < 0.5 * len(pos)


def test_enrichment_helpers_on_hand_computed_cases():
    b = WB(days=30)
    oids = [b.filler(1 + i % 25, A=i / 20.0) for i in range(20)]
    w = b.build()
    low, high = oids[:2], oids[18:]
    x = mkq("breakfast", [], T(29))
    x = dataclasses.replace(x, evidence_oids=tuple(low + high))
    # lines 18 and 19 are the top tenth (mid-rank >= 0.9): 2 of 4 evidence lines, divided by 0.10
    assert Q.evidence_line_enrichment(w, [x], 0.10) == pytest.approx(5.0)
    assert Q.evidence_line_enrichment(w, [x], 0.25) == pytest.approx((2 / 4) / 0.25)
    assert Q.evidence_line_enrichment(w, [mkq("breakfast", [], T(29))]) == 0.0
    A_all = Q.stream_arousal(w)
    t = lambda a, fam="EP1": dataclasses.replace(mkq("breakfast", [], T(29), fam), tags=S.Tags(target_arousal=a))     # noqa: E731
    qs = [t(0.95), t(0.92), t(0.5), t(0.1), t(0.0, "ME1")]            # ME1 carries no target
    assert Q.realised_enrichment(qs, A_all, 0.10) == pytest.approx((2 / 4) / 0.10)
    assert Q.realised_enrichment(qs, A_all, 0.50) == pytest.approx((3 / 4) / 0.50)
    assert Q.realised_enrichment([t(0.0, "ME1")], A_all) == 0.0


def test_sample_targets_orders_by_the_achieved_counts_when_support_is_thin():
    A_all = [i / 999.0 for i in range(1000)]
    pool = [_Cand("c%04d" % i, i / 999.0) for i in range(1000) if not (i < 100 and i % 50 != 0)]   # decile 0 keeps 2
    d = Q.sample_targets(pool, 100, CELLS["C0"], 1, A_all, "thin")
    assert d.quota.counts[0] == 10 and d.quota.taken[0] == 2 and d.shortfall == 8
    total = sum(d.quota.taken)
    for m in (20, 50):
        assert abs(d.deciles[:m].count(0) - m * 2 / total) <= 1.5, m


def test_wanted_counts_split_the_query_budget():
    for total in range(20, 401, 7):
        for share in (0.05, 0.08, 0.15):
            cfg = dataclasses.replace(TierCfg.for_tier("L1"), queries_per_world=total, abstain_share=share)
            want = Q.wanted_counts(cfg)
            raw = Q._split_counts(total - round(total * share), list(dict(cfg.family_mix).items()))
            assert want["ME1"] == round(total * share) and want["EP4"] % 2 == 0
            assert want["EP4"] in (raw["EP4"], raw["EP4"] + 1)
            assert all(want[f] == raw[f] for f in raw if f != "EP4")
            assert sum(want.values()) - want["ME1"] - (want["EP4"] - raw["EP4"]) == total - want["ME1"]


def test_ep4_central_threshold_is_inclusive_and_errands_must_be_lived():
    b = WB(days=60)
    mara = b.entity("person", "Mara")
    b.breakfast(2, "porridge")
    cf, pf, _ = b.event(10, mara, "Mara", "blue", 0.6)
    b.facts[b.facts.index(next(f for f in b.facts if f.fid == cf))] = dataclasses.replace(
        next(f for f in b.facts if f.fid == cf), centrality=0.5)
    f1, _ = b.errand(20, "dentist")
    told = b.fact("me", "errand_visit", "dentist", 21, 21, src="told")
    b.line(b.situation(21, "minor", 0.2, [told]), [Mention(fid=told, role="assert")],
           [Slot(name="errand", value="dentist", fid=told)])
    w = b.build(narrator="me")
    pool = Q.candidate_pool(w)
    assert [c.day for c in pool.of("EP4")] == [10]                      # centrality 0.5 counts as central
    assert [c.value for c in pool.of("EP3c")] == ["1"] and pool.of("EP3c")[0].fids == (f1,)
    stricter = dataclasses.replace(w.cfg).with_extra(central_min_centrality=0.6)
    assert Q.candidate_pool(w, stricter).of("EP4") == ()


def test_me1_trap_types_are_interleaved_and_trips_use_the_trip_companion_predicate():
    class C:
        def __init__(self, key, typ):
            self.key, self._t = key, typ

        def get(self, name, default=""):
            return self._t if name == "type" else default

    cands = [C("%s%02d" % (t, i), t) for t in ("breakfast", "shop", "trip") for i in range(6)]
    order = Q._me1_order(R.stream(1, "me1"), cands)
    assert len(order) == 18 and len({c.key for c in order}) == 18
    assert [c._t for c in order[:8]] == ["breakfast", "shop", "trip", "breakfast"] * 2
    assert [c.key for c in order] == [c.key for c in Q._me1_order(R.stream(1, "me1"), list(reversed(cands)))]
    only = Q._me1_order(R.stream(1, "me1"), [C("a", "breakfast"), C("b", "weird"), C("c", "breakfast")])
    assert sorted(c.key for c in only) == ["a", "b", "c"]            # an unknown type is still visited
    b = WB(days=60)
    b.breakfast(2, "porridge")
    away, never = b.entity("city", "Verdton"), b.entity("city", "Dorndam")
    vf = b.fact("me", "visited", away, 20, 23)
    cf = b.fact("me", "trip_companion", b.entity("person", "Imre"), 20, 23, centrality=0.7)
    b.line(b.situation(20, "trip", 0.3, [vf, cf]), [Mention(fid=vf, role="assert"), Mention(fid=cf, role="assert")],
           [Slot(name="visited", value="Verdton", fid=vf), Slot(name="travel_companion", value="Imre", fid=cf)])
    w = b.build(narrator="me")
    assert Q.slow_answers(w, mkq("companion", [("city", "Verdton")], T(40), "ME1")) == ["Imre"]
    assert Q.slow_answers(w, mkq("companion", [("city", "Dorndam")], T(40), "ME1")) == []
    assert [c.get("city") for c in Q.candidate_pool(w).of("ME1") if c.get("type") == "trip"] == ["Dorndam"]
    cand = next(c for c in Q.candidate_pool(w).of("ME1") if c.get("type") == "trip")
    (qq,) = Q._build_me1(Q._Index(w), CELLS["C0"], cand, R.stream(2, "t"), "dev")
    assert qq.gold.kind == "unknown" and [n.value for n in qq.gold.near_miss] == ["Imre"] and qq.ask == "companion"
    assert [s.value for s in qq.cue] == ["Dorndam"]


@pytest.mark.skipif(WORLD_MOD is None, reason="world.py is not importable")
def test_false_premise_items_of_real_worlds_use_more_than_one_trap_type():
    asks = set()
    for seed in (0, 1, 2):
        w = WORLD_MOD.build_world(seed, TierCfg.for_tier("L1"))
        asks |= {x.ask for x in Q.build_queries(w, w.cfg, "C0") if x.family == "ME1"}
    assert {"breakfast", "closing_time"} <= asks
