from __future__ import annotations

import unittest

from scripts import run_forgetting_benchmark as benchmark


class ForgettingBenchmarkTests(unittest.TestCase):
    def test_all_authored_single_fault_cases_localize(self) -> None:
        cases = benchmark.make_fault_cases()
        self.assertEqual(28, len(cases))
        for case in cases:
            self.assertEqual(case["expected_label"], benchmark.localize_fault(case["probes"]))

    def test_intact_canonical_record_is_not_storage_loss(self) -> None:
        probes = benchmark._healthy_probes()
        probes["gold_retrieved"] = False
        probes["gold_in_context"] = False
        self.assertEqual("F2", benchmark.localize_fault(probes))

    def test_f1_stage_need_not_mean_physical_data_loss(self) -> None:
        cases = benchmark.make_fault_cases()
        recoverable_f1 = [
            case
            for case in cases
            if case["expected_label"] == "F1" and case["probes"]["canonical_bytes_recoverable"]
        ]
        self.assertEqual(2, len(recoverable_f1))
        self.assertTrue(all(not case["expected_data_loss"] for case in recoverable_f1))

    def test_f2_ids_and_labels_are_consistent(self) -> None:
        corpus = benchmark.make_interference_corpus()
        queries = benchmark.make_interference_queries()
        benchmark.validate_interference(corpus, queries)
        self.assertEqual(256, len(corpus))
        self.assertEqual(56, len(queries))

    def test_entity_time_ceiling_selects_requested_version(self) -> None:
        corpus = [row for row in benchmark.make_interference_corpus() if row["version"] <= 8]
        query = next(
            row
            for row in benchmark.make_interference_queries()
            if row["history_id"] == "atlas-access"
            and row["update_count"] == 8
            and row["query_type"] == "historical-as-of"
        )
        retrieved = benchmark.RuleEntityTimeRetriever(corpus).retrieve(query, 5)
        self.assertEqual(query["gold_evidence_ids"], retrieved)

    def test_rule_entity_time_does_not_read_gold_metadata(self) -> None:
        corpus = [row for row in benchmark.make_interference_corpus() if row["version"] <= 4]
        query = {
            "query": "What is the current access code for Atlas?",
            "history_id": "deliberately-wrong",
            "as_of_version": 1,
            "gold_evidence_ids": [benchmark.evidence_id("atlas-access", 4)],
            "forbidden_stale_ids": [],
        }
        self.assertEqual(
            query["gold_evidence_ids"], benchmark.RuleEntityTimeRetriever(corpus).retrieve(query, 5)
        )

    def test_normalized_auc(self) -> None:
        self.assertEqual(1.0, benchmark.normalized_auc({1: 1.0, 2: 1.0, 4: 1.0}))
        self.assertEqual(0.5, benchmark.normalized_auc({1: 1.0, 2: 0.5, 4: 0.0}))


if __name__ == "__main__":
    unittest.main()
