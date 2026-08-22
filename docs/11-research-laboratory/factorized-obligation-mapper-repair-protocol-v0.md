# Factorized obligation-mapper repair protocol v0

Status: preregistration draft derived from spent challenge diagnostics; no repair implementation

## Why a factorized program is necessary

PMLAB-MAP challenge v0 rejected both integrated candidates. The deterministic arm coupled surface templates to construction-specific entity and predicate rules. The optional model coupled JSON generation, span copying, graph construction, grounding, and safety state in one response. Their failures overlap, so neither a prompt edit nor a larger rule table can identify the responsible mechanism.

This protocol turns the mapper into six independently falsifiable stages before another integrated challenge is allowed:

1. **contract and span alignment** — valid serialization, exact source spans, stable IDs, backward-only dependencies;
2. **obligation graph** — operators, atomic facets, dependency edges, unsupported-structure detection;
3. **entity grounding** — catalog linking, type collisions, coreference, NIL detection, and conservative ambiguity;
4. **predicate and namespace linking** — schema-conditioned candidate generation, synonym robustness, and unseen-schema transfer;
5. **time and authorization scope** — normalized intervals/event anchors and access state without conflating them with graph operators;
6. **certificate routing** — applicable, derived, explicit-negative, collection-bounded absence, ambiguous, and inapplicable states.

The stage order is an observability order, not a claim about neural or cognitive processing.

## Data partitions

Create three new artifacts. PMLAB-MAP construction and challenge v0 are now development/diagnostic data and cannot become confirmation sets.

| Artifact | Purpose | Permitted use |
| --- | --- | --- |
| `pmlab-map-stage-dev-v1` | minimal pairs and single-stage perturbations | design and debug |
| `pmlab-map-stage-challenge-v1` | new surface families with familiar schema atoms | post-freeze stage estimates |
| `pmlab-map-integrated-challenge-v1` | disjoint schema IDs, entities, compounds, languages, and ambiguity patterns | final post-repair gate only |

Every semantic group, translation, and paraphrase stays in one partition. Challenge authors must not inspect candidate outputs. At least one independent human or different model family must review critical labels before the integrated run.

## Stage interventions and controls

Each stage receives only the inputs it could have at runtime. Diagnostic gold may replace exactly one upstream stage, but every such arm must be named `oracle-*` and may never count as deployable performance.

| Stage under test | Fixed input | Primary output | Required controls |
| --- | --- | --- | --- |
| contract/span | raw query + proposed graph payload | validated or typed rejection; exact spans | corrupted JSON, paraphrased non-spans, empty required fields |
| graph | raw query only | operator DAG + spans + status | atomic, coordinated, coreferential, set, numeric, unsupported |
| entity | gold leaf spans + catalog | ranked ID/NIL/ambiguous | alias collision, cross-type collision, unseen alias, missing entity |
| predicate | gold leaf spans + schema/glossary | ranked predicate + namespace/abstain | synonyms, adversarial near-neighbors, unseen schema family |
| time/auth | gold leaf + clock + principal | interval/event anchor + access state | relative/recurring/ambiguous time, denied and partially visible scope |
| certificate | gold mappings + collection metadata | typed certificate query/status | explicit falsity versus absence, stale/incomplete certificates, insertion counterexamples |

Candidate generation and final selection must be reported separately. Recall@k can justify a later reranker only when top-1 remains inadequate; it cannot satisfy the end-to-end gate by itself.

## Metrics and asymmetric gates

All confidence intervals are grouped by semantic template, not by translated row.

- contract validity: 1.000; invalid output always becomes a typed unresolved result, never silent repair;
- critical obligation full recall: at least 0.95 with zero unsupported coercions;
- entity and predicate candidate Recall@5: at least 0.99 on supported cases;
- entity and predicate top-1: at least 0.95, with 1.000 safe handling of critical NIL/ambiguity;
- supported temporal exact interval/event-anchor match: at least 0.90; ambiguous-time safe handling 1.000;
- authorization and certificate safety: zero unauthorized exposure, zero false explicit-negative or collection-absence certificates;
- integrated obligation F1: at least 0.90 and no more than 0.05 unseen-schema or 0.10 unseen-composition degradation;
- integrated safety: zero critical omissions, zero false closures, and critical unresolved safe handling 1.000.

No average score compensates for a safety-gate failure. Report coverage, abstention, latency, token/API cost, and schema-invalid rate with accuracy.

## Repair candidates worth testing

These are hypotheses, not architecture decisions:

1. deterministic contract wrapper that converts invalid spans or empty fields into typed unresolved output;
2. catalog-first entity candidate generation with explicit NIL and collision sets;
3. schema-first predicate candidate generation from versioned aliases/descriptions, followed by a separate selector;
4. graph parser that emits placeholders rather than inventing groundings;
5. temporal parser and certificate router as independent modules;
6. constrained decoding or tool-schema validation only after measuring whether it improves semantic validity rather than JSON syntax alone;
7. optional LLM selection over deterministic candidate sets, with local fallback and identical provider-neutral I/O.

For any model arm, cross four interface modes where the provider/runtime permits them: prompt-only direct JSON, hard constrained output, controlled-sublanguage followed by deterministic conversion, and semantic draft followed by deterministic validation/packaging. Score `schema_valid`, `semantic_correct`, `end_to_end_correct`, and `wrong_valid_contract` separately. A 100% valid JSON stream can still fail the semantic safety gate.

For schema retrieval, report candidate Recall@5 together with false-positive rate, retained-schema fraction, tokens, calls, and latency. A union of lexical and contextual candidates is admissible only as a recall-stage arm; it must not be presented as correct top-1 scope selection.

## Stop and promotion rules

Stop repairing an integrated arm on challenge v0: it is spent. A repair may proceed only on stage dev v1, then freeze. If an oracle-isolated stage does not improve the downstream critical metric by at least five percentage points or remove a safety failure, do not add its complexity. If candidate Recall@5 is below 0.99, do not spend effort on a reranker. If all isolated stages pass but integration fails, investigate interface composition rather than retraining each stage.

An integrated mapper may advance only after stage challenges, a newly frozen integrated challenge, independent critical-label review, and clean reproduction. Until then the memory controller must default to continued search, clarification, or abstention when mapping is unresolved.
