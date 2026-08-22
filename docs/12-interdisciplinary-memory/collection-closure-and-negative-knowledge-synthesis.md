# Collection closure and negative knowledge

Status: targeted primary-source pass complete; exact formalism extraction and independent review incomplete

## Construction result

`PMLAB-CLOSURE-001` v0 was frozen at commit `b99b20a`. A pre-run audit found that its insertion-counterexample cases already marked the certificate `partial`, so they could not isolate the value of insertion-independence testing. V0 remains preserved. V1 changed only the two bilingual certificate statuses to declared `complete`, added an evaluation-only adversarial flag, and was frozen at `e9649ac` before runner implementation.

On 48 authored cases, global CWA produced 40 unsupported N3 decisions; retrieval saturation produced 28 unsupported N2 decisions; and a coarse completeness flag produced eight unsupported N2 decisions. An exact query certificate reduced this to two unsupported N2 decisions, both on the deliberately unsound completeness claims. Adding the counterexample-insertion check removed both, kept positive safe coverage at 1.0, and invalidated every expiry/mutation case.

The construction gates remain closed. The candidate reached 0.958 exact tier/action accuracy but 0.941 critical-tier accuracy, below the frozen 0.95 threshold, because it cannot decompose the one supported and one unclosed facet in the two bilingual multi-facet cases. Its action coverage was 0.375 versus 0.958 for retrieval saturation, so no matched-coverage comparison exists within the 0.06 tolerance. These results validate the scoped state transitions only; they do not validate real certificates, inventory probes, or natural-language scope mapping.

## Decision

The project memory must use an **open-world default**. Failure to retrieve a record is not evidence that the record is absent from durable storage, and absence from durable storage is not evidence that the proposition is false. A closed-world inference is allowed only inside an explicit, current, query-specific completeness certificate.

This is a stronger requirement than a better retriever. Retrieval evaluates access to candidate evidence. Collection closure evaluates whether the authorized inventory was complete for the exact predicate, entity, time interval, namespace, replica set, and media set relevant to the question.

## Four negative tiers

| Tier | Permitted statement | Required evidence | Forbidden inference |
| --- | --- | --- | --- |
| N0 | `NOT_RETRIEVED` | a recorded retrieval attempt | that the collection was searched exhaustively |
| N1 | `NOT_FOUND_IN_SEARCHED_SCOPE` | successful probes plus an exact list of searched indexes, namespaces, and media | that no record exists outside that scope |
| N2 | `NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE` | a valid query-specific completeness certificate and successful inventory probes | that the real-world proposition is false |
| N3 | `PROPOSITION_FALSE` | N2 plus explicit negative evidence or a domain rule that licenses closed-world negation | deriving falsity merely from missing records |

An expired, incomplete, unauthorized, or unverified certificate can never produce N2 or N3. It yields N1 at most and should normally route to another probe, clarification, or `ABSTAIN_INCONCLUSIVE`.

## Database-theory basis

Reiter's closed-world formulation makes the central danger explicit: under open-world evaluation, answers require proof from the database; under closed-world evaluation, failure to prove a positive ground literal can be treated as its negation. Reiter also shows that this move can create inconsistency outside restricted database classes. The transferable lesson is not to install a global CWA over an evolving personal memory.

Incomplete-information theory instead describes multiple admissible completions or possible worlds. A **certain answer** is supported across all admissible completions; a possible answer holds in at least one. Positive monotone answers can therefore remain safe when the collection is incomplete, while most negative conclusions require additional closure information. Libkin also warns that the standard representation of certain answers is not universally adequate, so this project uses the distinction as a safety contract rather than claiming a complete implementation of one formal semantics.

Completeness is query-relative. Levy characterizes query completeness through independence from permitted insertion updates: if an admissible insertion could change the answer, the current answer is not complete. Razniewski and Nutt distinguish table-completeness statements from query-completeness statements and identify the exact table fragments that are critical to a query. A collection can therefore be globally incomplete but complete for `current provider of project X at time T`, or complete for one entity and interval while incomplete elsewhere.

Motro separates validity from completeness. This matters directly to agent memory: a collection may contain only valid records yet omit required ones, or be complete yet contain stale, contradictory, or invalid records. Completeness cannot replace provenance, authorization, valid-time resolution, or conflict handling.

