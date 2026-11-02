"""Tests for corpus.lifesim.scorers (step D1-D): the closed-vocabulary candidate-set rule, the time,
number, date, letter and UNKNOWN parsers, the CONF field, and the cluster bootstrap.

The adversarial set at the bottom is a hand-labelled table of answers whose labels were written
from the specification before the scorer was run. Standard library and pytest only."""

from __future__ import annotations

import dataclasses
import math
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import rng as R  # noqa: E402
from corpus.lifesim import schema as S  # noqa: E402
from corpus.lifesim import scorers as SC  # noqa: E402
from corpus.lifesim import vocab as V  # noqa: E402
from corpus.lifesim.schema import Entity, Gold, NearMiss, Query, Tags, TierCfg, World  # noqa: E402

# ------------------------------------------------------------------------------- fixtures

WORLD = World(seed=0, cfg=TierCfg(), entities=(
    Entity(eid="e0001", kind="city", name="Karmont"),
    Entity(eid="e0002", kind="city", name="Verdton", aliases=("Verd",)),
    Entity(eid="e0003", kind="city", name="Dorndam"),
    Entity(eid="e0004", kind="person", name="Mirela"),
    Entity(eid="e0005", kind="person", name="Dana"),
    Entity(eid="e0006", kind="person", name="Imre"),
))


def mk(kind, gold, vid, near=(), fmt="open", options=(), family="EP1", delay=0, conf=True):
    return Query(qid="q0001", family=family, t_ask=1000, text="", fmt=fmt,
                 gold=Gold(kind=kind, value=gold, vocab_id=vid,
                           near_miss=tuple(NearMiss(kind=k, value=v) for k, v in near)),
                 options=tuple(options), tags=Tags(delay_days=delay), conf=conf)


QUERIES = {
    "dish": mk("entity", "porridge", "pool:dishes",
               [("adjacent_day", "croissant"), ("confuser", "kippers"), ("habit", "toast with jam")]),
    "city_k": mk("entity", "Karmont", "kind:city", [("stale", "Verdton")]),
    "city_v": mk("entity", "Verdton", "kind:city"),
    "person": mk("entity", "Mirela", "kind:person", [("confuser", "Dana")]),
    "grey": mk("entity", "grey", "pool:colours"),
    "navy": mk("entity", "navy", "pool:colours"),
    "t1800": mk("time", "18:00", "pool:times", [("confuser", "17:15")], family="IN4"),
    "t1830": mk("time", "18:30", "pool:times", family="IN4"),
    "t1845": mk("time", "18:45", "pool:times", family="IN4"),
    "t1815": mk("time", "18:15", "pool:times", family="IN4"),
    "t1715": mk("time", "17:15", "pool:times", family="IN4"),
    "t1945": mk("time", "19:45", "pool:times", family="IN4"),
    "t1400": mk("time", "14:00", "pool:times", family="IN4"),
    "c3": mk("count", "3", "pool:counts", [("adjacent_day", "4")], family="EP3c"),
    "c1": mk("count", "1", "pool:counts", family="EP3c"),
    "c2": mk("count", "2", "pool:counts", family="EP3c"),
    "c21": mk("count", "21", "pool:counts", family="EP3c"),
    "c0": mk("count", "0", "pool:counts", family="EP3c"),
    "me1": mk("unknown", "UNKNOWN", "pool:dishes", [("adjacent_day", "croissant")], family="ME1"),
    "choice": mk("entity", "blue", "pool:colours", fmt="choice", options=("red", "blue", "green", "grey")),
    "date": mk("date", "2027-03-14", "", family="EP3a", delay=100),
    "letter": mk("letter", "C", "", fmt="choice", options=("w", "x", "y", "z"), family="AU3"),
    "bool": mk("bool", "yes", "", family="FM1"),
}


def run(key, answer):
    return SC.score(QUERIES[key], answer, world=WORLD)


# --------------------------------------------------------------------------- normaliser


def test_normalise_is_the_vocabulary_normaliser():
    assert SC.normalise is V.norm
    assert SC.normalise("  Caf\u00e9  -- Cr\u00e8me, \u00c0 LA carte! ") == "cafe creme a la carte"
    assert SC.normalise("\uff21\uff22\uff23 18:00") == "abc 18 00"      # NFKC folds full-width letters
    assert SC.normalise("") == ""


# ------------------------------------------------------------------------ reply parsing

PARSE_CASES = [
    # text, body, conf, conf_found, parse_ok
    ("porridge CONF: 85", "porridge", 85, True, True),
    ("porridge\nCONF: 85", "porridge", 85, True, True),
    ("porridge. CONF=85%", "porridge.", 85, True, True),
    ("porridge (confidence 70/100)", "porridge", 70, True, True),
    ("porridge [conf: 15]", "porridge", 15, True, True),
    ("conf 40 porridge", "porridge", 40, True, True),
    ("porridge CONF: 100", "porridge", 100, True, True),
    ("porridge CONF: 0", "porridge", 0, True, True),
    ("porridge CONFIDENCE: 5", "porridge", 5, True, True),
    ("porridge CONF: 85.5", "porridge", 86, True, True),
    ("Answer: porridge\nCONF: 20\nCONF: 90", "Answer: porridge", 90, True, True),
    ("CONF: 0", "", 0, True, False),
    ("porridge CONF: 101", "porridge", None, True, False),
    ("porridge CONF: 0.85", "porridge", None, True, False),
    ("porridge CONF: 0-100", "porridge CONF: 0-100", None, False, False),
    ("porridge CONF: 1234", "porridge CONF: 1234", None, False, False),
    ("porridge", "porridge", None, False, False),
    ("the conference room", "the conference room", None, False, False),
    ("", "", None, False, False),
]


