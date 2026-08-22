import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "review_pmlab_map_stage_deepseek",
    ROOT / "scripts" / "review_pmlab_map_stage_deepseek.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class BlindReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1" / "independent-review-queue.jsonl"
        cls.queue = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        cls.jobs = MODULE.build_jobs(cls.queue)

    def test_builds_all_paired_groups(self):
        self.assertEqual(22, len(self.jobs))
        self.assertTrue(all(len(job["cases"]) == 2 for job in self.jobs))

    def test_jobs_do_not_copy_empty_review_fields(self):
        encoded = json.dumps(self.jobs, ensure_ascii=False)
        self.assertNotIn("review_fields", encoded)
        for forbidden in ("gold", "criticality", "stratum", "provenance", "evaluation_metadata"):
            self.assertNotIn(f'"{forbidden}"', encoded)

    def test_validate_contract_and_entity_labels(self):
        catalog_ids = {"vendor:cobalt"}
        contract = self.jobs[0]["cases"][0]
        entity = next(job for job in self.jobs if job["stage"] == "entity_linking")["cases"][0]
        base = {"confidence": "high", "case_validity": "valid", "disputed_field": None, "rationale": "visible evidence"}
        MODULE.validate_label({**base, "case_id": contract["case_id"], "independent_label": {"decision": "accept", "reject_reason": "none"}}, contract, catalog_ids)
        MODULE.validate_label({**base, "case_id": entity["case_id"], "independent_label": {"action": "linked", "candidate_ids": ["vendor:cobalt"], "selected_id": "vendor:cobalt", "selected_ids": []}}, entity, catalog_ids)


if __name__ == "__main__":
    unittest.main()
