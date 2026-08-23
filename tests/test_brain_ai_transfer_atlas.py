from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_brain_ai_transfer_atlas.py"
SPEC = importlib.util.spec_from_file_location("validate_brain_ai_transfer_atlas", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_atlas_contract_and_coverage() -> None:
    result = MODULE.validate()
    assert result["rows"] == 38
    assert result["gap_candidates"] >= 8
    assert result["agent_status"]["none_found"] >= 1
    assert result["status"] == "valid-research-atlas-not-architecture-approval"


def test_atlas_has_distinct_risks_tests_and_source_layers() -> None:
    with MODULE.DEFAULT_ATLAS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len({row["primary_risk"] for row in rows}) == len(rows)
    assert len({row["next_test"] for row in rows}) == len(rows)
    assert all("http" in row["biology_sources"] for row in rows)
    assert all(
        row["llm_agent_status"] == "none_found" or "http" in row["ai_sources"]
        for row in rows
    )
