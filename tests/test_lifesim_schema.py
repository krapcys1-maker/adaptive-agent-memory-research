"""Tests for corpus.lifesim.schema (LifeSim D1-A). Standard library and pytest only."""

from __future__ import annotations

import dataclasses
import inspect
import json
import sys
import typing
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import schema as S  # noqa: E402

# --------------------------------------------------------------------- hand-built samples

FEATS = S.Feats(goal_rel=0.8, surprisal_bits=3.5, stakes=0.9, bond=0.6, control=0.2,
                norm=-0.3, conduciveness=-0.7)
ENTITY = S.Entity(eid="e0007", kind="person", name="Mirela", aliases=("Mira",), bond=0.75)
CITY = S.Entity(eid="e0009", kind="city", name="Verdton")
FACT_OLD = S.Fact(fid="f00003", subj="e0007", pred="lives_in", obj="e0010", vfrom=0, vto=11)
FACT = S.Fact(fid="f00012", subj="e0007", pred="lives_in", obj="e0009", vfrom=12, vto=None,
              src="told", centrality=0.4, supersedes="f00003", surprisal_bits=2.25)
SIT = S.Situation(sid="s00005", day=12, minute=545, scene="move", actors=("e0007", "e0008"),
                  place="e0009", feats=FEATS, A=0.64, V=-0.42, facts=("f00012",), turning=True,
                  topic="housing", mood=-0.18)
SIT2 = S.Situation(sid="s00002", day=3, minute=480, scene="routine", facts=("f00003",))
OBS_SPEC = S.ObsSpec(
    oid="o00031", t_obs=S.to_minutes(12, 600), channel="chat", sid="s00005",
    mentions=(S.Mention("f00012", "update"), S.Mention("f00003", "retract")),
    slots=(S.Slot("city", "Verdton", "f00012"), S.Slot("who", "Mirela")),
    source="e0007", frame="v2.07", target_len=52)
OBS_SPEC2 = S.ObsSpec(oid="o00004", t_obs=S.to_minutes(3, 500), channel="diary", sid="s00002",
                      mentions=(S.Mention("f00003"),), slots=(S.Slot("city", "Kenaburg", "f00003"),))
OBS = S.Obs(oid="o00031", t_obs=S.to_minutes(12, 600), channel="chat", text="Moved to Verdton!")
PRIOR = S.Prior(slot="breakfast", values=("porridge", "muesli", "toast with jam"),
                probs=(0.5, 0.3, 0.2))
CARD = S.Card(name="Mara", role="teacher")
GOLD = S.Gold(kind="entity", value="muesli", aliases=("granola",), vocab_id="pool:dishes",
              near_miss=(S.NearMiss("habit", "porridge"), S.NearMiss("adjacent_day", "toast with jam")))
TAGS = S.Tags(delay_days=40, anchor_kind="relative_date", n_confusers=5, n_evidence=1,
              target_arousal=0.31, arousal_decile=3, centrality=0.2, surprisal_bits=4.5,
              update_count=2, relative_time=True, need_label="L2", partition="test",
              prior_answerable=True, role="peripheral", pair_id="p7", hard=True,
              extra=(("fork", "choice"),))
QUERY = S.Query(qid="q0001", family="EP1", t_ask=S.to_minutes(52, 700),
                text="What did I have for breakfast on 2027-02-10?", fmt="choice", gold=GOLD,
                evidence_oids=("o00004",), evidence_fids=("f00003",), tags=TAGS,
                cue=(S.Slot("date", "2027-02-10"),), ask="breakfast",
                options=("porridge", "muesli", "toast with jam", "cornflakes"), conf=True,
                twin_of="q0002")
SCORE = S.ScoreRecord(qid="q0001", family="EP1", correct=False, score=0.0, error_type="habit",
                      candidates=("porridge",), abstained=False, hedged=False, unmatched=False,
                      parse_ok=True, conf=85, cost_weighted=-1.0, abs_error=2.0, within_one=False)
CHANNEL = S.Channel(arm="TRUE", reliability=0.7, nu=0.3, seed=1, oids=("o00004", "o00031"),
                    h=(0.25, None), sigma=0.12, realised_corr=0.69, x=(0.1, 0.4),
                    meta=(("rho", 0.5),))
RECORD = S.Record(id="o00031", text="Moved to Verdton!", timestamp=S.to_minutes(12, 600),
                  channel="chat", source="e0007", heartbeat=0.4)
CONTEXT = S.ContextItem(text="Moved to Verdton!", timestamp=S.to_minutes(12, 600), oid="o00031")
ANSWER = S.LifeAnswer(text="muesli", evidence_ids=("o00004",), context=(CONTEXT,),
                      context_tokens=3, abstained=False, confidence=70,
                      cost=(("model_calls", 1.0),), metadata=(("note", "x"),))
CFG_L0 = S.TIERS["L0"]


def build_world(cfg=CFG_L0, **kw) -> S.World:
    base = dict(seed=3, cfg=cfg, entities=(ENTITY, CITY), facts=(FACT_OLD, FACT),
                situations=(SIT2, SIT), obs_specs=(OBS_SPEC2, OBS_SPEC), card=CARD,
                priors=(PRIOR,), mapping="M2", partition="dev", ablated=("s00099",),
                extras=(("goals", "[1,2]"),))
    base.update(kw)
    return S.World(**base)


