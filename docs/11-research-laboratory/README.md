# Research laboratory

Status: reviewed

## Mission

Produce conclusions that another person or model can audit, falsify, and reproduce before the project commits to a product architecture.

The laboratory studies two different objects:

1. **research memory** — whether the project preserves sources, claims, conflicts, decisions, failed attempts, and experimental experience;
2. **candidate agent memory** — whether a proposed mechanism improves retrieval or downstream work under controlled conditions.

The first supports the investigation. It must not be presented as validation of the second.

## Evidence-to-decision pipeline

```text
search protocol
    ↓
source screening and deduplication
    ↓
source card with exact locator
    ↓
atomic claim + limitation + conflicts
    ↓
independent challenge/review
    ↓
synthesis and falsifiable hypothesis
    ↓
preregistered experiment manifest
    ↓
frozen corpus + blinded backend labels
    ↓
deterministic run artifacts
    ↓
statistical and error analysis
    ↓
reproduction or rejection
    ↓
versioned project-memory update
```

## Roles and independence

| Role | May do | Must not do |
| --- | --- | --- |
| Librarian | search, deduplicate, record metadata | promote a paper's abstract into a supported claim |
| Researcher | extract atomic claims and exact evidence | assign final confidence to own extraction |
| Challenger | seek contradictions, boundary conditions, and null results | see a preferred architecture or desired outcome when avoidable |
| Methodologist | freeze variables, metrics, power/repetition plan, and rejection rules | alter them after seeing test results without marking an exploratory run |
| Runner | execute the registered manifest and preserve logs | tune a backend on the held-out test set |
| Analyst | calculate registered metrics and inspect randomized system labels | reveal labels before primary analysis is signed off |
| Reproducer | rerun from public artifacts in a clean environment | depend on the original research narrative |
| Memory curator | append reviewed findings and supersede obsolete conclusions | erase negative or contradictory history |

Separate role prompts are not sufficient independence. High-impact conclusions require a different model family or a human reviewer, plus hidden backend labels and frozen artifacts where feasible.

## Laboratory directories

