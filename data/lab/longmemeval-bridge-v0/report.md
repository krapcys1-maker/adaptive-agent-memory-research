# LongMemEval public bridge v0

Status: selection and execution protocol frozen before backend execution

The source is `LongMemEval-S cleaned` at Hugging Face dataset commit `98d7416c24c778c2fee6e6f3006e7a073259d48f`. The verified file contains 500 unique questions, 896 answer-tagged turns, and 38-62 sessions per question. Its byte size is `277383467` and SHA-256 is `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.

The bridge selects five answerable questions from each of six official question types and six abstention questions, using only a salted SHA-256 ordering of public question IDs. A base question and its `_abs` counterpart cannot both enter the bridge. No conversations, questions, answers, or evidence IDs are redistributed here. The source remains in the ignored local cache.

This bridge is useful for transfer diagnostics because it exposes evidence sessions/turns, knowledge updates, temporal reasoning, multi-session composition, and abstention. It is not a hidden test: labels are public and contamination is possible. Scores must never be pooled with Project Memory Lab v0.

Abstention is a separate selective-decision metric. Twenty-one of the 30 source abstention rows have zero `has_answer` turns; eight have one and one has two because a required operand is present while another is absent. Their answer-session identifiers point to near-miss sessions, not a complete answer set. Treating those identifiers as ordinary positive retrieval gold would be a scoring bug.

Backends were locked until the PMLAB lexical result and the bridge adapter froze. Those prerequisites are now satisfied; execution may proceed without changing chunking, token budget, query expansion, or fusion based on bridge results.

## Frozen execution adapter

`execution-protocol.json` maps one complete LongMemEval session to one lexical record. Only ordered `role: content` text is indexed. Session IDs, dates, labels, answers, and all question metadata other than the question text are hidden from B1/B2. The unchanged lexical-v0 tokenization and ranking rules run at `k=5`.

The primary transfer outcome is the equal-weight macro Recall@5 across the six answerable question types. The six abstention cases are reported separately as candidate-null and near-miss diagnostics; retrieval alone cannot establish correct abstention. Tracked outputs must remain content-free.
