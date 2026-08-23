# Operating doctrine

One page answering: what do we test next, and why that one?

Everything else in `docs/00-project/` says what **blocks** a claim. Nothing said what to **pick**. That gap is why 23 of 66 registered experiments never ran and 16 more produced results without a recorded decision: every candidate was equally registered, so none was prioritised.

## The five questions we are actually answering

From [`research-questions.md`](research-questions.md). An experiment that does not move one of these is not worth running, however interesting.

1. What is the atomic unit of agent memory?
2. How is storage failure distinguished from retrieval failure and reasoning failure?
3. How is future utility measured causally rather than by retrieval frequency?
4. When should episodes be consolidated into semantic or procedural knowledge?
5. How are memories updated without losing provenance, uncertainty, or superseded states?

## Selection rule

Score each candidate on four factors, then take the highest score that fits the WIP limit.

**1. Does the answer already exist?** Before designing anything, check the benchmark catalog, the evidence ledger, and published work. An experiment that reproduces a known public result buys nothing but confidence in our harness — which is sometimes worth it, but must be labelled as harness validation, not discovery.

**2. What would it rule *out*?** Score by falsification value, not by what it might show. A test that can only confirm is worth little; a test that would kill a mechanism if the mechanism is wrong is worth a lot. If no plausible outcome would change what we do next, do not run it.

**3. What does it cost, and can it run today?** Three tiers:

| Tier | Cost | Gate |
|---|---|---|
| **E** exploratory | hours, model-free, existing data | none — run it |
| **C** confirmatory | days, sealed split or fresh corpus | I1 sealed split minimum |
| **X** expensive | weeks, API budget, external review | explicit approval and a registered cap |

**Bias hard toward E.** A Tier E result today beats a Tier C design that sits unexecuted for a month. `PMLAB-ASSOC-E1` and `E2` exist because of this rule.

**4. Does it unblock other work?** A mechanism that several blocked items depend on outranks a self-contained curiosity of similar cost.

## Work-in-progress limit

**At most two experiments per track may sit in "designed, not executed".**

This is the hard rule that keeps the doctrine honest. When the limit is reached, the next action is to execute or retire something, never to design another. Retirement is a legitimate outcome and is recorded, not deleted.

## What counts as success

Success is **a recorded decision**, not a positive result.

An experiment succeeds when it produces a `result` and a `decision` in the registry, whatever direction the result points. `PMLAB-ASSOC-E1` was inconclusive and is a success: it registered the resolving step, which `E2` then executed.

An experiment fails when it produces neither — when it runs and nobody writes down what follows. 16 registry rows are currently in that state and each is a debt.

Every row needs `primary_metric` and `practical_threshold` **before** execution. 64 of 66 have them; the exceptions are the two Tier E runs, where the doctrine permits a descriptive label instead, provided the label is registered honestly.

## Promotion path

A finding climbs, and each step is cheap enough to actually take:

```
Tier E exploratory result
  -> repeat at larger n or with a second mechanism   (still Tier E)
  -> sealed held-out test under I1                   (scripts/sealed_split.py)
  -> cross-family decorrelation measured under I3
  -> human micro-task panel under I4
  -> full expert blind review under I5
```

See [`independence-ladder.md`](independence-ladder.md). The point of the ladder is that the first three steps need **no reviewer, no model, and no budget**, so a result can travel a long way before it needs anything scarce.

## Where to invest

In descending order of expected information per unit cost:

1. **Mechanical gates that remove a reviewer from the critical path.** The claim audit found six broken freezes on its first run; that is work no human would have done reliably.
2. **Instruments that make results cheap to obtain.** The sealed split harness cost one session and unlocks every future held-out test.
3. **Experiments on our own memory.** It is the only corpus we hold that was produced by real use rather than authored for a benchmark, and it grows on its own.
4. **Reading primary sources for mechanisms we are about to build.** Cheaper than discovering the same failure empirically.
5. **Anything requiring API budget or an external reviewer.** Last, because both are scarce and neither is under our control.

## What we deliberately do not have

**An architecture.** The project refuses to name one until evidence supports it, and that refusal is a decision rather than an omission. The cost is real: there is no target to converge on, so progress is measured by claims retired rather than by a system taking shape.

The condition for revisiting this: when three independent mechanisms have each passed at least tier I1, propose an architecture that uses all three and register it as a hypothesis like anything else.

## Rules of work

- Preserve negative results, failed runs, and rejected ideas as labelled evidence.
- Never rewrite a frozen artifact to make an audit pass.
- Revise a conclusion by appending a supersession with a reason, never by editing history.
- Record the independence tier that actually produced a claim; no claim inherits a tier from a neighbour.
- Every factual claim carries provenance. Findings and failures require a source reference, and the mechanical gate enforces it.
- State a limitation in the artifact that has it, not in a document nobody reads.
- When a measurement contradicts an expectation, the measurement wins and the expectation is recorded as refuted.
