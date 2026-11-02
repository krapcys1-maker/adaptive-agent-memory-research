"""Tests for LifeSim worlds (corpus.lifesim.world, scenes): determinism, check_world on many
seeds and on hand-built worlds, the Day-1 family structures, situation-first hosting (G-HOST and
support by construction), the arousal and corr(n, k) properties, rehearsal, tiers and the
delete_events operator. Standard library and pytest only."""

from __future__ import annotations

import dataclasses
import functools
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import channel as chan  # noqa: E402
from corpus.lifesim import scenes as S  # noqa: E402
from corpus.lifesim import vocab as V  # noqa: E402
from corpus.lifesim import world as W  # noqa: E402
from corpus.lifesim.appraisal import pearson, summary  # noqa: E402
from corpus.lifesim.rng import stream, zipf_probs  # noqa: E402
from corpus.lifesim.schema import (Card, Entity, Fact, Feats, Mention, ObsSpec, Prior, Situation,  # noqa: E402
                                   Slot, TierCfg, World, load_world, save_world)

L0, L1 = TierCfg.for_tier("L0"), TierCfg.for_tier("L1")


@functools.lru_cache(maxsize=None)
def worlds(tier: str = "L1", n: int = 12, start: int = 0, **cfg_changes) -> tuple:
    cfg = dataclasses.replace(TierCfg.for_tier(tier), **dict(cfg_changes))
    return tuple(W.build_world(s, cfg) for s in range(start, start + n))


def ents(w):
    return {e.eid: e for e in w.entities}


def facts_of(w, pred):
    return [f for f in w.facts if f.pred == pred]


def lines_of(w, fid):
    return [(o, m) for o in w.obs_specs for m in o.mentions if m.fid == fid]


def host_dec(w):
    return W.situation_deciles(w)


# ------------------------------------------------------------------ determinism and digests


def test_build_is_deterministic_and_seed_sensitive():
    a, b = W.build_world(3, L0), W.build_world(3, L0)
    assert a == b and a.digest() == b.digest() == W.world_digest(a)
    assert W.build_world(4, L0).digest() != a.digest()
    assert W.build_world(3, L1).digest() != a.digest()


def test_digest_is_independent_of_pythonhashseed_and_of_the_process():
    code = ("import sys; sys.path.insert(0, %r)\n"
            "from corpus.lifesim.world import build_world\n"
            "from corpus.lifesim.schema import TierCfg\n"
            "print(build_world(0, TierCfg.for_tier('L0')).digest()); print(build_world(5, TierCfg.for_tier('L1')).digest())"
            % str(ROOT / "scripts"))
    outs = []
    for hs in ("1", "4242"):
        env = dict(os.environ, PYTHONHASHSEED=hs)
        outs.append(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env,
                                   check=True).stdout.split())
    assert outs[0] == outs[1]
    assert outs[0] == [W.build_world(0, L0).digest(), W.build_world(5, L1).digest()]


def test_digest_ignores_rendering_and_channel_choices_but_not_structure():
    base = W.build_world(1, L0)
    same = W.build_world(1, dataclasses.replace(L0, affect="A2", r_aff=0.5, typo_rate=0.02, flash_share=0.2,
                                                v_mix=(0.2, 0.2, 0.6), nu=0.1, reliability_primary=0.5))
    assert same.digest() == base.digest()
    assert base.with_channel(chan.make_channel(base, "TRUE", 0.7, 0.3, 1)).digest() == base.digest()
    assert W.build_world(1, dataclasses.replace(L0, rehearsal="natural")).digest() != base.digest()
    assert W.build_world(1, dataclasses.replace(L0, routine_rate=12.0)).digest() != base.digest()


def test_save_and_load_round_trip(tmp_path):
    w = worlds("L0", 1)[0]
    w = w.with_channel(chan.make_channel(w, "TRUE", 0.7, 0.3, 2))
    save_world(w, tmp_path / "w")
    back = load_world(tmp_path / "w")
    assert back.digest() == w.digest() and back == w and back.extra("hosting") == w.extra("hosting")


def test_partition_names_follow_the_seed():
    dev, test = W.build_world(7, L0), W.build_world(10007, L0)
    assert dev.partition == "dev" and test.partition == "test"
    for w in (dev, test):
        for e in w.entities:
            if e.kind in ("person", "city", "street", "shop", "org"):
                assert V.partition_of_name(e.name.split()[0]) == w.partition, e
    assert not {e.name for e in dev.entities} & {e.name for e in test.entities}
    forced = W.build_world(7, dataclasses.replace(L0, name_partition="test"))
    assert forced.partition == "test" and V.partition_of_name(forced.card.name) == "test"


# ------------------------------------------------------------------------------ check_world


@pytest.mark.parametrize("tier,n", [("L0", 20), ("L1", 20), ("L2", 2), ("L3", 1)])
def test_check_world_passes_on_many_seeds(tier, n):
    for w in worlds(tier, n):
        assert W.check_world(w) == [], (tier, w.seed)


def test_check_world_passes_with_other_dials():
    for kw in (dict(rehearsal="natural"), dict(rehearsal="strong"), dict(mappings=("M3",)),
               dict(periphery_goal_relevant=1), dict(affect="A1", n_confusers_max=8)):
        for w in worlds("L1", 3, 100, **kw):
            assert W.check_world(w) == [], kw
    for w in worlds("L1", 2, 200, extra=(("host_top_boost", 3.0), ("ep4_pairs_per_30d", 12.0))):
        assert W.check_world(w) == []


