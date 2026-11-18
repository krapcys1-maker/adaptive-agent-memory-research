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
        ("s1-development-completed-s2-not-approved", "completed"),
        ("screen-completed-preliminary-not-confirmed", "completed"),
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


def test_every_status_that_names_a_completed_stage_is_counted_as_completed() -> None:
    """A status such as "<stage>-completed-<rest>" must not fall through to awaiting: add it to STATUS_BUCKETS."""
    with summary.REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        statuses = {row["status"].strip().lower() for row in csv.DictReader(handle)}
    for status in statuses:
        if "completed" in status and not status.startswith(("blocked", "invalid", "partial")):
            assert summary.bucket(status) == "completed", status


def test_the_autolab_alfworld_programs_are_registered() -> None:
    with summary.REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = {row["experiment_id"]: row for row in csv.DictReader(handle)}
    for program, folder in (("ALFWORLD-LADDER-R4-V3", "autolab-alfworld-ladder-r4-v3"),
                            ("ALFWORLD-LADDER-R4-V4", "autolab-alfworld-ladder-r4-v4")):
        row = rows[program]
        assert summary.bucket(row["status"]) == "completed"
        assert row["artifact_path"] == f"data/lab/{folder}/"
        assert (ROOT / row["artifact_path"] / "PUBLISHED_FILES.json").is_file()
        assert (ROOT / row["manifest_path"]).is_file()
