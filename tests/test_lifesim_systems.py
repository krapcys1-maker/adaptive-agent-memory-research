"""Tests for lifesim.interface and lifesim.systems (LifeSim D1-E). No model, no network, no clock."""

from __future__ import annotations

import ast
import dataclasses
import functools
import hashlib
import math
import os
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import channel as C  # noqa: E402
from corpus.lifesim import queries as Q  # noqa: E402
from corpus.lifesim import rng as R  # noqa: E402
from corpus.lifesim import schema as S  # noqa: E402
from corpus.lifesim import verbalise as V  # noqa: E402
from corpus.lifesim import world as W  # noqa: E402
from corpus.lifesim.scorers import Scorer  # noqa: E402
from lifesim import interface as I  # noqa: E402
from lifesim import systems as SY  # noqa: E402

LIFESIM_PKG = ROOT / "scripts" / "lifesim"


# ------------------------------------------------------------------------------ fixtures


@functools.lru_cache(maxsize=None)
def built(tier: str, seed: int, cell: str = "C0"):
    cfg = S.TierCfg.for_tier(tier)
    w = W.build_world(seed, cfg)
    obs = V.render(w, cfg, seed, "dev")
    qs = Q.build_queries(w, cfg, cell, render=V.render_question)
    ch = C.make_channel(w, "TRUE", 0.7, None, seed)
    w = w.with_channel(ch)
    recs = I.records_from_world(w, obs)
    need = frozenset(o for q in qs for o in q.evidence_oids)
    return cfg, w, obs, qs, recs, need


def rec(i, text, t=None, channel="diary", h=None):
    return S.Record(id="o%05d" % i, text=text, timestamp=i * 10 if t is None else t, channel=channel, heartbeat=h)


def words(r):
    return len(r.text.split())


def random_stream(n=300, seed=7, lo=5, hi=60, with_h=True, vocab=50):
    g = R.stream(seed, "systems-test")
    out = []
    for i in range(n):
        k = g.ri(lo, hi)
        text = " ".join("w%d" % g.below(vocab) for _ in range(k))
        out.append(rec(i, text, t=i * 7, channel=S.CHANNELS[g.below(3)], h=round(g.u(), 6) if with_h else None))
    return out


class Poisoned:
    """A query object that fails on ANY attribute access."""

    def __getattribute__(self, name):
        raise AssertionError("a salience policy touched the query: %s" % name)


# ------------------------------------------------------------------------------ interface


def test_count_units_is_whitespace_words():
    assert I.count_units("a  b\tc\nd") == 4
    assert I.count_units("") == 0
    assert I.count_units("   ") == 0
    assert I.count_units("one") == 1


def test_fill_to_budget_is_a_prefix_that_stops_at_the_first_misfit():
    items = [rec(i, " ".join(["x"] * n)) for i, n in enumerate([5, 3, 9, 2, 2, 4])]
    f = I.fill_to_budget(items, 10)
    assert [r.id for r in f.items] == ["o00000", "o00001"] and f.words == 8 and f.n_ranked == 2
    # the 2-word items after the misfit are NOT taken: the context is a prefix of the ranking
    assert I.fill_to_budget(items, 0).items == ()
    assert I.fill_to_budget(items, 5).words == 5
    assert I.fill_to_budget([], 100).items == ()


def test_fill_to_budget_is_monotone_in_the_budget():
    items = [rec(i, " ".join(["x"] * (1 + (i * 7) % 11))) for i in range(40)]
    prev = set()
    for budget in range(0, 120, 3):
        cur = {r.id for r in I.fill_to_budget(items, budget).items}
        assert prev <= cur
        assert sum(words(r) for r in items if r.id in cur) <= budget
        prev = cur


def test_fill_to_budget_padding_fills_the_rest_without_repeats():
    items = [rec(i, " ".join(["x"] * n)) for i, n in enumerate([5, 9, 2])]
    pad = [items[1], rec(7, "a b"), rec(8, "c d e f g h i j")]
    f = I.fill_to_budget(items, 12, pad=pad, key=lambda r: r.id)
    assert [r.id for r in f.items[:f.n_ranked]] == ["o00000"]       # unpadded: 5 words, next (9) does not fit
    assert [r.id for r in f.items] == ["o00000", "o00007"]            # padding: o00001 and o00008 do not fit
    assert f.words == 7


def test_enforce_budget_truncates_whole_items_and_logs_overflow():
    recs = [rec(i, "a b c d e") for i in range(3)]
    ans = I.make_answer("", recs)
    assert ans.context_tokens == 15
    cut, over = I.enforce_budget(ans, 7)
    assert over == 10 and [c.oid for c in cut.context] == ["o00000"] and cut.context_tokens == 5
    assert cut.evidence_ids == ("o00000",) and I.meta_dict(cut)["overflow_words"] == "10"
    same, over = I.enforce_budget(ans, 15)
    assert over == 0 and same is ans


def test_make_answer_orders_the_context_chronologically_and_counts_words():
    a = I.make_answer("x", [rec(2, "late one"), rec(1, "early one two")], k=1)
    assert [c.oid for c in a.context] == ["o00001", "o00002"] and a.context_tokens == 5
    assert a.evidence_ids == ("o00001", "o00002") and dict(a.metadata) == {"k": "1"}
    assert dict(a.cost) == {"input_tokens": 0.0, "model_calls": 0.0, "output_tokens": 0.0}


def test_lifememory_protocol_checks():
    m = SY.Recency()
    m.reset(S.Card(name="Nuri"))
    m.ingest([rec(1, "a b c", h=0.5)])
    with pytest.raises(ValueError):
        m.ingest([rec(0, "older")])                         # out of time order
    with pytest.raises(TypeError):
        m.ingest(["not a record"])
    with pytest.raises(ValueError):
        m.query("q", 100, -1)
    with pytest.raises(TypeError):
        m.query(5, 100, 10)
    assert m._recs["o00001"].heartbeat is None              # stripped: Recency does not accept a heartbeat
    g = SY.GatedMemory(SY.Recency(), "GH", 1.0, 1)
    g.ingest([rec(1, "a b c", h=0.5)])
    assert g._store["o00001"].heartbeat == 0.5             # kept: the gate accepts it
    assert g._inner._recs["o00001"].heartbeat is None       # ... and does not pass it on


