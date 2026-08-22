from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import screen_literature


class LiteratureScreeningTests(unittest.TestCase):
    def test_env_loader_reads_only_requested_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OTHER=value\nDEEPSEEK_API_KEY='secret-test-value'\n", encoding="utf-8")
            self.assertEqual("secret-test-value", screen_literature.load_env_value(path, "DEEPSEEK_API_KEY"))

    def test_conservative_cost_uses_peak_cache_miss_assumption(self) -> None:
        self.assertEqual(1.76, screen_literature.conservative_cost(1_000_000, 1_000_000))

    def test_schema_validation_requires_exact_job_ids(self) -> None:
        jobs = [{"job_id": "A"}, {"job_id": "B"}]
        valid = json.dumps(
            {
                "results": [
                    {"job_id": "A", "decision": "include", "relevance": 3},
                    {"job_id": "B", "decision": "exclude", "relevance": 0},
                ]
            }
        )
        self.assertEqual(2, len(screen_literature.validate_results(valid, jobs)))
        invalid = json.dumps({"results": [{"job_id": "A", "decision": "include", "relevance": 3}]})
        with self.assertRaises(ValueError):
            screen_literature.validate_results(invalid, jobs)

    def test_budget_above_user_cap_is_rejected_before_api_access(self) -> None:
        with self.assertRaises(ValueError):
            screen_literature.run("missing", Path("missing.env"), 10.01, 5, 1800, 1)

    def test_missing_abstract_include_is_downgraded_deterministically(self) -> None:
        candidate = {"job_id": "A", "decision": "include", "relevance": 3}
        normalized = screen_literature.apply_deterministic_policy(candidate, {"abstract": ""})
        self.assertEqual("maybe", normalized["decision"])
        self.assertEqual(2, normalized["relevance"])
        self.assertEqual(["missing-abstract-cannot-include"], normalized["policy_overrides"])
        self.assertEqual("include", normalized["model_decision"])


if __name__ == "__main__":
    unittest.main()
