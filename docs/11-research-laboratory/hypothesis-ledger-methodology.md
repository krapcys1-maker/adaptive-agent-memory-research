# Hypothesis ledger and verdict gate: methodology (proposal, not adopted)

**Status:** proposal. This is the methodology of a hypothesis ledger that was designed and prototyped in the maintainer's
local coordinator (branch `lab/hypothesis-ledger`, coordinator commits `c429d82` and `799c356`). The prototype is **not
merged there and not enabled** on any live database, and nothing in this repository implements the ledger itself. What this
repository gets is (a) this document, written in English from the coordinator's Polish design document, and (b) the pure
functions the methodology depends on, with tests: [scripts/hypothesis_statistics.py](../../scripts/hypothesis_statistics.py),
[scripts/hypothesis_conditions.py](../../scripts/hypothesis_conditions.py),
[scripts/hypothesis_textsim.py](../../scripts/hypothesis_textsim.py) and
[tests/test_hypothesis_statistics.py](../../tests/test_hypothesis_statistics.py). No result, frozen file or historical
verdict is changed by this document. It complements
[decision-rule-characteristics.md](decision-rule-characteristics.md): that module checks one decision rule before a protocol
is frozen; this document is about how several hypotheses, their tests and their verdicts are recorded and corrected.

**Provenance and limits.** The functions were extracted from the coordinator's `hypotheses.py`, `conditions.py` and
`textsim.py` by a new commit (line-by-line history is not preserved; the original author is the repository maintainer's
account, and the coordinator commits are named above). Logic is unchanged; docstrings and error messages were translated, and
`min_discordant` gained a guard against `alpha <= 0`. The four simulation checks of section 4 run in this repository and pass.
The two "whole gate" simulations in section 4 need the coordinator's database and ledger class, so they are quoted from the
coordinator's test file and **were not reproduced here**. The text below describes the intended design; where it says "the gate
rejects", that is the prototype's rule, not a mechanism running in this repository.

## 1. Source of truth

| Kind of fact | Canonical place | Second copy |
|---|---|---|
| Hypotheses, pre-registered tests, findings (negative ones too), verdicts, experiments | this repository (Git) | a mirror in the laboratory's database with the Git reference and a `provisional` state |
| Tasks, runs, limits, costs, approvals, exposure of held-out sets, reveal receipts | the laboratory's own database | none |

- Writes to the repository go only through an outbox: patch, draft pull request, merge by the maintainer. After the merge the
  event with the same hash is marked `landed`; a difference is a `conflict` and stops the loop.
- `provisional` holds only inside one research program. It does not raise a level and is not a parent outside the program.
- Proposed target file: `data/lab/hypotheses/ledger.jsonl`, append-only, chained by `prev_sha`/`sha`. The grain differs from
  `experiment-registry.csv` (hypothesis x experiment, not experiment), so the registry is not duplicated.

### Experimental memory is not evidence

The memory systems studied in experiments (this repository's memory, Mem0, variants) are **arms**, not a source of truth.

- A hypothesis's `grounds` accept only references with an allowed prefix (`claim:`, `finding:`, `registry:`, `experiment:`,
  `paper:`, `strategy:`, `owner:`, `data:`). A reference to a memory store (`memory:`, `mem0:`, a path containing `mem0` or
  `memory_store`) is rejected.
- A finding is created only from a mechanical verification result (`computed_by` starts with `mechanical:`).
- An arm's memory store is a run artefact: the ledger keeps its hash (`config_sha`, a snapshot in `raw-freeze.json`), never its
  content as evidence.

### Comparing this repository's memory with Mem0 and with no memory

Every arm of a test declares `memory_system.kind` in {`none`, `placebo`, `aamr`, `mem0`, `other`} with `version` and
`config_sha`. The rules of gate G1:

- if any arm has memory (`aamr`, `mem0`, `other`), an arm with `none` must exist;
- a hypothesis with `scope.comparator = "mem0"` needs a `mem0` arm; with `comparator = "none"` it needs a `none` arm;
- the `mem0` arm names the pinned version in this repository (Mem0 1.0.6 with patches under `data/lab/arena/**/vendor-patch`)
  and its hash, not the current release from the network;
- **Mem0 is one baseline, not a ceiling.** "Better than Mem0" means only what that frozen version and configuration say. Further
  baselines join as `other` arms with their own `config_sha`; a claim of superiority over "the competition" needs an arm for
  every competitor it concerns.

## 2. Objects

