# AAM-E0: delayed relevance at fixed budgets

**Status: exploratory, not registered** in `data/lab/experiment-registry.csv` (registering is the owner's
call). The generated reports in `stage0/` and `stage1/` say "tier E"; under the doctrine's selection table
a study that builds a fresh corpus is Tier C and needs an I1 sealed split, and this one was run without
sealing, so it carries no tier claim above "exploratory, unsealed". Synthetic worlds written by an agent. A
result here is a result about this generator, not about real agents. The first version was reviewed by
three independent agents and the defects they reported were fixed; the final version has had no
independent review. Authority: the owner said on 2026-11-01 "choose yourself and execute"; nothing is
pushed, merged, published or licensed, and no spend was made (Stage 2, the only paid stage, has not been
run).

Built from `docs/11-research-laboratory/delayed-relevance-first-experiment-proposal-v0.md` and the build
specification `E0_SPEC.md` (in `GH_REVIVAL/`, outside the repository). Informal id: AAM-E0. Generator
version `goalshift-v0.2`.

## Result in one paragraph

Stage 1 (test seeds 100-119, 20 worlds, 240 probes, MiniLM, run once) gives **NOT SUPPORTED**. On the
primary comparison (cell C3, context 250 words, retained memory 10%, strict gold) the associative-trace
arm D reaches 0.075; the best comparator chosen on the development seeds, Sum-raw, reaches 0.125; D minus
it is -0.050 with a 95% bootstrap interval of [-0.125, +0.0125]. The two qualifying statements of the
decision rules both fire: a summary index with expansion is at least as good, and dense retrieval over
everything (F2, 0.200) is not below D, so D is no better than conventional retrieval. D is not
distinguishable from the shuffled-pointer control (S 0.049; D minus S +0.026, interval [-0.016, +0.072]).
Against the shuffled control D is clearly better in C1, where cue and target share words (D minus S +0.099
at C=250 and R=10%), by a smaller margin whose interval touches zero in C2 (+0.044), and by +0.026 in C3.
**Read this null narrowly.** The primary cell could not have returned SUPPORTED, and the Stage 0 table already
showed it (notes below). An independent review of the final version also judged that the C3 result was close
to guaranteed for this D: it has no abstraction step, the generator was tuned until the embedder sees C3 cue
and target as unrelated, and there is no positive control (with every event stored D reaches a recall at
11 events of 0.40 in C1, where BM25 reaches 1.00, and 0.15 in C3). It is a null about a word-cluster index in
this synthetic world, not evidence that associative traces fail.

## The question

