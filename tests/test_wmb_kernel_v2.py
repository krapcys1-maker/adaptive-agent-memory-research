# SPDX-License-Identifier: Apache-2.0
"""wmb kernel 0.2.0 (scripts/wmb/kernel/memory_kernel.py): the live line of the shared memory module, on synthetic data only.

The frozen 0.1.0 (scripts/wmb/memory_kernel.py, tests/test_wmb_memory_kernel.py) is the instrument of the preregistered study WMB-R1 and is never edited. This file ports what the
0.1.0 tests covered and adds the 0.2.0 behaviour: a BM25 gate whose score does not decay with the length of the query, hardened inputs and logs, a stemmer that folds plurals,
a name channel that ignores sentence-initial words, and a reference guard measured on a bank of natural sentences that was written before the patterns were tuned.

The module under test is loaded from its file under a private name (the 0.1.0 tests import a module with the same file name). To run this suite against a copy that the
integrating project vendored, set WMB_KERNEL_V2_FILE to the path of that copy.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import importlib.util
import inspect
import json
import math
import os
import random
import re
import subprocess
import sys
import textwrap
import time
import tracemalloc
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "scripts" / "wmb" / "memory_kernel.py"
SOURCE = Path(os.environ.get("WMB_KERNEL_V2_FILE") or ROOT / "scripts" / "wmb" / "kernel" / "memory_kernel.py")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module                       # dataclasses look their module up by name
    spec.loader.exec_module(module)
    return module


mk = load_module(SOURCE, "wmb_kernel_v2_under_test")

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# The guard bank. Written before the patterns of 0.2.0 were designed or tuned, and not taken from the pattern list: natural sentences of the kind a writing agent produces
# about AI (news prose, first-person notes, references to the text being written). A POSITIVE is a sentence that explicitly refers back to something the author itself
# said, wrote, posted or covered earlier, outside the text being written. A NEGATIVE is anything else: news prose, third-person reports of what others wrote, narration of
# the author's own work, references to the current text (above, earlier in this note), and ordinary AI vocabulary that contains words such as post, last, previous, earlier.
# Every third sentence of each list (position 2, 5, 8, ...) is HELD OUT: it was not looked at while the patterns were tuned, and the report gives the figures for it apart.
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
BANK_POSITIVE = (
    "Last week I wrote about how open-weight models keep closing the gap with proprietary ones.",
    "As I argued in my post on agent benchmarks, the leaderboard tells you little about real work.",
    "Regular readers will remember my doubts about fully autonomous coding agents.",
    "I've written about this tension before, and the new release does not change my view.",
    "A few weeks back I wrote that context windows would stop being the headline number.",
    "Like I said last month, the expensive part is evaluation, not training.",
    "I keep saying that small models are underrated.",
    "In last week's issue I explained why retrieval quality matters more than model size.",
    "My earlier post on tokenizer quirks got more replies than I expected.",
    "We covered this in an earlier issue, so I will keep it short.",
    "As mentioned previously, the benchmark has known contamination problems.",
    "Back in March I predicted that agent frameworks would consolidate.",
    "I raised the same question in a thread two weeks ago and nobody had an answer.",
    "You may remember that I was sceptical of the first demo.",
    "I made this point in an earlier note about evals: scores without error bars mean little.",
    "Yesterday I posted a thread about the new pricing.",
    "Earlier this month I wrote that the labs were running out of easy wins.",
    "I flagged this problem in my last newsletter.",
    "As we discussed in the previous issue, the chip shortage is easing.",
    "I covered the same paper last month, and my reading has not changed.",
    "Some of you will recall the piece I did on synthetic data.",
    "I said it before and I will say it again: do not trust a single benchmark number.",
    "When I wrote about long-context models in the spring, I underestimated the cost.",
    "As I noted a while ago, open models trail by roughly a year.",
    "I touched on this in a post last autumn.",
    "This is the same argument I made two months ago about inference prices.",
    "Longtime readers know I have been arguing for smaller models for a long time.",
    "I wrote a piece on exactly this a few months ago.",
    "As I pointed out in an earlier column, the savings never reach the customer.",
    "I already covered the licence change, so I will skip the details here.",
    "Last time I mentioned the budget cap; here is how it played out.",
    "In a previous post I described the harness in detail.",
    "My last note on this was too optimistic.",
    "I owe you a follow-up to my post about scaling laws.",
    "Following up on my thread from last Tuesday, the vendor has now responded.",
    "As promised in my previous newsletter, here are the numbers.",
    "I argued in my first piece on agents that tool use would be the bottleneck.",
    "We reported on this outage last month.",
    "Last year I predicted that open weights would win the long tail, and I still think so.",
    "I've been saying for months that evaluation is the real moat.",
    "I told you last week that the rumor was shaky.",
    "I did a deep dive on this earlier in the year.",
    "Two weeks ago I shared a chart of inference costs; here is the update.",
    "I brought this up in my post about alignment budgets.",
    "Remember when I said the demo looked staged? It turned out I was right.",
    "I have said many times that data quality beats data volume.",
    "My notes from last month already flagged the licensing risk.",
    "A while ago I argued that routers would matter more than single models.",
    "I wrote about this when the first version came out.",
    "As I wrote in my earlier note, the gains come from the data mix.",
    "I talked about this on the account last week.",
    "The thread I posted on Monday covered the same ground.",
    "In my newsletter two issues ago I made the opposite prediction.",
    "I said as much in my post about open weights.",
    "I covered the earlier version of this story in an older issue.",
    "I raised a similar worry in a post earlier this year.",
    "Like I mentioned before, latency matters more than raw throughput for chat.",
    "As I've argued before, benchmark scores should come with confidence intervals.",
    "I explained last time why the cheaper model wins on batch jobs.",
    "I've said before that I distrust leaderboards.",
    "You'll remember my take on the last funding round.",
    "Readers of this account will know that I have covered the safety framework before.",
    "I've covered similar ground in earlier posts.",
    "Previously, I argued that the scaling story was incomplete.",
    "I made a similar point in a note back in June.",
    "I already wrote about the pricing change in my last post, so I'll link to it rather than repeat.",
)
BANK_NEGATIVE = (
    "Post-training has become the main source of capability gains this year.",
    "Earlier post-training recipes relied on supervised data alone.",
    "The previous generation of models struggled with long documents.",
    "Earlier versions of the API did not support streaming.",
    "The last column of the table lists the cost per million tokens.",
    "A previous entry in the leaderboard was removed after the lab withdrew its score.",
    "Our first post-mortem of the outage blamed the wrong service.",
    "My first impression of the new model was lukewarm.",
    "Last week the company announced a new inference chip.",
    "The team said last month that the model would ship in the spring.",
    "In a recent paper, the authors argue that data quality beats quantity.",
    "The earlier checkpoint performs better on long contexts.",
    "The last layer of the network is fine-tuned separately.",
    "Previously, the system used a fixed threshold for all queries.",
    "Earlier today the model failed three of the ten tests.",
    "OpenAI wrote in its release notes that the model is cheaper to run.",
    "She mentioned that the dataset was scraped without permission.",
    "Regulators noted that the system had not been audited.",
    "The authors previously reported a lower score on the same test.",
    "The paper I read on the train last night was surprisingly clear.",
    "I wrote a short script to compare the two tokenizers.",
    "I noted the price before and after the update, and it doubled.",
    "I posted the question to a forum and got three answers within the hour.",
    "I wrote the prompt, ran the benchmark, and compared the outputs.",
    "I tested the model yesterday and the latency was fine.",
    "We shipped the fix two days ago and the error rate dropped.",
    "I recall how nervous I felt when the demo failed on stage.",
    "I said no to the demo because the setup looked fragile.",
    "I mentioned the bug to the maintainers and they fixed it within an hour.",
    "I covered the cable with tape before moving the rack.",
    "I have written the evaluation harness in Python and it runs in under a minute.",
    "We argued about the name for an hour before settling on something dull.",
    "As I explained earlier in this article, the cost curve is flat.",
    "As noted above, the evaluation set is small.",
    "In the previous paragraph I argued that scaling is slowing.",
    "Earlier in this note I said that the benchmark is saturated.",
    "As the table above shows, inference costs fell sharply.",
    "I will come back to this point later in the post.",
    "As I said at the start, this is only a first look.",
    "The previous section covered training; this one covers inference.",
    "I covered the training setup in the first half of this piece.",
    "As discussed in the introduction, the data is synthetic.",
    "To recap what I wrote above: three labs lead and the rest trail.",
    "As mentioned earlier in this thread, the cache is the bottleneck.",
    "The next section describes the failure cases.",
    "I noted in the last paragraph that the sample is small.",
    "Anthropic released a smaller model this week that costs a fraction of its flagship.",
    "The benchmark has been criticised for leaking test questions into training data.",
    "Researchers found that models often ignore information in the middle of long prompts.",
    "Chip makers have promised new accelerators for the second half of the year.",
    "The company argued that the regulation would slow open research.",
    "Open-weight models now match last year's proprietary systems on most tasks.",
    "A group of academics published a critique of the leaderboard last month.",
    "Investors have poured money into agent start-ups over the past year.",
    "Regular updates to the model have improved its reliability.",
    "The lab promised to publish the evaluation code, but has not yet done so.",
    "I tried the new agent framework on a small project and it broke twice.",
    "I think the next big gain will come from better data, not bigger models.",
    "In my experience, small models are underrated for classification work.",
    "I am not convinced that longer context windows solve the memory problem.",
    "Honestly, I did not expect the demo to work at all.",
    "I spent the weekend reading the technical report, and it is dense.",
    "My guess is that prices will keep falling for at least another year.",
    "I would like to see error bars on every chart in this space.",
    "I keep a list of failed demos on my desk, and the list keeps growing.",
    "Remember to check the licence before you fine-tune anything.",
)
HELD_OUT = lambda position: position % 3 == 2                    # noqa: E731


def split_bank(sentences):
    """(development part, held-out part)."""
    return ([s for n, s in enumerate(sentences) if not HELD_OUT(n)], [s for n, s in enumerate(sentences) if HELD_OUT(n)])


def precision_recall(flagged_positive, flagged_negative, n_positive, n_negative):
    """Precision and recall of 'the guard sees a reference' on the bank; flagged_* are the numbers of sentences of each list that the guard flagged."""
    tp, fp = flagged_positive, flagged_negative
    return (tp / (tp + fp) if tp + fp else 1.0), (tp / n_positive if n_positive else 1.0)


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
SYNONYMS = {"boat": "ferry", "mum": "mother", "records": "ledgers", "charts": "tables", "firm": "company", "stored": "kept"}
SYNONYM_QUERY = "charts boat firm records stored mum"        # the words of n1 said in other words: no shared stem, a high cosine
LEXICAL_ONLY = {"name": "lexical-only", "embed": "off"}
NAMES_ONLY = {"name": "names-only", "embed": "off", "lex_tau": 1e6}        # the lexical channel is shut: only the channel for names can pass
EVERYTHING = {"name": "everything", "embed": "off", "names": False, "lex_tau": 1e-6, "min_evidence": 0.0, "k": 10 ** 6}      # every item that shares a stem, best first
ONE_WORD = {"name": "one-word", "embed": "off", "min_evidence": 0.8}      # the floor of evidence of the first 0.2.0: ONE shared rare word is enough (the default 1.4 asks for two)


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


def fillers(n: int, first: int = 0):
    """Items of words that nothing else uses, dated across January 2026."""
    return [mk.Item("f%03d" % k, "note", "account_history", "2026-01-%02d" % (1 + k % 28), "filler%d unrelated words about subject%d" % (k, k)) for k in range(first, first + n)]


def ids(result) -> list:
    return [i.id for i in result["items"]]


def hmac_fn(text: str) -> str:
    return "h" + hashlib.sha256(("key:" + text).encode("utf-8")).hexdigest()[:12]


def no_memory(task_type: str = "note"):
    """What the guard receives when nothing was injected."""
    return mk.retrieve(mk.build_index([], "2026-06-01"), "anything", task_type, "2026-06-01", "lexical")


def bank_flags(sentences, module=None) -> int:
    module = module or mk
    empty = {"items": [], "status": "ok"}
    return sum(1 for s in sentences if module.guard(empty, s)["callbacks"] > 0)


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# The contract: files, imports, effects, versions, and the interface of 0.1.0
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_file_is_standard_library_only_licensed_and_has_no_effects_on_import(tmp_path: Path) -> None:
    text = SOURCE.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "# SPDX-License-Identifier: Apache-2.0"
    imported = set()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported and imported <= set(sys.stdlib_module_names) and not imported & {"socket", "urllib", "http", "ssl", "subprocess", "os", "pathlib", "requests", "numpy", "random"}
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    attributes = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not calls & {"open", "print", "exec", "eval", "compile", "__import__", "hash", "input", "id"}            # no files, no output, no hash(): the same result in every process
    assert {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "time"} == {"perf_counter"}      # time is a stopwatch only
    assert not attributes & {"now", "utcnow", "today", "sleep", "environ", "getenv", "urlopen", "random"}
    code = ("import os, sys; sys.path.insert(0, %r); files, loaded = set(os.listdir('.')), set(sys.modules); import %s; "
            "assert set(os.listdir('.')) == files; "
            "assert not {'socket', 'urllib', 'http', 'ssl', 'subprocess', 'requests', 'numpy'} & (set(sys.modules) - loaded); print('ok')") % (str(SOURCE.parent), SOURCE.stem)
    run = subprocess.run([sys.executable, "-I", "-c", code], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and run.stdout.strip() == "ok" and run.stderr == ""


def test_the_version_is_one_constant_and_the_docstring_carries_the_design_and_the_changelog() -> None:
    assert mk.VERSION == mk.__version__ == "0.2.0"
    doc = mk.__doc__
    assert "CHANGELOG" in doc and "0.2.0" in doc and "0.1.0" in doc and "BM25" in doc and "FLOOR" in doc and "reference" in doc
    assert "floor" in mk.guard.__doc__.lower() and "do not reject" in mk.guard.__doc__.lower()


def test_the_interface_of_version_0_1_0_is_kept_names_signatures_fields_and_result_keys() -> None:
    old = load_module(FROZEN, "wmb_kernel_frozen_0_1_0")
    public = lambda module: {name for name in vars(module) if not name.startswith("_")}      # noqa: E731
    assert public(old) - {"__version__"} <= public(mk)
    for name in ("build_index", "retrieve", "render", "log_record", "guard", "calibrate", "write_back_item", "when", "stem", "analyse", "tokens", "item_id"):
        before, after = list(inspect.signature(getattr(old, name)).parameters.values()), list(inspect.signature(getattr(mk, name)).parameters.values())
        assert [(p.name, p.kind, p.default) for p in before] == [(p.name, p.kind, p.default) for p in after[: len(before)]], name
        assert all(p.default is not inspect.Parameter.empty for p in after[len(before):]), name              # a new parameter is optional
    assert [f.name for f in dataclasses.fields(old.Item)] == [f.name for f in dataclasses.fields(mk.Item)]
    assert [f.name for f in dataclasses.fields(old.Index)] == [f.name for f in dataclasses.fields(mk.Index)][: len(dataclasses.fields(old.Index))]
    assert old.KINDS == mk.KINDS and old.ORIGINS == mk.ORIGINS and set(old.PROFILES) == set(mk.PROFILES) and set(old.PROFILES["kernel"]) <= set(mk.PROFILES["kernel"])
    asked = ("who is Imre and the kitchen of the ferry company", "personal")
    before = old.retrieve(old.build_index([old.Item(**vars(i)) for i in base_items()], "2026-12-01"), asked[0], asked[1], "2026-12-01", "lexical")
    after = mk.retrieve(mk.build_index(base_items(), "2026-12-01"), asked[0], asked[1], "2026-12-01", "lexical")
    assert set(before) <= set(after) and set(after) - set(before) == {"_df", "rejected"}                  # the private document frequencies for the guard, the counters of the index
    record_before = old.log_record(before, hmac_fn)
    record_after = mk.log_record(after, hmac_fn)
    assert set(record_before) <= set(record_after) and set(record_after) - set(record_before) == {"now_key", "rejected", "unicode"}
    assert old.build_index([], "2026-01-01").rejected.keys() == mk.build_index([], "2026-01-01").rejected.keys()          # the three counters of 0.1.0, no more
    assert set(old.guard(before, "x")) == set(mk.guard(after, "x")) == {"ok", "flags", "callbacks"}


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_dates_of_any_precision_compare_in_utc_and_invalid_ones_are_refused() -> None:
    assert mk.when("2026-09-10") == "2026-09-10T00:00:00" and mk.when("2026-09") == "2026-09-01T00:00:00" and mk.when("1989") == "1989-01-01T00:00:00"
    assert mk.when("2026-09-10T08:00:00+02:00") == "2026-09-10T06:00:00" == mk.when("2026-09-10T08:00:00+0200") == mk.when("2026-09-10 06:00:00Z")
    assert mk.when("2026-09-10T23:30:00-01:30") == "2026-09-11T01:00:00" and mk.when(date(2026, 9, 10)) == "2026-09-10T00:00:00"
    assert mk.when("2026-09-10T08:00:00.123Z") == "2026-09-10T08:00:00" == mk.when("2026-09-10T08:00:00,9Z") == mk.when("2026-09-10T08:00Z") == mk.when(" 2026-09-10T08:00  ")
    for bad in ("10.09.2026", "2026-13-01", "2026-02-30", "2026-09-10T25:00:00", "yesterday", "", "2026-09-10T08", "2026-09-10Z", "2026-09-10T24:00:00", "2026-09-10T08:00:60"):
        with pytest.raises(ValueError):
            mk.when(bad)


def test_zone_offsets_are_validated_and_no_date_can_overflow() -> None:
    assert mk.when("2026-09-10T00:00:00+14:00") == "2026-09-09T10:00:00" and mk.when("2026-09-10T00:00:00-12:00") == "2026-09-10T12:00:00"
    assert mk.when("2026-09-10T12:00:00+23:59") == "2026-09-09T12:01:00" and mk.when("2026-09-10T12:00:00-23:59") == "2026-09-11T11:59:00"
    for bad in ("2026-09-10T00:00:00+99:00", "2026-09-10T00:00:00+24:00", "2026-09-10T00:00:00+05:60", "2026-09-10T00:00:00-24:00", "2026-09-10T00:00:00+2400"):
        with pytest.raises(ValueError):
            mk.when(bad)
    for edge in ("9999-12-31T23:59:59-23:59", "0001-01-01T00:00:00+01:00", "0001-01-01T00:00:00+23:59", "0000-01-01", "9999-12-31T23:59:59-00:01"):
        with pytest.raises(ValueError):                                  # ValueError, never OverflowError
            mk.when(edge)
    assert mk.when("9999-12-31") == "9999-12-31T00:00:00" and mk.when("0001-01-01") == "0001-01-01T00:00:00"
    index = mk.build_index([mk.Item("edge", "note", "account_history", "9999-12-31T23:59:59-23:59", "x1 text")] + base_items(), "2026-12-01")
    assert index.rejected["invalid"] == 1 and "edge" not in index.items                    # an item with an impossible date is invalid, it does not stop the build
    assert mk.retrieve(index, "tide tables", "note", "9999-12-31T23:59:59-23:59", "lexical")["status"] == "error"


def test_a_naive_time_is_utc_an_aware_one_is_converted_and_only_text_and_dates_are_accepted() -> None:
    assert mk.when(datetime(2026, 9, 10, 8, 0)) == "2026-09-10T08:00:00" == mk.when("2026-09-10T08:00:00") == mk.when(datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc))
    assert mk.when(datetime(2026, 9, 10, 8, 0, tzinfo=timezone(timedelta(hours=2)))) == "2026-09-10T06:00:00"
    assert mk.when(datetime(2026, 9, 10, 8, 0, 0, 999999)) == "2026-09-10T08:00:00"                      # microseconds are dropped
    indic = lambda text: "".join(chr(0x660 + int(c)) if c.isdigit() else c for c in text)                          # noqa: E731  the same date in Arabic-Indic digits
    for bad in (2026, 20260910, 2026.5, None, b"2026-09-10", ["2026-09-10"], True, indic("2026-09-10"), indic("2026"), indic("2026-09"), "2026-" + indic("09")):
        with pytest.raises(ValueError):
            mk.when(bad)
    assert mk.when("2026-09-10t08:00z") == "2026-09-10T08:00:00"
    # a naive item time and an aware task time meet in UTC: 09:30 naive is 09:30Z, later than 08:00Z although a clock on UTC+3 could say otherwise
    items = [mk.Item("late", "note", "account_history", datetime(2026, 9, 10, 9, 30, tzinfo=timezone.utc), "ferry company ledgers were audited")]
    index = mk.build_index(items, "2026-12-01")
    assert ids(mk.retrieve(index, "ferry company ledgers", "note", datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc), LEXICAL_ONLY)) == []
    assert ids(mk.retrieve(index, "ferry company ledgers", "note", datetime(2026, 9, 10, 11, 0), LEXICAL_ONLY)) == ["late"]            # naive 11:00 is read as 11:00Z
    assert ids(mk.retrieve(index, "ferry company ledgers", "note", datetime(2026, 9, 10, 11, 0, tzinfo=timezone(timedelta(hours=3))), LEXICAL_ONLY)) == []      # aware: 08:00Z


def test_date_boundaries_are_strict_and_a_date_without_a_time_is_the_start_of_its_day() -> None:
    items = [mk.Item("day", "note", "account_history", "2026-09-10", "ferry company ledgers of the harbour"), mk.Item("noon", "note", "account_history", "2026-09-10T12:00:00",
                                                                                                                   "ferry company ledgers of the harbour again")] + fillers(20)
    index = mk.build_index(items, "2026-09-10")                       # as_of is the start of that day
    assert [i for i in index.items if i in ("day", "noon")] == ["day"] and index.rejected["future"] == 1                # the noon item is later than as_of
    q = "ferry company ledgers harbour"
    assert ids(mk.retrieve(index, q, "note", None, LEXICAL_ONLY)) == []                  # no `now`: it is as_of, and the item of that very instant is not before it
    assert ids(mk.retrieve(index, q, "note", "2026-09-10", LEXICAL_ONLY)) == []
    assert ids(mk.retrieve(index, q, "note", "2026-09-10T00:00:01", LEXICAL_ONLY)) == ["day"] and ids(mk.retrieve(index, q, "note", "2026-09-11", LEXICAL_ONLY)) == ["day"]
    both = mk.build_index(items, "2026-09-11")
    assert ids(mk.retrieve(both, q, "note", "2026-09-10T12:00:00", LEXICAL_ONLY)) == ["day"]
    assert set(ids(mk.retrieve(both, q, "note", "2026-09-10T12:00:01", LEXICAL_ONLY))) == {"day", "noon"}
    assert mk.retrieve(both, q, "note", "2026-09-10T08:00", LEXICAL_ONLY)["n_considered"] == 21                     # a precision mix: the day item is before 08:00, the noon item is not (and the 20 fillers)
    with pytest.raises(ValueError):
        mk.build_index(items, "next week")
    for bad in (None, "", 20260910, "2026-09-31"):
        with pytest.raises(ValueError):
            mk.build_index(items, bad)                                                 # fail closed: the no-future gate needs a date


def test_the_default_task_time_is_the_index_date() -> None:
    index = mk.build_index(base_items(), "2026-09-15")
    out = mk.retrieve(index, "colleague Imre recovery procedure boring document archive", "note", None, LEXICAL_ONLY)
    assert out["now"] == "2026-09-15" and out["now_key"] == "2026-09-15T00:00:00" and ids(out) == ["n2"]


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# The lexical gate: BM25 normalised by the reference of the query's most informative terms
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_query_with_enough_shared_evidence_returns_the_item_and_an_unrelated_one_returns_nothing() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    hit = mk.retrieve(index, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "lexical")
    assert hit["status"] == "ok" and ids(hit) == ["n1"] and hit["reasons"] == [["lexical"]] and hit["scores"][0] >= 1.0 and 0.2 <= hit["channel_scores"][0]["lexical"] <= 0.5
    assert hit["n_candidates"] == 1 and hit["n_considered"] == 4 and hit["n_index"] == 5 and hit["as_of"] == "2026-12-01" and hit["profile"] == "lexical"
    miss = mk.retrieve(index, "quantum chromodynamics on a lattice", "note", "2026-12-01", "lexical")
    assert miss["status"] == "ok" and miss["items"] == [] and miss["scores"] == [] and miss["n_candidates"] == 0 and mk.render(miss) == "" and miss["tokens_est"] == 0
    weak = mk.retrieve(index, "a long question about tide and many other things that share nothing else at all with any note", "note", "2026-12-01", "lexical")
    assert weak["items"] == []                       # one shared common word is below the floor of evidence
    assert mk.retrieve(index, "tide", "note", "2026-12-01", "lexical")["items"] == []                   # fully matched, but the word is in two notes: too little evidence
    assert mk.retrieve(index, "kitchen", "note", "2026-12-01", "lexical")["items"] == []                # one word seen once is not enough evidence by default (min_evidence 1.4) ...
    assert ids(mk.retrieve(index, "kitchen", "note", "2026-12-01", ONE_WORD)) == ["n1"]                 # ... and is when the profile asks for one word (min_evidence 0.8)
    assert ids(mk.retrieve(index, "ferry kitchen", "note", "2026-12-01", "lexical")) == ["n1"]          # two words seen once are


def test_bm25_scores_are_the_formula_with_k1_1_2_and_b_0_75_normalised_by_the_reference_of_the_query() -> None:
    # Three items of 4, 2 and 6 stems (average 4); the query has two known stems: alpha (in 2 items) and beta (in 1).
    #   idf(alpha) = ln(1 + (3 - 2 + 0.5) / (2 + 0.5)) = ln 1.6 = 0.4700;   idf(beta) = ln(1 + (3 - 1 + 0.5) / (1 + 0.5)) = ln(8/3) = 0.9808
    #   d1 "alpha beta beta gamma", length 4 = average, norm = 1.2 * (0.25 + 0.75 * 1) = 1.2:
    #       alpha  0.4700 * 1 * 2.2 / (1 + 1.2) = 0.4700;   beta  0.9808 * 2 * 2.2 / (2 + 1.2) = 1.3486 (two occurrences earn 1.375 times one, not 2 times);   sum 1.8186
    #   d2 "alpha delta", length 2, norm = 1.2 * (0.25 + 0.75 * 0.5) = 0.75:   alpha  0.4700 * 2.2 / (1 + 0.75) = 0.5909
    #   reference = 2.2 * (0.4700 + 0.9808) = 3.1918;   s(d1) = 1.8186 / 3.1918 = 0.5698;   s(d2) = 0.5909 / 3.1918 = 0.1851;   d3 shares nothing
    items = [mk.Item("d1", "note", "account_history", "2026-01-01", "alpha beta beta gamma"), mk.Item("d2", "note", "account_history", "2026-01-02", "alpha delta"),
             mk.Item("d3", "note", "account_history", "2026-01-03", "epsilon zeta eta theta iota kappa")]
    index = mk.build_index(items, "2026-02-01")
    assert index.avgdl == 4.0 and index.dl == {"d1": 4, "d2": 2, "d3": 6} and index.tf["d1"] == {"alpha": 1, "beta": 2, "gamma": 1}
    out = mk.retrieve(index, "alpha beta", "note", "2026-02-01", {"name": "t", "embed": "off", "names": False, "lex_tau": 0.1, "min_evidence": 0.0})
    assert ids(out) == ["d1", "d2"]
    assert [c["lexical"] for c in out["channel_scores"]] == [0.5698, 0.1851]
    assert out["scores"] == pytest.approx([5.698, 1.851], abs=2e-3)                                        # in units of the gate: s / lex_tau
    ia, ib = math.log(1.6), math.log(1 + 2.5 / 1.5)
    assert out["channel_scores"][0]["lexical"] == round((ia * 2.2 / 2.2 + ib * 2 * 2.2 / 3.2) / (2.2 * (ia + ib)), 4)
    # the reference follows top_terms: with one reference term (beta, the rarest) it is 2.2 * ib, and the score counts every known term up to max_terms
    one = mk.retrieve(index, "alpha beta", "note", "2026-02-01", {"name": "t", "embed": "off", "names": False, "lex_tau": 0.1, "min_evidence": 0.0, "top_terms": 1})
    assert [c["lexical"] for c in one["channel_scores"]] == [round((ia + ib * 1.375) / (2.2 * ib), 4), round(ia * 2.2 / 1.75 / (2.2 * ib), 4)]
    only_beta = mk.retrieve(index, "alpha beta", "note", "2026-02-01", {"name": "t", "embed": "off", "names": False, "lex_tau": 0.1, "min_evidence": 0.0, "top_terms": 1, "max_terms": 1})
    assert ids(only_beta) == ["d1"] and only_beta["channel_scores"][0]["lexical"] == round(ib * 1.375 / (2.2 * ib), 4) == 0.625
    plain = mk.retrieve(index, "alpha beta", "note", "2026-02-01", {"name": "t", "embed": "off", "names": False, "lex_tau": 0.1, "min_evidence": 0.0, "top_terms": 0, "max_terms": 0})
    assert [c["lexical"] for c in plain["channel_scores"]] == [0.5698, 0.1851]
    flat = mk.retrieve(index, "alpha beta", "note", "2026-02-01", {"name": "t", "embed": "off", "names": False, "lex_tau": 0.1, "min_evidence": 0.0, "b": 0.0, "k1": 2.0})
    nb = lambda f: (2.0 + 1.0) * f / (f + 2.0)                                                           # noqa: E731  b = 0: no length normalisation
    assert flat["channel_scores"][0]["lexical"] == round((ia * nb(1) + ib * nb(2)) / (3.0 * (ia + ib)), 4)


def test_the_gate_is_a_share_of_the_reference_and_the_floor_of_evidence_is_absolute() -> None:
    items = [mk.Item("d1", "note", "account_history", "2026-01-01", "alpha beta beta gamma"), mk.Item("d2", "note", "account_history", "2026-01-02", "alpha delta"),
             mk.Item("d3", "note", "account_history", "2026-01-03", "epsilon zeta eta theta iota kappa")]
    index = mk.build_index(items, "2026-02-01")
    gate = lambda **kw: ids(mk.retrieve(index, "alpha beta", "note", "2026-02-01", dict({"name": "t", "embed": "off", "names": False, "min_evidence": 0.0}, **kw)))      # noqa: E731
    assert gate(lex_tau=0.18) == ["d1", "d2"] and gate(lex_tau=0.19) == ["d1"] and gate(lex_tau=0.56) == ["d1"] and gate(lex_tau=0.57) == []                  # 0.1851 and 0.5698
    # evidence: alpha alone has idf 0.4700, a word seen once has ln(8/3)... for N = 3 the floor is min_evidence * ln(1 + 2.5 / 1.5) = min_evidence * 0.9808
    ev = lambda me: ids(mk.retrieve(index, "alpha", "note", "2026-02-01", {"name": "t", "embed": "off", "names": False, "lex_tau": 1e-6, "min_evidence": me}))             # noqa: E731
    assert ev(0.47) == ["d2", "d1"] and ev(0.48) == [] and ev(0.0) == ["d2", "d1"]            # the shorter item first


def test_the_score_does_not_decay_with_the_length_of_the_query() -> None:
    generic = ["gen%02d" % n for n in range(80)]                                              # words every other item uses: low idf
    rng = random.Random(7)
    items = [mk.Item("g%02d" % n, "note", "account_history", "2026-01-%02d" % (1 + n % 28), " ".join(rng.sample(generic, 40))) for n in range(60)]
    items.append(mk.Item("target", "note", "account_history", "2026-02-01", "the zorblax quendel frimble was written up " + " ".join(rng.sample(generic, 30))))
    items.append(mk.Item("decoy", "note", "account_history", "2026-02-02", "an unrelated remark " + " ".join(rng.sample(generic, 40))))
    index = mk.build_index(items, "2026-03-01")
    distinct = ["zorblax", "quendel", "frimble"]
    scores = {}
    for length in (5, 20, 60):
        extra = rng.sample(generic, length - len(distinct))
        query = " ".join(distinct + extra)
        out = mk.retrieve(index, query, "note", "2026-03-01", "lexical")
        assert ids(out)[:1] == ["target"], (length, ids(out))                                  # the same item for 5, 20 and 60 terms
        scores[length] = out["channel_scores"][0]["lexical"]
    assert min(scores.values()) >= 0.2 and max(scores.values()) / min(scores.values()) < 2.0, scores           # the score is on one scale, not a function of the length
    # words the index has never seen cannot dilute the reference: the whole text of an item inside a longer query is found at 10, 25 and 60 foreign words
    note = "The ferry company ledgers were kept in the kitchen by my mother and the tide tables hung beside them"
    crowd = mk.build_index(fillers(40) + [mk.Item("ferry", "note", "account_history", "2026-02-01", note)], "2026-03-01")
    for foreign in (0, 10, 25, 60):
        query = note + " " + " ".join("unseen%d" % n for n in range(foreign))
        out = mk.retrieve(crowd, query, "note", "2026-03-01", "lexical")
        assert ids(out) == ["ferry"] and out["channel_scores"][0]["lexical"] == mk.retrieve(crowd, note, "note", "2026-03-01", "lexical")["channel_scores"][0]["lexical"]
    # a paragraph that shares six words with the note and has seventeen other words that the index knows only as filler
    paragraph = ("I keep thinking about the ferry company ledgers my mother kept; the kitchen table was full of them every winter and the tide tables hung beside the door while "
                 "nobody ever asked what the unrelated filler words were for in the first place")
    assert ids(mk.retrieve(crowd, paragraph, "note", "2026-03-01", "lexical")) == ["ferry"]
    # 0.1.0 lost this: coverage divided by the whole query; with every known stem in the reference (top_terms = 0, max_terms = 0) the loss comes back
    all_terms = {"name": "all", "embed": "off", "top_terms": 0, "max_terms": 0}
    long_query = " ".join(generic[:20]) + " " + " ".join(distinct)
    assert ids(mk.retrieve(index, long_query, "note", "2026-03-01", {"name": "top", "embed": "off"}))[:1] == ["target"]
    assert mk.retrieve(index, long_query, "note", "2026-03-01", all_terms)["channel_scores"][0]["lexical"] < scores[60]


def test_the_rank_is_bm25_repeats_saturate_short_items_win_and_ties_go_to_the_first_id() -> None:
    pads = lambda a, b: " ".join("pad%d" % n for n in range(a, b))                                      # noqa: E731
    items = [mk.Item("once", "note", "account_history", "2026-01-01", "tokenizer " + pads(0, 7)), mk.Item("many", "note", "account_history", "2026-01-02", "tokenizer " * 4 + pads(0, 4)),
             mk.Item("short", "note", "account_history", "2026-01-03", "tokenizer quirks"), mk.Item("long", "note", "account_history", "2026-01-04", "tokenizer " + pads(0, 60)),
             mk.Item("twin-b", "note", "account_history", "2026-01-05", "tokenizer quirks"), mk.Item("twin-a", "note", "account_history", "2026-01-06", "tokenizer quirks")]
    index = mk.build_index(items + fillers(10), "2026-03-01")
    out = mk.retrieve(index, "tokenizer", "note", "2026-03-01", {"name": "t", "embed": "off", "names": False, "lex_tau": 1e-6, "min_evidence": 0.0, "k": 10})
    order = ids(out)
    assert order.index("short") < order.index("once") < order.index("long")                         # length normalisation: the shorter item, the same term count
    assert order.index("many") < order.index("once")                                              # more occurrences score more ...
    s = {i.id: c["lexical"] for i, c in zip(out["items"], out["channel_scores"])}
    assert s["many"] < 4 * s["once"] and out["scores"] == sorted(out["scores"], reverse=True)       # ... but far from four times as much
    assert s["short"] == s["twin-a"] == s["twin-b"] and order.index("twin-a") < order.index("twin-b") and order.index("short") < order.index("twin-a")        # ties: the id that sorts first


def test_at_most_k_items_come_back_best_first_and_k_is_a_profile_setting() -> None:
    items = base_items() + fillers(20)
    stories = ["ferry company ledgers harbour story winter v0", "ferry company ledgers harbour story v1", "ferry company ledgers harbour v2", "ferry company ledgers v3",
               "ferry company v4"]
    items += [mk.Item("s%d" % n, "note", "account_history", "2026-07-0%d" % (n + 1), text) for n, text in enumerate(stories)]
    index = mk.build_index(items, "2026-12-01")
    query = "ferry company ledgers harbour story winter"
    top = mk.retrieve(index, query, "note", "2026-12-01", "lexical")
    assert ids(top) == ["s0", "s1", "s2"] and top["scores"] == sorted(top["scores"], reverse=True) and top["n_candidates"] == 3
    wide = mk.retrieve(index, query, "note", "2026-12-01", {"name": "wide", "k": 5, "embed": "off", "lex_tau": 0.1})
    assert ids(wide)[:3] == ["s0", "s1", "s2"] and 4 <= len(wide["items"]) <= 5 and wide["profile"] == "wide"
    assert ids(mk.retrieve(index, query, "note", "2026-12-01", {"k": 1, "embed": "off"})) == ["s0"]
    for k in (0, -1, -5):
        assert mk.retrieve(index, query, "note", "2026-12-01", {"k": k, "embed": "off"})["items"] == []          # a negative k is not a slice from the end
    assert len(mk.retrieve(index, query, "note", "2026-12-01", {"k": 99, "embed": "off"})["items"]) == top["n_candidates"] == 3
    assert mk.retrieve(index, query, "note", "2026-12-01", {"k": "2", "embed": "off"})["status"] == "ok" and len(mk.retrieve(index, query, "note", "2026-12-01", {"k": "2", "embed": "off"})["items"]) == 2


def test_the_hand_written_scores_agree_with_an_independent_bm25_on_random_text() -> None:
    rng = random.Random(3)
    vocab = ["w%03d" % n for n in range(300)]
    weights = [1.0 / (n + 1) ** 0.8 for n in range(300)]
    texts = [" ".join(rng.choices(vocab, weights, k=rng.randint(8, 60))) for _ in range(120)]
    index = mk.build_index([mk.Item("i%03d" % n, "note", "account_history", "2025-%02d-%02d" % (1 + n % 12, 1 + n % 28), t) for n, t in enumerate(texts)], "2026-01-01")
    n_docs, lengths = len(texts), [len(t.split()) for t in texts]
    avg = sum(lengths) / n_docs
    df = {}
    for t in texts:
        for w in set(t.split()):
            df[w] = df.get(w, 0) + 1

    def reference(query: str, top: int):
        terms = sorted({w for w in query.split() if w in df}, key=lambda w: (-math.log(1 + (n_docs - df[w] + 0.5) / (df[w] + 0.5)), w))
        idf = {w: math.log(1 + (n_docs - df[w] + 0.5) / (df[w] + 0.5)) for w in terms}
        out = []
        for n, t in enumerate(texts):
            counts = {w: t.split().count(w) for w in terms}
            score = sum(idf[w] * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * lengths[n] / avg)) for w, f in counts.items() if f)
            out.append(score / (2.2 * sum(idf[w] for w in (terms[:top] if top else terms))))
        return out

    for q in range(25):
        query = " ".join(rng.choices(vocab, weights, k=rng.choice([1, 3, 8, 20, 45])))
        for top in (10, 0):
            want = reference(query, top)
            got = mk.retrieve(index, query, "note", "2026-01-01", {"name": "r", "embed": "off", "names": False, "lex_tau": 1e-9, "min_evidence": 0.0, "k": 10 ** 6, "top_terms": top, "max_terms": 0})
            for item, channel in zip(got["items"], got["channel_scores"]):
                assert channel["lexical"] == pytest.approx(want[int(item.id[1:])], abs=6e-5), (query, top, item.id)
            assert {i.id for i in got["items"]} == {"i%03d" % n for n, v in enumerate(want) if v > 0}


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
    assert mk.calibrate(index, [("topic1 alpha1 beta1", "2026-09-01")], 0.2) is None                    # nothing is dated before the first of September: no candidate, nothing to calibrate (a threshold of 0.0 would let everything through)
    assert mk.calibrate(index, [("topic1 alpha1", "not a date")], 0.2) is None and mk.calibrate(index, [(None, "2026-10-01")], 0.2) is None and mk.calibrate(None, queries) is None


def test_calibration_uses_the_score_of_retrieve_and_the_bm25_settings_of_the_profile() -> None:
    items = [mk.Item("a", "note", "account_history", "2026-01-01", "alpha beta beta gamma"), mk.Item("b", "note", "account_history", "2026-01-02", "alpha delta"),
             mk.Item("c", "note", "account_history", "2026-01-03", "epsilon zeta eta theta iota kappa")]
    index = mk.build_index(items, "2026-02-01")
    best = mk.retrieve(index, "alpha beta", "note", "2026-02-01", {"name": "t", "embed": "off", "names": False, "lex_tau": 1e-9, "min_evidence": 0.0})["channel_scores"][0]["lexical"]
    got = mk.calibrate(index, [("alpha beta", "2026-02-01")], share=0.0)
    assert got == pytest.approx(best, abs=1e-4) and got <= best                                         # the best score of the single query, rounded down
    narrow = mk.calibrate(index, [("alpha beta", "2026-02-01")], share=0.0, profile={"top_terms": 1, "max_terms": 1, "min_evidence": 0.0})
    assert narrow == pytest.approx(0.625, abs=1e-4)                                                   # beta alone, as above
    assert mk.calibrate(index, [("alpha beta", "2026-02-01")], share=0.0, profile={"top_terms": 1, "max_terms": 1}) is None       # beta alone is below the default floor of evidence, as in retrieve
    # only d1 is dated before the second of January: the statistics are those of that one item (N = 1, the idf of both words is ln(4/3)), exactly as retrieve would take them
    idf = math.log(4 / 3)
    expected = (idf * 1.0 + idf * 1.375) / (2.2 * 2 * idf)
    assert mk.calibrate(index, [("alpha beta", "2026-01-02")], share=0.0) == pytest.approx(expected, abs=1e-4) and round(expected, 4) == 0.5398


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Text units: plurals, stop words, contractions, normalisation
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
PLURALS = (("gpu", "gpus"), ("GPU", "GPUs"), ("llm", "LLMs"), ("API", "APIs"), ("bot", "bots"), ("app", "apps"), ("law", "laws"), ("process", "processes"), ("bias", "biases"),
           ("box", "boxes"), ("batch", "batches"), ("class", "classes"), ("movie", "movies"), ("story", "stories"), ("ferry", "ferries"), ("model", "models"), ("cache", "caches"),
           ("virus", "viruses"), ("bus", "buses"), ("gas", "gases"), ("status", "statuses"), ("analysis", "analyses"), ("hypothesis", "hypotheses"), ("index", "indices"),
           ("matrix", "matrices"), ("axis", "axes"), ("wiki", "wikis"), ("menu", "menus"), ("idea", "ideas"), ("video", "videos"), ("size", "sizes"), ("case", "cases"),
           ("response", "responses"), ("database", "databases"), ("use", "uses"), ("tie", "ties"), ("H100", "H100s"), ("1990", "1990s"), ("ID", "IDs"), ("PR", "PRs"),
           ("VM", "VMs"), ("lens", "lenses"), ("focus", "focuses"), ("query", "queries"), ("entry", "entries"), ("cookie", "cookies"), ("city", "cities"), ("dish", "dishes"),
           ("prefix", "prefixes"), ("address", "addresses"), ("business", "businesses"), ("crisis", "crises"), ("child", "children"), ("tax", "taxes"), ("buzz", "buzzes"))


def test_plurals_fold_to_one_stem_for_short_stems_acronyms_and_es_forms_and_singulars_that_end_in_s_stay() -> None:
    for singular, plural in PLURALS:
        assert mk.stem(singular) == mk.stem(plural), (singular, plural, mk.stem(singular), mk.stem(plural))
    for word in ("bias", "status", "virus", "gas", "bus", "focus", "analysis", "basis", "process", "class", "news", "lens", "series", "species", "plus", "address", "business",
                 "chaos", "thesis", "crisis", "famous", "various", "previous"):
        assert mk.stem(word) == word, word
    assert mk.stem("GPUs") == "gpu" == mk.stem("gpus") and mk.stem("Imre's") == "imre" == mk.stem("Imre’s") and mk.stem("MOVIES") == "movy" == mk.stem("movie")
    assert mk.tokens("THIS WAS SHOUTED") == ["shouted"] and mk.stem("THIS") == "thi"                    # a shouted word is not an acronym plural; and the stop list is read before the stemmer
    assert mk.stem("movies") == "movy" and mk.stem("stories") == "story" and mk.stem("ties") == "tie" and mk.stem("pies") == "pie"
    # both sides of the match: the review's examples
    index = mk.build_index(fillers(25) + [mk.Item("g", "note", "account_history", "2026-02-01", "GPUs, LLMs and APIs: who pays for the compute"),
                                          mk.Item("b", "note", "account_history", "2026-02-02", "batches and boxes of GPUs get shipped to the dock")], "2026-03-01")
    for query in ("GPU LLM API", "GPUs LLMs APIs", "gpu llm api", "who pays for the compute of an API, an LLM and a GPU"):
        assert ids(mk.retrieve(index, query, "note", "2026-03-01", "lexical"))[:1] == ["g"], query
    assert ids(mk.retrieve(index, "a batch and a box of GPU shipped", "note", "2026-03-01", "lexical")) == ["b"]
    assert mk.tokens("bots apps laws GPUs LLMs APIs") == ["bot", "app", "law", "gpu", "llm", "api"]


def test_stop_words_are_tested_on_the_surface_form_before_stemming() -> None:
    for word in ("was", "has", "does", "this", "its", "yes", "his", "us", "is", "as", "thus", "less", "ours", "yours", "theirs", "hers", "Was", "HAS", "Does", "This"):
        assert mk.tokens(word) == [], word
    assert mk.tokens("bus gas lens news") == ["bus", "gas", "lens", "news"]                              # three-letter words that end in s are content, not stop words
    for word in "may might must one all any some other such only more most up out off like much many every each both either neither".split():
        assert mk.tokens(word) == [], word
    assert mk.tokens("Nikt nie wie, czy to jeszcze potrwa, ale tak bywa, gdy się wszyscy spieszą. Oni też bez planu dla nikogo") == ["nikt", "wie", "potrwa", "bywa", "spieszą", "planu", "nikogo"]
    assert mk.tokens("Czy to już koniec ery tanich GPU") == ["koniec", "ery", "tanich", "gpu"]
    old = load_module(FROZEN, "wmb_kernel_frozen_stop_check")
    assert old.STOP <= mk.STOP and len(mk.STOP) > len(old.STOP) + 80


def test_contractions_with_straight_or_curly_apostrophes_leave_no_stems() -> None:
    assert mk.tokens("It isn't what you think, is it?") == ["think"]
    assert mk.tokens("Don't I'm I've can't won't couldn't've it's that's there's let's he'd we'll they're she's") == []
    assert mk.tokens("It isn’t what you think. I’m sure they’ve gone; we‘ll see; she’d say it isn´t") == ["think", "sure", "gone", "see", "say"]
    assert mk.tokens("Alice's Imre’s dogs' GPU's") == ["alice", "imre", "dog", "gpu"]
    assert mk.tokens("rock'n'roll l'été o'brien") == ["rock'n'roll", "l'été", "o'brien"]                 # not contractions of function words: kept whole
    index = mk.build_index(fillers(40) + [mk.Item("h", "note", "account_history", "2026-02-01", "Honestly it isn't the model that fails, it's the harness.")], "2026-03-01")
    assert mk.retrieve(index, "It isn't what you think, is it?", "note", "2026-03-01", "lexical")["items"] == []         # 'isn't' alone is no evidence
    assert ids(mk.retrieve(index, "the harness fails, the model does not", "note", "2026-03-01", "lexical")) == ["h"]


def test_text_is_normalised_to_nfc_and_words_are_letters_of_any_script_split_at_hyphens() -> None:
    assert mk.tokens("Müller") == mk.tokens("Müller") == ["müller"] and mk.tokens("Źle") == mk.tokens("Źle")
    assert mk.tokens("Żółć gęślą jaźń, l'été") == ["żółć", "gęślą", "jaźń", "l'été"]
    assert mk.tokens("Imre's well-known list of the ferries and the stories") == ["imre", "well", "known", "list", "ferry", "story"]
    assert mk.tokens("GPT-4o costs 5 USD; H100s and A100s") == ["gpt", "4o", "cost", "usd", "h100", "a100"]
    assert mk.tokens("") == [] and mk.tokens("   ") == [] and mk.tokens("a I x") == []
    index = mk.build_index(fillers(20) + [mk.Item("m", "note", "account_history", "2026-02-01", "Müller visited the harbour")], "2026-03-01")
    assert ids(mk.retrieve(index, "Müller", "note", "2026-03-01", ONE_WORD)) == ["m"]


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_rare_capitalised_name_passes_the_gate_alone_for_personal_tasks_and_comes_first() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    q = "Who is Imre and why does the ferry company keep a tide gauge in the kitchen basement"
    personal = mk.retrieve(index, q, "personal", "2026-12-01", "lexical")
    assert ids(personal)[0] == "n2" and personal["reasons"][0] == ["name"] and "n1" in ids(personal)[1:] and personal["scores"][0] >= 1.0       # a name hit is at the gate, not below it
    note = mk.retrieve(index, q, "note", "2026-12-01", "lexical")                                       # the channel exists only for the task types a profile names
    assert "n2" not in ids(note) and "n1" in ids(note)
    alone = mk.retrieve(index, "Imre?", "personal", "2026-12-01", "lexical")                            # a name at the start of the text, never written with a small letter
    assert ids(alone) == ["n2"] and "name" in alone["reasons"][0]
    assert ids(mk.retrieve(index, "Who is Imre?", "personal", "2026-12-01", dict(ONE_WORD, names=False))) == ["n2"]     # here the lexical channel finds it as well (given a floor of one word)
    crowded = mk.build_index(base_items() + [mk.Item("n4", "note", "account_history", "2026-09-25", "another ledger entry about the winter")], "2026-12-01")
    assert mk.retrieve(index, "Who is Kitchen in the old stories", "personal", "2026-12-01", NAMES_ONLY)["items"] == []       # the note has the word, but not as a name
    common = mk.retrieve(crowded, "Who is Ledger and why does the ferry company keep a tide gauge in the kitchen basement", "personal", "2026-12-01", "lexical")
    assert all("name" not in r for r in common["reasons"])                                              # 'ledger' is in three items: not rare
    assert mk.retrieve(crowded, "Who is Ledger?", "personal", "2026-12-01", NAMES_ONLY)["items"] == []


def test_a_capital_at_the_start_of_a_sentence_proves_nothing_so_discourse_words_are_not_names() -> None:
    items = fillers(20) + [mk.Item("h1", "note", "account_history", "2026-02-01", "However the committee voted late."),
                           mk.Item("h2", "note", "account_history", "2026-02-02", "Meanwhile the harbour board met in secret."),
                           mk.Item("h3", "note", "account_history", "2026-02-03", "Today the gauge broke. Still, nobody noticed.")]
    index = mk.build_index(items, "2026-03-01")
    for query in ("Meanwhile, tell me about your weekend", "However, what did you do?", "Today I want to hear about your plans"):
        assert mk.retrieve(index, query, "personal", "2026-03-01", NAMES_ONLY)["items"] == [], query
        assert all("name" not in r for r in mk.retrieve(index, query, "personal", "2026-03-01", "lexical")["reasons"]), query
    # a sentence-initial word is still a name when one side shows the capital in the middle of a sentence ...
    people = mk.build_index(fillers(20) + [mk.Item("p1", "note", "account_history", "2026-02-01", "Imre called the first recovery procedure boring."),
                                           mk.Item("p2", "note", "account_history", "2026-02-02", "Last week the colleague Edda joined the project.")], "2026-03-01")
    assert ids(mk.retrieve(people, "Who is Imre and what happened?", "personal", "2026-03-01", NAMES_ONLY)) == ["p1"]            # mid-sentence in the query, initial in the item
    assert ids(mk.retrieve(people, "Edda?", "personal", "2026-03-01", NAMES_ONLY)) == ["p2"]                                    # initial in the query, mid-sentence in the item
    # ... and is not when both show it only at the start (the lexical channel can still find it)
    assert mk.retrieve(people, "Imre?", "personal", "2026-03-01", NAMES_ONLY)["items"] == []
    assert ids(mk.retrieve(people, "Imre?", "personal", "2026-03-01", ONE_WORD)) == ["p1"]
    # a word that is lower case in the same item is an ordinary word there
    plain = mk.build_index(fillers(20) + [mk.Item("k", "note", "account_history", "2026-02-01", "Kitchen duty is dull. The kitchen was cold and Imre cooked.")], "2026-03-01")
    assert mk.retrieve(plain, "Who is Kitchen?", "personal", "2026-03-01", NAMES_ONLY)["items"] == [] and ids(mk.retrieve(plain, "Who is Imre?", "personal", "2026-03-01", NAMES_ONLY)) == ["k"]
    # acronyms are capitals that no position explains
    acr = mk.build_index(fillers(20) + [mk.Item("a", "note", "account_history", "2026-02-01", "NASA launched it. The GPUs followed.")], "2026-03-01")
    assert ids(mk.retrieve(acr, "NASA?", "personal", "2026-03-01", NAMES_ONLY)) == ["a"] and ids(mk.retrieve(acr, "GPUs?", "personal", "2026-03-01", NAMES_ONLY)) == ["a"]
    assert mk.retrieve(acr, "It?", "personal", "2026-03-01", NAMES_ONLY)["items"] == []


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Time, supersession, origin classes, write-back
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_no_item_dated_at_or_after_the_task_is_shown_and_the_index_refuses_later_items() -> None:
    items = base_items() + [mk.Item("late", "note", "account_history", "2027-01-05", "the ferry company ledgers appear again in the new year"),
                            mk.Item("zone", "note", "account_history", "2026-09-12T08:00:00Z", "the ferry company ledgers were audited on a Saturday morning")]
    index = mk.build_index(items, "2026-12-01")
    assert index.rejected == {"future": 1, "invalid": 0, "duplicate": 0} and index.trace_dropped == 0 and "late" not in index.items
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


def test_a_replacement_counts_from_its_own_date_so_an_earlier_task_still_sees_the_old_item() -> None:
    old = mk.Item("flat", "event", "fiction_autobio", "2014-05-01", "you moved into a flat above a chandlery on Anchor Lane")
    new = mk.Item("cottage", "event", "fiction_autobio", "2020-06-01", "you moved from the flat on Anchor Lane to a cottage by the estuary", meta={"supersedes": "flat"})
    index = mk.build_index(base_items() + [old, new], "2026-12-01")
    q = "the flat on Anchor Lane"
    assert ids(mk.retrieve(index, q, "personal", "2018-01-01", "lexical")) == ["flat"]
    assert ids(mk.retrieve(index, q, "personal", "2026-01-01", "lexical")) == ["cottage"] and "flat" in index.items
    assert ids(mk.retrieve(index, q, "personal", "2020-06-01", "lexical")) == ["flat"]                  # the replacement is not before the task, the old item still is


def test_supersession_needs_a_later_existing_item_and_ignores_self_cycles_and_nonsense() -> None:
    def make(ident, day, text, supersedes=None):
        return mk.Item(ident, "note", "account_history", day, text, meta={} if supersedes is None else {"supersedes": supersedes})

    q = "ferry company ledgers harbour"
    body = "ferry company ledgers harbour story"
    cases = {
        "self": [make("x", "2026-01-01", body, "x")],
        "backwards": [make("old", "2026-03-01", body), make("new", "2026-02-01", body, "old")],                 # a replacement dated before what it replaces
        "unknown": [make("a", "2026-01-01", body, "nothing-like-this")],
        "future replacement": [make("old", "2026-01-01", body), make("new", "2027-01-01", body, "old")],              # rejected by the index, so it replaces nothing
        "list": [make("a", "2026-01-01", body, ["a", "b"]), make("b", "2026-01-02", body, {"x": 1})],
    }
    for name, items in cases.items():
        index = mk.build_index(items + fillers(20), "2026-06-01")
        out = mk.retrieve(index, q, "note", "2026-06-01", "lexical")
        assert not index.superseded_by or name == "list", name
        assert set(ids(out)) == {i.id for i in items if i.id in index.items}, name
    tie = mk.build_index([make("old", "2026-03-01", body), make("new", "2026-03-01", body, "old")] + fillers(20), "2026-06-01")          # a replacement of the very same instant counts
    assert tie.superseded_by == {"old": "2026-03-01T00:00:00"} and ids(mk.retrieve(tie, q, "note", "2026-06-01", "lexical")) == ["new"]
    assert mk.retrieve(tie, q, "note", "2026-03-01", "lexical")["items"] == []                                                  # at that instant neither is before the task
    assert ids(mk.retrieve(mk.build_index([make("new", "2026-03-01", body, "old"), make("old", "2026-03-01", body)] + fillers(20), "2026-06-01"), q, "note", "2026-06-01", "lexical")) == ["new"]    # whatever the order of the input
    mutual = mk.build_index([make("a", "2026-03-01", body, "b"), make("b", "2026-03-01", body, "a")] + fillers(20), "2026-06-01")         # items of one instant that replace each other: a cycle, ignored
    loop = mk.build_index([make("a", "2026-03-01", body, "b"), make("b", "2026-03-01", body, "c"), make("c", "2026-03-01", body, "a")] + fillers(20), "2026-06-01")
    assert mutual.superseded_by == {} and loop.superseded_by == {} and set(ids(mk.retrieve(mutual, q, "note", "2026-06-01", "lexical"))) == {"a", "b"}
    assert set(ids(mk.retrieve(loop, q, "note", "2026-06-01", "lexical"))) == {"a", "b", "c"}
    index = mk.build_index([make("a", "2026-01-01", body, "b"), make("b", "2026-02-01", body, "a")] + fillers(20), "2026-06-01")                    # a cycle: only the later one replaces
    assert index.superseded_by == {"a": "2026-02-01T00:00:00"} and ids(mk.retrieve(index, q, "note", "2026-06-01", "lexical")) == ["b"]
    assert ids(mk.retrieve(index, q, "note", "2026-01-15", "lexical")) == ["a"] and ids(mk.retrieve(index, q, "note", "2026-02-01", "lexical")) == ["a"]
    chain = mk.build_index([make("a", "2026-01-01", body), make("b", "2026-02-01", body, "a"), make("c", "2026-03-01", body, "b")] + fillers(20), "2026-06-01")
    assert [ids(mk.retrieve(chain, q, "note", day, "lexical")) for day in ("2026-01-15", "2026-02-15", "2026-03-15")] == [["a"], ["b"], ["c"]]
    twice = mk.build_index([make("a", "2026-01-01", body), make("late", "2026-05-01", body, "a"), make("early", "2026-02-01", body, "a")] + fillers(20), "2026-06-01")
    assert twice.superseded_by == {"a": "2026-02-01T00:00:00"}                                         # the earliest replacement counts, whatever the order of the input


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


def test_a_bare_string_for_a_list_of_task_types_means_one_type_and_unknown_types_get_no_fiction_and_no_names() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    q = "where were you born, Kellmouth fishing town on a cold estuary"
    assert mk.retrieve(index, q, "person", "2026-12-01", {"persona_task_types": "personal", "embed": "off"})["items"] == []        # not a substring match
    assert ids(mk.retrieve(index, q, "personal", "2026-12-01", {"persona_task_types": "personal", "embed": "off"})) == ["e1"]
    assert ids(mk.retrieve(index, q, "reply", "2026-12-01", {"persona_task_types": ["reply", "x"], "embed": "off"})) == ["e1"]
    assert ids(mk.retrieve(index, q, "reply", "2026-12-01", {"persona_task_types": {"reply"}, "embed": "off"})) == ["e1"]
    assert mk.retrieve(index, q, "reply", "2026-12-01", {"persona_task_types": None, "embed": "off"})["items"] == []
    for odd in ("personnal", "", "Personal", None, 7, ("personal",)):
        out = mk.retrieve(index, "Imre? " + q, odd, "2026-12-01", "lexical")
        assert out["status"] == "ok" and "e1" not in ids(out) and all("name" not in r for r in out["reasons"]), odd
    assert mk.retrieve(index, "Imre?", "person", "2026-12-01", {"name_task_types": "personal", "embed": "off", "lex_tau": 1e6})["items"] == []


def test_a_written_back_detail_is_an_invented_event_with_a_stable_id_that_the_next_index_finds() -> None:
    a, b = mk.write_back_item("her name is Edda", "2026-10-20", about="your sister"), mk.write_back_item("her name is Edda", "2026-10-20", about="your sister")
    assert a == b and a.kind == "event" and a.origin == "fiction_autobio" and a.id.startswith("event-2026-10-20-") and a.text == "your sister her name is Edda"
    index = mk.build_index(base_items() + [a], "2026-11-01")
    assert ids(mk.retrieve(index, "what is the name of your sister Edda", "personal", "2026-11-01", "lexical")) == [a.id]
    assert mk.retrieve(index, "what is the name of your sister Edda", "note", "2026-11-01", "lexical")["items"] == []
    assert mk.write_back_item("x", datetime(2026, 10, 20, 9, 0)).id.startswith("event-2026-10-20-")
    for bad in (mk.write_back_item(object(), "2026-10-20"), mk.write_back_item("lone surrogate \ud800", "2026-10-20")):
        assert bad.origin == "fiction_autobio" and (not bad.id or bad.id.startswith("event-"))              # never raises
    assert mk.build_index([mk.write_back_item("\ud800", "2026-10-20")], "2026-11-01").rejected["invalid"] == 1


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
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
    assert mk.build_index(base_items(), "2026-12-01", vectors={"n1": [1.0, 2.0], "n2": [1.0]}).degraded.startswith("embedder failed")          # ready vectors of two sizes
    assert mk.retrieve(mk.build_index(base_items(), "2026-12-01"), "tide tables ferry", "note", "2026-12-01", "hybrid")["status"] == "degraded"
    assert mk.retrieve(mk.build_index(base_items(), "2026-12-01"), "tide tables ferry", "note", "2026-12-01", "kernel")["status"] == "ok"      # auto: no embedder is not a fault


def test_an_empty_index_or_one_whose_items_were_all_rejected_is_ok_with_an_embedder_and_the_embedder_is_not_called() -> None:
    calls: list = []
    for items in ([], [None, mk.Item("x", "tweet", "account_history", "2026-01-01", "bad kind")], [mk.Item("late", "note", "account_history", "2027-01-01", "from the future")]):
        index = mk.build_index(items, "2026-06-01", bow_embedder(calls=calls))
        assert index.degraded == "" and not index.items
        for profile in ("kernel", "hybrid", "lexical"):
            out = mk.retrieve(index, "anything about ferries", "note", "2026-06-01", profile)
            assert out["status"] == "ok" and out["items"] == [] and out["error"] == "" and out["n_index"] == 0, profile
    assert calls == []
    full = mk.build_index(base_items(), "2026-12-01", bow_embedder(calls=calls))
    assert mk.retrieve(full, "anything", "note", "1999-01-01", "kernel")["status"] == "ok"             # every item is in the future of that task: nothing to show, nothing wrong


def test_nothing_raises_and_every_failure_is_a_status() -> None:
    junk = [None, mk.Item("a", "tweet", "account_history", "2026-01-01", "bad kind"), mk.Item("b", "note", "robot", "2026-01-01", "bad origin"),
            mk.Item("c", "note", "account_history", "2026-01-01", "   "), mk.Item("d", "note", "account_history", "not a date", "bad date"),
            mk.Item("", "note", "account_history", "2026-01-01", "empty id"), mk.Item("e", "note", "account_history", "2026-01-01", "fine item about harbour winters"),
            mk.Item("e", "note", "account_history", "2026-01-02", "duplicate id about harbour winters"), mk.Item("f", "note", "account_history", "2027-01-01", "from the future")]
    index = mk.build_index(junk, "2026-06-01")
    assert index.rejected == {"future": 1, "invalid": 6, "duplicate": 1} and index.trace_dropped == 0 and list(index.items) == ["e"] and index.items["e"].created_at == "2026-01-01"
    assert mk.retrieve(index, "harbour winters", "note", "2026-06-01", "no-such-profile")["status"] == "error"
    assert "unknown profile" in mk.retrieve(index, "harbour winters", "note", "2026-06-01", "no-such-profile")["error"]
    assert mk.retrieve(index, "harbour winters", "note", "someday", "lexical")["status"] == "error"
    assert mk.retrieve(index, None, "note", "2026-06-01", "lexical")["status"] == "error"          # type: ignore[arg-type]
    assert mk.retrieve(None, "harbour winters", "note", "2026-06-01", "lexical")["status"] == "error"   # type: ignore[arg-type]
    assert mk.retrieve(index, "harbour winters", "note", "2026-06-01", "lexical")["status"] == "ok"
    assert mk.render(None) == "" and mk.log_record(None, hmac_fn)["status"] == "error" and mk.guard(None, "x")["flags"][0].startswith("guard_error")   # type: ignore[arg-type]
    empty = mk.build_index([], "2026-06-01")
    assert mk.retrieve(empty, "anything at all", "note", "2026-06-01", "kernel")["items"] == []
    assert mk.build_index(None, "2026-06-01").rejected["invalid"] == 1 and mk.build_index(5, "2026-06-01").items == {}          # type: ignore[arg-type]
    assert list(mk.build_index(iter(junk), "2026-06-01").items) == ["e"] and list(mk.build_index(tuple(junk), "2026-06-01").items) == ["e"]


def test_retrieve_with_an_object_that_is_not_an_index_is_an_error_result_and_never_raises() -> None:
    for bad in ({"a": 1}, "idx", [1], 5, object(), mk.Item("a", "note", "account_history", "2026-01-01", "x1 text"), mk.Index, None):
        out = mk.retrieve(bad, "harbour winters", "note", "2026-06-01", "lexical")        # type: ignore[arg-type]
        assert out["status"] == "error" and out["items"] == [] and "not an Index" in out["error"] and out["as_of"] is None and out["n_index"] == 0, bad
        json.dumps(mk.log_record(out, hmac_fn))
        assert mk.guard(out, "As I wrote last week, tides turn.")["flags"] == ["spurious_reference"]
    index = mk.build_index(base_items(), "2026-12-01")
    for query in (None, 5, b"tide", ["tide"]):
        assert mk.retrieve(index, query, "note", "2026-12-01", "lexical")["status"] == "error"        # type: ignore[arg-type]
    for now in (5, 2026, b"2026-01-01", ["2026-01-01"], object(), "2026-13-01"):
        out = mk.retrieve(index, "tide", "note", now, "lexical")                             # type: ignore[arg-type]
        assert out["status"] == "error" and isinstance(out["now"], str), now


def test_a_profile_is_validated_and_a_bad_one_is_an_error_status() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    for bad in ({"embed": "sometimes"}, {"embed": "Off"}, {"k": "x"}, {"k": None}, {"lex_tau": float("nan")}, {"lex_tau": "high"}, {"min_evidence": -1}, {"b": 2}, {"b": -0.1}, {"k1": -1},
                {"k1": float("inf")}, {"tau": "x"}, {"timeout_ms": None}, {"timeout_ms": float("nan")}, {"top_terms": "x"}, {"rare_df": []}, [], 5, 3.5, ("lexical",)):
        out = mk.retrieve(index, "tide tables kitchen", "note", "2026-12-01", bad)          # type: ignore[arg-type]
        assert out["status"] == "error" and out["items"] == [], bad
    ok = mk.retrieve(index, "tide tables kitchen", "note", "2026-12-01", {"k": 2.0, "top_terms": "10", "tau": None, "embed": "off", "timeout_ms": float("inf")})
    assert ok["status"] == "ok" and ids(ok) == ["n1"] and ok["profile"] == "custom"                  # no embedding channel, no cosine threshold; an infinite deadline switches the deadline off
    assert mk.retrieve(index, "tide tables kitchen", "note", "2026-12-01", None)["profile"] == "kernel"
    assert set(mk.PROFILES) == {"kernel", "lexical", "hybrid"} and mk.PROFILES["lexical"]["embed"] == "off" and mk.PROFILES["hybrid"]["embed"] == "required"
    assert all(p["k1"] == 1.2 and p["b"] == 0.75 and p["k"] == 3 and p["tau"] == 0.57 and p["min_evidence"] == 1.4 and p["lex_tau"] == 0.2 and p["len_cap"] == 3.0 for p in mk.PROFILES.values())


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Deadlines and determinism
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
class FakeClock:
    """A stopwatch that moves one millisecond at every reading, so that a deadline falls on a known reading."""

    def __init__(self, step: float = 0.001) -> None:
        self.now, self.step = 0.0, step

    def perf_counter(self) -> float:
        value, self.now = self.now, self.now + self.step
        return value


def test_a_deadline_gives_status_timeout_and_no_items() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    out = mk.retrieve(index, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", {"timeout_ms": -1, "embed": "off"})
    assert out["status"] == "timeout" and out["items"] == [] and out["error"] == "deadline exceeded" and out["now"] == "2026-12-01"
    assert mk.guard(out, "As I wrote earlier, tides turn.")["flags"] == ["spurious_reference"]
    json.dumps(mk.log_record(out, hmac_fn))


def test_the_deadline_is_read_at_the_first_item_and_then_every_two_hundred_items(monkeypatch) -> None:
    index200, index201 = mk.build_index(fillers(200), "2026-12-01"), mk.build_index(fillers(201), "2026-12-01")
    q = "filler5 subject5"
    monkeypatch.setattr(mk, "time", FakeClock())
    # readings: the start (0 ms), the first item (1 ms), the 201st item (2 ms); the deadline is 1.5 ms after the start
    assert mk.retrieve(index200, q, "note", "2026-12-01", {"timeout_ms": 1.5, "embed": "off"})["status"] == "ok"
    monkeypatch.setattr(mk, "time", FakeClock())
    late = mk.retrieve(index201, q, "note", "2026-12-01", {"timeout_ms": 1.5, "embed": "off"})
    assert late["status"] == "timeout" and late["items"] == [] and late["n_considered"] == 0
    monkeypatch.setattr(mk, "time", FakeClock())
    assert mk.retrieve(index201, q, "note", "2026-12-01", {"timeout_ms": 2.5, "embed": "off"})["status"] == "ok"
    monkeypatch.setattr(mk, "time", FakeClock())
    assert mk.retrieve(index201, q, "note", "2026-12-01", {"timeout_ms": 0.5, "embed": "off"})["status"] == "timeout"             # already late at the first item


def test_the_same_inputs_give_the_same_result_whatever_the_order_of_the_items() -> None:
    items = base_items() + [mk.Item("t%d" % n, "note", "account_history", "2026-08-0%d" % (n + 1), "ferry company ledgers harbour story twin") for n in range(5)] + fillers(30)
    q = "ferry company ledgers harbour story"
    first = mk.retrieve(mk.build_index(items, "2026-12-01"), q, "note", "2026-12-01", "lexical")
    shuffled = list(items)
    random.Random(5).shuffle(shuffled)
    second = mk.retrieve(mk.build_index(shuffled, "2026-12-01"), q, "note", "2026-12-01", "lexical")
    keep = ("status", "scores", "channel_scores", "reasons", "dates", "keys", "n_candidates", "n_considered", "tokens_est")
    assert ids(first) == ids(second) == ["t0", "t1", "t2"] and all(first[k] == second[k] for k in keep)
    reordered = mk.build_index([mk.Item("x", "note", "account_history", "2026-01-01", "ferry text one"), mk.Item("x", "event", "account_history", "2026-01-02", "ferry text two")], "2026-06-01")
    flipped = mk.build_index([mk.Item("x", "event", "account_history", "2026-01-02", "ferry text two"), mk.Item("x", "note", "account_history", "2026-01-01", "ferry text one")], "2026-06-01")
    assert reordered.rejected["duplicate"] == flipped.rejected["duplicate"] == 1 and reordered.items["x"].kind == "note" and flipped.items["x"].kind == "event"     # the first one wins


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Rendering, traces, the injection log
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
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
    assert mk.render([items[0], items[1]]) == "[2026-09-01] " + items[0].text + "\n[2026-09-10] A colleague named the recovery procedure. Angle: credit goes to the boring document Left open: who else used it"


def test_a_trace_is_validated_when_the_index_is_built_and_a_bad_one_never_blanks_anything() -> None:
    def make(ident, trace, day):
        return mk.Item(ident, "note", "account_history", day, "ferry company ledgers variant %s" % ident, trace=trace)

    items = [make("list", {"gist": ["a", "list"], "angle": "A"}, "2026-01-01"), make("number", {"gist": 5}, "2026-01-02"), make("string", "gist only", "2026-01-03"),
             make("open", {"gist": "G", "angle": "A", "open": ["q1", "q2"]}, "2026-01-04"), make("seq", ["gist"], "2026-01-05"), make("good", {"gist": "G", "angle": "A", "open": "O"}, "2026-01-06"),
             make("none", None, "2026-01-07"), make("empty", {}, "2026-01-08"), make("gist", {"gist": "only a gist"}, "2026-01-09"), make("extra", {"gist": "G2", "confidence": 0.9}, "2026-01-10"),
             make("blank", {"gist": "  ", "angle": None}, "2026-01-11")]
    index = mk.build_index(items + fillers(10), "2026-03-01")
    assert index.trace_dropped == 5 and index.rejected["invalid"] == 0 and len(index.items) == len(items) + 10                # counted once per item, none rejected
    assert "trace_dropped" not in index.rejected and sum(index.rejected.values()) == 0                                           # rejected holds the three counters of 0.1.0: dropped items only
    assert all(index.items[i.id] is i for i in items)                                  # the items are kept as they were passed: no copy, no rewritten trace
    assert index.items["extra"].trace == {"gist": "G2", "confidence": 0.9} and index.items["list"].trace == {"gist": ["a", "list"], "angle": "A"} and index.items["string"].trace == "gist only"
    out = mk.retrieve(index, "ferry company ledgers", "note", "2026-03-01", dict(EVERYTHING, k=100))
    assert len(out["items"]) == len(items) and all(any(got is given for given in items) for got in out["items"])               # retrieve returns the caller's own objects
    rendered = mk.render(out).splitlines()
    assert len(rendered) == len(items) and out["tokens_est"] > 0 and "q1" not in "".join(rendered)                                  # nothing was blanked
    body = [line[13:] for line in rendered]                                      # one line per item, oldest first: the order of `items`
    raw = lambda ident: "ferry company ledgers variant %s" % ident                # noqa: E731
    assert body == [raw("list"), raw("number"), raw("string"), "G Angle: A", raw("seq"), "G Angle: A Left open: O", raw("none"), raw("empty"), "only a gist", "G2", raw("blank")]
    assert mk.render(out, mode="raw").count("variant") == len(items)
    assert mk.build_index([make("a", {"gist": "G"}, "2026-01-01")], "2026-03-01").trace_dropped == 0


def test_render_degrades_per_item_and_collapses_whitespace_so_an_item_cannot_add_a_line() -> None:
    good = mk.Item("good", "note", "account_history", "2026-01-02", "fine text about ferries", trace={"gist": "G", "angle": "A"})
    bad_trace = mk.Item("bt", "note", "account_history", "2026-01-01", "raw text of the broken trace", trace={"gist": ["x"], "angle": 5})            # type: ignore[arg-type]
    string_trace = mk.Item("st", "note", "account_history", "2026-01-03", "raw text of the string trace", trace="gist only")                          # type: ignore[arg-type]
    no_text = mk.Item("nt", "note", "account_history", "2026-01-04", None)                                                                            # type: ignore[arg-type]
    no_date = mk.Item("nd", "note", "account_history", "garbage", "text of the dateless item")
    no_id = mk.Item(None, "note", "account_history", "2026-01-05", "text of the item without an id")                                                 # type: ignore[arg-type]
    assert mk.render([good, bad_trace, string_trace, no_text, no_date, no_id]) == ("[2026-01-01] raw text of the broken trace\n[2026-01-02] G Angle: A\n"
                                                                                  "[2026-01-03] raw text of the string trace")
    assert mk.render([bad_trace], mode="raw") == "[2026-01-01] raw text of the broken trace" and mk.render([no_text, no_date]) == "" and mk.render([]) == ""
    forged = mk.Item("fg", "note", "account_history", "2026-01-06", "line one\n\n[2020-01-01] I won the lottery\r\n\tagain", trace={"gist": "gist\nwith\n[1999-01-01] a forged line", "open": "q\n\nr"})
    assert mk.render([forged]) == "[2026-01-06] gist with [1999-01-01] a forged line Left open: q r" and mk.render([forged], mode="raw") == "[2026-01-06] line one [2020-01-01] I won the lottery again"
    assert len(mk.render([good, forged]).splitlines()) == 2
    # the dates of a result are read from its keys; without them, from the items
    result = {"items": [good, bad_trace], "keys": ["2026-01-02T00:00:00", "2025-05-05T00:00:00"]}
    assert mk.render(result) == "[2025-05-05] raw text of the broken trace\n[2026-01-02] G Angle: A"
    assert mk.render({"items": [good, bad_trace], "keys": ["2026-01-02T00:00:00"]}) == "[2026-01-01] raw text of the broken trace\n[2026-01-02] G Angle: A"       # keys of another length: recomputed


def test_render_log_and_guard_agree_on_which_items_were_shown() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    q = "Who is Imre and why does the ferry company keep a tide gauge in the kitchen basement"
    result = mk.retrieve(index, q, "personal", "2026-12-01", "lexical")
    assert ids(result) == ["n2", "n1"] and len(mk.render(result).splitlines()) == 2
    first, second = result["items"]
    broken = mk.Item("n2", "note", "account_history", "2026-09-10", None)                                       # type: ignore[arg-type]
    altered = dict(result, items=[broken, second])
    assert len(mk.render(altered).splitlines()) == 1
    record = mk.log_record(altered, hmac_fn, raw_ids=True)
    assert record["item_hmacs"] == [hmac_fn("n1")] and record["ids"] == ["n1"] and record["kinds"] == ["note"] and record["origins"] == ["account_history"]
    assert record["dates"] == [result["dates"][1]] and record["scores"] == [result["scores"][1]] and record["reasons"] == [result["reasons"][1]]
    assert record["channel_scores"] == [result["channel_scores"][1]]
    ref = "As I wrote last week about the colleague Imre and the recovery procedure, the archive was saved."          # supported only by the item that is NOT shown
    assert mk.guard(result, ref)["flags"] == []
    assert mk.guard(altered, ref)["flags"] == ["unsupported_reference"]
    assert mk.guard(dict(result, items=[broken, dataclasses.replace(second, text="x")]), ref)["flags"] == ["unsupported_reference"]
    nothing = dict(result, items=[broken])
    assert mk.render(nothing) == "" and mk.log_record(nothing, hmac_fn)["item_hmacs"] == [] and mk.guard(nothing, ref)["flags"] == ["spurious_reference"]
    # items that retrieve returns are always shown: the rule is the same, applied before the result leaves
    for task in ("note", "personal"):
        for query in (q, "tide", "ferry company ledgers", SYNONYM_QUERY):
            out = mk.retrieve(index, query, task, "2026-12-01", "kernel")
            assert len(mk.render(out).splitlines()) == len(out["items"]) == len(mk.log_record(out, hmac_fn)["item_hmacs"])


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


def json_types_only(value) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, (list, tuple)):
        return all(json_types_only(v) for v in value)
    return isinstance(value, dict) and all(isinstance(k, str) and json_types_only(v) for k, v in value.items())


def test_the_log_record_is_json_whatever_type_now_has_and_keeps_both_the_text_and_the_key_of_now() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    q = "tide tables and the ferry ledgers kept by my mother"
    moments = {"string": ("2026-12-01T12:00:00+01:00", "2026-12-01T11:00:00"), "date": (date(2026, 12, 1), "2026-12-01T00:00:00"), "naive": (datetime(2026, 12, 1, 12, 0), "2026-12-01T12:00:00"),
               "aware": (datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc), "2026-12-01T12:00:00"), "zone": (datetime(2026, 12, 1, 12, 0, tzinfo=timezone(timedelta(hours=-5))), "2026-12-01T17:00:00"),
               "none": (None, "2026-12-01T00:00:00")}
    for name, (now, key) in moments.items():
        out = mk.retrieve(index, q, "note", now, "lexical")
        assert out["status"] == "ok" and isinstance(out["now"], str) and out["now_key"] == key, name
        record = mk.log_record(out, hmac_fn)
        assert json.loads(json.dumps(record)) == record and json_types_only(record) and isinstance(record["now"], str) and record["now_key"] == key, name
        assert not any(isinstance(v, (date, datetime)) for v in out.values()) and ids(out) == (["n1"] if key > "2026-09-01" else []), name
    assert mk.retrieve(index, q, "note", moments["aware"][0], "lexical")["now"] == str(moments["aware"][0])
    for broken in (7, object(), "yesterday"):
        out = mk.retrieve(index, q, "note", broken, "lexical")                               # type: ignore[arg-type]
        record = mk.log_record(out, hmac_fn)
        assert out["status"] == "error" and isinstance(out["now"], str) and json.loads(json.dumps(record)) == record and record["status"] == "error"


def test_the_log_record_carries_no_word_of_any_text_and_no_message_of_an_exception() -> None:
    texts = ["zorblax quendel frimble sprocket", "gwendolyn thistlewick marmalade", "the ferry company ledgers"]
    items = [mk.Item("a-1", "note", "account_history", "2026-01-01", texts[0], trace={"gist": "vexillology cartouche", "angle": "yodeling", "open": "quokka"}),
             mk.Item("b-2", "reply", "world_knowledge", "2026-01-02", texts[1]), mk.Item("c-3", "event", "fiction_autobio", "2026-01-03", texts[2])]
    index = mk.build_index(items + fillers(5), "2026-03-01")
    query = "zorblax quendel gwendolyn thistlewick ferry company ledgers sprocket marmalade"
    out = mk.retrieve(index, query, "personal", "2026-03-01", dict(EVERYTHING, names=True))
    assert len(out["items"]) == 3
    blob = json.dumps(mk.log_record(out, hmac_fn, key="a-task"))
    words = {w.lower() for text in texts + [query, "vexillology cartouche yodeling quokka"] for w in re.findall(r"[A-Za-z]{4,}", text)}
    assert words and not [w for w in words if w in blob.lower()], [w for w in words if w in blob.lower()]
    assert "a-1" not in blob and "b-2" not in blob and "c-3" not in blob                                       # ids only when raw_ids asks for them
    secret = mk.retrieve(index, query, "note", "the secret of zorblax", "lexical")
    assert secret["status"] == "error" and "zorblax" in secret["error"]                                      # the caller may read the message ...
    assert "zorblax" not in json.dumps(mk.log_record(secret, hmac_fn)) and mk.log_record(secret, hmac_fn)["error"] == "ValueError"        # ... the log keeps the class
    degraded = mk.retrieve(mk.build_index(items, "2026-03-01"), query, "note", "2026-03-01", "hybrid")
    assert mk.log_record(degraded, hmac_fn)["error"] == "no embedder"


def test_the_log_record_fails_into_an_error_record_when_the_hash_function_fails() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    out = mk.retrieve(index, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "lexical")

    def failing(text):
        raise RuntimeError("the key is gone: tide tables")

    for bad in (failing, lambda t: b"bytes", lambda t: 5, lambda t: None):
        record = mk.log_record(out, bad)
        assert record["status"] == "error" and record["error"].startswith("log_record: ") and "tide" not in json.dumps(record) and json_types_only(record)
    assert mk.log_record(out, failing)["error"] == "log_record: RuntimeError"


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Ids, kinds, the lens of retrieval
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_ids_are_unique_across_kinds_and_texts_may_repeat_under_different_ids() -> None:
    same = "zorblax quendel frimble sprocket"
    items = [mk.Item("n-1", "note", "account_history", "2026-01-01", same), mk.Item("n-1", "reply", "account_history", "2026-01-02", same + " other"),
             mk.Item("n-2", "note", "account_history", "2026-01-03", same), mk.Item("n-3", "comment", "account_history", "2026-01-04", same), mk.Item("n-4", "event", "account_history", "2026-01-05", same)]
    index = mk.build_index(items + fillers(10), "2026-03-01")
    assert index.rejected["duplicate"] == 1 and index.items["n-1"].kind == "note"
    out = mk.retrieve(index, same, "note", "2026-03-01", dict(LEXICAL_ONLY, k=10))
    assert ids(out) == ["n-1", "n-2", "n-3", "n-4"] and len(set(out["scores"])) == 1                      # the same text under four ids: all of them, the ids break the tie
    assert {i.kind for i in out["items"]} == {"note", "comment", "event"}


def test_urls_numbers_and_a_single_rare_word_in_a_short_query() -> None:
    items = fillers(30) + [mk.Item("u", "note", "account_history", "2026-02-01", "Read https://example.org/papers/2026/attention-is-all-you-need.html before the call, v2.5 notes"),
                           mk.Item("r", "note", "account_history", "2026-02-02", "The quokka enclosure reopened after the storm")]
    index = mk.build_index(items, "2026-03-01")
    assert ids(mk.retrieve(index, "the attention paper at example.org/papers/2026", "note", "2026-03-01", "lexical")) == ["u"]
    assert mk.retrieve(index, "quokka", "note", "2026-03-01", "lexical")["items"] == []                                 # one rare word is not enough by default: an unrelated short query that happens to share it does not fire ...
    assert ids(mk.retrieve(index, "quokka", "note", "2026-03-01", ONE_WORD)) == ["r"]                                   # ... unless the profile asks for one word (min_evidence 0.8)
    assert ids(mk.retrieve(index, "quokka enclosure", "note", "2026-03-01", "lexical")) == ["r"]                        # two rare words are enough
    long = "what do you think about the quokka situation in the news this week given everything we said about the weather the harbour the tides and the many other things"
    assert mk.retrieve(index, long, "note", "2026-03-01", "lexical")["items"] == []                                        # a long text with ONE shared rare word is not a match by default
    assert ids(mk.retrieve(index, long, "note", "2026-03-01", ONE_WORD)) == ["r"]                                          # words the index has not seen do not count against it, however many
    assert mk.retrieve(index, long, "note", "2026-03-01", {"name": "two", "embed": "off", "min_evidence": 1.4})["items"] == []        # the default, asked for by name


def test_the_fiction_the_future_and_replaced_items_are_not_part_of_the_statistics_of_a_call() -> None:
    # df, the number of items and the average length are those of the items that the call may see: a flood of invented autobiography in a note task, the items dated after a replayed
    # task and the items that are already replaced can neither dilute nor inflate the idf of a word (0.2.0 as first built took them over the whole index and lost the hit)
    visible = [mk.Item("a", "note", "account_history", "2026-01-01", "tokenizer quirks")] + fillers(12)
    flood = [mk.Item("f%d" % n, "event", "fiction_autobio", "2026-01-02", "tokenizer quirks again %d" % n) for n in range(30)]
    later = [mk.Item("z%d" % n, "note", "account_history", "2026-06-01", "tokenizer quirks later %d" % n) for n in range(30)]
    alone = mk.retrieve(mk.build_index(visible, "2026-12-01"), "tokenizer quirks", "note", "2026-03-01", "lexical")
    crowd = mk.build_index(visible + flood + later, "2026-12-01")
    assert crowd.df["tokenizer"] == 61 and len(crowd.items) == 73                         # the index counts everything ...
    mixed = mk.retrieve(crowd, "tokenizer quirks", "note", "2026-03-01", "lexical")
    assert ids(alone) == ["a"] and ids(mixed) == ["a"]                                    # ... a call counts what it may see: the same hit, the same numbers
    assert mixed["channel_scores"] == alone["channel_scores"] and mixed["scores"] == alone["scores"] and mixed["n_considered"] == alone["n_considered"] == 13
    assert mixed["n_index"] == 73
    personal = mk.retrieve(crowd, "tokenizer quirks", "personal", "2026-03-01", "lexical")      # a personal task may see the fiction: now the words are common and are no evidence
    assert personal["n_considered"] == 43 and personal["items"] == []
    after_all = mk.retrieve(crowd, "tokenizer quirks", "note", "2027-01-01", "lexical")        # and a task after the dated-later items sees them too
    assert after_all["n_considered"] == 43 and after_all["items"] == []
    old = mk.Item("old", "note", "account_history", "2026-01-03", "tokenizer quirks of the old kind")
    new = mk.Item("new", "note", "account_history", "2026-02-01", "tokenizer quirks of the new kind", meta={"supersedes": "old"})
    replaced = mk.build_index(visible + [old, new], "2026-12-01")
    assert mk.retrieve(replaced, "tokenizer quirks", "note", "2026-06-01", "lexical")["n_considered"] == 13 + 1      # the replaced item is not counted (a, the fillers and the new one)


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# The reference guard, measured. Two further banks were written after the first had been used to tune the patterns, each before the figures of the one before were fixed:
#   FRESH_ONE   written when the patterns of the first bank were frozen; 20 of 30 positives and 3 false alarms of 23 flags at that time (precision 0.870, recall 0.667), then the
#               patterns were extended for what it showed (possessives with a month, relative clauses, 'at the time', readers who follow, a restricted 'shared' and 'raised', numbers
#               after 'wrote about', private audiences) - so it is no longer an independent test
#   FRESH_TWO   written after that; 26 of 30 positives and 1 false alarm of 27 flags (precision 0.963, recall 0.867), then 'what I wrote', 'I already covered', 'as previously
#               reported', and a narrower 'wrote ... last week' were added - so it too is a development set now
# The figures below are therefore optimistic. The author of the sentences is the author of the patterns; what they show is the direction and the size of the change against 0.1.0
# (the same sentences through the frozen guard are scored in the test of the baseline), not the rates of any account. Relabel a sample of your own outputs before you trust a number.
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
FRESH_ONE_POSITIVE = (
    "Picking up where my November post left off, the new numbers are in.",
    "This is a follow-up to the thread I started on Friday.",
    "I returned to the topic of context length in a later post.",
    "I have already written about the licensing question at length.",
    "As I put it last time, evaluation is the product.",
    "I made a version of this argument when the model launched.",
    "Long-time followers of the account will have heard this from me before.",
    "I wrote up the results of that experiment in a post a month ago.",
    "I covered this exact failure mode in the last issue.",
    "We said at the time that the pricing would not last.",
    "I've been banging the drum on this since the spring.",
    "My thinking on this has not changed since my last newsletter.",
    "I flagged the same problem in a note in February.",
    "As promised, here is the follow-up to last week's piece.",
    "I think I mentioned this in passing a while back.",
    "Back in the summer, I made the opposite prediction.",
    "Readers who follow this feed will know my view.",
    "Some of you asked me about this after my post on agents.",
    "I'll admit I got this wrong in my first note on the subject.",
    "I wrote on this topic a couple of weeks ago.",
    "I have never been shy about saying that benchmarks mislead.",
    "Earlier in the year I laid out why I think costs will fall.",
    "Those who read my last column will remember the example.",
    "In an earlier thread I compared the two approaches.",
    "I put this to the test in a post last year.",
    "We published an explainer on this in the spring.",
    "I have posted about this before.",
    "My earlier argument still holds.",
    "Remember the chart I shared two weeks ago?",
    "I stand by what I told you in January.",
)
FRESH_ONE_NEGATIVE = (
    "The post-mortem published by the vendor blames a misconfigured cache.",
    "Last quarter's earnings call highlighted record data-centre revenue.",
    "I wrote the tests first, then the implementation.",
    "We noted a small drop in accuracy after the quantisation step.",
    "As shown earlier in the table, the smaller model is cheaper.",
    "The previous section explained the training loop.",
    "I mentioned in the introduction that the setup is simple.",
    "The earlier release was withdrawn after a safety review.",
    "I'm going to cover three topics: memory, tools and evaluation.",
    "A user posted a screenshot showing the model refusing a harmless request.",
    "Our first attempt at fine-tuning failed because of a data leak.",
    "My last meeting of the day was about GPU quotas.",
    "She explained that the lab had paused the release.",
    "I explained the trade-offs to the board, and they chose the cheaper option.",
    "The newsletter's open rate fell after the redesign.",
    "I argued with a colleague about whether to log full prompts.",
    "In an earlier version of the draft, the numbers were wrong.",
    "Previous editions of the benchmark used a smaller test set.",
    "We shared the dataset with two universities last summer.",
    "Last week, a bug in the scheduler delayed every job by an hour.",
    "I often say yes to demos, which is a bad habit.",
    "As I see it, the safest default is no memory at all.",
    "Regular expressions are still the fastest way to filter this log.",
    "I wrote about forty lines of glue code to connect the two services.",
    "The thread pool was exhausted after the retry storm.",
    "Remember, the model only sees what is in its context window.",
    "You can recall earlier turns by pasting them into the prompt.",
    "Two issues ago the maintainers deprecated the old API.",
    "I covered the keyboard with a cloth while the printer ran.",
    "The first post in the series is the best one.",
)
FRESH_TWO_POSITIVE = (
    "As previously reported, the vendor has not answered our questions.",
    "See my earlier note on retrieval for the details.",
    "It was noted in an earlier issue that small labs rarely publish negative results.",
    "I first raised this concern last autumn, and the answer I got was vague.",
    "Compare this with the thread I wrote in March about agent costs.",
    "In my December newsletter I said the bubble talk was premature.",
    "We have written before about the gap between demos and products.",
    "Anyone who read my piece on tokenisers will know where this is going.",
    "I made the same prediction last quarter and I am sticking with it.",
    "My view hasn't changed since the post I put out in the summer.",
    "This is a theme I first wrote about two years ago.",
    "As I keep reminding readers, a benchmark is not a product.",
    "I said last week that I would revisit the pricing numbers, so here they are.",
    "Last week's newsletter promised a follow-up on evaluation, and this is it.",
    "The argument I laid out in my first post still stands.",
    "I covered the paper's main result in a thread yesterday.",
    "I pointed this out in a previous issue and got a few replies.",
    "To follow up on what I wrote last time: the numbers held up.",
    "Long-time readers have heard me complain about leaderboards before.",
    "As some of you will recall, I was unimpressed by the first version.",
    "I have been over this ground in earlier posts, so I will be brief.",
    "I'd mentioned the pricing risk a few weeks ago.",
    "My previous post on safety cases drew several objections.",
    "Two months ago I argued that the smaller model would win on cost.",
    "I called this one in my spring newsletter.",
    "We wrote about the outage on the day it happened.",
    "I touched on this briefly in a post last month.",
    "I told readers in the last issue to wait for independent tests.",
    "I flagged the licence problem when the weights were first released, in a note.",
    "Earlier this year I wrote that inference prices would halve.",
)
FRESH_TWO_NEGATIVE = (
    "The post-training stage now takes longer than pre-training for some labs.",
    "Previous work on retrieval-augmented generation focused on question answering.",
    "As the chart above shows, latency grows with context length.",
    "Earlier in this section I described the evaluation set.",
    "I noted the error rate before and after the patch, and it halved.",
    "A previous release of the library had a different licence.",
    "Last week the maintainers merged a large refactor.",
    "She said earlier that the lab would release the weights.",
    "I wrote the migration script on Sunday and ran it on Monday.",
    "Our first attempt used a much smaller model.",
    "We posted the results on the project wiki so the team can find them.",
    "I mentioned the idea to a friend at the conference.",
    "Remember that tokens are not words.",
    "Readers of the paper will find the appendix useful.",
    "The authors wrote that the method needs further testing.",
    "Last month's outage was caused by an expired certificate.",
    "I covered three topics in the workshop: memory, tools and evaluation.",
    "The earlier prototype used a rule-based router.",
    "As I said in the introduction, this is a short note.",
    "My latest benchmark run finished overnight.",
    "I explained the rate limit to the new hire.",
    "The thread I am replying to asks about licensing.",
    "I posted a screenshot of the error to the issue tracker.",
    "In my previous job I worked on search ranking.",
    "I keep a spreadsheet of model prices.",
    "The first article in the series covers data collection.",
    "Yesterday the lab posted a statement about the incident.",
    "I argued with the reviewer, and the paper was accepted anyway.",
    "Back in March, the team changed the tokenizer.",
    "See the table below for details.",
)
# the positives that the patterns still do not see (known limits: idioms, a bare possessive noun without a qualifier, an anchor far from the verb)
KNOWN_MISSES = {
    "I returned to the topic of context length in a later post.", "I made a version of this argument when the model launched.", "I've been banging the drum on this since the spring.",
    "I have never been shy about saying that benchmarks mislead.", "I put this to the test in a post last year.",
    "Anyone who read my piece on tokenisers will know where this is going.",
}
BANK_DIGEST = "6e35b7185013d1538185d0251a7d65760421c6088b994d8f17900361757124f1"
FROZEN_BASELINE = {"tp": 23, "fp": 8}                  # the 0.1.0 guard on the first bank: 23 of 66 positives flagged, 8 of 66 negatives flagged (precision 0.742, recall 0.348)


def test_the_first_bank_is_intact_and_the_frozen_guard_scored_on_it_what_it_scored_before_the_patterns_were_written() -> None:
    blob = "\n".join(BANK_POSITIVE) + "\n--\n" + "\n".join(BANK_NEGATIVE)
    assert len(BANK_POSITIVE) == len(BANK_NEGATIVE) == 66 and len(set(BANK_POSITIVE) | set(BANK_NEGATIVE)) == 132
    assert hashlib.sha256(blob.encode("utf-8")).hexdigest() == BANK_DIGEST            # the bank is not edited after the fact: add a new list instead
    old = load_module(FROZEN, "wmb_kernel_frozen_guard_baseline")
    tp, fp = bank_flags(BANK_POSITIVE, old), bank_flags(BANK_NEGATIVE, old)
    assert (tp, fp) == (FROZEN_BASELINE["tp"], FROZEN_BASELINE["fp"])
    precision, recall = precision_recall(tp, fp, 66, 66)
    assert round(precision, 3) == 0.742 and round(recall, 3) == 0.348
    for positives, negatives in ((FRESH_ONE_POSITIVE, FRESH_ONE_NEGATIVE), (FRESH_TWO_POSITIVE, FRESH_TWO_NEGATIVE)):
        assert bank_flags(positives, old) < 0.4 * len(positives)                        # the 0.1.0 patterns find a fifth of the references of the fresh banks, too


def test_the_guard_finds_the_references_of_the_banks_and_not_the_sentences_that_only_look_like_them() -> None:
    results = {}
    for name, positives, negatives in (("bank", BANK_POSITIVE, BANK_NEGATIVE), ("dev", split_bank(BANK_POSITIVE)[0], split_bank(BANK_NEGATIVE)[0]),
                                       ("held out", split_bank(BANK_POSITIVE)[1], split_bank(BANK_NEGATIVE)[1]), ("fresh one", FRESH_ONE_POSITIVE, FRESH_ONE_NEGATIVE),
                                       ("fresh two", FRESH_TWO_POSITIVE, FRESH_TWO_NEGATIVE)):
        tp, fp = bank_flags(positives), bank_flags(negatives)
        results[name] = (tp, fp, len(positives), len(negatives)) + tuple(round(x, 3) for x in precision_recall(tp, fp, len(positives), len(negatives)))
    # (true positives, false alarms, positives, negatives, precision, recall) - pinned, so that a change of the patterns shows in the diff of this file
    assert results == {"bank": (66, 0, 66, 66, 1.0, 1.0), "dev": (44, 0, 44, 44, 1.0, 1.0), "held out": (22, 0, 22, 22, 1.0, 1.0),
                       "fresh one": (25, 0, 30, 30, 1.0, 0.833), "fresh two": (29, 0, 30, 30, 1.0, 0.967)}, results
    empty = {"items": [], "status": "ok"}
    missed = {s for s in FRESH_ONE_POSITIVE + FRESH_TWO_POSITIVE + BANK_POSITIVE if mk.guard(empty, s)["callbacks"] == 0}
    assert missed == KNOWN_MISSES
    assert [s for s in BANK_NEGATIVE + FRESH_ONE_NEGATIVE + FRESH_TWO_NEGATIVE if mk.guard(empty, s)["callbacks"]] == []


def test_the_guard_ignores_case_curly_apostrophes_spaces_markup_and_hidden_characters() -> None:
    def variants(sentence: str) -> dict:
        return {"upper": sentence.upper(), "title": sentence.title(), "curly": sentence.replace("'", "’"), "modifier": sentence.replace("'", "ʼ"), "nbsp": sentence.replace(" ", " "),
                "double": sentence.replace(" ", "  "), "tabs": sentence.replace(" ", "\t"), "zero width": "​".join(sentence[n:n + 4] for n in range(0, len(sentence), 4)),
                "emphasis": re.sub(r"\b(I|we|my|our)\b", r"*\1*", sentence), "bold": "**" + sentence + "**", "underscores": sentence.replace(" ", "_ _", 3), "wrapped": "Start of the note. " + sentence + " End.",
                "soft hyphen": sentence.replace("wrote", "wr­ote").replace("said", "sa­id"), "full width": sentence.replace("I ", "Ｉ ")}

    empty = {"items": [], "status": "ok"}
    for sentence in BANK_POSITIVE + FRESH_ONE_POSITIVE + FRESH_TWO_POSITIVE:
        base = mk.guard(empty, sentence)["callbacks"]
        for name, changed in variants(sentence).items():
            assert mk.guard(empty, changed)["callbacks"] == base, (name, changed)
    for sentence in BANK_NEGATIVE + FRESH_ONE_NEGATIVE + FRESH_TWO_NEGATIVE:
        for name, changed in variants(sentence).items():
            assert mk.guard(empty, changed)["callbacks"] == 0, (name, changed)
    spaced = "As I wrote  earlier last week, tides turn."
    assert mk.guard(empty, spaced)["callbacks"] == 1 and mk.guard(empty, "AS  I WROTE LAST WEEK about tides")["callbacks"] == 1


def test_a_reference_to_the_text_being_written_is_not_a_reference_unless_the_sentence_also_points_outside_it() -> None:
    empty = {"items": [], "status": "ok"}
    inside = ("As I explained earlier in this article, the cost curve is flat.", "As noted above, the evaluation set is small.", "In the previous paragraph I argued that scaling is slowing.",
              "Earlier in this note I said that the benchmark is saturated.", "I will come back to this point later in the post.", "As I said at the start, this is only a first look.",
              "To recap what I wrote above: three labs lead and the rest trail.", "I covered the training setup in the first half of this piece.", "As we discussed in the introduction, it is small.",
              "As I wrote earlier in the thread, the cache is the bottleneck.", "I mentioned this in my reply above.", "As I said so far, nothing has changed.")
    for sentence in inside:
        assert mk.guard(empty, sentence) == {"ok": True, "flags": [], "callbacks": 0}, sentence
    mixed = ("As I wrote last month, and as the table above shows, costs fell.", "Two weeks ago I argued the opposite of what the section below says.",
             "Last week I wrote about this, and I will return to it later in this post.")
    for sentence in mixed:
        assert mk.guard(empty, sentence) == {"ok": False, "flags": ["spurious_reference"], "callbacks": 1}, sentence
    # the answer to a note: the note above is the task, not a memory
    assert mk.guard(no_memory(), "As I wrote in the note above, the cost curve is flat.")["ok"] is True


def test_ordinary_ai_vocabulary_that_contains_words_of_the_old_phrase_list_is_not_a_reference() -> None:
    empty = {"items": [], "status": "ok"}
    for sentence in ("Post-training now accounts for most of the gains.", "A post-mortem of the outage is due on Friday.", "The previous generation of models was weaker.",
                     "Earlier checkpoints are available for download.", "The last layer is trained separately.", "Last-mile delivery is the hard part of agents.",
                     "My first impression was good.", "Our first prototype was slow.", "My previous employer ran a similar system.", "Regular updates ship every month.",
                     "Earlier versions of the API are deprecated.", "The first article in the series covers data collection.", "A recent paper argues the opposite.",
                     "I wrote a parser for the logs.", "I said no.", "I posted the form to the office.", "We covered the cost of the trip.", "I noted the price.",
                     "I recall how nervous I felt.", "You may recall that the first transformer was built for translation.", "Remember to save your work.",
                     "My issue with the benchmark is its size.", "My story starts in a small lab.", "I keep a list of papers.", "I mentioned the bug to the maintainers last week.",
                     "We shared the dataset with the team last month.", "I often say yes too quickly.", "I wrote about forty lines of code last week."):
        assert mk.guard(empty, sentence)["callbacks"] == 0, sentence


def test_callbacks_counts_the_sentences_that_refer_back_and_the_public_patterns_are_kept() -> None:
    empty = {"items": [], "status": "ok"}
    text = "Last week I wrote about agents. The model is small. As I said before, evals matter.\nMy earlier post covered it too. Costs fell."
    assert mk.guard(empty, text) == {"ok": False, "flags": ["spurious_reference"], "callbacks": 3}
    assert mk.guard(empty, "") == {"ok": True, "flags": [], "callbacks": 0} and mk.guard(empty, None) == {"ok": True, "flags": [], "callbacks": 0}       # type: ignore[arg-type]
    assert isinstance(mk.CALLBACKS, tuple) and len(mk.CALLBACKS) > 10 and all(hasattr(p, "search") for p in mk.CALLBACKS)
    assert any(p.search("As I Wrote Last Week, tides turn.") for p in mk.CALLBACKS) and not any(p.search("Post-training now accounts for most of the gains.") for p in mk.CALLBACKS)


def agent_index():
    common = [mk.Item("c%02d" % n, "note", "account_history", "2026-02-%02d" % (1 + n % 27), "agents and models in production: the cost story number %d" % n) for n in range(12)]
    target = mk.Item("t", "note", "account_history", "2026-01-05", "tokenizer quirks in the zorblax vocabulary broke our evaluation suite",
                     trace={"gist": "tokenizer quirks broke evaluation", "angle": "vocabulary drift continues", "open": "who owns the zorblax list"})
    mixed = mk.Item("m", "note", "account_history", "2026-01-06", "agents and models in production: the cost story of the quendel project")
    return mk.build_index(common + [target, mixed] + fillers(10), "2026-03-01")


def test_a_reference_is_supported_by_a_distinctive_shared_term_or_three_content_words_not_by_two_common_ones() -> None:
    index = agent_index()
    about_target = mk.retrieve(index, "tokenizer quirks zorblax vocabulary evaluation suite", "note", "2026-03-01", "lexical")
    about_common = mk.retrieve(index, "agents and models in production cost story quendel", "note", "2026-03-01", "lexical")
    assert ids(about_target) == ["t"] and "m" in ids(about_common) and "t" not in ids(about_common)
    flags = lambda result, text: mk.guard(result, text)["flags"]                                    # noqa: E731
    # a distinctive term (a word of one item in thirty-six) backs a reference alone
    assert flags(about_target, "As I wrote last week about tokenizer quirks, the point stands.") == []
    assert flags(about_common, "As I wrote last week about the quendel project, we shipped it.") == []
    # two common words do not (the review: 'agents and models' in an account about AI), three do
    assert flags(about_common, "As I wrote earlier about quantum lattices, agents and models matter here.") == ["unsupported_reference"]
    assert flags(about_common, "As I wrote earlier about the cost, we shipped it.") == ["unsupported_reference"]
    assert flags(about_common, "As I wrote earlier, agents and models in production are costly.") == []
    # the words of the reference phrase do not count: 'wrote last week' is in the item, 'quantum lattices' are not
    echo = mk.build_index([mk.Item("e", "note", "account_history", "2026-01-01", "The earlier post about ferries was a draft; last week I wrote a longer one.")] + fillers(20), "2026-03-01")
    echoed = mk.retrieve(echo, "earlier post about ferries draft longer", "note", "2026-03-01", "lexical")
    assert ids(echoed) == ["e"]
    assert flags(echoed, "As I wrote last week, quantum lattices are fun.") == ["unsupported_reference"]
    assert flags(echoed, "As I wrote last week about the ferries, the draft was longer.") == []
    # a reference with nothing to check is not unsupported; with nothing injected it is spurious
    assert flags(about_target, "As I wrote last week.") == [] and flags(about_target, "I covered this last month.") == []
    assert mk.guard(no_memory(), "As I wrote last week.") == {"ok": False, "flags": ["spurious_reference"], "callbacks": 1}
    # every reference sentence must be supported
    assert flags(about_target, "As I wrote last week about tokenizer quirks, the point stands. Last month I argued about quantum lattices.") == ["unsupported_reference"]
    assert mk.guard(about_target, "As I wrote last week about tokenizer quirks, the point stands. Last month I argued about quantum lattices.")["callbacks"] == 2
    # the words of the trace count too (three of them: no distinctive term is needed)
    assert flags(about_target, "As I wrote last week, drift continues across the board.") == ["unsupported_reference"]                      # two words of the trace: too few
    assert flags(about_target, "As I wrote last week, the drift continues and the owner of the list changes.") == []                      # three words of the trace
    # a result that carries no document frequencies (made by hand) is judged by the count of shared words alone
    by_hand = {"items": about_target["items"], "keys": about_target["keys"], "dates": about_target["dates"], "status": "ok", "task_type": "note", "n_index": 36}
    assert flags(by_hand, "As I wrote last week about tokenizer quirks, the point stands.") == ["unsupported_reference"]
    assert flags(by_hand, "As I wrote last week about tokenizer quirks in the zorblax vocabulary, the point stands.") == []
    # supported or not, a sentence that is not a reference raises nothing
    assert flags(about_target, "The model is small.") == [] and flags(about_common, "Quantum lattices are fun.") == []


def test_the_guard_flags_for_failed_and_degraded_results_and_never_adds_both_reference_flags() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    ref = "As I wrote last week about the ferry ledgers, the point stands."
    timeout = mk.retrieve(index, "tide tables", "note", "2026-12-01", {"timeout_ms": -1, "embed": "off"})
    error = mk.retrieve(None, "tide tables", "note", "2026-12-01", "lexical")                              # type: ignore[arg-type]
    degraded = mk.retrieve(mk.build_index(base_items(), "2026-12-01"), "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "hybrid")
    for result in (timeout, error):
        assert result["status"] in ("timeout", "error") and mk.guard(result, ref) == {"ok": False, "flags": ["spurious_reference"], "callbacks": 1}
        assert mk.guard(result, "Tides turn.") == {"ok": True, "flags": [], "callbacks": 0}
    assert degraded["status"] == "degraded" and ids(degraded) == ["n1"] and mk.guard(degraded, ref)["flags"] == []
    for result in (timeout, error, degraded):
        flags = mk.guard(result, ref)["flags"]
        assert not ({"spurious_reference", "unsupported_reference"} <= set(flags))


def test_the_guard_notices_an_altered_result_a_future_item_or_invented_autobiography_in_the_wrong_task() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    some = mk.retrieve(index, "tide tables and the ferry ledgers kept by my mother", "note", "2026-12-01", "lexical")
    assert mk.guard(dict(some, now_key="2026-01-01T00:00:00"), "Tides turn.")["flags"] == ["future_item"]
    assert mk.guard(dict(some, now_key="2026-09-01T00:00:00"), "Tides turn.")["flags"] == ["future_item"]            # at the instant: not before the task
    assert mk.guard(dict(some, now_key="2026-09-01T00:00:01"), "Tides turn.")["flags"] == []
    own = mk.retrieve(index, "where were you born, Kellmouth fishing town on a cold estuary", "personal", "2026-12-01", "lexical")
    assert mk.guard(own, "Born by the estuary.")["ok"] is True
    assert mk.guard(dict(own, task_type="note"), "Born by the estuary.")["flags"] == ["fiction_out_of_scope"]
    assert mk.guard(dict(own, task_type="note", persona_task_types=["note"]), "Born by the estuary.")["flags"] == []


def test_the_readme_describes_layout_interface_vendoring_changes_limits_and_the_tests() -> None:
    readme = (ROOT / "scripts" / "wmb" / "kernel" / "README.md").read_text(encoding="utf-8")
    for needle in ("0.1.0", "0.2.0", "frozen", "scripts/wmb/memory_kernel.py", "scripts/wmb/kernel/memory_kernel.py", "sha256", "VERSION", "BM25", "known limits", "pytest",
                   "tests/test_wmb_kernel_v2.py", "WMB_KERNEL_V2_FILE", "retrieve", "build_index", "render", "log_record", "guard", "calibrate"):
        assert needle.lower() in readme.lower(), needle


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Edges of the gates (every threshold is inclusive) and of the channel for names
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_every_threshold_of_the_lexical_gate_is_inclusive() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    # a word seen once meets min_evidence 1.0 exactly; a little more asks for a second word
    assert ids(mk.retrieve(index, "kitchen", "note", "2026-12-01", {"name": "t", "embed": "off", "min_evidence": 1.0})) == ["n1"]
    assert mk.retrieve(index, "kitchen", "note", "2026-12-01", {"name": "t", "embed": "off", "min_evidence": 1.0001})["items"] == []
    # with k1 = 1 and b = 0 one term, once, scores exactly half of its reference
    items = [mk.Item("a", "note", "account_history", "2026-01-01", "alpha pad1"), mk.Item("b", "note", "account_history", "2026-01-02", "gamma pad2"),
             mk.Item("c", "note", "account_history", "2026-01-03", "delta pad3")]
    small = mk.build_index(items, "2026-02-01")
    gate = lambda tau: mk.retrieve(small, "alpha", "note", "2026-02-01", {"name": "t", "embed": "off", "k1": 1.0, "b": 0.0, "lex_tau": tau, "min_evidence": 0.0})      # noqa: E731
    assert ids(gate(0.5)) == ["a"] and gate(0.5)["scores"] == [1.0] and gate(0.5)["channel_scores"][0]["lexical"] == 0.5 and gate(0.5000001)["items"] == []
    assert ids(gate(0.3)) == ["a"] and gate(0.3)["scores"] == [round(0.5 / 0.3, 4)]


def test_the_channel_for_names_has_a_minimum_length_a_rarity_limit_and_acronyms_of_three_letters() -> None:
    items = fillers(20) + [mk.Item("jo", "note", "account_history", "2026-02-01", "My friend Jo called me about the project"),
                           mk.Item("ann", "note", "account_history", "2026-02-02", "My friend Ann called me about the garden"),
                           mk.Item("llm", "note", "account_history", "2026-02-03", "LLM costs fell sharply. Other words follow here.")]
    index = mk.build_index(items, "2026-03-01")
    names = lambda q, **kw: ids(mk.retrieve(index, q, "personal", "2026-03-01", dict(NAMES_ONLY, **kw)))      # noqa: E731
    assert names("Who is Jo?") == [] and names("Who is Ann?") == ["ann"]                                  # two letters are no name, three are
    assert names("LLM?") == ["llm"] and names("llm?") == []                                               # three capitals at the start of a sentence are an acronym, not a position
    crowd = mk.build_index(fillers(20) + [mk.Item("p%d" % n, "note", "account_history", "2026-02-0%d" % (n + 1), "My friend Imre called about thing%d" % n) for n in range(3)], "2026-03-01")
    two = lambda **kw: sorted(ids(mk.retrieve(crowd, "Who is Imre?", "personal", "2026-03-01", dict(NAMES_ONLY, **kw))))      # noqa: E731
    assert two() == [] and two(rare_df=3) == ["p0", "p1", "p2"] and two(rare_df=2) == []                  # a name in three items is not rare at the default of two
    twice = mk.build_index(fillers(20) + [mk.Item("p%d" % n, "note", "account_history", "2026-02-0%d" % (n + 1), "My friend Imre called about thing%d" % n) for n in range(2)], "2026-03-01")
    assert sorted(ids(mk.retrieve(twice, "Who is Imre?", "personal", "2026-03-01", NAMES_ONLY))) == ["p0", "p1"]                    # but in two it is
    assert mk.retrieve(twice, "Who is Imre?", "personal", "2026-03-01", dict(NAMES_ONLY, names=False))["items"] == []


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# The bypasses that the review of 0.1.0 named, the text helpers that never raise, ties between equally rare words
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_trivial_bypasses_of_the_phrase_list_are_closed() -> None:
    empty = {"items": [], "status": "ok"}
    curly = "\N{RIGHT SINGLE QUOTATION MARK}"
    caught = (
        "LIKE I SAID LAST MONTH, the numbers are small.", "Like I said earlier, the numbers are small.", "like i said last month, the numbers are small.",
        "As I've said before, small models win.", "As I" + curly + "ve said before, small models win.", "AS I'VE SAID BEFORE, small models win.", "As I've said before, small models win.", "As I have said earlier, small models win.",
        "I keep saying that small models win.", "I KEEP SAYING that small models win.", "I keep on saying it" + curly + "s the data.",
        "A few weeks back I wrote that agents would stall.", "a few weeks back i wrote that agents would stall.", "A FEW WEEKS BACK I WROTE THAT AGENTS WOULD STALL.",
        "Regular readers will remember the saga.", "REGULAR READERS WILL REMEMBER THE SAGA.", "Regular  readers\N{NO-BREAK SPACE}will remember the saga.", "Our regular readers know the saga.",
        "As I wrote earlier this month, costs fell.", "As *I* wrote last week, costs fell.", "As I wrote\N{NO-BREAK SPACE}last week, costs fell.", "As I wr\N{ZERO WIDTH SPACE}ote last week, costs fell.",
    )
    for sentence in caught:
        assert mk.guard(empty, sentence) == {"ok": False, "flags": ["spurious_reference"], "callbacks": 1}, sentence
    # a bare stance phrase is conversation, not a reference (it needs an anchor: as I said last month, as I wrote earlier, as I argued in my last post)
    for sentence in ("LIKE I SAID, the numbers are small.", "Like I said, the numbers are small.", "As I've said, small models win.", "As I have said, small models win.",
                     "As I said, this is hard.", "Like I said, it works.", "As I was saying, the numbers are small.", "As I" + curly + "ve said, small models win."):
        assert mk.guard(empty, sentence)["callbacks"] == 0, sentence


def test_the_text_helpers_never_raise_and_when_keeps_its_contract_of_value_error() -> None:
    for odd in (None, 5, 5.5, b"bytes", ["a"], {"a": 1}, object()):
        assert mk.tokens(odd) == [] and mk.analyse(odd) == ([], set(), set(), set()) and mk.stem(odd) == "" and mk.item_id("note", "2026-01-01", odd) == "", odd      # type: ignore[arg-type]
    assert mk.tokens("\ud800 lone surrogate stays out of the words") == ["lone", "surrogate", "stay", "word"] and mk.stem("\ud800") == "\ud800"
    assert mk.item_id("note", "2026-01-01", "\ud800") == "" and mk.item_id("note", "2026-01-01", "text") == mk.item_id("note", "2026-01-01", "text")
    assert mk.item_id("note", "2026-01-01", "text").startswith("note-2026-01-01-") and len(mk.item_id("note", "2026-01-01", "text")) == len("note-2026-01-01-") + 8
    with pytest.raises(ValueError):
        mk.when(None)                                                                                  # a parser: the one function that says no by raising
    assert mk.render({"items": 5}) == "" and mk.calibrate(None, 5) is None                            # type: ignore[arg-type]


def test_equally_rare_words_are_chosen_by_their_place_in_the_query_in_every_process() -> None:
    ties = [mk.Item("t%02d" % n, "note", "account_history", "2025-01-%02d" % (n + 1), "rareword%02d filler%02d" % (n, n)) for n in range(12)]
    index = mk.build_index(ties, "2026-01-01")
    query = " ".join("rareword%02d" % n for n in reversed(range(12)))                           # rareword11 comes first
    for top in (1, 2, 3, 5):
        out = mk.retrieve(index, query, "note", "2026-01-01", dict(EVERYTHING, top_terms=top, max_terms=top))
        assert sorted(ids(out)) == ["t%02d" % n for n in range(12 - top, 12)], top              # the first `top` stems of the query, whatever their spelling (0.2.0 as first built chose the alphabetical first)
    narrow = mk.retrieve(index, query, "note", "2026-01-01", dict(EVERYTHING, top_terms=2, max_terms=3))
    assert sorted(ids(narrow)) == ["t09", "t10", "t11"] and [c["lexical"] for c in narrow["channel_scores"]] == [0.2273] * 3          # 1 / (2 * 2.2): one of two reference terms, once, average length
    forward = " ".join("rareword%02d" % n for n in range(12))
    assert sorted(ids(mk.retrieve(index, forward, "note", "2026-01-01", dict(EVERYTHING, top_terms=2, max_terms=2)))) == ["t00", "t01"]
    # many equally rare unknown-to-the-item words must not decide by spelling which words of the query are scored (a text with 45 such words and the 8 words of its source)
    source = mk.Item("src", "note", "account_history", "2025-02-01", " ".join("srcword%d" % n for n in range(8)))
    others = [mk.Item("o%02d" % n, "note", "account_history", "2025-03-%02d" % (1 + n % 28), "aanoise%02d zznoise%02d" % (n, n)) for n in range(45)]
    crowd = mk.build_index([source] + others, "2026-01-01")
    for spelling in ("aanoise%02d", "zznoise%02d"):
        noise = " ".join(spelling % n for n in range(45))
        query = " ".join("srcword%d" % n for n in range(8)) + " " + noise                       # the source words come first, 45 equally rare words after them
        assert ids(mk.retrieve(crowd, query, "note", "2026-01-01", "lexical")) == ["src"], spelling


# one sentence for each rule of the grammar, recognised by that rule and by no other: removing or breaking a rule loses its sentence
ONE_RULE_EACH = (
    "As I previously wrote, the vendor never answered.", "As I wrote earlier, costs fell.", "As previously reported, the vendor has not answered our questions.",
    "As mentioned previously, the benchmark has known contamination problems.", "I keep saying that small models are underrated.", "I always say that data quality beats volume.",
    "I have long argued that data curation matters more than architecture.", "When I wrote about long-context models in the spring, I underestimated the cost.",
    "I wrote a piece on exactly this a few months ago.", "I covered the same paper last month, and my reading has not changed.", "I wrote this in March, and little has changed.",
    "I already covered the licence change, so I will skip the details here.", "I wrote last week that costs would fall.", "Back in March I predicted that agent frameworks would consolidate.",
    "I said it before and I will say it again: do not trust a single benchmark number.", "My newsletter covered the launch in detail.", "In my newsletter I stressed that costs would fall.",
    "My last note on this was too optimistic.",
    "My notes from last month already flagged the licensing risk.", "My earlier argument still holds.", "In a previous post I described the harness in detail.",
    "Last week's newsletter promised a follow-up on evaluation, and this is it.", "This is a follow-up to the thread I started on Friday.", "Picking up what I wrote earlier, the numbers held.",
    "This is the same argument I made two months ago about inference prices.", "Regular readers will remember my doubts about fully autonomous coding agents.",
    "Readers of this account will know the drill.", "Readers who follow this feed will know my view.", "You may remember that I was sceptical of the first demo.",
    "Remember when I said the demo looked staged? It turned out I was right.", "As you may recall, the ledgers were lost.", "I owe you a follow-up to my post about scaling laws.",
)


def rules_matching(sentence: str) -> list:
    text = mk._normal(sentence)
    return [n for n, (pattern, private) in enumerate(mk._RULES) if pattern.search(text) and not (private and mk._PRIVATE_RE.search(text))]


def test_every_rule_of_the_grammar_has_a_sentence_that_only_it_recognises() -> None:
    owners = [rules_matching(s) for s in ONE_RULE_EACH]
    assert all(len(o) == 1 for o in owners), [(s, o) for s, o in zip(ONE_RULE_EACH, owners) if len(o) != 1]
    assert {o[0] for o in owners} == set(range(len(mk._RULES))) and len(mk._RULES) == len(mk.CALLBACKS) == len(ONE_RULE_EACH) == 32
    empty = {"items": [], "status": "ok"}
    assert all(mk.guard(empty, s) == {"ok": False, "flags": ["spurious_reference"], "callbacks": 1} for s in ONE_RULE_EACH)
    for private_audience in ("I mentioned this bug to the maintainers last week.", "I explained it to the team last month.", "We discussed the plan with three colleagues earlier."):
        assert mk.guard(empty, private_audience)["callbacks"] == 0                                    # the rules that read a verb of saying skip a talk with someone in private


def test_a_sentence_initial_query_word_that_is_an_ordinary_word_elsewhere_in_the_index_is_not_a_name() -> None:
    items = fillers(20) + [mk.Item("a", "note", "account_history", "2026-02-01", "My friend Ledger called me about the harbour"),
                           mk.Item("b", "note", "account_history", "2026-02-02", "The ledger entries were late again")]
    index = mk.build_index(items, "2026-03-01")
    assert mk.retrieve(index, "Ledger?", "personal", "2026-03-01", NAMES_ONLY)["items"] == []              # at the start of the query it may be the common noun that item b uses
    assert ids(mk.retrieve(index, "Who is Ledger?", "personal", "2026-03-01", NAMES_ONLY)) == ["a"]        # in the middle of a sentence the capital says it is a name
    assert mk.retrieve(index, "who is ledger?", "personal", "2026-03-01", NAMES_ONLY)["items"] == []
    assert mk.retrieve(index, "Ledger? Is it a ledger?", "personal", "2026-03-01", NAMES_ONLY)["items"] == []          # the query itself writes it with a small letter


def test_possessives_of_names_with_an_apostrophe_keep_the_name() -> None:
    assert mk.tokens("O'Neil's O'Brien d'Artagnan's") == ["o'neil", "o'brien", "d'artagnan"]
    assert mk.tokens("ands buts nors ifs") == ["ifs"]                                                   # the plural of a function word is none either (three-letter plurals stay as they are)


def test_an_acronym_in_the_plural_at_the_start_of_a_sentence_is_still_an_acronym() -> None:
    index = mk.build_index(fillers(20) + [mk.Item("g", "note", "account_history", "2026-02-01", "GPUs followed the launch. Other words follow here.")], "2026-03-01")
    assert ids(mk.retrieve(index, "GPUs?", "personal", "2026-03-01", NAMES_ONLY)) == ["g"]
    plain = mk.build_index(fillers(20) + [mk.Item("g", "note", "account_history", "2026-02-01", "Gpus followed the launch. Other words follow here.")], "2026-03-01")
    assert mk.retrieve(plain, "Gpus?", "personal", "2026-03-01", NAMES_ONLY)["items"] == []                      # a capital letter that the start of a sentence explains


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# The slow tests come last: determinism across processes, hostile text, and the limits of the contract at two thousand items
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_slow_embedder_cannot_be_interrupted_but_the_call_ends_as_a_timeout_when_it_returns() -> None:
    delay = {"s": 0.0}

    def slow(texts):
        time.sleep(delay["s"])
        return bow_embedder()(texts)

    index = mk.build_index(base_items(), "2026-12-01", slow)
    delay["s"] = 0.08
    started = time.perf_counter()
    out = mk.retrieve(index, SYNONYM_QUERY, "note", "2026-12-01", {"timeout_ms": 20, "embed": "auto"})
    assert out["status"] == "timeout" and out["items"] == [] and out["error"] == "deadline exceeded" and time.perf_counter() - started < 5
    delay["s"] = 0.0
    assert ids(mk.retrieve(index, SYNONYM_QUERY, "note", "2026-12-01", {"timeout_ms": 5000, "embed": "auto"})) == ["n1"]

DETERMINISM_SCRIPT = textwrap.dedent('''
    import importlib.util, json, random, sys
    spec = importlib.util.spec_from_file_location("kernel_under_test", sys.argv[1])
    mk = importlib.util.module_from_spec(spec); sys.modules["kernel_under_test"] = mk; spec.loader.exec_module(mk)
    rng = random.Random(5)
    vocab = ["Wd%03d" % n if n % 9 == 0 else "wd%03d" % n for n in range(500)]
    texts = [" ".join(rng.choices(vocab, [1.0 / (n + 1) for n in range(500)], k=rng.randint(10, 70))) for _ in range(250)]
    items = [mk.Item("i%03d" % n, "note", "account_history", "2025-%02d-%02d" % (1 + n % 12, 1 + n % 28), t) for n, t in enumerate(texts)]
    items += [mk.Item("e%d" % n, "event", "fiction_autobio", "1990-01-0%d" % (n + 1), "Wd%03d lived in Wd%03d" % (9 * n, 9 * n + 9)) for n in range(5)]
    index = mk.build_index(items, "2026-12-31")
    out = []
    for q in range(40):
        query = " ".join(rng.choices(vocab, [1.0 / (n + 1) for n in range(500)], k=rng.choice([2, 6, 15, 40])))
        for task, profile in (("note", "lexical"), ("personal", "lexical"), ("note", {"name": "wide", "k": 6, "embed": "off", "lex_tau": 0.05})):
            r = mk.retrieve(index, query, task, "2026-12-31", profile)
            rec = mk.log_record(r, lambda t: "h" + str(len(t)))
            rec.pop("latency_ms"); rec.pop("query_hmac")
            out.append([[i.id for i in r["items"]], r["scores"], r["channel_scores"], r["reasons"], r["n_candidates"], r["n_considered"], mk.render(r), rec,
                        mk.guard(r, "As I wrote last week about " + query[:30])])
    ties = [mk.Item("t%02d" % n, "note", "account_history", "2025-01-%02d" % (n + 1), "rareword%02d filler%02d" % (n, n)) for n in range(12)]
    tied = mk.build_index(ties, "2026-01-01")
    for top in (1, 2, 3, 5):
        r = mk.retrieve(tied, " ".join("rareword%02d" % n for n in range(12)), "note", "2026-01-01",
                        {"name": "ties", "embed": "off", "names": False, "lex_tau": 1e-6, "min_evidence": 0.0, "top_terms": top, "max_terms": top, "k": 20})
        out.append([[i.id for i in r["items"]], r["scores"], r["channel_scores"]])
    print(json.dumps(out, sort_keys=True))
''')

def test_the_result_is_the_same_in_processes_with_different_hash_seeds() -> None:
    outputs = {}
    for seed in ("0", "1", "2", "123", "99999", "random"):
        run = subprocess.run([sys.executable, "-c", DETERMINISM_SCRIPT, str(SOURCE)], capture_output=True, text=True, timeout=120, env=dict(os.environ, PYTHONHASHSEED=seed))
        assert run.returncode == 0, run.stderr[-500:]
        outputs[seed] = run.stdout
    assert len(set(outputs.values())) == 1 and json.loads(outputs["0"]) and any(row[0] for row in json.loads(outputs["0"]))

def test_the_guard_never_raises_and_is_fast_on_hostile_text() -> None:
    result = mk.retrieve(mk.build_index(base_items(), "2026-12-01"), "tide tables ferry", "note", "2026-12-01", "lexical")
    for odd in (None, "", " ", "\x00", "\ud800", "I" * 10 ** 5, 5, b"as I wrote", ["As I wrote last week."], {"a": 1}):
        verdict = mk.guard(result, odd)                                                            # type: ignore[arg-type]
        assert set(verdict) == {"ok", "flags", "callbacks"}
    for odd in (None, 5, "x", [], {"items": 5}, {"items": [None]}, {"items": [mk.Item("a", "note", "robot", "bad", None)]}):
        assert set(mk.guard(odd, "As I wrote last week.")) == {"ok", "flags", "callbacks"}          # type: ignore[arg-type]
    hostile = ["i " * 50000, "I wrote " * 10000, " ".join(["last week"] * 20000), "I have been " * 20000, "I already also once previously first even just " * 5000, "my " * 100000,
               "I said " + "word " * 40000 + "last", "I mentioned " + "x " * 40000 + "to the", "as i " + "have " * 30000, "the " * 100000 + "post i wrote", "readers who " * 30000,
               "you will " * 30000 + "remember", "I wrote about this last week. " * 5000, "a" * 500000]
    started = time.perf_counter()
    for text in hostile:
        mk.guard(result, text)
    assert time.perf_counter() - started < 20

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Limits of the contract
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
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
    wall = time.perf_counter()
    for q in queries[:40]:
        mk.retrieve(index, q, "note", "2026-12-31", "lexical")
    assert (time.perf_counter() - wall) / 40 < 0.3                                                   # the self-reported latency is not the only witness
    long_query = " ".join(random.Random(2).choices(["wd%04d" % n for n in range(4000)], k=3300))[:mk.MAX_QUERY_CHARS + 500]
    started = time.perf_counter()
    assert mk.retrieve(index, long_query, "note", "2026-12-31", "lexical")["status"] == "ok" and time.perf_counter() - started < 1.0       # a query of 20 000 characters and more

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


def test_long_items_and_long_queries_stay_within_the_limits() -> None:
    rng = random.Random(9)
    vocab = ["lw%04d" % n for n in range(6000)]
    weights = [1.0 / (rank + 1) ** 0.9 for rank in range(len(vocab))]
    items = [mk.Item("l%04d" % n, "note", "account_history", "2025-%02d-%02d" % (1 + n % 12, 1 + n % 28), " ".join(rng.choices(vocab, weights, k=330))) for n in range(1000)]
    assert min(len(i.text) for i in items) > 1900                                                          # items of about two thousand characters
    index = mk.build_index(items, "2026-12-31")
    assert index.built_ms < 2000 and len(index.items) == 1000
    queries = [" ".join(rng.choices(vocab, weights, k=rng.choice([10, 60, 400, 3000]))) for _ in range(60)]
    latencies = sorted(mk.retrieve(index, q, "note", "2026-12-31", "lexical")["latency_ms"] for q in queries)
    assert latencies[int(0.95 * len(latencies))] < 300 and all(mk.retrieve(index, q, "note", "2026-12-31", "lexical")["status"] == "ok" for q in queries[:10])


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Regressions: the defects that two independent verifiers found in the first build of 0.2.0 (V-nn: finding-by-finding verification, H-nn: adversarial hardening)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
HARD_NEGATIVES = (
    "Subscribe to my newsletter for more.", "Thanks for reading my newsletter.", "This is my post for today.", "Our newsletter goes out on Fridays.", "I've been writing tests all morning.",
    "I keep writing the same loop.", "I have been telling the team to wait.", "As I said, this is hard.", "Like I said, it works.", "As I was saying, the numbers are small.",
    "Welcome back, regular readers!", "In 2019 I wrote my first neural network.", "Last week I wrote a quick script to parse the logs.", "I once wrote a compiler for fun.",
    "I posted it on Monday morning, then went offline.", "I wrote about 40 lines of Python before lunch.", "I wrote about 12 pages of notes this week.", "I wrote about 4 lines of Python before lunch.",
    "I wrote a lot of code last week and my wrists hurt.", "Last week I wrote my first unit test in Rust.", "My last thread of the day got stuck on a mutex.",
    "The previous issue tracker had no labels.", "I reviewed the pull request last week.", "I covered for a colleague last week.", "Last week I posted the letter to the council.",
    "We reported the bug upstream last month.", "I discussed the budget with finance on Tuesday.", "My first note to self: back up the data.", "I wrote it in an afternoon.",
    "I wrote my thesis in 2019.", "Over the weekend I wrote a parser.", "In my previous role I led a platform team.", "My earlier career was in finance.",
)
HARD_POSITIVES = (
    "As I said last month, costs fell.", "My newsletter covered this twice, and I stand by it.", "My post on benchmarks argued otherwise.", "In my newsletter I argued that costs would fall.",
    "I covered this in my last newsletter, and the short version is below.", "As I wrote in my previous post, the first paragraph above still holds.",
    "My last newsletter covered this; here is the short version so far.", "I argued in an earlier post that agents stall, and the next section shows why.",
    "I wrote about this in my essay on scaling, which I summarise at the end.", "We discussed this in the October issue, and the numbers have only gotten better since.",
    "As promised in Tuesday's issue, here is the full breakdown of the pricing change.", "I made this argument at length in a post about scaling laws.",
    "This is a continuation of the theme from my last three issues.", "Past issues of this newsletter argued otherwise.", "You may remember the tide tables.",
    "As you may recall, the ledgers were lost.", "You will remember the ledger saga.", "Long-time followers of the account will have heard this from me before.",
    "Some of you asked me about this after my post on agents.", "I first wrote about this two years ago.", "Regular readers know the saga.",
)


def test_conversation_and_acts_of_making_are_not_references_but_the_references_next_to_them_are_still_found() -> None:
    empty = {"items": [], "status": "ok"}
    assert [s for s in HARD_NEGATIVES if mk.guard(empty, s)["callbacks"]] == []               # V-01, V-18 and the near-misses of H-24: the first build flagged 21 of 49 such sentences
    assert [s for s in HARD_POSITIVES if mk.guard(empty, s)["callbacks"] != 1] == []
    assert mk.guard(empty, "You may recall that the first transformer was built for translation.")["callbacks"] == 0        # a that-clause of world knowledge stays out
    assert bank_flags(["As I wr\u043ete last week, costs fell.", "As I wr\u03bfte last week, costs fell.", "AS I WR\u041eTE LAST WEEK, costs fell."]) == 3     # Cyrillic and Greek look-alikes of Latin letters
    assert bank_flags(["As I wrote&nbsp;last&nbsp;week, the gap is closing.", "As I wrote&#160;last&#160;week, the gap is closing."]) == 2           # the entity of a non-breaking space, copied as text
    assert bank_flags([s.replace("wrote", "wr\u200bote") for s in HARD_POSITIVES]) == len(HARD_POSITIVES)


def test_a_reference_to_the_text_cancels_only_its_own_clause() -> None:
    empty = {"items": [], "status": "ok"}
    # H-04 (a): a real back-reference whose sentence also says below, above, so far, at the end, the next section
    for sentence in ("I covered this in my last newsletter, and the short version is below.", "As I wrote in my previous post, the first paragraph above still holds.",
                     "My last newsletter covered this; here is the short version so far.", "I wrote about this in my essay on scaling, which I summarise at the end.",
                     "I argued in an earlier post that agents stall, and the next section shows why."):
        assert mk.guard(empty, sentence)["callbacks"] == 1, sentence
    # H-04 (b): a reference to the text being written whose sentence also has an ordinary time word about the world
    for sentence in ("As I said above, the launch last week changed the pricing.", "As I noted in the previous section, the company announced layoffs yesterday.",
                     "As I said at the top, the deal closed in March.", "As I wrote earlier in this note, the outage lasted two hours yesterday."):
        assert mk.guard(empty, sentence)["callbacks"] == 0, sentence


def test_world_knowledge_does_not_back_a_reference_to_what_the_author_wrote() -> None:
    world = mk.Item("w", "note", "world_knowledge", "2020-01-01", "harbour ferry timetable ledger kept in the kitchen")
    own = mk.Item("a", "note", "account_history", "2026-01-01", "tokenizer quirks in the zorblax vocabulary")
    index = mk.build_index([world, own] + fillers(20), "2026-06-01")
    only_world = mk.retrieve(index, "harbour ferry timetable ledger kitchen", "note", "2026-06-01", "lexical")
    assert ids(only_world) == ["w"]
    ref = "As I wrote last week, the harbour ferry timetable ledger lived in the kitchen."
    assert mk.guard(only_world, ref) == {"ok": False, "flags": ["spurious_reference"], "callbacks": 1}         # V-13: nothing of the account's own was injected
    assert mk.guard(only_world, "The harbour ferry timetable ledger lived in the kitchen.")["flags"] == []
    both = mk.retrieve(index, "harbour ferry timetable ledger kitchen tokenizer quirks zorblax vocabulary", "note", "2026-06-01", "lexical")
    assert set(ids(both)) == {"w", "a"}
    assert mk.guard(both, ref)["flags"] == ["unsupported_reference"]                                           # only the world item shares those words
    assert mk.guard(both, "As I wrote last week about the zorblax vocabulary, the point stands.")["flags"] == []


def test_calibrate_says_none_when_it_cannot_calibrate_and_the_gates_refuse_a_threshold_of_zero() -> None:
    items = [mk.Item("c%d" % k, "note", "account_history", "2026-09-%02d" % (k + 1), "topic%d alpha%d beta%d gamma%d words about subject%d" % (k, k, k, k, k)) for k in range(10)]
    plain = mk.build_index(items, "2026-12-01")
    queries = [("topic%d alpha%d beta%d gamma%d" % (k, k, k, k), "2026-10-01") for k in range(3)]
    assert mk.calibrate(plain, queries, 0.2, "lexical") is not None
    assert mk.calibrate(plain, queries, 0.2, "embedding") is None                    # H-02: no embedder, so nothing to calibrate; the first build said 0.0, a threshold that lets every item through
    for channel in ("bogus", None, "", 5):
        assert mk.calibrate(plain, queries, 0.2, channel) is None, channel
    assert mk.calibrate(plain, [("zzzunknown yyyunknown", "2026-10-01")] * 10, 0.2) is None                # no query has any candidate
    for share in (2, -1, float("nan"), "x", None, 1.0001):
        assert mk.calibrate(plain, queries, share) is None, share
    assert mk.calibrate(plain, queries, 0, "lexical") is not None and mk.calibrate(plain, queries, 1, "lexical") is not None
    with_vectors = mk.build_index(items, "2026-12-01", bow_embedder())
    assert mk.calibrate(with_vectors, queries, 0.2, "embedding") > 0
    # the thresholds that would switch a gate off are errors of the profile
    for bad in ({"tau": 0.0}, {"tau": -1}, {"tau": None}, {"lex_tau": 0}, {"lex_tau": -0.1}, {"lex_tau": None}):
        out = mk.retrieve(with_vectors, "topic1 alpha1 beta1 gamma1", "note", "2026-12-01", bad)
        assert out["status"] == "error" and out["items"] == [] and next(iter(bad)) in out["error"], bad          # the error names the key (not a ZeroDivisionError further down)
    assert mk.calibrate(with_vectors, queries, 0.2, "lexical", {"tau": 0}) is None
    # calibrate applies the floor of evidence like retrieve: a query that shares one rare word with an item is no candidate by default, and is with min_evidence 0.8
    one = [("topic1 zzzunknown", "2026-12-01")]
    assert mk.calibrate(plain, one, 0.0, "lexical") is None
    assert mk.calibrate(plain, one, 0.0, "lexical", ONE_WORD) > 0


def test_a_lone_surrogate_or_a_control_character_cannot_lose_the_record_or_break_the_prompt() -> None:
    bad = chr(0xD83D)                                                                  # half of an emoji, typical of a text truncated in UTF-16
    index = mk.build_index([mk.Item("a" + bad, "note", "account_history", "2026-03-01", "zorplax quentin " + bad + " frimble\x00\x1b[31m sprocket")] + fillers(20), "2026-12-31")
    result = mk.retrieve(index, "zorplax quentin frimble sprocket " + bad, "note", "2027-01-01", "lexical")
    assert ids(result) == ["a" + bad]

    def utf8_hmac(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]                    # the usual keyed hash: it cannot encode a lone surrogate

    record = mk.log_record(result, utf8_hmac, raw_ids=True)
    assert record["status"] == "ok" and len(record["item_hmacs"]) == 1 and record["query_hmac"] and record["reasons"] == [["lexical"]]      # H-03: the record is not lost
    assert mk.log_record(result, utf8_hmac, key="task-1")["query_hmac"] == utf8_hmac("task-1")
    json.dumps(record)
    text = mk.render(result)
    text.encode("utf-8")                                                               # the prompt can be encoded
    assert "\ufffd" in text and bad not in text and "\x00" not in text and "\x1b" not in text and len(text.splitlines()) == 1


def test_scripts_with_combining_marks_are_words_and_invisible_characters_do_not_split_them() -> None:
    hindi, thai, hebrew, arabic = "\u0939\u093f\u0928\u094d\u0926\u0940 \u092d\u093e\u0937\u093e", "\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35 \u0e04\u0e23\u0e31\u0e1a", "shalom \u05e9\u05b8\u05c1\u05dc\u05d5\u05b9\u05dd", "\u0643\u0650\u062a\u064e\u0627\u0628"
    for text in (hindi, thai, hebrew, arabic):
        assert mk.tokens(text) == [unicodedata.normalize("NFC", word) for word in text.split()], text                  # V-10 and H-17: whole words, none lost, none cut at a vowel sign
    assert mk.tokens("co\u200boperate with the team") == ["cooperate", "team"] == mk.tokens("co\u00adoperate with the team") == mk.tokens("co\u200doperate with the team")
    assert mk.tokens("Mu\u0308ller") == mk.tokens("M\u00fcller") == ["m\u00fcller"]
    index = mk.build_index([mk.Item("h", "note", "account_history", "2026-02-01", hindi + " \u0938\u0940\u0916\u0928\u093e")] + fillers(20), "2026-03-01")
    assert ids(mk.retrieve(index, hindi, "note", "2026-03-01", "lexical")) == ["h"]


def test_stop_words_that_are_names_months_or_acronyms_when_capitalised_are_kept_there() -> None:
    assert mk.tokens("US export controls on GPUs") == ["us", "export", "control", "gpu"]                  # V-17: the only distinguishing word of a note about the US
    assert mk.tokens("tell us about it, it may rain") == ["tell", "rain"]
    assert mk.tokens("Yoko Ono sang in May") == ["yoko", "ono", "sang", "may"] and mk.tokens("May I ask? Ten ways to win") == ["ask", "way", "win"]
    index = mk.build_index([mk.Item("u", "note", "account_history", "2026-02-01", "US export controls tighten again"), mk.Item("v", "note", "account_history", "2026-02-02",
                                                                                                                          "Please tell us what you think")] + fillers(20), "2026-03-01")
    assert ids(mk.retrieve(index, "new US export controls", "note", "2026-03-01", "lexical")) == ["u"]


def test_irregular_plurals_fold_to_their_singular() -> None:
    for singular, plural in (("quiz", "quizzes"), ("hero", "heroes"), ("potato", "potatoes"), ("wolf", "wolves"), ("knife", "knives"), ("wife", "wives"), ("shelf", "shelves"),
                             ("person", "people"), ("man", "men"), ("woman", "women"), ("tooth", "teeth"), ("goose", "geese"), ("echo", "echoes"), ("thief", "thieves")):
        assert mk.stem(singular) == mk.stem(plural), (singular, plural)


def test_dates_raise_only_value_error_and_accept_zones_with_seconds() -> None:
    class Odd:
        def isoformat(self):
            return 5

    class Boom:
        def isoformat(self):
            raise RuntimeError("no")

    for bad in (Odd(), Boom()):
        with pytest.raises(ValueError):                                                # H-09: not AttributeError, not RuntimeError
            mk.when(bad)
        with pytest.raises(ValueError):
            mk.build_index([], bad)
    odd_zone = timezone(timedelta(hours=5, minutes=53, seconds=28))                    # H-10: a historical offset of a local mean time
    assert mk.when(datetime(2026, 1, 1, 12, tzinfo=odd_zone)) == "2026-01-01T06:06:32" == mk.when("2026-01-01T12:00:00+05:53:28") == mk.when("2026-01-01T12:00:00+055328")
    index = mk.build_index([mk.Item("a", "note", "account_history", datetime(2026, 1, 1, 12, tzinfo=odd_zone), "alpha bravo charlie")], "2026-12-31")
    assert index.rejected["invalid"] == 0 and "a" in index.items
    for bad in ("2026-01-01T12:00:00+05:53:60", "2026-01-01T12:00:00+24:00:00", "2026-01-01T12:00:00+05:53:28:00"):
        with pytest.raises(ValueError):
            mk.when(bad)


def test_a_mistyped_profile_key_or_an_unsafe_value_is_an_error_not_a_silent_default() -> None:
    index = mk.build_index(base_items() + fillers(10), "2026-12-01")
    for bad in ({"lex_taus": 0.99}, {"min_evidance": 99}, {"lex_thau": 0.99}, {"k1": 1e308}, {"k1": 101}, {"k1": -1}, {"len_cap": -1}, {"len_cap": float("inf")}, {"timeout_ms": "x"}, {"names": 1, "bogus": 2}):
        out = mk.retrieve(index, "tide tables kitchen ferry", "note", "2026-12-01", dict(bad, embed="off"))
        assert out["status"] == "error" and out["items"] == [] and out["error"], bad
    assert "lex_taus" in mk.retrieve(index, "tide tables", "note", "2026-12-01", {"lex_taus": 0.99})["error"]
    assert mk.retrieve(index, "tide tables kitchen ferry", "note", "2026-12-01", dict(LEXICAL_ONLY, len_cap=0, k1=100.0))["status"] == "ok"
    assert mk.calibrate(index, [("tide tables", "2026-12-01")], 0.2, "lexical", {"lex_taus": 1}) is None


def test_a_now_without_a_zone_can_be_refused() -> None:
    index = mk.build_index(base_items(), "2026-12-01")
    strict = dict(LEXICAL_ONLY, require_zone=True)
    q = "tide tables and the ferry ledgers kept by my mother"
    for naive in (datetime(2026, 12, 1, 12, 0), "2026-12-01T12:00:00", "2026-12-01", date(2026, 12, 1), None):
        out = mk.retrieve(index, q, "note", naive, strict)                              # V-12: a naive datetime.now() of a machine ahead of UTC would show items from the future of the real clock
        assert out["status"] == "error" and "zone" in out["error"] and out["items"] == [], naive
    for aware in (datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc), "2026-12-01T12:00:00Z", "2026-12-01T12:00:00+01:00", "2026-12-01T12:00:00-0500"):
        assert mk.retrieve(index, q, "note", aware, strict)["status"] == "ok" and ids(mk.retrieve(index, q, "note", aware, strict)) == ["n1"], aware
    assert ids(mk.retrieve(index, q, "note", datetime(2026, 12, 1, 12, 0), LEXICAL_ONLY)) == ["n1"] and mk.PROFILES["kernel"]["require_zone"] is False


def test_render_shows_the_date_an_item_was_written_with_and_the_dates_of_a_result_stay_utc() -> None:
    items = fillers(15) + [mk.Item("y", "note", "account_history", "2025", "zorplax quentin frimble"), mk.Item("m", "note", "account_history", "2026-09", "zorplax quentin sprocket"),
                           mk.Item("z", "note", "account_history", "2026-09-10T23:30:00-05:00", "zorplax quentin gadget")]
    index = mk.build_index(items, "2027-01-01")
    out = mk.retrieve(index, "zorplax quentin frimble sprocket gadget", "note", "2027-01-01", dict(LEXICAL_ONLY, k=10, lex_tau=0.05))
    assert set(ids(out)) == {"y", "m", "z"}
    assert mk.render(out, mode="raw").splitlines() == ["[2025] zorplax quentin frimble", "[2026-09] zorplax quentin sprocket", "[2026-09-10] zorplax quentin gadget"]       # V-14: no invented day, no shifted day
    assert "2026-09-11" in out["dates"] and "2025-01-01" in out["dates"]               # the log and the sort keep the UTC key
    # a key that disagrees with the item (an altered result) wins, as before
    altered = dict(out, keys=["2024-02-02T00:00:00"] * 3)
    assert mk.render(altered, mode="raw").count("[2024-02-02]") == 3


def test_the_log_record_shows_a_feed_that_was_rejected_whole_and_the_version_of_the_unicode_tables() -> None:
    items = [mk.Item("a", "tweet", "account_history", "2026-01-01", "bad kind"), mk.Item("b", "note", "account_history", "not a date", "x1 text"),
             mk.Item("c", "note", "account_history", "2099-01-01", "from the future"), mk.Item("d", "note", "account_history", "2026-01-01", "  ")]
    out = mk.retrieve(mk.build_index(items, "2026-06-01"), "anything", "note", "2026-06-01", "lexical")
    record = mk.log_record(out, hmac_fn)
    assert out["status"] == "ok" and record["n_index"] == 0 and record["rejected"] == {"future": 1, "invalid": 3, "duplicate": 0}                 # V-15: the empty index is visible as a broken feed
    assert record["unicode"] == unicodedata.unidata_version and json.loads(json.dumps(record)) == record


def test_an_iterable_of_items_that_fails_midway_leaves_a_degraded_index_not_an_empty_memory() -> None:
    def feed():
        yield mk.Item("a", "note", "account_history", "2026-03-01", "zorplax quentin frimble")
        raise RuntimeError("the cursor died")

    index = mk.build_index(feed(), "2026-12-31")
    assert list(index.items) == ["a"] and index.source_error == "items could not be read: RuntimeError" and index.rejected["invalid"] == 1 and index.degraded == ""
    out = mk.retrieve(index, "zorplax quentin frimble", "note", "2027-01-01", ONE_WORD)
    assert out["status"] == "degraded" and out["error"] == index.source_error and ids(out) == ["a"]                                     # H-20: the items that were read still answer
    assert mk.log_record(out, hmac_fn)["status"] == "degraded"


def test_the_task_type_and_the_query_in_the_result_and_the_log_are_json_whatever_was_passed() -> None:
    index = mk.build_index(base_items(), "2026-12-31")
    for odd in ({"a"}, float("nan"), b"note", object(), 5, ("personal",)):
        out = mk.retrieve(index, "Zebulon Quillfeather", odd, "2027-01-01", "lexical")                 # H-07
        assert isinstance(out["task_type"], str) and out["status"] == "ok"
        json.dumps(mk.log_record(out, hmac_fn), allow_nan=False)
    long_query = "alpha " * 5000 + "TAILMARK"
    good = mk.retrieve(index, long_query, "note", "2027-01-01", "lexical")
    broken = mk.retrieve(index, long_query, "note", "2027-01-01", {"k1": float("nan")})
    assert good["status"] == "ok" and broken["status"] == "error" and len(good["_query"]) == len(broken["_query"]) == mk.MAX_QUERY_CHARS       # H-16: cut once, on every path
    assert mk.log_record(good, hmac_fn)["query_hmac"] == mk.log_record(broken, hmac_fn)["query_hmac"]
    ok = mk.retrieve(mk.build_index(base_items(), "2026-12-31"), "tide tables ferry ledgers mother kitchen", "note", "2027-01-01", "lexical")
    assert list(ok["_df"]) == sorted(ok["_df"]) and ok["_df"]                                       # H-21: no order that depends on the hash seed


def test_a_long_item_with_all_the_words_of_a_short_query_passes_the_gate() -> None:
    rng = random.Random(1)
    words = ["w%04d" % n for n in range(3000)]
    short = [mk.Item("s%d" % i, "note", "account_history", "2026-01-01", " ".join(rng.sample(words, 20))) for i in range(300)]
    rare = ["qzr%d" % n for n in range(10)]
    query = " ".join(rare)
    for length in (30, 60, 130, 210, 410, 810):                                        # H-01: 1.5 to 40 times the average length
        essay = mk.Item("essay", "note", "account_history", "2026-02-01", " ".join(rare + rng.sample(words, length - 10)))
        index = mk.build_index(short + [essay], "2026-06-01")
        out = mk.retrieve(index, query, "note", "2026-06-01", "lexical")
        assert ids(out) == ["essay"] and out["channel_scores"][0]["lexical"] >= 0.2, length
        if length >= 410:                                                              # without the cap, plain BM25 length normalisation puts it far under the threshold
            plain = mk.retrieve(index, query, "note", "2026-06-01", dict(LEXICAL_ONLY, len_cap=0))
            assert plain["items"] == [] and mk.retrieve(index, query, "note", "2026-06-01", dict(LEXICAL_ONLY, len_cap=0, lex_tau=0.01))["channel_scores"][0]["lexical"] < 0.1, length
    # the cap makes a long item at most as good as one of len_cap times the average length: it never beats a shorter item that has the same words
    short_hit = mk.Item("hit", "note", "account_history", "2026-02-02", " ".join(rare + rng.sample(words, 10)))
    both = mk.build_index(short + [essay, short_hit], "2026-06-01")
    assert ids(mk.retrieve(both, query, "note", "2026-06-01", "lexical")) == ["hit", "essay"]


def test_the_score_is_bounded_by_the_ratio_of_the_scored_terms_to_the_reference_terms() -> None:
    twenty = ["rarew%02d" % n for n in range(20)]
    long_fillers = [mk.Item("f%03d" % n, "note", "account_history", "2026-01-01", " ".join("fw%03d_%02d" % (n, j) for j in range(60))) for n in range(100)]       # longer than the item
    index = mk.build_index([mk.Item("t", "note", "account_history", "2026-01-01", " ".join(twenty))] + long_fillers, "2026-06-01")
    for profile, bound in ((LEXICAL_ONLY, 2.0), (dict(LEXICAL_ONLY, top_terms=5, max_terms=20), 4.0), (dict(LEXICAL_ONLY, top_terms=0, max_terms=0), 1.0), (dict(LEXICAL_ONLY, top_terms=1, max_terms=3), 3.0)):
        out = mk.retrieve(index, " ".join(twenty), "note", "2026-06-01", dict(profile, lex_tau=0.01))
        s = out["channel_scores"][0]["lexical"]
        assert 0 < s <= bound + 1e-9, (profile, s)                                     # H-05: s can exceed 1, by at most max_terms / top_terms
    assert mk.retrieve(index, " ".join(twenty), "note", "2026-06-01", dict(LEXICAL_ONLY, lex_tau=0.01))["channel_scores"][0]["lexical"] > 1.0


def test_the_four_edges_that_the_mutation_check_found_unpinned() -> None:
    items = [mk.Item("v", "note", "account_history", "2026-01-01", "alpha bravo"), mk.Item("w", "note", "account_history", "2026-01-02", "charlie delta"),
             mk.Item("x", "note", "account_history", "2026-01-03", "echo foxtrot")]
    vectors = {"v": [1.0, 0.0], "w": [0.8, 0.6], "x": [0.0, 1.0]}
    index = mk.build_index(items, "2026-02-01", embedder=lambda texts: [[1.0, 0.0] for _ in texts], vectors=vectors)
    gate = lambda **kw: mk.retrieve(index, "zzz", "note", "2026-02-01", dict({"name": "e", "embed": "auto", "lex_tau": 1e6}, **kw))      # noqa: E731  the fake embedder answers [1, 0]
    assert ids(gate(tau=1.0)) == ["v"] and gate(tau=1.0)["scores"] == [1.0]                      # the cosine gate is inclusive: cos 1.0 meets tau 1.0 ...
    assert gate(tau=1.0000001)["items"] == []                                                       # ... and not a hair above
    ranked = gate(tau=0.5, k=5)
    assert ids(ranked) == ["v", "w"] and ranked["scores"] == [2.0, 1.6]                            # the strength of the embedding channel is cos / tau, nothing more
    del index.vectors["w"]                                                                         # an item without a vector, in an index that has some
    mixed = mk.retrieve(index, "charlie delta", "note", "2026-02-01", dict(ONE_WORD, embed="auto", tau=0.5, min_evidence=0.0, lex_tau=0.05))
    assert ids(mixed) == ["w", "v"] and mixed["channel_scores"][0] == {"lexical": mixed["channel_scores"][0]["lexical"], "embedding": None} and mixed["reasons"][0] == ["lexical"]
    # a colon, a semicolon and an ellipsis end a sentence: a capital after them proves nothing, in the item as in the query
    for text in ("Update: Zsofia moved to Lisbon.", "Done; Zsofia moved to Lisbon.", "Done\u2026 Zsofia moved to Lisbon."):
        names = mk.build_index(fillers(20) + [mk.Item("u", "note", "account_history", "2026-02-01", text)], "2026-03-01")
        assert mk.retrieve(names, "Zsofia?", "personal", "2026-03-01", NAMES_ONLY)["items"] == [], text
        assert ids(mk.retrieve(names, "Who is Zsofia?", "personal", "2026-03-01", NAMES_ONLY)) == ["u"], text           # the query shows the capital in the middle of a sentence: a name
        assert ids(mk.retrieve(names, "Zsofia?", "personal", "2026-03-01", ONE_WORD)) == ["u"], text                   # and the lexical channel finds the word either way


def test_long_tokens_stay_out_of_the_caches_and_long_texts_are_cut() -> None:
    before = (mk._stem.cache_info().currsize, mk._root.cache_info().currsize)
    mk.tokens(" ".join("x" * 100 + str(n) for n in range(500)))                                      # H-13: 500 distinct tokens of 100 characters
    assert (mk._stem.cache_info().currsize, mk._root.cache_info().currsize) == before
    mk.tokens("distinctshortword")
    assert mk._root.cache_info().currsize > before[1]
    started = time.perf_counter()
    heavy = "zorplax " + ("a\u0323\u0301") * 60000                                                  # H-14: 180 000 characters of combining marks; normalising them whole is quadratic
    index = mk.build_index([mk.Item("a", "note", "account_history", "2026-03-01", heavy)], "2026-12-31")
    mk.guard({"items": [], "status": "ok"}, heavy)
    assert time.perf_counter() - started < 5 and len(index.items) == 1
    words = mk.tokens("alpha " * 20000 + "omega")
    assert "omega" not in words and len(words) <= mk.MAX_TEXT_CHARS // 6 + 1                       # nothing beyond MAX_TEXT_CHARS is read
    padded = "Filler sentence number one. " * 3000 + "As I wrote last week, costs fell."          # the writer's output is read up to MAX_GUARD_CHARS, too
    assert len(padded) > mk.MAX_GUARD_CHARS and mk.guard({"items": [], "status": "ok"}, padded)["callbacks"] == 0 and mk.guard({"items": [], "status": "ok"}, padded[-3000:])["callbacks"] == 1


def test_render_cuts_a_very_long_item_at_a_word_and_says_so() -> None:
    text = "zorplax quentin " + "lorem ipsum dolor " * 2000
    index = mk.build_index([mk.Item("big", "note", "account_history", "2026-03-01", text)] + fillers(20), "2026-12-31")
    out = mk.retrieve(index, "zorplax quentin", "note", "2027-01-01", "lexical")
    shown = mk.render(out)
    assert ids(out) == ["big"] and len(shown) <= len("[2026-03-01] ") + 4000 + 4 and shown.endswith(" ...") and out["tokens_est"] == (len(shown) + 3) // 4              # H-15
    assert len(mk.render(out, max_item_chars=0)) > 30000 and mk.render(out, max_item_chars=60).endswith(" ...") and len(mk.render(out, max_item_chars=60)) < 90
    assert mk.render(out, "raw", 10 ** 6).endswith("dolor") and mk.render(out, max_item_chars=60)[:-4].split()[-1] in {"lorem", "ipsum", "dolor"}      # cut at a word, not inside one
