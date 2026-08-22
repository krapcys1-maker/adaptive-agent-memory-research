import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("audit", ROOT / "scripts" / "audit_pmlab_split_leakage.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class SplitLeakageAuditTests(unittest.TestCase):
    def test_frozen_v0_is_detected_as_template_leaky_without_labels(self):
        rows = MODULE.read_jsonl(MODULE.SOURCE)
        pairs, summary = MODULE.audit(rows)
        self.assertEqual(len(pairs), 300)
        self.assertGreater(summary["flagged_pairs"], 0)
        self.assertIn("causal_multi_episode", summary["flagged_categories"])
        self.assertFalse(summary["labels_read"])
        self.assertFalse(summary["backend_output_read"])
        self.assertIn("reject v0 split", summary["decision"])

    def test_clean_candidate_is_not_automatically_called_independent(self):
        rows = [
            {"example_id": "D", "category": "x", "split": "development", "query": "Where is the cobalt tool stored?"},
            {"example_id": "T", "category": "x", "split": "test", "query": "Return the assigned location for the bronze instrument."},
        ]
        _, summary = MODULE.audit(rows, "test fixture")
        self.assertEqual(summary["flagged_pairs"], 0)
        self.assertIn("independent leakage audit remain required", summary["decision"])


if __name__ == "__main__":
    unittest.main()
