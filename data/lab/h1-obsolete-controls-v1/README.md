# H1 OBSOLETE controls v1 — completed local diagnostic

**The stale failure persists in the original pack; reduced oracle evidence works in these controls. This is not a repaired end-to-end memory result.** Follows #108 and the [plan](PLAN.md) frozen at `8504591`. Preparation/code committed at `b353695`; all raw outputs frozen at `1097e23` before the separate scorer read expected answer fragments.

| Condition | Cases | H1 answered | Stale leaked |
| --- | ---: | ---: | ---: |
| Repeat original v5 evidence pack | 24 | 23 | 1 |
| Oracle supporting source only | 24 | 24 | 0 |
| Obsolete source then correction | 24 | 24 | 0 |
| Correction then obsolete source | 24 | 24 | 0 |

Every public OBSOLETE case is included: 12 development and 12 validation-B, regardless of earlier outcome. Source IDs/family membership are intentionally supplied by oracle for the diagnostic; this is not automatic label-blind retrieval. `answered` is unchanged required-fragment/no-abstention scoring, with forbidden-marker `leaked` separate. No independent semantic judge or confirmation.

Validation `Q000043` fails again only under its original three-note pack: one later user correction plus two older notes. Both two-note orders and the oracle-only control answer correctly. Thus this run does not show that simply reversing order solves the original failure. Removing one older note, repetition, note specificity and total context differ; redundant stale evidence is a hypothesis to test, not a proven cause. Other original three-note packs passed (7 original packs had 3 notes, 7 had 2, 10 had 1).

There are 82 unique message packets among 96 declared primary calls. Identical packets are intentional repeated measurements, not hidden answer retries. Seed/model/answer schema and role instructions match v5; arm execution order rotates by case index as preregistered. All 3 unrelated controls passed, no JSON parse failures, model digest unchanged and the owned model was unloaded. See [scores](scores.json), [integrity replay](artifact-audit.json), [preparation](preparation.json) and [raw freeze](raw-freeze.json).

Actual phase: **99 local generations, 0 API**, 101.703 seconds reported phase elapsed time. Same H1 ledger grew from 2677 to 2776 unique attempts, below the existing 2800 cap, with its original byte prefix intact. API ledger unchanged at 463 attempts/$1.852 permanently reserved; no new paid budget. PR105 cumulative generations become 3733 = 3270 local + 463 Flash, including prior failed attempts and controls, not 3733 independent questions. Global ledgers were never reset.

The artifact replay reconstructs all 96 primary source packets/roles/clocks and recorded model requests, checks original input/gold hashes, source execution hashes and cumulative ledgers. Zero integrity failures is provenance evidence authored by the same implementing agent. Raw requests/final responses remain private local artifacts. The public audit records actual message bytes/native token counters; oracle-only uses less context, so no equal-total-input gain is claimed.

## Decision

The reader can answer all 24 cases from the supporting source in this one fixed-seed diagnostic. The surviving original-pack failure supports investigating evidence interference/composition; it does not establish a sole cause or a general intervention. Keep #108 open and preserve the original v5 score. Next test a preregistered source-repetition/neutral-volume contrast across the whole family before adopting a packing rule; any proposed method then needs every H1 family and fresh data. See the [candidate test](../../../docs/11-research-laboratory/evidence-redundancy-next-test-2026-11-05.md).
