from __future__ import annotations

import json
import unittest

from scripts import review_forgetting_benchmark as review


class ReviewForgettingBenchmarkTests(unittest.TestCase):
    def test_jobs_cover_f1_f2_and_next_gate(self) -> None:
        job_ids = {job["job_id"] for job in review.build_jobs()}
        self.assertEqual(
            {"F1-STAGE-VS-LOSS", "F1-INTERNAL-VALIDITY", "F2-BASELINE-FAIRNESS", "F2-CURVE-VALIDITY", "NEXT-GATE"},
            job_ids,
        )

    def test_validation_rejects_missing_job(self) -> None:
        jobs = [{"job_id": "A"}, {"job_id": "B"}]
        content = json.dumps({"results": [{"job_id": "A", "severity": "low", "findings": []}]})
        with self.assertRaises(ValueError):
            review.validate(content, jobs)

    def test_validation_accepts_exact_schema_boundary(self) -> None:
        jobs = [{"job_id": "A"}]
        content = json.dumps(
            {
                "results": [
                    {
                        "job_id": "A",
                        "severity": "medium",
                        "findings": [],
                        "minimum_next_action": "add blind cases",
                        "do_not_conclude": "validated architecture",
                    }
                ]
            }
        )
        self.assertEqual("A", review.validate(content, jobs)[0]["job_id"])


if __name__ == "__main__":
    unittest.main()
