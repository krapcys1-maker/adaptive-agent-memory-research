"""Validation tests for the AAMR -> ResearchOS testability contract
generator (scripts/build_researchos_contract.py). Proves each rule actually
catches a violation, not just that real data happens to pass -- and that the
real, checked-in manifest is currently valid.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/research/Dokumenty dla Resherchera/_manifest_input.json"

spec = importlib.util.spec_from_file_location(
    "build_researchos_contract", ROOT / "scripts/build_researchos_contract.py")
build_researchos_contract = importlib.util.module_from_spec(spec)
sys.modules["build_researchos_contract"] = build_researchos_contract
spec.loader.exec_module(build_researchos_contract)

validate = build_researchos_contract.validate
ValidationError = build_researchos_contract.ValidationError


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_real_manifest_is_currently_valid() -> None:
    manifest = load_manifest()
    violations = validate(manifest)
    assert violations == [], violations


def test_missing_top_level_key_raises_structural_error() -> None:
    manifest = load_manifest()
    del manifest["openGaps"]
    try:
        validate(manifest)
        assert False, "expected ValidationError"
    except ValidationError:
        pass


def test_rule1_open_gap_without_testability_status_flagged() -> None:
    manifest = copy.deepcopy(load_manifest())
    manifest["openGaps"][0]["status"] = "OPEN"
    manifest["openGaps"][0]["testability_status"] = None
    violations = validate(manifest)
    assert any("no testability_status" in v for v in violations)


def test_rule2_request_with_nonexistent_gap_and_not_standalone_flagged() -> None:
    manifest = copy.deepcopy(load_manifest())
    manifest["researchRequests"][0]["linked_gap"] = "GAP-999"
    manifest["researchRequests"][0]["standalone"] = False
    violations = validate(manifest)
    assert any("does not exist in openGaps" in v for v in violations)


def test_rule2_standalone_request_with_no_gap_is_allowed() -> None:
    manifest = copy.deepcopy(load_manifest())
    manifest["researchRequests"][0]["linked_gap"] = None
    manifest["researchRequests"][0]["standalone"] = True
    violations = validate(manifest)
    assert not any("does not exist in openGaps" in v for v in violations)


def test_rule5_request_requiring_cannot_test_now_capability_flagged() -> None:
    manifest = copy.deepcopy(load_manifest())
    manifest["researchRequests"][0]["requires_capabilities"] = ["model fine-tuning"]
    violations = validate(manifest)
    assert any("CANNOT_TEST_NOW" in v for v in violations)


def test_rule5_request_requiring_unknown_capability_flagged() -> None:
    manifest = copy.deepcopy(load_manifest())
    manifest["researchRequests"][0]["requires_capabilities"] = ["telepathy"]
    violations = validate(manifest)
    assert any("unknown capability" in v for v in violations)


def test_rule6_missing_provenance_flagged() -> None:
    manifest = copy.deepcopy(load_manifest())
    manifest["testability"][0]["source"] = ""
    violations = validate(manifest)
    assert any("missing provenance" in v for v in violations)


def test_rule7_duplicate_alias_across_two_mechanisms_flagged() -> None:
    manifest = copy.deepcopy(load_manifest())
    manifest["doNotRediscover"].append({
        "canonical_name": "FAKE_DUPLICATE_MECHANISM",
        "aliases": [manifest["doNotRediscover"][0]["canonical_name"]],
        "status": "DROP",
        "ledger_entry": "Z",
        "source": "test-only",
    })
    violations = validate(manifest)
    assert any("appears under both" in v for v in violations)


def test_rule8_researchos_file_with_reserved_status_flagged(tmp_path, monkeypatch) -> None:
    fake_inbox = tmp_path / "Dokumenty z Resherchera"
    (fake_inbox / "candidates").mkdir(parents=True)
    bad_file = fake_inbox / "candidates" / "2026-01-01_mechanism_candidate_bad.md"
    bad_file.write_text(
        "---\nid: rmc-2026-01-01-999\ntype: mechanism_candidate\nstatus: VALIDATED\n---\n\n## Summary\n",
        encoding="utf-8")
    monkeypatch.setattr(build_researchos_contract, "INBOX_DIR", fake_inbox)
    manifest = load_manifest()
    violations = validate(manifest)
    assert any("AAMR-reserved result status" in v for v in violations)


def test_rule8_researchos_file_with_pending_review_status_is_fine(tmp_path, monkeypatch) -> None:
    fake_inbox = tmp_path / "Dokumenty z Resherchera"
    (fake_inbox / "candidates").mkdir(parents=True)
    good_file = fake_inbox / "candidates" / "2026-01-01_mechanism_candidate_good.md"
    good_file.write_text(
        "---\nid: rmc-2026-01-01-998\ntype: mechanism_candidate\nstatus: PENDING_AAMR_REVIEW\n---\n\n## Summary\n",
        encoding="utf-8")
    monkeypatch.setattr(build_researchos_contract, "INBOX_DIR", fake_inbox)
    manifest = load_manifest()
    violations = validate(manifest)
    assert not any("AAMR-reserved result status" in v for v in violations)


def test_generator_end_to_end_writes_contract(tmp_path, monkeypatch) -> None:
    out_path = tmp_path / "researchos_contract_v1.json"
    monkeypatch.setattr(build_researchos_contract, "CONTRACT_PATH", out_path)
    monkeypatch.setattr(build_researchos_contract, "INBOX_DIR", ROOT / "docs/research/Dokumenty z Resherchera")
    rc = build_researchos_contract.main()
    assert rc == 0
    assert out_path.exists()
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["schemaVersion"] == "1"
    assert "generatedAt" in written and "aamrCommit" in written
    assert len(written["testability"]) > 0
    assert len(written["doNotRediscover"]) > 0
