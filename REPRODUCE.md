# Re-checking the arena claims

This file says what a stranger can re-check today, what they cannot, and why. It claims nothing it has not run.

## The claim under test

Entry H of [`docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md`](docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md): appending the raw source session behind Mem0's top-1 retrieval hit to its compact
context (`mem0_compact_plus_raw`) repaired one unit in each of two small LongMemEval-S samples (E3: compact 5/9, plus-raw 6/9; fresh replication: compact 5/8, plus-raw 6/8) and regressed none.

How much that is worth, said plainly:

* The evidence is **2 repairs in 17 observable units with 0 regressions, on legacy library versions** (`mem0ai` 1.0.6). An exact two-sided sign test on 2 against 0 gives p = 0.5. The ledger's label `REPLICATED_VALIDATED_TRANSPLANT` is a procedural ladder term, not a significance claim.
* One of the two repairs, `0e5e2d1a`, is a `single-session-assistant` question: it asks about what the assistant said, and the harness deliberately drops assistant turns before they reach Mem0 (`as_records()` in `scripts/arena/run_arena_pilot.py`). The other repair is `6a27ffc2`, a knowledge-update question.
* The plus-raw context is about 21 times longer than the compact one (mean per-unit ratio 21.36x). Table below.
* The ledger's own account: every measurement in Entries A to Q was taken on `mem0ai` 1.0.6 and `hindsight_api_slim` 0.9.1, not on current releases.

## Level 0: recompute the ledger's numbers. No key, no cost, no network, about a second

Needs Python 3.11 or newer and nothing else (standard library only). The script reads only files inside this repository and writes nothing.

```
python scripts/arena/verify_arena_numbers.py
```

It recomputes, from the tracked result files, the per-arm counts the ledger quotes for the fresh replication and the E3 sample, the repairs and regressions, the combined 17 units, the recorded spend of the replication
and the mean token overhead, compares each with the number it parses out of the ledger text, and prints per-unit token counts for compact versus plus-raw. Exit status: 0 all match; 1 a recomputed number differs from the ledger;
2 a required file is missing or malformed. The unit tests for the script are `python -m pytest tests/test_verify_arena_numbers.py` (needs `pytest`, see `requirements-dev.txt`).

Output of the run on 2026-11-01 (Python 3.12.10; also run under Python 3.11.13 with the same exit status 0):

