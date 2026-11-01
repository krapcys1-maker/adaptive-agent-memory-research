"""retrieval_calibration.py: candidate pairs, negative controls, parsing, a resumable run and the threshold analysis.

Vectors are hand-made unit vectors, the judge is a fake keyed on the cosine, and no text of any account is involved.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import retrieval_calibration as rc  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402


def unit(*values: float) -> list:
    norm = sum(v * v for v in values) ** 0.5
    return [v / norm for v in values]


def toy(n: int = 12) -> tuple:
    """Notes alternate between two topics, so each note has close earlier notes of its own topic and far ones of the other."""
    vectors = [unit(1, 0.05 * k, 0) if k % 2 == 0 else unit(0, 0.05 * k, 1) for k in range(n)]
    items = [sbm.Item("n%d" % k, date(2026, 1, 1) + timedelta(days=k), "text %d" % k) for k in range(n)]
    return items, vectors


def fake_generate(system: str, user: str, seed: int, opts: dict) -> dict:
    # rate by whether the two texts have the same parity: same topic -> 2, other topic -> 0
    new, earlier = user.split("NEW NOTE (the one being written):\n")[1].split("\n\nEARLIER NOTE (written before it):\n")
    earlier = earlier.split("\n\nIf the author")[0]
    same = (int(new.split()[-1]) - int(earlier.split()[-1])) % 2 == 0
    return {"text": "RELEVANCE: %d" % (2 if same else 0), "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}


def test_candidate_pairs_are_the_three_most_similar_earlier_notes_and_the_first_note_has_none() -> None:
    items, vectors = toy()
    pairs = rc.candidate_pairs(vectors)
    assert min(p["i"] for p in pairs) == 1 and all(p["j"] < p["i"] for p in pairs)
    for i in range(1, len(items)):
        mine = [p for p in pairs if p["i"] == i]
        assert len(mine) == min(3, i) and [p["kind"] for p in mine] == ["top1", "top2", "top3"][:len(mine)]
        assert [p["cos"] for p in mine] == sorted((p["cos"] for p in mine), reverse=True)
    top_for_8 = [p["j"] for p in pairs if p["i"] == 8]
    assert all(j % 2 == 0 for j in top_for_8)                      # note 8 is closest to earlier even notes


def test_controls_are_one_random_earlier_note_per_note_never_one_of_its_candidates_and_are_repeatable() -> None:
    _, vectors = toy(20)
    top = rc.candidate_pairs(vectors)
    controls = rc.control_pairs(vectors, top)
    assert controls == rc.control_pairs(vectors, top)
    assert [c["i"] for c in controls] == list(range(rc.TOP_K + 1, 20))
    taken = {(p["i"], p["j"]) for p in top}
    assert all((c["i"], c["j"]) not in taken and c["j"] < c["i"] and c["kind"] == "control" for c in controls)


def test_relevance_is_parsed_from_a_one_line_reply_and_a_missing_one_is_none() -> None:
    assert rc.parse_relevance("RELEVANCE: 2") == 2 and rc.parse_relevance("**Relevance**: 1.") == 1 and rc.parse_relevance("relevance = 0") == 0
    assert rc.parse_relevance("RELEVANCE: 3") is None and rc.parse_relevance("no idea") is None


def test_the_prompt_asks_about_the_new_note_and_the_earlier_one_and_nothing_else() -> None:
    prompt = rc.judge_prompt("alpha text", "beta text")
    assert "alpha text" in prompt and "beta text" in prompt and prompt.index("alpha text") < prompt.index("beta text") and "RELEVANCE: <0-2>" in prompt


def test_a_run_judges_every_pair_once_resumes_and_stores_indices_never_text(tmp_path: Path) -> None:
    items, vectors = toy(14)
    out = tmp_path / "judgments.jsonl"
    first = rc.run(items, vectors, out, fake_generate, workers=3, log=lambda line: None)
    expected = len(rc.candidate_pairs(vectors)) + len(rc.control_pairs(vectors, rc.candidate_pairs(vectors)))
    assert first == expected and rc.run(items, vectors, out, fake_generate, workers=3, log=lambda line: None) == 0
    text = out.read_text(encoding="utf-8")
    assert "text 3" not in text and all(set(json.loads(line)) == {"i", "j", "cos", "kind", "relevance", "raw"} for line in text.splitlines())


def test_the_analysis_finds_the_threshold_where_injected_notes_become_relevant(tmp_path: Path) -> None:
    items, vectors = toy(40)
    out = tmp_path / "judgments.jsonl"
    rc.run(items, vectors, out, fake_generate, workers=4, log=lambda line: None)
    result = rc.analyse([json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()], len(items))
    assert result["unparsed"] == 0 and result["controls"]["judge_reliable"] in (True, False)
    low, high = result["by_threshold"]["0.5"], result["by_threshold"]["0.7"]
    assert low["injected_pairs"] >= high["injected_pairs"] and low["notes_served"] >= high["notes_served"]
    assert high["precision_rated_1_or_2"] == pytest.approx(1.0)               # the fake judge says 2 for same-topic pairs
    assert result["lowest_usable_threshold"] is not None
    assert sum(b["pairs"] for b in result["calibration_by_cosine"]) == result["judged_pairs"]
    assert "# AAM-E3A retrieval calibration" in rc.report(result)


def test_a_judge_that_rates_random_pairs_as_related_is_declared_unreliable() -> None:
    rows = [{"i": k, "j": 0, "cos": 0.2, "kind": "control", "relevance": 2, "raw": ""} for k in range(5, 15)]
    rows += [{"i": k, "j": 1, "cos": 0.8, "kind": "top1", "relevance": 2, "raw": ""} for k in range(5, 15)]
    assert rc.analyse(rows, 20)["controls"]["judge_reliable"] is False


def test_no_threshold_is_declared_usable_when_precision_or_coverage_is_too_low() -> None:
    rows = [{"i": k, "j": 0, "cos": 0.9, "kind": "top1", "relevance": 0, "raw": ""} for k in range(1, 11)]
    assert rc.analyse(rows, 11)["lowest_usable_threshold"] is None
    sparse = [{"i": 1, "j": 0, "cos": 0.9, "kind": "top1", "relevance": 2, "raw": ""}]
    assert rc.analyse(sparse, 100)["lowest_usable_threshold"] is None       # one served note of 99 is below the coverage floor


def test_the_wilson_interval_brackets_the_estimate() -> None:
    low, high = rc.wilson(8, 10)
    assert low < 0.8 < high and rc.wilson(0, 0) is None
