# Natural-history corpus eligibility audit v0

Status: preserved pre-builder inventory for contract v0.1; design issues are repaired in the v0.2 source-unit audit, but no corpus or benchmark output exists

Audited commit: `4ab0684a3da3c30446ea9c3345ea35009517d1e5`

## Inventory

The pre-protocol commit contains:

| Item | Count |
| --- | ---: |
| tracked files | 1,401 |
| Markdown files | 213 |
| CSV files | 15 |
| JSON files | 157 |
| JSONL files | 179 |
| Markdown files under `docs/` | 115 |
| canonical project-memory event lines | 114 at the audited commit; 118 after this work's four new events |
| lab summary `README.md` / `report.md` files matched by the initial inventory | 49 |
| tracked paths under a `blind/` directory | 29 |
| tracked paths under an `artifacts/` directory | 26 |
| tracked API-screening paths | 111 |

There are 1,171 Markdown headings across the audited tree. Of those, 872 are in top-level orientation files or `docs/`, 7 are in canonical memory orientation/record files, and 128 are in the initially matched lab README/report set. These are upper bounds on section units, not a final corpus count.

## Findings

1. A naive `index every tracked file` policy is invalid. More than four fifths of tracked paths are under `data/`, including gold, blind review material, API outputs, and generated artifacts that can leak labels or dominate rankings.
2. The project has enough reviewed prose and append-only events for a natural-history development corpus. It does not yet have enough authentic pre-output queries for a powered prospective test.
3. `CURRENT_STATE.md` duplicates and compresses many primary records. It must be a registered include/exclude factor rather than silently mixed into the primary corpus.
4. Section boundaries are preferable to whole Markdown files, but a fixed model-token limit would favor one embedding tokenizer. The common unit ceiling must therefore be selected as UTF-8 bytes on development, with every model reporting actual truncation.
5. Historical Git reconstruction is mandatory. Indexing the latest tree for an earlier query would leak future conclusions and corrections.
6. Exact duplicate content can consume top-k without adding evidence. Exact byte duplicates may be collapsed with source aliases. Near-duplicate semantic collapse is not admitted because it would introduce another learned mechanism.
7. Paths, filenames, headings, timestamps, status, trust, and provenance can be useful later, but the first representation comparison must expose only opaque ID plus byte-identical search text. Metadata-aware retrieval is a separate B3/C3 mechanism.

## Design disposition

The inventory remains valid, but the initial contracts required revision for stable cross-snapshot IDs, declared Git object formats, heading-bearing search text, canonical row serialization, and private-origin receipts. Those repairs are documented in `docs/07-literature/natural-history-source-unit-contract-audit-v0.md`. The revised policy and schemas are candidates for independent review. A builder remains locked until the byte ceiling, historical snapshot semantics, Markdown parsing, exact-duplicate aliasing, privacy controls, and exclusion tests freeze. This audit does not authorize embedding downloads or backend execution.
