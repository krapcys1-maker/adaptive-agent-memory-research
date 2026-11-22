# experience_memory

A small, dependency-free Python library that gives an LLM agent the memory configuration the AAMR lab **measured**
to help: before each episode, show the agent the **2 successful walkthroughs from a bank whose goal is most similar
to the current goal**, rendered in the agent's own history format, never from the task's own family.

It also gives you the **token-matched placebo** the lab compared against, so that you can run the same controlled
comparison on your own agent and model. Standard library only; Python 3.11 or newer.

**Status:** version 0.1.0. The package reproduces the measured arm byte for byte (see [Acceptance](#acceptance-parity-with-the-measured-instrument)).
Everything beyond that arm (token budget, other formats, family refusal on banks that were not built disjoint) is
engineering, not a measured result.

## What was measured

| Claim | Evidence | State |
|---|---|---|
| Two goal-similar expert walkthroughs (k = 2, this package's defaults) raise the solve rate over a token-matched placebo by **+0.169 [+0.053, +0.285]** (55/21; paired sequential interval at look 2, `n = 201`, `z = 2.7777`) | [V5B package](../../data/lab/autolab-alfworld-ladder-r4-v5b/README.md) (**ALFWORLD-LADDER-R4-V5B**): 201 held-out ALFWorld `train` games (6 task types), Qwen3-4B-Instruct-2507-FP8, 360-item bank whose families are disjoint from the test games. Pinned instrument: [`tools/alfworld_ladder/v5b/`](../alfworld_ladder/v5b/SETUP_SAME.md), runner `src/agent.py` (SHA-256 `c5c5eea0…9636a`, the V5B program pin). The generic runner [`tools/alfworld_ladder/agent.py`](../alfworld_ladder/agent.py) has changed since (SHA-256 `5e22b4e0…88d0`) and is not the V5B runner: replicate V5B with `tools/alfworld_ladder/v5b/src/agent.py` | `positive` |
| Two walkthroughs of **other** task types against the same placebo: **+0.015 [−0.067, +0.097]** (19/16, same interval type) | [V5B package](../../data/lab/autolab-alfworld-ladder-r4-v5b/README.md), arm `mismatched_type` | `equivalent` at the declared ±0.12 margin, for this model, sample and seed. The interval still includes small benefits and small harms |
| The earlier run of this arm (without the V5 format reminder that `prompt_suffix` adds by default), on a 710-item bank: **+0.240 [+0.177, +0.303]** (91/19) over placebo, 300 games | [V4 package](../../data/lab/autolab-alfworld-ladder-r4-v4/README.md), [erratum on its H3 verdict](../../docs/11-research-laboratory/errata/2026-11-19-alfworld-ladder-r4-v4-h3-verdict.md) | `practical`, but verdict `measurement_problem`: answers without a parsable action tag rose with memory, so content and format were not separated |

**Notes and caveats on V5B.** The V5B result package is published at
[`data/lab/autolab-alfworld-ladder-r4-v5b/README.md`](../../data/lab/autolab-alfworld-ladder-r4-v5b/README.md), and
both the V5B and V4 verifiable numbers can be recomputed from their packages with `scripts/verify_autolab_packages.py`.
- **Why 201 of 350 prepared units (300 planned) were analysed:** the executed sequential rule had interim looks at
  `[0.34, 0.67]` with thresholds `[3.8992, 2.7777, 2.2736]` and stopped at interim look 2 (`n = 201`, `z = 2.7777`)
  once both primary contrasts were decided. As noted in the package's
  [caveats](../../data/lab/autolab-alfworld-ladder-r4-v5b/README.md#caveats), the power of the executed sequential
  rule was not calibrated before the measurement (the registered power 0.857 describes a single-look rule with
  `z = 2.2414`).
- **Secondary contrasts:** against no memory, `retrieved_task − none` was +0.109 [−0.007, +0.226] (48/26,
  `inconclusive`), `placebo − none` was −0.060 [−0.157, +0.037] (19/31, `inconclusive`) and `mismatched_type − none`
  was −0.045 [−0.135, +0.045] (17/26, `inconclusive`). The direct contrast `retrieved_task − mismatched_type` is
  documented in the
  [secondary contrast addendum](../../docs/11-research-laboratory/errata/2026-11-19-alfworld-ladder-r4-v5b-secondary-contrast.md):
  +0.154 [+0.035, +0.273] (55/24, `positive`, not `practical`), with an exposure imbalance noted (227 vs 141 distinct
  walkthroughs).

Together the two primary V5B arms say: goal-similar walkthroughs beat the placebo, and walkthroughs of other task
types were equivalent to it at the ±0.12 margin. So the gain over placebo is not explained by showing just any
walkthrough of that length. The direct contrast (+0.154 above) also changes the task type and the exposure, so it
does not show that goal similarity itself caused the difference. A balanced random walkthrough of the same task type
is still needed for that (see below).

**V6 (published, [package](../../data/lab/autolab-alfworld-ladder-r4-v6/README.md); summary as of 22 November 2026).** 300 `train` games not measured
in V3–V5B, all six task types, five arms, one seed. Retrieval was held fixed (the same two goal-similar walkthroughs)
and only the rendering changed. Against placebo: full walkthroughs +0.130 [+0.049, +0.211] (72/33), actions only
+0.137 [+0.055, +0.219] (75/34), abstract plans +0.130 [+0.060, +0.200] (60/21). All three are `positive` and none is
`practical`. The full-walkthrough and actions directions are `open`. The plan arm has a format measurement problem
(`untagged_not_truncated`/step +0.042 [+0.032, +0.052] above the pre-registered 0.03), so its positive contrast does
not separate content from format. Full walkthroughs against no memory: +0.073 [−0.009, +0.156], `inconclusive`.
- **What this package implements.** It ships one rendering, `walkthrough_v5b`, which is the full-walkthrough
  rendering of V5B; the parity check below covers it. The V6 actions-only and plan renderings were measured with the
  lab's V6 instrument, which is not part of this package. A formatter you register under any other name (for example
  `plan_v6` in the example below) is optional library code, not the measured V6 rendering.

The lab's practical threshold (SESOI) is 0.12; the states follow
[the decision rule](../../docs/11-research-laboratory/decision-rule-characteristics.md): `practical` = lower bound
≥ 0.12, `positive` = effect > 0 but practicality not shown, `equivalent` = |effect| < 0.12 shown.

## What is NOT shown

- **The effect is not shown to exceed the practical threshold.** The V5B lower bound, +0.053, is below 0.12, and so
  are the V6 lower bounds (+0.049 to +0.060). The
  gain is positive; whether it is large enough to matter is open.
- **One model.** Qwen3-4B-Instruct-2507-FP8 only, at temperature 0.7. Nothing is known about other models or sizes.
- **One environment, seen rooms.** ALFWorld text games from the `train` split. Bank and test games come from the
  same scenes; `valid_unseen` was never used. Nothing is known about unseen rooms or other environments.
- **Expert demonstrations, not the agent's own experience.** The bank holds planner walkthroughs replayed to a win.
  Whether the agent's own successes help is not measured.
- **Goal similarity is not shown to beat random walkthroughs of the same task type.** V5B separates "the right
  walkthrough" from "a walkthrough of another type", not retrieval by similarity from a random same-type pick
  (ladder rung 3, not measured).
- **Lexical similarity only.** Content-word Jaccard of the goal, not an embedding.
- **Not measured at all:** the token budget (V5B had none), any format other than the lab's full-walkthrough
  rendering (V5B, V6) and V6's actions-only and plan renderings (the plan with a measurement problem),
  k other than 2, and banks or prompts other than the lab's.

## Install

```bash
pip install ./tools/experience_memory
```

or, without installing, put `tools/experience_memory` on `sys.path`.

## Usage

```python
import experience_memory as em

bank = em.ExperienceBank([
    em.Trajectory(
        item_id="train/pick_and_place_simple-CD-None-Shelf-301/trial_1",
        goal="put a cd in shelf",
        task_type="pick_and_place_simple",
        family_id="pick_and_place_simple-CD-None-Shelf-301",   # episodes sharing a setting share a family
        initial_observation="You are in the middle of a room. You see a drawer 1 and a shelf 1.",
        steps=(em.Step("go to drawer 1", "You open the drawer 1. In it, you see a cd 1."),
               em.Step("take cd 1 from drawer 1", "You pick up the cd 1 from the drawer 1."),
               em.Step("go to shelf 1", "You arrive at shelf 1."),
               em.Step("move cd 1 to shelf 1", "You move the cd 1 to the shelf 1.")),
    ),
    # ... more successful trajectories; the bank refuses test-flagged and unsolved items
])

memory = em.ExperienceMemory(bank)                    # V5B defaults: k = 2, goal Jaccard, walkthrough format
shown = memory.for_task("put a cd on the shelf",
                        query_id="my-episode-17",     # with seed, breaks ties deterministically
                        query_family="my-family-3",   # this family is never shown; None if it has none
                        seed=0)

prompt = base_prompt + em.prompt_suffix(shown.block)  # AdaMEM's retrieval wrapper + the V5 format reminder
log.append(shown.log_record())                        # what was shown, scores, exclusions

# The controlled comparison: the same prompt with a token-matched placebo block.
placebo = memory.placebo_for(shown, count_tokens=my_model_tokenizer_count)
placebo_prompt = base_prompt + em.prompt_suffix(placebo)
```

For ALFWorld records in the lab's bank format, `experience_memory.alfworld.from_lab_record` builds the items and
flags every game outside `train` as test data. That flag alone does not protect a test set drawn from `train`, as
the lab's are: give the bank your test ids and families as well, and it refuses them at insertion.

```python
bank = em.ExperienceBank((from_lab_record(r) for r in records),
                         held_out_ids=test_game_ids, held_out_families=test_families)
```

The bank `tools/alfworld_ladder/data/bank.jsonl` is the 710-item V3/V4 bank, **not** the 360-item V5B bank,
and it was not built disjoint from the V5B test games. Do not use it to evaluate on V5B games; use the published
360-item V5B bank in [`tools/alfworld_ladder/v5b/data/bank.jsonl`](../alfworld_ladder/v5b/data/bank.jsonl) instead
(see [`tools/alfworld_ladder/v5b/SETUP_SAME.md`](../alfworld_ladder/v5b/SETUP_SAME.md)). Families and ids are compared
as exact strings in 0.1.0, so normalise them first if your sources differ in spelling.

`count_tokens` must be the tokenizer of the model you prompt (the lab used vLLM's `/tokenize`). A token budget is
optional: `ExperienceMemory(bank, token_budget=1200, count_tokens=...)` drops the lowest-ranked walkthrough whole
until the block fits, and shows nothing (the plain action instruction) if even the first does not fit.

## The measured rule, exactly

1. **Bank.** Successful trajectories only; an item flagged `is_test`, or whose id or family is held out, is refused
   (`LeakageError`), and so is a duplicate id. Rendering refuses `is_test` items too.
2. **Retrieval** (`GoalSimilarityRetriever`, k = 2). Lower-case the goal, take every run of `a`–`z`, drop the stop
   words `a an the some put in on to and of with it then your is`. Score every bank item by Jaccard of these sets.
   Order by score; break ties with `random.Random(int(sha256("<query_id>|<seed>|ret")[:12], 16)).random()`, one
   draw per bank item in bank order. Then drop items of the query's own family (and the query itself), keep the
   first k. The draws come before the exclusion, so excluding an item never reorders the others.
3. **Format** (`walkthrough_v5b`). Each item: `Task: <goal>.`, one line `[Observation i: '<obs>', Action i:
   '<action>']` per step, then `Final observation: '<obs>'`. Observation 1 is the initial observation; whitespace is
   collapsed and observations are cut to 240 characters. Items are joined as `Retrieved Item 0:` / `Retrieved
   Item 1:`, separated by a blank line.
4. **Placebo.** The same layout with neutral filler lines (the lab's), the line count chosen so the block's token
   count is closest to the memory block's.

## Adding a format

A format is any class with `name`, `render_item(item) -> str` and `wrap(texts) -> str`:

```python
class PlanFormatter:
    name = "plan_v6"
    def render_item(self, item): ...
    def wrap(self, texts): ...

em.register_formatter("plan_v6", PlanFormatter)
memory = em.ExperienceMemory(bank, formatter="plan_v6")
```

The placebo uses the formatter's `wrap`, so a new format keeps a matched control. A new format is not a measured
configuration until the lab has measured it against `walkthrough_v5b`; the name `walkthrough_v5b` itself cannot be
re-registered, so a log that says `walkthrough_v5b` always means the measured rendering.

## Acceptance: parity with the measured instrument

`parity/check_v5b_parity.py` runs the package and the V5B instrument code on the same bank and the same goals and
compares the chosen items (ids, in order), the memory block byte for byte, the placebo block byte for byte (with
the same stand-in token counter on both sides), the similarity metrics the instrument logs, and that nothing was
excluded.

```bash
python tools/experience_memory/parity/check_v5b_parity.py private --v5b-dir tools/alfworld_ladder/v5b --seeds 0-9 --require
python tools/experience_memory/parity/check_v5b_parity.py public --seeds 0-4
```

- `private` reads a V5B instrument folder (`--v5b-dir`, `EXPERIENCE_MEMORY_V5B_DIR`, or the lab layout — the pinned
  V5B folder is now public at [`tools/alfworld_ladder/v5b/`](../alfworld_ladder/v5b/SETUP_SAME.md)) and refuses inputs
  that differ from the program's SHA-256 pins (instrument, bank, units, families, unit goals). If the folder is absent
  it prints `SKIPPED` and exits 0 (`--require` makes that exit 2); a selection that would compare nothing exits 2.
  Result on 19 November 2026: all 350 V5B units × seeds 0–9, **3,500 comparisons, 0 mismatches**, inputs equal to the
  program pins.
- `public` uses the public 710-item bank and the V5B instrument code as pinned: the working copy of
  `tools/alfworld_ladder/agent.py` while it equals the pin, else the pinned version from git history, so a later
  change of the lab's runner does not silently change the reference. At 627c0da the working copy differs from the
  pin, so the check uses the version from git commit c8d54df691e6. CI runs it
  (`tests/test_experience_memory.py`), together with a synthetic fixture whose expected picks and block digests
  were produced by the instrument code
  ([`tests/fixtures/experience-memory-synthetic`](../../tests/fixtures/experience-memory-synthetic/expected.json),
  regenerated by `parity/make_synthetic_fixture.py`). The tests also check that a one-detail change of the rule
  (stop words, the 240-character cut, the tie-break salt) is reported as a mismatch.

### Parity certificate

[`PARITY_CERT.json`](PARITY_CERT.json) records the private run in the form the lab's goal code checks
(milestone M4). It contains:
- the package name, version and the commit of its code;
- the digests of the V5B instrument files and of the unit set, equal to the
  [published program record](../../data/lab/autolab-alfworld-ladder-r4-v5b/knowledge.jsonl);
- the number of units and the seeds;
- the result (comparisons and mismatches, here 0);
- the log [`parity/PARITY_LOG.txt`](parity/PARITY_LOG.txt) with its SHA-256.

The certificate is never written by hand. On the lab machine:
- `python tools/experience_memory/parity/make_parity_cert.py run` checks the inputs, runs the parity check and
  writes the log; it writes nothing if any comparison mismatches;
- `make_parity_cert.py build` writes the certificate from that log.

In CI, `tests/test_experience_memory_parity_cert.py` recomputes the certificate from the log. The test fails as
soon as the package code differs from the certified commit, so a changed package needs a new certified run before
it can claim parity. CI does not run the full V5B check (`private` mode) today: it runs `public` mode, the synthetic
fixture and the certificate recomputation. The certificate's log comes from the run on the lab machine. The inputs
of the full check are now public in [`tools/alfworld_ladder/v5b/`](../alfworld_ladder/v5b/SETUP_SAME.md), so anyone
can repeat it: `check_v5b_parity.py private --v5b-dir tools/alfworld_ladder/v5b --seeds 0-9 --require` gave 3,500
comparisons and 0 mismatches on 22 November 2026 at 627c0da, with inputs equal to the program pins. The run is
deterministic.

## Licence and credit

Apache-2.0, like the rest of the repository's code. The prompt wrapper and action instruction in `prompt.py` are
AdaMEM's ALFWorld prompts (`yunx-z/AdaMEM`, Apache-2.0), as used by the lab's instrument.
