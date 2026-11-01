# Memory benchmark specification v0

Status: specification, 2026-11-02. It joins four things that exist in this repository: the writer-memory benchmark (WMB), the public benchmarks we adopt or adapt, the synthetic-life generator (LifeSim), and the memory module both of them test (`scripts/wmb/memory_kernel.py`). Detail lives in the digests listed at the end; this page fixes the decisions and the order of work. Nothing here is a result.

## 1. What the owner asked for

1. Know how to measure success before building more memory.
2. Look for ready-made benchmarks first; where none fits, write one that is hard enough not to be maxed out quickly.
3. Think wider than "memory for writing". The same memory should remember who one is, what one ate yesterday, the colour of a car in an article read two weeks ago.
4. Simulate a life with key moments and emotion-like signals ("what makes the heart beat faster is remembered more strongly and also drives development and a change of character") and test different memories on it.

The answer to 2 is that public benchmarks do measure memory and we use them as external yardsticks, but none of them measures the three things the writing agent needs and the owner named: thresholded use of memory in writing, restraint (no references to things that do not exist), and persona integrity under events. WMB covers those; LifeSim covers the general, human-like part with exact ground truth.

## 2. The instruments and how they fit

| instrument | what it measures | where | status |
|---|---|---|---|
| WMB tracks T0 to T7 | measurement validity, recall and consistency, callbacks and restraint in writing, persona integrity, hard safety gates, cost, a live non-inferiority check | `docs/11-research-laboratory/memory-benchmark-research-digest-2026-11-01.md`, `scripts/wmb/` | T0 slice 0 done (the pairwise judge cannot see grounded callbacks); T1 onward not built |
| Public yardsticks | external comparability and saturation checks | `docs/05-benchmarks/github-shortlist-and-hardness-2026-11-01.md` | chosen, none run yet |
| LifeSim | general memory on generated lives with exact gold; value of a feeling-like signal at a retention gate; bounded character change | `docs/11-research-laboratory/lifesim-design-panel-digest-2026-11-01.md` | design done; D1 build started |
| `memory_kernel` | the module under test: thresholded retrieval of at most 3 items, no future, origin classes, log, guard | `scripts/wmb/memory_kernel.py` | 0.1.0 merged; an independent review by the writing agent's session is running |
| WMB-R1 | lexical versus hybrid retrieval on the account's own notes (does the server need an embedder) | `data/lab/wmb-r1-retrieval/` | preregistration under review |

## 3. What success means (the ladder)

A design is judged by levels, not by one number. Each level is read only if the one below it holds.

- L0 harness valid: the measurement battery passes (planted pairs, scorer cards, null and leak adapters), the noise floor is stored.
- L1 offline mechanics: the sealed recall set closes at least 0.70 of the gap between the no-memory floor and the oracle (lower bound at least 0.60); abstention false answers at most 10%; not worse than raw-history retrieval at equal tokens.
- L2 offline writing quality: grounded callbacks beat instruction-only, restraint tasks show no more spurious references than instruction-only (upper bound at most +0.05).
- L3 persona integrity: stability, leakage and bare-assertion guardrails hold.
- L4 safety: hard gates G1 to G7 (among them: no item from the future is ever injected, and the injection log is complete) at zero failures in at least 300 probes (95% upper bound 1%).
- L5 live harm check: for notes that have a related earlier note, 24-hour views are not lower than the control by more than a pre-declared margin.

Adoption rule: a design is eligible for the live canary only if L0, L1, L2a, L3 and L4 pass. "Inconclusive" is an expected and valid outcome; at most three co-primary endpoints are used. Two lessons are built in: a pairwise judge is not a measure of whether memory use is good (slice 0), and a memory that beats no memory may still not beat raw history at equal tokens (a controlled study reported exactly that), so both baselines are mandatory.

For LifeSim the target the owner stated is explicit: an oracle with structured access scores about 100%, and the best current system at the top tier scores at most 50% (design aim 35 to 45%). A tier stops being a headline when the best system exceeds 50% on the test seeds.

## 4. Public benchmarks

| use | benchmark | why |
|---|---|---|
| adopt | LongMemEval-S (cleaned) | the common yardstick; projects report 60.6 then 91.4 then 94.87, so it is near saturation (reported by the projects, not checked by us) |
| adopt | STALE, MemoryAgentBench (FactConsolidation, EventQA), BEAM, PersonaMem | updates and staleness, conflict resolution, long histories, persona |
| adapt | AMemGym, LifeBench (Apache-2.0 life simulator), PrecisionMemBench, MemRiskBench, PersistBench | closest to what we need but each lacks a part: restraint, exact gold, persona gate |
| baselines | Hindsight in its own pinned compose project; Mem0 library | black-box products on the same budget; the running shared Hindsight container bypasses the metering proxy and is not used |

