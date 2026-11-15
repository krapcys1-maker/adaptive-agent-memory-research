# Possible directions for the experience-memory ladder

Written 15 November 2026 as input for the autonomous laboratory and for contributors. **These are options, not instructions.** Each one gives the question, a sketch of the design, the cost, what speaks for it and against it, and what a result would mean. The laboratory or the maintainer chooses. Sources and their verification levels are in [README.md](README.md); the CPU tools are in [`tools/alfworld_cpu/`](../../tools/alfworld_cpu/).

## 1. What is fairly well established

1. **A simple bank of successful runs helps a prompted agent on ALFWorld.**
   - Self-Generated ICL (2505.00234): the agent's own successes, retrieved per step, give +16 points on unseen tasks with gpt-4o-mini.
   - AdaMEM (2606.05684): +14 points on seen tasks with Qwen3-4B.
   - Two teams, two models.
2. **Action format can wipe out the gain.** A bank in an older action syntax drops Qwen2.5-14B from 72% to 20% (MATE, 2609.35808). Our check: 90–92% of trajectories in ETO, AgentTraj-L and AgentBank contain an action that the current ALFWorld rejects.
3. **Stored abstractions tend to hurt; raw trajectories hurt less.**
   - "Abstraction" here means rules, insights or summaries written by the model.
   - Sources: 2610.27406, 2605.12978, MATE; in ExpRAG (2603.18272), learning from failures works only after retrieval-aware fine-tuning.
4. **Noise is large for small models.**
   - Two runs of Qwen3-4B that differ only in numeric precision flip 4 of 20 tasks.
   - Plain retries at temperature 0 flip 13% of tasks in Reflexion's logs.
   - A simulation at these noise levels (section 6): 60 tasks with 3 seeds detect +10 points with power 0.91–0.97, a single seed does not, and +5 points needs about 134–274 tasks with 3 seeds.

## 2. What is open

- **Q1. Does retrieval beat a random entry of the same task type, for a small model?**
  - With GPT-4, TRAD finds random same-type examples equal to task-similarity retrieval (89.8 vs 89.6). This was checked in TRAD's code.
  - With gpt-3.5, ExpeL finds retrieval clearly better than random (59.0 vs 42.5), though that comparison is confounded by insights.
  - Nobody has measured this for a 4B local model.
- **Q2. What is the right unit of retrieval: a whole trajectory, a window of steps, or one step?** Is refreshing the retrieval every step needed at all? Whole trajectories retrieved once ≈ every step (ExpRAG). Single steps with a window of following steps clearly win (TRAD).
- **Q3. Which bank source helps which failure?** Options: planner walkthroughs (free, but they never search), the agent's own successes (cost GPU time), or a translated public bank.
- **Q4. Does retrieval matter more for weaker models?** This is suggested by Q1's contrast between ExpeL and TRAD.
- **Q5. Which failures can memory fix at all?** Our 20 episodes point to hypotheses only:
  - goals in the adjective form ("put a cool egg in microwave") fail 3 of 3 in both runs;
  - "look at X under the desklamp" fails 2 of 2;
  - cabinet-by-cabinet search uses up the step limit.

## 3. Checks worth doing before any memory arm

These are cheap. Several need no GPU.

