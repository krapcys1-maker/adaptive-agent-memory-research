import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("review_validator", ROOT / "scripts" / "validate_natural_history_contract_review.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def completed_form():
    manifest = json.loads(MODULE.MANIFEST.read_text(encoding="utf-8"))
    return {
        "packet_id": manifest["packet_id"], "packet_manifest_sha256": hashlib.sha256(MODULE.MANIFEST.read_bytes()).hexdigest(),
        "source_commit": manifest["source_commit"],
        "reviewer": {"reviewer_id": "reviewer-test", "reviewer_class": "human_independent", "model_family": None, "provider": None},
        "blindness_attestation": {
            "not_an_author_of_reviewed_contract": True, "did_not_view_forbidden_advisory_paths": True,
            "did_not_view_builder_or_backend_output": True, "used_one_stateless_review_context": True,
        },
        "dimensions": [
            {"dimension": dimension, "decision": "accept", "evidence": "Reviewed exact rule and schema.", "required_change": ""}
            for dimension in sorted(MODULE.DIMENSIONS)
        ],
        "blockers": [], "required_adversarial_tests": ["Run frozen adversarial fixtures."],
        "overall_verdict": "accept_for_development_builder_review", "builder_unlock_recommendation": True,
        "signed_at": "2026-08-23T00:00:00Z",
    }


def test_completed_independent_form_validates(tmp_path):
    path = tmp_path / "review.json"
    path.write_text(json.dumps(completed_form()), encoding="utf-8")
    receipt = MODULE.validate(path)
    assert receipt["valid"] is True
    assert receipt["independent_class"] is True


def test_superseded_packet_rejects_every_form(tmp_path):
    path = tmp_path / "review.json"
    path.write_text(json.dumps(completed_form()), encoding="utf-8")
    old_packet = ROOT / "data" / "lab" / "pmlab-natural-history-v0" / "independent-contract-review-v0"
    try:
        MODULE.validate(path, old_packet)
    except ValueError as error:
        assert "not active" in str(error)
    else:
        raise AssertionError("superseded review packet accepted a form")


def test_nonaccept_cannot_recommend_unlock(tmp_path):
    form = completed_form()
    form["overall_verdict"] = "needs_revision"
    path = tmp_path / "review.json"
    path.write_text(json.dumps(form), encoding="utf-8")
    try:
        MODULE.validate(path)
    except ValueError:
        pass
    else:
        raise AssertionError("non-accept review recommended unlock")
