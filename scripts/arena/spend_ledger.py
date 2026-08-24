"""One spend ledger for the whole night, surviving every process that reads it.

A per-run cap stops one run. It cannot stop five runs from each stopping politely
at their own ceiling and costing five times what was agreed. So the total lives
on disk, is appended to per call, and every run consults it before asking the
provider for anything.

Append-only, one JSON object per line, for the reason the project's memory log is
append-only: a crash mid-run must not lose what was already paid for, and a total
recomputed from the lines cannot drift from them. A background run once died
after 29 calls with no result file and the spend was still real.

The file is the authority, not a variable. A second process starting later reads
the same total, so "each system gets $3" and "the night gets $10" are both true
at once and neither is a hope.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data/lab/arena/spend-ledger.jsonl"


class TotalCapReached(RuntimeError):
    """The night's budget is spent. Raised before the request, never after."""


class SpendLedger:
    """Cumulative paid-call cost, shared by every arena run that opens it."""

    def __init__(self, path: Path | None = None, total_cap_usd: float | None = None,
                 run_id: str = "unnamed", cap_scope: str | None = None) -> None:
        self.path = Path(path or DEFAULT_PATH)
        self.total_cap_usd = total_cap_usd
        self.run_id = run_id
        #: Which runs the cap counts. Without it the cap is all-time, which is
        #: what an author means by "the night's budget" and NOT what they mean by
        #: "$4 for this experiment". A $4 cap checked against an all-time total of
        #: $6 refuses the first call of a run that has spent nothing — correct
        #: arithmetic, wrong question, and it cost a run's worth of setup to find.
        #: Runs whose id starts with this prefix are counted; everything else in
        #: the file stays on the record and out of the sum.
        self.cap_scope = cap_scope
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    # ------------------------------------------------------------------ reading

    def entries(self) -> list[dict[str, Any]]:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        out: list[dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # A torn final line from a kill mid-write. Skipping it under-counts
                # by one call, which is the safe direction for a floor but not for
                # a cap — so it is counted at the most expensive rate seen instead.
                out.append({"usd": max((e.get("usd", 0.0) for e in out), default=0.0),
                            "torn": True})
        return out

    def total_usd(self, since_run: str | None = None) -> float:
        return round(sum(entry.get("usd", 0.0) for entry in self.entries()
                         if since_run is None or entry.get("run_id") == since_run), 6)

    def scoped_usd(self) -> float:
        """What the cap counts: this experiment's spend, or all of it if unscoped."""
        if self.cap_scope is None:
            return self.total_usd()
        return round(sum(entry.get("usd", 0.0) for entry in self.entries()
                         if str(entry.get("run_id", "")).startswith(self.cap_scope)), 6)

    def by_run(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for entry in self.entries():
            run = str(entry.get("run_id", "unnamed"))
            totals[run] = round(totals.get(run, 0.0) + entry.get("usd", 0.0), 6)
        return totals

    # ------------------------------------------------------------------ writing

    def record(self, usd: float, **detail: Any) -> None:
        line = json.dumps({
            "run_id": self.run_id,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "usd": round(usd, 8),
            **detail,
        }, sort_keys=True)
        # Opened per call rather than held open, so a killed process leaves a
        # complete file and a later one reads a correct total.
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    # ------------------------------------------------------------------ the cap

    def check(self, reserve_usd: float) -> None:
        """Refuse before the request, using the same reserve logic as the per-run cap."""
        if self.total_cap_usd is None:
            return
        spent = self.scoped_usd()
        if spent + reserve_usd > self.total_cap_usd:
            scope = f"runs matching {self.cap_scope!r}" if self.cap_scope else "all runs"
            raise TotalCapReached(
                f"${spent:.4f} spent across {scope}; the next call could cost up to "
                f"${reserve_usd:.4f} and the cap for this scope is "
                f"${self.total_cap_usd:.2f}. Stopping below it."
            )

    def summary(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "total_usd": self.total_usd(),
            "scoped_usd": self.scoped_usd(),
            "cap_scope": self.cap_scope,
            "total_cap_usd": self.total_cap_usd,
            "by_run": self.by_run(),
            "calls": len(self.entries()),
        }
