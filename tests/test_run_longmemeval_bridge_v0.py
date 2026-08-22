import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("bridge_runner", ROOT / "scripts" / "run_longmemeval_bridge_v0.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class LongMemEvalBridgeRunnerTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "question_id": "q1",
            "question_type": "multi-session",
            "haystack_session_ids": ["raw-a", "raw-b"],
            "haystack_sessions": [
                [{"role": "user", "content": "alpha"}, {"role": "assistant", "content": "beta", "has_answer": True}],
                [{"role": "user", "content": "gamma"}],
            ],
            "answer_session_ids": ["raw-a"],
        }

    def test_adapter_indexes_only_role_and_content(self):
        records, mapping, gold, near_miss = MODULE.adapt(self.source)
        self.assertEqual(mapping, {"raw-a": "S000", "raw-b": "S001"})
        self.assertEqual(records[0], {"evidence_id": "S000", "title": "", "body": "user: alpha\nassistant: beta"})
        self.assertEqual(gold, {"S000"})
        self.assertEqual(near_miss, set())
        self.assertNotIn("has_answer", records[0]["body"])
        self.assertNotIn("raw-a", records[0]["body"])

    def test_abstention_maps_labels_only_to_near_miss(self):
        self.source["question_id"] = "q1_abs"
        _, _, gold, near_miss = MODULE.adapt(self.source)
        self.assertEqual(gold, set())
        self.assertEqual(near_miss, {"S000"})

    def test_score_is_content_free(self):
        records, _, gold, near_miss = MODULE.adapt(self.source)
        row = MODULE.score_case(self.source, records, "B2-sqlite-fts5", ["S000"], gold, near_miss, 1.0, 2.0, 3, None)
        self.assertEqual(row["recall_at_5"], 1.0)
        self.assertNotIn("retrieved", row)
        self.assertNotIn("gold", row)
        self.assertNotIn("question", row)

    def test_oracle_is_empty_without_positive_gold(self):
        self.assertEqual(MODULE.Oracle(set()).retrieve("hidden", 5), [])


if __name__ == "__main__":
    unittest.main()
