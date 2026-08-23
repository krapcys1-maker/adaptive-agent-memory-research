# Corpus H1 — the first history family

Issue: [#41](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/41)
Tier: **E (exploratory)** — model-free construction, no network, no API cost
Authority: construction-test tier only. This corpus has never been run against an arm.

## What this is

The prefix half of the compaction benchmark: 30 simulated days of agent work,
538 events, of which 84 are probed by a delayed reveal generated separately.

```
data/lab/corpus-h1/
  prefix-v0/
    history.jsonl               538 events — what every arm sees
    construction-labels.jsonl   which property each event instantiates
    manifest.json               seed, counts, digests
  reveal-v0/
    queries.jsonl                84 questions — what an arm is asked
    gold.jsonl                   84 answers  — what an arm never sees
    manifest.json
```

Regenerate either half:

```bash
python scripts/build_history_family.py
python scripts/build_delayed_reveal.py
```

Both are deterministic from `seed=20260823`. No clock is read and `random` is
never used, so a run reproduces byte for byte on any platform and any Python
build.

## The eleven required properties

The protocol requires every history to contain all of these. Counts are from the
frozen corpus:

| Property | Count | | Property | Count |
|---|---:|---|---|---:|
| important-now | 24 | | repeated-noise | 302 |
| delayed-importance | 12 | | one-off-noise | 92 |
| common-fact | 118 | | poisoned-plausible | 12 |
| rare-critical-exception | 12 | | failed-attempt | 12 |
| obsolete-fact | 36 | | successful-fix | 12 |
| explicit-correction | 12 | | rationale | 12 |
| rederivable-from-files | 12 | | exact-identifier | 72 |
| not-rederivable-from-files | 12 | | authorization-state | 12 |
| bilingual-paraphrase | 24 | | | |

A first version had a count of **one** for most of these. It passed a
construction test and measured nothing: a single rare-critical-exception cannot
distinguish a system that retains exceptions from one that got lucky. Each
property is now a *family* instantiated twelve times, with the surface varied
from the seed — different hosts, ports, paths, line numbers, commit hashes,
counts, days — while the structure defining the failure mode stays fixed.

## The seven case families

Each names a way retrieval fails, and each carries a probe asked 14–28
simulated days later.

| Family | The failure it measures |
|---|---|
| `OBSOLETE` | the obsolete fact is stated three times and the correction once, tersely |
| `RARE-EXC` | one terse exception against 8–15 repetitions of the general rule |
| `DELAYED` | nothing refers to the event between day 3 and day 28, so recency and frequency both rank it near zero |
| `FAILFIX` | the rationale survives only in the history; the code that would explain it was deleted |
| `REDERIVE` | true, and arguably not worth remembering, because reading the file answers it |
| `POISON` | fetched content that reads as an instruction, contradicted by a real instruction the next day |
| `BILINGUAL` | the question is Polish and the corpus states the fact in both languages |

48 of the 84 probes carry a **forbidden event**: the superseded, poisoned, or
outweighed record whose retrieval *in place of* the gold is the specific failure.
Scoring those separately matters, because a system that retrieves both looks
fine on recall and is wrong in practice.

## Two design decisions worth arguing with

**The construction labels are a separate file.** If `properties` rode along on
each event, an arm could retain exactly the events marked
`rare-critical-exception` and score perfectly without performing any of the
selection being measured.

**The reveal generator never opens the history.** The protocol requires that no
write-side component sees the future query, task, gold, or consequence weights.
The natural implementation — write the history, read it back, author questions
against it — violates that invisibly, because the question author will write
questions the history happens to answer, and the resulting leak flatters every
arm equally.

Both generators are therefore pure functions of
`scripts/corpus/history_family_spec.py`. Gold event identifiers are recomputed
through the same `event_id()` function the history generator used, so the reveal
can name an event it has never seen.

### How that is proven, and how the proof failed first

`tests/test_history_family_construction.py` generates the reveal twice — once in
a tree containing the history, once in a tree without it — and requires
byte-identical output. Output that does not change when an input is removed did
not depend on that input.

The first version of that test compared a history-free run against the frozen
output, and **it passed while the generator was deliberately mutated to read the
history**. It could not have failed: with the history absent, the leaking branch
never ran. The comparison has to be between the two runs, because that is the
only pair that differs when a dependency exists.

The mutation was re-applied after the fix and the test failed as it should. This
is recorded rather than quietly corrected, because it is the same class of
error that caused `PMLAB-ASSOC-E2` to be retracted: a leakage control that
looked adequate until someone examined it.

## What this does not yet unblock, stated precisely

Twenty experiments carry `blocked-corpus-not-built`. **This corpus does not move
any of them to runnable**, and claiming otherwise would be the kind of premature
promotion the operating doctrine exists to prevent.

What each still needs:

- **A reader model.** `PMLAB-COMP-C1` through `C7` compare compaction arms by
  *delayed supported task success*. Scoring that needs a model to answer the 84
  probes from what each arm retained. The corpus supplies the questions and the
  gold; it does not answer them.
- **Compaction arms.** `P0` native product compaction, `P1` FTS5 pack, `P2`
  pinned external systems, `P3` the adaptive candidate. None is implemented
  against this corpus.
- **Scale.** This is the construction-test tier. The ladder continues at 100K,
  1M, 5M and 10M cumulative tokens. `--instances` and `--noise` scale the
  generator, but a larger corpus has not been generated or frozen.

What it *does* unblock is everything model-free: a lexical retrieval baseline
over the 84 probes, forbidden-intrusion measurement, and the cost-normalised
metric in [#38](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/38)
all run today with no API key.

## First measurement: PMLAB-H1-BASE-E1

A plain SQLite FTS5 index, BM25 over an OR of the query terms. Model-free, no
API cost, `python scripts/run_corpus_h1_baseline.py`.

```
recall@1   0.167   intrusion@1   0.042   tokens  20   recall/1k 8.15
recall@5   0.583   intrusion@5   0.167   tokens 117   recall/1k 4.97
recall@10  0.810   intrusion@10  0.271   tokens 248   recall/1k 3.26

forbidden outranks gold   0.083   over 48 probes
```

Per family, at depth 10:

| Family | recall@10 | forbidden outranks gold |
|---|---:|---:|
| OBSOLETE | 0.167 | 0.083 |
| BILINGUAL | 0.833 | — |
| DELAYED | 0.833 | — |
| FAILFIX | 0.833 | 0.000 |
| REDERIVE | 1.000 | — |
| POISON | 1.000 | **0.250** |
| RARE-EXC | 1.000 | 0.000 |

Three things worth noting.

**`OBSOLETE` at 0.167 is the family working.** The obsolete host is stated three
times over eleven days and the correction once, tersely, so frequency, order of
establishment and length all point at the wrong record. A lexical index finds
the corrected host in one probe out of six.

**`POISON` retrieves the poisoned line above the real rule in a quarter of
cases**, while scoring a perfect 1.000 on recall. That is exactly the reason
recall alone cannot be the headline: an arm that retrieves both records looks
flawless and would act on the wrong one.

**`RARE-EXC` and `REDERIVE` at 1.000 are currently too easy** for a lexical
baseline, and a compaction arm will not be separated by them at this scale.

The corpus was repaired once after a baseline run, for a reason independent of
any score. The evidence and the argument are in
[`baseline-v0-pre-length-fix/`](baseline-v0-pre-length-fix/README.md).

## Limits

- **Synthetic.** These are not real agent sessions. The failure modes are drawn
  from the protocol and from this project's own recorded failures, but the
  events were written to instantiate them, which is not the same as observing
  them in the wild.
- **Authored by the same agent that wrote the benchmark protocol.** The
  bootstrapping strategy already flags this as the standing limitation of a
  single-author project; it is mitigated by the generators being deterministic
  and inspectable, not removed.
- **One family.** The protocol asks for results in two corpus families before
  any candidate advances. This is one.
- **Surface variation is templated.** Two instances of `OBSOLETE` differ in host,
  port, service and version, and share sentence structure. A retriever that keys
  on structure rather than content would look better here than it deserves.
