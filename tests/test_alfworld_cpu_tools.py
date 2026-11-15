"""Tests for the CPU-only ALFWorld helper scripts in tools/alfworld_cpu (no ALFWorld install needed)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1] / "tools" / "alfworld_cpu"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_goal_phrasing_forms():
    gp = _load("goal_phrasing")
    assert gp.phrasing("put a cool egg in microwave") == "adjective_form"
    assert gp.phrasing("put a clean dishsponge in cart") == "adjective_form"
    assert gp.phrasing("put a hot apple in fridge") == "adjective_form"
    assert gp.phrasing("cool some bread and put it in countertop") == "verb_form"
    assert gp.phrasing("put two creditcard in dresser") == "two_objects"
    assert gp.phrasing("look at cd under the desklamp") == "look_at_form"
    assert gp.phrasing("examine the cellphone with the desklamp") == "examine_form"
    assert gp.phrasing("put some mug on sidetable") == "place"


def test_goal_extraction_from_grammar():
    gp = _load("goal_phrasing")
    game = {"grammar": '"task": [{"rhs": "Your task is to: clean some apple and put it in diningtable."}]'}
    assert gp.goal_of(game) == "clean some apple and put it in diningtable"
    assert gp.goal_of({"grammar": ""}) == "?"


def test_bank_syntax_detects_old_put(tmp_path):
    cb = _load("check_bank_syntax")
    bank = [{"conversations": [
        {"from": "human", "value": "task"},
        {"from": "gpt", "value": "Thought: go.\nAction: go to countertop 1"},
        {"from": "gpt", "value": "Action: take mug 1 from countertop 1"},
        {"from": "gpt", "value": "Action: put mug 1 in/on coffeemachine 1"},
    ]}]
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(bank), encoding="utf-8")
    convs = cb.load(str(path))
    acts = cb.actions(convs[0])
    assert acts == ["go to countertop 1", "take mug 1 from countertop 1", "put mug 1 in/on coffeemachine 1"]
    import re
    compiled = [re.compile("^" + p + "$") for p in cb.NEW_SYNTAX]
    ok = [any(c.match(a) for c in compiled) for a in acts]
    assert ok == [True, True, False]
    assert any(c.match("move mug 1 to coffeemachine 1") for c in compiled)


def test_power_beta_matches_requested_flip_rate():
    pp = _load("power_paired")
    a, b = pp.beta_params(0.65, 0.20)
    p = np.random.default_rng(1).beta(a, b, 200_000)
    assert abs(p.mean() - 0.65) < 0.005
    assert abs((2 * p * (1 - p)).mean() - 0.20) < 0.005
