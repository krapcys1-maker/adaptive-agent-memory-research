# AAMR-K1: scientific audit by an AI auditor (Fable 5.2), 2026-11-14

**Status: an AI audit, written after the results were known. Not a human review and not independent confirmation. Everything outside its section 2
is exploratory by the auditor's own statement.** It is kept apart from the mechanical record of the experiment
([`data/lab/aamr-k1/`](../../../../data/lab/aamr-k1/README.md)): that directory holds the code, stimuli, outcomes and the generated report; this one holds an interpretation of them.
The report is in **Polish**, as the auditor wrote it. The auditor worked read-only on the frozen K1 data, called no model and no paid API, and did not open the
sealed pilot. The numbers below are the auditor's, copied from the report; they were **not re-derived here** (the audit's scripts need the raw run, which is private).

## What the audit says (section numbers of the report)

1. **Verdict on credibility (section 1).** K1 is credible as a measurement and correctly read in its main part: the three contrasts, their 98.33% intervals and the states were
   re-derived from the raw data to the digit (M - P +2.70 [-5.97; 11.37] V4, M - X +4.05 [-4.35; 12.46] V4, M - S -0.23 [-8.14; 7.69] V5, section 2.1) and the analysis follows the frozen
   protocol v1.0.1 (section 2.2). The report's main conclusion is justified: no contrast detected an effect, and M - P and M - X exclude neither 0 nor 10 pp.
2. **Three reservations to the generated report (section 1).**
   - "M - S excludes the whole historical 8.1 pp" is formally right but brittle: the upper bound is 7.69 pp against 8.108; it widens to 9.5 pp with the detected dependence through shared traces, to
     13.1 pp after the length correction and to 14.3 pp on the 88 test tasks. It should not be quoted as a finding.
   - "A difference in block length may explain this result" has no support in the data: the LEN flag came only from the widening of the interval after regression, not from a dependence of the outcome on length (section 2.4).
   - The report is incomplete against section 11 of the protocol (the arm x block table in six strata, WR1 to WR3 and the imbalance statistics are only in `results.json`); this does not change any state.
3. **The main finding goes beyond the report (section 3, exploratory).** A mean effect near zero does not mean that memory is inert: at the level of single tasks the memory block changes the outcome strongly and repeatably in both
   directions, and the changes cancel (standard deviation of the true per-task effect M - N about 38 pp, permutation p = 0.0002; even neutral prose changes outcomes on particular tasks, but real memory most).
4. **Three categories of finding (section 7).**
   - *Confirmed by the data:* the numbers, intervals and states reproduce; no contrast detected an effect; the drift mismatch in block A comes from non-determinism with identical requests on the same stack, not from a version change; the frozen artifacts were not changed.
   - *Exploratory hypotheses (need confirmation):* heterogeneity of the memory effect; contamination by foreign values and functions as a cause of losses; the bottleneck is the form and timing of the content and the task state, not retrieval accuracy; memory helps mainly on the first turn; a domain pattern (file system gains even from random traces, Vehicle Control from selection, travel loses); the historical +8.1 pp is inflated by thresholding, noise and selection.
   - *Not yet verified:* the causal link between copying and losing a task; whether abstraction of traces keeps the gains; the existence of a mean effect of 3 to 8 pp; transfer to another pool, model or presentation; the source of non-determinism at temperature 0; the value of memory with dynamic links; NIGHT-1's raw data was not recomputed.
5. **Proposals (section 6.5)** of next experiments are for the owner's decision; nothing was implemented.

## Limits you should know

- The auditor is an AI model of the same project; the executor was another model. There was no human reviewer, and this is not the independence the [independence ladder](../../../00-project/independence-ladder.md) asks for above its lowest rungs.
- The exploratory analyses were added after the results were seen and are, unless the report says otherwise, not corrected for multiple comparisons.
- The auditor recorded two deviations itself (section 8): a helper session ran one `git log` and one `git status` in two worktrees (no working file changed); and a first, approximate reproduction of one statistic differed from the report until redone exactly, an error on the auditor's side.
- A manual, blinded assessment of 24 failed turns (without arm labels and without the memory block) is part of the audit's evidence in section 4. **Its material (the cases, which quote benchmark text, and the key) is withheld**, so that assessment cannot be re-checked from this repository.
- The scripts under `scripts/` read the raw K1 sessions (326 MB, private) and a copy of NIGHT-2's raw responses; they cannot be rerun from a clean clone. Machine-local paths in the report and scripts were replaced by `[machine-local path omitted]` (listed in `PUBLISHED_FILES.json`, with before and after hashes).

## Files

| File | What it is |
|---|---|
| [RAPORT_AUDYT_NAUKOWY_K1.md](RAPORT_AUDYT_NAUKOWY_K1.md) | the audit report (Polish), with an integration note at the end |
| `scripts/` | the auditor's analysis scripts (`common.py`, `mech1.py`, `mech2.py`, `mech_build.py`, `len_exact.py`, `final_checks.py`) |
| `PUBLISHED_FILES.json` | every published file with its source, SHA-256 and edits, and the list of what is withheld (the blinded cases, the key, the script that made them, the raw sessions) |
