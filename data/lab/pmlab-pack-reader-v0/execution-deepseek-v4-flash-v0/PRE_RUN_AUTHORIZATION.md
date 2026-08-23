# PMLAB-PACK-READER-001 pre-run authorization

Status: all registered construction locks passed; API execution authorized

## Frozen boundaries

- Fixture, gold, source spans, and opaque schedule: commit `365c0b6c0ae159b1517fbc87941aa33a8e369da2`.
- System prompt, 128 prompt packets, runner, validator, scorer, and gates: commit `d870741e8bba6257d12288b23d1e8f367571ae6e`.
- Reader: `deepseek-v4-flash`, temperature 0, thinking disabled, one stateless call per condition.
- Exact response schema is validated without gold. Gold is joined only after all terminal raw responses freeze.

## Passed checks

- The fixture construction audit passed all 11 registered structural and leakage checks.
- The frozen prompt audit resolved all 1,024 record locators to byte-identical evidence and found no named treatment, condition, or gold field in model-visible messages.
- Every condition contains the same eight record IDs and byte-identical evidence text as its three paired arms.
- The full test suite passed before prompt freeze (`260 passed`).

## Cost and retry authority

- Per-experiment hard cap: USD 0.50.
- Global project cap: USD 10.00.
- Global conservative spend before this run: USD 0.93229180.
- One-attempt peak cache-miss preflight: USD 0.10055672.
- Worst-case preflight if every condition consumes its one allowed retry: USD 0.20111344.
- One retry is allowed only after transport failure or invalid JSON/schema. A schema-valid wrong answer is never retried.

The user's standing authorization permits this synthetic, budgeted DeepSeek worker run. No credential, conversation, private project-memory event, or personal file is sent. Passing remains a single-family synthetic compatibility result and cannot select a production architecture.
