# Challenge: does a meaningless block help your model too?

**Our first controlled measurement on ALFWorld** (program V3: Qwen3-4B-Instruct-2507-FP8, 100 `valid_seen` games, 3 arms):

| Arm | What the agent sees | Solved |
|---|---|---|
| `none` | AdaMEM's no-memory prompt | 0.44 |
| `placebo` | the memory wrapper filled with neutral text, token-matched to the memory block | 0.57 |
| `retrieved_task` | the 2 expert walkthroughs most similar to the game's goal | 0.64 |

- **The placebo block alone added 13 points.**
- **The memory content added only 7 more.** That difference was not significant.
- **The placebo was not neutral.** It almost removed one decoding artefact: the model ending its answer at the first
  token and returning an empty reply. Empty answers per step were 0.743 with no memory, 0.582 with memory and 0.001
  with the placebo.
- **So comparing memory with no memory alone would have overstated the memory effect.** A placebo that changes
  decoding is itself not a clean control.
- The full result, its caveats and its provenance: [data/lab/autolab-alfworld-ladder-r4-v3](../../data/lab/autolab-alfworld-ladder-r4-v3/README.md).

The lab then ran program V4 with `min_tokens = 8` in vLLM for every arm, on 300 `train` games (five task types, no
game shared with V3). There were no empty answers, and placebo and no memory were equivalent (0.45 vs 0.47). Because
V4 also changed the games, it does **not** tell how much of the V3 13 points came from the empty-answer artefact.
That is a hypothesis. The direct test is the same games with `min_tokens` 0 and 8, all else fixed: two cells on
the same block. See [data/lab/autolab-alfworld-ladder-r4-v4](../../data/lab/autolab-alfworld-ladder-r4-v4/README.md).

**The question for you: does this replicate on your GPU, your vLLM version, your drivers?** Two things are worth
knowing:
- whether the placebo effect and the empty-answer artefact appear on other machines (`--min-tokens 0` re-creates
  the V3 decoding condition, on train games rather than the V3 games);
- whether they disappear with `--min-tokens 8`.

Two cells on the same block (one with each setting) answer both for those 20 games.

## What you need

- A GPU with about 12 GB of memory (an RTX 3060 works).
- Linux or WSL2, with ALFWorld, TextWorld and vLLM installed as in [tools/alfworld_ladder](../../tools/alfworld_ladder/README.md).
- About 2 hours per cell (20 games × 3 arms).

## How to run a cell

1. **Claim a block** in [#179](../../issues/179) ("B03, replicate 1, min_tokens 0"), so two people do not run the same
   cell. Blocks B00–B10 have 4 games of each of the 5 task types. The later blocks are mostly two-object and
   pick-and-place games.
2. **Prepare, run, finish and check:**

   ```bash
   python tools/alfworld_ladder/placebo_check.py prepare --pool v4 --block B03 --replicate 1 --min-tokens 0
   python tools/alfworld_ladder/placebo_check.py run     data/contrib/placebo-v4-B03-r1-mt0-fr0
   python tools/alfworld_ladder/placebo_check.py finish  data/contrib/placebo-v4-B03-r1-mt0-fr0
   python tools/alfworld_ladder/placebo_check.py summary data/contrib/placebo-v4-B03-r1-mt0-fr0
   ```

   `prepare` writes the card from the agent's own configuration: the model (`LADDER_MODEL`, default
   Qwen3-4B-Instruct-2507-FP8), the prompt hash and `--format-reminder` (default `0`, the V3/V4 prompts; `1` adds
   the V5 reminder and makes the cell a V5-prompt cell). A cell whose model or prompt text differs from V3/V4 gets
   `-x<8 hex>` at the end of its id. `run` needs vLLM on port 8001, passes the card's model, `min_tokens` and
   format reminder to the agent, and uses `$ALFWORLD_DATA/json_2.1.1` when that variable is set. `finish` records
   your GPU, driver, vLLM version and the model the server reports, and marks the cell `invalid` if a record lies
   outside the card's games and arms, appears twice, has another seed, or ran with another model, `min_tokens`,
   format reminder, temperature, `max_tokens` or step limit. `summary` refuses an invalid cell; otherwise it
   prints placebo − none, memory − placebo, and empty and untagged answers per step for each arm.
3. **Open a pull request** that adds the cell folder: `card.json`, `batch.jsonl` and `records.jsonl`. Submit
   interrupted or surprising runs too, marked as such. Negative and "nothing happened" results count.

## How we check a cell

- **Code checks:**
  - completeness: every game × arm of the card exactly once, with the card's seed, and nothing else;
  - every record ran with the card's model, `min_tokens`, format reminder, temperature, `max_tokens` and step limit;
  - the pinned files (agent, placebo text, bank, prompt template) match by sha256;
  - no memory taken from the test games' families;
  - the counters are consistent with each other.
- **A spot-check:** the lab re-runs a random sample of your games on its own GPU and compares the paired outcomes.
  The sample is fixed in advance with a committed random salt.
- **After both pass:** the cell is *validated* and enters the [results table](RESULTS.md).

## Credit

A validated cell that is included in the next report makes you a **co-author** of it, with the role *Investigation*.
Your name is also listed in the results table and in the result's README. See [AUTHORSHIP.md](../../AUTHORSHIP.md).

## Rules that keep it honest

- **Do not change the agent, the prompts, the placebo text, the bank, the temperature or the step limit.** A changed
  setup is welcome as a *conceptual* replication, but say so in `card.json`. It is analysed separately. The card
  states which one it is (`replication`).
- `agent.py` is the current public runner, not the V4 agent pin (which is not public). With the format reminder off,
  its prompt text equals `instrument/prompt_template.txt` as pinned by V3 and V4; a CPU test checks this.
- **Never use ALFWorld `valid_unseen`.** `prepare` refuses any game outside the frozen pools.
- **Report every started run,** including crashed ones.
