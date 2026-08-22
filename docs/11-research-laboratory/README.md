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

Release `project-memory-lab-v0`: a small, inspectable benchmark derived from this research project with dated evidence, decisions, supersessions, paraphrases, causal questions, abstention cases, and distractors. It begins with `rg` and SQLite FTS5. No embedding, graph, or salience mechanism is admitted until the corpus, labels, and evaluation script receive independent review.