def hand_world():
    """A world built by hand from schema rows: 3 days, 3 situations, 4 facts, 3 lines."""
    cfg = dataclasses.replace(L0, days=3, min_pool=1, n_persons=1, n_foods_min=40, n_foods_max=40, obs_per_day=1.0)
    dishes = tuple(V.DISHES[:40])
    es = (Entity(eid="e0001", kind="person", name="Kamuda"), Entity(eid="e0002", kind="person", name="Remi", bond=0.6),
          Entity(eid="e0003", kind="city", name="Boster"), Entity(eid="e0004", kind="street", name="Dadu Street"),
          Entity(eid="e0005", kind="shop", name="Gamo Bakery"))
    fs = (Fact(fid="f00001", subj="e0001", pred="breakfast", obj=dishes[3], vfrom=0, vto=0),
          Fact(fid="f00002", subj="e0001", pred="lives_in", obj="e0003", vfrom=0, centrality=0.9),
          Fact(fid="f00003", subj="e0001", pred="companion", obj="e0002", vfrom=1, vto=1, centrality=0.7),
          Fact(fid="f00004", subj="e0001", pred="car_colour", obj="red", vfrom=1, vto=1, centrality=0.05))
    f = Feats(goal_rel=0.1, surprisal_bits=2.0, stakes=0.1)
    ss = (Situation(sid="s00001", day=0, minute=480, scene="routine", feats=f, A=0.1, facts=("f00001", "f00002")),
          Situation(sid="s00002", day=1, minute=600, scene="minor", actors=("e0002",),
                    feats=Feats(goal_rel=0.3, surprisal_bits=6.0, stakes=0.1), A=0.3, facts=("f00003", "f00004")),
          Situation(sid="s00003", day=2, minute=500, scene="routine", feats=f, A=0.12))
    os_ = (ObsSpec(oid="o00001", t_obs=500, channel="diary", sid="s00001",
                   mentions=(Mention(fid="f00001"), Mention(fid="f00002")),
                   slots=(Slot(name="breakfast", value=dishes[3], fid="f00001"),
                          Slot(name="lives_in", value="Boster", fid="f00002")), target_len=40),
           ObsSpec(oid="o00002", t_obs=1440 + 620, channel="chat", sid="s00002",
                   mentions=(Mention(fid="f00003"), Mention(fid="f00004")),
                   slots=(Slot(name="companion", value="Remi", fid="f00003"),
                          Slot(name="car_colour", value="red", fid="f00004")), target_len=44),
           ObsSpec(oid="o00003", t_obs=2 * 1440 + 510, channel="log", sid="s00003", target_len=35))
    w = World(seed=1, cfg=cfg, entities=es, facts=fs, situations=ss, obs_specs=os_, card=Card(name="Kamuda"),
              priors=(Prior(slot="breakfast", values=dishes, probs=zipf_probs(40, 0.6)),))
    return w.with_extra("hosting", {"chains": {"lives_in": ["f00002"], "works_as": []}})


def test_a_hand_built_world_passes_and_every_break_is_caught():
    w = hand_world()
    assert W.check_world(w) == []
    replace = dataclasses.replace

    def fails(mutant, needle):
        problems = W.check_world(mutant)
        assert any(needle in p for p in problems), (needle, problems)

    fs, ss, os_ = w.facts, w.situations, w.obs_specs
    fails(replace(w, situations=(replace(ss[0], facts=("f00001", "f00002", "f00003")),) + ss[1:]), "hosted 2 times")
    fails(replace(w, situations=(replace(ss[0], facts=("f00001",)),) + ss[1:]), "hosted 0 times")
    fails(replace(w, obs_specs=(replace(os_[0], mentions=(Mention(fid="f00001"), Mention(fid="f00003"))),) + os_[1:]),
          "does not host")
    fails(replace(w, obs_specs=(replace(os_[0], slots=(os_[0].slots[0], Slot(name="lives_in", value="Dadu Street",
                                                                             fid="f00002"))),) + os_[1:]), "does not render")
    fails(replace(w, obs_specs=(replace(os_[0], slots=os_[0].slots[:1]),) + os_[1:]), "disagree")
    fails(replace(w, obs_specs=os_[:1] + os_[2:]), "never stated")
    fails(replace(w, obs_specs=(replace(os_[0], t_obs=100),) + os_[1:]), "before its situation")
    fails(replace(w, obs_specs=(replace(os_[0], target_len=999),) + os_[1:]), "target_len")
    fails(replace(w, situations=(replace(ss[0], A=1.5),) + ss[1:]), "out of range")
    fails(replace(w, situations=(replace(ss[0], A=0.9),) + ss[1:]), "relevance cap")
    fails(replace(w, situations=(replace(ss[0], day=7),) + ss[1:]), "outside the life")
    fails(replace(w, facts=(fs[0], replace(fs[1], obj="e0002")) + fs[2:]), "not an entity of kind:city")
    fails(replace(w, facts=(replace(fs[0], obj="a unicorn"),) + fs[1:]), "outside the habit pool")
    fails(replace(w, facts=fs[:3] + (replace(fs[3], obj="plaid"),)), "not in pool:colours")
    fails(replace(w, facts=(fs[0], replace(fs[1], vto=1)) + fs[2:]), "must be open")
    fails(replace(w, facts=(replace(fs[0], vfrom=1, vto=1),) + fs[1:]), "vfrom differs")
    fails(replace(w, facts=(replace(fs[0], supersedes="f99999"),) + fs[1:]), "supersedes unknown")
    fails(replace(w, situations=ss[:1] + (replace(ss[1], facts=("f00003",)), ss[2])), "hosted 0 times")
    fails(replace(w, situations=(replace(ss[0], facts=("f00001", "f00002", "f00004")),
                                 replace(ss[1], facts=("f00003",)), ss[2])), "without its central companion")
    fails(replace(w, entities=w.entities[:2] + (replace(w.entities[2], name="Fela"),) + w.entities[3:]), "partition")
    fails(replace(w, entities=w.entities[:4]), "min_pool")
    fails(replace(w, priors=(Prior(slot="breakfast", values=tuple(V.DISHES[:40]), probs=(0.5,) + (0.5 / 39,) * 39),)),
          "entropy")
    fails(replace(w, extras=()), "hosting record")
    fails(replace(w, obs_specs=os_[:2]), "far from obs_per_day")
    fails(replace(w, obs_specs=(replace(os_[0], source="e9999"),) + os_[1:]), "unknown source")
    fails(replace(w, entities=(w.entities[0], replace(w.entities[1], name="Kamuda")) + w.entities[2:]), "duplicate entity names")
    fails(replace(w, entities=w.entities[:1] + w.entities[2:]), "too few people")
    fails(replace(w, entities=(w.entities[0], replace(w.entities[1], bond=1.5)) + w.entities[2:]), "bond out of range")


def test_a_broken_chain_and_a_correlated_stream_are_caught():
    w = worlds("L1", 1, 3)[0]
    chain = [f for f in w.facts if f.pred == "lives_in"]
    assert len(chain) >= 2
    mutant = dataclasses.replace(w, facts=tuple(dataclasses.replace(f, supersedes="") if f.fid == chain[1].fid else f
                                                for f in w.facts))
    assert any("broken lives_in chain" in p for p in W.check_world(mutant))
    gap = dataclasses.replace(w, facts=tuple(dataclasses.replace(f, vto=f.vto - 1) if f.fid == chain[0].fid else f
                                             for f in w.facts))
    assert any("contiguous" in p for p in W.check_world(gap))
    # surprise equal to stakes in every situation: corr(n, k) = 1
    corr = dataclasses.replace(w, situations=tuple(
        dataclasses.replace(s, feats=dataclasses.replace(s.feats, surprisal_bits=8.0 * s.feats.stakes))
        for s in w.situations))
    assert any("corr(surprise, stakes)" in p for p in W.check_world(corr))


