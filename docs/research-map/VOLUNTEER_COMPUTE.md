# Lend a GPU: run one cell of an experiment

**The fastest way this project moves is many people each running a small piece.**

On one 12 GB GPU, a single arm of the ladder (60 tasks × 3 seeds) takes about 9 hours. All the directions in [DIRECTIONS.md](DIRECTIONS.md) together take several hundred GPU hours. Split into small cells and spread across contributors, that becomes days of calendar time instead of weeks. Several directions can also run side by side.

**Status, 15 November 2026: a proposal.**
- The cell runner does not exist yet. It depends on #166 (package skeleton), #167 (random-bank arms) and #176 (the frozen task list).
- The cell board is #179. Comment there before running anything.

## What a cell is

A **cell** is one block of named games, run on one machine, with every arm of a pre-registered comparison, under one replicate label. For example:
- block B2 (20 games, listed by path in the frozen list from #176);
- arms rung 3 and rung 4;
- replicate 2.

On a 12 GB GPU with Qwen3-4B FP8, two arms on 20 games take about 2 hours.

**Comparisons come from the plan, not from the volunteer.**
- The arms in a cell are those of a family declared before the runs. Every comparison that a decision rule uses gets its own cells. For example, the ROADMAP's stop rule compares rung 5 with rung 2, so cells for that pair must exist, not only for adjacent rungs.
- A cell may instead run every arm of its family on one block.
- This is why the cell counts in DIRECTIONS section 4c are larger than one run per arm.

**Assignment is random.** The maintainer assigns blocks, replicates and arm pairs to volunteers at random, and every block runs on at least two machines. A volunteer does not choose which block to run.

**Both arms run at the same time on one server.** For example, 10 + 10 environments, or interleaved. The two arms then share the same machine state, load and library versions.

**What pairing does, and what it does not.**
- Pairing within a machine removes differences in *level* between machines. One GPU's agent may simply solve more tasks than another's.
- It does not remove differences in *effect*. A memory arm could help more on one configuration than on another, for example native FP8 on newer GPUs versus weight-only FP8 kernels on Ampere cards such as the RTX 3060.
- Therefore:
  - **The primary analysis uses only cells run on the reference configuration.** That means the official FP8 checkpoint, the pinned vLLM version, and the quantisation kernel that vLLM reports in its log.
  - Cells from other configurations go into a sensitivity analysis declared in advance.

**Tasks are named, not counted.** The AdaMEM environment orders games by an unsorted directory walk, so "the first 20 tasks" can mean different games on different machines. A cell lists its games by relative path.

**A seed is a replicate label, not a guarantee.** vLLM serving 20 parallel environments at temperature 0.7 is not bit-reproducible, so replication is statistical. All replicates of one block for one direction run on the same machine, because spreading them across machines would bring back the bf16-versus-FP8 confound seen in DIRECTIONS section 1.4.

## What is fixed, and checked against your card

These are not your choices. Each must match the values published for the cell, and the card records them so they can be checked:
- model checkpoint and revision;
- temperature (0.7);
- maximum tokens;
- step limit;
- SHA-256 of the prompt template;
- number of retrieved entries k, and the retrieved-text budget;
- the embedding model;
- the harness commit;
- SHA-256 of the bank.

**Banks are built once and downloaded, never rebuilt locally.**

## What you need

**For the main model.**
- A GPU with about 12 GB of memory or more, able to run `Qwen/Qwen3-4B-Instruct-2507-FP8`.
- Linux or WSL2, with vLLM (the pinned version), ALFWorld and the harness.
- Embeddings run on the CPU (all-MiniLM-L6-v2), so they take no GPU memory.

**GPUs that cannot run FP8 (older generations)** can still help.
- Use the exact alternative checkpoint named on the cell board, with its repository and revision.
- Those cells count only in the sensitivity analysis.

**Direction D5 (model strength) compares models**, so the model and the hardware must not be mixed.
- A machine runs cells of the smaller model (`Qwen/Qwen3-1.7B-FP8`) only if it also runs the matching 4B cells.
- Otherwise its cells are excluded from the D5 comparison.

## What you submit

Submit a pull request to `data/contrib/<cell-id>/`. The exact layout will be fixed together with the cell runner. It contains three things.

**1. A configuration card:** one JSON file with the fixed values above plus:
- the GPU model and driver;
- the vLLM version;
- the quantisation kernel reported by vLLM;
- start and end times.

**2. Per-episode results**, one JSONL line per episode:
- the relative game path, the arm and the replicate;
- won, steps, and the action sequence;
- the ids of the retrieved bank entries at every step;
- the prompt hash and the number of prompt tokens;
- unparsed responses.

**3. Every started run**, including crashed or interrupted ones, marked as such. A cell is claimed on #179 before it is run, so unreported runs are visible.

**Licence.**
- Contributed data is published under the repository's data licence (CC BY 4.0).
- Logs contain ALFWorld text (MIT).
- Use relative paths only: absolute paths can reveal user names.
- Outputs of models with their own licence terms (for example Llama) carry those terms.

## How results are checked

**Replay.** ALFWorld is deterministic given the actions. The maintainer replays every submitted action sequence on the CPU (about 1.5 s per game), recomputes "won" and "steps", and recomputes the retrieved entry ids from the bank and the logged queries. A mismatch voids the cell.

**Re-runs.** At least 10% of cells, chosen by the maintainer after submission, are re-run on another machine.

**Outliers.** A cell is compared with other runs of the same block, never with other blocks. The threshold for "far from the others" is set in advance. Outlying cells are reported, not silently dropped.

**Analysis and credit.**
- Per-game paired differences are pooled, with the machine as a block, using the test in DIRECTIONS section 6.
- Contributors are credited in the result and in `CONTRIBUTORS.md`.

**Rules for every cell:**
- the frozen list only;
- never `valid_unseen` until the single confirmation;
- no bank built from test games.

## Jobs that need a GPU but no pairing

**Building a bank from the agent's own successful `train` runs** is a single-arm job.
- AdaMEM's bank came from all 3,553 `train` games (1,596 successes). That is roughly 180 GPU hours at about 20 games per hour, so it is well suited to splitting across volunteers by game.
- The bank is then frozen, hashed and published once.

**Rung 0 on all 140 `valid_seen` games** (direction D2, issue #172) is single-arm too. Run all its replicates of a block on one machine.

## No GPU? There is still a lot to do

Issues labelled [`no-gpu-needed`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/no-gpu-needed), all listed on #179:
- #166 package skeleton;
- #167 random-bank arms;
- #168 expert bank from walkthroughs;
- #169 gain/loss viewer;
- #171 read one paper;
- #173 embeddings;
- #176 frozen list;
- #177 failure tags;
- #178 translate a public bank.
