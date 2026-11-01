"""The registry summary must put every row in exactly one bucket."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import registry_summary as summary  # noqa: E402


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("completed", "completed"),
        ("completed-exploratory-negative-question-closed", "completed"),
        ("retracted-leakage-artifact", "completed"),
        ("blocked-corpus-not-built", "blocked"),
        ("blocked-corpus-then-independent-review", "blocked"),
        ("invalid", "invalid"),
        ("invalidated-pre-run-split-leakage", "invalid"),
        ("partial-invalid", "invalid"),
        ("preregistered-not-run", "awaiting"),
        ("independent-review-packet-ready", "awaiting"),
        ("design-only-execution-locked", "awaiting"),
        ("", "awaiting"),
        ("  Completed  ", "completed"),
    ],
)
def test_a_status_lands_in_the_expected_bucket(status: str, expected: str) -> None:
    assert summary.bucket(status) == expected


def test_a_small_registry_is_counted_row_by_row(tmp_path: Path) -> None:
    registry = tmp_path / "registry.csv"
    with registry.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["experiment_id", "status"])
        writer.writeheader()
        for index, status in enumerate(["completed", "completed-x", "blocked-y", "partial-z", "design-q"]):
            writer.writerow({"experiment_id": f"PMLAB-T-{index:03d}", "status": status})
    assert summary.summarise(registry) == {
        "total": 5,
        "completed": 2,
        "blocked": 1,
        "invalid": 1,
        "awaiting": 1,
    }


def test_the_live_registry_is_fully_accounted_for() -> None:
    counts = summary.summarise()
    with summary.REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = sum(1 for _ in csv.DictReader(handle))
    assert counts["total"] == rows
    assert sum(counts[name] for name in summary.BUCKETS) == rows
