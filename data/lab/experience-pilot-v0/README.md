# EXP-PILOT-0: does an agent's own experience memory help a local model?

Pilot, completed 2026-11-12. Plan: [PLAN.md](PLAN.md) (SPEC v1 in Polish, approved by the owner before any model call; deviations are listed in its section 14). Code: [scripts/experience_pilot_v0.py](../../../scripts/experience_pilot_v0.py), [scripts/experience_pilot_v0_analysis.py](../../../scripts/experience_pilot_v0_analysis.py), tests in [tests/test_experience_pilot_v0.py](../../../tests/test_experience_pilot_v0.py).

## Short answer

The model was `qwen2.5:14b-instruct` running locally on BFCL multi-turn base, Vehicle Control. It saw raw traces of its own earlier episodes, restricted to the turns the official checker marked as passed. With that memory it solved 14 of 30 held-out test tasks, against 10 of 30 without memory. The plan required at least +6 tasks with exact McNemar p ≤ 0.05; the observed +4 gives one-sided p = 0.145. **The pre-registered "memory works" outcome is not met. The pilot does not support H1 at its threshold.**

Three pre-registered checks came out clean:

- The same-length placebo from another domain gained nothing (+0).
- Showing all experiences, failures included, gained only +1.
- The lexical gate added nothing on top of success filtering: S and R+ have the same score and the same harms.

The decision table has no row for a gain between +3 and +5, so the result is **intermediate rather than null**. The only row that fires is "Selection helps", which the plan marks as descriptive. The R+ arm shows that this row is explained by the success filter, not by the gate.

An exploratory finding, added after the results were seen and not pre-registered, matches the power risk recorded in E0 before any model call. Success-filtered memory roughly halves the environment errors per task: 85 errors without memory, 51 with R+, 45 with S. Most of the drop is the hidden `startEngine` precondition (38 → 18 errors). The model also discovers that precondition inside an episode from the error message, so the drop moves task success much less.

## Design (as run)

- **Data:** BFCL `multi_turn_base_50…99` (Vehicle Control plus one secondary API), pinned at `ShishirPatil/gorilla@6ea5797` ([bfcl-pinned.json](bfcl-pinned.json), Apache-2.0). Environments and checker are used unchanged.
- **Gold check (G1):** all 50 gold trajectories pass their own checker, contain no error calls, and replay identically. No task was excluded.
- **Split:** 20 training and 30 test tasks, fixed by seed ([split.json](split.json)).
- **Model and transport:** one local model, temperature 0, seed 7, `num_ctx` 8192, run 100% on the GPU (G2). Output is forced to JSON by a schema. Agent loop: at most 8 steps per turn and at most 6 calls per step. Calls are validated, then executed by the BFCL executor. No paid API, no judge, and no model calls were used to build memory.
- **Memory:** pool A holds the baseline N's own trajectories on the 20 training tasks, one entry per turn with its executed calls and their results. A+ is the subset of A that the checker labelled `PASSED` (31 of 61 turns). G holds the training gold trajectories. F holds GorillaFileSystem-only gold turns from tasks 0–49, used as the placebo. Retrieval uses kernel 0.2.0 in lexical mode on the request text, k = 2. All pools were frozen before the test stage.
- **Arms on the test tasks:**

  | Arm | What the model sees |
  |---|---|
  | N | no memory |
  | P | placebo from the other domain, length-matched to what R shows |
  | R | A, all labels, top 2 |
  | R+ | A+, top 2 |
  | S | A+, only items above the lexical gate |
  | N′ | exact repeat of N on 5 tasks |
  | O (oracle) | conditional, not triggered |

- **Gate calibration (training only):** `lex_tau` 0.10, `min_evidence` 1.4, F1 0.52 ([gate-calibration.json](gate-calibration.json)). This is the lowest threshold on the grid, so S injected memory in 91% of test turns.
- **Isolation:** BFCL keeps environment instances in module `globals()`, keyed by model name and task id. Every executor and checker call therefore got its own unique name. Every episode's live results matched a fresh replay (0 `replay_mismatch` in all arms).

## Results (30 test tasks, all arms complete)

| Arm | Solved | State-only | Mean progress | Env. errors | Invalid calls | Model calls |
|---|---|---|---|---|---|---|
| N | 10 | 11 | 0.516 | 85 | 5 | 313 |
| P (placebo) | 10 | 11 | 0.473 | 80 | 9 | 313 |
| R (all labels) | 11 | 11 | 0.486 | 77 | 4 | 329 |
| R+ (PASSED only) | **14** | 14 | 0.577 | 51 | 4 | 292 |
| S (PASSED + gate) | **14** | 14 | 0.573 | 45 | 2 | 286 |
| N′ (5 tasks) | 3/5 | 3/5 | — | 16 | 2 | 60 |

