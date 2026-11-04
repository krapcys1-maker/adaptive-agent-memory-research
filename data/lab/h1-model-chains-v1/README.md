# Model-derived fact chains: complete negative H1 result

Both full, unsealed H1 splits were captured without questions or construction
labels. The extractor received raw note text only; model-facing source/query IDs
were opaque. All 336 matched reader outputs were frozen before separate scoring.

| Split/arm | Answered /84 | All leaks /84 | OBSOLETE answered /12 | OBSOLETE leaks /12 |
|---|---:|---:|---:|---:|
| Development base | 68 | 12 | 0 | 12 |
| Development derived fact chains | 67 | 12 | 0 | 12 |
| Validation base | 73 | 9 | 3 | 9 |
| Validation derived fact chains | 73 | 9 | 3 | 9 |

**Decision: this fact-only chain arm fails the intended improvement.** Do not
report the MAB improvement as proof that ordinary procedural memory now works.
Full per-family readings and retrieval outcomes are in `dev-score.json` and
`valid-score.json`; the old .833 no-chain and .000 oracle OBSOLETE readings are
historical bounds from a different reader/protocol, not matched baselines here.

Development capture: 538 sources, 96 claims, 506 empty sources, 264 actual
extraction calls and 274 exact-text reuses. Validation: 539 sources, 100 claims,
504 empty sources, 262 extraction calls and 277 exact-text reuses. All raw text
remains stored. Empty proposals were not counted as semantic extraction success.
Each capture also made three transport controls; each reader made 168 primary
calls and three controls. Total: **874 local generations, $0 API**.

Raw statements about causes, commands, exceptions and policy routinely produced
empty entity-fact triples. The subsequent version explicitly indexes these
different evidence kinds as retrieval metadata, preserving the distinction
between a note's topic and an asserted current fact. This is the
[v2 amendment](../h1-model-chains-v2/PLAN.md), with a separate
[case-grounding projection](../h1-model-chains-v3/PLAN.md), not a rewrite of v1.

The gold-free artifact audit reconstructs every source, exact-text reuse, raw
proposal and all 336 reader inputs/outputs with zero integrity failures. It does
not establish semantic extraction accuracy. Frozen kernels, NIE personality and
deployment, old worktrees and sealed confirmation material remain unchanged.
