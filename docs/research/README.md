# docs/research: index for a newcomer

This folder holds the written record of one experimental campaign: small, preregistered tests of changes to an open-source long-term memory system for LLM agents (Mem0, with Hindsight as a second system),
run on LongMemEval-S. The project is abbreviated AAMR in these documents. Everything here is a lab notebook, not a paper: sample sizes are 4 to 10 questions per test, and the ledger records nulls and
failed replications next to the one positive result.

**One caveat before anything else.** Every measurement in these documents was taken on `mem0ai` 1.0.6 and `hindsight_api_slim` 0.9.1. Mem0 2.x (first released 2026-04-16) rewrote extraction and retrieval,
and nothing here has been re-run on it. See the addendum at the end of the ledger (Entry R) and [`OPEN_QUESTION_THREE_FAILURE_MODES.md`](OPEN_QUESTION_THREE_FAILURE_MODES.md).

## Where to start

1. [`MECHANISM_REGIME_EVIDENCE_LEDGER.md`](MECHANISM_REGIME_EVIDENCE_LEDGER.md). The source of truth. One entry per mechanism and regime, each with the failure it targets, the observed effect, the experiments behind it, a confidence, known counterexamples and a status.
   If a report and the ledger disagree, the ledger wins. Entries are appended, not rewritten; Entry R at the end records corrections and the version caveat. The entry letters are not in chronological order (Entry Q sits before Entry L).
2. [`../../REPRODUCE.md`](../../REPRODUCE.md). What you can re-check offline in a second, with the real output, and what you cannot re-run and why.
3. [`OPEN_QUESTION_THREE_FAILURE_MODES.md`](OPEN_QUESTION_THREE_FAILURE_MODES.md). The standing research question, in English: three named failure modes, the unit ids that define them, and the acceptance filter for a proposal.
4. [`LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md`](LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md). Publicly reported data defects in the benchmark, and which of them touch units used here.

## How to read the headline result

The only mechanism that reached the ledger's top status is Entry H, `RAW_PROVENANCE`: append the raw source session behind Mem0's top-1 hit to its compact context. The status label is `REPLICATED_VALIDATED_TRANSPLANT`,
defined in the ledger as a ladder of "external motivation + isolated transplant + exploratory positive + fresh gold-blind replication + confirmed mechanistic trace, all satisfied". The evidence is 2 repairs in 17 observable units with 0 regressions on legacy versions.
One repair is a question about what the assistant said, whose evidence sits in a turn the harness deliberately drops. The label is procedural, not a significance claim. Context length is a confound: the plus-raw context is about 21 times longer.

## The numbered experiment reports

Report titles use their own mechanism letters ("Mechanism D", "E3", "Stage 2"), which are **not** the ledger's entry letters. This table maps them. Each ledger entry lists its own source experiments too.

| Ledger entry | What was tried | Report |
|---|---|---|
| A, B | read-side rendering of the session date next to each retrieved fact | [`READ_SIDE_TEMPORAL_ANCHOR_V1.md`](READ_SIDE_TEMPORAL_ANCHOR_V1.md) ("E1"), [`TEMPORAL_ANCHOR_FRESH_REPLICATION_V1.md`](TEMPORAL_ANCHOR_FRESH_REPLICATION_V1.md) ("Stage 2"), [`TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md`](TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md) |
| C | harmful sibling-entity distraction: a failure-mode candidate with one observed case (`gpt4_f420262c`), not a mechanism | the E1 report and the archaeology report above |
| D | consolidation that does not override its raw sources (an external concept, never tested here) | none |
| E | an instruction in the extraction prompt to resolve relative dates | [`EVENT_TIME_RESOLUTION_CALIBRATION_V1.md`](EVENT_TIME_RESOLUTION_CALIBRATION_V1.md) |
| F, G | current-state-over-history for superseded facts | [`MECHANISM_B_STATE_SUPERSESSION_DESIGN_V1.md`](MECHANISM_B_STATE_SUPERSESSION_DESIGN_V1.md), [`MECHANISM_B_STAGE1_RESULTS_V1.md`](MECHANISM_B_STAGE1_RESULTS_V1.md) |
| H | append the raw session behind the top-1 hit | [`CLEAN_RAW_PROVENANCE_RETEST_V2.md`](CLEAN_RAW_PROVENANCE_RETEST_V2.md) ("E3"), [`RAW_PROVENANCE_FRESH_REPLICATION_V1.md`](RAW_PROVENANCE_FRESH_REPLICATION_V1.md) ("Mechanism C"); the earlier [`CONTEXT_AND_PROVENANCE_ABLATION_V1.md`](CONTEXT_AND_PROVENANCE_ABLATION_V1.md) came first, and the retest explains why its raw-provenance conclusion was set aside |
| I | a note when the top two retrieval scores are close | [`RETRIEVAL_CONFIDENCE_SIGNAL_V1.md`](RETRIEVAL_CONFIDENCE_SIGNAL_V1.md) ("Mechanism D") |
| J | enumerate same-category entities | [`SAME_CATEGORY_ENTITY_ENUMERATION_V1.md`](SAME_CATEGORY_ENTITY_ENUMERATION_V1.md) ("Mechanism E") |
| K | annotate each retrieved item with its rank and score | [`RETRIEVAL_RANK_ANNOTATION_V1.md`](RETRIEVAL_RANK_ANNOTATION_V1.md) ("Mechanism F") |
| L | one extra retrieval seeded by the top-1 item | [`SECOND_HOP_ASSOCIATIVE_EXPANSION_V1.md`](SECOND_HOP_ASSOCIATIVE_EXPANSION_V1.md) ("Mechanism G") |
| M | rewrite the query as a hypothetical memory (HyDE) | [`HYDE_QUERY_REFORMULATION_V1.md`](HYDE_QUERY_REFORMULATION_V1.md) ("Mechanism H") |
| N | the date rendering of A and B, restricted to duration questions | [`TEMPORAL_ANCHOR_BOUNDARY_V3.md`](TEMPORAL_ANCHOR_BOUNDARY_V3.md) ("Mechanism I") |
| O, P | a second extraction pass that looks for missed or bundled facts | [`EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V1.md`](EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V1.md), [`EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V2.md`](EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V2.md) ("Mechanism J") |
| Q | escalate to the raw session when sampled answers disagree | [`SEMANTIC_ENTROPY_SUFFICIENCY_GATE_V1.md`](SEMANTIC_ENTROPY_SUFFICIENCY_GATE_V1.md); the candidate came from an outside suggestion, reviewed in [`rmc-2026-08-24-001_aamr-review.md`](rmc-2026-08-24-001_aamr-review.md) |

