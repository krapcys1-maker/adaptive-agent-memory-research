"""Count the experiment registry by what has happened to each row.

The README quotes these counts, and a hand-typed number drifts the moment a row
changes status: it once said 71 registered and 37 run while the registry held 74
rows, and "run" was never defined. Run this instead of trusting prose.

Buckets, by the start of the ``status`` column:

  completed   starts with "completed", or the row was retracted
  blocked     starts with "blocked"
  invalid     starts with "invalid" or "partial"
  awaiting    anything else: designs, review packets, preregistered but not run

Every row lands in exactly one bucket, so the four counts always sum to the total.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "lab" / "experiment-registry.csv"

BUCKETS = ("completed", "blocked", "invalid", "awaiting")


def bucket(status: str) -> str:
    status = status.strip().lower()
    if status.startswith(("completed", "retracted")):
        return "completed"
    if status.startswith("blocked"):
        return "blocked"
    if status.startswith(("invalid", "partial")):
        return "invalid"
    return "awaiting"


def summarise(path: Path = REGISTRY) -> dict[str, int]:
    counts: Counter = Counter()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            counts[bucket(row.get("status") or "")] += 1
    return {"total": sum(counts.values()), **{name: counts[name] for name in BUCKETS}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    arguments = parser.parse_args(argv)
    summary = summarise()
    if arguments.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"{summary['total']} registered experiments")
        for name in BUCKETS:
            print(f"  {name:<10} {summary[name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
