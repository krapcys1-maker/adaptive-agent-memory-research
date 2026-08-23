# Operating plan and working rules

Written so this work can continue autonomously. It carries two things: **what
happens next, in order**, and **the rules that constrain how**.

Most rules below exist because something went wrong first. Where that is true it
is said, because a rule with its failure attached is remembered and a rule
without one is decoration.

---

## The plan

Four phases. **Each finishes before the next begins.** The reason is the failure
mode this replaced: reading one system, finding an interesting mechanism, and
disappearing into it — which produces deep knowledge of one repository and no
comparable results.

### Phase A — build the arena

Every system through the same harness. Per system, in order:

```
adapter  →  ARENA-0 fixtures  →  operational fit  →  infra dry-run  →  frozen run  →  PUT IT DOWN
```

| system | status |
|---|---|
| AAMR (reference) | **pilot done, $0.00.** Stored nothing on 996 turns, abstained 4/4 |
| CUPMem | **operational fit PASS**, nine of nine. **Pilot done, $1.5892** |
| Mem0 | **pilot done, $0.2939.** No model at query time |
| Hindsight | **pilot done, $1.8123.** pg0 embedded Postgres, local embeddings |
| Graphiti | **BLOCKED.** Neither embedded backend runs here; adapter written, mechanism unmeasured |
| Letta, MemOS, Cognee | later, if the first four leave a gap |

**"Put it down" is a rule, not a suggestion.** After a system's frozen run, no
tuning, no analysis of why it won or lost, no reading further into its code.
Move to the next adapter. Analysis is Phase B and it needs every system's
results to be worth anything.

The dry-run is 10–20 units and exists only to catch infrastructure: reset
leakage, billing, nondeterminism, token accounting, timeouts. **Fix adapter and
infrastructure defects only.** "This system answers this class badly, let us
change its retrieval" is tuning a competitor on the arena and voids the run.

### Phase B — analyse

Only once every system has a frozen run.

```
common results → per-probe error matrix → failure profiles → phi correlations → category winners
```

The output is **not a leaderboard**. Four systems within a few points of each
other on an aggregate says nothing about what to compose. What is wanted is a
profile per failure mode, an error-correlation matrix, and a cost column.

Then, and only then, code gets read — **under a measured effect**:

> Hindsight won spelling. Open `entity_resolver.py` and find out why.

### Phase C — transplants

One block at a time, never a Frankenstein first:

```
BASE          BASE + A          BASE + B          BASE + A + B
```

```
interaction = S(A+B) - S(A) - S(B) + S0

  ≈ 0   additive — the mechanisms address different failures
  < 0   redundant, or they interfere
  > 0   synergistic
```

Combining everything at once means a higher number and no way to know why.

### Phase D — a second arena

Arena #1 compares. **Arena #2 tests whether the profiles transfer**, and must be
a benchmark whose questions were never inspected.

STALE is no longer that. Its question text was read during the grammar-coverage
audit — gold, labels and scoring were not, and the audit was worth its cost — but
the strongest sealing property is spent. MemoryAgentBench conflict resolution or
LongMemEval-V2 are the candidates.

---

## Working rules

### On measuring

**Freeze before measuring.** Thresholds, implementations and seeds get a digest
before a result exists. *After seeing 87% it is easy to decide 87% is fine, and
for a memory system 87% may mean catastrophic drawer-mixing.*

**A negative result is a result.** Three of the six findings on the front page
are negatives and one is a retraction of our own work. `E2-A` failing at 0.143
is recorded as the preregistered failure it is.

**Report the vector, never the scalar.** `POISON` scored a perfect 1.000 on
answering while surfacing the poisoned instruction on a quarter of probes. One
number scores a confabulator and an abstainer identically.

**A test that has never failed is not evidence.** The independence proof passed
while the generator was deliberately mutated to read the history — with the
history absent, the leaking branch never ran. Mutate the code and watch the test
fail before trusting it.

**Properties over examples, for anything that aggregates.** Six defects in
combining measurements this session: three found by reading output, three by
commutativity, identity and associativity, **none** by the example tests that
were already green.

