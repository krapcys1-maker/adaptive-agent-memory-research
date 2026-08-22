import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "model_leakage_review",
    ROOT / "scripts" / "run_pmlab_v01_model_leakage_review.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _prediction(job, decision="accept", severity="low"):
    dev = next(row for row in job["queries"] if row["split"] == "development")
    test = next(row for row in job["queries"] if row["split"] == "test")
    material = [dev["example_id"], test["example_id"]] if decision == "reject" else []
    return {
        "category_review": {
            "category": job["category"],
            "decision": decision,
            "material_overlap_example_ids": material,
            "notes": "Specific comparison completed.",
            "findings": [
                {
                    "development_example_id": dev["example_id"],
                    "test_example_id": test["example_id"],
                    "leakage_type": "semantic_task_equivalence",
                    "severity": severity,
                    "reason": "The pair was compared directly.",
                }
            ],
        }
    }


def test_jobs_expose_only_registered_query_fields():
    jobs = MODULE.build_jobs()
    assert len(jobs) == 12
    assert all(len(job["queries"]) == 10 for job in jobs)
    assert all(
        set(row) == {"example_id", "split", "language", "query", "query_time", "family"}
        for job in jobs
        for row in job["queries"]
    )


def test_accept_and_reject_contracts_are_consistent():
    job = MODULE.build_jobs()[0]
    assert MODULE.validate_prediction(_prediction(job), job)["decision"] == "accept"
    assert MODULE.validate_prediction(_prediction(job, "reject", "material"), job)["decision"] == "reject"


def test_accept_cannot_hide_material_finding():
    job = MODULE.build_jobs()[0]
    with pytest.raises(ValueError, match="accepted category cannot contain"):
        MODULE.validate_prediction(_prediction(job, "accept", "material"), job)


def test_reject_requires_material_finding():
    job = MODULE.build_jobs()[0]
    with pytest.raises(ValueError, match="requires at least one material"):
        MODULE.validate_prediction(_prediction(job, "reject", "high"), job)
