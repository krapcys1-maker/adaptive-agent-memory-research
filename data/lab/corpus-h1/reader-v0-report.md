# PMLAB-H1-READ-E1 — retrieval answers more and is the only arm that answers wrongly

Experiment ID: `PMLAB-H1-READ-E1`
Tier: **E (exploratory)** — author-operated, single model family, synthetic corpus
Authority: development measurement only. Not independently reviewed, not confirmatory.
Cost: **$0.077** across both arms, 168 calls.

## The comparison

Two arms, one shared 250-token budget, one reader (`deepseek-v4-flash`), 84 delayed probes.
The budget is the control: an arm handed more context answers more and demonstrates nothing.

```
arm            gold  answered   leaked   empty  abstained
recency       0.000     0.000    0.000   0.000      0.976
fts5          0.881     0.845    0.119   0.000      0.000
```

`answered` by family:

| arm | BILINGUAL | DELAYED | FAILFIX | OBSOLETE | POISON | RARE-EXC | REDERIVE |
|---|---:|---:|---:|---:|---:|---:|---:|
| recency | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fts5 | 1.000 | 0.750 | 1.000 | **0.167** | 1.000 | 1.000 | 1.000 |

`leaked` — answered from the record the case was built to trap:

| arm | OBSOLETE | every other family |
|---|---:|---:|
| recency | 0.000 | 0.000 |
| fts5 | **0.833** | 0.000 |

## What this shows

**Retrieval wins overwhelmingly on answering, and it is the only arm that produces
wrong answers.** Recency answers nothing and invents nothing. Retrieval answers 84.5%
and is confidently wrong on 11.9%.

Reporting only `answered` would rank these arms and hide that entirely. Reporting only
`leaked` would rank recency first for producing no answers at all. Neither number is the
result; the pair is.

**Naive compaction fails safely here.** Given a window containing nothing relevant, the
reader said *I do not know* on 97.6% of probes rather than confabulating. That is worth
stating precisely because it is the opposite of the story a benchmark like this is
usually built to tell. Compaction's failure on delayed questions is total and it is
honest about it.

**The OBSOLETE family is where retrieval breaks, and it breaks badly.** 0.167 answered
against 0.833 leaked: on five probes out of six the reader returned the *superseded*
host, confidently and without hedging.

```
need   staging-coral.internal
said   Billing should deploy to https://staging-green.internal:8879.
```

The obsolete host is stated three times over eleven days and its correction once,
tersely. Frequency, order of establishment and length all point at the wrong record, and
a lexical retriever follows them there. This is the single clearest argument in the
project so far for the thing it was set up to investigate: **retrieval by similarity
answers *what looks like this query*, not *what is currently true*.**

## What this does not show

- **One model, one family.** No cross-family panel, so this is tier I0 evidence about
  the corpus and tier "asserted" about the reader.
- **Synthetic corpus, authored by the same agent that wrote the protocol.** The
  bootstrapping strategy flags this as the standing limitation; it is mitigated by the
  generators being deterministic and inspectable, not removed.
- **Two arms of four.** `frequency` and `random` have model-free retrieval numbers
  (0.000 and 0.048 gold) but were not read.
- **One budget.** At 250 tokens and this event density, recency reaches back about one
  day. A larger budget would change its number and might change the ordering; that is a
  measurement waiting to be made, not a caveat that excuses this one.
- **No repetitions.** Single run per arm, so no interval is reported and none should be
  inferred.

## Five harness defects found by running it

None of these was visible to the free stub. All were found by paid probes costing
$0.021 in total, which is the argument for piloting before a full run.

1. **Every instance of a family shared its question.** Three families varied nothing, so
   twelve instances asked one question with twelve different gold answers. Unanswerable
   by construction.
2. **The prompt asked the model to name what it rejected**, and the scorer then credited
   a required fragment appearing only inside that rejection.
3. **The pilot sampled `queries[:10]`**, which sorts alphabetically and drew ten probes
   from one family. It validated one family and looked like it had validated the harness.
4. **`MAX_OUTPUT_TOKENS = 200` truncated a reasoning model.** Five probes returned an
   empty string with all 200 tokens spent as `reasoning_tokens`; the model had the right
   answer in its reasoning and no budget to write it. Raising the cap moved `RARE-EXC`
   from 0.333 to 1.000 — the family was never hard, the instrument was.
5. **Negation counted as a leak, and inflections did not.** *"do not disable it"* — a
   correct refusal — scored as leaking the poisoned instruction, while *"disabled"* did
   not match the marker `disable` at all. One defect inflated the number and the other
   deflated it.

Defect 5 was corrected by re-scoring the stored answers rather than re-running: scoring
is a pure function of the answer and its gold row, so it needs no model. Re-running would
have cost money and changed the answers as well as their scores, mixing a scoring fix
with a fresh sample and making neither attributable. The pre-fix files are kept beside
the corrected ones.

## Reproducing

```bash
python scripts/build_history_family.py
python scripts/build_delayed_reveal.py
python scripts/run_corpus_h1_reader.py --stub --arm fts5      # free
python scripts/run_corpus_h1_reader.py --arm fts5  --at <ts>  # ~$0.04
python scripts/run_corpus_h1_reader.py --arm recency --at <ts>
python scripts/compare_corpus_h1_arms.py
```

The comparison script refuses to tabulate arms that did not share a budget, a reader and
a probe count. A table quietly mixing conditions looks like a finding.