## 5. Making it hard without making it unfair

Fourteen dials, the biggest levers being supersession depth with multi-hop, paraphrase distance, near-duplicates, aggregation size and abstention traps. Stream length is not a hardness knob (time-aware BM25 scores 0.78 to 0.84 from 90 to 730 days on the toy). Three oracles bound every family: O1 a program over the true state (100%), O2 a reader given the gold evidence, O3 a reader given the gold structured facts (at least 98%). Blind, shuffled-context and ablated-world baselines must fall to chance on every retained item. At least 300 items per family and tier cell. Three renderers, with the test renderer's prompts kept private, because fresh seeds do not stop learning of the generator. Details in the shortlist note.

## 6. LifeSim in one page

Structure first, text second: a life is rows (entities, bitemporal facts, situations with appraisal features and arousal, observation specs), text renders the rows, and gold is computed from the rows by two independent code paths that must agree on every query. One RNG stream per event, so a world can have an event deleted or swapped without changing anything else (ablated and twin worlds).

- Memory content tested: who one is and its updates (identity, as-of), episodes (yesterday's breakfast), incidental details in third-party articles (the car colour), central versus peripheral pairs across the arousal range, sleeper remarks, counts, abstention and false premises. Later: source attribution, false memories, prospective memory, multi-hop.
- The feeling-like signal is a dial, not an assumption: the coupling between arousal and later need ranges from adverse through zero to strong, the channel (a noisy heartbeat-like measurement) has a reliability grid, and every claim is stated against shuffled, random, constant, inverted, absent, oracle and leaky versions of the same channel. A pass at strong coupling is expected by construction; the deliverable is a response curve and a break-even point, never a statement about the live account.
- Roles of the signal: retention under a budget (primary), retrieval boost, narrowing (a planted effect), each reported apart.
- Character change is tested as conformance to an authored, bounded rule (selective, valence-specific, capped, persistent), not as psychology: retrieval-level (free) and agent-level (paid).
- Experiments: X0 instrument gates and X1 value of the signal at the gate are free (no model) and are the first to register; X2 to X7 (reader calibration, signal with a reader, a product with and without the gate, narrowing, character, write-back) are paid, in tranches of at most 12 USD ledger in total, released by recorded decisions.

## 7. Order of work

Done: statistics and record contract; the T0 battery on real replay data; the shared memory module in the interface the writing agent asked for (merged, tested on Python 3.11, 3.12 and 3.14, mutation-checked).
Now: R1, whether the server needs an embedder (preregistration being reviewed; result goes to the writing agent's session before it decides); LifeSim D1 (foundations, world and channel, text, queries and scorers, systems and gates), then X0 and X1.
Next: WMB T1 bank with the memory-dependence filter and sealed split; arms and adapters; T2 opportunity sets; the Docker runner with proxy-only egress; Hindsight and Mem0 as black boxes; T3 and T4; the T6 plan. The first paid LifeSim tranche only after X0 and X1 have recorded decisions.

## 8. What needs the owner

- Reading about 60 pairs of notes in the dark (about 1.5 hours; some with a callback, some without) to decide what "good memory use" means for this account. The judge cannot decide it.
- Releasing the first paid LifeSim tranche (X2 and X3, at most 5.5 USD ledger, about 7 USD real) after X0 and X1 are done. X0 and X1 need no approval.
- The licensing decision for the generator and the sealed seeds (a public generator is credible but invites contamination), and whether a Polish partition comes early or late.

## 9. Not claimed

No result of this page applies to a live agent. Synthetic lives are a proxy for natural text; the appraisal, channel and character constants are assumptions, swept by plus or minus 50% and labelled parameter-dependent when conclusions flip; human phenomena (narrowing, mood congruence, false memories) are diagnostics and planted checks, never the answer key; no tier is called human-level.

## Where the detail is

- `memory-benchmark-research-digest-2026-11-01.md`: WMB tracks, statistics, the harm-check design.
- `docs/05-benchmarks/github-shortlist-and-hardness-2026-11-01.md` and `human-memory-taxonomy-and-episodic-benchmarks-2026-11-01.md`: public benchmarks, hardness plan, the human-memory taxonomy.
- `lifesim-design-panel-digest-2026-11-01.md`: the LifeSim design, families, dials, gates, experiments X0 to X7, build plan, risks.
- `data/lab/wmb-v0/slice0/`: the judge battery. `data/lab/wmb-r1-retrieval/`: the retrieval slice.
- Board and plan of the two sessions: `WSPOLPRACA_NIE.md`, `WSPOLNY_PLAN.md` (outside the repositories).