@pytest.mark.parametrize("text,body,conf,found,ok", PARSE_CASES)
def test_parse_answer(text, body, conf, found, ok):
    p = SC.parse_answer(text)
    assert (p.body, p.conf, p.conf_found, p.parse_ok) == (body, conf, found, ok)


def test_parse_answer_without_a_conf_requirement():
    assert SC.parse_answer("porridge", conf_required=False).parse_ok is True
    assert SC.parse_answer("  ", conf_required=False).parse_ok is False


# ----------------------------------------------------------------------------- times

TIME_CASES = [
    ("18:00", ["18:00"]), ("6pm", ["18:00"]), ("6 PM", ["18:00"]), ("6 p.m.", ["18:00"]),
    ("6:30 pm", ["18:30"]), ("at 6.15pm", ["18:15"]), ("6:30", ["18:30"]), ("1830 hrs", ["18:30"]),
    ("six in the evening", ["18:00"]), ("six o'clock", ["18:00"]), ("6 o'clock", ["18:00"]),
    ("half past six", ["18:30"]), ("quarter past six", ["18:15"]), ("quarter to seven", ["18:45"]),
    ("ten past six", ["18:10"]), ("twenty to seven", ["18:40"]), ("six thirty", ["18:30"]),
    ("six forty-five", ["18:45"]), ("seven fifteen in the evening", ["19:15"]),
    ("5 o'clock in the afternoon", ["17:00"]), ("half past six in the morning", ["06:30"]),
    ("nine in the morning", ["09:00"]), ("8am", ["08:00"]), ("08:00", ["08:00"]), ("12:30", ["12:30"]),
    ("12 pm", ["12:00"]), ("12am", ["00:00"]), ("noon", ["12:00"]), ("midnight", ["00:00"]),
    ("6pm or 7:30pm", ["18:00", "19:30"]), ("7:30pm and 6pm", ["19:30", "18:00"]),
    ("6pm, that is 18:00", ["18:00"]), ("2 in the afternoon", []), ("two in the afternoon", ["14:00"]),
    ("13:00", ["13:00"]), ("13:45", ["13:45"]), ("1pm", ["13:00"]), ("23:15", ["23:15"]), ("0:30", ["00:30"]),
    ("the 14th of March", []), ("2027-03-14", []), ("14.03.2027", []), ("I have 3 apples", []),
    ("at 6", []), ("in 2027", []), ("around six", []), ("", []),
    ("on 2027-03-14 it closes at 6pm", ["18:00"]),
]


@pytest.mark.parametrize("text,expected", TIME_CASES)
def test_parse_times(text, expected):
    assert SC.parse_times(text) == expected


def test_parse_times_prefer_pm_switch():
    assert SC.parse_times("6:30", prefer_pm=False) == ["06:30"]
    assert SC.parse_times("6:30 am") == ["06:30"]


def test_every_pool_time_survives_every_surface_form():
    for t in V.TIMES:
        h, m = int(t[:2]), int(t[3:])
        h12 = h - 12
        forms = [t, "%d:%02d pm" % (h12, m), "%d:%02dpm" % (h12, m), "%d.%02d pm" % (h12, m), "%d:%02d" % (h12, m),
                 "at %s on Saturdays" % t]
        if m == 0:
            forms += ["%dpm" % h12, "%d pm" % h12, "%d o'clock" % h12]
        if m == 30:
            forms.append("half past %s" % V.NUMBER_WORDS[h12])
        for f in forms:
            assert SC.parse_times(f) == [t], (t, f)


# --------------------------------------------------------------------------- numbers

NUMBER_CASES = [
    ("3", [3]), ("three", [3]), ("I went 3 times", [3]), ("twenty-one", [21]), ("twenty one", [21]),
    ("twenty", [20]), ("ninety nine", [99]), ("twice", [2]), ("once", [1]), ("once or twice", [1, 2]),
    ("2027-03-14", []), ("on 14 March 2027 I went twice", [2]), ("18:00", []), ("3.5", [3.5]),
    ("3.0", [3]), ("3rd", []), ("b12", []), ("zero", [0]), ("none", []), ("a dozen", []),
    ("between 2027-02-01 and 2027-04-01 I went 3 times", [3]), ("3 and 4", [3, 4]), ("", []),
    ("seventeen visits", [17]), ("I went 24 times.", [24]), ("14/03/2027 was the 2nd visit", []),
]


@pytest.mark.parametrize("text,expected", NUMBER_CASES)
def test_parse_numbers(text, expected):
    assert SC.parse_numbers(text) == expected


def test_parse_integers_drops_fractions():
    assert SC.parse_integers("3.5 or 4") == [4]


def test_every_pool_count_is_parsed_from_digits_and_words():
    for i in range(1, 25):
        assert SC.parse_integers(str(i)) == [i]
        assert SC.parse_integers(V.NUMBER_WORDS[i]) == [i]
        assert SC.parse_integers(V.NUMBER_WORDS[i].replace(" ", "-")) == [i]