```
== Entry H: fresh replication (8 gold-blind units) ==
PASS  fresh: compact / compact+raw / raw-only correct = ledger 5/8, 6/8, 4/8  | recomputed 5/8, 6/8, 4/8
PASS  fresh: repairs = [0e5e2d1a] (ledger), regressions = 0  | repairs=['0e5e2d1a'] regressions=[]
PASS  fresh: all 8 units observable
PASS  fresh: recorded spend = ledger $0.575419  | results.json says 0.575419

== Entry H: E3 original sample (9 observable units) ==
PASS  E3: compact / compact+raw / raw-only correct = ledger 5/9, 6/9, 4/9  | recomputed 5/9, 6/9, 4/9
PASS  E3: repairs = [6a27ffc2] (ledger), regressions = 0  | repairs=['6a27ffc2'] regressions=[]
PASS  E3: agrees with the stored e3-analysis.json  | stored scores {'compact_native_base_9_observable': '5/9', 'compact_plus_raw': '6/9', 'raw_only': '4/9'}

== Entry H: combined ==
PASS  combined observable units = ledger 17  | recomputed 17
NOTE  combined: 2 repairs, 0 regressions in 17 observable units.
NOTE  question types of the repaired units: 0e5e2d1a = single-session-assistant, 6a27ffc2 = knowledge-update
NOTE  exact McNemar p = 0.250 (one-sided), 0.500 (two-sided); 95% Clopper-Pearson interval for the repair rate 0.015 to 0.364. This is a small-sample descriptive result, not a significance claim.

== Context length: compact vs compact_plus_raw (the length confound) ==
fresh replication, tokens as stored in results.json
  unit       type                        compact     +raw raw_only    ratio
  0862e8bf   single-session-user              89     2154     2065    24.2x
  06878be2   single-session-preference       104     3339     3235    32.1x
  099778bb   multi-session                   128     2405     2277    18.8x
  078150f1   multi-session                   105     2581     2476    24.6x
  0bc8ad93   temporal-reasoning              128     2045     1917    16.0x
  07741c44   knowledge-update                102     2375     2273    23.3x
  06db6396   knowledge-update                 98     2580     2482    26.3x
  0e5e2d1a   single-session-assistant        109      609      500     5.6x
  mean of per-unit ratios 21.36x (min 5.6x, max 32.1x); pooled ratio 20.96x
PASS  fresh: compact_plus_raw tokens == compact tokens + raw_only tokens for every unit
PASS  fresh: mean per-unit overhead rounds to the ledger's ~21.4x  | recomputed 21.36x
E3 sample, DERIVED: the E3 files store no token count for the plus-raw context, so it is taken as compact tokens
(mem0-breadth-arms.json) + raw session tokens (e3-arms.json); the fresh data above shows this sum is exact there.
  unit           type                compact     +raw    ratio
  311778f1       single-session-user      101     2654    26.3x
  58bf7951       single-session-user      117     1735    14.8x
  6a27ffc2       knowledge-update         100     2988    29.9x
  ba358f49       multi-session             114     2574    22.6x
  eace081b       knowledge-update         100     2234    22.3x
  gpt4_59c863d7  multi-session             142     3173    22.3x
  gpt4_98f46fc6  temporal-reasoning        92     2233    24.3x
  gpt4_f420262c  temporal-reasoning       126     2379    18.9x
  gpt4_f49edff3  temporal-reasoning       126     1917    15.2x
NOTE  The plus-raw arm carries roughly 5x to 32x more context than compact. raw_only is about as long as plus-raw yet scored lower (4/8 and 4/9 against 6/8 and 6/9), so length alone does not explain the repairs; but no arm here holds length fixed while removing the relevant text, so these files cannot rule length out either.

all checks passed
```

What a pass means, and does not mean. It means the numbers in the ledger prose are the numbers in the tracked result files, and that the plus-raw arm is much longer. It does not mean the judge was right, that the reader's
answers were good, or that the contexts say what we think: the fresh replication's `results.json` keeps answers, labels and token counts but not the context text (the raw contexts are git-ignored, see below). The E3 file
`data/lab/arena/base-plus-x-v2/e3-arms.json` does keep the context items, so for E3 you can read what the reader was given.

Please also read the statistics line honestly: 2 repairs and 0 regressions in 17 units is compatible with no effect at all.

## What cannot be reproduced yet, and why

We have not run Level 1 or Level 2 below for this document, and we do not claim that they are runnable by a stranger today.

1. **The raw contexts and the Mem0 stores are git-ignored.** `/data/lab/arena/raw/`, `/data/lab/arena/pilot-raw/` and `/external/venvs/` are in `.gitignore`, because they hold corpus text, gold answers and an installed environment. What is tracked is answers, judge labels, token counts and selections. Re-reading or re-judging the fresh replication from the repository alone is not possible.
2. **Re-running needs the old libraries, Windows paths and a manual setup.** The measurements used `mem0ai` 1.0.6 and Hindsight `hindsight_api_slim` 0.9.1 in virtual environments under `external/venvs/`. We found no pinned dependency file for the arena in the repository (`requirements-dev.txt` is for the tests). Several scripts put `external/venvs/mem0/Lib/site-packages` on `sys.path`, which is the Windows virtual-environment layout. The result files carry absolute Windows paths (for example `D:\Pamiec LLM\...`) as provenance. Embeddings used `sentence-transformers/all-MiniLM-L6-v2` at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (`data/lab/arena/embedding-model-provenance.json`), held constant across systems.
3. **A paid model API, with a local spend proxy.** Reader and judge are `deepseek-chat`, reached through `scripts/arena/provider_proxy.py`, which expects a `DEEPSEEK_API_KEY` in a git-ignored `.env`. Nothing in this repository contains a key; do not commit one. The judge prompts and label rule are LongMemEval's, the model is not the one its authors use, so scores are not comparable with published LongMemEval numbers. The provider does not guarantee identical answers for identical requests (`data/lab/arena/decoder-reproducibility.json`: `reproducible_everywhere: false`), so a re-run is expected to differ in places and should be compared as same or different label per arm per unit, not as byte equality.
4. **The dataset is not in the repository.** LongMemEval-S is MIT-licensed (dataset card). Download `longmemeval_s_cleaned.json` yourself from `xiaowu0162/longmemeval-cleaned`; this project used revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`, SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` (`docs/06-datasets/longmemeval-public-bridge-audit.md`), and the code looks for it under `external/datasets/longmemeval-cleaned-98d7416c24c7/`. Keep upstream's licence with it. Publicly reported defects in that file: [`docs/research/LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md`](docs/research/LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md).
5. **Patched vendor code.** Several mechanisms (for example Entries O and P) ran against a patched copy of Mem0 1.0.6; the patches and manifests are under `data/lab/arena/*/vendor-patch/`. They were written against 1.0.6 and have not been tried on Mem0 2.x.
6. **The versions are old.** Mem0 v2.0.0 (2026-04-16) changed extraction and retrieval; the newest releases we saw on 2026-11-01 were Mem0 2.2.1 and Hindsight 1.1.0. Nobody, including us, has shown that Entry H or the three failure modes survive that change.

