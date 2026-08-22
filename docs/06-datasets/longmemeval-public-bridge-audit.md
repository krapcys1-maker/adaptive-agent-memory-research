# LongMemEval public bridge audit

Status: primary-source and local-byte audit complete; bridge selection frozen; backend execution locked

## Decision

Use a small, separately reported LongMemEval-S cleaned sample as the first public bridge for Project Memory Lab. Do not merge its score with the project-derived corpus and do not call it hidden held-out evidence.

The official LongMemEval repository defines 500 questions spanning information extraction, multi-session reasoning, knowledge updates, temporal reasoning, and abstention. Its released format includes timestamped sessions, `answer_session_ids`, and turn-level `has_answer` annotations. The official retrieval runner excludes 30 abstention questions because there is no complete positive answer location. Sources: [official repository](https://github.com/xiaowu0162/LongMemEval), [ICLR 2025 paper](https://openreview.net/pdf?id=pZiyCaVuti), and [cleaned dataset card](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned).

## Frozen source

| Field | Value |
| --- | --- |
| Dataset | `xiaowu0162/longmemeval-cleaned` |
| Dataset revision | `98d7416c24c778c2fee6e6f3006e7a073259d48f` |
| File | `longmemeval_s_cleaned.json` |
| Bytes | `277383467` |
| SHA-256 | `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` |
| Dataset-card license | MIT |
| Official code revision observed | `9e0b455f4ef0e2ab8f2e582289761153549043fc` |

The verified local file has 500 unique IDs, all nine required fields, 38-62 sessions per question, and 896 answer-tagged turns. Type counts are 70 single-session-user, 56 single-session-assistant, 30 single-session-preference, 133 multi-session, 78 knowledge-update, and 133 temporal-reasoning.

## Abstention boundary discovered locally

The source has 30 `_abs` questions. Twenty-one have no answer-tagged turn, eight have one, and one has two. The latter nine are not positive-answer cases: they expose an incomplete operand or a near-miss fact, such as one trip duration when a total over two trips is asked. Their `answer_session_ids` point to relevant near-miss sessions in the haystack.

Therefore:

- answerable cases receive ordinary evidence-session/turn Recall@k;
- abstention cases have `retrieval_gold_defined=false`;
- near-miss retrieval is recorded but is neither automatically correct nor incorrect;
- correctness is whether the completeness controller/reader abstains despite partial plausibility;
- pooling retrieval recall with abstention would be a construct error.

## Frozen selection

`prepare_longmemeval_bridge.py` selects five answerable questions from each of six types and six abstention cases using ascending `sha256("pmlab-longmemeval-bridge-v0:" + question_id)` within strata. A normal ID and its `_abs` counterpart cannot both be selected. The committed file contains only 36 public IDs and structural counts—not conversations, question text, answers, or evidence IDs.

This mechanism prevents manual cherry-picking but not public-data contamination. Models or embedding systems may have seen LongMemEval. The bridge can test transfer and adapter compatibility; it cannot prove clean generalization.

## Why not the alternatives first

- **LoCoMo:** the official release provides evidence dialogue IDs and temporal/event annotations, but only ten conversations and a CC BY-NC 4.0 license. It remains useful for a noncommercial secondary audit, with attribution and no casual redistribution. Sources: [official repository](https://github.com/snap-research/locomo), [ACL 2024 paper](https://aclanthology.org/2024.acl-long.747/), and [license](https://github.com/snap-research/locomo/blob/main/LICENSE.txt).
- **LongMemEval-V2:** the 2026 official benchmark adds 451 manually curated questions, web/enterprise trajectories, workflow knowledge, gotchas, premise awareness, latency, hidden evaluator metadata, and up to 115M-token haystacks. Its repository and dataset declare Apache-2.0, but the dataset is about 7.12 GB and multimodal. It is a high-value later agent-level reproduction, not the minimal first bridge. Sources: [official repository](https://github.com/xiaowu0162/LongMemEval-V2) and [dataset](https://huggingface.co/datasets/xiaowu0162/longmemeval-v2).
- **LongBench v2:** useful for long-context reasoning and search, but it mixes documents, code, structured data, and multiple-choice reasoning rather than sequential durable-memory lifecycle. It is a reader/context stress suite, not the nearest bridge. Source: [official repository](https://github.com/THUDM/LongBench).

## Gate

Do not run the bridge before the PMLAB lexical adapter, token budget, chunking, cache policy, and scoring contract freeze. Once unlocked, run the exact same adapter without bridge-specific tuning and report all 36 cases separately from the 120-query PMLAB corpus.
