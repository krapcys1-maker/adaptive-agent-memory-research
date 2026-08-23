# Natural project-history retrieval benchmark protocol v0

Status: source-unit/query contracts revised after primary-source and M1 advisory audits; independent review remains open; no corpus, backend run, or result exists

Experiment ID: `PMLAB-NATURAL-RET-001`

## Purpose

Determine whether local multilingual dense retrieval and a simple sparse-dense hybrid add useful recall over the retained `rg` and SQLite FTS5 baselines on real project work. This benchmark replaces authored paraphrase-heavy evidence with queries that arise from actual research activity.

The result selects a retrieval baseline for later experiments. It does not select the whole memory architecture and it does not measure whether an LLM should answer.

## Hypotheses

H1 — dense semantic value: the development-selected local dense model improves all-required-evidence Recall@5 over FTS5 on the frozen semantic-target strata: paraphrase, Polish/English cross-language cue, and terminology shift.

H2 — complementarity: equal-input RRF improves all-required-evidence Recall@5 over both of its FTS5 and dense components across all answerable strata.

H3 — cost boundary: any gain remains practically useful after embedding time, query latency, peak RAM, on-disk bytes, returned bytes, and energy-proxy runtime are reported.

Failure of H1 leaves FTS5 as the baseline. Failure of H2 rejects hybrid complexity even if dense alone advances. Neither result authorizes graph, temporal, salience, or emotional mechanisms.

## Authentic-query rule

A test query is eligible only if it was recorded before its author saw any candidate backend output or gold evidence search. Its provenance must be one of:

- a verbatim future user question in the project task;
- a question recorded in a research issue or lab notebook before investigation;
- a debugging or decision question recorded before the answer was found;
- a reviewer question logged before evidence selection.

Backend-generated questions, retrospective paraphrases written to fill a quota, and questions derived from filenames or known gold passages are excluded from the confirmatory set. They may enter development only with an explicit `authored_diagnostic` label.

Each query records a UTC timestamp. Only durable records whose valid-time and commit/event time precede that timestamp may be gold evidence. This query-time cutoff prevents future summaries from leaking answers into earlier cases.

Public Git locators may serve as origin receipts. Private origins use independently random receipts or keyed digests whose mapping/key remains outside Git; unkeyed hashes of query text or private locators are forbidden. Verbatim private queries remain in local-restricted storage and public artifacts expose only opaque IDs and aggregate receipts. A pre-output attestation is process evidence, not independent proof of blindness.

## Corpus and source units

The canonical source universe is reconstructed as of each query cutoff from reviewed Git history and append-only project-memory events. Generated model outputs, temporary API work directories, benchmark gold files, raw annotations, caches, vendored repositories, and the prospective query log are excluded.

One model-independent source-unit builder must freeze:

- one project-memory event per unit;
- one Markdown heading section per unit, with parent path, blob hash, heading path, and line locator;
- one CSV or JSONL row per unit when the row is independently meaningful;
- no hidden backend-specific summary, label, entity expansion, timestamp expansion, or filename boost;
- a common size ceiling compatible with the selected E5 input boundary, with deterministic split rules for oversized units;
- stable opaque unit IDs and exact UTF-8 content hashes.

Historical reconstruction enumerates the exact cutoff tree and reads addressed Git blobs, never same-named files from the working tree. Each unit records the declared Git object format and typed object name plus a portable SHA-256 of exact blob bytes. Unit identity excludes the snapshot commit so unchanged content at the same path/locator remains stable across cutoffs; an edit produces a new unit.

Markdown follows CommonMark 0.31.2 block semantics. Search text includes heading-path text plus direct body, while child bodies remain separate units. CSV uses its historical header and source column order; JSONL admits I-JSON objects serialized with RFC 8785 JCS. Symlinks, gitlinks, binary blobs, non-UTF-8 text, malformed rows, and duplicate JSON members fail closed in v0.

The experiment manifest records the single frozen UTF-8 byte ceiling; it is not repeated in every unit. JSON Schema checks shapes only. A deterministic validator must separately recompute canonical unit IDs, audit exact backend projection to `unit_id,search_text`, verify alias uniqueness/canonical selection, enforce path exclusions, and verify receipt generation. Private random receipts use a 128-bit-form CSPRNG identifier; private keyed receipts use HMAC-SHA-256 with the key outside Git. Query capture also records a monotonic sequence, which supports ordering audit but does not prove blindness.

All backends receive byte-identical units. `CURRENT_STATE.md` and other curated summaries form a registered factor: primary analysis excludes them, and a secondary analysis includes them to quantify summary leakage or genuine utility.

## Query strata

Every answerable query has one primary stratum and optional secondary tags:

1. exact identifier or lexical phrase;
2. natural paraphrase;
3. Polish/English cross-language cue;
4. terminology or synonym shift;
5. named entity or specialized term;
6. temporal state or supersession;
7. multi-evidence causal, procedural, or decision reconstruction.

Non-answerable, stale-only, poison-only, conflicting, and incomplete-evidence cases are logged but scored in `PMLAB-NATURAL-COMP-001`, not converted into correct retrieval misses.

## Systems

