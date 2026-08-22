# Include-candidate source review

Status: identity verified and abstract screened; full-text review pending

## Procedure

All 37 normalized `include` candidates were checked through deterministic DOI content negotiation and the OpenAlex work endpoint. Titles were matched against registered metadata, retraction flags and source types were recorded, and every available frozen abstract was read. Selected version relationships were then checked against publisher, institutional-repository, eLife, and arXiv records.

This is a source-screening pass, not a full-paper evidence extraction. No scientific claim was promoted to reviewed status.

## Identity result

- 33/37 DOI records matched their registered titles.
- 4/37 sources without DOI matched their OpenAlex title and primary landing page.
- 0 title mismatches and 0 unresolved identities.
- 0 records were marked retracted in the retrieved OpenAlex metadata.

## Screening result

| Action | Count | Meaning |
|---|---:|---|
| priority full read | 19 | directly tests or formalizes a mechanism important to the project |
| background | 9 | useful review, map, or indirect bridge |
| defer | 6 | valid source but presently too specialized or indirect |
| challenge only | 1 | preserve as a contested/adversarial lead, not supporting evidence |
| remove/merge | 2 | duplicate version or peer-review artifact |

After merging the duplicate and review artifact, the queue represents 35 distinct intellectual works.

## Corrections to the model queue

1. `semantic_compression-007` and `semantic_compression-025` are journal and arXiv versions of the same work. Keep DOI `10.1162/neco_a_01520`.
2. `semantic_compression-021` is an eLife decision letter, not a separate research article. Merge it into `10.7554/eLife.79450`.
3. `semantic_compression-022` should use the published eLife DOI `10.7554/eLife.79450`, not the bioRxiv DOI.
4. `prospective_metamemory-018` should use published DOI `10.1080/09658211.2021.1991380` instead of the OSF preprint.
5. `prospective_metamemory-020` should use published DOI `10.1037/pag0000751` instead of the OSF preprint.
6. `cls_replay-023` was over-ranked: its primary method is domain-specific continual learning and it only compares conditions with and without replay.
7. `durable_storage-011` is identifiable as arXiv:2603.01384, but its unusually broad unreviewed claims make it suitable for a challenge queue only.

## Priority full-reading batches

1. **Direct agent memory and compression:** arXiv:2605.10870, arXiv:2607.08032, eLife 79450, adaptive episodic/semantic compression, and the semantic-completion model.
2. **Allocation and operational salience:** reward-associated enhancement, emotional-system bias, engram precision, and synaptic tagging/capture.
3. **Replay and consolidation:** time-compressed hippocampal replay, task-dependent replay, sharp-wave ripples, experience-replay taxonomy, and relational replay selection.
4. **Prospective memory and control:** working-memory/offloading benefits, age-sensitive reminder calibration, and consequence-sensitive partial versus full offloading.
5. **Durability:** FSCQ first; only then narrower NVMM mechanisms if a benchmark exposes a relevant failure.

## Decision

Do not spend additional model budget on these 37 records. The next useful cost is full-text reading and structured claim extraction for the 19 priority sources, beginning with the five direct compression/agent-memory works. Use a second reviewer or model family only after extraction, to challenge locators, boundary conditions, and unsupported generalization.

## Verification references

- DOI metadata method: https://citation.doi.org/docs.html
- Published rate-distortion article: https://elifesciences.org/articles/79450
- Published intention-offloading record: https://discovery.ucl.ac.uk/id/eprint/10138172/
- Published older-adult offloading record: https://archive-ouverte.unige.ch/unige:185139
- Direct agent-memory preprint: https://arxiv.org/abs/2605.10870
- Cross-layer memory-compaction preprint: https://arxiv.org/abs/2607.08032
- FITO persistence preprint: https://arxiv.org/abs/2603.01384
