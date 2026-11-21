# V5B action-format counter audit

This audit addresses #231 using the public V5B runner and per-unit CSV.

## Reproduce

From the repository root, run:

```sh
python data/contrib/2018cx-alfworld-ladder-r4-v5b-audit/audit_action_format.py
```

The script checks that the runner matches the V5B SHA-256 in
[`PARITY_CERT.json`](../../../tools/experience_memory/PARITY_CERT.json).
It uses the standard library and makes no inference calls.

## Counterexample

The runner's [format reminder](../../../tools/alfworld_ladder/agent.py#L79)
asks the model to end with exactly one admissible action in tags.
[`classify_answer`](../../../tools/alfworld_ladder/agent.py#L261) checks whether
there is any complete pair, and
[`parse_action`](../../../tools/alfworld_ladder/agent.py#L271) accepts the last
pair if its action is admissible. With both commands admissible and
`finish_reason="stop"`, the script exercises both functions:

| Action tags in the answer | Executed action | Accepted | `untagged_not_truncated` |
|---|---|---|---:|
| `<action>go to shelf 1</action>` | `go to shelf 1` | yes | 0 |
| `<action>go to desk 1</action><action>go to shelf 1</action>` | `go to shelf 1` | yes | 0 |

The second answer violates the exactly-one requirement. It also increments
neither `invalid_actions` nor `invalid_no_action_tag`, since
[the episode loop](../../../tools/alfworld_ladder/agent.py#L321) uses parser
acceptance for both counters. The same action is executed in both cases.

## What the published data can establish

For the reported format criterion `untagged_not_truncated`, the script
recomputes the step-weighted rates from the
[published CSV](../../lab/autolab-alfworld-ladder-r4-v5b/per_unit.csv):

| Arm | Flagged steps | Total steps | Rate |
|---|---:|---:|---:|
| Placebo | 476 | 7,700 | 6.182% |
| Retrieved task | 279 | 5,687 | 4.906% |

The difference is -1.276 percentage points, consistent with the reported
-0.013. This criterion measures missing complete pairs on nontruncated
answers. The CSV has no pair-count field, so the prevalence of duplicate
pairs, their imbalance across arms, and any effect on solve rates are
unknown. The examples above are synthetic and keep the executed command
fixed.

For a future run, count nontruncated answers with more than one complete
pair by arm while keeping the existing parser semantics. A check of
exactly-one-tag compliance would then cover both missing and duplicate
pairs.

Prepared by @2018cx with Codex assistance.
