import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("challenge", ROOT / "scripts" / "build_obligation_mapping_challenge.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ObligationMappingChallengeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = ROOT / "data" / "lab" / "pmlab-obligation-mapping-challenge-v0"
        cls.cases = [json.loads(line) for line in (cls.data / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
        cls.manifest = json.loads((cls.data / "manifest.json").read_text(encoding="utf-8"))

    def test_semantic_groups_remain_bilingual_pairs(self):
        groups = {}
        for case in self.cases:
            groups.setdefault(case["evaluation_metadata"]["semantic_template_group"], set()).add(case["language"])
        self.assertEqual(len(groups), 14)
        self.assertTrue(all(languages == {"en", "pl"} for languages in groups.values()))

    def test_schema_ids_are_disjoint_from_construction(self):
        self.assertTrue(self.manifest["unseen_schema"]["all_ids_disjoint_from_construction"])

    def test_challenge_was_authored_after_arm_freezes(self):
        self.assertEqual(self.manifest["deterministic_runner_freeze_commit"], "6a82bd8")
        self.assertEqual(self.manifest["optional_model_prompt_freeze_commit"], "6a288f6")
        self.assertEqual(self.manifest["optional_model_adapter_freeze_commit"], "8913667")

    def test_critical_unresolved_cases_never_have_applicable_certificate(self):
        forbidden = {"applicable", "explicit-negative", "requires-complete-scope"}
        for case in self.cases:
            if case["evaluation_metadata"]["criticality"] == "critical" and case["query_status"] != "resolved":
                self.assertFalse(any(node["certificate_query"]["status"] in forbidden for node in case["graph"]["nodes"]))


if __name__ == "__main__":
    unittest.main()
