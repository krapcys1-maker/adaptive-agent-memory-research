# Possible directions for the experience-memory ladder

Written 15 November 2026 as input for the autonomous laboratory and for contributors. **These are options, not instructions.** Each one gives the question, a sketch of the design, the cost, what speaks for it and against it, and what a result would mean. The laboratory or the maintainer chooses. **Contributors with a GPU can run any direction in parallel, in small cells**: see section 4c and [VOLUNTEER_COMPUTE.md](VOLUNTEER_COMPUTE.md). How the evidence, questions and directions connect, which results would re-route the work, and what stays fixed versus what the laboratory may decide: [CONNECTIONS.md](CONNECTIONS.md).

Sources and their verification levels are in [README.md](README.md); the CPU tools are in [`tools/alfworld_cpu/`](../../tools/alfworld_cpu/). An independent review of a first draft of this page found over-claims and design gaps; they are corrected here.

## 0. Terms used on this page

| Term | Meaning |
|---|---|
| Rung | One arm of the ladder in the [root README](../../README.md): 0 no memory; 1 fixed expert examples; 2 random entries from the whole bank; 3 random entries of the same task type; 4 whole trajectories retrieved by task similarity; 5 steps retrieved by the current state at every step; 6+ one improvement at a time |
| Rung −1 | Checks before any run: action syntax of the bank, prompt format, frozen task list |
| Reference arm | The arm a comparison is made against (usually the rung below) |
| Family | A group of comparisons decided before the runs, corrected together for multiplicity (Holm) |
| Flip | A task whose outcome differs between two runs |
| Walkthrough | The planner solution stored in every ALFWorld game file |
| `synapse` mode | AdaMEM's built-in arm retrieving whole trajectories by task |
| T (helper) | Read in full by a helper agent; not spot-checked by us unless marked ✓ |

## 1. What the evidence says, and how strongly

**1. A bank of successful runs helps a prompted agent on ALFWorld, in two independent studies.**
- Self-Generated ICL (2505.00234): growing the bank with the agent's own successes raises gpt-4o-mini from 73% to 89% on unseen tasks (5 seeds). The 73% is not "no memory": it is a fixed bank of 18 human examples, already retrieved per step.
- AdaMEM (2606.05684, Qwen3-4B, seen tasks):
  - main table: 45.2% without memory, 54.0% with AdaMEM;
  - ablation (Table 3): 59.3% with memory and no strategy, 65.5% with both;
  - strategy synthesis without memory: 34.8%;
  - decoding temperature 0.7.

**2. Action format can wipe out the gain.**
- In MATE (2609.35808), a bank in an older ALFWorld action syntax drops Qwen2.5-14B from 72.4% to 20.1% (temperature 0, seed 0, one run). With the 72B model and gpt-5.4-mini the drop is about 18–19 points.
- Our regex check (`check_bank_syntax.py`, not a replay): 90–92% of trajectories in ETO, AgentTraj-L and AgentBank contain an action that does not match the current syntax templates.

**3. Abstraction: the evidence is mixed.** Here "abstraction" means rules or summaries written by the model and stored.
- Against stored abstractions:
  - 2610.27406: abstraction memory is worse than trajectories in 7 of 9 settings, and stored abstractions are worse than discarded ones;
  - 2605.12978: repeated LLM consolidation degrades memory.
- For stored abstractions:
  - AdaMEM: synthesis on top of memory, 65.5 versus 59.3;
  - AutoManual: 97.4% with online rules;
  - 2604.27003: abstract insights transfer better than raw trajectories across tasks.
- Separately, ExpRAG (2603.18272) shows that memory of *failures* helped only after retrieval-aware fine-tuning.

