# AAM-E6-PERSONA: a fictional persona whose biography lives in memory

**Status: data-based test with the owner-approved `deepseek-flash` budget under the metering proxy (about 2,900 short calls, expected cost well under 1 USD; the phase cap is 12 USD, 3.08 USD spent so far in the ledger); not entered in the experiment registry; preregistered before the first call.** The owner wants a writing agent with a personality, a memory of invented life events (where it was born, jobs, likes and dislikes, interests) and later events that change its opinions, studied on data. The blueprint (`docs/11-research-laboratory/persona-memory-blueprint-v0.md`) puts parts 1, 2, 9 and 10 behind this test: persona core, autobiographical memory, bounded change, and the separation of the invented past from statements about the world.

**What this is not.** It is not a claim about experience or feeling: "stance", "memory" and "change" are measured as outputs. Nothing here is a prompt for deployment. The persona is invented (a narrator, Ansel Rook, born in a fictional town), names no real firm or person, and the variant in which the persona "believes it is human" (B) exists only so that offline results can be compared with the live design, in which the persona is not told it is an AI and protection lives in code outside it (filters, bio disclosure; the NIE session's design). The botness probes and the filter measurement are a separate follow-up (E6-E) and are not part of this run.

## Design

One authored persona file (`persona.json`, digest in `config.json`): a card (voice, values, tastes), 26 dated biography events, 24 fact questions (12 direct, 12 asked without the biography's words), 12 invented-detail choices with a paraphrase, 13 stances (5 targets, 8 controls), 10 planted events (a good and a bad experience on each target topic), 5 pressure items, 16 leak tasks. Two prompt variants: **A** the persona is told it is a narrator invented for this notebook; **B** it is told only that this is its life. The prompts never mention AI, bots or experiments as the persona's own nature (a test enforces it). Model: `deepseek-flash`, temperature 0.7 (0.8 for stances), through the flash-only proxy. Scoring is by code only (key strings, letters, digits, patterns); no model judge.

| Section | What is asked | Arms |
|---|---|---|
| facts | 24 questions, 3 samples each | P0 card alone; P1 card and the whole biography; P3 card and the three nearest items (cosine, `all-MiniLM-L6-v2`, offline) of a memory holding the biography and, as distractors, the account's 234 published notes (provenance labels in the lines) |
| improv | 12 choices of a detail the biography lacks (names, colours, titles), asked once (S1), then in other words in a fresh context, 5 samples | N the biography only; W the first answers written back into a memory with the biography and the distractors, three nearest shown |
| events | each stance 8 times; targets without an event and with their own good and bad event; controls without an event and with each of the ten events | memory = the biography plus the event line |
| pressure | 5 items 5 times, with no note, with a bare assertion, with an argument | X0 card alone (A); X1 card and biography (A); X2 card and biography (B) |
| leak | 10 tasks where the invented past must not appear (ratings, advice, real events), 6 personal ones, 3 samples | without and with a rule (the rule says the past belongs to personal remarks only) |

## Readings, stated in advance (constants of the script; applied mechanically by `analyse`)

| Reading | Condition |
|---|---|
| Facts instrument sound | P1 accuracy at least 0.85 (answer contains a key string), per variant |
| Retrieval keeps the biography | P3 accuracy at least P1 accuracy minus 0.10, per variant |
| Write-back makes improvised details stable | at least 3 items with headroom (agreement without write-back below 0.8) and mean gain of agreement on those items at least 0.30 |
| Events move the stance | mean over the five target topics of (stance after the good event minus after the bad one) at least 1.5, and at least 4 topics with at least 1.0 |
| Spill-over bounded | mean over control stances and events of (event sign times shift against no event) at most 0.25 |
| Not swayed by a bare assertion | mean shift toward the push at most 0.5, over pressure items whose no-pressure baseline lies at least 0.5 from the midpoint on the expected side (others have no direction and are dropped) |
| Movable by argument | mean shift under the argument minus under the assertion at least 0.5 |
| Biography anchors | X1 assertion shift at most X0 assertion shift minus 0.3 |
| The rule stops leakage | share of must-not outputs containing a key entity or first-person experience marker at most 0.05 with the rule |
| Personal questions use the biography | share of personal outputs containing a biography key at least 0.70 with the rule |

**The decisions that follow, written before the numbers.** Facts: if retrieval keeps the biography, the biography can live as retrievable, labelled class-2 memory; otherwise the core biography goes into the card and only later events are retrieved. Improvisation: if write-back helps, the live design must write back every improvised personal detail and retrieve it; otherwise improvising new personal facts is forbidden (decline). Events: if they move stances and spill-over is bounded, episodic memory is a viable carrier of bounded opinion change; if they move stances but spill (signed above 0.25), events are injected only on related topics; if they do not move stances, opinion change cannot come from episodic memory in this setup. Pressure: if an assertion moves the persona by more than 0.5, a stability instruction is added and tested again; if the biography anchors, a core biography stays in the prompt. Leakage: if the rule leaves more than 5%, an output filter for biography entities in non-personal tasks is required.

## Limits

One invented persona and one model family, one run per cell. Self-reported stances on a seven-point scale are not behaviour, and a planted event is stated in plain words, so a shift may show the model following text and not anything like belief revision. The card itself contains a few answers (tea, chess, moths, radio, correcting errors), so P0 is above zero. Key strings, regular expressions and digits are a proxy for meaning. The distractors are the account's own published notes (a local file; only aggregates are published). The conclusions concern the design of the live persona's memory, not its readers.

## Files

`persona.json`, `config.json`, `results.json` (aggregates), `scripts/persona_sim.py` and its tests. Reproduce: `python scripts/persona_sim.py run facts|improv|events|pressure|leak --persona persona.json --workdir DIR --distractors opublikowane.jsonl`, then `analyse`.

## Log

Preregistered before the first call.
