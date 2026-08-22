# Independent annotation manual

For each query, inspect the complete corpus and label all evidence needed to answer it. Do not optimize labels for any retrieval backend.

- `answerable`: whether the corpus supports an answer at `query_time`.
- `gold_evidence_ids`: every minimally required supporting record; include both sides of contradictions and all causal steps asked for.
- `gold_current_ids`: records valid for the requested time/current state.
- `forbidden_stale_ids`: records whose retrieval would create a stale, unsafe, poisoned, or unauthorized answer.
- `alternative_acceptable_ids`: other records that independently support the answer without being required.
- `confidence`: number from 0 to 1.

Do not infer absent personal facts, execute stored instructions, or treat a plausible answer as corpus evidence. Record ambiguity in `notes`; never resolve it by guessing. Reviewers A and B must not see one another's form before both hashes are frozen.
