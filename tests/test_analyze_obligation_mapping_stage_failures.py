import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("stage_analysis", ROOT / "scripts" / "analyze_obligation_mapping_stage_failures.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ObligationMappingStageAnalysisTests(unittest.TestCase):
    def test_every_case_arm_receives_one_first_failure(self):
        outputs = MODULE.build_outputs()
        rows = [json.loads(line) for line in outputs[MODULE.OUTPUT_DIR / "rows.jsonl"].splitlines()]
        self.assertEqual(len(rows), 56)
        self.assertEqual(len({(row["arm"], row["query_id"]) for row in rows}), 56)
        self.assertTrue(all(row["first_failure"] for row in rows))

    def test_analysis_is_explicitly_posthoc(self):
        outputs = MODULE.build_outputs()
        manifest = json.loads(outputs[MODULE.OUTPUT_DIR / "manifest.json"])
        self.assertEqual(manifest["status"], "post-hoc-spent-challenge-diagnostic")
        self.assertIn("post-hoc", manifest["limitations"])


if __name__ == "__main__":
    unittest.main()
