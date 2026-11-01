"""analyze_followup_memory_sim.py: measures, planted controls, the blind judge, the readings and the command line.

Everything is synthetic: a fake embedder, a fake writer and a fake judge keyed on markers planted in the text.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_followup_memory_sim as afu  # noqa: E402
import followup_memory_sim as fu  # noqa: E402
import writer_memory_sim as sim  # noqa: E402
from test_followup_memory_sim import FakeEmbedder  # noqa: E402


def fake_writer(system: str, user: str, seed: int, opts: dict) -> dict:
    if system == fu.TRACE_SYSTEM:
        return {"text": "GIST: a gist\nANGLE: an angle\nOPEN: none\nKEYWORDS: alpha, beta, gamma, delta, omega", "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}
    hook = re.search(r"Item: (.*)", user).group(1)
    has_notes = "Notes from your own earlier entries" in user
    marker = (" BUILDS ON EARLIER" if "Follow-up on the story" in hook else " DISTRACTED") if has_notes else ""
    return {"text": "A note on %s%s." % (hook[:50], marker), "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}


def fake_judge(system: str, user: str, seed: int, opts: dict) -> dict:
    note = re.search(r"Note to score:\n(.*?)\n\nScore the note", user, re.S).group(1)
    context = user.split("Note to score:")[0]
    hook = re.search(r"Item the author is writing about(?: \(a development of an earlier story\))?: (.*)", user).group(1)
    fresh = 1 if note.strip() in context else 4
    fit = 4 if set(sim.content_tokens(hook)) & set(sim.content_tokens(note)) else 1
    quality = 3 if "DISTRACTED" in note else 4
    if "CONTINUITY" in user:
        return {"text": "FIT: %d, FRESH: %d, CONTINUITY: %d, QUALITY: %d" % (fit, fresh, 4 if "BUILDS ON EARLIER" in note else 2, quality)}
    return {"text": "FIT: %d, FRESH: %d, QUALITY: %d" % (fit, fresh, quality)}


@pytest.fixture(scope="module")
def rows(tmp_path_factory) -> list:
    path = tmp_path_factory.mktemp("e2") / "records.jsonl"
    fu.run(path, fake_writer, FakeEmbedder(), 0.55, (1, 2, 3), 60, fu.ARMS, 4, log=lambda line: None)
    return fu.load_records(path)


def test_scores_are_read_from_one_line_replies_with_three_or_four_dimensions() -> None:
    assert afu.parse_scores("FIT: 4, FRESH: 3, CONTINUITY: 5, QUALITY: 2") == {"fit": 4, "fresh": 3, "continuity": 5, "quality": 2}
    assert afu.parse_scores("FIT: 4, FRESH: 3, QUALITY: 2") == {"fit": 4, "fresh": 3, "continuity": None, "quality": 2}


def test_measures_find_explicit_grounded_and_spurious_references_and_overlap() -> None:
    def row(arm, day, kind, text, base_day=None, story=0, theme="t"):
        return {"seed": 1, "arm": arm, "day": day, "kind": kind, "base_day": base_day, "story": story, "theme": theme, "hook": "h", "text": text}
    base = "agents forget instructions after many turns of conversation"
    rows = [row("A2", 8, "fresh", base), row("A2", 12, "followup", "As I wrote earlier, agents forget instructions after many turns, and repetition helps", 8),
            row("A2", 13, "fresh", "As I wrote earlier, something entirely unrelated about harbours and ferries happened here"),
            row("A2", 14, "fresh", "agents forget instructions after many turns of conversation")]
    table = afu.measure_all(rows, FakeEmbedder())
    follow, spurious, copy = table[("A2", 1, 12)], table[("A2", 1, 13)], table[("A2", 1, 14)]
    assert follow["callback_ext"] == 1.0 and follow["grounded_callback"] == 1.0 and follow["spurious_callback"] is None
    assert spurious["spurious_callback"] == 1.0 and spurious["grounded_callback"] is None
    assert copy["overlap4"] == pytest.approx(1.0)


def test_a_reference_in_a_follow_up_is_not_grounded_when_it_points_at_nothing_related() -> None:
    rows = [{"seed": 1, "arm": "A0", "day": 8, "kind": "fresh", "base_day": None, "story": 0, "theme": "t", "hook": "h", "text": "harbours ferries tides lighthouses weather"},
            {"seed": 1, "arm": "A0", "day": 12, "kind": "followup", "base_day": 8, "story": 0, "theme": "t", "hook": "h",
             "text": "As I wrote earlier, tomatoes need compost and patience in the allotment this spring"}]
    assert afu.measure_all(rows, FakeEmbedder())[("A0", 1, 12)]["grounded_callback"] == 0.0


def test_the_judge_prompt_adds_continuity_only_for_follow_ups_and_never_shows_the_arm() -> None:
    follow = {"kind": "followup", "hook": "Follow-up on the story that X: Y.", "arm": "A3", "text": "n"}
    fresh = {"kind": "fresh", "hook": "A fresh item.", "arm": "A3", "text": "n"}
    p1 = afu.judge_prompt(follow, "the new note", [{"text": "the earlier note on the story"}])
    p2 = afu.judge_prompt(fresh, "the new note", [{"day": 3, "text": "an earlier note"}])
    assert "CONTINUITY" in p1 and "the earlier note on the story" in p1 and "CONTINUITY" not in p2 and "[Earlier note, day 3]" in p2
    assert "A3" not in p1 and "A3" not in p2


def test_planted_controls_come_from_arm_a0_follow_ups_and_are_built_as_described(rows) -> None:
    controls = afu.build_controls(rows, each=4)
    assert controls == afu.build_controls(rows, each=4) and [c["control"] for c in controls] == ["copy", "other"] * 4
    a0 = [r for r in rows if r["arm"] == "A0"]
    for c in controls:
        assert c["arm"] == "A0" and c["kind"] == "followup"
        base = next(r for r in a0 if r["seed"] == c["seed"] and r["day"] == c["base_day"])
        if c["control"] == "copy":
            assert c["text"] == base["text"]
        else:
            assert c["text"] != base["text"] and not any(r["text"] == c["text"] and r["story"] == c["story"] for r in a0)


def test_a_judge_run_judges_each_note_and_control_once_and_resumes_and_a_sample_thins_the_fresh_notes(rows, tmp_path: Path) -> None:
    out = tmp_path / "j.jsonl"
    first = afu.judge_run(rows, out, fake_judge, workers=4, log=lambda line: None, controls_each=3)
    expected = sum(1 for r in rows if r["day"] >= afu.ANALYSIS_FROM) + 6
    assert first == expected and afu.judge_run(rows, out, fake_judge, workers=4, log=lambda line: None, controls_each=3) == 0
    thin = tmp_path / "thin.jsonl"
    afu.judge_run(rows, thin, fake_judge, workers=4, sample_fresh=0.25, log=lambda line: None, controls_each=3)
    judged = afu.load_jsonl(thin)
    follow_all = sum(1 for r in rows if r["kind"] == "followup" and r["day"] >= afu.ANALYSIS_FROM)
    assert sum(1 for j in judged if j["kind"] == "followup" and not j["control"]) == follow_all
    fresh_judged = sum(1 for j in judged if j["kind"] == "fresh")
    fresh_all = sum(1 for r in rows if r["kind"] == "fresh" and r["day"] >= afu.ANALYSIS_FROM)
    assert 0.1 * fresh_all < fresh_judged < 0.4 * fresh_all


def test_the_readings_find_that_thresholded_memory_helps_and_always_on_memory_harms(rows, tmp_path: Path) -> None:
    out = tmp_path / "j.jsonl"
    afu.judge_run(rows, out, fake_judge, workers=4, log=lambda line: None, controls_each=6)
    result = afu.judge_analysis(afu.load_jsonl(out), draws=300)
    assert result["informative"]["continuity"] and result["informative"]["fit"] and result["informative"]["fresh"]
    follow = result["contrasts"]["followup"]
    assert follow["A2-A0"]["continuity"]["mean"] == pytest.approx(2.0) and follow["A3-A2"]["continuity"]["mean"] == pytest.approx(0.0)
    assert result["contrasts"]["fresh"]["A1-A0"]["quality"]["mean"] < -0.5
    final = afu.final_readings({"fake": result})
    reading = final["per_judge"]["fake"]
    assert reading["memory_helps_where_relevant"] and sorted(reading["arms_that_gain"]) == ["A2", "A3"] and reading["fresh_quality_guard_holds"]
    assert reading["always_on_harms"] and reading["traces_vs_notes"] == "equivalent here"
    assert final["memory_helps_where_relevant"] is True and final["judges_disagree_on_help"] is False
    assert "Readings stated in advance" in afu.readings_report(final)


def test_a_judge_that_cannot_tell_a_copy_from_a_follow_up_is_not_used_for_a_reading() -> None:
    blind = [{"control": kind, "seed": 1, "arm": "A0", "day": 9 + i, "kind": "followup", "fit": 4, "fresh": 4, "continuity": 4, "quality": 4, "raw": ""}
             for kind in ("copy", "other") for i in range(6)]
    real = [{"control": None, "seed": 1, "arm": arm, "day": 8 + i, "kind": "followup", "fit": 4, "fresh": 4, "continuity": 4 + (arm == "A2"), "quality": 4, "raw": ""}
            for arm in ("A0", "A2") for i in range(8)]
    result = afu.judge_analysis(real + blind, draws=100)
    assert not result["informative"]["continuity"] and not afu.final_readings({"x": result})["per_judge"]["x"]["memory_helps_where_relevant"]


def test_measures_analysis_and_the_command_line_write_aggregates(rows, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    res = afu.measures_analysis(rows, FakeEmbedder(), draws=200)
    assert res["arms"] == list(fu.ARMS) and set(res["arm_means"]) == set(afu.KINDS)
    assert res["arm_means"]["fresh"]["A1"]["spurious_callback"] is not None and res["arm_means"]["followup"]["A2"]["grounded_callback"] is not None
    path = tmp_path / "records.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert afu.main(["measures", str(path), "--json", str(tmp_path / "m.json"), "--md", str(tmp_path / "m.md")], embedder=FakeEmbedder()) == 0
    capsys.readouterr()
    assert "provenance" in json.loads((tmp_path / "m.json").read_text(encoding="utf-8")) and "# AAM-E2-FU deterministic measures" in (tmp_path / "m.md").read_text(encoding="utf-8")
    assert afu.main(["measures", str(tmp_path / "missing.jsonl")], embedder=FakeEmbedder()) == 2
