# Project Memory Lab v0 construction report

Status: complete authored construction; independent dual annotation and adjudication pending

## Outcome

Commit `612eb06` freezes the first full-sized PMLAB v0 construction corpus before any lexical baseline is run. It contains 176 evidence records and 120 queries:

| Dimension | Count |
| --- | ---: |
| Registered retrieval strata | 12 |
| Queries per stratum | 10 |
| Development queries | 60 |
| Test queries | 60 |
| Controlled-synthetic queries | 96 |
| Project-research queries | 24 |
| Answerable author hypotheses | 110 |
| Unanswerable author hypotheses | 10 |
| Queries requiring multiple evidence records | 24 |
| Queries with stale/poisoned forbidden evidence | 24 |

The development and test partitions share no history identifiers. Evidence and history IDs are deterministic but opaque, and blind queries do not disclose their history ID or author labels.

## Construction defects found before freeze

The pre-freeze audit found fourteen duplicate query templates, directly decodable evidence/history IDs, three malformed causal questions, and six project records whose cited source was broader than the authored paraphrase. These defects were repaired before `612eb06`; the rejected intermediate output was never called frozen or run against a backend.

Mechanical checks now report zero case-folded duplicate queries, zero history overlap between splits, zero missing project source paths, and no history IDs in the blind query file. This is same-process construction evidence. It does not establish semantic label correctness, acceptable alternative evidence, or template-family independence.

## Blind annotation design

The `blind/` packet contains the complete corpus, label-free query objects, two blank forms, one annotation manual, two blank attestations, and content hashes. Reviewers A and B must:

1. use only the blind packet from `612eb06`;
2. avoid author labels, builder source, backend output, and one another's form;
3. label answerability, required/current/forbidden/alternative evidence, confidence, and notes;
4. hash and attest the completed form before comparison;
5. preserve disagreements for adjudication rather than silently harmonizing them.

`validate_pmlab_v0_annotation.py` rejects missing/duplicate cases, blank or inconsistent identity, unknown or overlapping evidence roles, invalid confidence, mismatched hashes, unsigned attestations, the same reviewer in both slots, and byte-identical dual submissions. A receipt proves only contract and byte integrity. It cannot confer independence, compute agreement, adjudicate labels, or permit a baseline.

## Remaining validity gates

- obtain two genuinely independent complete reviews;
- audit the 24 project paraphrases against exact source locations;
- inspect development/test template-family similarity beyond exact duplicates;
- adjudicate every answerability and evidence-set disagreement in writing;
- keep the selected 36-ID LongMemEval bridge version-pinned and separately scored; audit adapter fidelity before transfer execution;
- preserve the lexical-v0 contract frozen at `e111a57`; any change to query rules, thresholds, bootstrap, cache policy, or missing-data handling creates a new version;
- reproduce `B0`, `B1`, and `B2` in a clean environment.

Local dense embeddings remain locked. Their model, pooling, chunking, index, and fusion rule may be selected only from development data after the lexical result contract is frozen. The test split must not become a tuning set.
