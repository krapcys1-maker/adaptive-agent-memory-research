from __future__ import annotations

import unittest

from scripts import run_forgetting_challenge as challenge


class ForgettingChallengeTests(unittest.TestCase):
    def test_multi_fault_and_unknown_sets_are_preserved(self) -> None:
        cases = challenge.make_f1_challenges()
        self.assertGreaterEqual(sum(len(case["expected_faults"]) > 1 for case in cases), 6)
        self.assertGreaterEqual(sum(bool(case["expected_unknown_stages"]) for case in cases), 6)
        for case in cases:
            diagnosis = challenge.diagnose_fault_set(case["probes"])
            self.assertEqual(case["expected_faults"], diagnosis["known_faults"])
            self.assertEqual(case["expected_unknown_stages"], diagnosis["unknown_stages"])
            self.assertEqual(case["expected_data_loss"], diagnosis["data_loss_diagnosed"])

    def test_challenge_entities_do_not_overlap_development(self) -> None:
        development = {"Atlas", "Helios", "Mira", "Quartz"}
        challenge_entities = {row[1] for row in challenge.HISTORIES}
        self.assertFalse(development & challenge_entities)

    def test_duplicate_surface_names_exist(self) -> None:
        entities = [row[1] for row in challenge.HISTORIES]
        self.assertGreater(entities.count("Mercury"), 1)
        self.assertGreater(entities.count("Jordan"), 1)

    def test_query_contract_is_valid(self) -> None:
        corpus = challenge.make_f2_corpus()
        queries = challenge.make_f2_queries()
        challenge.validate_f2(corpus, queries)
        self.assertEqual(154, len(corpus))
        self.assertEqual(24, len(queries))
        self.assertEqual(4, sum(not query["answerable"] for query in queries))


if __name__ == "__main__":
    unittest.main()
