#!/usr/bin/env python3
"""A blind LLM judge for AAM-E1-SIM, with planted controls so that we know whether the judge can tell anything.

The lexical measures of the main analysis see copying and drift but not quality. This adds a rubric score from a model that is
not told which arm wrote an entry. Each entry is scored 1 to 5 on four points (fit to the trigger, freshness against the same
author's earlier entries on the theme, voice, overall quality). Planted controls (an entry replaced by a copy of the author's
previous entry, an entry replaced by one on another theme) show whether the judge notices what it should; if it does not, the
dimension is declared uninformative. Design and acceptance rules: data/lab/aam-e1-writer-memory-sim/README.md, addendum A.

Usage:
  python scripts/judge_writer_memory_sim.py run RECORDS.jsonl --out JUDGMENTS.jsonl [--model qwen2.5:14b-instruct] [--workers 2]
  python scripts/judge_writer_memory_sim.py analyse RECORDS.jsonl JUDGMENTS.jsonl [--json OUT.json] [--md OUT.md]
Standard library only; the run talks to a local Ollama server (or any generate callable when used as a library).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_writer_memory_sim as ana  # noqa: E402
import llm_backends as backends  # noqa: E402
import writer_memory_sim as sim  # noqa: E402

DIMENSIONS = ("fit", "fresh", "voice", "quality")
JUDGE_SYSTEM = "You are a careful, sceptical editor who scores short column entries against a rubric. Reply with exactly four lines and nothing else."
JUDGE_OPTS = {"temperature": 0.0, "top_p": 1.0, "num_predict": 40}
JUDGE_SEED = 11
ANALYSIS_FROM = ana.ANALYSIS_FROM
CONTROLS_EACH = 12
CONTROL_SEED = 2026
ACCEPT_SHARE = 0.75          # a control is "noticed" when fresh <= 2 (copy) or fit <= 2 (off topic); the judge is informative if >= this share are
QUALITY_GUARD = 0.30         # mean drop against M0 on a 1-5 scale that voids a repetition win (with an interval below zero)
SCORE = re.compile(r"(?im)^\W*(fit|fresh|voice|quality)\W*[:=]\s*([1-5])\b")


def parse_scores(raw: str) -> Dict[str, Optional[int]]:
    found = {name.lower(): int(value) for name, value in SCORE.findall(raw)}
    return {dimension: found.get(dimension) for dimension in DIMENSIONS}


def earlier_entries(rows: Sequence[dict], row: dict, k: int = 2) -> List[dict]:
    """The same author's (same arm and stream) latest k entries on the same theme before this day, oldest first."""
    same = [r for r in rows if r["seed"] == row["seed"] and r["arm"] == row["arm"] and r["theme"] == row["theme"] and r["day"] < row["day"]]
    return sorted(same, key=lambda r: r["day"])[-k:]


def judge_prompt(row: dict, earlier: Sequence[dict]) -> str:
    shown = "\n\n".join("[Earlier entry, day %d]\nTITLE: %s\n%s" % (e["day"], e["title"], e["text"]) for e in earlier) or "(none)"
    return ("Author persona card:\n%s\n\nToday's trigger (theme: %s): %s\n\nEarlier entries by the same author on this theme (oldest first):\n%s\n\n"
            "Entry to score:\nTITLE: %s\n%s\n\n"
            "Score the entry from 1 (poor) to 5 (excellent) on four points:\n"
            "FIT: how well it responds to today's trigger (1 = ignores it, 5 = built around it)\n"
            "FRESH: how new its points, examples and wording are compared with the earlier entries above (1 = repeats them, 5 = clearly new)\n"
            "VOICE: how well it sounds like the persona card: dry, concrete, a little self-mocking, specific examples (1 = generic, 5 = unmistakably this author)\n"
            "QUALITY: overall, how good it is as a short column entry (1 = poor, 5 = excellent)\n\n"
            "Reply with exactly four lines, in the form FIT: <1-5>, FRESH: <1-5>, VOICE: <1-5>, QUALITY: <1-5>."
            % (sim.PERSONA, row["theme"], row["hook"], shown, row["title"], row["text"]))


