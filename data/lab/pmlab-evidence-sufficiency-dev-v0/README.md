# PMLAB evidence-sufficiency construction corpus v0

Status: authored construction freeze; not held out; no architecture claim permitted

The corpus isolates relevance, answerability, facet completeness, bridge completeness, validity, authorization, conflict, attribution, collection closure, and redundant retrieval. It contains paired English and Polish cases and keeps collection state separate from the currently retrieved evidence set.

The first Git commit containing `cases.jsonl`, `manifest.json`, and the builder is the freeze boundary. Any later label or case change creates a new dataset version. The future runner must verify `case_sha256` before scoring.

Obligation mappings, evidence support, reader scores, and expected actions are authored diagnostic labels. Passing this corpus can validate only that a policy implements the intended state machine. It cannot establish decomposition accuracy, learned-judge calibration, real retrieval performance, multilingual generalization, or deployment safety.
