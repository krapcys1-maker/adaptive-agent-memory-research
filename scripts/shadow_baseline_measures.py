#!/usr/bin/env python3
"""Baseline measures for the live-memory evaluation, computed from an agent's own past texts.

Part B of docs/11-research-laboratory/live-memory-shadow-audit-spec-draft-v0.md: for a list of the
agent's own published items (id, date, text, optional title) compute a repetition rate and a callback
rate, the day-to-day variance and intraclass correlation of those rates, and the minimum detectable
difference of a randomised comparison at several exposures. The rules below are provisional: they are
fixed in a preregistration before any real history is read.

Properties: standard library only, no network, reads one JSONL file given on the command line, writes
only to standard output, deterministic. Nothing here knows about any particular agent.

Usage: python scripts/shadow_baseline_measures.py items.jsonl [--window-days 30] [--ngram 5]
                                                             [--threshold 0.5] [--tasks-total N]
Each line of the input: {"id": "...", "date": "YYYY-MM-DD", "text": "...", "title": "..." (optional)}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from statistics import NormalDist
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

TOKEN = re.compile(r"\w+", re.UNICODE)

# Provisional explicit-callback phrases (English and Polish); to be fixed in the preregistration.
CALLBACK_PHRASES: Tuple[str, ...] = (
    "as i wrote", "i wrote earlier", "i wrote before", "as i mentioned", "i mentioned before",
    "in my earlier", "in my last post", "in my previous post", "last time i",
    "jak pisałem", "jak pisałam", "pisałem wcześniej", "pisałam wcześniej", "wspominałem",
    "wspominałam", "w poprzednim wpisie", "w moim poprzednim", "ostatnio pisałem", "ostatnio pisałam",
)


@dataclass(frozen=True)
class Item:
    item_id: str
    day: date
    text: str
    title: str = ""


def parse_items(lines: Iterable[str]) -> List[Item]:
    items: List[Item] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            items.append(Item(str(row["id"]), date.fromisoformat(row["date"]), str(row["text"]), str(row.get("title", ""))))
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("line %d is not a valid item: %s" % (number, exc))
    return sorted(items, key=lambda i: (i.day, i.item_id))


def tokens(text: str) -> List[str]:
    return TOKEN.findall(text.lower())


def ngrams(text: str, n: int) -> Set[Tuple[str, ...]]:
    toks = tokens(text)
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def earlier_within(items: Sequence[Item], index: int, window_days: int) -> List[Item]:
    """Items strictly before items[index] in time and at most window_days days older."""
    current = items[index]
    return [j for j in items[:index] if 0 < (current.day - j.day).days <= window_days]


def repetition_overlap(items: Sequence[Item], index: int, window_days: int = 30, n: int = 5) -> float:
    """Largest share of the item's n-grams that one earlier item (within the window) already contains."""
    grams = ngrams(items[index].text, n)
    if not grams:
        return 0.0
    best = 0.0
    for earlier in earlier_within(items, index, window_days):
        best = max(best, len(grams & ngrams(earlier.text, n)) / len(grams))
    return best


def is_repetition(items: Sequence[Item], index: int, window_days: int = 30, n: int = 5, threshold: float = 0.5) -> bool:
    return repetition_overlap(items, index, window_days, n) >= threshold


def is_callback(items: Sequence[Item], index: int, window_days: int = 30, min_title_words: int = 3,
                phrases: Sequence[str] = CALLBACK_PHRASES) -> bool:
    """An explicit reference to an earlier own item: a callback phrase, or an earlier title quoted in full."""
    text = items[index].text.lower()
    if any(p in text for p in phrases):
        return True
    for earlier in earlier_within(items, index, window_days):
        title = " ".join(tokens(earlier.title))
        if len(title.split()) >= min_title_words and title in " ".join(tokens(text)):
            return True
    return False


def daily_counts(items: Sequence[Item], predicate: Callable[[int], bool]) -> List[Tuple[date, int, int]]:
    """(day, number of items, number flagged) per day, in date order."""
    per_day: Dict[date, List[int]] = {}
    for index, item in enumerate(items):
        counts = per_day.setdefault(item.day, [0, 0])
        counts[0] += 1
        counts[1] += 1 if predicate(index) else 0
    return [(d, c[0], c[1]) for d, c in sorted(per_day.items())]


