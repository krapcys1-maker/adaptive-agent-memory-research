# Structured-output and schema-linking targeted audit

Status: targeted primary-source audit for `PMLAB-MAP-STAGE-001`; not a systematic review

Reviewed: 2026-08-22

## Question

Can constrained generation repair the model arm's invalid outputs, and can schema retrieval repair unseen-schema grounding, without hiding semantic errors or increasing unsafe scope selection?

## Exact-source findings

### JSONSchemaBench

Geng et al., *JSONSchemaBench: A Rigorous Benchmark of Structured Outputs for Language Models*, arXiv:2501.10868v3.

- Abstract/page 1 and Section 1/pages 2-3 define three separate dimensions: efficiency, schema-feature coverage, and output quality. The corpus contains 9,558 retained real-world schemas across ten sources (Table 1, page 4), not a semantic-parsing benchmark.
- Definitions 5.1-5.3, pages 6-7, separate declared, empirical, and true schema coverage; empirical success does not prove semantic equivalence between a grammar and the schema.
- Definitions 5.4-5.5, page 7, distinguish over-constrained engines that reject valid instances from under-constrained engines that admit invalid ones.
- Section 6, page 10, explicitly tests whether token masking changes downstream task quality and notes tokenization/distribution-shift failure mechanisms.

Project use: report contract validity, declared/empirical feature coverage, semantic correctness, latency, and over/under-constraint separately. JSON validity cannot count as mapper correctness.

Limit: tasks and schemas evaluate structured decoding infrastructure; they do not supply obligation, entity, time, authorization, or closure labels.

Primary: https://arxiv.org/pdf/2501.10868

### Constraint Tax

Ray, *The Constraint Tax: Measuring Validity-Correctness Tradeoffs in Structured Outputs for Small Language Models*, arXiv:2605.26128.

- Main GPU experiment, page 3/Figure 2, reports schema validity rising from 61.5% to 100% while answer accuracy falls from 19.7% to 11.0% and wrong-valid-schema output rises from 49.5% to 88.9%.
- Calendar control, pages 3-4/Tables 6-7, holds schema validity at 100% but reports executable accuracy 91.5% for prompt JSON and delayed deterministic packaging versus 48.0% under direct hard-schema decoding. The delayed packager preserves the original semantic result.
- Section 6.5/page 5 reports the effect at a 3B boundary as well; it is not shown to generalize to larger proprietary models or obligation mapping.

Project use: add `wrong_valid_contract_rate` and a delayed deterministic packaging control. Hard constraints are a contract mechanism, not a semantic safety mechanism.

Limit: very recent preprint, small-model focus, authored deterministic suites, and no direct memory-mapping task. Treat as a high-priority lead requiring replication, not established universal behavior.

Primary: https://arxiv.org/pdf/2605.26128

### Hidden Cost of Structure

Schall and de Melo, *The Hidden Cost of Structure: How Constrained Decoding Affects Language Model Performance*, RANLP 2025.

- Section 4/pages 3-4 reports that effects depend on model adaptation and task: constraints may help base models, hurt or stabilize instruction-tuned models, and affect open generation more than classification.
- Section 4.8/page 6 reports that simultaneously requesting reasoning and structured compliance can degrade both; this does not prove that hidden reasoning or a two-call pipeline is always superior.

Project use: cross provider/model class and task type; never infer the constraint effect from one model. Keep semantic planning and packaging as a preregistered factor, not an assumed best practice.

Limit: benchmark tasks are not semantic memory mapping; some reported effects change direction across models and tasks.

Primary: https://aclanthology.org/2025.ranlp-1.124.pdf

### Controlled-sublanguage semantic parsing

Shin et al., *Constrained Language Models Yield Few-Shot Semantic Parsers*, EMNLP 2021.

- Introduction/page 1 and conclusion/page 9 formulate semantic parsing as paraphrasing into a controlled English-like sublanguage constrained to valid paraphrases, followed by deterministic mapping to a task representation.
- The method uses small hundreds of examples in its evaluated tasks; it is not zero-shot proof and does not solve grounding or safe abstention by itself.

Project use: retain a two-stage `controlled obligation language -> deterministic IR` candidate. Compare it with direct JSON and delayed packaging under identical semantic labels.

Limit: evaluated domains, grammar engineering, and examples differ from local-memory scope mapping; adaptation effort and unseen-schema behavior must be measured.

Primary: https://aclanthology.org/2021.emnlp-main.608.pdf

### Context-aware bidirectional schema retrieval

Nahid et al., *Rethinking Schema Linking: A Context-Aware Bidirectional Retrieval Approach for Text-to-SQL*, Findings of EACL 2026.

