# Obligation decomposition and scope mapping

Status: targeted primary-paper pass complete; full-text metric audit, multilingual evidence, and independent review incomplete

## Central conclusion

Collection closure is only as safe as the mapping from a natural-language question to the scopes being certified. The controller must not ask whether the whole question is complete as one string. It must first enumerate answer obligations, represent dependencies among them, and map each obligation independently to predicates, entities, valid time, namespaces, authorization, and certificate requirements.

A missed obligation is safety-critical: the system may certify and answer the part it noticed while silently omitting the rest. An extra obligation mainly costs retrieval or causes conservative abstention. The benchmark must therefore report under-decomposition and over-decomposition separately and assign higher utility loss to omitted critical facets.

## Evidence transferred

QDMR represents a complex question as an ordered sequence of simpler natural-language steps and a small operator inventory. The BREAK work shows that these decompositions can be converted to a pseudo-SQL representation and used in downstream QA. This makes QDMR a useful candidate intermediate representation, not a ready-made oracle for personal memory: its source tasks, annotations, operators, and evaluation do not encode our authorization, valid-time, provenance, or collection-certificate semantics.

Text-to-SQL work separates schema encoding from schema linking. RAT-SQL and subsequent schema-linking analysis show that aligning mentions to columns/tables is a central failure source, especially on unseen schemas. This maps directly to predicate and namespace selection in memory. A correct logical decomposition with the wrong predicate is still a wrong collection certificate.

Spider-Syn removes easy lexical overlap by substituting natural synonyms and reports large performance degradation in existing parsers. Therefore our mapper cannot be evaluated only on questions that repeat canonical predicate names. English paraphrases, Polish forms, abbreviations, and user vocabulary must be split by semantic template and schema, with synonym glossaries frozen independently.

COGS and CFQ expose compositional generalization gaps by holding out new combinations of familiar atoms and structures. Random row splits are not sufficient. Bilingual translations and paraphrases of one semantic template belong to one split group; new test structures must combine familiar predicates, entity types, time operators, and question operators in unseen ways.

Temporal normalization is a distinct semantic task. SCATE-style work represents expressions using compositional operators and handles relative, recurring, intersecting, and event-anchored time. The project must preserve the original span, normalized interval, reference time, timezone, granularity, inclusivity, and ambiguity. A parser that guesses an interval must not silently select a certificate.

Entity linking is likewise separate. Retrieval-plus-reranking systems such as BLINK illustrate the candidate-generation/disambiguation split, but dense similarity is not authorization or identity proof. The mapper must return multiple candidates or unresolved state when names collide.

## Proposed intermediate representation

```yaml
query_id: ...
language: pl
reference_time: 2026-08-22T12:00:00+03:00
obligations:
  - obligation_id: O1
    operator: SELECT
    natural_span: "czy projekt został sprawdzony"
    predicate_candidates:
      - {predicate: review_status, basis: glossary, score: 0.91}
    entity:
      mention: "Umber"
      candidates: [{entity_id: project:umber, basis: exact_alias}]
    time:
      raw: null
      normalized: {from: null, to: 2026-08-22T12:00:00+03:00}
      anchor: query_reference_time
      status: resolved
    namespace_candidates: [canonical-events]
    dependencies: []
  - obligation_id: O2
    operator: SELECT
    natural_span: "kto go zatwierdził"
    predicate_candidates: [{predicate: approver, basis: glossary, score: 0.88}]
    entity: {mention: "go", corefers_to: O1.entity}
    time: {inherit_from: O1}
    namespace_candidates: [canonical-events, approvals]
    dependencies: [O1]
query_status: resolved | ambiguous | unsupported_structure
```

Every normalized field retains its evidence basis. Scores rank candidates but do not choose a closed-world scope by themselves. When two entity, predicate, or time interpretations remain live, the output is ambiguous and the controller asks or searches multiple scopes.

## Stage separation

| Stage | Output | Typical error | Required metric |
| --- | --- | --- | --- |
| obligation discovery | atomic required answer facets | omitted approver facet | obligation recall/precision, critical omission count |
| dependency graph | references and computation order | wrong coreference or missing bridge | labeled edge F1 and executable graph validity |
| entity linking | candidate entity IDs | project/person name collision | top-k recall, exact link, ambiguity calibration |
| predicate/schema linking | predicates and namespaces | `approval` mapped to `review` | link recall/precision under unseen schemas and synonyms |
| temporal normalization | interval, anchor, timezone, status | “last month” anchored incorrectly | exact/overlap interval, anchor and ambiguity accuracy |
| certificate routing | one certificate query per obligation | whole-query certificate reused for one facet | per-obligation scope exactness and unsafe-closure rate |

End-to-end answer accuracy cannot localize these failures. Gold obligations must be a diagnostic ceiling; a deployable closure evaluator receives only predicted scopes.

