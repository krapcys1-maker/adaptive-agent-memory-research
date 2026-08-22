import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_screening_sources.py"
SPEC = importlib.util.spec_from_file_location("audit_screening_sources", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class SourceAuditTests(unittest.TestCase):
    def test_title_normalization_handles_case_punctuation_and_accents(self):
        self.assertEqual(
            MODULE.normalize_title("A Rate–Distortion: Résumé"),
            "a rate distortion resume",
        )

    def test_title_similarity_recognizes_case_only_version(self):
        self.assertEqual(MODULE.title_similarity("A Model of Memory", "a model of memory"), 1.0)


if __name__ == "__main__":
    unittest.main()
