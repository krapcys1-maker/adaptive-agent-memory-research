# Project Memory Lab v0 specification

Status: 120-query authored construction frozen; dual independent annotation pending

## Construction checkpoint

The first complete construction corpus froze at commit `612eb06`. It contains 120 queries and 176 records: ten queries in each of the twelve registered strata, balanced 60/60 across development and test with no shared history IDs. Ninety-six queries use controlled synthetic histories and twenty-four use versioned project-research records.

This closes the corpus-count and mechanical split-construction gap, not benchmark validity. Author labels are explicitly non-gold and independent template/provenance review is incomplete. A 36-ID LongMemEval bridge is now version-pinned separately, but it is public transfer evidence and is not part of this corpus. The blind packet requires two reviewers whose forms remain mutually hidden until both byte hashes are frozen. `B0/B1/B2` execution remains locked until their labels are adjudicated and the baseline thresholds are frozen.

## Objective

Create a small, inspectable benchmark that measures retrieval over this research project's durable history before any advanced memory mechanism is selected.

It is a laboratory instrument, not a leaderboard. The first release prioritizes label quality and error diagnosis over scale.

## Corpus families

1. **Controlled synthetic histories:** exact ground truth for updates, delayed utility, distractors, poisoning, and retention mistakes.
2. **Project research history:** reviewed decisions, findings, source cards, failed approaches, benchmark notes, and supersessions from this repository.
3. **Public benchmark bridge:** a small version-pinned sample from LoCoMo, LongMemEval, or another audited dataset, kept separate from project-derived examples.

Results are reported per family; they are never merged into one score without showing composition.

## Example schema

```json
{
  "example_id": "PMLAB-0001",
  "history_id": "H-001",
  "query_time": "2026-08-22T12:00:00Z",
  "query": "Which conclusion replaced the original decision?",
  "language": "en",
  "category": "supersession",
  "answerable": true,
  "gold_evidence_ids": ["E-009", "E-014"],
  "gold_current_ids": ["E-014"],
  "forbidden_stale_ids": ["E-009"],
  "consequence_weight": 3,
  "notes": "Requires old and new state but only new is currently valid."
}
```

## Pilot composition

Build a 120-query pilot, ten examples for each stratum:

1. exact lexical;
2. paraphrase;
3. weak lexical overlap;
4. what-where-when;
5. temporal `as of`;
6. current state after supersession;
7. contradiction requiring both sources;
8. causal/multi-episode;
9. procedure or failure avoidance;
10. unanswerable/abstention;
11. Polish-English cross-language cue;
12. prompt-injection or irrelevant-memory resistance.

This size is for instrument debugging. It is not powered for a final architecture claim. Confidence intervals and error distributions determine the size of v1.

## Split policy

- Split by complete history and entity, not by query alone.
- Paraphrases of one fact stay in one split.
- Synthetic templates and entity vocabularies differ between development and test.
- Public benchmark data never enters a project-derived split.
- Test labels are hidden from backend tuning.

## Gold-label procedure

1. Annotator A selects all supporting evidence and stale/forbidden evidence.
2. Annotator B works independently without seeing A's labels.
3. Disagreements are adjudicated with a written reason.
4. An adversarial pass searches for acceptable alternative evidence and leakage.
5. Gold is frozen and hashed before backend comparison.

Inter-annotator agreement is reported, but agreement does not replace adjudication of missing gold evidence.

## First registered comparison

Backends:

- B0 no memory;
- B1 `rg` with a frozen tokenization/query-expansion rule;
- B2 current SQLite FTS5 implementation;
- O full reviewed evidence oracle.

Controls:

- identical corpus snapshot;
- top-k and retrieved-character/token budget;
- same hardware and warm/cold-cache policy;
- no reader model in the primary retrieval result;
- reader evaluation performed later with a fixed prompt and at least two provider/model families where subscriptions allow.

Primary metric: macro Recall@5 across the 12 strata, with critical-memory miss rate reported separately.

Secondary metrics: MRR, nDCG, evidence recall per token, stale intrusion, abstention, p50/p95 latency, index size, and scale degradation.

## Leakage and validity checks

- Verify whether each gold answer can be found in filenames, titles, or query text alone.
- Detect duplicate episodes across splits.
- Keep query authors blind to backend behavior where feasible.
- Do not use this conversation or its paraphrases as both instruction text and held-out test questions.
- Report results both with and without `CURRENT_STATE.md`, because that file is a curated summary and may hide retrieval weaknesses.

## Release gate

`v0` may be called ready only after the corpus license/provenance audit, dual annotation, adjudication, split-leakage check, baseline manifest, and one clean-environment reproduction are complete.
