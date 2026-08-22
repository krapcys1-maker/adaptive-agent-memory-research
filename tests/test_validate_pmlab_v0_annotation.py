import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("validator", ROOT / "scripts" / "validate_pmlab_v0_annotation.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PMLABAnnotationValidatorTests(unittest.TestCase):
    def test_invalidated_v0_packet_cannot_enter_annotation(self):
        with self.assertRaisesRegex(ValueError, "not independently leakage-accepted"):
            MODULE.verify_packet()

    def completed(self, directory: Path, reviewer: str, slot: str, alter_first: bool = False):
        labels = MODULE.read_jsonl(MODULE.PACKET / "internal" / "author-labels.jsonl")
        rows = MODULE.read_jsonl(MODULE.BLIND / f"annotation-form-{slot.lower()}.jsonl")
        gold = {row["example_id"]: row for row in labels}
        for row in rows:
            source = gold[row["example_id"]]
            row.update({
                "reviewer_id": reviewer, "answerable": source["answerable"],
                "gold_evidence_ids": source["gold_evidence_ids"], "gold_current_ids": source["gold_current_ids"],
                "forbidden_stale_ids": source["forbidden_stale_ids"], "alternative_acceptable_ids": [],
                "confidence": 0.9, "notes": "Synthetic contract test; not independent evidence.",
            })
        if alter_first:
            rows[0]["confidence"] = 0.8
        form = directory / f"form-{slot}.jsonl"
        form.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
        attestation = json.loads((MODULE.BLIND / f"attestation-{slot.lower()}.json").read_text(encoding="utf-8"))
        attestation.update({
            "reviewer_id": reviewer, "reviewer_family_or_affiliation": f"test-{reviewer}",
            "review_started_at": "2026-08-22T01:00:00Z", "review_completed_at": "2026-08-22T02:00:00Z",
            "assigned_slot": slot, "completed_form_sha256": hashlib.sha256(form.read_bytes()).hexdigest(),
            "conflicts_prior_exposure_or_assistance": "Unit test used author labels and is not independent.",
            "signature_or_verifiable_acknowledgement": f"test-signature-{reviewer}",
        })
        attestation["statements"] = {key: True for key in attestation["statements"]}
        att = directory / f"att-{slot}.json"
        att.write_text(json.dumps(attestation), encoding="utf-8")
        return form, att

if __name__ == "__main__":
    unittest.main()
