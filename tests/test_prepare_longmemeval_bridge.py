import importlib.util
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("bridge", ROOT / "scripts" / "prepare_longmemeval_bridge.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def fixture():
    rows = []
    for question_type in MODULE.QUESTION_TYPES:
        for i in range(7):
            rows.append({
                "question_id": f"{question_type}-{i}", "question_type": question_type,
                "haystack_sessions": [[{"role": "user", "content": "x", "has_answer": True}]],
                "answer_session_ids": ["evidence"],
            })
    for question_type, count in MODULE.ABSTENTION_QUOTAS.items():
        for i in range(count + 2):
            rows.append({
                "question_id": f"abs-{question_type}-{i}_abs", "question_type": question_type,
                "haystack_sessions": [[{"role": "user", "content": "distractor"}]],
                "answer_session_ids": ["phantom_abs"],
            })
    return rows


class LongMemEvalBridgeTests(unittest.TestCase):
    def test_selection_is_deterministic_and_balanced(self):
        first = MODULE.public_selection(fixture())
        second = MODULE.public_selection(list(reversed(fixture())))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 36)
        self.assertEqual(Counter(row["answerable"] for row in first), Counter({True: 30, False: 6}))
        self.assertTrue(all(sum(row["question_type"] == kind and row["answerable"] for row in first) == 5 for kind in MODULE.QUESTION_TYPES))
        bases = {row["question_id"] for row in first if row["answerable"]}
        self.assertFalse(bases & {row["question_id"].removesuffix("_abs") for row in first if not row["answerable"]})

    def test_abstention_has_no_retrieval_gold(self):
        rows = MODULE.public_selection(fixture())
        abstentions = [row for row in rows if not row["answerable"]]
        self.assertTrue(all(row["retrieval_gold_defined"] is False for row in abstentions))
        self.assertTrue(all(row["gold_evidence_session_count"] is None and row["gold_evidence_turn_count"] is None for row in abstentions))
        self.assertTrue(all(row["near_miss_session_count"] == 1 for row in abstentions))


if __name__ == "__main__":
    unittest.main()
