# Access, valuation, use: the ordering note of 2026-11-01

Status: historical planning note, published 2026-11-12. This is an English translation of a Polish note written on
2026-11-01 after the research vision ([`research-vision-2026-11.md`](research-vision-2026-11.md)) and a conversation the
owner had about importance and emotion in memory. The original stayed outside the repository (SHA-256 of the original
file: `23c9868d1ce2203b9fc37c19bf21b1aa0e3b666c87f29b354e4933a6e357f2c9`). The translation keeps the content and order of the original. Two things were changed in
line with the repository's rules for public documents: the name of the platform of the live writing agent is replaced by
"writing agent", and a reference to a local file is replaced by its published summary. The note contains hypotheses and
a proposed order of work. None of its statements is a result.

What happened afterwards is at the end.

---

No new infrastructure is added here. This is thinking only: what in the conversation is valuable, what I question, what
follows for the first experiment, and what I need to ask. I treat the conversation as a source of hypotheses, not of
results. The assistant in it is encouraging, and none of its theses comes with evidence.

## 1. The main observation: one research object, described three times

Three sources describe the same thing: **a memory controller that decides how experiences are represented and accessed
on the basis of their consequences, judged by behaviour and task outcome under a limited budget.**

- The original project notes ([`original-notes-summary.md`](original-notes-summary.md)) already contain "Operational
  Affect": signals from the consequences of the agent's work (prediction error, cost, failures, novelty, reward),
  learning future utility from later outcomes, and the rule that these are not real emotions. The conversation derives
  the same thing again under the name "regulatory signals".
- The repository has it on paper and deliberately postponed it: the hypotheses of the human-AI bridge (causal future
  utility; operational salience), the utility-telemetry protocol (observational, later tiers locked), and the current
  state's rule to test emotional salience only once utility labels and consequence-weighted retention metrics exist.
  That is an ordering, not neglect.
- The vision is a narrowing of the same thing to one mechanism (associative traces plus dynamic importance) and a small
  study.

Conclusion: we do not add a fourth programme. We choose the order of three questions inside one.

## 2. Three questions instead of one "how important is a memory"

| Question | What it asks | Can it be studied cheaply and causally |
|---|---|---|
| **Access** | Does a new cue or goal reach an old, unimportant experience? | Yes: synthetically, without a model, at zero cost, with exact ground truth (the generator knows which event is relevant). |
| **Valuation** | Which signal at write time predicts later usefulness, and does re-evaluation after a change of goal help? | Yes in a synthetic world, where usefulness is known by construction, so predicted importance can be compared with measured usefulness without costly ablations. On real logs it needs counterfactuals (remove the memory, run again), which costs. |
| **Use** | Does the agent behave better after recall, and can it distrust a false analogy? | Only with an LLM in the loop, so it is costlier and noisier; it needs an environment and a behavioural measure. |

The conversation is right that having memories is not learning from them, and that success is better decisions, not
remembering more. That is the third question. It is the most expensive and the most confounded, so it should come last,
with the first two done where the truth is known.

## 3. What I take seriously from the conversation

1. **Importance is not a property of information but a relation between information, agent, situation and future.**
   This justifies storing a trace plus the possibility of re-evaluation, not a single number.
2. **Separate "retained" from "available to the model".** This is the vision's operational forgetting: the raw archive
   stays, the context holds only what was selected.
3. **Three axes instead of one: relevance to the user or goal, usefulness in the future, durability of truth.** The
   third already exists in the store (valid time, supersession). The first two are goal and utility.
