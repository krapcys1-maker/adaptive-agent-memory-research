import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("review_natural_v2", ROOT / "scripts" / "review_natural_history_contract_deepseek_v2.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_compact_validator_is_bounded_and_locked():
    value = {
        "verdict": "needs_revision", "fatal": [],
        "repairs": [{"severity": "major", "artifact": "schema", "issue": "x", "required_test": "y"}],
        "schema_mismatches": [], "privacy_or_leakage_attacks": [], "builder_locked": True, "confidence": 0.8,
    }
    assert MODULE.validate(value) == value
    value["builder_locked"] = False
    try:
        MODULE.validate(value)
    except ValueError:
        pass
    else:
        raise AssertionError("compact M1 unlocked builder")