SAMPLES = {
    "Feats": FEATS, "Entity": ENTITY, "Fact": FACT, "Situation": SIT, "ObsSpec": OBS_SPEC,
    "Obs": OBS, "Prior": PRIOR, "Card": CARD, "Gold": GOLD, "Tags": TAGS, "Query": QUERY,
    "ScoreRecord": SCORE, "Channel": CHANNEL, "Record": RECORD, "ContextItem": CONTEXT,
    "LifeAnswer": ANSWER, "Cell": S.CELLS["C-half"], "Slot": S.Slot("city", "Verdton", "f00012"),
    "Mention": S.Mention("f00012", "update"), "NearMiss": S.NearMiss("stale", "Kenaburg"),
}

# Schema fingerprint: any change to a field name, field order, default or canonical form
# changes these digests; make the change on purpose (bump SCHEMA_VERSION) and re-pin.
PINNED = {
    "Card": "6fc7e603146b47d270f6968318271ead6aae1884969fddd256725d19869fe45c",
    "Cell": "9d2abb7d8cb8ae1b28f2611a115f8ecd43e24f7da66e7c379e4c422dac95d3ef",
    "Channel": "c14eea05f1a0405b8fb2a194dcecc6c4a709e733f61683931003fb9f0a981345",
    "ContextItem": "1bc98052cd48c300e2d86f823a7a0133b1ce41ebbb5ff1b98b96b2b5fe96e41f",
    "Entity": "875f6150c1ecb804bcb83faccd3fbee4e88451113eea5d07b54b58602fe3bb90",
    "Fact": "99dc16d8c097c3c65e7fd096cb80a56fc78540819396fa9083caf272ae83b761",
    "Feats": "8c10bf0c68d35943bd409443904b8213556d3af302211be03de04faed93f2aea",
    "Gold": "05939efbef59a4b045d2a15867a114e44ea6258def41a9623e935f08a8927399",
    "LifeAnswer": "782a27e947c0b54c879e5f196b29c29d3aba181193c564db8e7cb4e72f99c3b8",
    "Mention": "dca0f16ec3005ee917ac41d291b9325eb06dc97615760cec44b4c3f010f23362",
    "NearMiss": "7ac5610cfc5901dbd6cd1fa0128c9accd053f7c14dd76a9259752122c7ba8888",
    "Obs": "a475a503928ad08de31a3e6e73f11d59201f53e1109a6df91daae51ab01694d6",
    "ObsSpec": "67e9de001360c9343bec26e0024f445d00aa71f5181f59992806365e2d6e54d2",
    "Prior": "476b4f8da681ff70554007c6c55bf530bae9930795a2becb91ff9294099fd730",
    "Query": "9e73e7d11dd63f18c5e9ba2486bb9f978edf1849e6ad8498dcdac81b610f4fc0",
    "Record": "267b9209cee3fdec75d6f22b3b92020dbcaf83ad1affe49c49f267a1e34e77d1",
    "ScoreRecord": "26399ccd8d3d314c5988c0fb6e9facd8be6c239b123fb778f82fc432da643754",
    "Situation": "c9745a1873386f0a015d30a07fd078fdb0f40d3efb9209cc5d8d9fe4873029b4",
    "Slot": "3004d3c8d979ad5a860ba5e4a9a0ecc675f89959ccfea9784982742f02fd9264",
    "Tags": "e43f1c5025361c63dfe66e20fdf48f0e2e6053acbcc251e855d2bb8b5d5a777e",
}
PINNED_CFG = {
    "L0": "8179be0bba77a02c8869175ebbab05fd12935085bb491c435375f8df6c7fde45",
    "L1": "6355861f0840a1f53c11d320b47294da8238f32493ec675826a345908614ebfc",
    "L2": "e5a2395e7a42e0dd5fdf6c3bd718c363b215fe6eb8f44572818f02d4e0573e6c",
    "L3": "b085a0512974291da0da7ae1e2ba62d67ba0b34087f1c93456e62700a76ad076",
}
PINNED_WORLD = "b1e0b64ce9215b3f984e354333e78baf70d6d74e531ba62c1810cb90d2db336d"


def all_schema_classes():
    return [c for _, c in inspect.getmembers(S, inspect.isclass)
            if dataclasses.is_dataclass(c) and c.__module__ == S.__name__]


# ------------------------------------------------------------------ round trip and digests


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_every_row_type_round_trips_json_with_stable_digest(name):
    obj = SAMPLES[name]
    text = obj.to_json()
    back = type(obj).from_json(text)
    assert back == obj
    assert back.digest() == obj.digest()
    assert type(obj).from_dict(obj.to_dict()) == obj
    assert text == json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"))
    assert text.isascii()
    assert set(json.loads(text)) == {f.name for f in dataclasses.fields(obj)}


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_digests_are_pinned(name):
    assert SAMPLES[name].digest() == PINNED[name]


@pytest.mark.parametrize("tier", ["L0", "L1", "L2", "L3"])
def test_tier_config_digests_are_pinned(tier):
    assert S.TIERS[tier].digest() == PINNED_CFG[tier]


def test_world_digest_is_pinned():
    assert build_world().digest() == PINNED_WORLD


def test_digest_ignores_container_types_and_keyword_order():
    a = S.Situation(sid="s1", day=1, minute=2, scene="minor", actors=["e1", "e2"],
                    facts=["f1"], A=1, V=0)
    b = S.Situation(V=0.0, A=1.0, facts=("f1",), actors=("e1", "e2"), scene="minor", minute=2,
                    day=1, sid="s1")
    assert a == b and a.digest() == b.digest()
    assert isinstance(a.actors, tuple) and isinstance(a.A, float)
    assert hash(a) == hash(b)  # frozen and hashable