- Table 3/page 6 describes a recall/false-positive tradeoff: prior high-recall arms can retain many irrelevant elements; the paper reports 92.91% recall with 19.28% FPR for one BIRD setting, still below this project's proposed critical Recall@5 gate.
- Table 5/page 8 shows both table-first and column-first directions contribute; their removal changes recall and FPR differently.
- Limitations/page 9 state that multiple LLM calls add latency/cost, outputs remain non-deterministic, and similar schema names can still cause selection errors.
- Error analysis/Table 14/page 14 assigns most observed misses to explicit-column oversight (37%), name mismatch (33%), and partial match (23%) in that sample.

Project use: test complementary lexical and contextual candidate generators and union them only at the candidate-recall stage. Measure retained-schema fraction, FPR, tokens, calls, and downstream false closure; do not equate retrieval recall with correct selection.

Limit: Text-to-SQL, BIRD/Spider metrics, model-dependent multi-call method, and no NIL/authorization/certificate contract. Results do not directly transfer to user-disk memory schemas.

Primary: https://aclanthology.org/2026.findings-eacl.236.pdf

## Synthesis and decision

The evidence supports four additions to the factorized protocol:

1. split syntactic contract validity from semantic validity and from executable/end-to-end correctness;
2. measure wrong-but-valid output explicitly;
3. include prompt-only direct JSON, hard/constrained output where available, controlled-sublanguage, and delayed deterministic packaging as crossed interface factors;
4. evaluate schema candidate recall and false-positive/retained-schema cost before selection accuracy and downstream closure safety.

It does **not** justify adding a constrained-decoding runtime to the architecture. Provider support differs, model/task interactions can reverse, and none of these sources demonstrates safe obligation mapping in a local-memory system.

## Selective prediction and NIL follow-up

### Risk-coverage, not confidence alone

Xin et al., *The Art of Abstention*, ACL 2021, defines selective prediction as a predictor plus a selection function and evaluates the tradeoff with risk-coverage curves and their area (Section 3.1, pages 2-3). It also distinguishes calibration, which can change absolute probability levels, from selective ranking, and distinguishes model uncertainty from questions unanswerable even for humans (Section 2, page 2). The reported tasks are classification, not structured mapping.

Varshney et al., *Towards Improving Selective Prediction Ability of NLP Systems*, RepL4NLP 2022, reports that maximum probability degrades strongly out of domain and uses a learned calibrator based on confidence plus instance difficulty (Sections 2-5, pages 1-4). The result is task-specific and relies on held-out correctness annotations; it does not make a model's verbal confidence privileged evidence.

Project use: evaluate selective risk at fixed coverage and risk-coverage AUC separately for each mapper stage, with IID and unseen-schema strata. Do not use raw model self-confidence or MaxProb as the only abstention signal.

Primary: https://aclanthology.org/2021.acl-long.84.pdf and https://aclanthology.org/2022.repl4nlp-1.23.pdf

### NIL is not one class

Zhu et al., *Learn to Not Link*, Findings of ACL 2023, separates NIL into **Missing Entity** and **Non-Entity Phrase** (Section 2, page 3). Its NEL dataset has 9,924 examples and 33.57% NIL, mostly non-entity phrases (Table 2, page 4); the paper also reports that a manual sample of AIDA NIL labels contained about 10% linkable errors (Section 3, page 3). Its tested bi-/cross-encoders use score thresholds and type information; this does not establish calibrated thresholds for a new catalog.

Schindler et al., *Find the Funding*, COLING 2022, explicitly evaluates In-KB, Emerging Entity/out-of-KB, and All strata (Evaluation Metrics, page 3) and separates candidate retrieval from a lightweight Entity-or-NIL selector using retrieval, string, link-probability, and commonness features (page 3). The funding-domain supervision and Wikipedia-derived priors do not transfer directly to a local project catalog.

Project use: gold and outputs must distinguish `linked`, `ambiguous_in_catalog`, `missing_entity`, `non_entity_phrase`, and `mention_not_detected`. Report candidate recall, NIL subtype accuracy, false-link rate, and selective risk separately. A single similarity threshold may be a baseline, not an oracle.

Primary: https://aclanthology.org/2023.findings-acl.690.pdf and https://aclanthology.org/2022.coling-1.168.pdf

## Remaining search gaps

- calibrated selective prediction for joint NIL/entity/schema linking on structured outputs rather than classification;
- multilingual Polish schema-linking and span-alignment evidence;
- constrained-decoding comparisons on nested DAG outputs rather than shallow answer wrappers;
- local small-model replication with exact provider-neutral I/O;
- independently authored obligation-mapping labels.
