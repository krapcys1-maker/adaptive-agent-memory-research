# memory_kernel, the live line (0.2.x)

A small, deterministic, standard-library-only memory for a writing agent: thresholded retrieval of at most three earlier items, a strict no-future rule, origin classes, a channel for names, an optional embedder, a log record without text, and a floor-level guard for the writer's output.

## Layout

| path | what it is | status |
|---|---|---|
| `scripts/wmb/memory_kernel.py` | version 0.1.0 | **frozen**: the instrument of the preregistered study WMB-R1 (its digest is declared in `data/lab/wmb-r1-retrieval/config.json`; the claim audit fails the build if it changes). Never edited. |
| `tests/test_wmb_memory_kernel.py` | the tests of 0.1.0 | frozen with it |
| `scripts/wmb/kernel/memory_kernel.py` | version 0.2.0 (`VERSION` in the file) | **frozen since 2026-11-13**: experiments that ran on 0.2.0 declare its digest (nine manifests on that date, among them `data/lab/reader-model-compare-v1/` and `data/lab/nie-local-reader-v1/`), so a committed edit fails the claim audit. The owner decided on 2026-11-13 that the next kernel version is a **new versioned module** next to this one, with its own `VERSION`, CHANGELOG and tests, rather than an edit of 0.2.0 with drift notes for nine historical manifests. `python scripts/pinned_files.py PATH` shows whether a file is pinned before you edit it |
| `tests/test_wmb_kernel_v2.py` | the tests of the live line | runs in the job "Memory kernel (Python 3.14)" and in the full suite |

## Interface

The interface agreed with the writing agent is unchanged: no public name was renamed or removed, signatures only gained optional parameters at the end (`calibrate`: `profile`, `task_type`; `render`: `max_item_chars`), results keep their keys. Keys were added: `_df` (private, document frequencies of the injected words for the guard; never logged) and `rejected` (the counters of the index) in the result of `retrieve`; `now_key`, `rejected` and `unicode` (the version of the Unicode tables that cut the words) in the log record. `Index.rejected` keeps the three counters of 0.1.0 (`future`, `invalid`, `duplicate`); the items of the caller are kept as they were passed, and `Index.trace_dropped` counts those with a trace that `render` will partly ignore.

| call | returns |
|---|---|
| `build_index(items, as_of, embedder=None, vectors=None)` | an `Index`; raises `ValueError` only for an invalid `as_of` (the no-future gate needs it); counts and drops invalid, future and duplicate items in `index.rejected`; keeps the items read so far if the iterable fails midway (`index.source_error`, and `retrieve` then answers `degraded`) |
| `retrieve(index, query, task_type, now, profile)` | a dict (`status`, `items`, `scores`, `channel_scores`, `reasons`, `dates`, `keys`, `now`, `now_key`, `rejected`, `latency_ms`, `tokens_est`, ...); never raises |
| `render(result, mode="trace", max_item_chars=4000)` | the text for the prompt, one dated line per item, oldest first, the date as the item was written, a very long item cut at a word |
| `log_record(result, hmac_fn, key=None, raw_ids=False)` | one JSON-safe record with keyed hashes, scores and reasons, no text; a lone surrogate cannot lose it |
| `guard(result, output_text)` | `{"ok", "flags", "callbacks"}`: a floor, to be logged, not a gate |
| `calibrate(index, queries, share=0.2, channel="lexical", profile="kernel", task_type=None)` | the threshold that lets `share` of the (query, date) pairs have a candidate, or `None` when it cannot say |

Profiles `kernel` (embedder when the index has one), `lexical`, `hybrid`, or a dict (a key the profile does not know is an error, and so are `tau` or `lex_tau` at zero or below).

## The lexical gate in three sentences

The score of an item is BM25 (k1 1.2, b 0.75) over the stems of the query, with document frequency, document count and average length taken over exactly the items the call may see (dated before the task, not yet replaced, invented autobiography only where the profile allows it), and with the length of an item counted as at most `len_cap` (3) times the average, so that a long essay that holds all the words of a short query is not out of reach. The score is divided by the largest value that the query's ten most informative known words could give, so it does not depend on the length of the query; an item passes when that share reaches `lex_tau` (0.20) and the idf mass of the shared words reaches `min_evidence` (1.4) times the idf of a word seen once, that is when about two rare words are shared. The rank is the share over `lex_tau`; equally rare query words are ranked by their place in the query, never by their spelling.

## Vendoring in the integrating project

The module is **one file** with no dependency outside the standard library (Python 3.11 to 3.14) and no effect on import.

