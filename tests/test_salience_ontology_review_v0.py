import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


BUILDER = load_module("salience_builder", ROOT / "scripts" / "build_salience_ontology_review_v0.py")
VALIDATOR = load_module("salience_validator", ROOT / "scripts" / "validate_salience_ontology_review_v0.py")


class SalienceOntologyPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = BUILDER.build_outputs()
        cls.blind = BUILDER.OUT
        cls.contract = json.loads(cls.outputs[cls.blind / "factor-contract.json"])
        cls.probes = [json.loads(line) for line in cls.outputs[cls.blind / "probe-cases.jsonl"].splitlines()]

    def test_packet_is_deterministic_gold_free_and_controller_free(self):
        self.assertEqual(self.outputs, BUILDER.build_outputs())
        manifest = json.loads(self.outputs[self.blind / "manifest.json"])
        self.assertFalse(manifest["author_probe_labels_present"])
        self.assertFalse(manifest["controller_or_backend_outputs_present"])
        self.assertFalse(manifest["outcome_corpus_present"])
        self.assertEqual(manifest["factor_count"], 12)
        self.assertEqual(manifest["probe_count"], 24)

    def test_blank_forms_cover_every_factor_and_probe(self):
        review = json.loads(self.outputs[self.blind / "review-form.json"])
        self.assertEqual({row["factor_id"] for row in review["factor_reviews"]}, {row["factor_id"] for row in self.contract["factors"]})
        self.assertEqual({row["case_id"] for row in review["probe_reviews"]}, {row["case_id"] for row in self.probes})
        self.assertIsNone(review["whole_packet_decision"])
        self.assertTrue(all(row["decision"] is None for row in review["factor_reviews"]))

    def test_hash_manifest_covers_every_non_manifest_blind_file(self):
        manifest = json.loads(self.outputs[self.blind / "manifest.json"])
        expected = {path.name for path in self.outputs if path.parent == self.blind and path.name != "manifest.json"}
        self.assertEqual(set(manifest["blind_hashes"]), expected)
        for name, digest in manifest["blind_hashes"].items():
            self.assertEqual(hashlib.sha256(self.outputs[self.blind / name].encode("utf-8")).hexdigest(), digest)

    def test_validator_accepts_complete_hash_bound_review(self):
        review = json.loads(self.outputs[self.blind / "review-form.json"])
        review.update({
            "review_id": "external-r1", "reviewer_id_or_pseudonym": "reviewer-x",
            "reviewer_family_or_affiliation": "external-test-affiliation", "reviewed_at": "2026-08-23T00:00:00Z",
            "whole_packet_decision": "revise", "whole_packet_rationale": "Definitions are testable but require the recorded revisions.",
            "attestation_id": "att-x",
        })
        for row in review["factor_reviews"]:
            row.update({"decision": "accept", "operational_observability": "clear", "independent_from_other_factors": "conditional", "rationale": "Operationally usable when provenance remains explicit."})
        review["factor_reviews"][0].update({"decision": "revise", "proposed_revision": "Clarify authority ordering across signed policies and outcomes."})
        all_factors = [row["factor_id"] for row in self.contract["factors"]]
        always_prohibited = self.contract["always_prohibited_actions"]
        for row in review["probe_reviews"]:
            row.update({
                "supported_factor_ids": [], "unsupported_factor_ids": [], "unresolved_factor_ids": all_factors,
                "permitted_actions": ["no_control_change"], "prohibited_actions": always_prohibited,
                "material_ambiguity": True, "rationale": "The probe does not establish every factor without extra evidence.",
            })
        with tempfile.TemporaryDirectory() as temp:
            review_path = Path(temp) / "review.json"
            attestation_path = Path(temp) / "attestation.json"
            review_path.write_text(json.dumps(review, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            attestation = json.loads(self.outputs[self.blind / "attestation.json"])
            attestation.update({
                "attestation_id": "att-x", "reviewer_id_or_pseudonym": "reviewer-x",
                "reviewer_family_or_affiliation": "external-test-affiliation",
                "review_started_at": "2026-08-22T23:00:00Z", "review_completed_at": "2026-08-23T00:00:00Z",
                "packet_manifest_sha256": hashlib.sha256((self.blind / "manifest.json").read_bytes()).hexdigest(),
                "completed_review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
                "tools_conflicts_or_prior_exposure_notes": "No prior exposure; no tools used.",
                "signature_or_verifiable_acknowledgement": "reviewer-x",
            })
            attestation["statements"] = {key: True for key in attestation["statements"]}
            attestation_path.write_text(json.dumps(attestation, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            receipt = VALIDATOR.validate_completed(review_path, attestation_path)
        self.assertEqual(receipt["whole_packet_decision"], "revise")
        self.assertFalse(receipt["controller_unlocked"])
        self.assertEqual(receipt["factor_decisions"]["revise"], 1)


if __name__ == "__main__":
    unittest.main()
