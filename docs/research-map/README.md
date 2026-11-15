# Research map: memory for agents that act

Compiled 13–15 November 2026 for the change of direction. Possible next steps for the laboratory and for contributors are in [DIRECTIONS.md](DIRECTIONS.md). The rule is the project's usual one: a claim that shaped a decision was checked in the full paper or in the code; anything read only as an abstract is a lead, not a basis.

Verification levels:
- **T**: full text read (method, setup, main tables, limitations);
- **K**: code read at a stated commit;
- **P**: counted or recomputed by us;
- **A**: abstract only.

Coverage is not complete; see the end of this page.

## A. Experience memory (the core of the new direction)

| Work | What it shows | Level | Caveats |
|---|---|---|---|
| AdaMEM, arXiv 2606.05684 (ICML 2026); code `yunx-z/AdaMEM`, Apache-2.0 | Retrieving successful steps **by the current state, every step**: ALFWorld seen 45.2 → 59.3% (Qwen3-4B, 3 runs); with strategy synthesis 65.5%; synthesis without memory 34.8% (worse than none) | T + K | one paper, one model; bank built from successes only; failures excluded |
| MemHarness, arXiv 2607.28272; code `KnowledgeXLab/MemHarness`, Apache-2.0 | Memory reconstructed before acting, trained with GRPO: ALFWorld 85.2% | T + K | without memory at test time 83.0%, so most of the gain is training; its per-memory "utility" is an observational success counter |
| Auto-Dreamer, arXiv 2605.20616 | Offline consolidation with provenance; with a pre-built fixed bank, ordinary methods jump about 40 points over their baseline, with a bank grown from empty they stay near it | T | point estimates without variance; no code found |
| ASSAY ("Not All Skills Help"), arXiv 2606.15390 | Per-skill effects measured by random masking; suppressing harmful skills per task; large AppWorld gains | T | frontier models; per-cell power 38.5% by the authors' own analysis |
| ACE, arXiv 2510.04618; code `ace-agent/ace` | Evolving playbook; in the code only ADD operations are applied | K | in ASSAY's table, ACE falls below the no-memory agent on AppWorld Test-C with GPT-5.1 |

## B. Harms and stability

| Work | What it shows | Level |
|---|---|---|
| "Useful Memories Become Faulty When Continuously Updated by LLMs", arXiv 2605.12978 | Repeated LLM consolidation degrades memory across seven frameworks; episodes carry the gain, abstractions alone fall to the no-memory level | T |
| TraceRetain, arXiv 2606.29178 | On clean ALFWorld with a strong model, memory policies are indistinguishable (ceiling); similar failed entries lower retrieval precision; memory shortens episodes by 37–55% | T |
| Causal Memory Policy, arXiv 2610.02070 | A memory's utility is identifiable only with randomised exposure; one score per memory does not transfer to new queries | T |
| arXiv 2604.27003 | Raw trajectories transfer negatively across different tasks; abstraction is safer | T (two runs per condition) |

## C. Simple baselines and critique

| Work | What it shows | Level |
|---|---|---|
| Raw-RAG, arXiv 2610.30755 | Plain dense retrieval over raw history ranks first in 6 of 7 settings against 12 memory systems (conversation QA) | T |
| Memory Tax, arXiv 2610.34073 | Many memory systems have negative net value against naive retrieval; the loss splits into faithfulness, accessibility and backbone dependence | T |
| Cross-component interference, arXiv 2605.05716 | Enabling every component is always worse than the best subset; effects are not additive | T |
| "Memory in the LLM Era", arXiv 2604.01707 | A method composed from 12 systems' modules ties Zep on LoCoMo; keeping raw messages is key | T |
| LoCoMo audit, `dial481/locomo-audit` | 99 of 1,540 gold answers wrong (6.4%) and a lenient judge | K + P (we recounted the error file and checked three cases against the conversations) |

**Why these simple baselines win, as far as is known.**
- *Raw retrieval:* the authors attribute it to higher evidence coverage, preserved relations, and irrecoverable losses when memory is transformed. These are the authors' analyses; we did not recompute them.
- *Interference:* that it exists is measured; *why* is mostly the authors' hypotheses (competition for context, conflicting instructions).

