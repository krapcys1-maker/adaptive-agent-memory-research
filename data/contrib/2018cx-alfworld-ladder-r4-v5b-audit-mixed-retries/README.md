# V5B mixed-retry scoring audit

This audit addresses #231. The pinned runner handles an exhausted retry budget
differently when one attempt returned an empty completion and the others
failed at the transport layer. This can turn a backend failure into an
invalid game action and an ordinary unsolved result.

## Reproduce

From the repository root, run:

```sh
python data/contrib/2018cx-alfworld-ladder-r4-v5b-audit-mixed-retries/audit_mixed_retries.py
```

The script verifies the runner against the published V5B SHA-256, then calls
the actual `episode()` and `chat()` functions with a one-step game and scripted
HTTP outcomes. It requires the Python standard library and performs no
network calls or model inference.

| Attempt sequence | Game actions | Episode result | `untagged_not_truncated` |
|---|---|---|---:|
| Four transport failures | None executed | Error, no solve field | — |
| Four empty HTTP completions | Literal `None` | `solved=false` | 1 |
| One empty completion, then three transport failures | Literal `None` | `solved=false` | 1 |
| Three transport failures, then one empty completion | Literal `None` | `solved=false` | 1 |
| Empty completion, transport failure, valid completion | `go to shelf 1` | `solved=true` | 0 |

## Measurement implication

In [`chat()`](../../../tools/alfworld_ladder/agent.py#L234), exhaustion raises
`ServerError` only if the number of empty responses is zero. An exhausted
mixed sequence yields the synthetic tuple `("", 0, 1, None)` even when the
last three attempts failed at the transport layer. The
[episode loop](../../../tools/alfworld_ladder/agent.py#L320) treats that tuple
as a model answer, records an untagged and invalid action, and sends the
literal `None` to the game. A pure transport failure enters the episode error
path and returns no solve field.

The published `per_unit.csv` has 804 rows and zero for both `empty_retries`
and `error` throughout. The mixed-exhaustion path would increment
`empty_retries` in any retained scored row, so the public table gives no
evidence that this path affected the published measurements. The counterexample
identifies a scoring risk for future runs, especially if transport failures
are distributed unevenly across arms. The one-step game is synthetic.

For a future instrument version, distinguish all-empty exhaustion from
mixed exhaustion with transport failures. Return an infrastructure error
for the mixed case and preserve both retry counts for audit.

Prepared by @2018cx with Codex assistance.
