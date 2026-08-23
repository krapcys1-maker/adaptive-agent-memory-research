# Equal-evidence citation and order reader pilot v0

Experiment ID: `PMLAB-PACK-READER-001`  
Status: first-reader synthetic compatibility branch completed; all frozen gates passed; fixture spent
Authority: synthetic reader compatibility pilot only

Post-run status note: the fixture froze at `365c0b6`, prompt/runner/scorer at `d870741`, authorization at `5f98277`, raw responses at `1df509b` before the gold join, and scoring/audit at `b114865`. This sentence is a status annotation after execution; the preregistered gates remain recoverable at the prompt-freeze commit and are not retroactively changed.

## Purpose

Determine whether a reader can use exact full locators and compact source-footer locators when evidence IDs are held constant, and whether governed ordering changes answer accuracy or stale-value use. This follows the deterministic drafting gate from `PMLAB-PACK-002`.

It does not test retrieval, capacity selection, trust detection, automatic current/stale classification, natural project history, long-term utility, or architecture superiority.

## Fresh grouped fixture

The frozen construction fixture contains 16 new semantic groups, each with an English and Polish case (`32` cases). Bilingual cases remain one analysis group and never count as independent replications.

Every case contains the same eight evidence records in all four arms:

- two current records;
- two supporting records;
- two stale/conflicting records with plausible superseded values;
- two reviewed distractors;
- one to three exact answer atoms;
- one to three required evidence IDs;
- no untrusted record, because detection and pre-exposure filtering are separate experiments.

Strata must include single-fact, multi-fact, current-versus-stale conflict, supporting bridge, middle-position evidence, and bilingual instruction cases. Answers use synthetic unique atoms so scoring requires no LLM judge. All evidence, gold answers, required citations, group IDs, and stale atoms freeze before the reader runner or prompt packet.

## Factorial arms

| Factor | Arm | Serialized representation |
|---|---|---|
| Citation | `F0_FULL` | `[Rnn|path:Lx-Ly] <bucket> evidence` |
| Citation | `F1_COMPACT` | `[Rnn|Snn:Lx-Ly] <bucket> evidence`, followed by complete `[Snn]=path` dictionary |
| Order | `O0_RETRIEVAL` | frozen supplied order |
| Order | `O1_GOVERNED` | stable current, supporting, stale/conflicting order |

This yields `32 × 2 × 2 = 128` calls per reader model. The same `Rnn` record identifier appears in every citation format, and the reader always returns `Rnn` citations. This keeps the output contract identical while changing only locator serialization.

Every arm receives identical evidence IDs and byte-identical evidence text. Serialized bytes and provider tokens are measured, not equalized: adding padding would introduce a second contextual treatment and erasing locator length would remove the citation-format treatment.

## Prompt and blinding

- one case-condition per fresh API call;
- temperature `0`, thinking disabled, no conversation history;
- opaque condition/run IDs contain no `full`, `compact`, `retrieval`, `governed`, `current`, `stale`, `gold`, or expected-answer token;
- evidence precedes the question; the question appears once after evidence;
- no in-context solved example;
- the system prompt defines bucket semantics and says stale/conflicting evidence may be discussed but must not replace current facts;
- exact JSON output: `{"answer_atoms":["..."],"citations":["Rnn"],"abstain":false}`;
- no chain-of-thought request or storage.

Condition mapping and gold stay local and are joined only after all raw responses freeze.

## Reader models and cost

First reader: frozen `deepseek-v4-flash` model identifier, author-operated M1 synthetic reader. It is optional and replaceable, not project memory or an independent reviewer.

- per-experiment conservative cap: USD `0.50`;
- project cap: USD `10.00`;
- preflight must assume peak cache-miss input pricing;
- one retry is allowed only for transport failure or invalid JSON and must be charged and preserved;
- no retry for a wrong answer;
- every call records model-returned usage, response ID, latency, and conservative cost.

A second model family is required before any format or order recommendation beyond this reader.

## Deterministic scoring

- exact answer-atom set accuracy;
- per-atom recall and precision;
- exact required-citation set accuracy;
- required citation recall;
- invalid or unresolved citation rate;
- stale-atom use rate;
- current/stale conflict resolution accuracy;
- schema-valid response rate;
- inappropriate abstention rate;
- paired differences by semantic group and language;
- serialized UTF-8 bytes and provider input tokens as descriptive mediators.

No LLM judge is used. Normalization is limited to Unicode NFC, surrounding whitespace, and set ordering. It may not map synonyms or repair values.

## Frozen compatibility gates

Across the 16 semantic groups, score a group correct only when both language cases are correct.

1. schema validity at least `0.95` in every arm;
2. unresolved citation rate `0` in every arm;
3. no critical stale atom in any answer;
4. absolute reader competence in every arm: at least `14/16` groups exact-answer correct, required-citation recall at least `0.95`, and inappropriate-abstention rate no more than `0.05`;
5. within each order, `F1_COMPACT` group exact-answer accuracy is no more than one group below `F0_FULL`, and required-citation recall differs by no worse than `-0.05`;
6. within each format, `O1_GOVERNED` stale-use rate is no higher than `O0_RETRIEVAL`, and group exact-answer accuracy differs by no worse than `-0.05`;
7. every arm must receive identical record IDs and evidence text for a case; any mismatch invalidates the comparison.

These are compatibility gates, not superiority tests. Passing advances the format/order pair only to cross-family replication or natural-history development. Failure localizes reader incompatibility and preserves both baselines.

## Analysis boundaries

- Report the frozen four-arm table even if a gate fails.
- Do not pool 32 bilingual cases as independent observations.
- Do not tune prompts, evidence order, atoms, or normalization after the first valid response.
- Do not use the deterministic 24-case pack fixture as reader data.
- Post-hoc position, token, or error analyses must be labelled and cannot modify this pilot.
- No architecture or default format follows from an author-built fixture or a single reader family.

## Construction and execution locks

Execution remains locked until:

1. [complete] the 16-group fixture, source spans, and gold hashes freeze;
2. [complete] a leakage audit verifies opaque condition IDs and removes treatment/gold names from prompt-safe inputs;
3. [complete] the provider-neutral prompt, JSON validator, scorer, condition schedule, and model manifest freeze;
4. [complete] all 128 prompts pass local evidence-identity and citation-resolution checks;
5. [complete] the peak-cost preflight is below USD 0.50;
6. [complete] project memory records the frozen commit and the fact that this is an M1 synthetic reader.

## Completion receipt

The DeepSeek V4 Flash arm made 128 stateless calls with zero retry/error for USD `0.04026000`, below the USD `0.50` experiment cap. All four arms reached 16/16 grouped exact answers with zero stale use and unresolved citations. One compact-governed Polish condition returned the correct answer atoms but substituted one resolvable non-supporting citation, leaving required-citation recall at `0.984375` in that arm. All registered compatibility gates still passed.

`data/lab/pmlab-pack-reader-v0/execution-deepseek-v4-flash-v0/completion-audit.json` verifies the freeze/authorization/raw/score commit order, exact frozen bytes, 1,024 locator resolutions, no named treatment/gold leakage, model and decoding, cost preflight, 128 unique API receipts, zero retries, budget-ledger cost, raw and score hashes, deterministic metric reproduction, and the preserved claim boundary.

This closes only the first-reader build/freeze/execute/audit branch. A different model family or independently reviewed natural-history development remains mandatory before any locator-format or order recommendation.
