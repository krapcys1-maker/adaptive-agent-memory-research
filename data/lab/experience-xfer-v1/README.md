# EXP-XFER-1, stage S1: tool-keyed lessons on BFCL Vehicle Control (development stage)

Stage S1 completed 2026-11-12. Plan: [PLAN.md](PLAN.md) (SPEC v0.1 in Polish; the owner approved stage S1 only). Code: [scripts/experience_xfer_v1.py](../../../scripts/experience_xfer_v1.py), [scripts/experience_xfer_v1_analysis.py](../../../scripts/experience_xfer_v1_analysis.py), tests in [tests/test_experience_xfer_v1.py](../../../tests/test_experience_xfer_v1.py). The pilot this builds on: [../experience-pilot-v0/README.md](../experience-pilot-v0/README.md).

S1 runs on the 30 Vehicle Control test tasks of the pilot. The mechanism was designed after looking at failures on these tasks, so **nothing here is a confirmatory result**. S1 exists to check that the mechanism works at all and to decide whether stage S2 (two domains the agent has never seen) is worth running. Stage S2 has not been approved or started.

## Short answer

Three lessons of the form "this error was resolved by first calling X" were compiled without a language model from the agent's own 20 training episodes. All three are about `startEngine`.

- **Shown up front (arm Tp), the lessons almost remove the error they are about.** The first `startEngine` attempt of a turn failed in 21 of 21 turns without memory and in 2 of 29 turns with the lessons. Error events fell from 44 to 23. Tasks solved did not change: 9 of 30 in both arms.
- **Shown only after the matching error (arm Tr), the same lessons left the error counts unchanged and solved 13 tasks against 9.** The paired count is 5 gained and 1 lost (one-sided p = 0.11), so this is not established. It was not predicted either.
- **The pilot's raw success traces (arm R+) repeated their pilot result:** 13 tasks against 9, 6 gained and 2 lost, no gain on turns whose procedure is absent from memory (27 of 37 passed in both arms).
- **The probe for harmful analogies could not discriminate.** Without memory the model already acted in 43 of 47 turns where it should have done nothing, despite an explicit instruction not to guess. Gate C fails, as registered.
- **Outputs are not fully reproducible across runs.** The rerun of the no-memory arm matched the pilot byte for byte in 21 of 30 episodes and changed the outcome of one task.

Gates A, B and D pass, so by the registered rules S2 may start, without the probe. That needs the owner's approval and, in our reading, three amendments first (see "Decision").

## Design as run

- **Data and model:** the pilot's pinned BFCL checkout, split, pools and local model (`qwen2.5:14b-instruct`, temperature 0, seed 7, `num_ctx` 8192, fully on the GPU). No paid API and no judge.
- **Lessons:** [lessons.jsonl](lessons.jsonl), compiled from pool A (the agent's own traces on the 20 training tasks) with the rules of PLAN 5.2. Checker labels are not used. Two error signatures were seen in several tasks but have no consistent fix and stay in [open-problems.json](open-problems.json): the fuel-tank capacity error (6 tasks) and "distance not found" (3 tasks).
- **Arms on the 30 test tasks**, all run in one session with the arm order shuffled per task:

  | Arm | What the model sees |
  |---|---|
  | N | no memory |
  | R+ | the pilot's best arm: two raw traces of its own successful turns, retrieved by request text |
  | Tp | the lesson block at the start of every turn (698 characters) |
  | Tr | nothing up front; a lesson is appended to the results message when its error occurs, once per episode |
  | G | tool guidance written by the model itself from the tool's call history (357 characters), same place as Tp |
  | T* | ceiling, triggered: lessons compiled from training plus the agent's own first attempt at the same test tasks |

- **Agreement with the pilot (S1a):** the new loop sends byte-identical requests to the pilot's (unit test against the pilot's raw requests). On the five determinism tasks, 9 of 10 episodes reproduced the pilot's outputs exactly and one differed in one invalid argument string. By rule 8.1, N and R+ were therefore run again on all 30 tasks instead of reusing the pilot's results.
- **Probe (S1d):** 50 `multi_turn_miss_param` variants of the Vehicle Control tasks, each cut after the turn whose ground truth is empty, with the system prompt extended by one sentence that tells the model to return no calls when information is missing. Arms N, R+, Tp, G.
- **Budget:** 3 232 of the 3 600-call cap for S1 (S1a 114, writer 1, S1c 1 483, S1d 1 371, T* 263), 66 minutes of model time.

