# Obligation decomposition and scope mapping

Status: targeted full-text metric audit complete for BREAK, schema linking, Spider-Syn, COGS, CFQ, SCATE, SemEval time normalization, and BLINK; multilingual evidence, later replication audit, and independent review incomplete

## Central conclusion

Collection closure is only as safe as the mapping from a natural-language question to the scopes being certified. The controller must not ask whether the whole question is complete as one string. It must first enumerate answer obligations, represent dependencies among them, and map each obligation independently to predicates, entities, valid time, namespaces, authorization, and certificate requirements.

A missed obligation is safety-critical: the system may certify and answer the part it noticed while silently omitting the rest. An extra obligation mainly costs retrieval or causes conservative abstention. The benchmark must therefore report under-decomposition and over-decomposition separately and assign higher utility loss to omitted critical facets.

## Evidence transferred

QDMR represents a complex question as an ordered, backward-referencing DAG of simpler natural-language steps and 13 operator families. BREAK contains 83,978 questions, but its full-text metrics impose caution: expert review found 97.4% correct decompositions and 93.8% both correct and granular; conversion review found 99.4% correct individual logical steps but only 93.1% fully accurate logical forms; the granular parser's exact match was 0.157 while manual semantic acceptance was 54%. The split follows source datasets/contexts rather than held-out semantic templates, and grounding is outside QDMR. It is therefore a useful candidate computation graph, not a ready-made oracle for personal-memory scopes.

Text-to-SQL work separates schema encoding from schema linking. The audited Spider study raised a simple parser from 57.4 to 72.4 dev exact match with oracle links, but automatic versus adjudicated link labels reached only 0.775 column, 0.801 table, and 0.915 value micro F1. In repeated manual audits of oracle-link parser errors, 29.6% were semantically valid outputs rejected by exact match, 26.3% were corpus errors, and 44.1% were genuine model incapability. A correct logical decomposition with the wrong predicate is still a wrong collection certificate, but correct links are also not sufficient for correct logical composition.

Spider-Syn removes easy lexical overlap by substituting natural synonyms. RAT-SQL+BERT fell from 69.7% Spider dev exact match to 48.2% on Spider-Syn. However, Spider-Syn has no public test set, 35% of development substitutions also occur in training, and ManualMAS uses the benchmark's own synonym annotations. It establishes lexical fragility, not open-schema or Polish generalization. English paraphrases, Polish forms, abbreviations, and user vocabulary must be grouped by semantic template and schema, with glossaries frozen independently.

COGS exposes compositional generalization gaps by contrasting ordinary in-distribution data with a 21,000-example, 21-case generalization set. Tested models scored 0.96-0.99 in distribution but only 0.16-0.35 on generalization, with high seed sensitivity, and structural recombinations were harder than lexical ones. CFQ/DBCA formalizes the split objective: keep atom distributions similar while making rule-application compounds different. Its MCD baselines fell from above 97% random-split accuracy to 14.9-18.9%, but CFQ deliberately removes ambiguity and named-entity learning. These generated-task numbers do not transfer; the split discipline does. Bilingual translations and paraphrases of one semantic template belong to one group, and challenge structures must recombine familiar atoms in unseen compounds. Hyperparameters may not be selected on a validation set drawn from the challenge compound distribution.

Temporal normalization is a distinct semantic task. SCATE defines typed periods, intervals, repeating intervals, and 18 temporal operator signatures/variants. Its initial 34-document corpus reached 0.917 span/type F1 but 0.821 full span/type/property/link F1. SemEval-2018 then separated component-graph parsing from interpreted bounded intervals and showed that better component scores need not yield better interval scores. The project must preserve raw span, operator graph, normalized interval, reference time, timezone, granularity, inclusivity, recurrence, and ambiguity, and score structure separately from denotation. A parser that guesses an interval must not silently select a certificate.

Entity linking is likewise separate. BLINK illustrates candidate retrieval plus reranking, but its zero-shot task assumes a valid in-KB gold entity and explicitly leaves NIL prediction to future work. Its 82.06% Recall@64 on the zero-shot test also demonstrates that reranking cannot recover a gold entity absent from the candidate set. Dense similarity is not authorization or identity proof. The mapper must preserve multiple candidates and return ambiguous/NIL state when required rather than force a link.

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

Semantic equivalence needs structured comparison or controlled execution. Raw exact match remains a strict diagnostic but cannot be the only decomposition metric. Conversely, denotational equivalence cannot replace graph scoring because a wrong intermediate structure can accidentally produce the same result on one fixture. Strict form, structure, and denotation/action are three separate score views.

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

- audit later CFQ/COGS/QDMR replications and alternative compound definitions;
- find Polish and multilingual decomposition/entity/temporal benchmarks or establish a documented translation protocol;
- compare SCATE, TimeML/TIMEX3, HeidelTime, and modern multilingual normalizers on our supported time language;
- audit later entity-linking calibration and NIL/unknown handling rather than top-1 in-KB accuracy alone;
- obtain an independent review of obligation atomicity, operator inventory, and asymmetric utilities.

Exact local locators, hashes, numerical caveats, and audit corrections are recorded in `docs/07-literature/obligation-mapping-primary-source-audit.md`. The construction contract is in `docs/11-research-laboratory/obligation-ir-schema-v0.md`.
