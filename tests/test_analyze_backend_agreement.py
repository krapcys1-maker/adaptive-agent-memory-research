from scripts.analyze_backend_agreement import agreement_gate, jaccard, risk_coverage_curve


def test_jaccard_treats_empty_outputs_as_full_agreement():
    assert jaccard([], []) == 1.0
    assert jaccard(["A", "B"], ["B", "C"]) == 1 / 3


def test_agreement_gate_requires_top1_and_set_threshold():
    rows = [
        {"example_id": "A", "fts5_retrieved": ["X"], "backend_jaccard": 1.0, "top1_agreement": True},
        {"example_id": "B", "fts5_retrieved": ["Y"], "backend_jaccard": 0.9, "top1_agreement": False},
        {"example_id": "C", "fts5_retrieved": ["Z"], "backend_jaccard": 0.7, "top1_agreement": True},
    ]
    assert agreement_gate(rows, 0.8) == {"A": ["X"], "B": [], "C": []}


def test_risk_coverage_exposes_high_signal_unsafe_cases():
    rows = [
        {"fts5_retrieved": ["A"], "signal": 1.0, "fts5_safe": False},
        {"fts5_retrieved": ["B"], "signal": 0.8, "fts5_safe": True},
        {"fts5_retrieved": [], "signal": 0.0, "fts5_safe": True},
    ]
    curve = risk_coverage_curve(rows, "signal")
    assert curve["points"][0]["risk"] == 1.0
    assert curve["points"][-1]["coverage"] == 2 / 3
