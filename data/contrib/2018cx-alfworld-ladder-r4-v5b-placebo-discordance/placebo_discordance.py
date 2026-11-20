"""Reproduce the V5B placebo contrast and tabulate all three-arm solve patterns."""

import argparse
from collections import Counter
import csv
from itertools import product
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "data/lab/autolab-alfworld-ladder-r4-v5b/per_unit.csv"
ARMS = ("none", "placebo", "retrieved_task")
Z_STOPPING_LOOK = 2.7777


def load_outcomes(path):
    pairs = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            arm = row["arm"]
            if arm not in ARMS:
                continue
            if row["error"] != "0" or row["solved"] not in {"0", "1"}:
                raise ValueError(f"Missing or invalid outcome: {row}")
            key = (row["cycle"], row["unit"], row["seed"])
            outcomes = pairs.setdefault(key, {})
            if arm in outcomes:
                raise ValueError(f"Duplicate outcome for {key}, {arm}")
            outcomes[arm] = int(row["solved"])
    if len(pairs) != 201 or any(set(outcomes) != set(ARMS) for outcomes in pairs.values()):
        raise ValueError("Expected 201 complete three-arm task pairs.")
    return [tuple(outcomes[arm] for arm in ARMS) for outcomes in pairs.values()]


def describe_contrast(label, differences):
    n = len(differences)
    gains = differences.count(1)
    losses = differences.count(-1)
    mean = statistics.mean(differences)
    se = math.sqrt(statistics.pvariance(differences) / n) or 1 / n
    margin = Z_STOPPING_LOOK * se
    print(f"{label}: {mean:+.3f} [{mean - margin:+.3f}, {mean + margin:+.3f}], "
          f"{gains} gains / {losses} losses")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, nargs="?", default=CSV_PATH)
    outcomes = load_outcomes(parser.parse_args().csv)
    print(f"Complete three-arm pairs: {len(outcomes)}")
    describe_contrast("placebo - none", [p - n for n, p, r in outcomes])
    describe_contrast("retrieved - placebo", [r - p for n, p, r in outcomes])
    describe_contrast("retrieved - none", [r - n for n, p, r in outcomes])

    patterns = Counter(outcomes)
    print("\nnone placebo retrieved count")
    for pattern in product((0, 1), repeat=len(ARMS)):
        print(*pattern, patterns[pattern])
    print("\nAmong retrieved gains vs placebo, none fails / solves:",
          patterns[0, 0, 1], patterns[1, 0, 1])
    print("Among retrieved losses vs placebo, none fails / solves:",
          patterns[0, 1, 0], patterns[1, 1, 0])


if __name__ == "__main__":
    main()