def test_a_stated_twice_closing_time_and_a_type_hosted_story_are_caught():
    w = worlds("L1", 1, 4)[0]
    ct = facts_of(w, "closing_time")
    dup = dataclasses.replace(w, facts=tuple(dataclasses.replace(f, subj=ct[0].subj) if f.fid == ct[1].fid else f
                                             for f in w.facts))
    assert any("stated twice" in p for p in W.check_world(dup))
    vc = facts_of(w, "vehicle_colour")[0]
    host = w.host(vc.fid)
    lonely = dataclasses.replace(w, situations=tuple(
        dataclasses.replace(s, facts=tuple(x for x in s.facts if w.fact(x).pred != "read_story")) if s.sid == host.sid else s
        for s in w.situations))
    assert any("hosted 0 times" in p or "without the story" in p for p in W.check_world(lonely))
    # a world with the wrong name partition for a person
    tw = W.build_world(10009, L0)
    bad = dataclasses.replace(tw, partition="dev")
    assert any("partition" in p for p in W.check_world(bad))


# ------------------------------------------------------------------------- Day-1 structures


def test_every_fact_is_hosted_once_and_lines_mention_only_their_own_facts():
    for w in worlds("L1", 6):
        host = {}
        for s in w.situations:
            for fid in s.facts:
                assert fid not in host
                host[fid] = s.sid
        assert set(host) == {f.fid for f in w.facts}
        for o in w.obs_specs:
            assert all(host[m.fid] == o.sid for m in o.mentions)
            assert {sl.fid for sl in o.slots if sl.fid} == {m.fid for m in o.mentions}
            assert all(sl.value for sl in o.slots)


def test_ep1_breakfast_episodes_follow_the_habit_prior():
    top3_hits = top3_expected = n = 0
    first_of_day = total_hosts = 0
    for w in worlds("L1", 12):
        bf, prior = facts_of(w, "breakfast"), w.prior("breakfast")
        assert 40 <= len(bf) <= 60 and 40 <= len(prior.values) <= 60
        assert prior.entropy_bits() >= 4.5 and sum(prior.probs[:3]) < 0.30 and set(prior.values) <= set(V.DISHES)
        days = [f.vfrom for f in bf]
        assert len(set(days)) == len(days)
        for f in bf:
            assert (f.vto, f.src, f.subj) == (f.vfrom, "lived", w.entities[0].eid) and f.obj in prior.values
            assert f.surprisal_bits == pytest.approx(-math.log2(prior.p_of(f.obj)), abs=1e-5)
            ((o, m),) = lines_of(w, f.fid)
            assert m.role == "assert" and o.day == f.vfrom
            assert Slot(name="breakfast", value=f.obj, fid=f.fid) in o.slots
        top3 = set(prior.values[:3])  # the generator's rank order is the prior's order
        top3_hits += sum(1 for f in bf if f.obj in top3)
        for f in bf:
            same_day = [s.sid for s in w.situations if s.day == f.vfrom]
            first_of_day += w.host(f.fid).sid == same_day[0]
            total_hosts += 1
        top3_expected += len(bf) * sum(prior.probs[:3])
        n += len(bf)
    assert abs(top3_hits - top3_expected) / n < 0.05  # realised episodes follow the prior (not uniform)
    assert first_of_day / total_hosts < 0.3  # a day's breakfast is mentioned in any of its lines


def test_se_identity_chains_and_week_one_introductions():
    for w in worlds("L1", 12):
        for pred in ("lives_in", "works_as"):
            chain = sorted(facts_of(w, pred), key=lambda f: f.vfrom)
            assert 2 <= len(chain) <= 1 + L1.chain_depth_max
            assert chain[0].vfrom < 7 and chain[1].vfrom >= 8 and len({f.obj for f in chain}) == len(chain)
            for i, f in enumerate(chain):
                roles = [m.role for _, m in lines_of(w, f.fid)]
                first = "assert" if i == 0 else "update"
                assert roles.count(first) == 1 and set(roles) <= {first, "recall"}
                assert f.supersedes == (chain[i - 1].fid if i else "")
                if f.vto is not None:  # the stale value is mentioned about 6 times, the new one once
                    assert roles.count("recall") == min(L1.se_stale_mentions, f.vto - f.vfrom)
                    assert all(f.vfrom < o.day <= f.vto and o.frame == "recall" for o, m in lines_of(w, f.fid)
                               if m.role == "recall")
                else:
                    assert roles == [first]
        rel = facts_of(w, "relation")
        assert len(rel) == round(0.6 * L1.n_persons) and len({f.subj for f in rel}) == len(rel)
        assert all(f.vfrom < 7 and f.src == "told" and len(lines_of(w, f.fid)) == 1 and f.obj in V.RELATIONS
                   for f in rel)
        assert all(ents(w)[f.subj].kind == "person" and f.subj != w.entities[0].eid for f in rel)
        assert len({w.host(f.fid).sid for f in rel}) >= 13  # spread over week one, not piled into a few lines


def test_incidental_updates_follow_their_dial():
    def share(**kw):
        ups = [o for w in worlds("L0", 60, 700, **kw) for o in w.obs_specs for m in o.mentions if m.role == "update"]
        assert len(ups) >= 100
        return sum(1 for o in ups if o.frame == "incidental") / len(ups)

    assert share(incidental_update_share=0.0) == 0.0 and share(incidental_update_share=1.0) == 1.0
    assert 0.1 <= share(incidental_update_share=0.2) <= 0.3


def test_updates_start_after_week_one():
    for w in worlds("L0", 60, 700, incidental_update_share=0.2):
        for pred in S.CHAIN_PREDS:
            chain = sorted(facts_of(w, pred), key=lambda f: f.vfrom)
            assert chain[0].vfrom < 7 and all(f.vfrom >= 8 for f in chain[1:]), (w.seed, pred)


def test_lines_carry_context_slots_for_their_subjects():
    for w in worlds("L1", 3):
        e = ents(w)
        for f in facts_of(w, "relation"):
            ((o, _),) = lines_of(w, f.fid)
            assert Slot(name="person", value=e[f.subj].name, fid="") in o.slots
        for f in facts_of(w, "closing_time"):
            ((o, _),) = lines_of(w, f.fid)
            assert Slot(name="shop", value=e[f.subj].name, fid="") in o.slots
        for f in facts_of(w, "vehicle_colour"):
            ((o, _),) = lines_of(w, f.fid)
            assert [sl.name for sl in o.slots].count("story") == 1  # the read_story slot, no duplicate
        for f in facts_of(w, "breakfast"):
            ((o, _),) = lines_of(w, f.fid)
            assert all(sl.fid for sl in o.slots if sl.name == "breakfast")