1. Copy `scripts/wmb/kernel/memory_kernel.py` byte for byte (the repository stores files without line-ending conversion).
2. Record next to the copy the `VERSION` string (`python -c "import memory_kernel; print(memory_kernel.VERSION)"`) and the SHA-256 of the file: `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" memory_kernel.py`. Compare both after every update; do not edit the copy. A change belongs in a new versioned module in this directory (0.2.0 is frozen; see the layout table), which you then vendor again.
3. Read `kernel_version` in every log record: it is the `VERSION` of the file that produced it.
4. To run this suite against the vendored copy: `WMB_KERNEL_V2_FILE=/path/to/memory_kernel.py python -m pytest tests/test_wmb_kernel_v2.py -q` from a checkout of this repository (the suite loads the copy under a private name; the frozen 0.1.0 and this README are still read from the checkout).
5. Pass aware datetimes (`datetime.now(timezone.utc)`), or set `require_zone` in the profile so that a `now` without a zone is refused.

## What changed in 0.2.0

- **Lexical gate**: BM25 in place of idf coverage (the study WMB-R1 found coverage the weakest lexical method), normalised by the top-term reference; new profile keys `k1`, `b`, `len_cap`, `top_terms`, `max_terms`, `require_zone`; `lex_tau` means a share of the reference. Thresholds of 0.1.0 do not carry over: fit `lex_tau` with `calibrate()`.
- **Statistics of a call**: the idf, the document count and the average length are those of the items the call may see; fiction, items after a replayed task and replaced items cannot change a score (the first build of 0.2.0 took them over the whole index and lost hits to a flood of invented autobiography).
- **Evidence floor**: `min_evidence` 1.4 in place of 0.8: one shared rare word is not enough. A short query that shared one rare word fired about half of the time in the synthetic world below.
- **Text units**: plurals fold for short stems, acronyms, `-es`/`-ie`/`-oes`/`-ves` forms and a few irregular plurals; stop words are tested before stemming (a few names, months and acronyms such as US, May, Ono are kept when written with a capital); contractions leave no stems; longer English and Polish stop lists; NFC; combining marks belong to words (Hindi, Thai, Hebrew, Arabic with vowel signs), invisible characters are removed, long tokens stay out of the caches, long texts are cut.
- **Names**: a sentence-initial capital is no evidence; a name hit has strength at least 1.
- **Inputs and outputs**: `now` may be a date or datetime and the log stays JSON; traces are counted when the index is built and ignored when rendering (the items are not rewritten); `render` degrades per item, cannot add a line, shows the date as written and cuts very long items; render, log and guard use one rule for the shown items; `retrieve` returns an error status for a non-Index and `ok` for an empty index with an embedder; dates are validated (offsets with seconds, overflow, only `ValueError`); supersession counts from an item of the same or a later instant and ignores self-links and cycles; `calibrate` returns `None` instead of a threshold of zero, applies `min_evidence` and the statistics of each pair.
- **Guard**: references are recognised by grammar, not by a phrase list; case, apostrophes, spaces, markup and look-alike Cyrillic or Greek letters are normalised; references to the text being written cancel only their own clause; a bare possessive (`my newsletter`), a bare stance (`as I said`), an act of making (`I wrote a script last week`) and a greeting (`welcome back, regular readers`) are not references; world knowledge does not back a reference to what the author wrote.

## Measured (synthetic and offline; the shape, not the rates of an account)

**Gate**, a synthetic world of 300 notes in 30 topics with a Zipf vocabulary of 3000 words, 3 seeds, 200 relevant and 200 unrelated queries per length (an independent verifier's world, not the builder's). The share of queries that return something:

| words in the query | 0.1.0 relevant / unrelated | first build of 0.2.0 | this version (`min_evidence` 1.4) |
|---|---|---|---|
| 5 | 0.94 / 0.46 | 0.84 / 0.53 | 0.66 / 0.10 |
| 20 | 0.69 / 0.00 | 0.83 / 0.01 | 0.83 / 0.01 |
| 60 | 0.17 / 0.00 | 0.89 / 0.00 | 0.90 / 0.00 |

An item of 5000 words that holds two or more of the rare words of the query is a candidate at every length (the first build lost it beyond about four times the average length). The Zipf-world rates are a guide to the shape only: fit `lex_tau` and `min_evidence` with `calibrate()` on labelled queries of your own account before the first production use.

**Guard**, precision and recall of "the guard sees a reference". The banks of the tests were written by the author of the patterns (the first before the patterns, the others after); a second bank was written by the hardening verifier before it had read the patterns. 0.1.0: first bank precision 0.74, recall 0.35.

