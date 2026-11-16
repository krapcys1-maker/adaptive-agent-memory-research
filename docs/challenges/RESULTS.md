# Placebo check: results table

Each row is one validated cell or one lab program. A cell enters the table only after the lab's code checks and
its spot-check rerun pass (see [the challenge](placebo-check.md)). Rows are never removed. A cell that later turns
out to be flawed is marked, not deleted.

Columns:
- **solved**: the solve rate per arm;
- **empty / step**: empty answers per step, which is the decoding artefact;
- **untagged / step**: answers without an `<action>` tag.

| Source | Who | GPU · vLLM | Games | min_tokens | solved none / placebo / memory | empty / step none / placebo / memory | untagged / step none / placebo / memory | Status |
|---|---|---|---|---|---|---|---|---|
| [lab V3](../../data/lab/autolab-alfworld-ladder-r4-v3/README.md) | lab | RTX 3060 · pinned in the result | 100 `valid_seen` | not set (0) | 0.44 / 0.57 / 0.64 | 0.743 / 0.001 / 0.582 | 0.172 / 0.062 / 0.177 | valid; placebo not neutral |
| lab V4 | lab | RTX 3060 | 300 train (pool `v4`) | 8 | running | running | running | measurement in progress |

Your cell goes here. Claim a block in [#179](../../issues/179).