def test_floats_are_quantised_to_six_decimals_and_negative_zero_is_normalised():
    f = S.Feats(goal_rel=0.12345678, surprisal_bits=-1e-9, stakes=1, bond=0.5000004)
    assert f.goal_rel == 0.123457 and f.stakes == 1.0 and isinstance(f.stakes, float)
    assert f.bond == 0.5
    assert str(f.surprisal_bits) == "0.0"
    assert S.Prior("s", ("a", "b"), (0.123456789012, 0.876543210988)).probs == (0.123456789, 0.876543211)
    s = S.Situation(sid="s", day=0, minute=0, scene="minor", A=0.2 + 0.1, V=-0.30000000000000004)
    assert s.A == 0.3 and s.V == -0.3  # last-bit noise cannot reach a digest


def test_every_quantised_name_is_a_field():
    for cls in all_schema_classes():
        names = {f.name for f in dataclasses.fields(cls)}
        for q_name in getattr(cls, "_Q", ()):
            assert q_name in names, (cls.__name__, q_name)


def test_all_type_hints_resolve_and_are_supported():
    for cls in all_schema_classes():
        hints = typing.get_type_hints(cls)
        assert all(f.name in hints for f in dataclasses.fields(cls))
        if issubclass(cls, S._Schema):
            S._plan(cls)  # builds the conversion plan without error


def test_dataclasses_are_frozen_and_hold_no_dicts_or_lists():
    for cls in all_schema_classes():
        assert cls.__dataclass_params__.frozen, cls.__name__
        for hint in typing.get_type_hints(cls).values():
            assert "dict" not in str(hint) and "list" not in str(hint), (cls.__name__, hint)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ENTITY.name = "x"  # type: ignore[misc]


def test_digest_is_the_sha256_of_the_canonical_json_text():
    import hashlib
    slot = S.Slot("city", "Verdton", "f00012")
    text = '{"fid":"f00012","name":"city","value":"Verdton"}'
    assert slot.to_json() == text
    assert slot.digest() == hashlib.sha256(text.encode("ascii")).hexdigest()
    assert S.Feats(goal_rel=0.5).to_json() == (
        '{"bond":0.0,"conduciveness":0.0,"control":0.5,"goal_rel":0.5,"norm":0.0,'
        '"stakes":0.0,"surprisal_bits":0.0}')
    e = S.Entity(eid="e1", kind="person", name="Zoë")
    assert "\\u00eb" in e.to_json() and e.to_json().isascii()  # escaped: same bytes everywhere
    assert S.digest_of({"b": 1, "a": [1, 2.5, None, True]}) ==         hashlib.sha256(b'{"a":[1,2.5,null,true],"b":1}').hexdigest()


def test_worlds_survive_pickle_and_deepcopy_with_their_caches():
    import copy
    import pickle
    w = build_world().with_channel(CHANNEL)
    w.digest()
    w.fact("f00012")
    CHANNEL.value("o00004")  # fill the lazy caches before copying
    for clone in (pickle.loads(pickle.dumps(w)), copy.deepcopy(w)):
        assert clone == w and clone.digest() == w.digest() and clone.fact("f00012") == FACT
        assert clone.channel.value("o00004") == 0.25


# -------------------------------------------------------------------- validation