**4. Noise is large, but our estimates of it are rough.**
- Two runs of Qwen3-4B on the same 20 `valid_seen` tasks (AdaMEM harness, temperature 0.7, bf16 versus FP8 weights) flip 4 of 20 tasks. That mixes sampling noise with a weight change. With 20 tasks, the 95% interval for 4/20 is roughly 8–42%.
- In Reflexion's published logs (temperature 0), a single retry of the 50 failed tasks solved 10 (84 → 94 of 134). That counts only failure-to-success, since successes were not rerun. The often-quoted 17 accumulate over 6 retries, so that figure is best-of-6.
- The power figures in section 6 assume a symmetric flip rate of 13% or 20%. They are planning numbers, not measurements.

## 2. What is open

**Q0. Does AdaMEM's gain reproduce here at all?** Two facts make this uncertain:
- Our 20-task sample gave 60–70% without memory, against AdaMEM's 45.2% on all 140 `valid_seen` tasks with the same model. Either these 20 tasks are easier, or the harness settings differ.
- That gap changes the headroom and the power assumptions.

**Q1. Does retrieval beat a random entry of the same task type, for a small model?**
- With GPT-4, TRAD finds random same-type examples equal to task-similarity retrieval (89.8 vs 89.6). This was checked in its code.
- ExpeL's Table 3 (gpt-3.5), an ablation of example selection, gives random 42.5±0.8, reasoning similarity 48.5±2.1 and task similarity 59.0±0.3. The paper does not say whether the random row keeps the insights.
- Nobody has measured this for a 4B local model.

**Q2. What is the right unit of retrieval: a whole trajectory, a window of steps, or one step? And does refreshing every step matter?**
- ExpRAG: whole trajectories retrieved once are about as good as whole trajectories retrieved every step.
- TRAD: single steps with a window of following steps clearly win.

**Q3. Which bank source helps which failure?** The options are planner walkthroughs (free, but they never search), the agent's own successes (cost GPU time), or a translated public bank.

**Q4. Does retrieval matter more for weaker models?**
- This is suggested by Q1.
- One single-run table (Imagine-then-Plan, 2601.08955, about 140 tasks, no variance) shows RAP adding +9.3 points for Qwen3-8B and +1.4 for Llama-3.1-8B-Instruct. In the same table RAP *lowers* Qwen3-8B's two-object tasks from 25.0 to 4.2.

**Q6. What should the query be?** The evidence is scattered: TRAD retrieves by the agent's thought; Self-Generated ICL by reasoning after the first step; R2A found a raw-state query gave no gain; ReMe (2512.10696) found a model-written "usage scenario" key beats the raw task description (figure only); AdaMEM retrieves by the current state. No one compares these keys for step retrieval with a small model.

**Q7. How should a retrieved entry be presented?**
- Classic in-context learning work (Min et al. 2022, 2202.12837, classification tasks) found that demonstrations work largely through format, the label space and the input distribution: random labels barely hurt.
- For agents, 2606.20978 kept action sequences identical and changed only their organisation. On 43 web tasks with vague descriptions, actions grouped into named subgoals raised the pass rate from 76.7% to 90.7% (win-loss 6:0, paired permutation test), and flat logs gave a smaller, non-significant gain. On 42 precisely described tasks no format helped.
- Our most systematic failure (a skipped transform in adjective-form goals) is a missed subgoal, so presentation may matter as much as selection.

**Q5. Which failures can memory fix at all?** These are hypotheses from our 20 episodes only:
- goals in the adjective form ("put a cool egg in microwave") fail 3 of 3 in both runs. Other models show the same failure: HiPlan reports the skipped cooling step for "put a cool tomato in the microwave" ✓, and 2408.06458 reports Gemma-2-9B fetching the desklamp first and substituting a handtowel for a cloth ✓. Nobody has tested whether the phrasing itself causes the failure;
- "look at X under the desklamp" fails 2 of 2;
- cabinet-by-cabinet search uses up the step limit.

## 3. Checks worth doing before any memory arm

These are cheap; several need no GPU.

