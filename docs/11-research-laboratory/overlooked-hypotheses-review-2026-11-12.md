# Overlooked hypotheses about task memory: review of 2026-11-12

Status: review. No model was called and no experiment was registered for this document. It reads four ideas that were
written down in the project and then not followed, checks their external sources, and says which are still worth a test.
Nothing here is a result unless a line says where it was measured.

Why now: an audit of local work on 2026-11-12 found two planning documents that had never been published. One is the
literature map of 2026-08-24, now at
[`../research/GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md`](../research/GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md).
The other is a note of 2026-11-01 that ordered the work as access, then valuation, then use; its translation is
[`../00-project/task-memory-ordering-note-2026-11-01.md`](../00-project/task-memory-ordering-note-2026-11-01.md).
The project ran the first step (E0, a narrow null) and then moved to a writing-agent simulation and to factual
benchmarks. The valuation step (E0b) and the use step (E1) were not run in the form the note describes.

On the same day a first pilot of experience memory for a tool-using agent finished: EXP-PILOT-0, on BFCL multi-turn
base, Vehicle Control, with a local `qwen2.5:14b-instruct`. Its record is on the branch `claude/experience-pilot-v0`
(commit `52487db`, folder `data/lab/experience-pilot-v0/`), which was not merged when this review was written. The
pilot numbers quoted below come from that record. They are a pilot on 30 test tasks in one domain.

## Sources checked

| Source | Checked on 2026-11-12 | What the source says | Difference from the 2026-08-24 map |
|---|---|---|---|
| MAGE, arXiv:2606.06090v2 (EMNLP 2026) | abstract, setup, ablation, limitations | A within-task execution-state tree with compress, validate and revise operations; +7.8 to 20.4 pp task success over baselines and 55.1% fewer tokens on MemoryArena, backend Qwen3.6-27B. Its own table reports about 1.0M and 2.0M tokens per task in two domains. | none in the headline numbers |
| "Honest Lying", arXiv:2605.29463v2 | abstract | Reflexion-style reflections store confident wrong diagnoses; 0 of 121 reflections in 16 frozen ALFWorld environments name the right object; programmatic failure signals raise that to 86% and solve 3 of the 16. | none |
| "Sample More, Reflect Less", arXiv:2607.28576v1 | abstract | At equal token cost, on two mathematics benchmarks and models of 1.5B to 7B, no self-inspection method beats repeated sampling; Self-Refine and forced Reflexion are 3.6 to 10.1 points lower at 7B. | none; note it is about answering, not memory |
| "Useful Memories Become Faulty", arXiv:2605.12978v2 | abstract | LLM-consolidated memory first helps, then degrades, sometimes below no memory; an episodic-only control stays competitive; consolidation should be gated. | none |
| "Right Family, Wrong Skill", arXiv:2606.10388v4 | abstract | Four public skill retrievers reach Recall@3 of 0.903 to 0.944 while exposing a conflicting same-capability skill at a rate of 0.344 to 0.393. | the map quoted an earlier version (0.848 to 0.888 and 0.346 to 0.372) |
| AFTER, arXiv:2606.23127v1 | abstract | Procedural memory gives consistent gains on 382 enterprise tasks (+3.7 to 6.7 points per refinement round); some skills lose effectiveness under transfer. | the map reported only transfer costs (−4.8 to −7.5, up to −11.3); those figures are not in the abstract and were not checked |
| Post-retrieval assembly, arXiv:2606.01435v2 | abstract | On MemoryAgentBench FactConsolidation at 262K: 82% / 93% single-hop and 27% / 41% multi-hop with gpt-4o-mini / gpt-4o; no significant advantage on LongMemEval. | the map quoted 78.0% and 94.8% from an earlier version; those figures are not in the current abstract |

Read earlier in full sections, during the audit of the same day and not again here: Hu, Long and Wang
(arXiv:2604.27003), Xiong et al. (arXiv:2505.16067), MemRL (arXiv:2601.03192), EvoMemBench (arXiv:2605.18421),
SkillEvolBench (arXiv:2605.24117), MemoryArena (arXiv:2602.16313). Everything else the map cites is unverified here.

## 1. Valuation at write time (E0b)

**The idea.** Before asking whether memory helps, ask whether any signal available when an experience is written
predicts its later usefulness better than recency and length. The note proposed to test this at zero cost in a synthetic
world where usefulness is known by construction.

