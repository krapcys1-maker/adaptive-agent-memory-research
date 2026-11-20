# Lend a GPU: run one cell of an experiment

**The fastest way this project moves is many people each running a small piece.**

On one 12 GB GPU, a single arm of the ladder (60 tasks × 3 seeds) takes about 9 hours. All the directions in [DIRECTIONS.md](DIRECTIONS.md) together take several hundred GPU hours. Split into small cells and spread across contributors, that becomes days of calendar time instead of weeks. Several directions can also run side by side.

**Status, 16 November 2026: one cell type works, the placebo check.**
- `tools/alfworld_ladder/placebo_check.py` runs one block of 20 frozen games × the arms none, placebo and retrieved_task, and writes the submission layout below. Blocks are listed in `tools/alfworld_ladder/contrib/pools.json`.
- Other cell types (ladder rungs 2–5, embeddings) still depend on #166, #167 and #176.
- The cell board is #179. Claim a block there before running anything.

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
  - **The primary analysis uses only cells run on the [reference configuration](#the-reference-configuration).** That means the official FP8 checkpoint, the pinned vLLM version, the quantisation kernel that vLLM reports in its log, and the pinned ALFWorld game archive.
  - Cells from other configurations go into the [sensitivity analysis](#sensitivity-analysis-declared-in-advance) declared in advance.

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

## The reference configuration

These are the values of the lab's own ALFWorld runs (programs V3 to V6, one RTX 3060). A cell is on the reference
configuration when the first four match. The environment versions in the last row are recorded on the card
and reported, but do not by themselves make a cell a sensitivity cell. Your card and your vLLM log show each value.

| Item | Reference value | Where you see it |
|---|---|---|
| Checkpoint | `Qwen/Qwen3-4B-Instruct-2507-FP8`, revision `8591804019c8b22094c3b5b4454e0edc05dffc98` | the Hugging Face snapshot folder name |
| vLLM | `0.33.0` | `finish` writes it to the card from the server's `/version` |
| Quantisation kernel | `MarlinFP8ScaledMMLinearKernel` for `Fp8LinearMethod` (weight-only FP8) | the vLLM log line `Selected … for Fp8LinearMethod` |
| ALFWorld game archive | `json_2.1.2_tw-pddl.zip` (ALFWorld release 0.4.0), as fetched by `alfworld-download` from ALFWorld 0.4.2 | see the check below |
| Environment | ALFWorld 0.4.2, TextWorld 1.7.0, fast-downward-textworld 20.6.4 | `pip show` |

- **The kernel follows the GPU.** Ampere GPUs, such as the RTX 3060 and the A100, have no native FP8, so vLLM selects
  the Marlin weight-only kernel there, as in the lab's runs. GPUs with native FP8 (Ada, Hopper) select another kernel.
  Their cells go into the sensitivity analysis.
- **Check the game archive before you run.** The two public archives differ in the text of the game:
  - In `json_2.1.2`, putting an object down reads `move <object> to <receptacle>`, the same text as the lab's bank.
    Arriving reads "You arrive at safe 1".
  - In the older `json_2.1.1_tw-pddl.zip`, the same action reads `put <object> in/on <receptacle>`, and arriving
    reads "You arrive at loc 14".
  - Byte check: `train/pick_and_place_simple-CellPhone-None-Safe-302/trial_T20190908_122757_136508/game.tw-pddl`
    has SHA-256 `86059504faa14bd6a04b7443f3779c240e2eedbcf673e0282795cdee29497b53` in the reference archive.
- **The archive matters for the memory arms**, not only for replay. The bank's walkthroughs use the `json_2.1.2`
  text. In a game from the older archive, a walkthrough shows actions that game does not accept.

These values were first written down on 20 November 2026. Earlier versions of this page named the items without
their values.

## What you need

**For the main model.**
- A GPU with about 12 GB of memory or more, able to run `Qwen/Qwen3-4B-Instruct-2507-FP8`.
- Linux or WSL2, with vLLM 0.33.0, ALFWorld with the reference game archive, and the harness (see [the reference configuration](#the-reference-configuration)).
- Embeddings run on the CPU (all-MiniLM-L6-v2), so they take no GPU memory.

**GPUs that cannot run FP8 (older generations)** can still help.
- Use the exact alternative checkpoint named on the cell board, with its repository and revision.
- Those cells count only in the sensitivity analysis.

**Direction D5 (model strength) compares models**, so the model and the hardware must not be mixed.
- A machine runs cells of the smaller model (`Qwen/Qwen3-1.7B-FP8`) only if it also runs the matching 4B cells.
- Otherwise its cells are excluded from the D5 comparison.

## What you submit

Submit a pull request to `data/contrib/<cell-id>/`. For the placebo check, `placebo_check.py` writes this layout: `card.json` (the configuration card, with the block id and the sha256 of its frozen game list), `batch.jsonl` (the jobs), `records.jsonl` (one line per episode, with the full action sequence for replay) and `per_unit.csv` (the same per-episode counters as the lab's published tables). The cell id is `placebo-<pool>-<block>-r<replicate>-mt<min_tokens>`. It contains three things.

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

**Replay.** ALFWorld is deterministic given the actions. The maintainer replays every submitted action sequence on the CPU (about 1.5 s per game), recomputes "won" and "steps", and recomputes the retrieved entry ids from the bank and the logged queries. A mismatch voids the cell. The replay uses the reference game archive. A cell run on the older `json_2.1.1` archive is replayed with one one-to-one mapping of the action text (`put X in/on Y` becomes `move X to Y`; a `move …` the agent typed there stays inadmissible) and goes into the sensitivity analysis.

**Validation.** This is the one rule for validating cells. The placebo check and
[AUTHORSHIP.md](../../AUTHORSHIP.md) refer to it.

1. **Code checks and replay, for every submitted cell.**
   - The cell passes the lab's code checks: completeness, settings, pinned files and family separation.
   - It also passes the CPU replay of all its action sequences, described above.
2. **A small spot-check, for every cell that enters a report.**
   - **What is re-run.** The lab re-runs 5 of the cell's 20 games on its own hardware, with all of the cell's arms,
     its replicate seed and its settings. That is 15 episodes for a three-arm cell.
   - **Which games.** The 5 with the lowest `sha256(salt + cell id + game path)`, where the random salt is committed
     to this repository before the draw.
   - **What it flags: gross deviations only, with these limits declared in advance.**
     - The retrieved entry ids, `memory_tokens`, `top1_similarity` and `memory_similarity` must be equal for every
       re-run episode.
     - The number of solved episodes may differ by at most 8 of the 15, in either direction. If every episode had a
       50% chance of success on both sides, the standard deviation of that difference would be √(15 × 0.5) ≈ 2.74,
       which is its largest possible value. A difference of 9 is then more than 3 standard deviations.
   - A spot-check this small cannot show that two configurations are equivalent, and it is not meant to.
3. **A fuller replication, for at least 10% of cells.** The lab chooses these cells after submission and re-runs each
   in full on another GPU. The results are reported next to the cell.
4. **A cell is *validated* when steps 1 and 2 pass.** Whether a cell is drawn for step 3 never decides its
   contributor's credit. The cell keeps its class, primary or sensitivity, whatever steps 2 and 3 show.

**Outliers.** A cell is compared with other runs of the same block, never with other blocks. The threshold for "far from the others" is set in advance. Outlying cells are reported, not silently dropped.

**Analysis and credit.**
- Per-game paired differences are pooled, with the machine as a block, using the test in DIRECTIONS section 6.
- Contributors are credited in the result and in [CONTRIBUTORS.md](../../CONTRIBUTORS.md).

### Sensitivity analysis (declared in advance)

This plan was declared on 20 November 2026. That was after the first off-reference cell (#243) was submitted, and
before any cell was pooled.

- **Which analysis a cell enters is decided from its card alone,** before its outcomes are read. A cell that differs
  from the [reference configuration](#the-reference-configuration) in the checkpoint or revision, the vLLM version,
  the quantisation kernel or the game archive is a *sensitivity cell*. Every other check above still applies to it.
- **Sensitivity cells are pooled separately,** with the same test and the machine as a block, for each comparison of
  the primary analysis.
- **They are reported next to the primary result,** never instead of it. The report also lists how each cell
  differs from the reference.
- **No cell moves between the two analyses after its data have been seen,** in either direction. A cell is
  reclassified only for an error in its card, and the report says so.
- **A difference between the primary and the sensitivity estimates is a finding,** for example a memory effect that
  depends on the configuration. It is reported, not averaged away.

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
