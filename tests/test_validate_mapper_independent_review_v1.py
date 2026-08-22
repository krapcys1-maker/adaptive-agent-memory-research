import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("review_validator", ROOT / "scripts" / "validate_mapper_independent_review_v1.py")
MODULE = importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; SPEC.loader.exec_module(MODULE)


class ReviewValidatorTests(unittest.TestCase):
    def test_blank_packet_integrity(self):
        manifest = MODULE.verify_blank_packet()
        self.assertEqual(67, manifest["selected_semantic_groups"])

    def test_blank_form_is_rejected_as_incomplete(self):
        with self.assertRaises(ValueError):
            MODULE.validate_completed(MODULE.BLIND_DIR / "review-form.jsonl", MODULE.BLIND_DIR / "attestation.json")

    def test_duplicate_form_is_rejected_before_label_validation(self):
        rows = MODULE.read_jsonl(MODULE.BLIND_DIR / "review-form.jsonl")
        duplicate = rows[:-1] + [rows[0]]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in duplicate), encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.validate_completed(path, MODULE.BLIND_DIR / "attestation.json")

    def test_contract_complete_synthetic_form_receives_integrity_receipt(self):
        forms = MODULE.read_jsonl(MODULE.BLIND_DIR / "review-form.jsonl")
        jobs = {row["semantic_group_id"]: row for row in MODULE.read_jsonl(MODULE.JOBS_PATH)}
        corpus = {
            row["case_id"]: row
            for row in MODULE.read_jsonl(MODULE.ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1" / "cases.jsonl")
        }
        attestation_id = "TEST-ATTESTATION"
        for form in forms:
            form["reviewer_id_or_pseudonym"] = "test-reviewer"
            form["reviewer_family_or_affiliation"] = "test-family"
            form["reviewed_at"] = "2026-08-22T00:00:00Z"
            form["language_equivalent"] = True
            form["stage_isolation"] = "valid"
            form["confidence"] = "high"
            form["exclude_recommendation"] = False
            form["rationale"] = "Synthetic validator test using contract-valid labels."
            form["attestation_id"] = attestation_id
            for case in jobs[form["semantic_group_id"]]["cases"]:
                label = dict(corpus[case["case_id"]]["gold"])
                if case["stage"] == "entity_linking" and "selected_ids" not in label:
                    label["selected_ids"] = []
                form["independent_labels"][case["language"]] = label
        attestation = {
            "attestation_id": attestation_id,
            "reviewer_id_or_pseudonym": "test-reviewer",
            "reviewer_family_or_affiliation": "test-family",
            "review_started_at": "2026-08-22T00:00:00Z",
            "review_completed_at": "2026-08-22T01:00:00Z",
            "source_commit": "fc9b212",
            "packet_manifest_sha256": MODULE.sha256(MODULE.MANIFEST_PATH),
            "statements": {
                "did_not_inspect_author_gold": True,
                "did_not_inspect_advisory_predictions_or_scores": True,
                "did_not_inspect_candidate_implementations": True,
                "labeled_each_language_before_reveal": True,
                "disclosed_conflicts_or_prior_exposure": True,
            },
            "conflict_or_prior_exposure_notes": "Synthetic unit test only; not an independent review.",
            "signature_or_verifiable_acknowledgement": "unit-test-signature",
        }
        with tempfile.TemporaryDirectory() as directory:
            form_path = Path(directory) / "completed.jsonl"
            attestation_path = Path(directory) / "attestation.json"
            form_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in forms), encoding="utf-8")
            attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
            receipt = MODULE.validate_completed(form_path, attestation_path)
        self.assertEqual("completed-independent-form-valid-before-reveal", receipt["status"])
        self.assertEqual(67, receipt["reviewed_groups"])


if __name__ == "__main__": unittest.main()
