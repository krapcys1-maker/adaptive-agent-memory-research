# Diverse-cue retrieval development protocol v0

Status: frozen development protocol; authored after inspection of PMLAB v0; not confirmatory

## Question

Can mechanisms that change the information used by retrieval—valid-time filtering, trust filtering, and bilingual cue expansion—reduce common-mode failures that remain invisible to agreement between ripgrep and FTS5?

This is a mechanism-isolation development run on the existing 24-query `pmlab-v0-dev` corpus. Its labels and earlier lexical results have already been inspected. It can reject mechanisms or validate instrumentation, but it cannot establish generalization.

## Frozen arms

All arms use SQLite FTS5 and top-k 5. Filtering arms retrieve up to 10 candidates and preserve original rank after filtering.

1. `raw`: unchanged query, no metadata filtering;
2. `time`: keep records whose inclusive valid interval contains `query_time`;
3. `trust`: remove records whose explicit trust field is `untrusted`;
4. `bilingual`: append terms from a fixed, bidirectional English–Polish glossary;
5. `time_trust`: combine valid-time and trust filtering;
6. `time_trust_bilingual`: combine all three interventions.

The fixed glossary is an authored development artifact tailored after corpus inspection. It is not a learned translation system and its result cannot count as held-out cross-language evidence.

No arm may use `category`, `answerable`, `gold_evidence_ids`, or `forbidden_stale_ids` during retrieval. Those fields are scoring labels only.

## Primary metrics

- safe-action accuracy: full gold retrieval without forbidden IDs for answerable queries, or empty retrieval for unanswerable queries;
- selective retrieval risk among non-empty result sets;
- macro Recall@5 for answerable cases;
- forbidden-record intrusion;
- unanswerable abstention;
- cross-language Recall@5;
- per-arm delta from raw.

## Candidate gates

The full arm must satisfy every gate:

- safe-action accuracy at least 15 percentage points above raw;
- forbidden-record intrusion at most 0.05;
- cross-language Recall@5 at least 0.50 above raw;
- unanswerable abstention at least 0.50.

Failure of any gate blocks the full mechanism bundle. Passing every gate still permits only a new held-out benchmark with an independently sourced glossary and labels.

## Interpretation rules

- A gain from time filtering is evidence for metadata-aware validity selection, not human-like temporal memory.
- A gain from trust filtering is evidence for provenance policy, not emotion or intuition.
- A gain from the fixed glossary is a construction test, not multilingual generalization.
- If abstention remains poor, the bundle is not a complete metamemory controller even if recall and intrusion improve.
- Costs are reported as retrieval depth and FTS calls; this small run does not estimate production latency.