- `docs/11-research-laboratory/coverage-protocol.md` — how evidence coverage is measured and when searching may pause.
- `docs/11-research-laboratory/research-to-experiment-gate.md` — the enforceable boundary between targeted reading, exploratory tests, frozen confirmation, and architecture promotion.
- `docs/11-research-laboratory/benchmark-ladder.md` — ordered baseline and mechanism comparisons.
- `docs/11-research-laboratory/stage-gates.md` — evidence required before added complexity.
- `docs/11-research-laboratory/minimal-architecture.md` — provider-neutral architecture boundary.
- `docs/11-research-laboratory/optional-api-worker-policy.md` — when a cloud model may enter as a replaceable, review-gated batch worker.
- `docs/11-research-laboratory/deepseek-screening-pilot.md` — preregistered public-metadata admission pilot with a cumulative USD 10 hard cap.
- `data/lab/api-screening/deepseek-v4-flash-screening-125-20260822/source-review-report.md` — deterministic identity audit and abstract-level disposition of all 37 model-included candidates.
- `docs/11-research-laboratory/project-memory-lab-v0.md` — preregistration draft for the first real project benchmark.
- `docs/07-literature/local-dense-hybrid-retrieval-audit.md` — primary-source audit and revision-pinned candidates for multilingual local dense retrieval, exact search, and untuned fusion.
- `docs/11-research-laboratory/natural-history-retrieval-benchmark-protocol-v0.md` — prospective authentic-query protocol for the next matched B1/B2/local-dense/RRF comparison.
- `data/lab/pmlab-natural-history-v0/manifest.json` — machine-readable execution locks, arms, and sample-size rule for that comparison.
- `data/lab/pmlab-natural-history-v0/corpus-eligibility-policy-v0.json` — model-independent inclusion, exclusion, unitization, exact-duplicate, and metadata-visibility rules.
- `data/lab/pmlab-natural-history-v0/corpus-eligibility-audit-v0.md` — pre-builder inventory showing why gold, blind, raw, and generated artifacts cannot be indexed naively.
- `docs/07-literature/natural-history-source-unit-contract-audit-v0.md` — primary-source repair of historical Git reconstruction, stable IDs, CommonMark sections, canonical CSV/JSONL rows, duplicate aliases, backend projection, and private query receipts. A failed oversized M1 packet and compact `needs_revision` disposition are preserved; independent review and builder execution remain locked.
- `data/lab/pmlab-natural-history-v0/independent-contract-review-v0/` — preserved superseded packet. A pre-review inspection found that its oversized-single-block rule lacked whitespace/code-point fallback and reconstruction semantics, so it must not be completed or used as evidence.
- `data/lab/pmlab-natural-history-v0/token-feasibility-v0/` — deterministic label-free byte/token inventory over 1,673 logical units and three revision-pinned tokenizer configurations. It records truncation exposure and rejects percentile-only ceiling selection without choosing a ceiling or authorizing a builder.
- `docs/11-research-laboratory/reuse-characterization-benchmark-protocol-v0.md` — frozen synthetic contract test for FTS5, exact citations, local FastEmbed, RRF, and current/supporting/stale packs; it cannot select architecture.
- `data/lab/pmlab-reuse-characterization-v0/execution-v0/` — deterministic result plus post-hoc failure localization: dense semantic gains coupled to higher forbidden intrusion, RRF below dense, exact citations, and measurable context-budget overhead. The author-operated DeepSeek M1 disposition lives under `data/lab/api-screening/deepseek-v4-flash-reuse-characterization-review-20260823/` and does not count as independent validation.
- `docs/11-research-laboratory/pack-citation-order-benchmark-protocol-v0.md` — frozen then invalidated before execution because per-locator handles could not operationalize source-path reuse. `pack-citation-order-benchmark-protocol-v1.md` preserves the fixture and repairs only the citation treatment to source-path handles plus inline line ranges. Reader behavior remains a separate gate.
- `data/lab/pmlab-pack-characterization-v1/execution-v0/` — 864-pack deterministic result with exact source resolution and repeat hash: compact source handles improve retention at constrained budgets but have fixed footer costs and do not select a reader format or order.
- `docs/11-research-laboratory/pack-reader-benchmark-protocol-v0.md` and `data/lab/pmlab-pack-reader-v0/execution-deepseek-v4-flash-v0/` — completed frozen 128-call bilingual equal-evidence reader pilot. Every arm reached 16/16 group exact answers with zero stale/unresolved citations; one compact-governed Polish condition substituted a valid but non-supporting citation. Compact messages were 24.22% smaller by UTF-8 bytes and 16.00% smaller by provider prompt tokens. All compatibility gates passed, but this single-family authored fixture cannot select a default.
- `docs/07-literature/retrieval-safety-context-order-followup-v0.md` — primary-source follow-up on fusion boundaries, positional reader effects, knowledge poisoning, and indirect prompt injection.
- `docs/11-research-laboratory/natural-completeness-controller-benchmark-protocol-v0.md` — separate N0-N3 sufficiency, abstention, closure, and escalation benchmark.
- `data/lab/pmlab-completeness-natural-v0/manifest.json` — machine-readable controller arms and unresolved execution gates.
- `docs/07-literature/tiered-memory-routing-and-future-utility-audit.md` — primary-source correction of cascade, repository, utility, and current DeepSeek-cost claims.
- `docs/11-research-laboratory/memory-manager-cascade-benchmark-protocol-v0.md` — shadow-only deterministic/cheap/strong manager comparison with typed escalation and no canonical mutation.
- `data/lab/pmlab-memory-router-v0/manifest.json` — execution-locked `PMLAB-ROUTER-001` arms, safety gates, and resource outcomes.
- `docs/11-research-laboratory/future-utility-telemetry-protocol-v0.md` — U0-U5 evidence ladder and staged path from immutable telemetry to safe randomized exposure.
- `data/lab/pmlab-future-utility-v0/manifest.json` — execution-locked `PMLAB-UTILITY-001` phase and causal-identification constraints.
- `docs/11-research-laboratory/future-utility-telemetry-privacy-and-capture-policy-v0.md` — allowlist-first hashed/typed capture contract that prohibits raw transcripts, secrets, and private reasoning.
- `data/lab/pmlab-future-utility-v0/t0/` — completed synthetic T0 validation: exact retry collapse, append-only correction, explicit censoring, privacy rejection, and premature-U5 rejection; T1 remains locked.
- `docs/07-literature/future-utility-causal-privacy-primary-source-audit.md` — primary-source falsification of bundle credit, interference, censoring, propensity, hashing, append-only erasure, and local-first privacy shortcuts.
- `data/lab/pmlab-future-utility-v0/independent-audit-v0/blind/` — deterministic gold-free T0.1 audit packet with fixed questions, subject hashes, blank review form, and attestation; preparation is not independent approval.
- `data/lab/pmlab-future-utility-v0/independent-audit-v0/model-review-disposition.md` — disposition of the frozen DeepSeek cross-family challenge: A07 lifecycle/erasure and A08 security/access are blocking, T1-T4 remain denied, and inaccurate model advice is explicitly rejected.
- `docs/11-research-laboratory/compression-benchmark-extension.md` — preregistered repeated-compaction, model-change, semantic-completion, and factor-separated emotion tests.
- `docs/11-research-laboratory/replay-benchmark-extension.md` — preregistered phase-conditioned replay, compression-throughput, and sampling-safety tests.
- `docs/11-research-laboratory/revision-benchmark-extension.md` — preregistered versioning, non-mutating retrieval, return, and representation-dissociation tests.
- `docs/11-research-laboratory/interference-forgetting-benchmark-extension.md` — preregistered fault localization, interference curves, reversible forgetting, recovery-integrity, and retrieval-neighbor tests.
- `docs/12-interdisciplinary-memory/metamemory-selective-control-synthesis.md` — evidence synthesis and preregistration draft for typed monitoring, cue escalation, stopping, and abstention.
- `data/lab/pmlab-metamemory-control-dev-v0/` — 26-case frozen authored construction corpus and deterministic monitor/control ablation; not held out.
- `data/lab/pmlab-backend-agreement-v0/` — post-hoc real `rg`/FTS5 output analysis showing that agreement within one lexical failure domain does not lower selective retrieval risk.
- `docs/11-research-laboratory/diverse-cue-retrieval-protocol-v0.md` — frozen development protocol isolating valid-time, trust, and bilingual cue interventions after the lexical-agreement falsification.
- `data/lab/pmlab-diverse-cues-v0/` — frozen-protocol result: strong validity/trust/cross-language gains, but the bundle is rejected by the zero-abstention result.
- `docs/12-interdisciplinary-memory/evidence-sufficiency-and-completeness-synthesis.md` — source-backed typology and preregistration draft for answerability, obligation coverage, claim support, and typed gaps.
- `data/lab/pmlab-evidence-sufficiency-dev-v0/` — 36-case frozen construction corpus and policy ablation; gold hybrid validates the state contract while matched-coverage and real-mapping gates remain closed.
- `docs/07-literature/obligation-mapping-primary-source-audit.md` — exact-locator audit of BREAK, schema linking, Spider-Syn, COGS, CFQ, SCATE, SemEval time parsing, and BLINK.
- `docs/11-research-laboratory/obligation-ir-schema-v0.md` — design-freeze candidate separating computation graphs from entity/predicate/time/authorization/certificate scopes.
- `data/lab/pmlab-obligation-mapping-dev-v0/` — bilingual 28-group/56-case construction source, metric-equivalence fixtures, generated payloads, and deterministic validation; not held out or independently reviewed.
- `data/lab/pmlab-obligation-mapping-dev-v0/artifacts/` — repaired deterministic construction comparison; QDMR rules pass discovery/safe-abstention checks but fail entity/predicate and end-to-end promotion gates. The rejected first instrument run is preserved beside it.
- `data/lab/pmlab-obligation-mapping-deepseek-v1/` — frozen optional-model construction comparator; only 45/56 schema-valid predictions, F1 0.710, critical recall 0.607, E2E 0.143, and two false closures. Rejected for promotion.
- `data/lab/pmlab-obligation-mapping-challenge-v0/` — 14-group/28-case paired PL/EN post-arm challenge with disjoint schema/entity identifiers, unseen complete composition signatures, and unresolved safety strata; same-process labels still require independent review.
- `data/lab/pmlab-obligation-mapping-deepseek-challenge-v0/` — unchanged optional-model prompt on the post-freeze challenge; 13/28 valid, F1 0.325, critical recall 0.292, E2E 0.107, two false closures. Rejected.
- `data/lab/pmlab-obligation-mapping-challenge-v0/stage-failure-analysis-v0/` — post-hoc localization showing multi-stage errors in 24/28 rule cases and 21/28 model cases; descriptive only because challenge v0 is spent.
- `docs/11-research-laboratory/factorized-obligation-mapper-repair-protocol-v0.md` — next-stage protocol isolating contract/span, graph, entity, schema, time/authorization, and certificate routing before another integrated challenge.
- `docs/07-literature/structured-output-and-schema-linking-audit.md` — exact-locator audit showing why valid structured output, semantic correctness, executable correctness, schema recall, and schema false positives require separate metrics.
- `data/lab/pmlab-map-stage-dev-v1/` — 72-group/144-row base allocation across all six stages plus a five-group/10-row versioned coverage supplement, schema/catalogs, annotation manual, and blind-review material; still unreviewed and no candidate implementation.
- `data/lab/pmlab-map-stage-dev-v1/manifest.json` — machine-checked 77-group/154-row development corpus with exact spans, backward DAGs, catalog/schema integrity, time/policy inputs, certificate safety invariants, leakage checks, critical quotas, and zero unresolved exercisable label gaps.
- `data/lab/pmlab-map-stage-dev-v1/declared-label-coverage-audit-v1.md` — records the five repaired coverage gaps and explains why `obligation_graph=unauthorized` is non-exercisable without leaking policy input into graph-only scoring.
- `data/lab/api-screening/deepseek-v4-flash-map-stage-advisory-review-20260822/result-manifest.json` — post-freeze blind advisory review: 44/44 valid, 40/44 exact agreement, 28/28 entity agreement, four mechanically contradicted contract objections, and an explicitly excluded confounded `case_validity` field; not independent annotation.
- `data/lab/api-screening/deepseek-v4-flash-map-stage-remaining-review-20260822/result-manifest.json` — blind advisory review of the remaining 110 rows: 104 schema-valid after two unchanged attempts, strict exact 18/110, and field-level evidence that graph operators/spans, time normalization, and certificate status/basis are not independently reproducible under the current manual; USD 0.05700112, gold unchanged.
- `docs/11-research-laboratory/mapper-canonical-equivalence-and-adjudication-plan-v1.md` — post-advisory repair protocol separating mechanical, semantic, and representation disagreement; proposes graph equivalence classes, a canonical time grammar, structured certificate contract v2, a predicate adjudication queue, and the independent-review gate before candidates.
- `data/lab/pmlab-map-stage-dev-v1/independent-adjudication-v1/blind/` — self-contained gold-free reviewer packet revision 1.1 with 67 groups/134 rows: every critical group plus one deterministic ordinary sample per stage, concrete JSON label shapes, versioned catalogs/contracts, canonical manual, blank form, attestation, and artifact hashes.
- `scripts/validate_mapper_independent_review_v1.py` — pre-reveal gate requiring all 67 completed group forms, schema-valid labels for both languages, consistent reviewer identity, source commit and manifest hashes, signed blindness statements, and a receipt that confirms no gold was revealed.
- `scripts/reveal_mapper_adjudication_v1.py` — receipt-gated reveal that preserves author, independent, and advisory labels separately, records field differences, and creates a pending group adjudication queue without mutating gold or permitting candidates.
- `data/lab/pmlab-map-stage-dev-v1/independent-adjudication-v1/internal-priority-index.jsonl` — embargoed-until-label-freeze triage index (40 P0, 25 P1, 2 P2); never send it with the blind packet.
- `data/lab/pmlab-forgetting-dev/` — deterministic 28-case F1 and 56-query F2 development instrument with artifacts and an adversarial review.
- `data/lab/pmlab-forgetting-challenge-v0/` — unseen-template multi-fault and ambiguous entity/time challenge that breaks the development resolver.
- `data/lab/reader-interference-stress-v5/` — first fully audited single-model factorial over stale count, cue quality, order, similarity, and instruction strength.
- `data/lab/pmlab-fault-probes-v0/` — deterministic comparison of cascading passive telemetry with isolated active stage probes and explicit data-loss diagnosis.
- `data/lab/pmlab-fault-probes-robustness-v1/` — 1,972-case stress test of retries, timeouts, false-health signals, correlated probe failures, safe abstention, and abstract probe budgets.
- `data/lab/pmlab-probe-success-audit-v0/` — exact expected localization/cost curve for auditing first-pass healthy results under transient flips.
- `docs/11-research-laboratory/probe-failure-domain-and-reliability-protocol.md` and `data/lab/probe-failure-domain-map-v0.csv` — versioned rules for independence, empirical error rates, replica inventory, and safe physical-loss decisions.
- `data/lab/pmlab-storage-injection-v0/` — real disposable fsync/read/checksum/file-loss construction test on two logical paths sharing Disk 0; explicitly not P10.
- `data/lab/pmlab-forgetting-challenge-v0/parser-v0/` — label-free-at-runtime catalog parser baseline on observed development templates; not held out.
- `data/lab/pmlab-forgetting-challenge-v0/parser-challenge-v1/` — post-freeze language/date perturbation set that falsifies parser v0 generality.
- `data/lab/coverage-matrix.csv` — topic status and gaps.
- `data/lab/search-log.csv` — denominator for saturation claims.
- `data/lab/experiment-registry.csv` — all planned, running, completed, null, and failed experiments.
- `data/lab/phase-gate-status.csv` — current gate decision and blockers for each active experiment family.
- `data/lab/backend-registry.csv` — frozen retrieval ladder and unlock state.
- `data/lab/pmlab-v0-dev/` — 24-query development slice and first B0/B1/B2 instrument report; explicitly not the released benchmark.
- `data/lab/project-memory-lab-v0-construction/` — complete 120-query/176-record authored construction corpus frozen at `612eb06`, with opaque IDs, disjoint 60/60 history splits, a dual blind-annotation packet, and an integrity validator; author labels are not gold and lexical runs remain locked.
- `data/lab/longmemeval-bridge-v0/` — completed content-free 36-ID public transfer diagnostic. After a preserved Unicode-JSONL parser failure, repaired v0.1 produced B1/B2 macro Recall@5 `0.933/0.983`, paired difference `+0.050`, and 95% CI `[0.000,0.117]`; the registered support label is compatible with no difference and has no architecture authority. Both backends failed candidate-null on all six incomplete-answer cases.
- `data/lab/pmlab-v0-lexical-preregistration/` — lexical-v0 protocol frozen at `e111a57`: query-only backend input, exact B1/B2 rules, eleven-stratum primary metric, paired bootstrap, safety guardrails, and an explicit execution lock.
- `data/lab/pmlab-v0-split-audit/` — label-free audit preserving the v0 split as an invalid pre-run instrument after repeated development/test query frames were found; labels and backends remained unseen.
- `data/lab/project-memory-lab-v0.1-construction/` — query-form repair frozen at `cc904dd`; M1 leakage review and role-separated M2 annotation/adjudication are complete under the explicitly non-human model-review fallback.
- `data/lab/pmlab-v0.1-split-audit/` — 300-pair label-free screen with zero descriptive threshold crossings plus a direct author inspection; neither substitutes for independent leakage review.
- `data/lab/pmlab-v0.1-lexical-preregistration/` — unchanged `e111a57` B0/B1/B2/O contract rebound to the repaired blind-query hash; its single M2 exploratory authorization is consumed.
- `data/lab/pmlab-v0.1-lexical-exploratory-m2/` — sealed one-time result: B2-B1 macro Recall@5 +0.0576, stratified 95% CI [0.0030, 0.1212], deterministic rankings, and B2 advanced only as an exploratory sparse baseline; absolute safety/completeness failures remain documented.
- `data/lab/api-screening/deepseek-v4-flash-pmlab-v01-adjudication-m2-20260823/` — frozen A/B disagreement adjudication, complete raw API provenance, and 120-query model-reviewed exploratory gold (95 unanimous, 25 adjudicated).
- `emotion-salience-benchmark-protocol-v0.md` — expanded PMLAB-COMP-C4-001 draft separating phase, target feature, timing, consequence, surprise, controllability, signal provenance, competition, and controller action; no corpus or result exists.
- `data/lab/pmlab-salience-ontology-review-v0/blind/` — gold-free independent-review packet that operationalizes 12 factor boundaries through 24 probes; its acceptance permits corpus construction, never controller implementation.
- `biological-savings-benchmark-protocol-v0.md` — preregistration draft separating retained content, latent reconstruction savings, and final recovered performance; no corpus or runner exists.
- `model-review-fallback-protocol.md` — permits explicitly labelled M1/M2 blind external-model review to prevent indefinite blocking while reserving confirmatory and architecture claims for later H-tier review.

