<h1 align="center">Can an agent learn what is worth remembering?</h1>

<p align="center">
Research on local-first, model-agnostic memory for LLM agents.<br>
<b>Can measured future usefulness improve what an agent retains?</b>
</p>

<p align="center">
<a href="https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/workflows/ci.yml"><img src="https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
<a href="#license"><img src="https://img.shields.io/badge/License-Apache%202.0%20%2B%20CC%20BY%204.0-blue.svg" alt="License: Apache-2.0 for code, CC BY 4.0 for documentation and data"></a>
<img src="https://img.shields.io/badge/engine%20dependencies-none-brightgreen" alt="The memory engine has no dependencies">
<img src="https://img.shields.io/badge/API%20key-not%20required-blue" alt="No API key">
<a href="https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/good%20first%20issue"><img src="https://img.shields.io/github/issues/krapcys1-maker/adaptive-agent-memory-research/good%20first%20issue?label=good%20first%20issues&color=7057ff" alt="Good first issues"></a>
</p>

**New here?** Read [Status and where help is wanted](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/84): what is in progress, what just finished, and every task where outside help is welcome.

**Delivery audit (4 November 2026):** the project-memory tool and research components work; a generic adaptive memory product is not yet validated. The [audit of delivered work, tests and unresolved failures](docs/00-project/project-delivery-audit-2026-11-04.md) distinguishes those capabilities from supplied-evidence pilots and scoped hard-benchmark failures.

---

## Give Claude Code persistent project memory in two minutes

The memory engine this research is built on is dependency-free, offline, and works today on **your** project. Point any MCP client at it:

```bash
git clone https://github.com/krapcys1-maker/adaptive-agent-memory-research ~/aamr
claude mcp add project-memory -- python ~/aamr/tools/project_memory/server.py --root .
```

Your agent now has eight tools — `memory_status`, `memory_search`, `memory_context`, `memory_get`, `memory_timeline`, `memory_add`, `memory_supersede`, `memory_rebuild_index` — writing to a single append-only `memory/events.jsonl` in your repository. No API key, no vector database, no daemon, no cloud account, no `pip install`.

Prefer no MCP client? Everything works from the CLI. Run it from your own project with `--root .`; without `--root` the CLI reads and writes this repository's own research log:

```bash
python ~/aamr/tools/project_memory/cli.py --root . add --kind decision \
  --title "Use SQLite for the cache" \
  --summary "Chose SQLite over Redis because the deployment target has no daemon." \
  --source docs/adr/0003.md
python ~/aamr/tools/project_memory/cli.py --root . search "why sqlite"
```

> **This is the research engine, not a finished product.** The project used it on itself on each of its first four days (22 to 25 August 2026); the November work is documented in the READMEs under `data/lab/`. Bugs, rough edges, and honest reports of both are welcome — if setup fights you, [open an issue](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/new/choose) and say so.

---

## The problem

An agent's context window is a workspace, not a memory. Once a conversation is compacted, whatever was dropped is gone — including the thing that turns out to matter three weeks later.

The usual answer is to embed everything and retrieve by similarity. That answers *what looks like this query*, which is not the same question as *what will this agent need*. Those two come apart badly, and this project exists to measure exactly where.

## The idea

Two stores, not one. A fast, evidence-preserving episodic log that learns from single experiences, and a slower semantic or procedural store that consolidates what recurs. What moves between them is governed by **measured future utility** rather than by semantic similarity or retrieval frequency.

```text
                 experience
                     │
                     ▼
        ┌────────────────────────┐
        │   append-only log      │   immutable evidence, never rewritten
        └────────────┬───────────┘
                     ▼
        ┌────────────────────────┐
        │   memory controller    │   write · preserve · consolidate · revise · archive
        └────────────┬───────────┘
                     ▼
    ┌──────────┬───────────┬────────────┬──────────┐
    │ episodic │ semantic  │ procedural │ failure  │
    └──────────┴─────┬─────┴────────────┴──────────┘
                     ▼
        ┌────────────────────────┐
        │  measured future use   │   ◄── the part that is actually research
        └────────────┬───────────┘
                     ▼
                 retrieval ──────────► agent
```

The append-only log, the controller and retrieval are built and running — that is what the two-minute setup above gives you. The box marked *the part that is actually research* is the open question, and the four stores below the controller are a design rather than a measured decomposition. This diagram is the hypothesis, not a claim about what works.