@pytest.mark.parametrize("factory", [
    lambda: S.Entity(eid="e1", kind="alien", name="x"),
    lambda: S.Entity(eid="e1", kind="person", name=""),
    lambda: S.Entity(eid=1, kind="person", name="x"),
    lambda: S.Entity(eid="e1", kind="person", name="x", bond="high"),
    lambda: S.Entity(eid="e1", kind="person", name="x", bond=float("nan")),
    lambda: S.Entity(eid="e1", kind="person", name="x", aliases="abc"),
    lambda: S.Fact(fid="f", subj="s", pred="p", obj="o", vfrom=5, vto=3),
    lambda: S.Fact(fid="f", subj="s", pred="p", obj="o", vfrom=5, src="dreamed"),
    lambda: S.Fact(fid="f", subj="s", pred="p", obj="o", vfrom=True),
    lambda: S.Fact(fid="f", subj="s", pred="p", obj="o", vfrom=2.0),
    lambda: S.Situation(sid="s", day=0, minute=1440, scene="minor"),
    lambda: S.Situation(sid="s", day=0, minute=0, scene="holiday"),
    lambda: S.ObsSpec(oid="o", t_obs=0, channel="telegram", sid="s"),
    lambda: S.ObsSpec(oid="o", t_obs=0, channel="diary", sid="s", target_len=0),
    lambda: S.Mention("f", "mention"),
    lambda: S.Slot("n", ""),
    lambda: S.NearMiss("random", "x"),
    lambda: S.Gold("number", "3"),
    lambda: S.Tags(anchor_kind="vibes"),
    lambda: S.Tags(arousal_decile=10),
    lambda: S.Tags(partition="train"),
    lambda: S.Query(qid="q", family="XX9", t_ask=0, text="", fmt="open", gold=GOLD),
    lambda: S.Query(qid="q", family="EP1", t_ask=0, text="", fmt="essay", gold=GOLD),
    lambda: S.Query(qid="q", family="EP1", t_ask=0, text="", fmt="choice", gold=GOLD, options=("a",)),
    lambda: S.ScoreRecord(qid="q", family="EP1", correct=True, score=1.0, error_type="oops"),
    lambda: S.ScoreRecord(qid="q", family="EP1", correct=True, score=1.0, conf=101),
    lambda: S.Prior("s", ("a",), (0.5, 0.5)),
    lambda: S.Prior("s", ("a",), (-0.5,)),
    lambda: S.Channel(arm="TRUE", reliability=0.7, nu=0.3, seed=1, oids=("o1",), h=()),
    lambda: S.Channel(arm="MAGIC", reliability=0.7, nu=0.3, seed=1),
    lambda: S.TierCfg(affect="A9"),
    lambda: S.TierCfg(rehearsal="always"),
    lambda: S.TierCfg(start_date="2027-13-01"),
    lambda: S.TierCfg(words_min=70),
    lambda: S.TierCfg(days=0),
    lambda: S.TierCfg(mappings=("M1", "M9")),
    lambda: S.TierCfg(locality=(1.0, 0.4)),  # a fixed-length tuple needs exactly its length
    lambda: S.TierCfg(caps=(0.1, 0.2, 0.3, 0.4, 0.5)),
    lambda: S.TierCfg(family_mix=(("EP1", 0.5), ("IN1", 0.4))),
    lambda: S.TierCfg(family_mix=(("EP1", 1.5), ("IN1", -0.5))),
    lambda: S.TierCfg(family_mix=(("XX9", 1.0),)),
    lambda: S.TierCfg(family_mix=(("ME1", 1.0),)),  # ME1 is sized by abstain_share, not by the mix
    lambda: S.TierCfg(retention_ratios=(1.0, "x")),
    lambda: S.World(seed=1, cfg=CFG_L0, mapping="M7"),
    lambda: S.World(seed=1, cfg=CFG_L0, partition="validation"),
    lambda: S.World(seed=1, cfg="L0"),
    lambda: S.World(seed=1, cfg=CFG_L0, facts=(FACT, FACT)),
    lambda: S.World(seed=1, cfg=CFG_L0, obs_specs=(OBS_SPEC, OBS_SPEC2)),  # not sorted by t_obs
    lambda: S.World(seed=1, cfg=CFG_L0, situations=(SIT, SIT)),
    lambda: S.Cell("c", 0.0, 0.0, 0.0),
    lambda: S.Cell("c", 1.0, 0.0, 1.5),
])
def test_bad_values_are_rejected_on_construction(factory):
    with pytest.raises((ValueError, TypeError)):
        factory()


def test_from_dict_rejects_unknown_keys_and_fills_defaults():
    with pytest.raises(ValueError, match="unknown keys"):
        S.Entity.from_dict({"eid": "e1", "kind": "person", "name": "x", "colour": "red"})
    e = S.Entity.from_dict({"eid": "e1", "kind": "person", "name": "x"})
    assert e.aliases == () and e.bond == 0.0
    with pytest.raises(TypeError):
        S.Entity.from_dict({"kind": "person", "name": "x"})  # eid is required
    with pytest.raises(json.JSONDecodeError):
        S.Entity.from_json("{not json")


def test_non_finite_floats_cannot_be_serialised():
    with pytest.raises(ValueError):
        S.canonical_json({"x": float("inf")})
    with pytest.raises(ValueError):
        S.to_jsonable(float("nan"))


# --------------------------------------------------------------- World: digest and lookups


def test_world_structure_covers_every_world_field_except_cfg_and_channel():
    fields = {f.name for f in dataclasses.fields(S.World)}
    covered = set(build_world().structure()) - {"schema", "generator"}
    assert fields - covered == {"cfg", "channel"}
    assert covered - fields == set()


def test_world_digest_reacts_to_every_structural_field():
    base = build_world().digest()
    changed = {
        "seed": build_world(seed=4),
        "partition": build_world(partition="test"),
        "mapping": build_world(mapping="M1"),
        "card": build_world(card=S.Card(name="Mara", role="nurse")),
        "entities": build_world(entities=(ENTITY,)),
        "entity_name": build_world(entities=(dataclasses.replace(ENTITY, name="Mirelo"), CITY)),
        "facts": build_world(facts=(FACT_OLD,)),
        "fact_obj": build_world(facts=(FACT_OLD, dataclasses.replace(FACT, obj="e0001"))),
        "situations": build_world(situations=(SIT,)),
        "sit_A": build_world(situations=(SIT2, dataclasses.replace(SIT, A=0.65))),
        "obs_specs": build_world(obs_specs=(OBS_SPEC2,)),
        "mention_role": build_world(obs_specs=(OBS_SPEC2, dataclasses.replace(
            OBS_SPEC, mentions=(S.Mention("f00012", "assert"), S.Mention("f00003", "retract"))))),
        "priors": build_world(priors=()),
        "ablated": build_world(ablated=()),
        "extras": build_world(extras=(("goals", "[1,3]"),)),
    }
    for name, w in changed.items():
        assert w.digest() != base, name
    assert len({w.digest() for w in changed.values()}) == len(changed)


def test_world_digest_ignores_cfg_channel_and_rendering_choices():
    base = build_world()
    cfg2 = dataclasses.replace(CFG_L0, affect="A2", r_aff=0.4, typo_rate=0.02, flash_share=0.2,
                               v_mix=(0.5, 0.5, 0.0), rehearsal="strong", reliability_primary=0.5,
                               queries_per_world=999)
    assert build_world(cfg=cfg2).digest() == base.digest()
    assert base.with_channel(CHANNEL).digest() == base.digest()
    assert base.with_channel(CHANNEL) != base and base.with_channel(CHANNEL).channel == CHANNEL
    assert base.with_channel(CHANNEL).with_channel(None) == base


