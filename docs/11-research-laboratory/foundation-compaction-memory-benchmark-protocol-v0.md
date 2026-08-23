# Foundation compaction plus memory benchmark protocol v0

Status: preregistration draft; design only; parent execution locked; model-free event/receipt construction passed

Experiment ID: `PMLAB-FOUNDATION-001`

## Question

Does a local evidence-preserving memory layer add delayed task value beyond compaction, filesystem search, FTS5, stronger retrieval, and pinned external memory systems at matched active-context and total-resource budgets?

## Claims this protocol may decide

1. Whether Foundation v0 is a valid lower-bound comparison substrate.
2. Whether external evidence retrieval adds value after a frozen open compactor.
3. Whether the project's adaptive candidate earns complexity over the strongest unlocked baseline.

It cannot establish human-like memory, consciousness, emotion, or universal provider superiority.

## Track R: reproducible arms

- `R0`: recent window only.
- `R1`: frozen open compactor only.
- `R2`: `R1` plus raw filesystem/`rg` retrieval.
- `R3`: `R1` plus FTS5 and exact citations.
- `R4`: `R1` plus pinned local dense retrieval.
- `R5`: `R1` plus deterministic RRF.
- `R6a..n`: `R1` plus one pinned external system per arm.
- `R7`: `R1` plus the project's adaptive memory candidate.
- `O`: oracle evidence pack under the same active-context budget.

Every arm writes the identical authorized raw event stream. A backend may decide what to derive or retrieve, but cannot suppress canonical capture. Compactor output is versioned derived state.

## Track P: provider black boxes

For each provider separately:

- `P0`: native product compaction only;
- `P1`: native compaction plus FTS5/cited Foundation v0 pack;
- `P2a..n`: native compaction plus a pinned external system;
- `P3`: native compaction plus the adaptive candidate.

Do not compare or pool raw scores across different action models or providers. Product version, model, account mode, client/API version, date, compaction trigger, and all reported usage must be captured. An opaque native compactor is evaluated only by inputs and outcomes.

## History families

Each history must include all of the following with immutable event IDs:

- important-now events;
- events important only after a delayed task reveal;
- common facts and rare critical exceptions;
- obsolete facts plus explicit corrections;
- repeated noise and one-off noise;
- plausible but poisoned instructions/data;
- failed attempts, successful fixes, and rationale;
- a fact cheaply re-derivable from current files;
- a fact no longer re-derivable from current files;
- exact identifiers, paths, versions, times, and authorization state;
- bilingual paraphrases where the corpus permits.

The delayed-task reveal is generated and frozen separately from the prefix. No write-side component sees the future query, future task, gold labels, or consequence weights.

## Scale ladder

Run construction tests first, then 100K, 1M, 5M, and 10M cumulative input-token histories where feasible. A scale is a separate stratum; no headline average may hide collapse at the largest history.

Histories are built from stable source units and repeated through multiple compaction cycles. Report exact accepted event count and bytes in addition to nominal tokens.

## Frozen controls

- same canonical history and authorization policy;
- same reader/action model within one comparison block;
- same query and tool surface;
- same active-context token budget measured with the target tokenizer;
- same maximum wall time and declared action-turn policy;
- deterministic seeds where supported and repeated stochastic runs otherwise;
- cache state, hardware, network mode, and concurrency recorded;
- maintenance work counted before the query, not hidden as free preprocessing;
- retrieval output frozen before reader scoring;
- blind backend labels during primary analysis.

Native black-box arms cannot satisfy full reproducibility and therefore never replace Track R.

## Stage diagnostics

For every answer or action, preserve:

1. canonical capture receipt;
2. storage/recovery probe outcome;
3. index membership;
4. candidates per retrieval channel with ranks and raw scores;
5. fusion and filter trace;
6. constructed context with omissions and exact token count;
7. exposure receipt with cited source snapshot/hash;
8. reader answer and citations;
9. executed action, authorization verdict, and external effect receipt;
10. cost, latency, calls, tokens, bytes, and failures.

