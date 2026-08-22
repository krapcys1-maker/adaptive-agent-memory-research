# PMLAB v0.1 lexical failure localization

Status: post-hoc descriptive analysis of sealed exploratory output; decision and thresholds unchanged

## What advanced

B2 beat B1 on Recall@5 for 5 answerable queries, lost on 1, and tied on 49. It recovered 3 complete-evidence cases that B1 missed and lost 0 B1 successes.

The warm median query-time ratio was 1637.4x in B2's favor, while the FTS5 index used 4.28x the bytes of the ripgrep text view.

## What remains unsafe or incomplete

Absolute B2 macro Recall@5 was 0.755; all-required@5 was 0.673. It missed complete evidence on 10/14 critical queries.

B2 retrieved forbidden evidence on 9/60 queries. It introduced 1 forbidden cases absent from B1 and removed 0 B1 forbidden cases.

Both lexical backends returned candidates for every one of the 5 unanswerable queries. Candidate-null behavior therefore remains 0; this is not an abstention mechanism.

The weakest B2 answerable strata were cross-language (0.200), paraphrase (0.400), causal multi-episode (0.500), and poison resistance (0.500). These are failure-localization targets, not permission to tune on the spent test set.

## Consequence

FTS5 advances only as the stronger sparse retrieval baseline for a new preregistered experiment. The result does not admit dense embeddings, graphs, salience, a reader policy, or product architecture. The current test set is spent and must not be used to tune B2 or a successor.
