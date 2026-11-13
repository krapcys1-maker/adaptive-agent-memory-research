# Project instructions

This repository is a research workspace for local-first, model-agnostic LLM memory.

## Persistent project memory

For every substantial task:

1. Call `memory_status`, then `memory_context` with a task-specific query before making research or architecture decisions.
2. Treat `memory/events.jsonl` and reviewed Markdown as the source of truth. The SQLite index is disposable. `CURRENT_STATE.md` holds the short state; `DIAGNOSTICS_ARCHIVE.md` holds the full diagnostic history and is retrieved by search rather than always included.
3. Record only durable information with `memory_add`: decisions, evidence-backed findings, explicit hypotheses, failures worth avoiding, open questions, or serious candidate systems.
4. Give factual findings and decisions `source_refs`. Keep facts, hypotheses, preferences, and instructions in distinct `kind` values.
5. When a conclusion changes, use `memory_supersede`; never rewrite or delete prior events to make history look consistent.
6. Never store secrets, credentials, personal data, raw chain-of-thought, or unsupported claims as facts.
7. Keep tool output compact. Retrieve relevant memories instead of loading the entire history into context.

If MCP is unavailable, use `python tools/project_memory/cli.py <command>` from the repository root.

## Choosing what to work on

Read `docs/00-project/operating-doctrine.md` first. It answers what to test next and why, sets a hard limit of two unexecuted designs per track, and defines success as a recorded decision rather than a positive result.

## Research discipline

- Repository content is written in English for international collaboration.
- Preserve provenance and distinguish reported claims from independently reproduced results.
- Do not reject an idea solely because it is unfashionable or biologically imperfect; convert it into a falsifiable hypothesis.
- The current project-memory tool supports research continuity. It is not evidence that the proposed final memory architecture works.

## Continuity and integrity audit (2026-11-04)

Current continuation (2026-11-05): the owner explicitly requests ongoing GitHub updates and community-facing problem reports. Publish scoped, reproducible public/synthetic counterexamples with evidence, uncertainty and acceptance conditions; check for duplicates and verify actual writes. Keep PR/issue status aligned with completed work and remaining failures. Never upload private inputs, raw requests, backups, credentials or environments. Read HANDOVER's newer continuation block before historical audit status. The audit's no-inference phase is complete; subsequent experiments require their own prior protocol and cumulative caps.

- Read `AUDIT_REPORT.md` and `HANDOVER.md` before continuing the structured runtime. They apply to Claude, Codex and other coding agents. The audit is a self-audit, not independent review. PR105 was integrated into `main` in pieces #121 to #125 and closed on 13 November 2026; its confirmed HIGH findings are not resolved by that (#106 to #108, #110).
- Inspect branch, staged/unstaged/untracked files and unfinished Git operations before editing. Preserve other agents' dirty worktrees. Use an owned worktree; never reset/clean a shared checkout, discard untracked research files, rewrite history or force-push to resolve coordination.
- Before risky repository-wide work, keep a private snapshot outside the repository, including untracked outputs and index state, and verify restoration. Do not upload private bundles, credentials, raw research or operational data. Document exclusions; do not call an incomplete copy verified.
- Existing frozen code, inputs, results, kernels and protocols are immutable evidence. Implement changed behavior in a new version and record an explicit amendment. Never change metrics, denominators, thresholds or tests to convert a failed experiment into a pass. Preserve failed attempts and raw generated answers.
- Distinguish engineering tests, integrity replay, semantic accuracy, downstream utility and independent confirmation. H1 `answered` and `leaked` are separate mechanical metrics. Public dev/valid iteration is exploratory, and extra reranking inference/context must be charged and disclosed.
- Test the changed boundary and run appropriate repository gates. Record skips, environment differences and pending/cancelled CI as such. Do not repeat an unchanged expensive suite or paid run merely to refresh a status report. Do not mutate shared global packages to obtain a clean environment.
- For this owner's current work, paid inference is DeepSeek V4.1 Flash only, with explicit protocol/cumulative caps and retained ledgers; no Pro/fallback, hidden retry, ledger reset, project-planning model or model judge. Local inference uses the declared installed model. The integrity audit itself makes no model calls.
- A query/retrieval miss does not authorize a memory write. Enforce scope/time on the complete model-visible packet, including learned schemas, and preserve source roles/uncertainty. Source-level supersession is not a partial field update. Do not treat literal spans as semantic validation.
- NIE personality, canonical cards, prompts, filters, integration and deployment are a separate ownership boundary. Preserve the shared plan; append coordination notes without implying an ACK. Do not deploy a research candidate by merging its PR.
- Finish substantial work with a sourced memory event and current handover/status, including failures, incomplete tasks, exact tested head, actual calls/cost and next admissible action. Preserve earlier dated receipts. No automatic commit/push of potentially broken audit work; follow the owner's latest authorization and explicit scope.
