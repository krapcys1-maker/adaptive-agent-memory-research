# AAM-LifeSim: registration of X0 (instrument gate) and X1 (value of a feeling-like signal at the retention gate)

Status: REGISTERED BEFORE ANY RESULT RUN. Worlds have been built on development seeds (0 to 999) while the code was written and its tests run; those runs calibrate and debug the instrument and are not results. No gate has been evaluated on the confirmation seeds (5000 to 5099) and X1 has not been run on the sealed test seeds. `config.json` (every assumed parameter, the seed epochs, the threshold rules, the arm lists, a digest block) is exported from the code and committed before the first result run; the digests of the scripts are recorded there. Amendments are appended at the end with the reason and the commit. Both experiments use no model and cost 0 USD.

Design source: `docs/11-research-laboratory/lifesim-design-panel-digest-2026-11-01.md` (three designers and an editor; a design, not a result) and `docs/11-research-laboratory/memory-benchmark-spec-v0.md`. Every numeric parameter of the generator is an ASSUMPTION, lives in the config, and is swept by plus or minus 50% where a conclusion depends on it; a conclusion that flips is labelled parameter-dependent.

## What the instrument is

One deterministic, structure-first life generator: bitemporal facts, situations with appraisal features and an arousal variable, observation specifications, THEN text. Gold answers come from two code paths (`gold_fast` in the generator, `gold_slow` as a naive scan of the raw specifications) that must agree on every query. Scoring is closed-vocabulary and deterministic; no model judge for facts. One random stream per event, so deleting or swapping an event changes nothing else.

The "feeling-like" signal is a generator variable and a measurement channel, nothing more: arousal A, valence V and a noisy heartbeat-like channel H = g(A mixed with nuisance activity) + noise, with a reliability grid corr(H, A) in {0, 0.3, 0.5, 0.7, 0.9, 1.0} (primary 0.7). Nothing here claims experience for any system. The coupling between arousal and later need is a dial that includes zero and negative values, defined on the realised enrichment E_0.10 of needed facts among the top 10% most arousing lines (grid 0.2, 0.5, 1, 2, 4), because defining it on a nominal correlation was shown on a toy to be misleading.

## Seeds, sealing, looks

Development seeds 0 to 999 (calibration; never reused for a result). Confirmation seeds 5000 to 5099 (X0 evaluated once). Test epochs E1 and E2 sealed with `scripts/sealed_split.py` and a look ledger kept outside the output folders; a version bump consumes an epoch. X1 runs once on the revealed E1 challenge half. A failed version consumes the confirmation epoch; failures are fixed on development seeds only.

## Threshold rules (fixed before any number, from development headroom)

A cell is LIVE if its headroom H_cell = GO - max(GU, GR, GS, GN, GM) is at least 0.20 on development seeds, otherwise it is void. theta = max(0.05, 0.25 H_cell); delta = min(0.04, 0.10 H_cell); SUPPORTED = point estimate at least theta and Holm lower bound above theta / 2; EQUIVALENT = 90% interval inside plus or minus delta; the feasibility margin is 1.5 theta. Worlds per retrieval-level cell: the smallest of {24, 32, 40, 60, 80} with equivalence power at least 0.80 at SD_plan = 1.25 SD_dev, one pre-declared extension of +40 worlds per cell; default 40. Uncertainty: 10,000-draw cluster bootstrap over worlds; Holm over at most three primary hypotheses per experiment.

## X0: instrument gate and free grid (Tier E, no model)

Question. Before any hypothesis: does the generator measure memory and nothing else (floors, ceilings, tells, support, determinism, scorer accuracy), and do the gates fire on planted artefacts?

