import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_foundation_contract_construction.py"
SPEC = importlib.util.spec_from_file_location("foundation_contract", SCRIPT)
foundation = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(foundation)


def test_frozen_construction_passes(tmp_path):
    report = foundation.run(tmp_path / "report.json")
    assert report["status"] == "passed-authored-model-free-construction"
    assert report["counts"] == {"canonical_events": 2, "stage_receipts": 6, "invalid_mutations": 12}
    assert all(check["passed"] for check in report["checks"])
    assert report["model_api_used"] is False
    assert report["independent_review"] is False
    assert report["parent_execution_authorized"] is False


def test_physical_loss_cannot_be_claimed_from_recoverable_bytes():
    receipts = foundation.load_jsonl(foundation.RECEIPTS)
    f1 = copy.deepcopy(receipts[1])
    f1["data_loss_state"] = "confirmed"
    with pytest.raises(foundation.ContractError, match="confirmed physical loss"):
        foundation.validate_receipt_shape(f1)


def test_correction_target_must_precede_correction():
    events = foundation.load_jsonl(foundation.EVENTS)
    changed = copy.deepcopy(events)
    changed[1]["revision"]["target_event_id"] = "EV-FFFFFFFFFFFFFFFF"
    with pytest.raises(foundation.ContractError, match="revision target"):
        foundation.validate_events(changed)


def test_passing_receipt_requires_all_mandatory_checks_to_pass():
    receipts = foundation.load_jsonl(foundation.RECEIPTS)
    changed = copy.deepcopy(receipts[3])
    next(check for check in changed["checks"] if check["check_id"] == "authorization_filter_passed")["status"] = "unknown"
    with pytest.raises(foundation.ContractError, match="pass receipt has non-pass check"):
        foundation.validate_receipt_shape(changed)