def test_closer_people_appear_more_often_and_norm_violations_have_both_signs():
    signs = [0, 0]
    for w in worlds("L1", 6):
        e = ents(w)
        assert all(s.feats.bond == e[s.actors[0]].bond for s in w.situations if s.actors and s.scene != "article")
        assert not any(s.feats.bond for s in w.situations if not s.actors and s.scene not in ("article",))
        count = {}
        for s in w.situations:
            for a in s.actors:
                count[a] = count.get(a, 0) + 1
            if s.feats.norm:
                signs[s.feats.norm < 0] += 1
        people = [x for x in w.entities if x.kind == "person"][1:]
        assert pearson([x.bond for x in people], [count.get(x.eid, 0) for x in people]) > 0.3
    assert 0.4 < signs[1] / sum(signs) < 0.6


def test_in1_stories_with_decoys_and_confusers():
    decoy = [0, 0]
    peripheral = [0, 0]
    for w in worlds("L1", 12):
        e = ents(w)
        stories = [x for x in w.entities if x.kind == "story"]
        assert len({x.name for x in stories}) == len(stories) >= 7  # >= 6 other articles carry a colour
        assert all(x.name.split(" in ")[0] in V.STORY_KINDS for x in stories)
        assert len(facts_of(w, "read_story")) == len(facts_of(w, "vehicle_colour")) == len(stories)
        for f in facts_of(w, "vehicle_colour"):
            assert f.src == "read" and e[f.subj].kind == "story" and f.obj in V.COLOURS
            host = w.host(f.fid)
            assert host.scene == "article" and host.actors == ()
            ((o, _),) = lines_of(w, f.fid)
            assert o.channel == "article" and e[o.source].kind == "org" and o.day == f.vfrom
            ds = [d for d in facts_of(w, "decoy_colour") if d.subj == f.subj]
            assert len(ds) <= 1 and all(d.obj != f.obj and w.host(d.fid).sid == host.sid for d in ds)
            decoy[0] += bool(ds)
            decoy[1] += 1
            peripheral[0] += S.role_of(f.centrality) == "peripheral"
            peripheral[1] += 1
        for f in facts_of(w, "read_story"):
            assert f.src == "read" and f.vfrom == f.vto == w.host(f.fid).day
    assert decoy[0] / decoy[1] >= 0.5  # a decoy colour sits in the same article in >= 50% of the items
    assert abs(peripheral[0] / peripheral[1] - L1.peripheral_share) < 0.08


def test_ep4_central_and_peripheral_pairs_share_one_situation_and_line():
    for w in worlds("L1", 8):
        pairs = 0
        for s in w.situations:
            by = {w.fact(x).pred: w.fact(x) for x in s.facts}
            if "car_colour" not in by:
                continue
            pairs += 1
            comp, car = by["companion"], by["car_colour"]
            assert comp.obj == s.actors[0] and comp.centrality >= 0.55 and car.centrality <= 0.2
            assert S.role_of(comp.centrality) == "central" and S.role_of(car.centrality) == "peripheral"
            assert any({m.fid for m in o.mentions} >= {comp.fid, car.fid} for o in w.obs_specs if o.sid == s.sid)
        assert 44 <= pairs <= 48 == len(facts_of(w, "car_colour")) + (48 - len(facts_of(w, "car_colour")))  # 8 per 30 days
        assert len(facts_of(w, "companion")) == len(facts_of(w, "car_colour"))  # trips use their own predicate
    for w in worlds("L1", 2, 0, periphery_goal_relevant=1):
        assert all(S.role_of(f.centrality) == "central" for f in facts_of(w, "car_colour"))


def test_in4_sleeper_remarks_are_single_quiet_and_never_repeated():
    quiet = []
    for w in worlds("L1", 12):
        e = ents(w)
        ct = facts_of(w, "closing_time")
        shops = [f.subj for f in ct]
        assert len(set(shops)) == len(shops) <= int(0.8 * len(w.entities_of("shop")))
        assert len(w.entities_of("shop")) - len(set(shops)) >= 6  # shops never mentioned exist (ME1 traps)
        dec = host_dec(w)
        for f in ct:
            assert f.obj in V.TIMES and f.src == "told" and e[f.subj].kind == "shop" and f.vto is None
            s = w.host(f.fid)
            assert s.scene == "remark" and len(s.actors) == 1
            (street,) = [w.fact(x) for x in s.facts if w.fact(x).pred == "on_street"]
            assert street.subj == f.subj and e[street.obj].kind == "street" and street.src == "told"
            ((o, _),) = lines_of(w, f.fid)
            assert o.source == s.actors[0] and o.channel in ("dialogue", "chat")
            quiet.append(dec[s.sid] <= 1)
    assert sum(quiet) / len(quiet) >= 0.6  # the remark sits in the lowest two deciles


def test_ep3c_visits_and_lookalikes():
    counts = set()
    per = {}
    for w in worlds("L1", 8):
        nar = w.entities[0].eid
        visits = facts_of(w, "errand_visit")
        own, other = [f for f in visits if f.subj == nar], [f for f in visits if f.subj != nar]
        assert {f.obj for f in own} == {name for name, _ in S.ERRAND_RATES}
        assert len({(f.vfrom, f.obj, f.subj) for f in visits}) == len(visits)
        assert 0.25 < len(other) / len(own) < 0.55 and all(ents(w)[f.subj].kind == "person" for f in other)
        assert all(f.vto == f.vfrom and f.obj in V.ERRANDS and 0.1 <= f.centrality <= 0.4 for f in visits)
        assert all(f.centrality == pytest.approx(0.1 + 0.3 * w.host(f.fid).feats.goal_rel, abs=1e-6) for f in visits)
        for name, rate in S.ERRAND_RATES:
            per[name] = per.get(name, 0) + sum(1 for f in own if f.obj == name) / (L1.days / 30.0)
        for name, _ in S.ERRAND_RATES:
            days = [f.vfrom for f in own if f.obj == name]
            counts |= {sum(1 for d in days if a <= d < a + 60) for a in range(0, 121, 20)}
    assert {1, 2, 3, 4, 5, 6, 7, 8} <= counts and max(counts) >= 10  # windows with 1-8 and more visits
    expected = {"dentist": 0.6, "barber": 1.0, "library": 1.6, "gym": 2.4, "pharmacy": 3.2, "market": 4.4}
    assert dict(S.ERRAND_RATES) == expected
    for name, rate in expected.items():  # the realised visit rates are the documented ones
        assert abs(per[name] / 8 - rate) <= 0.25 * rate + 0.1, (name, per[name] / 8, rate)