# ----------------------------------------------------------------------------- dates

DATE_CASES = [
    ("2027-03-14", ["2027-03-14"]), ("14 March 2027", ["2027-03-14"]), ("March 14th, 2027", ["2027-03-14"]),
    ("the 14th of March 2027", ["2027-03-14"]), ("14/03/2027", ["2027-03-14"]), ("14.03.2027", ["2027-03-14"]),
    ("03/14/2027", ["2027-03-14"]), ("2027/03/14", ["2027-03-14"]), ("14 Mar 2027", ["2027-03-14"]),
    ("2027-03-14 and 2027-03-15", ["2027-03-14", "2027-03-15"]), ("14 March", []),
    ("31 February 2027", []), ("2027-13-01", []), ("sometime in March", []),
]


@pytest.mark.parametrize("text,expected", DATE_CASES)
def test_parse_dates(text, expected):
    assert SC.parse_dates(text) == expected


def test_parse_dates_default_year():
    assert SC.parse_dates("14 March", default_year=2027) == ["2027-03-14"]
    assert SC.parse_dates("March 14th", default_year=2028) == ["2028-03-14"]


# ------------------------------------------------------------ letters, yes/no, abstention


@pytest.mark.parametrize("text,expected", [
    ("B", ["B"]), ("(b)", ["B"]), ("B)", ["B"]), ("b.", ["B"]), ("B) blue", ["B"]), ("The answer is B", ["B"]),
    ("option c", ["C"]), ("I choose D", ["D"]), ("B or C", ["B", "C"]), ("A, B and D", ["A", "B", "D"]),
    ("b/c", ["B", "C"]), ("A dog barked", []), ("I think so", []), ("blue", []), ("E", []), ("", []),
])
def test_parse_letters(text, expected):
    assert SC.parse_letters(text, 4) == expected


def test_parse_letters_respects_the_number_of_options():
    assert SC.parse_letters("D", 3) == [] and SC.parse_letters("C", 3) == ["C"]


@pytest.mark.parametrize("text,expected", [
    ("yes", ["yes"]), ("No.", ["no"]), ("yes and no", ["yes", "no"]), ("Yes, it did", ["yes"]),
    ("never", []), ("not really", []), ("", []),
])
def test_parse_yes_no(text, expected):
    assert SC.parse_yes_no(text) == expected


@pytest.mark.parametrize("text", [
    "UNKNOWN", "unknown", "Unknown.", "I don't know", "I do not know", "Don't know.", "I dont know",
    "I can't recall", "I cannot remember", "I don't remember that", "That was never mentioned",
    "There is no record of this", "You never told me", "no information", "I have no idea",
    "Not stated", "I'm unable to determine that", "There was no such trip", "Not in my notes",
])
def test_abstention_lexicon_strong(text):
    assert SC.is_abstention(text) and SC.is_abstention(text, has_candidates=True)


@pytest.mark.parametrize("text", [
    "porridge", "I know it was porridge", "no", "known", "knowledge", "nothing special", "not the red one",
    "He remembered it well", "", "I recall porridge",
])
def test_abstention_lexicon_negatives(text):
    assert not SC.is_abstention(text)


def test_weak_doubt_is_an_abstention_only_without_a_candidate():
    assert SC.is_abstention("not sure") and not SC.is_abstention("not sure", has_candidates=True)
    assert SC.is_abstention("I'm not sure") and SC.is_abstention("unsure")


# ------------------------------------------------------------------------------ scoring


def test_the_closed_vocabulary_rule_in_one_place():
    r = run("dish", "porridge CONF: 90")
    assert (r.correct, r.score, r.error_type, r.candidates, r.conf, r.parse_ok) == (True, 1.0, "", ("porridge",), 90, True)
    assert r.cost_weighted == 1.0 and not r.hedged and not r.unmatched and not r.abstained
    h = run("dish", "porridge or croissant")
    assert (h.correct, h.hedged, h.error_type, h.candidates) == (False, True, "hedge", ("porridge", "croissant"))
    assert h.cost_weighted == -1.0
    u = run("dish", "pizza")
    assert (u.correct, u.unmatched, u.error_type, u.candidates) == (False, True, "unmatched", ())
    w = run("dish", "kippers")
    assert (w.correct, w.error_type, w.hedged, w.unmatched) == (False, "confuser", False, False)


def test_error_types_come_from_the_near_miss_list():
    assert run("dish", "croissant").error_type == "adjacent_day"
    assert run("dish", "toast with jam").error_type == "habit"
    assert run("dish", "fruit salad").error_type == "commission"          # a pool value, but no listed trap
    assert run("city_k", "Verdton").error_type == "stale"
    assert run("c3", "4").error_type == "adjacent_day"
    assert run("t1800", "5:15 pm").error_type == "confuser"
    assert run("t1800", "6:15 pm").error_type == "commission"