## D. Fact memory and graphs (side lines for this direction)

| System | What we checked | Level |
|---|---|---|
| Graphiti | deterministic invalidation of facts over time | K |
| Mem0 v3 | extraction is ADD-only | K |
| HippoRAG | personalised PageRank over a graph works | K |
| Synapse | the authors' own release reports that literal spreading activation does not rank better than vectors alone | K |

## E. Random controls and the unit of retrieval (added 15 November 2026)

These works bear directly on ladder rungs 1–5. Taken together, they say that the random-bank question is open for small local models, rather than settled.

| Work | What it shows | Level | Caveats |
|---|---|---|---|
| TRAD, arXiv 2403.06221 (SIGIR 2024); code `SkyRiver-2000/TRAD-Official`, MIT | On the 134 ALFWorld unseen tasks with GPT-4, 2 examples, 3 seeds: random trajectories **of the same task type** 89.8%, fixed human examples 90.6%, retrieval by task description (Synapse) 89.6%, retrieval of **single steps by the current thought, with a window of following steps** 96.8%. The same ordering holds on Mind2Web and in an industrial deployment | T + K (`run_react_random.py` draws from the pool of the task's own type, so "Random" is our rung 3, not rung 2) | GPT-4 near the ceiling; ablations only on Mind2Web |
| ExpeL, arXiv 2308.10144 (AAAI 2024); code `LeapLabTHU/ExpeL`, Apache-2.0 | ALFWorld with gpt-3.5, Table 3 (ablation of example selection): ReAct 40.0%, randomly sampled successful trajectories 42.5±0.8%, reasoning-similarity retrieval 48.5±2.1%, task-similarity retrieval (ExpeL) 59.0±0.3% | T (ablation table) | the paper does not say whether the random row keeps the extracted insights |
| Self-Generated In-Context Examples, arXiv 2505.00234 | Growing the bank with the agent's own successful runs, retrieved at every step: ALFWorld unseen 73 → 89% with gpt-4o-mini (5 seeds). The 73% is a fixed bank of 18 human examples, already retrieved per step, not "no memory". The gain exceeds the upgrade to gpt-4o (88%). Two curation steps reach 93%. Large spread across seeds; some added trajectories lower the score | T | no random-bank control; no code found |
| ExpRAG, arXiv 2603.18272 | Models of 3–8B with a scripted-expert bank: retrieving once at the start ≈ retrieving every step for whole trajectories (64.2 vs 63.8%, k=4); per-step retrieval is the least stable factor across models; a bank of the wrong task types gives little on hard tasks | T | the no-memory arm gets no list of admissible actions (4.5%), so much of the gain is action format |

**What this leaves open for the ladder:**
1. Does retrieval beat a random entry of the same task type for a small model? This is the rung 3 versus rung 4 comparison.
2. Does the unit of retrieval matter more than how often it is refreshed? That is, a whole trajectory versus a window of steps around a similar state.

## F. Harms from format and from stored abstractions (added 15 November 2026)

| Work | What it shows | Level |
|---|---|---|
| MATE, arXiv 2609.35808 | Under the released MemP protocol, a bank in the old ALFWorld action syntax lowers Qwen2.5-14B from 72.4% (no memory) to 20.1%. Rewriting 19 of 877 lines restores 82.1%. With a bank collected by the same executor, raw trajectories are best (79.9%). Reports paired wins and losses with exact McNemar tests | T |
| "More Memory, Worse Agents" (Anti-Persistence), arXiv 2610.27406 | 3 benchmarks × 3 models × 10 rounds: memory of abstractions, or of abstractions plus trajectories, is worse than trajectories alone in 7 of 9 settings. Using a synthesised abstraction once and discarding it beats storing it (Llama, ALFWorld: 54.7 vs 26.7%) | T (main sections) |
| EDV, arXiv 2606.24428 | Reflection can endorse an execution error and store it as a lesson ("self-confirmation trap"): 11% of stored lessons in an annotated τ²-bench Retail subset | A |

## G. Qualitative analyses we ran (added 15 November 2026)

All of these ran offline, with no model calls.

- **Reflexion's published ALFWorld logs** (`noahshinn/reflexion`, MIT; 134 tasks, a retry run and a reflection run):
  - Plain retries at temperature 0 solve 10 of the 50 tasks failed in the first trial at the first retry, and 17 over six retries (best-of-6). At an equal number of trials (6), reflections reach 123 of 134 and plain retries 101, so 17 of the 39 tasks gained with reflections were also gained without them. Only failure-to-success is observable: successes were not rerun.
  - 161 of 200 reflections open with the wording of the single reflection example in the prompt.
  - 17 reflections, in 4 tasks, state that the microwave or fridge must be opened before heating or cooling. ALFWorld's PDDL does not require that.
- **Twenty no-memory episodes of Qwen3-4B-Instruct-2507** from a feasibility run (AdaMEM harness, `valid_seen`; bf16 and FP8):
  - 12 and 14 of 20 solved. 4 of 20 tasks flip between the two runs, which differ in weights (bf16 vs FP8) and in sampling (temperature 0.7). This is far above AdaMEM's 45.2% for the same model on all 140 tasks; see DIRECTIONS Q0.
  - All 3 goals in the adjective form ("put a cool egg in microwave") fail in both runs. Verb-form goals of the same types ("cool some X and put it in Y") mostly succeed.
  - Both "look at X under the desklamp" tasks fail in both runs.
  - Sequential cabinet-by-cabinet search uses up the step limit.
  - These are hypotheses from 20 tasks, not results.
- **CPU checks** with the scripts in `tools/alfworld_cpu/`:
  - Adjective-form goals make up 28% of `valid_seen` and 25% of `valid_unseen`.
  - Every ALFWorld game carries a planner walkthrough in the installed action syntax. Replaying 30 random train walkthroughs on the CPU solved 30 of 30, with all actions admissible, at about 1.5 s per game.
  - ETO's expert trajectories are a median of 8 steps against the walkthrough's 6 for the same games, so public banks show little search.
  - In three widely used public ALFWorld banks (ETO, AgentGym AgentTraj-L, AgentBank), 90–92% of trajectories contain at least one action that does not match the current syntax templates (a regex check, not a replay), mostly the old "put X in/on Y" form of the final placement.

## H. Other method papers, coding agents, benchmarks and older work (added 15 November 2026)

**Level.** Read in full by helper agents, which extracted the numbers. The rows marked ✓ were spot-checked by us in the paper. Treat the rest as T (helper): re-check before citing.

| Work | What matters for the ladder |
|---|---|
| Synapse, 2306.07863 (the table values could not be extracted from the HTML version; not spot-checked) | the cleanest fixed-versus-retrieved contrast: on Mind2Web with GPT-3.5, retrieved exemplars add only +1.4 / +1.5 / +0.2 step SR over fixed ones (cross-task, website, domain); most of the gain comes from format and state abstraction |
| Memp, 2508.06433 (code `zjunlp/MemP`) ✓ | ALFWorld test with GPT-4o: no memory 42.1, retrieved trajectories 74.3, with scripts 77.9; retrieval once by task. Random versus retrieved only on TravelPlanner, where they are close (74.6 vs 73.4), and hard constraints worsen with every memory arm |
| RAP, 2402.03610 | the one paper retrieving windows of steps during the episode (ALFWorld, GPT-3.5: 52.2 → 85.8 with 3 trials). Its plain variant adds memories from the test stream itself, so the gain mixes memory with extra attempts |
| ReasoningBank, 2509.25140 (code `google-research/reasoning-bank`) ✓ (the k sweep) | WebArena +4 to +7 points; one retrieved experience is best (k=1 49.7, k=4 44.4); learns on the test stream with an LLM judge of 72.7% accuracy |
| AWM, 2409.07429 | WebArena 15.0 → 35.5 (GPT-4), learned online from the test stream; rule-based and LLM-based workflow induction perform about the same |
| AutoManual, 2405.16247 | ALFWorld unseen 97.4% (GPT-4-turbo) with rules built online; offline rules are clearly weaker (90.7) |
| Imagine-then-Plan, 2601.08955 ✓ | in one harness and a single run (about 140 tasks, no variance), RAP retrieval adds +9.3 points for Qwen3-8B (19.29 → 28.57) and +1.43 for Llama-3.1-8B-Instruct (21.43 → 22.86) on ALFWorld; it lowers Qwen3-8B's two-object tasks from 25.0 to 4.2 |
| SeqMem-Eval, 2605.15384 ✓ (code `ShenGroup/SeqMem-Eval`, Apache-2.0) | Qwen3-8B on ALFWorld: no memory 52.9, G-Memory 62.9, ExpeL single-attempt 59.3, ExpeL multi-attempt 79.3 (the extra attempts are a confound). On API tasks, online gains largely vanish on the hold-out set |
| Coding agents: SWE-Exp 2507.23361 ✓ (the k sweep), Agent KB 2507.06229, CTIM-Rover 2505.23422, SWE-ContextBench 2602.08316 ✓, subtask memory 2602.21611 | gains of 2–7 points that shrink with stronger models. One negative result (CTIM-Rover: no arm beat the baseline). Retrieval without an oracle can fall below no memory (SWE-ContextBench 22.2 vs 26.3). One retrieved item beats several (SWE-Exp). None has a random-example control |
| Episodic control and case-based reasoning: MFEC 2016, NEC 2017, R2A 2022; the utility (swamping) problem in case bases | episodic memory helps most early, with little data; querying with the raw state alone gave no gain in R2A; a growing case base can cost more than it helps |
| ReMe, 2512.10696 ✓ | BFCL-V3 and AppWorld with Qwen3-8B: no memory 40.33 / 14.97, ReMe 45.17 / 24.70 (Avg@4); A-Mem and LangMem fall below no memory on AppWorld; a model-written "usage scenario" key beats the raw task description (figure) |
| HiPlan 2508.19076 ✓; Adaptive-planning 2408.06458 ✓ | the same failures we saw in Qwen3-4B, in other agents: a skipped cooling step for "put a cool tomato in the microwave"; Gemma-2-9B fetching the desklamp first and substituting a handtowel for a cloth |
| PlyBench, 2608.03420 (abstract and sections) | games with computable optimal moves, as a judge-free test bed for experience memory; a lead for a fresh benchmark |
| EffectMem, EMNLP 2026 Findings (ACL 2026.findings-emnlp.859) ✓ | applicability-gated "contracts" with fallback to the plain policy; Qwen3-8B: ALFWorld 38.3 → 91.8, ScienceWorld 15 → 65, WebShop 28.3 → 54.5 (ReAct → EffectMem; single seed; a multi-agent pipeline per step) |
| CFGM, 2508.15305 | ALFWorld (GPT-4-turbo, 4-fold): ReAct 80.6 → 91.0; key = task description, unit = whole experience plus tips; helper reports k=2–3 best and k=5 falling back to 81.3 |
| HSL, "Spinning Straw into Gold", 2607.04235 (ICLR 2026) | failed runs relabeled as successes for the goals they did reach (90% relabel accuracy on 200 hand checks), used for fine-tuning a 1B model, not as in-context examples |
| ProactAgent, 2604.20572; PlugMem, 2603.03296; REAPER, 2608.03420 | retrieval as an RL-trained action (gain not separable from training); a graph memory evaluated without ALFWorld; in tic-tac-toe, a raw-observation key at least as good as a model-written state description |
| Benchmarks: Evo-Memory 2511.20857, EvoMemBench 2605.18421, MemEvoBench 2604.15774, AMA-Bench 2602.22769, procedural retrieval 2511.21730 | see DIRECTIONS.md section 4a. Evo-Memory has no public code. EvoMemBench's repository has no licence. MemEvoBench measures safety and AMA-Bench in-trajectory recall, not reuse across tasks |

## Not yet read in full

ReMe, ExpGraph, the IBM trajectory-tips work, CMC, SWE-Bench-CL, the ReflAct table for Llama-3.1-8B. We did not find the full text of the NeurIPS 2026 paper "When Does Agent Memory Transfer?". Reading these is a good first contribution: one paper per pull request, with the level of verification stated.
