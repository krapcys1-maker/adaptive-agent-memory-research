# Autonomous Memory Mechanism Campaign v1 — Final Report

Limited Autonomous Experimental Research campaign, run under an explicit contract (commit `96336ea` onward). **Stopped at STOP condition B: 3 consecutive mechanism families (D, E, F) failed to produce a replicated positive signal.** All work committed through `163bb9c`.

## 1. Total spend

**$2.143325 of the $10.00 hard cap.** $7.856675 unspent, well above the $1.50 reserve. The stop was evidence-driven, not budget-driven — every stage stayed inside its own preregistered cap, and the campaign as a whole used barely a fifth of what was authorized.

## 2. Experiments run

7 paid runs across 5 mechanisms, all preregistered before their first paid call:

| mechanism | runs | spend |
|---|---|---|
| B — `CURRENT_STATE_OVER_HISTORY` | exploratory + 1 repair retest | $0.064069 |
| C — `RAW_PROVENANCE` | fresh replication (8 units, 3 arms) | $0.575419 |
| D — `RETRIEVAL_CONFIDENCE_SIGNAL` | exploratory (interrupted) + continuation | $0.347161 |
| E — `SAME_CATEGORY_ENTITY_ENUMERATION` | exploratory (8 units) | $0.574796 |
| F — `RETRIEVAL_RANK_ANNOTATION` | exploratory (8 units) | $0.581880 |

Plus a large volume of $0 work: zero-cost archaeology (per-probe decomposition on B, D), unit-test suites for every mechanism's deterministic transform (11+8+8+6 = 33 tests, all passing), two live bug fixes caught by those tests before any paid call, one live infrastructure bug caught mid-run (D's ingest-loop cap handling) and fixed without wasting the already-completed work, and one brief web search before designing Mechanism F.

## 3. Mechanisms considered

Selected and tested: **B** (state/supersession), **C** (raw provenance), **D** (retrieval confidence margin), **E** (harmful-sibling entity enumeration), **F** (retrieval rank annotation). Considered and not tested: a generic/gold-adjacent harmful-sibling design (rejected pre-B in favor of B's narrower state-key template approach); retrieval-sufficiency/abstention-strengthening (rejected — conflicts with the frozen-reader-prompt invariant held across every experiment in this project); consolidation, procedural memory, learned admission/forgetting, multi-agent concurrency, graph-structure, memory poisoning (rejected as out-of-scope, too invasive for a first transplant, or not applicable to this arena's single-agent flat-store architecture).

## 4. Mechanisms dropped

**B, D, E, F** — four of five tested mechanisms, for three distinct reasons: `B` — host precondition never materialized (Mem0's own write-time consolidation absorbed the target failure mode before the read-side mechanism could act); `D`, `E` — regime mismatch (narrow, threshold- or template-gated preconditions that a modest gold-blind sample failed to exercise, in `E`'s case not even once); `F` — genuinely exercised on every unit but net negative (0 repairs, 1 regression).

## 5. Exploratory positives

None of the five mechanisms cleared a clean `EXPLORATORY_SUPPORTED` gate on its first paid test in this campaign. `C`'s antecedent (`E3`, run in an earlier phase of this project, not part of this campaign's spend) scored `CONDITIONAL` — 1 repair, 0 regressions, too thin to trust alone — which is exactly what this campaign's fresh-replication step exists to resolve.

## 6. Replication results

**One successful replication: `C` (`RAW_PROVENANCE`).** Fresh, independently-selected, gold-blind 8-unit sample reproduced `E3`'s shape almost exactly (compact 5/8 vs. 5/9, compact+raw 6/8 vs. 6/9, raw-only 4/8 vs. 4/9), via a *different* repair mechanism (absence, not `E3`'s competing-facts case) — broadening rather than narrowing the evidence. Zero regressions across both runs (17 combined observable units).

## 7. Validated transplants

**`RAW_PROVENANCE` (Mechanism C) — `REPLICATED_VALIDATED_TRANSPLANT`.** The only mechanism in this entire project (not just this campaign) to reach that status. Calibrated, not overclaimed: small effect size (~1 repair per 8–9 units), single-hop-limited (a named counterexample, `078150f1`, shows the boundary directly).

## 8. Failure modes discovered

