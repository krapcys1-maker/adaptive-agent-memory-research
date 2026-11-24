# Placebo check B03, replicate 1

Submitted by @2018cx for #179 and the placebo-check challenge #193.
The frozen `v4` block contains 20 games. All three arms ran in one model
server session with replicate seed 1, `min_tokens=0`, and the format
reminder off.

## Configuration

| Item | Value |
|---|---|
| Model | `Qwen/Qwen3-4B-Instruct-2507-FP8` |
| Checkpoint revision | `8591804019c8b22094c3b5b4454e0edc05dffc98` |
| Weight SHA-256 | `b6154d74332140fd6dfbfbe70bbb3650dd6955861132bd59dda6789e6322b485` |
| Hardware and driver | One NVIDIA A100-SXM4 80 GB, driver 535.129.03 |
| Serving software | vLLM `0.20.0+cu129` (server API reports `0.20.0`) |
| Precision and kernel | Weight-only FP8, `MarlinFP8ScaledMMLinearKernel` |
| Environment | ALFWorld 0.4.2, TextWorld 1.6.2, fast-downward-textworld 20.6.4 |
| Game archive | Official ALFWorld `json_2.1.1_tw-pddl.zip`, SHA-256 `d376c4bbb097c068528a2a9805e358e4cd14bc75c4d68a24e5141aebd234ef67` |
| Public harness commit | `aae47bfe8645490b1675bb181a6ac6768e26c8fa` |
| Runner settings | Temperature 0.7, 2,048 completion tokens, 50 steps, 8 parallel workers |
| Run window in UTC | 2026-11-20 02:33:55 to 04:06:14 (1 h 32 min 19 s) |

The original vLLM 0.21.0 preflight failed CUDA initialization on this host.
The completed run used the vLLM build and kernel listed above. Lab
classification as a reference or hardware sensitivity cell is pending.

## Results

| Arm | Solved | Steps | Empty retries | Empty retries per step |
|---|---:|---:|---:|---:|
| `none` | 9/20 | 707 | 408 | 0.577 |
| `placebo` | 9/20 | 707 | 1 | 0.001 |
| `retrieved_task` | 12/20 | 578 | 315 | 0.545 |

Placebo minus none was 0 percentage points (2 gains and 2 losses).
Retrieved minus placebo was +15 percentage points (5 gains and 2 losses).
These are descriptive comparisons within B03. Pooled results are left to the
lab.

## Verification

The project's finish check found all 60 expected game/arm/seed records and
reported zero missing, duplicated, extra, seed-mismatched or setting-mismatched
records. The fixed file hashes were checked again on the submission checkout.
The CSV solve flags and step counts match the JSONL, and the logged memory
sources do not share a task family with their evaluation games.

An independent pass through the environment on CPU replayed each submitted
action sequence. All 60 solve flags and step counts matched. The lab's spot-check re-run
(5 games, 15 episodes, 2026-11-24) passed; see [`spotcheck/`](spotcheck/README.md).

From the repository root, with the environment versions above and
`ALFWORLD_DATA` pointing to the directory containing `json_2.1.1`:

```sh
python tools/alfworld_ladder/placebo_check.py summary data/contrib/placebo-v4-B03-r1-mt0-fr0
python data/contrib/placebo-v4-B03-r1-mt0-fr0/replay_cell.py data/contrib/placebo-v4-B03-r1-mt0-fr0
```

Use a POSIX local or memory-backed `TMPDIR` for the replay. The generated
records, card, CSV and frozen jobs are included as `records.jsonl`,
`card.json`, `per_unit.csv` and `batch.jsonl`.

## Interrupted attempt

The first full-cell launch (02:32:08 to 02:32:14 UTC) reached the
runner but all 60 game resets failed before any model completion request.
Fast Downward opened a temporary native library on NFS and its temporary
directory cleanup raised `OSError(39, "Directory not empty")`. The attempt
ended with status `incomplete`, 0 scored records and 60 missing records.
Its card and logs were archived. The successful retry used memory-backed
scratch for the temporary library and the same checkpoint, games, arms,
seed and decoding settings.

## Review request

Please confirm cell validation (including the lab spot-check), whether the
cell can be included in the next report, and whether it will qualify
@2018cx for co-authorship as `Investigation` under
[`AUTHORSHIP.md`](../../../AUTHORSHIP.md).