## Non-negotiable practices

- Distinguish discovery leads, screened sources, fully read sources, extracted claims, and independently reviewed claims.
- Record exact paper section/page/figure/table or repository commit and file location.
- Freeze test data before tuning.
- Keep retrieval evaluation separate from reader-model evaluation.
- Preserve every run, including null results and infrastructure failures.
- Use the same corpus, query set, token budget, reader model, prompt, and judge when comparing retrieval backends.
- Report uncertainty, per-category failures, latency, tokens, disk growth, and model calls alongside headline accuracy.
- Never use test-set failures to tune a system and continue calling the same set held out.
- Never label an end-to-end miss as forgetting until storage, index, retrieved set, constructed context, reader, and action probes localize the failure.

## Immediate laboratory milestone

The frozen lexical baseline and public LongMemEval bridge are complete and spent. The next natural-history retrieval and completeness-controller protocols now exist, but execution is locked. Token feasibility is measured but the global ceiling is deliberately unset; first freeze a corrected independent-review packet and validate post-split heading overhead and reconstruction. Only then may a development-only common source-unit manifest and authentic outcome-hidden set be considered. Dense representation may be screened only with exact search and identical units. Storage engines, ANN, graphs, salience, emotion, and product architecture remain downstream. H-tier or cross-family replication remains required for confirmation.
