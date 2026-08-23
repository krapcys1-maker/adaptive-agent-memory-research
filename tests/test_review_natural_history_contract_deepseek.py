import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("review_natural", ROOT / "scripts" / "review_natural_history_contract_deepseek.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_review_validator_accepts_exact_locked_shape():
    value = {
        "verdict": "needs_revision", "fatal_issues": [],
        "major_issues": [{"issue": "x", "artifact": "schema", "why": "y", "repair": "z"}],
        "minor_issues": [],
        "schema_prose_mismatches": [{"field_or_rule": "x", "mismatch": "y", "repair": "z"}],
        "leakage_or_privacy_attacks": [{"attack": "x", "expected_control": "y", "residual_risk": "z"}],
        "invariants_to_test": ["x"], "claims_allowed": ["x"], "claims_forbidden": ["x"],
        "builder_must_remain_locked": True, "confidence": 0.8,
    }
    assert MODULE.validate(value) == value


def test_review_validator_cannot_unlock_builder():
    value = {
        "verdict": "admit_for_independent_review", "fatal_issues": [], "major_issues": [], "minor_issues": [],
        "schema_prose_mismatches": [], "leakage_or_privacy_attacks": [], "invariants_to_test": [],
        "claims_allowed": [], "claims_forbidden": [], "builder_must_remain_locked": False, "confidence": 1,
    }
    try:
        MODULE.validate(value)
    except ValueError:
        pass
    else:
        raise AssertionError("M1 review unlocked the builder")
