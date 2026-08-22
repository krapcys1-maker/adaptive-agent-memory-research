# Project Memory Lab v0.1 query-form repair report

Status: candidate frozen; independent leakage review pending; retrieval execution locked

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

## Gates that remain closed

1. An auditor independent of corpus construction must accept or reject the query split and disclose prior exposure.
2. If accepted, two distinct reviewers must annotate the blind packet independently and freeze signed receipts.
3. Disagreements require written adjudication before author hypotheses are compared or gold is frozen.
4. Provenance, alternative evidence, template leakage, and gold hashes must be accepted.
5. Only then may B0/B1/B2/O execute under the unchanged protocol frozen at `e111a57`.

No DeepSeek or Codex self-review qualifies as the independent gate.
