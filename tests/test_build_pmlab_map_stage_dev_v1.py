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

    def test_base_plus_supplement_has_77_bilingual_groups(self):
        groups = defaultdict(set)
        for case in self.cases:
            groups[case["semantic_group_id"]].add(case["language"])
        self.assertEqual(len(groups), 77)
        self.assertEqual(len(self.cases), 154)
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
        groups = [group for path in MODULE.SOURCE_PATHS for group in MODULE.read_jsonl(path)]
        for group in groups:
            if group["stage"] == "contract_span":
                for variant in group["variants"].values():
                    self.assertEqual(MODULE.contract_decision(variant, ids), group["gold"])

    def test_graph_and_predicate_allocations(self):
        groups = defaultdict(set)
        for case in self.cases:
            groups[case["stage"]].add(case["semantic_group_id"])
        self.assertEqual(16, len(groups["obligation_graph"]))
        self.assertEqual(14, len(groups["predicate_linking"]))

    def test_graph_gold_uses_language_specific_exact_spans(self):
        for case in self.cases:
            if case["stage"] != "obligation_graph":
                continue
            previous = []
            for index, node in enumerate(case["gold"]["nodes"], start=1):
                self.assertEqual(f"O{index}", node["obligation_id"])
                self.assertIn(node["source_span"], case["input"]["raw_query"])
                self.assertTrue(all(dependency in previous for dependency in node["depends"]))
                previous.append(node["obligation_id"])

    def test_predicate_gold_has_link_ambiguity_and_unsupported(self):
        actions = Counter(case["gold"].get("action") for case in self.cases if case["stage"] == "predicate_linking")
        self.assertEqual({"linked", "ambiguous_schema", "unsupported_predicate"}, set(actions))
        self.assertEqual(18, actions["linked"])
        self.assertEqual(6, actions["ambiguous_schema"])
        self.assertEqual(4, actions["unsupported_predicate"])

    def test_time_and_certificate_base_plus_supplement_counts(self):
        groups = defaultdict(set)
        for case in self.cases:
            groups[case["stage"]].add(case["semantic_group_id"])
        self.assertEqual(11, len(groups["time_authorization"]))
        self.assertEqual(12, len(groups["certificate_routing"]))

    def test_time_labels_preserve_all_resolution_and_access_states(self):
        time_statuses = {case["gold"]["time_status"] for case in self.cases if case["stage"] == "time_authorization"}
        authorization = {case["gold"]["authorization_status"] for case in self.cases if case["stage"] == "time_authorization"}
        self.assertEqual({"resolved", "ambiguous", "unbounded", "unsupported", "inherited"}, time_statuses)
        self.assertEqual({"allowed", "denied", "partial", "inherited"}, authorization)

    def test_certificate_labels_cover_safe_negative_boundaries(self):
        statuses = {case["gold"]["certificate_status"] for case in self.cases if case["stage"] == "certificate_routing"}
        self.assertEqual(
            {"applicable", "derived", "explicit_negative", "requires_complete_scope", "ambiguous", "inapplicable"},
            statuses,
        )
        inserted = [
            case
            for case in self.cases
            if case["stage"] == "certificate_routing"
            and case["input"].get("insertion", {}).get("matches_scope")
        ]
        self.assertTrue(inserted)
        self.assertTrue(all(case["gold"]["certificate_status"] == "inapplicable" for case in inserted))

    def test_supplement_closes_exercisable_declared_label_gaps(self):
        self.assertEqual(72, self.manifest["base_allocation_semantic_group_count"])
        self.assertEqual(5, self.manifest["supplemental_coverage_semantic_group_count"])
        self.assertEqual({}, self.manifest["unresolved_coverage_gaps"])
        self.assertEqual(
            {"obligation_graph.query_status": ["unauthorized"]},
            self.manifest["uncovered_declared_labels"],
        )
        self.assertIn(
            "obligation_graph.query_status=unauthorized",
            self.manifest["non_exercisable_declared_labels"],
        )

    def test_certificate_actions_include_partial_and_abstain(self):
        actions = {case["gold"]["action"] for case in self.cases if case["stage"] == "certificate_routing"}
        self.assertEqual({"answer", "continue_search", "clarify", "partial_with_gap", "abstain"}, actions)

    def test_manifest_records_unreviewed_and_no_candidates(self):
        self.assertEqual(self.manifest["review_status"], "not-reviewed")
        self.assertTrue(self.manifest["leakage_checks"]["candidate_outputs_absent"])
        self.assertIn("independent label review not completed", self.manifest["blockers"])


if __name__ == "__main__":
    unittest.main()
