# Collective, externalized, and socially transmitted memory audit v0

Status: targeted primary-source and contradiction pass; candidate abstractions only, no shared-memory architecture selected.

## Scope

The label `collective memory` hides mechanisms with different storage, copying, and failure modes. This audit separates:

1. an environmental trace read by later individuals;
2. private memories distributed across group members;
3. socially copied behavior persisting as membership changes;
4. group-state hysteresis without a portable record;
5. physical fusion or material transfer;
6. symbolic, inspectable shared artifacts.

Only the sixth resembles a Git file or an agent memory record. Evidence for the other five may inspire tests, but cannot establish equivalence.

## Environmental traces and private memory interact

House-hunting experiments with *Myrmecina nipponica* found that follower groups usually selected the same nest as lead groups and relocated faster. Laboratory pheromone trails were followed reliably for four hours and influenced choice for roughly 24 hours. This is a persistent shared environmental cue, but its content is low-dimensional, its lifetime depends on chemistry and conditions, and it carries no explicit author or evidence chain. [Robinson et al. 2013](https://doi.org/10.1371/journal.pone.0064668)

In *Lasius niger*, individual ants rapidly learned routes and could prioritize private route memory over pheromone information. On complex routes, pheromone and private learning interacted rather than acting as interchangeable stores. [Czaczkes et al. 2013](https://doi.org/10.1242/jeb.076570)

A later ant study isolated private and social information and found that private route memory alone could help trap a colony at a poorer food source in one paradigm. It did not produce the same trapping in a shortest-path paradigm. This challenges the default story that collective lock-in is always caused by pheromone positive feedback. [Czaczkes et al. 2016](https://pubmed.ncbi.nlm.nih.gov/26747911/)

Engineering boundary: a shared file and a private agent memory are parallel inputs. Their agreement is not independent evidence, and neither should silently overwrite the other. Every shared trace needs origin, scope, time, trust, and invalidation that pheromone systems do not supply.

## Social transmission can outlive the original holders

In wild great-tit subpopulations, two trained birds seeded alternative foraging techniques. The behavior spread through social networks to about 75% of individuals; local variants remained biased toward the seeded technique over two generations despite population turnover. The experiment supports persistence through repeated social acquisition, not an internal group database. [Aplin et al. 2015](https://doi.org/10.1038/nature13998)

Persistence is conditional. In wild meerkats, demonstrators initially created local preferences between equally rewarded landmarks, but individuals explored the alternative and the traditions collapsed. Social seeding alone did not guarantee stable conformity. [Thornton & Malapert 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2660974/)

In guppies, social learning transmitted use of a longer, less efficient route and slowed discovery of the shorter route. This provides a direct maladaptive-transmission warning: prevalence and longevity are not evidence of truth or utility. [Laland & Williams 1998](https://doi.org/10.1093/beheco/9.5.493)

Engineering boundary: repeated citation, majority adoption, and survival across agent turnover cannot validate a memory. A poison, stale convention, or convenient shortcut can become more entrenched precisely because many workers copy it.

## Turnover can preserve or improve—and the direction is empirical

A captive experiment with 18 great-tit populations compared static membership with gradual introduction of naive individuals. Turnover groups were more likely to replace an inefficient established technique with an efficient variant; newcomers disproportionately sampled the efficient alternative rather than merely innovating more. [Chimento et al. 2021](https://doi.org/10.1016/j.cub.2021.03.057)

This does not imply that replacing agents is generally beneficial. It shows that membership churn changes adoption dynamics. Under different exploration cost, conformity, trust, or feedback, turnover can preserve, erode, or improve a tradition.

Engineering boundary: a fresh model or agent is useful as an independently initialized auditor only if it can inspect alternatives and outcomes. If it receives the same summary, examples, retrieval results, or hidden state, it is another carrier of the same tradition rather than independent evidence.

## Group hysteresis is not necessarily an external record

A 2002 self-organizing model called history-dependent transitions in simulated animal-group structure `collective memory`. It is a model of path-dependent group dynamics, not an experimental demonstration of a retrievable proposition or durable artifact. [Couzin et al. 2002](https://doi.org/10.1006/jtbi.2002.3065)

Recent experiments in *Pseudomonas aeruginosa* report population-level quorum-sensing bistability: previously induced populations could remain induced at lower density than naive populations, with positive feedback and cooperativity proposed as the mechanism. This is a history-dependent response state, not symbolic recall. [Population-level bistability study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12505975/)

The existing *Physarum* fusion result likewise transfers a physiological response state by merging material. It does not transmit a portable claim with identity, authorship, permissions, and conflict semantics.

Engineering boundary: hysteresis and copied behavior are candidates for cache state or control priors. Canonical evidence must remain a separate inspectable artifact.

## Candidate abstractions that survive translation

### Shared traces as coordination hints

A shared trace may reduce repeated search and coordinate workers, but it should be treated as a hint until resolved to evidence. Required fields include:

- trace ID and immutable source event;
- writer identity and authorization;
- valid time, transaction time, and expiry/review time;
- scope and intended consumers;
- trust and sensitivity classification;
- independent corroboration receipts;
- supersession, correction, and deletion state;
- outcome observations and counterfactual uncertainty.

### Private/shared conflict as a first-class state

When private and shared memories conflict, the system should expose `conflict`, not average confidence or follow a majority. Candidate controls are direct source inspection, an independent search path, a context/scope check, and reversible abstention.

### Evaporation as review pressure, not evidence deletion

Pheromone decay suggests reducing the routing priority of unrefreshed coordination hints. It does not justify deleting immutable evidence. TTL belongs on cache/index/salience layers; source retention follows governance and evidentiary rules.

### Turnover as de-anchoring

A new reviewer/model family can reduce convention lock-in only when its context excludes prior verdicts and includes raw source artifacts plus alternative hypotheses. Independence must be attested and tested for common inputs.

## Shared-memory benchmark requirements

A future `PMLAB-SHARED-001` should compare:

- isolated private memories;
- append-only shared evidence with no derived convention;
- shared coordination hints with TTL;
- majority/adoption ranking;
- provenance- and validity-gated shared retrieval;
- a fresh independently initialized reviewer;
- an oracle conflict and provenance control.

Required strata:

- correct shared trace, absent private memory;
- correct private memory, stale shared majority;
- poisoned trace copied by many agents;
- two authorized writers with scope-specific conflicting procedures;
- membership turnover with and without raw-source access;
- trace expiry while immutable evidence remains;
- revoked authorization and deletion/export requests;
- low-cost exploration that should dissolve an arbitrary convention;
- high exploration cost where a convention may remain rational;
- outcome feedback that is delayed, censored, or common-mode corrupted.

Primary metrics:

- exact supported action and critical false-action rate;
- stale/poison adoption and propagation depth;
- time to detect and correct a bad convention;
- diversity of genuinely independent evidence paths;
- source-resolvable citation completeness;
- cross-agent contamination and unauthorized exposure;
- useful coordination saved work at matched quality;
- convergence to truth versus mere convergence to one behavior.

Rejection gates:

- majority use is treated as correctness;
- TTL deletes evidence rather than only derived priority;
- a fresh agent receives prior conclusions and is counted as independent;
- shared/private conflict is hidden inside one scalar score;
- propagation speed improves while poison or stale adoption worsens;
- agent turnover breaks provenance, authorization, correction, export, or erasure.

## Current conclusion

The most useful biological analogy is not a colony mind. It is a layered system in which private memory, public traces, and population dynamics interact and can disagree. For the LLM project, canonical disk artifacts should be inspectable and append-only; derived shared hints should be scoped, expiring, reversible, and never self-validating. Conformity and repeated copying are safety risks as much as coordination mechanisms.

## Open searches

- independent replications of long-lived wild social traditions with full population turnover;
- experiments that manipulate trace decay separately from individual memory;
- negative or failed replications of context-specific ant trail/private-memory interactions;
- group correction after a deliberately seeded false or stale convention;
- authorization and asymmetric-information analogues in animal groups;
- distributed-systems evidence on provenance-preserving shared state, CRDT conflict, and revocation before translating this branch into software architecture.
