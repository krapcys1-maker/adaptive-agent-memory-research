# Plan: integrating PR #105 in independent pieces

Status: proposal, written 13 November 2026 after a review of the branch `codex/structured-memory-runtime-2026-11-04` (head `16c6d60`, 88 commits). Nothing in PR #105 has been merged. This plan changes no result, no frozen file and no strategy; it only proposes how to bring the work onto `main` so that each step can be reviewed.

## What PR #105 is

A draft that adds a source-grounded structured-memory candidate with its evidence: 277 files, 51,921 added lines, one changed line (a README sentence), no deletions. It is additive: earlier versions (`v1` to `v5`) stay next to their successors, and failed and negative runs are kept. Its own description says it makes no claim of general memory readiness: semantic capture, evidence sufficiency and fresh external confirmation are open. The branch passes all 12 CI jobs.

By content it contains four separable research lines plus shared documents:

| Piece | Files | Added lines | Content |
|---|---:|---:|---|
| S1 structured-memory core and boundary audit | 58 | 7,679 | `tools/structured_*`, pipeline and path scripts v1 to v5, boundary audit and validation, `data/lab/structured-memory-v1`, `structured-boundaries-v1`, `AUDIT_REPORT.md`, tests |
| S2 H1 evidence line and integrity replay | 103 | 25,614 | H1 model-chain, metadata, routing, rerank, density, chronological-pack and obsolete-control experiments (v1 to v5), the evidence and retrieval-metadata libraries, `repository-integrity-audit-v1` |
| S3 BEAM line | 66 | 13,545 | BEAM transfer formats, source windows, source context, reader-evidence and evidence-boundary experiments |
| S4 local-model upgrade audit | 33 | 4,375 | two matrices of local readers, review script, tests |
| S5 documents and state | 17 | 708 | `HANDOVER.md`, `memory/CURRENT_STATE.md`, entry-point edits, registry rows, 26 memory events, `docs/` notes |

The assignment is by path pattern and every one of the 277 files falls into exactly one piece; it must be confirmed when the pieces are cut.

## Review findings

1. **Dependencies.** The modules under `tools/` import nothing from each other. The scripts form chains: structured pipeline v1 to v3, then H1 model chains v1 to v5 and their obsolete-control, density and chronological-pack successors; separately BEAM transfer, windows, reader evidence and boundary. S2 depends on S1; S3 and S4 do not depend on S1 or S2.
2. **Known limitations, all documented by the authors.** The structured candidate promotes conditional and compound spans to positive claims ([#106](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/106)), exposes future and cross-scope information in routing packets ([#107](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/107)), and one H1 reader still emits an obsolete value despite a shown correction ([#108](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/108)). The BEAM literal-provenance guard cannot see a distant hypothetical frame ([#110](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/110)). The headline numbers are on spent development questions, not a held-out or official score.
3. **Machine paths and private locations.** Four files in the branch contain absolute paths of the author's machine, including the location of private backups: `HANDOVER.md` (7 lines), `AUDIT_REPORT.md` (1), `data/lab/local-model-upgrade-v2/README.md` (1) and `data/lab/local-model-upgrade-v2/stage-history.md` (1). The contribution rules forbid this ([CONTRIBUTING.md](../../CONTRIBUTING.md)). They must be replaced by repository-relative or generic descriptions before the affected piece is merged. If a scrubbed file is digest-pinned by a result manifest, the scrub goes in as a recorded amendment, not a silent edit.
4. **No secrets found.** A scan of the added lines for keys and tokens found none; private inputs, answers and model weights are reported as kept outside Git.
5. **Trial merge with the current `main`** (done in a scratch worktree, nothing pushed): conflicts only in `memory/events.jsonl` and `data/lab/experiment-registry.csv`, because PR #111 landed first. The registry resolves by appending both sets of rows (90 rows). The memory log does **not** resolve cleanly: the first of the branch's 26 events is dated 4 November, earlier than the last event now on `main` (12 November), and the integrity check reports one `non-monotonic-time` violation. The log is append-only and must not be rewritten.
6. **Size.** The added files total about 1.9 MiB, about half of it JSON score and result files. Repository growth is not the concern; a single 277-file, 52,000-line review is.

## Proposed order

Each piece is its own pull request from a branch cut from the then-current `main`, takes its files from the branch head `16c6d60` (so the content and the recorded hashes are byte-identical), cites that commit, and must pass CI on its own. Documents travel with the piece they describe; shared state goes last.

1. **S1: structured-memory core and boundary audit.** Label it experimental in its README and link #106 and #107 from the pull request. Includes the negative and failed runs and `AUDIT_REPORT.md` (after the path scrub).
2. **S3: BEAM line** and **S4: local-model upgrade audit**, in either order, independently of S1. S3 links #110; S4 must state that no default model, judge or persona was migrated and that the Gemma matrix is incomplete (as its own README does). S4 needs the path scrub.
3. **S2: H1 evidence line and integrity replay**, after S1. Links #108. Largest piece by lines, mostly data; may be cut into the H1 chain and the replay.
4. **S5: documents and state**, last: `HANDOVER.md` and `memory/CURRENT_STATE.md` rewritten against what has actually merged, entry-point edits, registry rows and memory events (see the open decision below).

Nothing in these pieces is a stable product component. The pieces that are infrastructure in character (deterministic, unit-tested, making no claim about memory quality) are the window preparation, metadata and evidence libraries; the structured pipeline and path scripts are research candidates with open defects, and the experiments are evidence records. All stay labelled experimental on arrival.

## Preservation rules

- Frozen predecessors, failed runs and negative results move unchanged; no result is rescored or re-ranked.
- Keep the branch `codex/structured-memory-runtime-2026-11-04` and PR #105 until the last piece has merged, and keep the head SHA in every piece's description. If the branch is later deleted, tag the head first.
- Do not merge pieces out of order, and do not squash away the provenance statement in the description.

## Decision for the maintainer: the 26 memory events

Because PR #111 merged first, the 26 events from the branch (created 4 to 5 November) cannot be appended unchanged after `main`'s last event without breaking the monotonic-time invariant. Options, in order of preference:

1. Append them as new events at integration time, each recording its original creation time and original identifier in its body, so history is neither rewritten nor falsified.
2. Relax the invariant for events carried over from a merged branch. This changes what the integrity check guarantees and is not recommended without a recorded decision.
3. Leave the events on the branch and cite them from S5.

Until this is decided, S5 should not be merged.