**What exists.** No run. The project's `future utility` protocol is still limited to schema validation. MemRL and
Xiong et al. report that selecting experiences by recorded outcome beats selecting by similarity, so the general claim is
not new.

**What the pilot adds.** One write-time signal was tested in passing. Restricting the pool to turns that the benchmark
checker marked as passed solved 14 of 30 test tasks against 11 of 30 with all turns, and halved the harmed tasks (2
against 4). The difference is not significant (two-sided exact McNemar p = 0.51). The lexical gate on top of that filter
changed nothing (14 of 30, same harms).

The checker label needs gold trajectories, which a deployed agent does not have. A model-free reading of the pilot's
committed training pool (61 turns; computed for this review, descriptive) asked whether a gold-free signal could stand in
for it:

| Trace of the turn | Passed | Failed | Unverified |
|---|---:|---:|---:|
| contains no error result | 17 | 5 | 12 |
| contains an error result | 14 | 8 | 5 |

"No error in the trace" keeps 34 turns, half of them passed, and discards 14 of the 31 passed turns. Those 14 are the
turns in which the agent hit an error and recovered, which is the content one would most want to keep in a domain with a
hidden precondition. The error flag here is a substring test on the stored result text, slightly broader than the
pilot's own parser.

**Verdict: current, in a narrower form.** The open question is not whether outcome-based selection helps but which
signal an agent can compute without gold. Candidates: the turn ended without a forced stop; the last call of the turn
succeeded after an earlier error (recovery); the environment state changed as requested.

**Cheapest test.** Tier E on the pilot's frozen files, no model call: score each gold-free signal by how well it
reproduces the passed/failed label on the training pool, then by the pass rate of test turns that were shown items
selected by it. It would be ruled out if no gold-free signal beats "keep everything" on both counts.

**Do not claim** that success filtering works. The pilot's main threshold (+6 tasks, p ≤ 0.05) was not met.

## 2. Lessons with a scope of applicability

**The idea.** Store an experience as situation, expectation, action, outcome and lesson, with the conditions under which
the lesson holds. The note argued that a lesson without conditions is the source of false analogies.

**What exists.** Nothing in the project stores lessons; the pilot used raw traces only, by design.

**External evidence, which points both ways.** Hu, Long and Wang report negative transfer from raw trajectories (−9.5%
and −7.5%, worse on hard cases) and positive transfer from abstracted insights (+6.5% and +9.0%). Zhang et al.
(2605.12978) report the opposite risk: consolidated memories written by an LLM degrade with repeated updates, and keeping
raw episodes stays competitive. Dixit et al. (2605.29463) show that free-form self-diagnosis confabulates and that
programmatically extracted failure signals do much better. Read together, they favour lessons that are extracted by
rule from the environment's own signals and stored next to the raw episode, and they warn against lessons a small model
writes about itself.

**What the pilot adds.** In Vehicle Control the error message of `startEngine` names the missing precondition. Memory
of passed turns cut those errors from 38 to 18 or 21, an exploratory count added after the results were seen. The
success rate on turns whose solution was absent from memory did not move (28 of 38 with and without memory). So the
raw trace transferred a rule only weakly, and the rule is the thing a lesson would state directly.

**Verdict: current, and the most direct next arm.** A rule-based lesson needs no model call here: from each
error-then-success pair in a trace, emit "function, error text, call that fixed it", scoped to that function name.

**Cheapest test.** One added arm in the confirmatory run that the pilot's record recommends: lessons with scope against
raw passed traces at equal context length, with errors per task and task success both pre-registered. It would be ruled
out if lessons do not reduce precondition errors more than raw traces do, or if they raise harmed tasks.

**Do not claim** that lessons beat traces; no arm has compared them.

## 3. False analogies (negative transfer from a retrieved experience)

**The idea.** A true memory can be applied wrongly when the resemblance is only on the surface. The note asked for decoys
with surface similarity and for negative transfer as a first-class measure.

**What exists.** The mechanism ledger holds two observed cases from the arena (Entries B and C) and one net-negative
mechanism (Entry K), all on question answering with 4 to 10 units. The pilot is the first measurement on an acting
agent.

**External evidence.** Ding et al. (2606.10388) measure the exposure side: a retriever that finds the right skill also
ranks a conflicting sibling in the top three for about a third of queries. Xiong et al. describe the behaviour side,
agents following retrieved experience closely.

