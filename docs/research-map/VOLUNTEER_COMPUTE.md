# Lend a GPU: run one cell of an experiment

**The fastest way this project moves is many people each running a small piece.**

On one 12 GB GPU, a single arm of the ladder (60 tasks × 3 seeds) takes about 9 hours, and the ladder as planned takes 2–3 days. The directions in [DIRECTIONS.md](DIRECTIONS.md) together need far more. Split into small cells and spread across contributors, the same work takes hours instead of weeks. Several directions can then run side by side, instead of one after another.

This page describes how such a cell works. **Status, 15 November 2026: a proposal.** The cell runner does not exist yet; it depends on #166 (package skeleton), #167 (random-bank arms) and #176 (the frozen task list). Two things can be run today with the existing AdaMEM code:
- rung 0 (#172);
- reproducing AdaMEM's own arms (direction D0).

Comment on the cell board issue to take part.

## What a cell is

A cell is **two arms on the same block of 20 frozen tasks, with one seed, on your machine**. For example:
- rung 3 versus rung 4;
- tasks 21–40 of the development list;
- seed 2.

On a 12 GB GPU with Qwen3-4B FP8, that is about 2 hours.

**Why both arms run on the same machine.**
- Hardware, drivers, precision and library versions change outcomes. Two of our runs that differed in weights (bf16 vs FP8) and sampling flipped 4 of 20 tasks.
- If one person ran arm A and another ran arm B, that machine difference would be mixed into the arm difference.
- With both arms in every cell, each machine contributes **paired** differences, and the machine becomes a block in the analysis, not a confound.

**Tasks are named, not counted.** The AdaMEM environment orders games by an unsorted directory walk, so "tasks 21–40" can mean different games on different machines. A cell always lists its games by path, from the frozen list (#176).

## What you need

**Hardware.**
- A GPU with about 12 GB or more of memory for the main model (`Qwen/Qwen3-4B-Instruct-2507-FP8`).
- Smaller GPUs (about 6–8 GB) can run cells for the weaker model in direction D5 (`Qwen/Qwen3-1.7B-FP8`).
- If your GPU does not support the FP8 checkpoint, use the bf16 or AWQ version and record it. Pairing within your machine keeps the comparison valid; the configuration becomes a factor in the analysis.

**Software.** Linux or WSL2 with vLLM, ALFWorld and the AdaMEM harness. Embeddings run on the CPU (all-MiniLM-L6-v2), so they take no GPU memory.

## What you submit

1. **A configuration card**, one small JSON file:
   - model id and revision;
   - precision;
   - vLLM and ALFWorld versions;
   - GPU model and driver;
   - temperature and maximum tokens;
   - step limit;
   - harness commit;
   - SHA-256 of the bank and of the task list;
   - seed;
   - the two arms.
2. **Per-episode results**, one JSONL line per episode: task id, arm, seed, won, steps, the actions taken, unparsed responses, prompt tokens.
3. **The SHA-256 of your raw logs.** Large raw logs can be linked rather than committed.

Submit it as a pull request to `data/contrib/<cell-id>/`. The exact folder layout will be fixed together with the cell runner.

## How results are checked

**Replication.** A share of cells is repeated by a second contributor or by the maintainer's laboratory. Cells whose rung-0 baseline is far from the others are reported, not silently dropped.

**Analysis.** Per-task paired differences are pooled across cells, with the machine as a block, using the test in DIRECTIONS.md section 6. Contributors are credited in the result and in `CONTRIBUTORS.md`.

**Rules that apply to every cell:**
- the frozen task list only;
- never `valid_unseen`, until the single confirmation;
- no change to the step limit or prompts;
- no bank built from test tasks.

## No GPU? There is still a lot to do

Issues labelled [`no-gpu-needed`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/no-gpu-needed):
- the frozen task list (#176);
- failure tags from action logs (#177);
- translating a public bank, verified by replay (#178);
- the expert bank from walkthroughs (#168);
- the random-bank arms (#167);
- the gain/loss viewer (#169);
- reading one paper in full (#171).
