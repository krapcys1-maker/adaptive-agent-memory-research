#!/usr/bin/env python3
"""Analysis of AAM-E1-SIM records, as fixed in data/lab/aam-e1-writer-memory-sim/README.md before the run.

Reads the JSONL written by writer_memory_sim.py and prints the arm means, the paired contrasts with a bootstrap interval
and the readings stated in advance, applied mechanically. Standard library only, no network, deterministic: the
bootstrap uses its own generator, so the numbers do not depend on the Python version.

Usage: python scripts/analyze_writer_memory_sim.py RECORDS.jsonl [--json OUT.json] [--md OUT.md]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shadow_baseline_measures as sbm  # noqa: E402
import writer_memory_sim as sim  # noqa: E402

ANALYSIS_FROM = 7
CONTRASTS = (("M1", "M0"), ("M2", "M0"), ("M3a", "M0"), ("M3b", "M0"), ("M3a", "M2"), ("M3b", "M2"), ("M3b", "M3a"))
MEASURES = ("overlap4", "union_novelty", "overlap8", "rep_rate", "callback_strict", "callback_ext", "hook_coverage",
            "words", "shown_copy8")
THRESHOLD = 0.05
GUARD = 0.10
DRAWS = 10000
BOOT_SEED = 20261101
MASK = (1 << 64) - 1
Measures = Dict[str, Optional[float]]


def entry_measures(items: Sequence[sbm.Item], index: int, row: dict) -> Measures:
    text = row["text"]
    grams4, grams8 = sbm.ngrams(text, 4), sbm.ngrams(text, 8)
    earlier: set = set()
    for item in items[:index]:
        earlier |= sbm.ngrams(item.text, 4)
    overlap4 = sbm.repetition_overlap(items, index, 400, 4)
    hook, post = set(sim.content_tokens(row["hook"])), set(sim.content_tokens(text))
    block = row.get("memory_block") or ""
    return {
        "overlap4": overlap4,
        "union_novelty": 1.0 - len(grams4 & earlier) / len(grams4) if grams4 else 1.0,
        "overlap8": sbm.repetition_overlap(items, index, 400, 8),
        "rep_rate": 1.0 if overlap4 >= 0.25 else 0.0,
        "callback_strict": 1.0 if sbm.is_callback(items, index, 400) else 0.0,
        "callback_ext": 1.0 if sim.callback_extended(text, row["day"]) else 0.0,
        "hook_coverage": len(hook & post) / len(hook) if hook else 1.0,
        "words": float(len(text.split())),
        "shown_copy8": len(grams8 & sbm.ngrams(block, 8)) / len(grams8) if block and grams8 else None,
    }


def measure_all(rows: Sequence[dict]) -> Dict[tuple, Dict[int, Measures]]:
    """{(arm, seed): {day: measures}} for every entry; the history of an arm is its own earlier entries."""
    grouped: Dict[tuple, List[dict]] = {}
    for row in rows:
        grouped.setdefault((row["arm"], row["seed"]), []).append(row)
    out: Dict[tuple, Dict[int, Measures]] = {}
    for key, group in grouped.items():
        group.sort(key=lambda r: r["day"])
        items = [sbm.Item("%d-%s-%02d" % (r["seed"], r["arm"], r["day"]), date(2026, 1, 1) + timedelta(days=r["day"] - 1),
                          r["text"], r["title"]) for r in group]
        out[key] = {r["day"]: entry_measures(items, i, r) for i, r in enumerate(group)}
    return out


def mean(values: Sequence[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def bootstrap_indices(n: int, draws: int = DRAWS, seed: int = BOOT_SEED) -> List[List[int]]:
    """Resample indices from a splitmix64 stream: no dependence on the interpreter's random module."""
    state, out = seed & MASK, []
    for _ in range(draws):
        picks = []
        for _ in range(n):
            state = (state + 0x9E3779B97F4A7C15) & MASK
            z = ((state ^ (state >> 30)) * 0xBF58476D1CE4E5B9) & MASK
            z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
            picks.append((z ^ (z >> 31)) % n)
        out.append(picks)
    return out


