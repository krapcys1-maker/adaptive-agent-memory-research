"""Tests for the AAM-E0 arms, with the dense backend replaced by a hashing embedder."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus import goalshift as gs  # noqa: E402
from corpus.goalshift_arms import (ARM_NAMES, ArmConfig, CachedEmbedder, Engine,  # noqa: E402
                                   HashingEmbedder, dot)

EMB = CachedEmbedder(HashingEmbedder())


@pytest.fixture(scope="module")
def world():
    return gs.generate(1)


def _engine(world, labels=True):
    lab = {eid: l["concepts"] for eid, l in world["labels"]["events"].items()} if labels else None
    return Engine(world["events"], EMB, ArmConfig(), lab, seed=1)


def _probes(world):
    cue_of = {c["probe_id"]: c for c in world["cues"]}
    for p in world["labels"]["probes"]:
        yield p, cue_of[p["probe_id"]]


def _run(engine, arm, p, cue, C=250, R=0.10):
    return engine.run(arm, cue["cue"], cue["goal"], cue["day"], C, R,
                      [p["concept"]] if arm in ("O", "Oc") else None)


def test_hashing_embedder_is_deterministic_and_normalised():
    a = HashingEmbedder().encode(["the freight carrier arrived late"])[0]
    b = HashingEmbedder().encode(["the freight carrier arrived late"])[0]
    assert a == b and abs(dot(a, a) - 1.0) < 1e-9


def test_cached_embedder_calls_inner_once():
    calls = []

    class Inner:
        def encode(self, texts):
            calls.append(list(texts))
            return [[1.0, 0.0] for _ in texts]

    c = CachedEmbedder(Inner())
    c.encode(["a", "b"])
    c.encode(["a", "b", "c"])
    assert calls == [["a", "b"], ["c"]]


def test_arm_a_is_empty(world):
    eng = _engine(world)
    p, cue = next(iter(_probes(world)))
    res = _run(eng, "A", p, cue)
    assert res["context"] == [] and res["words"] == 0


def test_no_future_leakage_and_budget(world):
    eng = _engine(world)
    day_of = {e["event_id"]: e["day"] for e in world["events"]}
    for p, cue in _probes(world):
        for arm in ARM_NAMES:
            for C in (100, 250, 500):
                res = _run(eng, arm, p, cue, C=C, R=0.25)
                assert res["words"] <= C
                assert all(day_of[c["event_id"]] <= cue["day"] for c in res["context"])


def test_future_events_are_invisible_to_every_arm(world):
    p, cue = next(iter(_probes(world)))
    mutated = copy.deepcopy(world)
    for e in mutated["events"]:
        if e["day"] > cue["day"]:
            e["text"] = "zzz totally different future words " * 3 + e["text"]
            e["consequence"] = 3
    a, b = _engine(world), _engine(mutated)
    for arm in ARM_NAMES:
        ra, rb = _run(a, arm, p, cue, R=0.25), _run(b, arm, p, cue, R=0.25)
        assert [c["event_id"] for c in ra["context"]] == [c["event_id"] for c in rb["context"]], arm


def test_f1_finds_the_high_overlap_target(world):
    eng = _engine(world)
    hits = [_run(eng, "F1", p, cue)["context"] for p, cue in _probes(world) if p["cell"] == "C1"]
    found = sum(1 for (p, cue), ctx in zip([x for x in _probes(world) if x[0]["cell"] == "C1"], hits)
                if p["gold_event_id"] in [c["event_id"] for c in ctx])
    assert found >= 3


def test_b3_is_newest_first(world):
    eng = _engine(world)
    p, cue = next(iter(_probes(world)))
    res = _run(eng, "B3", p, cue)
    days = [c["day"] for c in res["context"]]
    assert days == sorted(days, reverse=True)


def test_retained_budget_is_respected(world):
    eng = _engine(world)
    for p, cue in _probes(world):
        for R in (0.10, 0.25):
            part = eng._partition(cue["day"], R)
            assert sum(len(e["text"].split()) for e in part["recent"]) <= part["R_words"] * 0.4
            for arm in ("Del", "Sum", "Sum-raw", "D", "O", "S"):
                _run(eng, arm, p, cue, R=R)
            kept = sum(len(e["text"].split()) for e in part["recent"])
            tstate = eng._trace_state("D", cue["day"], R)
            assert kept + tstate["trace_words"] <= part["R_words"]
            ostate = eng._trace_state("O", cue["day"], R)
            assert kept + ostate["trace_words"] <= part["R_words"]
            # Del and Sum: the words they store (raw / summaries) stay within R as well
            by_id = {e["event_id"]: e for e in world["events"]}
            for arm in ("Del", "Sum", "Sum-raw"):
                res = _run(eng, arm, p, cue, R=R)
                stored = res["meta"]["stored_ids"]
                recent_ids = {e["event_id"] for e in part["recent"]}
                words = sum(len(by_id[i]["text"].split()) for i in stored if i in recent_ids)
                for i in stored:
                    if i in recent_ids:
                        continue
                    text = by_id[i]["text"].split()
                    words += len(text) if arm == "Del" else min(len(text), ArmConfig().summary_words)
                assert words <= part["R_words"], (arm, words, part["R_words"])


def test_sum_returns_lead_truncated_text_and_sum_raw_expands(world):
    eng = _engine(world)
    for p, cue in _probes(world):
        s = _run(eng, "Sum", p, cue, R=0.25)
        raw = {e["event_id"]: e["text"] for e in world["events"]}
        for c in s["context"]:
            if c["form"] == "summary":
                assert raw[c["event_id"]].startswith(c["text"])
                assert len(c["text"].split()) <= ArmConfig().summary_words
        r = _run(eng, "Sum-raw", p, cue, R=0.25)
        assert all(c["text"] == raw[c["event_id"]] for c in r["context"])
        break


def test_oracle_arm_reaches_the_target_when_budget_allows(world):
    eng = _engine(world)
    hits = [p["gold_event_id"] in [c["event_id"] for c in _run(eng, "O", p, cue, R=0.25)["context"]]
            for p, cue in _probes(world)]
    assert sum(hits) >= 11


def test_d_does_not_read_labels(world):
    with_labels, without = _engine(world, True), _engine(world, False)
    for p, cue in _probes(world):
        a, b = _run(with_labels, "D", p, cue), _run(without, "D", p, cue)
        assert [c["event_id"] for c in a["context"]] == [c["event_id"] for c in b["context"]]
        assert a["log"] == b["log"]


def test_d_logs_the_link_behind_every_fetch(world):
    eng = _engine(world)
    seen = 0
    for p, cue in _probes(world):
        res = _run(eng, "D", p, cue, R=0.25)
        assert [l["event_id"] for l in res["log"]] == [c["event_id"] for c in res["context"]]
        for entry in res["log"]:
            assert entry["links"] and entry["via"] in ("direct", "spread") and entry["score"] > 0
            seen += 1
    assert seen > 0


def test_shuffled_pointers_are_a_permutation_of_the_stored_traces(world):
    eng = _engine(world)
    p, cue = next(iter(_probes(world)))
    _run(eng, "S", p, cue, R=0.25)
    state = eng._trace_state("S", cue["day"], 0.25)
    traces = [t for t in state["stored"] if t["form"] == "trace"]
    assert sorted(t["pointer"] for t in traces) == sorted(t["event_id"] for t in traces)
    assert any(t["pointer"] != t["event_id"] for t in traces)
    assert all(t["pointer"] == t["event_id"] for t in state["stored"] if t["form"] == "recent")


def test_importance_uses_fields_known_at_write_time(world):
    from corpus.goalshift_arms import importance

    e = world["events"][10]
    assert importance({**e, "novelty": 1.0, "consequence": 3}, 0.5) == 1.0
    assert importance({**e, "novelty": 0.0, "consequence": 0}, 0.5) == 0.0


def test_unknown_arm_is_rejected(world):
    p, cue = next(iter(_probes(world)))
    with pytest.raises(ValueError):
        _run(_engine(world), "nope", p, cue)


class StubEmbedder:
    """Vectors fixed by a marker word: texts with ALPHA point one way, the rest the other."""

    def encode(self, texts):
        return [[1.0, 0.0] if "ALPHA" in t else [0.0, 1.0] for t in texts]


def _tiny_events(n=12):
    return [{"event_id": "e%03d" % i, "day": 1 + i // 2, "position": i,
             "text": ("ALPHA token about the case " if i == 3 else "plain routine entry number ")
             + "w%d filler words to make the line a little longer than twelve words." % i,
             "novelty": 0.5, "consequence": 1} for i in range(1, n + 1)]


def test_f2_puts_the_best_dense_match_first():
    eng = Engine(_tiny_events(), CachedEmbedder(StubEmbedder()), ArmConfig(), None, seed=0)
    res = eng.run("F2", "ALPHA question", "goal", 6, 40, 0.0)
    assert res["context"][0]["event_id"] == "e003"
    ranked = eng._dense_order(eng.visible(6), "ALPHA question")
    assert ranked[0]["event_id"] == "e003"


def test_del_keeps_the_newest_events(world):
    eng = _engine(world)
    for p, cue in _probes(world):
        res = _run(eng, "Del", p, cue, C=500, R=0.10)
        part = eng._partition(cue["day"], 0.10)
        assert part["recent"] and part["recent"][0]["event_id"] in [c["event_id"] for c in res["context"]]


def test_link_ids_are_the_context_events_for_trace_arms_and_empty_otherwise(world):
    eng = _engine(world)
    p, cue = next(iter(_probes(world)))
    for arm in ("D", "O", "Oc", "S"):
        res = _run(eng, arm, p, cue, R=0.25)
        assert res["link_ids"] == [c["event_id"] for c in res["context"]], arm
    for arm in ("A", "F1", "F2", "B3", "Del", "Sum", "Sum-raw"):
        assert _run(eng, arm, p, cue)["link_ids"] == [], arm


def test_oc_has_d_s_stored_set_and_costs_and_o_stores_more(world):
    eng = _engine(world)
    p, cue = next(iter(_probes(world)))
    day = cue["day"]
    for R in (0.10, 0.25):
        d, oc, o = (eng._trace_state(a, day, R) for a in ("D", "Oc", "O"))
        assert [i["event_id"] for i in oc["stored"]] == [i["event_id"] for i in d["stored"]]
        assert oc["trace_words"] == d["trace_words"]
        assert o["n_traces"] >= d["n_traces"]
    d10, o10 = eng._trace_state("D", day, 0.10), eng._trace_state("O", day, 0.10)
    assert o10["n_traces"] > d10["n_traces"]  # the cheaper oracle traces cover more events


def test_gold_stored_is_reported_and_bounds_the_hit(world):
    eng = _engine(world)
    for p, cue in _probes(world):
        for arm in ("Del", "Sum-raw", "D", "Oc", "S"):
            res = _run(eng, arm, p, cue)
            stored = set(res["meta"]["stored_ids"])
            got = {c["event_id"] for c in res["context"]}
            if p["gold_event_id"] in got:
                assert p["gold_event_id"] in stored, arm


def test_shuffles_differ_and_are_each_a_permutation(world):
    eng = _engine(world)
    p, cue = next(iter(_probes(world)))
    a = eng._trace_state("S", cue["day"], 0.25, 0)
    b = eng._trace_state("S", cue["day"], 0.25, 1)
    pa = [t["pointer"] for t in a["stored"] if t["form"] == "trace"]
    pb = [t["pointer"] for t in b["stored"] if t["form"] == "trace"]
    assert pa != pb and sorted(pa) == sorted(pb)


def test_concept_rule_drops_one_off_tokens_and_stemmer_fragments(world):
    eng = _engine(world)
    day = 30
    concepts, _ = eng._concepts(day)
    df = {}
    for cs in concepts.values():
        for st in cs:
            df[st] = df.get(st, 0) + 1
    visible_df = {}
    for e in eng.visible(day):
        for st in gs.stems_of(e["text"]):
            visible_df[st] = visible_df.get(st, 0) + 1
    for cs in concepts.values():
        for st in cs:
            assert len(st) >= 4 and visible_df[st] >= 2
    loose = Engine(world["events"], EMB, ArmConfig(min_concept_df=1, min_concept_len=3), None, 1)
    loose_concepts, _ = loose._concepts(day)
    assert sum(len(v) for v in loose_concepts.values()) > sum(len(v) for v in concepts.values())


def test_s_is_worse_than_the_oracle_on_the_dev_world(world):
    eng = _engine(world)
    o = s = 0
    for p, cue in _probes(world):
        o += p["gold_event_id"] in [c["event_id"] for c in _run(eng, "O", p, cue, R=0.25)["context"]]
        s += p["gold_event_id"] in [c["event_id"] for c in _run(eng, "S", p, cue, R=0.25)["context"]]
    assert s < o
