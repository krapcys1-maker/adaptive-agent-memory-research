"""Tests for corpus.lifesim.vocab (LifeSim D1-A). Standard library and pytest only."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import rng as R  # noqa: E402
from corpus.lifesim import schema as S  # noqa: E402
from corpus.lifesim import vocab as V  # noqa: E402

ANSWER_POOLS = ("colours", "dishes", "jobs", "relations", "times", "counts")
COMPOSITION_POOLS = ("shop_types", "story_kinds", "errands")


# ------------------------------------------------------------------------- pools


def test_pool_sizes_match_the_specification():
    assert len(V.COLOURS) == 40 and len(V.DISHES) == 120
    assert len(V.TIMES) == 24 and len(V.COUNTS) == 24
    for pid in ANSWER_POOLS + COMPOSITION_POOLS:
        pool = V.POOLS[pid]
        assert len(pool) >= 24, pid  # blind chance at most 1/24
        assert len(set(pool)) == len(pool), pid
    assert len(V.WEEKDAYS) == 7 and len(V.MONTHS) == 12


def test_the_per_world_entity_pools_reach_the_minimum_at_every_tier():
    for cfg in S.TIERS.values():
        for n in (cfg.n_persons, cfg.n_cities, cfg.n_streets, cfg.n_shops):
            assert n >= cfg.min_pool >= 24


@pytest.mark.parametrize("pid", sorted(V.POOLS))
def test_pool_values_are_clean_ascii_lowercase_strings(pid):
    for v in V.POOLS[pid]:
        assert v == v.strip() and "  " not in v and v.isascii() and v == v.lower(), v
    for alias, target in V.POOL_ALIASES.get(pid, ()):
        assert alias.isascii() and alias == alias.strip() and target in V.POOLS[pid]


@pytest.mark.parametrize("pid", sorted(V.POOLS))
def test_pools_are_unique_after_normalisation_and_free_of_word_level_containment(pid):
    pool = V.POOLS[pid]
    toks = {v: V.norm(v).split() for v in pool}
    assert len({V.norm(v) for v in pool}) == len(pool)
    for a, b in itertools.permutations(pool, 2):
        ta, tb = toks[a], toks[b]
        contained = any(tb[i:i + len(ta)] == ta for i in range(len(tb) - len(ta) + 1))
        assert not contained, "%s is inside %s" % (a, b)  # longest match is then unambiguous


@pytest.mark.parametrize("pid", sorted(V.POOL_ALIASES))
def test_aliases_resolve_to_exactly_one_value_and_never_shadow_another(pid):
    voc = V.pool_vocab(pid)
    idx = voc.index  # raises ValueError on any ambiguity
    for v in voc.values:
        assert idx[V.norm(v)] == v
    for alias, target in voc.aliases:
        assert idx[V.norm(alias)] == target
    assert len({V.norm(a) for a, _ in voc.aliases}) == len(voc.aliases)


def test_selected_aliases():
    colours, dishes = V.pool_vocab("colours"), V.pool_vocab("dishes")
    assert colours.canonical("gray") == "grey" and colours.canonical("GREY") == "grey"
    assert colours.canonical("Navy Blue") == "navy" and colours.canonical("pink") == "pink"
    assert dishes.canonical("oatmeal") == "porridge" and dishes.canonical("Cheese Omelet") == "cheese omelette"
    assert V.pool_vocab("jobs").canonical("fireman") == "firefighter"
    assert V.pool_vocab("relations").canonical("Neighbor") == "neighbour"
    assert V.pool_vocab("counts").canonical("twenty-four") == "24"
    assert V.pool_vocab("counts").canonical("three") == "3" and V.pool_vocab("counts").canonical("zero") is None


def test_times_are_the_twenty_four_quarter_hours_from_1400_to_1945():
    assert V.TIMES[0] == "14:00" and V.TIMES[-1] == "19:45"
    assert list(V.TIMES) == sorted(V.TIMES)
    minutes = [int(t[:2]) * 60 + int(t[3:]) for t in V.TIMES]
    assert all(b - a == 15 for a, b in zip(minutes, minutes[1:]))
    assert all(len(t) == 5 and t[2] == ":" for t in V.TIMES)


def test_counts_are_one_to_twenty_four_with_number_word_aliases():
    assert V.COUNTS == tuple(str(i) for i in range(1, 25))
    counts = V.pool_vocab("counts")
    assert len(V.NUMBER_WORDS) == 25
    for i in range(1, 25):
        assert counts.canonical(V.NUMBER_WORDS[i]) == str(i)
        assert counts.canonical(str(i)) == str(i)


# ------------------------------------------------------------------------ normaliser


def test_norm():
    assert V.norm("  Café—Crème!  ") == "cafe creme"
    assert V.norm("GRAY") == "gray" and V.norm("Navy-Blue") == "navy blue"
    assert V.norm("O'Neil's") == "o neil s" and V.norm("18:00") == "18 00"
    assert V.norm("ＡＢＣ") == "abc"  # full-width letters (NFKC)
    assert V.norm("Straße") == "strasse" and V.norm("") == "" and V.norm("...") == ""
    assert V.norm("twenty\tfour\n") == "twenty four"
    assert V.norm("Łódź") == "łodz"  # letters without a decomposition are kept
    assert V.norm(V.norm("Ünï Cödé")) == V.norm("Ünï Cödé")  # idempotent


# ---------------------------------------------------------------- Vocab and matching


def test_matches_uses_the_longest_match_and_reports_distinct_values_in_order():
    colours = V.pool_vocab("colours")
    assert colours.matches("It was a navy blue car") == ["navy"]  # not ['navy', 'blue']
    assert colours.matches("a blue car and a red car") == ["blue", "red"]
    assert colours.matches("RED!!! red, red") == ["red"]
    assert colours.matches("dark-green, almost olive green") == ["green", "olive"]
    assert colours.matches("charcoal gray") == ["charcoal"]
    assert colours.matches("silver grey") == ["silver"]
    assert colours.matches("no colour was mentioned") == []
    assert colours.matches("reddish") == []  # no inflection handling by design
    assert colours.matches("") == []
    assert V.pool_vocab("dishes").matches("I had oatmeal with banana") == ["porridge"]
    assert V.pool_vocab("dishes").matches("a chocolate croissant") == ["pain au chocolat"]
    assert V.pool_vocab("times").matches("It closes at 18:00.") == ["18:00"]
    assert V.pool_vocab("counts").matches("about twenty four, or maybe 3") == ["24", "3"]


def test_spans_give_token_positions_and_do_not_overlap():
    colours = V.pool_vocab("colours")
    assert colours.spans("a navy blue car, then red") == [(1, 3, "navy"), (5, 6, "red")]
    spans = colours.spans("red blue green red")
    assert [(a, b) for a, b, _ in spans] == [(0, 1), (1, 2), (2, 3), (3, 4)]
    assert V.Vocab("empty", ()).spans("anything") == [] and V.Vocab("empty", ()).max_words == 0
    assert colours.max_words == 2 and V.pool_vocab("dishes").max_words == 5


def test_vocab_rejects_ambiguous_or_dangling_aliases():
    with pytest.raises(ValueError, match="names both"):
        V.Vocab("x", ("a", "b"), (("a", "b"),)).index
    with pytest.raises(ValueError, match="not in"):
        V.Vocab("x", ("a", "b"), (("c", "z"),)).index
    with pytest.raises(ValueError, match="names both"):
        V.Vocab("x", ("a", "b"), (("Q", "a"), ("q", "b"))).index
    ok = V.Vocab("x", ("a", "b"), (("Q", "a"),)).with_aliases((("r", "b"),))
    assert ok.canonical("q") == "a" and ok.canonical("R") == "b" and len(ok) == 2


# ----------------------------------------------------------------------- name inventories


def test_syllable_inventories_are_disjoint_and_use_disjoint_letters():
    dev, test = V.CONSONANTS["dev"], V.CONSONANTS["test"]
    assert not set(dev) & set(test) and not set(dev + test) & set(V.VOWELS)
    assert not set(V.SYLLABLES["dev"]) & set(V.SYLLABLES["test"])
    assert len(V.SYLLABLES["dev"]) == len(V.SYLLABLES["test"]) == 45
    assert not set(V.CODAS["dev"]) & set(V.CODAS["test"])
    assert not set(V.SUFFIXES["dev"]) & set(V.SUFFIXES["test"])
    for p in ("dev", "test"):
        allowed = set(V.CONSONANTS[p]) | set(V.VOWELS)
        assert set(V.CODAS[p]) <= set(V.CONSONANTS[p])
        for s in V.SUFFIXES[p]:
            assert set(s) <= allowed, (p, s)


def test_the_two_name_spaces_cannot_intersect():
    def space(p):
        syl = V.SYLLABLES[p]
        names = {a + b for a, b in itertools.product(syl, syl)}
        names |= {n + c for n in list(names) for c in V.CODAS[p]}
        names |= {a + b + c for a, b, c in itertools.product(syl[::3], syl[::5], syl[::7])}
        return {n.capitalize() for n in names}
    dev, test = space("dev"), space("test")
    assert len(dev) > 5000 and len(test) > 5000
    assert not dev & test


def test_make_names_is_deterministic_golden_vector():
    r = R.stream(1, "cast")
    used: set = set()
    assert V.make_names(r, 6, "dev", "person", used) == ["Guto", "Batu", "Reme", "Tabaku", "Kumus", "Damem"]
    assert V.make_names(r, 6, "test", "person", used) == ["Yicel", "Peva", "Fohovo", "Cuca", "Haveje", "Hejo"]
    assert V.make_names(r, 4, "dev", "city", used) == ["Bokadam", "Susa", "Nenamont", "Redadam"]
    assert V.make_names(r, 4, "test", "city", used) == ["Levaville", "Vuyi", "Cavi", "Lowuwuflow"]
    assert V.make_names(r, 3, "dev", "street", used) == ["Sotu", "Togon", "Koki"]
    assert V.make_names(r, 3, "test", "shop", used) == ["Fijofof", "Wuya", "Yuca"]
    assert V.make_names(r, 3, "dev", "org", used) == ["Nuke", "Sinaki", "Kakegi"]
    assert r.state == 10333382435915901182 and len(used) == 29


@pytest.mark.parametrize("partition", ["dev", "test"])
@pytest.mark.parametrize("kind", ["person", "city", "street", "shop", "org"])
def test_names_use_only_their_partitions_consonants_and_are_well_formed(partition, kind):
    other = "test" if partition == "dev" else "dev"
    for seed in range(40):
        names = V.make_names(R.stream(seed, "cast", kind), 25, partition, kind)
        assert len(names) == 25 and len({n.casefold() for n in names}) == 25
        for n in names:
            assert n.isalpha() and n.isascii() and n[0].isupper() and n[1:] == n[1:].lower()
            assert len(n) >= 4
            assert not set(n.casefold()) & set(V.CONSONANTS[other]), (n, partition)
            assert V.partition_of_name(n) == partition
            assert n.casefold() not in V.RESERVED


def test_no_name_ever_appears_in_both_partitions():
    dev, test = set(), set()
    for seed in range(120):
        dev |= {n.casefold() for n in V.make_names(R.stream(seed, "cast"), 30, "dev")}
        test |= {n.casefold() for n in V.make_names(R.stream(seed, "cast"), 30, "test")}
    assert len(dev) > 1500 and len(test) > 1500
    assert not dev & test


def test_names_in_one_world_are_unique_and_never_nest():
    for partition in ("dev", "test"):
        for seed in range(10):
            r = R.stream(seed, "cast")
            used: set = set()
            cfg = S.TIERS["L3"]  # the biggest cast the generator will ask for
            names = []
            for n, kind in ((cfg.n_persons, "person"), (cfg.n_cities, "city"), (cfg.n_streets, "street"),
                            (cfg.n_shops, "shop"), (cfg.n_orgs, "org")):
                names += V.make_names(r, n, partition, kind, used)
            keys = [n.casefold() for n in names]
            assert len(keys) == len(set(keys)) == 100 + 60 + 60 + 60 + 24
            assert used == set(keys)
            for a, b in itertools.permutations(keys, 2):
                assert a not in b, (a, b)


def test_used_set_is_respected_across_calls():
    used = {"guto"}
    names = V.make_names(R.stream(1, "cast"), 5, "dev", "person", used)
    assert "Guto" not in names and "guto" in used and len(used) == 6
    again = V.make_names(R.stream(1, "cast"), 5, "dev", "person", used)
    assert not {n.casefold() for n in again} & {n.casefold() for n in names}


def test_reserved_words_are_filtered_and_exhaustion_is_reported(monkeypatch):
    assert {"banana", "red", "porridge", "pharmacy", "roma"} <= V.RESERVED
    assert V.make_names(R.stream(1, "cast"), 1, "dev")[0] == "Guto"
    monkeypatch.setattr(V, "RESERVED", frozenset({"guto"}))
    assert V.make_names(R.stream(1, "cast"), 1, "dev")[0] != "Guto"
    everything = {s for s in V.SYLLABLES["dev"]}  # every dev name contains one of these
    with pytest.raises(RuntimeError, match="exhausted"):
        V.make_names(R.stream(1, "cast"), 1, "dev", used=everything)


def test_names_shorter_than_four_letters_are_rejected(monkeypatch):
    offered = iter(["Kab", "Ka", "Kabu"])
    monkeypatch.setattr(V, "_one_name", lambda rng, partition, kind: next(offered))
    assert V.make_names(R.stream(1, "x"), 1, "dev") == ["Kabu"]


def test_make_names_rejects_bad_arguments():
    with pytest.raises(ValueError):
        V.make_names(R.stream(1, "x"), 3, "train")
    with pytest.raises(ValueError):
        V.make_names(R.stream(1, "x"), 3, "dev", kind="planet")
    assert V.make_names(R.stream(1, "x"), 0, "dev") == []


def test_partition_of_name():
    assert V.partition_of_name("Guto") == "dev" and V.partition_of_name("Fohovo") == "test"
    assert V.partition_of_name("Mirela") is None  # mixes both sets (m, r vs l)
    assert V.partition_of_name("aeiou") is None and V.partition_of_name("") is None


# ----------------------------------------------------------------------- closed_vocab


def _world(*entities):
    return S.World(seed=1, cfg=S.TIERS["L0"], entities=tuple(entities))


def test_closed_vocab_for_static_pools_returns_the_whole_pool():
    w = _world()
    assert V.closed_vocab(w, "breakfast").values == V.DISHES
    assert V.closed_vocab(w, "pool:colours").values == V.COLOURS
    assert V.closed_vocab(w, "closing_time").values == V.TIMES
    assert V.closed_vocab(w, "visit_count").canonical("two") == "2"
    assert V.closed_vocab(w, "car_colour").canonical("gray") == "grey"
    assert V.closed_vocab(w, "works_as").vocab_id == "pool:jobs"


def test_closed_vocab_for_entity_kinds_lists_all_entities_of_the_kind_with_aliases():
    w = _world(S.Entity("e0001", "city", "Bokadam"), S.Entity("e0002", "city", "Susa", aliases=("Susa City",)),
               S.Entity("e0003", "person", "Guto", aliases=("G",)), S.Entity("e0004", "shop", "Nuke Bakery"))
    cities = V.closed_vocab(w, "lives_in")
    assert cities.vocab_id == "kind:city" and cities.values == ("Bokadam", "Susa")
    assert cities.canonical("susa city") == "Susa" and cities.matches("I live in Bokadam now") == ["Bokadam"]
    assert V.closed_vocab(w, "kind:person").canonical("g") == "Guto"
    assert V.closed_vocab(w, "shop").matches("the nuke bakery on the corner") == ["Nuke Bakery"]
    assert len(V.closed_vocab(w, "kind:street")) == 0  # no entities of that kind: empty, not an error


def test_gold_vocab_ids_round_trip_through_closed_vocab():
    w = _world(S.Entity("e0001", "city", "Bokadam"))
    for vid in ("pool:dishes", "pool:colours", "kind:city", "pool:times"):
        gold = S.Gold(kind="entity", value="x", vocab_id=vid)
        assert V.closed_vocab(w, gold.vocab_id).vocab_id == vid


def test_unknown_slots_are_an_error_and_every_registered_slot_resolves():
    w = _world()
    for bad in ("nonsense", "pool:nonsense", "volume:colours", ""):
        with pytest.raises(KeyError):
            V.closed_vocab(w, bad)
    for slot, vid in V.SLOTS.items():
        scheme, _, ident = vid.partition(":")
        assert (scheme == "pool" and ident in V.POOLS) or (scheme == "kind" and ident in S.ENTITY_KINDS), slot
        assert V.closed_vocab(w, slot).vocab_id == vid
    # the predicates the Day-1 families ask about all have a vocabulary
    for slot in ("breakfast", "lives_in", "works_as", "relation", "vehicle_colour", "closing_time",
                 "visit_count", "companion"):
        assert slot in V.SLOTS


def test_blind_chance_of_every_answer_vocabulary_is_at_most_one_in_twenty_four():
    w = _world()
    for slot in ("breakfast", "vehicle_colour", "works_as", "relation", "closing_time", "visit_count"):
        assert 1 / len(V.closed_vocab(w, slot)) <= 1 / 24