### What it cost us, so you can price a re-run

All figures are token-derived estimates at a fixed list price (0.27 and 1.10 US dollars per million input and output tokens), not invoice amounts: we checked that all 19,585 per-call records in `data/lab/arena/spend-ledger.jsonl` equal their token counts times that price.

| Item | Spend | Source |
|---|---|---|
| Fresh replication, 8 units, 3 arms, from ingest to judged labels | 0.575419 USD (about 0.072 per unit) | `raw-provenance-fresh-replication-v1/results.json`, `autonomous-research-budget-v2/ledger.json` |
| E3 retest, 9 observable units: reader 0.016483 + judge 0.001907 | 0.018390 USD (reused an earlier Mem0 ingest, which is among the git-ignored files) | `docs/research/CLEAN_RAW_PROVENANCE_RETEST_V2.md` |
| Re-judging one 3-arm answer set | pennies; the 36 judge calls of the E3 judging cost 0.00191 USD | `base-plus-x-v2/e3-judged.json` |
| Mechanism campaign V1 (stopped after three failed families) | 2.143325 USD | `autonomous-research-budget-v1/ledger.json` |
| Mechanism campaign V2 | 4.393354 USD | `autonomous-research-budget-v2/ledger.json` |
| Every recorded model call in the arena, pilots and Hindsight runs included | about 19.44 USD over 19,585 calls | `spend-ledger.jsonl` |

A fresh ingest of one unit (46 to 51 sessions into Mem0) cost about 0.06 to 0.08 USD in the replication, and ingest was about 97 percent of that run's spend (0.559 of 0.575 USD by the end of the eighth ingest); ingest, not reading or judging, is the dominant cost of rerunning anything.

## The first thing worth doing

Before re-running the old numbers, re-run a few frozen units on current Mem0 (and Hindsight) and see which of the old findings still occur. The ledger names this as the next step (Entry R) and the open question
[`docs/research/OPEN_QUESTION_THREE_FAILURE_MODES.md`](docs/research/OPEN_QUESTION_THREE_FAILURE_MODES.md) makes it a precondition for testing any candidate. It has not been preregistered yet and nothing here authorises spending; the units it would use are the ones named in that document.
A result that says "this no longer happens on Mem0 2.x" is as useful to us as one that says it still does.

## Tell us where we are wrong

* A number in the ledger that the script prints differently on your machine: that is the best bug report. Send the full output and your Python version.
* A unit we classified under the wrong failure mode, or a claim above that the files do not support.
* A defect in LongMemEval-S that is not in [`docs/research/LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md`](docs/research/LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md), or a better treatment for one that is.
* A run on current Mem0 or Hindsight, with versions and n, whichever way it came out.
* A proposal for one of the three failure modes: see the open question.

Use the issue tracker of the repository this file is in, if it is open to you.
