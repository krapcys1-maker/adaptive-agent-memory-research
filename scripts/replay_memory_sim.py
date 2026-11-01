#!/usr/bin/env python3
"""AAM-E5-REPLAY: the memory arms of AAM-E2-FU replayed on an account's real published history.

The owner's rule is tests on data, not on guesses. AAM-E2-FU used authored stories and near-ideal retrieval. Here the memory is the account's
real earlier notes, the recurrence of topics is the real one (about a fifth of the notes have a related earlier note), and retrieval is
imperfect because it works from a one-sentence brief of the new note's topic, as a live pipeline working from a task input would.

For each real note i from WARMUP on: a brief (one neutral sentence, written once by the model from the note), the three earlier notes most
similar to the brief, a threshold chosen so that a fifth of the tasks have a candidate. Five arms write a new note from the brief:
R0 nothing, R0i the instruction without notes, R1 the three nearest earlier notes always, R2 the same only above the threshold, R3 traces of
the notes above the threshold. Notes written by the model are synthetic but conditioned on the real history: they stay in a local work
directory outside the repository; only aggregates are published. Design and rules: data/lab/aam-e5-replay/README.md.

Subcommands: prepare, write, judge, analyse. Needs the optional sentence-transformers package for the embedder (offline).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_followup_memory_sim as afu  # noqa: E402
import analyze_writer_memory_sim as ana  # noqa: E402
import followup_memory_sim as fu  # noqa: E402
import llm_backends as backends  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402
import writer_memory_sim as sim  # noqa: E402

WARMUP = 20
ARMS: Tuple[str, ...] = ("R0", "R0i", "R1", "R2", "R3")
CANDIDATE_SHARE = 0.20            # matched to the 20.6% of real notes that have a related earlier note at note-to-note cosine 0.6
NONCANDIDATE_SAMPLE = 80
CANDIDATE_PAIRS = (("R2", "R0"), ("R3", "R0"), ("R2", "R0i"), ("R3", "R0i"), ("R3", "R2"), ("R1", "R0"), ("R2", "R1"), ("R0i", "R0"))
OTHER_PAIRS = (("R1", "R0"), ("R2", "R0"), ("R3", "R0"), ("R0i", "R0"))
WIN_RATE = 0.60
HARM_BELOW = 0.5
CONTROL_NEEDED = 0.75
GROUNDING_COSINE = 0.5
CONTROLS = 12
BRIEF_SYSTEM = "You write neutral one-sentence descriptions of notes. Reply with the sentence only."
BRIEF_OPTS = {"temperature": 0.0, "top_p": 1.0, "num_predict": 60}


def brief_prompt(text: str) -> str:
    return ("Note:\n%s\n\nDescribe in one sentence, at most 25 words, what this note is about, as an item a writer could be given to write about. "
            "Do not quote the note, do not mention earlier notes, do not use the first person." % text)


def top_candidates(brief_vector: Sequence[float], note_vectors: Sequence[Sequence[float]], i: int, k: int = 3) -> List[Tuple[int, float]]:
    ranked = sorted(((fu.cosine(brief_vector, note_vectors[j]), j) for j in range(i)), key=lambda p: (-p[0], -p[1]))[:k]
    return [(j, round(c, 4)) for c, j in ranked]


def choose_threshold(top1: Sequence[float], share: float = CANDIDATE_SHARE) -> float:
    ordered = sorted(top1)
    return ordered[min(len(ordered) - 1, int((1 - share) * len(ordered)))]


def prepare(items: Sequence[sbm.Item], embedder, generate: backends.Generate, workers: int = 12) -> dict:
    texts = [i.text for i in items]

    def brief(k: int) -> str:
        return fu.clean_note(str(generate(BRIEF_SYSTEM, brief_prompt(texts[k]), 7, BRIEF_OPTS)["text"]))

    def trace(k: int) -> dict:
        return sim.parse_trace(str(generate(fu.TRACE_SYSTEM, fu.build_trace_prompt(texts[k]), sim.TRACE_SEED, fu.TRACE_OPTS)["text"]), texts[k])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        briefs, traces = list(pool.map(brief, range(len(items)))), list(pool.map(trace, range(len(items))))
    note_vectors, brief_vectors = embedder.encode(texts), embedder.encode(briefs)
    top = [top_candidates(brief_vectors[i], note_vectors, i) if i else [] for i in range(len(items))]
    tau = choose_threshold([t[0][1] for i, t in enumerate(top) if i >= WARMUP and t])
    return {"briefs": briefs, "traces": traces, "top": top, "tau": tau}


def memory_block(arm: str, i: int, prep: dict, items: Sequence[sbm.Item]) -> Tuple[str, List[int]]:
    if arm in ("R0", "R0i"):
        return "", []
    candidates = prep["top"][i]
    if arm != "R1":
        candidates = [(j, c) for j, c in candidates if c >= prep["tau"]]
    shown = sorted(j for j, _ in candidates)
    if not shown:
        return "", []
    if arm == "R3":
        lines = []
        for j in shown:
            t = prep["traces"][j]
            line = "[Your earlier note, %s, summarised] %s" % (items[j].day, t["gist"].rstrip("."))
            line += ". Angle: %s" % t["angle"].rstrip(".") if t["angle"] else ""
            line += ". Left open: %s" % t["open"].rstrip(".") if t["open"] else ""
            lines.append(line + ".")
        return "\n".join(lines), shown
    return "\n\n".join("[Your earlier note, %s]\n%s" % (items[j].day, items[j].text) for j in shown), shown


def is_candidate(prep: dict, i: int) -> bool:
    return bool(prep["top"][i]) and prep["top"][i][0][1] >= prep["tau"]


def write_all(items: Sequence[sbm.Item], prep: dict, out: Path, generate: backends.Generate, workers: int = 12, log=print) -> int:
    done = set()
    if out.exists():
        done = {(r["i"], r["arm"]) for r in (json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip())}
    todo = [(i, arm) for i in range(WARMUP, len(items)) for arm in ARMS if (i, arm) not in done]
    lock, written = threading.Lock(), 0

    def one(i: int, arm: str) -> dict:
        block, shown = memory_block(arm, i, prep, items)
        text = fu.clean_note(str(generate(fu.PERSONA, fu.build_prompt({"hook": prep["briefs"][i]}, block, arm == "R0i"), 1000 + i, fu.WRITE_OPTS)["text"]))
        return {"i": i, "arm": arm, "candidate": is_candidate(prep, i), "ref": prep["top"][i][0][0] if prep["top"][i] else None, "shown": shown,
                "text": text, "words": len(text.split())}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool, out.open("a", encoding="utf-8") as handle:
        for future in as_completed([pool.submit(one, i, arm) for i, arm in todo]):
            row = future.result()
            with lock:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                written += 1
                if written % 200 == 0:
                    log("wrote %d/%d" % (written, len(todo)))
    return written


def pair_prompt(brief: str, reference: Optional[str], note1: str, note2: str) -> str:
    ref = ("The author's earlier note on a related topic:\n%s\n\n" % reference) if reference else "The author has no earlier note on this topic.\n\n"
    return ("Item the author is writing about: %s\n\n%sNOTE 1:\n%s\n\nNOTE 2:\n%s\n\nWhich is the better public note on this item, given what the author has already written? "
            "Prefer the note that fits the item, adds something new, refers to the earlier note only where that really helps, and does not repeat it or force a reference.\n"
            "Reply with one line in the form WINNER: 1, WINNER: 2 or WINNER: TIE." % (brief, ref, note1, note2))


def pair_tasks(records: Sequence[dict]) -> List[dict]:
    cell = {(r["i"], r["arm"]): r for r in records}
    tasks = []
    candidate_ids = sorted({r["i"] for r in records if r["candidate"]})
    other_ids = sorted({r["i"] for r in records if not r["candidate"]})
    chosen = [other_ids[k] for k in sim.Lcg(2026).shuffled(range(len(other_ids)))[:NONCANDIDATE_SAMPLE]]
    for i in candidate_ids:
        for x, y in CANDIDATE_PAIRS:
            if (i, x) in cell and (i, y) in cell:
                tasks += [{"i": i, "x": x, "y": y, "order": o, "stratum": "candidate"} for o in (0, 1)]
    for i in sorted(chosen):
        for x, y in OTHER_PAIRS:
            if (i, x) in cell and (i, y) in cell:
                tasks += [{"i": i, "x": x, "y": y, "order": o, "stratum": "other"} for o in (0, 1)]
    for i in candidate_ids[:CONTROLS]:
        tasks += [{"i": i, "x": "R0", "y": "copy", "order": o, "stratum": "control"} for o in (0, 1)]
    return tasks


def judge_all(items: Sequence[sbm.Item], prep: dict, records: Sequence[dict], out: Path, generate: backends.Generate, workers: int = 12, log=print) -> int:
    cell = {(r["i"], r["arm"]): r for r in records}
    done = set()
    if out.exists():
        done = {(r["i"], r["x"], r["y"], r["order"]) for r in (json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip())}
    todo = [t for t in pair_tasks(records) if (t["i"], t["x"], t["y"], t["order"]) not in done]
    lock, written = threading.Lock(), 0

    def one(t: dict) -> dict:
        i = t["i"]
        reference = items[prep["top"][i][0][0]].text if t["stratum"] != "other" else None
        note_x = cell[(i, t["x"])]["text"]
        note_y = reference if t["y"] == "copy" else cell[(i, t["y"])]["text"]
        first, second = (note_x, note_y) if t["order"] == 0 else (note_y, note_x)
        raw = str(generate(afu.PAIR_SYSTEM, pair_prompt(prep["briefs"][i], reference, first, second), afu.JUDGE_SEED, afu.PAIR_OPTS)["text"])
        winner = afu.parse_winner(raw)
        return dict(t, winner=winner, x_score=afu.x_score_of(winner, t["order"]), raw=raw.strip()[:40])

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool, out.open("a", encoding="utf-8") as handle:
        for future in as_completed([pool.submit(one, t) for t in todo]):
            row = future.result()
            with lock:
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                written += 1
                if written % 200 == 0:
                    log("compared %d/%d" % (written, len(todo)))
    return written


def win_rates(results: Sequence[dict], stratum: str, pairs: Sequence[Tuple[str, str]], draws: int = ana.DRAWS) -> dict:
    cache: Dict[int, list] = {}
    out = {}
    for x, y in pairs:
        by_task: Dict[int, List[float]] = {}
        for r in results:
            if r["stratum"] == stratum and r["x"] == x and r["y"] == y and r.get("x_score") is not None:
                by_task.setdefault(r["i"], []).append(r["x_score"])
        scores = [sum(v) / len(v) for v in by_task.values()]
        if scores:
            low, high = ana.interval(scores, cache, draws)
            out["%s-%s" % (x, y)] = {"win_rate": sum(scores) / len(scores), "ci_low": low, "ci_high": high, "n": len(scores)}
    return out


def deterministic(items: Sequence[sbm.Item], records: Sequence[dict], embedder) -> dict:
    vectors = embedder.encode([r["text"] for r in records] + [i.text for i in items])
    note_vectors = {j: vectors[len(records) + j] for j in range(len(items))}
    table: Dict[str, Dict[str, List[float]]] = {}
    for r, v in zip(records, vectors):
        cell = table.setdefault(r["arm"] + (":candidate" if r["candidate"] else ":other"), {"references": [], "grounded": [], "words": []})
        reference = 1.0 if sim.callback_extended(r["text"]) else 0.0
        cell["references"].append(reference)
        cell["words"].append(float(r["words"]))
        if r["candidate"]:
            cell["grounded"].append(1.0 if reference and fu.cosine(v, note_vectors[r["ref"]]) >= GROUNDING_COSINE else 0.0)
    return {k: {m: (sum(x) / len(x) if x else None) for m, x in v.items()} | {"n": len(v["references"])} for k, v in sorted(table.items())}


def readings(results: Sequence[dict], draws: int = ana.DRAWS) -> dict:
    cand, other = win_rates(results, "candidate", CANDIDATE_PAIRS, draws), win_rates(results, "other", OTHER_PAIRS, draws)
    controls = [r for r in results if r["stratum"] == "control" and r.get("x_score") is not None]
    control_rate = (sum(1 for r in controls if r["x_score"] > 0.5) / len(controls)) if controls else None

    def wins(name: str) -> bool:
        e = cand.get(name)
        return bool(e and e["win_rate"] >= WIN_RATE and e["ci_low"] > 0.5)

    def harmed(name: str) -> bool:
        e = other.get(name)
        return bool(e and e["ci_high"] < HARM_BELOW)

    gains = [arm for arm in ("R2", "R3") if wins("%s-R0" % arm) and wins("%s-R0i" % arm)]
    return {"judge_informative": control_rate is not None and control_rate >= CONTROL_NEEDED, "control_win_rate": control_rate, "candidate_tasks": cand, "other_tasks": other,
            "memory_helps_on_real_candidates": bool(gains) and control_rate is not None and control_rate >= CONTROL_NEEDED, "arms_that_gain": gains,
            "thresholded_arms_harm_other_tasks": [a for a in ("R2", "R3") if harmed("%s-R0" % a)], "always_on_harms_other_tasks": harmed("R1-R0"),
            "traces_vs_notes": ("traces better" if wins("R3-R2") else "notes better" if (cand.get("R3-R2") and cand["R3-R2"]["ci_high"] < 0.5 and cand["R3-R2"]["win_rate"] <= 1 - WIN_RATE) else "equivalent here")}


def load_jsonl(path: Path) -> List[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main(argv: Optional[List[str]] = None, embedder=None) -> int:
    parser = argparse.ArgumentParser(description="AAM-E5-REPLAY: memory arms replayed on an account's real published history.")
    parser.add_argument("command", choices=("prepare", "write", "judge", "analyse"))
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8799/v1")
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    args.workdir.mkdir(parents=True, exist_ok=True)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        with open(args.items, encoding="utf-8") as handle:
            items = sbm.parse_items(handle)
        generate = backends.openai_generate(args.base_url, args.model)
        prep_path, records_path, pairs_path = args.workdir / "prep.json", args.workdir / "records.jsonl", args.workdir / "pairs.jsonl"
        if args.command == "prepare":
            prep = prepare(items, embedder or fu.Embedder(), generate, args.workers)
            prep_path.write_text(json.dumps(prep, ensure_ascii=False), encoding="utf-8")
            print("prepared %d briefs and traces; threshold %.4f; tasks with a candidate: %d of %d" % (
                len(items), prep["tau"], sum(is_candidate(prep, i) for i in range(WARMUP, len(items))), len(items) - WARMUP))
            return 0
        prep = json.loads(prep_path.read_text(encoding="utf-8"))
        if args.command == "write":
            print("done: %d new notes" % write_all(items, prep, records_path, generate, args.workers, log=lambda l: print(l, flush=True)))
        elif args.command == "judge":
            print("done: %d new comparisons" % judge_all(items, prep, load_jsonl(records_path), pairs_path, generate, args.workers, log=lambda l: print(l, flush=True)))
        else:
            result = {"tau": prep["tau"], "tasks": len(items) - WARMUP, "candidates": sum(is_candidate(prep, i) for i in range(WARMUP, len(items))),
                      "deterministic": deterministic(items, load_jsonl(records_path), embedder or fu.Embedder()), "judge": readings(load_jsonl(pairs_path)),
                      "provenance": {"script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
            text = json.dumps(result, indent=1, sort_keys=True)
            if args.json:
                args.json.write_text(text + "\n", encoding="utf-8")
            print(text)
    except (OSError, ValueError, ImportError, backends.SpendCapRefused) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
