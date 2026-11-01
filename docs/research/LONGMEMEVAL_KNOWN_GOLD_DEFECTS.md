# LongMemEval-S: publicly reported gold-label and data defects

Version 1, dated 2026-11-01. This is a snapshot of upstream issues, not a finding of this project.

Every claim below about the upstream dataset comes from the text of the issues in
[xiaowu0162/LongMemEval](https://github.com/xiaowu0162/LongMemEval/issues), read on 2026-11-01 through the GitHub API (read-only).
We have not re-derived any of the defects from the dataset itself: the dataset file is not in this repository and was not
opened for this document. Where this document adds something, it is only (a) a check of whether the question id occurs in this
repository's tracked files and (b) one recommended treatment. Re-fetch the issues before relying on a state or a status; they change.

The dataset this repository measured is `xiaowu0162/longmemeval-cleaned`, revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`,
file `longmemeval_s_cleaned.json`, SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`
(recorded in [`docs/06-datasets/longmemeval-public-bridge-audit.md`](../06-datasets/longmemeval-public-bridge-audit.md)).
The reporter of issue 54 states they validated exactly that revision and hash. The other issues name the cleaned file but not a revision.

Two of the reporters (issues 40 and 41) run a commercial retrieval product and cite their own benchmark score in the issue title. Treat their
claims as claims. The date arithmetic in issue 41 is easy to check: 2023-04-10 minus 2023-01-19 is 81 days (checked with Python `datetime`).
That checks the sum, not that those are the right dates in the haystack sessions.

## Treatment classes

| Class | Meaning | What to do in an analysis |
|---|---|---|
| EXCLUDE | the reported defect concerns the gold answer itself | drop the id from the headline number; report the number with and without it |
| EXCLUDE-FROM-RETRIEVAL-METRICS | the reported defect concerns evidence labels (`has_answer`, answer-session mapping), not the answer text | keep in answer-accuracy numbers; drop from any metric computed from those labels |
| FLAG-AND-KEEP | a construction artefact that does not change the answer | keep; make sure your adapter treats the repeated session the way you intend; say what you did |
| NO-ACTION | the reporter withdrew the claim | keep as normal |

Excluding means exclude from the headline and say so, never delete from the raw result files. The with-and-without pair is the thing to publish.

## The list

"In this repository" means: the 8-character question id, matched as a whole word, occurs in a tracked file (`git grep -w`, worktree of 2026-11-01).
The directory `docs/research/Dokumenty dla Resherchera/` was left out of that search. "Not found" is a statement about tracked files only.

| Upstream issue | State on 2026-11-01 | Question id | Reported defect (reporter's claim) | In this repository | Class |
|---|---|---|---|---|---|
| [#21](https://github.com/xiaowu0162/LongMemEval/issues/21) | open; the maintainer replied on 2025-12-22 that it will be fixed in a future revision | `dd2973ad` | gold "2 AM" is the bedtime of 24 May, but the doctor's appointment the reporter resolves is 18 May, so the "day before" is 17 May | not found | EXCLUDE |
| [#22](https://github.com/xiaowu0162/LongMemEval/issues/22) | open; the maintainer replied on 2025-12-22 that earlier turns should indeed carry `has_answer: true` | `51a45a95` | only one turn is labelled `has_answer`, but the answer ("Target") needs earlier turns too; the answer text itself is not disputed | not found | EXCLUDE-FROM-RETRIEVAL-METRICS |
| [#26](https://github.com/xiaowu0162/LongMemEval/issues/26) | open, no reply | not named in the issue; it names sessions `answer_61d1be50_1` and `answer_61d1be50_2`, which issues 40 and 41 attach to `370a8ff4` | gold 15 weeks, reporter computes about 11.6 weeks (81 days) from 2023-01-19 to 2023-04-10 | see `370a8ff4` below | EXCLUDE |
| [#37](https://github.com/xiaowu0162/LongMemEval/issues/37) | open, no maintainer reply | `eac54add` | the answer-session mapping points to a session about 18 days away from the session that holds the answer; also a typo in the question text. The issue gives no further detail | not found | EXCLUDE-FROM-RETRIEVAL-METRICS |
| [#38](https://github.com/xiaowu0162/LongMemEval/issues/38) | open, no reply | `618f13b2` | gold "six", but a later-timestamped message says "four times" while an earlier-timestamped one says "six"; reporter suggests the "six" message carries a wrong timestamp | in `data/lab/longmemeval-bridge-v0/` (selection and retrieval-recall result rows, no answer scoring seen) and in the planning file `data/lab/arena/run-cost-projection.json`; in no arena result file | EXCLUDE |
| [#39](https://github.com/xiaowu0162/LongMemEval/issues/39) | open, no reply | `37f165cf` | gold 856 pages, but the two novels were finished in May by the message timestamps, not in January and March; reporter says the answer should be "insufficient information" | not found | EXCLUDE |
| [#40](https://github.com/xiaowu0162/LongMemEval/issues/40) | closed as completed on 2026-04-28, about an hour after opening; the issue text does not say the dataset changed | `370a8ff4` and `gpt4_88806d6e` | `370a8ff4`: as for #26 and #41. `gpt4_88806d6e`: the reporter later withdrew this one in a comment (the gold "Tom" is correct, the session text says "a few months ago") | `370a8ff4`: yes, see below. `gpt4_88806d6e`: not found | `370a8ff4` EXCLUDE; `gpt4_88806d6e` NO-ACTION |
| [#41](https://github.com/xiaowu0162/LongMemEval/issues/41) | open, no reply; re-filed by the same reporter as a `370a8ff4`-only issue | `370a8ff4` | gold 15 weeks, reporter computes 81 days, about 11.6 weeks | yes, see below | EXCLUDE |
| [#54](https://github.com/xiaowu0162/LongMemEval/issues/54) | open, no reply | 13 histories, listed below | the same filler `haystack_session_id` appears twice in 13 question histories, content identical, dates different, never an answer session; the reporter counts 23,867 session occurrences and 23,854 after removing one copy of each pair | 6 of the 13 ids occur, see below | FLAG-AND-KEEP |

### `370a8ff4` in this repository

It was one unit of the sample behind ledger Entry L ([`SECOND_HOP_ASSOCIATIVE_EXPANSION_V1.md`](SECOND_HOP_ASSOCIATIVE_EXPANSION_V1.md), line 18, in its results table;
data in `data/lab/arena/second-hop-expansion-v1/{selection.json,results.json}`). The question type is temporal-reasoning and the stored gold is "15",
as the issues say. The question reads "How many weeks had passed since I recovered from the flu when I went on my 10th jog outdoors?".
Both the base arm and the second-hop arm answered it wrongly.

With and without it, recomputed from `results.json`:

| | units | base correct | second-hop arm correct | repairs | regressions |
|---|---|---|---|---|---|
| as published (Entry L) | 6 | 3 | 3 | 0 | 0 |
| without `370a8ff4` | 5 | 3 | 3 | 0 | 0 |

The unit was wrong in both arms, so excluding it changes the base accuracy from 3 of 6 to 3 of 5 and leaves the Entry L verdict (no repair, no regression) unchanged.
We have not checked whether the dataset gold or the reporter is right; if the reporter is right, this unit was a correct refusal to match a wrong gold.

### Issue 54: the 13 histories

The issue lists, per question id, the session id that appears twice. We cross-checked only the question ids against tracked files.

| Question id | Duplicated filler session (per the issue) | Where the id occurs in this repository |
|---|---|---|
| `58bf7951` | `07b7a667_1` | many arena files, including the E1 and E3 samples (Entry H's E3 sample; all three arms correct there) |
| `1e043500` | `d5d1f9c4` | `data/lab/arena/second-hop-expansion-v1/` (Entry L; base and second-hop arms both correct) |
| `001be529` | `sharegpt_SYbLHTK_0` | `selection.json` of the fresh raw-provenance replication and of `retrieval-confidence-signal-v1`, the `stage2-fresh-replication/` files, one archaeology file, the bridge-v0 files; not among the 8 result rows of the fresh replication |
| `078150f1` | `sharegpt_z7Ogy29_0` | `data/lab/arena/raw-provenance-fresh-replication-v1/results.json` (Entry H's multi-session counterexample; all three arms wrong), and other files |
| `gpt4_76048e76` | `8fcaf3a9_2` | only `data/lab/arena/run-cost-projection.json` and `data/lab/longmemeval-bridge-v0/` |
| `c7dc5443` | `6b8e8bb3_1` | only `data/lab/arena/run-cost-projection.json` and `data/lab/longmemeval-bridge-v0/` |
| `18bc8abd` | `sharegpt_vyHqfrX_0` | `data/lab/arena/extraction-completeness-verification-v1/` (Entry O) |
| `1d4da289` | `sharegpt_qktLFWS_21` | `data/lab/arena/extraction-completeness-verification-v2/` (Entry P; a unit whose failure is attributed to assistant-turn loss) |
| `d23cf73b`, `caf03d32`, `91b15a6e`, `gpt4_4929293b`, `gpt4_c27434e8_abs` | `334ab2f1`, `sharegpt_YCfhENU_0`, `sharegpt_fgnzLtE_0`, `sharegpt_81riySf_0`, `8c64ce26_3` | not found |

Whether this repository's ingest indexed the repeated session twice, collapsed it, or counted it once in a per-session statistic was not checked.
That is the open question for any of the units above, and it is checkable only with the dataset file (SHA-256 above) in hand.
Because the repeated sessions are filler, not answer sessions, the issue gives no reason to expect a changed gold answer; it matters for adapters that key on
`(question_id, session_id)`, as the reporter says, and for token and cost accounting.

## How to use this list

```python
EXCLUDE = {"dd2973ad", "370a8ff4", "618f13b2", "37f165cf"}
EXCLUDE_FROM_RETRIEVAL_METRICS = {"51a45a95", "eac54add"}
FLAG_AND_KEEP = {"58bf7951", "1e043500", "001be529", "078150f1", "gpt4_76048e76", "c7dc5443", "18bc8abd",
                 "1d4da289", "d23cf73b", "caf03d32", "91b15a6e", "gpt4_4929293b", "gpt4_c27434e8_abs"}
```

Report every accuracy figure twice, over all questions and over all questions except `EXCLUDE`. Do not edit a frozen result file; add a column.
Any temporal-accuracy claim in this repository should be recomputed this way before it is quoted outside it.

## What is not verified here

* None of the nine issues was re-derived from the dataset. Their descriptions are the reporters' own.
* Issue 37 gives no session ids, so the reported mapping error cannot be located from the issue alone.
* Whether the dataset maintainers have changed the data since these issues were filed. No issue states a new revision; issue 40 is closed without a stated change.
* Whether defects exist that nobody has reported. A short list of reported defects is a lower bound, not an audit.
* This list will go stale. Version 1, 2026-11-01.
