# Bootstrapping strategy

The memory we build is the memory we use to build it. This page states that as a deliberate strategy, names what it buys, and names what it costs — because until now it was implicit, and an implicit strategy cannot be argued with.

## The claim

The project-memory tool has three roles at once:

1. **Working infrastructure** — it carries research continuity across sessions and agents.
2. **A corpus** — it accumulates real usage traces at zero cost.
3. **A source of hypotheses** — using it seriously surfaces failures that designing a test would not.

Borrowed designs come in from outside; measurement of them happens here.

## What it has already bought

Three defects were found by *using* the memory, not by reasoning about it, and none would have appeared in an authored fixture:

- **Retrieval starvation.** `CURRENT_STATE.md` consumed the entire context budget; all twelve retrieved documents received zero characters. Invisible until a bundle was inspected under a real query.
- **A disconnected graph.** 89.1% of events had no edge at all, while 57 shared source references sat unmaterialized.
- **Silence in the owner's language.** Questions whose answers were written the same day returned zero memories in Polish and four in English.

It also solves a problem the preregistration triage exposed: **0 of 21 registered experiments have a corpus.** This one exists and grows on its own.

## Why the corpus is unusually good

Most benchmark corpora are authored, and an authored corpus can be tuned to, consciously or not. This one was produced by real work before anyone knew what would be measured against it. That is close to the ideal condition for independence tier I1 — the data could not have been shaped to flatter a candidate that did not yet exist.

That property is fragile and is protected by a rule below.

## Three ways this fails

### 1. N = 1

One agent, one project, one maintainer, 185 events, predominantly English. A mechanism that works beautifully here may not survive a different scale, a different domain, or several users. This is the largest risk and it is not fixable from inside — only replication elsewhere addresses it.

**Rule:** every finding derived from the project's own memory is labelled `self-observed, n=1` and may not be promoted past tier I1 on that evidence alone.

### 2. The tool shapes the data it is measured on

`PMLAB-ASSOC-E2` already brushed this: tags authored by the agent running the experiment became graph edges. Stratifying the gold caught it, and the mechanical stratum turned out to agree with the tag stratum, so the estimate was not inflated. But the risk was structural rather than accidental, and it will recur.

**Rule:** memory content is never authored to suit a feature under test. If a mechanism needs particular data to show its effect, that data belongs in a separate fixture, not in the canonical log.

### 3. Dogfooding prioritises irritation, not importance

The context-budget defect was fixed within an hour of being noticed because it was annoying. Research question 3 — how future utility is measured causally rather than by retrieval frequency — irritates nobody and has stood untouched for months.

**Rule:** at least one item in flight must serve a research question rather than a usage complaint. The operating doctrine's selection rule already scores by falsification value; this is the reminder to apply it to ourselves.

## The line that must not move

`CLAUDE.md` states:

> The current project-memory tool supports research continuity. It is not evidence that the proposed final memory architecture works.

This strategy does not weaken that. Using our own memory as a corpus produces **hypotheses and measurements**, never validation of the architecture. The distinction is operational, not rhetorical:

| Our memory can | Our memory cannot |
|---|---|
| generate a Tier E result | support a confirmatory claim |
| expose a failure mode | show that a mechanism generalises |
| supply a held-out corpus for I1 | substitute for I4 or I5 |
| falsify a design | confirm one |

A finding graduates by passing a sealed held-out test, a measured cross-family panel, or human review — the same ladder as anything else. Origin inside our own tooling earns no discount.

## Borrowing

Designs are borrowed rather than invented wherever a mature answer exists. The recorded project decision is a composite reuse architecture rather than adoption of any single memory product: reuse narrow audited boundaries behind project-owned, evidence-first interfaces.

Borrowing carries its own obligations, all of which already exist in `CONTRIBUTING.md`:

- every claim about another system cites a pinned revision or version;
- what a system demonstrably does is separated from what its documentation claims;
- whatever the borrowed model leaves unsolved is listed explicitly, so it is not inherited silently.

Testing someone else's solution is expensive — each needs a harness, and a fair comparison needs matched corpora. **A comparison requires a registered question, not curiosity.** Without that rule, benchmarking becomes a hobby that produces activity instead of answers.

## The loop, stated plainly

```
use the memory for real work
  -> a failure surfaces that no fixture would have shown
  -> check whether a mature system already solved it        (doctrine rule 1)
  -> borrow the semantics, or design if nothing exists
  -> measure on our own corpus as Tier E
  -> if it holds, promote through a sealed held-out test
  -> the improved tool carries the next round of work
```

Each turn of the loop makes the tool better and the corpus larger. The corpus growing is not a side effect; it is the point.
