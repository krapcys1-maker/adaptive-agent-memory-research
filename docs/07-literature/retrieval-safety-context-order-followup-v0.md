# Retrieval safety and context-order follow-up v0

Status: targeted primary-source follow-up triggered by `PMLAB-REUSE-CHAR-001`

All hypotheses in this document are post-hoc proposals generated after the characterization result. They are not registered outcomes and cannot be tested without a separate frozen protocol.

## Trigger

The synthetic characterization found three coupled effects:

- local dense retrieval greatly improved semantic and cross-language recall while increasing forbidden/stale intrusion;
- RRF improved the sparse baseline but did not beat the dense component;
- citations and section headers consumed enough of a fixed byte budget to drop required evidence in some packs.

These observations do not establish general effects. They identify the next mechanisms and controls that need primary-source grounding.

## Rank fusion is a comparator, not a law

Cormack, Clarke, and Buettcher introduced RRF as a simple rank-only fusion rule and reported aggregate gains across their TREC/LETOR evaluations. The result justifies RRF as a strong untuned baseline. It does not prove that RRF beats every component on every corpus, representation pair, depth, or safety metric.

Our result is compatible with that boundary: sparse and dense errors were not always complementary, and the fused ranking inherited stale candidates. The next analysis must report per-query component discordance, overlap, unique wins, unique harms, and depth sensitivity. Tuning `k`, weights, or depth on the 20 visible cases is prohibited.

Primary source: [Cormack et al., SIGIR 2009](https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/).

## Ordering a context pack is a reader intervention

Liu et al. found that reader performance can change substantially with the position of relevant information and is often strongest when evidence appears near the beginning or end of a long context. Therefore `current -> supporting -> stale` is not a neutral formatting choice. It may protect a reader from stale evidence but can also push necessary supporting evidence into a weak position.

The next reader experiment must hold retrieved IDs and bytes constant while permuting order. It must separate:

- current-first governance benefit;
- relevance-first answer benefit;
- stale-at-end warning benefit;
- critical-evidence duplication cost;
- provider/model-specific position effects.

Primary source: [Liu et al., TACL 2024](https://aclanthology.org/2024.tacl-1.9/).

## Retrieved memory is an untrusted input channel

Greshake et al. demonstrated indirect prompt injection through data later retrieved by LLM-integrated applications. PoisonedRAG formalizes knowledge-base corruption and reports strong targeted attack success in its evaluated settings. These sources make one architecture boundary non-negotiable: retrieval relevance cannot authorize an instruction or external action.

The characterization's untrusted omission proves only that an already-labelled record can be excluded. It does not detect adversarial content, resolve mixed trusted/untrusted spans, or protect a model that has already seen the malicious text. Trust and authorization filters must run before context construction, and external actions need a separate policy boundary.

Primary sources: [Greshake et al., 2023](https://arxiv.org/abs/2302.12173), [Zou et al., USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/zou-poisonedrag).

## New falsifiable hypotheses

### H-CHAR-01 — complementarity-gated fusion

RRF improves over the stronger component only when sparse and dense arms have enough distinct correct top-depth candidates and do not contribute disproportionate forbidden candidates.

Reject if predeclared complementarity measures cannot predict the direction of held-out RRF gain better than a constant stronger-component choice.

### H-CHAR-02 — compact evidence references

Compact citation IDs plus one footer dictionary preserve more required evidence than repeated full path/line strings under an equal UTF-8 budget without reducing exact citation resolution.

Reject if retained-required gain is below five points or any citation becomes ambiguous or invalid.

### H-CHAR-03 — governed order versus reader position bias

Current-first/stale-last ordering reduces stale-use errors but can reduce multi-evidence answer accuracy when required supporting evidence moves into middle positions.

Reject the fixed order if no stale-use benefit appears or if the answer-accuracy loss exceeds its preregistered guardrail.

### H-CHAR-04 — retrieval cannot supply abstention alone

A typed completeness/trust controller reduces unsupported answers at matched coverage compared with any non-empty, similarity-threshold, or backend-agreement rule.

Reject if the typed controller does not dominate baselines on held-out risk-coverage or causes critical false negatives.

## Research decision

Do not tune the current fixture. Preserve it as a spent implementation diagnostic. Advance only its deterministic contracts: exact citations, explicit omission reporting, reversible metadata buckets, and reproducible rank traces. Dense selection, fusion choice, trust classification, order, and abstention remain separate experiments.
