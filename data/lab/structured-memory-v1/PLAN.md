# Source-grounded structured runtime: engineering development v1

This executes the previously missing model-extracted arm of issue #47 and the
capture/lookup boundary identified by PR #104. It is an engineering candidate,
not a new final architecture or a confirmatory preregistration. Codex implements
and assesses the system. Models only perform extraction and question translation
inside the tested system. No model plans project changes or judges correctness.

## Frozen execution boundary

Commit this plan, config, runtime, runner and tests before model calls. Keep
attempts, final outputs, captures, plans, source paths and manifests outside Git;
publish hashes and content-free scores. Do not edit a pinned source after a run;
version amendments separately. Source provenance and raw outputs are frozen
before the separate scoring command opens gold. Preserve all earlier negatives.

## Mechanism

1. Save every raw source to an append-only, checksummed log before extraction.
2. A model proposes literal subject/predicate/object claims. Code checks spans
   and bounds. Unextractable text remains stored. Nothing sees questions or gold
   during extraction. Learned literal sentence shells reduce repeated calls;
   these are induced from text, not hand-coded domain relations or question rules.
3. Resolve state with provenance. Generic sources default to unresolved conflict.
   Only the MAB source adapter declares ordered single-value overwrite, as the
   benchmark specifies. Recording/knowledge time and effective time differ.
4. A model translates each question into a bounded relation path, with literal
   anchors from scoped memory and the learned relation catalog. Code executes
   that path. The returned value is a system-computed answer with source proofs,
   **not** the raw reader's answer, memorization or a claim about model reasoning.
5. Lookups are read-only. No missing answer creates or revises a fact.

## Execution and interpretation

- Run the 15+ deterministic boundary tests first: restart, scope, conflict,
  explicit updates, negation, future validity, expiration, corruption and identity.
- Prefer existing local Qwen 2.5 14B (pinned installed digest). Use local capture
  first and then all 100 questions from the already-spent FC-MH 262k corpus.
- Compare Flash planning on the same captured graph, without treating shared
  extraction as independent end-to-end Flash capture. If local extraction fails,
  retain it and run a separately frozen Flash-capture amendment, not a hidden retry.
- Three transport controls precede each phase. Failed controls stop that phase.
- Report extraction coverage, model/cache counts, quarantines, catalog, answer
  statuses, exact correctness, paths, calls, cost and wall time. No partial run
  may masquerade as a complete 100-question result.
- Development aspirations: at least 80/100 exact and 99.9% non-header capture,
  zero span-inventing claims, no contract regression. These are our engineering
  targets, not an industry standard or a claim of readiness. Failure requires
  diagnosis, not benchmark-specific gold routing.
- Next transfer boundary: unsupplied fields in journal prose and H1 development
  data, with query routing and obsolete leakage. No sealed H1 or LifeSim splits.

## Resources

New task, new cumulative ledger; neither old PR #103 nor #104 ledger is reset or
reused. API: official DeepSeek V4.1 Flash only (`deepseek-flash`, metadata identity
checked before/after), thinking disabled, no Pro/provider fallback/retry. Reuse
the unchanged strict Flash client: at most 205 paid attempts, $1 permanent reserve
cap, $.004 each, max 512 output tokens, max 6000 message bytes and four messages.
Actual usage is priced at the previously verified peak/uncached upper rates and
is not an account invoice. Halt on unknown usage. Local: one GPU, no downloads,
at most 205 calls/3600 seconds per phase, at most four phases in this candidate.
Unload only our own model. No private NIE data is transmitted. No production,
NIE personality, prompt, deployment or original-worktree changes.

## Known limits before execution

Span validation is not proof of semantic extraction accuracy. Learned shells
can overgeneralize; this is measured development, not a general parser. Aliases,
coreference, multi-valued properties, arbitrary time prose, causal/procedural
reasoning and uncertain claims are not solved by a short relation path. A model
may choose the wrong relation. Conflict defaults can decline valid multi-valued
answers. No world-knowledge correction is permitted on counterfactual facts.
