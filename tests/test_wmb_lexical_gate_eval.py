"""Fixed-grid evaluation plumbing, not assertions that one scorer must win."""
import importlib.util
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lexical_eval_tests", ROOT / "scripts/wmb/lexical_gate_eval.py")
evaluation = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = evaluation
spec.loader.exec_module(evaluation)


def test_rank_and_gate_grids_cover_every_registered_setting():
    ranks, gates = evaluation.rank_grid(), evaluation.gate_grid()
    assert len(ranks) == 18 and len(gates) == 30
    assert {r["max_terms"] for r in ranks} == {0, 20}
    assert {r["b"] for r in ranks if r["k1"] == 1.2} == set(evaluation.BS)
    assert {(r["b"], r["k1"]) for r in ranks if r["k1"] != 1.2} == {(0.75, 0.5), (0.75, 2.0)}
    assert {(r["lex_tau"], r["top_terms"]) for r in gates} == set(evaluation.itertools.product(evaluation.LEX_TAUS, evaluation.TOP_TERMS))
    assert all(not r["names"] and r["embed"] == "off" for r in ranks + gates)


def test_dates_follow_the_asked_day_not_the_last_event():
    assert evaluation.end_of_day(1) == "2026-01-01T23:59:00Z"
    assert evaluation.end_of_day(20) == "2026-01-20T23:59:00Z"


def test_adapters_keep_gold_out_of_the_items_and_report_exclusions():
    suites = evaluation.suites()
    assert {s.name for s in suites} == {"H1", "E6", "H2-dev", "H2-valid"}
    for suite in suites:
        ids = {i[0] for i in suite.items}
        assert len(ids) == len(suite.items)
        assert suite.questions and all(gold and gold <= ids for _, _, _, gold in suite.questions)
        assert all(len(item) == 3 for item in suite.items)
    persona = next(s for s in suites if s.name == "E6")
    assert len(persona.questions) + len(persona.exclusions) == 24
    assert persona.task_type == "personal"
    for suite in (s for s in suites if s.name.startswith("H2-")):
        assert len(suite.questions) == 56 and len(suite.exclusions) == 14


def test_paired_difference_counts_discordance_and_is_deterministic():
    left, right = [1, 0, 1, 0], [0, 1, 1, 1]
    first = evaluation.difference(left, right, resamples=200)
    assert first == evaluation.difference(left, right, resamples=200)
    assert first["difference"] == 0.25
    assert first["coverage_only"] == 1 and first["tested_only"] == 2
    assert first["ci95"][0] <= first["difference"] <= first["ci95"][1]
    assert evaluation.difference([0, 0], [1, 1])["ci95"] == [1.0, 1.0]
    with pytest.raises(ValueError):
        evaluation.difference([], [])


def test_rank_recall_is_any_declared_gold_at_the_requested_depth():
    suite = evaluation.Suite("tiny", [], [("q", "question", "2026", {"g1", "g2"})], "note", [], [], "fixture")
    assert evaluation.hits(suite, [["wrong", "g2"]], 1) == [0]
    assert evaluation.hits(suite, [["wrong", "g2"]], 3) == [1]


def test_gate_separates_positive_firing_gold_and_unrelated_firing():
    suite = evaluation.Suite("tiny", [], [("q", "positive", "2026", {"gold"})], "note", [], [], "fixture")
    class Kernel:
        def retrieve(self, index, query, *args):
            return {"status": "ok", "items": [types.SimpleNamespace(id="gold")] if query != "unrelated" else []}
    result = evaluation.gate_row(Kernel(), None, suite, {}, ["unrelated"])
    assert result["fired"] == result["gold_shown"] == 1
    assert result["unrelated_fired"] == 0 and result["unrelated_queries"] == 1


def test_kernel_errors_are_not_counted_as_zero_recall():
    suite = evaluation.Suite("tiny", [], [("q", "question", "2026", {"gold"})], "note", [], [], "fixture")
    class Kernel:
        def retrieve(self, *args):
            return {"status": "error", "items": []}
    with pytest.raises(ValueError, match="retrieval failed"):
        evaluation.rankings(Kernel(), None, suite, {})


def test_historical_outputs_cannot_be_overwritten(tmp_path):
    output = tmp_path / "old.json"
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit):
        evaluation.main(["--output", str(output)])
    assert output.read_text() == "keep"
