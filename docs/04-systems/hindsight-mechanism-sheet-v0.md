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

## Three classes of variance, and trigram covers one

Their assumption makes the taxonomy visible:

```
1  SPELLING       Alice Chen · alice chen · Alice C.
                  → trigram similarity. Solved here.

2  LEXICAL ALIAS  billing service · invoice backend
                  → alias table or semantic match. Not solved by trigram —
                    the strings share almost no characters.

3  REFERENTIAL    Alice Chen · the new PM · she · her replacement
                  → coreference over discourse. Not a string problem at all.
```

`OBSOLETE` in our own corpus is class 1. The near-clone failure that motivated
addressing is class 1 as well — twelve services phrased identically. Classes 2
and 3 are untouched by anything either project has built, and no measurement
here says how often they occur.

That is a map of the problem rather than a choice of embedding, and it is the
more useful output of this reading.

---

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