def interval(diffs: Sequence[float], cache: Dict[int, List[List[int]]], draws: int = DRAWS) -> tuple:
    n = len(diffs)
    if n not in cache:
        cache[n] = bootstrap_indices(n, draws)
    means = sorted(sum(diffs[i] for i in picks) / n for picks in cache[n])
    return means[int(0.025 * draws)], means[int(0.975 * draws) - 1]


def contrast(measured: Dict[tuple, Dict[int, Measures]], a: str, b: str, measure: str, seeds: Sequence[int],
             cache: Dict[int, List[List[int]]], draws: int = DRAWS) -> Optional[dict]:
    pairs = []
    for seed in seeds:
        ma, mb = measured.get((a, seed)), measured.get((b, seed))
        if not ma or not mb:
            continue
        for day in sorted(set(ma) & set(mb)):
            if day >= ANALYSIS_FROM and ma[day][measure] is not None and mb[day][measure] is not None:
                pairs.append((seed, ma[day][measure] - mb[day][measure]))
    if not pairs:
        return None
    diffs = [d for _, d in pairs]
    centre = sum(diffs) / len(diffs)
    spread = (sum((d - centre) ** 2 for d in diffs) / (len(diffs) - 1)) ** 0.5 if len(diffs) > 1 else 0.0
    low, high = interval(diffs, cache, draws)
    return {"mean": centre, "ci_low": low, "ci_high": high, "sd_paired": spread, "n": len(diffs),
            "per_seed": {str(s): mean([d for seed, d in pairs if seed == s]) for s in seeds if any(seed == s for seed, _ in pairs)}}


def arm_means(measured: Dict[tuple, Dict[int, Measures]], arm: str, seeds: Sequence[int]) -> Dict[str, Optional[float]]:
    rows = [m for seed in seeds for day, m in measured.get((arm, seed), {}).items() if day >= ANALYSIS_FROM]
    out: Dict[str, Optional[float]] = {name: mean([r[name] for r in rows]) for name in MEASURES}
    out["n"] = float(len(rows))
    return out


def readings(contrasts: Dict[str, Dict[str, Optional[dict]]], means: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, Optional[bool]]:
    """The table of readings in the README, applied mechanically; None when an arm or contrast is missing."""
    def primary(a: str, b: str) -> Optional[dict]:
        return contrasts.get("%s-%s" % (a, b), {}).get("overlap4")

    def guard_holds(arm: str) -> Optional[bool]:
        if arm not in means or "M0" not in means or means[arm]["hook_coverage"] is None or means["M0"]["hook_coverage"] is None:
            return None
        return means[arm]["hook_coverage"] - means["M0"]["hook_coverage"] > -GUARD

    def lowers(a: str, b: str) -> Optional[bool]:
        c, g = primary(a, b), guard_holds(a)
        return None if c is None or g is None else (c["mean"] <= -THRESHOLD and c["ci_high"] < 0 and g)

    raised = primary("M2", "M0")
    sizes = [c["mean"] for c in (primary(a, b) for a, b in CONTRASTS) if c]
    return {
        "raw_history_helps": lowers("M2", "M0"),
        "raw_history_hurts": None if raised is None else (raised["mean"] >= THRESHOLD and raised["ci_low"] > 0),
        "traces_beat_entries": lowers("M3a", "M2"),
        "dynamics_add": lowers("M3b", "M3a"),
        "nothing_moves": None if not sizes else all(abs(s) < THRESHOLD for s in sizes),
    }


