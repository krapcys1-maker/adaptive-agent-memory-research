"""Additive boundary tests from issue 73; both original suites remain unchanged."""
import importlib.util
import math
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=["scripts/wmb/memory_kernel.py", "scripts/wmb/kernel/memory_kernel.py"])
def mk(request):
    name = "mutation_boundary_" + ("frozen" if "/kernel/" not in request.param else "live")
    spec = importlib.util.spec_from_file_location(name, ROOT / request.param)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def item(mk, ident="one", text="amber birch", created="2020-01-01", **kwargs):
    return mk.Item(ident, "note", "account_history", created, text, **kwargs)


def lookup(mk, index, query="amber", now="2026-01-01", **profile):
    return mk.retrieve(index, query, "personal", now,
                       dict(embed="off", names=False, lex_tau=0.1, min_evidence=0.0, **profile))


def ids(result):
    return [it.id for it in result["items"]]


def test_as_of_includes_the_exact_instant_but_retrieval_does_not(mk):
    it = item(mk, created="2020-01-01T12:00:00Z")
    index = mk.build_index([it], "2020-01-01T12:00:00Z")
    assert list(index.items) == ["one"]
    assert ids(lookup(mk, index, now="2020-01-01T12:00:00Z")) == []
    assert ids(lookup(mk, index, now="2020-01-01T12:00:01Z")) == ["one"]


def test_replacement_becomes_visible_strictly_after_its_own_instant(mk):
    old = item(mk, "old")
    new = item(mk, "new", created="2021-01-01", meta={"supersedes": "old"})
    index = mk.build_index([old, new], "2026")
    assert ids(lookup(mk, index, now="2021-01-01")) == ["old"]
    assert ids(lookup(mk, index, now="2021-01-01T00:00:01")) == ["new"]


def test_mixed_embedding_dimensions_degrade_and_clear_the_cache(mk):
    index = mk.build_index([item(mk), item(mk, "two")], "2026",
                           embedder=lambda _: [[1.0, 0.0], [1.0, 0.0, 0.0]])
    assert index.degraded
    assert index.vectors == {} and index.dim == 0


@pytest.mark.parametrize("word,expected", [("cries", "cry"), ("grass", "grass"), ("Imre's", "imre")])
def test_plural_and_possessive_boundaries(mk, word, expected):
    assert mk.stem(word) == expected


def test_sentence_interior_names_are_distinct_from_initial_capitals(mk):
    assert "uma" in mk.analyse("We saw Uma.")[2]
    assert "uma" not in mk.analyse("Uma arrived.")[2]


def test_rare_name_document_frequency_is_inclusive_and_two_letters_do_not_qualify(mk):
    index = mk.build_index([item(mk, "a", "we met Uma"), item(mk, "b", "they met Uma"), item(mk, "c", "we met Xi")], "2026")
    profile = dict(embed="off", names=True, min_evidence=100.0, rare_df=2)
    found = mk.retrieve(index, "we met Uma", "personal", "2026", profile)
    assert sorted(ids(found)) == ["a", "b"]
    assert ids(mk.retrieve(index, "we met Uma", "personal", "2026", dict(profile, rare_df=1))) == []
    assert ids(mk.retrieve(index, "we met Xi", "personal", "2026", profile)) == []


def test_query_cap_is_enforced_before_the_name_channel(mk, monkeypatch):
    monkeypatch.setattr(mk, "MAX_QUERY_CHARS", 24)
    index = mk.build_index([item(mk, text="we met Uma")], "2026")
    query = "ordinary filler words " * 4 + "Uma"
    assert ids(mk.retrieve(index, query, "personal", "2026",
                          dict(embed="off", names=True, min_evidence=100.0))) == []


def test_calibration_excludes_an_item_at_the_query_instant(mk):
    index = mk.build_index([item(mk)], "2026")
    value = mk.calibrate(index, [("amber birch", "2020-01-01")])
    assert value == (0.0 if mk.VERSION == "0.1.0" else None)


def test_embedding_calibration_floors_to_four_decimal_places(mk):
    cosine = 0.123456789
    vector = [cosine, math.sqrt(1.0 - cosine * cosine)]
    index = mk.build_index([item(mk)], "2026", embedder=lambda _: [vector], vectors={"one": [1.0, 0.0]})
    assert mk.calibrate(index, [("question", "2026")], channel="embedding") == 0.1234


def test_embedding_below_its_gate_is_not_reported_as_a_matching_channel(mk):
    index = mk.build_index([item(mk)], "2026", embedder=lambda _: [[0.6, 0.8]], vectors={"one": [1.0, 0.0]})
    found = mk.retrieve(index, "amber", "note", "2026",
                        dict(embed="required", names=False, tau=0.9, min_evidence=0.0, lex_tau=0.1))
    assert ids(found) == ["one"]
    assert found["reasons"] == [["lexical"]]


def test_one_shared_word_without_document_frequencies_does_not_support_a_callback(mk):
    result = {"items": [item(mk)], "keys": ["2020-01-01T00:00:00"],
              "now_key": "2026-01-01T00:00:00", "task_type": "note"}
    assert mk.guard(result, "As I wrote earlier about amber.")["flags"] == ["unsupported_reference"]


def test_distinctive_shared_word_at_the_guard_boundary_is_supported(mk, monkeypatch):
    if mk.VERSION != "0.2.0":
        return  # The frozen line has a word-count guard, not an idf boundary.
    monkeypatch.setattr(mk, "DISTINCT", 1.0)
    result = {"items": [item(mk)], "keys": ["2020-01-01T00:00:00"],
              "now_key": "2026-01-01T00:00:00", "task_type": "note", "n_index": 10, "_df": {"amber": 1}}
    assert mk.guard(result, "As I wrote earlier about amber.")["flags"] == []