def test_world_lookups_and_indexes():
    w = build_world()
    assert w.entity("e0007") is ENTITY and w.fact("f00012") == FACT
    assert w.situation("s00005") == SIT and w.obs_spec("o00031") == OBS_SPEC
    assert w.host("f00012").sid == "s00005" and w.host("f00003").sid == "s00002"
    assert w.mentions_of("f00003") == (("o00004", "assert"), ("o00031", "retract"))
    assert w.mentions_of("f99999") == ()
    assert [e.eid for e in w.entities_of("city")] == ["e0009"]
    assert w.prior("breakfast") == PRIOR and w.prior("nothing") is None
    assert w.n_days == CFG_L0.days and w.date_of(0) == "2027-01-01"
    with pytest.raises(KeyError):
        w.fact("f77777")


def test_world_extras_round_trip_and_replace():
    w = build_world(extras=())
    w2 = w.with_extra("goals", {"b": [1, 2], "a": "x"}).with_extra("mood", [0.5])
    assert w2.extra("goals") == {"a": "x", "b": [1, 2]} and w2.extra("mood") == [0.5]
    assert w2.extra("missing", 7) == 7
    assert [k for k, _ in w2.extras] == ["goals", "mood"]  # sorted: canonical
    assert w2.with_extra("goals", 1).extra("goals") == 1


def test_world_json_round_trip_includes_cfg_and_channel():
    w = build_world().with_channel(CHANNEL)
    back = S.World.from_json(w.to_json())
    assert back == w and back.digest() == w.digest() and back.cfg == w.cfg


def test_world_save_and_load_are_byte_identical_lf_only(tmp_path):
    w = build_world().with_channel(CHANNEL)
    d1, d2 = tmp_path / "a", tmp_path / "b"
    S.save_world(w, d1)
    back = S.load_world(d1)
    assert back == w and back.digest() == w.digest()
    S.save_world(back, d2)
    names = sorted(p.name for p in d1.iterdir())
    assert names == ["channel.json", "obs_specs.jsonl", "situations.jsonl", "world.json"]
    for name in names:
        raw = (d1 / name).read_bytes()
        assert raw == (d2 / name).read_bytes()
        assert b"\r" not in raw and raw.endswith(b"\n") and raw.isascii()
    assert (d1 / "obs_specs.jsonl").read_bytes().count(b"\n") == len(w.obs_specs)
    # without a channel there is no channel.json
    S.save_world(build_world(), tmp_path / "c")
    assert not (tmp_path / "c" / "channel.json").exists()
    assert S.load_world(tmp_path / "c").channel is None


def test_load_world_detects_tampering(tmp_path):
    S.save_world(build_world(), tmp_path)
    path = tmp_path / "world.json"
    head = json.loads(path.read_bytes())
    head["facts"][0]["obj"] = "e0001"
    path.write_bytes(S.canonical_json(head).encode("ascii") + b"\n")
    with pytest.raises(ValueError, match="digest"):
        S.load_world(tmp_path)
    head["digest"] = build_world().digest()
    head["schema"] = "lifesim-schema-0"
    path.write_bytes(S.canonical_json(head).encode("ascii") + b"\n")
    with pytest.raises(ValueError, match="schema"):
        S.load_world(tmp_path)


def test_jsonl_helpers(tmp_path):
    S.write_jsonl(tmp_path / "x.jsonl", [OBS, OBS])
    raw = (tmp_path / "x.jsonl").read_bytes()
    assert raw.count(b"\n") == 2 and b"\r" not in raw
    assert S.read_jsonl(tmp_path / "x.jsonl", S.Obs) == [OBS, OBS]
    S.write_jsonl(tmp_path / "empty.jsonl", [])
    assert (tmp_path / "empty.jsonl").read_bytes() == b"" and S.read_jsonl(tmp_path / "empty.jsonl", S.Obs) == []
    assert S.dumps_jsonl(x for x in [QUERY]).endswith("}\n")


# ------------------------------------------------------------------------- small types


def test_prior_helpers():
    assert PRIOR.chance() == pytest.approx(0.25 + 0.09 + 0.04)
    assert PRIOR.mode() == "porridge" and PRIOR.top(2) == ("porridge", "muesli")
    assert PRIOR.p_of("muesli") == 0.3 and PRIOR.p_of("tea") == 0.0
    assert PRIOR.entropy_bits() == pytest.approx(1.4854752972273344, abs=1e-6)
    tie = S.Prior("s", ("a", "b", "c"), (0.2, 0.4, 0.4))
    assert tie.mode() == "b" and tie.top(3) == ("b", "c", "a")  # ties keep value order


def test_fact_validity_window():
    day = S.Fact(fid="f1", subj="s", pred="breakfast", obj="x", vfrom=5, vto=5)  # an event fact
    assert day.valid_on(5) and not day.valid_on(4) and not day.valid_on(6)
    assert FACT_OLD.valid_on(0) and FACT_OLD.valid_on(11) and not FACT_OLD.valid_on(12)
    assert not FACT.valid_on(11) and FACT.valid_on(12) and FACT.valid_on(10**6)


