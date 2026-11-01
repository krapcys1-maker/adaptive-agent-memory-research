#!/usr/bin/env python3
"""AAM-E1-SIM harness: does showing a writing agent its own earlier entries change what it writes?

An offline simulation: no real agent, no real readers, no data from any real account. A fictional columnist
writes one short entry per simulated day. Six themes come back every few days with a new news hook, so there is
always something earlier to repeat or to refer back to. Five arms differ only in the notes about the writer's own
earlier entries that are placed in the prompt:

  M0   nothing
  M1   the last three entries, in full (what a naive agent loop does)
  M2   the three earlier entries most similar to today's trigger (BM25), in full (raw own-history retrieval)
  M3a  one short trace per earlier entry (gist, angle, what was left open); the three most similar (BM25)
  M3b  M3a plus dynamic importance (a trace gains weight when a later entry explicitly refers back to it and loses
       weight with age) and association (traces that share keywords or were used together pull each other in)

Everything except the model's text is deterministic. Standard library only; talks only to a local Ollama server.
Design, hypotheses and decision rules: data/lab/aam-e1-writer-memory-sim/README.md and config.json, written before
the first run.

Usage: python scripts/writer_memory_sim.py --records PATH [--model qwen2.5:7b-instruct] [--seeds 1 2 3]
                                           [--days 36] [--workers 5] [--arms M0 M1 M2 M3a M3b] [--max-days N]
The run appends one JSON line per entry and can be stopped and started again; finished entries are not redone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

OLLAMA_URL = "http://localhost:11434"
ARMS: Tuple[str, ...] = ("M0", "M1", "M2", "M3a", "M3b")

PERSONA = (
    "You are Ola Wren, a columnist who writes a short daily entry about work and everyday life. "
    "Your voice is dry, concrete and a little self-mocking; you prefer one specific example to a general claim. "
    "You never use stock openings such as 'in today's fast-paced world'. "
    "Recurring things in your life: your late grandfather's pocket watch, which runs four minutes slow and which you "
    "still wear; your allotment, where you test small ideas on tomatoes; and a friendly rivalry with a columnist "
    "called Piotr who writes about productivity. You keep a running list of small experiments you have tried on yourself."
)

THEMES: Dict[str, List[str]] = {
    "meetings": [
        "A firm bans meetings before 10 a.m. for a month.",
        "A survey says the average worker spends eleven hours a week in meetings.",
        "A startup replaces its weekly status meeting with a shared document.",
        "A manager cancels every recurring meeting and watches which ones come back.",
        "A study finds standing meetings run shorter but decide less.",
        "A team tries 'no agenda, no meeting' for a quarter.",
    ],
    "email and messages": [
        "A bank adds a mandatory 24-hour delay to internal group emails.",
        "A chat tool introduces quiet hours that mute notifications at night.",
        "A study finds people check messages every six minutes at work.",
        "A company deletes all email older than 90 days.",
        "A founder answers email only twice a day and publishes the results.",
        "A team switches from chat to a weekly written update.",
    ],
    "remote and hybrid work": [
        "A city council reports that empty offices cost it more than expected.",
        "A company announces a four-day week trial.",
        "A survey finds hybrid workers sleep forty minutes longer.",
        "A firm requires everyone back in the office on Tuesdays.",
        "A coworking space opens in a village of four hundred people.",
        "A manager measures a remote team only by finished work.",
    ],
    "learning and skills": [
        "A library offers free coding evenings for retirees.",
        "A study finds adults learn languages faster with short daily sessions.",
        "A company pays staff for an hour of learning each Friday.",
        "A college drops one required course in favour of a project.",
        "A mentor programme pairs new hires with people from other departments.",
        "A teacher publishes her failed lesson plans.",
    ],
    "money and prices": [
        "Supermarkets shrink packages without lowering prices.",
        "A town introduces a local currency for small shops.",
        "A bank starts rounding up card payments to fund savings.",
        "A survey says most people cannot guess what they spent last month.",
        "A shop publishes how it sets its prices.",
        "Rent rises faster than pay in a mid-sized city.",
    ],
    "habits and routines": [
        "A study finds morning routines matter less than consistent wake times.",
        "A runner explains why she quit tracking her steps.",
        "An office installs a stairs-only sign and measures the effect.",
        "A writer works in forty-minute blocks with a kitchen timer.",
        "A gym reports that most January sign-ups stop by March.",
        "A company introduces a daily ten-minute walk break.",
    ],
}

STOP = frozenset(
    "the and but for with from that this these those into over after before about than then too very can will would "
    "should could has have had does did not our your their them his her its they you she him who how why what when "
    "which there here also just more most some any all one two are was were been being out off per via".split()
)

WRITE_OPTS = {"temperature": 0.8, "top_p": 0.95, "num_predict": 320}
TRACE_OPTS = {"temperature": 0.0, "top_p": 1.0, "num_predict": 120}
TRACE_SEED = 7

TRACE_SYSTEM = "You write terse memory notes for a columnist. Reply with exactly four lines and nothing else."

# Fixed in the preregistration before any run: an explicit reference to an earlier piece of the writer's own
# writing. Narrated life events ("last week I tried ...") are fiction in this genre and deliberately do not count.
CALLBACK_PATTERNS = tuple(re.compile(p, re.I) for p in (
    r"\bas i (?:wrote|said|noted|mentioned|argued)\b",
    r"\bi (?:wrote|noted|mentioned|argued|described|admitted|said)\b[^.]{0,60}"
    r"\b(?:earlier|before|previously|recently|last (?:week|month|time)|(?:days?|weeks?) ago)\b",
    r"\bmy (?:earlier|previous|last|recent) (?:entry|entries|column|columns|post|posts|note|notes|piece)\b",
    r"\b(?:earlier|previous|last) (?:entry|column|post)\b",
    r"\bwhen i (?:first |last )?wrote\b",
    r"\bi(?:'ve| have) (?:written|mentioned|noted) (?:about )?(?:this|that|it)\b",
))
DAY_REFERENCE = re.compile(r"\bday (\d+)\b", re.I)
WORD = re.compile(r"[a-z0-9']+")

Generate = Callable[[str, str, int, Dict[str, float]], Dict[str, object]]


class Lcg:
    """Small deterministic generator: a stream must not depend on the Python version's random module."""

    def __init__(self, seed: int) -> None:
        self.state = (seed * 2654435761 + 12345) % (2 ** 31)

    def next(self) -> int:
        self.state = (1103515245 * self.state + 12345) % (2 ** 31)
        return self.state >> 8

    def shuffled(self, items: Sequence) -> list:
        out = list(items)
        for i in range(len(out) - 1, 0, -1):
            j = self.next() % (i + 1)
            out[i], out[j] = out[j], out[i]
        return out


