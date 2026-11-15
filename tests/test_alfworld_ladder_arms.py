"""CPU tests of the ALFWorld ladder arms: no GPU, no model, no ALFWorld install (token counts are faked)."""
import importlib.util
import pathlib

import pytest

SPEC = importlib.util.spec_from_file_location(
    "ladder_agent", pathlib.Path(__file__).resolve().parents[1] / "tools" / "alfworld_ladder" / "agent.py")
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


def entry(task, goal, n_steps=5):
    return {"task": task, "family": task.split("/")[1], "type": task.split("/")[1].split("-")[0],
            "goal": goal, "initial_observation": f"You are in a room.\n\nYour task is to: {goal}.",
            "steps": [{"action": f"go to shelf {i}", "observation": f"You arrive at shelf {i}. On it you see a cd."}
                      for i in range(n_steps)]}


@pytest.fixture()
def bank(monkeypatch):
    monkeypatch.setattr(agent, "count_tokens", lambda text: len(text.split()))
    b = [entry(f"train/pick_and_place_simple-CD-None-Shelf-{i}/trial_1", f"put a cd in shelf", 4 + i % 3)
         for i in range(5)]
    b += [entry(f"train/pick_heat_then_place_in_recep-Egg-None-Fridge-{i}/trial_1", "put a hot egg in fridge")
          for i in range(5)]
    return b


TASK = "valid_seen/pick_heat_then_place_in_recep-Egg-None-Fridge-99/trial_9"


def test_none_has_no_block(bank):
    assert agent.choose_memory(TASK, "heat some egg and put it in fridge", "none", 0, bank) == (None, [])


def test_retrieved_task_returns_k_sources_and_is_deterministic(bank):
    a = agent.choose_memory(TASK, "heat some egg and put it in fridge", "retrieved_task", 0, bank)
    b = agent.choose_memory(TASK, "heat some egg and put it in fridge", "retrieved_task", 0, bank)
    assert a == b and len(a[1]) == agent.CFG["k"]
    assert all("Egg" in s for s in a[1])


def test_random_same_type_stays_in_type(bank):
    block, src = agent.choose_memory(TASK, "x", "random_same_type", 3, bank)
    assert len(src) == 2 and all("pick_heat" in s for s in src)


def test_placebo_matches_memory_length_and_reports_no_source(bank):
    goal = "heat some egg and put it in fridge"
    mem, _ = agent.choose_memory(TASK, goal, "retrieved_task", 0, bank)
    pla, src = agent.choose_memory(TASK, goal, "placebo", 0, bank)
    assert src == []
    n_mem, n_pla = agent.count_tokens(mem), agent.count_tokens(pla)
    assert abs(n_pla - n_mem) <= 12, (n_mem, n_pla)
    assert "Retrieved Item 0:" in pla and "Retrieved Item 1:" in pla
    for word in ("egg", "fridge", "shelf", "heat", "microwave", "go to"):
        assert word not in pla.lower()


def test_parse_action_maps_case_and_rejects_unknown():
    adm = ["go to shelf 1", "take cd 1 from shelf 1"]
    assert agent.parse_action("<think>x</think><action>Go to shelf 1</action>", adm) == ("go to shelf 1", True)
    assert agent.parse_action("<action>fly away</action>", adm) == ("fly away", False)
    assert agent.parse_action("no tags", adm) == ("None", False)


def test_server_failure_is_an_error_not_an_unsolved_step(monkeypatch):
    def down(*a, **k):
        raise ConnectionRefusedError("server down")
    monkeypatch.setattr(agent.urllib.request, "urlopen", down)
    monkeypatch.setattr(agent.time, "sleep", lambda s: None)
    with pytest.raises(agent.ServerError):
        agent.chat("prompt", 1)


def test_empty_answers_are_retried_and_counted(monkeypatch):
    import io
    import json as _json

    class R(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    body = {"choices": [{"message": {"content": ""}}], "usage": {"prompt_tokens": 1, "completion_tokens": 0}}
    monkeypatch.setattr(agent.urllib.request, "urlopen", lambda *a, **k: R(_json.dumps(body).encode()))
    assert agent.chat("prompt", 1) == ("", 0, 4)
