import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "review_foundation_contracts_deepseek.py"
SPEC = importlib.util.spec_from_file_location("foundation_review", SCRIPT)
review = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(review)


def valid_result():
    return {
        "findings": [
            {"question_id": f"A{i:02d}", "verdict": "conditional", "severity": "major", "evidence_locators": ["artifact:section"], "rationale": "A control remains incomplete.", "required_change": "Add an unseen attack."}
            for i in range(1, 13)
        ],
        "overall_verdict": "needs_revision",
        "gate_recommendations": {"canonical_contract": "conditional", "delayed_reveal_contract": "conditional", "parent_experiment": "deny"},
        "blocking_findings": ["A06", "A11"],
        "residual_risks": ["Same-author bias remains."],
        "overall_rationale": "The contracts need unseen review.",
    }


def test_job_contains_only_declared_subject_artifacts():
    job = review.build_job()
    manifest = review.json.loads((review.BLIND / "packet-manifest.json").read_text(encoding="utf-8"))
    assert set(job["subject_artifacts"]) == set(manifest["subject_artifacts"])
    assert not any("invalid-mutations" in path or "audit-report" in path or "CURRENT_STATE" in path for path in job["subject_artifacts"])
    serialized = review.json.dumps(job)
    for forbidden in ("INV-PREFIX-QUERY-FIELD", "INV-EVENT-BAD-HASH", "passed-authored-L0-L4", "Latest diagnostics"):
        assert forbidden not in serialized


def test_exact_review_schema_accepts_registered_form():
    assert review.validate(valid_result())["overall_verdict"] == "needs_revision"


def test_model_cannot_unlock_parent():
    value = valid_result()
    value["gate_recommendations"]["parent_experiment"] = "allow"
    with pytest.raises(ValueError, match="cannot unlock parent"):
        review.validate(value)


def test_all_twelve_findings_are_required_in_order():
    value = valid_result()
    value["findings"] = value["findings"][:-1]
    with pytest.raises(ValueError, match="A01-A12"):
        review.validate(value)
