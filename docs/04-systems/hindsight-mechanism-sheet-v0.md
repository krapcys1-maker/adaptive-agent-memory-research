# Hindsight — mechanism sheet

Repository: [`vectorize-io/hindsight`](https://github.com/vectorize-io/hindsight) ·
MIT · pinned at `3295716c` (2026-08-23)
Method: read from code. **Claimed and verified are separate sections.**
Tier: I0 — every statement below is a file and line reference, not a measurement.

First entry in the [Comparative Memory Systems Lab](comparative-memory-systems-lab.md),
chosen because `CANDIDATE-0` measurably fails at the component it names as solved.

---

## The finding, before the detail

**Their model/heuristic boundary sits between extraction and resolution. Ours was
in the wrong place, and we have the measurement to show it.**

```
text ──[ LLM, structured output ]──► entity mentions ──[ deterministic ]──► canonical entity
        fact_extraction.py                                entity_resolver.py
```

`E2-A`, `E2-A2` and `E2-A3` tried to make the **first** arrow deterministic —
regex over entity and property grammar. It reached 1.000 internally and 0.000 on
external questions, because rules written for one corpus's grammar do not
transfer.

Hindsight puts a model on that arrow and keeps the **second** one deterministic:
trigram similarity and union-find, no embeddings and no model. So the question
this project has been asking — *where does a model become necessary* — has an
answer in a shipping system, and it is not the answer three of our arms assumed.

---

## Verified from the code

### Extraction is a structured model call

`engine/retain/fact_extraction.py` imports `llm_interface`, `llm_wrapper`,
`parse_llm_json` and `sanitize_llm_output`, and defines Pydantic response models
— `ExtractedFact`, `FactExtractionResponse`, and variants for verbose and
no-causal modes. Entities arrive as `fact.entities`, and
`entity_processing.py:37` names the result plainly:

```python
llm_entities = [{"text": entity.name, "type": "CONCEPT", "resolve": True}
                for entity in (fact.entities or [])]
```

### Resolution is deterministic, and is not embeddings

`engine/entity_resolver.py`, 1405 lines, no model anywhere in the merge path.

**Trigram similarity** (`:74–96`) reimplements PostgreSQL `pg_trgm` in Python —
lowercase, split to words, pad each with two leading and one trailing blank, take
every 3-character window, then Jaccard over the sets. The docstring records that
it was verified byte-for-byte against Postgres across emoji, accent, CJK, hyphen
and apostrophe cases, *so the merge cutoff calibrated on pg_trgm transfers
exactly*. Two reasons given: it keeps in-batch dedup off the retain
transaction's database connection, and it makes the behaviour backend-agnostic.

**Union-find clustering** (`:115–160`) merges similar-name pairs with path
halving, then picks a canonical name per cluster:

```
most-mentioned, then shortest, then lexicographically smallest
```

The comment calls this "a deterministic pick that prefers the plainest spelling
in the cluster". Singletons map to themselves so every member looks up
uniformly.

**Pair finding** (`:99–112`) is `O(N²)` over a capped batch of new names, pure
CPU, no database round-trip — stated as a deliberate trade.

### An escape hatch for exact identifiers

`entity_processing.py:22–26` and `:56–61`. Extracted names always carry
`resolve=True` because they are *the extractor's guess at a name*. Caller-supplied
names carry the caller's own `resolve_entities` flag, and when both produce the
same spelling the caller's intent wins:

> a literal name must not become resolvable just because extraction happened to
> agree on the spelling

So a caller can supply an identifier that is taken **literally** and never
merged, while extraction stays resolvable. That is a distinction this project
has not made and probably needs: `service.billing` may be fuzzy-matched, an
exact commit SHA must not be.

---

## Claimed, not verified here

From the paper and public material, recorded separately because none of it was
checked in the code during this pass: four memory networks separating world
facts, agent experience, entity summaries and evolving beliefs; TEMPR retrieval
running semantic, BM25, entity-graph traversal and temporal filtering in
parallel with cross-encoder reranking; 91.4% on LongMemEval.

---

## Sheet

| Field | |
|---|---|
| mechanism | LLM extracts entity mentions into a typed schema; deterministic trigram + union-find merges them to a canonical name |
| assumption | surface variants of one entity share character trigrams. "Alice" and "Alice Chen" do; "IBM" and "Big Blue" do not |
| what it solves | surface-form variation, which is where our rule-based extractor failed externally |
| what it costs | one structured model call per content item; merging is CPU-only, `O(N²)` on a capped batch |
| where it fails | aliases with no character overlap. Trigram similarity cannot connect "the new PM" to "Alice Chen" unless a model already emitted both as the same name |
| model dependence | extraction only. Zero in the merge path |
| ontology dependence | none required — type defaults to `CONCEPT`. Labels are optional |
| temporal model | not in this file; `occurred_start` and `mentioned_at` are carried on facts |
| provenance | facts carry content index and dates; not audited here |
| context cost | not measured here |
| failure profile | not measured here — no run was performed |

---

## What to take, what to keep, what to study

**Candidate for transplant: the resolution half.** Trigram plus union-find with a
deterministic canonical rule is simple, auditable and model-free. Our arms never
had a merge step at all, so it fills a gap rather than replacing anything, and it
fits an append-only store without modification.

**Its advantage over alternatives is unmeasured.** Reading code establishes how a
mechanism is built and never that it beats one. Nothing here has compared it to
anything on a shared harness, and calling it demonstrated would be the same
claimed-versus-verified slip this project audits other people for.

**Take: the `resolve` flag.** Literal-versus-resolvable is a distinction we lack
and the `RARE-EXC` family is exactly where it matters. A flag like `--dist=no`
must never be fuzzy-matched to `--dist=yes`, and trigram similarity between those
two is high.

**Keep ours: the temporal resolver.** Not present in this file, and our H2 result
(0.200 → 1.000 across five non-monotonic families) has no counterpart here yet.
Graphiti is the comparison, not Hindsight.

**Study: the gap their assumption leaves.** Trigram similarity solves *spelling*
variation and cannot solve *referential* variation. "The new PM" and "Alice Chen"
share no trigrams, so if their extractor does not already resolve the coreference,
the merge step cannot. Whether that gap matters, and how often, is measurable —
and it is a sharper research question than the one we were asking, because it
sits at the boundary of a mechanism built on an explicit, checkable assumption.

## Five classes of variance, and a measured threshold conflict

A first version of this section had three classes and put our `OBSOLETE` family
under *spelling*. That was wrong, and the error mattered enough to measure.

```
1  ORTHOGRAPHIC    Alice Chen · alice chen · Alice C.
                   same entity, different spelling

2  LEXICAL ALIAS   billing service · invoice backend
                   same entity, no shared characters

3  REFERENTIAL     Alice Chen · the new PM · she
                   same entity, resolvable only in discourse

4  IDENTITY        billing staging host · vault staging host
                   DIFFERENT entities, near-identical wording

5  TEMPORAL STATE  old host · current host · future host · correction
                   one entity, several versions, one in force
```

`OBSOLETE` and the 48-near-clone failure are **4 and 5**. They are not spelling.
Trigram similarity answers *are these two strings the same name*; addressing
answers *are these two records about the same object*. Different axes, and
conflating them would have produced a wrong conclusion about what transplanting
their resolver buys us.

### The measurement

Their algorithm, run over examples from each class:

| pair | class | similarity |
|---|---|---:|
| `Alice Chen` / `alice chen` | 1 — should merge | **1.000** |
| `Microsoft Corp.` / `microsoft corporation` | 1 — should merge | 0.609 |
| `Alice Chen` / `Alice C.` | 1 — should merge | 0.583 |
| `service.billing/staging/endpoint.host` / `service.vault/…` | 4 — must **not** merge | **0.707** |
| `billing staging host` / `vault staging host` | 4 — must **not** merge | 0.520 |
| `tests/billing-fuzz` / `tests/vault-fuzz` | 4 — must **not** merge | 0.440 |
| `--dist=no` / `--dist=yes` | must **not** merge | 0.417 |
| `billing service` / `invoice backend` | 2 — should merge | 0.103 |
| `the new PM` / `Alice Chen` | 3 — should merge | 0.000 |

**Class 4 overlaps class 1.** Two distinct services score 0.707, higher than two
spellings of one person at 0.583. **No single threshold separates them.** Any
cutoff low enough to merge `Alice C.` would also merge `billing` with `vault` —
and collision is a gate this project froze at `< 0.02` before any of this.

Class 2 and 3 sit at 0.103 and 0.000, below any usable cutoff. Trigram cannot
reach them at all.

### What that means for the transplant

Not that their mechanism is wrong. It assumes it is comparing **entity names**,
and in their pipeline those come from an extractor that names entities
distinctly. Feeding it a *composed address* like `service.X/scope/property`
violates that assumption, because the shared scope and property tokens dominate
the trigram set and the distinguishing token is a small fraction of it.

So the transplant is conditional, and the condition is precise:

> apply trigram resolution to the **entity component alone**, never to a composed
> address, and never to a value that must match exactly.

`--dist=no` versus `--dist=yes` at 0.417 is why the `resolve=false` escape hatch
is not optional here — it is what keeps a flag from merging with its opposite.

### What is not known

The earlier draft said classes 2 and 3 are untouched by anything either project
has built. That is not established. Hindsight's **extractor** runs before the
deterministic merge and may already resolve some aliasing and coreference —
their own example, *"Alice", "Alice Chen" and "the new PM" all map to the same
person*, is a class 3 claim, and nothing in `entity_resolver.py` could achieve it.

So the honest statement is that **it is not known how much of classes 2 and 3
these systems resolve, or at which stage.** The shared arena is what would show
it, and this is one more reason to run the arena before reading further code.

## Consequence for CANDIDATE-1

The arms that tried deterministic extraction are not to be extended. The reading
is not "regex was a bad idea" but "the deterministic component belongs one step
later than we put it". `CANDIDATE-1` should be:

```
model extracts mentions into a controlled schema
        ↓
deterministic trigram + union-find merge, with a literal escape hatch
        ↓
our addressing and temporal layers, unchanged
```

and the marginal contribution to measure is what our layers add **on top of** a
resolution step that already works — which is a much better-posed question than
whether we can rebuild theirs.
