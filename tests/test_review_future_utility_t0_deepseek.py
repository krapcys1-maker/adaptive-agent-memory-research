import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "review_future_utility_t0_deepseek.py"
SPEC = importlib.util.spec_from_file_location("utility_review", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FutureUtilityT0DeepSeekReviewTests(unittest.TestCase):
    def test_review_packet_has_two_bounded_jobs_without_private_content(self):
        jobs = MODULE.build_jobs()
        self.assertEqual([job["job_id"] for job in jobs], ["privacy-and-governance", "measurement-and-causal-integrity"])
        for job in jobs:
            serialized = MODULE.json.dumps(job).lower()
            self.assertIn("no transcript", serialized)
            self.assertNotIn("deepseek_api_key", serialized)
            self.assertFalse(job["current_phase_locks"]["t1_natural_capture_authorized"])

    def test_prediction_contract_accepts_only_exact_schema(self):
        value = {
            "job_id": "privacy-and-governance",
            "verdict": "needs_revision",
            "fatal_issues": [],
            "major_issues": ["Missing erasure implementation."],
            "minor_issues": [],
            "missing_privacy_controls": ["Erasure receipt."],
            "missing_causal_controls": [],
            "accepted_t0_claims": ["Synthetic joins were tested."],
            "claims_not_supported": ["T1 readiness."],
            "required_repairs_before_t1": ["Implement erasure receipt."],
            "next_test": "Run a synthetic erasure fixture.",
            "confidence": 0.8,
        }
        self.assertEqual(MODULE.validate_prediction(value, value["job_id"]), value)
        broken = dict(value)
        broken["unexpected"] = True
        with self.assertRaises(ValueError):
            MODULE.validate_prediction(broken, value["job_id"])


if __name__ == "__main__":
    unittest.main()