def test_entity_hedges_need_the_world_vocabulary():
    q = QUERIES["city_k"]
    assert SC.score(q, "Karmont or Dorndam", world=WORLD).hedged
    scorer = SC.Scorer(WORLD)
    assert scorer.score(q, "Karmont or Dorndam").error_type == "hedge"
    assert scorer.vocab_for(q) is scorer.vocab_for(QUERIES["city_v"])         # cached per vocabulary id
    # Without a world only the gold, the near misses and the options are known: the limitation is real.
    assert SC.score(q, "Karmont or Dorndam").correct is True
    assert SC.score(q, "Karmont or Verdton").hedged
    explicit = V.kind_vocab(WORLD, "city")
    assert SC.score(q, "Karmont or Dorndam", vocab=explicit).hedged


def test_accents_case_punctuation_and_aliases():
    for ans in ("karmont", "KARMONT.", "Karm\u00f3nt", "I live in Karmont now", "Karmont!!!"):
        assert run("city_k", ans).correct, ans
    assert run("city_v", "Verd").correct and run("city_v", "Verdton (Verd)").correct
    assert run("grey", "gray").correct and run("grey", "It was a Gray car").correct
    assert run("navy", "navy blue").correct and not run("navy", "blue").correct
    assert run("dish", "oatmeal").correct


def test_list_punctuation_separates_candidates_but_other_punctuation_does_not():
    assert run("grey", "silver grey").candidates == ("silver",)            # an alias of silver
    r = run("grey", "silver, grey")
    assert r.hedged and r.candidates == ("silver", "grey")
    r = run("navy", "navy, blue")
    assert r.hedged and not r.correct
    assert run("navy", "navy-blue").correct and run("navy", "navy/blue").hedged
    assert run("navy", "Navy blue.").correct and run("navy", "(navy blue)").correct
    assert run("dish", "porridge; croissant").hedged and run("dish", "porridge\ncroissant").hedged
    assert run("city_v", "Verdton (Verd)").candidates == ("Verdton",)


def test_longest_match_beats_the_shorter_value_inside_it():
    r = run("grey", "charcoal grey")                   # an alias of charcoal, not of grey
    assert not r.correct and r.candidates == ("charcoal",)
    r = run("navy", "navy blue or black")
    assert r.hedged and r.candidates == ("navy", "black")


def test_abstention_on_an_answerable_item_is_an_omission_with_zero_cost():
    for ans in ("UNKNOWN", "I don't know", "not sure"):
        r = run("dish", ans)
        assert (r.correct, r.abstained, r.error_type, r.cost_weighted) == (False, True, "omission", 0.0)
    r = run("dish", "I don't recall, maybe porridge")
    assert (r.correct, r.hedged, r.abstained, r.error_type) == (False, True, True, "hedge")
    assert run("dish", "porridge, not sure").correct


def test_me1_scoring_and_the_cost_weighted_rule():
    ok = run("me1", "UNKNOWN CONF: 95")
    assert (ok.correct, ok.abstained, ok.cost_weighted, ok.conf, ok.error_type) == (True, True, 1.0, 95, "")
    for ans in ("Unknown.", "I don't know.", "I do not recall.", "You never told me.", "There is no record of that.", "not sure"):
        assert run("me1", ans).correct, ans
    bad = run("me1", "I had croissant")
    assert (bad.correct, bad.error_type, bad.cost_weighted, bad.candidates) == (False, "hallucination_on_abstain", -1.0, ("croissant",))
    assert run("me1", "porridge").error_type == "hallucination_on_abstain"
    assert run("me1", "It was nice").error_type == "hallucination_on_abstain"
    hedge = run("me1", "UNKNOWN, maybe croissant")
    assert (hedge.correct, hedge.hedged, hedge.error_type, hedge.cost_weighted) == (False, True, "hedge", -1.0)
    empty = run("me1", "")
    assert (empty.correct, empty.error_type, empty.parse_ok, empty.cost_weighted) == (False, "parse_failure", False, 0.0)


def test_always_abstain_scores_the_abstain_share_and_always_answering_is_punished():
    items = [("dish", "porridge")] * 8 + [("me1", "UNKNOWN")] * 2
    recs = [run(k, "UNKNOWN") for k, _ in items]
    assert sum(r.correct for r in recs) / 10 == pytest.approx(0.2)
    assert sum(r.cost_weighted for r in recs) / 10 == pytest.approx(0.2)
    guess = [run(k, "porridge") for k, _ in items]
    assert sum(r.cost_weighted for r in guess) / 10 == pytest.approx((8 - 2) / 10)
    wrong = [run("dish", "kippers")] * 5
    assert sum(r.cost_weighted for r in wrong) / 5 == -1.0


def test_conf_field_never_changes_correctness():
    assert run("dish", "porridge").correct and run("dish", "porridge").parse_ok is False       # missing CONF
    r = run("dish", "porridge CONF: 150")
    assert r.correct and r.conf is None and r.parse_ok is False
    r = SC.score(dataclasses.replace(QUERIES["dish"], conf=False), "porridge", world=WORLD)
    assert r.correct and r.parse_ok is True and r.conf is None
    r = run("dish", "kippers CONF: 99")
    assert not r.correct and r.conf == 99