def test_feats_surprise_is_clipped_bits_over_scale():
    assert S.Feats(surprisal_bits=4.0).surprise() == 0.5
    assert S.Feats(surprisal_bits=20.0).surprise() == 1.0
    assert S.Feats(surprisal_bits=0.0).surprise() == 0.0
    assert S.Feats(surprisal_bits=4.0).surprise(scale=16.0) == 0.25


def test_gold_accepted_and_tags_get():
    assert GOLD.accepted() == ("muesli", "granola")
    assert S.Gold("entity", "grey", aliases=("grey", "gray")).accepted() == ("grey", "gray")
    assert TAGS.get("fork") == "choice" and TAGS.get("nope") is None and TAGS.get("nope", "d") == "d"


def test_situation_and_obs_spec_time_properties():
    assert SIT.t == 12 * 1440 + 545
    assert OBS_SPEC.day == 12 and OBS_SPEC.t_obs == 12 * 1440 + 600


def test_channel_lookup_by_oid():
    assert CHANNEL.value("o00004") == 0.25 and CHANNEL.value("o00031") is None
    assert CHANNEL.value("o99999") is None


def test_cells_match_the_specification():
    assert S.CELLS["C+"] == S.Cell("C+", 4.0, 0.3, 0.2)
    assert S.CELLS["C-half"] == S.Cell("C-half", 2.0, 0.3, 0.2)
    assert S.CELLS["C0"] == S.Cell("C0", 1.0, 0.3, 0.0)
    assert S.CELLS["C0r"] == S.Cell("C0r", 1.0, 0.0, 0.0)
    assert S.CELLS["C-"] == S.Cell("C-", 0.3, 0.0, 0.6)
    assert S.E_GRID == (0.2, 0.5, 1.0, 2.0, 4.0) and S.MU_GRID == (0.0, 0.1, 0.3, 0.6)
    assert S.LAG_GRID == (7, 30, 120)
    g = S.grid_cell(2, 0.3)
    assert (g.name, g.e_target, g.mu, g.rehearsal, g.lag_days) == ("E2_mu0.3", 2.0, 0.3, 0.0, 0)
    assert S.grid_cell(0.5, 0, rehearsal=0.3, lag_days=30).lag_days == 30
    assert S.CELLS["C+"].to_dict()["e_target"] == 4.0


# ---------------------------------------------------- time, ids, epochs, partitions


def test_minute_day_arithmetic():
    t = S.to_minutes(12, 600)
    assert t == 12 * 1440 + 600 and S.day_of(t) == 12 and S.minute_of(t) == 600
    assert S.day_of(1439) == 0 and S.day_of(1440) == 1 and S.minute_of(1440) == 0


def test_dates():
    assert S.date_of("2027-01-01", 0) == "2027-01-01"
    assert S.date_of("2027-01-01", 31) == "2027-02-01"
    assert S.date_of("2027-01-01", 72) == "2027-03-14"  # the specification's example date
    assert S.date_of("2027-01-01", 365) == "2028-01-01"
    assert S.date_of("2027-01-01", 365 + 59) == "2028-02-29"  # leap day
    assert S.date_of("2027-01-01", 999) == "2029-09-26"
    assert S.weekday_of("2027-01-01", 0) == 4  # a Friday
    assert S.weekday_of("2027-01-01", 1) == 5 and S.weekday_of("2027-01-01", 3) == 0
    assert S.iso_of("2027-01-01", S.to_minutes(72, 9 * 60 + 5)) == "2027-03-14T09:05"
    assert S.iso_of("2027-01-01", 0) == "2027-01-01T00:00"


def test_delay_bins_have_the_specified_edges():
    expected = {1: 0, 3: 0, 4: 1, 14: 1, 15: 2, 60: 2, 61: 3, 180: 3, 181: 4, 1000: 4}
    for days, b in expected.items():
        assert S.delay_bin(days) == b, days
    assert S.delay_bin(0) == 0


def test_id_formats_sort_numerically():
    assert S.new_id("entity", 7) == "e0007" and S.new_id("fact", 12) == "f00012"
    assert S.new_id("situation", 5) == "s00005" and S.new_id("obs", 31) == "o00031"
    assert S.new_id("query", 1) == "q0001"
    ids = [S.new_id("obs", n) for n in range(1, 6001)]
    assert ids == sorted(ids)
    assert S.new_id("fact", 123456) == "f123456"


def test_seed_epochs_and_partitions():
    assert [S.seed_epoch(s) for s in (0, 5, 999)] == ["dev"] * 3
    assert [S.seed_epoch(s) for s in (5000, 5099)] == ["confirm"] * 2
    assert S.seed_epoch(5100) == "adhoc" and S.seed_epoch(1000) == "adhoc"
    assert S.seed_epoch(10000) == "test" and S.seed_epoch(20999) == "test"
    assert S.seed_epoch(21000) == "adhoc"
    assert [S.partition_of_seed(s) for s in (0, 5000, 1234, 10005, 20001)] == \
        ["dev", "dev", "dev", "test", "test"]
    assert CFG_L0.resolved_partition(7) == "dev" and CFG_L0.resolved_partition(10001) == "test"
    forced = dataclasses.replace(CFG_L0, name_partition="test")
    assert forced.resolved_partition(7) == "test"


# --------------------------------------------------------------------- TierCfg


