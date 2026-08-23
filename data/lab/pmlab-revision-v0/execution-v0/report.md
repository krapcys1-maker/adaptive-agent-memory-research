# PMLAB-REV-V0 — does separating valid time from transaction time buy anything?

Experiment ID: `PMLAB-REV-V0-001`
Tier: **E (exploratory)** — deterministic, model-free, no network, no API cost
Registered threshold, set before the run: *zero critical future leakage or silent concurrent winner; exact pre-correction reconstruction*
Authority: development measurement only. The corpus is authored by the same agent that implemented the schema.

## Why this run exists

Schema version 2 separated transaction time from valid time on the strength of a code comparison with Graphiti and the SQL:2011 standard. That is an argument, not a measurement. This run could have falsified it: had the bitemporal arm failed to beat a transaction-only one, the change bought nothing and should have been reverted.

## Design

14 events across 7 cases, in the shipped version-2 shape. 18 queries of three types:

- `current` — what is true now
- `valid_at(T)` — what was true at T in the world
- `as_known_at(T)` — what we believed at T, using only records written by then

Cases: late correction, succession, future-effective rule, correction-of-a-correction, future-information leakage (marked **critical**), concurrent writers one second apart, and an unrevised fact queried before it existed.

Five arms, each a small resolver blind to the expected answers: `one_timestamp` (what version 1 was), `transaction_only`, `valid_only`, `bitemporal` (what version 2 is), and `oracle` as a ceiling.

## Results

| Arm | exact | `current` | `valid_at` | `as_known_at` | future leaks | critical failures |
|---|---|---|---|---|---|---|
| **bitemporal** | **0.944** | 1.00 | **1.00** | 0.86 | **0** | **0** |
| valid_only | 0.778 | 1.00 | 1.00 | 0.43 | 4 | 1 |
| transaction_only | 0.722 | 1.00 | 0.20 | 0.86 | 0 | 0 |
| one_timestamp | 0.389 | 1.00 | 0.20 | **0.00** | 6 | 1 |
| oracle | 1.000 | 1.00 | 1.00 | 1.00 | 0 | 0 |

**Bitemporal is the only arm meeting the registered threshold while also reconstructing world-state**: zero critical failures, zero leaks, and perfect `valid_at`.

## What the failures show

Each single-axis design fails precisely the question the other axis answers, which is the sharpest possible confirmation that both are needed rather than one.

**`valid_only` leaks the future.** It scores 1.00 on `valid_at` and 0.43 on `as_known_at`, with four leaks including the critical one. Asked what we believed in February, it returns a record written in December. Without a transaction axis the question cannot even be posed, so it silently answers a different one.

**`transaction_only` cannot reconstruct the world.** It reaches 0.86 on `as_known_at` with zero leaks, then collapses to 0.20 on `valid_at`. It knows what was believed and when, and nothing about when facts were true.

**`one_timestamp` — what version 1 was — scores 0.00 on `as_known_at` with six leaks.** It cannot reconstruct a past belief at all. Every answer is the latest write, so every historical question is answered with present information.

## The caveat that matters most

**Every arm scores 1.00 on `current`.** If the only question ever asked is *what is true now*, the schema change buys nothing and version 1 was adequate.

The value appears exclusively in historical questions: what was true then, and what did we believe then. That is a real limit on the result and it should temper any claim that version 2 is simply better. It is better *at questions version 1 could not ask*.

## The one bitemporal failure, and why it is worth more than the score

Case C3, `as_known_at`. A rate of 5% is recorded on 10 January valid from 1 January. A rate of 7% is recorded on 15 January but valid only from 1 September. Asked what we believed on 1 May, the arm answered 7%. The correct answer is 5%: the new rule existed on paper but was not yet in force.

The cause is a real trap rather than a typo. The resolver treated the superseded record as dead the moment a successor existed. **When a superseding record's `valid_from` lies in the future, the record it supersedes is still the answer.** Supersession ends a fact at the successor's `valid_from`, not at the successor's existence.

This did not breach the registered threshold — it is not a leak and not a critical case — so the result above stands as run. But the trap must be handled when the store grows a real query layer, which today it does not have: `derive_temporal_view` computes interval ends and answers no queries.

## Limits

- **The corpus is authored by the agent that implemented the schema.** Mitigated only by the arms being blind to expected answers and the oracle deriving from the case definition, not from any resolver's output. This is `n = 1` and not independent.
- 18 queries over 7 cases. The protocol in `revision-benchmark-extension.md` lists eleven case families; this run covers six of them. Overlapping scopes, clock skew, uncertain ranges, timezone boundaries, and replay/import are untested.
- Resolvers are small reimplementations, not the store's own query path, because that path does not exist yet.
- Deterministic, so repetition adds nothing; there is no interval to report.

## What follows

1. **Version 2 is kept.** The change is measured rather than argued, and the arm comparison isolates why both axes are needed.
2. **The future-effective trap is registered** before any query layer is written, so it is designed for rather than discovered later.
3. `PMLAB-REV-V1` through `V3` are unblocked by the registered threshold — no critical leak, no silent concurrent winner — but they need a reader and a larger corpus, so they stay behind the corpus constraint the triage identified.