At equal budgets, does a compact associative trace kept in the active store, pointing back to a raw
archive, recover an old, low-priority experience that only becomes relevant after a goal change better
than deleting it (Del) or summarising it (Sum, Sum-raw)? A null ("a summary index with expansion is as
good", or "plain retrieval is as good") is a complete answer.

## What is here

| path | what |
|---|---|
| `scripts/corpus/goalshift.py` | deterministic generator (own LCG, standard library only) |
| `scripts/corpus/goalshift_arms.py` | arms A, F1, F2, B3, Del, Sum, Sum-raw, D, O, Oc, S; lazy dense backend, injectable |
| `scripts/run_goalshift_e0.py` | harness: `generate`, `stage0`, `stage1`, `stage2-plan`, `stage2-run` |
| `tests/test_goalshift_*.py` | 86 unit tests (hashing embedder instead of the dense model) |
| `config.json` | all parameters, seeds, arm list, thresholds, SHA-256 of the three scripts (frozen after Stage 0, before Stage 1) |
| `stage0/` | `results.json`, `report.md`, `timing.json` (development seeds 0-4, local MiniLM) |
| `stage1/` | `results.json`, `records.jsonl`, `report.md`, `timing.json` (test seeds 100-119, one run) |
| `stage2/`, `stage2-ledger.json` | not created; written only by the lead's authorised run |

`results.json`, `records.jsonl` and `report.md` contain no clock value, so re-running the same stage in the
same environment gives byte-identical files (hash seed independent). Wall-clock and the timestamp are in
`timing.json`. Package versions are in `results.json` (`environment`); bit-equality of dense results is
claimed only for a fixed environment, since the 0.55 cosine thresholds could move at the margin on other
torch versions or hardware.

## Worlds

150 experiences over 30 days, three goal phases, each in a different one of six domains; 12 probes per
world, four in each cell. Every probe has a target (day 2-9, at least 14 days before the cue, carrying a
reference code that is the gold answer), a cue (day 21-30, a task in the current domain), and three decoys
placed before the cue: two surface decoys and one domain decoy in C1 and C2, and in C3 one surface decoy, one
domain decoy and a lookalike with the opposite outcome.

* **C1**: about 40% of the cue's content words occur in the target (measured on the development seeds: mean 0.380).
* **C2**: no shared content word after stop-word removal and light stemming; same topic, different words.
* **C3**: no shared content word; relevance by role (unreliable outside party, failed shortcut, hard
  limit, silent dependency, estimate slip, single owner, late approval, scale surprise) learned in another
  domain; the cue is a task in the current domain. Each world uses four roles; alternate worlds take
  alternate halves of the eight, so the 20 test worlds contain every role in exactly 10 worlds.

Names, places, numbers and codes are fresh per world; sentence templates are shared. Cues are rendered
from the probe's own random stream, so the cue file is byte-identical with or without the history (tested).

## Metric

`gold` (primary, strict): the reference code is present in the text the arm delivers. `gold_id`
(secondary): the gold event's id is present, so a lead-truncated 8-word summary counts although it never
holds the code. v0.1 made the id measure primary; that credited Sum for information it did not hold and
made Sum the "best comparator" with a spurious number. `gold_stored`: whether the arm kept anything of the
gold event (raw, summary or trace). Gold-in-context cannot exceed gold stored, so the loss splits into
"not stored" (a budget effect) and "stored but not retrieved".

## Changes after the verifiers' review (v0.1 to v0.2)

The review found that write-time importance was correlated with the hidden target label, so every
forgetting arm was quietly told which events mattered. Fixed in v0.2, before any rerun and without any
test seed:

* Consequence and novelty are authored write-time fields drawn from one stream by position only
  (independent of kind, text and later events). Importance is **uninformative by construction**, as the
  specification's "low-salience target" asks. Consequence: v0.1 targets 1.53 vs filler 0.68; novelty:
  targets 0.86 vs filler 0.53, falling with time. Stage 0 now has a gate that the targets' mean importance
  rank share lies in [0.30, 0.70]; measured 0.55 / 0.63 / 0.40 (C1/C2/C3).
* Every event carries a reference code (v0.1: all targets and decoys, 62% of filler).
* Strict gold is primary, the id measure secondary; the headroom gate and the best comparator use strict.
* Oracle: O keeps cheaper traces (about 2 words against up to 6 for D) and so stores about three times as
  many events at the same R. It is kept and labelled "oracle with cheaper traces". A new arm **Oc** is D's
  stored set and D's trace costs with the generator's labels: the like-for-like oracle.
* S is the mean of 20 independent pointer shuffles per probe, reported with the paired contrast D minus S.
* D's concept rule: a stem must occur in at least 2 visible events and have at least 4 letters. This was
  fixed a priori, before the test seeds, but it was suggested by a verifier's diagnostic on development
  seeds, so it is not "untouched". D's sensitivity to it and to the cluster/query threshold is a secondary
  table (below). "Not tuned" must not be read as "robust": on development seeds one preprocessing detail
  moved C3 by +/-0.15.
* Decision-rule comparisons carry a tolerance. With raw float subtraction a gap of exactly 0.15
  (12/80, e.g. 0.35 - 0.20) was classed NOT SUPPORTED for 16 of 69 grid pairs, and the Sum-raw band
  failed the same way. Tests sweep the whole grid.
* Gate in front of every use of the test seeds (`generate --allow-test-seeds`, `stage1`, `stage2-plan`):
  `config.json` digests equal the current scripts, Stage 0 passed on the same digests, on exactly seeds
  0-4, with the real embedder. `--allow-digest-mismatch` is gone. Stage 1 refuses to overwrite results in its
  output folder and runs only the frozen test seeds (nothing outside that folder records that the test seeds were
  evaluated, so a second look with another `--out` is not prevented; an independent review found this, and the
  frozen scripts are not changed); `--dev-dry-run` exists for mechanics on development seeds and
  writes elsewhere. Stage 2 plan on the test seeds also needs a real Stage 1 result.
* Stage 2 hardening: the cap must be finite, positive and at most $5; the plan's reader must equal the
  frozen `READER` (model, endpoint, parameters) and the endpoint and model used are the constants, not the
  plan's; `outputs.jsonl` must be empty; the cost projection uses characters/3 and is called an estimate.

## Stage 0 (development seeds 0-4, MiniLM): passed, narrowly on the headroom gate

Nine gates, all passed (`stage0/report.md`). Read the first one with care: the best of Del / Sum /
Sum-raw in C3 at C=250, R=10% is Sum-raw = 0.250 (Del 0.150, Sum 0.000 strict), which is the floor of
the [0.2, 0.8] window plus one probe of 20. With uninformative importance the comparators hold the gold
mainly by coverage (a few older events fit in 10%), so there is little headroom by design, and the gate
was passed by a single probe. The v0.1 side-by-side is in the report (C3, C=250, R=10%, by id / strict:
Del 0.20/0.20, Sum 0.35/0.00, Sum-raw 0.05/0.05, D 0.10, O 0.95, S 0.15 in v0.1).

The oracle gate now tests the retrieval path: O and Oc reach the gold 1.000 of the time when they stored
it, at R=10% and 25%, and O is 1.000 unconditionally at R=25%. It does not claim O is near 1 at R=10%
(0.533 stored). The shuffle gate is loose by nature (S 0.072 vs chance 0.069 at R=10%, 0.090 vs 0.126 at
R=25%). The semantic gate passed with gaps C1 0.366, C2 0.178, C3 0.045 (v0.1 had 0.082 in C3; the
random streams and the role mix of the generator changed).

## Stage 1 (test seeds 100-119, MiniLM, one run)

Strict gold-in-context at C=250 words, R=10% (R=25% in the second column of the trace and forgetting arms):

| arm | C1 | C2 | C3 | C3 at R=25% |
|---|---|---|---|---|
| F1 (BM25, everything) | 1.000 | 0.000 | 0.037 | |
| F2 (dense, everything) | 0.988 | 0.863 | 0.200 | |
| Del | 0.087 | 0.025 | 0.062 | 0.100 |
| Sum | 0.000 | 0.000 | 0.000 | 0.000 |
| Sum-raw | 0.138 | 0.138 | 0.125 | 0.075 |
| D | 0.200 | 0.088 | 0.075 | 0.088 |
| O (oracle, cheap traces) | 0.562 | 0.575 | 0.550 | 1.000 |
| Oc (oracle at D's footing) | 0.250 | 0.175 | 0.200 | 0.500 |
| S (mean of 20 shuffles) | 0.101 | 0.043 | 0.049 | 0.105 |
| A, B3 | 0 | 0 | 0 | |

Primary: D 0.075 vs Sum-raw 0.125 (chosen on 20 development probes, a noisy draw): difference -0.050,
interval [-0.125, +0.0125]. NOT SUPPORTED. By event id (secondary) the dev-chosen comparator is Sum
(0.175) and D minus it is -0.100, interval [-0.1875, -0.025]. The contrasts against the other arms are in
`stage1/report.md`.

What the numbers say, and what they do not:

* **D loses mostly at storage and then at retrieval.** At R=10% in C3, D has the gold stored 0.200 of the
  time and puts it in the context 0.075 (stored but not retrieved: 0.125). Oc, with D's store and perfect
  association, reaches 0.200: the ceiling of this trace design at R=10% is 0.20. At R=25% D stores 0.500
  and retrieves 0.088 (0.412 stored but not retrieved), against Oc 0.500 and S 0.105.
* **D is not above its shuffled control in C3** (D minus S +0.026, interval spanning zero).
* D's false-association rate is 0.99, which is almost uninformative: the context holds about 10 events
  and one is gold, and every non-gold fetch counts. The audit of about 30 associations for a finer label
  has not been done.
* O's high value comes from storing more events at the same R, plus perfect labels; it is not a ceiling
  for D.
* Negative transfer, decoy intrusion, every C and R, and the sensitivity table are in the report.
* D's sensitivity (C3, C=250, R=10%): primary rule 0.075; v0.1 concept rule 0.075; threshold 0.45 0.0875;
  threshold 0.65 0.0375. At R=25%: 0.0875, 0.0875, 0.050, 0.075. No variant approaches the 0.15 gap.
* Per role (C3, 10 probes each; the report has all eight): F2 reaches the gold for `hard_constraint`
  (0.80) and `failed_approach` (0.50) and not for `estimate_slip` or `late_approval` (0.00); D is 0.30 on
  `failed_approach` and 0.00 on `hard_constraint`. C3 mixes paraphrase-level and abstract roles, with
  about ten probes per role; no role-level claim is supported.

A small defect in the Stage 1 report text: the row "paired bootstrap 95%% interval" prints a doubled
percent sign. It was not corrected, because editing the script would break the frozen digests after the
single Stage 1 look; the numbers are right.

## Limits

* A synthetic world authored by an agent: a null here says that, in this generator, with these
  parameters, D does not beat Sum-raw or dense retrieval. It does not say associative traces cannot help
  real agents, and a positive result would have been equally bounded.
* Importance is uninformative by construction, so Del, Sum and D keep random subsets of the older events
  and the comparators' headroom is set by coverage. In v0.1 the opposite error made importance reveal
  the targets. A world with informative-but-noisy importance is a different experiment and was not run.
* Stage 0's headroom gate was passed by one probe (0.25 against a floor of 0.2). The best comparator is a
  noisy draw from 20 probes. The bootstrap interval over 20 scenarios is discrete and coarse.
* Free resources are not charged to R: D's cluster vocabulary, seed vectors and co-occurrence table (built
  from all visible events, including dormant ones, so richer than a sequential ingest) and the dense index
  of Sum and Sum-raw. R measures only stored trace or summary words. Write-time cost is not counted.
* Overlap is measured in the arms' own token space (one stop-word list and crude stemmer shared by the
  generator, the overlap measure and D), so D's direct lexical route is blocked by construction.
