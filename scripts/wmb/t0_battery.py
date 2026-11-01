#!/usr/bin/env python3
"""WMB T0 core: does the pairwise judge of the E5 harness see what it must see? Planted pairs built from the account's own replay data.

Families (each a note we expect to win against a comparator, judged in both orders by the E5 judge prompt, temperature 0):
  aa        a note against an identical copy of itself: the verdict should be a tie
  copy      the model's note against a verbatim copy of the author's earlier note: the model's note should win
  callback  a note with a grounded callback against the same note with the callback sentences removed: the callback note should win
  spurious  a clean note against the same note with a fabricated callback prepended, on a task with no relevant earlier note: the clean note should win
  null      a real note against a one-line non-answer: the real note should win
Also reported, from judgments that already exist: the share of real arm pairs on which both orders agree, and the test-retest agreement of the verdicts.
The rules are fixed here, before the first scored run; they are ours (the literature gives ranges, not cutoffs). A family that fails keeps the judge descriptive only.

Usage: python scripts/wmb/t0_battery.py run --items notes.jsonl --replay DIR --workdir DIR [--n 40] [--retest] [--base-url URL]
       python scripts/wmb/t0_battery.py analyse --replay DIR --workdir DIR [--json OUT.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze_followup_memory_sim as afu  # noqa: E402
import llm_backends as backends  # noqa: E402
import replay_memory_sim as rp  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402
import writer_memory_sim as sim  # noqa: E402
from wmb import contract, stats  # noqa: E402

FAMILIES = ("aa", "copy", "callback", "spurious", "null")
FAMILY_SIZE = 40
SEED = 20261101
TIE_RATE_MIN = 0.90            # aa: share of verdicts that are ties
WIN_SHARE_MIN = 37 / 40        # copy, callback, spurious, null: tasks on which the expected note wins (mean score over the two orders above one half)
ORDER_CONSISTENCY_MIN = 0.70   # real arm pairs on which both orders agree
FORMAT_FAILURE_MAX = 0.02
NULL_NOTE = "Nothing to add here."
SENTENCE = re.compile(r"(?<=[.!?])\s+")
Generate = Callable[[str, str, int, dict], dict]


def strip_callbacks(text: str) -> str:
    return " ".join(s for s in SENTENCE.split(text.strip()) if not any(p.search(s) for p in sim.CALLBACK_PATTERNS))


def fabricate_callback(text: str, topic: str) -> str:
    words = topic.split()[:12]
    return "As I wrote last week about %s, %s" % (" ".join(words).rstrip(".,;:"), text[:1].lower() + text[1:])


def shuffled(ids: Sequence[int]) -> List[int]:
    return [ids[k] for k in sim.Lcg(SEED).shuffled(range(len(ids)))]


def build_tasks(items: Sequence[sbm.Item], prep: dict, records: Sequence[dict], n: int = FAMILY_SIZE) -> List[dict]:
    cell = {(r["i"], r["arm"]): r for r in records}
    candidates = sorted({r["i"] for r in records if r["candidate"]})
    others = sorted({r["i"] for r in records if not r["candidate"]})
    reference = lambda i: items[cell[(i, "R0")]["ref"]].text if cell[(i, "R0")]["candidate"] else None   # noqa: E731
    tasks: List[dict] = []
    for i in shuffled(candidates)[:n]:
        tasks.append({"family": "aa", "i": i, "x": cell[(i, "R0")]["text"], "y": cell[(i, "R0")]["text"], "reference": reference(i)})
        tasks.append({"family": "copy", "i": i, "x": cell[(i, "R0")]["text"], "y": reference(i), "reference": reference(i)})
    callbacks = []
    for i in candidates:
        for arm in ("R3", "R2"):
            r = cell.get((i, arm))
            if r and sim.callback_extended(r["text"]) and len(strip_callbacks(r["text"]).split()) >= 10:
                callbacks.append({"family": "callback", "i": i, "x": r["text"], "y": strip_callbacks(r["text"]), "reference": reference(i)})
                break
    tasks += callbacks[:n]
    clean = [i for i in others if not sim.callback_extended(cell[(i, "R0")]["text"])]
    for i in shuffled(clean)[:n]:
        topic = prep["briefs"][(i + 37) % len(prep["briefs"])]
        tasks.append({"family": "spurious", "i": i, "x": cell[(i, "R0")]["text"], "y": fabricate_callback(cell[(i, "R0")]["text"], topic), "reference": None})
    for i in shuffled(sorted({r["i"] for r in records}))[:n]:
        tasks.append({"family": "null", "i": i, "x": cell[(i, "R0")]["text"], "y": NULL_NOTE, "reference": reference(i)})
    for t in tasks:
        t["brief"] = prep["briefs"][t["i"]]
    return tasks


def run_judgments(tasks: Sequence[dict], generate: Generate, out: Path, seed_offset: int = 0, workers: int = 8) -> int:
    done = {(r["family"], r["i"], r["order"], r["seed_offset"]) for r in contract.load_jsonl(out)}
    todo = [(t, o) for t in tasks for o in (0, 1) if (t["family"], t["i"], o, seed_offset) not in done]
    lock = threading.Lock()

    def one(args) -> None:
        t, o = args
        first, second = (t["x"], t["y"]) if o == 0 else (t["y"], t["x"])
        raw = str(generate(afu.PAIR_SYSTEM, rp.pair_prompt(t["brief"], t["reference"], first, second), afu.JUDGE_SEED + seed_offset, afu.PAIR_OPTS)["text"])
        winner = afu.parse_winner(raw)
        with lock:
            contract.append_jsonl(out, [{"family": t["family"], "i": t["i"], "order": o, "seed_offset": seed_offset, "raw": raw.strip()[:40], "winner": winner,
                                         "x_score": afu.x_score_of(winner, o)}])

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, todo))
    return len(todo)


def aggregate(records: Sequence[dict]) -> dict:
    """Everything the readings need, recomputable from the judgment records alone."""
    first = [r for r in records if r["seed_offset"] == 0]
    out: Dict[str, dict] = {}
    for family in FAMILIES:
        rows = [r for r in first if r["family"] == family]
        if not rows:
            continue
        valid = [r for r in rows if r["x_score"] is not None]
        per_task: Dict[int, List[float]] = {}
        for r in valid:
            per_task.setdefault(r["i"], []).append(r["x_score"])
        complete = {i: s for i, s in per_task.items() if len(s) == 2}
        wins = sum(1 for s in complete.values() if sum(s) / 2 > 0.5)
        ties = sum(1 for r in valid if r["winner"] == 0)
        non_tie = [r for r in valid if r["winner"] != 0]
        cell = {"verdicts": len(rows), "format_failures": len(rows) - len(valid), "tasks": len(complete), "wins": wins,
                "tie_rate": round(ties / len(valid), 4) if valid else None,
                "first_position_share_among_non_ties": round(sum(1 for r in non_tie if r["winner"] == 1) / len(non_tie), 4) if non_tie else None}
        if complete:
            cell["win_share"], cell["wilson95"] = round(wins / len(complete), 4), [round(x, 3) for x in stats.wilson(wins, len(complete))]
        out[family] = cell
    retest = [r for r in records if r["seed_offset"] != 0]
    if retest:
        base = {(r["family"], r["i"], r["order"]): r["winner"] for r in first}
        pairs = [(base[(r["family"], r["i"], r["order"])], r["winner"]) for r in retest if (r["family"], r["i"], r["order"]) in base]
        out["retest_agreement"] = {"verdicts": len(pairs), "same_verdict": round(sum(1 for a, b in pairs if a == b) / len(pairs), 4) if pairs else None}
    return out


def order_consistency(pairs: Sequence[dict]) -> dict:
    """Share of real arm pairs (E5 judgments) on which the two orders give the same verdict about x."""
    cells: Dict[tuple, List[float]] = {}
    for r in pairs:
        if r.get("x_score") is not None and r.get("stratum") != "control":
            cells.setdefault((r["i"], r["x"], r["y"]), []).append(r["x_score"])
    both = [s for s in cells.values() if len(s) == 2]
    agree = sum(1 for s in both if s[0] == s[1])
    return {"pairs": len(both), "consistent": agree, "share": round(agree / len(both), 4) if both else None}


def readings(agg: dict, consistency: dict) -> dict:
    """The rules fixed above, applied mechanically."""
    out: Dict[str, object] = {}
    aa = agg.get("aa")
    out["aa_ties"] = bool(aa and aa["tie_rate"] is not None and aa["tie_rate"] >= TIE_RATE_MIN)
    for family in ("copy", "callback", "spurious", "null"):
        cell = agg.get(family)
        out[family + "_seen"] = bool(cell and cell.get("win_share") is not None and cell["win_share"] >= WIN_SHARE_MIN)
    out["order_consistent"] = bool(consistency.get("share") is not None and consistency["share"] >= ORDER_CONSISTENCY_MIN)
    total = sum(c["verdicts"] for k, c in agg.items() if k in FAMILIES)
    failures = sum(c["format_failures"] for k, c in agg.items() if k in FAMILIES)
    out["format_ok"] = bool(total and failures / total <= FORMAT_FAILURE_MAX)
    out["judge_usable_as_secondary"] = all(out[k] for k in ("aa_ties", "copy_seen", "callback_seen", "spurious_seen", "null_seen", "order_consistent", "format_ok"))
    return out


def load_replay(replay: Path):
    return json.loads((replay / "prep.json").read_text(encoding="utf-8")), contract.load_jsonl(replay / "records.jsonl"), contract.load_jsonl(replay / "pairs.jsonl")


def main(argv: Optional[List[str]] = None, generate: Optional[Generate] = None) -> int:
    parser = argparse.ArgumentParser(description="WMB T0: a battery of planted pairs for the pairwise judge.")
    parser.add_argument("command", choices=("run", "analyse"))
    parser.add_argument("--items", type=Path)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--n", type=int, default=FAMILY_SIZE)
    parser.add_argument("--retest", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8798/v1")
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    args.workdir.mkdir(parents=True, exist_ok=True)
    sys.stdout.reconfigure(encoding="utf-8")
    records_path = args.workdir / "judgments.jsonl"
    try:
        prep, records, pairs = load_replay(args.replay)
        if args.command == "run":
            if not args.items:
                parser.error("run needs --items")
            with open(args.items, encoding="utf-8") as handle:
                items = sbm.parse_items(handle)
            tasks = build_tasks(items, prep, records, args.n)
            gen = generate or backends.openai_generate(args.base_url, args.model)
            written = run_judgments(tasks, gen, records_path, 0, args.workers)
            if args.retest:
                written += run_judgments([t for t in tasks if t["family"] == "copy"], gen, records_path, 1, args.workers)
            print("tasks per family:", {f: sum(1 for t in tasks if t["family"] == f) for f in FAMILIES}, "| new judgments:", written)
        else:
            judgments = contract.load_jsonl(records_path)
            agg, cons = aggregate(judgments), order_consistency(pairs)
            result = {"families": agg, "order_consistency": cons, "readings": readings(agg, cons),
                      "minimum_detectable_win_rate": {str(n): stats.mde_win_rate(n) for n in (43, 100, 160, 214, 300)}}
            text = json.dumps(result, indent=1, sort_keys=True)
            if args.json:
                args.json.write_text(text + "\n", encoding="utf-8")
                contract.write_summary(args.json.with_name("summary.json"), records_path, agg,
                                       {"script": Path(__file__).name, "rules": {"tie_rate_min": TIE_RATE_MIN, "win_share_min": WIN_SHARE_MIN, "order_consistency_min": ORDER_CONSISTENCY_MIN}})
            print(text)
    except (OSError, ValueError, backends.SpendCapRefused) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
