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
    assert agent.chat("prompt", 1) == ("", 0, 4, None)


def test_chat_returns_finish_reason(monkeypatch):
    import io
    import json as _json

    class R(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    body = {"choices": [{"message": {"content": "<action>look</action>"}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
    monkeypatch.setattr(agent.urllib.request, "urlopen", lambda *a, **k: R(_json.dumps(body).encode()))
    assert agent.chat("prompt", 1) == ("<action>look</action>", 5, 0, "length")


@pytest.mark.parametrize("text,finish,expected", [
    ("<think>x</think><action>go to shelf 1</action>", "stop", (0, 0)),   # well formed
    ("<action>fly away</action>", "stop", (0, 0)),                         # tagged but not admissible: not a format error
    ("reasoning without any tag", "stop", (0, 1)),                         # missing tag
    ("</action>\ntake plate 1\n</action>", "stop", (0, 1)),                # malformed: closing tag used as opening
    ("long deliberation cut in the middle of a sente", "length", (1, 0)),  # truncated: behaviour, not format
    ("", None, (0, 1)),                                                    # empty after all retries
])
def test_classify_answer(text, finish, expected):
    c = agent.classify_answer(text, finish)
    assert (c["truncated"], c["untagged_not_truncated"]) == expected


def test_mismatched_type_is_other_type_length_matched_and_deterministic(bank):
    bank = bank + [entry(f"train/pick_two_obj_and_place-Pen-None-Desk-{i}/trial_1", "put two pen in desk", 3 + i % 5)
                   for i in range(12)]
    goal = "heat some egg and put it in fridge"
    mem, _ = agent.choose_memory(TASK, goal, "retrieved_task", 0, bank)
    a = agent.choose_memory(TASK, goal, "mismatched_type", 0, bank)
    assert a == agent.choose_memory(TASK, goal, "mismatched_type", 0, bank)
    block, src = a
    assert len(src) == 2 and not any("pick_heat" in s for s in src)
    n_mem, n_mis = agent.count_tokens(mem), agent.count_tokens(block)
    assert abs(n_mis - n_mem) <= 0.15 * n_mem, (n_mem, n_mis)


def test_similarity_metrics(bank):
    goal = "heat some egg and put it in fridge"
    _, src = agent.choose_memory(TASK, goal, "retrieved_task", 0, bank)
    m = agent.similarity_metrics(goal, src, bank)
    assert m["top1_similarity"] > 0 and m["memory_similarity"] == m["top1_similarity"]
    assert agent.similarity_metrics(goal, [], bank)["memory_similarity"] is None


def test_mismatched_type_comes_from_the_least_similar_quarter(bank):
    bank = bank + [entry(f"train/pick_two_obj_and_place-Pen-None-Desk-{i}/trial_1", "put two pen in desk", 3 + i % 5)
                   for i in range(30)]
    goal = "heat some egg and put it in fridge"
    _, src = agent.choose_memory(TASK, goal, "mismatched_type", 1, bank)
    other = sorted((b for b in bank if b["type"] != "pick_heat_then_place_in_recep"),
                   key=lambda b: (agent.jaccard(goal, b["goal"]), b["task"]))
    # the least similar quarter unless no pair there is within 3% of the memory block; then wider
    assert all(t in {b["task"] for b in other} for t in src)
    mem, _ = agent.choose_memory(TASK, goal, "retrieved_task", 1, bank)
    blk, _ = agent.choose_memory(TASK, goal, "mismatched_type", 1, bank)
    assert abs(agent.count_tokens(blk) - agent.count_tokens(mem)) <= 0.05 * agent.count_tokens(mem) + 4


def test_format_reminder_is_on_by_default_and_identical_text():
    assert agent.CFG["format_reminder"] is True
    assert "<action>" in agent.FORMAT_REMINDER and agent.FORMAT_REMINDER.startswith(chr(10))
