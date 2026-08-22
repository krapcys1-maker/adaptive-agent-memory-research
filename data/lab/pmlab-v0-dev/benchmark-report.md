# PMLAB v0 development-slice report

Status: completed exploratory instrument run

## Scope and validity

This run used 28 controlled memory records and 24 queries: two for each planned PMLAB v0 stratum. It compares B0 no memory, B1 actual ripgrep with deterministic term scoring, and B2 SQLite FTS5 at top-k 5.

This is **not** PMLAB v0. The author knew the backend design while creating the corpus, labels have not received independent dual annotation, and the set is too small for an architecture decision. The purpose is to test the measurement instrument and expose failure types.

## Results

| Backend | Answerable Recall@5 | MRR | Forbidden intrusion | Unanswerable abstention | p50 latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| B0 no memory | 0.000 | 0.000 | 0.000 | 1.000 | ~0.0001 ms | ~0.0006 ms |
| B1 ripgrep | 0.841 | 0.765 | 0.292 | 0.000 | 90.55 ms | 144.01 ms |
| B2 SQLite FTS5 | 0.841 | 0.735 | 0.292 | 0.000 | 0.053 ms | 0.131 ms |

Latency is diagnostic, not a fair production throughput claim. B1 starts one `rg` process per retained query token; B2 uses an already-open local connection, and index-build time is excluded for both.

## Failures that matter

- **Cross-language retrieval:** both lexical systems scored 0/2. A Polish cue to English evidence and an English cue to Polish evidence were missed.
- **Weak lexical overlap:** both missed the camera record for “photography equipment” because no synonym or semantic mapping was allowed.
- **Contradiction completeness:** both retrieved only one of the two deletion-policy sources.
- **Temporal and supersession safety:** the correct record was retrieved, but the stale alternative also entered top-5 in all four relevant cases.
- **Prompt-injection resistance:** the correct safety record was found, but the untrusted malicious memory also appeared in top-5.
- **Abstention:** both lexical backends returned an irrelevant local-first record for both unanswerable questions because generic terms overlapped. Neither backend has a calibrated rejection threshold.

The apparent 0.841 Recall@5 therefore overstates useful memory behavior. A system can retrieve the right evidence while simultaneously retrieving stale or malicious evidence.

## Instrument findings

1. Report safety metrics beside recall; recall alone is inadequate.
2. Separate retrieval from temporal/current-state filtering. Raw lexical ranking does not resolve validity intervals or supersession.
3. Add a frozen abstention rule or confidence policy before reader-model testing.
4. Cross-language and weak-overlap strata are the earliest justified place to test embeddings or another semantic bridge—but only after the full labels are frozen.
5. Add source-trust filtering and an adversarial-memory metric before any reader sees retrieved text.
6. Benchmark optimized latency separately; this runner intentionally favors transparency over B1 batching.

## Decision

The runner is useful enough to expand, but the dataset is not ready to freeze. Next create 120 examples split by histories/entities, add independent annotator A/B labels and adjudication, audit query leakage, then rerun B0/B1/B2 without changing their frozen retrieval rules.