## What we have measured

Of 74 registered experiments, 39 are completed or retracted, 20 are blocked (waiting on a corpus, four of them also on independent review), 7 were invalidated or only partly valid, and 8 are designs or review packets awaiting execution; `python scripts/registry_summary.py` prints the current counts. All are exploratory and none is independently reviewed, so read these as measurements rather than settled science — but they are measurements, and the data is in the repository. The registry covers the August campaign. The experiments of November 2026 (series `AAM-` and `WMB-`, described under [Since August](#since-august-the-writer-memory-track)) are not entered in it; each has its own README with the preregistration, the results and the limits.

**A superseded fact is maximally similar to the fact that replaced it.** Mean cosine 0.816 between an old fact and its replacement, against a corpus baseline of 0.372 — two pairs at 1.000. With the metadata filter removed, the stale version was the nearest neighbour in 6 of 9 cases and its median rank was 1. *Content cannot separate a retired fact from its successor. Only bookkeeping can.* → `PMLAB-STALE-E1`

**One timestamp cannot answer "what did we believe at time T".** It scored 0.00 on that question and leaked future information into 6 of 18 queries. Separating valid time from transaction time scored 0.944 with zero leaks. The caveat matters as much as the result: every design scored 1.00 on *what is true now*, so the second axis buys nothing unless historical questions get asked. → `PMLAB-REV-V0`

**A 220 MB local multilingual embedder lifted Polish-query recall@10 from 0.156 to 0.978** — but a hand-built glossary already reached 0.867, and the queries are translated memory titles looked up against their own ids, not questions. Safety was not measured in this run; a separate, smaller one (`PMLAB-REUSE-CHAR-001`) found 0.200 forbidden intrusion for dense retrieval against 0.050 for lexical search. → `PMLAB-XLANG-E2`

**An association graph over memory lowered Recall@5 by 0.114** on the mechanical-gold stratum (95% CI −0.179 to −0.054); at Recall@10 the difference there is −0.039 and its interval includes zero, while the smaller authored-gold stratum points the same way (−0.052 at @5, −0.056 at @10). The earlier, favourable version of this result was **retracted by us**: its leakage control removed one edge where it needed to remove several, so the gold-generating group reassembled over two hops. → `PMLAB-ASSOC-E2` retracted, `PMLAB-ASSOC-E3`

**An early baseline suggested that perfect recall can sit beside a wrong top-ranked line — that result did not survive a corpus repair.** The committed baseline reports **1.000 recall@10** for the poisoned-instruction family and the poisoned line ranked *above* the genuine rule in **25%** of probes (3 of 12). Re-running the same, unchanged script on the current corpus gives 0 of 12 for that family (recall@10 still 1.000) and an overall recall@10 of 0.881 against the committed 0.810. The cause is a corpus repair made 34 minutes after the baseline was written (commit `cd5c3f4`): before it, the 84 probes asked only 24 distinct questions (the 12 poisoned-instruction probes asked 4), so many probes did not identify their own case. The script run on a snapshot of the earlier corpus reproduces the committed baseline byte for byte, and on a snapshot of the repaired corpus it reproduces the re-run. Both are recorded next to the original, which is left untouched, in [`data/lab/corpus-h1/baseline-v0.1-rerun-2026-11-01/`](data/lab/corpus-h1/baseline-v0.1-rerun-2026-11-01/README.md). Treat the 25% as an artefact of probes that did not identify their own case, not as a finding about retrieval or memory systems. → `PMLAB-H1-BASE-E1`

**We cannot currently instantiate tier I3 of our own independence ladder.** Two roles of one model fabricated an evidence identifier zero times across 120 queries, so the error correlation is *undefined* rather than zero — and the harness reports undefined, because 0.0 would claim an independence nobody measured. → `PMLAB-DECORR-E1`

Four of those six are negatives and one is a retraction of our own work. **That ratio is the honest one at this stage**, and it is the thing this project is most willing to defend.

### Since August: the writer-memory track

From 1 November 2026 the lab turned to one applied question — what a memory should do for an agent that *writes*, and how to tell whether it does — and to the instruments needed to ask it honestly. The experiments are small, each preregistered in its own README before the first model call, and reported with their limits. Three of them (F1, E6, E6E) were corrected after an adversarial review by separate reviewers ([PR #61](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/61)); in the [independence ladder](docs/00-project/independence-ladder.md) that is tier I2, which claims no independence. The original wording stays in git history.

**Showing a writer its own raw earlier entries made it repeat itself more, not less; a short trace did far less damage.** A 7B local writer on three streams and a strong hosted writer on six, synthetic throughout: raw entries raised overlap and length and lowered judged quality for the 7B writer, with the opposite lexical sign for the strong one; short traces produced the most explicit references back in both (15.6% and 8.9%, against 0% and 1.1% with no memory); dynamic importance and association added nothing measurable, in a test the review found too weak to say more. The preregistered readings could not fire for a reduction, because the practical threshold exceeded the baseline level of the measure. → [`AAM-E1-SIM`](data/lab/aam-e1-writer-memory-sim/README.md), [`AAM-E1-DS`](data/lab/aam-e1ds-writer-memory-sim/README.md)

**In a simulated follow-up test, thresholded memory was used accurately where a related earlier note existed, and always-on raw retrieval hurt where none did; the preregistered headline reading is unresolved.** Follow-up notes cited the earlier note accurately in 73.6% of cases with thresholded traces, against 2.8% with no memory and 4.2% with the instruction alone. Always-on raw retrieval made the writer refer back to irrelevant earlier notes in 30.1% of fresh items and lowered judged quality; a relevance threshold removed the damage. The headline reading was preregistered as *unresolved* because the pointwise scale saturated, and retrieval in this design is close to ideal. → [`AAM-E2-FU`](data/lab/aam-e2-followup-memory-sim/README.md)

**Replayed on a live account's real history, thresholded memory was preferred on the one task in five that has a related earlier note (win rates 0.64 to 0.73 against the instruction-only control), and always-on memory was judged worse on the rest (0.18) — but the judge then failed a check of its own.** WMB slice 0 planted pairs into the same judge: it sees identical pairs, copies, fabricated callbacks and non-answers, yet it prefers the note *without* a grounded callback (the callback note won 3 of 24). The pairwise lane is therefore descriptive only, and the E5 preference is not evidence that callbacks help. → [`AAM-E5-REPLAY`](data/lab/aam-e5-replay/README.md), [`WMB slice 0`](data/lab/wmb-v0/slice0/README.md)

**An LLM rating of relevance could not be calibrated on that account's notes.** Both rating scales failed their own control (70.9% and 81.7% of random pairs rated unrelated with the judge of record, 90% required), so no threshold is certified; a note-to-note cosine of 0.6 is recorded as a post-hoc starting value and not as a result. → [`AAM-E3A`](data/lab/aam-e3a-retrieval-calibration/README.md)

**No large per-note engagement signal was found beyond the recent level.** On 202 measured notes the note type adds nothing to the recent level for views or likes. The instrument could see a planted +50% effect in view counts but only about +100% in like counts, so smaller effects and other features were not testable. Feedback can be read at 24 hours instead of 72, and a live comparison cannot establish a small benefit quickly (about 74 days for a 50% effect in views). → [`AAM-F1`](data/lab/aam-f1-engagement-signal/README.md)

**A persona's invented biography can live in retrievable memory with a guard; opinion change from events is not shown at the preregistered size.** The biography was recalled at 0.92 (0.83 on the questions that need memory, a subset chosen after the fact). Improvised details agreed across fresh contexts 0.40 to 0.57 without write-back and 0.92 to 1.00 with it, which is a copy test. A good and a bad experience moved a stance by 1.1 points (1.5 preregistered). The invented past leaked into tasks where it must not appear in about 0.27 of outputs without a rule and 0.07 to 0.10 with one. A phrase filter for explicit claims in the persona's answers about its own nature caught about half of them (0.54 by hand count), so it cannot be the main defence. → [`AAM-E6`](data/lab/aam-e6-persona/README.md), [`AAM-E6E`](data/lab/aam-e6e-botness/README.md)

**A word-cluster "associative trace" index did not beat a summary comparator in a synthetic world — a narrow null, not evidence against associative traces.** The primary cell could not have returned a positive result, and there was no positive control. → [`AAM-E0`](data/lab/aam-e0-delayed-relevance/README.md)

**Lexical or embedding retrieval for the memory module? No verdict, and a finding about our own scorer.** The preregistered judge gate failed on its positive control by one pair (54 of 60, 55 required), so the decision was not issued. Exploratory readings, labelled as such: at equal exposure the module's own coverage score found 15 hits against 17 for BM25 and for tf-idf and 16 for a small sentence-embedding model (43 tasks; the rule could not exclude a gain of up to 6 hits); embeddings helped clearly only on questions that avoid the note's words, which is true by construction; the shipped max-fusion hybrid kept little of that gain. → [`WMB-R1`](data/lab/wmb-r1-retrieval/README.md)

**The instruments.** [`scripts/wmb/memory_kernel.py`](scripts/wmb/memory_kernel.py) is a one-file, standard-library memory module (version 0.1.0, 22 tests): thresholded injection of at most three items, nothing from the future, a log without text, and a deterministic reference guard that is a floor and not a proof. Version 0.1.0 is frozen as the instrument of WMB-R1; it is the module under test, not evidence that memory helps. Its live line is [`scripts/wmb/kernel/memory_kernel.py`](scripts/wmb/kernel/memory_kernel.py) (version 0.2.0, 94 further tests): a BM25 lexical gate in place of idf coverage, a rewritten guard and hardening; its defaults are not fitted to any real account. The [memory benchmark specification](docs/11-research-laboratory/memory-benchmark-spec-v0.md) joins the pieces, including the success ladder and what is not claimed. LifeSim, a deterministic generator of synthetic lives with exact answers, is the other instrument ([registration of its first two experiments](data/lab/aam-lifesim/README.md), [design](docs/11-research-laboratory/lifesim-design-panel-digest-2026-11-01.md)): X0 (does the generator measure memory and nothing else?) and X1 (value of a feeling-like signal at a retention gate) are registered and have not been run, and on 20 development worlds four of its sixteen validity gates fail.

#### What works, and what is unproven

*Works:* the append-only memory engine and its mechanical checks; the claim audit; the small-sample statistics and the record contract in `scripts/wmb/`; a memory module (the frozen 0.1.0 with 22 tests, the live line 0.2.0 with 94 more); deterministic synthetic corpora and a deterministic synthetic-life generator (859 tests) with exact answers. Each analysis script is deterministic given its record files. Model outputs cannot be regenerated exactly (the provider ignores the seed), and where a live account's texts were used only aggregates are published.

*Unproven:* that any memory design improves what a real agent writes (nothing here shows it); that thresholded injection helps readers (its only supporter is a judge shown to penalise grounded callbacks); whether an embedder is needed (R1 issued no verdict); whether a feeling-like signal has any value for retention (no per-note engagement signal was found in the one live account we can measure, and LifeSim will report a response curve in a synthetic world, which is by construction not a claim about real agents). None of these results is independently reviewed in the sense of the [independence ladder](docs/00-project/independence-ladder.md); the adversarial reviews that were done are recorded in the READMEs and in PR #61.

### The number that is not here yet

There is no headline benchmark table on this page, and there will not be one until it is earned. The comparison that matters — adaptive memory against native compaction and against vector retrieval, at a fixed context budget, on a long history — needs a corpus and a reader model.

The corpus now exists: [corpus H1](data/lab/corpus-h1/README.md), 538 events over 30 simulated days, 84 delayed probes across seven failure families, generated deterministically with no model and no API key. Its first run found a defect *in the corpus* — document length predicted the answer in 12 of 12 instances of three families — which is exactly what the construction-test tier is for. Both the broken and the repaired measurement are published.

A reader now exists: [`PMLAB-H1-READ-E1`](data/lab/corpus-h1/reader-v0-report.md) ran one reader model over two arms and the 84 probes, and found that retrieval answered 84.5% of them and was confidently wrong on 11.9%, the only arm that gave wrong answers (on the obsolete-family probes it answered from the superseded record 0.833 of the time). What is still missing is the compaction arms themselves. That is [#41](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/41), still open, still the highest-leverage task.

We have pre-committed to publishing that result whichever way it falls. Given that three separate runs here have already measured our own mechanisms *harming* retrieval, a negative headline is a live possibility — and it would be published in the same font as a positive one.

Since November the benchmark effort has two further instruments, the [writer-memory benchmark](docs/11-research-laboratory/memory-benchmark-spec-v0.md) and LifeSim. Neither has produced a headline number. The first result of the first is a warning about the kind of mistake that hides in a benchmark: a pairwise judge can look reliable on planted copies and still be blind to the thing the benchmark exists to reward. The specification's first level (L0) is exactly this check: planted pairs and null adapters must pass before any higher level is read.

## Try the research, not just the tool

```bash
git clone https://github.com/krapcys1-maker/adaptive-agent-memory-research
cd adaptive-agent-memory-research
python -m pip install -r requirements-dev.txt
```

The install pulls about 230 MB, mostly `transformers`, which is needed only to import one frozen audit script; the memory engine itself needs nothing.

Inspect the memory this project keeps about its own research, and watch it assemble a context bundle under a hard character budget:

```bash
python tools/project_memory/cli.py status
python tools/project_memory/cli.py context "what is blocking independent review" --char-budget 4000
```

Check that the append-only log satisfies every invariant decidable from its bytes — no model, no network, no reviewer:

```bash
python scripts/verify_memory_integrity.py
```

Audit the whole repository for claims that no longer hold:

```bash
python scripts/audit_repository_claims.py
```

That last one lists what no longer holds. It fails only on a critical finding: a declared hash that matches neither the working copy nor the Git blob, meaning a frozen artifact changed after it was frozen. It currently reports none. One declaration that did drift (`scripts/corpus/address_extract.py`, edited two minutes after the E2-A2 freeze) is shown as a low `explained-drift` finding, backed by a note next to the manifest that the audit re-derives from Git, because this project does not rewrite a freeze to make an audit pass. The medium findings — registry rows pointing at artifacts for experiments that have not run, experiment identifiers described in documentation but absent from the registry, memory sources that are not tracked — are printed, not hidden. Run it to see the current counts; they change as work lands.

Run the three gates CI runs (the tests, the memory-log check and the claim audit) on your own Python. It takes about six minutes on one Windows machine, almost all of it the test suite:

```bash
python tasks.py check
```

CI also runs the memory module's tests on Python 3.14 and a diff guard on `memory/events.jsonl`, which `check` does not. Use a full clone (no `--depth`), because one audit test reads an old commit with `git show`; on Windows, if git prints "Filename too long", run `git config --global core.longpaths true` first.

Run only the writer-memory and LifeSim pieces:

```bash
python -m pytest -q tests/test_wmb_memory_kernel.py tests/test_wmb_kernel_v2.py   # the memory module: 22 + 94 tests, about 25 s, needs only pytest
python -m pytest -q tests/test_wmb_*.py               # the benchmark code and the memory module: 403 tests, about a minute
python -m pytest -q tests/test_lifesim_*.py           # LifeSim: 859 tests, about 2 minutes
```

## How to help

Contributions run at three depths, and **you do not need a background in memory research for the first one.**

**Start with [Status and where help is wanted](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/84).** It lists what is in progress, what just finished, and every task where outside help is welcome, with an effort estimate. To take a task, comment on its issue. By area: [`kernel`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/kernel) (the memory module), [`wmb`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/wmb) (the writer-memory benchmark), [`lifesim`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/lifesim) (the synthetic-life generator). By size: [`help-wanted`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/help-wanted) with [`effort:S`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/effort%3AS), [`effort:M`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/effort%3AM) or [`effort:L`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/effort%3AL).

### About an hour, no research background

Issues labelled [`good first issue`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/good%20first%20issue) and [`no-expertise-needed`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/no-expertise-needed) are ordinary software work: a scoped bug, a missing exclusion rule, a CLI subcommand, reading one unfamiliar repository carefully, checking a citation against its source, running the tests on your platform and saying what happened. Each states what "done" means before you start.

If the setup instructions above fail on your machine, saying so in an issue is itself a useful contribution — this is developed on Windows and tested on Linux, and that gap has already produced one real defect.

**A negative result closes an issue here.** If you inspect something and find it is not what we assumed, write that down and you are done. Several of the findings above are exactly that.

### A few sessions, engineering

Issues labelled [`track:engine`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/track%3Aengine) build the machinery the research needs: sealed held-out splits, error-decorrelation measurement, the bitemporal query layer, cost-normalised retrieval metrics, an evaluation of the BM25 gate and a mutation check for the memory module, and the failing validity gates of the LifeSim generator. These need care but not domain expertise.

**Finding a hole in our method is worth more than completing a task.** The sealed-split tool carries three guards, each added after the corresponding attack was reproduced against it. A fourth would be the better contribution.

### Research review

Issues labelled [`independent-review`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/independent-review) need someone who can judge evidence. Read [the independence ladder](docs/00-project/independence-ladder.md) first — it explains why a large share of what once required an expert reviewer is now a mechanical check, and what genuinely still needs human judgement. The design of a replication of WMB-R1 with a repaired judge protocol needs someone who can judge a statistical protocol.

Everything goes through [CONTRIBUTING.md](CONTRIBUTING.md). Disagreement with a recorded conclusion is welcome; that is what the evidence ledger is for. Say hello in [Discussions](https://github.com/krapcys1-maker/adaptive-agent-memory-research/discussions).

## What we will not trade away

- User data stays local by default.
- The system must be model-agnostic.
- Raw evidence is append-only during early research.
- Experimental forgetting must never destroy the only copy of a memory.
- Every derived memory preserves provenance.
- Facts, hypotheses, decisions, preferences, and instructions are never conflated.
- A retrieved memory is not automatically a useful memory.
- Every added mechanism justifies itself in controlled evaluation.

## Prior art, and what is actually open

Two 2026 systems were verified in August 2026 and both occupy ground this page had been treating as open.

[APEX-MEM](https://arxiv.org/abs/2604.14362) (ACL 2026, Amazon) implements entity-property-value triplets over an append-only store with query-time temporal resolution — the architecture this project converged on independently — at 88.88% LoCoMo and 86.2% LongMemEval. **Structured temporal memory is not a novel claim here and is not made as one.**

[Fidelity Before Structure: Verbatim Chunks Beat Lossy Artifact Extraction in Long-Conversation LLM Memory](https://arxiv.org/abs/2601.00821) (formerly "Verbatim Chunks Beat Extracted Artifacts"; v4, July 2026) finds extraction *losing* to raw chunks by 15.9 points on LoCoMo, and attributes 78.8% of the 3,121 missing keywords in failed questions to extraction gaps. This project measured 85.7% abstention from a deterministic extractor — a different quantity on a different corpus, but consistent with that finding and a reason to take the paper's conclusion seriously rather than route around it.

[A-MAC](https://arxiv.org/abs/2603.04549) (March 2026) is verified: it scores memory admission with five factors, one of them an LLM-estimated *future utility*, so future utility as a retention criterion is already occupied as a predicted score. Whether it can be *measured causally* (question 3 below) is not addressed in its abstract and stays open. NEMORI and the other systems listed in [#48](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/48) are still being verified; until that resolves, read question 3 as **open only in its causal form**.

What still looks unoccupied is not a system but a diagnostic programme: *when and why similarity stops being the right access mechanism*, measured through failure attribution, an oracle router ceiling, near-clone density and context cost. Full assessment in [related work and novelty](docs/00-project/related-work-and-novelty.md), including the process failure that let this be found late.

## The five research questions

> Does an agent need complementary memory systems — an evidence-preserving episodic store for rapid learning from single experiences, and a slower semantic or procedural store that consolidates recurring evidence? And should transitions between them be governed by **measured future utility** rather than by semantic similarity?

1. What is the atomic unit of agent memory: message, event, fact, relation, episode, procedure, or decision?
2. How can storage failure be distinguished from retrieval failure and from reasoning failure?
3. How can future utility be measured causally rather than inferred from retrieval frequency?
4. When should exact episodes be consolidated into semantic or procedural knowledge?
5. How can memories be updated without losing provenance, uncertainty, or superseded historical states?

## Current phase

Evidence collection alongside gated laboratory testing. Each falsifiable hypothesis may enter an exploratory test under the [research-to-experiment gate](docs/11-research-laboratory/research-to-experiment-gate.md); confirmatory claims, added architecture, and any product implementation remain blocked behind stricter benchmark, reproduction, safety, and review gates.

Work runs in three tracks — engine, experiment, community — with milestones **M1 Engine**, **M2 Execute**, **M3 Independence**. The experiment registry (the `PMLAB-` series; 20 of its 74 rows are still blocked) paused new rows because the project was designing protocols faster than it could run them, and it has not changed since 23 August. Since 1 November 2026 the lab records each new experiment (series `AAM-` and `WMB-`) in its own README, with a `config.json` that holds the SHA-256 digests of its scripts and inputs, committed before the first model call; see [Since August](#since-august-the-writer-memory-track).

Both defects this section used to list as open are now closed, and how they closed is more interesting than that they did. Frozen hashes were reproducible only on a Windows checkout because Git's end-of-line conversion made 843 of 1348 files under `data/` differ byte for byte across platforms; `.gitattributes` now disables conversion repository-wide. Six frozen artifacts had been modified after freezing, by two distinct causes rather than one. CI verifies freezes on Linux with full history, so the check cannot pass vacuously.

---

<details>
<summary><b>Deep research — the full repository</b></summary>

### Reading path

New contributors do not need all of this. Read the first three, then follow whatever your issue touches.

1. [Start here](START_HERE.md) — the shape of the problem
2. [Operating doctrine](docs/00-project/operating-doctrine.md) — what we test next, and why that one
3. [Bootstrapping strategy](docs/00-project/bootstrapping-strategy.md) — why the tool is also the corpus, and what that costs
4. [Independence ladder](docs/00-project/independence-ladder.md) — how a claim earns promotion
5. [Repository map](docs/00-project/REPOSITORY_MAP.md) — where everything lives
6. [Scope](docs/00-project/scope.md) and [definitions](docs/00-project/definitions.md)
7. [Research plan](RESEARCH_PLAN.md) and [research questions](docs/00-project/research-questions.md)
8. [Human memory](docs/01-human-memory/README.md) · [LLM memory](docs/02-llm-memory/README.md) · [mapping between them](docs/03-human-ai-bridge/mapping.md)
9. [Systems catalog](docs/04-systems/catalog.md) · [benchmark catalog](docs/05-benchmarks/catalog.md)
10. [Research laboratory](docs/11-research-laboratory/README.md) and the [experiment gate](docs/11-research-laboratory/research-to-experiment-gate.md)
11. [Memory benchmark specification v0](docs/11-research-laboratory/memory-benchmark-spec-v0.md) — what success means for a writer's memory, and how the instruments fit together

### Repository layout

```text
docs/00-project/          Scope, definitions, methodology, independence ladder, decisions
docs/01-human-memory/     Cognitive psychology and neuroscience
docs/02-llm-memory/       LLM and agent memory mechanisms
docs/03-human-ai-bridge/  Testable mappings and invalid analogies
docs/04-systems/          Open-source systems and architecture comparisons
docs/05-benchmarks/       Benchmark coverage, flaws, and evaluation design
docs/06-datasets/         Training and evaluation data
docs/07-literature/       Reading queues, bibliography, evidence ledger
docs/08-experiments/      Experiment specifications
docs/09-synthesis/        Findings, open questions, exclusions
docs/10-comparative-biological-memory/  Animal, motor, immune, cellular, collective memory
docs/11-research-laboratory/            Protocols, benchmark ladder, gates, architecture boundary
docs/12-interdisciplinary-memory/       Compression, storage, control, offloading synthesis
docs/13-brain-ai-transfer/              Brain-to-AI mechanism atlas and transfer gaps
data/catalogs/            Machine-readable paper and repository catalogs
data/lab/                 Experiment registry, corpora, frozen runs, results
scripts/                  Experiment runners, audits, discovery helpers
tests/                    Test suite; runs on every pull request
memory/                   Append-only project memory and its generated index
tools/project_memory/     Dependency-free CLI and MCP memory adapter
```

</details>

## Working language

Repository content is written in English so contributors can collaborate internationally. Issues and discussions may use any language; durable findings are summarised in English.

## License

- Code (`tools/`, `scripts/`, `tests/`, `.github/workflows/`): [Apache-2.0](LICENSE).
- Documentation, research notes and the experiment data produced here (`docs/`, `data/`, `memory/`): [CC BY 4.0](LICENSES/CC-BY-4.0.txt).
- `data/lab/arena/*/vendor-patch/` holds modified copies of Mem0 1.0.6 (Apache-2.0); see [NOTICE](NOTICE).
- LongMemEval (MIT) is quoted in arena result files; LoCoMo (CC BY-NC 4.0) is not redistributed. Other systems, datasets and papers keep their own licences.
- Contributions are accepted under the licence of the path they touch (inbound = outbound). The path map is [`REUSE.toml`](REUSE.toml).
