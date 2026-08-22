# LongMemEval bridge v0 lexical transfer result

Status: complete public transfer diagnostic

Decision: `supports-sparse-transfer`. This result has no architecture-promotion authority and is never pooled with PMLAB.

## Primary comparison

- B1 macro Recall@5: 0.933333
- B2 macro Recall@5: 0.983333
- paired B2-B1: +0.050000
- stratified 95% bootstrap interval: [0.000000, 0.116667]
- deterministic across primary and two fresh processes: true

## Abstention boundary

B1 candidate-null was 0.000 and B2 candidate-null was 0.000. These are candidate-generation diagnostics, not correct-answer abstention. Near-miss intrusion at five was 1.000 for B1 and 0.833 for B2.

## Interpretation boundary

The bridge is public, small, and potentially contaminated. It tests whether an unchanged sparse lexical adapter transfers to session retrieval. It does not test a reader, completeness controller, durable-memory lifecycle, or a final architecture. No source question, answer, conversation, raw session ID, or evidence label is present in tracked execution artifacts.
