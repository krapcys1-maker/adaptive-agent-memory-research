# Evidence coverage protocol

Status: reviewed

## Why counts are insufficient

A topic with 100 near-duplicate papers may be less covered than a topic with ten sources spanning theory, primary experiments, replications, null results, methods, and opposing interpretations. Coverage is a protocol state, not a guessed percentage of all knowledge.

## Topic state machine

```text
missing → discovered → screened → primary-read → triangulated → contested/saturated
```

- `missing`: no reproducible search performed;
- `discovered`: query results captured and deduplicated;
- `screened`: inclusion/exclusion decisions recorded;
- `primary-read`: decisive primary studies read with exact evidence locators;
- `triangulated`: multiple independent methods or groups considered, including disconfirmation search;
- `contested`: credible evidence supports incompatible conclusions;
- `saturated`: searching may pause under the stopping rule; this never means complete forever.

## Required search rounds

1. **Seed round:** canonical terms, surveys, reviews, benchmarks, and known repositories.
2. **Synonym round:** alternative vocabulary, adjacent disciplines, mechanism names, species, and negative terms.
3. **Backward snowballing:** references from included sources.
4. **Forward snowballing:** later citing papers, replications, corrections, and retractions.
5. **Adversarial round:** `failure`, `null`, `does not replicate`, `boundary condition`, `artifact`, `critique`, and competing theories.
6. **Artifact round:** code, datasets, preregistrations, supplementary methods, issue trackers, and pinned revisions.

Use at least two scholarly indexes when available. OpenAlex alone is discovery infrastructure, not a systematic review.

## Every search-log row records

- topic and round;
- database or repository host;
- exact query and filters;
- date and result count;
- number screened;
- new unique relevant sources;
- sources included for full reading;
- reviewer and exclusion notes.

## Provisional stopping rule

A topic may be marked `saturated` only when:

1. three consecutive materially different rounds each add fewer than 5% new unique relevant sources relative to the number screened in that round;
2. the last two rounds add no new mechanism class, benchmark family, major contradiction, or safety failure;
3. backward and forward snowballing were completed for the decisive sources;
4. at least one independent reviewer agrees that the remaining gaps are documented;
5. the date and databases are recorded.

Small result sets remain `partial` when the field itself is sparse. A low novelty rate caused by a bad query is not saturation.

## Source-card minimum

- stable source ID and version;
- population, species, dataset, or software revision;
- intervention/comparison;
- measured outcome and result;
- exact locator;
- causal, correlational, or proposal status;
- limitations and alternative explanations;
- conflicts and replications;
- possible computational translation and its rejection test.

## Re-audit triggers

- six months have passed in fast-moving LLM research;
- a major survey, benchmark, replication, correction, or retraction appears;
- a mechanism becomes an architecture candidate;
- an experiment contradicts the current synthesis;
- new terminology reveals a missed adjacent literature.
