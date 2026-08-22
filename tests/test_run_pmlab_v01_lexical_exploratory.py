import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pmlab_v01_lexical", ROOT / "scripts" / "run_pmlab_v01_lexical_exploratory.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_frozen_inputs_join_to_complete_split_without_human_claim():
    corpus, queries, prereg = MODULE.load_inputs()
    assert len(corpus) == 176
    assert len(queries) == 120
    assert sum(row["split"] == "development" for row in queries) == 60
    assert sum(row["split"] == "test" for row in queries) == 60
    assert all(row["evidence_tier"] == "M2" and row["human_confirmed"] is False for row in queries)
    assert prereg["execution_authorized"] is False
    assert prereg["exploratory_execution_authorized"] is True


def test_backend_boundary_passes_query_text_only():
    seen = []

    class Spy:
        def retrieve(self, query, top_k):
            seen.append((query, top_k))
            return []

    query = {"example_id": "secret", "query": "visible words", "category": "hidden", "gold_evidence_ids": ["hidden"]}
    assert MODULE.retrieve(Spy(), query) == []
    assert seen == [("visible words", 5)]


def test_scoring_separates_recall_safety_and_unanswerable_null():
    corpus = {"E1": {"title": "one", "body": "body"}, "OLD": {"title": "old", "body": "body"}}
    query = {"example_id": "Q", "split": "test", "category": "temporal_as_of", "family": "x", "consequence_weight": 4, "answerable": True, "gold_evidence_ids": ["E1"], "forbidden_stale_ids": ["OLD"]}
    row = MODULE.score(query, ["OLD", "E1"], corpus, 1.0, "B")
    assert row["recall_at_5"] == 1.0
    assert row["forbidden_intrusion_at_1"] is True
    assert row["all_required_at_5"] is True


def test_decision_rejects_gain_when_safety_regresses():
    base = {
        "macro_recall_at_5_answerable_strata": 0.5, "critical_full_evidence_miss_rate": 0.1,
        "forbidden_intrusion_at_5_rate": 0.1, "all_required_at_5_rate": 0.5,
        "unanswerable_candidate_null_rate": 1.0, "backend_error_rate": 0.0,
    }
    summary = {"backends": {
        "B0-no-memory": {**base, "macro_recall_at_5_answerable_strata": 0.0},
        "B1-ripgrep": dict(base),
        "B2-sqlite-fts5": {**base, "critical_full_evidence_miss_rate": 0.2},
        "O-reviewed-evidence": {**base, "macro_recall_at_5_answerable_strata": 1.0, "all_required_at_5_rate": 1.0, "forbidden_intrusion_at_5_rate": 0.0},
    }}
    boot = {"point_difference": 0.1, "ci_95": [0.01, 0.2], "category_differences": {"paraphrase": 0.1, "weak_overlap": 0.1, "cross_language": 0.1}}
    result = MODULE.decision(summary, boot, True)
    assert result["outcome"].startswith("reject-B2")
    assert result["checks"]["critical_miss_regression_at_most_0.02"] is False


def test_bootstrap_is_deterministic_and_stratified():
    rows = []
    for category in ("paraphrase", "weak_overlap"):
        for index in range(2):
            for backend, recall in (("B1-ripgrep", 0.0), ("B2-sqlite-fts5", 1.0)):
                rows.append({"answerable": True, "backend": backend, "example_id": f"{category}-{index}", "category": category, "recall_at_5": recall})
    first = MODULE.bootstrap(rows)
    second = MODULE.bootstrap(rows)
    assert first == second
    assert first["point_difference"] == 1.0
    assert first["ci_95"] == [1.0, 1.0]
