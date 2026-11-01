# Shadow-memory audit and baseline measures (stage N2): specification, draft v0

**Status: draft.** Nothing is built and no data exists yet. It specifies what the research side will compute from the shadow records of the live agent (stage N1) and from its existing history, so that stage N3 (live memory in a randomised arm) can be judged ready or not. It follows the [evaluation protocol draft](live-agent-memory-evaluation-protocol-draft-v0.md). Facts about the agent are reported by its own session. The record fields are those of the shared plan (record v0, with the changes the agent's session announced before the first data).

## 1. Privacy and where it runs

The shadow records hold keyed hashes of the target text and its author, item identifiers, ranks, scores and token estimates; never the target text. The analysis therefore needs only the agent's own published texts, which are public, and the records. It runs where the data lives or on a pseudonymised copy kept outside this repository and outside the agent's repository. Only aggregate tables and synthetic fixtures may enter this repository. Judging uses a local model on own texts only; nothing derived from third parties goes to an external service.

## 2. Part A: audit of the shadow records (no outcomes involved)

1. **Integrity.** Records against comments actually sent (joined by the keyed target hash and time); status distribution (`ok`, `degraded`, `timeout`, `error`); duplicate record ids; schema versions; latency percentiles; file growth per day; share of records that came from dry runs or tests (excluded from everything else).
2. **Coverage** per profile (production thresholds and the two looser ones), by task type and by arm of the live experiment: the share of comments for which the memory returns at least one item (the existing block returned none in 16 of 16 comments of one arm, reported), items per comment, estimated tokens.
3. **Mechanical quality proxies** on own texts: repeat risk (longest n-gram overlap between each returned item and the comment actually posted); diversity (distinct items across consecutive comments); recency (age distribution); same-correspondent share (records whose author hash matched an earlier record), which is where the rule for memories of named third parties applies.
4. **Sampled judgement**, 100 comments stratified by arm and by coverage: for each, a pre-registered prompt (fixed model, temperature 0, prompt hash recorded) shown only the posted comment and the returned items' own texts judges duplicate, contradiction and relevance to what the agent wrote. This is a proxy for relevance to the target, whose text is not stored; say so in every table. The owner spot-checks 20; report agreement.

## 3. Part B: baseline measures computed backwards from the history (read-only)

Three candidate primary measures are computed on the roughly 78 days of past comments and notes: a **callback rate** (the item explicitly refers to an earlier own item, by rule), a **repetition rate** (maximum 5-gram overlap with own items of the previous 30 days above a fixed threshold), and a **contradiction rate** (sampled pairs, judged as above). For each: daily and weekly rates, the day-to-day variance and the intra-day correlation, and from them the minimum detectable difference of a randomised comparison at exposures of 10%, 25% and 50% over 30 days. The owner then chooses the primary measure with the detectable difference stated.

## 4. Proposed readiness criteria for N3 (for the owner to set)

At least 99% of records with status `ok`; p95 latency and run duration within a stated margin; the candidate profile returns something often enough to matter; no blocker in the sampled judgement; no personal-data pattern in the file; the primary measure chosen and its detectable difference stated; kill switch and stop conditions tested. The decision and its date are recorded in the shared plan.

## 5. Outputs

Aggregate tables per part, the scripts (with synthetic fixtures for their tests) in this repository, and one short report. No agent data in the repository.
