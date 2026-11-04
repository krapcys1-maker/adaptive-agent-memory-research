"""Cost-normalized recall: preserve the denominator and never invent history."""
import importlib.util
import json
import math
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import retrieval_metrics as metrics
import backfill_retrieval_cost as backfill


def test_aggregate_is_a_ratio_of_means_not_a_mean_of_ratios():
    result = metrics.efficiency([1, 0], [1, 100])
    assert result == {"queries": 2, "recall": 0.5, "mean_retrieved_tokens": 50.5,
                      "recall_per_1k_tokens": 9.90099}
    assert result["recall_per_1k_tokens"] != 500.0


@pytest.mark.parametrize("hits,costs", [([], []), ([0, 0], [0, 0]), ([1], [0])])
def test_zero_cost_is_undefined_never_infinity(hits, costs):
    assert metrics.efficiency(hits, costs)["recall_per_1k_tokens"] is None


@pytest.mark.parametrize("hits,costs", [([1], []), ([2], [1]), ([-1], [1]), ([math.nan], [1]),
                                       ([1], [-1]), ([1], [math.inf]), ([1], [True])])
def test_bad_or_unpaired_observations_are_not_silently_averaged(hits, costs):
    with pytest.raises(ValueError):
        metrics.efficiency(hits, costs)


def test_text_count_and_scored_window_exclude_unshown_candidates():
    events = {"a": {"title": "one two", "summary": "three", "body": "four\nfive"},
              "b": {"title": "six", "summary": "seven", "body": ""},
              "unshown": {"title": "ignored " * 100}}
    result = metrics.snapshot_costs({"b1": {1: ["a"], 5: ["a", "b"]}}, events)
    assert result["b1_retrieved_tokens@1"] == 5
    assert result["b1_retrieved_tokens@5"] == 7
    assert result["b1_retrieved_ids@1"] == ["a"]
    assert metrics.token_count(" a\t b\n c ") == 3
    with pytest.raises(KeyError):
        metrics.snapshot_costs({"b1": {1: ["missing"]}}, events)


def test_backfill_uses_surviving_costs_and_preserves_original_records():
    data = {"summary": {"experiment_id": "fixture"}, "records": [
        {"recall@1": 1, "retrieved_tokens@1": 2}, {"recall@1": 0, "retrieved_tokens@1": 8}]}
    before = json.dumps(data, sort_keys=True)
    result = backfill.summarize(data)
    assert result["groups"]["all"]["recall@1"]["recall_per_1k_tokens"] == 100.0
    assert json.dumps(data, sort_keys=True) == before


def test_missing_historical_costs_are_not_zero_or_inferred_from_hits():
    data = {"records": [{"language": "pl", "b1_hit@5": 1, "b1_retrieved_tokens@5": 10},
                         {"language": "pl", "b1_hit@5": 0}]}
    result = backfill.summarize(data)
    cost = result["groups"]["pl"]["b1@5"]
    assert result["status"] == "unavailable-or-incomplete"
    assert cost["missing_cost_or_recall_rows"] == 1 and cost["recall_per_1k_tokens"] is None


def test_authored_gold_and_mechanical_strata_are_never_pooled():
    result = backfill.summarize({"records": [
        {"stratum": "mechanical", "b1_hit@5": 1, "b1_retrieved_tokens@5": 10},
        {"stratum": "tag_only", "b1_hit@5": 0, "b1_retrieved_tokens@5": 100}]})
    assert set(result["groups"]) == {"mechanical", "tag_only"}
    assert result["groups"]["mechanical"]["b1@5"]["recall_per_1k_tokens"] == 100.0


def test_h1_callers_use_the_shared_metric_with_zero_cost():
    import run_corpus_h1_address_probe as address
    import run_corpus_h1_baseline as baseline
    row = {"family": "fixture", "forbidden_above_gold": None}
    for depth in baseline.DEPTHS:
        row.update({f"recall@{depth}": 0, f"retrieved_tokens@{depth}": 0, f"intrusion@{depth}": None})
    result = baseline.summarise([row], 1)
    assert result["recall_per_1k_tokens@1"] is None
    assert "ratio of means" in result["retrieval_cost_definition"]["aggregation"]
    row = {"family": "fixture"}
    for arm in ("lexical", "addressed"):
        row.update({arm + "_gold": 0, arm + "_stale": 0, arm + "_candidates": 0, arm + "_tokens": 0})
    assert address.summarise([row], 1000)["arms"]["lexical"]["gold_per_1k_retrieved_tokens"] is None


def test_existing_outputs_cannot_be_overwritten(tmp_path):
    path = tmp_path / "historical.json"
    path.write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit):
        backfill.main(["--output", str(path)])
    assert path.read_text() == "keep"
