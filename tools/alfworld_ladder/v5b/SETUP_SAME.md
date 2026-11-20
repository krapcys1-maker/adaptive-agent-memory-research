# V5B instrument: running the replication as `setup: same`

This folder is the instrument of the lab's program ALFWORLD-LADDER-R4-V5B, byte for byte.
- **Where the hashes are pinned.** Each file in `src/`, `instrument/` and `data/` has its SHA-256 pinned in at least
  one of three places:
  - the replication task [#229](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/229);
  - `tools/experience_memory/PARITY_CERT.json`;
  - the program's provenance (`data/lab/autolab-alfworld-ladder-r4-v5b/knowledge.jsonl`).
- **#229 lists 12 of these 13 files,** by the first 12 hex characters. `data/unit_goals.json` is pinned only in
  PARITY_CERT.json and `tools/experience_memory/parity/check_v5b_parity.py`. It has the layout the agent expects: `src/agent.py`
finds `instrument/` and `data/` next to `src/` on its own, so the bank and the placebo text are the V5B ones without
any extra flag.

A submission to #229 with `"setup": "same"` is the only kind the lab's goal counts as an independent replication.
This page says exactly what `same` means.

## Fixed: changing any of these makes the run `setup: different`

| Item | Value for `same` |
|---|---|
| Code and data | the files of this folder, unchanged. Check them with `sha256sum src/* instrument/* data/*`: compare the first 12 hex characters with #229, and `data/unit_goals.json` with PARITY_CERT.json. |
| Checkpoint | `Qwen/Qwen3-4B-Instruct-2507-FP8`, revision `8591804019c8b22094c3b5b4454e0edc05dffc98` |
| vLLM | `0.33.0` |
| Quantisation kernel class | weight-only FP8, `MarlinFP8ScaledMMLinearKernel` for `Fp8LinearMethod`. Ampere GPUs, such as the RTX 3060 and the A100, select it. |
| Server flags | `--enforce-eager --seed 0`, with `VLLM_ATTENTION_BACKEND=FLASH_ATTN VLLM_USE_FLASHINFER_SAMPLER=0` |
| ALFWorld game archive | `json_2.1.2_tw-pddl.zip` (release 0.4.0), as fetched by `alfworld-download` from ALFWorld 0.4.2 |
| Environment | ALFWorld 0.4.2, TextWorld 1.7.0, fast-downward-textworld 20.6.4. This is stricter than for volunteer cells, where these versions are recorded but do not decide the class. |
| Arms | `none`, `placebo` and `retrieved_task`. `mismatched_type` is closed and is not needed. |
| Decoding | temperature 0.7, max_tokens 2048, `min_tokens` 8, format reminder on, 50 steps, k = 2. These are the defaults of `src/agent.py`. Leave `LADDER_MIN_TOKENS` and `LADDER_FORMAT_REMINDER` unset, or set them to `8` and `1`. |
| Games | all 350 games of `data/units.json`, or exactly the lab's 300 in `replication_units.json` (see below) |
| Seed | `0` for every job, as in V5B |

**How to check the game archive.**
- **By the text.** In the reference archive, putting an object down reads `move <object> to <receptacle>`, as in
  `data/bank.jsonl`. If your game offers `put <object> in/on <receptacle>`, you have the older
  `json_2.1.1_tw-pddl.zip`.
- **By the bytes.**
  `train/pick_and_place_simple-CellPhone-None-Safe-302/trial_T20190908_122757_136508/game.tw-pddl` has SHA-256
  `86059504faa14bd6a04b7443f3779c240e2eedbcf673e0282795cdee29497b53` in the lab's copy. This is the same check as in
  [VOLUNTEER_COMPUTE.md](../../../docs/research-map/VOLUNTEER_COMPUTE.md#the-reference-configuration).
- **The folder name.** `alfworld-download` extracts the reference archive into a folder named `json_2.1.1`, even
  though the archive is `json_2.1.2`. That is why the command below says `json_2.1.1`.

## Free: these do not change `same`

- `--gpu-memory-utilization`.
- `--max-model-len`, as long as it is **16384 or more**. A smaller value would make long episodes overflow the
  context where the lab's did not.
- Paths: the model folder, `--data-root` and the output files.
- `--parallel`, the number of episodes in flight.
- The GPU, if vLLM selects the same kernel class (`MarlinFP8ScaledMMLinearKernel`). A GPU with native FP8, which
  selects another kernel, makes the run `setup: different`.

## The exact commands

The server. These are `src/vllm_serve.sh`'s settings; only the model path, the memory share and the context length
may be yours:

```bash
VLLM_ATTENTION_BACKEND=FLASH_ATTN VLLM_USE_FLASHINFER_SAMPLER=0 \
python -m vllm.entrypoints.openai.api_server \
  --model <your path to Qwen3-4B-Instruct-2507-FP8 at revision 8591804…> \
  --served-model-name Qwen/Qwen3-4B-Instruct-2507-FP8 \
  --host 127.0.0.1 --port 8001 --max-model-len 16384 \
  --gpu-memory-utilization 0.80 --enforce-eager --seed 0
```

The episodes (`$ALFWORLD_DATA` is where `alfworld-download` put the games):

```bash
python tools/alfworld_ladder/v5b/src/agent.py --batch batch.jsonl --out records.jsonl \
  --parallel 24 --data-root "$ALFWORLD_DATA/json_2.1.1"
```

`batch.jsonl` holds one line per (game, arm), each with seed 0:

```json
{"unit": "<unit id>", "task": "<the part after ~>", "arm": "retrieved_task", "seed": 0}
```

## Unit ids and the designated 300 games

- **Unit id.** The lab names each game `sha256("alfworld-ladder-r4-v5b|" + task)[:10] + "~" + task`. For example,
  `0018448af8~train/look_at_obj_in_light-CD-None-DeskLamp-305/trial_T20190909_132447_100635`.
- **The 300 games.** `replication_units.json` holds the 300 unit ids that #229 designates, chosen with this rule:

  ```python
  sorted(random.Random("ALFWORLD-LADDER-R4-V5B:replication:retrieved_task").sample(sorted(all_350_unit_ids), 300))
  ```

  The SHA-256 of `json.dumps(sorted(ids))` is `de4b7d0dbd71f8856865f2b8b40bb9b262916ddef01d5a6aeb90a3aeca5e3f9b`.
  #229 pins the same value (prefix `de4b7d0dbd71`).
- **Scope.** 300 games × 3 arms = 900 episodes.
- **Time.** One A100 ran 60 episodes in 92 minutes at `--parallel 8`. At that rate, 900 episodes take about 23 GPU
  hours (900 / 60 × 92 min = 1,380 min). A higher `--parallel` is usually faster.

## What the lab checks in a #229 submission

- **Code checks.**
  - The games are exactly the 350 or the designated 300, each × arm exactly once with seed 0.
  - The settings and the pinned files are as on this page.
  - No memory comes from a test game's family.
- **CPU replay.** The lab replays every action sequence and recomputes the retrieved entries.
- **A spot-check re-run.** The lab re-runs a random sample of your games in the `placebo` and `retrieved_task` arms
  on its own hardware, and compares the contrast with a sign test, in the direction your result claims.
  - **The sample.** It is drawn with a salt the lab fixes when it receives your submission.
  - **Its size.** It is chosen by the lab's power rule (80% power to detect a contrast inflated by the SESOI, 0.12),
    within the lab's limits.
  - **The status.** The lab states the size and the power in #229. The submission counts as `verified` only if the
    sample could detect the SESOI; otherwise its status is `verified_low_power`.
- **The calibration is not required** for a submission or for credit.

## A calibration before the long run (recommended, not counted)

The calibration is a **technical check of your setup**, run before the 900 episodes. It is not a statistical
comparison with the lab. With 20 games at a solve rate of about 60% (V5B `retrieved_task`: 0.617), the standard
error of one arm's solve rate is about √(0.6 × 0.4 / 20) ≈ 0.11, i.e. 11 percentage points. Twenty games cannot
show that two setups are equivalent.

**The games.** `calibration_units.json` lists 20 games that V5B measured and that are **not** among the designated
300. They are in the public `data/lab/autolab-alfworld-ladder-r4-v5b/per_unit.csv`.
- **Rule.** From the 201 V5B units in `per_unit.csv`, the units outside the designated 300 are grouped by task type.
  Within each type they are ordered by `sha256("ALFWORLD-LADDER-R4-V5B:calibration|" + unit id)`. Units are then
  taken round-robin over the types in alphabetical order, skipping exhausted types, until there are 20.
- **Result.** 3 or 4 games of each of the six types. The SHA-256 of `json.dumps(sorted(ids))` is
  `a4b4856e61396e72319a0292f4d31abe14fc681726e2ca75680905ba960a8527`.

**How to run it.** The three arms, seed 0, with the commands above: 60 episodes, about 1.5 GPU hours at `--parallel 8`. Submit the
result as its own folder, marked `calibration`. It is never pooled with the replication.

**It passes when all of these hold (declared in advance):**
1. **Setup.** The card shows every fixed item of this page at its `same` value: checkpoint and revision, vLLM
   0.33.0, the kernel line, the game archive, the ALFWorld and TextWorld versions, and the flags.
2. **Records.** All 60 records are present (20 games × 3 arms, seed 0), with no duplicates or extra rows, and
   every record carries the fixed decoding settings.
3. **Replay.** The lab's CPU replay of every action sequence reproduces won and steps. Recomputed from the bank and
   the goal, the retrieved entry ids, and `top1_similarity` and `memory_similarity` as stored (rounded to 4 decimals), equal yours and equal the V5B
   values in `per_unit.csv`, as does `memory_tokens`.
4. **No gross deviation.** In each arm, your number of solved games differs from V5B's on the same 20 games by at
   most 9.
   - V5B solved 10 (`none`), 11 (`placebo`) and 12 (`retrieved_task`) of these games.
   - Suppose each game has the same chance of success in both runs. Then the standard deviation of the difference
     is at most √(20 × 0.5) ≈ 3.16, with the maximum reached when every chance is 50%. A difference of 10 is then
     more than 3 standard deviations.

If a check fails, post the output in #229 before starting the long run.

## Your card

Record the following, and fill `hardware` and `notes` with the rest:
- the GPU, the driver and the vLLM version;
- the kernel line from the vLLM log;
- ALFWorld and TextWorld versions and the game archive;
- `--parallel`, `--max-model-len` and `--gpu-memory-utilization`.

Use the card format of #229:

```json
{"task_id": "community_task:df0415bd6480ad6d", "setup": "same", "model": "Qwen/Qwen3-4B-Instruct-2507-FP8@8591804",
 "hardware": "...", "command_commit": "<this repository's commit>", "instrument_sha256": {"<file>": "<sha256>"},
 "notes": "..."}
```

If anything on your machine forces a change to a fixed item, for example a driver that cannot run vLLM 0.33.0, say
so in #229 **before** running. The run is then `setup: different`, and the lab analyses it separately.