* Concepts are single stemmed words, not phrases. Summaries are lead-truncated extracts, weaker than
  model summaries. Cluster centre is the first member (greedy leader).
* Every event carries a code, but the reader question still says "reference code": a Stage 2 reader could
  pick a code at random from the context; mechanical scoring would credit it only if it is the gold one.
* The semantic gate thresholds were written before the first semantic measurement; the generator was
  revised after the first Stage 0 run and again after review. That is tuning of the generator on
  development seeds, which the plan allows; the cell separations are partly a product of it.
* The test seeds were generated and run once, in Stage 1, after the freeze. They were not generated or
  inspected earlier. Seeds 200-329 were used only to check that generation succeeds.

## Notes added after the run (lead, 2026-11-01)

Written after Stage 1; they change no number above and no generated file.

* **The primary cell could not have confirmed the hypothesis.** In C3 at R=10% D stores the gold event in 20%
  of the probes (`gold stored`), so no association rule can put it in the context more often than that; Oc,
  D's own store with perfect association, reaches 0.200. The best comparator reached 0.125, so the largest
  gap any association rule on this D's stored set could have shown was 0.075, below the pre-declared +0.15.
  SUPPORTED could not have been returned at the primary cell, and the committed Stage 0 table already showed it
  (development seeds, same cell: Oc 0.350 against a best comparator of 0.250, a ceiling gap of 0.10), so the
  test seeds were used when the outcome at the primary cell was predictable. The verdict NOT SUPPORTED says only
  that D is below its own ceiling. Checked against `stage1/records.jsonl` by recomputation: D 0.075,
  Sum-raw 0.125, D stored 0.200, bootstrap [-0.125, +0.0125], all matching the report. Stage 0 lacks a
  feasibility gate: before the test seeds are touched, the best case for D (Oc minus the best comparator)
  must be able to clear the threshold.