def make_stream(seed: int, days: int = 36) -> List[dict]:
    """One theme per day; every theme once per round of six days, each with a fresh hook."""
    themes = list(THEMES)
    if days % len(themes) or days // len(themes) > len(THEMES[themes[0]]):
        raise ValueError("days must be a multiple of %d and at most %d" % (len(themes), len(themes) * len(THEMES[themes[0]])))
    rng = Lcg(seed)
    hook_order = {theme: rng.shuffled(range(len(THEMES[theme]))) for theme in themes}
    stream: List[dict] = []
    for round_ in range(days // len(themes)):
        for position, theme in enumerate(rng.shuffled(themes)):
            stream.append({"day": round_ * len(themes) + position + 1, "theme": theme,
                           "hook": THEMES[theme][hook_order[theme][round_]]})
    return stream


def content_tokens(text: str) -> List[str]:
    return [w for w in WORD.findall(text.lower()) if len(w) > 2 and w not in STOP]


def bm25_scores(query: Sequence[str], docs: Dict[int, List[str]], k1: float = 1.2, b: float = 0.75) -> Dict[int, float]:
    n = len(docs)
    if not n:
        return {}
    average = (sum(len(d) for d in docs.values()) / n) or 1.0
    frequency: Dict[str, int] = {}
    for tokens in docs.values():
        for word in set(tokens):
            frequency[word] = frequency.get(word, 0) + 1
    scores: Dict[int, float] = {}
    for key, tokens in docs.items():
        counts = Counter(tokens)
        total = 0.0
        for word in set(query):
            tf = counts.get(word, 0)
            if not tf:
                continue
            idf = math.log(1 + (n - frequency[word] + 0.5) / (frequency[word] + 0.5))
            total += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(tokens) / average))
        scores[key] = total
    return scores