def intraclass_correlation(daily: Sequence[Tuple[date, int, int]]) -> float:
    """One-way ANOVA estimator of the day-level intraclass correlation of a binary measure, clamped to [0, 1]."""
    sizes = [n for _, n, _ in daily]
    k, total = len(sizes), sum(sizes)
    if k < 2 or total <= k:
        raise ValueError("need at least two days and more observations than days")
    flagged = sum(f for _, _, f in daily)
    mean = flagged / total
    msb = sum(n * (f / n - mean) ** 2 for _, n, f in daily) / (k - 1)
    msw = sum(f * (1 - f / n) for _, n, f in daily) / (total - k)
    n0 = (total - sum(n * n for n in sizes) / total) / (k - 1)
    denominator = msb + (n0 - 1) * msw
    return 0.0 if denominator <= 0 else max(0.0, min(1.0, (msb - msw) / denominator))


def _z(alpha: float, power: float) -> float:
    dist = NormalDist()
    return dist.inv_cdf(1 - alpha / 2) + dist.inv_cdf(power)


def mde_task_randomised(p: float, n_a: float, n_b: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """Minimum detectable difference when tasks are randomised within days (the day effect is blocked out)."""
    return _z(alpha, power) * (p * (1 - p) * (1 / n_a + 1 / n_b)) ** 0.5


def mde_day_randomised(p: float, days_a: float, days_b: float, tasks_per_day: float, icc: float,
                       alpha: float = 0.05, power: float = 0.8) -> float:
    """Minimum detectable difference when whole days are randomised (design effect 1 + (m - 1) * icc)."""
    deff = 1 + (tasks_per_day - 1) * icc
    n_a, n_b = days_a * tasks_per_day / deff, days_b * tasks_per_day / deff
    return _z(alpha, power) * (p * (1 - p) * (1 / n_a + 1 / n_b)) ** 0.5


def mde_table(p: float, tasks_total: float, exposures: Sequence[float] = (0.1, 0.25, 0.5)) -> List[Dict[str, float]]:
    return [{"exposure": e, "tasks_in_memory_arm": tasks_total * e,
             "mde": mde_task_randomised(p, tasks_total * (1 - e), tasks_total * e)} for e in exposures]


def summarise(items: Sequence[Item], window_days: int, n: int, threshold: float, tasks_total: Optional[float]) -> Dict[str, object]:
    out: Dict[str, object] = {"items": len(items), "days": len({i.day for i in items}), "window_days": window_days,
                              "ngram": n, "repetition_threshold": threshold}
    measures = {
        "repetition": lambda idx: is_repetition(items, idx, window_days, n, threshold),
        "callback": lambda idx: is_callback(items, idx, window_days),
    }
    for name, predicate in measures.items():
        daily = daily_counts(items, predicate)
        total, flagged = sum(c for _, c, _ in daily), sum(f for _, _, f in daily)
        rate = flagged / total if total else 0.0
        entry: Dict[str, object] = {"rate": rate, "flagged": flagged}
        try:
            entry["day_icc"] = intraclass_correlation(daily)
        except ValueError as exc:
            entry["day_icc"] = None
            entry["note"] = str(exc)
        if tasks_total and 0 < rate < 1:
            entry["mde_by_exposure"] = mde_table(rate, tasks_total)
        out[name] = entry
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Repetition and callback rates, their day-to-day variance and the detectable "
                                                 "difference of a randomised comparison, from an agent's own past items.")
    parser.add_argument("items", help="JSONL file: id, date, text, optional title")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--ngram", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--tasks-total", type=float, default=None, help="tasks in the planned comparison, for the detectable-difference table")
    args = parser.parse_args(argv)
    try:
        with open(args.items, encoding="utf-8") as handle:
            items = parse_items(handle)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("input error: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summarise(items, args.window_days, args.ngram, args.threshold, args.tasks_total), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
