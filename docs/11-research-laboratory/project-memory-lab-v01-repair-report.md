# Project Memory Lab v0.1 query-form repair report

Status: M2 model-reviewed exploratory gold frozen; one frozen lexical run permitted; H-tier confirmation pending

## Why v0.1 exists

PMLAB v0 was rejected before annotation and before any backend run because development and test questions reused authored frames. Preserving v0 makes that instrument failure auditable. V0.1 is a narrowly scoped replacement rather than a silent edit.

## Frozen repair

Candidate commit `cc904dd`:

- preserves the complete 176-record evidence corpus byte for byte (SHA-256 `260b44de1314629aaa7efd5bffe2157bd2414548cce2501cff6998f6ebae0d9d`);
- preserves all IDs, histories, splits, categories, times, answerability hypotheses, required-evidence relations, and forbidden-evidence relations;
- keeps all 60 development queries unchanged;
- changes all 60 test query forms;
- creates new blind-query SHA-256 `6dca3fcea6e7b7830231444d6e8050952843bbe8974f78633889e6ac76c056bf` and matching attestations;
- reads no backend output because no PMLAB v0 or v0.1 backend run exists.

## Construction checks

The same label-free screen that flagged 22 of 300 v0 pairs flagged 0 of 300 v0.1 pairs. Across the twelve categories, maxima were 0.496 sequence ratio, 0.294 token Jaccard, and 0.367 character-trigram Jaccard. Direct author inspection also classified each development/test form family as distinct.

These numbers are descriptive, post-hoc construction checks. They do not prove semantic independence and do not validate labels.

## Model-review fallback outcome

The project used the registered M1/M2 fallback because no external human reviewer was available:

1. A fresh blind DeepSeek M1 context accepted all twelve leakage categories without seeing corpus answers, author labels, builder source, or backend output.
2. Two stateless M2 roles independently labelled all 120 questions using distinct prompts and deterministic input orders. Exact label agreement was 95/120 (0.7917).
3. A third blind role saw only the 25 disputes, full blind evidence, and anonymous candidates; it adjudicated every dispute.
4. Exploratory gold is frozen at SHA-256 `ed9f88778c42526ae37762b6a47e40c2ab7381c3eb2f10703851e3d1004d170f`.

This author-operated same-family process is operationally blind but not institutionally independent. It permits one execution of the already frozen B0/B1/B2 lexical protocol with a permanent exploratory label. Human/cross-family confirmation, confirmatory claims, and architecture promotion remain closed.
