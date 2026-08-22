import importlib.util
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("builder", ROOT / "scripts" / "build_project_memory_lab_v0.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProjectMemoryLabBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = MODULE.build_outputs()
        cls.labels = [json.loads(line) for line in cls.outputs[MODULE.OUT / "internal" / "author-labels.jsonl"].splitlines()]
        cls.blind = [json.loads(line) for line in cls.outputs[MODULE.OUT / "blind" / "queries.jsonl"].splitlines()]

    def test_has_ten_cases_per_stratum_and_balanced_splits(self):
        self.assertEqual(len(self.labels), 120)
        self.assertEqual(Counter(row["category"] for row in self.labels), Counter({name: 10 for name in MODULE.CATEGORIES}))
        self.assertEqual(Counter(row["split"] for row in self.labels), Counter({"development": 60, "test": 60}))

    def test_histories_do_not_cross_splits(self):
        dev = {row["history_id"] for row in self.labels if row["split"] == "development"}
        test = {row["history_id"] for row in self.labels if row["split"] == "test"}
        self.assertFalse(dev & test)

    def test_queries_are_not_exact_template_duplicates(self):
        normalized = [row["query"].casefold().strip() for row in self.labels]
        self.assertEqual(len(normalized), len(set(normalized)))

    def test_blind_queries_exclude_labels(self):
        forbidden = {"history_id", "answerable", "gold_evidence_ids", "gold_current_ids", "forbidden_stale_ids"}
        self.assertEqual(len(self.blind), 120)
        self.assertTrue(all(not forbidden.intersection(row) for row in self.blind))

    def test_output_identifiers_are_opaque(self):
        records = [json.loads(line) for line in self.outputs[MODULE.OUT / "corpus.jsonl"].splitlines()]
        self.assertTrue(all(row["evidence_id"].startswith("E-") and len(row["evidence_id"]) == 14 for row in records))
        self.assertTrue(all(row["history_id"].startswith("H-") and len(row["history_id"]) == 14 for row in records))

    def test_manifest_keeps_baseline_locked(self):
        manifest = json.loads(self.outputs[MODULE.OUT / "manifest.json"])
        self.assertFalse(manifest["author_labels_are_gold"])
        self.assertFalse(manifest["baseline_run_permitted"])
        self.assertEqual(manifest["families"], {"controlled_synthetic": 96, "project_research": 24})
        self.assertEqual(manifest["corpus_freeze_commit"], "612eb06")
        self.assertEqual(manifest["status"], "invalidated-pre-run-template-leakage")

    def test_builder_is_deterministic(self):
        self.assertEqual(self.outputs, MODULE.build_outputs())


if __name__ == "__main__":
    unittest.main()
