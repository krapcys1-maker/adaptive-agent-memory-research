from __future__ import annotations

import unittest

from scripts import run_forgetting_challenge as challenge
from scripts import run_query_scope_factorial as factorial


class QueryScopeFactorialTests(unittest.TestCase):
    def test_normalized_text_uses_registered_target_metadata(self) -> None:
        corpus = challenge.make_f2_corpus()
        records = {row["evidence_id"]: row for row in corpus}
        query = next(row for row in challenge.make_f2_queries() if row["example_id"] == "vela-threshold-relative")
        text = factorial.normalized_text(query, records)
        target = records[query["gold_evidence_ids"][0]]
        self.assertIn(target["entity"], text)
        self.assertIn(target["valid_from"], text)

    def test_history_scope_never_contains_another_history(self) -> None:
        corpus = challenge.make_f2_corpus()
        query = next(row for row in challenge.make_f2_queries() if row["answerable"])
        scoped = factorial.scoped_records(query, corpus, True)
        self.assertTrue(scoped)
        self.assertEqual({query["history_id"]}, {row["history_id"] for row in scoped})

    def test_unanswerable_query_cannot_receive_oracle_history(self) -> None:
        corpus = challenge.make_f2_corpus()
        query = next(row for row in challenge.make_f2_queries() if not row["answerable"])
        self.assertEqual(corpus, factorial.scoped_records(query, corpus, True))


if __name__ == "__main__":
    unittest.main()