def test_answer_objects_and_flags():
    la = S.LifeAnswer(text="porridge", confidence=77)
    r = SC.score(QUERIES["dish"], la, world=WORLD)
    assert r.correct and r.conf == 77 and r.parse_ok
    r = SC.score(QUERIES["dish"], S.LifeAnswer(text="porridge CONF: 40", confidence=77), world=WORLD)
    assert r.conf == 40                                  # the field in the text wins
    r = SC.score(QUERIES["dish"], S.LifeAnswer(text="", abstained=True), world=WORLD)
    assert (r.correct, r.error_type, r.abstained, r.parse_ok is False) == (False, "omission", True, True)
    r = SC.score(QUERIES["me1"], S.LifeAnswer(text="", abstained=True, confidence=10), world=WORLD)
    assert r.correct and r.cost_weighted == 1.0
    with pytest.raises(TypeError):
        SC.score(QUERIES["dish"], 42, world=WORLD)


def test_empty_replies_are_parse_failures_not_wrong_answers_of_a_kind():
    for ans in ("", "   ", "CONF: 80", "\n"):
        r = run("dish", ans)
        assert (r.correct, r.error_type, r.parse_ok, r.cost_weighted) == (False, "parse_failure", False, 0.0)


def test_counts_use_exactly_one_integer_and_log_the_error_size():
    for ans in ("3", "three", "Three times.", "3 times CONF: 60", "I went to the dentist 3 times between 2027-02-01 and 2027-04-01"):
        assert run("c3", ans).correct, ans
    r = run("c3", "2")
    assert (r.correct, r.abs_error, r.within_one, r.error_type) == (False, 1.0, True, "commission")
    r = run("c3", "7")
    assert (r.abs_error, r.within_one) == (4.0, False)
    for ans, err, near in (("5", 2.0, False), ("1", 2.0, False), ("4", 1.0, True)):
        r = run("c3", ans)
        assert (r.abs_error, r.within_one) == (err, near), ans
    for ans in ("3 or 4", "three or four", "3 times (once in Feb, twice in Mar)"):
        r = run("c3", ans)
        assert r.hedged and not r.correct and r.abs_error is None and r.within_one is None
    assert run("c3", "a few").unmatched and run("c3", "none").unmatched
    assert run("c1", "once").correct and run("c2", "twice").correct and run("c0", "zero").correct
    assert run("c21", "twenty-one").correct and run("c21", "twenty one").correct and not run("c21", "twenty").correct
    assert run("c3", "3.0").correct and not run("c3", "3.5").correct


def test_times_are_normalised_before_the_exact_match():
    for ans in ("18:00", "6pm", "6 pm", "6:00 PM", "6 p.m.", "six in the evening", "six o'clock", "6 o'clock",
                "18.00", "1800 hrs", "it closes at 18:00 on Saturdays", "6:00"):
        assert run("t1800", ans).correct, ans
    assert run("t1830", "half past six").correct and run("t1830", "6:30").correct
    assert run("t1845", "quarter to seven").correct and run("t1815", "quarter past six").correct
    assert run("t1715", "5:15pm").correct and run("t1945", "7:45 in the evening").correct
    assert run("t1400", "2pm").correct and run("t1400", "two in the afternoon").correct
    assert not run("t1400", "noon").correct and not run("t1830", "06:30").correct
    assert run("t1800", "6pm or 7pm").hedged and run("t1800", "at 6").unmatched
    r = run("t1800", "5pm")
    assert not r.correct and not r.unmatched and r.candidates == ("17:00",)
    assert run("t1800", "UNKNOWN").error_type == "omission"


def test_forced_choice_accepts_letters_and_option_text_alike():
    for ans in ("B", "(b)", "B) blue", "blue", "The answer is B", "B CONF: 70", "Blue."):
        assert run("choice", ans).correct, ans
    r = run("choice", "A")
    assert not r.correct and r.candidates == ("red",) and r.error_type == "commission"
    assert run("choice", "E").unmatched
    for ans in ("blue or green", "B or C", "blue, green"):
        assert run("choice", ans).hedged, ans
    assert run("choice", "green").candidates == ("green",)
    assert run("choice", "B) green").hedged                      # letter and text disagree
    assert run("choice", "B) blue").candidates == ("blue",)
    assert run("choice", "grey").candidates == ("grey",) and run("choice", "gray").candidates == ("grey",)


def test_dates_score_exact_one_and_near_half_with_the_error_in_days():
    for ans in ("2027-03-14", "14 March 2027", "March 14th, 2027", "14/03/2027", "14.03.2027"):
        r = run("date", ans)
        assert r.correct and r.score == 1.0 and r.abs_error == 0.0, ans
    r = run("date", "2027-03-15")
    assert (r.correct, r.score, r.abs_error, r.within_one) == (False, 0.5, 1.0, True)
    r = run("date", "2027-03-24")                              # delay 100 d: tolerance max(1, 10) = 10 days
    assert (r.score, r.abs_error) == (0.5, 10.0)
    r = run("date", "2027-03-25")
    assert (r.score, r.abs_error, r.within_one) == (0.0, 11.0, False)
    assert run("date", "2027-03-14 or 2027-03-15").hedged and run("date", "sometime in March").unmatched


def test_letters_and_booleans():
    assert run("letter", "C").correct and run("letter", "the answer is c").correct and run("letter", "(C) y").correct
    assert not run("letter", "B").correct and run("letter", "B or C").hedged and run("letter", "none").unmatched
    assert run("bool", "Yes").correct and not run("bool", "no").correct and run("bool", "yes and no").hedged
    assert run("bool", "maybe").unmatched