**A property test passing is not the property holding.** Rounding each float sum
to microseconds looked associative: 400,000 random triples found no violation. A
targeted search at the half-microsecond boundary found **17,338 violations in
54,872 triples**. Random values almost never land on the boundary. Where a
property can be made exact by construction — integer microseconds rather than
rounded floats — make it exact rather than testing for it.

**A double written by the adapter's author certifies the adapter, not the
system.** CUPMem's double agreed with its adapter in all five places the adapter
was wrong, because both were written from one reading of their surface. A double
is evidence only where it can disagree with the thing it is testing, so it must
quote the system's code, and something must re-check the quotations. Fixing one
field last session left the class untouched and four more were waiting.

**A repeated probe cannot detect mutation against a sampling decoder.** At
temperature 0, deepseek-chat returned 4 distinct outputs in 20 identical
free-form requests and 3 in 20 structured ones. So *ask twice and compare* reads
a decoder as a store that learned, and it rejected an adapter whose state digest
was byte-identical either side of the query. Fingerprint the state instead —
another case of a property that can be settled by construction rather than
sampled for.

**Internal corpora are diagnostic instruments only.** H1 and H2 answer *why a
system failed*. They cannot answer *whether it works elsewhere* — they were
written by the author of the mechanisms they score, and disjoint splits control
for wording, not for knowing the case taxonomy.

**Do not tune on an external benchmark.** It becomes a development set the
moment it is used that way, and the only property it was wanted for is gone.

### On distinctions that must not collapse

Each cost something to learn.

```
admissible ≠ good              the contract is obeyed; the system may still be terrible
structural fit ≠ operational   the three methods exist; deriving evidence and cost is separate
capability ≠ observability     90% with no evidence and 87% with full evidence differ in kind
unknown ≠ zero                 else the blindest system looks cheapest
known partial ≠ known total    a floor is not a total; keep the number, mark the floor
claimed ≠ verified             reading code establishes construction, never advantage
```

### On correcting

**Supersede, never edit.** A correction keeps the original claim and the reason
it was wrong attached to each other. Used on: *a model is needed for property
resolution*, *Hindsight's resolver demonstrably works*, *the contract survived
first contact*.

**Correct overclaims in our own record first.** The claimed-versus-verified slip
we audit others for was committed in this project's own first mechanism sheet.

### On prior art

**Selection rule 1 applies to the architecture, not only to mechanisms.**
Applying it only to individual mechanisms produced an architecture identical to
APEX-MEM, published with better numbers before we measured ours.

**Existing systems are the floor.** Order: our failure mode → our hypothesis →
prior art → take a working component if one exists → measure only our marginal
contribution.

**A mechanism carries its representation level.** Trigram similarity is sound on
entity names and unsound on composed addresses — 0.707 for two distinct services
against 0.583 for two spellings of one person. Transplanting a mechanism without
the representation it was designed for is the error, not a shortcut.

### On the arena specifically

**Translate, never interpret.** An adapter reports what happened; the harness
decides what it means. An adapter emitting `failure_type` would be grading its
own exam, and the failure matrix would become an artefact of five opinions.

**Cost is part of the mechanism.** Ingestion calling a model per item is not free
because the call happens early. 90% with paid ingestion against 88% with no model
calls is not obviously a win for the first.

**If a system fails operational fit, question the requirement first.** Not *how
do we work around it*, but *should the arena require this at all, or only because
our own system happens to have it*. A requirement no independent system can meet
is a finding about the requirement.

**One adapter is a self-contained contribution.** The contract is frozen with a
digest and `validate` rejects mechanically, so an outside contributor needs no
understanding of this project.

### On spending

This is funded out of one person's pocket, which is a constraint on the design
and not only on the accounting. It is why the dry-run became a four-unit pilot.

**A cap is enforced below the system, or it is a report.** The arena's provider
wrapper refuses the request that could cross the ceiling, using the most
expensive call so far as its reserve, so it stops under the line. Checking after
the call is how one finds out about an overspend rather than preventing it.

**A rate measured on a fixture is not a rate.** The first projection came from
four single-turn synthetic sessions and was wrong twice over: it over-stated
calls per session, and it missed that cost grows as the store fills. Measure the
rate on the corpus that will be run.

