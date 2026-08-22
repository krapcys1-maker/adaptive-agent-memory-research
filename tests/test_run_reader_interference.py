from __future__ import annotations
import json, unittest
from scripts import run_reader_interference as reader

class ReaderInterferenceTests(unittest.TestCase):
    def test_balanced_conditions(self):
        cases=reader.make_cases()
        self.assertEqual(40,len(cases))
        self.assertEqual({condition:8 for condition in reader.CONDITIONS},{condition:sum(case["condition"]==condition for case in cases) for condition in reader.CONDITIONS})
    def test_stale_only_requires_abstention(self):
        self.assertTrue(all(case["expected_abstain"] for case in reader.make_cases() if case["condition"]=="stale-only"))
    def test_schema_validation_requires_all_ids(self):
        cases=[{"case_id":"A"},{"case_id":"B"}]
        with self.assertRaises(ValueError): reader.validate(json.dumps({"results":[{"case_id":"A","abstain":False}]}),cases)
    def test_model_payload_excludes_gold_labels(self):
        item=reader.model_item(reader.make_cases()[0]); serialized=json.dumps(item)
        self.assertNotIn("expected_",serialized)

if __name__=="__main__": unittest.main()
