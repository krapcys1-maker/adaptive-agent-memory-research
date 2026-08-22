# Manual admission review

Reviewer: Codex (single reviewer; not independent)

Status: passed-for-expanded-candidate-generation

## Results

- 25/25 jobs returned schema-valid JSON with exact job IDs.
- 25/25 include/maybe/exclude decisions were plausible for triage from the supplied title and abstract.
- Three records lacked abstracts; all were restricted to `maybe` rather than `include`.
- Zero missing-abstract records were marked `include`.
- The worker exposed query drift instead of forcing relevance: seven exclusions and ten uncertain `maybe` decisions were retained.
- Source identity, DOI, and content hash were attached from frozen inputs, so model-generated identity was not trusted.
- No output was promoted to a fully read source, claim, evidence-ledger entry, or accepted finding.

## Decision

Admit screening-v2 for expanded **candidate generation** at 25 records per profile under the same cumulative USD 10 cap. This does not establish scientific screening precision or recall. Those require an independently labeled gold sample and source-level review.
