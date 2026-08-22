# Research-to-experiment gate

Status: reviewed

## Decision

Research does not stop globally before testing begins. The transition is made **per falsifiable hypothesis**. Discovery may continue in parallel, but once a confirmatory experiment is frozen, new reading cannot change that experiment's primary hypothesis, held-out data, metric, threshold, or rejection rule.

The governing question is not "have we read everything?" It is:

> Can another bounded literature search resolve the remaining uncertainty, or must a controlled observation distinguish the alternatives?

If the uncertainty is empirical and the test below can reject the proposal, the project should test rather than continue accumulating sources.

## Boundary A — pause broad discovery for a topic

Broad discovery may pause only under the stopping rule in `coverage-protocol.md`. Saturation is local, dated, database-specific, and reversible. It never means that the field is complete.

Targeted searches continue when they are needed to:

- find a missing null result, replication, boundary condition, method, dataset, or artifact;
- interpret an observed failure;
- check a newly discovered mechanism or terminology;
- re-audit a mechanism being considered for architecture promotion.

## Boundary B — admit a hypothesis to an exploratory test

All boxes are required:

- [ ] A concrete failure or opportunity is observable.
- [ ] At least one decisive primary source was read with an exact locator, or the proposal is explicitly labeled engineering-first with no biological evidence claim.
- [ ] A disconfirmation search and the strongest known alternative explanation are recorded.
- [ ] The computational mechanism is specified as input, state, update rule, and readout.
- [ ] The simplest meaningful baseline and an oracle or upper-bound control are identified where feasible.
- [ ] A characteristic failure case is included.
- [ ] The primary outcome, costs, safety guardrails, and rejection condition are stated before the run.
- [ ] The test is reversible and cannot silently modify canonical evidence.

An exploratory run may debug the instrument, estimate variance, discover failure modes, and refine a later protocol. It must not be used as confirmatory architecture evidence.

## Boundary C — freeze a confirmatory test

Before any held-out result is observed, record all of the following in the experiment registry and manifest:

- immutable corpus and development/test split identifiers;
- hypothesis and direction of the expected effect;
- compared systems and the one permitted mechanism difference;
- retrieved-token, model-call, latency, and disk budgets;
- primary metric and practically meaningful threshold;
- guardrail metrics and automatic safety failures;
- repetitions, uncertainty calculation, missing-data policy, and tie handling;
- reader model, judge, prompts, versions, and random seeds where applicable;
- leakage, contamination, and provenance audit;
- reviewer and blinded labels where feasible;
- explicit outcomes for `advance`, `restrict`, `reject`, and `inconclusive`.

After freeze, a protocol change creates a new version. The original run remains preserved and is reported as exploratory or protocol-invalidated; it is never rewritten to fit the result.

## Boundary D — promote a mechanism toward architecture

A positive exploratory result is not sufficient. Promotion requires:

1. a frozen held-out gain over the immediately simpler baseline under an equal budget;
2. survival of the mechanism's characteristic adversarial case and all safety guardrails;
3. benefit in at least two task families;
4. reproduction on a second corpus and, when a reader is used, a second reader/provider family;
5. provenance, correction, export, and recovery remaining intact;
6. independent review of evidence, labels, analysis, and negative results;
7. a cost-effect size that justifies the added component.

Failure to pass does not delete the idea. The result becomes one of:

- `restricted`: useful only under stated boundary conditions;
- `parked`: insufficient evidence or blocked by an unavailable instrument;
- `rejected`: the registered prediction failed and the simpler baseline remains preferable;
- `inconclusive`: the test could not distinguish the alternatives.

## Anti-analysis-paralysis rule

For each active hypothesis, use bounded cycles:

1. one targeted evidence wave;
2. one mechanism-card revision;
3. one preregistration review;
4. one instrument pilot if needed;
5. freeze or record the exact blocker.

Do not open another general search wave merely because uncertainty remains. Open it only when the missing evidence could change the intervention, baseline, metric, safety rule, or interpretation. Otherwise run the test.

## Research-resumption triggers

Research resumes for that hypothesis when:

- a pilot exposes construct invalidity or an unmeasured confound;
- a frozen experiment produces an unexpected failure pattern;
- a credible contradiction, replication failure, correction, or retraction appears;
- a result transfers poorly across a second corpus or reader;
- the mechanism approaches architecture promotion and therefore triggers re-audit.

## Current project boundary

The project has enough breadth to stop waiting for global literature completeness. It does **not** yet have enough benchmark validity to promote a memory architecture.

The immediate transition is therefore:

```text
targeted reading continues
        +
finish and independently review Project Memory Lab v0
        -> freeze no-memory / rg / FTS5 test
        -> reproduce lexical baselines
        -> unlock one added mechanism at a time
```

Current gate states are tracked in `data/lab/phase-gate-status.csv`.

