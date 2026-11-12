# Integration of unpublished local work, 2026-11-12

Status: record of one integration pass on the branch `claude/integrate-unmerged-research-2026-11-12`, cut from `main`
at `1b673d3`. Local commits only; nothing was pushed or merged. No model was called and no paid API was used.

## Why

An audit of every local working tree and branch on 2026-11-12 found work that was neither on `main` nor in the open
draft pull request #105:

1. five research documents of 2026-08-24 and the inbox folder of the external research agent, present in one working
   tree only, although `main` cited them;
2. a spend ledger whose committed copy was shorter than the file the proxies had actually written;
3. a note of 2026-11-01 that ordered the research as access, valuation, use, kept outside the repository;
4. a label screen of MemoryAgentBench FactConsolidation made on 2026-11-12, kept outside the repository;
5. the experience-memory pilot EXP-PILOT-0, on its own unpushed branch.

Items 1 to 4 are integrated here. Item 5 belongs to its author's branch and is not touched.

## What was integrated

| Material | Where it is now | How it was brought in |
|---|---|---|
| Roadmap, dependency synthesis, cross-paper map, frontier map, red-team search (2026-08-24) | [`../research/`](../research/README.md) | Unedited text under a publication note that carries the SHA-256 of the original file |
| Inbox of the external research agent (14 files with templates) | `docs/research/Dokumenty z Resherchera/` | Byte for byte; the folder's own rule forbids later edits |
| "Red-team update" section of the positioning document | end of [`../research/RELATED_WORK_AND_POSITIONING_2026-08-24.md`](../research/RELATED_WORK_AND_POSITIONING_2026-08-24.md) | The uncommitted 13-line addition, applied to the current file; the banner added on 2026-11-01 is untouched |
| Full DeepSeek spend ledger | [`../../data/lab/aam-deepseek-2026-11/`](../../data/lab/aam-deepseek-2026-11/README.md) | Append-only replacement, with a README that records the checks and the open points |
| Ordering note of 2026-11-01 | [`task-memory-ordering-note-2026-11-01.md`](task-memory-ordering-note-2026-11-01.md) | English translation with the original's SHA-256 and a section on what happened afterwards |
| FactConsolidation label screen | [`../../data/lab/mab-fc-label-screen-v1/`](../../data/lab/mab-fc-label-screen-v1/README.md), two scripts, one test file | Aggregates and an index list without benchmark text; scripts take the benchmark path as an argument |
| Review of the hypotheses that were not followed | [`../11-research-laboratory/overlooked-hypotheses-review-2026-11-12.md`](../11-research-laboratory/overlooked-hypotheses-review-2026-11-12.md) | New document |

SHA-256 of the originals of the five planning documents, as they stood in the working tree:

| File | SHA-256 of the unedited original |
|---|---|
| `RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md` | `b9496570d02efe5d6b0a45f9a47f33c4e2aef4b56fd6886cf649ba684ae16233` |
| `MECHANISM_DEPENDENCY_SYNTHESIS_2026-08-24.md` | `c283bd77f68d4aea7d6f4419bb0c017602f95901d2ba7615c32a1d778acc3e46` |
| `CROSS_PAPER_HYPOTHESIS_MAP_2026-08-24.md` | `033bc4345824fe9ee7f169f1a7a21a1687ebd80a8e8cecd2de2b8a6823087592` |
| `GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md` | `d362ad309504d6b51b0cfa054ece8f6a5092465d15207358215b746cbb3fe4bd` |
| `RELATED_WORK_RED_TEAM_2026-08-24.md` | `3cf47b1c444354edeb4506edf796762ddd7f37e8e7e032e9f6251a21f772dea8` |

## What was checked and what was found

