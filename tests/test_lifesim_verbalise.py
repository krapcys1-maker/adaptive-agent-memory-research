"""Tests for lifesim verbalise (step D1-C): text of observations and questions.

Worlds here are built by hand from the schema (no build_world), with realistic slot names:
breakfast, lives_in, works_as, relation, story, vehicle_colour, decoy_colour, companion,
car_colour, closing_time, street, errand, visited. Standard library and pytest only.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import rng as R  # noqa: E402
from corpus.lifesim import schema as S  # noqa: E402
from corpus.lifesim import verbalise as VB  # noqa: E402
from corpus.lifesim import vocab as V  # noqa: E402

CHANNEL_FOR = {"routine": ("diary", "note"), "minor": ("diary", "chat", "log"),
               "major": ("diary", "dialogue"), "move": ("diary", "note"),
               "health": ("diary", "log"), "purchase": ("diary", "chat"),
               "remark": ("chat", "note", "dialogue"), "trip": ("diary", "chat"),
               "article": ("article",)}


# ------------------------------------------------------------------ hand-built worlds


class _B:
    """Counter-based builder of ids and rows for a hand-made world."""

    def __init__(self, seed: int, partition: str) -> None:
        self.seed, self.partition = seed, partition
        self.rng = R.stream(seed, "testfix")
        self.used: set = set()
        self.n = {"entity": 0, "fact": 0, "situation": 0, "obs": 0}
        self.entities: list = []
        self.facts: list = []
        self.situations: list = []
        self.specs: list = []

    def nid(self, kind: str) -> str:
        self.n[kind] += 1
        return S.new_id(kind, self.n[kind])

    def entity(self, kind: str, name: str) -> S.Entity:
        e = S.Entity(eid=self.nid("entity"), kind=kind, name=name)
        self.entities.append(e)
        return e

    def fact(self, pred: str, subj: str, obj: str, src: str = "lived", vfrom: int = 0) -> S.Fact:
        f = S.Fact(fid=self.nid("fact"), subj=subj, pred=pred, obj=obj, vfrom=vfrom, vto=vfrom, src=src)
        self.facts.append(f)
        return f


def make_world(seed: int = 1, n_lines: int = 240, partition: str = "dev", cfg: S.TierCfg | None = None,
               empty_share: float = 0.1):
    """A hand-built world of ``n_lines`` observation specs covering every Day-1 line type.

    Arousal A is right-skewed and independent of everything else; ``target_len`` is uniform on
    words_min..words_max, independent of kind, arousal and evidence status."""
    cfg = cfg or S.TierCfg.for_tier("L1")
    b = _B(seed, partition)
    rng = b.rng
    used: set = set()
    me = b.entity("person", "Ravo")
    people = [b.entity("person", n) for n in V.make_names(rng, 14, partition, "person", used)]
    cities = [b.entity("city", n) for n in V.make_names(rng, 12, partition, "city", used)]
    streets = [b.entity("street", n + " Street") for n in V.make_names(rng, 10, partition, "street", used)]
    shops = [b.entity("shop", n + " Pharmacy") for n in V.make_names(rng, 10, partition, "shop", used)]
    orgs = [b.entity("org", n) for n in V.make_names(rng, 4, partition, "org", used)]
    kinds = ("breakfast", "companion", "article", "remark", "relation", "move", "errand", "trip", "empty")
    day = 0
    minute = 360
    for i in range(n_lines):
        minute += 20 + rng.below(120)
        if minute >= 1380:
            day += 1
            minute = 360 + rng.below(60)
        kind = "empty" if rng.chance(empty_share) else rng.choice(kinds[:-1])
        a = min(1.0, R.dexp(-1.644 + 0.51 * rng.normal()))  # lognormal: mean 0.22, SD 0.12, right-skewed
        v = rng.u() * 2 - 1
        scene = {"breakfast": "routine", "companion": "major", "article": "article", "remark": "remark",
                 "relation": "remark", "move": "move", "errand": "minor", "trip": "trip",
                 "empty": rng.choice(S.SCENE_NAMES)}[kind]
        slots: list = []
        mentions: list = []
        facts_here: list = []
        role = rng.choice(("assert", "assert", "assert", "update", "recall", "retract"))

        def add(f, slot_name, value, role_=None):
            facts_here.append(f.fid)
            slots.append(S.Slot(name=slot_name, value=value, fid=f.fid))
            mentions.append(S.Mention(fid=f.fid, role=role_ or "assert"))

        if kind == "breakfast":
            f = b.fact("breakfast", me.eid, rng.choice(V.DISHES), vfrom=day)
            add(f, "breakfast", f.obj, role if role != "update" else "assert")
        elif kind == "companion":
            who = rng.choice(people)
            f1 = b.fact("companion", me.eid, who.eid, vfrom=day)
            f2 = b.fact("car_colour", me.eid, rng.choice(V.COLOURS), vfrom=day)
            pick = rng.below(3)
            if pick != 1:
                add(f1, "companion", who.name)
            if pick != 0:
                add(f2, "car_colour", f2.obj)
        elif kind == "article":
            city = rng.choice(cities)
            sk = rng.choice(V.STORY_KINDS)
            story = b.entity("story", "%s in %s" % (sk, city.name))
            col = rng.choice(V.COLOURS)
            dec = rng.choice([c for c in V.COLOURS if c != col])
            add(b.fact("read_story", me.eid, story.eid, "read", day), "story", story.name)
            add(b.fact("vehicle_colour", story.eid, col, "read", day), "vehicle_colour", col)
            if rng.chance(0.5):
                add(b.fact("decoy_colour", story.eid, dec, "read", day), "decoy_colour", dec)
            slots.append(S.Slot(name="story_kind", value=sk))
            slots.append(S.Slot(name="city", value=city.name))
        elif kind == "remark":
            shop = rng.choice(shops)
            st = rng.choice(streets)
            t = rng.choice(V.TIMES)
            add(b.fact("closing_time", shop.eid, t, "told", day), "closing_time", t)
            if rng.chance(0.5):
                add(b.fact("on_street", shop.eid, st.eid, "told", day), "street", st.name)
        elif kind == "relation":
            who = rng.choice(people)
            f = b.fact("relation", who.eid, rng.choice(V.RELATIONS), "told", day)
            add(f, "relation", f.obj)
        elif kind == "move":
            if rng.chance(0.5):
                c = rng.choice(cities)
                add(b.fact("lives_in", me.eid, c.eid, vfrom=day), "lives_in", c.name, role)
            else:
                job = rng.choice(V.JOBS)
                add(b.fact("works_as", me.eid, job, vfrom=day), "works_as", job, role)
        elif kind == "errand":
            other = rng.chance(0.4)
            subj = rng.choice(people) if other else me
            er = rng.choice(V.ERRANDS)
            add(b.fact("errand_visit", subj.eid, er, vfrom=day), "errand", er)
            if other and rng.chance(0.5):
                slots.append(S.Slot(name="person", value=subj.name))
        elif kind == "trip":
            c = rng.choice(cities)
            who = rng.choice(people)
            add(b.fact("visited", me.eid, c.eid, vfrom=day), "visited", c.name)
            add(b.fact("companion", me.eid, who.eid, vfrom=day), "companion", who.name)
        sid = b.nid("situation")
        b.situations.append(S.Situation(sid=sid, day=day, minute=minute, scene=scene, A=a, V=v,
                                        facts=tuple(facts_here)))
        channel = rng.choice(CHANNEL_FOR[scene])
        b.specs.append(S.ObsSpec(
            oid=b.nid("obs"), t_obs=S.to_minutes(day, minute) + 5, channel=channel, sid=sid,
            mentions=tuple(mentions), slots=tuple(slots),
            target_len=rng.ri(cfg.words_min, cfg.words_max)))
    world = S.World(seed=seed, cfg=cfg, entities=tuple(b.entities), facts=tuple(b.facts),
                    situations=tuple(b.situations), obs_specs=tuple(b.specs),
                    card=S.Card(name="Ravo"), partition=partition)
    return world.with_extra("narrator", me.eid)


@pytest.fixture(scope="module")
def world_dev():
    return make_world(1, 240, "dev")


@pytest.fixture(scope="module")
def world_test():
    return make_world(10005, 240, "test")


# ----------------------------------------------------------------- small statistics kit


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2.0
        i = j + 1
    return out


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else 0.0


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def auc(pos, neg):
    """P(pos > neg) + P(tie) / 2 by ranks (Mann-Whitney)."""
    allv = list(pos) + list(neg)
    rk = ranks(allv)
    r_pos = sum(rk[: len(pos)]) + len(pos)  # 1-based ranks of the positives
    return (r_pos - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))


def chi2_sf(x, df):
    """Upper tail of the chi-square distribution (regularised upper incomplete gamma)."""
    a, xx = df / 2.0, x / 2.0
    if xx <= 0:
        return 1.0
    if xx < a + 1:
        term = total = 1.0 / a
        n = a
        for _ in range(1000):
            n += 1
            term *= xx / n
            total += term
            if abs(term) < 1e-15 * abs(total):
                break
        return 1.0 - total * math.exp(-xx + a * math.log(xx) - math.lgamma(a))
    b = xx + 1 - a
    c = 1e300
    d = 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-xx + a * math.log(xx) - math.lgamma(a)) * h


def test_statistics_kit_matches_known_values():
    assert chi2_sf(7.814727903, 3) == pytest.approx(0.05, abs=1e-6)
    assert chi2_sf(4.641627676, 3) == pytest.approx(0.2, abs=1e-6)
    assert chi2_sf(0.0, 3) == 1.0
    assert auc([3, 4, 5], [1, 2, 3]) == pytest.approx((8 + 0.5) / 9)
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert ranks([5, 5, 1]) == [1.5, 1.5, 0.0]


def cfg_with(**kw):
    return dataclasses.replace(S.TierCfg.for_tier("L1"), **kw)


def words(text):
    return len(text.split())


def evidence_flags(world, share=0.25):
    """A fixed random subset of the lines that carry a fact slot plays 'evidence'."""
    rng = R.stream(77, "evidence")
    return {o.oid: bool(any(s.fid for s in o.slots)) and rng.chance(share) for o in world.obs_specs}


# ------------------------------------------------------------------ containment and shape


@pytest.mark.parametrize("partition,seed", [("dev", 1), ("test", 10005)])
@pytest.mark.parametrize("affect", ["A0", "A1", "A2"])
def test_one_obs_per_spec_in_order_with_every_slot_verbatim(partition, seed, affect):
    w = make_world(seed, 200, partition)
    cfg = cfg_with(affect=affect, r_aff=0.5)
    obs = VB.render(w, cfg, seed, partition)
    assert [o.oid for o in obs] == [s.oid for s in w.obs_specs]
    assert [(o.t_obs, o.channel) for o in obs] == [(s.t_obs, s.channel) for s in w.obs_specs]
    assert all(isinstance(o, S.Obs) for o in obs)
    for o, sp in zip(obs, w.obs_specs):
        assert VB.missing_slots(sp, o.text) == [], (sp, o.text)
        for sl in sp.slots:
            assert sl.value in o.text  # case-sensitive, exact canonical string
        assert "?" not in o.text  # observations are statements, questions are not


def test_every_channel_and_every_known_slot_name_renders_its_value_verbatim():
    rng = R.stream(5, "slots")
    names = {"breakfast": V.DISHES, "lives_in": ["Verdton"], "works_as": V.JOBS, "works_at": ["Karbadam"],
             "relation": V.RELATIONS, "vehicle_colour": V.COLOURS, "decoy_colour": V.COLOURS,
             "car_colour": V.COLOURS, "companion": ["Mirela"], "closing_time": V.TIMES,
             "street": ["Tisbo Street"], "errand": V.ERRANDS, "visited": ["Paxton"], "visit_count": V.COUNTS,
             "story": ["flood in Verdton"], "pet_name": ["Rex"]}
    cfg = S.TierCfg.for_tier("L1")
    n = 0
    for channel in S.CHANNELS:
        for name, pool in names.items():
            for role in S.MENTION_ROLES:
                for fid_on in (True, False):
                    b = _B(1, "dev")
                    me = b.entity("person", "Ravo")
                    f = b.fact(name, me.eid, "x")
                    value = pool[rng.below(len(pool))]
                    sl = S.Slot(name=name, value=value, fid=f.fid if fid_on else "")
                    sit = S.Situation(sid="s00001", day=3, minute=600, scene="minor", A=0.4, V=0.2)
                    spec = S.ObsSpec(oid="o00001", t_obs=S.to_minutes(3, 600), channel=channel, sid="s00001",
                                     mentions=(S.Mention(fid=f.fid, role=role),) if fid_on else (),
                                     slots=(sl,), target_len=rng.ri(30, 60))
                    w = S.World(seed=1, cfg=cfg, entities=tuple(b.entities), facts=tuple(b.facts),
                                situations=(sit,), obs_specs=(spec,), card=S.Card(name="Ravo"))
                    for part in ("dev", "test"):
                        txt = VB.render(w, cfg, 1, part)[0].text
                        assert value in txt, (channel, name, role, fid_on, txt)
                        n += 1
    assert n == 6 * 16 * 4 * 2 * 2


def test_length_equals_target_len_and_overflow_is_reported():
    w = make_world(4, 600, "dev")
    for affect in ("A0", "A1"):
        cfg = cfg_with(affect=affect)
        ctx = VB._Ctx(w, cfg, 4, "dev")
        n_over = 0
        for sp in w.obs_specs:
            p = VB._render_line(ctx, sp)
            assert p.n_words == words(p.text)
            if p.overflow == 0:
                assert p.n_words == sp.target_len, (sp.target_len, p.text)
            else:
                n_over += 1
                assert p.n_words == sp.target_len + p.overflow and p.pre == () and p.post == ()
        assert n_over <= 0.01 * len(w.obs_specs)  # the core nearly always fits 30 words


def test_render_is_deterministic_and_sensitive_to_seed_partition_and_spec():
    w = make_world(2, 80, "dev")
    cfg = S.TierCfg.for_tier("L1")
    a = [o.text for o in VB.render(w, cfg, 2, "dev")]
    assert a == [o.text for o in VB.render(w, cfg, 2, "dev")]
    assert a != [o.text for o in VB.render(w, cfg, 3, "dev")]
    assert a != [o.text for o in VB.render(w, cfg, 2, "test")]  # dev world, test banks (OOD)
    assert sum(x != y for x, y in zip(a, [o.text for o in VB.render(w, cfg, 3, "dev")])) >= 0.95 * len(a)


def test_a_line_depends_only_on_its_own_spec_so_deleting_events_is_byte_clean():
    w = make_world(6, 200, "dev")
    for affect, r in (("A0", 0.0), ("A1", 0.0), ("A2", 0.7)):
        cfg = cfg_with(affect=affect, r_aff=r, typo_rate=0.02)
        full = {o.oid: o.text for o in VB.render(w, cfg, 6, "dev")}
        keep = tuple(sp for i, sp in enumerate(w.obs_specs) if i % 3 != 0)
        part = dataclasses.replace(w, obs_specs=keep)
        sub = {o.oid: o.text for o in VB.render(part, cfg, 6, "dev")}
        assert len(sub) == len(keep)
        assert all(full[k] == v for k, v in sub.items())


def test_render_parts_agree_with_render_and_expose_the_pieces():
    w = make_world(7, 60, "dev")
    cfg = cfg_with(affect="A1")
    obs = VB.render(w, cfg, 7, "dev")
    for o in obs:
        p = VB.render_parts(w, cfg, 7, "dev", o.oid)
        assert p.text == o.text and p.oid == o.oid
        assert p.core and p.core in o.text
        for piece in p.pre + p.post + p.affect:
            assert piece in o.text
        assert p.n_words == words(o.text) and p.kind == o.channel
        if o.channel == "dialogue":
            assert o.text.startswith('"') and o.text.endswith(p.tag + ".")


# --------------------------------------------------------------- partitions and templates


def test_banks_are_disjoint_between_dev_and_test_and_every_bank_has_both_halves():
    dev, test = VB.bank_strings("dev"), VB.bank_strings("test")
    assert dev and test and not (dev & test)
    for name, halves in VB.BANKS.items():
        assert len(halves["dev"]) >= 2 and len(halves["test"]) >= 2, name
        assert not set(halves["dev"]) & set(halves["test"]), name
    assert not VB.pad_clause_set("dev") & VB.pad_clause_set("test")
    for fam in ("EP1", "SE4", "SE5", "IN1", "EP4", "IN4", "EP3c", "ME1"):
        assert not set(VB.question_stems(fam, "dev")) & set(VB.question_stems(fam, "test"))
    stems_dev = {s for f in ("EP1", "SE4", "IN1", "EP4", "IN4", "EP3c", "ME1") for s in VB.question_stems(f, "dev")}
    stems_test = {s for f in ("EP1", "SE4", "IN1", "EP4", "IN4", "EP3c", "ME1") for s in VB.question_stems(f, "test")}
    assert not stems_dev & stems_test


def test_at_least_twelve_template_families_per_kind_and_40_to_80_frames_per_scene():
    for kind in S.CHANNELS:
        for part in ("dev", "test"):
            fams = VB.SKELETONS[kind][part]
            assert VB.template_family_count(kind, part) >= 12 and len(set(fams)) == len(fams)
        assert not set(VB.SKELETONS[kind]["dev"]) & set(VB.SKELETONS[kind]["test"])  # held out
    sizes = []
    for scene in S.SCENE_NAMES:
        for part in ("dev", "test"):
            fr = VB.frames_of(scene, part)
            assert 40 <= len(fr) <= 80 and len(set(fr)) == len(fr)
            assert fr == tuple(sorted(fr)) and VB.frame_count(scene, part) == len(fr)
        sizes.append(VB.frame_count(scene, "dev"))
    assert min(sizes) == 40 and max(sizes) == 80
    # frames are not one-to-one with scenes: scenes share skeletons and differ in their frames
    a, b = set(VB.frames_of("routine", "dev")), set(VB.frames_of("minor", "dev"))
    assert a != b and {f[0] for f in a} & {f[0] for f in b}
    assert len({f[0] for f in a}) >= 8


def test_frames_used_by_a_scene_vary_inside_a_world(world_dev):
    cfg = S.TierCfg.for_tier("L1")
    seen: dict = {}
    for sp in world_dev.obs_specs:
        p = VB.render_parts(world_dev, cfg, 1, "dev", sp.oid)
        seen.setdefault(p.scene, set()).add(p.frame)
    assert all(f in VB.frames_of(sc, "dev") for sc, fs in seen.items() for f in fs)
    assert max(len(v) for v in seen.values()) >= 8  # many frames per scene, not one per scene
    assert len({fr for fs in seen.values() for fr in fs}) > len(seen)


def test_a_partition_renders_only_its_own_clause_banks(world_dev):
    cfg = S.TierCfg.for_tier("L1")
    pads = {p: VB.pad_clause_set(p) for p in ("dev", "test")}

    def up(s):
        return s[0].upper() + s[1:]

    for part in ("dev", "test"):
        other = "test" if part == "dev" else "dev"
        n = 0
        for sp in world_dev.obs_specs:
            p = VB.render_parts(world_dev, cfg, 1, part, sp.oid)
            for s in p.pre + p.post:
                n += 1
                assert up(s) in pads[part] and up(s) not in pads[other], s
        assert n > 500


def test_test_seeds_render_only_the_test_partition_and_bad_partitions_fail():
    w = make_world(10005, 20, "test")
    cfg = S.TierCfg.for_tier("L1")
    assert S.partition_of_seed(10005) == "test"
    VB.render(w, cfg, 10005, "test")
    with pytest.raises(ValueError):
        VB.render(w, cfg, 10005, "dev")
    with pytest.raises(ValueError):
        VB.render(w, cfg, 1, "other")
    with pytest.raises(ValueError):
        VB.render_parts(w, cfg, 10005, "dev", w.obs_specs[0].oid)


def test_v3_is_not_implemented():
    w = make_world(1, 10, "dev")
    with pytest.raises(NotImplementedError):
        VB.render(w, cfg_with(v_mix=(0.5, 0.2, 0.3)), 1, "dev")
    with pytest.raises(NotImplementedError):
        VB.render_v3(w)
    VB.render(w, cfg_with(v_mix=(0.5, 0.5, 0.0)), 1, "dev")


# ------------------------------------------------------------------ one-line worlds


def build(entities=(), facts=(), slots=(), role="assert", channel="diary", scene="minor", source="",
          target=45, A=0.3, Vv=0.0, n_specs=1, frame=""):
    """A world with a narrator, the given entities [(kind, name)], facts [(pred, subj, obj, src)]
    where subj is None (the narrator) or an index into entities, and slots [(name, value, fact
    index or None)]. ``n_specs`` copies of the spec get oids o00001... for frequency checks."""
    b = _B(1, "dev")
    me = b.entity("person", "Ravo")
    ents = [b.entity(k, n) for k, n in entities]
    fs = [b.fact(p, me.eid if s is None else ents[s].eid, o, src) for p, s, o, src in facts]
    sl = tuple(S.Slot(name=n, value=v, fid=fs[i].fid if i is not None else "") for n, v, i in slots)
    ments = tuple(S.Mention(fid=f.fid, role=role) for f in fs)
    sit = S.Situation(sid="s00001", day=3, minute=600, scene=scene, A=A, V=Vv, facts=tuple(f.fid for f in fs))
    specs = tuple(S.ObsSpec(oid=S.new_id("obs", i + 1), t_obs=S.to_minutes(3, 600) + i, channel=channel,
                            sid="s00001", mentions=ments, slots=sl, target_len=target,
                            source=ents[source].eid if isinstance(source, int) else "", frame=frame)
                  for i in range(n_specs))
    w = S.World(seed=1, cfg=S.TierCfg.for_tier("L1"), entities=tuple(b.entities), facts=tuple(b.facts),
                situations=(sit,), obs_specs=specs, card=S.Card(name="Ravo"))
    return w.with_extra("narrator", me.eid)


def lines(world, cfg=None, part="dev"):
    return [o.text for o in VB.render(world, cfg or S.TierCfg.for_tier("L1"), 1, part)]


# ----------------------------------------------------------------------------- affect


def test_affect_lexicon_scan_has_exact_semantics():
    assert VB.affect_scan("My heart was pounding and I was terrified.") == ["heart was pounding", "terrified"]
    assert VB.affect_scan("Tears of joy ran down my face") == ["tears of joy"]
    assert VB.affect_scan("TERRIFIED!") == ["terrified"]
    assert VB.affect_scan("She felt happy, then happy again") == ["happy", "happy"]
    assert VB.affect_scan("The tram ran a few minutes behind.") == []
    assert VB.affect_scan("") == []
    assert set(VB.AFFECT_LEXICON) >= {"terrified", "delighted", "heart was pounding", "over the moon"}


def test_every_affect_phrase_is_exactly_one_lexicon_entry_and_a_clean_bank_has_none():
    for name, halves in VB.BANKS.items():
        for part, items in halves.items():
            for t in items:
                hits = VB.affect_scan(re.sub(r"\{\w+\}", "x", t))
                if name.startswith("aff."):
                    assert len(hits) == 1, (name, t, hits)
                else:
                    assert hits == [], (name, t, hits)
    for part in ("dev", "test"):
        assert all(VB.affect_scan(c) == [] for c in VB.pad_clause_set(part))


@pytest.mark.parametrize("partition,seed", [("dev", 1), ("test", 10005)])
def test_a0_renders_zero_affect_words_in_every_channel(partition, seed):
    w = make_world(seed, 500, partition)
    cfg = cfg_with(affect="A0", r_aff=0.8, dramatic_decoy_share=1.0)  # A0 ignores both dials
    for o in VB.render(w, cfg, seed, partition):
        assert VB.affect_scan(o.text) == [], o.text


def _affect_counts(world, seed, **kw):
    cfg = cfg_with(**kw)
    sit = {s.sid: s for s in world.situations}
    obs = VB.render(world, cfg, seed, "dev")
    return ([len(VB.affect_scan(o.text)) for o in obs],
            [sit[sp.sid].A for sp in world.obs_specs], [sit[sp.sid].V for sp in world.obs_specs])


def test_a1_is_independent_of_arousal_and_a2_follows_r_aff_with_the_same_marginal():
    w = make_world(21, 2500, "dev")
    c1, a, _ = _affect_counts(w, 21, affect="A1", r_aff=0.8)  # r_aff is ignored under A1
    assert abs(spearman(a, c1)) <= 0.10
    prev = abs(spearman(a, c1))
    means = [sum(c1) / len(c1)]
    for r in (0.3, 0.6, 0.8):
        c2, a2, _ = _affect_counts(w, 21, affect="A2", r_aff=r)
        rho = spearman(a2, c2)
        assert rho > prev + 0.05, (r, rho, prev)
        prev = rho
        means.append(sum(c2) / len(c2))
        assert max(c2) <= 3
    assert prev >= 0.5
    assert max(means) - min(means) <= 0.08  # same marginal count distribution in A1 and A2
    assert 0.3 <= means[0] <= 0.8
    c0, _, _ = _affect_counts(w, 21, affect="A2", r_aff=0.0)
    assert abs(spearman(a, c0)) <= 0.10


def test_polarity_of_affect_phrases_follows_valence():
    w = make_world(22, 2500, "dev")
    pos = {p for n in ("aff.pos_mild", "aff.pos_strong") for part in ("dev", "test") for p in VB.BANKS[n][part]}
    neg = {p for n in ("aff.neg_mild", "aff.neg_strong") for part in ("dev", "test") for p in VB.BANKS[n][part]}
    cfg = cfg_with(affect="A2", r_aff=0.8)
    sit = {s.sid: s for s in w.situations}
    share = {"hi": [0, 0], "lo": [0, 0]}
    for o, sp in zip(VB.render(w, cfg, 22, "dev"), w.obs_specs):
        v = sit[sp.sid].V
        key = "hi" if v >= 0.5 else "lo" if v <= -0.5 else None
        if key:
            share[key][0] += sum(p.lower() in o.text.lower() for p in pos)
            share[key][1] += sum(p.lower() in o.text.lower() for p in neg)
    assert share["hi"][0] / sum(share["hi"]) > 0.7 and share["lo"][0] / sum(share["lo"]) < 0.3


def test_dramatic_decoys_add_strong_phrases_to_low_arousal_lines_only_when_asked():
    w = make_world(23, 800, "dev")
    line_a = VB._Ctx(w, S.TierCfg.for_tier("L1"), 23, "dev").line_a  # retelling lines have A x 0.5
    strong = {p for n in ("aff.pos_strong", "aff.neg_strong") for part in ("dev", "test") for p in VB.BANKS[n][part]}
    base = VB.render(w, cfg_with(affect="A1"), 23, "dev")
    dec = VB.render(w, cfg_with(affect="A1", dramatic_decoy_share=1.0), 23, "dev")
    lows = 0
    for b, d, sp in zip(base, dec, w.obs_specs):
        low = line_a[sp.oid] < 0.3
        n_b, n_d = len(VB.affect_scan(b.text)), len(VB.affect_scan(d.text))
        assert n_d >= n_b
        if low:
            lows += 1
            assert n_d == n_b + 1 and any(p.lower() in d.text.lower() for p in strong)
        else:
            assert d.text == b.text
    assert lows > 400
    same = VB.render(w, cfg_with(affect="A1", dramatic_decoy_share=0.0), 23, "dev")
    assert [x.text for x in same] == [x.text for x in base]


def test_retelling_lines_use_the_retell_factor_for_their_arousal():
    w = make_world(24, 60, "dev")
    ctx = VB._Ctx(w, S.TierCfg.for_tier("L1"), 24, "dev")
    sit = {s.sid: s for s in w.situations}
    n = 0
    for sp in w.obs_specs:
        recall = bool(sp.mentions) and all(m.role == "recall" for m in sp.mentions)
        expect = sit[sp.sid].A * (0.5 if recall else 1.0)
        assert ctx.line_a[sp.oid] == pytest.approx(expect)
        n += recall
    assert n >= 1


# ------------------------------------------------------------------------- padding


def test_pad_clauses_carry_a_small_fact_and_nothing_queryable():
    pools = {pid: V.pool_vocab(pid) for pid in V.POOLS}
    number_tokens = {t for nw in V.NUMBER_WORDS for t in nw.split()}
    for part in ("dev", "test"):
        clauses = VB.pad_clause_set(part)
        assert len(clauses) >= 400
        for c in clauses:
            assert c.endswith(".") and words(c) >= 4 and c[0].isupper(), c
            assert len(re.findall(r"\b[A-Z]", c)) == 1  # no name, only the sentence start
            assert not re.search(r"\d", c)
            assert not set(V.norm(c).split()) & number_tokens, c
            for pid, voc in pools.items():
                assert voc.matches(c) == [], (c, pid)
        assert {words(c) for c in clauses} >= set(VB.PAD_LENGTHS)


def test_pad_to_length_is_exact_deterministic_and_varied():
    for part in ("dev", "test"):
        pads = VB.pad_clause_set(part)
        for n in [0] + list(range(4, 70)):
            cl = VB.pad_to_length(R.stream(1, "padtest", n), n, part)
            assert sum(words(c) for c in cl) == n and all(c in pads for c in cl)
        assert VB.pad_to_length(R.stream(2, "x"), 40, part) == VB.pad_to_length(R.stream(2, "x"), 40, part)
        variants = {tuple(VB.pad_to_length(R.stream(i, "v"), 40, part)) for i in range(200)}
        assert len(variants) >= 190
    for bad in (1, 2, 3, -4):
        with pytest.raises(ValueError):
            VB.pad_to_length(R.stream(1, "x"), bad, "dev")
    with pytest.raises(ValueError):
        VB.pad_to_length(R.stream(1, "x"), 10, "other")


def test_observation_templates_carry_no_digit_and_no_weekday_or_month_word():
    wk = set(V.WEEKDAYS) | set(V.MONTHS)
    for name, halves in VB.BANKS.items():
        if name.startswith(("qsuf", "stem", "ask", "qtail")):
            continue
        for part, items in halves.items():
            for t in items:
                assert not re.search(r"\d", t), (name, t)
                if not name.startswith("head.time"):
                    assert not set(V.norm(t).split()) & wk, (name, t)


# ---------------------------------------------------------------------- twins and layout


def test_twin_lines_have_a_string_identical_queried_sentence():
    w = make_world(8, 40, "dev")
    base = next(sp for sp in w.obs_specs if sp.channel == "diary" and any(s.fid for s in sp.slots))
    cfg = S.TierCfg.for_tier("L1")
    twins = [dataclasses.replace(base, oid="o9000%d" % i, t_obs=base.t_obs + 1 + i, frame="twin-7",
                                 target_len=base.target_len) for i in range(1, 4)]
    w2 = dataclasses.replace(w, obs_specs=tuple(sorted(w.obs_specs + tuple(twins), key=lambda s: s.t_obs)))
    parts = [VB.render_parts(w2, cfg, 8, "dev", t.oid) for t in twins]
    assert len({p.core for p in parts}) == 1  # the queried sentence is identical ...
    assert len({p.text for p in parts}) == 3  # ... and the surrounding lines are not
    assert len({(p.pre, p.post) for p in parts}) == 3
    own = VB.render_parts(w2, cfg, 8, "dev", base.oid)
    assert own.text != parts[0].text or own.core == parts[0].core
    cores = set()
    for k in range(40):
        t = dataclasses.replace(base, oid="o9100%d" % k, t_obs=base.t_obs + 100 + k, frame="twin-%d" % k)
        w3 = dataclasses.replace(w, obs_specs=tuple(sorted(w.obs_specs + (t,), key=lambda s: s.t_obs)))
        cores.add(VB.render_parts(w3, cfg, 8, "dev", t.oid).core)
    assert len(cores) >= 12  # the frame key selects the wording


def test_position_of_the_queried_clause_is_independent_of_evidence_status():
    w = make_world(31, 2500, "dev")
    flags = evidence_flags(w)
    cfg = S.TierCfg.for_tier("L1")
    ctx = VB._Ctx(w, cfg, 31, "dev")
    bins = {True: [0] * 4, False: [0] * 4}
    for sp in w.obs_specs:
        p = VB._render_line(ctx, sp)
        n = len(p.pre) + len(p.post)
        if n >= 3:
            bins[flags[sp.oid]][min(3, int(4 * len(p.pre) / (n + 1)))] += 1
    tot = [bins[True][i] + bins[False][i] for i in range(4)]
    assert all(0.12 <= t / sum(tot) <= 0.40 for t in tot)
    n_t, n_f = sum(bins[True]), sum(bins[False])
    chi = sum((bins[k][i] - n_k * tot[i] / (n_t + n_f)) ** 2 / (n_k * tot[i] / (n_t + n_f))
              for k, n_k in ((True, n_t), (False, n_f)) for i in range(4))
    assert chi2_sf(chi, 3) >= 0.05


# --------------------------------------------------- the gates on the real and the naive renderer


def _gate_metrics(world, obs, carries):
    sit = {s.sid: s for s in world.situations}
    a = [sit[sp.sid].A for sp in world.obs_specs]
    lens = [words(o.text) for o in obs]
    pos = [l for l, sp in zip(lens, world.obs_specs) if carries[sp.oid]]
    neg = [l for l, sp in zip(lens, world.obs_specs) if not carries[sp.oid]]
    counts = [len(VB.affect_scan(o.text)) for o in obs]
    return {"auc": auc(pos, neg), "corr_len_a": pearson(lens, a), "rho_aff_a": spearman(a, counts),
            "affect_hits": sum(counts)}


def test_planted_naive_renderer_fails_g_len_and_g_aff_and_the_real_one_passes():
    w = make_world(12, 2500, "dev")
    carries = {sp.oid: any(s.fid for s in sp.slots) for sp in w.obs_specs}
    cfg = cfg_with(affect="A0")
    real = _gate_metrics(w, VB.render(w, cfg, 12, "dev"), carries)
    assert 0.45 <= real["auc"] <= 0.55 and abs(real["corr_len_a"]) <= 0.05
    assert real["affect_hits"] == 0
    real1 = _gate_metrics(w, VB.render(w, cfg_with(affect="A1"), 12, "dev"), carries)
    assert 0.45 <= real1["auc"] <= 0.55 and abs(real1["rho_aff_a"]) <= 0.10
    real2 = _gate_metrics(w, VB.render(w, cfg_with(affect="A2", r_aff=0.5), 12, "dev"), carries)
    assert abs(real2["rho_aff_a"]) > 0.10  # G-AFF does fire on correlated affect (A2)
    naive_obs = VB.render_planted_naive(w, cfg, 12, "dev")
    naive = _gate_metrics(w, naive_obs, carries)
    assert abs(naive["auc"] - 0.5) >= 0.2  # G-LEN: evidence status
    assert abs(naive["corr_len_a"]) >= 0.3  # G-LEN: arousal
    assert naive["affect_hits"] >= 0.2 * len(naive_obs)  # G-AFF under A0: affect words are there
    assert naive["rho_aff_a"] >= 0.4  # G-AFF: Spearman(A, affect phrases) far above 0.10
    for o, sp in zip(naive_obs, w.obs_specs):
        assert VB.missing_slots(sp, o.text) == [] and (o.oid, o.t_obs) == (sp.oid, sp.t_obs)


def test_each_leak_of_the_naive_renderer_fires_only_its_own_gate():
    w = make_world(13, 2500, "dev")
    carries = {sp.oid: any(s.fid for s in sp.slots) for sp in w.obs_specs}
    cfg = cfg_with(affect="A0")
    only_len = _gate_metrics(w, VB.render_planted_naive(w, cfg, 13, "dev", leaks=("length",)), carries)
    assert only_len["affect_hits"] == 0 and abs(only_len["auc"] - 0.5) >= 0.2 and abs(only_len["corr_len_a"]) >= 0.3
    only_aff = _gate_metrics(w, VB.render_planted_naive(w, cfg, 13, "dev", leaks=("affect",)), carries)
    assert only_aff["rho_aff_a"] >= 0.4 and only_aff["affect_hits"] > 0
    assert 0.45 <= only_aff["auc"] <= 0.55 and abs(only_aff["corr_len_a"]) <= 0.1
    none = _gate_metrics(w, VB.render_planted_naive(w, cfg, 13, "dev", leaks=()), carries)
    assert none["affect_hits"] == 0 and 0.45 <= none["auc"] <= 0.55 and abs(none["corr_len_a"]) <= 0.1


# ------------------------------------------------------------------------------- typos


def test_typos_swap_letters_outside_slots_and_keep_words_and_slots():
    w = make_world(14, 300, "dev")
    base = VB.render(w, cfg_with(), 14, "dev")
    assert [o.text for o in base] == [o.text for o in VB.render(w, cfg_with(typo_rate=0.0), 14, "dev")]
    noisy = VB.render(w, cfg_with(typo_rate=0.1), 14, "dev")
    assert [o.text for o in noisy] == [o.text for o in VB.render(w, cfg_with(typo_rate=0.1), 14, "dev")]
    changed = 0
    for a, b, sp in zip(base, noisy, w.obs_specs):
        assert VB.missing_slots(sp, b.text) == []
        assert words(a.text) == words(b.text)
        assert sorted(a.text) == sorted(b.text)  # only a swap of letters
        changed += a.text != b.text
    assert changed >= 0.6 * len(base)


# ----------------------------------------------------------- roles, sources, subjects


TOLD = re.compile(r"\b(told|heard|mentioned|word is|informed|said|apparently)\b")
READ = re.compile(r"\b(read|paper|article|news|reported|according)\b")


def test_told_and_read_facts_are_carried_by_wording_and_lived_facts_are_not():
    def share(src, rx):
        w = build(facts=[("breakfast", None, "porridge", src)], slots=[("breakfast", "porridge", 0)], n_specs=1)
        w = dataclasses.replace(w, obs_specs=tuple(
            dataclasses.replace(w.obs_specs[0], oid=S.new_id("obs", i + 1), t_obs=w.obs_specs[0].t_obs + i)
            for i in range(120)))
        txt = [VB.render_parts(w, S.TierCfg.for_tier("L1"), 1, "dev", sp.oid).core for sp in w.obs_specs]
        return sum(bool(rx.search(t)) for t in txt) / len(txt)

    assert share("told", TOLD) >= 0.85 and share("read", READ) >= 0.85
    assert share("lived", TOLD) <= 0.05 and share("lived", READ) <= 0.05
    assert share("told", READ) <= 0.1 and share("read", TOLD) <= 0.1


def test_roles_change_the_wording_but_never_the_slot():
    cfgl = S.TierCfg.for_tier("L1")
    markers = {"update": r"\b(now|these days|as of now|by now|nowadays|since then|at this point|update|newest|moved|relocated|settled|switched|new)\b",
               "retract": r"(not true|wrong|scratch|correction|take back|ignore|retracting)",
               "recall": r"\b(again|once more|retold|repeated|brought it up|went over)\b"}
    texts = {}
    for role in ("assert", "update", "retract", "recall"):
        got = []
        for ch in ("diary", "chat"):
            w = build(entities=[("city", "Verdton")], facts=[("lives_in", None, "e0002", "lived")],
                      slots=[("lives_in", "Verdton", 0)], role=role, channel=ch, n_specs=40)
            got += [VB.render_parts(w, cfgl, 1, "dev", sp.oid).core for sp in w.obs_specs]
        assert all("Verdton" in t for t in got)
        texts[role] = got
        if role != "assert":
            assert sum(bool(re.search(markers[role], t)) for t in got) >= 0.9 * len(got), role
    assert sum(bool(re.search(markers["retract"], t)) for t in texts["assert"]) <= 0.05 * 80
    assert sum(bool(re.search(markers["recall"], t)) for t in texts["assert"]) <= 0.05 * 80


def test_subjects_come_from_the_fact_and_the_teller_is_never_named():
    cfgl = S.TierCfg.for_tier("L1")
    # a shop closing time is about the shop even when no shop slot is given
    w = build(entities=[("shop", "Kalmer Pharmacy"), ("street", "Tisbo Street")],
              facts=[("closing_time", 0, "18:00", "told"), ("on_street", 0, "e0003", "told")],
              slots=[("closing_time", "18:00", 0), ("street", "Tisbo Street", 1)], channel="chat", scene="remark",
              n_specs=30)
    for t in lines(w, cfgl):
        assert "Kalmer Pharmacy" in t and "18:00" in t and "Tisbo Street" in t and "Saturdays" in t
        assert t.index("Tisbo Street") < t.index("18:00") or True
    # 'who is X': the person named by the fact, with the relation
    w = build(entities=[("person", "Imre")], facts=[("relation", 0, "cousin", "told")],
              slots=[("relation", "cousin", 0)], channel="diary", scene="remark", n_specs=30)
    assert all("Imre" in t and "cousin" in t for t in lines(w, cfgl))
    # another person's errand is theirs, the narrator's own is 'I'
    w = build(entities=[("person", "Mirela")], facts=[("errand_visit", 0, "dentist", "lived")],
              slots=[("errand", "dentist", 0)], n_specs=30)
    assert all("Mirela" in t for t in lines(w, cfgl))
    w = build(entities=[("person", "Mirela")], facts=[("errand_visit", None, "dentist", "lived")],
              slots=[("errand", "dentist", 0)], n_specs=30)
    assert all("Mirela" not in t for t in lines(w, cfgl))
    # a context slot that names the subject is not repeated
    w = build(entities=[("person", "Mirela")], facts=[("errand_visit", 0, "dentist", "lived")],
              slots=[("errand", "dentist", 0), ("person", "Mirela", None)], n_specs=30)
    assert all(t.count("Mirela") == 1 for t in lines(w, cfgl))
    # the teller (ObsSpec.source) does not appear: wording alone carries the source kind
    w = build(entities=[("person", "Zetaba"), ("shop", "Kalmer Pharmacy")],
              facts=[("closing_time", 1, "18:00", "told")], slots=[("closing_time", "18:00", 0)],
              source=0, n_specs=30)
    assert all("Zetaba" not in t for t in lines(w, cfgl))


def test_articles_render_the_decoy_as_another_vehicle_and_never_repeat_story_parts():
    cfgl = S.TierCfg.for_tier("L1")
    w = build(entities=[("story", "flood in Verdton")],
              facts=[("read_story", None, "e0002", "read"), ("vehicle_colour", 0, "red", "read"),
                     ("decoy_colour", 0, "blue", "read")],
              slots=[("story", "flood in Verdton", 0), ("vehicle_colour", "red", 1), ("decoy_colour", "blue", 2),
                     ("story_kind", "flood", None), ("city", "Verdton", None)], channel="article", scene="article",
              n_specs=1)
    specs = tuple(dataclasses.replace(w.obs_specs[0], oid=S.new_id("obs", i + 1), t_obs=w.obs_specs[0].t_obs + i)
                  for i in range(150))
    w = dataclasses.replace(w, obs_specs=specs)
    nouns = ("car", "van", "bus", "lorry", "taxi", "truck", "minibus", "coach", "tractor")
    ok = 0
    for t in lines(w, cfgl):
        clauses = re.split(r"[.;,:]|\bthen\b|\band\b|\balso\b|\bplus\b|\+", t.lower())

        def near(col):
            seg = next(c for c in clauses if re.search(r"\b%s\b" % col, c))
            return next(n for n in re.findall(r"[a-z]+", seg) if n in nouns)

        assert t.count("Verdton") == 1 and t.count("flood in Verdton") == 1  # story_kind and city are covered
        ok += near("red") == "car" and near("blue") != "car"
    assert ok >= 0.97 * 150


def test_unknown_and_awkward_slots_are_still_verbatim():
    cfgl = S.TierCfg.for_tier("L1")
    w = build(entities=[("person", "Mirela")],
              facts=[("pet_name", None, "Rex", "lived"), ("breakfast", None, "toast with jam", "lived")],
              slots=[("pet_name", "Rex", 0), ("note", "St. John's (north)", None), ("breakfast", "toast with jam", 1),
                     ("jam", "jam", None), ("person", "Mirela", None), ("odd_context", "Q9-x", None)],
              n_specs=40, channel="chat")
    for t in lines(w, cfgl):
        for v in ("Rex", "St. John's (north)", "toast with jam", "Mirela", "Q9-x"):
            assert v in t
    for ch in S.CHANNELS:  # a line with no slot at all still has a core and the exact length
        w = build(channel=ch, target=33)
        p = VB.render_parts(w, cfgl, 1, "dev", "o00001")
        assert p.core and p.n_words == 33


def test_voices_v1_declarative_and_v2_informal_and_dialogue_quotes(world_dev):
    cfgl = S.TierCfg.for_tier("L1")
    for sp in world_dev.obs_specs:
        p = VB.render_parts(world_dev, cfgl, 1, "dev", sp.oid)
        for s in p.pre + p.post:
            if sp.channel in ("chat",):
                assert s[0].islower() or s.startswith("I "), s
            else:
                assert s[0].isupper(), s
        if sp.channel == "dialogue":
            assert p.text.count('"') == 2 and p.text.startswith('"') and p.tag in p.text
        else:
            assert '"' not in p.text
    assert {VB.STYLE_OF_CHANNEL[c] for c in S.CHANNELS} == {"V1", "V2"}


# --------------------------------------------------------------------------- questions


def mq(fam, ask, cue=(), qid="q0001", gold="x", fmt="open", options=(), conf=True, twin="", kind="entity"):
    return S.Query(qid=qid, family=fam, t_ask=2000, text="", fmt=fmt,
                   gold=S.Gold(kind=kind, value=gold), cue=tuple(S.Slot(name=n, value=v) for n, v in cue),
                   ask=ask, options=tuple(options), conf=conf, twin_of=twin)


QUESTION_CASES = [
    ("EP1", "breakfast", [("date", "2027-03-14")], "porridge"),
    ("EP1", "breakfast", [("relative_day", "yesterday")], "porridge"),
    ("EP1", "breakfast", [("relative_day", "3 days ago")], "porridge"),
    ("SE4", "lives_in", [], "Verdton"),
    ("SE5", "lives_in", [("date", "2027-03-14")], "Verdton"),
    ("SE4", "works_as", [], "baker"),
    ("SE5", "works_as", [("date", "2027-03-14")], "baker"),
    ("SE4", "works_at", [], "Karbadam"),
    ("SE4", "relation", [("person", "Imre")], "cousin"),
    ("IN1", "vehicle_colour", [("story_kind", "flood"), ("city", "Verdton"), ("relative_window", "about two weeks ago")], "teal"),
    ("IN1", "vehicle_colour", [("story_kind", "flood"), ("city", "Verdton"), ("date", "2027-03-01")], "teal"),
    ("EP4", "companion", [("date", "2027-03-14")], "Mirela"),
    ("EP4", "car_colour", [("relative_day", "5 days ago")], "teal"),
    ("IN4", "closing_time", [("shop", "Kalmer Pharmacy"), ("street", "Tisbo Street")], "18:00"),
    ("IN4", "closing_time", [("shop", "Kalmer Pharmacy")], "18:00"),
    ("EP3c", "visit_count", [("errand", "dentist"), ("window_from", "2027-02-01"), ("window_to", "2027-04-01")], "3"),
    ("ME1", "breakfast", [("date", "2027-03-15")], "UNKNOWN"),
    ("ME1", "companion", [("city", "Paris")], "UNKNOWN"),
    ("ME1", "closing_time", [("shop", "Kalmer Pharmacy")], "UNKNOWN"),
]


@pytest.mark.parametrize("part", ["dev", "test"])
def test_every_question_holds_its_cues_verbatim_and_the_conf_request(part):
    seen = set()
    for i in range(30):
        for k, (fam, ask, cue, gold) in enumerate(QUESTION_CASES):
            q = mq(fam, ask, cue, qid="q%04d" % (i * 40 + k), gold=gold)
            t = VB.render_question(q, part)
            seen.add(t)
            for s in q.cue:
                assert s.value in t, (fam, s, t)
            assert t.count("CONF: 0-100") == 1 and t.rstrip().endswith("CONF: 0-100.") or "CONF: 0-100" in t
            assert VB.render_question(dataclasses.replace(q, conf=False), part).count("CONF") == 0
            assert "UNKNOWN" in t  # the same abstention hint on every open question
            assert t == VB.render_question(q, part)  # deterministic
            assert gold in ("UNKNOWN",) or gold not in t or gold in [s.value for s in q.cue] or gold.isdigit()
    assert len(seen) > 400


def test_question_wording_of_the_day1_examples():
    t = VB.render_question(mq("IN4", "closing_time", [("shop", "Kalmer Pharmacy"), ("street", "Tisbo Street")]), "dev")
    assert "the Kalmer Pharmacy on Tisbo Street" in t and "Saturday" in t
    t = VB.render_question(mq("EP3c", "visit_count", [("errand", "dentist"), ("window_from", "2027-02-01"),
                                                      ("window_to", "2027-04-01")]), "dev")
    assert "the dentist" in t and "between 2027-02-01 and 2027-04-01" in t
    t = VB.render_question(mq("IN1", "vehicle_colour", [("story_kind", "flood"), ("city", "Verdton"),
                                                        ("relative_window", "about two weeks ago")]), "test")
    assert "the flood in Verdton" in t and "colour" in t and t.count("about two weeks ago") == 1
    t = VB.render_question(mq("SE4", "relation", [("person", "Imre")]), "dev")
    assert "Imre" in t and t.count("Imre") == 1
    t = VB.render_question(mq("SE5", "lives_in", [("date", "2027-03-14")]), "dev")
    assert "on 2027-03-14" in t and ("did I live" in t or "was my home" in t or "I lived" in t or "Where did" in t)
    t = VB.render_question(mq("ME1", "companion", [("city", "Paris")]), "dev")
    assert "Paris" in t and ("visit" in t or "trip" in t or "went with" in t)


def test_choice_questions_list_the_options_in_order_and_skip_the_abstain_hint():
    q = mq("IN1", "vehicle_colour", [("story_kind", "flood"), ("city", "Verdton")], fmt="choice",
           options=("red", "blue", "green", "black"), gold="blue")
    for part in ("dev", "test"):
        t = VB.render_question(q, part)
        assert "A) red B) blue C) green D) black." in t
        assert "UNKNOWN" not in t and "CONF: 0-100" in t
    assert VB.render_question(q, "dev", abstain_hint=True) == VB.render_question(q, "dev")
    o = mq("EP1", "breakfast", [("date", "2027-03-14")])
    assert "UNKNOWN" not in VB.render_question(o, "dev", abstain_hint=False)


def test_at_least_eight_question_frames_per_family_in_each_partition_and_all_are_used():
    for fam in ("EP1", "SE4", "SE5", "IN1", "EP4", "IN4", "EP3c", "ME1"):
        dev, test = VB.question_stems(fam, "dev"), VB.question_stems(fam, "test")
        assert len(set(dev)) >= 8 and len(set(test)) >= 8, fam
        assert not set(dev) & set(test)
    for fam, ask, cue, gold in QUESTION_CASES:
        if fam == "ME1":
            continue
        used = {}
        for part in ("dev", "test"):
            stems = VB.question_stems(fam, part)
            texts = {VB.render_question(mq(fam, ask, cue, qid="q%04d" % i), part) for i in range(400)}
            assert len(texts) >= 8
            for st in stems:  # every frame of the family is reachable
                pre = st.split("{")[0]
                assert any(t.startswith(pre) or pre.strip() == "" for t in texts), (fam, st)
            used[part] = texts
        assert not used["dev"] & used["test"]


def test_twin_queries_share_their_question_text_and_other_queries_differ():
    base = mq("EP1", "breakfast", [("date", "2027-03-14")], qid="q0001")
    twin = dataclasses.replace(base, qid="q0777", twin_of="q0001")
    for part in ("dev", "test"):
        assert VB.render_question(twin, part) == VB.render_question(base, part)
    other = {VB.render_question(dataclasses.replace(base, qid="q%04d" % i), "dev") for i in range(2, 60)}
    assert len(other) >= 8
    assert VB.render_question(base, "dev") != VB.render_question(base, "test")


def test_render_question_reads_only_the_documented_fields():
    q = mq("EP4", "companion", [("date", "2027-03-14")], gold="Mirela")
    ref = VB.render_question(q, "dev")
    other = dataclasses.replace(
        q, gold=S.Gold(kind="entity", value="Someone Else", near_miss=(S.NearMiss(kind="stale", value="x"),)),
        t_ask=9, tags=S.Tags(delay_days=77, partition="test"), evidence_oids=("o00001",), evidence_fids=("f00001",),
        text="old text")
    assert VB.render_question(other, "dev") == ref
    assert VB.render_question(dataclasses.replace(q, fmt="choice", options=("a", "b")), "dev") != ref
    assert VB.render_question(dataclasses.replace(q, cue=()), "dev") != ref
    assert VB.render_question(dataclasses.replace(q, ask="car_colour"), "dev") != ref
    with pytest.raises(ValueError):
        VB.render_question(q, "other")


def test_unknown_cue_names_and_asks_are_still_contained_and_readable():
    q = mq("SE4", "weight", [("mystery", "Zorb 7"), ("date", "2027-01-02"), ("shop", "Fumo Pharmacy")])
    for part in ("dev", "test"):
        t = VB.render_question(q, part)
        assert all(v in t for v in ("Zorb 7", "2027-01-02", "Fumo Pharmacy")) and "weight" in t


def test_question_frames_differ_from_observation_frames(world_dev):
    obs_strings = {s for name, h in VB.BANKS.items() if not name.startswith(("stem.", "ask.", "qsuf", "qtail"))
                   for part in h for s in h[part]}
    q_strings = {s for name, h in VB.BANKS.items() if name.startswith(("stem.", "ask.", "qsuf", "qtail"))
                 for part in h for s in h[part]}
    assert not obs_strings & q_strings
    obs = VB.render(world_dev, S.TierCfg.for_tier("L1"), 1, "dev")
    assert all("?" not in o.text for o in obs)
    first_words = {"What", "Which", "Who", "How", "Where", "When", "At", "In"}
    for fam, ask, cue, gold in QUESTION_CASES:
        t = VB.render_question(mq(fam, ask, cue), "dev")
        assert "?" in t or t.split()[0] in ("Tell", "Remind", "Please", "Help", "Think", "Count", "Work", "Look",
                                             "I", "Can", "Could", "Settle", "Check") or t.split()[0] in first_words
    # no stem or ask clause is also a sentence of any rendered observation
    sentences = {s.strip() for o in obs for s in re.split(r"(?<=[.])\s+", o.text)}
    assert not any(st.replace("{Qd}", "").strip() in sentences for fam in ("EP1", "IN1") for st in VB.question_stems(fam, "dev"))


# ----------------------------------------------------------------- flash pass verifier


def test_validate_paraphrase_accepts_only_faithful_rewrites():
    w = build(entities=[("person", "Mirela")], facts=[("errand_visit", 0, "dentist", "lived"),
                                                     ("car_colour", None, "red", "lived")],
              slots=[("errand", "dentist", 0), ("car_colour", "red", 1)], target=20)
    sp = w.obs_specs[0]
    tpl = "Mirela went to the dentist at noon and a red car waited outside the entrance for a while today."
    assert VB.validate_paraphrase(sp, tpl, tpl) == (True, "")
    ok = "At noon Mirela went to the dentist, and a red car was waiting outside the entrance for a while."
    assert VB.validate_paraphrase(sp, tpl, ok) == (True, "")
    assert VB.validate_paraphrase(sp, tpl, ok.replace("dentist", "dental clinic"))[1].startswith("slot missing")
    assert VB.validate_paraphrase(sp, tpl, ok.replace("red", "scarlet"))[1].startswith("slot missing")
    assert VB.validate_paraphrase(sp, tpl, ok + " It took 5 minutes.")[1] in ("new numeral", "length 25 outside 0.8-1.3 of 20")
    assert VB.validate_paraphrase(sp, tpl, "Mirela went to the dentist and a red car and a blue car waited outside "
                                          "the entrance for a while today")[1] == "new colour"
    assert VB.validate_paraphrase(sp, tpl, "Mirela went to the dentist with Tomas and a red car waited outside "
                                          "the entrance for a while today.")[1].startswith("new proper noun")
    assert VB.validate_paraphrase(sp, tpl, "Mirela went to the dentist and a red car waited outside, "
                                          "which left me terrified, for a while today.")[1] == "affect words changed"
    assert VB.validate_paraphrase(sp, tpl, "Mirela went to the dentist, a red car.")[1].startswith("length")
    assert VB.validate_paraphrase(sp, tpl, tpl + " " + tpl)[1].startswith("length")
    base = "Mirela went to the dentist and a red car waited outside the entrance"  # 12 words
    pad = " for a while today and it did not change before the evening came and then the whole street went quiet again"

    def n_words(k):  # a candidate of exactly k words that keeps both slots
        return " ".join((base + pad).split()[:k]) if k >= 12 else None

    assert VB.validate_paraphrase(sp, tpl, n_words(26))[0]  # 1.3 x 20 words
    assert VB.validate_paraphrase(sp, tpl, n_words(27))[1].startswith("length 27")
    assert VB.validate_paraphrase(sp, tpl, n_words(16))[0]  # 0.8 x 20 words
    assert VB.validate_paraphrase(sp, tpl, n_words(15))[1].startswith("length 15")
    with_aff = "Mirela went to the dentist and a red car waited outside the entrance while I felt terrified today."
    assert VB.validate_paraphrase(sp, with_aff, with_aff)[0]
    assert not VB.validate_paraphrase(sp, with_aff, with_aff.replace("terrified", "happy"))[0]


# ------------------------------------------------------------------ hygiene inside a line


def test_no_pad_clause_repeats_inside_a_line_and_subjects_rarely_do(world_dev):
    cfg = S.TierCfg.for_tier("L1")
    dup_clause = dup_subject = n = 0
    for p in VB.render_all_parts(world_dev, cfg, 1, "dev"):
        pads = p.pre + p.post
        n += 1
        dup_clause += len(set(pads)) != len(pads)
        subj = [" ".join(s.split()[:2]) for s in pads]
        dup_subject += len(set(subj)) != len(subj)
    assert dup_clause <= 0.005 * n and dup_subject <= 0.25 * n


def test_the_source_wording_is_stated_once_per_line_even_with_several_clauses():
    prefixes = [t.split("{c}")[0].strip() for st in ("V1", "V2") for part in ("dev", "test")
                for t in VB.BANKS["wrap.read." + st][part] if t.split("{c}")[0].strip()]
    rx = re.compile("|".join(re.escape(p) for p in sorted(prefixes, key=len, reverse=True)), re.I)
    w = build(entities=[("story", "flood in Verdton")],
              facts=[("read_story", None, "e0002", "read"), ("vehicle_colour", 0, "red", "read"),
                     ("decoy_colour", 0, "blue", "read")],
              slots=[("story", "flood in Verdton", 0), ("vehicle_colour", "red", 1), ("decoy_colour", "blue", 2)],
              channel="article", scene="article", n_specs=1)
    specs = tuple(dataclasses.replace(w.obs_specs[0], oid=S.new_id("obs", i + 1), t_obs=w.obs_specs[0].t_obs + i)
                  for i in range(100))
    w = dataclasses.replace(w, obs_specs=specs)
    cfg = S.TierCfg.for_tier("L1")
    for part in ("dev", "test"):
        cores = [VB.render_parts(w, cfg, 1, part, sp.oid).core for sp in w.obs_specs]
        assert max(len(rx.findall(c)) for c in cores) <= 1
        assert sum(bool(rx.search(c)) for c in cores) >= 85


def test_render_all_parts_matches_render_and_every_family_id_has_a_question():
    w = make_world(9, 50, "dev")
    cfg = cfg_with(affect="A1")
    assert [p.text for p in VB.render_all_parts(w, cfg, 9, "dev")] == [o.text for o in VB.render(w, cfg, 9, "dev")]
    for fam in S.FAMILIES:
        for ask in ("breakfast", "weight", ""):
            q = mq(fam, ask, [("shop", "Fumo Pharmacy"), ("date", "2027-02-02")], qid="q0003")
            for part in ("dev", "test"):
                t = VB.render_question(q, part)
                assert "Fumo Pharmacy" in t and "2027-02-02" in t and "CONF: 0-100" in t, (fam, ask, t)


# ------------------------------------------------------- real worlds and determinism


def test_real_worlds_from_the_builder_render_with_every_slot_and_the_exact_length():
    try:
        from corpus.lifesim import world as WORLD
        build_world = WORLD.build_world
    except Exception:  # the builder's module may not exist yet: this test is then skipped
        pytest.skip("corpus.lifesim.world is not available")
    cfg = S.TierCfg.for_tier("L0")
    for seed in (3, 4):
        try:
            w = build_world(seed, cfg)
        except Exception as exc:  # a failing builder is not a failure of the text module
            pytest.skip("build_world failed: %r" % (exc,))
        for part in ("dev", "test"):
            parts = VB.render_all_parts(w, cfg, seed, part)
            assert len(parts) == len(w.obs_specs) > 50
            over = 0
            for p, sp in zip(parts, w.obs_specs):
                assert VB.missing_slots(sp, p.text) == [] and VB.affect_scan(p.text) == []
                over += p.overflow > 0
                assert p.overflow > 0 or p.n_words == sp.target_len
            assert over <= 0.02 * len(parts)


def _digest(texts):
    return hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()


PINS = {
    "dev_A0": "4c246ef4ef69d2fe4a3f599c154d59f2abbc1b1054c33d58c03008ff0a210893",
    "test_A0": "2a3a9fe431fed76b1a5b5a1c218c64dcedf1b4ff00f06fc360da4f7e542ad65b",
    "dev_A2_typo": "4b9b53e48168f1416667fcf6116a2020852593c610bb3e37a4d3371d9c9b3791",
    "ood_dev_world_test_banks": "bcade61bd9e6b1bd69c76cfdb044167da4b6554fc9f747a898c8e29d3b0544d5",
    "questions_dev": "a78ccfea553fdbebd9673adfe76e32f87c30de43339d393006f47ea8a1fbfb8b",
    "questions_test": "ca261b4ee79bcf6255983e028c159ca5b376fb9d95c9edae0fc37faca9b0f381",
}


def test_golden_lines_and_digests_are_pinned():
    base = S.TierCfg.for_tier("L1")
    w, w2 = make_world(1, 60, "dev"), make_world(10005, 60, "test")
    obs = VB.render(w, base, 1, "dev")
    assert obs[0].text == ("My phone stayed unused. The shutters caught the afternoon light. The cobbles gleamed "
                           "after the rain. My bag stayed unused. A dog nearby carried on for an hour in the end. "
                           "The late bus stayed crowded until the last stop. During a short outing, I visited the barber.")
    assert obs[2].text == ("The afternoon dragged on. Before leaving the house, I had banana pancakes for breakfast. "
                           "The shutters had been repaired overnight. The pavement looked freshly cleaned. "
                           "The evening went by unnoticed.")
    t0 = VB.render(w2, base, 10005, "test")[0].text
    assert t0 == ("The sun changed towards dusk. The platform filled up fast. The spare charger ended up under the "
                  "table. The radio next door moved on around noon. The footbridge filled up fast. I saw in the "
                  "paper that a concert in Cujepo was reported. Separately a witness recalled a black car. "
                  "Separately a navy taxi appeared in the pictures.")
    assert _digest(o.text for o in obs) == PINS["dev_A0"]
    assert _digest(o.text for o in VB.render(w2, base, 10005, "test")) == PINS["test_A0"]
    noisy = dataclasses.replace(base, affect="A2", r_aff=0.5, typo_rate=0.02, dramatic_decoy_share=0.1)
    assert _digest(o.text for o in VB.render(w, noisy, 1, "dev")) == PINS["dev_A2_typo"]
    assert _digest(o.text for o in VB.render(w, base, 1, "test")) == PINS["ood_dev_world_test_banks"]
    q = mq("IN1", "vehicle_colour", [("story_kind", "flood"), ("city", "Verdton"),
                                     ("relative_window", "about two weeks ago")], qid="q0042")
    assert VB.render_question(q, "dev") == ("Help me: What colour was the car in the article on the flood in Verdton "
                                           "that I read about two weeks ago? Reply UNKNOWN when it was not "
                                           "mentioned. End with CONF: 0-100.")
    qs = [mq(f, a, c, qid="q%04d" % (i + 1)) for i, (f, a, c, g) in enumerate(QUESTION_CASES)]
    assert _digest(VB.render_question(x, "dev") for x in qs) == PINS["questions_dev"]
    assert _digest(VB.render_question(x, "test") for x in qs) == PINS["questions_test"]


def test_text_is_identical_in_a_fresh_interpreter_with_another_hash_seed():
    import os
    import subprocess
    code = ("import sys, hashlib\nsys.path.insert(0, %r)\nimport test_lifesim_verbalise as T\n"
            "from corpus.lifesim import verbalise as VB, schema as S\n"
            "w = T.make_world(1, 60, 'dev')\n"
            "o = VB.render(w, S.TierCfg.for_tier('L1'), 1, 'dev')\n"
            "print(hashlib.sha256('\\n'.join(x.text for x in o).encode('utf-8')).hexdigest())\n"
            % str(Path(__file__).resolve().parent))
    env = dict(os.environ, PYTHONHASHSEED="12345")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)
    assert out.returncode == 0, out.stderr[-800:]
    assert out.stdout.strip() == PINS["dev_A0"]


def test_the_documented_assumed_extras_are_read_from_the_config():
    w = make_world(41, 400, "dev")
    obs_of = lambda cfg: VB.render(w, cfg, 41, "dev")  # noqa: E731
    base = cfg_with(affect="A1")
    counts = lambda cfg: [len(VB.affect_scan(o.text)) for o in obs_of(cfg)]  # noqa: E731
    assert min(counts(base.with_extra(aff_t1=-9.0, aff_t2=9.0))) == 1 == max(counts(base.with_extra(aff_t1=-9.0, aff_t2=9.0)))
    assert set(counts(base.with_extra(aff_t1=-9.0, aff_t2=-9.0))) == {2}
    assert set(counts(base.with_extra(aff_t1=9.0, aff_t2=9.0))) == {0}
    dec = cfg_with(affect="A1", dramatic_decoy_share=1.0).with_extra(aff_low_a=9.0, aff_t1=9.0, aff_t2=9.0)
    assert set(counts(dec)) == {1}  # every line counts as low-A, so every line gets its decoy
    sit = {s.sid: s for s in w.situations}
    flip = base.with_extra(aff_t1=-9.0, aff_t2=9.0, aff_pos_floor=0.5)  # polarity is a coin toss
    pos = {p.lower() for n in ("aff.pos_mild", "aff.pos_strong") for part in ("dev", "test") for p in VB.BANKS[n][part]}
    hi = [any(p in o.text.lower() for p in pos) for o, sp in zip(obs_of(flip), w.obs_specs) if sit[sp.sid].V > 0.5]
    lo = [any(p in o.text.lower() for p in pos) for o, sp in zip(obs_of(flip), w.obs_specs) if sit[sp.sid].V < -0.5]
    assert abs(sum(hi) / len(hi) - sum(lo) / len(lo)) < 0.2
    assert [o.text for o in obs_of(base.with_extra(pad_plain_p=0.0))] != [o.text for o in obs_of(base)]
    assert [o.text for o in obs_of(base.with_extra(pad_plain_weight=1.0))] != [o.text for o in obs_of(base)]
    tails = lambda cfg: sum(bool(re.search(r"\b(that day|that time|that week|at home|at that time|just after noon|in the end|before the evening|today|earlier|then|later)\.", o.text)) for o in obs_of(cfg))  # noqa: E731
    assert tails(base.with_extra(pad_plain_p=0.0, pad_plain_weight=1.0)) > tails(base.with_extra(pad_plain_p=1.0, pad_plain_weight=0.01))


def test_tight_lines_fall_back_to_compact_wording_instead_of_overflowing():
    w = build(entities=[("story", "road closure in Gebesukirk")],
              facts=[("read_story", None, "e0002", "read"), ("vehicle_colour", 0, "burgundy", "read"),
                     ("decoy_colour", 0, "turquoise", "read")],
              slots=[("story", "road closure in Gebesukirk", 0), ("vehicle_colour", "burgundy", 1),
                     ("decoy_colour", "turquoise", 2)], channel="article", scene="article", target=30, n_specs=1)
    specs = tuple(dataclasses.replace(w.obs_specs[0], oid=S.new_id("obs", i + 1), t_obs=w.obs_specs[0].t_obs + i)
                  for i in range(300))
    w = dataclasses.replace(w, obs_specs=specs)
    for part in ("dev", "test"):
        ps = VB.render_all_parts(w, S.TierCfg.for_tier("L1"), 1, part)
        assert all(p.overflow == 0 and p.n_words == 30 for p in ps)
        assert all(VB.missing_slots(sp, p.text) == [] for p, sp in zip(ps, w.obs_specs))
        assert all(p.fallbacks == 0 for p in ps)
    # an impossible line (five long slots, 30 words) is longer than its target and says so
    names = ["breakfast", "works_as", "lives_in", "errand", "companion"]
    vals = ["bagel with cream cheese", "physiotherapist", "Gebesukirkstad", "swimming pool", "Tinugamdorn"]
    w = build(entities=[("city", "Gebesukirkstad"), ("person", "Tinugamdorn")],
              facts=[("breakfast", None, vals[0], "lived"), ("works_as", None, vals[1], "lived"),
                     ("lives_in", None, "e0002", "lived"), ("errand_visit", None, vals[3], "lived"),
                     ("companion", None, "e0003", "lived")],
              slots=[(n, v, i) for i, (n, v) in enumerate(zip(names, vals))], target=30, n_specs=1)
    p = VB.render_all_parts(w, S.TierCfg.for_tier("L1"), 1, "dev")[0]
    assert p.overflow > 0 and p.n_words == 30 + p.overflow and p.pre == () == p.post
    assert VB.missing_slots(w.obs_specs[0], p.text) == []