## Results on the 30 test tasks

| Arm | Solved | Error events | Error results | Repeat errors | First `startEngine` attempt failed | Model calls | Prompt tokens |
|---|---|---|---|---|---|---|---|
| N | 9 | 44 | 85 | 41 | 21 / 21 | 307 | 554 758 |
| R+ | 13 | 29 | 46 | 17 | 13 / 25 | 289 | 655 076 |
| Tp | 9 | 23 | 38 | 15 | 2 / 29 | 293 | 589 448 |
| Tr | 13 | 44 | 84 | 40 | 21 / 21 | 299 | 549 688 |
| G | 11 | 42 | 61 | 19 | 17 / 26 | 295 | 557 319 |
| T* | 11 | 21 | 30 | 9 | 2 / 26 | 263 | 507 515 |

An error event is a (turn, function) pair with at least one failed call, so a loop of the same error counts once. Repeat errors are the failed calls after the first one of such a pair.

**Paired with N.** "Gained" are tasks the arm solved and N did not. Error events are compared on the turns both arms started.

| Arm | Gained : lost | Exact McNemar, one-sided | Error events, arm vs N | Tasks with fewer / more events | Sign test, one-sided |
|---|---|---|---|---|---|
| R+ | 6 : 2 | 0.145 | 26 vs 42 | 15 / 5 | 0.021 |
| Tp | 3 : 3 | 0.66 | 22 vs 44 | 17 / 0 | < 0.0001 |
| Tr | 5 : 1 | 0.109 | 44 vs 44 | 1 / 1 | 0.75 |
| G | 4 : 2 | 0.34 | 40 vs 43 | 9 / 5 | 0.21 |
| T* | 5 : 3 | 0.36 | 20 vs 43 | 18 / 2 | 0.000 |

**Turn pass rates by layer** (turns reached in both arms; arm vs N):

| Layer | R+ | Tp | Tr | G |
|---|---|---|---|---|
| Procedure absent from memory (M-C) | 27 vs 27 of 37 | 26 vs 25 of 36 | 28 vs 25 of 37 | 26 vs 27 of 37 |
| Turn needs a tool that has a lesson | 9 vs 6 of 11 | 10 vs 8 of 14 | 12 vs 8 of 15 | 10 vs 7 of 13 |
| Turn needs no such tool | 37 vs 37 of 50 | 30 vs 33 of 44 | 35 vs 36 of 49 | 34 vs 38 of 49 |

The two arms that put a block of notes in front of every turn (Tp, G) gain on turns that need `startEngine` and lose on turns that do not. Tp ran the lesson's fix calls (`lockDoors`, `pressBrakePedal`) in 4 of 76 turns that needed neither; Tr in none.

**How the predictions written down before the run fared** (PLAN section 1):

| Prediction | Outcome |
|---|---|
| Tp: error events down by 40% or more | held: 44 → 23 |
| Tp: 0 to +3 tasks solved | held: 0 |
| R+: gain where the procedure is in memory, none where it is not | held |
| Tp: no extra unwarranted actions in the probe | held, but the probe is at ceiling |
| R+: clear excess of unwarranted actions when the same task is in memory | not measurable: N is already at 100% in that layer |
| Tr: repeat errors down by 30% | wrong: 40 vs 41 |
| Tr: tasks solved similar to N | wrong in direction: 13 vs 9, not significant |

**Ceiling T*.** With the fixes of every error the agent resolved in its own first attempt at the same tasks, it solves 11 tasks, 2 more than N. The registered reading is "own fixes are not enough" (the gain is below 10% of the tasks). Lessons of this kind cannot raise task success much on this domain even with full coverage.

**LLM-written guidance (G).** The model's own summary is correct ("ensure all doors are securely locked and press the brake pedal fully before initiating the engine") and shorter than the lessons, but the first `startEngine` attempt still failed in 17 of 26 turns, against 2 of 29 with the compiled lessons. A concrete call to copy worked far better than a correct sentence.

## Probe: turns where the right action is no action

| Arm | Reached the turn | Proposed a call (UAR) | State changed | Used a value that appears only in the memory block |
|---|---|---|---|---|
| N | 47 | 43 (91.5%) | 19 | — |
| R+ | 50 | 50 (100%) | 22 | 34 |
| Tp | 48 | 42 (87.5%) | 21 | 9 |
| G | 47 | 42 (89.4%) | 21 | 1 |