def test_score_records_round_trip_through_json():
    for key, ans in (("dish", "porridge CONF: 90"), ("c3", "3 or 4"), ("me1", "UNKNOWN"), ("date", "2027-03-15")):
        r = run(key, ans)
        assert S.ScoreRecord.from_json(r.to_json()) == r


def test_scoring_is_deterministic_and_independent_of_other_answers():
    first = [run("dish", a) for a in ("porridge", "kippers", "porridge or kippers")]
    again = [run("dish", a) for a in ("porridge", "kippers", "porridge or kippers")]
    assert first == again


# --------------------------------------------------------------------- the adversarial set
# Hand-labelled before the scorer ran: (query key, reply, correct, error_type). 100+ items.

ADVERSARIAL = [
    # dish: porridge (traps: croissant adjacent_day, kippers confuser, toast with jam habit)
    ("dish", "porridge", True, ""), ("dish", "Porridge.", True, ""), ("dish", "I had porridge for breakfast.", True, ""),
    ("dish", "oatmeal", True, ""), ("dish", "PORRIDGE!!!", True, ""), ("dish", "porridge CONF: 90", True, ""),
    ("dish", "porridge, I think", True, ""), ("dish", "The answer is porridge", True, ""),
    ("dish", "croissant", False, "adjacent_day"), ("dish", "kippers", False, "confuser"),
    ("dish", "toast with jam", False, "habit"), ("dish", "pizza", False, "unmatched"),
    ("dish", "porridge or croissant", False, "hedge"), ("dish", "croissant or porridge", False, "hedge"),
    ("dish", "porridge and toast with jam", False, "hedge"), ("dish", "I don't know", False, "omission"),
    ("dish", "UNKNOWN", False, "omission"), ("dish", "", False, "parse_failure"), ("dish", "   ", False, "parse_failure"),
    ("dish", "CONF: 80", False, "parse_failure"), ("dish", "not sure", False, "omission"),
    ("dish", "porridge, not sure", True, ""), ("dish", "I don't recall, maybe porridge", False, "hedge"),
    ("dish", "poridge", False, "unmatched"), ("dish", "porridges", False, "unmatched"),
    ("dish", "fruit salad", False, "commission"),
    # cities and people from the world vocabulary
    ("city_k", "karmont", True, ""), ("city_k", "Karm\u00f3nt", True, ""), ("city_k", "KARMONT.", True, ""),
    ("city_k", "I live in Karmont now", True, ""), ("city_k", "Verdton", False, "stale"),
    ("city_k", "Karmont or Verdton", False, "hedge"), ("city_k", "Dorndam", False, "commission"),
    ("city_k", "Atlantis", False, "unmatched"), ("city_k", "Verd", False, "stale"),
    ("city_v", "Verd", True, ""), ("city_v", "Verdton (Verd)", True, ""), ("city_v", "Karmont", False, "commission"),
    ("person", "With Mirela", True, ""), ("person", "Dana", False, "confuser"), ("person", "Mirela and Dana", False, "hedge"),
    ("person", "Imre", False, "commission"), ("person", "nobody", False, "unmatched"),
    # colours
    ("grey", "grey", True, ""), ("grey", "gray", True, ""), ("grey", "Gray.", True, ""), ("grey", "It was a gray car", True, ""),
    ("grey", "silver", False, "commission"), ("grey", "grey and white", False, "hedge"), ("grey", "dark grey", True, ""),
    ("grey", "charcoal grey", False, "commission"), ("grey", "greyish", False, "unmatched"),
    ("navy", "navy blue", True, ""), ("navy", "blue", False, "commission"), ("navy", "navy blue or black", False, "hedge"),
    # closing times
    ("t1800", "18:00", True, ""), ("t1800", "6pm", True, ""), ("t1800", "6 pm", True, ""), ("t1800", "6:00 PM", True, ""),
    ("t1800", "6 p.m.", True, ""), ("t1800", "six in the evening", True, ""), ("t1800", "six o'clock", True, ""),
    ("t1800", "6 o'clock", True, ""), ("t1800", "18.00", True, ""), ("t1800", "it closes at 18:00 on Saturdays", True, ""),
    ("t1800", "at 6", False, "unmatched"), ("t1800", "5pm", False, "commission"), ("t1800", "6pm or 7pm", False, "hedge"),
    ("t1800", "I think it closes around six", False, "unmatched"), ("t1800", "UNKNOWN", False, "omission"),
    ("t1800", "5:15 pm", False, "confuser"), ("t1830", "half past six", True, ""), ("t1830", "6:30", True, ""),
    ("t1830", "06:30", False, "commission"), ("t1845", "quarter to seven", True, ""), ("t1815", "quarter past six", True, ""),
    ("t1715", "5:15pm", True, ""), ("t1945", "7:45 in the evening", True, ""), ("t1400", "2pm", True, ""),
    ("t1400", "two in the afternoon", True, ""), ("t1400", "noon", False, "commission"),
    # counts
    ("c3", "3", True, ""), ("c3", "three", True, ""), ("c3", "Three times.", True, ""), ("c3", "3 times CONF: 60", True, ""),
    ("c3", "2", False, "commission"), ("c3", "4", False, "adjacent_day"), ("c3", "3 or 4", False, "hedge"),
    ("c3", "three or four", False, "hedge"), ("c3", "between 2027-02-01 and 2027-04-01 I went 3 times", True, ""),
    ("c3", "a few", False, "unmatched"), ("c3", "3.0", True, ""), ("c3", "3.5", False, "commission"),
    ("c3", "I went 3 times (once in Feb, twice in Mar)", False, "hedge"), ("c1", "once", True, ""), ("c2", "twice", True, ""),
    ("c21", "twenty-one", True, ""), ("c21", "twenty one", True, ""), ("c21", "20", False, "commission"),
    ("c0", "zero", True, ""), ("c0", "0", True, ""),
    # false premise (gold UNKNOWN)
    ("me1", "UNKNOWN", True, ""), ("me1", "Unknown.", True, ""), ("me1", "I don't know.", True, ""),
    ("me1", "I do not recall.", True, ""), ("me1", "You never told me.", True, ""),
    ("me1", "There is no record of that.", True, ""), ("me1", "porridge", False, "hallucination_on_abstain"),
    ("me1", "I had croissant", False, "hallucination_on_abstain"), ("me1", "UNKNOWN, maybe croissant", False, "hedge"),
    ("me1", "", False, "parse_failure"), ("me1", "It was nice", False, "hallucination_on_abstain"),
    ("me1", "not sure", True, ""), ("me1", "UNKNOWN CONF: 95", True, ""),
    # forced choice
    ("choice", "B", True, ""), ("choice", "(b)", True, ""), ("choice", "B) blue", True, ""), ("choice", "blue", True, ""),
    ("choice", "The answer is B", True, ""), ("choice", "A", False, "commission"), ("choice", "E", False, "unmatched"),
    ("choice", "B or C", False, "hedge"), ("choice", "blue or green", False, "hedge"), ("choice", "green", False, "commission"),
    ("choice", "B CONF: 70", True, ""), ("choice", "B) green", False, "hedge"),
    # dates, letters, booleans
    ("date", "2027-03-14", True, ""), ("date", "14 March 2027", True, ""), ("date", "March 14th, 2027", True, ""),
    ("date", "14/03/2027", True, ""), ("date", "2027-03-15", False, "commission"), ("date", "sometime in March", False, "unmatched"),
    ("date", "2027-03-14 or 2027-03-15", False, "hedge"),
    ("letter", "C", True, ""), ("letter", "B", False, "commission"), ("letter", "none", False, "unmatched"),
    ("bool", "yes", True, ""), ("bool", "No.", False, "commission"), ("bool", "yes and no", False, "hedge"),
]


