# Mechanism B — Stage 1 Exploratory Test: Results and Closure

`MECHANISM_B_STATE_SUPERSESSION_V1` per `data/lab/arena/mechanism-b-state-supersession-v1/preregistration.json`. Original run + one permitted repair retest. **Verdict: DROP (V1 harness, this host) — mechanism logic itself was never exercised, not refuted.**

Artifacts: [`stage1-raw.json`](../../data/lab/arena/mechanism-b-state-supersession-v1/stage1-raw.json) (original, $0.022315), [`stage1-archaeology.json`](../../data/lab/arena/mechanism-b-state-supersession-v1/stage1-archaeology.json) (zero-cost diagnostic), [`stage1-repair-raw.json`](../../data/lab/arena/mechanism-b-state-supersession-v1/stage1-repair-raw.json) (repair retest, $0.041754).

## Original run (12/12 probes, $0.022315)

BASE 12/12 correct, `+B` 12/12 correct. Net repairs: 0. Zero-cost diagnostic (`memory.get_all()` reads against the persisted store — no LLM call) explained why: **8 of 9 R1/R2/R3 probes' sequential same-key state statements were fully consolidated by Mem0 1.0.6's own write-time ADD/UPDATE/DELETE reconciliation into a single surviving memory** before `CURRENT_STATE_OVER_HISTORY` ever received competing items to disambiguate. The mechanism's own logic was correct everywhere it had material: 0/3 false supersession on R4 controls, and a correct, safe tie-fallback on `SUP3` rather than guessing.

A second, independent finding surfaced in that same diagnostic: Mem0's UPDATE path can silently rewrite `metadata.timestamp` on an *existing* memory to a later, unrelated call's date even when that memory's own text is untouched (`SUP3`'s "Got engaged..." record kept its wording but had its stored timestamp overwritten to match the later "married" call). This means `evidence_times` — the sole signal both `TEMPORAL_ANCHOR_AT_CONTEXT` and `CURRENT_STATE_OVER_HISTORY` depend on — is not always a reliable record of a memory's true observation time on this Mem0 version.

## Repair hypothesis, retest, and its own failure ($0.041754)

Diagnosed cause (working hypothesis): probe turns were packed in immediate adjacency with nothing else in the store, unlike real conversations where related statements sit far apart. Repair: insert 2 fixed, template-verified-neutral filler turns between every pair of state-changing turns in the 9 affected probes (R4 unchanged). One retest, per the repair budget rule.

**Result: the hypothesis was wrong.** Stored item counts rose (3–5 per probe, vs. 1–2 before) because the *filler* turns survived — but the state-carrying facts themselves still consolidated to exactly one surviving item in every probe. Mem0's own "existing memories" comparison at `add()` time is a semantic/embedding search, not a proximity or recency check, so spacing related statements apart in the conversation did not stop it from finding and merging them. **Across both runs — 24 probe-executions total — the mechanism's core action (`current_history_split`, grouping ≥2 same-key items into Current/History) fired zero times.**

One apparent flip (`RET3_DIET`: BASE wrong → `+B` correct) is **not evidence the mechanism worked** — its trace shows `single_item_passthrough`, not a split; the only difference between arms was that the render transform's passthrough ordering happened to move the one surviving relevant fact later in the context (after the filler items), which is a token-order/salience side effect of the implementation, not the intended Current/History logic. Recorded honestly, not counted as a repair. A second data point, `RET1_JOB`, went BASE wrong / `+B` wrong — Mem0's write-time consolidation kept the *middle* of three sequential facts ("...Globex"), not the most recent one ("Rejoined Acme Corp"), showing the host's own implicit consolidation is not even reliably recency-correct.

## Verdict

**`DROP` — for this V1 harness on this host, not a refutation of `CURRENT_STATE_OVER_HISTORY`'s logic.** The mechanism's design (state-key detection, tie-safe no-guess fallback, non-collapse of genuinely distinct entities) was verified correct in every case it had material to act on — it simply never received that material, in either the original or the repaired run, because Mem0 1.0.6 itself absorbs sequential same-key state changes at write time before any read-side mechanism can see the conflict. Per the one-retest rule and the circuit breaker (no repeated failed paid actions on the same fingerprint), no further repair attempt is made.

This reframes what a valid test of any read-side state/supersession mechanism on Mem0 1.0.6 would require: either probes built from real, far-separated multi-session LongMemEval conversations (genuinely unknown whether that changes Mem0's own consolidation behavior — an open question, not assumed), or a harness that bypasses/observes Mem0's update-decision step directly rather than treating it as an opaque precondition. Neither is undertaken here — per the campaign contract, Mechanism B is closed and the campaign proceeds to selecting an independent second candidate.

## What is NOT concluded

Not concluded: "state/supersession mechanisms don't work," "Mem0 already solves this so no mechanism is needed" (its own consolidation is inconsistent and not even reliably recency-correct, per `RET1_JOB`), or "`CURRENT_STATE_OVER_HISTORY` is a bad design" (untested, not refuted). The honest status is: **mechanism-level evidence is absent, not negative.**
