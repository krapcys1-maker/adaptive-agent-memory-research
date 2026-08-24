# Same-Category Entity Enumeration — Exploratory Test v1 ("Mechanism E")

Preregistration: `PM-20260824-fd63ec2d`. **Verdict: regime mismatch — mechanism never fired. `MECHANISM_E_FAIL` — DROP.**

## Mechanism

Read-side, deterministic, zero LLM. Extracts entities via a 22-category-suffix template list (Airlines, Museum, Hotel, ...), enumerating distinct entities when ≥2 share a category. A regex bug (sentence-initial capitalized verbs swept into entity names) was caught by the mechanism's own unit tests before any paid call, fixed with a leading-word stoplist, and reverified both by the test suite and by replay against the real historical case that motivates it — E1's `gpt4_f420262c` ("Spirit Airlines" wrong answer): the fixed transform cleanly identifies American/Spirit/United Airlines as three distinct entities, confirming it would have fired there.

## Results

8 fresh, gold-blind units. **0 of 8 units triggered the flag.** No category ever had ≥2 distinct entities co-occur among any unit's retrieved items. Net repairs: 0 (nothing to repair — the mechanism was byte-identical to `BASE` on all 8 units, confirmed inert by construction). 4/8 units already correct under `BASE`, 4/8 already wrong under `BASE`; `+E` matches `BASE` exactly on every one.

## Interpretation

**Pure regime mismatch, not a mechanism failure.** The transform behaved exactly as specified — inert when its precondition doesn't hold, which is what happened on all 8 units. Unlike `RAW_PROVENANCE`'s precondition (Mem0 compact extraction losing detail — present on essentially every unit, since Mem0 always compresses), `SAME_CATEGORY_ENTITY_ENUMERATION`'s precondition (two distinct same-category entities co-retrieved together) is evidently rare even in an 8-unit sample chosen with a category-structure prior toward richer, longer conversations. The one confirmed real case (`gpt4_f420262c`) came from a unit with 208 retrieved items at the widest breadth setting — a much larger retrieval than this project's `native`/`compact` operating point typically returns (`~10` items, matching `BASE` here). This suggests the precondition may correlate with *retrieval breadth*, not just category, an axis this exploratory test did not vary.

## Emerging campaign-level lesson

Two consecutive mechanisms now (`D`, `E`) have been closed as regime-mismatch nulls rather than clean pass/fail results, both sharing a common shape: a **narrow, templated precondition** that a modest fresh sample failed to exercise even once. `RAW_PROVENANCE` (the one validated mechanism) has a **universal precondition** by contrast — it always has *something* to check, because Mem0 always compresses. Future mechanism candidates should weight this heavily: prefer mechanisms whose target condition is common across most retrievals, or explicitly budget for a larger or breadth-varied sample when the precondition is known to be narrow, rather than assuming an 8-unit gold-blind sample will reliably surface a rare structural pattern.

## Cost

$0.574796 (ingest-dominated: 373 sessions across 8 units; reader+judge ~$0.0028). Three transient "Invalid JSON response" ingest warnings, same benign, non-blocking pattern already seen in `RAW_PROVENANCE`'s run — all 8 units show sane stored-item counts and no contamination FAIL.
