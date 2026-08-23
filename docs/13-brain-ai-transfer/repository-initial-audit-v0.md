# Initial repository audit: transfer-map candidates v0

Status: documentation and targeted static-code audit; no benchmark claims reproduced

Audit date: 2026-08-23

## Scope and pinned revisions

| Repository | Revision | Role | License observation |
| --- | --- | --- | --- |
| `FeishuLuo/Evolving-LLM-Agent-Memory-Survey` | `92b5a4b1b25a02e3a053ed0309704e0ad31d3093` | discovery index | root MIT file present |
| `xjtuleeyf/Locomo-Plus` | `059f4e3d38f7f1f96765e8e2cb7de3097551bffb` | cognitive/cue-trigger benchmark | no root license file; README only says to see repository |
| `qinchonghanzuibang/ImplicitMemBench` | `927413bf3f5389bb47c94c2a0ba987e435b101b8` | procedural, priming, conditioning benchmark | root code MIT and dataset CC BY 4.0 files present |
| `ericjiang18/MemCon` | `aa15afc9406aab8854b957ebfea08816997de882` | learned memory-operation controller | README says MIT but no root license file |

The local clones are ignored research inputs. Pinning makes observations repeatable; it does not grant permission, establish correctness, or reproduce a paper.

## MemCon: what the code currently does

Targeted files:

- `hmf/mcp_framework/memory_mdp.py`;
- `hmf/mcp_framework/policy.py`;
- `hmf/mcp_framework/wrapper.py`;
- relevant HMF integrations and README instructions.

Verified operations:

- compact, discretized task/memory state key;
- nine discrete candidate actions, including multiple fixed retrieval settings, plan injection, re-retrieval, consolidation, forgetting, and no-op;
- tabular action values with UCB exploration;
- one terminal task reward distributed backward across every recorded memory action;
- hard-coded goal-type extraction and plan generalization for ALFWorld-like tasks;
- JSON persistence of policy tables and successful action templates.

Material mismatches and risks:

1. The module describes continuous action parameters, but the inspected action space is a fixed list of nine discrete actions.
2. `ENCODE` exists in the enum but is absent from the policy action list; encoding is delegated later rather than selected by the shown controller.
3. The implementation is closer to a contextual bandit with terminal credit than a learned transition model for the declared memory MDP.
4. All co-exposed actions receive the same task-level reward with positional discount. This does not identify which retrieved memory or maintenance action caused success.
5. The `FORGET` branch calls `clear_insights()` when available. It has no visible reversible archive, affected-record receipt, or rare-critical-memory protection at this wrapper boundary.
6. Consolidation/forgetting exceptions are swallowed, so a selected action can silently fail while still receiving outcome credit.
7. A single successful action sequence can be generalized by domain-specific regular expressions and inserted as a `[Proven plan]`; this label is stronger than the evidence and lacks per-plan source/version metadata in the injection text.
8. The wrapper contains task-specific `puttwo` behavior, object vocabularies, and state heuristics. Backend wrapping is broad, but the inspected policy is not yet a universal provider/task-neutral controller.
9. The core `hmf` tree has no matching core test files; numerous repository tests belong to bundled external agent-framework sources rather than MemCon's controller.
10. Loading persisted nested count maps into ordinary dictionaries may make unseen action lookup fragile in partially populated saved states; this needs a direct regression test.

Decision: retain as a high-priority audit and reproduction candidate. Do not copy or promote it. First reconstruct a minimal isolated controller, add deterministic action traces, frozen rules, no-op/random/equal-cost controls, reversible forgetting, and delayed-harm/shift tests.

## ImplicitMemBench: what it contributes

The pinned repository contains released data and evaluators for:

- 15 procedural task files;
- 10 priming task files;
- 10 classical-conditioning task files;
- model-under-test conversations with learning, interference, and test phases;
- paired experimental/control priming evaluation;
- LLM-judge paths for procedural and conditioning outcomes;
- code MIT and dataset CC BY 4.0 licensing.

Useful design contribution: behavior at the probe, especially first response/action, is separable from asking the model to explicitly recall a fact. Paired priming contexts are also more diagnostic than a single exposed condition.

Audit risks:

- headline results depend partly on an LLM judge and its pinned model/prompt;
- model API behavior and sampling configuration must be frozen;
- generation code does not exactly recreate the released benchmark;
- some procedural correctness uses expected-pattern containment, which can reward mentioning an answer rather than performing a complete action;
- conditioning difficulty includes hand-set dimensions based on target difficulty, so it must not be treated as an independently measured cognitive quantity;
- the benchmark exposes behavior within one constructed context; it does not yet test a disk-backed memory over days or provider migration.

Decision: use the released corpus as a benchmark-design reference and possible external evaluation after a deterministic subset and judge-stability audit are created. Keep the word `implicit` operational, not phenomenological.

## LoCoMo-Plus: what it contributes

The repository extends LoCoMo with cue-dialogue/trigger-query pairs intended to test a later response that should use an earlier latent constraint despite low surface overlap. The pinned `locomo_plus.json` contains 401 candidate pair records with relation type, time gap, generating model, lexical/dense similarity scores, and ranks. Its pipeline includes manual filtering stages and an LLM-as-judge.

Audit risks:

- the cognitive judge has no gold answer and asks only whether the prediction is linked to supplied evidence; mere thematic association may score without appropriate constraint-sensitive behavior;
- the released pair file is an intermediate component, while unified conversation construction and evaluation add further transformations;
- cue/query items were model-generated and selected partly through similarity ranks, so generator and selection effects require stratification;
- manual stages need released decisions or a new blind review to reproduce them;
- judge identity, prompt, and variance materially affect the reported score;
- absent explicit repository licensing blocks redistribution or code reuse until clarified.

Decision: preserve it as the best current lead for cue-trigger semantic disconnect. Before comparative use, build a license-safe manifest, deterministic structural checks, relation/time/model strata, human-reviewed action constraints, and judge-free subsets where possible.

## Evolving-memory survey repository

The index is MIT-licensed and actively maintained. It is useful for coverage closure because it organizes papers and benchmarks across storage, reflection, and experience. It does not replace primary reading, negative-result searches, or direct system comparisons. New entries enter the reading queue, not the evidence ledger, until screened.

## Audit outcome

All four repositories remain useful. None is architecture-ready.

```text
survey index -> discovery only
benchmark code -> freeze and validate evaluators
controller code -> isolate operations and falsify claims
brain analogy -> functional test only
```

The most valuable immediate reuse is experimental structure: ImplicitMemBench's first-action/paired controls, LoCoMo-Plus's cue-trigger disconnect, and MemCon's explicit action vocabulary. Their scoring, credit assignment, maintenance safety, and licensing constraints must be redesigned or resolved before integration.