Result files (selections, judged labels, token counts) live under [`../../data/lab/arena/`](../../data/lab/arena/), one folder or file set per experiment.

## Campaign-level documents

* [`AUTONOMOUS_MEMORY_MECHANISM_CAMPAIGN_V1.md`](AUTONOMOUS_MEMORY_MECHANISM_CAMPAIGN_V1.md): final report of the first campaign, which stopped after three consecutive failed mechanism families.
* [`EXTERNAL_DISCOVERY_CANDIDATE_POOL_V2.md`](EXTERNAL_DISCOVERY_CANDIDATE_POOL_V2.md), [`EXTERNAL_DISCOVERY_CANDIDATE_POOL_V3.md`](EXTERNAL_DISCOVERY_CANDIDATE_POOL_V3.md), [`CAMPAIGN_V2_CANDIDATE_SHORTLIST_2026-08-25.md`](CAMPAIGN_V2_CANDIDATE_SHORTLIST_2026-08-25.md): how the second campaign picked candidates from the literature and code of other projects.
* [`HINDSIGHT_INFORMATION_COMPOSITION_ARCHAEOLOGY_V1.md`](HINDSIGHT_INFORMATION_COMPOSITION_ARCHAEOLOGY_V1.md): a diagnosis, with no new model calls, of what information Hindsight and Mem0 put into the context; it carries a correction notice about which Mem0 source it first cited.
* [`RELATED_WORK_AND_POSITIONING_2026-08-24.md`](RELATED_WORK_AND_POSITIONING_2026-08-24.md): related work and where this project sits.
* Budget ledgers, as JSON: [`../../data/lab/arena/autonomous-research-budget-v1/ledger.json`](../../data/lab/arena/autonomous-research-budget-v1/ledger.json), [`v2`](../../data/lab/arena/autonomous-research-budget-v2/ledger.json), [`v3`](../../data/lab/arena/autonomous-research-budget-v3/ledger.json).

Some documents cite files that are not in this repository (for example a "frontier map" of the literature written in a parallel session). Where a link in an older report does not resolve, the file was not published; the ledger does not depend on it.

## The two Polish-named folders

Two folders next to the reports have Polish names and a one-way protocol between this project and an external research agent, a separate automated system that searches papers and code and returns candidate mechanisms. It does not run experiments and has no access to the lab host.

* [`Dokumenty dla Resherchera/`](Dokumenty%20dla%20Resherchera/) ("documents for the researcher"): the **outbox**, written by this project, in Polish. It states what the project can and cannot test now ([`TESTABILITY_ENVELOPE.md`](Dokumenty%20dla%20Resherchera/TESTABILITY_ENVELOPE.md)), the open gaps ([`OPEN_TESTABLE_GAPS.md`](Dokumenty%20dla%20Resherchera/OPEN_TESTABLE_GAPS.md)),
  the mechanisms already tried that should not be proposed again ([`DO_NOT_REDISCOVER.md`](Dokumenty%20dla%20Resherchera/DO_NOT_REDISCOVER.md)), and the requests themselves under [`RESEARCH_REQUESTS/`](Dokumenty%20dla%20Resherchera/RESEARCH_REQUESTS/).
  Its own [`README.md`](Dokumenty%20dla%20Resherchera/README.md) explains the protocol. It is a snapshot, not a source of truth: the ledger wins any disagreement. The standing request, `2026-08-25_research_request_three-precise-failure-modes.md`, is the Polish original of [`OPEN_QUESTION_THREE_FAILURE_MODES.md`](OPEN_QUESTION_THREE_FAILURE_MODES.md); read the English one.
* `Dokumenty z Resherchera/` ("documents from the researcher"): the **inbox**, written by the external agent, in the opposite direction. It is **not tracked** in this repository, so links to it from some documents and from project-memory records do not resolve here.

## Status words you will meet

`DROP` (closed, not pursued), `CALIBRATION_FAILED`, `FAIL_ON_REPLICATION_GATE`, `EXPLORATORY_SUPPORTED` (one small positive sample, not replicated), `REPLICATED_VALIDATED_TRANSPLANT` (defined above),
`UNEXERCISED` (the mechanism never got the chance to act), `DESIGN_PREREGISTERED`. Each is defined where the ledger uses it; none of them is a claim about Mem0 2.x.

## Licence and contact

Documents here are CC BY 4.0, code Apache-2.0 (see [`../../LICENSE`](../../LICENSE) and [`../../NOTICE`](../../NOTICE)). Contributing: [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md). Project orientation: [`../../START_HERE.md`](../../START_HERE.md).
