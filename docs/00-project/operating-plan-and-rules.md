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
| AAMR (reference) | adapter done, admissible, abstains on all fixtures |
| CUPMem | adapter done against a double; real fixtures next |
| Hindsight | not started |
| Graphiti | not started |
| Mem0 | not started |
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

1. Real CUPMem against ARENA-0 fixtures — reset, session and time semantics,
   answer shape, abstention, evidence and cost observability, query-time state
   mutation. **Ignore accuracy entirely.**
2. If operational fit passes: 10–20 unit infra dry-run.
3. Freeze adapter and config; frozen run; **put CUPMem down**.
4. Hindsight adapter. Same sequence.
5. Graphiti, then Mem0.
6. Phase B.

## Open blockers

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