* **What the run does show.** At R=25% D stores the gold in 50% of the C3 probes and puts it in the context in
  8.75%, against 50% for Oc and 10.5% for the shuffled control: the loss is in association, not in storage,
  and in C3 D's association is not distinguishable from random pointers. In C1, where cue and target share
  words, D reaches 0.20 against 0.10 for S, so the trace links words, not roles. Dense retrieval over the
  whole archive (F2) reaches 0.20 in C3 at 250 words and 0.325 at 500 words, so even unconstrained dense
  retrieval finds only a fifth to a third of the role-level lessons.
* **Seeds 100-119 are spent for this configuration.** A changed design (feasibility gate, informative
  importance, model-written traces) needs a new version, a new Stage 0 on development seeds and fresh test
  seeds; it cannot be run again on 100-119.
* **Stage 2 is not planned.** A retrieval-level null cannot be rescued at the answer level; the paid stage
  would only qualify it.
* **The generated reports say "tier E"** because the frozen script writes that text; they are not edited,
  since that would change the digests. The status paragraph above is the correct reading.
* **Admission under the research-to-experiment gate** (Boundary B in
  `docs/11-research-laboratory/research-to-experiment-gate.md`):
  - Failure observable: lexical and dense retrieval reach 1.000 on the DELAYED and REDERIVE families of
    corpus H1 (`data/lab/corpus-h1/baseline-v0.1-rerun-2026-11-01/`), so that corpus cannot separate
    mechanisms.
  - Source: engineering-first, no biological evidence claim.
  - Disconfirmation and strongest alternative: `docs/07-literature/associative-memory-prior-art-2026-11.md`
    (explicit memory shows no consistent edge over raw-history retrieval). The alternative, that a summary
    index with expansion or plain dense retrieval is as good, is encoded in the decision rules.
  - Mechanism: input = event texts in time order plus the goal text; state = for events beyond the budget R,
    up to five stemmed concept words (document frequency at least 2, at least 4 letters) clustered greedily
    at cosine 0.55, with a pointer to the raw event; readout = the concepts of the cue and the goal
    activate clusters, one hop of co-occurrence spreading, raw events fetched by summed activation until
    the context budget C is full.
  - Baselines and bounds: A, F1, F2, B3, Del, Sum, Sum-raw; O and Oc as oracles; S as the shuffled control.
  - Characteristic failure: false association and negative transfer, reported per arm.
  - Outcome, costs and rejection condition: `config.json`, fixed before the test seeds (the first note
    describes the one flaw found afterwards).
  - Reversible: a new directory, no frozen file touched (the claims audit exits 0).