- **Hypothesis:** one sentence, a research question (RQ1 to RQ5), a kind (`mechanism`, `null` or `artifact`), a scope
  (`mechanism`, `variable`, `corpus`, `direction`, `metric`, optionally `model` and `comparator`), a refutation condition and an
  inconclusive condition written in the closed language of [hypothesis_conditions.py](../../scripts/hypothesis_conditions.py)
  (comparisons of metrics with numbers or other metrics, `all`/`any`/`not`; three-valued evaluation, nothing else is executed),
  `grounds`, origin and generation, a fingerprint of the scope ([hypothesis_statistics.py](../../scripts/hypothesis_statistics.py)
  `fingerprint`), a status and a level.
- **Statuses:** `proposed` to `testing` to one of `supported_exploratory`, `supported_unreplicated`, `refuted`,
  `refuted_unreplicated`, `inconclusive`, `invalidated`, then `promoted`; also `merged` and `retired`. A closed direction is a
  `refuted` or `retired` hypothesis; its fingerprint blocks new registrations.
- **Test:** the pre-registration of a set of rival hypotheses on an experiment from the registry: arms with their memory system,
  a control and a treated arm, the metrics the scorer emits, for each hypothesis a `supports` and a `refutes` condition, the
  **expected outcome** if each hypothesis is true (used to check that rivals are separable), split, family, track, planned
  repeats, determinism, and hashes of protocol, scorer and corpus.
- **Finding:** one per hypothesis and repeat: observed metrics, verification levels, a condition outcome
  (`prediction_met`, `falsified`, `inconclusive`, `invalid`), p, flags `posthoc` and `circular`, a level, and the original
  runner's verdict kept verbatim as `runner_verdict`.
- **Verdict events** and an **outbox** (hash chain); **corpus splits** with a manifest, a seal, an exposure budget, a registered
  candidate and the moment of reveal.

## 3. Gates

**G0, registering a hypothesis.** Reject when: there are no `grounds` or one has a disallowed reference; the question is outside
RQ1 to RQ5; a condition does not parse; a mechanism hypothesis has no rival (`contradicts`) in the ledger or in the same batch;
the fingerprint already exists or belongs to a closed direction; text similarity is at or above the threshold without a
`distinct_from` link with a reason of at least 20 characters; the `builds_on` parent is not `supported_exploratory` or
`promoted` (exception: a deciding test for an `inconclusive` parent); the generation of an agent-proposed hypothesis exceeds
`max_generation` (default 2), which needs the owner.

**G1, pre-registering a test.** Reject when: a hypothesis has no prediction; a condition uses a metric the scorer does not emit;
**no pair of rivals is separated** (hypothesis A's expected outcome satisfies A's `supports` and not the rival's, and the
reverse); `n_units` is below the minimum number of discordant pairs at which the exact McNemar test can reach alpha
(`min_discordant`); there is no control arm, or control equals treated arm; an arm with memory has no `none` arm; a `challenge`
split lacks a sealed unused set and a registered candidate; a `validation` split has an exhausted exposure budget; the family
already has a result (the family is closed); the track already holds `wip_limit` (default 2) registered and unexecuted tests.

**G2, a verdict proposal.** The gate proposes; the owner applies (automatic application of exploratory statuses is off by
default). For each hypothesis, from the findings of its tests:

1. An `invalid` finding (a blocking verification error, or a missing required level) is not a negative result.
2. `posthoc` (registered after the first raw record) and `circular` (the data the hypothesis came from) give at most a
   description: they neither support nor refute.
3. `prediction_met` plus Holm rejecting H0 in the family plus replication (at least `min_repeats` agreeing repeats, or a
   deterministic test) gives `supported_exploratory`; without replication `supported_unreplicated`; without Holm
   `inconclusive` (`threshold_met_not_significant`).
4. `falsified` in at least `min_repeats` agreeing repeats, or in a deterministic test, gives `refuted`; once,
   `refuted_unreplicated`. **Exception:** refuting a `null` or `artifact` hypothesis is a claim about an effect, so it also needs
   Holm to reject; otherwise `inconclusive` (`falsified_not_significant`).
5. Conflicting repeats give `inconclusive` (`conflicting_repeats`).
6. Level: development and validation are `E`; a challenge split after a reveal registered after the candidate is `I1`. Model
   reviews (Claude, DeepSeek, Qwen) never change the level; only the owner sets `promoted`.
7. An owner verdict that differs from the gate's proposal needs a `despite` text of at least 20 characters; both are stored.

## 4. Holm correction

- **Family** = the tests of one pre-registration (protocol) on one split, declared at registration. Members are frozen from the
  first result in the family; a later test makes a new family. Families are not merged across programs: generalising needs new
  data (validation, challenge), not a correction over the laboratory's whole history.
- **Unit of test:** one p per test, computed from the primary repeat (`repeat_index = 0`) with the test declared in the protocol
  (for example the exact one-sided McNemar test, `mcnemar_one_sided`). Repeats are not separate family members; they serve the
  replication requirement of G2.