def test_me1_absences_and_traps_exist():
    for w in worlds("L1", 8):
        bf_days = {f.vfrom for f in facts_of(w, "breakfast")}
        assert any(d not in bf_days and (d - 1 in bf_days or d + 1 in bf_days) for d in range(1, 179))
        persons = [x.eid for x in w.entities if x.kind == "person"][1:]
        assert len(persons) - len({f.subj for f in facts_of(w, "relation")}) >= 12
        assert len(w.entities_of("city")) - len({f.obj for f in facts_of(w, "visited")}) >= 20
        assert facts_of(w, "visited") and all(f.vto > f.vfrom for f in facts_of(w, "visited"))


# ------------------------------------------------------------- situation-first hosting (G-HOST)


def test_hosting_quotas_are_flat_across_arousal_deciles_for_every_flexible_type():
    for w in worlds("L1", 12):
        prof = W.host_profile(w, 10)
        for pred, spread in (("breakfast", 2), ("car_colour", 2), ("errand_visit", 4)):
            row = prof[pred]
            assert max(row) - min(row) <= spread, (w.seed, pred, row)
            if pred == "breakfast":
                row = prof["vehicle_colour"]  # stories too: balanced donors, a little jitter from the repair
                assert max(row) - min(row) <= 5, (w.seed, row)
            assert min(row) >= 4 or pred == "errand_visit" and min(row) >= 7  # support in every decile
        assert w.extra("hosting")["shortfall"] == {"breakfast": 0, "companion": 0, "visit": 0}


def test_fact_type_is_independent_of_arousal_tercile():
    table = {p: [0, 0, 0] for p in ("breakfast", "car_colour", "errand_visit")}
    story = [0, 0, 0]
    for w in worlds("L1", 12):
        prof = W.host_profile(w, 3)
        for pred in table:
            table[pred] = [a + b for a, b in zip(table[pred], prof[pred])]
        story = [a + b for a, b in zip(story, prof["vehicle_colour"])]
    chi2, dof, p = W.chi_square_independence(list(table.values()))
    assert dof == 4 and p >= 0.2, (chi2, p)
    # third-party stories borrow the arousal of donors drawn from a balanced decile sequence: flat as well
    assert all(0.29 <= x / sum(story) <= 0.38 for x in story), story
    chi2, dof, p = W.chi_square_independence(list(table.values()) + [story])
    assert p >= 0.2, (chi2, p)


def test_top_decile_boost_is_the_same_for_every_flexible_type():
    for w in worlds("L1", 8, 0, extra=(("host_top_boost", 3.0),)):
        assert W.check_world(w) == []
    tops = {}
    for w in worlds("L1", 8, 0, extra=(("host_top_boost", 3.0),)):
        for pred, row in W.host_profile(w, 10).items():
            if pred in ("breakfast", "car_colour", "errand_visit"):
                t = tops.setdefault(pred, [0, 0, 0])
                t[0] += row[9]
                t[1] += row[0]
                t[2] += sum(row)
    for pred, (top, low, tot) in tops.items():
        assert 0.21 <= top / tot <= 0.29 and 0.06 <= low / tot <= 0.11, (pred, top / tot, low / tot)  # 3/12 and 1/12


def test_hosting_that_outgrows_its_support_reports_a_shortfall_and_adds_no_lines():
    base = worlds("L0", 1, 0)[0]
    greedy = worlds("L0", 1, 0, extra=(("visit_rate_scale", 40.0), ("ep4_pairs_per_30d", 400.0)))[0]
    short = greedy.extra("hosting")["shortfall"]
    assert short["visit"] > 0 and short["companion"] > 0 and short["breakfast"] == 0
    assert W.check_world(greedy) == []
    assert len(facts_of(greedy, "errand_visit")) > 5 * len(facts_of(base, "errand_visit"))
    assert len(greedy.obs_specs) == len(base.obs_specs) and len(greedy.situations) == len(base.situations)


def test_chi_square_helper_matches_hand_values():
    chi2, dof, p = W.chi_square_independence([[10, 20], [20, 10]])
    assert chi2 == pytest.approx(6.6667, abs=1e-3) and dof == 1 and p == pytest.approx(0.00982, abs=2e-4)
    assert W.chi_square_independence([[5, 5, 5], [5, 5, 5]])[2] == pytest.approx(1.0)
    assert W.chi_square_independence([[3, 0], [4, 0]]) == (0.0, 0, 1.0)  # an empty column leaves no table
    assert W.chi_square_independence([[30, 10, 5], [5, 10, 30]])[2] < 1e-6


# ------------------------------------------------------------------------ appraisal in worlds


def test_arousal_is_right_skewed_and_corr_surprise_stakes_is_small():
    by_map = {"M1": [], "M2": []}
    pooled, high_lines, months, nks = [], 0, 0.0, []
    for tier, n in (("L0", 30), ("L1", 20)):
        for w in worlds(tier, n, 300):
            by_map[w.mapping] += [s.A for s in w.situations]
            pooled += [s.A for s in w.situations]
            high_lines += sum(1 for a in chan.obs_arousal(w) if a >= 0.7)
            months += w.cfg.days / 30.0
            nk = pearson([s.feats.surprise(8.0) for s in w.situations], [s.feats.stakes for s in w.situations])
            nks.append(nk)
            assert nk <= 0.8 * w.cfg.max_corr_nk + 1e-9  # the generator repairs what would breach the gate
    s = summary(pooled)
    assert 0.16 <= s["mean"] <= 0.26 and 0.10 <= s["sd"] <= 0.19 and 0.72 <= s["below_03"] <= 0.90
    assert 1.5 <= high_lines / months <= 8.0  # a few high-arousal lines a month
    assert summary(by_map["M2"])["mean"] > summary(by_map["M1"])["mean"] + 0.05 and by_map["M1"] and by_map["M2"]
    assert max(nks) <= 0.24 and sum(nks) / len(nks) < 0.2 and min(nks) > -0.1


def test_scenes_are_ordered_by_loudness():
    acc = {}
    for w in worlds("L1", 6, 400):
        for s in w.situations:
            acc.setdefault((w.mapping, s.scene), []).append(s.A)
    for m in ("M1", "M2"):
        mean = {sc: sum(v) / len(v) for (mm, sc), v in acc.items() if mm == m}
        assert mean["remark"] < mean["routine"] < mean["minor"] < mean["major"]
        assert mean["article"] < mean["minor"] and mean["health"] > mean["minor"]


