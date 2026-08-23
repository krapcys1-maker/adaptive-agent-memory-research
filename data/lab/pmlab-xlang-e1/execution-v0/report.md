# PMLAB-XLANG-E1 — retrieving project memory in the maintainer's language

Experiment ID: `PMLAB-XLANG-E1`
Tier: **E (exploratory)** — model-free, no weights downloaded, no network, no API cost
Authority: development measurement only. Not confirmatory, not independently reviewed.

## Design

Language is the only variable. For each of 45 sampled memories, taken as every fourth active memory by sorted id:

- the **English** query is its title *verbatim*;
- the **Polish** query is a natural translation of that same title.

The target is the memory's own id, known by construction, so no relevance judgement is authored. English recall is expected to be perfect because the query is the target's own text. That is the control: it makes any shortfall in Polish attributable to language alone.

## Results

| Arm | EN R@5 | EN R@10 | PL R@5 | PL R@10 |
|---|---|---|---|---|
| **B1** FTS5 only | 1.000 | 1.000 | **0.156** | **0.156** |
| **B2** FTS5 + association graph | **0.711** | 1.000 | 0.133 | 0.156 |
| **B3** FTS5 + domain glossary | 1.000 | 1.000 | **0.800** | **0.867** |

```
Polish queries returning zero candidates : 26 / 45
mean candidates returned    EN 50.0  |  PL 6.7

graph gain    @10  +0.0000   95% CI [+0.0000, +0.0000]
glossary gain @10  +0.7111   95% CI [+0.5778, +0.8444]
```

## Three findings

### 1. The gap is a collapse, not a degradation

Recall falls from 1.000 to 0.156 with nothing changed but the language of the question. **More than half of Polish queries — 26 of 45 — return no candidates at all**, so the store does not return a poor answer, it returns silence. Mean candidate count drops from 50.0 to 6.7.

This is the recorded "zero cross-language recall" of FTS5, measured on the memory the maintainer actually owns.

### 2. The association graph contributes exactly nothing here — and the reason matters

Graph gain is **+0.0000 with a confidence interval of [0.0000, 0.0000]**. Not small. Zero, on every query.

The cause is structural rather than incidental. Graph expansion is seeded from the top lexical hits. When lexical search returns nothing — which is what happens in 26 of 45 Polish queries — there are no seeds, so there is nothing to expand from.

> **A graph layered on top of lexical retrieval cannot rescue a query that lexical retrieval cannot start.**

`PMLAB-ASSOC-E2` registered cross-language as its untested case and speculated the graph might help precisely here. It does not. That speculation is now refuted.

### 3. A trivial glossary recovers most of the gap

A hand-built Polish-to-English term map, about a hundred entries of general project vocabulary, lifts Recall@10 from 0.156 to 0.867. The paired interval is far from zero.

This is the cheapest imaginable remedy and it works better than the sophisticated one.

## A correction to PMLAB-ASSOC-E2

Look at **B2 in English at depth 5: 0.711 against B1's 1.000.**

On queries where lexical search already returns the correct answer first, graph fusion **pushes the target out of the top five in 29% of cases** by injecting neighbours above it.

E1 measured and reported this displacement cost. E2 dropped the metric, and its report therefore told only the favourable half of the story. The honest combined reading is:

- on hard queries the graph helps a little — E2 measured about +0.05;
- on easy queries it hurts a lot — measured here as −0.29 at depth 5;
- when lexical returns nothing it does nothing at all.

E2's conclusion is not withdrawn, but it is incomplete as published, and the displacement metric must be restored before the graph is promoted to a sealed test.

## Limits

- **Local dense retrieval is not tested.** Config and tokenizer files for `multilingual-e5-small`, `bge-m3` and `paraphrase-multilingual-MiniLM-L12-v2` are cached under `external/models`, but the weights are absent. Testing would mean downloading roughly two gigabytes and adding an inference runtime — a maintainer decision, not one an exploratory run should take unilaterally. It remains the most likely real fix, since it needs no glossary and handles paraphrase.
- **The glossary is hand-built and will not generalise.** It covers about a hundred terms someone thought of, is unweighted, and cannot handle paraphrase or vocabulary outside this project. It establishes that a trivial remedy closes most of the gap; it is not the answer.
- **The Polish queries are authored.** The gold is mechanical — a memory's own id — but the translations are the author's. A translation that happened to preserve a distinctive rare token would flatter B1.
- **Title-verbatim English queries are unrealistically easy.** That is deliberate, to isolate language, but it means the English column is a control rather than a performance estimate.
- 45 queries, one corpus, one language pair, `n = 1` project.

## What follows

1. **Ship the glossary.** It is cheap, it works, and its weaknesses are known. Not as the answer — as the stopgap that makes memory usable for its owner today.
2. **Ask the maintainer about dense retrieval.** It is the likely real fix and needs an explicit resource decision.
3. **Restore the displacement metric to the association experiments** before any promotion.
4. **Stop seeding graph expansion only from lexical hits.** Any structure that can only start where lexical search already succeeded inherits lexical search's blind spots exactly.
