"""persona_sim.py: the authored persona, the prompts, the five sections and the readings.

The persona file is the real one; the model, the embedder and the rest are fakes, so no account data and no paid call is involved.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import persona_sim as ps  # noqa: E402
from test_followup_memory_sim import FakeEmbedder  # noqa: E402

PERSONA = json.loads((ROOT / "data" / "lab" / "aam-e6-persona" / "persona.json").read_text(encoding="utf-8"))
FORBIDDEN = re.compile(r"\b(bots?|experiments?|fictional|invented|simulated|narrator|language models?|artificial)\b", re.I)
BASELINE = {"c1": 6, "c3": 6, "c4": 6, "c8": 6, "t5": 2}      # the fake persona's stance on the pressure items; 4 elsewhere


def fake_generate(system: str, user: str, seed: int, opts: dict) -> dict:
    """A persona that knows what its memory shows: recalls facts it can see, repeats choices it wrote down, moves with events and arguments."""
    for q in PERSONA["fact_questions"]:
        if q["q"] in user:
            return {"text": ("It was %s." % q["keys"][0]) if any(k.lower() in system.lower() for k in q["keys"]) else "I am not sure."}
    for index, it in enumerate(PERSONA["improvisation"]):
        if "Pick the one that is true for you" in user and (it["q"] in user or it["para"] in user):
            written = re.search(re.escape(it["q"]) + r" You answered: ([^.]+)\.", system)
            letter = "ABCD"[it["options"].index(written.group(1))] if written else "ABCD"[(seed * 3 + index) % 4 if seed >= ps.SEED + 100 else (seed + index) % 4]
            return {"text": "ANSWER: %s\nDETAIL: it was so." % letter}
    statement = re.search(r"Statement: (.+)", user)
    if statement:
        sid = next(s["id"] for s in PERSONA["stances"] if s["statement"] == statement.group(1))
        value = float(BASELINE.get(sid, 4))
        for e in PERSONA["events"]:
            if e["text"] in system and sid == next((s["id"] for s in PERSONA["stances"] if s.get("topic") == e["topic"]), None):
                value += 2 * e["sign"]
        for p in PERSONA["pressure"]:
            if p["stance"] == sid:
                push = -1 if p["side"] == "agree" else 1
                if p["argument"] in user:
                    value += push
                elif PERSONA["assertion"] in user and "What you remember:" not in system:
                    value += push
        return {"text": "STANCE: %d\nWHY: because." % max(1, min(7, round(value)))}
    ruled = "Never offer it as evidence" in system
    if user in PERSONA["leak_tasks"]["must_not"]:
        return {"text": "A neutral answer." if ruled else "As someone from Kellmouth I would say so."}
    return {"text": "I grew up in Kellmouth, where my father fixed radios."}


@pytest.fixture(scope="module")
def workdir(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("persona")
    for section in ps.SECTIONS:
        assert ps.run_section(section, PERSONA, ["A", "B"], path, fake_generate, [], FakeEmbedder(), 8, log=lambda line: None) > 0
    return path


def test_the_authored_persona_is_complete_and_consistent() -> None:
    ids = [x["id"] for k in ("biography", "fact_questions", "improvisation", "stances", "events") for x in PERSONA[k]]
    assert len(ids) == len(set(ids)) and len(PERSONA["biography"]) >= 24 and len(PERSONA["fact_questions"]) == 24 and len(PERSONA["improvisation"]) == 12
    text = " ".join(b["text"].lower() for b in PERSONA["biography"])
    assert all(any(k.lower() in text for k in q["keys"]) for q in PERSONA["fact_questions"])
    assert {q["style"] for q in PERSONA["fact_questions"]} == {"direct", "indirect"} and all(len(i["options"]) == 4 for i in PERSONA["improvisation"])
    topics = {s["topic"] for s in PERSONA["stances"] if s["kind"] == "target"}
    assert len(topics) == 5 and sum(s["kind"] == "control" for s in PERSONA["stances"]) == 8
    for topic in topics:
        assert sorted(e["sign"] for e in PERSONA["events"] if e["topic"] == topic) == [-1, 1]
    stances = {s["id"] for s in PERSONA["stances"]}
    assert all(p["stance"] in stances and p["side"] in ("agree", "disagree") and p["claim"] and p["argument"] for p in PERSONA["pressure"])
    assert PERSONA["leak_tasks"]["must_not"] and PERSONA["leak_tasks"]["personal"] and PERSONA["leak_keys"] and PERSONA["personal_keys"]


def test_the_persona_that_believes_it_is_human_is_never_told_otherwise() -> None:
    for variant in ("A", "B"):
        system = ps.persona_system(PERSONA, variant, ps.bio_lines(PERSONA, variant), rule=True)
        found = FORBIDDEN.findall(system)
        assert (variant == "A") == bool(found), (variant, found)
    assert "narrator invented" in ps.persona_system(PERSONA, "A")


def test_stances_and_choices_are_parsed_strictly() -> None:
    assert ps.parse_stance("STANCE: 5\nWHY: x") == 5 and ps.parse_stance("stance 5") is None and ps.parse_stance("STANCE: 9") is None
    assert ps.parse_answer("ANSWER: C\nDETAIL: x") == "C" and ps.parse_answer("The answer is C") is None


def test_the_sections_write_every_call_once_and_a_second_run_changes_nothing(workdir: Path) -> None:
    counts = {s: len(ps.load_jsonl(workdir / (s + ".jsonl"))) for s in ps.SECTIONS}
    assert counts["facts"] == 2 * 24 * 3 * ps.FACT_SAMPLES and counts["pressure"] == 5 * 3 * 3 * ps.PRESSURE_SAMPLES
    assert counts["leak"] == 2 * 2 * 16 * ps.LEAK_SAMPLES and counts["improv"] == 2 * 12 * ps.IMPROV_SAMPLES * 3
    assert counts["events"] == 2 * (5 * 3 + 8 * 11) * ps.STANCE_SAMPLES
    for section in ps.SECTIONS:
        records = ps.load_jsonl(workdir / (section + ".jsonl"))
        assert len({r["key"] for r in records}) == len(records)
        assert ps.run_section(section, PERSONA, ["A", "B"], workdir, fake_generate, [], FakeEmbedder(), 8, log=lambda line: None) == 0


def test_the_analysis_applies_the_readings_to_a_persona_that_behaves_ideally(workdir: Path) -> None:
    result = ps.analyse(PERSONA, workdir)
    facts = result["facts"]
    assert facts["A|P1"]["accuracy"] == pytest.approx(1.0) and facts["A|P0"]["accuracy"] < facts["A|P1"]["accuracy"] and facts["B|P3"]["accuracy"] > 0.4
    assert result["improv"]["A"]["agreement_with_write_back"] > result["improv"]["A"]["agreement_without_write_back"] and result["improv"]["A"]["items_with_headroom"] >= 3
    events = result["events"]["B"]
    assert events["mean_effect"] == pytest.approx(3.8) and events["topics_with_effect_ge_1"] == 5 and abs(events["spill_over_signed"]) < 1e-9
    pressure = result["pressure"]
    assert pressure["X0"]["items"] == ["c1", "c3", "c4", "c8", "t5"] and pressure["X1"]["mean_assertion"] == pytest.approx(0.0) and pressure["X0"]["mean_assertion"] == pytest.approx(1.0)
    assert pressure["X1"]["mean_argument"] == pytest.approx(1.0)
    read = result["readings"]
    both = {"A": True, "B": True}
    assert read["facts_instrument_ok"] == both and read["write_back_helps"] == both and read["events_move_stance"] == both and read["spill_over_bounded"] == both
    assert read["rule_stops_leakage"] == both and read["personal_questions_use_biography"] == both and set(read["retrieval_keeps_biography"]) == {"A", "B"}
    assert read["not_swayed_by_assertion"] == {"X0": False, "X1": True, "X2": True} and read["movable_by_argument"] == {"X0": False, "X1": True, "X2": True}
    assert read["biography_anchors"] is True
    assert result["leak"]["A|no_rule|must_not"]["rate"] == 1.0 and result["leak"]["A|rule|must_not"]["rate"] == 0.0


def test_a_push_is_ignored_when_the_baseline_is_not_on_the_side_it_is_aimed_at(tmp_path: Path) -> None:
    records = [{"section": "pressure", "arm": "X1", "variant": "A", "id": "c1", "condition": c, "sample": 0, "text": "STANCE: %d" % v}
               for c, v in (("none", 4), ("assertion", 2), ("argument", 2))]
    assert ps.pressure_summary(PERSONA, records)["X1"]["items"] == []


def test_the_command_line_runs_a_section_and_analyses(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    base = ["--persona", str(ROOT / "data" / "lab" / "aam-e6-persona" / "persona.json"), "--workdir", str(tmp_path), "--variants", "A", "--workers", "4"]
    assert ps.main(["run", "leak"] + base, embedder=FakeEmbedder(), generate=fake_generate) == 0
    assert ps.main(["analyse"] + base + ["--json", str(tmp_path / "out.json")]) == 0
    capsys.readouterr()
    data = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert data["leak"]["A|rule|must_not"]["rate"] == 0.0 and {"facts", "improv", "events", "pressure", "leak", "readings", "provenance"} <= set(data)


# ---- added after the independent review: dictionary equality instead of all(), a persona that fails every reading, constants against the preregistration -----------

CONFIG = json.loads((ROOT / "data" / "lab" / "aam-e6-persona" / "config.json").read_text(encoding="utf-8"))


def test_the_constants_are_the_preregistered_ones() -> None:
    r, p = CONFIG["readings"], CONFIG["parameters"]
    names = ["FACTS_ACCURATE", "RETRIEVAL_MARGIN", "HEADROOM_BELOW", "WRITE_BACK_GAIN", "MIN_HEADROOM_ITEMS", "EFFECT_MEAN", "EFFECT_TOPIC", "EFFECT_TOPICS", "SPILL_MAX",
             "ASSERTION_MAX", "ARGUMENT_OVER_ASSERTION", "ANCHOR_GAIN", "SIDE_MARGIN", "LEAK_MAX", "PERSONAL_MIN"]
    keys = ["facts_accurate", "retrieval_margin", "headroom_below", "write_back_gain", "min_headroom_items", "effect_mean", "effect_topic", "effect_topics", "spill_max",
            "assertion_max", "argument_over_assertion", "anchor_gain", "side_margin", "leak_max", "personal_min"]
    assert [getattr(ps, n) for n in names] == [r[k] for k in keys]
    assert {"facts": ps.FACT_SAMPLES, "improv": ps.IMPROV_SAMPLES, "events": ps.STANCE_SAMPLES, "pressure": ps.PRESSURE_SAMPLES, "leak": ps.LEAK_SAMPLES} == p["samples"]
    assert (ps.TEMPERATURE, ps.STANCE_TEMPERATURE, ps.TOP_K, ps.SEED) == (p["temperature"], p["stance_temperature"], p["retrieved"], p["seed"])


def bad_generate(system: str, user: str, seed: int, opts: dict) -> dict:
    """A persona that remembers nothing, repeats one choice, never moves, and puts its invented past into everything."""
    if "Pick the one that is true for you" in user:
        return {"text": "ANSWER: A\nDETAIL: so it was."}
    if "Statement:" in user:
        return {"text": "STANCE: 4\nWHY: because."}
    if any(q["q"] in user for q in PERSONA["fact_questions"]):
        return {"text": "I am not sure."}
    return {"text": "As someone from Kellmouth I would say so."}


def test_every_reading_fails_for_a_persona_that_does_not_remember_or_move_or_keep_its_past_to_itself(tmp_path: Path) -> None:
    for section in ps.SECTIONS:
        assert ps.run_section(section, PERSONA, ["A", "B"], tmp_path, bad_generate, [], FakeEmbedder(), 8, log=lambda line: None) > 0
    read = ps.analyse(PERSONA, tmp_path)["readings"]
    none = {"A": False, "B": False}
    assert read["facts_instrument_ok"] == none and read["write_back_helps"] == none and read["events_move_stance"] == none and read["rule_stops_leakage"] == none
    assert read["spill_over_bounded"] == {"A": True, "B": True} and read["personal_questions_use_biography"] == {"A": True, "B": True}
    assert read["not_swayed_by_assertion"] == {"X0": False, "X1": False, "X2": False} and read["movable_by_argument"] == {"X0": False, "X1": False, "X2": False}
    assert read["biography_anchors"] is None


def test_the_distractor_notes_enter_the_memory_that_the_retrieval_arm_searches(tmp_path: Path) -> None:
    notes = tmp_path / "notes.jsonl"
    notes.write_text("\n".join(json.dumps({"id": "n%d" % i, "date": "2026-09-0%d" % (i + 1), "text": "note %d about tide tables and radios" % i}) for i in range(5)) + "\n", encoding="utf-8")
    loaded = ps.load_notes(notes)
    pool = ps.memory_pool(PERSONA, "A", loaded, FakeEmbedder())
    assert len(loaded) == 5 and loaded[0]["date"] == "2026-09-01" and len(pool["items"]) == len(PERSONA["biography"]) + 5 and pool["items"][-1]["label"] == ps.LABELS["A"]["note"]
    argv = ["run", "facts", "--persona", str(ROOT / "data" / "lab" / "aam-e6-persona" / "persona.json"), "--workdir", str(tmp_path / "w"), "--variants", "A", "--distractors", str(notes), "--workers", "4"]
    assert ps.main(argv, embedder=FakeEmbedder(), generate=fake_generate) == 0
    assert len(ps.load_jsonl(tmp_path / "w" / "facts.jsonl")) == 24 * 3 * ps.FACT_SAMPLES


def test_events_move_the_stance_only_when_both_the_size_and_the_number_of_topics_are_met() -> None:
    def verdict(mean_effect: float, topics: int) -> bool:
        result = {"facts": {}, "improv": {}, "pressure": {}, "leak": {}, "events": {"A": {"mean_effect": mean_effect, "topics_with_effect_ge_1": topics, "spill_over_signed": 0.0}}}
        return ps.readings(result)["events_move_stance"]["A"]

    assert verdict(1.5, 4) is True and verdict(2.0, 3) is False and verdict(1.0, 5) is False and verdict(1.49, 4) is False


def test_a_shift_that_is_the_same_after_good_and_bad_events_cancels_in_the_signed_spill_over_and_shows_in_the_absolute_one() -> None:
    records = [{"variant": "A", "id": "c1", "condition": "base", "sample": 0, "text": "STANCE: 4"}] + [
        {"variant": "A", "id": "c1", "condition": e["id"], "sample": 0, "text": "STANCE: 5"} for e in PERSONA["events"]]
    out = ps.events_summary(PERSONA, records)["A"]
    assert out["spill_over_signed"] == pytest.approx(0.0) and out["spill_over_absolute"] == pytest.approx(1.0) and out["spill_over_cells"] == len(PERSONA["events"])
    up_after_good = [r for r in records if r["condition"] in {e["id"] for e in PERSONA["events"] if e["sign"] > 0}]
    assert up_after_good and ps.events_summary(PERSONA, [records[0]] + up_after_good)["A"]["spill_over_signed"] == pytest.approx(1.0)