def test_surprise_stakes_repair_breaks_a_perfect_dependence_deterministically():
    cfg = L1
    sits = [Situation(sid="s%05d" % (i + 1), day=i // 5, minute=500, scene="minor",
                      feats=Feats(goal_rel=0.2, surprisal_bits=(7.0 if i % 2 else 3.0), stakes=(0.9 if i % 2 else 0.1)),
                      A=0.3, V=0.0) for i in range(60)]
    before = pearson([s.feats.surprise(8.0) for s in sits], [s.feats.stakes for s in sits])
    assert before > 0.95
    a, b = list(sits), list(sits)
    W._repair_surprise_stakes(1, cfg, "M1", a)
    W._repair_surprise_stakes(1, cfg, "M1", b)
    assert a == b  # deterministic
    after = pearson([s.feats.surprise(8.0) for s in a], [s.feats.stakes for s in a])
    assert after <= 0.8 * cfg.max_corr_nk
    changed = [x for x, y in zip(a, sits) if x != y]
    assert 0 < len(changed) < len(sits) and all(x.feats.stakes == y.feats.stakes for x, y in zip(a, sits))
    ok = [Situation(sid="s%05d" % (i + 1), day=0, minute=500, scene="minor", feats=Feats(surprisal_bits=i % 8 * 1.0,
                    stakes=(i * 7 % 10) / 10), A=0.2) for i in range(80)]
    keep = list(ok)
    W._repair_surprise_stakes(1, cfg, "M1", keep)
    assert keep == ok  # nothing to repair, nothing touched


def test_mood_is_the_decayed_daily_mean_of_valence_times_arousal():
    from corpus.lifesim import appraisal as ap

    for w in worlds("L0", 2):
        by_day = {}
        for s in w.situations:
            by_day.setdefault(s.day, []).append(s)
        m = 0.0
        for d in range(w.cfg.days):
            day = by_day.get(d, [])
            assert all(s.mood == m for s in day)
            m = ap.mood_step(m, [(s.A, s.V) for s in day], w.cfg)


# ---------------------------------------------------------------------------- the stream


def test_stream_shape_and_length_distribution():
    lens, evid, per_day_mean, kinds = [], ([], []), [], {}
    pairs_len, pairs_a = [], []
    for w in worlds("L1", 12):
        t = [o.t_obs for o in w.obs_specs]
        assert t == sorted(t) and [o.oid for o in w.obs_specs] == ["o%05d" % (i + 1) for i in range(len(t))]
        per_day = {}
        for o in w.obs_specs:
            per_day[o.day] = per_day.get(o.day, 0) + 1
        assert min(per_day.values()) >= w.cfg.obs_min and len(per_day) == w.cfg.days
        assert max(per_day.values()) <= w.cfg.obs_max + 8
        per_day_mean.append(len(t) / w.cfg.days)
        a = chan.obs_arousal(w)
        for o, x in zip(w.obs_specs, a):
            lens.append(o.target_len)
            (evid[0] if o.mentions else evid[1]).append(o.target_len)
            kinds.setdefault(w.situation(o.sid).scene, []).append(o.target_len)
        pairs_len += [o.target_len for o in w.obs_specs]
        pairs_a += a
    assert 5.6 <= sum(per_day_mean) / len(per_day_mean) <= 6.9
    n = len(lens)
    assert all(0.02 <= lens.count(v) / n <= 0.046 for v in range(30, 61))  # one flat distribution
    assert abs(pearson(pairs_len, pairs_a)) <= 0.05  # independent of arousal
    assert abs(sum(evid[0]) / len(evid[0]) - sum(evid[1]) / len(evid[1])) <= 1.0  # ...and of evidence status
    assert all(43.0 <= sum(v) / len(v) <= 47.0 for v in kinds.values() if len(v) > 100)  # ...and of kind


def test_rehearsal_levels():
    off, nat, strong = (worlds("L1", 6, 0), worlds("L1", 6, 0, rehearsal="natural"),
                        worlds("L1", 6, 0, rehearsal="strong"))
    assert not any(o.frame == "retell" for w in off for o in w.obs_specs)
    n_high = sum(1 for w in off for s in w.situations if s.A >= L1.rehearsal_a_min)
    n_nat = sum(1 for w in nat for o in w.obs_specs if o.frame == "retell")
    n_strong = sum(1 for w in strong for o in w.obs_specs if o.frame == "retell")
    assert n_high >= 15 and abs(n_nat - 0.8 * n_high) <= 0.1 * n_high and n_strong == 3 * n_high
    for w in nat + strong:
        for o in w.obs_specs:
            if o.frame == "retell":
                assert w.situation(o.sid).A >= L1.rehearsal_a_min and all(m.role == "recall" for m in o.mentions)
                assert chan.is_retell(o) and o.t_obs >= w.situation(o.sid).t
                assert all(w.fact(m.fid).centrality >= 0.5 for m in o.mentions)  # people retell the gist
    for a, b in zip(off, nat):  # rehearsal adds lines and changes nothing else
        assert a.situations == b.situations and a.facts == b.facts and a.entities == b.entities

        def plain(w):
            return [(o.t_obs, o.sid, o.channel, o.mentions, o.slots, o.target_len, o.source, o.frame)
                    for o in w.obs_specs if o.frame != "retell"]

        assert plain(a) == plain(b)


@pytest.mark.parametrize("tier,lo,hi", [("L0", 150, 260), ("L1", 900, 1350), ("L2", 1900, 2700), ("L3", 5300, 7400)])
def test_tier_sizes(tier, lo, hi):
    w = worlds(tier, 1)[0]
    assert lo <= len(w.obs_specs) <= hi and w.cfg.tier == tier
    assert len(w.entities_of("person")) == w.cfg.n_persons + 1 and len(w.entities_of("city")) == w.cfg.n_cities
    assert all(len(w.entities_of(k)) >= w.cfg.min_pool for k in ("city", "street", "shop"))
    assert max(f.vfrom for f in w.facts) < w.cfg.days


# ------------------------------------------------------------------------- scenes, cast, hosting


def test_sample_feats_ranges_and_draw_count():
    for name, spec in S.SCENES.items():
        r, ref = stream(1, "sf", name), stream(1, "sf", name)
        specs = [spec] + ([S._BIG] if spec.big > 0 else [])
        for _ in range(400):
            f = S.sample_feats(name, r, 0.4)
            for _ in range(9):
                ref.u()
            assert r.state == ref.state and f.bond == 0.4
            assert any(sp.g[0] - 1e-6 <= f.goal_rel <= sp.g[1] + 1e-6 and sp.k[0] - 1e-6 <= f.stakes <= sp.k[1] + 1e-6
                       and sp.p[0] - 1e-6 <= f.control <= sp.p[1] + 1e-6 and abs(f.norm) <= sp.norm[1] + 1e-6
                       and sp.c[0] - 1e-6 <= f.conduciveness <= sp.c[1] + 1e-6
                       and min(sp.bits_sched[0], sp.bits_unsched[0]) - 1e-6 <= f.surprisal_bits
                       <= max(sp.bits_sched[1], sp.bits_unsched[1]) + 1e-6 for sp in specs), name


