#!/usr/bin/env python3
"""Analysis of AAM-E2-FU: deterministic measures, a blind judge with planted controls, and the readings fixed in advance.

Subcommands
  measures      RECORDS [--json OUT] [--md OUT]            overlap, explicit and grounded references back, spurious ones, length; paired contrasts by stratum
  judge-run     RECORDS --out JUDGMENTS [--backend openai --base-url URL | ollama] --model M [--workers N] [--sample-fresh F]
  judge-analyse RECORDS JUDGMENTS... [--json OUT] [--md OUT]   one result per judgments file, then the readings applied mechanically

Standard library plus, for the grounded-reference measure, the optional embedder of followup_memory_sim. Deterministic: the bootstrap uses
its own generator. Design, thresholds and readings: data/lab/aam-e2-followup-memory-sim/README.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_writer_memory_sim as ana  # noqa: E402
import followup_memory_sim as fu  # noqa: E402
import llm_backends as backends  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402
import writer_memory_sim as sim  # noqa: E402

ANALYSIS_FROM = 8
KINDS = ("followup", "fresh")
CONTRASTS = (("A1", "A0"), ("A2", "A0"), ("A3", "A0"), ("A2", "A1"), ("A3", "A1"), ("A3", "A2"),
             ("A0i", "A0"), ("A1", "A0i"), ("A2", "A0i"), ("A3", "A0i"))
DIMENSIONS = ("fit", "fresh", "continuity", "quality")
GROUNDING_COSINE = 0.5
PRIMARY_THRESHOLD = 0.5
TRACE_VS_NOTES = 0.3
FRESH_QUALITY_HARM = 0.15
ACCEPT_SHARE = 0.75
CONTROLS_EACH = 12
CONTROL_SEED = 2026
FRESH_SAMPLE_SEED = 77
JUDGE_SYSTEM = "You are a careful, sceptical editor who scores short notes against a rubric. Reply with one line and nothing else."
JUDGE_OPTS = {"temperature": 0.0, "top_p": 1.0, "num_predict": 40}
JUDGE_SEED = 11
SCORE = re.compile(r"(?i)\b(fit|fresh|continuity|quality)\b\W{0,4}[:=]\s*([1-5])\b")


def mean(values: Sequence[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


# ---------------------------------------------------------------------------------------------------------- deterministic measures
def measure_all(rows: Sequence[dict], embedder=None) -> Dict[tuple, dict]:
    """{(arm, seed, day): measures}. Notes of an arm and a stream form its own history; grounding needs the embedder."""
    by_key = {(r["arm"], r["seed"], r["day"]): r for r in rows}
    texts = [r["text"] for r in rows]
    vectors = dict(zip((id(r) for r in rows), embedder.encode(texts))) if embedder is not None and rows else {}
    out: Dict[tuple, dict] = {}
    groups: Dict[tuple, List[dict]] = {}
    for r in rows:
        groups.setdefault((r["arm"], r["seed"]), []).append(r)
    for (arm, seed), group in groups.items():
        group.sort(key=lambda r: r["day"])
        items = [sbm.Item("%d-%s-%02d" % (seed, arm, r["day"]), date(2026, 1, 1) + timedelta(days=r["day"] - 1), r["text"]) for r in group]
        for index, r in enumerate(group):
            callback = sim.callback_extended(r["text"], r["day"])
            grounded: Optional[float] = None
            if r["kind"] == "followup" and embedder is not None:
                base = by_key.get((arm, seed, r["base_day"]))
                close = base is not None and fu.cosine(vectors[id(r)], vectors[id(base)]) >= GROUNDING_COSINE
                grounded = 1.0 if callback and close else 0.0
            out[(arm, seed, r["day"])] = {
                "overlap4": sbm.repetition_overlap(items, index, 400, 4), "callback_ext": 1.0 if callback else 0.0, "grounded_callback": grounded,
                "spurious_callback": (1.0 if callback else 0.0) if r["kind"] == "fresh" else None, "words": float(len(r["text"].split())),
                "kind": r["kind"]}
    return out


METRICS = ("overlap4", "callback_ext", "grounded_callback", "spurious_callback", "words")


def contrast(table: Dict[tuple, dict], key_of, a: str, b: str, kind: str, metric: str, cache: Dict[int, list], draws: int) -> Optional[dict]:
    """Paired by (stream, day) within one stratum. `key_of(arm, seed, day)` returns the value or None."""
    diffs = []
    for (arm, seed, day), cell in sorted(table.items()):
        if arm != a or cell["kind"] != kind or day < ANALYSIS_FROM:
            continue
        other = table.get((b, seed, day))
        va, vb = key_of(cell, metric), key_of(other, metric) if other else None
        if va is not None and vb is not None:
            diffs.append(va - vb)
    if not diffs:
        return None
    low, high = ana.interval(diffs, cache, draws)
    return {"mean": sum(diffs) / len(diffs), "ci_low": low, "ci_high": high, "n": len(diffs)}


def measures_analysis(rows: Sequence[dict], embedder=None, draws: int = ana.DRAWS) -> dict:
    table = measure_all(rows, embedder)
    arms = [a for a in fu.ALL_ARMS if any(r["arm"] == a for r in rows)]
    get = lambda cell, metric: cell.get(metric)  # noqa: E731
    cache: Dict[int, list] = {}
    means = {kind: {arm: {m: mean([c[m] for (a, s, d), c in table.items() if a == arm and c["kind"] == kind and d >= ANALYSIS_FROM]) for m in METRICS}
                    for arm in arms} for kind in KINDS}
    contrasts = {kind: {"%s-%s" % (a, b): {m: contrast(table, get, a, b, kind, m, cache, draws) for m in METRICS}
                        for a, b in CONTRASTS if a in arms and b in arms} for kind in KINDS}
    return {"arms": arms, "notes": len(rows), "arm_means": means, "contrasts": contrasts}


# ------------------------------------------------------------------------------------------------------------------------- judge
def parse_scores(raw: str) -> Dict[str, Optional[int]]:
    found = {name.lower(): int(value) for name, value in SCORE.findall(raw)}
    return {d: found.get(d) for d in DIMENSIONS}


def theme_history(rows: Sequence[dict], row: dict, k: int = 2) -> List[dict]:
    same = [r for r in rows if r["seed"] == row["seed"] and r["arm"] == row["arm"] and r["theme"] == row["theme"] and r["day"] < row["day"]]
    return sorted(same, key=lambda r: r["day"])[-k:]


def judge_prompt(row: dict, note: str, earlier: Sequence[dict]) -> str:
    head = "Author persona card:\n%s\n\n" % fu.PERSONA
    if row["kind"] == "followup":
        base = earlier[0]["text"] if earlier else "(missing)"
        return (head + "Item the author is writing about (a development of an earlier story): %s\n\nThe author's earlier note on that story:\n%s\n\nNote to score:\n%s\n\n"
                "Score the note from 1 (poor) to 5 (excellent):\nFIT: how well it responds to the item\n"
                "FRESH: how new its points and wording are compared with the earlier note above (1 = repeats it, 5 = clearly new)\n"
                "CONTINUITY: how well it builds on the earlier note: accurate about what that note said, specific about what changed, no contradiction, not a mere repetition\n"
                "QUALITY: overall, how good it is as a short public note\n\nReply with one line in the form FIT: <1-5>, FRESH: <1-5>, CONTINUITY: <1-5>, QUALITY: <1-5>."
                % (row["hook"], base, note))
    shown = "\n\n".join("[Earlier note, day %d]\n%s" % (e["day"], e["text"]) for e in earlier) or "(none)"
    return (head + "Item the author is writing about: %s\n\nEarlier notes by the author on the same theme (may be none):\n%s\n\nNote to score:\n%s\n\n"
            "Score the note from 1 (poor) to 5 (excellent):\nFIT: how well it responds to the item\n"
            "FRESH: how new its points and wording are compared with the earlier notes above (1 = repeats them, 5 = clearly new; 5 if there are none)\n"
            "QUALITY: overall, how good it is as a short public note\n\nReply with one line in the form FIT: <1-5>, FRESH: <1-5>, QUALITY: <1-5>."
            % (row["hook"], shown, note))


def base_note(rows: Sequence[dict], row: dict) -> List[dict]:
    return [r for r in rows if r["seed"] == row["seed"] and r["arm"] == row["arm"] and r["day"] == row["base_day"]]


def build_controls(rows: Sequence[dict], each: int = CONTROLS_EACH, seed: int = CONTROL_SEED) -> List[dict]:
    """From arm A0 follow-ups: 'copy' (the note replaced by the learner's earlier note on the story) and 'other' (replaced by a note on another story)."""
    a0 = sorted((r for r in rows if r["arm"] == "A0"), key=lambda r: (r["seed"], r["day"]))
    pool = [r for r in a0 if r["kind"] == "followup" and r["day"] >= ANALYSIS_FROM and base_note(a0, r)]
    controls = []
    for index, r in enumerate(sim.Lcg(seed).shuffled(pool)[:2 * each]):
        if index % 2 == 0:
            source, kind = base_note(a0, r)[0], "copy"
        else:
            source, kind = max((o for o in a0 if o["seed"] == r["seed"] and o["story"] != r["story"] and o["day"] < r["day"]), key=lambda o: o["day"]), "other"
        controls.append(dict(r, text=source["text"], control=kind))
    return controls


def fresh_sample(rows: Sequence[dict], share: float) -> List[dict]:
    rng = sim.Lcg(FRESH_SAMPLE_SEED)
    fresh = sorted((r for r in rows if r["kind"] == "fresh" and r["day"] >= ANALYSIS_FROM), key=lambda r: (r["seed"], r["arm"], r["day"]))
    return [r for r in fresh if (rng.next() % 1000) / 1000 < share]


def task_key(r: dict) -> tuple:
    return (r.get("control") or "real", r["seed"], r["arm"], r["day"])


def judge_run(rows: Sequence[dict], out: Path, generate: backends.Generate, workers: int = 4, sample_fresh: float = 1.0, log=print,
              controls_each: int = CONTROLS_EACH) -> int:
    real = [r for r in rows if r["day"] >= ANALYSIS_FROM and (r["kind"] == "followup" or r in fresh_sample(rows, sample_fresh))] \
        if sample_fresh < 1.0 else [r for r in rows if r["day"] >= ANALYSIS_FROM]
    tasks = sorted(real + build_controls(rows, controls_each), key=lambda r: (task_key(r)[0] != "real", r["seed"], r["day"], r["arm"]))
    done = set()
    if out.exists():
        done = {task_key(json.loads(line)) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()}
    todo = [t for t in tasks if task_key(t) not in done]
    lock, written = threading.Lock(), 0

    def one(task: dict) -> dict:
        history = [r for r in rows if r["arm"] == task["arm"] and r["seed"] == task["seed"]]
        earlier = base_note(history, task) if task["kind"] == "followup" else theme_history(history, task)
        raw = str(generate(JUDGE_SYSTEM, judge_prompt(task, task["text"], earlier), JUDGE_SEED, JUDGE_OPTS)["text"])
        return dict({"control": task.get("control"), "seed": task["seed"], "arm": task["arm"], "day": task["day"], "kind": task["kind"], "raw": raw.strip()[:80]},
                    **parse_scores(raw))

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool, out.open("a", encoding="utf-8") as handle:
        for future in as_completed([pool.submit(one, t) for t in todo]):
            row = future.result()
            with lock:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                written += 1
                if written % 100 == 0:
                    log("judged %d/%d" % (written, len(todo)))
    return written


def judge_analysis(judgments: Sequence[dict], draws: int = ana.DRAWS) -> dict:
    for j in judgments:
        if j.get("raw"):
            j.update({d: v for d, v in parse_scores(j["raw"]).items() if j.get(d) is None})
    real = [j for j in judgments if not j.get("control")]
    controls = [j for j in judgments if j.get("control")]
    arms = [a for a in fu.ALL_ARMS if any(j["arm"] == a for j in real)]
    cell = {(j["arm"], j["seed"], j["day"]): j for j in real}
    cache: Dict[int, list] = {}
    means = {kind: {arm: {d: mean([j[d] for j in real if j["arm"] == arm and j["kind"] == kind]) for d in DIMENSIONS} for arm in arms} for kind in KINDS}
    contrasts: Dict[str, dict] = {kind: {} for kind in KINDS}
    for kind in KINDS:
        for a, b in CONTRASTS:
            if a not in arms or b not in arms:
                continue
            entry = {}
            for d in DIMENSIONS:
                diffs = [cell[(a, s, day)][d] - cell[(b, s, day)][d] for (arm, s, day) in sorted(cell)
                         if arm == a and cell[(arm, s, day)]["kind"] == kind and (b, s, day) in cell
                         and cell[(a, s, day)][d] is not None and cell[(b, s, day)][d] is not None]
                if diffs:
                    low, high = ana.interval(diffs, cache, draws)
                    entry[d] = {"mean": sum(diffs) / len(diffs), "ci_low": low, "ci_high": high, "n": len(diffs)}
                else:
                    entry[d] = None
            contrasts[kind]["%s-%s" % (a, b)] = entry

    def noticed(kind: str, dimension: str) -> Optional[float]:
        scored = [j[dimension] for j in controls if j["control"] == kind and j.get(dimension) is not None]
        return sum(1 for v in scored if v <= 2) / len(scored) if scored else None

    checks = {"copy_fresh": noticed("copy", "fresh"), "copy_continuity": noticed("copy", "continuity"), "other_fit": noticed("other", "fit")}
    informative = {"fresh": checks["copy_fresh"] is not None and checks["copy_fresh"] >= ACCEPT_SHARE,
                   "continuity": checks["copy_continuity"] is not None and checks["copy_continuity"] >= ACCEPT_SHARE,
                   "fit": checks["other_fit"] is not None and checks["other_fit"] >= ACCEPT_SHARE}
    informative["quality"] = informative["fresh"] or informative["fit"]
    return {"arms": arms, "judged": len(real), "controls": len(controls), "arm_means": means, "contrasts": contrasts,
            "controls_check": checks, "informative": informative}


def reading_for_judge(result: dict) -> dict:
    c = result["contrasts"]
    follow, fresh = c["followup"], c["fresh"]

    def cont(name: str) -> Optional[dict]:
        return (follow.get(name) or {}).get("continuity")

    def quality(name: str) -> Optional[dict]:
        return (fresh.get(name) or {}).get("quality")

    controls = ["A0"] + (["A0i"] if "A0i" in result["arms"] else [])        # a gain counts only against every no-notes control that was run
    gain = {arm: [cont("%s-%s" % (arm, control)) for control in controls] for arm in ("A2", "A3")}
    gains = [arm for arm, gs in gain.items() if all(g and g["mean"] >= PRIMARY_THRESHOLD and g["ci_low"] > 0 for g in gs)]
    guard_ok = all(not (q and q["mean"] <= -FRESH_QUALITY_HARM and q["ci_high"] < 0) for q in (quality("A2-A0"), quality("A3-A0")))
    always = quality("A1-A0")
    tn = cont("A3-A2")
    return {"continuity_informative": result["informative"]["continuity"],
            "memory_helps_where_relevant": bool(gains) and guard_ok and result["informative"]["continuity"], "arms_that_gain": gains,
            "fresh_quality_guard_holds": guard_ok,
            "always_on_harms": bool(always and always["mean"] <= -FRESH_QUALITY_HARM and always["ci_high"] < 0),
            "traces_vs_notes": None if not tn else ("traces better" if tn["mean"] >= TRACE_VS_NOTES and tn["ci_low"] > 0 else
                                                   "notes better" if tn["mean"] <= -TRACE_VS_NOTES and tn["ci_high"] < 0 else "equivalent here")}


def final_readings(per_judge: Dict[str, dict], pairwise: Optional[dict] = None) -> dict:
    out = {name: reading_for_judge(res) for name, res in per_judge.items()}
    helps = [r["memory_helps_where_relevant"] for r in out.values() if r["continuity_informative"]]
    harms = [r["always_on_harms"] for r in out.values()]
    if pairwise is not None:                                   # the pairwise judge is one more judge: it counts only if it passes its control
        reading = pair_reading(pairwise)
        out["pairwise"] = reading
        if reading["informative"]:
            helps.append(reading["memory_helps_where_relevant"])
    return {"per_judge": out, "memory_helps_where_relevant": (all(helps) if helps else None),
            "judges_disagree_on_help": bool(helps) and any(helps) and not all(helps), "always_on_harms": (any(harms) if harms else None)}


# ------------------------------------------------------------------------------------------------------------------------- output


# ----------------------------------------------------------------------------------------------------------------- pairwise judge
PAIRS = (("A1", "A0"), ("A2", "A0"), ("A3", "A0"), ("A2", "A1"), ("A3", "A2"), ("A0i", "A0"), ("A2", "A0i"), ("A3", "A0i"))
PAIR_SYSTEM = "You are a careful, sceptical editor comparing two short notes. Reply with one line and nothing else."
PAIR_OPTS = {"temperature": 0.0, "top_p": 1.0, "num_predict": 20}
PAIR_WIN_RATE = 0.60
PAIR_CONTROL_NEEDED = 0.75
WINNER = re.compile(r"(?i)\bwinner\b\W{0,4}[:=]\s*(1|2|tie)\b")


def pair_prompt(hook: str, base: str, note1: str, note2: str) -> str:
    return ("Item the author is writing about (a development of an earlier story): %s\n\nThe author's earlier note on that story:\n%s\n\n"
            "NOTE 1:\n%s\n\nNOTE 2:\n%s\n\nWhich note builds better on the earlier note: accurate about what that note said, specific about what changed, "
            "no contradiction, not a mere repetition of it?\nReply with one line in the form WINNER: 1, WINNER: 2 or WINNER: TIE." % (hook, base, note1, note2))


def parse_winner(raw: str) -> Optional[int]:
    m = WINNER.search(raw)
    return None if not m else (0 if m.group(1).lower() == "tie" else int(m.group(1)))


def pair_tasks(rows: Sequence[dict], controls_each: int = CONTROLS_EACH) -> List[dict]:
    """Every follow-up note of every arm pair on the same item, in both orders, plus planted controls (a real A0 note against a copy of the earlier note)."""
    cell = {(r["arm"], r["seed"], r["day"]): r for r in rows if r["kind"] == "followup" and r["day"] >= ANALYSIS_FROM}
    tasks = []
    for (arm, seed, day), r in sorted(cell.items()):
        for x, y in PAIRS:
            if arm == x and (y, seed, day) in cell:
                for order in (0, 1):
                    tasks.append({"x": x, "y": y, "seed": seed, "day": day, "order": order, "control": None})
    for c in build_controls(rows, controls_each):
        if c["control"] == "copy":
            for order in (0, 1):
                tasks.append({"x": "A0", "y": "copy", "seed": c["seed"], "day": c["day"], "order": order, "control": "copy"})
    return tasks


def pair_key(t: dict) -> tuple:
    return (t["x"], t["y"], t["seed"], t["day"], t["order"])


def x_score_of(winner: Optional[int], order: int) -> Optional[float]:
    """1 if x won, 0.5 for a tie, 0 if y won; x is Note 1 when order is 0."""
    if winner is None:
        return None
    return 0.5 if winner == 0 else (1.0 if (winner == 1) == (order == 0) else 0.0)


def pair_run(rows: Sequence[dict], out: Path, generate: backends.Generate, workers: int = 8, log=print, controls_each: int = CONTROLS_EACH) -> int:
    by_key = {(r["arm"], r["seed"], r["day"]): r for r in rows}
    done = set()
    if out.exists():
        done = {pair_key(json.loads(line)) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()}
    todo = [t for t in pair_tasks(rows, controls_each) if pair_key(t) not in done]
    lock, written = threading.Lock(), 0

    def one(t: dict) -> dict:
        row = by_key[("A0" if t["y"] == "copy" else t["x"], t["seed"], t["day"])]
        base = by_key[(row["arm"], t["seed"], row["base_day"])]["text"]
        note_x = by_key[(t["x"], t["seed"], t["day"])]["text"]
        note_y = base if t["y"] == "copy" else by_key[(t["y"], t["seed"], t["day"])]["text"]
        first, second = (note_x, note_y) if t["order"] == 0 else (note_y, note_x)
        raw = str(generate(PAIR_SYSTEM, pair_prompt(row["hook"], base, first, second), JUDGE_SEED, PAIR_OPTS)["text"])
        winner = parse_winner(raw)
        return dict(t, winner=winner, x_score=x_score_of(winner, t["order"]), raw=raw.strip()[:40])

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool, out.open("a", encoding="utf-8") as handle:
        for future in as_completed([pool.submit(one, t) for t in todo]):
            row = future.result()
            with lock:
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                written += 1
                if written % 100 == 0:
                    log("compared %d/%d" % (written, len(todo)))
    return written


def pair_analysis(results: Sequence[dict], draws: int = ana.DRAWS) -> dict:
    for r in results:
        if r.get("x_score") is None and r.get("raw"):
            r["winner"] = parse_winner(r["raw"])
            r["x_score"] = x_score_of(r["winner"], r["order"])
    real = [r for r in results if not r.get("control") and r.get("x_score") is not None]
    controls = [r for r in results if r.get("control") and r.get("x_score") is not None]
    cache: Dict[int, list] = {}
    pairs = {}
    for x, y in PAIRS:
        by_task: Dict[tuple, List[float]] = {}
        for r in real:
            if r["x"] == x and r["y"] == y:
                by_task.setdefault((r["seed"], r["day"]), []).append(r["x_score"])
        scores = [sum(v) / len(v) for v in by_task.values()]
        if scores:
            low, high = ana.interval(scores, cache, draws)
            pairs["%s-%s" % (x, y)] = {"win_rate": sum(scores) / len(scores), "ci_low": low, "ci_high": high, "n": len(scores)}
    control_rate = (sum(1 for r in controls if r["x_score"] > 0.5) / len(controls)) if controls else None
    choices = [r["winner"] for r in real if r.get("winner") in (1, 2)]
    return {"pairs": pairs, "control_win_rate": control_rate, "control_pairs": len(controls),
            "judge_informative": control_rate is not None and control_rate >= PAIR_CONTROL_NEEDED,
            "unparsed": sum(1 for r in results if r.get("x_score") is None),
            "share_choosing_note_1": (sum(1 for w in choices if w == 1) / len(choices)) if choices else None}


def pair_reading(res: dict) -> dict:
    p = res["pairs"]

    def wins(name: str) -> bool:
        e = p.get(name)
        return bool(e and e["win_rate"] >= PAIR_WIN_RATE and e["ci_low"] > 0.5)
    controls = ["A0"] + (["A0i"] if "A2-A0i" in p else [])
    gains = [arm for arm in ("A2", "A3") if all(wins("%s-%s" % (arm, c)) for c in controls)]
    return {"informative": res["judge_informative"], "memory_helps_where_relevant": bool(gains) and res["judge_informative"], "arms_that_gain": gains}


def pair_report(res: dict) -> str:
    rows = "\n".join("| %s | %.3f | [%.3f, %.3f] | %d |" % (k, v["win_rate"], v["ci_low"], v["ci_high"], v["n"]) for k, v in res["pairs"].items())
    return ("# AAM-E2-FU pairwise judge\n\nControl: the real note beat a copy of the earlier note in %s of %d comparisons (informative: %s); "
            "share of choices for Note 1: %s; unparsed replies: %d.\n\n| pair (first over second) | win rate | interval | follow-ups |\n|---|---|---|---|\n%s\n\n"
            "Reading: %s\n" % (fmt(res["control_win_rate"]), res["control_pairs"], res["judge_informative"], fmt(res["share_choosing_note_1"]),
                                res["unparsed"], rows, json.dumps(res["reading"])))
def fmt(v: Optional[float]) -> str:
    return "-" if v is None else "%.3f" % v


def measures_report(res: dict) -> str:
    out = ["# AAM-E2-FU deterministic measures", "", "Notes: %d; arms: %s; analysis from day %d." % (res["notes"], ", ".join(res["arms"]), ANALYSIS_FROM), ""]
    for kind in KINDS:
        out += ["## %s notes" % kind, "", "| arm | " + " | ".join(METRICS) + " |", "|---|" + "---|" * len(METRICS)]
        out += ["| %s | %s |" % (arm, " | ".join(fmt(res["arm_means"][kind][arm][m]) for m in METRICS)) for arm in res["arms"]]
        out += ["", "| contrast | " + " | ".join(METRICS) + " |", "|---|" + "---|" * len(METRICS)]
        for name, by in res["contrasts"][kind].items():
            out.append("| %s | %s |" % (name, " | ".join("-" if not by[m] else "%.3f [%.3f, %.3f]" % (by[m]["mean"], by[m]["ci_low"], by[m]["ci_high"]) for m in METRICS)))
        out.append("")
    return "\n".join(out) + "\n"


def judge_report(name: str, res: dict) -> str:
    out = ["## Judge: %s" % name, "", "Judged notes: %d; controls: %d; informative dimensions: %s; control checks: %s" % (
        res["judged"], res["controls"], res["informative"], {k: fmt(v) for k, v in res["controls_check"].items()}), ""]
    for kind in KINDS:
        out += ["### %s notes, arm means" % kind, "", "| arm | " + " | ".join(DIMENSIONS) + " |", "|---|" + "---|" * len(DIMENSIONS)]
        out += ["| %s | %s |" % (arm, " | ".join(fmt(res["arm_means"][kind][arm][d]) for d in DIMENSIONS)) for arm in res["arms"]]
        out += ["", "| contrast | " + " | ".join(DIMENSIONS) + " |", "|---|" + "---|" * len(DIMENSIONS)]
        for cname, by in res["contrasts"][kind].items():
            out.append("| %s | %s |" % (cname, " | ".join("-" if not by[d] else "%+.2f [%+.2f, %+.2f]" % (by[d]["mean"], by[d]["ci_low"], by[d]["ci_high"]) for d in DIMENSIONS)))
        out.append("")
    return "\n".join(out) + "\n"


def readings_report(final: dict) -> str:
    out = ["## Readings stated in advance, applied mechanically", ""]
    for name, r in final["per_judge"].items():
        out.append("- judge %s: %s" % (name, json.dumps(r)))
    out += ["- memory helps where it is relevant (all informative judges agree): %s" % final["memory_helps_where_relevant"],
            "- judges disagree on help: %s" % final["judges_disagree_on_help"], "- always-on memory harms fresh notes: %s" % final["always_on_harms"]]
    return "\n".join(out) + "\n"


def load_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: Optional[List[str]] = None, embedder=None) -> int:
    parser = argparse.ArgumentParser(description="Analysis of AAM-E2-FU.")
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("measures")
    m.add_argument("records", type=Path)
    m.add_argument("--json", type=Path)
    m.add_argument("--md", type=Path)
    r = sub.add_parser("judge-run")
    r.add_argument("records", type=Path)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--backend", choices=("ollama", "openai"), default="openai")
    r.add_argument("--base-url", default="http://127.0.0.1:8798/v1")
    r.add_argument("--model", required=True)
    r.add_argument("--workers", type=int, default=8)
    r.add_argument("--sample-fresh", type=float, default=1.0)
    pr = sub.add_parser("pair-run")
    pr.add_argument("records", type=Path)
    pr.add_argument("--out", type=Path, required=True)
    pr.add_argument("--backend", choices=("ollama", "openai"), default="openai")
    pr.add_argument("--base-url", default="http://127.0.0.1:8798/v1")
    pr.add_argument("--model", required=True)
    pr.add_argument("--workers", type=int, default=8)
    pa = sub.add_parser("pair-analyse")
    pa.add_argument("results", type=Path)
    pa.add_argument("--json", type=Path)
    pa.add_argument("--md", type=Path)
    a = sub.add_parser("judge-analyse")
    a.add_argument("records", type=Path)
    a.add_argument("judgments", nargs="+", help="NAME=PATH pairs, e.g. flash=judgments-flash.jsonl")
    a.add_argument("--pairwise", type=Path, default=None, help="results of pair-run, counted as one more judge")
    a.add_argument("--json", type=Path)
    a.add_argument("--md", type=Path)
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        rows = fu.load_records(args.records) if getattr(args, "records", None) else []
        if args.command == "measures":
            res = measures_analysis(rows, embedder or fu.Embedder())
            res["provenance"] = {"records_sha256": hashlib.sha256(args.records.read_bytes()).hexdigest(), "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
            text = measures_report(res)
        elif args.command == "pair-run":
            generate = backends.ollama_generate(args.model) if args.backend == "ollama" else backends.openai_generate(args.base_url, args.model)
            print("done: %d new comparisons" % pair_run(rows, args.out, generate, args.workers, log=lambda line: print(line, flush=True)))
            return 0
        elif args.command == "pair-analyse":
            res = pair_analysis(load_jsonl(args.results))
            res["reading"] = pair_reading(res)
            text = pair_report(res)
        elif args.command == "judge-run":
            generate = backends.ollama_generate(args.model) if args.backend == "ollama" else backends.openai_generate(args.base_url, args.model)
            print("done: %d new judgments" % judge_run(rows, args.out, generate, args.workers, args.sample_fresh, log=lambda line: print(line, flush=True)))
            return 0
        else:
            per = {}
            for spec in args.judgments:
                name, _, path = spec.partition("=")
                per[name] = judge_analysis(load_jsonl(Path(path)))
            pairwise = pair_analysis(load_jsonl(args.pairwise)) if args.pairwise else None
            final = final_readings(per, pairwise)
            res = {"judges": per, "pairwise": pairwise, "readings": final}
            text = "# AAM-E2-FU judge results\n\n" + "\n".join(judge_report(n, r_) for n, r_ in per.items()) + "\n" + readings_report(final)
    except (OSError, ValueError, ImportError, backends.SpendCapRefused) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if args.json:
        args.json.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if args.md:
        args.md.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
