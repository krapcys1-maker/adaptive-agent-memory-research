# PMLAB-BIO-SAVINGS-001 — retained content versus reacquisition savings

Status: preregistration draft; corpus, runner, reader, and results do not exist

## Purpose

Test whether a compact latent state helps reconstruct useful derived memory after the active cache is purged, without confusing three different outcomes:

- content still available at rest;
- less work needed to rebuild useful state;
- correct final action after rebuilding.

This is the first comparative-biology translation admitted to laboratory design. It tests a systems property, not DNA, methylation, muscle, immune cells, or subjective memory.

## Fixed substrate boundary

Every arm receives the same immutable raw event archive. No arm may delete, edit, or hide raw evidence. Only the derived state surviving a simulated inactive interval differs.

The unit is a complete history containing observations, one or more derived mappings or procedures, a rest boundary, possible corrections or task drift, and a post-rest action query. Histories—not rows—are the unit of splitting and bootstrap inference.

## Strata

1. stable terminology or entity mapping;
2. repeatable tool procedure with an unchanged context;
3. procedure whose policy or context changed during rest;
4. factual summary with a quiet verification record;
5. ambiguous near match that should trigger retrieval rather than reuse;
6. rare critical exception to an otherwise repeated pattern;

Development and test must split entity families, surface templates, procedures, change patterns, and generator seeds. At least one held-out combination must make a familiar latent cue unsafe.

## Arms

- `R0 cold-archive`: no surviving derived state; scan/reconstruct from raw evidence.
- `R1 retained-view`: retain the full previously materialized derived view plus raw fallback.
- `R2 latent-cues`: retain only provenance-bound cue IDs, source ranges, type, validity checkpoint, and reconstruction recipe.
- `R3 retained-summary`: retain a compact natural-language summary plus raw fallback.
- `R4 random-cues`: size-matched random cue metadata plus raw archive.
- `R5 corrupted-cues`: plausible but stale or wrong cue metadata plus raw archive.
- `O reviewed-oracle`: reviewed current mapping/action, used only to validate scoring.

All non-oracle arms receive identical disk, active-context, reconstruction-call/token, and latency budgets. A retained full view is charged for every surviving byte. Raw evidence read during reconstruction is charged separately.

## Timeline and measurements

1. **Acquisition:** expose each arm to the same pre-rest history.
2. **Rest:** purge active context and ephemeral process state; preserve only the registered arm state.
3. **Pre-query audit:** measure surviving derived bytes and whether the raw archive remains byte-identical.
4. **Reactivation:** present the post-rest task and measure evidence bytes, calls/tokens, and elapsed time until a frozen competence threshold is reached.
5. **Final probe:** score the action, evidence attribution, current-validity selection, and abstention.
6. **Recovery probe:** remove the derived state and confirm deterministic recovery from the raw archive.

Report the whole reacquisition curve, not only the last point.

## Outcomes

Primary: evidence bytes plus model/tool tokens required to reach at least 95% reviewed current-action accuracy after the rest boundary.

Secondary:

- zero-shot post-rest accuracy before reconstruction;
- area under the accuracy-versus-reconstruction-cost curve;
- final action accuracy and time to competence;
- stale/forbidden intrusion;
- source and provenance completeness;
- surviving derived bytes;
- deterministic raw-archive recovery;
- per-history transition-cost distribution and worst decile.

## Frozen success-rule candidate

Before outcome labels or outputs exist, freeze the final thresholds and sensitivity analysis. Initial candidate:

1. `R2 latent-cues` reduces median charged reconstruction evidence/tokens by at least 30% versus `R0 cold-archive`, with a history-stratified paired 95% confidence interval excluding zero.
2. Final accuracy is within 2 percentage points of the reviewed oracle and no critical stale/forbidden intrusion occurs.
3. `R2` beats both size-matched `R4 random-cues` and `R5 corrupted-cues`; otherwise the gain is attributable to generic extra state or scorer leakage.
4. The gain appears in at least three strata and the worst decile does not lose more than 5 points.
5. Removing all derived state preserves 100% direct recovery of immutable evidence with correct source IDs.

Passing supports replication of compact reconstruction metadata only. It does not admit a salience controller, weight update, or biological architecture.

## Falsification map

| Result | Conclusion |
| --- | --- |
| `R1` wins only by retaining far more bytes | materialized cache benefit, not compact savings |
| `R2` equals random cues | cue semantics unsupported |
| `R2` fails after task drift | latent priming is unsafe without validity checkpoints |
| final accuracy matches but reconstruction cost does not improve | no savings advantage |
| initial output persists but final adaptation worsens | imprinting/competitive-capture failure |
| population mean improves while worst histories fail | heterogeneous transition policy rejected |
| raw recovery fails | derived state has become an unauthorized canonical store |

## Leakage controls

- no target answer, gold source ID, stratum name, or stale/current label in model-visible IDs;
- generator families split before labels and before runner implementation;
- latent cues created from pre-rest information only;
- changed-policy and near-match cases contain matched surface forms;
- random and corrupted cues are generated before results and hash-frozen;
- scorer and competence threshold are frozen before any candidate run;
- author labels require independent review before confirmatory use.

## Unlock prerequisites

- PMLAB v0.1 independent leakage acceptance and adjudicated gold, or a documented reason this isolated deterministic instrument cannot leak into that baseline;
- frozen corpus generator, split audit, and outcome-label contract;
- independent review of action utilities and rare-critical strata;
- power/sensitivity analysis using histories as the inference unit;
- matched budgets and deterministic recovery test;
- no access to test outcomes while implementing a candidate.

Until these hold, no runner or candidate latent-state policy should be implemented.
