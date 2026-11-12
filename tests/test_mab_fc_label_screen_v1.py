"""The label screen on a constructed context: the classes it assigns are checked against facts built by hand.

The benchmark file is not in the repository, so these tests use five synthetic sentences in the benchmark's format.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("mab_fc_label_screen_v1", ROOT / "scripts" / "mab_fc_label_screen_v1.py")
screen = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = screen
_spec.loader.exec_module(screen)

CONTEXT = "\n".join(
    [
        "Here is a list of facts:",
        "1. Ada Example is a citizen of France.",
        "2. The capital of France is Paris.",
        "3. Ada Example is a citizen of India.",
        "4. The capital of India is New Delhi.",
        "5. The capital of France is Lyon.",
    ]
)


def graph():
    return screen.Graph(CONTEXT)


def test_grammar_parses_every_numbered_sentence_and_keeps_history():
    g = graph()
    assert g.lines == 5 and g.unparsed == []
    history = g.hist[(screen.key("Ada Example"), "citizen_of")]
    assert [(serial, value) for serial, value, _ in history] == [(1, "France"), (3, "India")]
    assert g.latest(screen.key("France"), "capital")[1] == "Lyon"


def test_single_hop_answer_from_an_overwritten_sentence_is_flagged():
    g = graph()
    assert screen.classify_sh(g, "Which country is Ada Example a citizen of?", ["France"])["class"] == "SUPERSEDED_VALUE"
    assert screen.classify_sh(g, "Which country is Ada Example a citizen of?", ["India"])["class"] == "CONSISTENT"


def test_multi_hop_classes_follow_the_position_of_the_outdated_hop():
    g = graph()
    question = "What is the capital of the country Ada Example is a citizen of?"
    assert screen.classify_mh(g, question, ["New Delhi"])["class"] == "CONSISTENT"
    # Reaching Lyon needs the outdated citizenship (sentence 1) and the current capital of France.
    assert screen.classify_mh(g, question, ["Lyon"])["class"] == "SUPERSEDED_INTERMEDIATE_HOP"
    # Reaching Paris needs the outdated citizenship and the outdated capital.
    paris = screen.classify_mh(g, question, ["Paris"])
    assert paris["class"] == "SUPERSEDED_INTERMEDIATE_HOP"
    assert [h["is_latest"] for h in paris["paths"][0]["hops"]] == [False, False]


def test_question_without_a_known_subject_is_not_classified_as_consistent():
    assert screen.classify_sh(graph(), "Which country is Nobody Known a citizen of?", ["France"])["class"] == "NO_ANCHOR"


def test_published_counts_are_internally_consistent():
    folder = ROOT / "data" / "lab" / "mab-fc-label-screen-v1"
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    results = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    flagged = [json.loads(line) for line in (folder / "flagged-items.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(flagged) == 68
    assert sum(item["verdict"] == "CONFIRMED" for item in flagged) == 63
    for variant, row in summary.items():
        assert row["unparsed"] == 0
        not_consistent = row["questions"] - row["classes"].get("CONSISTENT", 0)
        assert not_consistent == results["per_variant"][variant]["flagged"]
        assert not_consistent == sum(item["variant"] == variant for item in flagged)
    assert all(set(item) >= {"variant", "index", "screen_class", "verdict", "relation_path"} for item in flagged)
    assert not any("question" in item or "released_answer" in item for item in flagged)
