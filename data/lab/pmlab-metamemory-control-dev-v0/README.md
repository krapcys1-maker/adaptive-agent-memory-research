# PMLAB metamemory-control development corpus v0

Status: authored development freeze; not held out; no architecture claim permitted

This corpus is a construction test for the typed monitoring and control proposal in `docs/12-interdisciplinary-memory/metamemory-selective-control-synthesis.md`. It deliberately crosses clean evidence with misleading scalar confidence, familiar poison, stale versions, semantically consistent unsupported answers, disagreement despite valid evidence, ambiguity, absence, conflict, alternate cues, and direct-ID recovery.

The first Git commit containing `cases.jsonl` and `manifest.json` is the freeze boundary. Any later change creates a new dataset version. A runner may be developed after this boundary, but it must verify `case_sha256` before scoring.

The cases are synthetic and authored to expose control semantics. Passing them can show only that an implementation follows the intended state machine. It cannot demonstrate real retrieval quality, calibrated confidence, biological similarity, or generalization.