- **Determinism:** N′ produced byte-identical model outputs to N on all 5 checked tasks, so N is deterministic, the noise threshold is 0, and the full N′ run was not needed (plan 8.3).
- **Paired exact McNemar tests.** "Only X" counts tasks the left arm solved and the right arm did not, and vice versa.

  | Pair | Only first arm | Only second arm | p |
  |---|---|---|---|
  | R–N | 5 | 4 | one-sided 0.50 |
  | S–N | 6 | 2 | one-sided 0.145 |
  | R+–N | 6 | 2 | two-sided 0.29 |
  | P–N | 2 | 2 | two-sided 1.0 |
  | R+–R | 6 | 3 | two-sided 0.51 |
  | S–R+ | 1 | 1 | two-sided 1.0 |

- **Harm and help vs N.** Harm counts tasks N solved and the arm did not; help is the reverse.

  | Arm | Harm | Help |
  |---|---|---|
  | R | 4 | 5 |
  | R+ | 2 | 6 |
  | S | 2 | 6 |
  | P | 2 | 2 |

  H4 decomposition: the success filter removes two harms (R+ against R); the gate removes none (S against R+). Every harm is listed in [results.json](results.json) with its turn, checker error, extra functions and the memory shown.
- **H3 layers.** Pass rates are paired, counted only on turns that both arms reached ([strata.json](strata.json), [exposure.json](exposure.json)). H3 is decidable, with 18 turns in M-B and 38 in M-C. For S against N: M-B 78% vs 72% (+5.6 pp), M-C 74% vs 74% (0 pp). The gain does not reach turns whose solution is absent from memory. Because the main threshold was not met, the plan's "memorisation only" row is not evaluated, but the layer data point the same way.
- **Budget:** 1 795 of the 2 000-call cap (G2 4, E1 198, E2 1 593), 40 minutes of model time.

## Exploratory, not pre-registered

Section `exploratory_not_preregistered` of [results.json](results.json) was added after the E2 results were seen. It counts environment errors per function and runs a paired sign test on per-task error counts against N.

| Arm | `startEngine` precondition errors | All env. errors | Tasks with fewer / more errors than N | Sign test p (two-sided) |
|---|---|---|---|---|
| N | 38 | 85 | — | — |
| P | 42 | 80 | 8 / 8 | 1.0 |
| R | 24 | 77 | 16 / 9 | 0.23 |
| R+ | 21 | 51 | 18 / 5 | 0.011 |
| S | 18 | 45 | 18 / 3 | 0.0015 |

Read this as a hypothesis for the next test, not as a result of this one.

## Decision (plan section 11)

No "scale" or "abandon" row is met. "Selection helps" fires; it is descriptive in the pilot, and the R+ arm attributes it to the success filter. The oracle arm O was not run, because its trigger condition (neither R nor S exceeding N by 3) was not met.

Recommended next step, not yet registered: a confirmatory test of N against R+ on new tasks. Following the plan's scaling note, use a BFCL domain with few repeated turns. Pre-register an error-count measure next to task success, and size the test for the observed effect, about +13 pp. That needs roughly 3× the tasks.

## What this pilot does not show

- Generalisation beyond one domain dominated by one hidden rule.
- Small effects.
- An advantage over other memory systems.
- Anything about distillation or learned utility.
- Correctness of BFCL labels beyond G1.
- Whether the gain comes from relevant retrieval or from domain exposure as such: there was no random-A arm.

## Reproduce

The BFCL checkout lives outside Git at `../experience-pilot-2026-11-12/bfcl/src` relative to the repository's parent folder. Recreate it at the pinned commit with a sparse checkout of `berkeley-function-call-leaderboard/bfcl_eval`. Then run:

```bash
python scripts/experience_pilot_v0.py e0
python scripts/experience_pilot_v0.py g1
python scripts/experience_pilot_v0.py g2
python scripts/experience_pilot_v0.py e1a
python scripts/experience_pilot_v0.py e1b
python scripts/experience_pilot_v0.py build
python scripts/experience_pilot_v0.py e2
python scripts/experience_pilot_v0.py freeze
python scripts/experience_pilot_v0.py analyze
```

Raw requests, responses and trajectories stay outside Git; their sha256 hashes are in [raw-freeze.json](raw-freeze.json). Pools, plans and exposure files quote BFCL requests and gold calls under Apache-2.0 (see `REUSE.toml`).
