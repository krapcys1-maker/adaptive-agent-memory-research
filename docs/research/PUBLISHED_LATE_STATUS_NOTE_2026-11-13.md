# Status note: documents published late (13 November 2026)

Several documents in this folder and in `Dokumenty z Resherchera/` were written in August 2026 and published on 12–13
November 2026. They are historical planning records and outputs of an external research agent, not current findings.
This note says what each group is, what happened to it, and what was and was not checked at publication. The
documents themselves are published unedited.

## The five planning documents (2026-08-24)

`RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md`, `MECHANISM_DEPENDENCY_SYNTHESIS_2026-08-24.md`,
`CROSS_PAPER_HYPOTHESIS_MAP_2026-08-24.md`, `GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md` and
`RELATED_WORK_RED_TEAM_2026-08-24.md` each open with their own publication note, which gives the SHA-256 of the
original, says that the text below it is unedited, and points to the ledger
([`MECHANISM_REGIME_EVIDENCE_LEDGER.md`](MECHANISM_REGIME_EVIDENCE_LEDGER.md)), which wins wherever they disagree.
Several project numbers they quote were measured on contaminated Mem0 stores or with a truncation bug and are
invalid; the notes name which. Their claims about external papers were produced by automated search passes and were
not re-verified at publication, apart from seven papers checked in
[`../11-research-laboratory/overlooked-hypotheses-review-2026-11-12.md`](../11-research-laboratory/overlooked-hypotheses-review-2026-11-12.md).

## The inbox `Dokumenty z Resherchera/` (9 files)

- **Provenance.** Outputs of ResearchOS night-campaign runs, written into the inbox under the folder's own
  append-only rule. The run identifiers (`rmc-…`, `cm…`) are ResearchOS-internal identifiers and are kept as written.
  The front matter field `status: PENDING_AAMR_REVIEW` is the status at the time of writing, not the current one.
- **The candidate** `rmc-2026-08-24-001` (semantic-entropy escalation gate) was tested as
  `SEMANTIC_ENTROPY_SUFFICIENCY_GATE` and failed: 3 of 6 for both arms, no regressions, and the escalation fired in 2 of
  6 units with no repair ([`SEMANTIC_ENTROPY_SUFFICIENCY_GATE_V1.md`](SEMANTIC_ENTROPY_SUFFICIENCY_GATE_V1.md); ledger
  Entry Q). The sample was six units and the test was exploratory.
- **The three notes** of 2026-08-25 respond to the standing request `arr-2026-08-25-001`: one records that the
  request was still waiting, one that no qualifying candidate was found, and one a completed re-evaluation that again
  found none with measured or verified support. The V3 budget attached to that request stayed gated and unspent.
- **The templates and the folder README** (Polish) describe the exchange format.

## The two documents of 2026-11

[`task-memory-ordering-note-2026-11-01.md`](../00-project/task-memory-ordering-note-2026-11-01.md) and the
[overlooked-hypotheses review](../11-research-laboratory/overlooked-hypotheses-review-2026-11-12.md) mention the
experience-memory pilot EXP-PILOT-0 as unmerged. It was audited and merged on 13 November 2026 (pull request 111);
read the "Amendments" section of its README, [`data/lab/experience-pilot-v0/README.md`](../../data/lab/experience-pilot-v0/README.md),
together with those mentions.

## Quotations, licence, sensitive data

- **Quotations.** A scan of the August documents and the inbox for quotation marks around 15 words or more found one
  third-party passage above that length: `RELATED_WORK_RED_TEAM_2026-08-24.md`, line 87, 21 words, attributed to the
  OpenReview submission it describes. The other long quoted passages quote this project's own text or the ResearchOS
  reports. The documents are published unedited, so the passage stays as written. A scan cannot detect copying that is
  not in quotation marks, and this note does not claim that none exists.
- **Licence.** Published under the documentation licence of this repository (CC BY 4.0, see `REUSE.toml`) at the
  maintainers' decision. The repository records no separate licence terms for ResearchOS outputs.
- **Sensitive data.** The added files were searched for machine paths, e-mail addresses, keys and tokens; none were
  found. They are prose documents; no benchmark data files or raw logs are included.
