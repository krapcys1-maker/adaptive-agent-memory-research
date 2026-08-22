import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("model_adjudication", ROOT / "scripts" / "run_pmlab_v01_model_adjudication.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_jobs_cover_only_all_frozen_disagreements():
    jobs = MODULE.build_jobs()
    ids = [case["example_id"] for job in jobs for case in job["cases"]]
    assert len(ids) == len(set(ids)) == 25
    assert all(set(case) == {"example_id", "query", "differing_fields", "candidate_alpha", "candidate_beta"} for job in jobs for case in job["cases"])


def test_adjudication_contract_accepts_a_grounded_unanswerable_case():
    job = MODULE.build_jobs()[0]
    rows = [{"example_id": case["example_id"], "answerable": False, "gold_evidence_ids": [], "gold_current_ids": [], "forbidden_stale_ids": [], "alternative_acceptable_ids": [], "confidence": 0.7, "candidate_disposition": "synthesized", "decision_basis": "No complete support."} for case in job["cases"]]
    assert len(MODULE.validate_batch({"adjudications": rows}, job, set())) == len(rows)


def test_adjudication_requires_specific_basis():
    job = MODULE.build_jobs()[0]
    rows = [{"example_id": case["example_id"], "answerable": False, "gold_evidence_ids": [], "gold_current_ids": [], "forbidden_stale_ids": [], "alternative_acceptable_ids": [], "confidence": 0.7, "candidate_disposition": "synthesized", "decision_basis": ""} for case in job["cases"]]
    with pytest.raises(ValueError, match="basis is blank"):
        MODULE.validate_batch({"adjudications": rows}, job, set())