## How to run

Quote every path (the worktree path contains a space). Development Python (no torch) for tests and
`generate`; the dense Python only for the dense arms, with the offline switches set.

```
DEV="<python 3.11 or later with pytest; torch is not needed>"
DENSE="<python with torch and sentence-transformers>"
MODEL="<local directory holding all-MiniLM-L6-v2; this code never downloads it>"

"$DEV" -m pytest tests/test_goalshift_generator.py tests/test_goalshift_arms.py tests/test_goalshift_harness.py -q

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
"$DENSE" scripts/run_goalshift_e0.py stage0 --embedder minilm --model-dir "$MODEL"
"$DEV"   scripts/run_goalshift_e0.py generate --write-config      # freeze the digests after Stage 0 passed
"$DENSE" scripts/run_goalshift_e0.py stage1 --embedder minilm --model-dir "$MODEL"   # once; refuses to overwrite its output folder
```

Any edit to one of the three scripts changes the digests: rerun Stage 0, refreeze, and (because Stage 1
refuses to overwrite) use a fresh output directory only for a new, clearly labelled run on new seeds.
`stage0` refuses the test seeds always. `stage1 --dev-dry-run --seeds 0-1 --embedder hashing --out <dir>`
checks mechanics on development seeds and is not a result.

### Stage 2 (paid; the lead runs it, not a builder; not run)

`stage2-plan` writes `stage2/plan.json` (contexts for A, F2, Del, Sum-raw, D at C=250, R=10%, the reader
prompt hash, and a cost estimate; no network). `stage2-run` refuses without `--i-have-authorisation` and a
finite positive `--cap-usd` of at most $5, refuses a plan whose reader differs from the frozen one,
refuses if the estimate exceeds the cap, and checks the hard cap before every call through
`arena.decoding.FixedDecoding` and `arena.spend_ledger.SpendLedger` (run id and scope `aam-e0-stage2`).
Reader id in code: `deepseek-v4-flash`, temperature 0, `max_tokens` 300, the system prompt of
`scripts/arena/fixed_reader.py`; scoring is mechanical (reference code contained in the answer). The owner
said DeepSeek Flash may be used for tests; the lead should confirm that the id `deepseek-v4-flash` is the
model meant before authorising spend. The ledger `stage2-ledger.json` is JSON lines, because that is what
`SpendLedger` writes; the V1/V2/V3 arena ledger is never touched. The API key is read only by
`arena.run_pilot.load_key` inside `stage2-run`, never by this code. Given the Stage 1 null, Stage 2 would
only qualify it at the answer level; start with `--pilot-calls 20` if it is ever run.
