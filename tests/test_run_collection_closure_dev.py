import json

import pytest

from scripts.build_collection_closure_corpus_v1 import write_corpus
from scripts.run_collection_closure_dev import artifact_maps, public_case, read_jsonl, run, run_all


def rows_for_arm(rows, arm):
    return {row["stratum"]: row for row in rows if row["arm"] == arm and row["language"] == "en"}


def test_public_case_strips_all_gold():
    case = {"case_id": "x", "query": "q", "gold": {"expected_action": "secret"}}
    assert public_case(case) == {"case_id": "x", "query": "q"}


def test_insertion_check_isolated_from_certificate_only_arm(tmp_path):
    write_corpus(tmp_path)
    cases = read_jsonl(tmp_path / "cases.jsonl")
    rows = run_all(cases, artifact_maps(tmp_path))
    certificate = rows_for_arm(rows, "query_certificate")["admissible-insertion-changes-negative-answer"]
    checked = rows_for_arm(rows, "certificate_plus_insertion")["admissible-insertion-changes-negative-answer"]
    assert certificate["negative_tier"] == "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE"
    assert certificate["unsafe_strong_negative"]
    assert checked["negative_tier"] == "N1_NOT_FOUND_IN_SEARCHED_SCOPE"
    assert checked["action"] == "ABSTAIN_INCONCLUSIVE"
    assert not checked["unsafe_strong_negative"]


def test_candidate_invalidates_expiry_mutation_and_unavailable_replica(tmp_path):
    write_corpus(tmp_path)
    rows = rows_for_arm(run_all(read_jsonl(tmp_path / "cases.jsonl"), artifact_maps(tmp_path)), "certificate_plus_insertion")
    assert rows["expired-exact-certificate"]["action"] == "PROBE_SCOPE"
    assert rows["scope-mutated-after-certificate"]["action"] == "PROBE_SCOPE"
    assert rows["required-replica-unavailable"]["action"] == "PROBE_SCOPE"
    assert not rows["required-replica-unavailable"]["unsafe_strong_negative"]


def test_candidate_distinguishes_explicit_negative_from_bounded_absence(tmp_path):
    write_corpus(tmp_path)
    rows = rows_for_arm(run_all(read_jsonl(tmp_path / "cases.jsonl"), artifact_maps(tmp_path)), "certificate_plus_insertion")
    assert rows["explicit-negative-fact-in-complete-scope"]["negative_tier"] == "N3_PROPOSITION_FALSE"
    assert rows["absent-positive-without-explicit-negation"]["negative_tier"] == "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE"
    assert rows["globally-incomplete-query-complete-entity-slice"]["action"] == "REPORT_BOUNDED_ABSENCE"


def test_positive_evidence_does_not_require_global_closure(tmp_path):
    write_corpus(tmp_path)
    rows = rows_for_arm(run_all(read_jsonl(tmp_path / "cases.jsonl"), artifact_maps(tmp_path)), "certificate_plus_insertion")
    assert rows["positive-certain-answer-in-incomplete-collection"]["action"] == "ANSWER_SUPPORTED"
    assert rows["positive-certain-answer-in-incomplete-collection"]["negative_tier"] == "NONE"


def test_summary_keeps_promotion_gate_closed(tmp_path):
    write_corpus(tmp_path)
    summary = run(tmp_path)
    candidate = summary["policy_metrics"]["certificate_plus_insertion"]
    assert candidate["unsupported_n3"] == 0
    assert candidate["unsupported_n2"] == 0
    assert candidate["counterexample_insertion_detection"] == 1
    assert candidate["positive_safe_coverage"] == 1
    assert summary["candidate_gate_checks"]["matched_coverage_point_available"] is False
    assert summary["all_candidate_gates_pass"] is False


def test_runner_rejects_tampered_artifact(tmp_path):
    write_corpus(tmp_path)
    path = tmp_path / "certificates.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["status"] = "invalid"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen corpus hash mismatch|Frozen artifact hash mismatch"):
        run(tmp_path)
