# NOBI327/amygdala repository audit

Status: pinned local code audit; mechanism donor only; not an adopted dependency

## Snapshot and reproducibility

- Repository: https://github.com/NOBI327/amygdala
- Audited commit: `344133c15966075b41a41862375a56b34cdde2f8`
- Commit date: 2026-03-27
- License: MIT
- Local ignored cache: `external/repos/NOBI327__amygdala/`
- Python 3.12 test run without `OPENAI_API_KEY`: one failure because the OpenAI adapter factory eagerly constructs a client that requires a key.
- Repeat with a non-secret dummy key: 331 passed, one skipped, reported coverage 85%.

The tests establish internal behavior under authored fixtures. They do not compare memory quality with lexical, FTS5, dense, hybrid, no-memory, or oracle controls.

## What is actually implemented

- SQLite working, pinned, long-term, graph, and recall-log tables;
- an MCP interface and Anthropic/OpenAI/Gemini adapter boundary;
- automatic transcript capture through a Claude Code stop hook;
- eight nonnegative emotion axes plus importance and urgency;
- scene tags, time decay, recall feedback, graph expansion, and diversity injection;
- local daemon/session-hook paths for proactive context injection.

The central search score is not semantic content retrieval. It combines cosine similarity over emotion axes, Jaccard scene overlap, time decay, recall-derived relevance, and cosine similarity over importance/urgency. The query string is used upstream to obtain tags, but `SearchEngine.search_memories` ranks all active rows from those tags and scenes rather than lexical or semantic content match.

## Reusable ideas

1. Provider adapters behind a local MCP boundary.
2. Explicit pinning as a user-authorized control distinct from inferred salience.
3. A diversity watchdog as an experimental arm against feedback-driven recall monoculture.
4. Session hooks and proactive context as trigger-policy candidates.
5. Emotion-only retrieval as a concrete scalar/vector salience baseline to falsify.

These ideas are candidates for isolated reproduction, not justification for importing the full runtime.

## Material risks

### Retrieval validity

- Content relevance can lose to affect/scene similarity because the core ranker has no lexical or dense content term.
- Importance/urgency similarity is added outside the multiplicative time-decay term, so its contribution does not decay with the main affect/scene component.
- Recalled/used items increase relevance and receive a longer half-life, creating a feedback loop that can amplify early mistakes.
- The diversity mechanism samples underrepresented emotion categories, not missing evidentiary obligations.

### Capture and authority

- The stop hook treats most user turns of at least 30 characters as significant and may store truncated user/assistant dialogue automatically.
- Assistant output and inferred tags can enter memory without source-truth, trust, authorization, or support distinctions.
- The schema lacks evidence IDs, source provenance, event/observation/validity/transaction time separation, supersession relations, checksums, and query-specific completeness certificates.
- Emotion, importance, urgency, and entities may be supplied by the calling LLM, so a prompt or dramatic wording can influence persistence and retrieval.

### Evaluation and portability

- Keyword auto-tagging is primarily Japanese, while the project requires Polish/English and provider/model variation.
- The advertised biological names are analogies, not validated biological equivalence.
- The default adapter configuration is Anthropic-oriented even though adapters exist; one test requires an OpenAI key merely to construct the client.
- No LongMemEval, LoCoMo, PMLAB, collateral-memory, poisoned-salience, supersession, or held-out emotional-language benchmark is present in the audited snapshot.

## Verdict

Retain at catalog tier C as a useful, permissively licensed experimental comparator. Do not make it the project's memory foundation and do not import its schema or scoring constants. If evaluated, use its emotion/scene ranker as the scalar/vector-salience arm under the same frozen corpus and budget as lexical and raw-retrieval controls.

Promotion requires it to beat content-based retrieval on supported task outcomes while passing quiet-critical, collateral-loss, stale-version, poison-persistence, provenance, multilingual, and cost guardrails. Its own unit suite is necessary engineering evidence but not memory-science evidence.
