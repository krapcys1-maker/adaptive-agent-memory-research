import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("reviewer", ROOT / "scripts" / "run_deepseek_memory_reviewer.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class DeepSeekMemoryReviewerTests(unittest.TestCase):
    def test_jobs_are_content_bounded_and_cover_three_roles(self):
        jobs = MODULE.build_jobs()
        self.assertEqual({row["job_id"] for row in jobs}, {"protocol-integrity", "statistics-and-constructs", "architecture-and-next-gate"})
        serialized = str(jobs)
        self.assertNotIn("haystack_sessions", serialized)
        self.assertNotIn("DEEPSEEK_API_KEY", serialized)

    def test_prediction_schema_is_exact(self):
        value = {
            "job_id": "protocol-integrity", "verdict": "needs_revision", "fatal_issues": [],
            "major_issues": ["x"], "minor_issues": [], "claims_supported": [], "claims_not_supported": ["y"],
            "required_claim_boundary": "exploratory only", "next_required_test": "cross-family test", "confidence": 0.7,
        }
        self.assertEqual(MODULE.validate_prediction(value, "protocol-integrity"), value)
        value["extra"] = True
        with self.assertRaises(ValueError):
            MODULE.validate_prediction(value, "protocol-integrity")


if __name__ == "__main__":
    unittest.main()