def top_ids(scores: Dict[int, float], k: int) -> List[int]:
    """Highest positive scores first; a tie goes to the more recent day."""
    ranked = sorted(((s, d) for d, s in scores.items() if s > 0), key=lambda p: (-p[0], -p[1]))
    return [d for _, d in ranked[:k]]


def callback_extended(text: str, day: Optional[int] = None) -> bool:
    """An explicit reference to an earlier own entry; a bare 'day N' counts only for N < day."""
    if any(p.search(text) for p in CALLBACK_PATTERNS):
        return True
    return day is not None and any(int(n) < day for n in DAY_REFERENCE.findall(text))


def parse_entry(raw: str) -> Tuple[str, str]:
    lines = [line.strip().replace("**", "") for line in raw.strip().splitlines()]
    title, start = "", 0
    for index, line in enumerate(lines):
        if line:
            title = re.sub(r"^[#\s]*(?:title\s*:\s*)?", "", line, flags=re.I).strip(" \"'#")
            start = index + 1
            break
    body = re.sub(r"^(?:text|entry)\s*:\s*", "", " ".join(line for line in lines[start:] if line), flags=re.I)
    return title, body or title


def parse_trace(raw: str, entry_text: str) -> dict:
    fields: Dict[str, str] = {}
    for label in ("gist", "angle", "open", "keywords"):
        match = re.search(r"^\W*%s\s*:\s*(.+)$" % label, raw, re.I | re.M)
        fields[label] = match.group(1).strip() if match else ""
    keywords: List[str] = []
    for word in re.split(r"[,;\s]+", fields["keywords"].lower()):
        word = word.strip(".'\"")
        if len(word) > 2 and word not in STOP and word not in keywords:
            keywords.append(word)
    if len(keywords) < 3:
        for word, _ in Counter(content_tokens(entry_text)).most_common():
            if word not in keywords:
                keywords.append(word)
            if len(keywords) >= 5:
                break
    gist = fields["gist"] or re.split(r"(?<=[.!?])\s", entry_text.strip(), maxsplit=1)[0]
    opened = "" if fields["open"].strip(" .").lower() in ("none", "nothing", "") else fields["open"]
    return {"gist": gist, "angle": fields["angle"], "open": opened, "keywords": keywords[:5]}


@dataclass
class Trace:
    day: int
    title: str
    gist: str
    angle: str
    open: str
    keywords: List[str]
    uses: int = 0
    last_used: Optional[int] = None
    theme: str = ""

    @property
    def text(self) -> str:
        return " ".join([self.title, self.theme, self.gist, self.angle, self.open] + self.keywords)


