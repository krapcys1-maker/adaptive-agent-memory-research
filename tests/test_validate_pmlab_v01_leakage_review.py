import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("leakage_validator", ROOT / "scripts" / "validate_pmlab_v01_leakage_review.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PMLABV01LeakageReviewValidatorTests(unittest.TestCase):
    def completed_review(self):
        review = json.loads((MODULE.BLIND / "leakage-review-form.json").read_text(encoding="utf-8"))
        review.update({
            "reviewer_id": "synthetic-validator-test-only",
            "reviewer_family_or_affiliation": "unit test",
            "review_started_at": "2026-08-22T01:00:00Z",
            "review_completed_at": "2026-08-22T02:00:00Z",
            "whole_packet_decision": "accept",
            "signature_or_verifiable_acknowledgement": "not-independent-unit-test",
        })
        for item in review["category_reviews"].values():
            item["decision"] = "accept"
        for key in review["statements"]:
            review["statements"][key] = True
        return review

    def write_review(self, review, folder):
        path = Path(folder) / "review.json"
        path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def test_complete_synthetic_contract_passes_without_unlocking_backend(self):
        with tempfile.TemporaryDirectory() as folder:
            result = MODULE.validate(self.write_review(self.completed_review(), folder))
        self.assertEqual(result["decision"], "accept")
        self.assertFalse(result["backend_run_permitted"])
        self.assertFalse(result["author_labels_read"])

    def test_rejection_requires_notes_and_controls_whole_decision(self):
        review = self.completed_review()
        first = next(iter(review["category_reviews"].values()))
        first["decision"] = "reject"
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "rejection requires notes"):
                MODULE.validate(self.write_review(review, folder))
            first["notes"] = "material frame overlap"
            review["whole_packet_decision"] = "reject"
            result = MODULE.validate(self.write_review(review, folder))
        self.assertEqual(result["decision"], "reject")

    def test_blank_template_fails(self):
        with self.assertRaisesRegex(ValueError, "reviewer_id is blank"):
            MODULE.validate(MODULE.BLIND / "leakage-review-form.json")


if __name__ == "__main__":
    unittest.main()