def test_the_adversarial_set_agrees_100_percent():
    assert len(ADVERSARIAL) >= 100
    bad = []
    for key, reply, correct, err in ADVERSARIAL:
        r = run(key, reply)
        if (r.correct, r.error_type) != (correct, err):
            bad.append((key, reply, (correct, err), (r.correct, r.error_type)))
    assert bad == []


def test_hedges_and_two_pool_values_never_score():
    pools = {"dish": V.DISHES, "grey": V.COLOURS}
    for key, pool in pools.items():
        gold = QUERIES[key].gold.value
        for other in pool[:40]:
            if other != gold:
                r = run(key, "%s or %s" % (gold, other))
                assert not r.correct and r.score == 0.0 and r.hedged, (gold, other)
                r = run(key, "%s, %s" % (other, gold))
                assert not r.correct and r.hedged


def test_every_pool_value_scores_one_for_itself():
    for pid, key in (("colours", "grey"), ("dishes", "dish"), ("jobs", "grey"), ("relations", "grey"), ("shop_types", "grey")):
        for value in V.POOLS[pid]:
            q = mk("entity", value, "pool:" + pid)
            assert SC.score(q, value + " CONF: 50", world=WORLD).correct, (pid, value)
            for alias, canon in V.POOL_ALIASES.get(pid, ()):
                if canon == value:
                    assert SC.score(q, alias, world=WORLD).correct, (pid, alias)


# ------------------------------------------------------------------------------ statistics


def test_bootstrap_of_constant_clusters_has_no_spread():
    b = SC.cluster_bootstrap([0.4] * 12, n_boot=200, seed=1)
    assert b.estimate == pytest.approx(0.4) and b.lo == b.hi == b.estimate and b.se == 0.0
    assert b.n_clusters == 12 and b.n_boot == 200


def test_bootstrap_is_deterministic_and_seeded():
    c = [0.2, 0.4, 0.6, 0.8, 1.0, 0.5, 0.7]
    a1 = SC.cluster_bootstrap(c, n_boot=500, seed=3)
    a2 = SC.cluster_bootstrap(c, n_boot=500, seed=3)
    a3 = SC.cluster_bootstrap(c, n_boot=500, seed=4)
    assert a1 == a2 and (a1.lo, a1.hi) != (a3.lo, a3.hi)
    assert a1.lo < a1.estimate < a1.hi and 0.2 <= a1.lo and a1.hi <= 1.0
    assert a1.estimate == pytest.approx(sum(c) / len(c))
    assert SC.cluster_bootstrap(c, n_boot=500, seed=3, label="other") != a1


def test_bootstrap_statistics_differ_in_how_they_weigh_worlds():
    clusters = [[1, 1, 1, 1], [0]]
    assert SC.cluster_bootstrap(clusters, "mean_of_means", n_boot=50).estimate == pytest.approx(0.5)
    assert SC.cluster_bootstrap(clusters, "pooled", n_boot=50).estimate == pytest.approx(0.8)
    assert SC.cluster_bootstrap([[1, 0], 1.0], "mean_of_means", n_boot=50).estimate == pytest.approx(0.75)


