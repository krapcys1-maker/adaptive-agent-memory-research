import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_foundation_delayed_reveal.py"
SPEC = importlib.util.spec_from_file_location("delayed_reveal", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


def dataset():
    return {
        "prefixes": audit.load_jsonl(audit.PREFIXES),
        "access": audit.load_json(audit.ACCESS),
        "reveals": audit.load_jsonl(audit.REVEALS),
        "gold": audit.load_jsonl(audit.GOLD),
        "states": audit.load_json(audit.STATES),
        "schedule": audit.load_jsonl(audit.SCHEDULE),
    }


def test_frozen_delayed_reveal_audit_passes(tmp_path):
    report = audit.run(tmp_path / "report.json")
    assert report["status"] == "passed-authored-L0-L4-construction"
    assert report["levels"]["L0_BYTE_FIELD"]["passed"] is True
    assert report["levels"]["L1_LEXICAL"]["passed"] is None
    assert report["levels"]["L4_REPRODUCIBLE_BUILD"]["passed"] is True
    assert report["levels"]["L5_INDEPENDENT_SEMANTIC"]["passed"] is False
    assert report["counts"]["invalid_mutations"] == 14
    assert report["parent_execution_authorized"] is False


def test_prefix_rejects_direct_future_query_field():
    value = dataset()
    value["prefixes"][0]["query"] = "future query"
    with pytest.raises(audit.LeakageError, match="prefix forbidden field"):
        audit.validate_all(value)


def test_counterfactual_fork_requires_same_prefix_and_incompatible_tasks():
    value = dataset()
    value["reveals"][2]["prefix_id"] = "PFX-FFFFFFFFFFFFFFFF"
    with pytest.raises(audit.LeakageError, match="reveal prefix join"):
        audit.validate_all(value)
    value = dataset()
    for row in value["gold"]:
        row["supported_answer_state"] = "STATE-000000000001"
    with pytest.raises(audit.LeakageError, match="counterfactual answers not incompatible"):
        audit.validate_all(value)


def test_write_side_access_must_stay_inside_prefix_allowlist():
    value = dataset()
    value["access"]["observed_read_paths"].append("reveal-freeze-v0/reader/reveals.jsonl")
    with pytest.raises(audit.LeakageError, match="observed read outside allowlist"):
        audit.validate_all(value)