**Report the model you believe and the one you fear.** The pilot projection
carries $1.84 and $4.00 and says which is which and why. A projection that
reports only its preferred number is a hope.

Total spend to date is under $1.50. Every finding on the front page except the
reader runs cost nothing.

**Run the free version first.** The stub caught nothing the paid pilot then found
— four harness defects in ten probes for $0.004 — but the free grammar-coverage
audit prevented an entire wasted external run.

**Bound spend before the fact.** The runner refuses to start when the projection
exceeds a ceiling, and a test asserts the refusal precedes any call.

**Record cost per call, not per run.** A background run died after 29 calls with
no result file; the ledger still had the $0.014.

---

## Immediate next steps

The dry-run became a **pilot**: four units rather than ten to twenty, about a
tenth of the bridge, sized to what a hard cap buys. It is not a leaderboard and
four units cannot be one.

1. ~~Real CUPMem against ARENA-0 fixtures.~~ **Done. Nine of nine, accuracy not
   scored.** Source, embedding revision and decoding pinned; cost native and
   fully known; the query path read-only over state, proved by fingerprint.
2. ~~Decide a corpus.~~ **Done.** LongMemEval-S cleaned, its own frozen
   four-unit selection — not `bridge-v0`, which was frozen for a
   lexical-retrieval protocol under a different question. Stratified on user
   turns, one unit per regime, four distinct question types, frozen before
   anything ran.
3. ~~Amend the contract.~~ **Done.** ARENA-0.1 splits `query_mutates_state`
   from `output_reproducible`. ARENA-0 stays unedited.
4. **Pilot CUPMem under a $3 hard cap**, enforced beneath the provider so it
   refuses the request that would cross rather than reporting an overspend.
   Projected $1.84 on the believed model, $4.00 on the pessimistic one.
5. **Stop.** No 36-unit run, no second pass, no further system, without a new
   decision. The question the pilot answers is whether there is any signal worth
   paying more for.
6. Then Hindsight, Graphiti, Mem0 — same sequence, each with its own projection.
7. Phase B.

## Open blockers

- **Cost is not linear in corpus size.** CUPMem's calls per session ran 5.6 over
  the first half of a fifteen-session calibration and 13.1 over the second: an
  empty store has nothing to invalidate. So a dollars-per-record figure depends
  on how much the system already remembers, and two systems measured at
  different corpus positions are not comparable on cost. Whether it plateaus is
  believed, not proved; the pilot's per-session series is recorded to settle it.
- **A frozen run will not be reproducible.** The decoder is not deterministic at
  temperature 0, so a per-probe difference between two systems carries variance
  that has not been separated from the systems. Repeating each probe *k* times
  measures it and multiplies the cost by *k*. The pilot does **one** pass and
  reports the decoder's variance from a separate cheap probe instead.
- **`evidence_ids` is underspecified: whose id space?** The reference adapter
  returns arena record ids because it stores the records. CUPMem returns its own
  item ids, because it stores facts it extracted. The harness cannot ask *was the
  gold record retrieved* across both. Per the rule below, question the
  requirement first: record-level evidence provenance may be a requirement that
  exists only because our own system happens to have it.
- ~~The frozen contract's `read_only` is stronger than read-only.~~ **Resolved
  in ARENA-0.1**, which measures state through a probe and reproducibility by
  repetition, and never infers either from the other.
- Arena infrastructure: databases for Graphiti and Hindsight; API budget for
  systems whose ingestion calls a model
- `MemEval` may carry the harness — audited in #35, with the recorded caveat
  that its constants are repeated per adapter rather than enforced
- Six prior-art systems reported and unverified (#48)
- Nothing external has confirmed any internal effect yet

## The question this is all for

> **When is deterministic addressable state sufficient, and where exactly does a
> model become necessary?**

Structured memory exists (APEX-MEM). Temporal validity exists (Graphiti). State
resolution exists (A-TMA). Similarity failing on near-clones is measured
(Tenure). What none of them isolates is **the margin** — how much of the work a
model is assumed to be needed for can be done without one, and which residue
genuinely cannot.
