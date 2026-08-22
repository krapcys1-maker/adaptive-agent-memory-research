# Interference and active-forgetting benchmark extension v0

Status: preregistration-draft; no test results observed

## Purpose

Determine whether a local memory system can resist interference, reduce the default influence of obsolete information reversibly, recover archived evidence with correct cues, and diagnose whether an end-to-end miss arose at write, storage, retrieval, selection, reader, or action time.

## Shared invariants

- Canonical raw events remain append-only in every non-deletion arm.
- Physical deletion is tested only on disposable synthetic copies and never on the research source of truth.
- Retrieval-only and reader-mediated outcomes are reported separately.
- Every record has an immutable ID, content checksum, valid-time interval, source, and transformation lineage.
- Corpus, token budget, query expansion, reader, prompts, model versions, random seeds, and judges are fixed within a comparison.
- Current-state and historical questions are distinct strata; improving one may not silently destroy the other.

## F1 — Fault localization

Inject exactly one controlled fault per case:

1. capture omission;
2. write truncation or checksum corruption;
3. index omission with intact canonical record;
4. stale or poisoned selection despite gold retrieval;
5. reader failure with exact gold evidence in context;
6. action or evaluator failure after a correct answer.

Controls:

- no-fault pipeline;
- direct-ID canonical read;
- full-record scan;
- oracle evidence context;
- fixed correct-answer executor.

Primary metric: macro fault-localization accuracy across `F0`–`F5`.

Initial success threshold: at least 95% macro localization accuracy, at least 90% in every class, and zero cases labeled storage loss when an exact checksum-valid record is directly recoverable. Any ambiguous case must be labeled multi-fault or inconclusive rather than forced into one class.

## F2 — Proactive and retroactive interference curves

Create entity histories with update counts `{1, 2, 4, 8, 16, 32, 64}` and cross:

- same key versus semantically related keys;
- low versus high value similarity;
- random interleaving versus sequential blocks;
- current-value, historical-as-of, and all-versions queries;
- short versus long delay and distractor density;
- lexical, paraphrase, and cross-language cues.

Arms:

- raw context reader;
- `rg`;
- FTS5/BM25;
- exact entity plus valid-time filter;
- diversity-constrained retrieval;
- oracle evidence.

Primary metric: area under the current-value accuracy curve over log2 update count.

Guardrails: historical-as-of recall, stale intrusion, unsupported value rate, evidence recall per token, p95 latency, and index growth.

Initial success threshold: a candidate must improve the interference AUC by at least 10 percentage points over the immediately simpler equal-budget baseline, keep historical-as-of recall within 2 points, and not increase unsupported values or poisoned-memory selection by more than 1 point. The paired 95% interval must exclude zero.

## F3 — Reversible active forgetting

Label disposable synthetic records as currently valid, superseded, low-utility, rare-critical, poisoned, or legally deleted. Compare:

- no suppression;
- recency-only rank decay;
- retrieval-frequency decay;
- current-validity filtering;
- reversible archive/index unlink;
- context-gated accessibility;
- destructive deletion on disposable copies only.

Primary metric: current-state correct action minus stale/poison intrusion under an equal active-index budget.

Guardrails:

- 100% direct-ID recovery for every non-deletion arm;
- at least 99% provenance and checksum recovery;
- rare-critical recall no worse than 2 points below no suppression;
- explicitly historical queries remain within 2 points of the archive baseline;
- deleted synthetic records are unrecoverable only in the explicit deletion arm.

Initial success threshold: reduce stale/poison intrusion by at least 10 points without violating any recovery or rare-critical guardrail. If reversible archiving matches destructive deletion within 2 points, destructive forgetting is rejected as unnecessary.

## F4 — Cue-dependent recovery and distortion

For records missed by the default query, test a ladder:

1. lexical reformulation;
2. entity and time cue;
3. original task/context cue;
4. alternate-language cue;
5. full-index query diversification;
6. direct-ID or source oracle.

Include misleading cues that share an entity, context, or emotional/consequence label with the target.

Primary metric: correct recovery rate among checksum-valid stored targets.

Safety metrics: wrong-version recovery, false association, unsupported detail, poisoned-record recovery, and recovery without source identity.

Initial success threshold: the typed-cue ladder must improve correct recovery by at least 15 points over default retrieval while increasing each distortion metric by no more than 1 point. Provenance-gated recovery must return the immutable source ID in 100% of accepted recoveries.

## F5 — Retrieval-induced access competition

Repeatedly query one member of a related memory set while holding storage constant, then test unqueried neighbors. Compare:

- retrieval with no index update;
- retrieval-frequency boosting;
- diversity balancing;
- neighbor protection;
- context-scoped retrieval;
- random-query control.

Primary metric: change in recall of unqueried related records relative to unrelated controls.

Initial success threshold: repeated access must not reduce related-record recall by more than 2 points in the no-update invariant arm. If frequency boosting creates a larger decrement, it is rejected as an unguarded utility signal. A mitigation advances only if it removes at least 80% of that decrement without reducing target recall by more than 2 points.

## Required artifacts

- immutable corpus and split hashes;
- event/write receipts and canonical checksums;
- complete stored-memory snapshot;
- index version and candidate scores;
- retrieved IDs and excluded IDs with reasons;
- final context with token accounting;
- reader output, parsed answer, action, and judge output;
- per-stage fault label and confidence;
- full negative, null, timeout, and infrastructure-failure logs.

## Interpretation rules

- `oracle fails` means the reader/task contract is invalid for memory attribution.
- `canonical succeeds; retrieval fails` is an access failure, not forgetting by deletion.
- `retrieval succeeds; context fails` is a selection/construction failure.
- `context contains gold; answer fails` is a reader-utilization failure.
- A recovered answer without matching source identity is not successful memory recovery.
- One positive model result authorizes replication only, never architecture promotion.
