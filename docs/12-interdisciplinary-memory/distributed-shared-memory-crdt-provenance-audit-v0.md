# Distributed shared memory, CRDT, provenance, and authorization audit v0

Status: targeted primary-source pass; architecture selection not authorized

Last reviewed: 2026-08-23

## Question

Can a local-first long-term memory be shared across models, agents, processes, or devices without turning repeated copies into truth, losing provenance, or allowing an offline writer to exceed its authority?

The short answer is: replication can be made convergent, but convergence is only one of several independent properties. The project must separately specify and test:

1. delivery and state convergence;
2. application invariants and semantic conflict;
3. evidence identity and derivation provenance;
4. write, read, share, correct, and delete authority;
5. confidentiality after replication;
6. correction and poison recovery;
7. user-visible disagreement and abstention.

No source reviewed here supports collapsing these properties into one `shared memory confidence` score.

## Primary evidence and exact contribution

| Source | Exact contribution used here | Boundary |
| --- | --- | --- |
| [Shapiro et al. 2011, Conflict-free Replicated Data Types](https://perso.lip6.fr/Marc.Shapiro/papers/2011/CRDTs_SSS-2011.pdf) | Abstract and Sections 2-3 formalize state- and operation-based sufficient conditions for strong eventual convergence | replicas converge after receiving the same updates; this does not establish application truth, authorization, or confidentiality |
| [Kleppmann et al. 2019, Local-first software](https://doi.org/10.1145/3359591.3359737) | Sections 3-4 distinguish local-first ideals such as offline work, multi-device support, ownership, longevity, and collaboration | design principles and prototypes, not a proof that every local-first merge preserves domain invariants |
| [Bailis et al. 2014/2015, Coordination Avoidance](https://www.vldb.org/pvldb/vol8/p185-bailis.pdf) | Abstract and Sections 1-3 define invariant confluence as the condition under which valid independently reached states can merge to a valid state without coordination | the application must state its invariants and operations; convergence alone is insufficient |
| [LoRe, Haas et al. 2023/2024](https://arxiv.org/abs/2304.07133) | identifies concurrent interactions that may violate safety invariants and selectively introduces coordination | a programming-model result, not an evaluated LLM-memory architecture |
| [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) | Sections 1, 5, and 7 distinguish entities, activities, agents, derivations, bundles, and validation constraints | provenance helps assess trust; it is not itself proof of correctness or authorization |
| [Secure RDTs, Renaux et al. 2023](https://doi.org/10.1145/3622802) | integrates role-based access-control policies with offline-available replicated JSON data | one policy model and artifact; it does not erase data already observed by a formerly authorized replica |
| [UCAN specification v1.0](https://github.com/ucan-wg/spec) and [revocation specification](https://ucan.xyz/revocation/) | defines signed, attenuable capability chains and an explicit revocation lifecycle for local-first/distributed resources | revocation limits future use; it cannot undo irreversible actions or previously disclosed plaintext |
| [Yanakieva et al. 2026, Datalog framework](https://doi.org/10.1017/S1471068426100556) | proposes executable semantic specifications and property-based comparison for composed CRDTs | recent article/watchlist; useful as a test-design candidate, not established LLM-memory evidence |

## What CRDT convergence does and does not mean

A CRDT supplies deterministic conflict semantics for a declared data type. Under the required delivery and causal assumptions, replicas that have incorporated the same updates converge. This is useful for offline edits, replicated counters, sets, maps, and collaborative text.

The guarantee is deliberately narrower than the needs of scientific or agent memory:

- two agents can converge on the same false claim;
- an add-wins or last-writer-wins rule can preserve the wrong domain meaning;
- a syntactically valid merge can violate a cross-record invariant;
- an unauthorized operation can be delivered consistently to every replica;
- a revoked reader can retain plaintext already copied locally;
- replicas can agree while all cite the same poisoned source;
- a compacted view can converge while losing the derivation path needed for audit.

Therefore `replica convergence`, `supported belief convergence`, and `correct action convergence` are separate endpoints.

## Semantic conflicts require declared invariants

The invariant-confluence result gives a practical decision boundary. For a fixed set of operations, merge function, and application invariants, coordination-free execution is safe only when independently valid states always merge to another valid state. When this condition does not hold, the system needs coordination, escrow, a single authority, or an explicit unresolved state.

Candidate memory invariants include:

- a claim marked `accepted` has at least one immutable, resolvable supporting source;
- only an authorized reviewer may promote a candidate claim;
- supersession never destroys the prior version or its valid-time interval;
- a deletion receipt is not issued until every registered replica and rebuildable derivative has an accounted state;
- private or restricted evidence cannot enter a broader retrieval namespace;
- contradictory current procedures cannot silently collapse to one scalar or last-writer winner;
- independent review cannot share the verdict or hidden context it is intended to audit.

Some operations are naturally append-only and likely coordination-friendly. Promotion, exclusive ownership, budget reservation, erasure completion, and policy narrowing are plausible non-confluent cases and must be tested rather than assumed.

## Provenance is a graph, not a trust score

W3C PROV supplies a useful interoperable vocabulary: entities are generated or derived through activities associated with agents, and provenance bundles can themselves have provenance. A minimal project mapping is:

| Project object | PROV-like role |
| --- | --- |
| immutable source bytes or event | entity |
| extraction, normalization, review, merge, or compaction | activity |
| user, agent, worker, model, or deterministic tool | agent |
| summary, claim, index row, or context pack | derived entity |
| one signed/imported account of a derivation | bundle |

This is a candidate interchange mapping, not a requirement to adopt RDF or PROV-O. The stable requirement is that derived memory never overwrites its evidence identity and that a reviewer can traverse the derivation chain. Provenance supports a trust decision but does not make one automatically.

## Authorization and revocation boundary

Offline-first authority is difficult because a disconnected replica cannot know about every concurrent policy change. Short-lived, attenuated capabilities can limit exposure. Signed capability chains can make writer authority independently checkable. Neither solves retrospective secrecy.

The project should distinguish at least:

- authority at operation creation time;
- authority when another replica receives the operation;
- authority when a derived index exposes the content;
- current retrieval authorization;
- revocation knowledge and propagation state;
- crypto-erasure eligibility;
- verified physical and derivative deletion.

A tombstone, revocation event, or expired token must not be reported as deletion of bytes already exported, backed up, copied into a prompt, or learned by an external model. The safe claim is bounded future non-use within an inventoried system.

## Local repository audit

The following repositories were cloned only into the ignored `external/repos/` research cache. No dependency was added and no production integration was performed.

| Candidate | Pinned revision | License observation | Reusable segment | Missing project guarantees |
| --- | --- | --- | --- | --- |
| [`automerge/automerge`](https://github.com/automerge/automerge) | `47908d6c04a0ce3fea0fa1d6b7f5ce6ba3e5792e` | root MIT license | JSON-like CRDTs, compact history, transport-agnostic sync protocol; repository/storage adapters are a separate layer | truth, memory lifecycle, review authority, restricted retrieval, erasure receipts |
| [`yjs/yjs`](https://github.com/yjs/yjs) | `567af9b41fe5e1290e0cfe7fcc025a9f98c514a0` | root MIT license and README declaration | mature shared types, network-independent updates, snapshots/undo, multiple persistence providers | canonical evidence model, provenance, policy semantics, poison correction, end-to-end confidentiality |
| [`ucan-wg/spec`](https://github.com/ucan-wg/spec) | `9955aa1fb7b32897f80b57651f4ee8b22ebf35a7` | Community Specification License 1.0 for specification; MIT for included source code unless otherwise designated | capability vocabulary, signed delegation/invocation/revocation contracts, least-authority design | memory-specific policy, replica inventory, plaintext recovery, deletion proof, implementation selection |

### Adoption disposition

- **Keep Automerge and Yjs as competing optional sync/view adapters.** Do not put canonical evidence directly behind either until `PMLAB-SHARED-001` passes semantic, security, and recovery gates.
- **Keep UCAN as a capability-contract candidate, not an implementation dependency.** Compare it with a simpler local ACL/capability baseline using identical cases.
- **Do not add a blockchain.** None of the identified requirements needs consensus over a permissionless adversarial network, and immutability would conflict with privacy and erasure obligations.
- **Keep Git-tracked text/JSON plus SQLite FTS5 as the single-user baseline.** Shared replication is extra complexity and must demonstrate a measured multi-device or multi-principal benefit.

## Candidate layered design, not an implementation decision

```text
immutable evidence/events
        |
        +--> provenance + signatures + valid/transaction time
        |
        +--> policy decision: may this principal perform this operation?
        |
        +--> append operation to scoped log
                     |
                     +--> local derived indexes
                     +--> optional replicated coordination view
                                  |
                                  +--> conflict/invariant checker
                                  +--> current/supporting/stale context pack
```

The evidence log and policy decisions remain inspectable even if a replicated view is discarded and rebuilt. Semantic conflicts remain first-class records. An adapter may converge a view but cannot promote a claim or certify erasure.

## Falsifiable hypotheses

| ID | Hypothesis | Required comparison | Failure interpretation |
| --- | --- | --- | --- |
| SH-D01 | an append-only operation log plus deterministic merge reduces lost updates across offline replicas | single-writer SQLite/Git, naive file merge, CRDT adapters | no benefit or unacceptable disk/latency cost rejects shared sync for the target scale |
| SH-D02 | explicit provenance and validity gates reduce poison/stale propagation without erasing useful coordination gains | ungated shared state versus provenance-gated state at matched retrieval budget | convergence without lower harmful adoption rejects provenance gate implementation |
| SH-D03 | declared invariant checks expose conflicts that CRDT convergence hides | raw CRDT state versus invariant-aware state with oracle conflicts | missed violations or excessive false blocks reject the checker |
| SH-D04 | attenuated capability checks prevent unauthorized writes and reads during offline merge | local ACL, UCAN-like chain, oracle authorization | any critical unauthorized exposure rejects the candidate |
| SH-D05 | revocation plus replica inventory can bound future use but cannot guarantee retrospective secrecy | connected, partitioned, exported, backed-up, and prompt-exposed cases | claiming recovery of disclosed plaintext is a benchmark-definition failure |

## Current conclusion

The project does not need distributed shared memory to continue its present single-user research. It does need a precise shared-memory contract before multiple agents or devices can mutate the same long-term store. The strongest current candidate is a two-plane design: canonical append-only evidence with provenance and authorization, plus replaceable derived/replicated coordination views. CRDT, provenance, and capabilities remain separate mechanisms and must earn adoption in separate ablations.

## Open work

- independently review the proposed invariants and threat model;
- add crash, partition, delayed-revocation, malicious-writer, and stale-reader cases;
- characterize Automerge and Yjs on the same operation trace without LLM involvement;
- compare signed capabilities with a simple local namespace ACL;
- define registered-replica, backup, export, model-prompt, and derived-index inventories;
- test correction propagation independently from deletion and secrecy;
- independently reproduce the recent Datalog semantic-testing proposal before adopting any tooling from it.
