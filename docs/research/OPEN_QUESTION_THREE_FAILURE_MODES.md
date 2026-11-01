# Open question: three failure modes of long-term memory for LLM agents

Public, self-contained English version of the standing research request `arr-2026-08-25-001`, written in Polish and kept in
[`Dokumenty dla Resherchera/RESEARCH_REQUESTS/2026-08-25_research_request_three-precise-failure-modes.md`](Dokumenty%20dla%20Resherchera/RESEARCH_REQUESTS/2026-08-25_research_request_three-precise-failure-modes.md).
Status of the request: open, no candidate has been tested against it. Public version dated 2026-11-01.

## Read this first: what the measurements are about

* **Every measurement behind this question was taken on `mem0ai` 1.0.6 and `hindsight_api_slim` 0.9.1.** These are the pinned versions recorded in the
  result files (`data/lab/arena/pilot-mem0.json`, `data/lab/arena/expansion-hindsight.json`) and in the licence map `REUSE.toml`.
* **Mem0 2.x rewrote extraction and retrieval.** Mem0 v2.0.0, released 2026-04-16, replaced the add/update/delete extraction with a single-pass,
  ADD-only extraction, made retrieval fuse semantic, keyword (BM25) and entity-matching signals into one score, and, in its own release notes,
  captures agent-generated facts as memories "for the first time" (source: the v2.0.0 release notes on GitHub). On 2026-11-01 the newest releases we saw were Mem0 2.2.1 (2026-09-25) and Hindsight 1.1.0 (2026-10-21).
* **The three failure modes below have not been re-checked on any current version.** Each may shrink, move or disappear. We do not know.
* **A version re-baseline comes before any candidate is tested.** That means re-running the frozen units named below on current Mem0 (and Hindsight), under a
  preregistration written first. The ledger records this as the next step ([`Entry R`](MECHANISM_REGIME_EVIDENCE_LEDGER.md) of the evidence ledger). A proposal that only works on 1.0.6 is a
  result about 1.0.6.

The reader and judge in all of these runs are `deepseek-chat`. The judge prompts and label rule are LongMemEval's, the judge model is not the one the
benchmark's authors use, so scores are comparable within this project's runs and not with published LongMemEval numbers (the `deviation` field in the judged result files says so).
The benchmark is LongMemEval-S (500 questions, MIT licence for the dataset card).

## Background in four sentences

This project compared long-term memory systems for LLM agents, then tried a series of small, preregistered read-side and write-side changes to one of them (Mem0),
each on a handful of fresh, gold-blind questions, and logged each one in [`MECHANISM_REGIME_EVIDENCE_LEDGER.md`](MECHANISM_REGIME_EVIDENCE_LEDGER.md) with its units, its counts and its verdict.
Most closed entries are drops, failed calibrations or failed replication gates; negative results are kept in the ledger.
The one mechanism that cleared this project's replication gate (Entry H: append the raw source session behind the top-1 retrieval hit to Mem0's compact context) did so on thin
evidence: **2 repairs in 17 observable units with 0 regressions on legacy versions, and one of those two repairs is a question about what the assistant said (`0e5e2d1a`, type `single-session-assistant`),
whose evidence sits in a turn the harness deliberately drops.** The ledger's label for that status, `REPLICATED_VALIDATED_TRANSPLANT`, is defined there as a ladder: "external motivation + isolated transplant + exploratory positive + fresh gold-blind
replication + confirmed mechanistic trace, all satisfied". It is a procedural label, not a significance claim (an exact two-sided sign test on 2 repairs against 0 regressions gives p = 0.5).
After many small tests, the failures that remain fall into a few distinct, individually rare patterns, and this question asks about three of them.

## The three failure modes

Each is defined by units you can inspect in the tracked result files. All ids are LongMemEval-S question ids.

### 1. Assistant-turn representation loss

The needed fact exists in the original conversation but only in an assistant-authored turn, and the shared ingest function never gives it to Mem0:
`as_records()` in `scripts/arena/run_arena_pilot.py` keeps only `user` turns, on purpose, because CUPMem, another system in the same comparison, silently drops assistant turns in its own chunker, and the docstring reasons that an adapter should not hand over turns it knows will vanish.

* Units: `0e5e2d1a` (type `single-session-assistant`; compact arm wrong, the raw-session arm right; this is the Entry H replication repair);
  `1de5cff2` (Entry Q; the ledger says the needed fact exists only on an assistant turn, and that the top-1 session was also the wrong one, so this unit mixes modes 1 and 2);
  `1d4da289` (Entry P; the ledger calls it the 5th independently observed case of this root cause).
  The standing request counts six instances project-wide; the ledger names the ones above.
* Prevalence signal: 56 of the 500 questions in LongMemEval-S are `single-session-assistant` (11.2%), per this repository's dataset audit.
* What would help: a precedent, in code or a paper, for **selectively** including assistant-authored content in memory extraction (only content that answers the user or
  carries new factual information), with a measured result, not only an architectural description. Including every assistant turn is not what is asked.
* Constraint on any candidate: it must enter through a separate, isolated ingest path (a new bank). It must not modify `as_records()`, because every other mechanism in the project shares that baseline.
* Note: Mem0 v2.0.0 says it now captures agent-generated facts. If that already closes this mode, the re-baseline will show it, and this mode drops off the list. That would be a finding, not a failure.

### 2. Retrieval anchor failure (remedy selection, not retrieval ranking)