**What the pilot adds.**

- Exposure was mostly non-matching. With the success-filtered pool, 84 of 106 test turns were shown two items of which
  neither contained the turn's procedure, even as a skeleton.
- Harm was small and concentrated in the unfiltered pool: 4 tasks harmed with all turns, 2 with passed turns, 2 with the
  placebo from another domain.
- A post-hoc reading of the committed harm list (not pre-registered, 8 cases): in 3 of the 4 harms with the unfiltered
  pool, and in 1 of the 2 with the filtered pool, the agent made a call that the gold trajectory does not contain and that
  appears in the memory it was shown (`fillFuelTank`, `set_navigation`). In the 2 placebo harms it did not. This is what
  imitation of a shown procedure would look like. The base rate of such calls in unharmed episodes was not computed, so it
  is a lead and not a finding.

**Verdict: current.** The pilot's gate did not address it: the calibrated threshold let 91% of turns through, and its
best F1 on training data was 0.52. Similarity of request text is a weak proxy for similarity of procedure in this
domain.

**Cheapest test.** Tier E first: on the pilot's frozen raw files, count for every episode the calls outside the gold
trajectory that occur in the shown memory, split by arm and by harmed or not. Then, in the confirmatory run, add a
random-items-from-the-same-pool arm, which the pilot's record already lists as missing; it separates relevant retrieval
from mere exposure to the domain.

**Do not claim** that memory causes imitation errors; three cases support it.

## 4. Execution-state memory

**The idea.** Organise memory around what the agent did and what later steps depend on, not around content similarity.
The 2026-08-24 map listed this family; no project document followed it.

**External evidence.** MAGE is the checked source. It manages state inside one long task: a tree of subgoal summaries
and recent traces, with summaries validated before they are trusted and a revise operation that branches away from a
flawed segment. Its ablation attributes 4 to 7 pp of task success to each of the three operations. The evaluation uses
tasks of up to hundreds of steps, a 27B model, and on the order of a million tokens per task.

**Fit to this project.** It answers a different question from the pilot. The pilot asks whether experience from earlier
tasks helps a later task. MAGE asks how to keep the working state of one long task intact. BFCL multi-turn tasks average
3.4 turns and about ten model calls, so they do not fragment state. The reported setup is also outside the project's
hardware (a 12 GB GPU) and its call budgets.

**Verdict: defer, with a trigger.** Take it up if the project moves to long-horizon tasks, or if a confirmatory run
shows failures caused by lost within-task state. One element transfers now at no cost: memory writes should be validated
before they become trusted state. That is the same lesson as the pilot's success filter.

**Do not claim** anything about this family from project data; there is none.

## Other findings of the map that bear on these choices

- **Reflection as memory.** Free-form self-diagnosis is unreliable (2605.29463), and at equal token cost
  self-inspection lost to plain repeated sampling on small models (2607.28576, on mathematics). For a 9B to 14B local
  model this argues against any arm in which the model writes its own lessons before rule-based lessons have been
  tried.
- **Consolidation.** The evidence against unconditional LLM consolidation (2605.12978) supports keeping raw episodes as
  the first-class record, which is what the pilot did.
- **Weak backbones.** The map notes that in StateMemBench a 9B model cancelled the benefit of every memory layer. That
  claim was not re-checked. If the confirmatory run adds a second, smaller model, it should be a separate arm with its
  own no-memory baseline.

## Order of work this review supports

The operating doctrine allows at most two designed-but-unexecuted experiments per track and favours Tier E. Within that:

1. Tier E, now: the two model-free readings of the pilot's frozen files described in sections 1 and 3.
2. One confirmatory design: no memory against success-filtered traces on new tasks in a domain with few repeated turns,
   sized for the observed effect, with errors per task pre-registered next to task success, plus two arms from this
   review (rule-based lessons with scope; random items from the same pool).
3. Deferred: execution-state memory; anything in which a model writes or consolidates its own memory.

## Limits of this review

- Most external sources were checked at abstract level only; one (MAGE) in three sections.
- The pilot is one domain with one dominant hidden rule, one model, 30 test tasks, and its primary threshold was not
  met.
- The two descriptive readings of pilot files made here were chosen after the pilot's results were visible.
- The author of this review also wrote the pilot's first specification, so it is not an independent assessment of the
  pilot.
