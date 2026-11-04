# PR 90 integrity correction and Claude handoff — 2026-11-04

The three findings from [the review](pr90-review-2026-11-04.md) are addressed by the versioned successor `scripts/persona_battery_v1.py` and its separate `data/lab/aam-p-persona-v1/config.json`. The predecessor remains byte-identical at reviewed head `c7f0321e76b87af20eec70b70d4a1f4df5816840`, including all six PR 90 files. New executions must use v1; historical v0 defects remain in the deliberately preserved artifact.

## Implementation and ownership

Codex worked in its own branch `codex/fix-pr90-integrity-2026-11-04`, based on the review-evidence commit `8d5673ce5381b1b9644c762390d7bf72e792ad66`. This includes the PR/main integration and the earlier handoff, not changes made in Claude's worktree. NIE's persona, prompts, filters and deployment remain owned by its separate session.

- R1: saved execution manifests bind effective settings, input and script digests, configuration, proxy URLs and free controls. Resume checks identity and all previously saved records before touching a proxy. Re-prepare is idempotent for an unchanged v1 run and refuses adoption or reset of old answers.
- R2: analysis exports saved execution provenance separately from analysis-code provenance. A changed environment is refused. Historical folders require an explicit provenance declaration and are analysed read-only; their verification status and missing historical judge digests are disclosed.
- R3: expected stage keys and dependencies determine coverage. Partial descriptive summaries remain available, while registered readings wait for their required observations and labels. Completed P1-only and P2-only amendments work without other stages. P1 automatic fact readings do not require the separate unanswered-question labels.

The code imports frozen builders and statistics rather than duplicating their definitions or changing thresholds. V1 has a separate frozen configuration with the predecessor's parameters plus the new entry point's digest. No historical hash declaration was edited to make a check pass.

## Usage and boundaries

Read [the v1 README](../../data/lab/aam-p-persona-v1/README.md) for new-run and legacy-analysis commands. New experimental identities require new folders. Do not convert a legacy folder by deleting/replacing its baseline. No model experiment was run or paid for in this correction.

Preserved historical provenance is a declaration, not retroactive proof of a run. Current v1 manifests are local consistency checks, not a signature against deliberate modification by a privileged local actor. The workflow assumes one owner of a run folder; separate concurrent writers need separate folders.

## Validation record

Focused tests and a full required gate run are recorded below once completed. Model-free checks of existing private results publish aggregate counts and verification status only; private inputs, prompts, responses, labels and machine-specific paths remain outside Git.

## Handoff and remaining work

Use this implementation with its pinned configuration, tests and README together. The old review and synthetic defect reproducer remain historical evidence; that reproducer still targets v0 and is expected to demonstrate v0's defects. Use the v1 regression tests to verify the correction.

Do not blindly merge a local integration branch over another agent's checkout. Preserve both tails of the append-only memory log, run its integrity checker after integration and re-run required gates on the actual integration head. The original PR 90 must be integrated together with this successor and the entry-point documentation before treating the review findings as addressed for new use. This work does not implement issue 73, a new persona prompt, a new NIE filter, deployment or LifeSim changes.

The focused run before the full gate passed 139 predecessor/successor tests. After refining P1 label dependencies, all 22 v1 regression tests passed again. Read-only v1 legacy analysis then matched all eight compared sections (P1/P2/P3/P7, free controls, readings, counts and provenance) for all five stored result sets. File-set and digest checks found no changes to any of those legacy run folders. The sanitized evidence is [legacy-analysis-check.json](pr90-integrity-fix-2026-11-04/legacy-analysis-check.json).

Two fresh-process, synthetic P2 checks also passed on kernel 0.2.0 with min_evidence 1.0, with the honour switch off and on (80 fixture records each, fake model only). See [kernel-v2-synthetic-check.json](pr90-integrity-fix-2026-11-04/kernel-v2-synthetic-check.json).

Project memory appended decision `PM-20261104-1a78763e` and succession `PM-20261104-d065cab3`, superseding the earlier pending-fix decision while preserving its history. The entire previous 327-event byte prefix is unchanged. Integrity now reports 329 events, 307 active memories, 22 superseded memories and zero violations. The factual finding about the historical v0 defects remains valid.

Final required gate: `python tasks.py check` passed all three gates in 341.8 seconds. The full suite passed 2782 tests with 20 skipped and 2 warnings. Memory integrity: 329 events, zero violations. Claim audit: exit 0, zero critical findings, 45 medium and 13 low existing findings. The canonical-store diff against the PR 90 head contains six appended lines and zero removals (four prior review/audit events and two current events). New code and the pinned runner digest were unchanged throughout this full gate run.
