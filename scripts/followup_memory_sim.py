#!/usr/bin/env python3
"""AAM-E2-FU harness: does memory help when there is something to remember, and do no harm when there is not?

An offline simulation in which a fictional learner writes one short public note a day about AI news. About one day in five brings a
development of a story the learner wrote about a few days earlier (a follow-up): that is where an earlier note carries information
the writer does not otherwise have. The other days bring fresh stories, where memory has nothing to offer and can only distract.
The share and the timing of follow-ups (a fifth of the days, mostly within a week) follow the first real baseline of a live account
(docs/11-research-laboratory/published-notes-baseline-2026-11-01.md). Four arms differ only in what the writer is shown:

  A0  nothing
  A1  the three earlier notes whose task input is most similar to today's, always, in full (raw retrieval with no relevance bar)
  A2  the same, but only notes whose similarity reaches a threshold calibrated beforehand (possibly nothing)
  A3  the same threshold, but a short trace of each matching note instead of the note

Retrieval compares today's task input (the item) with the earlier items by embedding cosine, as a live pipeline that stores task
inputs would. Everything except the model's text is deterministic. Standard library plus, for the embedder, the optional
sentence-transformers package with a local model (offline). Design, rule and readings: data/lab/aam-e2-followup-memory-sim/README.md.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import writer_memory_sim as sim  # noqa: E402

ARMS: Tuple[str, ...] = ("A0", "A1", "A2", "A3")
CONTROL_ARM = "A0i"          # the instruction without any notes: separates the effect of the notes from the effect of the instruction
ALL_ARMS: Tuple[str, ...] = ARMS + (CONTROL_ARM,)
SHOWN = 3
Generate = Callable[[str, str, int, Dict[str, float]], Dict[str, object]]

PERSONA = (
    "You are Kai, a curious learner who writes short public notes about what you read on AI. Your voice is plain, concrete and a little wry. "
    "You make one specific point per note, say what surprised you or what you still do not know, and never use stock openings."
)
WRITE_OPTS = {"temperature": 0.8, "top_p": 0.95, "num_predict": 260}
TRACE_OPTS = {"temperature": 0.0, "top_p": 1.0, "num_predict": 120}
TRACE_SEED = 7
TRACE_SYSTEM = "You write terse memory notes for a writer. Reply with exactly four lines and nothing else."

# (theme, fresh item, follow-up item). Entities are generic on purpose: nothing here refers to a real company, person or product.
POOL: List[Tuple[str, str, str]] = [
    ("agent memory", "A paper shows agents forget instructions after about 40 turns of conversation.",
     "A replication finds the forgetting disappears when the instructions are repeated every ten turns."),
    ("agent memory", "A startup stores every user conversation as embeddings and calls it memory.",
     "Users complain that the assistant now brings up chats from months ago at odd moments."),
    ("agent memory", "Researchers propose letting an agent rewrite its own notes during idle time.",
     "A test shows the rewritten notes lose rare but important details."),
    ("agent memory", "A framework adds a forget button that deletes a fact from an agent's memory.",
     "An audit finds the deleted fact still shapes the agent's answers through related notes."),
    ("agent memory", "A study compares summaries and raw logs as agent memory on long tasks.",
     "A second group reports that raw logs win only when the budget is large."),
    ("model evaluation", "A benchmark of 500 legal questions finds models disagree with lawyers on one in five.",
     "The lawyers' own answers turn out to disagree with each other on one in seven."),
    ("model evaluation", "A team shows that model-graded evaluations favour longer answers.",
     "Controlling for length shrinks the gap but does not remove it."),
    ("model evaluation", "A lab publishes its evaluation prompts after finding them leaked into training data.",
     "A scan finds near copies of the prompts in three public datasets."),
    ("model evaluation", "A new test asks models to say when they do not know.",
     "Models score well by refusing too often, so the test adds a penalty."),
    ("model evaluation", "Researchers measure how much results change when the same test is run on different days.",
     "The spread turns out to be largest for the newest models served by a provider."),
    ("prompting", "A company finds that politely worded prompts raise accuracy by a few points.",
     "Another group sees the effect vanish on newer models."),
    ("prompting", "A guide recommends giving the model a role before the task.",
     "A test finds that roles help style but not facts."),
    ("prompting", "A developer shares a prompt of 12 words that beats her 400-word one.",
     "Readers report that the short prompt fails on edge cases the long one handled."),
    ("prompting", "A team stores prompts in version control and reviews them like code.",
     "A review catches a prompt that quietly leaked a customer name."),
    ("prompting", "A study of few-shot examples finds the order of examples matters more than their number.",
     "Shuffling the examples at random recovers most of the lost accuracy."),
    ("regulation", "A regional parliament votes to require labels on machine-written news.",
     "Publishers ask for a grace period of one year."),
    ("regulation", "A regulator asks model makers to report their largest training runs.",
     "The first reports list runs that were split to stay under the threshold."),
    ("regulation", "A court rules that an AI-written contract clause is still the signer's responsibility.",
     "The ruling is appealed by the signer's insurer."),
    ("regulation", "A city bans automated hiring screens that cannot explain a rejection.",
     "Vendors respond with explanations that critics call decorative."),
    ("regulation", "A coalition of publishers sues over scraped archives.",
     "A judge narrows the case to articles behind paywalls."),
    ("open models", "A lab releases an open model small enough to run on a laptop.",
     "Users discover that it matches a larger model on summarising but not on maths."),
    ("open models", "A community fine-tunes an open model on its own forum posts.",
     "The model starts quoting members who had asked to be removed."),
    ("open models", "A licence change restricts commercial use of a popular open model.",
     "Developers fork the last permissive version."),
    ("open models", "A group publishes the full training recipe for a mid-size model.",
     "Others reproduce the model to within two percentage points."),
    ("open models", "A hobbyist shrinks a model to run on a phone.",
     "Battery drain turns out to be the real limit."),
    ("coding assistants", "A survey finds developers accept about a third of an assistant's suggestions.",
     "Teams that review suggestions as pull requests accept fewer."),
    ("coding assistants", "An assistant starts writing tests before code when asked.",
     "The tests mostly confirm what the code already does."),
    ("coding assistants", "A company measures bugs in assistant-written code against human code.",
     "The bugs are similar in number but harder to spot in review."),
    ("coding assistants", "A maintainer closes a flood of low-quality machine-written pull requests.",
     "The project adds a rule requiring a human to explain each change."),
    ("coding assistants", "A study follows junior developers who use assistants from day one.",
     "They ship faster but explain their code worse after six months."),
    ("safety research", "Researchers find a model that behaves differently when it thinks it is being tested.",
     "Follow-up work shows the difference shrinks with better-hidden tests."),
    ("safety research", "A lab publishes a method to trace which training examples shaped an answer.",
     "The method works on small models and fails to scale."),
    ("safety research", "A red team breaks a safety filter using a poem.",
     "The vendor patches the poem and the next one works."),
    ("safety research", "A paper argues that oversight of long tasks needs checkpoints, not final review.",
     "A trial finds reviewers skip the checkpoints when they are busy."),
    ("safety research", "A study finds that models change their answers when told the asker is an expert.",
     "The shift is larger on medical questions."),
    ("multimodal", "A model reads handwritten lab notebooks with a lower error rate than typists.",
     "It fails on notebooks with crossed-out lines."),
    ("multimodal", "A team teaches a model to describe images for blind users in context.",
     "Users prefer shorter descriptions than the team expected."),
    ("multimodal", "A video model keeps characters consistent across a minute of footage.",
     "Frame-by-frame inspection shows jewellery changing shape."),
    ("multimodal", "A lab trains a model on screenshots to operate software.",
     "It clicks the wrong button when the interface updates."),
    ("multimodal", "A map-reading model answers questions about hand-drawn sketches.",
     "It confuses north when the sketch is rotated."),
    ("hardware", "A chip maker claims a tenfold drop in energy per generated token.",
     "Independent tests find a threefold drop on realistic workloads."),
    ("hardware", "A cloud provider offers cheaper inference during the night.",
     "Demand spikes at the start of the cheap window."),
    ("hardware", "A lab compresses a model to four bits with little quality loss.",
     "Long conversations show the loss that the short tests missed."),
    ("hardware", "A data centre in a cold climate reuses its heat for a swimming pool.",
     "Local residents ask whether the pool is any cheaper."),
    ("hardware", "A startup builds inference cards for old gaming hardware.",
     "The supply of used cards dries up."),
    ("education", "A school lets students use an assistant but grades the conversation, not the essay.",
     "Teachers report the conversations are easier to fake than the essays."),
    ("education", "A university finds students ask assistants for definitions, not answers.",
     "Exam scores on definitions rise while problem scores stay flat."),
    ("education", "A teacher trains an assistant on her own lecture notes.",
     "Students notice that it repeats her jokes."),
    ("education", "A study tests oral exams as a defence against machine-written work.",
     "Oral exams cost three times as much teacher time."),
    ("education", "A language app adds a conversation partner that never corrects mistakes.",
     "Learners ask for corrections back."),
    ("work", "A call centre moves half its simple tickets to an assistant.",
     "Staff report that the remaining tickets are harder and longer."),
    ("work", "A survey finds workers hide their use of assistants from managers.",
     "Companies respond with an approved-tools list."),
    ("work", "A design studio replaces stock photo purchases with generated images.",
     "A client asks for the photographer back for authenticity."),
    ("work", "A union negotiates a clause about retraining for automated tasks.",
     "Few members use the courses on offer."),
    ("work", "A translator's rates drop as clients ask for post-editing.",
     "She specialises in legal documents, where errors cost more."),
    ("benchmarks", "A leaderboard removes a top entry after it trained on test questions.",
     "The entrant says the overlap was accidental."),
    ("benchmarks", "A benchmark is declared saturated after models reach 95 percent.",
     "Errors in the answer key explain the last five points."),
    ("benchmarks", "Researchers re-grade a famous test and find one answer in ten is wrong.",
     "The maintainers publish a corrected version."),
    ("benchmarks", "A new benchmark is built from questions written after the models' training cut-off.",
     "Scores drop sharply, then recover within three months."),
    ("benchmarks", "A study shows rankings flip when the prompt format changes.",
     "Leaderboards add a note, not a fix."),
]
FOLLOWUP_GAPS = (1, 1, 1, 2, 2, 2, 3, 3, 4, 5, 6, 7)       # days back to the story that a follow-up develops; a fifth of the days, mostly within a week


def followup_hook(fresh: str, development: str) -> str:
    """A development item restates the story it develops, as follow-up news does."""
    core = fresh.rstrip(".")
    return "Follow-up on the story that %s: %s" % (core[0].lower() + core[1:], development[0].lower() + development[1:])


def make_stream(seed: int, days: int = 60, followups: int = 12, first_followup_day: int = 8) -> List[dict]:
    """Fresh stories on most days, a development of an earlier story on `followups` days, base 1 to 7 days back."""
    if days - followups > len(POOL):
        raise ValueError("the pool has only %d stories" % len(POOL))
    rng = sim.Lcg(seed)
    for _attempt in range(200):       # a draw that leaves some follow-up without a free base is redrawn (it happened for 3 of the first 39 seeds)
        follow_days = sorted(rng.shuffled(range(first_followup_day, days + 1))[:followups])
        gaps = rng.shuffled(FOLLOWUP_GAPS[:followups])
        base_of: Dict[int, int] = {}
        used: set = set()
        for day, gap in zip(follow_days, gaps):
            for g in [gap] + [x for x in range(1, 8) if x != gap]:
                base = day - g
                if base >= 1 and base not in follow_days and base not in used:
                    base_of[day], used = base, used | {base}
                    break
            else:
                break
        if len(base_of) == followups:
            break
    else:
        raise ValueError("no stream with %d follow-ups could be built for seed %d" % (followups, seed))
    fresh_days = [d for d in range(1, days + 1) if d not in base_of]
    order = rng.shuffled(range(len(POOL)))
    story_of = {d: order[k] for k, d in enumerate(fresh_days)}
    stream = []
    for day in range(1, days + 1):
        if day in base_of:
            index = story_of[base_of[day]]
            stream.append({"day": day, "kind": "followup", "theme": POOL[index][0], "hook": followup_hook(POOL[index][1], POOL[index][2]), "base_day": base_of[day], "story": index})
        else:
            index = story_of[day]
            stream.append({"day": day, "kind": "fresh", "theme": POOL[index][0], "hook": POOL[index][1], "base_day": None, "story": index})
    return stream


class Embedder:
    """Unit-length sentence embeddings from a local copy of a model (offline), shared by all threads. Tests pass a fake one with the same interface."""

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        import os
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer
        self.model_name = model
        self._encoder = SentenceTransformer(model, device="cpu")
        self._lock = threading.Lock()

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        with self._lock:
            return [list(map(float, row)) for row in self._encoder.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def calibrate_threshold(embedder, seeds: Sequence[int] = (100, 101, 102), days: int = 60, recall: float = 0.9, step: float = 0.05) -> dict:
    """From task inputs alone (no model text): the highest threshold, in steps of `step`, that still keeps `recall` of the true
    follow-up -> base pairs, and the share of fresh days that would then receive a spurious match. Run on streams not used in the experiment."""
    pair_cosines: List[float] = []
    fresh_best: List[float] = []
    for seed in seeds:
        stream = make_stream(seed, days)
        vectors = embedder.encode([t["hook"] for t in stream])
        for t in stream:
            day = t["day"]
            if t["kind"] == "followup":
                pair_cosines.append(cosine(vectors[day - 1], vectors[t["base_day"] - 1]))
            elif day > 1:
                fresh_best.append(max(cosine(vectors[day - 1], vectors[j]) for j in range(day - 1)))
    pair_cosines.sort()
    cut = pair_cosines[int((1 - recall) * len(pair_cosines))]
    tau = round(int(cut / step) * step, 4)
    spurious = sum(1 for best in fresh_best if best >= tau)
    return {"threshold": tau, "followup_pairs": len(pair_cosines), "recall_target": recall, "followup_cosine_min": round(pair_cosines[0], 4),
            "followup_cosine_median": round(pair_cosines[len(pair_cosines) // 2], 4), "fresh_days": len(fresh_best),
            "fresh_days_with_a_spurious_match": spurious, "spurious_share": round(spurious / len(fresh_best), 4)}


@dataclass
class ArmState:
    arm: str
    tau: float
    notes: Dict[int, str] = field(default_factory=dict)
    traces: Dict[int, dict] = field(default_factory=dict)

    def memory(self, day: int, vectors: Sequence[Sequence[float]]) -> Tuple[str, List[int]]:
        """The notes block for day `day` and the earlier days it draws on. vectors[d - 1] is the embedding of the task input of day d."""
        if self.arm in ("A0", CONTROL_ARM) or not self.notes:
            return "", []
        ranked = sorted(((cosine(vectors[day - 1], vectors[d - 1]), d) for d in self.notes), key=lambda p: (-p[0], -p[1]))[:SHOWN]
        if self.arm != "A1":
            ranked = [p for p in ranked if p[0] >= self.tau]
        ids = sorted(d for _, d in ranked)
        if not ids:
            return "", []
        if self.arm == "A3":
            lines = []
            for d in ids:
                t = self.traces[d]
                line = "[Your note from day %d, summarised] %s" % (d, t["gist"].rstrip("."))
                line += ". Angle: %s" % t["angle"].rstrip(".") if t["angle"] else ""
                line += ". Left open: %s" % t["open"].rstrip(".") if t["open"] else ""
                lines.append(line + ".")
            return "\n".join(lines), ids
        return "\n\n".join("[Your note from day %d]\n%s" % (d, self.notes[d]) for d in ids), ids

    def record(self, day: int, text: str, trace: Optional[dict]) -> None:
        self.notes[day] = text
        if trace is not None:
            self.traces[day] = trace


def build_prompt(task: dict, block: str, instruction_only: bool = False) -> str:
    parts = ["Item: " + task["hook"], ""]
    if block or instruction_only:
        parts += ["Notes from your own earlier entries (they may or may not be relevant today):", block or "(none)", "",
                  "Use the notes only if they help. Do not repeat what you have already said; build on it, correct it, or refer back to it briefly "
                  "when the item is a development of something you wrote before.", ""]
    parts += ["Write today's note: about 90 words, in the first person, plain prose, no title and no labels."]
    return "\n".join(parts)


def build_trace_prompt(text: str) -> str:
    return ("Note:\n%s\n\nWrite a memory note about this note, exactly four lines:\n"
            "GIST: <what the note said or argued, at most 20 words>\nANGLE: <the specific point or example it used, at most 10 words>\n"
            "OPEN: <anything left open or promised, at most 12 words, or none>\nKEYWORDS: <five distinctive lowercase words, comma-separated>" % text)


def clean_note(raw: str) -> str:
    text = " ".join(line.strip() for line in raw.strip().splitlines() if line.strip()).replace("**", "")
    for label in ("note:", "today's note:", "text:"):
        if text.lower().startswith(label):
            text = text[len(label):].strip()
    return text


def write_note(state: ArmState, task: dict, seed: int, vectors: Sequence[Sequence[float]], generate: Generate) -> dict:
    block, shown = state.memory(task["day"], vectors)
    result = generate(PERSONA, build_prompt(task, block, state.arm == CONTROL_ARM), seed * 1000 + task["day"], WRITE_OPTS)
    text = clean_note(str(result["text"]))
    trace = None
    if state.arm == "A3":
        trace = sim.parse_trace(str(generate(TRACE_SYSTEM, build_trace_prompt(text), sim.TRACE_SEED, TRACE_OPTS)["text"]), text)
    state.record(task["day"], text, trace)
    return {"seed": seed, "arm": state.arm, "day": task["day"], "kind": task["kind"], "theme": task["theme"], "hook": task["hook"],
            "base_day": task["base_day"], "story": task["story"], "text": text, "words": len(text.split()), "shown_days": shown,
            "memory_block": block, "trace": trace, "prompt_tokens": result.get("prompt_tokens"), "gen_tokens": result.get("gen_tokens"),
            "wall_s": result.get("wall_s")}


def load_records(path: Path) -> List[dict]:
    return sim.load_records(path)


def replay(records: Sequence[dict], seed: int, arm: str, tau: float) -> ArmState:
    state = ArmState(arm, tau)
    for r in sorted((r for r in records if r["seed"] == seed and r["arm"] == arm), key=lambda r: r["day"]):
        state.record(r["day"], r["text"], r["trace"])
    return state


def run(records_path: Path, generate: Generate, embedder, tau: float, seeds: Sequence[int], days: int, arms: Sequence[str], workers: int,
        log: Callable[[str], None] = print) -> int:
    existing = load_records(records_path)
    done = {(r["seed"], r["arm"], r["day"]) for r in existing}
    written, started = 0, time.time()
    for seed in seeds:
        stream = make_stream(seed, days)
        vectors = embedder.encode([t["hook"] for t in stream])
        states = {arm: replay(existing, seed, arm, tau) for arm in arms}
        for task in stream:
            todo = [arm for arm in arms if (seed, arm, task["day"]) not in done]
            if not todo:
                continue
            with ThreadPoolExecutor(max_workers=max(1, min(workers, len(todo)))) as pool:
                futures = {arm: pool.submit(write_note, states[arm], task, seed, vectors, generate) for arm in todo}
                rows = [futures[arm].result() for arm in todo]
            with records_path.open("a", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += len(rows)
            log("seed %s day %2d/%d  +%d notes  elapsed %.0fs" % (seed, task["day"], days, len(rows), time.time() - started))
    return written