Once something has decided to escalate from the compact context to the raw source, the remedy follows one pointer only: the session behind Mem0's rank-1 hit (`raw_session()`, deterministic, single hop).
If rank-1 is off-topic, the remedy appends irrelevant raw text; if the needed detail lives in a different session, it cannot reach it. This holds whatever decides when to escalate.

* Units: `1de5cff2` (Entry Q: rank-1 pointed to a session about jeans and watches, not the brand the question asks about); `078150f1` (Entry H counterexample, multi-session: the needed detail is in a session other than the top-1 hit's; all three arms wrong).
* Not this mode: "the gold fact is outside the top 10 for the literal question". That is query-side ranking and was tried as HyDE query reformulation (Entry M, dropped: the precondition was real elsewhere, but the sample drew a different failure subtype).
  Also not this mode: deciding *when* to escalate. A sample-and-cluster semantic-entropy trigger was tried (Entry Q, dropped: 1 genuine true positive and 1 clustering artefact in 2 firings, 0 traceable repairs).
* What would help: measured evidence on how to choose *what* to pull in: several candidate sessions rather than one, confidence-gated choice of the anchor, multi-hop pointer-following, in systems with persistent agent memory.
* Caution: Mem0 2.x changed retrieval the most, so this mode is the one most likely to look different after the re-baseline.

### 3. Temporal representation loss

Questions that need date arithmetic or ordering across sessions fail even when every needed fact is retrieved, because neither the compact bullet nor the raw session dump carries the session dates.

* Units: `6e984301` (Entry Q; the ledger traced it to the primary corpus: the gold needs arithmetic between two session dates, 11 February and 4 March, giving 3 Saturdays; neither the compact context nor the raw-injection format carries those dates);
  `0db4c65d`, `2ebe6c90`, `2ebe6c92`, `4dfccbf7` (listed in Entry M as the largest identified cluster at that time); `5e1b23de` (Entry P).
* Already tried and not sufficient: an instruction in the extraction prompt to resolve relative dates (Entry E: changed behaviour in 0 of 5 calibration cases) and rendering each fact's session timestamp in the context (Entries A, B, N: safe and sometimes useful in a narrow regime; the latest
  replication cleared 0 repairs against a required 2).
* What would help: measured examples of **structured** temporal resolution inside extraction pipelines: a separate output field, not inline substitution, resolved by deterministic code (Python standard-library `datetime`), not by the model doing arithmetic.
* A caution from Entry E: any design that resolves event dates must keep an explicit in-text date instead of silently replacing it with the session date.

## How an answer is judged: the four-part acceptance filter

A proposal is accepted for testing only if it meets all four. There are no exceptions, and the filter is applied before any test is designed.

1. **Testable now.** With open weights or hosted APIs and the existing harness. Not fine-tuning, hidden activations, provider-side training or weight updates.
2. **Not a duplicate.** Not a re-labelled copy of an already-tested design: Entry E (inline temporal instruction), Entry M (single-shot HyDE), Entry Q (embedding-cosine sample-and-cluster trigger with a top-1-anchored remedy), or the read-side timestamp rendering of Entries A, B and N. Read them, and say in what way yours differs in substance.
3. **Exactly one mode.** It targets one of the three modes above and can be traced to a named unit, not "improves memory".
4. **A cheap causal contrast.** It reuses the frozen arm-building code (`scripts/arena/mechanism_ablation.py`, `raw_session()`, `as_records()`) instead of building new infrastructure, and one exploratory run is small. Examples of acceptable contrasts, not requirements:
   mode 1, ingest user and assistant turns through a separate bank and compare with the user-only bank on the same units;
   mode 2, anchor on the top-k hits, or on the session with the best query overlap, and compare with top-1 anchoring;
   mode 3, extract a date field and resolve it with deterministic `datetime` code, and compare with the same units without it.

State your evidence class for each cited support: measured on a benchmark, verified in code, verified as an artefact in a repository, or only claimed in a paper or README. Do not stretch single-turn retrieval-augmented-generation results to persistent agent memory without saying so.
We ask for at most one to three candidates in total, not per mode. Propose the strongest evidence at the lowest test cost. If no candidate passes all four parts, the request stays open as "waiting for research", which is a correct outcome and not a failure of the search.

## Where an outsider can start

* Cheapest to check is mode 3: no new infrastructure, deterministic post-processing, and a precondition check that can be done on stored data.
* Next is mode 1: one extra ingest path.
* Mode 2 is entangled with Mem0's retrieval, the part that changed most in 2.x.
* Equally welcome: reproduce the offline check in [`REPRODUCE.md`](../../REPRODUCE.md) and tell us a number differs, or report a hole in how a unit was classified.
* Known data defects in the benchmark itself, and what to do about them: [`LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md`](LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md). One of those ids (`370a8ff4`) was a unit in an earlier sample.

## Our commitments

* Units and arms are frozen before any run; unit selection is gold-blind; at most one repair attempt per mechanism.
* The first step of any accepted proposal is the version re-baseline described at the top.
* We publish the result whichever way it falls, nulls and regressions included, with the library versions and n.
* Small-n results are labelled exploratory. Nothing is called a general finding after one small sample.
* This document is a research question. It is not an offer of funding, compute or payment.

## How to answer

Send the design, the contrast, the evidence class of each cited support, the unit that would falsify it, and a pointer to the code if any. In this repository's issue tracker or discussions, if open to you;
the maintainers decide where answers are collected. Corrections to this document, in particular to the classification of a unit, are as useful as proposals.
