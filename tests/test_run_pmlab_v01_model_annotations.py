import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("model_annotations", ROOT / "scripts" / "run_pmlab_v01_model_annotations.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_roles_use_complete_but_differently_ordered_blind_inputs():
    a, b = MODULE.build_jobs("A"), MODULE.build_jobs("B")
    assert len(a) == len(b) == 12
    assert sum(len(job["queries"]) for job in a) == sum(len(job["queries"]) for job in b) == 120
    assert {row["example_id"] for job in a for row in job["queries"]} == {row["example_id"] for job in b for row in job["queries"]}
    assert a[0]["evidence_order"] != b[0]["evidence_order"]
    assert [job["category"] for job in a] != [job["category"] for job in b]


def test_batch_contract_accepts_valid_unanswerable_rows():
    job = MODULE.build_jobs("A")[0]
    rows = [{"example_id": row["example_id"], "answerable": False, "gold_evidence_ids": [], "gold_current_ids": [], "forbidden_stale_ids": [], "alternative_acceptable_ids": [], "confidence": 0.5, "notes": "No support found."} for row in job["queries"]]
    assert len(MODULE.validate_batch({"annotations": rows}, job, set())) == 10


def test_batch_rejects_answerable_without_gold():
    job = MODULE.build_jobs("A")[0]
    rows = [{"example_id": row["example_id"], "answerable": True, "gold_evidence_ids": [], "gold_current_ids": [], "forbidden_stale_ids": [], "alternative_acceptable_ids": [], "confidence": 0.5, "notes": ""} for row in job["queries"]]
    with pytest.raises(ValueError, match="answerability/current"):
        MODULE.validate_batch({"annotations": rows}, job, set())
