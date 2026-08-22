import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_obligation_mapping_construction.py"
SPEC = importlib.util.spec_from_file_location("run_obligation_mapping_construction", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def cases():
    return MODULE.read_jsonl(ROOT / "data" / "lab" / "pmlab-obligation-mapping-dev-v0" / "cases.jsonl")


def test_gold_oracle_is_exact_and_safe():
    rows = [MODULE.score_case(case, "gold_oracle", MODULE.predict(case, "gold_oracle")) for case in cases()]
    summary = MODULE.summarize(rows)["gold_oracle"]
    assert summary["obligation_f1"] == 1.0
    assert summary["structure_exact_rate"] == 1.0
    assert summary["end_to_end_exact_rate"] == 1.0
    assert summary["false_closure_count"] == 0


def test_unsupported_cases_are_not_coerced_by_rule_pipeline():
    unsupported = [case for case in cases() if case["query_status"] == "unsupported_structure"]
    assert unsupported
    for case in unsupported:
        prediction = MODULE.predict(case, "qdmr_rules_pipeline")
        assert prediction["query_status"] == "unsupported_structure"
        assert prediction["nodes"] == []


def test_simple_whole_query_arm_cannot_fake_multifacet_recall():
    multi = [case for case in cases() if len(case["graph"]["nodes"]) >= 2]
    assert multi
    rows = [MODULE.score_case(case, "whole_query_single_scope", MODULE.predict(case, "whole_query_single_scope")) for case in multi]
    assert any(row["obligation_recall"] < 1.0 for row in rows)
