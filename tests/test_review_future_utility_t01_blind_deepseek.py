import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("utility_blind_review", ROOT / "scripts" / "review_future_utility_t01_blind_deepseek.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FutureUtilityBlindDeepSeekReviewTests(unittest.TestCase):
    def test_job_is_bounded_to_public_blind_packet(self):
        job = MODULE.build_job()
        self.assertEqual("PMLAB-UTILITY-001-T0.1-blind-audit", job["job_id"])
        self.assertIn("no conversation", job["data_boundary"].lower())
        self.assertEqual(7, len(job["artifacts"]))
        self.assertNotIn("future-utility-causal-privacy-primary-source-audit", " ".join(job["artifacts"]))

    def test_exact_result_contract(self):
        findings = []
        for index in range(1, 11):
            findings.append({
                "question_id": f"A{index:02d}", "verdict": "conditional", "severity": "major",
                "evidence_locators": ["subject artifact: field"], "rationale": "Evidence is incomplete.",
                "required_change": "Add and test the missing control.",
            })
        value = {
            "findings": findings,
            "gate_recommendations": {"T1": "conditional", "T2": "deny", "T3": "deny", "T4": "deny"},
            "blocking_findings": [],
            "residual_risks": ["Model review can be wrong."],
            "overall_rationale": "Further evidence is required.",
        }
        self.assertEqual(value, MODULE.validate_result(value))
        broken = {**value, "unexpected": True}
        with self.assertRaises(ValueError):
            MODULE.validate_result(broken)


if __name__ == "__main__":
    unittest.main()

