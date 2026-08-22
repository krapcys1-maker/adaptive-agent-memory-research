# Laboratory data

Machine-readable research-control files. Empty cells mean unknown or not yet audited, never zero evidence.

- `coverage-matrix.csv`: current evidence state and next action by topic.
- `search-log.csv`: every reproducible search round and its novelty yield.
- `experiment-registry.csv`: preregistered, exploratory, failed, null, and completed experiments.
- `backend-registry.csv`: ordered retrieval candidates and unlock requirements.
- `pmlab-metamemory-control-dev-v0/`: frozen authored corpus and deterministic construction test for typed monitoring and retrieval control.
- `pmlab-evidence-sufficiency-dev-v0/`: frozen answerability, obligation, claim-support, attribution, conflict, and collection-closure construction test.
- `pmlab-collection-closure-dev-v0/`: preserved first freeze whose insertion-counterexample stratum failed to isolate the intended mechanism.
- `pmlab-collection-closure-dev-v1/`: pre-run repair, frozen 48-case closure corpus, deterministic ablations, artifacts, and construction report. No held-out claim is permitted.
- `PMLAB-MAP-001` is a preregistration-only obligation decomposition and per-obligation scope-mapping experiment in `docs/11-research-laboratory/obligation-scope-mapper-protocol.md`; no corpus or parser exists.
- `longmemeval-bridge-v0/`: 36 version-pinned public LongMemEval-S question IDs selected by a preregistered hash rule; source conversations remain in an ignored verified cache, abstention near-miss sessions are not treated as retrieval gold, and no backend has run.
- `pmlab-v0-lexical-preregistration/`: machine-readable lexical-v0 backend boundary, metrics, bootstrap, guardrails, and decision rules frozen at `e111a57`; execution remains false until dual review and adjudicated gold.
- `pmlab-v0-split-audit/`: label-free post-construction audit that rejected the v0 held-out split before review or backend execution after flagging 22/300 dev/test pairs in three repeated-frame categories.
- `pmlab-salience-ontology-review-v0/`: gold-free blind packet with 12 operational factors and 24 boundary probes for independent review before any outcome corpus or salience controller is built.

Large corpora and run artifacts belong in ignored, reproducible caches with versioned manifests. Final compact metrics and conclusions belong in Git.