def build_controls(rows: Sequence[dict], each: int = CONTROLS_EACH, seed: int = CONTROL_SEED) -> List[dict]:
    """Planted controls from arm M0 on analysis days. 'copy': the entry is replaced by the author's previous entry on the theme.
    'offtopic': the entry is replaced by the author's latest earlier entry on a different theme (the trigger is unchanged)."""
    m0 = sorted((r for r in rows if r["arm"] == "M0"), key=lambda r: (r["seed"], r["day"]))
    candidates = [r for r in m0 if r["day"] >= ANALYSIS_FROM and earlier_entries(m0, r, 1)
                  and any(o["seed"] == r["seed"] and o["theme"] != r["theme"] and o["day"] < r["day"] for o in m0)]
    order = sim.Lcg(seed).shuffled(candidates)
    controls: List[dict] = []
    for index, r in enumerate(order[:2 * each]):
        if index % 2 == 0:
            source = earlier_entries(m0, r, 1)[0]
            kind = "copy"
        else:
            source = max((o for o in m0 if o["seed"] == r["seed"] and o["theme"] != r["theme"] and o["day"] < r["day"]), key=lambda o: o["day"])
            kind = "offtopic"
        controls.append(dict(r, title=source["title"], text=source["text"], control=kind, source_day=source["day"]))
    return controls


def task_key(row: dict) -> Tuple:
    return (row.get("control") or "real", row["seed"], row["arm"], row["day"])


def run(records: Sequence[dict], out: Path, generate: backends.Generate, workers: int = 2, log=print,
        controls_each: int = CONTROLS_EACH) -> int:
    real = [r for r in records if r["day"] >= ANALYSIS_FROM]
    tasks = sorted(real + build_controls(records, controls_each), key=lambda r: (task_key(r)[0] != "real", r["seed"], r["day"], r["arm"]))
    done = set()
    if out.exists():
        done = {task_key(json.loads(line)) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()}
    todo = [t for t in tasks if task_key(t) not in done]
    lock, written = threading.Lock(), 0

    def one(task: dict) -> dict:
        history = [r for r in records if r["arm"] == task["arm"] and r["seed"] == task["seed"]]
        raw = str(generate(JUDGE_SYSTEM, judge_prompt(task, earlier_entries(history, task)), JUDGE_SEED, JUDGE_OPTS)["text"])
        return dict({"control": task.get("control"), "seed": task["seed"], "arm": task["arm"], "day": task["day"],
                     "source_day": task.get("source_day"), "raw": raw}, **parse_scores(raw))

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool, out.open("a", encoding="utf-8") as handle:
        for future in as_completed([pool.submit(one, t) for t in todo]):
            row = future.result()
            with lock:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                written += 1
                if written % 25 == 0:
                    log("judged %d/%d" % (written, len(todo)))
    return written


