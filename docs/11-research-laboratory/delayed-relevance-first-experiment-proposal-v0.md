# Delayed-relevance recovery at a fixed budget: first experiment, proposal v0

**Status: proposal.** Not registered, not approved, nothing built, no spend authorised. Registering it needs the owner's decision on the preregistration pause and the work-in-progress limit (section 6). It answers item 6 of the [research vision](../00-project/research-vision-2026-11.md) ("recommend the smallest useful first experiment") and uses the provisional ids V-H1 and V-H5 defined in the [direction review](../00-project/research-direction-review-2026-11.md), because plain "H1" already names corpus H1 here.

## 1. The question

At an equal token budget, does a compact **associative trace** index over a preserved raw archive recover an old, low-priority experience that only becomes relevant after the agent's goal changes, better than the conventional alternatives? The claim is about a *regime* (delayed relevance after a goal change, small budget, little shared wording), not about a new mechanism. A null result, "plain retrieval is as good", is a complete and publishable answer.

## 2. What the evidence already says, and what that forces

| Fact | Source | Consequence for the design |
|---|---|---|
| Corpus H1's DELAYED and REDERIVE families are solved: lexical recall 1.000 at k=1, 5 and 10, dense 1.000. The cue names the service and the phrase "pool exhaustion", so a word index finds the event first. MEASURED | [direction review](../00-project/research-direction-review-2026-11.md) 5a; `data/lab/corpus-h1/baseline-v0.1-rerun-2026-11-01/` | The existing corpus cannot show an advantage. The new corpus must make the cue and the old event share few content words, and must say how few. |
| The generator has no goal changes and no control over vocabulary overlap (about 28% of DELAYED cue tokens occur in the gold event). MEASURED | direction review 5b | A new deterministic family is required. |
| Raw-history retrieval is a strong control: six explicit-memory systems showed no consistent edge over it on LongMemEval-S and BEAM-100K. | arXiv 2610.24671 (abstract level) | Arm B must be strong raw retrieval, not a straw man. |
| Retention beat consolidation under loose budgets; consolidation helps only when the budget is tight. | arXiv 2607.17545 (abstract level) | Sweep the budget; do not test at one convenient size. |
| Concept indexes over raw text with associative retrieval already exist (HippoRAG 1 and 2, MRAgent and others). The delayed-relevance test at a fixed budget was not found in the literature reached. | [prior-art review](../07-literature/associative-memory-prior-art-2026-11.md) | The mechanism is deliberately simple and not claimed as new. The regime is the contribution. |
| In this repository, association-graph fusion lowered Recall@5 (`PMLAB-ASSOC-E3`) and second-hop expansion drifted (ledger Entry L); both seeded expansion from lexical hits. | `memory/CURRENT_STATE.md`; ledger Entry L | Seed activation from the cue and the goal only, cap the hops, and log every association so false ones can be counted. |
| Raw text beat lossy extraction (ledger Entry H, arXiv 2601.00821). | ledger; README | Traces must *point back* to the raw archive; they never replace it. |

## 3. Design

**Corpus (new, deterministic, no model).** A new family `GOALSHIFT` added to the history-family generator (a pure addition to `FAMILIES`; existing instances are not renumbered). One scenario holds about 150 experiences over 30 simulated days and 3 goal phases. In each phase a few early, low-salience experiences are *delayed-relevance targets*: they become relevant only after a later goal change, and the cue names the new goal in different words. Per probe the generator records the **content-word overlap** between cue and gold event and sets it at three levels (M0 about 40% as in corpus H1, M1 about 15%, M2 about 0 after stop-word removal). Each cue also gets at least two **decoys**: events that share a concept with the cue but are irrelevant, so a false association is measurable. Scenarios are generated from seeds: development seeds 0-4, test seeds 100-119 (20 scenarios, 12 delayed probes each, 240 paired probes), the test seeds frozen with `scripts/sealed_split.py` before Stage 1.

**Arms.** All arms read the same archive and fill the same budget with the shared `_fill` rule of `scripts/corpus/arms.py` (no future leakage).

| Arm | What it does | Stage |
|---|---|---|
| A | No memory: the goal and the cue only. Floor. | 1 |
| B1 | Lexical BM25 over the raw archive (existing FTS5 baseline). | 1 |
| B2 | Dense retrieval over the raw archive (local MiniLM, as in `dense-probe-v0`). | 1 |
| B3 | Recency window: newest experiences that fit. The default context window. | 1 |
| C | Summary memory. Stage 1: a deterministic extractive stand-in, flagged as weaker than a model summary. Stage 2: model summaries, pinned model. | 1, 2 |
| D | Associative trace. At ingest, up to 5 concepts per experience from an extractor that is independent of the generator's ontology (keyphrases mapped to concept clusters by a fixed local embedding threshold); trace = concept ids, day, pointer to the raw event. At retrieval, concepts of the cue and the active goal activate matching traces with one-hop spreading through concept co-occurrence, with a fixed cap; the pointed-to raw events are fetched under the budget. Every retrieval logs which concept link caused it. | 1 |
| O, S | Controls: O uses the generator's own concept labels (upper bound); S shuffles trace-to-event pointers (lower bound). | 1 |

