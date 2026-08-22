from __future__ import annotations
import json, unittest
from scripts import run_reader_stress as stress

class ReaderStressTests(unittest.TestCase):
    def test_full_factorial(self):
        cases=stress.make_cases(); self.assertEqual(128,len(cases)); self.assertEqual(128,len({x["case_id"] for x in cases}))
    def test_underdetermined_cues_require_abstention(self):
        cases=stress.make_cases(); self.assertTrue(all(x["expected_abstain"] for x in cases if x["cue_quality"] in {"absent","contradictory"}))
    def test_answerable_cues_have_gold(self):
        cases=stress.make_cases(); self.assertTrue(all(x["expected_answer"] and not x["expected_abstain"] for x in cases if x["cue_quality"] in {"full","weak"}))
    def test_validation_rejects_missing_ids(self):
        with self.assertRaises(ValueError): stress.validate(json.dumps({"results":[]}),[{"case_id":"A"}])
    def test_model_payload_excludes_gold_labels(self):
        serialized=json.dumps(stress.model_item(stress.make_cases()[0]))
        self.assertNotIn("expected_",serialized)
    def test_identifiers_and_values_do_not_expose_version_numbers(self):
        case=next(x for x in stress.make_cases() if x["stale_count"]==64 and x["cue_quality"]=="absent" and x["value_similarity"]=="high")
        serialized=json.dumps(case["records"])
        self.assertNotIn("V065",serialized)
        self.assertNotIn("amber-065",serialized)
    def test_cases_do_not_share_identifiers(self):
        cases=stress.make_cases(); seen=set()
        for case in cases:
            ids={row["evidence_id"] for row in case["records"]}
            self.assertFalse(seen & ids)
            seen.update(ids)
    def test_model_case_ids_do_not_name_conditions(self):
        forbidden={*stress.CUES,*stress.ORDERS,*stress.SIMILARITIES,*stress.INSTRUCTIONS}
        self.assertTrue(all(not any(token in case["case_id"] for token in forbidden) for case in stress.make_cases()))
if __name__=="__main__": unittest.main()
