# PMLAB-COMP-C4-001 — factor-separated operational salience protocol

Status: preregistration draft; corpus, labels, runner, and results do not exist

## Purpose

Test whether provenance-bearing consequence and control factors improve useful long-term retention under fixed budgets without causing collateral forgetting, false generalization, stale procedural action, or emotional-language poisoning.

The experiment tests an external memory controller. It does not test whether an LLM feels emotion.

## Unit and causal boundary

Each history contains raw append-only events, target features, temporally adjacent neutral evidence, a later verified or contradicted outcome, and delayed queries/actions. Salience metadata is never evidence for factual truth. It may only propose one of four actions: provisional eligibility, replay scheduling, retention protection, or retrieve-more control.

## Factor matrix

- valence: negative, neutral, positive;
- verified outcome magnitude: 1, 3, 10;
- urgency: reversible, time-limited, irreversible;
- surprise: expected, unexpected-model-change, unexpected-noise;
- controllability: preventable, recoverable, uncontrollable;
- signal source: explicit user, verified outcome, policy, model inference;
- contingency: target feature, peripheral feature, session-wide;
- phase: encoding, post-encoding, retrieval, revision;
- competition: one priority, two compatible priorities, two conflicting priorities;
- controller target: episodic evidence, semantic revision, cached procedure, retrieve-more;
- adversary: none, dramatic irrelevant prose, poisoned consequence claim, repeated corrected alarm.

Development and test must split complete histories, entities, surface forms, factor combinations, and generator templates. At least one held-out combination must reverse the apparent development-set winner.

## Arms

- S0 save/retrieve uniformly;
- S1 relevance plus recency;
- S2 scalar emotion/intensity;
- S3 verified consequence only;
- S4 surprise/prediction error only;
- S5 factor-separated phase-aware controller;
- S6 raw archive with retrieval only and no promotion;
- O reviewed action oracle, used only to validate scoring.

Every arm receives identical raw evidence and disk, maintenance-call, and active-context budgets. Retrieval and reader/action evaluation remain separate.

## Primary outcome

Consequence-weighted decision regret at fixed active-context and derived-memory budgets, macro-averaged across held-out factor families. Lower is better. The primary comparison is S5 against the best non-oracle preregistered arm, selected on development without changing test rules.

## Mandatory guardrails

- quiet-critical evidence recall;
- collateral loss for preceding, following, peripheral, and competing evidence;
- target-feature versus session-wide false promotion;
- contradicted/stale procedure execution;
- false generalization to near-neighbor contexts;
- poison persistence and retrieval intrusion;
- neutral evidence needed to verify a salient summary;
- unanswerable and ambiguous-scope abstention;
- raw-archive recovery and provenance completeness;
- disk bytes, maintenance calls/tokens, and p95 latency.

## Frozen success rule candidate

Before test labels or outputs exist, freeze numeric thresholds and uncertainty procedure. The initial candidate rule is:

1. S5 reduces primary weighted regret by at least 8 percentage points versus the best non-oracle arm and the paired stratified-bootstrap 95% lower bound is above zero.
2. No mandatory guardrail is worse by more than 2 percentage points.
3. The gain appears in at least three distinct factor families and both positive and negative valence; it cannot come only from high-magnitude negative events.
4. Dramatic language without verified consequence receives no extra persistence, and poisoned consequence claims never mutate canonical facts.
5. S5 beats S6 raw retrieval after all maintenance and context costs are counted. If it does not, promotion/control complexity is rejected.

Passing permits replication only. Architecture promotion requires a second corpus family, an independently reviewed label set, and a different reader/provider family where feasible.

## Falsification map

| Result | Conclusion |
| --- | --- |
| S2 wins weighted recall but loses quiet-critical evidence | scalar salience rejected |
| S5 equals S3 | added affect/surprise/control dimensions unnecessary |
| S5 equals S6 | derived promotion/controller unnecessary |
| retrieval improves but reader action does not | localization is retrieval-to-use, not retention |
| high arousal increases stale procedures | subsystem controller rejected |
| poison gains persistence from wording | signal provenance design rejected |
| only development combinations improve | interaction model rejected for generalization |

## Unlock prerequisites

- independent review of factor definitions and outcome labels;
- frozen generator and leakage audit;
- at least 20 cases per primary interaction cell after exclusions;
- matched budgets and a power/sensitivity analysis based on the final unit of inference;
- fixed reader, prompts, versions, and scorer;
- PMLAB lexical baseline complete enough to provide a surviving retrieval control.

Until then, no emotional-salience field is admitted to automatic write, retention, deletion, or ranking decisions.