**Budgets.** 250, 1,000 and 4,000 tokens (4,000 is the vision's starting figure), counted with one pinned tokenizer; the corpus-H1 convention of counting words is kept as a second column for comparability.

**Metrics.** Primary: *gold-in-context* for the delayed target at 1,000 tokens on M2 probes, arm D against the best baseline among B1, B2 and B3 (chosen on development seeds only). Secondary: the same at 250 and 4,000 tokens and at M0 and M1 (the dose-response: an honest trace effect should grow as overlap falls); decoy intrusion; **false-association rate** (retrieved events that the gold labels call irrelevant, split by whether a concept link caused them); tokens and wall-clock per retrieval; cost of the write-time and maintenance work, counted separately. Scoring is mechanical (gold event id in context); no judge.

**Decision rules (fixed before Stage 1).** Practical threshold: D exceeds the best baseline by at least 0.15 absolute with a paired-bootstrap 95% interval (resampling scenarios) whose lower bound is above zero. If dense B2 is within 0.05 of D, the reported conclusion is "conventional retrieval is as good here". Report O and S so a ceiling or floor effect is visible. Exploratory tier, no independent review.

## 4. Stages and gates

1. **Stage 0, construct checks on development seeds ($0).** Proceed only if: the best baseline at M2 and 1,000 tokens lies between 0.2 and 0.8 (headroom); measured cue-to-gold overlap matches the three levels; decoys exist; the reveal is identical with and without the history (the existing leakage-test pattern); O reaches at least 0.95 and S sits near chance. This is the step that found the length confound in corpus H1.
2. **Stage 1, retrieval-level run on the frozen test seeds ($0).** Model-free, local embeddings.
3. **Stage 2, answer-level run (paid, optional).** A fixed reader (`scripts/arena/fixed_reader.py`) over a sample, adding model summaries for arm C, under a separate small ledger and the existing spend-cap machinery. Only to confirm or qualify a Stage 1 result, or to see whether a null survives at the answer level.

## 5. Cost, effort and risk (INFERENCE unless stated)

- **Cost.** Stages 0 and 1: $0 (local BM25, local embeddings). Stage 2: about $1.5 to $5 for 150 experiences x 3 goals x 4 arms x 3 repeats, i.e. 1,440 reader calls at the measured $0.00046 to $0.00099 per call, plus $0.3 to $0.8 for write-time and maintenance calls; a pilot of a few cents first (measured precedent: $0.021 found five harness defects). Prices are DeepSeek's; another model costs more. The V3 campaign budget is frozen and gated on a different request, so Stage 2 needs its own authorisation.
- **Effort.** Generator family and its construction test: 1 to 2 engineer-days. Arms behind one interface, harness, statistics: 2 to 3 days. Manual audit of about 30 retrieved associations for the false-association label: about 2 hours. No human review of answers (mechanical scoring). These are estimates.
- **Risks and mitigations.** *Generator artefact*: a templated corpus measures the generator. Mitigate with the independent extractor, the oracle and shuffled controls, the overlap dose-response, and a follow-up on real text (the repository's own paper catalogue as a reading log) before any claim beyond synthetic data. *Circularity*: never reuse the generator's ontology inside arm D. *Headroom*: Stage 0 can stop the study cheaply. *Strong baseline*: B2 may simply win; that is a result. *Scope creep*: dynamic importance (V-H2), transfer and persistence are explicitly not in this study. *Cost creep*: Stage 2 is separate and capped.

## 6. Doctrine check and decisions needed

Against the [operating doctrine](../00-project/operating-doctrine.md): (1) the answer is partly known, so the labelled contribution is the regime, not the mechanism; (2) falsification value is high, since a null removes a plausible direction; (3) Stages 0 and 1 are tier E (hours, model-free); (4) the new family and the arm interface could also serve blocked experiments, which is a decision, not a claim. The doctrine pauses new preregistrations until the unexecuted drafts are triaged and limits designed-not-executed experiments per track; this document is a proposal, not a preregistration.

Decisions for the owner: (a) triage the unexecuted preregistrations first, or grant an explicit exception for this study; (b) authorise a separate small ledger for Stage 2, or stop after Stage 1; (c) whether the first family should also aim to unblock the existing blocked-corpus experiments; (d) accept arm D as *one mechanism under test*, not an architecture, which is what the doctrine requires.

## 7. What would change the plan

Stage 0 fails the headroom check (redesign the corpus, not the arms); the tokenizer choice moves results (report both); B2 matches D (stop, publish the null, and only then consider whether dynamic importance is worth testing); a Stage 1 effect appears only at M0 (it is a lexical-overlap effect, not association); new prior art shows the regime is already measured (cite it and re-scope).