## PMLAB-MAP-001 design

### Strata

- single atomic fact and two/three coordinated facets;
- dependencies, coreference, ellipsis, comparison, aggregation, negation, and conditionals;
- one supported facet plus one differently closed or unclosed facet;
- entity aliases, duplicate surface names, type collisions, and unresolved mentions;
- direct predicate names versus synonyms, abbreviations, domain vocabulary, and misleading lexical neighbors;
- new schemas/namespaces with familiar relation structure;
- absolute dates, relative dates, intervals, recurrence, event anchors, timezone, and underspecified time;
- English/Polish pairs, code-switching, inflection, and paraphrase;
- familiar atomic mappings in unseen structural combinations;
- unsupported structures that must abstain rather than invent a scope.

### Arms

1. whole-query single scope;
2. punctuation/conjunction splitter;
3. QDMR-inspired deterministic operator parser;
4. independent entity, predicate, and temporal linkers after gold obligations;
5. full predicted pipeline;
6. optional provider-neutral LLM decomposition with a frozen prompt and schema;
7. gold obligations plus predicted links;
8. gold obligations and links as diagnostic oracle.

### Metrics and error accounting

- exact obligation set and operator sequence;
- obligation precision/recall/F1, with critical weighted recall reported separately;
- dependency labeled-edge F1 and graph executability;
- entity/predicate/namespace top-1 and top-k link accuracy;
- time value, interval overlap, anchor, timezone, granularity, and ambiguity accuracy;
- per-obligation exact scope and certificate applicability;
- false closure caused by a missed or mislinked obligation;
- downstream N0-N3 tier/action accuracy using the frozen closure evaluator;
- abstention, clarification, retrieval cost, latency, and risk-coverage;
- errors by unseen template, unseen schema, synonym, language, ambiguity, and temporal class.

Semantic equivalence needs structured comparison or controlled execution. Raw string exact match remains a strict diagnostic but cannot be the only decomposition metric.

### Candidate gates

- zero critical obligations omitted in the held-out challenge;
- at least 0.95 critical obligation recall and 0.90 macro obligation F1;
- zero false N2/N3 caused by mapper output;
- at least 0.95 entity and predicate top-1 accuracy on answerable unambiguous scopes;
- 100% clarification/abstention on critical unresolved entity, predicate, and time cases;
- at least 0.90 exact temporal normalization on supported expressions and zero silent guesses on unsupported expressions;
- no more than five percentage points degradation from seen to unseen schema and no more than ten points from seen to unseen composition;
- at least 15 points lower unsafe-closure risk than the conjunction splitter at matched action coverage;
- every accepted scope carries span, normalization, candidate, glossary/schema version, and parser version provenance.

These are preregistration candidates. Dataset utilities and minimum coverage must be independently frozen before a confirmatory run.

## Rejected shortcuts

- split only on the word `and` or Polish `i`;
- use one certificate for a multi-facet question;
- map the most similar predicate and hide alternatives;
- random-split translations or paraphrases of the same semantic template;
- measure only exact output string or downstream answer correctness;
- let gold obligations leak into the deployable scope mapper;
- treat model consistency as correct schema linking;
- silently resolve relative time without recording the reference clock and timezone.

## Sources examined

- Wolfson et al. (2020), BREAK/QDMR: https://doi.org/10.1162/tacl_a_00309
- Wang et al. (2020), RAT-SQL: https://doi.org/10.18653/v1/2020.acl-main.677
- Lei et al. (2020), schema-linking analysis: https://doi.org/10.18653/v1/2020.emnlp-main.564
- Yu et al. (2018), Spider: https://doi.org/10.18653/v1/D18-1425
- Gan et al. (2021), Spider-Syn: https://doi.org/10.18653/v1/2021.acl-long.195
- Kim and Linzen (2020), COGS: https://doi.org/10.18653/v1/2020.emnlp-main.731
- Keysers et al. (2020), CFQ: https://openreview.net/forum?id=SygcCnNKwr
- Bethard and Parker (2016), SCATE: https://aclanthology.org/L16-1599/
- Laparra et al. (2018), SemEval parsing time normalizations: https://aclanthology.org/S18-1011/
- Wu et al. (2020), BLINK: https://doi.org/10.18653/v1/2020.emnlp-main.519

## Remaining evidence work

- read BREAK annotation, conversion, split, and evaluation sections in full and inspect later QDMR error analyses;
- audit Spider schema-linking labels, noise, execution metrics, and adversarial variants;
- find Polish and multilingual decomposition/entity/temporal benchmarks or establish a documented translation protocol;
- compare SCATE, TimeML/TIMEX3, HeidelTime, and modern multilingual normalizers on our supported time language;
- audit entity-linking calibration and NIL/unknown handling rather than top-1 accuracy alone;
- obtain an independent review of obligation atomicity, operator inventory, and asymmetric utilities.
