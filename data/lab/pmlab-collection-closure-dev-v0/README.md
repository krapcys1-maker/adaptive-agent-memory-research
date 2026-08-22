# PMLAB collection-closure construction corpus v0

Status: authored construction freeze; not held out; no architecture claim permitted

This 48-case English/Polish corpus isolates retrieval attempts, query-to-scope mapping, certificate applicability and freshness, mutation sequence, registered replica/media availability, authorization boundaries, enumeration counts, counterexample insertions, explicit negatives, conflicts, and valid positive answers in incomplete collections.

The first Git commit containing the builder, tests, `manifest.json`, and all five JSONL files is the freeze boundary. The future runner must verify every artifact hash before scoring. It must strip `gold` from any model-visible payload and split future development/challenge data by `pair_group`, never by individual translated row.

The corpus is synthetic and authored after the database-theory synthesis. Passing it can validate only the four-tier state machine and artifact contract. It cannot establish real inventory reliability, natural-language scope mapping, access-control correctness, storage durability, or generalization.

Artifacts:

- `cases.jsonl`: queries, observable links, and evaluation-only gold;
- `inventories.jsonl`: registered/available domains, mutation sequence, counts, and records;
- `probes.jsonl`: domain-specific observable probe outcomes;
- `certificates.jsonl`: scoped completeness claims, basis, exceptions, freshness, and version;
- `insertions.jsonl`: admissible update counterexamples;
- `manifest.json`: counts, strata, limitations, and canonical hashes.
