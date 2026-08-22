import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("builder_v01", ROOT / "scripts" / "build_project_memory_lab_v01.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def rows(data: bytes):
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]


class ProjectMemoryLabV01BuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = MODULE.build_outputs()
        cls.old_labels = [json.loads(line) for line in (MODULE.SOURCE / "internal" / "author-labels.jsonl").read_text(encoding="utf-8").splitlines()]
        cls.new_labels = rows(cls.outputs[MODULE.OUT / "internal" / "author-labels.jsonl"])

    def test_corpus_is_byte_identical_to_invalidated_parent(self):
        parent = (MODULE.SOURCE / "corpus.jsonl").read_bytes()
        self.assertEqual(self.outputs[MODULE.OUT / "corpus.jsonl"], parent)
        self.assertEqual(self.outputs[MODULE.OUT / "blind" / "corpus.jsonl"], parent)

    def test_every_test_query_and_no_development_query_changed(self):
        pairs = list(zip(self.old_labels, self.new_labels, strict=True))
        self.assertEqual(sum(a["query"] != b["query"] for a, b in pairs if a["split"] == "test"), 60)
        self.assertEqual(sum(a["query"] != b["query"] for a, b in pairs if a["split"] == "development"), 0)

    def test_only_query_field_changed(self):
        for old, new in zip(self.old_labels, self.new_labels, strict=True):
            old_without_query = {key: value for key, value in old.items() if key != "query"}
            new_without_query = {key: value for key, value in new.items() if key != "query"}
            self.assertEqual(old_without_query, new_without_query)

    def test_rewrite_map_exactly_covers_test(self):
        test_ids = {row["example_id"] for row in self.old_labels if row["split"] == "test"}
        self.assertEqual(test_ids, set(MODULE.TEST_REWRITES))

    def test_blind_packet_stays_blind_and_locked(self):
        blind = rows(self.outputs[MODULE.OUT / "blind" / "queries.jsonl"])
        forbidden = {"history_id", "answerable", "gold_evidence_ids", "gold_current_ids", "forbidden_stale_ids"}
        self.assertEqual(len(blind), 120)
        self.assertTrue(all(not forbidden.intersection(row) for row in blind))
        manifest = json.loads(self.outputs[MODULE.OUT / "manifest.json"])
        self.assertFalse(manifest["author_labels_are_gold"])
        self.assertFalse(manifest["baseline_run_permitted"])

    def test_attestation_binds_new_query_hash(self):
        queries = self.outputs[MODULE.OUT / "blind" / "queries.jsonl"]
        attestation = json.loads(self.outputs[MODULE.OUT / "blind" / "attestation-a.json"])
        self.assertEqual(attestation["blind_queries_sha256"], hashlib.sha256(queries).hexdigest())

    def test_builder_is_deterministic(self):
        self.assertEqual(self.outputs, MODULE.build_outputs())


if __name__ == "__main__":
    unittest.main()
