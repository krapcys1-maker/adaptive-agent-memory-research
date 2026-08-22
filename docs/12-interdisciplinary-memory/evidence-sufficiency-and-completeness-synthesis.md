# Evidence sufficiency, completeness, and answerability

Status: targeted primary-source pass complete; independent review and replication search incomplete

## Central conclusion

Retrieval relevance is not evidence sufficiency. A memory system can retrieve topically related, valid, trusted records and still lack the fact, one required facet, a bridge between records, a current resolution of conflict, or support for a particular generated claim. The monitor must represent these states separately and must be allowed to answer partially, name the missing evidence, search for a missing facet, ask for clarification, or abstain.

This conclusion follows both from the literature and from the project's frozen diverse-cue result. Valid-time, trust, and bilingual interventions removed stale/poison intrusions and recovered cross-language targets, but they did not abstain on two absent facts and did not repair one incomplete multi-source answer. Better retrieval did not create an evidence-sufficiency judgment.

The follow-up 36-case construction corpus was frozen before runner implementation at commit `4ca0309`. Non-empty retrieval produced 0.75 selective sufficiency risk; similarity, context relevance, self-report, and semantic-consistency arms each produced 0.80 on authored adversarial scores. Claim entailment fell to 0.20 but retained two critical false-sufficient decisions because support alone did not encode validity and conflict. A retrieved-obligation monitor reached 0.778 exact action at zero answer risk, but confused continued search with collection-confirmed absence or permanent partiality in eight cases. A diagnostic collection-aware hybrid reproduced all authored actions, while the matched-coverage gates failed. This validates the typed decision contract only and isolates collection-scope evidence as a required input.

## Distinctions that the system must preserve

| State | Question answered by the state | Example failure |
|---|---|---|
| relevance | Is this record about the query topic? | user-related record retrieved for an unknown favorite color |
| validity | Is the record authorized and valid at the requested time? | superseded provider selected as current |
| answerability | Does the authorized collection contain an answer? | pet name never captured |
| facet completeness | Are all requested subquestions or interpretations covered? | only one of two conflicting studies retrieved |
| bridge completeness | Is the relation needed to combine records present? | diagnosis and repair found but causal link absent |
| claim support | Does evidence entail each generated atomic claim? | fluent extrapolation beyond a passage |
| attribution completeness | Does every externally verifiable claim cite supporting evidence? | correct paragraph with only half its claims cited |
| conflict resolution | Can incompatible current claims be resolved under policy? | two authorized current owners with no precedence rule |
| collection closure | Are we authorized to infer absence from the searched inventory? | local scan omits an offline replica |

One scalar such as similarity, model confidence, number of chunks, or citation count collapses incompatible failure modes. In particular, a citation can be present but irrelevant, relevant but insufficient, or sufficient for only one claim.

## Evidence from question-answering and RAG evaluation

SQuAD 2.0 pairs relevant passages with adversarial unanswerable questions containing plausible answer-like material. Its engineering lesson is that topical relevance and answer-shaped spans must not count as answerability.

ASQA makes ambiguity explicit: a good long-form answer must cover multiple disambiguated interpretations, often using multiple sources. This supplies a measurable analogue for our incomplete-contradiction case: success is facet coverage, not the presence of any one correct fact.

ALCE separates answer correctness from citation quality and evaluates citation precision and recall. Its reported systems frequently lacked complete citation support. The transferable unit is a claim-to-evidence relation, not a document count.

ARES separates context relevance, answer faithfulness, and answer relevance and uses a small human-labeled set with prediction-powered inference to correct automated-judge estimates. RAGChecker likewise argues for separate retriever and generator diagnostics. Both warn against scoring one end-to-end number, although their learned judges are not independent ground truth for our local system.

RAGTruth supplies span-level annotations of unsupported and contradictory generated content. Chang and colleagues separately annotate hallucination and coverage errors when a response should represent multiple perspectives. These are complementary axes: a response may contain no invented statement yet still omit a required facet.

Self-RAG demonstrates a trainable design in which retrieval and critique actions are represented explicitly with reflection tokens. It is a candidate control architecture, not proof that self-critique is calibrated: the critic and generator can share model, training-data, and evidence failures. For this project, learned reflection is an arm to compare against deterministic provenance and obligation coverage, not an oracle.

## Proposed typed sufficiency state

The monitor should emit an inspectable object:

```text
query_resolution:
  status: resolved | ambiguous | unresolved
  obligations: [O1, O2, ...]
collection_scope:
  inventory_complete: true | false | unknown
  searched_domains: [...]
evidence_coverage:
  O1: supported | contradicted | partial | missing
  O2: supported | contradicted | partial | missing
claim_support:
  C1: [source_id, locator, entailment_status]
conflicts: [...]
next_missing_obligation: O2 | null
allowed_action: answer | partial_with_gap | retrieve | ask | abstain
```

