# Local iterative development result: 4/100, still not ready

The already launched follow-up completed all 100 questions, with **4 exact answers**, mean token F1 0.045, 87 UNKNOWN and no malformed final protocol outputs. It made 405 local completions: three positive controls and **402 primary read/search rounds**, all reconstructed against raw requests, responses, archive retrieval and stop rules. Wall time was 792.844 seconds; the pinned Qwen 14B digest was unchanged and the owned model was unloaded. There were zero paid or judge calls.

Compared with the same local B baseline (1/100), the follow-up repaired three cases and regressed none: [paired development counts](paired-development-summary.json). This small change **does not meet the 80/100 target** or validate a general memory system. It is a post-hoc development result on the same spent public questions, not independent transfer. It changes the query protocol/output schema and introduces a bounded search loop, so it does not isolate a single causal component.

The [plan](PLAN.md), [runner/auditor](../../../scripts/hard_memory_iterative_v1.py) and tests were frozen at `05a0ea6` before calls. The complete [raw freeze](raw-freeze.json) was committed at `b33096e` before scoring; [content-free question scores](scores.json) preserve the result. Primary histories and gold are identical to the prior [hard external diagnostic](../hard-memory-external-v1/README.md). No slot, chain map, inferred stale label or gold answer enters generation. The evidence byte ceiling remains 4500; only source records selected from the actual archive may be retained. Intermediate model queries never become accepted facts in the archive.

The owner's subsequent instruction switched the work to an audit. This already running local batch was completed and retained as evidence; no further feature repair was launched after that switch. The [project audit](../../../docs/00-project/project-delivery-audit-2026-11-04.md) also found earlier second-hop work in the repository. The old [mechanism G](../../../docs/research/SECOND_HOP_ASSOCIATIVE_EXPANSION_V1.md) used blind top-hit text as a second query and achieved zero repairs on six cases. The current query-guided loop differs, but prior evidence should have been consulted earlier. Neither mechanism is presented as a new validated architecture.

Full raw evidence remains local outside the public repository. Scoring can be rebuilt without model calls using the pinned prepared files and raw directory:

```text
python scripts/hard_memory_iterative_v1.py score --prepared PREPARED_DIRECTORY --output RAW_DIRECTORY --raw-freeze data/lab/hard-memory-iterative-v1/raw-freeze.json
```

The command creates a new scores file exclusively; use a fresh copy of a raw directory without an existing `scores.json`, or call the read-only `score` function. Do not rerun model inference just to reproduce the score. This result cannot replace the original ordinary-kernel 0/100 result or answer the untested question of production benefit.