Arms. Programmatic: `gold_fast`, `gold_slow`, S-SCRAMBLE (solver on another seed's log). Evidence-level ladder with no reader: B0a, B0h, B1, random, B2, B2t, oracle_text, oracle_struct, oracle_store. Gate grid on development seeds 5 to 59: R in {0.10, 0.25} x coupling E_0.10 in {0.2, 0.5, 1, 2, 4} x mu in {0, 0.3} x policies {ALL, GU, GR, GN, GM, GS, GH[TRUE, SHUF_TYPE, SHUF_LIFE, TIME_SHIFT, RANDOM, CONST, INVERTED, NUISANCE_ONLY, ORACLE, LEAKY], GTN, GO} x reliability {0.3, 0.5, 0.7, 0.9, 1.0}. Gates on development seeds 0 to 4, then evaluated once on confirmation seeds 5000 to 5099. Planted-artefact fixtures: a naive verbaliser (length and affect tells), a type-hosted generator (compositional tell), a leaky-importance generator (the AAM-E0 v0.1 mistake), a shuffled-label scorer.

Controls. Positive: every gate must fire on its planted fixture (instrument only, no model); `gold_fast` = `gold_slow` = a second independently coded solver. Negative: S-SCRAMBLE and blind heuristics at chance; the ablated world falls to chance for every non-oracle arm. Mutation test: at least 20 registered single-change mutants of generator, scorer, gates and arms (AAM-E0: 15 of 24 survived).

Readings before numbers. Primary metric: the number of gates met; practical threshold: all of them. PASS iff all hold.
- G-DET: world digests byte-identical across two builds and three reruns; the structure digest is invariant to verbaliser, coupling cell, channel arm and gate policy.
- G-SOLVE: `gold_slow` = `gold_fast` on 100% of queries; an independently coded second solver agrees on 100% of retained items (items with two or more consistent answers are dropped, at most 15% per family).
- G-SCORE: answering from structure scores 1.000 including abstention; the scrambled-world solver is at most chance + 0.02 per family; an adversarial scorer set (100 items on day 1, 500 before the confirmation seeds, labels written before the scorer) agrees 100%.
- G-HOST: chi-square p at least 0.2 (fact type x arousal tercile). G-SUPPORT: shortfall at most 2% at the null and at most 5% elsewhere, else the cell is void.
- G-ARO: null cell E_0.10 and E_0.25 in [0.8, 1.2], AUC_ev in [0.45, 0.55], |d| at most 0.10; other cells E_0.10 within plus or minus 15% of target and monotone.
- G-LEN: AUC(length: evidence vs other) in [0.45, 0.55] and |corr(length, A)| at most 0.05. G-AFF: |Spearman(A, affect phrases)| at most 0.10 under A1, zero affect words under A0 (scan). G-POS: target-clause and answer-token position chi-square p at least 0.2.
- G-TELL: world-grouped cross-validated AUC from surface features (length, template id, rare-token share, digit count, line position, day offset, hashed uni- and bigrams; L2 logistic regression via scipy) at most 0.55 as a point and at most 0.60 as a one-sided 95% upper bound, for evidence-vs-other and top-arousal-tercile-vs-rest, with at least 300 positives and 3,000 negatives.
- G-BLIND: B0a and B0h at most chance + 0.05 on at least 90% of memory-dependent items (Wilson 95% upper bound at most chance + 0.08 for open slots, + 0.10 for multiple choice, n at least 200 per family), else widen the answer space and regenerate.
- G-ORACLE: `oracle_struct` = 1.000 and `oracle_text` evidence-complete = 1.000 for every family. G-DEPTH: at least 40 retained items per scored family. G-FEAS: every cell H_cell at least 0.20. G-POWER: SD_world measured and n sized by the rule. G-LEAK: canaries absent and the reversed-order difference at most 0.02 in complete@C. G-PLANT: each gate fires on its fixture. G-MUT: at least 90% of mutants caught. G-STAT: the A/A false-positive rate of the 95% interval in [0.03, 0.08] over 1,000 split-half pseudo-contrasts; `results.json` byte-identical on rerun.

PASS unlocks X1. Cost 0 USD, about 1 to 2 CPU-hours on 20 cores.

## X1: value of a feeling-like signal at the retention gate (Tier C by corpus, no model)

Question. At the retrieval level, when does a noisy feeling-like signal used as a retention weight raise the share of needed evidence that survives a budget and reaches the context, beyond merely having a feature, beyond novelty, surprise and mention counts, and when does it hurt?

Arms. Stores S-LEX (BM25 + date window) and S-HYB (BM25 + MiniLM by reciprocal rank fusion) over the retained set, C = 1000 words; R in {0.10, 0.25} plus an R = 1.0 identity check; online retention K(t) = floor(R x words seen). Policies: ALL, GU, GR, GN, GM, GS, GH[TRUE, SHUF_TYPE, SHUF_LIFE, TIME_SHIFT, RANDOM, CONST, INVERTED, NUISANCE_ONLY, ORACLE, LEAKY], GTN, GO; GA exploratory. Cells (coupling E_0.10 / rehearsal / mu): C+ (4 / 0.3 / 0.2), C-half (2 / 0.3 / 0.2, dose, exploratory), C0 (1 / 0.3 / 0), C0r (1 / 0 / 0), C- (0.3 / 0 / 0.6). Reliability 0.7 in every cell; the ladder 0, 0.3, 0.5, 0.9, 1.0 in C+ and C-. Sub-grid pi in {0.1, 0.5} x periphery goal-relevant g in {0, 1} on the first 20 worlds of C+ and C0r (the narrowing cost). L2 size, 40 worlds per cell, affect words A0, one pre-declared extension of +40 worlds per cell.

Controls. Positive: the ORACLE channel and LEAKY in every cell, GO as the feasibility bound. Negative: C0r (nothing couples arousal to anything); R = 1.0 byte-identity; the five surrogates mutually equivalent; NUISANCE_ONLY; A/A pseudo-contrasts; the X0 planted-artefact fixtures re-run; rehearsal off in the signal reading with GM always present; the development-seed feasibility gate first.

Readings before numbers. Primary metric: SIGNAL = GH[TRUE] - GH[SHUF_TYPE] in complete@C at C+, R = 0.10, reliability 0.7, in both stores. Practical threshold theta = max(0.05, 0.25 H_dev). Feasibility: H_cell >= 0.20 per cell on development seeds, else the cell is void.
- Positive controls (must fire, else INSTRUMENT INSENSITIVE and no statement about H is admissible): PC1 ORACLE channel: GU at least 0.20 with lower bound at least 0.15 in every live cell; PC2 LEAKY at least GU + 0.75 (ORACLE - GU).
- Negative controls (must not fire, else INSTRUMENT BIASED and stop): NC1 SIGNAL EQUIVALENT within plus or minus delta in C0r and C0; NC2 byte-identical retained sets at R = 1.0; NC3 SHUF_TYPE, SHUF_LIFE, TIME_SHIFT, RANDOM, CONST mutually equivalent and none exceeds GU by an effect; NC4 NUISANCE_ONLY - CONST at most delta; NC5 A/A rate in [0.03, 0.08].
- Hypotheses (Holm family of 3; each must hold in both stores): H1 information value: at C+, SIGNAL >= theta with Holm lower bound > theta / 2 AND GH[TRUE] - max(GN, GM, GS) >= theta / 2. H2 sign follows coupling: at C-, GH[TRUE] - GU <= -delta with upper bound < 0 AND GH[INVERTED] - GH[TRUE] >= theta / 2. H3 dose and surrogate equivalence at C+: SIGNAL falls along the reliability ladder (Jonckheere-Terpstra one-sided p < 0.01) and GH[RANDOM] is EQUIVALENT to GH[SHUF_TYPE].
- Reported without a direction: C0 vs C0r (rehearsal route), C-half dose, R = 0.25, the pi x g sub-grid (loss expected for narrowing at pi = 0.5, g = 0), the mu regime (quiet-critical loss), GA, GL, GTN, collateral loss, the break-even E*.

Verdicts then decisions. Controls pass and H1 to H3 hold = SUPPORTED, decision: advance to replication only; in this generator the signal's value equals its information content with the right sign; no claim for live agents; the deliverable is the response curve and E*. Controls pass and H1 fails = NOT SUPPORTED (a valid null), decision: reject a feeling-like retention weight on this backbone where novelty, surprise or mention counts suffice. H1 holds and H2 fails: restrict, audit before any claim. H3 fails: inconclusive, suspect a shortcut. A positive control fails: INSTRUMENT INSENSITIVE, new version, new seeds. A negative control fires: INSTRUMENT BIASED, stop, new version, new seeds. INDETERMINATE: the one extension batch. The decision line is emitted by code (`analyse_lifesim.readings`) and copied verbatim. A pass at C+ is by construction a calibration of the instrument, never evidence for the live account.

Cost 0 USD; 200 worlds x 2 stores at L2; about 1 to 2 CPU-hours on 20 cores (dense embeddings dominate).

## Not claimed

The real coupling between arousal and later need in the live account is unknown (no per-note engagement signal, AAM-F1); LifeSim reports a response curve and a break-even point and makes no claim about it. The mappings from appraisal to arousal define what the benchmark's signal is, not what a person's is. Synthetic template text is a proxy for natural language. Human-like phenomena are diagnostics and planted checks, never the answer key. Toy numbers quoted in the design digest justify design choices and nothing more.

## Amendments

(none yet)
