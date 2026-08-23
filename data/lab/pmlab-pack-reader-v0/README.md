# PMLAB-PACK-READER-001 artifact map

Status: first-reader branch complete; synthetic fixture spent

## Which manifest means what

- `manifest.json` is the immutable-in-meaning **construction freeze snapshot**. Its `api_authorized=false`, `runner=not-built`, and pre-run status fields describe the moment before runner construction. They are deliberately not rewritten as live status.
- `execution-deepseek-v4-flash-v0/manifest.json` is the **execution receipt**. It pins the fixture and prompt commits, model/decoding, caps, prompt/raw/score hashes, call count, and observed cost.
- `execution-deepseek-v4-flash-v0/completion-audit.json` is the post-run **completion receipt**. It checks exact Git milestone order and byte identity, prompt leakage, cost authority, one-call/no-retry execution, budget-ledger joins, raw-before-score separation, deterministic metrics, gates, and claim limits.

The frozen protocol thresholds remain recoverable at commit `d870741e8bba6257d12288b23d1e8f367571ae6e`. Later status and audit additions do not retroactively change those thresholds.

## Milestones

1. Fixture/gold/source/schedule freeze: `365c0b6c0ae159b1517fbc87941aa33a8e369da2`.
2. Prompt/runner/scorer freeze: `d870741e8bba6257d12288b23d1e8f367571ae6e`.
3. Pre-run authorization: `5f98277`.
4. Raw-response freeze before gold join: `1df509b7b71f144fb924ba3737ec6c919de5857e`.
5. Score, report, and deterministic result audit: `b114865`.

## Decision

All frozen single-reader compatibility gates passed. Preserve full paths as the baseline and compact aliases as a candidate. Do not promote governed ordering or claim compact superiority. The next admissible evidence is an unchanged different-model-family replication or independently reviewed natural-history development.
