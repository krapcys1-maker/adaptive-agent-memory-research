import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_challenge", ROOT / "scripts" / "run_obligation_mapping_challenge.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ObligationMappingChallengeRunnerTests(unittest.TestCase):
    def test_harness_names_both_freeze_commits(self):
        outputs = MODULE.build_outputs()
        manifest = json.loads(outputs[MODULE.ARTIFACTS_DIR / "manifest.json"])
        self.assertEqual(manifest["challenge_freeze_commit"], "adc540f")
        self.assertEqual(manifest["prediction_runner_freeze_commit"], "6a82bd8")

    def test_gold_oracle_checks_scorer_contract(self):
        outputs = MODULE.build_outputs()
        summary = json.loads(outputs[MODULE.ARTIFACTS_DIR / "summary.json"])
        self.assertEqual(summary["gold_oracle"]["end_to_end_exact_rate"], 1.0)
        self.assertEqual(summary["gold_oracle"]["false_closure_count"], 0)


if __name__ == "__main__":
    unittest.main()