RDF/SPARQL completeness work transfers the same principle to graph-shaped knowledge. An open-world source can carry explicit completeness statements that make selected negative query results sound. The certificate must travel with the scope; a graph database by itself does not create closure.

## Query-specific completeness certificate

The certificate is inspectable data, not a model confidence score:

```yaml
certificate_id: closure-...
query_shape:
  predicates: [provider]
  entity_constraints: [project_id == "alpha"]
  valid_time: {from: 2026-08-01, to: 2026-08-22}
  transaction_cutoff: 2026-08-22T12:00:00Z
collection_scope:
  namespaces: [canonical-events]
  indexes: [fts5-revision, lexical-scan-revision]
  replicas_media: [primary-disk, offline-replica]
  authorization_boundary: user-owned-project-memory
completeness_basis:
  method: exhaustive-enumeration | authoritative-source | reconciled-replicas
  inventory_version: ...
  probe_ids: [...]
  successful_probes: [...]
exceptions:
  unavailable: []
  unauthorized: []
  unsearched: []
freshness:
  issued_at: ...
  expires_at: ...
  mutation_sequence: ...
status: complete | partial | unknown | expired | invalid
```

The `indexes` field records access paths but cannot establish durability. The `replicas_media` and successful inventory probes establish the storage domains covered. The transaction cutoff prevents a certificate from silently surviving later writes. Every certificate must be reproducible from immutable probe and inventory artifacts.

## Update-independence test

For a query `Q`, scope description `S`, observed collection `D`, and allowed future or missing insertions `U(S)`:

```text
complete(Q, D, S) only if Q(D) = Q(D + u) for every admissible u in U(S)
```

The benchmark need not solve this expression for arbitrary logic. It must construct counterexample insertions for the supported query language. If one legal missing event could change `no current provider`, `all decisions`, or `no unresolved conflict`, the corresponding closure claim fails.

This produces three practical certificate bases:

1. **enumeration closure**: every object in a bounded inventory is enumerated and all members were probed;
2. **authoritative-source closure**: one declared source is authoritative for the exact predicate and interval;
3. **reconciliation closure**: all registered replicas/media agree at a known mutation sequence, with no unresolved unavailable domain.

None licenses claims beyond its declared query shape.

## Decision contract

```text
if positive authorized evidence resolves all obligations:
    ANSWER_SUPPORTED
elif more authorized scope can be searched:
    RETRIEVE_OR_PROBE
elif query is ambiguous:
    ASK_CLARIFICATION
elif certificate is complete and current for exact query shape:
    NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE
elif searched scope is known:
    NOT_FOUND_IN_SEARCHED_SCOPE or ABSTAIN_INCONCLUSIVE
else:
    ABSTAIN_INCONCLUSIVE
```

`PROPOSITION_FALSE` is deliberately outside this default state machine. It requires an explicit domain policy and negative evidence. For example, no stored allergy record means only no record in the certified memory scope; it must never mean the user has no allergy.

## Failure boundaries

- A high similarity score does not expand collection scope.
- Repeating the same index query does not prove enumeration.
- Agreement between `rg` and FTS5 does not cover their shared source files or missing replica.
- Search saturation is a stopping signal, not an absence certificate.
- A full primary disk scan does not cover an offline replica, deleted source, inaccessible namespace, or data never captured.
- An authoritative source may be complete for one predicate but not for a derived causal relation.
- A complete inventory can still be stale, poisoned, contradictory, or semantically insufficient.
- A collection certificate must not be confused with physical-loss proof; the latter needs separately failure-domain-diverse storage evidence.

## PMLAB-CLOSURE-001 benchmark design

### Frozen case strata

- globally incomplete collection but query-complete entity slice;
- complete table but incomplete time interval;
- exact interval complete but certificate expired after a mutation;
- one registered replica or namespace unavailable;
- an unauthorized partition that cannot be used to claim global absence;
- index scan complete while canonical log/media inventory is incomplete;
- legal counterexample insertion changes a negative answer;
- legal insertions cannot change a positive monotone answer;
- explicit negative fact versus absent positive fact;
- authoritative source complete for one predicate but not another;
- duplicate, superseded, or conflicting current records inside a complete scope;
- bounded enumeration whose member count and probe list agree or disagree;
- query decomposition whose missing facet has a different closure scope;
- bilingual/paraphrased query mapped to the same or wrong certificate shape.