def mean(values: Sequence[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def analyse(judgments: Sequence[dict], draws: int = ana.DRAWS) -> dict:
    real = [j for j in judgments if not j.get("control")]
    controls = [j for j in judgments if j.get("control")]
    arms = [a for a in sim.ARMS if any(j["arm"] == a for j in real)]
    seeds = sorted({j["seed"] for j in real})
    table = {arm: {d: mean([j[d] for j in real if j["arm"] == arm]) for d in DIMENSIONS} for arm in arms}
    cell = {(j["arm"], j["seed"], j["day"]): j for j in real}
    cache: Dict[int, List[List[int]]] = {}
    contrasts: Dict[str, Dict[str, Optional[dict]]] = {}
    for a, b in ana.CONTRASTS:
        if a not in arms or b not in arms:
            continue
        out: Dict[str, Optional[dict]] = {}
        for d in DIMENSIONS:
            diffs = [cell[(a, s, day)][d] - cell[(b, s, day)][d] for (arm, s, day) in sorted(cell) if arm == a and (b, s, day) in cell
                     and cell[(a, s, day)][d] is not None and cell[(b, s, day)][d] is not None]
            if diffs:
                low, high = ana.interval(diffs, cache, draws)
                out[d] = {"mean": sum(diffs) / len(diffs), "ci_low": low, "ci_high": high, "n": len(diffs)}
            else:
                out[d] = None
        contrasts["%s-%s" % (a, b)] = out

    def noticed(kind: str, dimension: str) -> Optional[float]:
        scored = [j[dimension] for j in controls if j["control"] == kind and j[dimension] is not None]
        return sum(1 for v in scored if v <= 2) / len(scored) if scored else None

    copy_rate, off_rate = noticed("copy", "fresh"), noticed("offtopic", "fit")
    unparsed = sum(1 for j in judgments if any(j[d] is None for d in DIMENSIONS))
    guard = {}
    for a in arms:
        c = contrasts.get("%s-M0" % a, {}).get("quality") if a != "M0" else None
        guard[a] = None if c is None else not (c["mean"] <= -QUALITY_GUARD and c["ci_high"] < 0)
    return {"arms": arms, "seeds": seeds, "judged": len(real), "controls": len(controls), "unparsed": unparsed, "arm_means": table,
            "contrasts": contrasts,
            "controls_check": {"copy_noticed_on_fresh": copy_rate, "offtopic_noticed_on_fit": off_rate,
                               "fresh_informative": None if copy_rate is None else copy_rate >= ACCEPT_SHARE,
                               "fit_informative": None if off_rate is None else off_rate >= ACCEPT_SHARE,
                               "real_mean_fresh": mean([j["fresh"] for j in real]), "real_mean_fit": mean([j["fit"] for j in real])},
            "quality_guard_holds": guard}


def fmt(value: Optional[float]) -> str:
    return "-" if value is None else "%.2f" % value


def report(result: dict) -> str:
    out = ["# AAM-E1-SIM judge results", "", "Judged entries: %d (controls: %d, unparsed replies: %d); arms: %s." % (
        result["judged"], result["controls"], result["unparsed"], ", ".join(result["arms"])), "",
        "## Controls (can the judge tell?)", ""]
    c = result["controls_check"]
    out += ["- copies of the author's previous entry scored fresh <= 2: %s of the copies; fresh informative: %s" % (fmt(c["copy_noticed_on_fresh"]), c["fresh_informative"]),
            "- entries replaced by one on another theme scored fit <= 2: %s; fit informative: %s" % (fmt(c["offtopic_noticed_on_fit"]), c["fit_informative"]),
            "- mean fresh of real entries %s, mean fit of real entries %s" % (fmt(c["real_mean_fresh"]), fmt(c["real_mean_fit"])), "",
            "## Arm means (1 to 5)", "", "| arm | " + " | ".join(DIMENSIONS) + " |", "|---|" + "---|" * len(DIMENSIONS)]
    out += ["| %s | %s |" % (arm, " | ".join(fmt(result["arm_means"][arm][d]) for d in DIMENSIONS)) for arm in result["arms"]]
    out += ["", "## Paired contrasts, mean [95% bootstrap interval]", ""]
    for d in DIMENSIONS:
        out += ["### %s" % d, "", "| contrast | mean | interval | n |", "|---|---|---|---|"]
        out += ["| %s | %s | [%s, %s] | %d |" % (name, fmt(v[d]["mean"]), fmt(v[d]["ci_low"]), fmt(v[d]["ci_high"]), v[d]["n"])
                for name, v in result["contrasts"].items() if v.get(d)]
        out.append("")
    out += ["## Quality guard (a drop of %.2f or more against M0 with an interval below zero voids a repetition win)" % QUALITY_GUARD, ""]
    out += ["- %s: %s" % (arm, {True: "holds", False: "**violated**", None: "n/a"}[v]) for arm, v in result["quality_guard_holds"].items()]
    return "\n".join(out) + "\n"


def load_jsonl(path: Path) -> List[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Blind LLM judge for AAM-E1-SIM.")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("records", type=Path)
    run_p.add_argument("--out", type=Path, required=True)
    run_p.add_argument("--model", default="qwen2.5:14b-instruct")
    run_p.add_argument("--backend", choices=("ollama", "openai"), default="ollama",
                       help="ollama: a local server; openai: any OpenAI-compatible endpoint, e.g. the local metering proxy of a paid API")
    run_p.add_argument("--base-url", default="http://127.0.0.1:8799/v1")
    run_p.add_argument("--workers", type=int, default=2)
    an_p = sub.add_parser("analyse")
    an_p.add_argument("records", type=Path)
    an_p.add_argument("judgments", type=Path)
    an_p.add_argument("--json", type=Path, default=None)
    an_p.add_argument("--md", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            generate = (backends.ollama_generate(args.model) if args.backend == "ollama"
                        else backends.openai_generate(args.base_url, args.model))
            written = run(sim.load_records(args.records), args.out, generate, args.workers, log=lambda line: print(line, flush=True))
            print("done: %d new judgments" % written)
            return 0
        result = analyse(load_jsonl(args.judgments))
        result["provenance"] = {"judgments_sha256": hashlib.sha256(args.judgments.read_bytes()).hexdigest(),
                                "judge_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    except (OSError, ValueError) as exc:
        print("input error: %s" % exc, file=sys.stderr)
        return 2
    if args.json:
        args.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    text = report(result)
    if args.md:
        args.md.write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