- **Host write-time consolidation absorbing a read-side mechanism's precondition** (B): Mem0 1.0.6's own ADD/UPDATE/DELETE reconciliation fully merges sequential same-key state updates into one surviving memory before any read-side state/supersession mechanism can see the conflict.
- **Silent `metadata.timestamp` overwrite on an unrelated write** (B): an existing memory's stored timestamp can be rewritten by a later, textually-unrelated `add()` call even when that memory's own text is untouched — a new risk for anything (including the already-paused `TEMPORAL_ANCHOR_AT_CONTEXT`) that trusts `evidence_times`.
- **Regime mismatch for narrow/templated preconditions** (D, E): a mechanism gated on a specific structural pattern (score-margin ambiguity, same-category entity plurality) can go untested for many units in a row even at n=8, unlike mechanisms with universal preconditions.
- **Judge-penalized epistemic caution, confirmed a third time** (F): context annotations can induce more hedging/rambling reader behavior; a binary judge penalizes the hedge even when substantive content is comparable to `BASE`. Already seen in `E1`'s `+SRC` regressions and Stage 2's `031748ae`/`0977f2af`; now a cross-mechanism pattern, not an isolated one.

## 9. Regime map (mechanism × regime, this campaign + carried-forward ledger entries)

| Mechanism | Regime | Effect |
|---|---|---|
| `RAW_PROVENANCE` (C, Entry H) | compact-context absence/under-detail, single-hop-reachable | **positive**, replicated |
| `RAW_PROVENANCE` (C, Entry H) | single-hop-unreachable content (`078150f1`) | no effect (named limitation) |
| `CURRENT_STATE_OVER_HISTORY` (B, Entry G) | ≥2 surviving same-key items, distinct timestamps | **untested** — precondition never arose |
| `RETRIEVAL_CONFIDENCE_SIGNAL` (D, Entry I) | gold present but not top-ranked, genuine score ambiguity | **untested** — sample lacked the shape |
| `SAME_CATEGORY_ENTITY_ENUMERATION` (E, Entry J) | ≥2 same-category entities co-retrieved at `compact` breadth | **untested** — never observed; the one real historical case needed wide breadth |
| `RETRIEVAL_RANK_ANNOTATION` (F, Entry K) | any retrieval (universal) | **negative** (mild), on preference-rubric questions specifically in this sample |
| (carried forward) `TEMPORAL_ANCHOR_AT_CONTEXT` | bounded lookup, event date available | positive, but not fresh-replicated |
| (carried forward) `TEMPORAL_ANCHOR_AT_CONTEXT` | many-item filter/count, session≠event time | negative |

## 10. Negative transfers

`F`'s regression (this campaign) and the carried-forward `+SRC`/Stage-2 regressions are all instances of the same underlying risk: added structure can shift reader behavior toward hedging, which costs points under a strict binary judge even when it reflects genuine, defensible uncertainty. No mechanism this campaign showed a *content*-level negative transfer (nothing was ever made factually worse) — every observed regression was judge/phrasing-mediated.

## 11. Interaction results

**None — never unlocked.** The interaction test (`BASE`/`+A`/`+B`/`+A+B`) requires two independently `REPLICATED_VALIDATED_TRANSPLANT` mechanisms; this campaign produced exactly one (`RAW_PROVENANCE`). No interaction test was attempted, per contract §6/§21.

## 12. Bugs / invalidations

Two live infrastructure bugs, both caught by this campaign's own testing discipline before or during a run, both fixed without discarding valid prior work: (1) Mechanism D's run script lacked cap-reached exception handling in its ingest loop, crashing mid-run; fixed, and the 4 already-cleanly-ingested units were recovered via a zero-re-ingest continuation. (2) Mechanism E's entity-extraction regex over-captured sentence-initial capitalized verbs; caught by 2 of 8 unit tests failing before any paid call, fixed with a stoplist, reverified against the real historical case. No result in this campaign required invalidation after being published — both bugs were caught before they could contaminate a paid result.

## 13. External evidence used

Frontier map families (state/supersession, retrieval-utilization-gap/confident-but-wrong, skill/harmful-sibling); specific papers: arXiv:2608.19652 (StateMemBench/StateMemWrapper), arXiv:2605.06527 (STALE), arXiv:2608.01619 (StateAuditor), arXiv:2606.10388 (harmful-sibling rate), arXiv:2606.22728 (zero answer dispersion); this project's own internal evidence (`PMLAB-STALE-E1`, `memory/SCHEMA.md`'s bitemporal design, roadmap F13/F17).

## 14. GitHub/paper discoveries that changed decisions

One targeted web search was performed before designing Mechanism F (after two consecutive regime-mismatch nulls). Results were dominated by further state-supersession/temporal-validity variants — a family already tested and paused in this project — and did not surface a clearly superior candidate. No GitHub repository browsing was performed. This did not change the mechanism choice, but it did confirm (rather than merely assume) that the self-generated `RETRIEVAL_RANK_ANNOTATION` candidate was reasonable given the available literature at the time of the search.

## 15. Cost per decision

7 paid stages, $2.143325 total → **≈$0.306/stage**. By outcome: the one validated mechanism cost $0.575419 (its fresh replication; design/exploratory were $0 marginal, reusing `E3`). The four dropped mechanisms cost $1.567906 combined (≈$0.392/dropped mechanism) — money well spent relative to the alternative (adopting an unvalidated mechanism, or spending on a full interaction test with an unreplicated partner).

