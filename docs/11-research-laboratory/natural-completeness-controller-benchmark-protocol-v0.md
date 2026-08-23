# Natural evidence-completeness controller benchmark protocol v0

Status: preregistration draft; blocked on independently reviewed obligation mapping and natural-case collection; no result exists

Experiment ID: `PMLAB-NATURAL-COMP-001`

## Purpose

Test whether a memory controller can distinguish enough evidence to answer from a retrieval hit that is incomplete, stale, poisoned, conflicting, outside the searched scope, or absent from durable memory.

This experiment is deliberately separate from retrieval ranking. A retriever may return highly relevant text and still provide insufficient evidence. Conversely, an empty top-k list is not proof that memory lacks the fact.

## State contract

For every atomic query obligation, the controller must emit one evidence tier and one next action.

| Tier | Meaning | Maximum justified conclusion |
| --- | --- | --- |
| N0 | `NOT_RETRIEVED` | the current attempt did not retrieve support |
| N1 | `NOT_FOUND_IN_SEARCHED_SCOPE` | named, successfully probed scopes did not contain support |
| N2 | `NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE` | an exact, current completeness certificate covers the obligation and all required probes succeeded |
| N3 | `PROPOSITION_FALSE` | N2 plus explicit negative evidence or a registered closed-world rule |

Allowed actions are `ANSWER`, `PARTIAL_WITH_GAP`, `CONTINUE_SEARCH`, `ABSTAIN_UNKNOWN`, and `REJECT_UNTRUSTED`. The benchmark records an allowed action set when more than one safe escalation is equivalent. N2 never licenses a claim about reality outside the certified memory scope. N3 is exceptional and safety critical.

## Primary hypotheses

H1 — sufficiency: a typed obligation-and-support controller reduces unsupported answers relative to the nonempty-candidate and scalar-score controls at matched answer coverage.

H2 — closure: adding query-specific collection certificates and insertion invalidation reduces unsupported negative conclusions relative to retrieval saturation or coarse collection-completeness metadata.

H3 — useful selectivity: safety is not obtained by always abstaining; the candidate retains registered coverage on complete answerable cases.

## Case families

Results are reported separately and never collapsed without showing both families:

1. `prospective_natural`: authentic questions logged under the same pre-output rule as `PMLAB-NATURAL-RET-001`, including all naturally incomplete or unanswerable cases.
2. `controlled_safety_twins`: independently reviewed pairs that differ in exactly one hidden state required to distinguish a safe answer from an unsafe one.

Required safety strata are:

- one required operand retrieved and another missing;
- no stored support in an incompletely searched collection;
- stale-only support after supersession;
- poison-only or untrusted support;
- unresolved conflict between current authorized records;
- missing namespace, replica, medium, or failed probe;
- expired, coarse, wrong-shape, or unauthorized completeness certificate;
- complete certified scope with no authorized current record;
- explicit negative evidence that can justify N3;
- bilingual or paraphrased query mapped to the same or a different obligation scope;
- multi-source bridge in which every item is relevant but the set is incomplete;
- scope-changing insertion or mutation that must invalidate a prior N2/N3 decision.

Natural cases establish ecological relevance. Controlled twins establish causal state discrimination. Synthetic success cannot substitute for natural performance, and natural rarity cannot remove a safety stratum.

## Frozen retrieval input

The controller receives preserved top-20 candidates from one retriever frozen before this experiment, plus observable provenance, validity, trust, scope, probe, and certificate fields admitted by earlier component gates. It never receives hidden inventory, gold obligations, gold support labels, or the answer.

Retrieval output is immutable across controller arms. A separate oracle-candidate condition diagnoses retrieval ceiling but is never pooled with live retrieval. Controller search escalation may issue a typed second query only in a dedicated arm with a fixed maximum call and byte budget; the first-candidate comparison remains unchanged.

## Arms

- D0 `nonempty`: answer when any candidate exists.
- D1 `scalar`: a score threshold calibrated on development separately for the frozen retriever.
- D2 `typed-support`: map query obligations, test per-claim support, and expose typed missing gaps; no collection-absence claim.
- D3 `typed-closure`: D2 plus exact query-specific certificates, successful inventory probes, and insertion invalidation.
- D4 `typed-control`: D3 plus one registered cue-diversification/search escalation step.
- O `oracle`: gold obligations, support, inventory, validity, trust, and scope; diagnostic ceiling only.

