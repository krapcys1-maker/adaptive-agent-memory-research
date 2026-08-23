import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


BUILDER = load("utility_audit_builder", ROOT / "scripts" / "build_future_utility_independent_audit_v0.py")
VALIDATOR = load("utility_audit_validator", ROOT / "scripts" / "validate_future_utility_independent_audit_v0.py")


class FutureUtilityAuditPacketTests(unittest.TestCase):
    def test_builder_is_deterministic_and_gold_free(self):
        first = BUILDER.build_outputs()
        second = BUILDER.build_outputs()
        self.assertEqual(first, second)
        manifest = json.loads(first[BUILDER.BLIND / "manifest.json"])
        self.assertEqual(10, manifest["question_count"])
        self.assertFalse(manifest["author_answer_key_present"])
        self.assertNotIn("future-utility-causal-privacy-primary-source-audit", " ".join(map(str, first)))

    def test_generated_blank_packet_hashes_validate(self):
        manifest = VALIDATOR.verify_blank_packet()
        self.assertEqual("blank-gold-free-packet-awaiting-review", manifest["status"])

    def test_blank_form_is_not_a_completed_review(self):
        with self.assertRaises(ValueError):
            VALIDATOR.validate_completed(VALIDATOR.BLIND / "review-form.json", VALIDATOR.BLIND / "attestation.json")

    def test_contract_complete_synthetic_review_gets_integrity_receipt(self):
        form = json.loads((VALIDATOR.BLIND / "review-form.json").read_text(encoding="utf-8"))
        form["reviewer"] = {
            "reviewer_id_or_pseudonym": "unit-test-reviewer",
            "reviewer_kind": "model_project_operated",
            "family_or_affiliation": "synthetic-test",
            "review_started_at": "2026-08-23T10:00:00Z",
            "review_completed_at": "2026-08-23T10:05:00Z",
        }
        for finding in form["findings"]:
            finding.update({
                "verdict": "pass",
                "severity": "none",
                "evidence_locators": ["synthetic unit-test locator"],
                "rationale": "Contract exercise only; this is not a real review.",
                "required_change": None,
            })
        form["gate_recommendations"] = {"T1": "allow_shadow_only", "T2": "conditional", "T3": "deny", "T4": "deny"}
        form["blocking_findings"] = []
        form["residual_risks"] = ["Synthetic test does not establish real controls."]
        form["overall_rationale"] = "Validator contract exercise only."
        form["attestation_id"] = "ATTEST-UNIT-TEST"
        attestation = json.loads((VALIDATOR.BLIND / "attestation.json").read_text(encoding="utf-8"))
        attestation.update({
            "attestation_id": "ATTEST-UNIT-TEST",
            "reviewer_id_or_pseudonym": "unit-test-reviewer",
            "reviewer_kind": "model_project_operated",
            "family_or_affiliation": "synthetic-test",
            "packet_manifest_sha256": VALIDATOR.sha256(VALIDATOR.MANIFEST),
            "conflicts_or_prior_exposure": "Synthetic unit test; full project access.",
            "limitations": "No substantive review was performed.",
            "signature_or_verifiable_acknowledgement": "unit-test-acknowledgement",
        })
        attestation["statements"] = {key: True for key in attestation["statements"]}
        with tempfile.TemporaryDirectory() as directory:
            form_path = Path(directory) / "form.json"
            attestation_path = Path(directory) / "attestation.json"
            form_path.write_text(json.dumps(form), encoding="utf-8")
            attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
            receipt = VALIDATOR.validate_completed(form_path, attestation_path)
        self.assertEqual("completed-audit-form-integrity-valid", receipt["status"])
        self.assertEqual("allow_shadow_only", receipt["gate_recommendations"]["T1"])

    def test_blocking_finding_cannot_recommend_T1(self):
        form = json.loads((VALIDATOR.BLIND / "review-form.json").read_text(encoding="utf-8"))
        form["reviewer"] = {
            "reviewer_id_or_pseudonym": "test",
            "reviewer_kind": "human_project",
            "family_or_affiliation": "test",
            "review_started_at": "2026-08-23T10:00:00Z",
            "review_completed_at": "2026-08-23T10:01:00Z",
        }
        for index, finding in enumerate(form["findings"]):
            finding.update({
                "verdict": "fail" if index == 0 else "pass",
                "severity": "blocking" if index == 0 else "none",
                "evidence_locators": ["test"],
                "rationale": "test",
                "required_change": "repair" if index == 0 else None,
            })
        form.update({
            "gate_recommendations": {"T1": "conditional", "T2": "deny", "T3": "deny", "T4": "deny"},
            "blocking_findings": ["A01"],
            "residual_risks": [],
            "overall_rationale": "test",
            "attestation_id": "test",
        })
        with tempfile.TemporaryDirectory() as directory:
            form_path = Path(directory) / "form.json"
            form_path.write_text(json.dumps(form), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "blocking findings require T1 deny"):
                VALIDATOR.validate_completed(form_path, VALIDATOR.BLIND / "attestation.json")


if __name__ == "__main__":
    unittest.main()