def test_bootstrap_interval_covers_the_truth_about_as_often_as_claimed():
    rng = R.stream(11, "coverage")
    covered = 0
    reps = 120
    for r in range(reps):
        clusters = [sum(1.0 for _ in range(20) if rng.chance(0.6)) / 20.0 for _ in range(30)]
        b = SC.cluster_bootstrap(clusters, n_boot=300, seed=r)
        covered += b.lo <= 0.6 <= b.hi
    assert 0.85 <= covered / reps <= 1.0


def test_aa_contrast_contains_zero_and_a_real_difference_does_not():
    rng = R.stream(5, "aa")
    fp = 0
    for r in range(100):
        a = [rng.normal(0.5, 0.1) for _ in range(30)]
        b = [x + rng.normal(0.0, 0.05) for x in a]
        d = SC.cluster_bootstrap_diff(a, b, n_boot=300, seed=r)
        fp += not (d.lo <= 0.0 <= d.hi)
    assert fp / 100 <= 0.12                                    # A/A false positives near the nominal 5%
    a = [rng.normal(0.6, 0.1) for _ in range(30)]
    b = [x - 0.1 + rng.normal(0.0, 0.03) for x in a]
    d = SC.cluster_bootstrap_diff(a, b, n_boot=500, seed=1)
    assert d.lo > 0.05 and d.estimate == pytest.approx(0.1, abs=0.03)
    assert SC.cluster_bootstrap_diff([[1, 0], [1]], [[0, 0], [1]], n_boot=50).estimate == pytest.approx(0.25)


def test_bootstrap_default_is_ten_thousand_draws_and_fast_enough():
    c = [i / 40.0 for i in range(40)]
    t0 = time.perf_counter()
    b = SC.cluster_bootstrap(c, seed=2)
    assert b.n_boot == 10000 and time.perf_counter() - t0 < 15
    assert b.lo < b.estimate < b.hi and b.alpha == 0.05


def test_bootstrap_rejects_bad_input():
    with pytest.raises(ValueError):
        SC.cluster_bootstrap([])
    with pytest.raises(ValueError):
        SC.cluster_bootstrap([1.0], statistic="median")
    with pytest.raises(ValueError):
        SC.cluster_bootstrap_diff([1.0], [1.0, 2.0])


def test_calibration_metrics_golden_values():
    assert SC.brier([100, 0], [True, False]) == 0.0
    assert SC.brier([50], [True]) == pytest.approx(0.25)
    assert SC.brier([80, 80], [True, False]) == pytest.approx(0.34)
    assert SC.ece([90] * 10, [True] * 5 + [False] * 5) == pytest.approx(0.4)
    assert SC.ece([100, 100], [True, True]) == 0.0
    assert SC.ece([10, 90], [False, True]) == pytest.approx(0.1)
    assert SC.auroc([90, 80, 20, 10], [True, True, False, False]) == 1.0
    assert SC.auroc([10, 20, 80, 90], [True, True, False, False]) == 0.0
    assert SC.auroc([50, 50], [True, False]) == 0.5
    assert SC.auroc([50, 60], [True, True]) is None
    recs = [dataclasses.replace(run("dish", "kippers CONF: %d" % c)) for c in (95, 85, 60)] + [run("dish", "porridge CONF: 90")]
    assert SC.confident_wrong_rate(recs, 80) == pytest.approx(2 / 3)
    at_edge = [run("dish", "kippers CONF: 80"), run("dish", "porridge CONF: 79")]
    assert SC.confident_wrong_rate(at_edge, 80) == 1.0                  # CONF >= threshold is confident
    assert SC.confident_wrong_rate(recs, 99) is None
    with pytest.raises(ValueError):
        SC.brier([], [])
    with pytest.raises(ValueError):
        SC.ece([1], [True, False])


def test_quantile_interpolates_linearly():
    assert SC._quantile([1, 2, 3, 4], 0.5) == 2.5
    assert SC._quantile([1, 2, 3, 4], 0.0) == 1 and SC._quantile([1, 2, 3, 4], 1.0) == 4
    assert SC._quantile([1, 2, 3, 4], 1 / 3) == pytest.approx(2.0)
    assert SC._quantile([7], 0.3) == 7


def test_life_answer_confidence_range():
    for conf, expect in ((0, 0), (100, 100), (101, None), (-1, None)):
        r = SC.score(QUERIES["dish"], S.LifeAnswer(text="porridge", confidence=conf), world=WORLD)
        assert r.conf == expect, conf
    assert SC._unpack(S.LifeAnswer(text="x", confidence=100))[2] == 100


def test_gold_aliases_extend_the_vocabulary():
    q = dataclasses.replace(QUERIES["city_k"], gold=dataclasses.replace(QUERIES["city_k"].gold, aliases=("Karm", "Old Karmont")))
    for ans in ("Karm", "karm.", "Old Karmont", "Karmont"):
        assert SC.score(q, ans, world=WORLD).correct, ans
    assert SC.score(q, "Karm or Verdton", world=WORLD).hedged
    assert not SC.score(QUERIES["city_k"], "Karm", world=WORLD).correct             # not an alias without the gold record
