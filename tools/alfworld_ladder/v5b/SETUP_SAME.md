# V5B instrument: running the replication as `setup: same`

This folder is the instrument of the lab's program ALFWORLD-LADDER-R4-V5B, byte for byte. Every file's SHA-256 is
pinned in the replication task [#229](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/229),
in `tools/experience_memory/PARITY_CERT.json` and in the program's provenance
(`data/lab/autolab-alfworld-ladder-r4-v5b/knowledge.jsonl`). It has the layout the agent expects: `src/agent.py`
finds `instrument/` and `data/` next to `src/` on its own, so the bank and the placebo text are the V5B ones without
any extra flag.

A submission to #229 with `"setup": "same"` is the only kind the lab's goal counts as an independent replication.
This page says exactly what `same` means.

## Fixed: changing any of these makes the run `setup: different`

| Item | Value for `same` |
|---|---|
| Code and data | the files of this folder, unchanged. Check them with `sha256sum src/* instrument/* data/*` against #229. |
| Checkpoint | `Qwen/Qwen3-4B-Instruct-2507-FP8`, revision `8591804019c8b22094c3b5b4454e0edc05dffc98` |
| vLLM | `0.33.0` |
| Quantisation kernel class | weight-only FP8, `MarlinFP8ScaledMMLinearKernel` for `Fp8LinearMethod`. Ampere GPUs, such as the RTX 3060 and the A100, select it. |
| Server flags | `--enforce-eager --seed 0`, with `VLLM_ATTENTION_BACKEND=FLASH_ATTN VLLM_USE_FLASHINFER_SAMPLER=0` |
| ALFWorld game archive | `json_2.1.2_tw-pddl.zip` (release 0.4.0), as fetched by `alfworld-download` from ALFWorld 0.4.2 |
| Environment | ALFWorld 0.4.2, TextWorld 1.7.0, fast-downward-textworld 20.6.4 |
| Arms | `none`, `placebo` and `retrieved_task`. `mismatched_type` is closed and is not needed. |
| Decoding | temperature 0.7, max_tokens 2048, `min_tokens` 8, format reminder on, 50 steps, k = 2. These are the defaults of `src/agent.py`. Leave `LADDER_MIN_TOKENS` and `LADDER_FORMAT_REMINDER` unset, or set them to `8` and `1`. |
| Games | all 350 games of `data/units.json`, or exactly the lab's 300 in `replication_units.json` (see below) |
| Seed | `0` for every job, as in V5B |

**How to check the game archive.** In the reference archive, putting an object down reads `move <object> to
<receptacle>`, as in `data/bank.jsonl`. If your game offers `put <object> in/on <receptacle>`, you have the older
`json_2.1.1_tw-pddl.zip`.

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

## A calibration before the long run (recommended, not counted)

`calibration_units.json` lists 20 games that V5B measured (they are in the public
`data/lab/autolab-alfworld-ladder-r4-v5b/per_unit.csv`) and that are **not** among the designated 300. Running them
first costs about 1–2 GPU hours and tells both sides whether your setup reproduces the lab's.

- **Rule.** From the 201 V5B units in `per_unit.csv`, the units outside the designated 300 are grouped by task type.
  Within each type they are ordered by `sha256("ALFWORLD-LADDER-R4-V5B:calibration|" + unit id)`. Units are then
  taken round-robin over the types in alphabetical order, skipping exhausted types, until there are 20.
- **Result.** 3 or 4 games of each of the six types. The SHA-256 of `json.dumps(sorted(ids))` is
  `a4b4856e61396e72319a0292f4d31abe14fc681726e2ca75680905ba960a8527`.
- **Run.** The three arms, seed 0, with the commands above. Submit the result as its own folder, marked
  `calibration`. It is never pooled with the replication.
- **What the lab checks:**
  - the CPU replay of every action sequence;
  - the retrieved entry ids;
  - `memory_tokens`, `top1_similarity` and `memory_similarity`, which must equal the V5B values for those games and
    arms in `per_unit.csv`;
  - solve rates, which are compared only descriptively, because 20 games are too few for more.

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
