# Placebo check: results table

Each row is one validated cell or one lab program. A cell enters the table only after it passes the lab's code
checks, the CPU replay and its spot-check (see [the challenge](placebo-check.md)). Rows are never removed. A cell that later turns
out to be flawed is marked, not deleted.

Columns:
- **solved**: the solve rate per arm;
- **empty / step**: empty answers per step, which is the decoding artefact;
- **untagged / step**: answers without an `<action>` tag.

| Source | Who | GPU · vLLM | Games | min_tokens | solved none / placebo / memory | empty / step none / placebo / memory | untagged / step none / placebo / memory | Status |
|---|---|---|---|---|---|---|---|---|
| [lab V3](../../data/lab/autolab-alfworld-ladder-r4-v3/README.md) | lab | RTX 3060 · pinned in the result | 100 `valid_seen` | not set (0) | 0.44 / 0.57 / 0.64 | 0.743 / 0.001 / 0.582 | 0.172 / 0.062 / 0.177 | valid; placebo not neutral |
| [lab V4](../../data/lab/autolab-alfworld-ladder-r4-v4/README.md) | lab | RTX 3060 · pinned in the result | 300 train (pool `v4`, families disjoint from the bank; 5 of 6 task types, no `look_at_obj_in_light`; one seed) | 8 | 0.47 / 0.45 / 0.69 | 0.000 / 0.000 / 0.000 | 0.090 / 0.099 / 0.133 | valid; placebo neutral; memory − placebo +0.24 [+0.18, +0.30]; pre-registered format criterion exceeded (untagged +0.034 > 0.03), so the lab flags a measurement problem ([H3 erratum](../11-research-laboratory/errata/2026-11-19-alfworld-ladder-r4-v4-h3-verdict.md)) |
| [lab V5B](../../data/lab/autolab-alfworld-ladder-r4-v5b/README.md) | lab | RTX 3060 · vLLM 0.33.0 (lab server logs, unpublished) | 201 train (6 task types; families disjoint from 360-item bank; format reminder on; 4 arms incl. `mismatched_type`; seed 0; stopped at interim look 2) | 8 | 0.51 / 0.45 / 0.62 (`mismatched_type` 0.46) | 0.000 / 0.000 / 0.000 (`mismatched_type` 0.000) | 0.048 / 0.097 / 0.112 (`mismatched_type` 0.095; `untagged_not_truncated`: 0.013 / 0.062 / 0.049 / 0.050) | valid; `retrieved_task − placebo` +0.169 [+0.053, +0.285] (`positive`, open); `mismatched_type − placebo` +0.015 [-0.067, +0.097] (`equivalent`, closed); `placebo − none` -0.060 [-0.157, +0.037] (`inconclusive`); format criterion `untagged_not_truncated` balanced (-0.013); [secondary contrast addendum](../11-research-laboratory/errata/2026-11-19-alfworld-ladder-r4-v5b-secondary-contrast.md) |
| [lab V6](../../data/lab/autolab-alfworld-ladder-r4-v6/README.md) | lab | RTX 3060 · vLLM 0.33.0 (lab server logs, unpublished) | 300 train (6 task types, none measured in V3–V5B; bank and test swapped relative to V5B: test games from the 360 families of V5B's bank, bank = replayed walkthroughs of V5B's 350 test games, so not a same-bank re-run of V5B; 5 arms: memory = full walkthroughs, plus `retrieved_steps` (actions only) and `retrieved_plan` (abstract plan) from the same retrieval, padded with placebo filler to the same block length; one seed) | 8 | 0.53 / 0.48 / 0.61 (steps 0.61, plan 0.61) | 0.000 / 0.000 / 0.000 (steps 0.000, plan 0.000) | 0.053 / 0.091 / 0.116 (steps 0.122, plan 0.138; `untagged_not_truncated`: 0.013 / 0.053 / 0.050, steps 0.049, plan 0.095) | valid; against placebo (paired sequential intervals, final look, n = 300, z = 2.4166): full walkthroughs +0.130 [+0.049, +0.211], steps +0.137 [+0.055, +0.219], plan +0.130 [+0.060, +0.200] (all `positive`, none `practical`); full walkthroughs and steps `open`; plan `measurement_problem` (`untagged_not_truncated` +0.042 > 0.03); against none: full walkthroughs +0.073 [−0.009, +0.156] (`inconclusive`), steps +0.080 [+0.000, +0.160] (`positive`), plan +0.073 [+0.002, +0.145] (`positive`), labels differ at the threshold with similar estimates |
| [B03 r1 (mt0)](../../data/contrib/placebo-v4-B03-r1-mt0-fr0/README.md) | [@2018cx](https://github.com/2018cx) | A100-SXM4-80GB · vLLM 0.20.0 | 20 train (pool `v4`, block B03, replicate 1, `format_reminder=0`, older `json_2.1.1` archive) | 0 | 0.45 / 0.45 / 0.60 | 0.577 / 0.001 / 0.545 | 0.195 / 0.091 / 0.209 (`untagged_not_truncated`: 0.116 / 0.018 / 0.121) | valid; sensitivity cell (PR #243); code checks, 60/60 CPU replay and [lab spot-check](../../data/contrib/placebo-v4-B03-r1-mt0-fr0/spotcheck/README.md) passed (2026-11-24, reference configuration: must-match fields 15/15 equal; solved on the 5 drawn games none / placebo / memory, volunteer 2 / 2 / 4, lab 3 / 2 / 3) |

## Merged cells awaiting lab spot-check

Per the rule above, a volunteer cell enters the validated table only after its lab spot-check passes. Merged cells that have passed code checks and CPU replay are tracked here until then.

No merged cell is waiting for its spot-check at present.

Your cell goes here. Claim a block in [#179](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/179).