- B1: frozen `rg` tokenized lexical baseline.
- B2: frozen SQLite FTS5/BM25 sparse baseline.
- C1-dev-a: multilingual E5 small at the pinned revision.
- C1-dev-b: BGE-M3 dense-only at the pinned revision, if the resource gate passes.
- C0: multilingual MiniLM semantic diagnostic; never architecture-selecting.
- C1: one dense arm selected on development and then frozen.
- C2: B2 plus C1 using RRF `score(d) = sum(1 / (60 + rank_i(d)))`.
- O: full independently reviewed relevant-evidence oracle.

Dense ranking uses L2-normalized float32 vectors and exhaustive inner product. Ties use opaque unit ID. RRF inputs each retrieve the same frozen depth selected before test; raw sparse and dense scores are never combined. No reranker or reader is used in the primary result.

## Development, freeze, and test sequence

1. Build an outcome-hidden retrospective development set from authentic past questions and query-time corpora.
2. Audit source-unit leakage and annotation feasibility before running dense arms.
3. Use development only to choose between E5 small and BGE-M3, establish feasible batch/dtype, freeze the common unit ceiling, and choose a reader-pack byte budget for a later secondary analysis.
4. Freeze the selected C1 model and every transformation in a model manifest.
5. Start a prospective query log. Query authors remain blind to all backend output until the query record is immutable.
6. Independently label all relevant, required, stale, forbidden, and acceptable-alternative units. Adjudicate before system labels are revealed.
7. Estimate paired discordance from development, calculate the required test size, and freeze it before prospective backend labels are analyzed.
8. Execute every backend at least three fresh processes with cold and warm-cache order counterbalanced.
9. Analyze opaque backend labels; reveal identities only after the primary table and failure codes are signed.

Development and test never share a query episode. A test query that triggers protocol repair is preserved as invalidated and cannot re-enter a later test.

## Sample-size rule

The primary per-query endpoint is binary `all_required_evidence_in_top5`. A paired design is planned with two-sided alpha 0.05 and 80% power. The required size depends on the expected gain `delta` and total discordant-pair probability `q = p10 + p01`; it is not fixed by a convenient round number.

Approximate planning values for a paired McNemar endpoint are:

| Target gain | q=0.15 | q=0.20 | q=0.30 | q=0.40 |
| --- | ---: | ---: | ---: | ---: |
| 5 percentage points | 469 | 626 | 940 | 1,254 |
| 8 percentage points | 182 | 243 | 366 | 489 |
| 10 percentage points | 116 | 155 | 234 | 312 |
| 12 percentage points | 80 | 107 | 162 | 216 |

The development estimate selects the confirmatory target with its upper uncertainty bound so power is not inflated. The final size is the maximum required by H1 and H2, not the easier of the two, and must also contain at least 30 queries in each of the three H1 semantic-target strata. The table makes the cost of detecting H2's five-point minimum explicit: a strong hybrid claim may require a long prospective collection. If the feasible set is smaller than the calculated target, the run is explicitly exploratory and cannot support a superiority or architecture claim.

The approximation is checked by exact or simulation-based power before freeze. Sample-size recalculation after seeing test backend identities or outcomes is forbidden.

## Outcomes and budgets

Primary endpoint: proportion with every required evidence unit present in top 5.

Secondary retrieval endpoints:

- macro evidence Recall@5;
- Recall@1, MRR, and nDCG@5;
- critical required-unit miss rate;
- stale and poison intrusion at 5;
- acceptable-alternative coverage;
- unique useful evidence per returned KiB;
- p50/p95 warm and cold latency;
- indexing/embedding wall time, peak RAM, index/vector bytes, and corpus growth slope;
- deterministic rank agreement across processes.

Top 5 is the primary rank budget because all arms share source units. A secondary reader-pack comparison uses whole ranked units under one tokenizer-neutral UTF-8 byte ceiling selected on development and then frozen. It must not silently truncate different arms at different semantic boundaries.

## Statistical decision

H1 advances C1 only if its paired point gain over B2 is at least 0.10 on the semantic-target subset, the stratified paired 95% confidence interval excludes zero, no semantic target stratum loses more than 0.05, critical miss rate does not increase, and ranks reproduce exactly.

H2 advances C2 only if its paired point gain is at least 0.05 over each component, both paired 95% confidence intervals exclude zero, no registered stratum loses more than 0.05, and its added query latency is within the frozen deployment budget. This is an intersection claim: hybrid must beat both components.

If statistical evidence is positive but below the practical threshold, record `statistically_detectable_not_practically_sufficient`. If confidence intervals include both useful gain and meaningful harm, record `inconclusive`, never `no difference`.

## Leakage and validity failures

Automatically invalidate a comparison if:

- source units or query text differ across arms;
- the query author saw any candidate output before logging the query;
- test questions were authored to match a known backend weakness;
- gold evidence includes records written after query time;
- model revision, tokenizer, prefixes, pooling, dtype, normalization, or truncation differs from the manifest;
- an ANN or vector-store approximation enters C1;
- a test result is used to select the dense model, chunking, RRF depth, or budget;
- system identities are revealed before the blinded primary analysis freezes.

## Promotion boundary

This benchmark may promote B1, B2, C1, or C2 only as the next retrieval baseline. Product architecture still requires a second corpus, an independently reviewed test, completeness-controller safety, recovery/integrity tests, and a provider-neutral reader comparison.
