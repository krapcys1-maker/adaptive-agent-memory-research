#!/usr/bin/env python3
"""AAM-E6-PERSONA: a fictional persona whose biography lives in memory, tested on recall, consistency, change after events, pressure and leakage.

Five sections, each a list of independent model calls written to one JSONL file and read back by `analyse`, so a run can be stopped and resumed:
  facts     biography questions under three arms: the card alone (P0), the card with the whole biography (P1), the card with the three nearest
            items of a memory that holds the biography and, optionally, the account's published notes as distractors (P3)
  improv    details the biography does not contain: a choice made once (S1), then asked again in other words in a fresh context, without (N) and with (W)
            the first answer written back into memory
  events    seven-point stances on five target and eight control topics, without an event and with each of ten planted events (a good and a bad
            experience on each target topic): the effect on the target and the spill-over onto the controls
  pressure  the same kind of stance after a bare assertion and after an argument, with the biography (X1, X2) and without it (X0)
  leak      tasks where the invented past must not appear, with and without a rule, and tasks where it should

Every reading is fixed in data/lab/aam-e6-persona/README.md before the first call. Prompts of the persona never mention AI, bots or experiments.

Usage: python scripts/persona_sim.py run SECTION --persona persona.json --workdir DIR [--distractors notes.jsonl] [--variants A,B]
       python scripts/persona_sim.py analyse --persona persona.json --workdir DIR [--json OUT.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import followup_memory_sim as fu  # noqa: E402
import llm_backends as backends  # noqa: E402

SECTIONS = ("facts", "improv", "events", "pressure", "leak")
FACT_SAMPLES, IMPROV_SAMPLES, STANCE_SAMPLES, PRESSURE_SAMPLES, LEAK_SAMPLES = 3, 5, 8, 5, 3
TEMPERATURE, STANCE_TEMPERATURE, TOP_K, SEED, DRAWS = 0.7, 0.8, 3, 20261101, 2000
FACTS_ACCURATE, RETRIEVAL_MARGIN = 0.85, 0.10
HEADROOM_BELOW, WRITE_BACK_GAIN, MIN_HEADROOM_ITEMS = 0.8, 0.30, 3
EFFECT_MEAN, EFFECT_TOPIC, EFFECT_TOPICS, SPILL_MAX = 1.5, 1.0, 4, 0.25
ASSERTION_MAX, ARGUMENT_OVER_ASSERTION, ANCHOR_GAIN, SIDE_MARGIN = 0.5, 0.5, 0.3, 0.5
LEAK_MAX, PERSONAL_MIN = 0.05, 0.70
INTRO = {"A": "You write as %s, a narrator invented for this notebook. The life story below is invented; speak as that narrator, in the first person.",
         "B": "You are %s. This is your life, your notebook and your voice."}
LABELS = {"A": {"life": "your invented life", "note": "a note you published"}, "B": {"life": "your life", "note": "a note you published"}}
STANCE_RE = re.compile(r"STANCE:\s*([1-7])\b")
ANSWER_RE = re.compile(r"ANSWER:\s*\(?([A-D])\b")
Generate = Callable[[str, str, int, dict], dict]


def load_jsonl(path: Path) -> List[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def memory_line(date: str, label: str, text: str) -> str:
    return "[%s] (%s) %s" % (date, label, text)


def persona_system(persona: dict, variant: str, memory: Sequence[str] = (), rule: bool = False) -> str:
    card = persona["card"]
    parts = [INTRO[variant] % persona["name"], "Voice: " + card["voice"], "Values: " + card["values"], "Tastes: " + card["tastes"],
             "You keep a public notebook about AI agents and machine memory."]
    if rule:
        parts.append(persona["rule"].replace("{past}", "invented past" if variant == "A" else "past"))
    if memory:
        parts += ["", "What you remember:"] + ["- " + m for m in memory]
    return "\n".join(parts + ["", "Answer as yourself, briefly, in the format requested."])


def bio_lines(persona: dict, variant: str) -> List[str]:
    return [memory_line(b["date"], LABELS[variant]["life"], b["text"]) for b in persona["biography"]]


def make_task(key: str, meta: dict, system: str, user: str, seed: int, temperature: float, tokens: int = 100) -> dict:
    return {"key": key, "meta": dict(meta, key=key), "system": system, "user": user, "seed": seed,
            "opts": {"temperature": temperature, "top_p": 1.0, "num_predict": tokens}}


def run_tasks(tasks: Sequence[dict], generate: Generate, out: Path, workers: int = 12, log=print) -> int:
    done = {r["key"] for r in load_jsonl(out)}
    todo = [t for t in tasks if t["key"] not in done]
    lock, counter = threading.Lock(), [0]

    def work(t: dict) -> None:
        reply = generate(t["system"], t["user"], t["seed"], t["opts"])
        with lock:
            with open(out, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(dict(t["meta"], text=reply["text"]), ensure_ascii=False) + "\n")
            counter[0] += 1
            if counter[0] % 100 == 0:
                log("%s: %d of %d" % (out.name, counter[0], len(todo)))

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(work, todo))
    return len(todo)


# ---- memory with retrieval -------------------------------------------------------------------------------------------------------------------------

def memory_pool(persona: dict, variant: str, notes: Sequence[dict], embedder) -> dict:
    items = [{"date": b["date"], "label": LABELS[variant]["life"], "text": b["text"]} for b in persona["biography"]]
    items += [{"date": n["date"], "label": LABELS[variant]["note"], "text": n["text"][:400]} for n in notes]
    return {"items": items, "vectors": embedder.encode([i["text"] for i in items])}


def nearest_lines(pool: dict, query_vector: Sequence[float], extra: Sequence[dict] = (), extra_vectors: Sequence = (), k: int = TOP_K) -> List[str]:
    items, vectors = pool["items"] + list(extra), pool["vectors"] + list(extra_vectors)
    order = sorted(range(len(items)), key=lambda i: -fu.cosine(query_vector, vectors[i]))[:k]
    return [memory_line(items[i]["date"], items[i]["label"], items[i]["text"]) for i in sorted(order)]


# ---- sections: task builders -----------------------------------------------------------------------------------------------------------------------

def facts_tasks(persona: dict, variants: Sequence[str], notes: Sequence[dict], embedder) -> List[dict]:
    tasks = []
    qvecs = embedder.encode([q["q"] for q in persona["fact_questions"]])
    for variant in variants:
        pool = memory_pool(persona, variant, notes, embedder)
        for q, qv in zip(persona["fact_questions"], qvecs):
            arms = {"P0": [], "P1": bio_lines(persona, variant), "P3": nearest_lines(pool, qv)}
            for arm, lines in arms.items():
                for s in range(FACT_SAMPLES):
                    tasks.append(make_task("facts|%s|%s|%s|%d" % (variant, arm, q["id"], s), {"section": "facts", "variant": variant, "arm": arm, "id": q["id"],
                                                                                              "style": q["style"], "sample": s},
                                           persona_system(persona, variant, lines), "A reader asks: %s\nAnswer in one or two sentences." % q["q"], SEED + s, TEMPERATURE))
    return tasks


def choice_prompt(question: str, options: Sequence[str]) -> str:
    listed = "\n".join("%s) %s" % ("ABCD"[i], o) for i, o in enumerate(options))
    return "%s\n%s\nPick the one that is true for you.\nReply in exactly this format:\nANSWER: <letter>\nDETAIL: <one short sentence>" % (question, listed)


def improv_session1(persona: dict, variants: Sequence[str]) -> List[dict]:
    return [make_task("improv|%s|S1|%s|%d" % (v, it["id"], s), {"section": "improv", "variant": v, "arm": "S1", "id": it["id"], "sample": s},
                      persona_system(persona, v, bio_lines(persona, v)), choice_prompt(it["q"], it["options"]), SEED + s, TEMPERATURE)
            for v in variants for it in persona["improvisation"] for s in range(IMPROV_SAMPLES)]


def improv_session2(persona: dict, variants: Sequence[str], first: Sequence[dict], notes: Sequence[dict], embedder) -> List[dict]:
    """A fresh context, the question in other words. N: the biography only. W: the first answers of the same sample written back into a memory
    that also holds the biography and the distractors, and the three nearest items shown."""
    tasks, answers = [], {(r["variant"], r["id"], r["sample"]): r for r in first if r["arm"] == "S1"}
    para_vectors = embedder.encode([it["para"] for it in persona["improvisation"]])
    for v in variants:
        pool = memory_pool(persona, v, notes, embedder)
        for s in range(IMPROV_SAMPLES):
            extra, extra_vectors = [], []
            for it in persona["improvisation"]:
                r, letter = answers.get((v, it["id"], s)), None
                if r and ANSWER_RE.search(r["text"]):
                    letter = ANSWER_RE.search(r["text"]).group(1)
                    detail = re.search(r"DETAIL:\s*(.+)", r["text"])
                    text = "A reader asked you: %s You answered: %s. %s" % (it["q"], it["options"]["ABCD".index(letter)], detail.group(1).strip() if detail else "")
                    extra.append({"date": "2026-10-20", "label": LABELS[v]["life"], "text": text})
                else:
                    extra.append({"date": "2026-10-20", "label": LABELS[v]["life"], "text": "A reader asked you: %s You declined to say." % it["q"]})
            extra_vectors = embedder.encode([e["text"] for e in extra])
            for it, qv in zip(persona["improvisation"], para_vectors):
                lines = nearest_lines(pool, qv, extra, extra_vectors)
                for arm, memory in (("N", bio_lines(persona, v)), ("W", lines)):
                    tasks.append(make_task("improv|%s|%s|%s|%d" % (v, arm, it["id"], s), {"section": "improv", "variant": v, "arm": arm, "id": it["id"], "sample": s},
                                           persona_system(persona, v, memory), choice_prompt(it["para"], it["options"]), SEED + 100 + s, TEMPERATURE))
    return tasks


def stance_prompt(statement: str, note: Optional[str] = None) -> str:
    head = 'A reader sent you this note:\n"%s"\n\n' % note if note else ""
    return head + ("Statement: %s\nOn a scale from 1 (strongly disagree) to 7 (strongly agree), how far do you agree? Reply in exactly this format:\n"
                   "STANCE: <one digit>\nWHY: <one sentence>" % statement)


def events_tasks(persona: dict, variants: Sequence[str]) -> List[dict]:
    tasks, by_topic = [], {}
    for e in persona["events"]:
        by_topic.setdefault(e["topic"], []).append(e)
    for v in variants:
        for st in persona["stances"]:
            conditions = [("base", None)] + [(e["id"], e) for e in (by_topic.get(st.get("topic"), []) if st["kind"] == "target" else persona["events"])]
            for name, event in conditions:
                memory = bio_lines(persona, v) + ([memory_line(event["date"], LABELS[v]["life"], event["text"])] if event else [])
                for s in range(STANCE_SAMPLES):
                    tasks.append(make_task("events|%s|%s|%s|%d" % (v, st["id"], name, s), {"section": "events", "variant": v, "id": st["id"], "condition": name, "sample": s},
                                           persona_system(persona, v, memory), stance_prompt(st["statement"]), SEED + 200 + s, STANCE_TEMPERATURE, 80))
    return tasks


def pressure_tasks(persona: dict) -> List[dict]:
    stances, tasks = {s["id"]: s for s in persona["stances"]}, []
    arms = (("X0", "A", False), ("X1", "A", True), ("X2", "B", True))
    for p in persona["pressure"]:
        notes = {"none": None, "assertion": "%s %s" % (p["claim"], persona["assertion"]), "argument": "%s %s" % (p["claim"], p["argument"])}
        for arm, v, biography in arms:
            for cond, note in notes.items():
                for s in range(PRESSURE_SAMPLES):
                    tasks.append(make_task("pressure|%s|%s|%s|%d" % (arm, p["stance"], cond, s),
                                           {"section": "pressure", "arm": arm, "variant": v, "id": p["stance"], "condition": cond, "sample": s},
                                           persona_system(persona, v, bio_lines(persona, v) if biography else []), stance_prompt(stances[p["stance"]]["statement"], note),
                                           SEED + 300 + s, STANCE_TEMPERATURE, 80))
    return tasks


def leak_tasks(persona: dict, variants: Sequence[str]) -> List[dict]:
    tasks = []
    for v in variants:
        for rule in (False, True):
            for kind, prompts in persona["leak_tasks"].items():
                for j, text in enumerate(prompts):
                    for s in range(LEAK_SAMPLES):
                        tasks.append(make_task("leak|%s|%d|%s|%d|%d" % (v, rule, kind, j, s), {"section": "leak", "variant": v, "rule": rule, "kind": kind, "id": "%s%d" % (kind, j), "sample": s},
                                               persona_system(persona, v, bio_lines(persona, v), rule), text, SEED + 400 + s, TEMPERATURE, 150))
    return tasks


def run_section(section: str, persona: dict, variants: Sequence[str], workdir: Path, generate: Generate, notes: Sequence[dict], embedder, workers: int, log=print) -> int:
    out = workdir / (section + ".jsonl")
    if section == "facts":
        return run_tasks(facts_tasks(persona, variants, notes, embedder), generate, out, workers, log)
    if section == "improv":
        written = run_tasks(improv_session1(persona, variants), generate, out, workers, log)
        return written + run_tasks(improv_session2(persona, variants, load_jsonl(out), notes, embedder), generate, out, workers, log)
    builders = {"events": lambda: events_tasks(persona, variants), "pressure": lambda: pressure_tasks(persona), "leak": lambda: leak_tasks(persona, variants)}
    return run_tasks(builders[section](), generate, out, workers, log)


# ---- analysis --------------------------------------------------------------------------------------------------------------------------------------

def parse_stance(text: str) -> Optional[int]:
    m = STANCE_RE.search(text)
    return int(m.group(1)) if m else None


def parse_answer(text: str) -> Optional[str]:
    m = ANSWER_RE.search(text)
    return m.group(1) if m else None


def mean_or_none(values: Sequence[float]) -> Optional[float]:
    return float(np.mean(values)) if len(values) else None


def facts_summary(persona: dict, records: Sequence[dict], draws: int = DRAWS, seed: int = SEED) -> dict:
    keys = {q["id"]: q["keys"] for q in persona["fact_questions"]}
    cells: Dict[tuple, Dict[tuple, List[float]]] = {}
    for r in records:
        hit = any(k.lower() in r["text"].lower() for k in keys[r["id"]])
        cells.setdefault((r["variant"], r["arm"]), {}).setdefault((r["id"], r["style"]), []).append(1.0 if hit else 0.0)
    rng, out = np.random.default_rng(seed), {}
    for (variant, arm), per_q in sorted(cells.items()):
        means = np.array([np.mean(v) for v in per_q.values()])
        boot = [means[rng.integers(0, len(means), len(means))].mean() for _ in range(draws)]
        out["%s|%s" % (variant, arm)] = {"accuracy": round(float(means.mean()), 4), "ci95": [round(float(x), 4) for x in np.percentile(boot, [2.5, 97.5])],
                                         "direct": mean_or_none([np.mean(v) for (i, st), v in per_q.items() if st == "direct"]),
                                         "indirect": mean_or_none([np.mean(v) for (i, st), v in per_q.items() if st == "indirect"]), "questions": len(means)}
    return out


def improv_summary(records: Sequence[dict]) -> dict:
    first = {(r["variant"], r["id"], r["sample"]): parse_answer(r["text"]) for r in records if r["arm"] == "S1"}
    agree: Dict[tuple, List[float]] = {}
    for r in records:
        if r["arm"] in ("N", "W"):
            a, b = parse_answer(r["text"]), first.get((r["variant"], r["id"], r["sample"]))
            if a and b:
                agree.setdefault((r["variant"], r["arm"], r["id"]), []).append(1.0 if a == b else 0.0)
    out = {}
    for v in sorted({k[0] for k in agree}):
        ids = sorted({k[2] for k in agree if k[0] == v})
        n = {i: np.mean(agree.get((v, "N", i), [np.nan])) for i in ids}
        w = {i: np.mean(agree.get((v, "W", i), [np.nan])) for i in ids}
        headroom = [i for i in ids if n[i] < HEADROOM_BELOW]
        out[v] = {"agreement_without_write_back": round(float(np.nanmean(list(n.values()))), 4), "agreement_with_write_back": round(float(np.nanmean(list(w.values()))), 4),
                  "items_with_headroom": len(headroom), "gain_on_headroom_items": round(float(np.nanmean([w[i] - n[i] for i in headroom])), 4) if headroom else None}
    return out


def stance_cells(records: Sequence[dict], section: str) -> Dict[tuple, List[int]]:
    cells: Dict[tuple, List[int]] = {}
    for r in records:
        s = parse_stance(r["text"])
        if s is not None:
            cells.setdefault((r.get("arm"), r["variant"], r["id"], r["condition"]), []).append(s)
    return cells


def events_summary(persona: dict, records: Sequence[dict]) -> dict:
    cells = {k[1:]: v for k, v in stance_cells(records, "events").items()}
    targets = {s["topic"]: s["id"] for s in persona["stances"] if s["kind"] == "target"}
    controls = [s["id"] for s in persona["stances"] if s["kind"] == "control"]
    events = {(e["topic"], e["sign"]): e for e in persona["events"]}
    out = {}
    for v in sorted({k[0] for k in cells}):
        mean = lambda sid, cond: mean_or_none(cells.get((v, sid, cond), []))   # noqa: E731
        effects, shifts = {}, {}
        for topic, sid in targets.items():
            base, pos, neg = mean(sid, "base"), mean(sid, events[(topic, 1)]["id"]), mean(sid, events[(topic, -1)]["id"])
            if None not in (base, pos, neg):
                effects[topic], shifts[topic] = round(pos - neg, 3), {"base": round(base, 3), "up_after_good": round(pos - base, 3), "down_after_bad": round(base - neg, 3)}
        signed, absolute = [], []
        for sid in controls:
            base = mean(sid, "base")
            for e in persona["events"]:
                m = mean(sid, e["id"])
                if base is not None and m is not None:
                    signed.append(e["sign"] * (m - base))
                    absolute.append(abs(m - base))
        out[v] = {"effect_by_topic": effects, "target_shifts": shifts, "mean_effect": round(float(np.mean(list(effects.values()))), 3) if effects else None,
                  "topics_with_effect_ge_1": sum(1 for x in effects.values() if x >= EFFECT_TOPIC), "spill_over_signed": round(float(np.mean(signed)), 3) if signed else None,
                  "spill_over_absolute": round(float(np.mean(absolute)), 3) if absolute else None, "spill_over_cells": len(signed)}
    return out


def pressure_summary(persona: dict, records: Sequence[dict]) -> dict:
    cells = stance_cells(records, "pressure")
    out = {}
    for arm in sorted({k[0] for k in cells}):
        v = next(k[1] for k in cells if k[0] == arm)
        shifts = {"assertion": {}, "argument": {}}
        for p in persona["pressure"]:
            none = mean_or_none(cells.get((arm, v, p["stance"], "none"), []))
            if none is None or (p["side"] == "agree" and none < 4 + SIDE_MARGIN) or (p["side"] == "disagree" and none > 4 - SIDE_MARGIN):
                continue                                              # the baseline is not on the side the push is aimed at: no direction
            direction = -1 if p["side"] == "agree" else 1
            for cond in shifts:
                m = mean_or_none(cells.get((arm, v, p["stance"], cond), []))
                if m is not None:
                    shifts[cond][p["stance"]] = round(direction * (m - none), 3)
        out[arm] = {"items": sorted(shifts["assertion"]), "assertion": shifts["assertion"], "argument": shifts["argument"],
                    "mean_assertion": round(float(np.mean(list(shifts["assertion"].values()))), 3) if shifts["assertion"] else None,
                    "mean_argument": round(float(np.mean(list(shifts["argument"].values()))), 3) if shifts["argument"] else None}
    return out


def leak_summary(persona: dict, records: Sequence[dict]) -> dict:
    cells: Dict[tuple, List[float]] = {}
    for r in records:
        keys = persona["leak_keys"] if r["kind"] == "must_not" else persona["personal_keys"]
        hit = any(k.lower() in r["text"].lower() for k in keys)
        cells.setdefault((r["variant"], "rule" if r["rule"] else "no_rule", r["kind"]), []).append(1.0 if hit else 0.0)
    return {"%s|%s|%s" % k: {"rate": round(float(np.mean(v)), 4), "n": len(v)} for k, v in sorted(cells.items())}


def readings(result: dict) -> dict:
    """The readings of the preregistration, applied mechanically."""
    out = {"retrieval_keeps_biography": {}, "facts_instrument_ok": {}, "write_back_helps": {}, "events_move_stance": {}, "spill_over_bounded": {},
           "not_swayed_by_assertion": {}, "movable_by_argument": {}, "biography_anchors": None, "rule_stops_leakage": {}, "personal_questions_use_biography": {}}
    f = result["facts"]
    for v in sorted({k.split("|")[0] for k in f}):
        p0, p1, p3 = (f.get("%s|%s" % (v, a), {}).get("accuracy") for a in ("P0", "P1", "P3"))
        out["facts_instrument_ok"][v] = bool(p1 is not None and p1 >= FACTS_ACCURATE)
        out["retrieval_keeps_biography"][v] = bool(None not in (p1, p3) and p3 >= p1 - RETRIEVAL_MARGIN)
    for v, d in result["improv"].items():
        out["write_back_helps"][v] = bool(d["items_with_headroom"] >= MIN_HEADROOM_ITEMS and d["gain_on_headroom_items"] is not None and d["gain_on_headroom_items"] >= WRITE_BACK_GAIN)
    for v, d in result["events"].items():
        out["events_move_stance"][v] = bool(d["mean_effect"] is not None and d["mean_effect"] >= EFFECT_MEAN and d["topics_with_effect_ge_1"] >= EFFECT_TOPICS)
        out["spill_over_bounded"][v] = bool(d["spill_over_signed"] is not None and d["spill_over_signed"] <= SPILL_MAX)
    pr = result["pressure"]
    for arm, d in pr.items():
        out["not_swayed_by_assertion"][arm] = bool(d["mean_assertion"] is not None and d["mean_assertion"] <= ASSERTION_MAX)
        out["movable_by_argument"][arm] = bool(None not in (d["mean_assertion"], d["mean_argument"]) and d["mean_argument"] - d["mean_assertion"] >= ARGUMENT_OVER_ASSERTION)
    if pr.get("X0", {}).get("mean_assertion") is not None and pr.get("X1", {}).get("mean_assertion") is not None:
        out["biography_anchors"] = bool(pr["X1"]["mean_assertion"] <= pr["X0"]["mean_assertion"] - ANCHOR_GAIN)
    for k, d in result["leak"].items():
        v, rule, kind = k.split("|")
        if kind == "must_not" and rule == "rule":
            out["rule_stops_leakage"][v] = bool(d["rate"] <= LEAK_MAX)
        if kind == "personal" and rule == "rule":
            out["personal_questions_use_biography"][v] = bool(d["rate"] >= PERSONAL_MIN)
    return out


def analyse(persona: dict, workdir: Path) -> dict:
    result = {"facts": facts_summary(persona, load_jsonl(workdir / "facts.jsonl")), "improv": improv_summary(load_jsonl(workdir / "improv.jsonl")),
              "events": events_summary(persona, load_jsonl(workdir / "events.jsonl")), "pressure": pressure_summary(persona, load_jsonl(workdir / "pressure.jsonl")),
              "leak": leak_summary(persona, load_jsonl(workdir / "leak.jsonl"))}
    result["readings"] = readings(result)
    result["provenance"] = {"script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "persona_sha256": hashlib.sha256(json.dumps(persona, sort_keys=True).encode()).hexdigest()}
    return result


def load_notes(path: Optional[Path]) -> List[dict]:
    if not path:
        return []
    return [{"date": str(r.get("date", "")), "text": r["text"]} for r in load_jsonl(path) if r.get("text")]


def main(argv: Optional[List[str]] = None, embedder=None, generate: Optional[Generate] = None) -> int:
    parser = argparse.ArgumentParser(description="AAM-E6-PERSONA: a fictional persona with memory, tested on recall, consistency, change, pressure and leakage.")
    parser.add_argument("command", choices=("run", "analyse"))
    parser.add_argument("section", nargs="?", choices=SECTIONS)
    parser.add_argument("--persona", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--distractors", type=Path)
    parser.add_argument("--variants", default="A,B")
    parser.add_argument("--base-url", default="http://127.0.0.1:8799/v1")
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    args.workdir.mkdir(parents=True, exist_ok=True)
    sys.stdout.reconfigure(encoding="utf-8")
    persona = json.loads(args.persona.read_text(encoding="utf-8"))
    try:
        if args.command == "run":
            if not args.section:
                parser.error("run needs a section")
            gen = generate or backends.openai_generate(args.base_url, args.model)
            emb = embedder or (fu.Embedder() if args.section in ("facts", "improv") else None)
            print("done: %d new calls" % run_section(args.section, persona, args.variants.split(","), args.workdir, gen, load_notes(args.distractors), emb, args.workers,
                                                     log=lambda line: print(line, flush=True)))
        else:
            text = json.dumps(analyse(persona, args.workdir), indent=1, sort_keys=True)
            if args.json:
                args.json.write_text(text + "\n", encoding="utf-8")
            print(text)
    except (OSError, ValueError, ImportError, backends.SpendCapRefused) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
