# Extraction Completeness Verification Pass — Fresh Replication v2 ("Mechanism J", GAP-001)

Preregistration: `PM-20260824-df787f9d`. v1 result: `EXPLORATORY_SUPPORTED` (Ledger Entry O). **Verdict: `MECHANISM_J_REPLICATION_FAILED` on the replication gate.** Entry O remains `EXPLORATORY_SUPPORTED`, not elevated to `REPLICATED_VALIDATED_TRANSPLANT`.

## Why this test

v1 (n=6, reduced from a preregistered 8 by a cost-cap interruption) found 1 genuine, transcript-traceable repair (a power-bank fact bundled inside an unrelated travel-organizing frame, split out and used correctly by the reader) and 0 regressions. Per this project's standing lifecycle (matching `RAW_PROVENANCE`'s own exploratory-to-validated path, Ledger Entry H), the mechanism needed a fresh, gold-blind replication before elevation. This run applied both operational fixes learned from v1 proactively — a cap sized from v1's own measured per-unit cost, and the brotli/httpx2 decoder fix applied from the start — and completed cleanly, 8/8 units, no interruption, no decoder errors.

## Results

| unit | type | BASE | +J |
|---|---|---|---|
| `25e5aa4f` | single-session-user | OK | OK |
| `2318644b` | multi-session | OK | OK |
| `0a34ad58` | single-session-preference | WRONG | WRONG |
| `27016adc` | multi-session | OK | OK |
| `5e1b23de` | temporal-reasoning | WRONG | WRONG |
| `2133c1b5` | knowledge-update | WRONG | WRONG |
| `1cea1afa` | knowledge-update | OK | OK |
| `1d4da289` | single-session-assistant | WRONG | WRONG |

**0 net repairs, 0 regressions** — `+J` is judgment-identical to `BASE` on all 8 units, despite the mechanism visibly firing (context differs between arms) on every one.

## Archaeology — why the 4 `BASE`-wrong units didn't repair

**`0a34ad58`** (Tokyo transit tips) — `BASE` and `+J` answers are byte-identical. `+J`'s context churn (different travel-related filler swapped in/out) never touches the actual gap (the user's Suica card / TripIt app facts the gold rubric needs) — pure irrelevant churn, no effect.

**`5e1b23de`** (photography-workshop, months-ago) — both arms answer "cannot be determined," identical. `+J` does surface photography-workshop facts, but the underlying date ("today," session-relative) is never resolved to an absolute value in either arm — a **temporal-representation-loss** case (absence subtype 3), structurally outside this mechanism's scope (it splits bundled facts; it does not resolve dates).

**`2133c1b5`** (Harajuku apartment duration, knowledge-update) — both arms confidently answer "one month" (gold: 3 months) — identical, confidently wrong. Both arms retain the same stale value; the completeness-check pass operates on one session's newly extracted facts, before Mem0's own cross-session ADD/UPDATE/DELETE reconciliation runs — a **knowledge-update/supersession** issue (the domain of the already-`DROP`ped `CURRENT_STATE_OVER_HISTORY`, Ledger Entries F/G), not a within-session bundling issue this mechanism could ever touch.

**`1d4da289`** (two-factor authentication methods, single-session-assistant) — both arms correctly (for the wrong reason) decline: "cannot recall/determine, don't have that detail." Gold requires content the *assistant* stated (biometric/OTP examples); `as_records()` drops all assistant-role turns before any extraction call ever sees them (**assistant-turn-scoping-loss**, absence subtype 4, per the project's own recorded finding, `PM-20260824-169683b7` / `GAP-004`). No mechanism operating on Mem0's stored content — this one included — can recover content that was never given to Mem0 to begin with. This is now the **5th** independently-observed `single-session-assistant` failure with this exact root cause.

## Classification

Not a negative result for the mechanism's own correctness (0 regressions, and the calibration + v1's own genuine repair already established the split-detection logic works when its actual precondition is met) — a **regime-rarity** result. Across v1 and v2 combined (n=14 fresh gold-blind units), exactly 1 unit showed the specific precondition this mechanism targets (a bundled enumeration whose split content the question actually needs) — roughly 1/14 (~7%). The other observed failures in both samples spread across three *different* absence subtypes (temporal-representation-loss, knowledge-update/supersession, assistant-turn-scoping-loss) that this mechanism was never designed to address and correctly left untouched, with zero collateral harm.

## Verdict

**`MECHANISM_J_REPLICATION_FAILED`** on the preregistered gate (0 net genuine repairs on this draw, required ≥1). Ledger Entry O remains `EXPLORATORY_SUPPORTED` — **not** elevated to `REPLICATED_VALIDATED_TRANSPLANT`, and not dropped either (0 regressions across both samples, 14 units total, is itself a meaningful safety signal). This does **not** unlock the interaction test with `RAW_PROVENANCE` (Entry H) — AAMR remains at 1 validated mechanism project-wide.

## Cost

$1.338754 (8 units, dual BASE/+J bank ingest, no cap interruption, no decoder errors — both operational issues from v1 fixed proactively and did not recur).