R+ against N on the 47 entries both reached: 4 entries where only R+ acted, 0 the other way (one-sided p = 0.06). In the registered layer for H4 (the same turn of the same task is shown by R+; 10 entries) both arms acted every time, so the test has nothing to compare. **Gate C fails:** the model does not abstain often enough for this probe to measure extra harm from memory.

## Reproducibility

N and R+ were run again here. Against the pilot run of the same arm:

| Arm | Episodes with byte-identical outputs | Tasks solved, pilot → now | Tasks whose outcome changed |
|---|---|---|---|
| N | 21 of 30 | 10 → 9 | 1 (task 77) |
| R+ | 19 of 30 | 14 → 13 | 1 (task 84) |

The pilot's determinism check (5 tasks, identical) does not hold over 30 tasks or across sessions. Differences of one or two tasks between arms are inside this run-to-run variation. Every comparison above is between arms run in the same session, but the noise floor is not zero.

## Exploratory, not pre-registered

[results-s1-exploratory.json](results-s1-exploratory.json) was written after the results were seen.

- **Where Tr's five gained tasks come from.** In four of them N started the engine and then released the brake on its own, which changes the final state without any error; in the fifth N gave up after the first error. With the note, the agent stopped after the start (4 tasks) or carried on (1 task). After a successful start the brake was released in 4 of 20 turns in N and in 0 or 1 turns in every memory arm.
- **Why Tp gained nothing overall.** It fixed three tasks and broke three others. Two of the three broken tasks (52 and 57) were also broken by the pilot's placebo block, which carries no relevant content; they appear to be fragile to any text in front of the request.
- **Filling in what the user withheld.** Where the hidden value could be identified and the same turn was in memory, R+ proposed the withheld value in 6 of 7 entries (for example zip codes and a street address copied from the remembered trace); N did in 3 of 7. Small numbers.

## Decision (PLAN 8.2)

| Gate | Condition | Result |
|---|---|---|
| A, the channel works | Tp's first-attempt error rate is at most half of N's | pass (0.07 vs 1.00) |
| B, no gross harm | Tp solves at least N − 2 tasks | pass (9 vs 9) |
| C, the probe discriminates | N's rate of unwarranted action is between 10% and 90% | **fail** (91.5%) |
| D, the LLM writer is not clearly better | G solves at most Tp + 2 tasks | pass (11 vs 11) |

By these rules S2 may start and runs without the probe. S2 has not been approved. Before it starts, three points need the owner's decision and an entry in PLAN section 15:

1. **Noise.** Add a full repeat of N in S2. Without it a difference of one or two tasks cannot be told from run-to-run variation.
2. **Tr.** The plan's confirmatory tests are about Tp. S1 suggests the after-error delivery is the more promising one for task success. Registering "Tr solves more tasks than N" as a confirmatory test for S2 now, before any S2 data exist, would give that hypothesis its first clean test.
3. **Harm.** The probe is dropped by rule. S2 then measures harm only as tasks broken relative to N and as unneeded fix calls. Whether to design a different probe is open.

## What S1 does not show

- Anything confirmatory. The domain was used to design the mechanism, the tasks are few, and the run-to-run variation is about one task per arm.
- Generalisation beyond one domain whose three lessons concern one tool.
- That after-error notes raise task success. The gain is 5:1 on 30 tasks and was not predicted.
- Robustness to harmful analogies. The probe was at ceiling.
- Fidelity to ExpG. Arm G is a simplified variant: no per-call LLM judge, a 14B writer, a block in the turn.

## Reproduce

The BFCL checkout and the pilot's raw run live outside Git, next to the repository (see the pilot's README). Then:

```bash
python scripts/experience_xfer_v1.py s0
python scripts/experience_xfer_v1.py s1a
python scripts/experience_xfer_v1.py s1b
python scripts/experience_xfer_v1.py s1c
python scripts/experience_xfer_v1.py s1d
python scripts/experience_xfer_v1.py s1e
python scripts/experience_xfer_v1.py freeze
python scripts/experience_xfer_v1.py analyze
python scripts/experience_xfer_v1_exploratory.py
```

Raw requests, responses and trajectories stay outside Git; their sha256 hashes are in [raw-freeze.json](raw-freeze.json). All measures are in [results-s1.json](results-s1.json).