def test_tier_presets_follow_the_specification():
    t = S.TIERS
    assert [t[k].days for k in ("L0", "L1", "L2", "L3")] == [30, 180, 365, 1000]
    assert [t[k].queries_per_world for k in ("L0", "L1", "L2", "L3")] == [80, 160, 220, 260]
    assert [t[k].context_words for k in ("L0", "L1", "L2", "L3")] == [400, 600, 800, 1000]
    assert t["L0"].retention_ratios == (1.0,) and t["L1"].retention_ratios == (1.0, 0.25)
    assert t["L2"].retention_ratios == (1.0, 0.25, 0.10) and t["L3"].retention_ratios == (1.0, 0.10)
    assert (t["L0"].target_lo, t["L1"].target_lo, t["L1"].target_hi) == (0.80, 0.65, 0.85)
    assert (t["L2"].target_lo, t["L2"].target_hi, t["L3"].target_hi) == (0.45, 0.65, 0.50)
    for name, n_obs in (("L0", 180), ("L1", 1100), ("L2", 2200), ("L3", 6000)):
        assert t[name].expected_obs() == pytest.approx(n_obs, rel=0.03), name
    assert t["L2"].expected_words() == pytest.approx(110_000, rel=0.15)
    assert t["L3"].hard_share >= 0.6 and t["L0"].hard_share == 0.0
    ladder = [t[k] for k in ("L0", "L1", "L2", "L3")]
    for field_name in ("abstain_share", "anchor_mix", "n_confusers_max", "update_rate",
                       "chain_depth_max", "disorder", "n_persons", "hard_share", "days"):
        values = [getattr(c, field_name) for c in ladder]
        assert values == sorted(values), field_name  # difficulty never falls with the tier
    assert [t[k].abstain_share for k in ("L0", "L3")] == [0.05, 0.15]
    assert all(0.0 <= c.abstain_share <= 0.3 and c.anchor_mix <= 0.8 for c in ladder)
    for c in ladder:
        assert c.delay_max_days < c.days
        assert min(c.n_persons, c.n_cities, c.n_streets, c.n_shops) >= c.min_pool
        assert c.n_foods_min == 40 and c.n_foods_max == 60 and c.min_pool == 24
    assert S.TierCfg().tier == "L1" and S.TierCfg() == t["L1"]  # defaults are the L1 preset
    assert S.TierCfg.for_tier("L2") == t["L2"]
    assert len({c.digest() for c in ladder}) == 4
    with pytest.raises(KeyError):
        S.TierCfg.for_tier("L9")


def test_tier_config_round_trips_json():
    for cfg in S.TIERS.values():
        assert S.TierCfg.from_json(cfg.to_json()) == cfg


def test_specification_constants_are_the_defaults():
    c = S.TierCfg()
    assert c.m1_w == (0.30, 0.25, 0.25, 0.15, 0.05) and c.m1_eps_sd == 0.05
    assert (c.m1_cap_base, c.m1_cap_slope) == (0.35, 0.65)
    assert (c.v_gain_c, c.v_gain_norm, c.surprise_bits_scale) == (1.5, 0.3, 8.0)
    assert (c.mood_decay, c.mood_gain, c.mood_quiet_decay) == (0.9, 0.1, 0.97)
    assert (c.nu, c.x_burst_rate, c.reliability_primary, c.retell_a_factor) == (0.3, 0.5, 0.7, 0.5)
    assert c.reliability_grid == (0.0, 0.3, 0.5, 0.7, 0.9, 1.0)
    assert (c.dropout, c.sign_reversal) == (0.1, 0.15)
    assert (c.rehearsal_p_natural, c.rehearsal_a_min, c.rehearsal_p_strong, c.rehearsal_repeats_strong) == (0.8, 0.7, 1.0, 3)
    assert c.p_immediate_diary == 0.7 and c.max_corr_nk == 0.3
    assert (c.a_target_mean, c.a_target_sd, c.a_frac_below_03) == (0.22, 0.12, 0.77)
    assert c.caps == (0.10, 0.20, 0.30, 0.40) and c.half_lives == (365.0, 60.0)
    assert c.locality == (1.0, 0.4, 0.05) and c.experiencer_weights == (1.0, 0.25, 0.1)
    assert c.persistent_share == (0.6, 0.2) and c.habituation == 0.5 and c.tp_refractory_days == 30
    assert (c.eta_ordinary, c.eta_turning, c.n_topics) == (0.25, 0.9, 12)
    assert (c.words_min, c.words_max, c.obs_min, c.obs_max) == (30, 60, 3, 10)
    assert c.ep1_competing == (1, 60) and c.in1_confusers == (6, 12) and c.in1_decoy_share == 0.5
    assert c.in1_min_other_articles == 6 and c.ep3c_count_range == (1, 8) and c.ep3c_evidence == (2, 10)
    assert c.in4_low_deciles == 2 and c.se_stale_mentions == 6 and c.habit_zipf_s == 0.6
    assert dict(c.family_mix) == {"EP1": 0.22, "SE4": 0.12, "SE5": 0.12, "IN1": 0.16, "EP4": 0.16,
                                  "IN4": 0.10, "EP3c": 0.12} and c.query_overgenerate == 1.5
    assert c.mappings == ("M1", "M2") and c.affect == "A0" and c.rehearsal == "off"


