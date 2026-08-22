import json

import pytest

from scripts.build_evidence_sufficiency_corpus import write_corpus
from scripts.run_evidence_sufficiency_dev import read_jsonl, run, run_all


def rows_for_policy(rows, policy):
    return {row["case_id"]: row for row in rows if row["policy"] == policy}


def test_retrieved_monitor_does_not_claim_absence_without_collection_probe(tmp_path):
    write_corpus(tmp_path)
    cases = read_jsonl(tmp_path / "cases.jsonl")
    rows = run_all(cases)
    monitor = rows_for_policy(rows, "retrieved_obligation")

    assert monitor["SUFF-ABSENT-EMPTY-EN"]["action"] == "RETRIEVE_MISSING"
    assert monitor["SUFF-INVENTORY-UNKNOWN-EN"]["action"] == "ABSTAIN_INCONCLUSIVE"
    assert monitor["SUFF-STALE-RECOVERABLE-EN"]["action"] == "RETRIEVE_VALID"
    assert monitor["SUFF-CONFLICT-EN"]["action"] == "ABSTAIN_CONFLICT"


def test_collection_hybrid_executes_typed_gap_and_claim_actions(tmp_path):
    write_corpus(tmp_path)
    cases = read_jsonl(tmp_path / "cases.jsonl")
    rows = rows_for_policy(run_all(cases), "collection_hybrid")

    assert rows["SUFF-FACET-RECOVERABLE-EN"]["action"] == "RETRIEVE_MISSING"
    assert rows["SUFF-FACET-UNAVAILABLE-EN"]["action"] == "PARTIAL_WITH_GAP"
    assert rows["SUFF-EXTRA-CLAIM-EN"]["action"] == "ANSWER_SUPPORTED_ONLY"
    assert rows["SUFF-CITATION-GAP-EN"]["action"] == "REPAIR_ATTRIBUTION"
    assert rows["SUFF-ABSENT-SIMILAR-EN"]["action"] == "ABSTAIN_NOT_FOUND"
    assert all(row["exact_action"] for row in rows.values())


def test_summary_exposes_scalar_false_sufficiency_and_rejects_unmatched_coverage(tmp_path):
    write_corpus(tmp_path)
    summary = run(tmp_path)

    assert summary["policy_metrics"]["self_report"]["selective_sufficiency_risk"] > 0
    assert summary["policy_metrics"]["collection_hybrid"]["selective_sufficiency_risk"] == 0
    assert summary["policy_metrics"]["retrieved_obligation"]["exact_action_accuracy"] < 1
    assert summary["candidate_gate_checks"]["zero_critical_false_sufficient"] is True
    assert summary["candidate_gate_checks"]["gap_action_at_least_0.90"] is True
    assert summary["candidate_gate_checks"]["matched_coverage_point_available"] is False
    assert summary["candidate_gate_checks"]["matched_coverage_risk_gain_at_least_0.15"] is False
    assert summary["all_candidate_gates_pass"] is False


def test_runner_rejects_tampered_frozen_case(tmp_path):
    write_corpus(tmp_path)
    path = tmp_path / "cases.jsonl"
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    cases[0]["truth"]["expected_action"] = "ABSTAIN_NOT_FOUND"
    path.write_text("\n".join(json.dumps(case) for case in cases) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Frozen case hash mismatch"):
        run(tmp_path)
