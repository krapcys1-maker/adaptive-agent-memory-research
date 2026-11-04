# NIE published-detail journal: offline bridge demonstration

An engineering fixture, not an answer-quality experiment. Three authored synthetic notes use the existing NIE journal shape. No real journal, model, live prompt, NIE source or deployment was touched. The [contract and observed source gap](../../../docs/00-project/nie-offline-bridge-2026-11-04.md) were recorded before this demonstration.

| Replay | Available notes | Future notes excluded before indexing | Kernel-ranked items | Shown items | Context words |
| --- | --- | --- | --- | --- | --- |
| personal | 2 | 1 | 1 | 1 | 19 |
| general-comment | 2 | 1 | 0 | 0 | 0 |
| before-publication | 0 | 3 | 0 | 0 | 0 |
| too-small-budget | 2 | 1 | 1 | 0 | 0 |

The personal cue retrieves the earlier bicycle detail. It remains `fiction_autobio` with original `improwizacja`/publication/run metadata and a heading that does not call it canonical biography. The future note mentions 2019, but its actual November 5 recording time keeps it outside a November 3 index. The ordinary comment task does not receive autobiography. With too little word budget, no partial fact is emitted.

Two personal CLI executions produced byte-identical output; the input and frozen live-kernel source hashes stayed unchanged. `demonstration-receipt.json` records the committed bridge source and digests. The shipped lexical profile is used with an explicit infinite offline deadline and timezone requirement; neither these four cases nor an open-gate unit test recommends a universal profile.

Fourteen focused tests cover the actual journal shape, origin restrictions, timezone/subsecond availability, future-index exclusion, exact deduplication versus conflicting publications, unsupported input, full-context word budgeting, offline-only profiles, deterministic output and refusal to overwrite. Full integrated gates and CI are reported on the delivery PR.

## Run on a fresh local output path

```powershell
python scripts/nie_persona_replay.py --input data/lab/nie-offline-bridge-v1/synthetic-journal.jsonl --output NEW_REPLAY.json --query "blue bicycle harbour workshop" --as-of "2026-11-03T00:00:00Z"
python -m pytest -q tests/test_nie_persona_replay.py
python tasks.py check
```

For real use, supply an explicitly chosen private journal and private output path. The adapter never searches an agent data directory or sends data anywhere. Its budget counts whitespace words including heading/date labels, not model tokens; the kernel characters/4 estimate remains separately labelled.

## Remaining boundary

This implements journal → validated improvised events → time-filtered index → retrieval → bounded offline context. It does **not** implement context injection into NIE, a generated answer, a consistency verdict, canonical-fact promotion, supersession or write-back. The negative P2 finding remains. The next controlled replay must test whether a reader uses the recovered detail consistently and handles conflicting/stale details; engineering retrieval alone cannot establish that.

Operational-helper cleanup in the same change moves the LifeSim runner's BLAS environment setup from import time into its main execution. Reusing/importing that helper now leaves a caller's thread settings untouched; its own standalone measurement setup stays the same. Canonical LifeSim source and historical measurements are unchanged.