def test_every_tier_config_field_is_documented_and_numeric_ones_are_assumed():
    hints = typing.get_type_hints(S.TierCfg)
    structural = set()
    for f in dataclasses.fields(S.TierCfg):
        doc = f.metadata.get("doc", "")
        assert doc.startswith(("ASSUMED: ", "STRUCTURAL: ")), f.name
        assert len(doc) > 14, f.name
        assert f.metadata["assumed"] == doc.startswith("ASSUMED"), f.name
        if not f.metadata["assumed"]:
            structural.add(f.name)
        else:
            assert hints[f.name] is not str, f.name  # a string setting is never an assumption
    assert structural == {"tier", "start_date", "name_partition", "affect", "rehearsal",
                          "h_repr", "mappings"}
    assert set(S.TierCfg.assumed_float_names()) >= {"nu", "mood_decay", "habit_zipf_s", "anchor_mix"}
    assert "days" not in S.TierCfg.assumed_float_names()  # ints are not swept as floats
    assert "mappings" not in S.TierCfg.assumed_float_names()


def test_describe_lists_every_field_with_its_default_and_documentation():
    rows = S.TierCfg.describe()
    assert [r["name"] for r in rows] == [f.name for f in dataclasses.fields(S.TierCfg)]
    by = {r["name"]: r for r in rows}
    assert by["nu"]["default"] == 0.3 and by["nu"]["assumed"] is True and by["nu"]["type"] == "float"
    assert by["tier"]["assumed"] is False and by["caps"]["default"] == [0.1, 0.2, 0.3, 0.4]
    assert by["retention_ratios"]["type"] == "tuple[float, ...]"
    assert all(r["doc"].startswith(("ASSUMED: ", "STRUCTURAL: ")) for r in rows)
    json.dumps(rows)  # plain JSON, ready for config.json


def test_default_values_respect_their_documented_ranges():
    c = S.TierCfg()
    assert c.reliability_primary in c.reliability_grid
    assert abs(sum(c.v_mix) - 1.0) < 1e-12 and len(c.m1_w) == 5 and len(c.m2_w) == 5
    assert all(0.0 <= w <= 1.0 for w in c.m2_w)
    probs = [c.nu, c.dropout, c.sign_reversal, c.hard_share, c.abstain_share, c.anchor_mix,
             c.relative_time_share, c.name_rarity, c.same_frame_share, c.disorder,
             c.peripheral_share, c.incidental_update_share, c.rehearsal_p_natural,
             c.rehearsal_p_strong, c.p_immediate_diary, c.a_frac_below_03, c.in1_decoy_share]
    assert all(0.0 <= p <= 1.0 for p in probs)
    assert 0.5 <= c.habit_zipf_s <= 0.7 and 0.1 <= c.pi_peripheral_need <= 0.5
    assert c.periphery_goal_relevant in (0, 1) and 1 <= c.shared_slots <= 3
    assert dict(c.scene_rates).keys() <= set(S.SCENE_NAMES) and "routine" not in dict(c.scene_rates)
    assert c.scene_rate("major") == 1.5 and c.scene_rate("volcano") == 0.0
    assert sorted(c.caps) == list(c.caps)
    assert c.a_high_per_month == (3.0, 6.0)


def test_extra_parameters_and_get():
    c = S.TierCfg().with_extra(zeta=0.25, alpha=3)
    assert c.get("zeta") == 0.25 and c.get("alpha") == 3.0 and c.get("nu") == 0.3
    assert c.get("missing") is None and c.get("missing", 5) == 5
    assert [k for k, _ in c.extra] == ["alpha", "zeta"]  # sorted: canonical
    assert c.with_extra(zeta=0.5).get("zeta") == 0.5 and c != S.TierCfg()
    assert c.digest() != S.TierCfg().digest()
    assert S.TierCfg.from_json(c.to_json()) == c


def test_config_ints_become_floats_so_digests_do_not_depend_on_spelling():
    assert S.TierCfg(nu=1).digest() == S.TierCfg(nu=1.0).digest()
    assert S.TierCfg(retention_ratios=(1, 0.25)).retention_ratios == (1.0, 0.25)
    assert isinstance(S.TierCfg(nu=1).nu, float) and isinstance(S.TierCfg().days, int)


def test_enumerations_hold_what_the_specification_names():
    assert S.CHANNELS == ("diary", "chat", "article", "log", "note", "dialogue")
    assert S.SRC_KINDS == ("lived", "told", "read") and S.MENTION_ROLES == ("assert", "update", "retract", "recall")
    assert S.NEAR_MISS_KINDS == ("stale", "adjacent_day", "confuser", "habit")
    assert set(S.CHANNEL_ARMS) == {"TRUE", "SHUF_TYPE", "SHUF_LIFE", "TIME_SHIFT", "RANDOM", "CONST",
                                   "INVERTED", "NUISANCE_ONLY", "LAG", "ABSENT", "ORACLE", "LEAKY"}
    assert S.GATE_POLICIES[:9] == ("ALL", "GU", "GR", "GN", "GM", "GS", "GH", "GTN", "GO")
    assert set(S.DAY1_FAMILIES) == {"EP1", "SE4", "SE5", "IN1", "EP4", "IN4", "EP3c", "ME1"}
    assert set(S.DAY1_FAMILIES) < set(S.FAMILIES) and len(set(S.FAMILIES)) == len(S.FAMILIES)
    assert {"routine", "minor", "major", "move", "health", "purchase", "remark", "trip"} <= set(S.SCENE_NAMES)
    assert S.MAPPINGS == ("M1", "M2", "M3") and S.PARTITIONS == ("dev", "test")
    assert S.GENERATOR_ID == "lifesim-v0.1"
