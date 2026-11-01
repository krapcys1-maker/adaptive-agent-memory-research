"""wmb.memory_kernel: the interface agreed with the writing agent (N-028), on synthetic data only.

Thresholded injection, no future, origin classes, a channel for names, an optional embedder, the injection log, the reference guard, and the limits of the contract
(standard library only, no effects on import, 300 ms at 2000 items).
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
import subprocess
import sys
import tracemalloc
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "wmb"))

import memory_kernel as mk  # noqa: E402

SOURCE = ROOT / "scripts" / "wmb" / "memory_kernel.py"
SYNONYMS = {"boat": "ferry", "mum": "mother", "records": "ledgers", "charts": "tables", "firm": "company", "stored": "kept"}
SYNONYM_QUERY = "tide charts boat firm records stored mum kitchen"        # the words of n1 said in other words: few shared stems, a high cosine


def bow_embedder(dim: int = 64, calls: list | None = None):
    """A fake embedder: words (with a few synonyms merged) hashed into `dim` buckets."""
    def embed(texts):
        if calls is not None:
            calls.append(len(texts))
        out = []
        for text in texts:
            vec = [0.0] * dim
            for word in text.lower().replace("?", " ").replace(".", " ").split():
                vec[int(hashlib.md5(SYNONYMS.get(word, word).encode()).hexdigest(), 16) % dim] += 1.0
            out.append(vec)
        return out
    return embed


def base_items():
    return [
        mk.Item("n1", "note", "account_history", "2026-09-01", "tide tables and the ferry company ledgers kept by my mother in the kitchen"),
        mk.Item("n2", "note", "account_history", "2026-09-10", "the colleague Imre called the first recovery procedure the boring document that saved the archive"),
        mk.Item("e1", "event", "fiction_autobio", "1989-03-04", "you were born in Kellmouth a fishing and rail town on a cold estuary"),
        mk.Item("n3", "note", "account_history", "2026-09-20", "sourdough starter named Ledger survived two jobs and a flood in the basement"),
        mk.Item("w1", "note", "world_knowledge", "2020-01-01", "the harbour board keeps minutes of every tide gauge reading"),
    ]


def ids(result) -> list:
    return [i.id for i in result["items"]]


def hmac_fn(text: str) -> str:
    return "h" + hashlib.sha256(("key:" + text).encode("utf-8")).hexdigest()[:12]


def test_the_file_is_standard_library_only_licensed_and_has_no_effects_on_import(tmp_path: Path) -> None:
    text = SOURCE.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "# SPDX-License-Identifier: Apache-2.0"
    imported = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported and imported <= set(sys.stdlib_module_names) and not imported & {"socket", "urllib", "http", "ssl", "subprocess", "os", "pathlib", "requests", "numpy"}
    code = ("import os, sys; sys.path.insert(0, %r); files, loaded = set(os.listdir('.')), set(sys.modules); import memory_kernel; "
            "assert set(os.listdir('.')) == files; "
            "assert not {'socket', 'urllib', 'http', 'ssl', 'subprocess', 'requests', 'numpy'} & (set(sys.modules) - loaded); print('ok')") % str(SOURCE.parent)
    run = subprocess.run([sys.executable, "-I", "-c", code], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and run.stdout.strip() == "ok" and run.stderr == ""


def test_dates_of_any_precision_compare_in_utc_and_invalid_ones_are_refused() -> None:
    assert mk.when("2026-09-10") == "2026-09-10T00:00:00" and mk.when("2026-09") == "2026-09-01T00:00:00" and mk.when("1989") == "1989-01-01T00:00:00"
    assert mk.when("2026-09-10T08:00:00+02:00") == "2026-09-10T06:00:00" == mk.when("2026-09-10T08:00:00+0200") == mk.when("2026-09-10 06:00:00Z")
    assert mk.when("2026-09-10T23:30:00-01:30") == "2026-09-11T01:00:00" and mk.when(date(2026, 9, 10)) == "2026-09-10T00:00:00"
    assert mk.when("2026-09-10T08:00:00.123Z") == "2026-09-10T08:00:00"
    for bad in ("10.09.2026", "2026-13-01", "2026-02-30", "2026-09-10T25:00:00", "yesterday", ""):
        with pytest.raises(ValueError):
            mk.when(bad)


def test_a_query_with_enough_shared_evidence_returns_the_item_and_an_unrelated_one_returns_nothing() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    hit = mk.retrieve(index, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "lexical")
    assert hit["status"] == "ok" and ids(hit) == ["n1"] and hit["reasons"] == [["lexical"]] and hit["scores"][0] >= 1.0 and hit["channel_scores"][0]["lexical"] == 1.0
    assert hit["n_candidates"] == 1 and hit["n_considered"] == 4 and hit["n_index"] == 5 and hit["as_of"] == "2026-12-01" and hit["profile"] == "lexical"
    miss = mk.retrieve(index, "quantum chromodynamics on a lattice", "note", "2026-12-01", "lexical")
    assert miss["status"] == "ok" and miss["items"] == [] and miss["scores"] == [] and miss["n_candidates"] == 0 and mk.render(miss) == "" and miss["tokens_est"] == 0
    weak = mk.retrieve(index, "a long question about tide and many other things that share nothing else at all with any note", "note", "2026-12-01", "lexical")
    assert weak["items"] == []                       # one shared common word is below the floor of evidence
    assert mk.retrieve(index, "tide", "note", "2026-12-01", "lexical")["items"] == []                   # fully covered, but the word is in two notes: too little evidence
    assert ids(mk.retrieve(index, "kitchen", "note", "2026-12-01", "lexical")) == ["n1"]                # a word seen once is evidence enough


def test_at_most_k_items_come_back_best_first_and_k_is_a_profile_setting() -> None:
    items = base_items() + [mk.Item("f%02d" % n, "note", "account_history", "2026-08-%02d" % (n + 1), "filler%d unrelated words about subject%d" % (n, n)) for n in range(20)]
    stories = ["ferry company ledgers harbour story winter v0", "ferry company ledgers harbour story v1", "ferry company ledgers harbour v2", "ferry company ledgers v3",
               "ferry company v4"]
    items += [mk.Item("s%d" % n, "note", "account_history", "2026-07-0%d" % (n + 1), text) for n, text in enumerate(stories)]
    index = mk.build_index(items, "2026-12-01")
    query = "ferry company ledgers harbour story winter"
    top = mk.retrieve(index, query, "note", "2026-12-01", "lexical")
    assert ids(top) == ["s0", "s1", "s2"] and top["scores"] == sorted(top["scores"], reverse=True) and top["n_candidates"] >= 4
    wide = mk.retrieve(index, query, "note", "2026-12-01", {"name": "wide", "k": 5, "embed": "off"})
    assert ids(wide)[:3] == ["s0", "s1", "s2"] and 4 <= len(wide["items"]) <= 5 and wide["profile"] == "wide"
    assert ids(mk.retrieve(index, query, "note", "2026-12-01", {"k": 1, "embed": "off"})) == ["s0"]


def test_no_item_dated_at_or_after_the_task_is_shown_and_the_index_refuses_later_items() -> None:
    items = base_items() + [mk.Item("late", "note", "account_history", "2027-01-05", "the ferry company ledgers appear again in the new year"),
                            mk.Item("zone", "note", "account_history", "2026-09-12T08:00:00Z", "the ferry company ledgers were audited on a Saturday morning")]
    index = mk.build_index(items, "2026-12-01")
    assert index.rejected == {"future": 1, "invalid": 0, "duplicate": 0} and "late" not in index.items
    q = "ferry company ledgers"
    assert "late" not in ids(mk.retrieve(index, q, "note", "2099-01-01", "lexical"))
    assert "zone" not in ids(mk.retrieve(index, q, "note", "2026-09-12", "lexical"))                    # that day starts before the item
    assert "zone" in ids(mk.retrieve(index, q, "note", "2026-09-13", "lexical"))
    assert "zone" not in ids(mk.retrieve(index, q, "note", "2026-09-12T08:00:00Z", "lexical")) and "zone" in ids(mk.retrieve(index, q, "note", "2026-09-12T10:00:00+01:00", "lexical"))
    imre = "colleague Imre recovery procedure boring document saved the archive"
    assert ids(mk.retrieve(index, imre, "note", "2026-09-10", "lexical")) == []                    # strictly before: the item of that very day is out
    assert ids(mk.retrieve(index, imre, "note", "2026-09-11", "lexical")) == ["n2"]
    assert all(k < "2026-09-05T00:00:00" for k in mk.retrieve(index, "tide tables ferry ledgers mother kitchen", "note", "2026-09-05", "lexical")["keys"])
    with pytest.raises(ValueError):
        mk.build_index(base_items(), "next week")                                                       # fail closed: the no-future gate needs a date


def test_a_rare_capitalised_name_passes_the_gate_alone_for_personal_tasks_and_comes_first() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    q = "Who is Imre and why does the ferry company keep a tide gauge in the kitchen basement"
    personal = mk.retrieve(index, q, "personal", "2026-12-01", "lexical")
    assert ids(personal)[0] == "n2" and personal["reasons"][0] == ["name"] and {"n1", "w1"} <= set(ids(personal)[1:])
    note = mk.retrieve(index, q, "note", "2026-12-01", "lexical")                                       # the channel exists only for the task types a profile names
    assert "n2" not in ids(note) and {"n1", "w1"} <= set(ids(note))
    alone = mk.retrieve(index, "Imre?", "personal", "2026-12-01", "lexical")                            # a name at the start of the text, never written with a small letter
    assert ids(alone) == ["n2"] and "name" in alone["reasons"][0]
    assert ids(mk.retrieve(index, "Who is Imre?", "personal", "2026-12-01", {"names": False, "embed": "off"})) == ["n2"]     # here the lexical channel finds it as well
    crowded = mk.build_index(base_items() + [mk.Item("n4", "note", "account_history", "2026-09-25", "another ledger entry about the winter")], "2026-12-01")
    plain_noun = mk.retrieve(index, "Who is Kitchen in the old stories", "personal", "2026-12-01", "lexical")
    assert plain_noun["items"] == []                                                                    # the note has the word, but not as a name: nothing passes on a capital letter alone
    common = mk.retrieve(crowded, "Who is Ledger and why does the ferry company keep a tide gauge in the kitchen basement", "personal", "2026-12-01", "lexical")
    assert all("name" not in r for r in common["reasons"])                                              # 'ledger' is in three items: not rare


def test_invented_autobiography_is_considered_only_for_the_task_types_a_profile_allows() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    q = "where were you born, Kellmouth fishing town on a cold estuary"
    own = mk.retrieve(index, q, "personal", "2026-12-01", "lexical")
    assert ids(own) == ["e1"] and own["task_type"] == "personal" and own["items"][0].origin == "fiction_autobio"
    other = mk.retrieve(index, q, "note", "2026-12-01", "lexical")
    assert other["items"] == [] and other["n_considered"] == own["n_considered"] - 1
    custom = mk.retrieve(index, q, "reply", "2026-12-01", {"persona_task_types": ("reply",), "embed": "off"})
    assert ids(custom) == ["e1"]
    world = mk.retrieve(index, "the harbour board keeps minutes of every tide gauge reading", "note", "2026-12-01", "lexical")
    assert ids(world) == ["w1"] and world["items"][0].origin == "world_knowledge"                       # world knowledge is for every task type


def test_a_replacement_counts_from_its_own_date_so_an_earlier_task_still_sees_the_old_item() -> None:
    old = mk.Item("flat", "event", "fiction_autobio", "2014-05-01", "you moved into a flat above a chandlery on Anchor Lane")
    new = mk.Item("cottage", "event", "fiction_autobio", "2020-06-01", "you moved from the flat on Anchor Lane to a cottage by the estuary", meta={"supersedes": "flat"})
    index = mk.build_index(base_items() + [old, new], "2026-12-01")
    q = "the flat on Anchor Lane"
    assert ids(mk.retrieve(index, q, "personal", "2018-01-01", "lexical")) == ["flat"]
    assert ids(mk.retrieve(index, q, "personal", "2026-01-01", "lexical")) == ["cottage"] and "flat" in index.items


def test_a_written_back_detail_is_an_invented_event_with_a_stable_id_that_the_next_index_finds() -> None:
    a, b = mk.write_back_item("her name is Edda", "2026-10-20", about="your sister"), mk.write_back_item("her name is Edda", "2026-10-20", about="your sister")
    assert a == b and a.kind == "event" and a.origin == "fiction_autobio" and a.id.startswith("event-2026-10-20-") and a.text == "your sister her name is Edda"
    index = mk.build_index(base_items() + [a], "2026-11-01")
    assert ids(mk.retrieve(index, "what is the name of your sister Edda", "personal", "2026-11-01", "lexical")) == [a.id]
    assert mk.retrieve(index, "what is the name of your sister Edda", "note", "2026-11-01", "lexical")["items"] == []


def test_the_embedder_adds_what_words_miss_and_the_lexical_profile_never_calls_it() -> None:
    calls: list = []
    index = mk.build_index(base_items(), "2026-12-01", bow_embedder(calls=calls))
    assert calls == [5] and index.dim == 64 and set(index.vectors) == set(index.items)
    q = SYNONYM_QUERY
    hybrid = mk.retrieve(index, q, "note", "2026-12-01", "kernel")
    assert ids(hybrid) == ["n1"] and hybrid["reasons"] == [["embedding"]] and hybrid["status"] == "ok" and hybrid["channel_scores"][0]["embedding"] >= 0.57
    before = len(calls)
    assert mk.retrieve(index, q, "note", "2026-12-01", "lexical")["items"] == [] and len(calls) == before          # not called at all
    assert mk.retrieve(index, q, "note", "2026-12-01", "hybrid")["status"] == "ok" and calls[-1] == 1


def test_ready_vectors_are_used_instead_of_the_embedder_and_a_broken_embedder_degrades_to_lexical() -> None:
    calls: list = []
    fresh = bow_embedder()
    vectors = {i.id: fresh([i.text])[0] for i in base_items()}
    index = mk.build_index(base_items(), "2026-12-01", bow_embedder(calls=calls), vectors=vectors)
    assert calls == [] and index.degraded == "" and index.dim == 64
    assert ids(mk.retrieve(index, SYNONYM_QUERY, "note", "2026-12-01", "kernel")) == ["n1"] and calls == [1]

    def broken(texts):
        raise RuntimeError("model missing")

    down = mk.build_index(base_items(), "2026-12-01", broken)
    assert down.degraded.startswith("embedder failed at build") and down.vectors == {} and len(down.items) == 5
    degraded = mk.retrieve(down, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "kernel")
    assert degraded["status"] == "degraded" and "RuntimeError" in degraded["error"] and ids(degraded) == ["n1"]       # lexical still answers
    assert mk.retrieve(down, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "lexical")["status"] == "ok"

    def flaky(texts):
        if len(texts) == 1:
            raise TimeoutError("slow")
        return bow_embedder()(texts)

    def shrinking(texts):
        return bow_embedder(64 if len(texts) > 1 else 32)(texts)

    other_size = mk.retrieve(mk.build_index(base_items(), "2026-12-01", shrinking), "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "kernel")
    assert other_size["status"] == "degraded" and "ValueError" in other_size["error"] and ids(other_size) == ["n1"]       # no silent dot product of unequal vectors
    late = mk.retrieve(mk.build_index(base_items(), "2026-12-01", flaky), "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "kernel")
    assert late["status"] == "degraded" and "query" in late["error"] and ids(late) == ["n1"]
    assert mk.build_index(base_items(), "2026-12-01", lambda texts: [[1.0]]).degraded.startswith("embedder failed")            # a vector too few
    assert mk.build_index(base_items(), "2026-12-01", lambda texts: [[float("nan")]] * len(texts)).degraded.startswith("embedder failed")
    assert mk.retrieve(mk.build_index(base_items(), "2026-12-01"), "tide tables ferry", "note", "2026-12-01", "hybrid")["status"] == "degraded"
    assert mk.retrieve(mk.build_index(base_items(), "2026-12-01"), "tide tables ferry", "note", "2026-12-01", "kernel")["status"] == "ok"      # auto: no embedder is not a fault


def test_nothing_raises_and_every_failure_is_a_status() -> None:
    junk = [None, mk.Item("a", "tweet", "account_history", "2026-01-01", "bad kind"), mk.Item("b", "note", "robot", "2026-01-01", "bad origin"),
            mk.Item("c", "note", "account_history", "2026-01-01", "   "), mk.Item("d", "note", "account_history", "not a date", "bad date"),
            mk.Item("", "note", "account_history", "2026-01-01", "empty id"), mk.Item("e", "note", "account_history", "2026-01-01", "fine item about harbour winters"),
            mk.Item("e", "note", "account_history", "2026-01-02", "duplicate id about harbour winters"), mk.Item("f", "note", "account_history", "2027-01-01", "from the future")]
    index = mk.build_index(junk, "2026-06-01")
    assert index.rejected == {"future": 1, "invalid": 6, "duplicate": 1} and list(index.items) == ["e"]
    assert mk.retrieve(index, "harbour winters", "note", "2026-06-01", "no-such-profile")["status"] == "error"
    assert "unknown profile" in mk.retrieve(index, "harbour winters", "note", "2026-06-01", "no-such-profile")["error"]
    assert mk.retrieve(index, "harbour winters", "note", "someday", "lexical")["status"] == "error"
    assert mk.retrieve(index, None, "note", "2026-06-01", "lexical")["status"] == "error"          # type: ignore[arg-type]
    assert mk.retrieve(None, "harbour winters", "note", "2026-06-01", "lexical")["status"] == "error"   # type: ignore[arg-type]
    assert mk.retrieve(index, "harbour winters", "note", "2026-06-01", "lexical")["status"] == "ok"
    assert mk.render(None) == "" and mk.log_record(None, hmac_fn)["status"] == "error" and mk.guard(None, "x")["flags"][0].startswith("guard_error")   # type: ignore[arg-type]
    empty = mk.build_index([], "2026-06-01")
    assert mk.retrieve(empty, "anything at all", "note", "2026-06-01", "kernel")["items"] == []


def test_a_deadline_gives_status_timeout_and_no_items() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    out = mk.retrieve(index, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", {"timeout_ms": -1, "embed": "off"})
    assert out["status"] == "timeout" and out["items"] == [] and out["error"] == "deadline exceeded"
    assert mk.guard(out, "As I wrote earlier, tides turn.")["flags"] == ["spurious_reference"]


def test_the_same_inputs_give_the_same_result_whatever_the_order_of_the_items() -> None:
    items = base_items() + [mk.Item("t%d" % n, "note", "account_history", "2026-08-0%d" % (n + 1), "ferry company ledgers harbour story twin") for n in range(5)]
    q = "ferry company ledgers harbour story"
    first = mk.retrieve(mk.build_index(items, "2026-12-01"), q, "note", "2026-12-01", "lexical")
    shuffled = list(items)
    random.Random(5).shuffle(shuffled)
    second = mk.retrieve(mk.build_index(shuffled, "2026-12-01"), q, "note", "2026-12-01", "lexical")
    keep = ("status", "scores", "channel_scores", "reasons", "dates", "keys", "n_candidates", "n_considered", "tokens_est")
    assert ids(first) == ids(second) == ["t0", "t1", "t2"] and all(first[k] == second[k] for k in keep)


def test_render_has_no_label_of_origin_orders_by_date_and_prefers_a_trace_when_asked() -> None:
    trace = {"gist": "A colleague named the recovery procedure.", "angle": "credit goes to the boring document", "open": "who else used it"}
    items = base_items()
    items[1] = mk.Item("n2", "note", "account_history", "2026-09-10", items[1].text, trace=trace)
    index = mk.build_index(items, "2026-12-01")
    out = mk.retrieve(index, "Who is Imre and where were you born in Kellmouth fishing town and tide gauge harbour board minutes", "personal", "2026-12-01", "lexical")
    assert {"n2", "e1", "w1"} <= set(ids(out))
    text = mk.render(out)
    lines = text.splitlines()
    assert [l[:12] for l in lines] == sorted(l[:12] for l in lines) and all(l.startswith("[") and l[11] == "]" for l in lines)
    assert not any(word in text.lower() for word in ("fiction", "autobio", "account_history", "world_knowledge", "origin", "invented"))
    assert "A colleague named the recovery procedure. Angle: credit goes to the boring document Left open: who else used it" in text and "Imre called" not in text
    assert "Imre called" in mk.render(out, mode="raw") and out["tokens_est"] == (len(text) + 3) // 4
    assert mk.render([items[0]], mode="raw") == "[2026-09-01] " + items[0].text


def test_the_log_record_has_keyed_hashes_and_no_text_and_exists_also_when_nothing_was_injected() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    query = "Who is Imre and why does the ferry company keep a tide gauge in the kitchen basement"
    out = mk.retrieve(index, query, "personal", "2026-12-01", "lexical")
    record = mk.log_record(out, hmac_fn)
    assert record["query_hmac"] == hmac_fn(query) and record["item_hmacs"] == [hmac_fn(i) for i in ids(out)] and "ids" not in record
    assert record["origins"] == [i.origin for i in out["items"]] and record["kinds"] == [i.kind for i in out["items"]] and record["dates"] == out["dates"]
    assert record["status"] == "ok" and record["profile"] == "lexical" and record["task_type"] == "personal" and record["kernel_version"] == mk.VERSION and record["reasons"][0] == ["name"]
    blob = json.dumps(record)
    assert not any(word in blob for word in ("Imre", "Kellmouth", "kitchen", "colleague", "ferry", "basement", "archive"))
    assert mk.log_record(out, hmac_fn, key="task-17")["query_hmac"] == hmac_fn("task-17") and mk.log_record(out, hmac_fn, raw_ids=True)["ids"] == ids(out)
    nothing = mk.log_record(mk.retrieve(index, "quantum chromodynamics on a lattice", "note", "2026-12-01", "lexical"), hmac_fn)
    assert nothing["item_hmacs"] == [] and nothing["scores"] == [] and nothing["n_candidates"] == 0 and nothing["status"] == "ok" and nothing["n_index"] == 5
    json.dumps(nothing)


EXPLICIT = ("As I said before, the ferry runs late.", "I wrote about this last week.", "In my previous post I argued otherwise.", "Regular readers will know my view.",
            "You may remember the tide tables.", "Remember when I mentioned the flood?", "I've written about this before.", "When I first wrote about tides, nobody cared.")
PLAIN = ("The ferry runs late again today.", "I wrote this on the train, between two stations.", "She said the archive was saved by a boring document.",
         "Last week the ferry was cancelled twice.", "He said that he wrote it on the train earlier.")


def test_the_guard_flags_references_nothing_supports_and_lets_plain_text_and_supported_references_pass() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    none = mk.retrieve(index, "quantum chromodynamics on a lattice", "note", "2026-12-01", "lexical")
    for sentence in EXPLICIT:
        verdict = mk.guard(none, "Start of the note. " + sentence + " End of the note.")
        assert verdict == {"ok": False, "flags": ["spurious_reference"], "callbacks": 1}, sentence
    for sentence in PLAIN:
        assert mk.guard(none, "Start of the note. " + sentence + " End of the note.") == {"ok": True, "flags": [], "callbacks": 0}, sentence
    assert mk.guard(none, "")["ok"] is True and mk.guard(none, None)["ok"] is True                      # type: ignore[arg-type]
    some = mk.retrieve(index, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "lexical")
    assert mk.guard(some, "As I wrote earlier about the ferry company ledgers, the point stands.") == {"ok": True, "flags": [], "callbacks": 1}
    assert mk.guard(some, "As I wrote last week about quantum lattices, the point stands.")["flags"] == ["unsupported_reference"]
    assert mk.guard(some, "The ferry company ledgers are back in the news.")["ok"] is True


def test_the_guard_notices_an_altered_result_a_future_item_or_invented_autobiography_in_the_wrong_task() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    some = mk.retrieve(index, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "lexical")
    assert mk.guard(dict(some, now_key="2026-01-01T00:00:00"), "Tides turn.")["flags"] == ["future_item"]
    own = mk.retrieve(index, "where were you born, Kellmouth fishing town on a cold estuary", "personal", "2026-12-01", "lexical")
    assert mk.guard(own, "Born by the estuary.")["ok"] is True
    assert mk.guard(dict(own, task_type="note"), "Born by the estuary.")["flags"] == ["fiction_out_of_scope"]


def test_calibration_puts_about_a_fifth_of_the_queries_above_the_threshold_on_either_channel() -> None:
    items = [mk.Item("c%d" % k, "note", "account_history", "2026-09-%02d" % (k + 1), "topic%d alpha%d beta%d gamma%d words about subject%d" % (k, k, k, k, k)) for k in range(10)]
    index = mk.build_index(items, "2026-12-01", bow_embedder())
    queries = [("topic%d alpha%d beta%d gamma%d" % (k, k, k, k), "2026-10-01") for k in range(2)] + [("zzz%d yyy%d xxx%d" % (k, k, k), "2026-10-01") for k in range(8)]
    off = {"names": False, "min_evidence": 0.0, "lex_tau": 9.0, "tau": 9.0}
    for channel, gate in (("lexical", {"lex_tau": None, "embed": "off"}), ("embedding", {"tau": None, "embed": "auto"})):
        threshold = mk.calibrate(index, queries, share=0.2, channel=channel)
        profile = dict(off, **{key: (threshold if value is None else value) for key, value in gate.items()})
        fired = sum(1 for query, day in queries if mk.retrieve(index, query, "note", day, profile)["items"])
        assert 0.1 <= fired / len(queries) <= 0.3, (channel, threshold, fired)
    assert mk.calibrate(index, [], 0.2) is None
    assert mk.calibrate(index, [("topic1 alpha1 beta1", "2026-09-01")], 0.2) == 0.0                     # nothing is dated before the first of September


def synthetic_corpus(n_items: int, seed: int = 11):
    rng = random.Random(seed)
    vocab = ["wd%04d" % n for n in range(4000)]
    weights = [1.0 / (rank + 1) ** 0.9 for rank in range(len(vocab))]
    texts = [" ".join(rng.choices(vocab, weights, k=rng.randint(40, 120))) for _ in range(n_items)]
    items = [mk.Item("i%04d" % n, "note", "account_history", "2025-%02d-%02d" % (1 + n % 12, 1 + n % 28), text) for n, text in enumerate(texts)]
    queries = [" ".join(rng.choices(texts[rng.randrange(n_items)].split(), k=25) + rng.choices(vocab, weights, k=25)) if n % 2 else " ".join(rng.choices(vocab, weights, k=50))
               for n in range(200)]
    return items, queries


def test_two_thousand_items_build_in_two_seconds_and_answer_within_three_hundred_milliseconds() -> None:
    items, queries = synthetic_corpus(2000)
    index = mk.build_index(items, "2026-12-31")
    assert index.built_ms < 2000 and len(index.items) == 2000
    latencies = sorted(mk.retrieve(index, q, "note", "2026-12-31", "lexical")["latency_ms"] for q in queries)
    assert latencies[int(0.95 * len(latencies))] < 300, latencies[-5:]
    hybrid = mk.build_index(items, "2026-12-31", bow_embedder(384))
    slow = sorted(mk.retrieve(hybrid, q, "note", "2026-12-31", "kernel")["latency_ms"] for q in queries[:60])
    assert slow[int(0.95 * len(slow))] < 300, slow[-5:]


def test_two_thousand_items_with_vectors_fit_in_two_hundred_megabytes() -> None:
    items, queries = synthetic_corpus(2000, seed=3)
    tracemalloc.start()
    try:
        index = mk.build_index(items, "2026-12-31", bow_embedder(384))
        for q in queries[:10]:
            mk.retrieve(index, q, "note", "2026-12-31", "kernel")
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert peak < 200 * 1024 * 1024, peak / 1e6


def test_words_are_letters_of_any_script_split_at_hyphens_with_plurals_and_possessives_folded() -> None:
    assert mk.tokens("Żółć gęślą jaźń, l'été") == ["żółć", "gęślą", "jaźń", "l'été"]
    assert mk.tokens("Imre's well-known list of the ferries and the stories") == ["imre", "well", "known", "list", "ferry", "story"]
