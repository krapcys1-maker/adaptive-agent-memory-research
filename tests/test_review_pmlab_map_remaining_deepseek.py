import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("remaining_review", ROOT / "scripts" / "review_pmlab_map_remaining_deepseek.py")
MODULE = importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; SPEC.loader.exec_module(MODULE)

class RemainingReviewTests(unittest.TestCase):
    def test_partition_is_disjoint_and_complete(self):
        reviewed={row["case_id"] for row in MODULE.shared.read_jsonl(MODULE.FIRST_RUN_DIR/"predictions.jsonl")}
        queue=MODULE.shared.read_jsonl(MODULE.CORPUS_DIR/"independent-review-queue.jsonl")
        remaining=[row for row in queue if row["case_id"] not in reviewed]
        self.assertEqual(44,len(reviewed)); self.assertEqual(110,len(remaining)); self.assertFalse(reviewed & {row["case_id"] for row in remaining})

    def test_prompt_explicitly_separates_negative_fixture_from_case_quality(self):
        self.assertIn("valid negative fixtures", MODULE.SYSTEM_PROMPT)
        self.assertIn("Do not infer authorization", MODULE.SYSTEM_PROMPT)

if __name__ == "__main__": unittest.main()
