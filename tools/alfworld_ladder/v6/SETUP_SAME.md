# V6 instrument: running the replication as `setup: same`

This folder is the instrument of the lab's program ALFWORLD-LADDER-R4-V6, byte for byte.
- **Where the hashes are pinned.** 12 of its 13 files in `src/`, `instrument/` and `data/` have their SHA-256 pinned
  in two places:
  - the replication tasks [#252](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/252)
    (`retrieved_task`), #251 (`retrieved_steps`) and #250 (`retrieved_plan`), by the first 12 hex characters;
  - the program's provenance (`data/lab/autolab-alfworld-ladder-r4-v6/knowledge.jsonl`), in full, as the run's
    `runner_pins` and the program's instrument hashes.
- **`data/unit_goals.json` has no earlier pin.** It maps each of the 360 games to its goal text. The agent does not
  read it (it takes the goal from the game). Its SHA-256 is first published here, in the table below.
- **The layout is the one the agent expects.** `src/agent.py` finds `instrument/` and `data/` next to `src/` on its own,
  so the bank and the placebo text are the V6 ones without any extra flag.

A submission to #252 with `"setup": "same"` is the only kind the lab's goal counts as an independent replication.
This page says exactly what `same` means for V6.

## The files

| File | SHA-256 | Pinned in |
|---|---|---|
| `src/agent.py` | `b223b34ba1f9d2957d9ab2dffca11e339d9dda2dddaf84e2ebf2572beb56b841` | #252 command, `knowledge.jsonl` |
| `src/run_episode.sh` | `39024c9525d1a575dccd0e7bc96828ec7eb9932fe2f94e94628ead61b7ecfa39` | #252 command, `knowledge.jsonl` |
| `src/vllm_serve.sh` | `b4ba3d576d80b70550b1b833b0c52067a8b109148a52e861fd7733f6d4d520a3` | #252 command, `knowledge.jsonl` |
| `instrument/memory_build.md` | `44ac891f6fd33da80b97dcd72ff1aab97fb291829db5afebdafed064470c9920` | #252 instrument, `knowledge.jsonl` |
| `instrument/prompt_template.txt` | `f04f0ba7697cf78e5fd6babd87f9cad81e68b627829555e31edd14f5bf6e6cd7` | #252 instrument, `knowledge.jsonl` |
| `instrument/prompt_examples.txt` | `bf37a8630a85b28b9ba6fa0081a1fa4e422fb2358b396dfe64bd27b8f00600b1` | #252 instrument, `knowledge.jsonl` |
| `instrument/placebo.txt` | `ac91b81d689a4994bf60ea660b7294d5606792ca1e6e46274243d09e2720b834` | #252 instrument and command, `knowledge.jsonl` |
| `instrument/length_check.json` | `ec2c8ded3f46082922873feb99da61ba59943904e0b705f0939223af3daea094` | #252 instrument, `knowledge.jsonl` |
| `data/bank.jsonl` (350 `train` walkthroughs) | `e8bd0daf75f30847b8a839a0c45ccb72b0fa3d7e23b485fdc59c99743dfccef1` | #252 command, `knowledge.jsonl` |
| `data/units.json` (360 `train` games) | `5c4b594aa6e389db14316cd2a0d533428111542cc7ec16a8c8d37d58c40ea78e` | #252 task list and command, `knowledge.jsonl` |
| `data/families.json` (770 entries) | `83c42d8f04e60aa55e27556e1502584a75a7229ee5856feba66cb734cf9f6c6c` | #252 command, `knowledge.jsonl` |
| `data/pilot_units.json` (60 `train` games) | `5d0a565f11934420094be57e7471242ecde2b9e9bde5ba5e7968e8933f139924` | #252 command, `knowledge.jsonl` |
| `data/unit_goals.json` (360 goals) | `92cb33541dd97021787cb738c739814426d6fd4347e6f8b6a98bb3cb8760b07c` | this page only |

Check them with `sha256sum src/* instrument/* data/*`. The repository stores these files with `-text`
(`.gitattributes`), so a checkout on any platform reproduces the same bytes and digests.
`tests/test_alfworld_ladder_v6_instrument.py` checks every row of this table against `knowledge.jsonl`.

**Pinned in #252 but not in this folder.** Four of the pins in #252 belong to lab-internal files. None of them is
read when an episode of `none`, `placebo` or `retrieved_task` runs, so a `same` run does not need them:
- `data/pool_manifest.json` (`1b5080809b11`): the lab's record of how the bank and the games were drawn;
- `tests/dry_run_fake_report.json` (`0c1cfeb6ec4a`): the report of a dry run against a fake model server;
- `pilot/pilot6_report.json` (`5929d78d8c6d`): the report of the lab's pilot 6;
- `data/pilot_walkthroughs.jsonl` (`8e1063ac8d0d`): replayed walkthroughs of the 60 pilot games. `src/agent.py`
  reads it only for positive-control jobs (`"control": "positive"`), which a replication does not run. Without it,
  the agent refuses such jobs and runs every program arm unchanged.

`instrument/memory_build.md` names these files and other private pilot outputs as references only.

## The games: `train` split only

- **Test games.** `data/units.json` lists 360 games of the ALFWorld `train` split, one per family (family = the
  ALFWorld task directory). They are the 360 families of V5B's bank.
- **Bank.** `data/bank.jsonl` holds the replayed expert walkthroughs of V5B's 350 test games, also `train`. V6 swapped
  bank and test relative to V5B; see `instrument/memory_build.md`.
- **Separation.** Bank, test and pilot games share no family (`data/families.json` covers all 770).
- **No `valid_seen` or `valid_unseen` game.** No game id in this folder starts with `valid_seen/` or `valid_unseen/`.
  `src/agent.py` refuses any task outside `valid_seen` and `train`, and `valid_unseen` is never read.
- **What the lab measured.** The lab ran 300 of the 360 games (all 5 arms, seed 0). They are the units of the public
  `data/lab/autolab-alfworld-ladder-r4-v6/per_unit.csv`; every one of them is in `data/units.json`.

## Fixed: changing any of these makes the run `setup: different`

| Item | Value for `same` |
|---|---|
| Code and data | the files of this folder, unchanged (table above) |
| Checkpoint | `Qwen/Qwen3-4B-Instruct-2507-FP8`, revision `8591804019c8b22094c3b5b4454e0edc05dffc98` |
| vLLM | `0.33.0` (the V6 run's server log records `v0.33.0`) |
| Quantisation kernel class | weight-only FP8, `MarlinFP8ScaledMMLinearKernel` for `Fp8LinearMethod`, as in the V6 run's server log. Ampere GPUs, such as the RTX 3060 and the A100, select it. |
| Server flags | `--enforce-eager --seed 0`, with `VLLM_ATTENTION_BACKEND=FLASH_ATTN VLLM_USE_FLASHINFER_SAMPLER=0` |
| ALFWorld game archive | `json_2.1.2_tw-pddl.zip` (release 0.4.0), as fetched by `alfworld-download` from ALFWorld 0.4.2 |
| Environment | ALFWorld 0.4.2, TextWorld 1.7.0, fast-downward-textworld 20.6.4 |
| Arms | for #252: `none`, `placebo` and `retrieved_task`. #251 and #250 replace `retrieved_task` with `retrieved_steps` or `retrieved_plan`; the placebo is always matched to the `retrieved_task` block. |
| Decoding | temperature 0.7, max_tokens 2048, `min_tokens` 8, format reminder on, 50 steps, k = 2. These are the defaults of `src/agent.py`. Leave `LADDER_MIN_TOKENS` and `LADDER_FORMAT_REMINDER` unset, or set them to `8` and `1`. |
| Games | all 360 games of `data/units.json`, or exactly the 300 that #252 designates (see below) |
| Seed | `0` for every job, as in V6 |

`src/vllm_serve.sh` and `instrument/placebo.txt` are identical to the V5B copies in `../v5b/`, so the server settings
and the game-archive checks of [`../v5b/SETUP_SAME.md`](../v5b/SETUP_SAME.md) apply unchanged. In short: in the
reference archive, putting an object down reads `move <object> to <receptacle>`, as in `data/bank.jsonl`, and
`alfworld-download` extracts it into a folder named `json_2.1.1`.

## Free: these do not change `same`

- `--gpu-memory-utilization`.
- `--max-model-len`, as long as it is **16384 or more**.
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
python tools/alfworld_ladder/v6/src/agent.py --batch batch.jsonl --out records.jsonl \
  --parallel 24 --data-root "$ALFWORLD_DATA/json_2.1.1"
```

`batch.jsonl` holds one line per (game, arm), each with seed 0:

```json
{"unit": "<unit id>", "task": "<the part after ~>", "arm": "retrieved_task", "seed": 0}
```

`src/run_episode.sh` is the lab's wrapper around the same call. It expects the lab's WSL layout under
`~/test-a-feasibility/`; you do not need it.

## Unit ids and the designated 300 games

- **Unit id.** The lab names each game `sha256("alfworld-ladder-r4-v6|" + task)[:10] + "~" + task`. For example,
  `00f30e90e9~train/pick_cool_then_place_in_recep-Pot-None-CounterTop-24/trial_T20190909_012033_758096`.
- **The 300 games of #252.** Run this from the repository root; it prints the 300 unit ids and checks them against
  #252's pin:

  ```python
  import hashlib, json, random
  tasks = json.load(open("tools/alfworld_ladder/v6/data/units.json", encoding="utf-8"))
  ids = sorted(hashlib.sha256(("alfworld-ladder-r4-v6|" + t).encode()).hexdigest()[:10] + "~" + t for t in tasks)
  chosen = sorted(random.Random("ALFWORLD-LADDER-R4-V6:replication:retrieved_task").sample(ids, 300))
  assert hashlib.sha256(json.dumps(chosen).encode()).hexdigest() == \
      "c90b87e5ea2de9b96645b68841a122b389f41a64344ebc3045fae50724778e0e"
  print("\n".join(chosen))
  ```

  #252 pins the prefix `c90b87e5ea2d`; the full value is in `knowledge.jsonl`. With the seed string ending in
  `retrieved_steps` or `retrieved_plan` the same rule gives the lists of #251 (`49de1b1845fc`) and #250
  (`e03b7c17411d`).
- **Overlap with the lab's run.** 249 of the 300 are among the 300 games the lab measured; 51 were not measured by
  the lab.
- **Scope.** 300 games × 3 arms = 900 episodes.
- **Time.** The lab's 1,500 episodes took 126,301 s of batch time (`work_s` of the run record in `knowledge.jsonl`),
  about 84 s per episode on the lab's one RTX 3060. At that rate, 900 episodes take about 21 GPU hours.

## What the lab checks in a #252 submission

The same checks as for V5B (#229):
- **Code checks.** The games are exactly the 360 or the designated 300, each × arm exactly once with seed 0; the
  settings and the files are as on this page; no memory comes from a test game's family.
- **CPU replay.** The lab replays every action sequence and recomputes the retrieved entries.
- **A spot-check re-run** of a random sample of your games in the `placebo` and `retrieved_task` arms on the lab's
  hardware. The sample is drawn with a salt fixed when your submission arrives, and its size comes from the lab's
  power rule (SESOI 0.12). The submission counts as `verified` only if the sample could detect the SESOI; otherwise
  its status is `verified_low_power`.

No calibration list is published for V6. The V5B calibration in `../v5b/SETUP_SAME.md` checks the same server,
archive and environment, and may be run first as a technical check of the setup.

## Your card

Record the GPU, the driver and the vLLM version; the kernel line from the vLLM log; the ALFWorld and TextWorld
versions and the game archive; `--parallel`, `--max-model-len` and `--gpu-memory-utilization`. Use the card format
of #252:

```json
{"task_id": "community_task:f4241150b99941b6", "setup": "same", "model": "Qwen/Qwen3-4B-Instruct-2507-FP8@8591804",
 "hardware": "...", "command_commit": "<this repository's commit>", "instrument_sha256": {"<file>": "<sha256>"},
 "notes": "..."}
```

`instrument_sha256` lists the files of this folder with the digests of the table above.

If anything on your machine forces a change to a fixed item, for example a driver that cannot run vLLM 0.33.0, say
so in #252 **before** running. The run is then `setup: different`, and the lab analyses it separately.
