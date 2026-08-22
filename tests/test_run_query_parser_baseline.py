from __future__ import annotations

import unittest

from scripts import run_query_parser_baseline as parser
from scripts.run_forgetting_challenge import make_f2_corpus


class QueryParserBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = parser.build_catalog(make_f2_corpus())

    def test_parser_requires_only_text_and_catalog(self) -> None:
        result = parser.parse_query("What is the current project channel for Mercury?", self.catalog)
        self.assertEqual("mercury-project", result["history_id"])
        self.assertEqual("parsed", result["status"])

    def test_natural_date_is_normalized(self) -> None:
        result = parser.parse_query("What was the Jordan station locker on January 7, 2026?", self.catalog)
        self.assertEqual("2026-01-07", result["target_date"])

    def test_iso_date_survives_text_normalization(self) -> None:
        result = parser.parse_query("What was the Aster access phrase on 2026-01-01?", self.catalog)
        self.assertEqual("2026-01-01", result["target_date"])

    def test_polish_relative_time_is_normalized(self) -> None:
        result = parser.parse_query("Jaka była incident owner dla Nimbus dwie zmiany przed najnowszą?", self.catalog)
        self.assertEqual("2026-01-09", result["target_date"])

    def test_ambiguous_entity_abstains(self) -> None:
        result = parser.parse_query("What is the current Mercury value?", self.catalog)
        self.assertEqual("abstain", result["status"])
        self.assertEqual("ambiguous-entity", result["reason"])

    def test_underspecified_old_time_abstains(self) -> None:
        result = parser.parse_query("What was the old Vela value?", self.catalog)
        self.assertEqual("abstain", result["status"])
        self.assertEqual("unresolved-time", result["reason"])


if __name__ == "__main__":
    unittest.main()
