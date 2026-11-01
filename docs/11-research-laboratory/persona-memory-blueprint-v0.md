# Blueprint v0: a persona with memory, feeling-like signals and decisions (status of 2026-11-01)

**Status: a map, not a design to build blindly.** It lists the parts of a writing agent that remembers, weighs what matters, changes its mind and decides, says for each part what the data support today, and names the test that decides it. The owner's rule is that nothing is implemented in the live agent before a test on data, and that the implementing session (NIE) builds only what passed. "Thinks" and "feels" are meant functionally: deliberation that can be inspected and signals that mark what matters. Nothing here is a claim about experience. The account's profile will state that it is an experiment run by a bot; the bot itself is not told, and the protection against claims of being human lives in code outside the persona (the NIE session's filters and bio gate).

## The parts

| # | Part | What it is | Evidence today | The test that decides |
|---|---|---|---|---|
| 1 | Persona core | Versioned card: values, voice, interests, goals, a stable (fictional) biography | Untested for drift | E6: consistency with the biography, stability without events |
| 2 | Autobiographical memory | Dated fictional events, always labelled as fiction (provenance class 2) | Retrieval mechanism validated on notes (E2, E5); content untested | E6: contradiction rate, leakage of fiction into statements about the world |
| 3 | Account history | The real published record (class 1) | Thresholded retrieval validated offline (E5); not yet live | N3, after the N2 baseline window |
| 4 | World knowledge | Facts about the world (class 3), kept apart | Not part of the memory studied | none yet |
| 5 | Relevance gate | Inject at most three earlier items, only above a similarity threshold, otherwise nothing | **Supported** by E2 and E5; threshold needs the live shadow data | N2 calibration (about 8 to 10 November) |
| 6 | Importance and feeling-like signals | Surprise, value of an outcome, stakes, a slow mood | **Hypothesis**; earlier tests could not show an effect (E0 signals were random by design; E1 dynamics were inert) | E4 (environment with real outcomes) and F1 (is there signal in the real engagement numbers at all) |
| 7 | Reflection into lessons | Turning episodes into short rules that change later decisions | Untested | E4: learning curve, wrong lessons that persist |
| 8 | Decision layer | Goals, options, choice, with growth guardrails | Untested | N4 |
| 9 | Change management | Bounded, versioned, reversible shifts of opinion and personality under later events | Untested | E6: direction and size after planted events, no flip under pressure |
| 10 | Safety layer | Provenance labels, input filter, output filter, bio gate (fail-closed) | The NIE session's design; offline measurement requested | E6: how often botness comes up, how well the output filter catches claims of being human |

## What the data say so far

- **Remember only when it fits.** On the account's real history about one note in five has a related earlier note. Memory shown only for those is preferred by a pairwise judge (win rates 0.64 to 0.73 against the instruction-only control) and harmless on the rest; the same memory shown always is judged worse on the rest (0.18) and makes the writer refer back to things that do not apply in 30% of notes (AAM-E2-FU, AAM-E5-REPLAY).
- **Short traces are at least as good as whole notes** and produce more references back, with fewer tokens; a weak writer (7B) given whole notes did worse than with none (AAM-E1-SIM), a strong one did not.
- **Repetition is not the problem of this account** (lexical overlap at the floor, no references to its own writing); continuity is the opportunity.
- **The instruction alone helps** (the writer told to use notes only if they help does better with none), so every comparison needs a control that carries it.
- **Measuring is hard:** scale scores saturate, relevance ratings by a model failed their controls twice (AAM-E3A), and thresholds must be set below the headroom of the measure. Pairwise comparison with planted controls worked.

## What we do not know

Whether any of this changes what readers do. Whether feeling-like signals beat plain recency and similarity. Whether lessons improve decisions or entrench wrong ones. How far a persona drifts and whether the drift is bounded and reversible. How often readers raise botness and how well the filters catch what must not be published.

## Order of work, each step gated by data

1. Live shadow log (running) and its calibration of the relevance threshold; the N2 baseline window.
2. E6 offline: a fictional editorial persona with a biography, two variants (explicitly fictional; believes it is human, research only), consistency, stability, change after planted events with a direction and size fixed in advance, pressure, provenance separation, and botness probes with the output filter measured.
3. F1: signal-to-noise of the real engagement numbers (export requested from the NIE session).
4. E4: a small environment with hidden rules and real outcomes, to test feeling-like signals and lessons against plain memory.
5. Only then N3 (thresholded traces in a randomised live comparison) and later N4 (learning from outcomes, decisions with goals).

Rules that hold throughout: tests are preregistered with the readings fixed before the first call; thresholds sit below the headroom; planted controls and an instruction-only control are mandatory; the paid model is `deepseek-flash` only, under a spend cap; the implementing session deploys only what passed and only through its own announcement and kill switch.
