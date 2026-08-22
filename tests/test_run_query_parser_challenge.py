from __future__ import annotations

import unittest

from scripts import run_query_parser_challenge as challenge
from scripts.run_forgetting_challenge import make_f2_corpus


class QueryParserChallengeTests(unittest.TestCase):
    def test_challenge_is_balanced_and_ids_are_unique(self) -> None:
        cases = challenge.challenge_cases()
        self.assertEqual(28, len(cases))
        self.assertEqual(28, len({case["case_id"] for case in cases}))
        self.assertGreaterEqual(sum(case["answerable"] for case in cases), 20)
        self.assertGreaterEqual(sum(not case["answerable"] for case in cases), 7)

    def test_every_answerable_target_exists_in_corpus(self) -> None:
        known = {(row["history_id"], row["valid_from"]) for row in make_f2_corpus()}
        for case in challenge.challenge_cases():
            if case["answerable"]:
                self.assertIn((case["expected_history_id"], case["expected_target_date"]), known)

    def test_parser_commit_is_frozen(self) -> None:
        self.assertEqual("1a43b7a", challenge.PARSER_FROZEN_COMMIT)


if __name__ == "__main__":
    unittest.main()