- **Registered but unexecuted tests** stay in the family with p = 1; so do `invalid` tests. They raise m, so the correction is
  stricter, never looser. A test can be voided only before the first result in the family, with a reason.
- **Procedure** (`holm`): sort p ascending (ties by identifier); for i = 1..m reject when p(i) <= alpha / (m - i + 1); stop at the
  first non-rejection. Adjusted p(i) = max over j <= i of min(1, (m - j + 1) p(j)).
- **An interim result is safe:** unexecuted tests have p = 1, and later smaller p can only lower the adjusted p of earlier
  rejections, so a rejection announced during a family stays valid.
- Holm protects the claim of an **effect**, including one hidden in refuting a null hypothesis. Refuting a mechanism with a
  threshold (for example "V0 - N <= 4") is not a significance test; the replication requirement protects it from noise.

### Simulation checks

| Check | Result | Reproduced in this repository |
|---|---|---|
| Holm equals closed testing with local Bonferroni (an independently written reference), 3000 random families of m <= 6 with ties and unexecuted tests | agree in all | **yes**, `test_holm_equals_closed_testing_reference` |
| Family-wise error rate, 5 true nulls, independent / correlation +0.7 / mixed -0.2 (20 000 simulations each) | <= alpha (+3 SE) | **yes**, `test_holm_fwer_under_global_null` |
| Family-wise error rate with unexecuted tests (p = 1) and partly true effects | <= alpha | **yes**, `test_holm_fwer_with_unexecuted_tests_and_partial_nulls` |
| Exact McNemar with no effect, 5 to 33 discordant pairs | P(p <= alpha) <= alpha (conservative) | **yes**, `test_discrete_mcnemar_null_is_conservative` |
| Whole path G1 to results to G2, 88 tasks, family of 3, 2 repeats, run noise +-0.15, no effect (300 programs) | false `supported_exploratory`: 2/300 | no (needs the ledger class) |
| Same, the true null hypothesis "refuted" (a hidden effect claim) | **217/300 before the correction, 6/300 after** | no |
| Effect +0.15 in one test of three (120 programs) | power 48/120 (40%); true mechanism refuted 0/120 | no |

Consequence for design: with 88 tasks, a family of 3 tests and two repeats, an effect of +15 percentage points is found in about
40% of cases. Deciding tests need either more tasks or smaller families. The last three rows come from the coordinator's own test
file and are reported as such; the simulation noise model is the coordinator's and has not been checked independently.

## 5. The similarity threshold (working value)

0.45 stays a working threshold until it is measured on a separate set. Observations so far: a paraphrase of one hypothesis in
other words scored 0.50 (detected; at 0.6 it would not be); unrelated claims scored 0.0 to 0.09; **a false alarm**: two null
hypotheses from one template for different mechanisms scored 0.49. The module's blind spot is stated in its docstring and tested
(`test_textsim_blind_spot_is_real_a_synonym_paraphrase_is_not_detected`): a paraphrase with no shared words is not detected by
text similarity, and the structural fingerprint has to catch it. Planned measurement: about 60 pairs built from the experiment
registry, the hypothesis portfolio and the hypotheses of earlier experiments (duplicates, paraphrases, different mechanisms
from one template, unrelated), labelled by the owner without seeing the similarity score, a false-positive / false-negative
curve for thresholds 0.3 to 0.7, and a choice by cost (a false positive costs one `distinct_from` reason; a false negative costs
a duplicated experiment). Until then, registering an agent's hypothesis with `distinct_from` is shown to the owner.

## 6. Order that keeps a retrospective test blind

A retrospective test of the gate against past experiments is only blind if the gate code is frozen by a commit before labelling,
the gate's proposals for the labelled cases are generated only after the labels are returned, and every change to the gate code
after that is reported next to the result. Success criterion: no case in which the gate raises a result that the owner labelled
invalid or refuted; every disagreement is settled in writing. **The material of the coordinator's own retrospective test (the
blinded sheet, its key and the labels) is deliberately not published**; publishing a key together with proposals it blinds would
defeat the test.

## 7. Limits on self-confirmation

Generation at most 2 from an owner root; a mandatory rival; only separating tests; no circular and no post-hoc results counted;
a parent only after replication; negative results always included in the input of the next generation; a program envelope (at
most 3 cycles, at most 4 hypotheses per cycle, work-in-progress limit 2). Calibrating the proposer and attacking the leader belong
to a later mission type and are not specified here.

## What is deliberately not in this repository

The ledger class and its storage, the database migration, the runner and scheduler, the agent isolation tests (which describe the
protection of a held-out set, including where its key lives), the import procedure for two earlier experiments, and the
retrospective test's blinded material. They are the coordinator's infrastructure or private by design
([consolidation map](../00-project/consolidation-map.md), section 5).
