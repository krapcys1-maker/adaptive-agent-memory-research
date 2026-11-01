# `SEMANTIC_ENTROPY_SUFFICIENCY_GATE` — exploratory causal test, `MECHANISM_SEG_FAIL`

**Preregistration:** `PM-20260825-e88248ff` (causal test), `PM-20260825-41d5d71e` (calibration).
**Responds to:** ResearchOS candidate `rmc-2026-08-24-001` (`semantic-entropy-escalation-gate`), AAMR research request `arr-2026-08-24-001` (GAP-005).
**Artifacts:** `data/lab/arena/semantic-entropy-sufficiency-calibration-v1/calibration.json`, `data/lab/arena/semantic-entropy-gate-v1/{selection.json,results.json}`, `scripts/arena/calibrate_semantic_entropy_gate.py`, `scripts/arena/run_semantic_entropy_gate_v1.py`.
**Spend:** calibration $0.003309 + causal test $0.435904 = **$0.439213**.
**Verification:** independent 8-agent verify→adversarial-refute workflow (`wf_4c4d2a6e-40f`) checked every interpretive claim below against the raw JSON, underlying pipeline code, and (for two units) the primary LongMemEval corpus. One claim in this report's own first-draft analysis was caught and corrected as a result (see unit `6e984301` below) — kept here as a record of the correction, not smoothed over.

---

## Mechanism

Read/query-side. For each unit: retrieve the standard compact top-10 context. Sample the frozen reader M=4 times at temperature=0.7 on `(question, compact_context)`. Embed each sample locally, greedy-cluster by cosine similarity (threshold 0.85), compute Shannon entropy over cluster-size proportions. If `entropy > 0.5` (a round threshold, not tuned to the 8-unit calibration sample): escalate by appending the raw source session behind the top-1 retrieval hit (`mechanism_ablation.raw_session()`, the exact frozen code Entry H / `RAW_PROVENANCE` uses) to the context. Generate one final answer at `temperature=0` on whichever context resulted (`BASE` = compact-only, unconditional; `GATE` = entropy-conditional).

## Why this candidate

ResearchOS's own candidate (`rmc-2026-08-24-001`) named the exact risk that this test ultimately confirmed, *before* any AAMR spend: its `possible_negative_regime` field states that AAMR's own observed failures are dominated by "presence-type" failures (gold retrieved but reader still wrong), not "absence-type" failures semantic entropy is theoretically suited to catch. A $0 calibration (`PM-20260825-41d5d71e`, reusing already-persisted, already-labeled data from `raw-provenance-fresh-replication-v1` — zero new ingest) found a clean, correctly-directioned separation (sufficient=0.300, insufficient=1.104, +0.804) that justified one bounded, fresh, gold-blind causal test. This report is that test's result.

## Result

6 fresh, gold-blind units (1/category), never used elsewhere in this project.

| unit | type | entropy | escalated | base_correct | gate_correct |
|---|---|---|---|---|---|
| `29f2956b` | single-session-user | 0.000 | no | ✓ | ✓ |
| `2788b940` | multi-session | 0.000 | no | ✓ | ✓ |
| `0edc2aef` | single-session-preference | 1.500 | **yes** | ✗ | ✗ |
| `6e984301` | temporal-reasoning | 0.000 | no | ✗ | ✗ |
| `22d2cb42` | knowledge-update | 0.000 | no | ✓ | ✓ |
| `1de5cff2` | single-session-assistant | 0.811 | **yes** | ✗ | ✗ |

BASE 3/6 correct, GATE 3/6 correct (byte-identical judgment on every unit). **0 regressions, 0 repairs.** Escalation fired on 2/6 (33%, selective — neither 0% nor 100%). Spend $0.435904 against a $0.60 cap.

## Preregistered gate applied

**Success required all three:** (a) GATE matches/exceeds BASE with 0 unexplained regressions — **met** (tied, 0 regressions); (b) selective firing — **met** (33%); (c) ≥1 traceable repair among escalated units — **NOT met** (0/2).

**Verdict: `MECHANISM_SEG_FAIL`.** Criterion (c) fails cleanly. This is a null result, not a "works safely" result — reported as such.

## Per-unit archaeology (verified against raw JSON, pipeline code, and — for two units — the primary LongMemEval corpus)

**`0edc2aef` (Miami hotel, escalated, still wrong).** All 4 samples are semantically identical refusals ("no Miami info in the context"), yet clustered into 3 groups (entropy=1.5) — a clustering artifact, not real disagreement: independent re-inspection found the two *most* lexically similar refusals split into different clusters while two more different ones were merged, the opposite of what a coherent entailment-based split should produce. The escalation injected a Seattle hotel-booking session — no Miami content, confirmed. Independent review also surfaced a sharper framing than this report's first draft: the injected raw text actually contains an even *more* explicit, generalizable statement of the user's stated preference ("rooftop pool or hot tub on the balcony") than `compact_context` does — and the reader still refused to generalize it to a Miami recommendation. This is a reader reasoning/application failure, not a retrieval-completeness gap raw injection could ever fix — exactly the "presence-type failure" risk the ResearchOS candidate itself flagged as its main threat.

