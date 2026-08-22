import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("reveal", ROOT / "scripts" / "reveal_mapper_adjudication_v1.py")
MODULE = importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; SPEC.loader.exec_module(MODULE)


class RevealGateTests(unittest.TestCase):
    def test_blank_form_and_missing_receipt_block_reveal(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaises((ValueError, FileNotFoundError)):
                MODULE.verified_receipt(MODULE.validator.BLIND_DIR / "review-form.jsonl", MODULE.validator.BLIND_DIR / "attestation.json", missing)

    def test_differing_fields_is_structural(self):
        self.assertEqual(["action", "basis"], MODULE.differing_fields({"action":"answer","basis":"A"},{"action":"abstain","basis":"B"}))

    def test_entity_normalization_adds_empty_selected_ids(self):
        value = MODULE.normalized_label("entity_linking", {"action":"missing_entity","candidate_ids":[],"selected_id":None})
        self.assertEqual([], value["selected_ids"])


if __name__ == "__main__": unittest.main()