@dataclass
class ArmState:
    """What one arm remembers. record() is the only way state changes, live or on replay."""

    name: str
    entries: Dict[int, Tuple[str, str]] = field(default_factory=dict)
    themes: Dict[int, str] = field(default_factory=dict)
    traces: Dict[int, Trace] = field(default_factory=dict)
    edges: Dict[Tuple[int, int], float] = field(default_factory=dict)

    def importance(self, trace_day: int, today: int) -> float:
        trace = self.traces[trace_day]
        return min(3.0, max(0.25, 1.0 + 0.5 * trace.uses - 0.5 * (today - trace.day) / 30.0))

    def memory(self, day: int, theme: str, hook: str) -> Tuple[str, List[int]]:
        """The notes block placed in the prompt and the ids (days) it draws on."""
        if self.name == "M0" or not self.entries:
            return "", []
        query = content_tokens(theme + " " + hook)
        if self.name == "M1":
            ids = sorted(self.entries)[-3:]
            return self._render_entries(ids), ids
        if self.name == "M2":
            docs = {d: content_tokens(title + " " + text + " " + self.themes.get(d, "")) for d, (title, text) in self.entries.items()}
            ids = sorted(top_ids(bm25_scores(query, docs), 3))
            return self._render_entries(ids), ids
        scores = bm25_scores(query, {d: content_tokens(t.text) for d, t in self.traces.items()})
        if self.name == "M3b":
            scores = {d: s * self.importance(d, day) for d, s in scores.items()}
            ids = top_ids(scores, 2)
            neighbour = self._neighbour(ids)
            ids = sorted(ids + ([neighbour] if neighbour is not None else []))
        else:
            ids = sorted(top_ids(scores, 3))
        return self._render_traces(ids), ids

    def record(self, day: int, title: str, text: str, shown: Sequence[int], trace: Optional[dict], theme: str = "") -> None:
        self.entries[day] = (title, text)
        self.themes[day] = theme
        if self.name not in ("M3a", "M3b") or trace is None:
            return
        new = Trace(day, title, trace["gist"], trace["angle"], trace["open"], list(trace["keywords"]), theme=theme)
        self.traces[day] = new
        if self.name == "M3b":
            self._update_dynamics(new, text, shown)

    # -- internals ------------------------------------------------------------------------------------------
    def _render_entries(self, ids: Sequence[int]) -> str:
        return "\n\n".join("[Entry from day %d]\nTITLE: %s\n%s" % (d, *self.entries[d]) for d in ids)

    def _render_traces(self, ids: Sequence[int]) -> str:
        lines = []
        for d in ids:
            t = self.traces[d]
            line = "[Note from day %d] \"%s\" - said: %s" % (d, t.title, t.gist.rstrip("."))
            if t.angle:
                line += ". Angle: %s" % t.angle.rstrip(".")
            if t.open:
                line += ". Left open: %s" % t.open.rstrip(".")
            lines.append(line + ".")
        return "\n".join(lines)

    def _link(self, a: int, b: int, weight: float, add: bool = False) -> None:
        key = (min(a, b), max(a, b))
        self.edges[key] = min(1.0, self.edges.get(key, 0.0) + weight) if add else max(self.edges.get(key, 0.0), weight)

    def _neighbour(self, ids: Sequence[int]) -> Optional[int]:
        best: Optional[Tuple[float, int]] = None
        for j in self.traces:
            if j in ids:
                continue
            weight = max((self.edges.get((min(i, j), max(i, j)), 0.0) for i in ids), default=0.0)
            if weight >= 0.15 and (best is None or (weight, j) > best):
                best = (weight, j)
        return best[1] if best else None

    def _update_dynamics(self, new: Trace, text: str, shown: Sequence[int]) -> None:
        words = set(content_tokens(text))
        used: List[int] = []
        if callback_extended(text, new.day):
            for i in shown:
                if i in self.traces and len(words & set(self.traces[i].keywords)) >= 2:
                    self.traces[i].uses += 1
                    self.traces[i].last_used = new.day
                    used.append(i)
        mine = set(new.keywords)
        for j, other in self.traces.items():
            if j == new.day:
                continue
            union = mine | set(other.keywords)
            overlap = len(mine & set(other.keywords)) / len(union) if union else 0.0
            if overlap >= 0.2:
                self._link(new.day, j, overlap)
        group = used + ([new.day] if used else [])
        for x in range(len(group)):
            for y in range(x + 1, len(group)):
                self._link(group[x], group[y], 0.25, add=True)


def build_user_prompt(item: dict, block: str) -> str:
    parts = ["Day %d. Theme: %s." % (item["day"], item["theme"]), "Today's trigger: " + item["hook"], ""]
    if block:
        parts += ["Notes from your own earlier entries (they may or may not be relevant today):", block, "",
                  "Use the notes only if they help. Do not repeat what you have already said; build on it, contrast "
                  "with it, or refer back to it briefly when that adds something.", ""]
    parts += ["Write today's entry: a title, then 110 to 150 words in the first person.",
              "Reply in exactly this form and use no other labels:", "TITLE: <the title>", "", "<the entry, as plain prose>"]
    return "\n".join(parts)


def build_trace_prompt(title: str, text: str) -> str:
    return ("Entry:\nTITLE: %s\n%s\n\nWrite a memory note about this entry, exactly four lines:\n"
            "GIST: <what the entry said or argued, at most 20 words>\n"
            "ANGLE: <the specific example or angle it used, at most 10 words>\n"
            "OPEN: <anything promised or left open, at most 12 words, or none>\n"
            "KEYWORDS: <five distinctive lowercase words, comma-separated>" % (title, text))