**`1de5cff2` (Veja fashion brand, escalated, still wrong).** Genuine disagreement (3/4 samples say "Veja," 1/4 refuses) — confirmed as a true positive, not an artifact: all 4 samples were generated from the *same* compact context as `base_answer`, so the split reflects the reader's own instability in choosing between its prompt-instructed grounding discipline and outside/parametric knowledge (Veja's wild-rubber sourcing is real public information). The escalation injected a session about jeans care, athletic wear, and watches — zero mention of Veja, wild rubber, or the Amazon rainforest. This is not an unexplained fallback: `raw_session()` deterministically fetches the session behind Mem0's own rank-1 retrieval hit, and that hit was topically wrong for this query — a retrieval-ranking miss (absence subtype 2). Independent code/corpus verification went further than "plausible": the gold-answer-bearing text (Veja's wild-rubber sourcing) exists **only** in an assistant-authored turn in the source LongMemEval session, and `as_records()` — the shared ingest function every mechanism in this project uses, by deliberate CUPMem-fair-comparison design — unconditionally drops all assistant-role turns before Mem0 ever sees them. This unit is a confirmed (not merely plausible) instance of the already-documented assistant-turn-scoping-loss (absence subtype 4), compounded by a retrieval-ranking miss on top.

**`6e984301` (sculpting classes, not escalated, wrong).** **Correction to this report's own first-draft read:** the initial characterization was "confident hallucination — a textbook black-box-entropy blind spot." Independent adversarial verification traced the unit to its primary LongMemEval source and refuted this. `gold=3` comes from cross-session date arithmetic: one session (Feb 11) states classes started "today"; a later session (Mar 4) states the tools were bought "today" — exactly 3 Saturdays apart. Neither `compact_context` nor this mechanism's own raw-injection format (verified from the two sibling escalated units above, both pure `user:/assistant:` text with no session-level date stamps) carries the timestamps needed to compute this. So even if entropy had fired here, this specific remedy could not have repaired it — the operative cause is temporal-representation-loss (absence subtype 3, already the largest documented failure cluster project-wide), not a defect in the entropy signal or a novel "confident hallucination" phenomenon. Zero cross-sample disagreement here is an *accurate* readout — there was no hidden disagreement for a diversity-based gate to detect in the first place.

**`2788b940` (fitness classes, not escalated, correct — minor methodological note).** One of 4 diversity samples says "at least four" fitness classes while the other three say "at least five"; all 4 were nonetheless clustered together (entropy=0.000). Independent review confirmed the raw text difference but tempered the "numeric blind spot" framing: the two responses differ by essentially one token against ~34 identical surrounding words, "at least four" is not logically contradicted by "at least five" (a weaker, non-contradictory subset claim), and — most importantly — the production `base_answer`/`gate_answer` were generated independently (a separate `temperature=0` call) from the 4 diversity-sampling calls and already correctly said "five" regardless of what the entropy estimator saw. This unit never affected a real outcome; worth carrying as a design note (long near-duplicate text can dominate embedding similarity over a single decision-relevant token) rather than a claim about this run's correctness.

## Why the mechanism failed, precisely

Not bad luck on an otherwise-sound design. Both cases where escalation fired hit into already-known structural absence subtypes that this specific remedy (`raw_session()`, anchored to Mem0's own top-1 retrieval hit, single-hop, no session-level date stamps) inherits wholesale from `RAW_PROVENANCE` (Entry H) — it was never going to repair a retrieval-ranking miss compounded by an assistant-turn-scoping loss (`1de5cff2`) any more than `RAW_PROVENANCE` itself could. And the one non-escalated wrong unit (`6e984301`) is a temporal-representation-loss case this entire mechanism family (trigger *and* remedy) is structurally blind to. Separately, the entropy *trigger* itself proved unreliable on this sample: 1 of 2 firings was a genuine true positive (`1de5cff2`), the other a clustering artifact on near-duplicate refusal phrasing (`0edc2aef`).

## Cost-efficiency note (secondary to the correctness gate, but the original motivation)

Not evaluated further — a gate that produces 0 traceable repairs has no efficiency benefit to weigh against `RAW_PROVENANCE`'s unconditional ~21.4x token overhead. `gate_context_tokens` were recorded per unit for completeness (92–3277 tokens) but are moot given the correctness result.

## Relation to the ResearchOS candidate

This closes `rmc-2026-08-24-001` and `arr-2026-08-24-001` with `AAMR_MEASURED` evidence — a bar the request's own stop condition treated as sufficient to close regardless of the outcome's direction. The candidate's own stated risk (presence-type failures, not absence-type, dominate AAMR's workload) is exactly what happened: of the two escalated units, zero were absence-type-fixable-by-raw-injection; the trigger itself only found one genuine (non-artifact) disagreement out of two firings. See `docs/research/rmc-2026-08-24-001_aamr-review.md` for the formal review file.

## Status

`DROP` — see Ledger Entry Q. Not `FAIL_ON_REPLICATION_GATE` (that status is reserved for mechanisms that already cleared an exploratory bar and then failed to replicate — SEG never cleared its own exploratory bar). Not scheduled for a second attempt at the same design per this project's "don't retune the same failed action" discipline.