def test_a_query_sees_only_records_strictly_before_it():
    for make in (SY.Recency, SY.BM25, lambda: SY.BM25Time("2027-01-01"), lambda: SY.RandomK(1)):
        m = make()
        m.reset(None)
        m.ingest([rec(1, "apple pie", t=100), rec(2, "apple tart", t=200)])
        ids = lambda at: sorted(c.oid for c in m.query("apple", at, 100).context)  # noqa: E731
        assert ids(100) == [] and ids(101) == ["o00001"] and ids(200) == ["o00001"] and ids(201) == ["o00001", "o00002"]


def test_run_stream_is_online_and_read_only():
    cfg, w, obs, qs, recs, need = built("L0", 2)
    m = SY.Recency()
    pairs = I.run_stream(m, recs, qs, 200, card=w.card)
    assert [q.qid for q, _ in pairs] == [q.qid for q in sorted(qs, key=lambda x: (x.t_ask, x.qid))]
    for q, a in pairs:
        visible = sum(1 for r in recs if r.timestamp < q.t_ask)
        assert int(I.meta_dict(a)["n_candidates"]) == visible
        assert all(c.timestamp < q.t_ask for c in a.context)
    last = pairs[-1][0].t_ask
    assert len(m.stored_ids()) == sum(1 for r in recs if r.timestamp < last)
    # asking twice changes nothing
    q = qs[3]
    assert m.query(q.text, q.t_ask, 200).to_json() == m.query(q.text, q.t_ask, 200).to_json()


def test_run_stream_ingests_strictly_before_the_question():
    def query(qid, t):
        return S.Query(qid=qid, family="EP1", t_ask=t, text="anything", fmt="open", gold=S.Gold(kind="entity", value="x"))

    seen = []
    m = SY.Recency()
    I.run_stream(m, [rec(1, "a b", t=100), rec(2, "c d", t=200)], [query("q0001", 100), query("q0002", 101), query("q0003", 201)],
                 50, on_query=lambda q, a, mem: seen.append((q.qid, mem.stored_ids())))
    assert seen == [("q0001", ()), ("q0002", ("o00001",)), ("q0003", ("o00001", "o00002"))]


def test_run_stream_binds_only_oracles():
    cfg, w, obs, qs, recs, need = built("L0", 2)
    class Spy(SY.OracleText):
        bound = []
        def bind(self, query):
            self.bound.append(query.qid)
            super().bind(query)
    spy = Spy()
    I.run_stream(spy, recs, qs, 300, card=w.card)
    assert len(spy.bound) == len(qs)
    plain = SY.BM25()
    plain.bind = lambda q: (_ for _ in ()).throw(AssertionError("a non-oracle was bound"))
    I.run_stream(plain, recs, qs, 300, card=w.card)


def test_evidence_metrics_and_summary():
    q = lambda fam, ev: S.Query(qid="q1", family=fam, t_ask=99, text="t", fmt="open",  # noqa: E731
                                gold=S.Gold(kind="entity", value="x"), evidence_oids=tuple(ev))
    a = I.make_answer("", [rec(1, "a b"), rec(2, "c d")])
    r = I.evidence_metrics(q("EP1", ["o00001", "o00002"]), a, stored=["o00001", "o00002", "o00003"])
    assert r["complete"] is True and r["recall"] == 1.0 and r["stored_complete"] is True and r["context_words"] == 4
    r = I.evidence_metrics(q("EP3c", ["o00001", "o00009"]), a, stored=["o00001"])
    assert r["complete"] is False and r["recall"] == 0.5 and r["stored_recall"] == 0.5
    r0 = I.evidence_metrics(q("ME1", []), a)
    assert r0["complete"] is None and r0["recall"] is None
    rows = [I.evidence_metrics(q("EP1", ["o00001"]), a), I.evidence_metrics(q("EP1", ["o00009"]), a), r0]
    summ = I.summarise_evidence(rows)
    assert summ["by_family"]["EP1"]["complete"] == 0.5 and summ["by_family"]["ME1"]["complete"] is None
    assert summ["macro"]["complete"] == 0.5


def test_records_from_world_carry_the_channel_reading_and_no_gold():
    cfg, w, obs, qs, recs, need = built("L0", 2)
    assert [r.id for r in recs] == [o.oid for o in obs]
    assert all(r.heartbeat == w.channel.value(r.id) for r in recs)
    assert all(r.source == "" for r in recs)
    prov = I.records_from_world(w, obs, provenance=True)
    assert [r.source for r in prov] == [s.source for s in w.obs_specs]
    assert all(r.heartbeat is None for r in I.records_from_world(w.with_channel(None), obs))
    with pytest.raises(ValueError):
        I.records_from_world(w, obs[:-1])


# --------------------------------------------------------------------------------- arena


class FakeArena:
    name = "fake-arena"
    query_mutates_state = "read_only"

    def __init__(self):
        self.calls = []
        self.records = []
        self.budget = None

    def reset(self):
        self.calls.append("reset")
        self.records = []

    def ingest(self, records):
        self.calls.append(("ingest", [r["id"] for r in records]))
        self.records += records
        return I.Cost()

    def query(self, question, asked_at=None):
        self.calls.append(("query", asked_at, self.budget))
        ids = [self.records[-1]["id"], "ghost-id"]
        return I.ArenaAnswer(text="fake answer", evidence_ids=ids, context_tokens=7,
                             system_metadata={"k": "v"}, cost=I.Cost())


def test_wrap_arena_adapter_ingests_the_card_first_and_sets_the_budget():
    fake = FakeArena()
    m = I.wrap_arena_adapter(fake, "budget")
    m.reset(S.Card(name="Nuri", role="diarist"))
    assert fake.calls[-2:] == ["reset", ("ingest", ["card"])]            # reset, then the card as record 0
    assert "Nuri" in fake.records[0]["text"]
    cost = m.ingest([rec(1, "first line", t=1500, h=0.3)])
    assert fake.records[1]["day"] == 1 and "heartbeat" not in fake.records[1]   # the wrapper does not accept it
    assert cost is not None
    a = m.query("what?", 3000, 123)
    assert fake.budget == 123 and fake.calls[-1] == ("query", 3000, 123)
    assert a.text == "fake answer" and a.context_tokens == 7
    assert [c.oid for c in a.context] == ["o00001"] and dict(a.metadata)["unobservable_ids"] == "ghost-id"
    assert dict(a.metadata)["k"] == "v"
    assert a.evidence_ids == ("o00001", "ghost-id")