def write_entry(state: ArmState, item: dict, seed: int, generate: Generate) -> dict:
    block, shown = state.memory(item["day"], item["theme"], item["hook"])
    result = generate(PERSONA, build_user_prompt(item, block), seed * 1000 + item["day"], WRITE_OPTS)
    title, text = parse_entry(str(result["text"]))
    trace = None
    if state.name in ("M3a", "M3b"):
        trace = parse_trace(str(generate(TRACE_SYSTEM, build_trace_prompt(title, text), TRACE_SEED, TRACE_OPTS)["text"]), text)
    state.record(item["day"], title, text, shown, trace, item["theme"])
    return {"seed": seed, "arm": state.name, "day": item["day"], "theme": item["theme"], "hook": item["hook"],
            "title": title, "text": text, "words": len(text.split()), "shown_ids": shown, "memory_block": block,
            "trace": trace, "prompt_tokens": result.get("prompt_tokens"), "gen_tokens": result.get("gen_tokens"),
            "wall_s": result.get("wall_s")}


def ollama_chat(model: str, system: str, user: str, seed: int, opts: Dict[str, float], num_ctx: int = 4096,
                retries: int = 3) -> Dict[str, object]:
    body = json.dumps({"model": model, "stream": False, "keep_alive": "3h",
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                       "options": dict(opts, seed=seed, num_ctx=num_ctx)}).encode()
    request = urllib.request.Request(OLLAMA_URL + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    for attempt in range(retries):
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=900) as handle:
                data = json.load(handle)
            return {"text": data["message"]["content"], "prompt_tokens": data.get("prompt_eval_count"),
                    "gen_tokens": data.get("eval_count"), "wall_s": round(time.time() - started, 2)}
        except (OSError, ValueError, KeyError):
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def ollama_meta(model: str) -> dict:
    def fetch(path: str, payload: Optional[dict] = None) -> dict:
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(OLLAMA_URL + path, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as handle:
            return json.load(handle)
    digest = next((m.get("digest") for m in fetch("/api/tags").get("models", []) if m.get("name") == model), None)
    return {"model": model, "model_digest": digest, "ollama_version": fetch("/api/version").get("version")}


def load_records(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def replay(records: Sequence[dict], seed: int, arm: str) -> ArmState:
    state = ArmState(arm)
    for r in sorted((r for r in records if r["seed"] == seed and r["arm"] == arm), key=lambda r: r["day"]):
        state.record(r["day"], r["title"], r["text"], r["shown_ids"], r["trace"], r["theme"])
    return state


def run(records_path: Path, generate: Generate, seeds: Sequence[int], days: int, arms: Sequence[str], workers: int,
        max_days: Optional[int] = None, log: Callable[[str], None] = print) -> int:
    existing = load_records(records_path)
    done = {(r["seed"], r["arm"], r["day"]) for r in existing}
    written = 0
    started = time.time()
    for seed in seeds:
        states = {arm: replay(existing, seed, arm) for arm in arms}
        for item in make_stream(seed, days)[:max_days]:
            todo = [arm for arm in arms if (seed, arm, item["day"]) not in done]
            if not todo:
                continue
            with ThreadPoolExecutor(max_workers=max(1, min(workers, len(todo)))) as pool:
                futures = {arm: pool.submit(write_entry, states[arm], item, seed, generate) for arm in todo}
                rows = [futures[arm].result() for arm in todo]
            with records_path.open("a", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += len(rows)
            log("seed %s day %2d/%d  +%d entries  elapsed %.0fs" % (seed, item["day"], days, len(rows), time.time() - started))
    return written


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AAM-E1-SIM writer-memory simulation against a local Ollama model.")
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--model", default="qwen2.5:7b-instruct")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--days", type=int, default=36)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    parser.add_argument("--max-days", type=int, default=None, help="stop each seed after this many days (smoke tests)")
    args = parser.parse_args(argv)
    meta_path = args.records.with_name("run-meta.json")
    meta = ollama_meta(args.model)
    meta.update({"write_options": WRITE_OPTS, "trace_options": TRACE_OPTS, "num_ctx": 4096, "seeds": args.seeds,
                 "days": args.days, "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    if meta_path.exists():
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
        for key in ("model", "model_digest", "harness_sha256"):
            if previous.get(key) != meta[key]:
                print("refusing to continue: %s differs from the first run (%r vs %r)" % (key, previous.get(key), meta[key]),
                      file=sys.stderr)
                return 2
    else:
        meta["first_started"] = datetime.now().isoformat(timespec="seconds")
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    generate: Generate = lambda system, user, seed, opts: ollama_chat(args.model, system, user, seed, opts)
    written = run(args.records, generate, args.seeds, args.days, args.arms, args.workers, args.max_days,
                  log=lambda line: print(line, flush=True))
    print("done: %d new entries" % written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
