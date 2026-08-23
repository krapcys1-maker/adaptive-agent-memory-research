# Current project state

## Objective

Research a local-first, model-agnostic long-term memory layer for LLM agents. The model context window remains working memory; durable evidence, experiences, conclusions, and procedures live on the user's disk.

## Current phase

Evidence collection and gated laboratory testing, run in three parallel tracks — engine, experiment, community — under [`docs/00-project/operating-doctrine.md`](../docs/00-project/operating-doctrine.md). New preregistrations are paused until the existing unexecuted drafts are triaged. No validated final architecture is claimed.

## How to read this file

This is the **short** current state. The full diagnostic history lives in [`DIAGNOSTICS_ARCHIVE.md`](DIAGNOSTICS_ARCHIVE.md), which is indexed and searchable but deliberately not forced into every context bundle. Nothing was deleted when it was moved out.

## What the memory tool now is

Git-tracked append-only JSONL plus reviewed Markdown is canonical. SQLite FTS5 is a disposable index. MCP stdio serves Codex, Claude Code and other clients; the CLI is the documented fallback. No model API key, vector database, graph database, or cloud account is required. External API models are optional, replaceable batch workers; they may write review candidates but never accepted evidence.

**Schema version 2** carries valid time. `created_at` and `expired_at` are transaction time, `valid_from` and `valid_to` are valid time, plus `claim_class` and `supersession_kind`. The two end-of-interval fields are **derived from the successor at read time**, never stored, because an append-only log cannot edit the record it ends and a stored end could drift from the revision that caused it. Version-1 events still read correctly through `tools/project_memory/upcast.py`.

## What is mechanically enforced

- CI runs the suite on Python 3.11 and 3.12 and blocks on the repository claim audit.
- `scripts/verify_memory_integrity.py` checks every invariant decidable from the bytes of `events.jsonl`, measured by 21 registered mutations.
- The canonical-store guard fails any pull request that deletes or rewrites a line of the log, or commits the disposable index.
- `.gitattributes` disables end-of-line conversion, so a declared hash reproduces on every platform.

## Settled this phase

- **Association graph as retrieval fusion: closed, negative.** `PMLAB-ASSOC-E1` inconclusive, `E2` retracted as a leakage artifact, `E3` measured harm at −0.114 Recall@5 on mechanical gold. The flaw is seeding expansion from lexical hits, which helps in neither regime. The graph is retained as *structure*, not as fusion.
- **Supersession cannot be solved by retrieval.** `PMLAB-STALE-E1`: a superseded fact and its replacement sit at the 99.5th percentile of corpus similarity, two pairs at cosine exactly 1.000. It must live in the schema.
- **Cross-language retrieval.** `PMLAB-XLANG-E1` measured Polish Recall@10 at 0.156 against English 1.000, with 26 of 45 queries returning nothing. A glossary lifted it to 0.867; local dense retrieval reached 0.978 in `E2`, but its safety cost is unmeasured and dense makes stale intrusion structurally worse.
- **Provenance repair.** 843 of 1348 lab files diverged between working copy and blob; now 0. Six broken freezes resolved as two distinct defects. Zero critical audit findings.

## Open blockers

1. Dense retrieval is **not** adopted. Its recall case is settled; its safety case is untouched and needs forbidden and stale intrusion measured against the new valid-time labels.
2. Independent review remains the scarcest tier. Four packets need it; the [independence ladder](../docs/00-project/independence-ladder.md) exists so that most claims no longer do.
3. Of 21 unexecuted preregistrations, 0 have a corpus and 18 need a reader model. The binding constraint was never reviewer scarcity — it is that no fixture exists.
4. Key grinding in the sealed split cannot be prevented offline. The manifest records whether a key was externally witnessed.

## Immediate priorities

1. Build one corpus family. Four fixtures would unblock sixteen experiments; treating the drafts as 21 separate items is why none moved.
2. Measure dense retrieval's forbidden and stale intrusion before considering any index change.
3. Run the six-round coverage protocol and repair the distinction between discovered, screened, read, and independently reviewed sources.
4. Fully read and snowball the comparative source seeds for animal, motor, skeletal-muscle, immune, transcriptional, non-neural, CRISPR, and collective memory.
5. Test emotional salience only after utility labels and consequence-weighted retention metrics exist; never equate operational signals with subjective emotion.
6. Preserve rejected ideas, null results, and failed runs as labeled evidence.
7. Run a synthesis checkpoint after 25 screened records or three newly primary-read decisive sources in one topic.
