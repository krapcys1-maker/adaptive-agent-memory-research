import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_memory_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_memory_benchmark", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class MemoryBenchmarkTests(unittest.TestCase):
    def test_tokenization_is_deterministic_and_removes_stopwords(self):
        self.assertEqual(
            MODULE.query_tokens("What is the current CURRENT provider?"),
            ["current", "provider"],
        )

    def test_partial_multi_evidence_recall(self):
        query = {
            "answerable": True,
            "gold_evidence_ids": ["E1", "E2"],
            "forbidden_stale_ids": ["OLD"],
        }
        result = MODULE.score_query(query, ["E2", "OLD", "X"])
        self.assertEqual(result["recall_at_5"], 0.5)
        self.assertEqual(result["reciprocal_rank"], 1.0)
        self.assertTrue(result["forbidden_intrusion"])

    def test_unanswerable_requires_empty_retrieval(self):
        query = {"answerable": False, "gold_evidence_ids": [], "forbidden_stale_ids": []}
        self.assertTrue(MODULE.score_query(query, [])["abstained_correctly"])
        self.assertFalse(MODULE.score_query(query, ["E1"])["abstained_correctly"])

    @unittest.skipUnless(shutil.which("rg"), "ripgrep is not installed")
    def test_ripgrep_jsonl_parser_preserves_unicode_line_separator(self):
        records = [{"evidence_id": "E-1", "title": "", "body": "alpha\u2028beta"}]
        with tempfile.TemporaryDirectory() as temporary:
            backend = MODULE.RipgrepRetriever(records, Path(temporary) / "docs")
            self.assertEqual(backend.retrieve("alpha", 5), ["E-1"])


if __name__ == "__main__":
    unittest.main()