def test_validate_adapter_accepts_views_and_wrapped_adapters():
    arena = pytest.importorskip("arena.adapter")
    fixture = arena.synthetic_fixture()
    for make in (SY.BM25, SY.Recency, lambda: SY.BM25Time("2027-01-01"), lambda: SY.RandomK(3)):
        view = I.as_arena_adapter(make(), 60)
        report = arena.validate_adapter(view, fixture)
        assert report["admissible"], report["problems"]
        assert report["query_mutates_state"] == "read_only"
    # a view of a gate, and a wrapped view (an arena adapter wrapped as a LifeMemory, viewed again)
    gate = SY.GatedMemory(SY.BM25(), "GU", 0.5, 1)
    assert arena.validate_adapter(I.as_arena_adapter(gate, 60), fixture)["admissible"]
    roundtrip = I.as_arena_adapter(
        I.wrap_arena_adapter(I.as_arena_adapter(SY.BM25(), 60), "_budget_unused", asked_at_unit="day"), 60)
    assert arena.validate_adapter(roundtrip, fixture)["admissible"]


def test_arena_view_finds_the_superseding_record():
    arena = pytest.importorskip("arena.adapter")
    view = I.as_arena_adapter(SY.BM25(), 200)
    view.reset()
    view.ingest(arena.synthetic_fixture()["records"])
    ans = view.query("Which host should a billing deploy target?", 20)
    assert "r3" in ans.evidence_ids and ans.context_tokens <= 200


# ----------------------------------------------------------------------------------- BM25


def test_bm25_reproduces_a_hand_built_ranking():
    docs = [("d1", "red car red car red", 10), ("d2", "blue car", 20), ("d3", "green bike green bike green bike", 30),
            ("d4", "red bike", 40)]
    idx = SY.BM25Index()
    for oid, text, t in docs:
        idx.add(oid, text.split(), t)
    # N = 4, df(red) = 2 (d1, d4), df(car) = 2 (d1, d2), avgdl = (5 + 2 + 6 + 2) / 4
    n, avg = 4, 15 / 4
    idf = math.log(1 + (n - 2 + 0.5) / (2 + 0.5))
    def term(tf, dl):
        return idf * tf * 2.2 / (tf + 1.2 * (1 - 0.75 + 0.75 * dl / avg))
    expected = {"d1": term(3, 5) + term(2, 5), "d2": term(1, 2), "d4": term(1, 2)}
    got = idx.scores(["red", "car"], 100)
    assert set(got) == {"d1", "d2", "d4"}                     # d3 shares no term
    for k, v in expected.items():
        assert got[k] == pytest.approx(v, rel=1e-12)
    # by hand: d1 matches both terms and repeats them; d2 and d4 tie, the newer one (d4) comes first
    assert [o for o, _ in idx.ranking(["red", "car"], 100)] == ["d1", "d4", "d2"]
    # visibility: only documents before asked_at
    assert [o for o, _ in idx.ranking(["red", "car"], 25)] == ["d1", "d2"]


def test_bm25_removal_equals_a_fresh_index():
    g = R.stream(3, "bm25-remove")
    docs = [("d%d" % i, " ".join("t%d" % g.below(15) for _ in range(g.ri(3, 12))), i) for i in range(60)]
    a, b = SY.BM25Index(), SY.BM25Index()
    for oid, text, t in docs:
        a.add(oid, text.split(), t)
    drop = {oid for oid, _, t in docs if t % 3 == 0}
    for oid in drop:
        a.remove(oid)
    for oid, text, t in docs:
        if oid not in drop:
            b.add(oid, text.split(), t)
    for terms in (["t1", "t2"], ["t7"], ["t3", "t9", "t14"], ["zzz"]):
        assert a.ranking(terms, 1000) == b.ranking(terms, 1000)
    assert a.total_len == b.total_len and len(a) == len(b)
    assert sorted(a.postings) == sorted(b.postings)


def test_bm25_idf_is_the_lucene_form_and_never_negative():
    idx = SY.BM25Index()
    for i in range(10):
        idx.add("d%d" % i, ["common", "x%d" % i], i)
    assert idx.idf("common") > 0
    assert idx.idf("common") == pytest.approx(math.log(1 + 0.5 / 10.5), rel=1e-12)
    assert idx.idf("x1") == pytest.approx(math.log(1 + 9.5 / 1.5), rel=1e-12)


def test_query_terms_drop_stop_words_and_iso_dates():
    t = SY.query_terms("What did I have for breakfast on 2027-03-14? Reply UNKNOWN. CONF: 0-100")
    assert "breakfast" in t and "2027" not in t and "what" not in t and "unknown" not in t and t == sorted(set(t))


def test_parse_window_covers_the_cue_grammar():
    pw = lambda q, day: SY.parse_window(q, day * 1440 + 600, "2027-01-01")  # noqa: E731
    assert pw("breakfast on 2027-01-05?", 30) == (4, 4)
    assert pw("What did I eat yesterday?", 10) == (9, 9)
    assert pw("I read it 3 days ago.", 10) == (7, 7)
    assert pw("It was about two weeks ago.", 30) == (13, 19)
    assert pw("about three months ago", 120) == (15, 45)
    assert pw("went between 2027-01-04 and 2027-01-06 to the gym", 40) == (3, 5)
    assert pw("no date cue here", 40) is None
    assert pw("on 2027-02-31 maybe", 40) is None                     # not a date