| Check | Why | How | GPU |
|---|---|---|---|
| Action syntax of the bank | the MATE effect | `check_bank_syntax.py` (regex). For walkthroughs and translated banks, replay with `replay_walkthroughs.py` | no |
| Frozen, stratified development list | adjective-form goals are 28% of `valid_seen`. In a paired design the draw cannot fake a difference between arms, but it decides how representative the result is and whether a heterogeneous effect is visible | `goal_phrasing.py`. Stratify 60 tasks by task type × phrasing (about 4–6 tasks per cell) and freeze the list (#176). **Exclude or flag the 20 feasibility tasks** that generated the Q5 hypotheses | no |
| Task identity | AdaMEM's ALFWorld environment collects game files with an **unsorted `os.walk`** and assigns validation games by index (`game_files[start_idx + i]`), so "the first 20 tasks" depends on the file system and can differ between machines. Our 20 feasibility tasks are such an arbitrary subset, with 7 of 20 plain pick-and-place against 35 of 140 in the split | select games by explicit path from the frozen list (or sort the file list) and log the game path of every episode | no |
| Response format | the model often writes `<thinking>` instead of `<think>` and sometimes omits `<action>` | count unparsed steps per arm. A tolerant parser, if used, applies to all arms | no |
| Rung 0 content | AdaMEM's no-memory prompt lists admissible actions and shows no examples, so rung 1 adds both examples and prompt length | write down what each rung's prompt contains, and its token count | no |
| Retriever sanity | MiniLM truncates at 256 tokens. A retriever should at least return the right task type | offline: the share of retrieved entries of the right type; the effect of truncation | no |
| Noise floor | flips are frequent | rung 0 with 3 seeds on the frozen list | yes |

## 4. Candidate directions

**Cost basis.** Qwen3-4B FP8 in the AdaMEM harness runs 20 tasks in about 1 hour with 20 environments in parallel, so 60 tasks × 3 seeds ≈ 9 hours per arm.

**Rules for every direction:**
- **Matched budget.** Every memory arm shows the same number of entries k and the same retrieved-text budget, as the root README promises ("same amount of retrieved text"). Log prompt tokens and truncation per arm.
- **Seeds.** A seed means a separate sampled run at a stated temperature, not a pairing device. AdaMEM decodes at 0.7. At temperature 0, three "seeds" would be near-copies.
- **No learning on the test stream.** Several published gains mix memory with extra attempts and a reward or judge signal on the test tasks themselves: RAP's plain variant, AWM online, ReasoningBank, Memp's update arm, and the multi-attempt ("MT") arms in SeqMem-Eval. Build the bank from `train` only, freeze it, and evaluate the frozen bank. A bank that grows online (a rung 6+ option in the root README) is a separate arm with its own trial budget, evaluated on tasks it has not seen.
- **Leakage.** `valid_seen` shares scenes with `train`, so a `train` bank can reveal where objects lie. Expect, and pre-register, a smaller effect on `valid_unseen`.

### D0. Reproduce before building

- **Question:** Q0.
- **Design:** on the frozen list, run AdaMEM's existing arms: no memory, `synapse` (whole trajectories by task) and the step-level mode without strategy. Use 3 seeds. This needs a bank from the agent's own `train` runs, as AdaMEM builds it.
- **Cost:** about 3 arms × 9 h, plus the bank (direction D3b).
- **For:** if the published gain does not appear here, every later rung is moot. The step needs no new code.
- **Against:** it does not answer Q1 by itself.

### D1. The ladder as planned

- **Question:** Q1, and the size of each step.
- **Design:** rungs −1, then 0 (3 seeds), 1, 2, 3, 4 and 5, all under the matched budget.
- **Not one change per rung.** Rung 4 → 5 changes three things: the unit (trajectory → steps), the refresh (once → every step) and the key (task → state). It may also change the bank, because AdaMEM's step-level bank comes from the agent's own runs while the ROADMAP's first bank comes from walkthroughs. To attribute a 4 → 5 gain, add an intermediate arm: whole trajectories by task similarity, refreshed every step. State whether rungs 2 and 3 refresh every step (the root README says rung 2 does).
- **Placebo option:** examples of the same length taken only from *other* task types, a variant of rung 2. It separates "the prompt got longer and showed the format" from "the content was relevant". ExpRAG suggests much of a gain can be format.
- **Cost:** about 6–7 arms × 9 h ≈ 2.5–3 days of GPU.
- **For:** a clear, cumulative story. A **pre-specified equivalence margin** between rungs 3 and 4 (for example ±5 points) turns a null result into information. Without it, a null result on 60 × 3 only says "smaller than about 10 points".
- **Against:** long. The ROADMAP's stop rule ("rung 5 does not beat rung 2 beyond noise") needs a numeric threshold written down before the runs.

### D2. Failure census first

- **Question:** Q5. How much of the failure mass is each failure type?
- **Design:** rung 0 on the 140 `valid_seen` tasks, 1–3 seeds. Tag every failure by rules applied to the action log (#177):
  - format failure;
  - adjective-form goal with a skipped transform;
  - desklamp procedure;
  - search exhausted the step limit;
  - two-object bookkeeping;
  - loop.
- **Cost:** about 7–21 GPU hours.
- **For:** turns 20-episode hypotheses into counts, sets predictions for D1, D3 and D4, and gives the noise floor as a by-product.
- **Against:** no memory comparison yet. Tags need a hand check on a sample.
- **Caution:** if slices for D6 are derived from this census, take them from tasks that are not later used to compare arms, or define them from the goal text alone, as `goal_phrasing.py` does.

### D3. Bank source as the variable

- **Question:** Q3.
- **Design:** the same retrieval with three banks:
  - (a) planner walkthroughs replayed on the CPU;
  - (b) the agent's own successes on a subset of `train`;
  - (c) a translated public bank, verified by replay (#178).
- **Cost:** (a) and (c) need no GPU to build. (b) needs `train` episodes: a few hundred for a small bank (about 5–15 GPU hours), or all 3,553 for AdaMEM's full bank (1,596 successes; roughly 180 GPU hours, a natural job to split across volunteers); Self-Generated ICL got most of its gain within the first 100 training tasks. Then 3 arms × 9 h.
- **For:** a cheap axis that the literature mixes up: ExpRAG uses scripted experts, Self-Generated ICL and AdaMEM the agent's own runs.
- **Against:** bank (b) depends on the agent's noisy success on `train`. Walkthroughs are short (about 6 steps) and our successes are longer (median about 8–9 steps), so prompt budgets must be matched.
- **Public banks barely search either.** ETO trajectories are only about 2 steps longer than the planner walkthrough for the same game (median 8 vs 6 over 3,118 `train` games, counted on the CPU). Only the agent's own runs, or those of another agent that explores, show real search.
- **Prediction to test:** walkthroughs help with procedure failures (adjective form, desklamp) but not with search.

### D4. Unit of retrieval

- **Question:** Q2.
- **Design:** one bank, one similarity, the same budget, four units:
  - a whole trajectory retrieved once;
  - a whole trajectory refreshed every step;
  - a window of steps around the most similar state, refreshed every step (TRAD, Self-Generated ICL);
  - a single step, refreshed every step.
- **Cost:** 4 arms × 9 h. The bank and embeddings are shared, and embeddings run on the CPU.
- **For:** the literature disagrees here, and nobody has the answer for small models.
- **Against:** windows and whole trajectories differ in length, so the budget must be held fixed by truncation or by k.

### D5. Model strength × retrieval

- **Question:** Q4.
- **Design:** rungs 0, 3 and 5 for a weaker model, the main 4B model and, optionally, a stronger quantised one.
- **Confound:** the Qwen3-1.7B and 8B models are hybrid "thinking" models, while 4B-2507 is instruct-only. A difference may come from post-training rather than size. Switch thinking off and report it.
- **Cost:** 3 rungs × 2–3 models.
- **For:** speaks to the ExpeL-versus-TRAD contrast.
- **Against:** multiplies runs. It fits best after D1 or D4 has shown which rungs differ.

### D6. Pre-defined slices

- **Question:** does memory fix what a small model gets systematically wrong?
- **Design:** report every arm on the full list and on slices defined from the goal text before the runs (adjective form, desklamp, two objects).
- **Cost:** none (reporting).
- **For:** the full score hides where memory acts (TraceRetain, 2606.29178).
- **Against:** a slice chosen after seeing results invites over-fitting.

### D7. Retrieval settings and two oracle arms

- **Question:** does a rung lose only because of a poor setting, and how much room is there?
- **Evidence:**
  - fewer items are often better (ReasoningBank k=1 49.7 → k=4 44.4 ✓; SWE-Exp k=1 42.0 → k=4 39.0 ✓);
  - a misleading item can push a run below no memory (SWE-ContextBench ✓: free retrieval 22.2 vs 26.3 without memory, 34.3 with an oracle);
  - episodic memory helps most early, with little data (MFEC, NEC).
- **Design:**
  - a k sweep (1, 2, 4);
  - an "abstain" variant that shows nothing below a similarity threshold;
  - a bank-size curve;
  - on development tasks only, two oracle arms:
    - a **best-of-bank oracle**: the `train` entry that best matches the task's type and objects, chosen with the answer known. This is a strong reference for retrieval from this bank, not a proven ceiling;
    - a **solution oracle**: the walkthrough of the same game. This is an answer key, including object locations, and shows only how much a perfect hint could give.
- **Cost:** a few arms on one rung.
- **Against:** many small comparisons; treat them as one family.

### D8. A non-memory competitor

- **Question:** is memory needed for the dominant failures, or would one sentence do?
- **Design:** rung 0 plus a fixed instruction (for example "if the goal says *put a cool X*, cool X before placing it; for a lamp, hold the object and use the lamp"), compared with the best memory rung.
- **Cost:** 1 arm.
- **For:** an honest baseline. If an instruction removes a failure type, memory's value lies elsewhere.
- **Against:** hand-written knowledge of the benchmark. Report it as a competitor, not as a method.

### D11. Presentation of the retrieved entry

- **Question:** Q7.
- **Design:** the same retrieved entries, shown in two forms: a flat action log, or the same actions grouped under named subgoals (for example "find the egg / cool it with the fridge / put it in the microwave"). Subgoals can be derived from action types (go, take, clean/cool/heat, move) without a model.
- **Cost:** 2 arms × 9 h on one rung. Segmentation runs on the CPU.
- **For:** directly targets the most common systematic failure. A presentation change costs nothing at run time.
- **Against:** one agent study (web tasks, 85 tasks, not ALFWorld). Grouped entries are slightly longer, so the text budget must be matched.
- **Prediction:** the gain concentrates on adjective-form goals and two-object tasks; it should vanish on plain pick-and-place.

### D9. Retrieval key

- **Question:** Q6.
- **Design:** one bank, one unit (for example a window of steps), the same budget, four keys: the task text, the current observation, the agent's current thought, and a short model-written description of the situation.
- **Cost:** 4 arms × 9 h. Embeddings run on the CPU.
- **For:** cheap once a bank exists. It also separates the key from the unit, which the literature changes together.
- **Against:** a model-written key adds a call per step. Retrieval metrics can mislead: with an observation key, a stored state retrieves itself (100% "retrieval success" in 2608.03420), which says nothing about usefulness. In that paper's tic-tac-toe setting, a raw-observation key was still at least as good as a model-written description.

### D10. An applicability gate (show nothing unless it fits)

- **Question:** does refusing to show a poorly matching entry help more than better similarity?
- **Evidence:**
  - EffectMem (EMNLP 2026 Findings ✓, seed 42 only, many LLM calls per step) checks each retrieved "contract" against the current task and falls back to the plain policy when none fits. With Qwen3-8B it reports ALFWorld 38.3 → 91.8, ScienceWorld 15 → 65, WebShop 28.3 → 54.5. In its ablation the gate alone takes ScienceWorld from 15 to 51.
  - In SWE-ContextBench ✓, unfiltered retrieval falls below no memory.
- **Design:** on top of the best rung, a **rule** gate first (show an entry only if its task type and the required receptacle or appliance match the goal), then, separately, a model-judged gate. Compare both with the ungated rung and with D7's similarity threshold.
- **Cost:** 2–3 arms. The rule gate costs nothing at run time.
- **For:** a cheap, testable mechanism with one large but single-seed result behind it.
- **Against:** EffectMem's gain mixes the gate with a whole pipeline (scoring agents, a monitor, corrections), so the gate's own share for a 4B model is unknown.

## 4a. Benchmarks

**Development and first confirmation: ALFWorld.**
- Develop on a frozen, stratified sample of `valid_seen`; confirm once on `valid_unseen` (134).
- For: our model runs on it, walkthroughs give a free expert bank, and the action syntax can be checked.
- Against: strong models hit a ceiling (TraceRetain). Several benchmark papers (Evo-Memory, EvoMemBench's CrossEp-Emb, the procedural-retrieval benchmark) reuse the same games, so it is not fresh for anyone.

**A second, fresh benchmark: no ready option fits all needs.** The candidates below were read by a helper. Numbers marked ✓ were spot-checked by us; the rest were not.

| Candidate | For | Against |
|---|---|---|
| ScienceWorld (Apache-2.0) | runs on the CPU (needs Java); several studies report gains from retrieved raw trajectories, the mechanism tested here: ExpRAG (Ministral 3-8B, 10.4% → about 34%; partly a format effect, since its no-memory arm lacks the action list) and Evo-Memory (helper-read, not spot-checked), and 2610.27406 ✓ (held-out success: Llama-4-Scout 9.4 → 20.0, Qwen3-Coder-Next 27.2 → 43.8, Gemma-4-31B 44.2 → 51.7); ExpRAG's easy-to-hard task-type split tests transfer | a 4B model may sit near the floor, so pilot it first; pin the version (1.3.0 changed object ordering); fix the score threshold for "success" in advance and report the raw score as well |
| BFCL multi-turn as packaged in EvoMemBench's CrossEp-Tool (4 × 50 tasks) | mid-range baselines and large memory gains reported (helper) | EvoMemBench's repository declares no licence; 200 tasks give about ±7 points; a 4B model's baseline is unknown |
| A stream built with SeqMem-Eval's protocol (Apache-2.0), for example APIBench-HF (911 tasks) | many tasks; an online-versus-hold-out protocol that exposes gains that vanish on hold-out (they do for Qwen3-8B ✓) | not embodied action; one fixed order |
| Evo-Memory's PDDL (60) | low baseline (helper) | no public code; small |
| AppWorld (Apache-2.0; task data are distributed encrypted), the ROADMAP's tool-use target | a local-model memory result exists: ReMe ✓ raises Qwen3-8B from 14.97 to 24.70 (Avg@4), while A-Mem (12.95) and LangMem (11.46) fall below no memory; low baselines leave room | prompts are long (the API documentation alone is about 142k tokens and is fetched in pieces), so a 16k context is tight on 12 GB; ReMe is distilled procedural memory in an undocumented harness, not raw exemplars; dev has only 60 tasks (20 scenarios × 3, correlated); roughly 3–10 times the cost of ScienceWorld (helper estimate) |

AMA-Bench (questions about one long trajectory), MemEvoBench (memory safety) and the procedural-retrieval benchmark (retrieval only) test other things.

## 4b. Local models (one RTX 3060, 12 GB, vLLM without nvcc)

**Source.** Licences, checkpoint ids and sizes come from the Hugging Face API, as read by a helper. The VRAM figures are estimates.

| Role | Candidate | Why | Drawbacks |
|---|---|---|---|
| Main agent | `Qwen/Qwen3-4B-Instruct-2507-FP8` (Apache-2.0, 4.4 GB) | already runs in the AdaMEM harness, 16k context fits, same model as AdaMEM's paper | strong for its size on our sample; Q0 is unresolved |
| Weaker model (D5) | `Qwen/Qwen3-1.7B-FP8` (Apache-2.0, about 2 GB) | same family and tokenizer, fast | hybrid thinking model (switch thinking off); possible floor effect |
| Larger, same family | `Qwen/Qwen3-8B-AWQ` (official, about 5.7 GB) | fits with 16k context; published ALFWorld numbers exist | quantisation noise; the FP8 version (8.2 GB) leaves too little room for 16k |
| Other family, final check | `RedHatAI/Phi-4-mini-instruct-FP8-dynamic` (MIT, about 4.5 GB), or Llama-3.1-8B-Instruct AWQ (Llama licence, gated) | a different training lineage | no published agent numbers for Phi-4-mini; Llama's licence has use restrictions |

**Models that do not fit, or are untested:**
- Gemma 3 12B and Ministral-3-8B do not fit with a 16k context.
- Qwen3.5 small models need vLLM kernels that are unverified without nvcc.

**Harness differences.** No-memory scores depend on the harness: the same Qwen3-8B scores 19.3% in one harness (Imagine-then-Plan ✓) and 52.9% in another (SeqMem-Eval ✓). Compare models only within one harness.

**Embeddings.**
- all-MiniLM-L6-v2 on the CPU: 50 ms per query, but a 256-token limit.
- bge-small-en-v1.5 (MIT, 512 tokens): the cheap upgrade.
- Qwen3-Embedding-0.6B has the best published retrieval scores, but it belongs on the GPU, not our CPU.

## 4c. Running directions in parallel with contributors

The cost figures above assume one GPU. **With volunteers, cost turns into calendar time divided by the number of machines.** Every direction above splits into *cells*: two arms on a block of 20 frozen tasks, one seed, one machine, about 2 hours on a 12 GB GPU. The protocol is in [VOLUNTEER_COMPUTE.md](VOLUNTEER_COMPUTE.md).

| Direction | Cells for the full design | Calendar time with 1 GPU | with 5 volunteers | with 10 |
|---|---|---|---|---|
| D0 near-reproduction of AdaMEM (MiniLM instead of Qwen3-Embedding-4B; bank as available) | about 18, plus the bank | about 1.5 days, plus about 180 h for the full bank | about 7 h, plus the bank | about 4 h, plus the bank |
| D2 failure census (rung 0 only, 3 replicates) | about 21 (single-arm blocks of about 1 h) | about 1 day | about 4 h | about 2 h |
| D1 ladder, rungs 0–5 plus the intermediate arm | about 54 | about 4–5 days | about 1 day | about half a day |
| D4 unit of retrieval | about 27 | about 2–3 days | about half a day | a few hours |

**How the parallel analysis stays sound:**
- Each cell runs **both** of its arms on the same machine, so every machine contributes paired differences, and hardware becomes a block in the analysis rather than a confound.
- Directions need not wait for each other: D2 and D0 can run at once on different machines, and D4 can start as soon as a bank exists.
- A share of cells is replicated on a second machine.

**Cell counts are larger than one run per arm**, because each cell repeats its reference arm and every comparison a decision rule uses needs its own cells (VOLUNTEER_COMPUTE.md). That is why the D1 row exceeds the 2.5–3 days of section 4.

**What volunteers without a GPU can do in parallel:** #166–#169, #171, #173 and #176–#178. All of these are CPU work: the frozen list, failure tags, banks, the viewer, paper summaries.

## 5. What we would not do now, and why

- **Stored rules, consolidation, or full layered memory at once.**
  - Evidence on abstraction is mixed (section 1.3), and components interfere (2605.05716).
  - If synthesis is tried, compare a version that discards the synthesis after use.
  - In ALFWorld, lessons about preconditions can be checked against the PDDL: Reflexion's logs contain 17 lessons ("open the microwave first") that the domain does not require.
- **Memory of failures without fine-tuning** (ExpRAG).
- **Conclusions from differences under about 10 points** on 60 × 3, or from single-seed runs.
- **Using `valid_unseen` during development.**

## 6. Measurement and reporting

**Primary test.**
- Compute the per-task difference between arms, averaged over seeds, and run a two-sided sign-flip permutation test on those differences.
- Do not run McNemar on task × seed pairs as if seeds were independent; that is anti-conservative.
- Report per-task wins and losses against the reference arm.
- Apply Holm within each family declared before the runs, for example "rungs 1–5 versus the rung below".

**Reporting.**
- Per-category tables, using the failure tags from D2.
- Behaviour measures:
  - steps to pick up the right object;
  - whether the transform was done before placing;
  - the share of actions outside the admissible list;
  - unparsed responses;
  - prompt tokens and truncation.

**Power.** Simulated with [`tools/alfworld_cpu/power_paired.py`](../../tools/alfworld_cpu/power_paired.py): a one-sided sign-flip test at α = 0.05 without multiplicity correction, with the same effect on every task. The real test (two-sided, Holm) and heterogeneous effects lower these numbers.

| Assumed flip rate | Tasks | 1 seed (+5 / +10 / +15 pts) | 3 seeds (+5 / +10 / +15 pts) |
|---|---|---|---|
| 13% | 60 | 0.16 / 0.56 / 0.88 | 0.51 / 0.97 / 1.00 |
| 20% | 60 | 0.14 / 0.42 / 0.77 | 0.41 / 0.91 / 1.00 |
| 20% | 134 | 0.32 / 0.79 / 0.99 | 0.72 / 1.00 / 1.00 |
| 20% | 274 | 0.55 / 0.96 / 1.00 | 0.94 / 1.00 / 1.00 |

**Exposure ledger.** Record which tasks each arm has seen (#163).

## 7. Making runs faster

The root README forbids "a shortcut that could move the result (for example, no cutting the step limit)". At temperature 0.7 no speed-up can keep each episode bit-identical, and batching changes the numerics. Speed-ups therefore must not change what the model is shown, and must be identical for every arm.

**Safe:**
- prefix caching in vLLM for the shared system prompt;
- batching more environments while the KV cache allows it.

**Not safe as a run setting:** a lower step limit or a loop stop. Memory arms shorten episodes (by 37–55% in TraceRetain), so a cap would favour them and break comparability with AdaMEM.

**What can be done instead:**
- Run full-length rung-0 logs.
- Simulate the cap or the loop stop on them after the fact.
- Report how many outcomes would change, by arm.

In our 20 episodes, stopping after 8 identical actions in a row would have cut no successful episode and saved 4–8% of the steps. Many loops alternate between two actions, and this rule misses them.

## 8. Reuse or build

| Code | Licence | What it gives | Gaps |
|---|---|---|---|
| AdaMEM (`yunx-z/AdaMEM`) | Apache-2.0 | works locally with vLLM; ALFWorld in the current syntax; modes: no memory, `synapse`, `reasoningbank`, step-level variants with and without strategy; truncation statistics | no fixed-example, random-bank or same-type random arms; embeddings via a server (Qwen3-Embedding-4B); the step-level bank is built from the agent's own `train` runs |
| TRAD (`SkyRiver-2000/TRAD-Official`) | MIT | reference scripts for fixed, random same-type, Synapse and TRAD arms; expert pool | OpenAI API; old ALFWorld syntax |
| ExpeL (`LeapLabTHU/ExpeL`) | Apache-2.0 | insight extraction and retrieval baselines | old stack |
| MemP (`zjunlp/MemP`) | MIT | the protocol MATE builds on (252 successful trajectories, frozen retrieval manifests) | legacy action syntax |
| Reflexion (`noahshinn/reflexion`) | MIT | published per-trial logs | same-task retries, not a cross-task bank |
| `tools/alfworld_cpu/` (this repository) | this repository's licence | phrasing counts, walkthrough replay, bank syntax check, power simulation | walkthroughs never search |

**Our reading.** Building from scratch would repeat what AdaMEM already does, and would lose comparability with a published result on the same model. The missing thin layer matches open issues #166–#169, #173 and #176–#178:
- rungs 1–3;
- a CPU embedding client;
- per-task tables;
- failure tags.
