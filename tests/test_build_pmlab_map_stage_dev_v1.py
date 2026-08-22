import importlib.util
import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("stage_builder", ROOT / "scripts" / "build_pmlab_map_stage_dev_v1.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class PmlabMapStageDevBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = MODULE.build_outputs()
        cls.cases = [json.loads(line) for line in cls.outputs[MODULE.DATA_DIR / "cases.jsonl"].splitlines()]
        cls.model_cases = [json.loads(line) for line in cls.outputs[MODULE.DATA_DIR / "model-cases.jsonl"].splitlines()]
        cls.review = [json.loads(line) for line in cls.outputs[MODULE.DATA_DIR / "independent-review-queue.jsonl"].splitlines()]
        cls.manifest = json.loads(cls.outputs[MODULE.DATA_DIR / "manifest.json"])

    def test_first_tranche_has_22_bilingual_groups(self):
        groups = defaultdict(set)
        for case in self.cases:
            groups[case["semantic_group_id"]].add(case["language"])
        self.assertEqual(len(groups), 22)
        self.assertEqual(len(self.cases), 44)
        self.assertTrue(all(languages == {"en", "pl"} for languages in groups.values()))

    def test_model_and_review_payloads_do_not_leak_gold(self):
        forbidden = {"gold", "criticality", "split", "evaluation_metadata", "provenance"}
        for row in self.model_cases + self.review:
            self.assertFalse(forbidden & set(row))
        self.assertEqual({row["case_id"] for row in self.model_cases}, {row["case_id"] for row in self.review})

    def test_entity_gold_contains_all_typed_unresolved_strata(self):
        actions = Counter(case["gold"].get("action") for case in self.cases if case["stage"] == "entity_linking")
        self.assertEqual(actions["ambiguous_in_catalog"], 6)
        self.assertEqual(actions["missing_entity"], 6)
        self.assertEqual(actions["non_entity_phrase"], 6)
        self.assertEqual(actions["linked"], 10)

    def test_contract_labels_are_recomputed_not_trusted(self):
        catalog = json.loads(MODULE.CATALOG_PATH.read_text(encoding="utf-8"))
        ids = MODULE.catalog_ids(catalog)
        groups = MODULE.read_jsonl(MODULE.SOURCE_PATH)
        for group in groups:
            if group["stage"] == "contract_span":
                for variant in group["variants"].values():
                    self.assertEqual(MODULE.contract_decision(variant, ids), group["gold"])

    def test_manifest_records_unreviewed_and_no_candidates(self):
        self.assertEqual(self.manifest["review_status"], "not-reviewed")
        self.assertTrue(self.manifest["leakage_checks"]["candidate_outputs_absent"])
        self.assertIn("independent label review not completed", self.manifest["blockers"])


if __name__ == "__main__":
    unittest.main()