| bank | positives found | false alarms | precision | recall |
|---|---|---|---|---|
| first bank of the tests (66 + 66; patterns tuned on two thirds of it) | 66 of 66 | 0 of 66 | 1.00 | 1.00 |
| fresh bank one (30 + 30; a development set by now) | 25 of 30 | 0 of 30 | 1.00 | 0.83 |
| fresh bank two (30 + 30; a development set by now) | 29 of 30 | 0 of 30 | 1.00 | 0.97 |
| hardening verifier's bank (60 + 60, written before reading the patterns) | 53 of 60 | 0 of 60 | 1.00 | 0.88 |
| finding-by-finding verifier's bank (45 + 44, written for the check) | 37 of 45 | 0 of 44 | 1.00 | 0.82 (0.1.0: 0.20) |
| 40 near-miss sentences (code, private speech, other meanings of post, issue, thread) | | 0 of 40 | | |
| 49 deliberately adversarial innocent sentences (0.1.0: 5; first build of 0.2.0: 21) | | 0 of 49 | | |

## Known limits

- The defaults of the gate (`lex_tau` 0.20, `min_evidence` 1.4, `len_cap` 3) are not fitted to any real account; the synthetic figures show a shape, not rates.
- One distinguishing word is not enough by default: a query with a single rare known word (and a note about it) returns nothing, as does a long text that shares only one rare word; names are covered by the name channel for the task types a profile names, and `min_evidence` 0.8 asks for one word. For a long task text the reference counts the ten rarest known words, so many rare words that an item does not share lower the share of the items that have a few.
- Items of one text under different ids rank equal and can fill all three slots (de-duplicate when the feed is built); ties go to the id that sorts first. The id suffix is 32 bits of SHA-256: two texts of one kind and day collide after some tens of thousands of items.
- A call makes one pass over the items of the index for the statistics of the items it may see and then reads the postings of the rarest stems of the query, so its cost grows with the size of the index and with how many items share those stems. Measured on this machine (Windows, Python 3.12, synthetic notes of about 60 words): 2000 items build in 0.2 s and answer in 1.1 ms (p95 2.6 ms); 10,000 items build in 1.3 s and answer in 6.7 ms (p95 17.5 ms); 2000 items of 700 words build in 1.5 s and answer in 3.1 ms (p95 8.8 ms). The name channel reads capitals, so title-cased headings and abbreviations can mislead it.
- A time without a zone is UTC (set `require_zone` to refuse it). The first of two items with one id wins. `when` raises `ValueError`, as does `build_index` for an invalid `as_of`.
- A script written without spaces (Chinese, Japanese) is one word per run of characters between spaces and punctuation, so it matches only whole runs.
- The stemmer is English and rule-based; Polish has stop words but no stemming, and a lower-case Polish function word that is an English content word (`ten`, `ale`) is dropped. Which characters are letters follows the Unicode tables of the interpreter (the log carries their version), except the table of combining marks, which is fixed in the file.
- The deadline is checked every 200 items and after the embedder returns; it cannot interrupt an embedder that hangs. With an embedder the cosine pass is pure Python (2000 items of 384 dimensions: 20 ms per call, p95 24 ms; 10,000 items: 101 ms, p95 117 ms, maximum 146 ms; a machine three times slower reaches the 300 ms deadline at 10,000 items), and the embedder is called once with all texts at build time, which exceeds the input limits of many hosted embedding services: batch in your embedder.
- The max-fusion of the hybrid profile is unchanged from 0.1.0; WMB-R1 found it keeps little of the embedder's gain. Fit the weights on your own data before relying on it.
- The guard is English only and sees explicit references only; the anchor must be within 80 characters of the verb; the date of an anchor is not compared with the age of the injected items; a result without the private `_df` key (made by hand) is judged by the count of shared words alone; `unsupported_reference` can fire on a terse reference that shares only common words with the item; invented autobiography written back from the persona's own text can back a reference. Log its flags; do not reject text on them.

## Tests

```
python -m pytest tests/test_wmb_kernel_v2.py tests/test_wmb_memory_kernel.py -q -p no:cacheprovider
```

Both files need only `pytest` and the standard library. The tests of the live line use synthetic data only, port what the tests of 0.1.0 covered, add hand-computed BM25 scores, the dates, the guard banks, one sentence for each rule of the grammar (a rule that is removed or broken loses its sentence), regressions for every defect that the two verifiers of the first build found, a determinism check across `PYTHONHASHSEED` values, and the limits of the contract (2000 items: build under 2 s, p95 retrieve under 300 ms, under 200 MB).
