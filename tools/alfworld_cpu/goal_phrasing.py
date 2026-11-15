"""Count goal phrasings per ALFWorld split (CPU only, read-only).

ALFWorld writes the three "transform" task types (clean, cool, heat) in two forms:
a verb form ("cool some egg and put it in microwave") and an adjective form
("put a cool egg in microwave"). Small models may treat the adjective form as plain
pick-and-place. This script counts both forms per split and per task type, so that a
development sample can be stratified by phrasing.

Usage:
    python goal_phrasing.py --data-root <ALFWORLD_DATA>/json_2.1.1 [--out phrasing.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import Counter, defaultdict

SPLITS = ("train", "valid_seen", "valid_unseen")


def goal_of(game: dict) -> str:
    grammar = game.get("grammar", "")
    i = grammar.find("Your task is to: ")
    if i < 0:
        return "?"
    return grammar[i + len("Your task is to: "):].split(".")[0].split('"')[0].strip()


def phrasing(goal: str) -> str:
    g = goal.lower()
    if re.match(r"(put|place) (a|an|some) (clean|hot|cool|cold|heated|cooled|warm) ", g):
        return "adjective_form"
    if re.match(r"(clean|heat|cool) ", g) and " and put" in g:
        return "verb_form"
    if g.startswith(("put two", "find two")):
        return "two_objects"
    if "lamp" in g:
        return "examine_form" if g.startswith("examine") else "look_at_form"
    if g.startswith(("put", "place", "find")):
        return "place"
    return "other"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", required=True, help="path to ALFWorld json_2.1.1")
    ap.add_argument("--out", default=None, help="optional JSON file with one row per game")
    args = ap.parse_args()
    rows = {}
    for split in SPLITS:
        rows[split] = []
        for path in sorted(glob.glob(os.path.join(args.data_root, split, "*", "*", "game.tw-pddl"))):
            with open(path, encoding="utf-8") as f:
                game = json.load(f)
            goal = goal_of(game)
            task_type = os.path.basename(os.path.dirname(os.path.dirname(path))).split("-")[0]
            rows[split].append({"game": os.path.relpath(os.path.dirname(path), os.path.join(args.data_root, split)),
                                "task_type": task_type, "goal": goal, "phrasing": phrasing(goal),
                                "walkthrough_len": len(game.get("walkthrough") or [])})
        counts = defaultdict(Counter)
        for r in rows[split]:
            counts[r["task_type"]][r["phrasing"]] += 1
        n = len(rows[split])
        adj = sum(1 for r in rows[split] if r["phrasing"] == "adjective_form")
        print(f"{split}: {n} games, adjective-form transform goals {adj} ({100 * adj / max(1, n):.0f}% of the split)")
        for t in sorted(counts):
            print(f"  {t}: {dict(counts[t])}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
