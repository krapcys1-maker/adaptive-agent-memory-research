import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analysis", ROOT / "scripts" / "analyze_pmlab_v01_lexical_result.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_analysis_separates_recall_gain_from_new_forbidden_intrusion():
    common = {"split": "test", "family": "x", "category": "temporal_as_of", "consequence_weight": 4, "answerable": True, "candidate_count": 1}
    rows = [
        {**common, "backend": "B1-ripgrep", "example_id": "Q", "retrieved": [], "recall_at_5": 0.0, "all_required_at_5": False, "forbidden_intrusion_at_5": False},
        {**common, "backend": "B2-sqlite-fts5", "example_id": "Q", "retrieved": ["OLD", "G"], "recall_at_5": 1.0, "all_required_at_5": True, "forbidden_intrusion_at_5": True},
    ]
    gold = [{"example_id": "Q", "forbidden_stale_ids": ["OLD"]}]
    backend = {"index_bytes": 1, "macro_recall_at_5_answerable_strata": 1, "all_required_at_5_rate": 1}
    final = {"decision": {"outcome": "advance"}, "summary": {"backends": {"B1-ripgrep": backend, "B2-sqlite-fts5": backend}}, "warm_latency": {"by_backend": {"B1-ripgrep": {"p50_ms": 2, "p95_ms": 4}, "B2-sqlite-fts5": {"p50_ms": 1, "p95_ms": 2}}}}
    value = MODULE.analyze(rows, gold, final)
    assert value["paired_recall"]["b2_wins"] == ["Q"]
    assert value["forbidden_intrusion"]["new_in_b2"] == ["Q"]
    assert value["forbidden_intrusion"]["b2_cases"][0]["forbidden_retrieved"] == ["OLD"]