def test_schedule_day():
    r = stream(4, "sched")
    tallies = {}
    for day in range(600):
        n_target = 3 + day % 6
        out = S.schedule_day(r, day, L1, n_target)
        assert sum(1 for _, _, h in out if h) >= max(n_target, 1)
        assert sum(1 for _, sc, _ in out if sc == "routine") >= 1
        for minute, scene, has in out:
            lo, hi = S.SCENES[scene].hours
            assert lo <= minute <= hi and (has or scene not in S.ALWAYS_WRITTEN)
            tallies[scene] = tallies.get(scene, 0) + 1
    for scene in S.NONROUTINE_ORDER:
        assert abs(tallies[scene] / 20.0 - L1.scene_rate(scene)) <= max(0.25 * L1.scene_rate(scene), 0.6), scene


def test_stratified_pick():
    deciles = [i % 10 for i in range(200)]
    picked, short = S.stratified_pick(stream(2, "sp"), list(range(200)), deciles, 40, [1.0] * 10)
    assert len(set(picked)) == 40 and short == 0
    assert {d: sum(1 for i in picked if deciles[i] == d) for d in range(10)} == {d: 4 for d in range(10)}
    picked, _ = S.stratified_pick(stream(2, "sp"), list(range(200)), deciles, 40, [1.0] * 9 + [3.0])
    cnt = [sum(1 for i in picked if deciles[i] == d) for d in range(10)]
    assert sum(cnt) == 40 and cnt[9] == 10 and all(3 <= c <= 4 for c in cnt[:9])
    low_only = [i for i in range(200) if deciles[i] < 5]  # no support above decile 4: the quota is refilled
    picked, short = S.stratified_pick(stream(2, "sp"), low_only, deciles, 40, [1.0] * 10)
    assert len(set(picked)) == 40 and short == 0 and all(deciles[i] < 5 for i in picked)
    picked, short = S.stratified_pick(stream(2, "sp"), [3, 4, 5, 6, 7], deciles, 40, [1.0] * 10)
    assert sorted(picked) == [3, 4, 5, 6, 7] and short == 35
    assert S.stratified_pick(stream(2, "sp"), list(range(200)), deciles, 40, [1.0] * 10) == \
        S.stratified_pick(stream(2, "sp"), list(range(200)), deciles, 40, [1.0] * 10)
    assert [S.decile_of_rank(r, 100) for r in (0, 9, 10, 55, 99)] == [0, 0, 1, 5, 9]


def test_make_cast():
    cast, priors = S.make_cast(5, L1, "dev")
    names = [e.name.casefold() for e in cast.all_entities()]
    assert len(set(names)) == len(names) == 1 + 40 + 30 + 30 + 30 + 12
    bases = [n.split()[0] for n in names]
    assert all(not (a in b or b in a) for i, a in enumerate(bases) for b in bases[i + 1:])  # names never nest
    assert all(e.name.endswith(" Street") for e in cast.streets) and len(cast.shop_street) == 30
    assert all(e.name.split(" ", 1)[1].lower() in V.SHOP_TYPES for e in cast.shops)
    assert set(cast.shop_street.values()) <= {s.eid for s in cast.streets}
    assert cast.narrator.eid == "e0001" and cast.narrator.bond == 1.0
    assert max(e.bond for e in cast.persons) >= 0.7 and min(e.bond for e in cast.persons) < 0.4
    assert 40 <= len(cast.dishes) <= 60 and set(cast.dishes) <= set(V.DISHES) and len(set(cast.dishes)) == len(cast.dishes)
    assert priors["breakfast"].values == tuple(cast.dishes) and priors["lives_in"].values == tuple(c.eid for c in cast.cities)
    assert priors["vehicle_colour"].chance() == pytest.approx(1 / 40) and priors["closing_time"].chance() == pytest.approx(1 / 24)
    assert len(priors["visit_count"].values) == 8
    again, _ = S.make_cast(5, L1, "dev")
    assert [e.name for e in again.all_entities()] == [e.name for e in cast.all_entities()]
    other, _ = S.make_cast(6, L1, "dev")
    assert [e.name for e in other.persons] != [e.name for e in cast.persons]
    test_cast, _ = S.make_cast(5, L1, "test")
    assert all(V.partition_of_name(e.name.split()[0]) == "test" for e in test_cast.all_entities())


def _state(cfg=L1):
    cast, priors = S.make_cast(1, cfg, "dev")
    return {"cast": cast, "cfg": cfg, "priors": priors, "next_eid": len(cast.all_entities()), "new_entities": [],
            "used_shops": [], "history": {}, "story_keys": []}, cast


def test_host_facts_per_kind():
    state, cast = _state()
    sit = Situation(sid="s00001", day=5, minute=600, scene="minor", actors=(cast.persons[0].eid,), A=0.3,
                    feats=Feats(goal_rel=0.5))
    r = lambda: stream(8, "hf")  # noqa: E731
    (bf,) = S.host_facts(sit, r(), ["breakfast"], state)
    assert bf.pred == "breakfast" and bf.obj in cast.dishes and bf.subj == "" and bf.span == 0
    comp, car = S.host_facts(sit, r(), ["companion"], state)
    assert (comp.pred, comp.obj, comp.role) == ("companion", cast.persons[0].eid, "central")
    assert (car.pred, car.role) == ("car_colour", "peripheral") and comp.centrality >= 0.55 > car.centrality
    quiet = S.host_facts(sit, r(), ["companion"], dict(state, cfg=dataclasses.replace(L1, periphery_goal_relevant=1)))
    assert quiet[1].centrality >= 0.55
    own, other = S.host_facts(sit, r(), ["visit:dentist", "visit_other:dentist"], state)
    assert (own.pred, own.subj, own.obj) == ("errand_visit", "", "dentist") and other.subj == cast.persons[0].eid
    t1 = S.host_facts(sit, r(), ["closing_time"], state)
    t2 = S.host_facts(sit, stream(9, "hf"), ["closing_time"], state)
    assert [f.pred for f in t1] == ["on_street", "closing_time"] and t1[1].obj in V.TIMES and t1[1].src == "told"
    assert t1[1].subj != t2[1].subj and state["used_shops"] == [t1[0].subj, t2[0].subj] and t1[0].obj == cast.shop_street[t1[0].subj]
    state["used_shops"] = [s.eid for s in cast.shops]
    assert S.host_facts(sit, r(), ["closing_time"], state) == []  # every shop is taken
    art = S.host_facts(sit, r(), ["article"], state)
    assert [f.pred for f in art][:2] == ["read_story", "vehicle_colour"] and state["new_entities"][-1].kind == "story"
    assert art[1].subj == state["new_entities"][-1].eid and art[0].src == "read" and art[0].obj == art[1].subj
    trip = S.host_facts(sit, r(), ["trip"], state)
    assert [f.pred for f in trip] == ["visited", "trip_companion"] and trip[0].span >= 2
    first = S.host_facts(sit, r(), ["first:lives_in"], state)[0]
    upd = S.host_facts(sit, stream(9, "hf"), ["update:lives_in"], state)[0]
    assert first.chain and upd.chain and first.mention == "assert" and upd.mention == "update" and first.obj != upd.obj
    assert state["history"]["lives_in"] == [first.obj, upd.obj] and first.span == -1
    disc = S.host_facts(sit, r(), ["disclose:" + cast.persons[3].eid], state)[0]
    assert (disc.pred, disc.subj, disc.src, disc.source) == ("relation", cast.persons[3].eid, "told", cast.persons[3].eid)
    assert S.host_facts(sit, r(), ["breakfast"], state) == S.host_facts(sit, r(), ["breakfast"], state)
    with pytest.raises(ValueError):
        S.host_facts(sit, r(), ["dragon"], state)