## 16. Remaining uncertainties

- Whether `SAME_CATEGORY_ENTITY_ENUMERATION` (E) would show a real effect at wider retrieval breadth (the one confirmed real case occurred at 208 retrieved items, far more than this campaign's `compact` ~10-item operating point) — untested.
- Whether `RETRIEVAL_CONFIDENCE_SIGNAL` (D) would show a real effect on a sample specifically screened for its precondition (gold present, not top-ranked, genuine score ambiguity) — untested; the campaign's gold-blind discipline correctly refused to screen on this without risking gold-adjacency, so this remains open by design.
- Whether `CURRENT_STATE_OVER_HISTORY` (B) could ever be tested meaningfully on Mem0 1.0.6 without a harness that bypasses or observes its write-time consolidation directly — genuinely unresolved.
- Whether `RAW_PROVENANCE`'s single-hop limitation (`078150f1`-class failures) is fixable with a cheap multi-hop extension — plausible, untested, and not independent enough from `C` to count as a second validated mechanism even if it worked.
- Whether the "judge-penalized epistemic caution" pattern (now 3x) reflects a real judge-calibration problem worth fixing at the harness level (a genuinely new, cross-cutting question this campaign surfaces but does not answer).

## 17. GO / PIVOT / STOP recommendation

**STOP** (per contract, evidence-driven — met, not manufactured). This is not a recommendation to abandon the memory-mechanism research program: it reflects that the current *method* (small, gold-blind, narrow-precondition mechanism candidates, self-generated or lightly externally-checked, tested one at a time on this specific host) has now produced one real validated result and three consecutive well-characterized nulls in a row. Continuing to generate a fourth, fifth, sixth narrow candidate by the same method has a worsening expected-value profile without a change in approach.

## 18. Recommended next $1

Either: (a) a targeted, larger (~15–20 unit) test of `SAME_CATEGORY_ENTITY_ENUMERATION` at wide retrieval breadth specifically (addressing remaining uncertainty #1 directly, ~$0.90–1.00), since it has the strongest *prior* evidence (one confirmed real case) of the three DROPped mechanisms; or (b) a cheap, sharply-scoped calibration of whether `RAW_PROVENANCE`'s multi-hop extension repairs the `078150f1`-class failure specifically (~$0.30–0.50), which would strengthen the one validated mechanism further even though it wouldn't itself unlock an interaction test.

## 19. Recommended next $10

A genuinely different search strategy, not more of the same: either (a) real GitHub repository research (cloning/reading actual open-source agent-memory implementations for atomic mechanisms with empirically common, not rare, preconditions — the lesson this campaign's ledger now records explicitly), or (b) widening the arena itself (a second benchmark, or LongMemEval-V2, per the standing roadmap's own Phase-D pivot option) so that mechanisms whose preconditions are rare at n=10-scale sampling get a fairer test at n=30-50 scale, which the current $10 campaign budget could support but this particular STOP-triggered run did not reach.

## 20. Whether controller is justified

**No — nowhere close.** The controller gate (contract §22) requires ≥2 independently `REPLICATED_VALIDATED_TRANSPLANT` mechanisms with demonstrated regime variance; this campaign has exactly one. No router, bandit, or learned controller work is justified by anything produced here.

---

## Appendix: full mechanism-by-mechanism links

- Mechanism B: [`MECHANISM_B_STAGE1_RESULTS_V1.md`](MECHANISM_B_STAGE1_RESULTS_V1.md) (Ledger Entry G)
- Mechanism C: [`RAW_PROVENANCE_FRESH_REPLICATION_V1.md`](RAW_PROVENANCE_FRESH_REPLICATION_V1.md) (Ledger Entry H)
- Mechanism D: [`RETRIEVAL_CONFIDENCE_SIGNAL_V1.md`](RETRIEVAL_CONFIDENCE_SIGNAL_V1.md) (Ledger Entry I)
- Mechanism E: [`SAME_CATEGORY_ENTITY_ENUMERATION_V1.md`](SAME_CATEGORY_ENTITY_ENUMERATION_V1.md) (Ledger Entry J)
- Mechanism F: [`RETRIEVAL_RANK_ANNOTATION_V1.md`](RETRIEVAL_RANK_ANNOTATION_V1.md) (Ledger Entry K)
- Full ledger: [`MECHANISM_REGIME_EVIDENCE_LEDGER.md`](MECHANISM_REGIME_EVIDENCE_LEDGER.md) (Entries A–K)
- Campaign budget detail: `data/lab/arena/autonomous-research-budget-v1/ledger.json`