**References.** On a clean export of `main` the claim audit reported 16 project-memory citations of paths that do not
exist and 3 broken document links. On this branch it reports 8 and 1. The remaining 8 citations point at git-ignored
external checkouts and one git-ignored dataset; the remaining broken link is an old one in
`EXTERNAL_DISCOVERY_CANDIDATE_POOL_V3.md` and was left alone. The first commit message of this branch says the count
fell "from 23 to 8". That figure came from a validation log of 2026-11-04 and is wrong for the current `main`; the
measured figures are 16 and 8.

**Duplicates.** Three things looked unintegrated and are not:

- the local branch `pr-45` holds one commit that is not an ancestor of `main`, but pull request 45 was squash-merged on
  2026-08-23 and its document is on `main`;
- the untracked `judgments-qwen14b.jsonl` in the working tree of `revival/e1-writer-sim` has the same SHA-256 as the file
  already on `main` in `data/lab/aam-e1ds-writer-memory-sim/`;
- four unreachable commits in the object store are a dropped stash and earlier versions of commits that were later
  merged.

**Spend ledger.** The committed ledger was a byte-for-byte prefix of the full file. The full file adds 13,875 rows and
4.71 USD at list price, for 29,627 rows and 7.40 USD, under the 12 USD cap of that phase. Three points could not be
reconciled from the repository and are listed in the ledger's README: two run ids that no configuration names, one
stated per-run cap that the cumulative figure exceeds, and 2,978 rows that are exact copies of another row.

**Changes of external facts since August.** Seven papers cited by the frontier map were opened again. Two of its
figures no longer match the current versions of the papers and one framing was one-sided; the table is in the hypotheses
review.

**Privacy.** The added files were searched for machine paths, account and platform names, addresses and credentials;
none were found. The ledger holds eight numeric or categorical fields per call and no message text. Benchmark questions
and answers are not added in bulk; the label screen's README quotes two short examples.

## Compatibility with other open work

Simulated three-way merges, made without changing any branch:

| Pair | Result |
|---|---|
| this branch and draft pull request #105 (`16c6d60`) | clean, no path changed by both |
| this branch and `claude/experience-pilot-v0` (`52487db`) | clean, no path changed by both |
| `claude/experience-pilot-v0` and draft pull request #105 | conflicts in `data/lab/experiment-registry.csv` and `memory/events.jsonl` |

The third row is outside this branch but matters for the order of merging. Both branches append rows to the end of the
same two append-only files. Whichever lands second has to re-append its rows after the other's. To stay out of that
conflict this branch adds no registry row and no project-memory event; if the label screen should be registered as an
experiment, that row is best added after the other two branches have landed.

## Validation

- `python tasks.py check` on the branch before the last documentation commit: 2,986 tests passed, 21 skipped; memory
  integrity 352 events, 0 violations; claim audit passed.
- All 79 relative links in the 20 added or changed Markdown files resolve.
- The two label-screen scripts were run against the benchmark file and reproduced the six original output files with
  identical SHA-256.
- Every figure in the ledger's README was recomputed from the ledger file.

## Left out on purpose

- **EXP-PILOT-0**: code, plan, results and its registry row stay on the author's branch. Only committed files of that
  branch were read.
- **Per-item label-screen files and the unposted report draft**: they quote benchmark text or belong to a decision that
  was not taken.
- **The Polish original of the ordering note**, the local coordination boards and the earlier revival drafts: local
  working documents, some with names the public repository does not use.
- **Private raw evidence** of earlier experiments.
- **A registry row and project-memory events for this pass**: see the compatibility section.

## Remaining risks

- The publication notes say what happened to each August document, but the documents themselves still contain numbers
  that were later invalidated. A reader who skips the note can be misled. The research index repeats the warning.
- The readings of external papers in the August documents were not re-verified, apart from the seven listed in the
  hypotheses review.
- The label screen rests on one AI reader.
- The local `main` of the original checkout is 198 commits behind and has the same August files untracked. After this
  branch is merged, updating that checkout will stop on those files until they are moved aside.
- The branch `pr-45` and one stale remote-tracking ref are redundant and were left in place.
