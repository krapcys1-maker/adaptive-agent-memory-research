"""Count the experiment registry by what has happened to each row.

The README quotes these counts, and a hand-typed number drifts the moment a row
changes status: it once said 71 registered and 37 run while the registry held 74
rows, and "run" was never defined. Run this instead of trusting prose.

Buckets. A status listed in STATUS_BUCKETS is classified by that table first; any
other status by the start of the ``status`` column:

  completed   a measurement or a stage of one ran and its result is recorded, whatever
              it showed: starts with "completed", the row was retracted, or the table
              names it (for example "s1-development-completed-s2-not-approved": stage S1
              ran, S2 was not approved; "screen-completed-preliminary-not-confirmed": the
              screen ran, nothing was confirmed). "completed" never means "confirmed".
  blocked     starts with "blocked"
  invalid     starts with "invalid" or "partial"
  awaiting    anything else: designs, review packets, preregistered but not run

Every row lands in exactly one bucket, so the four counts always sum to the total.
A status that names a completed stage without starting with "completed" must be added
to STATUS_BUCKETS; a test fails when one is not.
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

# Statuses the prefix rule below would misclassify. Found by an external audit (gpt raport,
# 2026-11-18): both rows below were counted as awaiting although their stage had run.
STATUS_BUCKETS = {
    "s1-development-completed-s2-not-approved": "completed",    # EXP-XFER-1: stage S1 ran; S2 not approved
    "screen-completed-preliminary-not-confirmed": "completed",  # MAB-FC-LABEL-SCREEN-V1: the screen ran
}


def bucket(status: str) -> str:
    status = status.strip().lower()
    if status in STATUS_BUCKETS:
        return STATUS_BUCKETS[status]
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