| Check | Why | How | GPU |
|---|---|---|---|
| Action syntax of the bank | MATE effect | `check_bank_syntax.py`; for walkthroughs, `replay_walkthroughs.py` | no |
| Stratified development sample | adjective-form goals are 28% of `valid_seen`; an unlucky draw can fake a difference | `goal_phrasing.py`; stratify the 60 tasks by task type × phrasing and freeze the list | no |
| Response format | the model often writes `<thinking>` instead of `<think>` and sometimes omits `<action>` | count unparsed steps per arm and report them; consider a tolerant parser applied to all arms alike | no (from logs) |
| Noise floor | 13–20% of tasks flip by chance | rung 0 with 3 seeds on the frozen sample | yes |
| Embedding choice | Qwen3-Embedding-4B (AdaMEM's choice) does not fit next to the agent | all-MiniLM-L6-v2 on the CPU: 50 ms per query, 39 texts/s on a busy CPU. Qwen3-Embedding-0.6B is impractical on our CPU; on the GPU it needs about 1.2 GB | no |

## 4. Candidate directions

Costs assume Qwen3-4B FP8 in the AdaMEM harness: 20 tasks in about 1 hour with 20 environments in parallel, so 60 tasks × 3 seeds ≈ 9 hours per arm before speed-ups (section 7).

### D1. The ladder as planned, with the checks above

- **Question:** Q1, plus the size of each rung's step.
- **Design:** rungs −1 (format) and 0 (noise, 3 seeds), then 1 (fixed expert examples), 2 (random from the whole bank), 3 (random of the same type), 4 (whole trajectories by task similarity; AdaMEM's `synapse` mode), and 5 (steps by state; AdaMEM's step-level modes without strategy synthesis).
- **Cost:** about 6 arms × 9 h ≈ 2–3 days of GPU before speed-ups.
- **For:** each rung changes one thing; a null result on rung 4 versus 3 is itself informative (it would replicate TRAD's GPT-4 finding on a small model).
- **Against:** long. The first informative contrast (3 versus 4) comes only after several arms.
- **A result means:** if 3 ≈ 4 < 5, the gain comes from the retrieval unit, not from similarity. If 2 ≈ 3 ≈ 4, the bank mostly teaches format and procedure.

### D2. Failure census first

- **Question:** Q5. How much of the failure mass is each failure type, and which rung could plausibly address it?
- **Design:** rung 0 on all 140 `valid_seen` tasks with 1–3 seeds. Tag every failure by rules applied to the action log: format failure, adjective-form goal with a skipped transform, desklamp procedure, search exhausted the step limit, two-object bookkeeping, a loop of identical actions.
- **Cost:** about 7–21 GPU hours.
- **For:** turns the hypotheses from 20 episodes into counts. It tells each later rung what it should fix. The noise floor comes as a by-product.
- **Against:** no comparison of memory arms yet. Rule-based tags need a hand check on a sample.
- **A result means:** sets predictions for D1, D3 and D4. If, say, half of the failures are adjective-form goals, a same-type random bank (rung 3) may already recover much of them.

### D3. Bank source as the variable

- **Question:** Q3.
- **Design:** the same retrieval (for example rung 4 or 5) with three banks:
  - (a) planner walkthroughs replayed on the CPU;
  - (b) the agent's own successes on a subset of `train`;
  - (c) a translated public bank, checked by replay.
- **Cost:** (a) and (c) need no GPU to build. (b) needs a few hundred `train` episodes, roughly 5–15 GPU hours; Self-Generated ICL got most of its gain within the first 100 training tasks. Then 3 arms × 9 h.
- **For:** a new, cheap axis that the literature mixes up (ExpRAG uses scripted experts, Self-Generated ICL and AdaMEM use the agent's own runs).
- **Against:** bank (b) depends on the agent's success rate on `train`, and that rate is itself noisy.
- **Prediction to test:** walkthroughs help with procedure failures (adjective form, desklamp) but not with search; the agent's own successes help with search too.

### D4. Unit of retrieval

- **Question:** Q2.
- **Design:** one bank, one similarity, three units:
  - a whole trajectory, retrieved once;
  - a window of steps around the most similar state, refreshed each step (TRAD, Self-Generated ICL);
  - a single step, refreshed each step.
- **Cost:** 3 arms × 9 h. The bank and the embeddings are shared. Embeddings run on the CPU.
- **For:** the literature disagrees here, and nobody has the answer for small models.
- **Against:** a window needs care with prompt length. Truncation must be logged per arm (AdaMEM already logs it).

### D5. Model strength × retrieval

- **Question:** Q4.
- **Design:** rungs 0, 3 and 5 only, for a weaker model (a smaller Qwen3), the main 4B model and, optionally, a stronger quantised model.
- **Cost:** 3 rungs × 2–3 models; the smaller model runs faster.
- **For:** explains the contradiction between ExpeL and TRAD.
- **Against:** multiplies runs. Best done after D1 or D4 has shown which rungs differ.

### D6. A "hard phrasing" slice as a second view of ALFWorld

- **Question:** does memory fix the failures a small model makes systematically?
- **Design:** report every arm on the full sample **and** on the slices defined in advance (adjective-form goals, desklamp, two objects).
- **Cost:** none beyond D1–D4; this is a reporting choice.
- **For:** the full score hides where memory acts; TraceRetain (2606.29178) shows ceiling effects.
- **Against:** a slice chosen after seeing results invites over-fitting. Freeze the slice definitions before the runs.

### D7. Retrieval knobs that the literature shows matter: k, a similarity threshold, bank size, an oracle arm

- **Question:** how sensitive is any rung to its settings? These are settings, not new methods.
- **Evidence:**
  - Fewer retrieved items are often better: ReasoningBank k=1 49.7 → k=4 44.4; SWE-Exp k=1 42.0 → k=4 39.0.
  - A misleading retrieved item can push a run below no memory: SWE-ContextBench, free retrieval 22.2 versus 26.3 without memory and 34.3 with an oracle.
  - Most of the bootstrap gain arrives with the first quarter of the bank (Self-Generated ICL). Episodic control in RL helps most early, with little data (MFEC, NEC).
- **Design:**
  - a k sweep (1, 2, 4) on the best rung;
  - an "abstain" variant: show nothing when the best similarity is below a threshold;
  - a bank-size curve (for example 50, 200, 800 entries);
  - on the development set only, an **oracle arm** that shows the walkthrough of the same game. This is an upper bound on what perfect retrieval could give, not a method.
- **Cost:** a few arms, but on one rung.
- **For:** guards against a rung looking bad because of a poor setting. The oracle arm says how much room there is.
- **Against:** many small comparisons. Treat them as one family and correct for multiplicity.

### Rule for every direction: no learning on the test stream

Several published gains mix memory with extra attempts and a reward or judge signal on the test tasks themselves: RAP's plain variant, AWM online, ReasoningBank, Memp's update arm, and the "MT" variants in SeqMem-Eval. Build the bank from `train` only, freeze it, and evaluate the frozen bank. If online updating is studied, it is a separate arm with its own trial budget.

## 4a. Benchmarks

**Development and first confirmation: ALFWorld.**
- Develop on a frozen, stratified sample of `valid_seen`.
- Confirm once on `valid_unseen` (134).
- Memory evidence and baselines exist for it, our model runs on it, walkthroughs give a free expert bank, and the action syntax is checked.
- Drawback: strong models reach the ceiling (TraceRetain), and several papers built on it (Evo-Memory, EvoMemBench's CrossEp-Emb, the procedural-retrieval benchmark) reuse the same games, so it is not fresh for anyone.

**A second, fresh benchmark: no ready option fits all needs.** Every candidate below has been read in full by a helper and spot-checked; see README section H.

| Candidate | For | Against |
|---|---|---|
| ScienceWorld (Apache-2.0) | the usual second environment; effects there often differ from ALFWorld (ExpRAG, 2610.27406); low baselines leave room | long episodes, slow with a local model |
| BFCL multi-turn as packaged in EvoMemBench's CrossEp-Tool (4 × 50 tasks) | mid-range baselines (26–64% for DeepSeek-V3.2) and large memory gains reported; tool use | EvoMemBench's repository declares no licence; 200 tasks give about ±7 points; a 4B model's baseline is unknown |
| A stream built with SeqMem-Eval's protocol (Apache-2.0), for example APIBench-HF (911 tasks) | many tasks; an online-versus-hold-out protocol that exposes gains that vanish on hold-out (they do for Qwen3-8B) | not embodied action; one fixed order |
| Evo-Memory's PDDL (60) | low baseline (0.12) | no public code; small |

AMA-Bench (questions about one long trajectory), MemEvoBench (memory safety) and the procedural-retrieval benchmark (retrieval only) test other things. The last one is a cheap check for the retriever: MiniLM's mean average precision falls from 84% to 59% when object names change.

## 4b. Local models (one RTX 3060, 12 GB, vLLM without nvcc)

| Role | Candidate | Why | Drawbacks |
|---|---|---|---|
| Main agent | `Qwen/Qwen3-4B-Instruct-2507-FP8` (Apache-2.0, 4.4 GB) | already runs in the harness, 16k context fits, same model as AdaMEM's results | strong for its size (14/20 on our sample), so headroom is smaller |
| Weaker model (direction D5) | `Qwen/Qwen3-1.7B-FP8` (Apache-2.0, about 2 GB) | same family and tokenizer, fast | hybrid thinking model, so thinking must be switched off; possible floor effect |
| Larger model of the same family | `Qwen/Qwen3-8B-AWQ` (official, about 5.7 GB) | fits with 16k context; published ALFWorld numbers with and without retrieval exist (below) | quantisation noise; the FP8 version (8.2 GB) leaves too little room for a 16k context |
| Other family, for a final robustness check | `RedHatAI/Phi-4-mini-instruct-FP8-dynamic` (MIT, about 4.5 GB), or Llama-3.1-8B-Instruct in AWQ (Llama licence, gated) | a different training lineage | no published agent numbers for Phi-4-mini; Llama's licence has use restrictions |

Not a fit: Gemma 3 12B and Ministral-3-8B (too large with a 16k context). Qwen3.5 small models are untested here: their mixed attention layers need vLLM kernels that we have not verified without nvcc.

**Retrieval gain depends on the model.** This was checked in the paper. In Imagine-then-Plan (2601.08955, Table 1, ALFWorld, one harness), RAP raises Qwen3-8B from 19.3% to 28.6% but Llama-3.1-8B-Instruct only from 21.4% to 22.9%. Compare models only within one harness: the same Qwen3-8B scores 52.9% without memory in SeqMem-Eval's harness.

**Embeddings.**
- all-MiniLM-L6-v2 on the CPU is enough to start: 50 ms per query, but a 256-token limit.
- bge-small-en-v1.5 (MIT, 512 tokens) is the cheap upgrade.
- Qwen3-Embedding-0.6B has the best published retrieval scores but belongs on the GPU (about 1.2 GB), not the CPU.

## 5. What we would not do now, and why

- **Stored rules, consolidation, or full layered memory at once.** Abstractions persist errors (2610.27406, 2605.12978), and components interfere (2605.05716). If synthesis is tried later, compare a version that discards the synthesis after use. In ALFWorld, lessons about preconditions can also be checked against the PDDL: Reflexion's logs contain 17 lessons ("open the microwave first") that the domain contradicts.
- **Memory of failures without fine-tuning.** It helped only after retrieval-aware fine-tuning in ExpRAG, and hurt on ScienceWorld.
- **Conclusions from differences under about 10 points** on 60 tasks, or from single-seed runs.
- **Using `valid_unseen` during development.** Keep it for one confirmation at the end.

## 6. Measurement and reporting

**Paired design.** Every arm runs on the same frozen task list with the same seeds. Report per-task wins and losses against the reference arm (for example 12:3) and an exact McNemar or sign-permutation test, as MATE does. Apply a Holm correction within each family of comparisons.

**Per-category tables.** Use the failure tags from D2.

**Simple behaviour measures:**
- steps to pick up the right object;
- whether the transform (clean, cool or heat) was done before placing;
- share of actions outside the admissible list;
- unparsed responses.

**Power.** Simulated at the measured noise levels with [`tools/alfworld_cpu/power_paired.py`](../../tools/alfworld_cpu/power_paired.py). The effect is assumed uniform across tasks, which is optimistic.

| Noise (tasks that flip) | Tasks | 1 seed (+5 / +10 / +15 pts) | 3 seeds (+5 / +10 / +15 pts) |
|---|---|---|---|
| 13% | 60 | 0.16 / 0.56 / 0.88 | 0.51 / 0.97 / 1.00 |
| 20% | 60 | 0.14 / 0.42 / 0.77 | 0.41 / 0.91 / 1.00 |
| 20% | 134 | 0.32 / 0.79 / 0.99 | 0.72 / 1.00 / 1.00 |
| 20% | 274 | 0.55 / 0.96 / 1.00 | 0.94 / 1.00 / 1.00 |

**Exposure ledger.** Record which tasks each arm has seen (#163), so that a confirmation uses fresh tasks.

## 7. Making runs faster without changing what is compared

Apply each change to every arm alike, and record it in the protocol before the runs.

- **Loop stop.** End an episode after the same action repeats, for example, 8 times in a row. In our 20 episodes, successful runs almost never repeat an action. The failed runs that loop (`examine cart 1` dozens of times) use most of the step budget.
- **Cap on reasoning tokens per step.** The harness allows 2,048.
- **Prefix caching in vLLM** for the shared system prompt.
- **A step limit of 40 instead of 50.** One success in our 20 episodes needed 42 steps, so measure the cost of the cap first.

## 8. Reuse or build

| Code | Licence | What it gives | Gaps |
|---|---|---|---|
| AdaMEM (`yunx-z/AdaMEM`) | Apache-2.0 | works locally with vLLM; ALFWorld in the current syntax; modes: no memory, `synapse` (whole trajectories by task), `reasoningbank` (strategies), step-level AdaMEM variants with and without strategy; truncation statistics | no fixed-example, random-bank or same-type random arms; embeddings via a server (Qwen3-Embedding-4B); the step-level bank must be built from the agent's own `train` runs |
| TRAD (`SkyRiver-2000/TRAD-Official`) | MIT | reference scripts for fixed, random same-type, Synapse and TRAD arms; expert pool | OpenAI API and the old ALFWorld syntax |
| ExpeL (`LeapLabTHU/ExpeL`) | Apache-2.0 | insight extraction and retrieval baselines | old stack; gpt-3.5 era |
| MemP (`zjunlp/MemP`) | MIT | the protocol MATE builds on (252 successful trajectories, frozen retrieval manifests) | legacy action syntax (MATE had to normalise it) |
| Reflexion (`noahshinn/reflexion`) | MIT | published per-trial logs for analysis | same-task retries, not a cross-task bank |
| `tools/alfworld_cpu/` (this repository) | this repository's licence | phrasing counts, walkthrough replay (expert bank in the current syntax), bank syntax check | walkthroughs never search |

**Our reading.** Building from scratch would repeat work that AdaMEM already does, and would lose comparability with a published result on the same model. The thin layer that is missing (rungs 1–3, a CPU embedding client, per-task tables) matches open issues #166–#169 and #173.
