# T39: plan for the temporal query layer (Issue #39): plan, reviews and reproductions

**Status: PROPOSAL. NOT APPROVED. No implementation exists.** Everything in this directory was written by AI agents
(the coordinator's Opus, Fable and Sonnet sessions) inside the maintainer's local autonomous laboratory, by 2026-11-13
(the mission report is dated 2026-11-13 16:10). **No owner decision has been made**: the 18 decisions A to R in
[iteration-2-proposal/task-14-decision-table.md](iteration-2-proposal/task-14-decision-table.md) and
[iteration-2-proposal/final-report.md](iteration-2-proposal/final-report.md) are all open. Nothing here was run except the
two reproductions in [reproductions/](reproductions/), and no paid API was used. The documents are in **Polish**, as the agents
wrote them; this README is the English entry point. They were imported on 2026-11-14 without a change of substance (see
"Provenance" for the only edits). Nothing here changes a frozen experiment, a verdict or a file of the REV-V0 benchmark.

## What this is about

Issue [#39](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/39) asks for a temporal query layer
for the project memory, including the "future-effective supersession trap" (a record that is correct today but has a successor
that only takes effect later must not disappear from a query about an earlier time). The public benchmark REV-V0
([`data/lab/pmlab-revision-v0/`](../../../data/lab/pmlab-revision-v0/)) has 18 queries over 7 cases (C1 to C7) with three
query types: `current`, `valid_at` and `as_known_at`. Its arm `bitemporal` scores 0.9444 exact, `valid_only` 0.7778,
`transaction_only` 0.7222 and `one_timestamp` 0.3889; the 0.9444 loses one query, the C3 `as_known_at` query (the trap). Those four
figures were checked against the public `data/lab/pmlab-revision-v0/execution-v0/results.json` (`summary.arms.*.exact`)
on 2026-11-14.

The agents' work, in the order it happened:

1. **Iteration 1 (superseded).** A plan for a layer `as_of(valid, known)` with a pre-registered held-out protocol (tasks 8 to 10).
   An AI methodological review (task 9) returned **revise** with `falsifiability_ok = false`: the single confirmatory criterion was
   under-specified, the leak check relied on the layer's own declaration, and the plan had dropped the comparison arms that gave
   REV-V0 its power to fail.
2. **Reproductions** (tasks 7 and 11, [reproductions/](reproductions/)). The C3 diagnosis was reproduced in a container (6 of 6
   expectations; the cause is two faults in the `as_known_at` branch of the REV-V0 resolver), and a mutation check settled a
   disagreement between the plan and its reviewer about mutant M1 and case C7 by running four resolver variants. The raw standard
   output of every executed command is included. **These are the only mechanical results in the directory.**
3. **Iteration 2 (current proposal)** (tasks 12 to 14, [iteration-2-proposal/](iteration-2-proposal/)). A revised plan, a
   second AI review (**conditional accept**, `falsifiability_ok = true`, 11 of 14 earlier remarks resolved, 3 partly, 13 new remarks
   N1 to N13; the acceptance condition is that N1 to N4 enter the pre-registration before the held-out set is written and sealed,
   and N5, N7, N8 before the seal), and the table of the 18 decisions A to R with the planner's recommendation, the reviewer's
   assessment and the consequences for correctness.

"Accept" means the protocol can be put to the owner for approval. It does not mean the layer works: it does not exist.

## Glossary (only what the files themselves fix; the plan has the full definitions)

| Term | Meaning |
|---|---|
| REV-V0 | the public revision benchmark above: 18 queries, cases C1 to C7, types `current`, `valid_at`, `as_known_at` |
| C1 to C7 | the seven cases of REV-V0; C3 is the future-effective supersession trap, C7 a case with no record valid at the asked time |
| as_of(valid, known) | the proposed query: what was true at time `valid` according to the records known at time `known` |
| M1 to M15 (M16 proposed) | mutants of the resolver used to test whether the acceptance tests can fail; "killed" = a named test gives a wrong answer on at least two chains. The mutant-to-test assignments are **analytical**, not measured, except M1/C7 (task 11) |
| X1 to X10, D, H | X: acceptance fixture cases written by the plan's author; D: the 18 REV-V0 queries; H: a held-out query set to be written by an isolated author and sealed. **X and D have no confirmatory power** (the plan says so); only H can refute the hypothesis |
| TK, WK, BA, FC | the plan's criteria: TK confirmatory thresholds (run once on a frozen commit), WK validity checks of H (WK1 before implementation), BA gates, FC falsification conditions |
| NI | the non-interference test (the layer must not change what the other arms answer) |
| S | the written specification the held-out labels are measured against |
| A to R | the 18 open owner decisions; N1 to N13 the second review's new remarks; R1 to R14 the first review's remarks |

## Provenance

[PROVENANCE.json](PROVENANCE.json) lists every published file with its source (task id and run), role, status, the SHA-256 of
the original and of the published file, and the edits. The statuses used:

| Status | Files |
|---|---|
| `VERIFIED-REPRODUCTION` | task 7 (C3 reproduction, 6 of 6), task 11 (mutation check, 4 variants) and their raw `cmd-*.txt` outputs |
| `REVIEW (AI)` | task 9 (revise), task 13 (conditional accept). Both reviews carry the same model name, so they do not count as independent confirmation |
| `SUPERSEDED` | task 8 (first plan), task 10 (owner brief with a draft comment for Issue #39, **never posted**) |
| `PROPOSAL-NOT-APPROVED` | task 12 (revised plan), task 14 (decision table), the mission's final report |
| `MECHANICAL-CHECK` | the coordinator's citation check of tasks 12, 13, 14 (see "Errata and checks") |

The only edits to the originals: **(a)** six machine-local absolute paths (the `output_file` fields in the two reproduction
responses) replaced by `[machine-local path omitted]`; **(b)** one trailing section of the final report, "Uwagi o procesie"
(process notes about how a different AI session started two of the tasks), removed; **(c)** an integration note appended to each
Markdown file. The raw `cmd-*.txt` files and the JSON checks are unmodified. `reproduction.json` of tasks 7 and 11 is
byte-identical to the `response.md` of the same task and is not copied twice.

Not published, on purpose: the agents' transcripts, the prompts and context manifests (they contain whole copies of repository
files), the mission definitions, the coordinator's task database, local configuration, and the blinded material of the
coordinator's separate retrospective test. The plan's file references (`context/NN_...`) point to files that were copies of AAMR
repository files supplied to each task; the numbering differs from task to task and the mapping is **not** reproduced here.

## Checks made before publication (2026-11-14)

- An earlier read on 2026-11-14 found five of five spot-checked file-and-line references to public AAMR files
  (`run_revision_v0.py:113`, `memory_store.py` lines 49 and 240 to 243, `SCHEMA.md:21`, `upcast.py:206 to 210`) in agreement with the
  repository at commit `1f6a1fd`. They were not re-verified line by line in this pull request.
- The four REV-V0 accuracy figures (above) match the public `results.json`.
- No e-mail address, credential, token, key or absolute path of the maintainer's machine remains in the published files (a pattern
  scan; the paths replaced are listed in `PROVENANCE.json`).
- `scripts/audit_repository_claims.py` reports **one new advisory finding** (58 to 59, severity medium, exit code unchanged): the first
  plan proposes the experiment name `PMLAB-REV-V0-002` for a re-run, which is not in the experiment registry because that
  experiment does not exist. The original text was not edited to hide it, and no registry row was invented.
- The review documents cite no external paper (no arXiv, DOI or URL). Mentions of Graphiti, Mem0 and SQL:2011 come from AAMR's own
  documents, not from a fresh check of those sources.

## Errata and known defects of the originals (not corrected in the files)

- The coordinator's citation checker flagged **12 of 15** quotations in task 12, **1 of 3** in task 13 and **2 of 4** in task 14
  (see the `evidence-check-task-*.json` files). The flagged quotations of task 12 that were inspected are fragments of the author's own
  prose between footnotes that the tool mistook for quotations (a tool artefact); not all 12 were inspected. In task 13 the
  quoted `touch(exist_ok=True)` is cited at `memory_store.py:404-405` but is at lines 240 to 243. In task 14 two quoted sentences
  are not in the files they cite. The check for task 14 also reports four evidence gaps.
- The first review (task 9) saw 7 of the 22 files the plan cites and numbered them differently; its verdict applies to what it saw.
- Task 10's brief contains a draft comment for Issue #39 that was never posted; it is kept only as history.
- The mutant-to-test assignments and the claim that REV-V0 gives 18 of 18 on the proposed semantics are analysis by hand
  (flagged as such by the second review), not measurements.
- The final report's remarks N13 (an off-by-one line number and a table/JSON mismatch) are open.

## The held-out set and the blinding risk (read this before writing H)

The protocol requires that the author of the held-out set H has **not** seen the plan, the fixture X1 to X10, the mutant
assignments, the reviews or the mutation check (decision G, with remark N5: author and second labeller must be different models,
or one of them the owner; Opus and Fable are excluded as authors). **Publishing this directory makes all of it public.** That does
not break the protocol if H is written by an isolated session that has no network access and no access to this repository; it
does break it if H is written by a person or a model that can read GitHub. Decision G is still open, so the publication is a
recorded choice, made under the maintainer's delegation of the consolidation, to publish the plan and let the protocol's
isolation requirement carry the blinding. **Anyone proposing to write H must state first how they were kept from reading this
directory.** If that cannot be guaranteed, H needs a redesigned protocol; this directory cannot be un-published.

## Where this stands and what is not done

All 18 decisions A to R, the independent review of the 18 REV-V0 labels (decision L), an audit of the canonical memory log
(decision K, read-only) and the choice of the independent author and second labeller are open. The next step per the final
report is for the owner to decide them. No comment was posted on Issue #39 on the basis of these documents.
