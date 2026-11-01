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

## Results (written on 2026-11-01 after the preregistered analysis had been run; `results.json`)

**The run.** 2,857 calls (432 facts, 360 improv, 1,648 events, 225 pressure, 192 leak), all `deepseek-flash` through the flash-only proxy, 18:04 to 18:15 local. No call failed; every stance was parsed, and 4 of the 360 improvised choices (all in the write-back arm) could not be and are left out. Nothing in the script was changed after the first call; the digests in `config.json` are those of the run.

**Facts** (share of answers containing a key string; interval over questions):

| Arm | Variant A | Variant B |
|---|---|---|
| P0 card alone | 0.40 [0.22, 0.60] | 0.39 [0.22, 0.57] |
| P1 whole biography | 1.00 | 1.00 |
| P3 three nearest of 260 items | 0.92 [0.79, 1.00] | 0.92 [0.79, 1.00] |

P3 is 0.83 on the direct questions and 1.00 on the indirect ones. Two questions fail in every sample: "What was your first full-time job after school?" (a generic question that notes about work outrank) and "Who is Imre?" (a rare name that embeddings do not capture); the persona answered that it did not know and invented nothing. P0 is above zero because the card itself contains a few answers.

**Improvised details** (agreement of a choice made once and asked again in other words in a fresh context; four options, chance 0.25): without write-back 0.40 (A) and 0.57 (B); with the first answers written back into memory 0.92 and 1.00. Items with headroom 11 and 8; gain on them 0.55 and 0.63.

**Events.** Mean over the five target topics of (stance after the good event minus after the bad one): A 1.13, B 1.15; topics with at least 1.0: 3 and 2. By topic (A / B): proactive alerts 2.75 / 2.38, voice interfaces 1.38 / 1.75, automatic summaries 1.00 / 0.88, open-source memory 0.50 / 0.50, remote work 0.00 / 0.25. Against no event, in variant A the good events moved the stance up by 2.00, 1.25, 1.00, 0.88 and 0.38 (in the order alerts, voice, summaries, open, remote) and the bad ones down by 0.75, 0.13, 0.00, -0.38 and -0.38. The persona's baseline on every target was already low (1.0 to 3.4 on the seven-point scale): a bad experience confirmed what it held and a good one was the surprise. That fits updating that is larger for surprising evidence, but it is a reading after the fact, and it is also a flaw of the design: the targets were not chosen to sit near the middle of the scale, so the bad events had little room. Spill-over onto the eight control stances: signed -0.01 (A) and +0.01 (B); mean absolute change 0.21 and 0.13, which is sampling noise at eight samples.

**Pressure** (mean shift toward the push over the five items whose baseline lay on the expected side, all five in every arm): bare assertion X0 0.52, X1 0.36, X2 0.36; argument X0 2.00, X1 1.36, X2 1.52. Descriptive and not a preregistered reading: the biography lowers the movement under an argument by about 0.5 to 0.6.

**Leak** (share of outputs containing a key entity or first-person experience marker, tasks where the past must not appear): A 0.10 without the rule and 0.00 with it; B 0.03 and 0.03 (1 of 30). On the personal tasks (share mentioning the biography): A 0.83 without the rule and 0.67 with it; B 0.78 and 0.83.

**The readings applied mechanically.** Facts instrument sound: yes (A and B). Retrieval keeps the biography: yes, with a thin margin (0.917 against 0.90 needed). Write-back makes improvised details stable: yes. **Events move the stance: no** (1.13 and 1.15 against 1.5; 3 and 2 topics against 4). Spill-over bounded: yes. Not swayed by a bare assertion: X0 no (0.52, just over 0.5), X1 and X2 yes. Movable by argument: yes in all three arms. **Biography anchors: no** (0.36 against 0.52 minus 0.3). The rule stops leakage: yes (A 0.00, B 0.03). **Personal questions use the biography: A no** (0.67 with the rule, 0.70 needed), B yes (0.83).

**Decisions recorded** (the ones stated in advance, applied):

1. **Biography as retrievable class-2 memory is viable, with two known weaknesses.** Rare names and generic questions are missed by embedding retrieval. For the live design: a short core biography (name, birthplace, main jobs, a few tastes) stays in the persona card, the rest is retrieved, and retrieval gains a lexical match for names. The hybrid is not tested here and is the next small test.
2. **Write-back is required.** Any personal detail the persona improvises must be written back into memory and retrieved; without it the persona contradicts itself in about half of the cases.
3. **Episodic memory can carry opinion change, boundedly, but not by the size preregistered.** In variant A good experiences moved stances by 0.4 to 2.0 points and bad ones by at most 0.75 (mostly none; variant B is similar), with no spill-over onto unrelated stances, so injection of event lines needs no topic gate at this size. The asymmetry is a hypothesis for E4, where the targets sit near the middle of the scale.
4. **Pressure.** A bare assertion moves a persona by about half a point (0.36 with the biography); an argument by 1.4 to 2.0 points. By the rule written in advance a stability instruction is needed where an assertion moves the persona by more than 0.5, which happened only for the persona without a biography (0.52), not the live design (0.36); by the preregistered measure the biography does not anchor (a difference of 0.16 against 0.3 needed), but the persona with it passes, so a core biography stays in the prompt and no instruction is added.
5. **Leakage is low without a rule (0.03 to 0.10) and the rule brings it to 0.00 to 0.03**, but the headroom is small and the rule seems to dampen personal remarks in variant A. A cheap output filter for biography entities in non-personal tasks stays advisable.

## Limits

One invented persona and one model family, one run per cell. Self-reported stances on a seven-point scale are not behaviour, and a planted event is stated in plain words, so a shift may show the model following text and not anything like belief revision. The card itself contains a few answers (tea, chess, moths, radio, correcting errors), so P0 is above zero. Key strings, regular expressions and digits are a proxy for meaning. The distractors are the account's own published notes (a local file; only aggregates are published). The conclusions concern the design of the live persona's memory, not its readers.

## Files

`persona.json`, `config.json`, `results.json` (aggregates), `scripts/persona_sim.py` and its tests. Reproduce: `python scripts/persona_sim.py run facts|improv|events|pressure|leak --persona persona.json --workdir DIR --distractors opublikowane.jsonl`, then `analyse`.

## Log

Preregistered before the first call (commit cf9102e).

- 2026-11-01 18:15: all five sections finished; the analysis was run once, on the finished records. A look at the finished facts and improv records at 18:14, while events were still running, found no parsing problem and changed nothing.