# --------------------------------------------------------------------------- delete_events


def test_delete_events_changes_only_the_deleted_events_lines():
    w = worlds("L1", 1, 9)[0]
    w = w.with_channel(chan.make_channel(w, "TRUE", 0.7, 0.3, 5))
    chain = sorted(facts_of(w, "lives_in"), key=lambda f: f.vfrom)
    drop = stream(11, "del").sample([s.sid for s in w.situations], 25) + [w.host(chain[0].fid).sid]
    ab = W.delete_events(w, drop)
    gone = set(drop)
    gone_facts = {fid for s in w.situations if s.sid in gone for fid in s.facts}
    assert ab.situations == tuple(s for s in w.situations if s.sid not in gone)
    assert [o.to_json() for o in ab.obs_specs] == [o.to_json() for o in w.obs_specs if o.sid not in gone]
    survivors = [f for f in w.facts if f.fid not in gone_facts]
    assert [f.fid for f in ab.facts] == [f.fid for f in survivors]
    changed = [(a, b) for a, b in zip(ab.facts, survivors) if a != b]
    assert changed and all(b.supersedes in gone_facts and a == dataclasses.replace(b, supersedes="") for a, b in changed)
    assert ab.entities == w.entities and ab.priors == w.priors and ab.card == w.card and ab.mapping == w.mapping
    assert ab.ablated == tuple(drop) and ab.digest() != w.digest() and ab.seed == w.seed
    assert not any(m.fid in gone_facts for o in ab.obs_specs for m in o.mentions)
    assert ab.channel.oids == tuple(o.oid for o in ab.obs_specs)
    assert all(ab.channel.value(o.oid) == w.channel.value(o.oid) for o in ab.obs_specs)
    assert set(ab.extra("hosting")["chains"]["lives_in"]) == {f.fid for f in chain} - gone_facts
    assert W.check_world(ab) == []


def test_delete_events_composes_and_validates():
    w = worlds("L1", 1, 10)[0]
    sids = [s.sid for s in w.situations]
    a, b, c = sids[40], sids[300], sids[700]
    assert W.delete_events(w, []).digest() == w.digest()
    assert W.delete_events(W.delete_events(w, [a, b]), [c]).digest() == W.delete_events(w, [a, b, c]).digest()
    assert W.delete_events(w, [a, a, b]).ablated == (a, b)
    with pytest.raises(ValueError):
        W.delete_events(w, ["s99999"])
    # one event gone: its fact is unstated and absent, every other line is byte-identical
    bf = facts_of(w, "breakfast")[7]
    host = w.host(bf.fid).sid
    ab = W.delete_events(w, [host])
    assert bf.fid not in {f.fid for f in ab.facts} and lines_of(ab, bf.fid) == []
    assert len(ab.obs_specs) < len(w.obs_specs) and {o.sid for o in w.obs_specs} - {o.sid for o in ab.obs_specs} == {host}
    everything = W.delete_events(w, sids)
    assert everything.facts == () and everything.obs_specs == () and everything.situations == ()
    assert W.check_world(everything) == []


def test_deleting_a_week_one_chain_host_clears_only_the_supersedes_pointer():
    w = worlds("L1", 1, 11)[0]
    chain = sorted(facts_of(w, "works_as"), key=lambda f: f.vfrom)
    ab = W.delete_events(w, [w.host(chain[0].fid).sid])
    second = ab.fact(chain[1].fid)
    assert second.supersedes == "" and dataclasses.replace(second, supersedes=chain[0].fid) == w.fact(chain[1].fid)
    assert W.check_world(ab) == []


def test_extra_parameters_have_documented_defaults_and_can_be_overridden():
    for name, (default, doc) in S.EXTRA_PARAMS.items():
        assert S.param(L1, name) == default and doc
        assert name in S.__doc__ or name in chan.__doc__ or name in W.__doc__ or name in S.EXTRA_PARAMS
        assert S.param(L1.with_extra(**{name: 7.0}), name) == 7.0
    with pytest.raises(KeyError):
        S.param(L1, "no_such_parameter")
    thin = worlds("L1", 1, 0, extra=(("disclosure_share", 0.25), ("visit_other_share", 0.0)))[0]
    assert len(facts_of(thin, "relation")) == round(0.25 * L1.n_persons)
    assert all(f.subj == thin.entities[0].eid for f in facts_of(thin, "errand_visit"))
    def mixed(w):  # a situation hosting a breakfast together with a pair or a visit
        return any("breakfast" in k and ("car_colour" in k or "errand_visit" in k)
                   for k in ({w.fact(x).pred for x in s.facts} for s in w.situations))

    few = worlds("L1", 1, 0, extra=(("max_hosted_per_situation", 1),))[0]
    assert W.check_world(few) == [] and not mixed(few) and mixed(worlds("L1", 1, 0)[0])


# ------------------------------------------------------------------------- golden digests

GOLDEN = {
    ("L0", 0): "99357116558ee2219c6c53c4bd123981ae3fa6cd59d4bb391aa98ce8f91d86e0",
    ("L0", 7): "916bdf392e2a7476acea4b39ed9c2336dc1276f878a954e2b29777710d786570",
    ("L1", 3): "75746b2d7abf59065118cf108861ffa52b8f1b873681502f88e09a401e2e6545",
    ("L1", 10003): "d02a276aaeb762c130e6dd5cf1925c0e49d27c5d74ec8511cd12091b92f7ac82",
    ("L2", 1): "d6bce493b7b38d4db47beaf2767e06318d0b6b19e8439eab545f65d11bd7a825",
}


def test_golden_digests_are_pinned():
    for (tier, seed), digest in GOLDEN.items():
        assert W.build_world(seed, TierCfg.for_tier(tier)).digest() == digest, (tier, seed)
    assert len(GOLDEN) >= 3