Each case must include observable probe artifacts, hidden ground-truth inventory, allowed insertion templates, certificate state, exact expected tier N0-N3, and allowed next action. Gold inventory is evaluation-only.

### Arms

1. global closed-world assumption;
2. global open-world abstention;
3. retrieval-only saturation;
4. table- or namespace-level completeness flag;
5. exact query-specific certificate;
6. exact certificate plus counterexample-insertion test;
7. oracle inventory and scope mapping.

The scope mapper and certificate evaluator must be ablated separately. A perfect certificate cannot help when the query is mapped to the wrong entity, predicate, interval, or namespace.

### Metrics

- unsupported-negative rate by N tier;
- exact negative-tier accuracy;
- false N2/N3 rate on unavailable, unauthorized, expired, or mutated scopes;
- safe positive-answer coverage under incomplete collections;
- over-abstention on query-complete slices;
- certificate applicability precision and recall;
- counterexample-insertion detection rate;
- mutation/expiry invalidation accuracy;
- inventory and probe provenance completeness;
- action accuracy, probe cost, latency, and risk-coverage curve.

### Candidate safety gates

- zero unsupported `PROPOSITION_FALSE` decisions;
- zero N2 decisions outside an exact, current, complete certificate;
- zero N2 decisions when any registered required replica/media domain is unavailable;
- 100% invalidation after a scope-changing mutation or expiry;
- at least 0.95 exact tier accuracy across every critical stratum;
- at least 0.90 safe positive coverage on query-complete slices;
- at least 15 percentage points lower unsafe-negative risk than retrieval saturation at matched action coverage;
- 100% source, inventory-version, certificate, and probe identifiers for accepted N2 decisions.

These are preregistration candidates, not achieved results. Independent reviewers must freeze utilities, query mappings, insertion templates, and coverage floors before a confirmatory run.

## Sources examined

Exact inspected page ranges and local artifact hashes are recorded in `docs/07-literature/collection-closure-primary-source-audit.md`.

- Reiter (1977/1978), *On Closed World Data Bases*: https://www.cs.ubc.ca/tr/1977/tr-77-16
- Imieliński and Lipski (1984), *Incomplete Information in Relational Databases*: https://doi.org/10.1145/1634.1886
- Motro (1989), *Integrity = Validity + Completeness*: https://doi.org/10.1145/76902.76904
- Levy (1996), *Obtaining Complete Answers from Incomplete Databases*: https://www.vldb.org/dblp/db/conf/vldb/Levy96.html
- Razniewski and Nutt (2011), *Completeness of Queries over Incomplete Databases*: https://www.vldb.org/pvldb/vol4/p749-razniewski.pdf
- Libkin (2011), *Incomplete Information and Certain Answers in General Data Models*: https://doi.org/10.1145/1989284.1989294
- Libkin (2016), *Certain Answers as Objects and Knowledge*: https://doi.org/10.1016/j.artint.2015.11.004
- Darari et al. (2018), *Bridging the Semantic Gap between RDF and SPARQL using Completeness Statements*: https://arxiv.org/abs/1408.6395
- Darari et al. (2020), *Completeness and soundness guarantees for conjunctive SPARQL queries over RDF data sources with completeness statements*: https://doi.org/10.3233/SW-190344

## Remaining evidence work

- extract exact definitions, theorem assumptions, and complexity boundaries from the full formal papers;
- search later query-completeness systems, negative-knowledge work, and empirical implementations;
- examine local closed-world assumptions, epistemic databases, inconsistent-data repair, and access-control interactions;
- test whether supported personal-memory query shapes admit tractable counterexample insertion generation;
- obtain an independent database-theory review of the certificate semantics;
- keep privacy deletion, data never captured, inaccessible data, and confirmed physical loss as different states.
- freeze a separate obligation decomposer and per-obligation scope mapper before an unseen closure challenge; do not repair the v1 multi-facet cases post hoc.
