import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "data" / "lab" / "pmlab-v0-lexical-preregistration" / "manifest.json"
CONSTRUCTION = ROOT / "data" / "lab" / "project-memory-lab-v0-construction" / "manifest.json"


class LexicalPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.corpus = json.loads(CONSTRUCTION.read_text(encoding="utf-8"))

    def test_execution_is_locked_on_independent_gold(self):
        self.assertEqual(self.protocol["protocol_freeze_commit"], "e111a57")
        self.assertFalse(self.protocol["execution_authorized"])
        self.assertFalse(self.protocol["freeze_prerequisites_satisfied"]["dual_independent_labels"])
        self.assertIsNone(self.protocol["corpus"]["adjudicated_gold_sha256"])

    def test_protocol_points_to_frozen_corpus_bytes(self):
        self.assertEqual(self.protocol["corpus"]["construction_commit"], "612eb06")
        self.assertEqual(self.protocol["corpus"]["corpus_sha256"], self.corpus["hashes"]["corpus.jsonl"])
        self.assertEqual(self.protocol["corpus"]["blind_queries_sha256"], self.corpus["hashes"]["blind/queries.jsonl"])

    def test_retriever_cannot_see_labels_or_scope_metadata(self):
        visible = self.protocol["backend_input_boundary"]["visible"]
        hidden = self.protocol["backend_input_boundary"]["hidden"]
        self.assertEqual(visible, ["query text"])
        self.assertIn("gold evidence", hidden)
        self.assertIn("query time metadata outside query text", hidden)

    def test_unanswerable_is_not_mislabeled_as_retrieval_abstention(self):
        metrics = " ".join(self.protocol["secondary_metrics"])
        self.assertIn("not called abstention", metrics)
        self.assertIn("eleven answerable strata", self.protocol["primary_outcome"]["metric"])


if __name__ == "__main__":
    unittest.main()