This prevents an end-to-end miss from being mislabeled as forgetting.

## Primary outcomes

- delayed supported task success;
- counterfactual decision regret under the hidden task reveal;
- critical evidence all-required recall in the delivered pack;
- critical wrong-action rate;
- exact citation support and provenance completeness;
- total resource cost: prompt/output tokens, model calls, USD, p50/p95 latency, action turns, maintenance compute, disk growth.

## Guardrails

- stale/corrected fact use;
- poison or untrusted-instruction execution;
- unsupported plausible detail;
- false promotion of noise;
- negative transfer and repeated-error rate;
- privacy/authorization violation;
- duplicate action or reminder;
- abstention and typed-gap correctness;
- alternate-domain recovery and isolated restore completeness;
- provider portability and deterministic rebuild.

## Decision rules

Foundation v0 is accepted only as a **benchmark floor** if `R3`:

- preserves exact canonical evidence and reconstructs its index;
- produces resolvable citations with zero observed critical stale/unauthorized exposure on frozen safety cases;
- stays within the declared context budget; and
- localizes injected storage, retrieval, pack, reader, and action failures correctly.

An adaptive candidate may advance only if it beats `R3`, the strongest unlocked `R4/R5`, and at least one suitable `R6` arm on delayed supported task success or decision regret in two corpus families, with paired uncertainty excluding zero and no critical guardrail failure. It must also show positive value beyond native compaction in at least one Track-P provider block.

A Recall@k-only gain, one seed, one authored fixture, one model family, or an oracle result cannot promote architecture.

If compaction alone matches memory on short or cheaply re-derivable tasks, report the boundary. If FTS5 plus compaction matches the adaptive candidate at lower cost, simplify or reject the adaptive candidate.

## Stop and review conditions

- any future-query leakage into write-side decisions;
- unmatched active-context budgets;
- changed product compactor or model during a block;
- missing raw event IDs or exposure receipts;
- irrecoverable canonical data loss;
- a scorer changed after seeing labeled arm results;
- external-system version, extraction model, or hidden managed optimization not frozen;
- cumulative API spend exceeding the experiment-specific approved cap.

## Required before execution

- freeze a versioned open-compactor prompt, model, decoding, and maximum output;
- specify subscription-client versus separately billed API access for every Track-P arm;
- select and pin external systems only after repository/license audits;
- build source-prefix and delayed-reveal generators with a leakage audit;
- freeze exact scorer code and consequence weights;
- obtain independent review of the critical histories and actions;
- run model-free construction and fault-localization tests;
- register sample size/repetition and experiment-specific budget.

## Model-free construction checkpoint

`PMLAB-FOUNDATION-CONTRACT-001` freezes the canonical-event and F0-F5 stage-receipt
contracts separately from this parent benchmark. Its exact fixture was committed at
`a7b15d6`; the validator was committed at `ca5d4bc` before execution. The authored
construction run passed 8/8 check groups and rejected all 12 registered invalid
mutations at zero API cost. This satisfies only the model-free canonical and
failure-localization construction prerequisite.

It does not satisfy independent review, unseen-fixture replication, delayed-reveal
leakage control, compactor, reader, external-system, sample-size, scorer, or budget
gates. `PMLAB-FOUNDATION-001` therefore remains execution-locked.

`PMLAB-FOUNDATION-REVEAL-001` separately froze a prefix before reveal/gold
authorship, then froze a three-task counterfactual fork and 14 invalid mutations.
After preserving one failed auditor version and freezing a check-order repair, the
same-author construction passed mechanical L0/L2/L3/L4; L1 remained descriptive
and independent semantic L5 was not performed. This advances the leakage
instrument only. The parent remains locked until L5 and an unseen second-author
fork pass, in addition to all other listed gates.

Evidence basis: `../04-systems/foundation-v0-architecture-decision.md`, `compression-benchmark-extension.md`, and `../04-systems/agentmem-repository-audit-v0.md`.