4. **The signal is "how much this changed the agent's model of the world", not "how important this is".** The most
   interesting hypothesis of the conversation. It requires separating three things the conversation mixes: **novelty**
   (distance from what is already there), **surprise** (the outcome differed from the agent's expectation) and
   **consequence** (cost or weight of the effect). Each has a different implementation and cost.
5. **Trust in one's own memory as a research problem.** A memory can be true and still be used wrongly if the analogy is
   superficial. This is measurable: negative transfer (a recalled lesson makes the outcome worse than no memory) and
   calibration (does the stated confidence of a lesson predict its correctness).
6. **An experience record as a loop: situation, expectation, action, outcome, lesson, with a scope of applicability.**
   A lesson without conditions ("when does this hold") is a source of false analogies. This is a practical change to the
   experience record.

## 4. What I question or sharpen

- **Emotion as an explanation.** Arousal strengthens memory, but emotional memories are often inaccurate. For an agent
  the risk is that a "drama" signal strengthens the loudest events, not the most useful. Signals are therefore variables
  with ablations, not a theory, and they are judged only by how well recall is used.
- **"Prediction error" is not free.** An LLM does not predict by default. One must (a) make it state an expected outcome
  before acting (token cost, risk of rationalising afterwards), or (b) use a cheap local measure such as the surprise of
  an observation under a small local model, or (c) measure from the task outcome. These are three different experiments.
- **Frequency of use is not value.** An agent can reinforce its own error. Utility must not be derived from the number
  of recalls. In a synthetic world we use truth by construction, in a real one counterfactuals.
- **The literature is less enthusiastic than the conversation.** Two papers are cited in the original as showing that
  systems with explicit memory have no steady advantage over plain retrieval over history (arXiv:2610.24671) and that
  under loose budgets retention beats consolidation (arXiv:2607.17545); neither was re-checked for this translation.
  The loop from experience to lesson is well studied (ExpeL, Reflexion, ReasoningBank, MemRL). What could be new is
  only: re-evaluation of old traces after a **change of goal**, durability against a retrieval control over long time,
  and measurement of negative transfer.
- **Our earlier result is a warning.** Associative expansions in the repository did poorly (graph fusion at −0.114
  Recall@5; a second hop null with semantic drift). Before an experiment one must say how a trace differs from those
  attempts and measure false associations directly.

## 5. The change to the first experiment that follows

The first-experiment proposal manipulated only vocabulary overlap. That is too little, because modern dense retrieval
will by itself reach a purely topical, lexically disjoint association. The real room for a trace may be where relevance
comes from **role**, not topical similarity (an old supplier delayed deliveries, which matters when planning the launch
of a different product; an old failed method, not to be repeated). The generator should therefore have two factors,
lexical overlap and semantic similarity, with relevance "by role" as a separate cell in which dense retrieval is weak and
false associations are also easiest. In addition:

- the usefulness of every event is known by construction, so the accuracy of **write-time signals** (novelty, surprise,
  consequence, recency, length) against true future usefulness can be studied at once, at zero cost;
- the first measure next to "is the relevant event in the context" is **negative transfer** on decoys with surface
  similarity.

## 6. The fork and my recommendation

*Memory that understands a particular user, or memory that makes an autonomous agent better at tasks?*

The vision chose the agent, so I recommend **task memory as the core of the research**: it is measurable, has an
objective function and can be repeated. Personal importance then enters through **goals and preferences** as inputs, not
as a separate programme. Memory about a user needs other experiments (consent, privacy, preferences that change) and
deserves its own decision.

## 7. Proposed order

1. **E0 (access, zero cost):** delayed relevance after a change of goal at fixed budgets, two factors, controls, negative
   transfer.
2. **E0b (valuation, zero cost):** does any write-time signal predict true future usefulness better than recency and
   length. This is the first real test of what "importance" is.
3. **E1 (use, a few dollars):** repetition of errors in a scripted environment with a hidden rule and decoys; an
   experience record with expectation, outcome and scope of applicability; arms: no memory, raw retrieval, retrieval plus
   lessons, experience with signals.
4. **Only then** a repeat on real logs of the writing agent and a long-term study.

Every step has a stop criterion fixed in advance: if plain retrieval is as good, that is a result, not a failure.

## 8. Process risks I guard against

- **Scope spill.** Three questions of one kind easily become three programmes; keep the order and the stop criteria.
- **The language of emotion.** No claims about feeling; only named variables, ablations and judgement by use.
- **Generator artefact.** A result on a synthetic world proves nothing about a real agent; hence an independent
  extractor, controls and a later test on real text.
- **Cost.** Stages 0, 0b and 1 run locally at zero cost; spending only after a separate decision with its own ledger.

## 9. Questions to the owner

1. Do you agree with the **task** core, with personal importance entering through goals?
2. Do you agree with the order E0, E0b, E1, or do you want to start with the experience loop (E1) although it is
   costlier and more confounded?
3. Should the "surprise" signal be demanded from the agent (a stated expectation before acting, costlier), or first
   measured cheaply and locally?

---

## What happened afterwards (added 2026-11-12)

- **E0** was built and run on 2026-11-01 as `aam-e0-delayed-relevance`: a narrow null for a word-cluster trace index in
  a synthetic world. The two-factor generator and the write-time-signal analysis of section 5 were not part of that run.
- **E0b** was not run, in a synthetic world or elsewhere.
- **E1** as described in section 7 was not run. The experiment that took the name E1 (`aam-e1-writer-memory-sim`) tested
  own-history memory for a writing agent, judged by text quality, not a scripted environment with a hidden rule.
- The first experiment of the E1 kind is EXP-PILOT-0 of 2026-11-12 (BFCL multi-turn tool use with a hidden
  precondition). It has the no-memory and raw-retrieval arms and a placebo; it has no lessons arm and no decoys.
- Which parts of this note are still worth testing is reviewed in
  [`../11-research-laboratory/overlooked-hypotheses-review-2026-11-12.md`](../11-research-laboratory/overlooked-hypotheses-review-2026-11-12.md).
