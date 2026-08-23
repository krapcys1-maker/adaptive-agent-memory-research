# Temporal provenance, versioning, and correction audit v0

Status: targeted primary-source pass; storage-engine selection not authorized

Last reviewed: 2026-08-23

## Question

What must long-term LLM memory record so that `current`, `historical`, `future`, `stale`, `corrected`, and `as previously believed` have reproducible meanings?

One timestamp is insufficient. At minimum, the system must distinguish the time described by a record from the time the system acquired or committed it. Multi-agent memory also needs causal order because two wall-clock timestamps do not necessarily reveal which event could have influenced the other.

## Evidence base

| Source | Contribution used here | Boundary |
| --- | --- | --- |
| [Jensen and Snodgrass, Temporal Database](https://www2.cs.arizona.edu/~rts/pubs/TRmerged.pdf) | defines valid-time, transaction-time, and bitemporal databases | reference synthesis of a mature field, not an LLM-memory evaluation |
| [Kulkarni and Michels 2012](https://doi.org/10.1145/2380776.2380786) | explains SQL:2011 application-time periods and system-versioned temporal tables | SQL feature description; implementations and defaults vary |
| [Akidau et al. 2015, Dataflow Model](https://research.google.com/pubs/archive/43864.pdf) | separates event time from processing time and treats late/out-of-order data explicitly | streaming-data model, not a memory schema prescription |
| [Lamport 1978](https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/) | defines happened-before as a causal partial order and logical clocks for distributed events | logical order is not physical event time or truth |
| [Buneman, Khanna, and Tan 2001](https://www.cis.upenn.edu/~sanjeev/papers/icdt01_data_provenance.pdf) | separates why-provenance from where-provenance for query results | syntactic database setting; natural-language derivations require additional semantics |
| [Green, Karvounarakis, and Tannen 2007](https://doi.org/10.1145/1265530.1265535) | supplies an algebraic account of how input annotations contribute to query outputs | formal relational/Datalog result, not proof that a generated claim is correct |

## The time axes must not be aliases

### Event or occurrence time

When an action or observation happened in the modeled world. It may be reported by a source, inferred, uncertain, or an interval. This is close to event time in streaming systems.

### Observation time

When a user, sensor, agent, or source observed or asserted the event. Observation can lag occurrence and different observers can disagree.

### Valid time

The interval during which a proposition, rule, permission, or procedure applies in the modeled domain. A valid interval can begin before the system learned it, end in the future, or remain unknown.

### Transaction or system time

When a version entered the canonical store and when it ceased to be the version the store exposed for a given query. This supports audit questions such as: what could the agent have known before the correction arrived?

### Processing and exposure time

When a pipeline processed a record and when a reader/model received it. These are needed for latency, leakage, and causal utility analysis. They are not substitutes for valid or transaction time.

### Causal order

For distributed writers, operation IDs and causal parents or a logical-clock equivalent identify happened-before relations. Concurrent events should stay concurrent unless a domain rule explicitly orders or coordinates them. Sorting only by local wall-clock time can invent causality.

## Three distinct historical questions

Suppose the store learns on 10 March that a procedure changed on 1 March. A bitemporal representation can answer three different questions:

1. **What procedure is valid for 5 March according to everything known now?** Use valid time 5 March and latest system time.
2. **What did the system believe on 5 March?** Use system time 5 March and the then-applicable valid-time view.
3. **What evidence arrived late and changed the reconstructed past?** Compare system-time slices while holding valid time fixed.

A Git commit, append-only event log, or Dolt revision naturally preserves transaction lineage. It does not automatically encode when a fact was valid in the world. Conversely, `valid_from`/`valid_to` fields without immutable system history cannot reconstruct what the agent previously knew.

## Correction is a new assertion, not silent erasure

A correction transaction should preserve:

- immutable identity and bytes of the earlier assertion;
- the correcting assertion and its evidence;
- author and authorization for both;
- valid interval affected by the correction;
- transaction time and causal parents;
- typed relation such as `supersedes`, `narrows`, `extends`, `contradicts`, `retracts`, or `contextualizes`;
- whether the old assertion was false, once true, ambiguous, or valid in a different scope;
- derivation invalidation for summaries, indexes, context packs, and decisions that used the old assertion.

`Last writer wins` is unsafe as a semantic correction rule. Recency can identify the newest database assertion, but cannot decide which source is true, whether a retroactive claim is authorized, or whether two versions apply to different contexts.

## Provenance questions are also distinct

Database provenance contributes a useful decomposition:

- **where**: which source location supplied a value;
- **why**: which source witnesses made an output exist;
- **how**: how operations combined contributions into the output.

For this project, an answer citation is closest to `where`, a sufficient evidence set resembles `why`, and the extraction/merge/summary trace resembles `how`. None alone proves factual truth. Temporal queries additionally require the exact corpus/version and query basis used to generate the answer.

## Failure cases that a temporal memory must preserve

- a late report corrects an earlier valid interval;
- a future-scheduled policy is inserted before it becomes effective;
- a temporary exception overlaps a general rule;
- two sources disagree on the event date;
- the event time is a month, range, season, relative phrase, or unknown;
- clock skew makes receipt order disagree with wall-clock order;
- two agents write concurrently without a causal edge;
- replay/import assigns a new ingestion time to old evidence;
- a timezone or daylight-saving conversion crosses a date boundary;
- a correction is later retracted or itself corrected;
- deletion makes content unavailable while the audit receipt must remain;
- a derived summary is stale even though its source record still exists;
- an answer is correct according to current knowledge but impossible according to the earlier corpus cutoff.

Unknown and unbounded intervals require typed states. A far-future sentinel date must not silently mean `unknown`, `open-ended`, `forever`, and `not yet reviewed` at once.

## Repository candidates and reuse boundary

### Already downloaded and inspected

- [`hjqcan/GoodMemory`](https://github.com/hjqcan/GoodMemory), pinned elsewhere at `08ebbb50097dc9cf03810391f37a2d8e22f20ca2`, separates observation, validity, expiry, and transaction fields. Its schema is a reusable contract candidate, not evidence that its default policies are correct.
- [`getzep/graphiti`](https://github.com/getzep/graphiti), local revision `993e081a6d7948a0d8851c12a5fbdbeb49fed862`, keeps raw episodes and derived graph facts with fields including `created_at`, `valid_at`, `invalid_at`, and `expired_at`. It is a graph/extraction comparator; model-derived invalidation must be measured against exact evidence and cannot define truth by itself.

### Metadata-pinned, not downloaded

- [`xtdb/xtdb`](https://github.com/xtdb/xtdb), remote revision `651a9df51af1abb853ef356172a759d35ee54a8c`, is an MPL-2.0 immutable SQL database with system and valid time. It is the strongest full bitemporal storage comparator found, but its JVM/cloud-native architecture is disproportionate to the current single-user baseline.
- [`dolthub/dolt`](https://github.com/dolthub/dolt), remote revision `0d6b06015867dd0cabd2eb51ff222691aae992dc`, is an Apache-2.0 SQL database with Git-style commits, branches, diffs, and merges. It is a versioned-table/lineage comparator, not a native substitute for valid-time semantics.

Neither heavy database should be downloaded or integrated until a deterministic SQLite/text implementation fails a preregistered temporal benchmark. Their concepts and test cases can be borrowed now without adopting their runtimes.

## Minimal candidate contract

```text
record_id                 immutable
version_id                immutable content-addressed or unique version
source_event_ids[]        immutable evidence references
actor_id                  writer/asserting principal
occurred_at               instant/range/unknown + precision + timezone/source
observed_at               instant/range/unknown
valid_from / valid_to     half-open domain interval or typed unknown
transaction_from          canonical commit time
transaction_to            system-maintained close time or open
causal_parents[]          operation IDs, not inferred from wall clock alone
scope                     entity/task/context/authorization namespace
revision_relation         supersedes/narrows/extends/contradicts/retracts/contextualizes
derived_from[]            exact transformation inputs and versions
status                    assertion/review state, not truth scalar
```

The physical representation remains open. Text/JSON plus deterministic derived SQLite views is still the minimal baseline.

## Benchmark consequences

The existing `PMLAB-REV-V1/V2/V3` family should add a model-free temporal-contract stage before any retrieval or reader evaluation. Required comparisons are:

- one-timestamp recency;
- append-only records with no temporal resolver;
- valid-time only;
- transaction-time only;
- bitemporal deterministic resolver;
- bitemporal plus causal-parent/conflict handling;
- oracle temporal basis.

Primary deterministic metrics are exact as-of reconstruction, valid-at action state, late-correction localization, false current/stale classification, causal misordering, provenance closure, and future-information leakage. Reader accuracy is downstream and cannot repair an incorrect temporal view.

## Current conclusion

Bitemporality is not an optional decoration for a memory that promises correction and historical audit. It is a semantic contract. A full bitemporal database is optional. The project should first encode the axes explicitly in portable records and prove that a deterministic resolver can answer current, historical, and as-previously-known queries. Only measured scale, query complexity, or reliability failure should justify XTDB, Dolt, or a temporal graph runtime.

## Open work

- independently review the time-axis definitions and half-open interval convention;
- define precision, timezone, ambiguous-relative-time, and typed-unknown grammars;
- freeze causal and concurrent operation semantics for multiple writers;
- add derivation invalidation and correction propagation tests;
- benchmark SQLite/text against XTDB and Dolt only after the minimal resolver is frozen;
- audit deletion and encryption semantics separately from historical visibility;
- test natural-language temporal parsing as a distinct upstream stage, never inside the storage score.