`inventory_complete=false` prohibits `not stored`; it permits only `not found in searched scope`. `partial_with_gap` must enumerate supported and unsupported obligations and must not silently fill gaps from model parameters.

## Benchmark proposal: PMLAB evidence-sufficiency v0

### Case strata

- answer absent, but a highly similar record exists;
- answer absent and retrieval is empty;
- one of two or three enumerated facets missing;
- multi-hop bridge record missing;
- all evidence present but one record is stale, untrusted, or unauthorized;
- two current records conflict without a precedence rule;
- ambiguity requiring clarification rather than aggregation;
- answer supported but a generated extra claim is unsupported;
- answer correct but citation coverage is incomplete;
- complete evidence expressed across paraphrase, bilingual, and direct-ID cues;
- incomplete replica inventory where absence cannot be concluded;
- retrieval saturation with repeated redundant evidence but no new obligation coverage.

### Arms

1. non-empty retrieval heuristic;
2. lexical-score or backend-agreement threshold;
3. reader self-report of sufficient context;
4. context-relevance judge;
5. claim-level entailment/faithfulness judge;
6. deterministic obligation and provenance coverage;
7. hybrid obligation coverage plus learned entailment;
8. separately reported answerability, evidence-set, and action oracles.

The query-decomposition component must be ablated from the coverage checker. Gold obligations may be used only as a diagnostic ceiling, never by a deployable arm.

### Metrics

- false-sufficient rate: answer allowed despite missing, contradictory, unauthorized, or unsupported evidence;
- false-insufficient rate: abstention despite complete authorized evidence within budget;
- obligation/facet recall and precision;
- evidence-set sufficiency accuracy;
- claim-support precision and recall;
- citation correctness and completeness;
- correct full answer, correct partial-with-gap, clarification, and abstention rates;
- gap-description accuracy: whether the named missing obligation is actually missing;
- risk–coverage curve for allowed answers;
- retrieval steps, new obligations per step, redundant-evidence rate, token cost, and latency;
- source-ID completeness and unsupported parametric additions;
- stage-localized errors for decomposition, retrieval, coverage, reader, and action.

### Candidate gates to freeze independently

- zero false-sufficient decisions in critical absent, conflict, unauthorized, and incomplete-inventory cases;
- at least 0.90 correct abstention or partial-with-gap action on absent and incomplete cases;
- at least 0.90 obligation recall with at least 0.95 claim-support precision on complete cases;
- at least 15 percentage points lower false-sufficient rate than self-reported sufficiency at matched answer coverage;
- 100% immutable source IDs and exact obligation-to-source links for accepted critical answers;
- no `not stored` output unless the separately frozen storage/replica probe contract permits it.

These thresholds are a preregistration proposal. A reviewer must freeze case utilities, decomposition labels, and minimum answer coverage before a confirmatory run.

## Rejected shortcuts

- any retrieved chunk means the question is answerable;
- high similarity means the evidence is sufficient;
- five chunks are more sufficient than one;
- the reader says the context is sufficient, therefore it is;
- every sentence has a citation, therefore every citation supports it;
- every generated claim is supported, therefore the answer is complete;
- search saturation proves the fact is absent;
- absence from one index proves absence from durable memory;
- adding more retrieval indefinitely is safer than a typed gap or abstention.

## Sources examined

- Rajpurkar, Jia, and Liang (2018), SQuAD 2.0 paper: https://doi.org/10.18653/v1/P18-2124
- Stelmakh et al. (2022), ASQA: https://doi.org/10.18653/v1/2022.emnlp-main.566
- Gao et al. (2023), ALCE: https://doi.org/10.18653/v1/2023.emnlp-main.398
- Saad-Falcon et al. (2024), ARES: https://doi.org/10.18653/v1/2024.naacl-long.20
- Ru et al. (2024), RAGChecker: https://proceedings.neurips.cc/paper_files/paper/2024/hash/27245589131d17368cccdfa990cbf16e-Abstract-Datasets_and_Benchmarks_Track.html
- Niu et al. (2024), RAGTruth: https://doi.org/10.18653/v1/2024.acl-long.585
- Chang et al. (2024), hallucination versus coverage errors: https://aclanthology.org/2024.lrec-main.423/
- Asai et al. (2024), Self-RAG: https://openreview.net/forum?id=hSyW5go0v8

## Remaining evidence work

- search direct SQuAD 2.0 answerability replications, adversarial failures, and calibration studies;
- inspect full metric definitions and human-correlation limitations in ALCE and RAGChecker;
- find evidence-set sufficiency datasets that label missing bridge and missing facet separately;
- compare learned entailment judges with deterministic claim/source labels under domain and language shift;
- audit Self-RAG reflection-token calibration and shared-failure controls;
- obtain independent review of the proposed obligation schema and critical-case utilities.