def analyse(rows: Sequence[dict], draws: int = DRAWS) -> dict:
    seeds = sorted({r["seed"] for r in rows})
    arms = [a for a in sim.ARMS if any(r["arm"] == a for r in rows)]
    measured = measure_all(rows)
    means = {arm: arm_means(measured, arm, seeds) for arm in arms}
    cache: Dict[int, List[List[int]]] = {}
    contrasts = {"%s-%s" % (a, b): {m: contrast(measured, a, b, m, seeds, cache, draws) for m in MEASURES}
                 for a, b in CONTRASTS if a in arms and b in arms}
    return {"seeds": seeds, "arms": arms, "analysis_from_day": ANALYSIS_FROM, "entries": len(rows), "arm_means": means,
            "contrasts": contrasts, "readings": readings(contrasts, means),
            "tokens": {arm: mean([r.get("prompt_tokens") for r in rows if r["arm"] == arm]) for arm in arms}}


def fmt(value: Optional[float], digits: int = 3) -> str:
    return "-" if value is None else ("%." + str(digits) + "f") % value


def report(result: dict, rows: Sequence[dict]) -> str:
    out = ["# AAM-E1-SIM results", "",
           "Entries: %d; stream seeds: %s; analysis days %d to the end; arms: %s." % (
               result["entries"], result["seeds"], result["analysis_from_day"], ", ".join(result["arms"])), "",
           "## Arm means (analysis days)", "", "| arm | n | " + " | ".join(MEASURES) + " | prompt tokens |",
           "|---|---|" + "---|" * (len(MEASURES) + 1)]
    for arm in result["arms"]:
        m = result["arm_means"][arm]
        out.append("| %s | %d | %s | %s |" % (arm, m["n"], " | ".join(fmt(m[name], 2 if name == "words" else 3) for name in MEASURES),
                                             fmt(result["tokens"][arm], 0)))
    out += ["", "## Paired contrasts (first minus second), mean [95% bootstrap interval], per-stream means", ""]
    for measure in ("overlap4", "hook_coverage", "callback_ext", "union_novelty", "words"):
        out += ["### %s" % measure, "", "| contrast | mean | interval | sd of pairs | per stream |", "|---|---|---|---|---|"]
        for name, by_measure in result["contrasts"].items():
            c = by_measure[measure]
            if c:
                out.append("| %s | %s | [%s, %s] | %s | %s |" % (name, fmt(c["mean"]), fmt(c["ci_low"]), fmt(c["ci_high"]), fmt(c["sd_paired"]),
                                                                  ", ".join("%s: %s" % (s, fmt(v)) for s, v in c["per_seed"].items())))
        out.append("")
    out += ["## Readings stated in advance, applied mechanically", ""]
    out += ["- %s: %s" % (name.replace("_", " "), {True: "**yes**", False: "no", None: "not computable"}[value])
            for name, value in result["readings"].items()]
    seed, day = min(result["seeds"]), 30
    sample = sorted((r for r in rows if r["seed"] == seed and r["day"] == day), key=lambda r: sim.ARMS.index(r["arm"]))
    if sample:
        out += ["", "## The same day in every arm (stream seed %d, day %d: %s)" % (seed, day, sample[0]["hook"]), ""]
        for r in sample:
            out += ["**%s** - notes drawn from days %s. *%s* %s" % (r["arm"], r["shown_ids"] or "none", r["title"],
                                                                    r["text"][:420] + ("..." if len(r["text"]) > 420 else "")), ""]
    return "\n".join(out) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Analyse AAM-E1-SIM records as fixed in the README.")
    parser.add_argument("records", type=Path)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--md", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        rows = sim.load_records(args.records)
    except (OSError, ValueError) as exc:
        print("input error: %s" % exc, file=sys.stderr)
        return 2
    if not rows:
        print("input error: no records", file=sys.stderr)
        return 2
    result = analyse(rows)
    result["provenance"] = {"records_sha256": hashlib.sha256(args.records.read_bytes()).hexdigest(),
                            "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            "bootstrap": {"draws": DRAWS, "seed": BOOT_SEED, "generator": "splitmix64"}}
    text = report(result, rows)
    if args.json:
        args.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if args.md:
        args.md.write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
