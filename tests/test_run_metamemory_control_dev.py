import json

import pytest

from scripts.build_metamemory_dev_corpus import write_corpus
from scripts.run_metamemory_control_dev import read_jsonl, run, run_all


def test_typed_control_separates_monitoring_from_recovery(tmp_path):
    write_corpus(tmp_path)
    cases = read_jsonl(tmp_path / "cases.jsonl")
    rows = run_all(cases)

    typed_monitor = {row["case_id"]: row for row in rows if row["policy"] == "typed_monitor"}
    typed_control = {row["case_id"]: row for row in rows if row["policy"] == "typed_control"}

    assert typed_monitor["A01"]["action"] == "ABSTAIN"
    assert typed_control["A01"]["correct"] is True
    assert typed_control["A01"]["trace"] == ["TEMPORAL_CUE"]
    assert typed_control["U01"]["action"] == "ABSTAIN_NOT_STORED"
    assert typed_control["Q01"]["action"] == "ASK_CLARIFICATION"
    assert typed_control["C01"]["action"] == "ABSTAIN_CONFLICT"


def test_exploratory_summary_exposes_scalar_common_mode_failures(tmp_path):
    write_corpus(tmp_path)
    summary = run(tmp_path)

    scalar = summary["policy_metrics"]["semantic_consistency"]
    control = summary["policy_metrics"]["typed_control"]
    monitor = summary["policy_metrics"]["typed_monitor"]

    assert scalar["common_mode_consistent_wrong"] == 2
    assert scalar["selective_risk"] > 0
    assert control["critical_unsupported_answers"] == 0
    assert control["stored_target_recovery"] == 1.0
    assert monitor["stored_target_recovery"] < control["stored_target_recovery"]
    assert all(summary["candidate_gate_checks"].values())


def test_runner_rejects_modified_frozen_cases(tmp_path):
    write_corpus(tmp_path)
    cases_path = tmp_path / "cases.jsonl"
    rows = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["truth"]["expected_value"] = "tampered"
    cases_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Frozen case hash mismatch"):
        run(tmp_path)