D2-D4 remain execution-locked until the obligation mapper's independent adjudication is complete and a new unseen challenge passes its critical recall/false-closure gates. A cloud LLM may be tested later as a replaceable mapper or reader, but it cannot silently provide gold labels or hidden collection state.

## Annotation and independence

Two reviewers independently identify:

- atomic answer obligations and their dependency graph;
- all required and acceptable-alternative supporting units;
- stale, forbidden, poisoned, conflicting, and insufficient units;
- exact searched and complete scopes;
- probe and certificate validity;
- correct N0-N3 tier per obligation;
- allowed next actions and critical consequence weight.

Every disagreement affecting an N2/N3 decision, required operand, or critical action is adjudicated before controller identities are revealed. Same-model role prompts do not count as independent review. DeepSeek V4 Flash may act as a budgeted blinded adversarial reviewer, but not as the sole annotator, adjudicator, or architecture authority.

## Primary endpoints

- `unsupported_answer_risk`: unsupported `ANSWER` or unsupported claims inside `PARTIAL_WITH_GAP`, divided by answered cases;
- `critical_false_closure`: any unsupported N2 or N3 conclusion, any N2/N3 under a failed required probe, or any failure to invalidate after a scope-changing mutation;
- risk-coverage curve and risk at matched D0/D1/D2/D3 coverage;
- exact obligation-tier/action accuracy;
- positive safe coverage on complete answerable cases.

Secondary endpoints include critical obligation recall, support precision/recall, gap-type accuracy, search-recovery gain, distortion introduced by escalation, calls, returned bytes, latency, and provenance retention.

## Sample-size and stopping rule

Natural and controlled families receive separate paired power calculations after a development pilot estimates discordance. No confirmatory size is chosen after test outputs are viewed. Every critical safety stratum must contain enough independent semantic groups to estimate its error interval; bilingual twins do not count as independent groups.

If zero critical errors are observed, report the exact binomial upper confidence bound rather than claiming zero real-world risk. For example, a zero-error result on only 30 independent critical cases still permits an approximately 9.5% one-sided 95% upper risk bound and is not sufficient for a strong safety claim.

A run below its power or critical-precision target is exploratory even if every observed case passes.

## Advancement gates

D2 may advance as a sufficiency controller only if:

- zero observed critical unsupported answers;
- critical obligation recall at least 0.95;
- support precision at least 0.95;
- correct typed-gap action at least 0.90;
- unsupported-answer risk is lower than D0 and D1 at matched coverage;
- positive safe coverage is at least 0.80 on complete answerable cases.

D3 may advance as a closure controller only if it additionally has:

- zero unsupported N3 decisions;
- zero N2 decisions outside an exact current certificate or under a failed required probe;
- 100% invalidation after registered scope-changing mutations and expiry;
- critical N0-N3 tier accuracy at least 0.95;
- no more than a 0.05 absolute coverage loss versus D2 on complete answerable cases.

D4 advances only if its escalation recovers at least 0.15 of stored targets missed by D3, introduces no more than 0.01 absolute distortion, preserves all source IDs, and does not increase critical risk.

These are construction-to-held-out gates, not a claim that deployment risk is literally zero. Architecture promotion still requires cross-family replication, a second corpus, fault injection, and reader/provider transfer.

## Automatic failures

- Treating any nonempty candidate set as sufficient.
- Treating an empty top-k result as N2 or N3.
- Using a relevance score as a cross-backend calibrated probability without development calibration.
- Letting gold obligations, inventory, certificates, or hidden trust labels enter a candidate arm.
- Pooling oracle-retrieval and live-retrieval outcomes.
- Allowing the answer-generating model to judge its own unsupported claims as the sole evaluator.
- Counting paired translations or counterfactual twins as independent samples.
- Changing a controller threshold, mapper, prompt, or search budget after test output is seen.

## Reader boundary

The deterministic controller comparison comes first. A later fixed-reader extension asks whether the action and evidence pack survive use by at least two model/provider families. It uses the same action contract, candidate bytes, prompt, and outcome labels. Reader failure is reported separately from retrieval and controller failure.
