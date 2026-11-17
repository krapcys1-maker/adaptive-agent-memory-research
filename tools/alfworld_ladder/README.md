# ALFWorld ladder runner (rungs 0, placebo, 3 and 4)

**Status:** works end to end on one RTX 3060 (12 GB). Two short pilots on train games outside the test set and
the bank. No ladder result yet: this is the instrument, not a finding.

A small, self-contained episode runner for the experience-memory ladder (see `docs/research-map/DIRECTIONS.md`).
It runs a whole batch of `(unit, task, arm, seed)` jobs against a local vLLM server and writes one JSON line per
job. The format is the batch contract of the autonomous lab (`solved`, `memory_sources`,
`metrics.memory_tokens`, `evidence`), so the same file is valid input for the lab and a volunteer cell.

| Arm | Memory block (fixed for the episode, same position for every memory arm) |
|---|---|
| `none` | none. The prompt is AdaMEM's no-memory ALFWorld prompt (`yunx-z/AdaMEM`, Apache-2.0). |
| `placebo` | AdaMEM's retrieval wrapper with neutral filler (`instrument/placebo.txt`), token-matched to the `retrieved_task` block of the same game and seed |
| `random_same_type` | 2 random bank walkthroughs of the same task type (rung 3, the TRAD "Random" control) |
| `retrieved_task` | the 2 bank walkthroughs whose goal is most similar to this game's goal (rung 4) |
| `mismatched_type` | 2 bank walkthroughs of OTHER task types from the least goal-similar quarter, chosen so the block is about as long as the `retrieved_task` block: real walkthrough content, wrong task. Separates "any walkthrough" from "the right walkthrough". `placebo_check.py prepare --with-mismatched` adds it to a cell |

Bank, families and the separation from the test games: `instrument/memory_build.md`.
Prompts: `instrument/prompt_template.txt`. Since V5 every arm ends with the same one-line format reminder (`LADDER_FORMAT_REMINDER=0` turns it off and reproduces the V3/V4 prompts).

## Placebo check: a volunteer cell (no coding needed)

In the lab's V3 run (100 valid_seen games), a token-matched block of neutral filler added about 13 points over
no memory. It also hid an artefact: without it, the model often ended its answer at once (empty answers).
The runner now sets vLLM `min_tokens = 8` for every arm. `--min-tokens 0` reproduces the artefact.

```
python placebo_check.py prepare --pool v4 --block B03 --replicate 1   # claim the block on #179 first
python placebo_check.py run data/contrib/placebo-v4-B03-r1-mt8           # 60 episodes, about 1.5 h on 12 GB
python placebo_check.py finish data/contrib/placebo-v4-B03-r1-mt8        # card: GPU, driver, vLLM version
python placebo_check.py summary data/contrib/placebo-v4-B03-r1-mt8
```

Then open a pull request with `data/contrib/<cell-id>/`.
- Pool `v4` holds the 354 held-out train games the lab measures in its V4 program, so a cell replicates them on
  other hardware.
- Pool `fresh` holds 242 games that nobody has measured, but only three task types. Use it only if the cell board
  asks.
- The bank is in `data/bank.jsonl`. Do not rebuild it: the card records its sha256.

## Run it

Inside the environment that has `alfworld`, `textworld` and a vLLM server for Qwen3-4B-Instruct-2507-FP8 on port 8001:

```
python build_data.py --data-root $ALFWORLD_DATA/json_2.1.1 --out data --per-type 120 --workers 8
python make_pilot.py $ALFWORLD_DATA/json_2.1.1 data 5        # 5 non-test train games per type x 3 arms
python agent.py --batch data/pilot_batch.jsonl --out pilot/pilot_out.jsonl --parallel 24
python analyse_pilot.py pilot
```

`run_episode.sh` wraps the same call for a Windows host with WSL. It starts the server and stops it afterwards,
and a watchdog stops exactly this run's processes if the caller is killed. `vllm_serve.sh` holds the server
settings. Paths in both scripts assume the layout of our test machine. Adjust them for yours.

## What to check before trusting a run

- The placebo block is within a few tokens of the memory block (`analyse_pilot.py` prints the difference).
- No `memory_sources` family appears in the test units (`families.json`).
- `valid_unseen` is never used. The agent refuses any task outside `valid_seen` and `train`.
- Unparsed answers per arm (`metrics.invalid_actions`, `invalid_no_action_tag`). Since November 2026 two more counters
  split them: `truncated` (the answer hit max_tokens, which is behaviour) and `untagged_not_truncated` (missing or
  malformed `<action>` tags in a complete answer, which is a format problem). Bank items must use the same
  format as the agent's own history. In our first pilot a `> action` rendering made the memory arm drop the
  `<action>` tags: 7.2 unparsed actions per successful episode against 0.3 for placebo. The history-format
  rendering cut that to 2.5 against 1.5.
- Throughput: on 12 GB the KV cache holds about 35k tokens. An episode takes about 45 s per step with 24 in
  parallel, so 137 games × 3 arms take roughly 8–10 h.

Tests: `tests/test_alfworld_ladder_arms.py` (CPU only, faked token counts).
