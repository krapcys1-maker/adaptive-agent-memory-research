import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("packet_builder", ROOT / "scripts" / "build_mapper_independent_adjudication_v1.py")
MODULE = importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; SPEC.loader.exec_module(MODULE)


class IndependentAdjudicationPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = MODULE.build_outputs()
        cls.jobs = [json.loads(line) for line in cls.outputs[MODULE.BLIND_DIR / "jobs.jsonl"].splitlines()]
        cls.forms = [json.loads(line) for line in cls.outputs[MODULE.BLIND_DIR / "review-form.jsonl"].splitlines()]
        cls.manifest = json.loads(cls.outputs[MODULE.BLIND_DIR / "manifest.json"])

    def test_selects_all_critical_plus_one_ordinary_per_stage(self):
        self.assertEqual(67, len(self.jobs))
        self.assertEqual(134, self.manifest["selected_rows"])
        self.assertEqual(61, self.manifest["critical_groups"])
        self.assertEqual(6, self.manifest["ordinary_groups"])
        self.assertTrue(self.manifest["all_six_stages_represented"])

    def test_blind_jobs_have_no_gold_or_evaluation_metadata(self):
        keys = MODULE.recursive_keys(self.jobs)
        self.assertFalse(keys & MODULE.FORBIDDEN_BLIND_KEYS)
        self.assertEqual({"en", "pl"}, {case["language"] for job in self.jobs for case in job["cases"]})

    def test_review_forms_are_blank(self):
        self.assertEqual(67, len(self.forms))
        self.assertTrue(all(form["independent_labels"] == {"en": None, "pl": None} for form in self.forms))
        self.assertTrue(all(form["reviewer_id_or_pseudonym"] is None for form in self.forms))

    def test_manifest_hashes_every_blind_artifact(self):
        for name, expected in self.manifest["blind_hashes"].items():
            path = MODULE.BLIND_DIR / name
            content = self.outputs.get(path)
            actual = MODULE.sha_bytes(content.encode("utf-8")) if content is not None else MODULE.sha_bytes(path.read_bytes())
            self.assertEqual(expected, actual)


if __name__ == "__main__": unittest.main()