def test_bm25time_ranks_the_window_first_and_hard_mode_drops_the_rest():
    recs = [rec(d, "I had porridge for breakfast", t=d * 1440 + 480) for d in range(1, 7)]
    recs.append(rec(9, "breakfast breakfast breakfast club breakfast", t=7 * 1440))   # lexically strongest, day 7
    q = "What did I have for breakfast on 2027-01-04?"                                  # day 3 -> record d = 4? see below
    soft = SY.BM25Time("2027-01-01")
    soft.reset(None)
    soft.ingest(recs)
    ranked = soft._ranked_ids(q, 10 * 1440)
    day_of = {r.id: r.timestamp // 1440 for r in recs}
    assert day_of[ranked[0]] == 3                                  # inside the window first although d9 scores higher
    assert "o00009" in ranked and ranked.index("o00009") > 0       # ... and the strong record is still reachable
    plain = SY.BM25()
    plain.reset(None)
    plain.ingest(recs)
    assert plain._ranked_ids(q, 10 * 1440)[0] == "o00009"          # without the window the strong record wins
    hard = SY.BM25Time("2027-01-01", hard=True)
    hard.reset(None)
    hard.ingest(recs)
    assert [day_of[o] for o in hard._ranked_ids(q, 10 * 1440)] == [3]
    wide = SY.BM25Time("2027-01-01", margin=1, hard=True)
    wide.reset(None)
    wide.ingest(recs)
    assert sorted(day_of[o] for o in wide._ranked_ids(q, 10 * 1440)) == [2, 3, 4]
    nodate = soft._ranked_ids("What did I have for breakfast?", 10 * 1440)
    assert nodate == plain._ranked_ids("What did I have for breakfast?", 10 * 1440)   # no cue: plain BM25


def test_bm25time_beats_bm25_and_recency_on_the_real_ladder():
    cfg, w, obs, qs, recs, need = built("L1", 3)
    fac = SY.ladder_factories(w, need=need, seed=3)
    macro = {}
    for name in ("B1", "random", "B2", "B2t"):
        pairs = I.run_stream(fac[name](), recs, qs, cfg.context_words, card=w.card)
        macro[name] = I.summarise_evidence([I.evidence_metrics(q, a) for q, a in pairs])["macro"]["complete"]
    assert macro["B1"] <= macro["B2"] <= macro["B2t"]
    assert macro["random"] <= macro["B2"] and macro["B2t"] > 0.5


# --------------------------------------------------------------------------- every system


def system_zoo(w, cfg, need, seed):
    emb = SY.hashing_embedder(32)
    zoo = {
        "recency": SY.Recency(), "random": SY.RandomK(seed), "bm25": SY.BM25(), "bm25t": SY.BM25Time(cfg.start_date),
        "dense": SY.DenseStore(emb), "hybrid": SY.HybridStore(emb, cfg.start_date),
        "oracle_text": SY.OracleText(), "oracle_store": SY.OracleStore(need, cfg.start_date),
        "prior": SY.Prior(w), "heuristic": SY.Heuristic.for_world(w), "abstain": SY.Abstainer(),
        "oracle_struct": SY.OracleStruct(w),
    }
    for pol in S.GATE_POLICIES:
        if pol != "GL":
            zoo["gate-" + pol] = SY.GatedMemory(SY.BM25Time(cfg.start_date), pol, 0.25, seed, need=need)
    return zoo


def test_every_system_respects_the_budget_in_words():
    cfg, w, obs, qs, recs, need = built("L0", 4)
    for budget in (0, 1, 40, 150, 400):
        for name, m in system_zoo(w, cfg, need, 4).items():
            for q, a in I.run_stream(m, recs, qs, budget, card=w.card):
                words_in = sum(len(c.text.split()) for c in a.context)
                assert words_in <= budget, (name, budget, q.qid)
                assert a.context_tokens == words_in, (name, budget)
                if name != "oracle_struct":
                    assert a.evidence_ids == tuple(c.oid for c in a.context), name
                ts = [c.timestamp for c in a.context]
                assert ts == sorted(ts) and all(t < q.t_ask for t in ts), name
                assert len({c.oid for c in a.context}) == len(a.context), name


def test_every_context_item_is_a_verbatim_ingested_record():
    cfg, w, obs, qs, recs, need = built("L0", 4)
    text_of = {r.id: (r.text, r.timestamp) for r in recs}
    for name, m in system_zoo(w, cfg, need, 4).items():
        for q, a in I.run_stream(m, recs, qs, 300, card=w.card):
            for c in a.context:
                assert text_of[c.oid] == (c.text, c.timestamp), name


def test_recency_returns_the_newest_prefix_and_random_is_seeded():
    m = SY.Recency()
    m.reset(None)
    m.ingest([rec(i, " ".join(["x"] * 10)) for i in range(10)])
    assert [c.oid for c in m.query("q", 10 ** 6, 35).context] == ["o00007", "o00008", "o00009"]
    a = SY.RandomK(5)
    b = SY.RandomK(5)
    c = SY.RandomK(6)
    for mem in (a, b, c):
        mem.reset(None)
        mem.ingest([rec(i, " ".join(["x"] * 10)) for i in range(60)])
    ans = lambda mem: [x.oid for x in mem.query("q", 10 ** 6, 100).context]  # noqa: E731
    assert ans(a) == ans(b) == ans(a) and ans(a) != ans(c)


def test_dense_ranking_and_reciprocal_rank_fusion_by_hand():
    vocab = {"alpha": 0, "beta": 1, "gamma": 2}

    def embed(texts):
        out = []
        for t in texts:
            v = [0.0] * 3
            for w_ in t.split():
                if w_ in vocab:
                    v[vocab[w_]] += 1.0
            out.append(v)
        return out

    calls = []
    def counting(texts):
        calls.append(len(texts))
        return embed(texts)

    d = SY.DenseStore(counting)
    d.reset(None)
    d.ingest([rec(1, "alpha alpha", t=10), rec(2, "alpha beta", t=20), rec(3, "gamma", t=30)])
    assert calls == [3]                                        # one embedder call per ingest batch
    assert [c.oid for c in d.query("alpha", 100, 100).context] == ["o00001", "o00002", "o00003"]
    assert calls == [3, 1]                                     # and one per question
    ranked = d._dense_ranking("alpha", 100, None)
    assert [r.id for r in ranked] == ["o00001", "o00002", "o00003"]      # cosine 1.0, 0.7071, 0.0
    assert calls == [3, 1, 1]
    # fusion: lexical order [a, b, c], dense order [b, c, a] -> scores
    #   a = 1/61 + 1/63, b = 1/62 + 1/61, c = 1/63 + 1/62  ->  b, a, c
    h = SY.HybridStore(embed, "2027-01-01")
    h.reset(None)
    h.ingest([rec(1, "alpha beta", t=10), rec(2, "alpha", t=20), rec(3, "alpha gamma", t=30)])
    h._lex._ranked_ids = lambda q, at: ["o00001", "o00002", "o00003"]
    h._dense._dense_ranking = lambda q, at, depth: [h._recs["o00002"], h._recs["o00003"], h._recs["o00001"]]
    got = [r.id for r in h._ranked_records("q", 100)]
    assert got == ["o00002", "o00001", "o00003"]
    a_, b_, c_ = 1 / 61 + 1 / 63, 1 / 62 + 1 / 61, 1 / 63 + 1 / 62
    assert b_ > a_ > c_


def test_dense_depth_cuts_the_ranking():
    embed = SY.hashing_embedder(16)
    d = SY.DenseStore(embed, depth=2)
    d.reset(None)
    d.ingest([rec(i, "alpha beta %d" % i, t=10 * i) for i in range(1, 7)])
    assert len(d.query("alpha", 10 ** 6, 1000).context) == 2
    full = SY.DenseStore(embed)
    full.reset(None)
    full.ingest([rec(i, "alpha beta %d" % i, t=10 * i) for i in range(1, 7)])
    assert len(full.query("alpha", 10 ** 6, 1000).context) == 6


def test_arena_view_without_a_time_sees_every_record_and_the_day_unit_converts():
    arena = pytest.importorskip("arena.adapter")
    view = I.as_arena_adapter(SY.BM25(), 200)
    view.reset()
    view.ingest(arena.synthetic_fixture()["records"])
    assert "r3" in view.query("billing staging host").evidence_ids        # asked_at None: after the last record
    fake = FakeArena()
    m = I.wrap_arena_adapter(fake, "budget", asked_at_unit="day")
    m.reset(None)
    m.ingest([rec(1, "first line", t=1500)])
    m.query("q", 3000, 10)
    assert fake.calls[-1] == ("query", 2, 10)                              # 3000 minutes = day 2
    with pytest.raises(ValueError):
        I.wrap_arena_adapter(fake, "budget", asked_at_unit="week")


def test_rrf_scores_by_hand():
    sc = SY.rrf_scores([["a", "b", "c"], ["b", "c", "a"]], 60)
    assert sc["a"] == pytest.approx(1 / 61 + 1 / 63, rel=1e-12)
    assert sc["b"] == pytest.approx(1 / 62 + 1 / 61, rel=1e-12)
    assert sc["c"] == pytest.approx(1 / 63 + 1 / 62, rel=1e-12)
    assert SY.rrf_scores([["x"]], 1) == {"x": 0.5} and SY.rrf_scores([], 60) == {}
    assert SY.rrf_scores([["x", "y"], ["y"]], 10)["y"] == pytest.approx(1 / 12 + 1 / 11, rel=1e-12)


def test_store_and_gate_factories():
    cfg, w, obs, qs, recs, need = built("L0", 2)
    assert isinstance(SY.make_store("S-LEX", cfg.start_date), SY.BM25Time)
    assert isinstance(SY.make_store("S-HYB", cfg.start_date, SY.hashing_embedder(8)), SY.HybridStore)
    with pytest.raises(ValueError):
        SY.make_store("S-HYB", cfg.start_date)                 # a dense store needs an embedder
    with pytest.raises(ValueError):
        SY.make_store("S-NOPE")
    g = SY.make_gate(w, "GH", 0.25, 3, store="S-HYB", need=need, embedder=SY.hashing_embedder(8))
    pairs = I.run_stream(g, recs, qs, cfg.context_words, card=w.card)
    assert len(pairs) == len(qs) and g.stats()["policy"] == "GH" and g.stats()["inner"] == "C2-hybrid"
    lex = SY.make_gate(w, "GU", 0.25, 3)
    assert lex.stats()["inner"] == "B2t-bm25-time"


def test_hashing_embedder_is_deterministic_and_lexical():
    e = SY.hashing_embedder(16)
    v1, v2 = e(["red car on the road"])[0], e(["red car on the road"])[0]
    assert v1 == v2 and len(v1) == 16
    assert e([""])[0] == [0.0] * 16


# ---------------------------------------------------------------------------- blind systems


def test_infer_slot_on_rendered_questions_in_both_partitions():
    bad = []
    for seed in (1, 2):
        cfg = S.TierCfg.for_tier("L1")
        w = W.build_world(seed, cfg)
        for part in ("dev", "test"):
            for q in Q.build_queries(w, cfg, "C0", render=V.render_question, partition=part):
                if SY.infer_slot(q.text) != q.ask:
                    bad.append((q.family, q.ask, SY.infer_slot(q.text)))
    assert bad == []
    assert SY.infer_slot("Tell me a joke") == ""


def test_prior_answers_with_the_mode_and_abstains_without_a_prior():
    cfg, w, obs, qs, recs, need = built("L1", 3)
    p = SY.Prior(w)
    p.reset(None)
    modes = {x.slot: x.mode() for x in w.priors}
    a = p.query("What did I have for breakfast on 2027-01-05? Reply UNKNOWN when it was not mentioned.", 10 ** 6, 0)
    assert a.text == modes["breakfast"] and not a.abstained and a.context == ()
    b = p.query("Tell me a joke", 10 ** 6, 0)
    assert b.abstained and b.text == "UNKNOWN"
    # no prior for the companion slot
    c = p.query("Who was there with me on 2027-02-18?", 10 ** 6, 0)
    assert c.abstained


def test_heuristic_answers_with_the_most_frequent_value_seen_so_far():
    cfg, w, obs, qs, recs, need = built("L1", 3)
    h = SY.Heuristic.for_world(w)
    h.reset(None)
    stream_ = [rec(1, "I had porridge for breakfast"), rec(2, "croissant for breakfast today"),
               rec(3, "porridge again for breakfast"), rec(4, "I had porridge and croissant for breakfast")]
    h.ingest(stream_[:2])
    h.ingest(stream_[2:])
    a = h.query("What did I have for breakfast on 2027-01-02?", 10 ** 6, 0)
    assert a.text == "porridge"
    # incremental: counts keep growing with later records
    h.ingest([rec(5, "croissant", t=60), rec(6, "croissant for breakfast", t=70), rec(7, "croissant and croissant", t=80)])
    assert h.query("What did I have for breakfast?", 10 ** 6, 0).text == "croissant"


def test_blind_floors_stay_near_chance_and_always_abstain_scores_the_abstain_share():
    cfg, w, obs, qs, recs, need = built("L1", 3)
    sc = Scorer(w)
    fac = SY.ladder_factories(w, need=need, seed=3)
    for name in ("B0a", "B0h"):
        pairs = I.run_stream(fac[name](), recs, qs, 0, card=w.card)
        acc = sum(sc.score(q, a).correct for q, a in pairs) / len(pairs)
        assert acc < 0.15, (name, acc)
    pairs = I.run_stream(SY.Abstainer(), recs, qs, 0, card=w.card)
    hits = [q.family == "ME1" for q, a in pairs if sc.score(q, a).correct]
    assert all(hits) and len(hits) == sum(1 for q in qs if q.family == "ME1")


# --------------------------------------------------------------------------------- oracles


def test_oracles_are_perfect_where_they_should_be():
    for tier, seed in (("L0", 2), ("L1", 3)):
        cfg, w, obs, qs, recs, need = built(tier, seed)
        sc = Scorer(w)
        for q, a in I.run_stream(SY.OracleStruct(w), recs, qs, cfg.context_words, card=w.card):
            r = sc.score(q, a)
            assert r.correct and r.score == 1.0, (q.qid, q.family, r.error_type)
            assert a.abstained == (q.family == "ME1") and a.evidence_ids == q.evidence_oids
        for q, a in I.run_stream(SY.OracleText(), recs, qs, cfg.context_words, card=w.card):
            m = I.evidence_metrics(q, a)
            assert m["complete"] in (True, None), (q.qid, q.family, m)
        fast = I.run_stream(SY.OracleStruct(w, source="fast"), recs, qs, 0, card=w.card)
        assert all(a.text == q.gold.value for q, a in fast)


def test_oracles_need_the_bound_query_and_the_store_holds_only_the_need():
    cfg, w, obs, qs, recs, need = built("L0", 2)
    for m in (SY.OracleText(), SY.OracleStruct(w)):
        m.reset(None)
        with pytest.raises(RuntimeError):
            m.query("anything", 10 ** 6, 100)
    store = SY.OracleStore(need, cfg.start_date)
    I.run_stream(store, recs, qs, cfg.context_words, card=w.card)
    assert set(store.stored_ids()) <= set(need) and set(store.stored_ids())
    assert SY.OracleText.needs_query and SY.OracleStruct.needs_query and not SY.BM25.needs_query


# ------------------------------------------------------------------------- the gate: capacity


def reference_gate(records, R_, weight):
    """Brute-force online gate: add, then evict the lowest (weight, arrival) until the words fit."""
    ratio = Fraction(repr(R_))
    store, seen = [], 0
    states = []
    for seq, r in enumerate(records):
        seen += words(r)
        store.append((weight(r), seq, r))
        cap = (ratio.numerator * seen) // ratio.denominator
        while sum(words(x[2]) for x in store) > cap:
            store.remove(min(store, key=lambda x: (x[0], x[1])))
        states.append([x[2].id for x in sorted(store, key=lambda x: x[1])])
    return states


@pytest.mark.parametrize("policy", [p for p in S.GATE_POLICIES if p not in ("GL",)])
@pytest.mark.parametrize("ratio", [0.1, 0.25, 0.3, 1.0])
def test_the_gate_holds_exactly_floor_r_times_words_seen_at_every_step(policy, ratio):
    stream_ = random_stream(150, seed=11)
    g = SY.GatedMemory(SY.BM25(), policy, ratio, seed=5, need={r.id for r in stream_[::9]})
    g.reset(None)
    seen = 0
    for n_seen, r in enumerate(stream_, start=1):
        g.ingest([r])
        seen += words(r)
        st = g.stats()
        ids = set(g.stored_ids())
        retained = [x for x in stream_ if x.id in ids]
        assert st["stored_words"] == sum(words(x) for x in retained)
        assert st["words_seen"] == seen
        if policy == "ALL":
            assert st["capacity"] is None and len(retained) == n_seen
            continue
        cap = math.floor(Fraction(str(ratio)) * seen)
        assert st["capacity"] == cap
        assert st["stored_words"] <= cap                       # never over capacity
        if ratio < 1.0:
            assert cap - st["stored_words"] < 60               # and within one record of it
        else:
            assert st["stored_words"] == seen and st["evicted"] == 0
        assert g._inner.stored_ids() == g.stored_ids()         # the inner store mirrors the retained set


def test_the_gate_is_exact_when_records_have_one_size():
    stream_ = [rec(i, " ".join(["x"] * 10)) for i in range(40)]
    g = SY.GatedMemory(SY.Recency(), "GU", 0.5, 3)
    g.reset(None)
    for i, r in enumerate(stream_, start=1):
        g.ingest([r])
        st = g.stats()
        assert st["capacity"] == 5 * i
        assert st["stored_words"] == (5 * i if i % 2 == 0 else 5 * i - 5)    # whole records of 10 words


def test_the_capacity_uses_exact_decimal_arithmetic():
    g = SY.GatedMemory(SY.Recency(), "GU", 0.29, 1)
    g.reset(None)
    g.ingest([rec(1, " ".join(["x"] * 100))])
    assert g.stats()["capacity"] == 29                          # float 0.29 * 100 is 28.999999999999996
    g2 = SY.GatedMemory(SY.Recency(), "GU", 0.1, 1)
    g2.reset(None)
    g2.ingest([rec(1, " ".join(["x"] * 70))])
    assert g2.stats()["capacity"] == 7


def test_batch_ingest_equals_record_by_record():
    stream_ = random_stream(120, seed=13)
    for pol in ("GU", "GR", "GH", "GN", "GM", "GS", "GTN"):
        one = SY.GatedMemory(SY.BM25(), pol, 0.2, 9)
        many = SY.GatedMemory(SY.BM25(), pol, 0.2, 9)
        one.reset(None)
        many.reset(None)
        for r in stream_:
            one.ingest([r])
        many.ingest(stream_)
        assert one.stored_ids() == many.stored_ids(), pol
        assert one._inner.stored_ids() == many._inner.stored_ids(), pol


@pytest.mark.parametrize("policy", ["GR", "GH"])
def test_heap_gate_equals_a_brute_force_reference(policy):
    stream_ = random_stream(110, seed=17)
    weight = (lambda r: float(r.timestamp)) if policy == "GR" else (lambda r: r.heartbeat)
    ref = reference_gate(stream_, 0.15, weight)
    g = SY.GatedMemory(SY.Recency(), policy, 0.15, 2)
    g.reset(None)
    for r, expected in zip(stream_, ref):
        g.ingest([r])
        assert list(g.stored_ids()) == expected


def test_r_equals_one_is_byte_identical_across_policies():
    cfg, w, obs, qs, recs, need = built("L0", 2)
    base = [a.to_json() for _, a in I.run_stream(SY.BM25Time(cfg.start_date), recs, qs, cfg.context_words, card=w.card)]
    for pol in S.GATE_POLICIES:
        if pol == "GL":
            continue
        g = SY.GatedMemory(SY.BM25Time(cfg.start_date), pol, 1.0, seed=99, need=need)
        out = [a.to_json() for _, a in I.run_stream(g, recs, qs, cfg.context_words, card=w.card)]
        assert out == base, pol
        last = max(q.t_ask for q in qs)
        assert set(g.stored_ids()) == {r.id for r in recs if r.timestamp < last}, pol
        assert g.stats()["evicted"] == 0, pol


def test_invalid_gates_are_refused():
    with pytest.raises(NotImplementedError):
        SY.GatedMemory(SY.BM25(), "GL", 0.5)
    for bad in (0.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            SY.GatedMemory(SY.BM25(), "GU", bad)
    with pytest.raises(ValueError):
        SY.GatedMemory(SY.BM25(), "NOPE", 0.5)
    with pytest.raises(TypeError):
        SY.GatedMemory(SY.Abstainer(), "GU", 0.5)             # cannot forget
    g = SY.GatedMemory(SY.BM25(), "GU", 1.0)
    g.reset(None)
    g.ingest([rec(1, "a b")])
    with pytest.raises(ValueError):
        g.ingest([rec(1, "a b", t=50)])                       # duplicate id


# ------------------------------------------------------------------------ the gate: policies


def run_policy(policy, stream_, ratio, seed=1, need=()):
    g = SY.GatedMemory(SY.Recency(), policy, ratio, seed, need=need)
    g.reset(None)
    g.ingest(stream_)
    return g


def test_gr_keeps_the_newest_and_gu_is_seeded_and_not_recency():
    stream_ = [rec(i, " ".join(["x"] * 10)) for i in range(100)]
    gr = run_policy("GR", stream_, 0.2)
    assert gr.stored_ids() == tuple("o%05d" % i for i in range(80, 100))
    a, b, c = (run_policy("GU", stream_, 0.2, seed=s).stored_ids() for s in (1, 1, 2))
    assert a == b and a != c and a != gr.stored_ids()
    ages = [int(x[1:]) for x in a]
    assert min(ages) < 50 < max(ages)                         # spread over the whole stream


def test_gn_and_gs_keep_the_lines_with_new_words():
    stream_ = []
    for i in range(40):
        if i % 2 == 0:
            stream_.append(rec(i, "same words again and again and again and again and again"))
        else:
            stream_.append(rec(i, " ".join("q%dx%d" % (i, k) for k in range(10))))
    for pol in ("GN", "GS"):
        g = run_policy(pol, stream_, 0.3)
        w_ = g.weights()
        kept = [int(x[1:]) for x in g.stored_ids()]
        assert kept and all(k % 2 == 1 or k == 0 for k in kept), (pol, kept)
        assert min(w_.values()) > 0.5 or pol == "GS"
    g = run_policy("GN", stream_, 1.0)
    assert g.weights()["o00000"] == 1.0 and g.weights()["o00002"] == 0.0 and g.weights()["o00001"] == 1.0


def test_gm_counts_later_repetitions_of_rare_tokens_only():
    filler = [rec(i, "the plain words of an ordinary day number %d" % i) for i in range(1, 201)]
    a = rec(300, "met zorbo at the market", t=3000)
    later = [rec(301, "zorbo called again about the market", t=3010), rec(302, "ordinary the day only", t=3020),
             rec(303, "zorbo", t=3030), rec(304, "something else entirely", t=3040)]
    g = run_policy("GM", filler + [a] + later, 1.0)
    w_ = g.weights()
    assert w_["o00300"] == 2.0          # bumped by the two later lines that repeat 'zorbo' (not by the common words)
    assert w_["o00301"] == 1.0 and w_["o00303"] == 0.0 and w_["o00302"] == 0.0 and w_["o00304"] == 0.0


def test_gh_keeps_the_high_readings_and_gtn_removes_the_type_base_rate():
    g_ = R.stream(21, "gtn")
    stream_ = []
    for i in range(400):
        kind = "diary" if i % 2 == 0 else "chat"
        h = 0.6 + 0.3 * g_.u() if kind == "diary" else 0.1 + 0.3 * g_.u()
        stream_.append(rec(i, " ".join(["x"] * 10), channel=kind, h=round(h, 6)))
    gh = run_policy("GH", stream_, 0.2)
    gtn = run_policy("GTN", stream_, 0.2)
    chat = lambda g: sum(1 for i in g.stored_ids() if stream_[int(i[1:])].channel == "chat") / len(g.stored_ids())  # noqa: E731
    assert chat(gh) < 0.1                                   # the raw reading keeps the louder channel kind
    assert 0.3 < chat(gtn) < 0.7                            # the type-normalised reading keeps both
    kept = [stream_[int(i[1:])].heartbeat for i in gh.stored_ids()]
    assert sum(kept) / len(kept) > 0.7
    # within each kind GTN keeps the high readings of that kind (it is not a uniform draw)
    def mean_h(g, kind, only_kept=True):
        hs = [r.heartbeat for r in stream_ if r.channel == kind and (not only_kept or r.id in set(g.stored_ids()))]
        return sum(hs) / len(hs)
    for kind in ("diary", "chat"):
        assert mean_h(gtn, kind) > mean_h(gtn, kind, only_kept=False) + 0.05, kind


def test_gh_imputes_the_running_median_for_missing_readings():
    stream_ = [rec(i, "a b", h=0.2 if i < 5 else None) for i in range(8)]
    g = run_policy("GH", stream_, 1.0)
    assert g.weights()["o00006"] == 0.2


def test_go_retains_the_needed_lines_and_ga_follows_the_affect_lexicon():
    stream_ = [rec(i, " ".join(["x%d" % i] * 10)) for i in range(120)]
    need = {"o%05d" % i for i in range(80, 90)}
    g = run_policy("GO", stream_, 0.2, need=need)
    assert need <= set(g.stored_ids())
    emphasis = "my heart was pounding and I was absolutely terrified"
    texts = [emphasis, "a calm quiet line about the garden path", emphasis + " again", "nothing much"]
    ga = run_policy("GA", [rec(i, t) for i, t in enumerate(texts)], 1.0)
    for i, t in enumerate(texts):
        assert ga.weights()["o%05d" % i] == float(len(V.affect_scan(t)))
    assert ga.weights()["o00000"] > 0 and ga.weights()["o00001"] == 0.0


def test_salience_policies_read_only_the_channel():
    cfg, w, obs, qs, recs, need = built("L0", 2)
    # 1. a poisoned Query proves that nothing reads the query: bind it before every question
    for pol in ("GH", "GTN", "GU", "GR", "GN", "GS", "GM", "GA", "ALL"):
        a = SY.GatedMemory(SY.BM25Time(cfg.start_date), pol, 0.25, 4)
        b = SY.GatedMemory(SY.BM25Time(cfg.start_date), pol, 0.25, 4)
        a.reset(w.card)
        b.reset(w.card)
        pos = 0
        for q in sorted(qs, key=lambda x: x.t_ask):
            batch = [r for r in recs[pos:] if r.timestamp < q.t_ask]
            pos += len(batch)
            a.ingest(batch)
            b.ingest(batch)
            a.bind(Poisoned())
            assert a.query(q.text, q.t_ask, 300).to_json() == b.query(q.text, q.t_ask, 300).to_json()
    # 2. GH retains the same positions whatever the text says, as long as the readings and sizes are equal
    stream_ = random_stream(160, seed=31)
    other = [dataclasses.replace(r, text=" ".join(["z%d" % ((i * 7 + k) % 40) for k in range(words(r))]))
             for i, r in enumerate(stream_)]
    assert run_policy("GH", stream_, 0.2).stored_ids() == run_policy("GH", other, 0.2).stored_ids()
    inverted = [dataclasses.replace(r, heartbeat=round(1.0 - r.heartbeat, 6)) for r in stream_]
    assert run_policy("GH", stream_, 0.2).stored_ids() != run_policy("GH", inverted, 0.2).stored_ids()
    # 3. the non-channel policies ignore the reading altogether
    blank = [dataclasses.replace(r, heartbeat=None) for r in stream_]
    for pol in ("GU", "GR", "GN", "GS", "GM", "GA"):
        assert run_policy(pol, stream_, 0.2).stored_ids() == run_policy(pol, blank, 0.2).stored_ids(), pol


def test_const_readings_behave_like_uniform_retention():
    stream_ = [rec(i, " ".join(["x"] * 10), h=0.5) for i in range(300)]
    gh = run_policy("GH", stream_, 0.2, seed=8).stored_ids()
    ages = [int(x[1:]) for x in gh]
    assert min(ages) < 100 and max(ages) > 200                  # ties break at random, not by age


# ------------------------------------------------------------------------ determinism, lint


_DIGEST_SCRIPT = """
import hashlib, sys
sys.path.insert(0, %r)
from corpus.lifesim import schema as S, world as W, verbalise as V, queries as Q, channel as C
from lifesim import interface as I, systems as SY
cfg = S.TierCfg.for_tier("L0")
w = W.build_world(1, cfg)
obs = V.render(w, cfg, 1, "dev")
qs = Q.build_queries(w, cfg, "C0", render=V.render_question)
w = w.with_channel(C.make_channel(w, "TRUE", 0.7, None, 1))
recs = I.records_from_world(w, obs)
h = hashlib.sha256()
mems = [SY.BM25Time(cfg.start_date), SY.BM25(), SY.HybridStore(SY.hashing_embedder(16), cfg.start_date),
        SY.GatedMemory(SY.BM25Time(cfg.start_date), "GM", 0.25, 1), SY.GatedMemory(SY.BM25Time(cfg.start_date), "GS", 0.25, 1),
        SY.GatedMemory(SY.BM25Time(cfg.start_date), "GH", 0.25, 1), SY.Heuristic.for_world(w), SY.RandomK(1)]
for m in mems:
    for q, a in I.run_stream(m, recs, qs, cfg.context_words, card=w.card):
        h.update(a.to_json().encode())
print(h.hexdigest())
"""


def _digest_in_subprocess(hash_seed):
    env = dict(os.environ, PYTHONHASHSEED=str(hash_seed))
    out = subprocess.run([sys.executable, "-c", _DIGEST_SCRIPT % str(ROOT / "scripts")], env=env,
                         capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_answers_do_not_depend_on_the_hash_seed():
    d1, d2 = _digest_in_subprocess(1), _digest_in_subprocess(2)
    assert d1 == d2 and len(d1) == 64


def test_the_same_run_twice_is_byte_identical():
    cfg, w, obs, qs, recs, need = built("L0", 2)
    def digest():
        h = hashlib.sha256()
        for name, m in system_zoo(w, cfg, need, 2).items():
            for q, a in I.run_stream(m, recs, qs, cfg.context_words, card=w.card):
                h.update(a.to_json().encode())
        return h.hexdigest()
    assert digest() == digest()


@pytest.mark.parametrize("path", sorted(LIFESIM_PKG.glob("*.py")), ids=lambda p: p.name)
def test_lint_of_the_systems_package(path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, feature_version=(3, 11))
    doc = ast.get_docstring(tree) or ""
    assert doc and "does not" in doc.lower(), "module docstring must say what the module does NOT do"
    banned = {"random", "time", "datetime"}
    heavy = {"numpy", "scipy"}
    for node in tree.body:                                      # module level imports only
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module.split(".")[0]]
        assert not (set(names) & banned), (path.name, names)
        assert not (set(names) & heavy), (path.name, names)
    calls = [n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert "hash" not in calls
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
    assert not (imported & banned), (path.name, imported & banned)
