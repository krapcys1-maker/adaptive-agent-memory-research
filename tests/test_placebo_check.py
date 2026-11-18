"""CPU tests of the placebo-check cell tool and its frozen pools (no GPU, no model, no ALFWorld install)."""
import importlib.util
import json
import pathlib
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools" / "alfworld_ladder"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, TOOLS / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def pc(tmp_path, monkeypatch):
    monkeypatch.setenv("AAMR_CONTRIB_ROOT", str(tmp_path))
    monkeypatch.delenv("LADDER_MODEL", raising=False)
    monkeypatch.delenv("LADDER_FORMAT_REMINDER", raising=False)
    return load("placebo_check", "placebo_check.py")


def test_pools_are_frozen_train_blocks_disjoint_from_the_bank():
    pools = json.loads((TOOLS / "contrib" / "pools.json").read_text(encoding="utf-8"))
    bank_fams = {json.loads(l)["family"] for l in (TOOLS / "data" / "bank.jsonl").read_text(encoding="utf-8").splitlines()}
    for name in ("v4", "fresh"):
        blocks = pools[name]["blocks"]
        games = [g for b in blocks.values() for g in b]
        assert all(len(b) == 20 for b in blocks.values())
        assert len(games) == len(set(games))
        assert all(g.startswith("train/") for g in games)
        assert not any("valid_unseen" in g for g in games)
        assert not {g.split("/")[1] for g in games} & bank_fams
        assert len({g.split("/")[1] for g in games}) == len(games)  # one game per family


def test_prepare_writes_batch_and_card(pc, tmp_path):
    pc.main(["prepare", "--pool", "v4", "--block", "B00", "--replicate", "2", "--min-tokens", "0"])
    d = tmp_path / "placebo-v4-B00-r2-mt0-fr0"
    batch = [json.loads(l) for l in (d / "batch.jsonl").read_text().splitlines()]
    card = json.loads((d / "card.json").read_text())
    assert len(batch) == 60 and {b["arm"] for b in batch} == set(pc.ARMS)
    assert all(b["seed"] == 2 and b["unit"].startswith("placebo-v4-B00-r2-mt0-fr0~") for b in batch)
    assert card["fixed"]["min_tokens"] == 0 and card["fixed"]["sha256"]["bank"] == pc.sha_file(pc.FIXED_FILES["bank"])
    with pytest.raises(SystemExit):
        pc.main(["prepare", "--block", "B99"])


SETTINGS = {"model": "Qwen/Qwen3-4B-Instruct-2507-FP8", "min_tokens": 8, "format_reminder": False,
            "temperature": 0.7, "max_tokens": 2048, "max_steps": 50}


def fake_records(cid, games, solved, seed=1, **settings):
    out = []
    for g in games:
        for arm in ("none", "placebo", "retrieved_task"):
            out.append({"unit": f"{cid}~{g}", "arm": arm, "seed": seed, "solved": solved(g, arm), "memory_sources": [],
                        "metrics": {"steps": 10, "empty_retries": 2 if arm == "none" else 0,
                                    "invalid_no_action_tag": 1, "memory_tokens": 0 if arm == "none" else 800,
                                    "top1_similarity": 0.5,
                                    "memory_similarity": 0.4 if arm == "retrieved_task" else None,
                                    **{**SETTINGS, **settings}}})
    return out


def test_finish_and_summary(pc, tmp_path, monkeypatch):
    pc.main(["prepare", "--block", "B01"])
    d = tmp_path / "placebo-v4-B01-r1-mt8-fr0"
    card = json.loads((d / "card.json").read_text())
    games = card["games"]
    recs = fake_records(card["cell_id"], games, lambda g, arm: arm != "none" or g == games[0])
    (d / "records.jsonl").write_text("\n".join(json.dumps(r) for r in recs[:-1]))
    monkeypatch.setattr(pc, "machine_facts", lambda url: {"gpu": "TEST"})
    pc.main(["finish", str(d)])
    assert json.loads((d / "card.json").read_text())["status"] == "incomplete"
    (d / "records.jsonl").write_text("\n".join(json.dumps(r) for r in recs))
    pc.main(["finish", str(d)])
    card = json.loads((d / "card.json").read_text())
    assert card["status"] == "complete" and card["machine"]["gpu"] == "TEST"
    assert card["block"] == "B01" and len(card["block_games_sha256"]) == 64 and len(card["pools_file_sha256"]) == 64
    rows = (d / "per_unit.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0] == ("unit,task,arm,seed,solved,steps,empty_retries,invalid_no_action_tag,invalid_actions,"
                       "memory_tokens,truncated,untagged_not_truncated,top1_similarity,memory_similarity")
    assert len(rows) == 61
    by_arm = {r.split(",")[2]: r for r in rows[1:]}
    assert by_arm["none"].endswith(",0.5,") and by_arm["retrieved_task"].endswith(",0.5,0.4")
    s = pc.summarise(recs, card)
    assert s["games_with_all_arms"] == 20
    assert s["placebo-none"] == {"wins": 19, "losses": 0, "difference": 0.95}
    assert s["none"]["totals"]["steps"] == 200 and s["none"]["totals"]["empty_retries"] == 40
    assert s["none"]["empty_retries_per_step"] == 0.2 and s["placebo"]["empty_retries_per_step"] == 0.0


def test_agent_min_tokens_switch(monkeypatch):
    monkeypatch.setenv("LADDER_MIN_TOKENS", "0")
    agent = load("ladder_agent_mt", "agent.py")
    assert agent.CFG["min_tokens"] == 0
    monkeypatch.delenv("LADDER_MIN_TOKENS")
    assert load("ladder_agent_mt8", "agent.py").CFG["min_tokens"] == 8


def test_prepare_with_mismatched_arm(pc, tmp_path):
    pc.main(["prepare", "--block", "B02", "--with-mismatched"])
    d = tmp_path / "placebo-v4-B02-r1-mt8-fr0-mis"
    batch = [json.loads(l) for l in (d / "batch.jsonl").read_text().splitlines()]
    assert len(batch) == 80 and "mismatched_type" in {b["arm"] for b in batch}
    assert json.loads((d / "card.json").read_text())["arms"][-1] == "mismatched_type"


# Finding 2 of the external audit (gpt raport, 2026-11-18): the card must pin the configuration the agent runs.

def test_card_records_model_prompt_and_format_reminder(pc, tmp_path):
    pc.main(["prepare", "--block", "B03", "--min-tokens", "0"])
    card = json.loads((tmp_path / "placebo-v4-B03-r1-mt0-fr0" / "card.json").read_text())
    fixed = card["fixed"]
    assert fixed["format_reminder"] is False and fixed["min_tokens"] == 0
    assert fixed["model"] == pc.load_agent().CFG["model"] == pc.V3V4_MODEL
    assert fixed["prompt"]["prompt_template_sha256"] == pc.V3V4_PROMPT_TEMPLATE_SHA256
    assert fixed["prompt"]["prompts_match_v3_v4"] is True
    assert fixed["sha256"]["prompt_template"] == pc.V3V4_PROMPT_TEMPLATE_SHA256
    assert card["replication"].startswith("V3/V4")


def test_format_reminder_on_is_a_v5_prompt_cell(pc, tmp_path):
    pc.main(["prepare", "--block", "B03", "--format-reminder", "1"])
    card = json.loads((tmp_path / "placebo-v4-B03-r1-mt8-fr1" / "card.json").read_text())
    assert card["fixed"]["format_reminder"] is True
    assert card["fixed"]["prompt"]["prompts_match_v3_v4"] is False
    assert card["replication"].startswith("conceptual")


def test_the_card_model_comes_from_the_agent_config_and_changes_the_cell_id(pc, tmp_path, monkeypatch):
    monkeypatch.setenv("LADDER_MODEL", "some-other/model-7B")
    pc.main(["prepare", "--block", "B03"])
    (d,) = [p for p in tmp_path.iterdir() if p.name.startswith("placebo-v4-B03-r1-mt8-fr0-x")]
    card = json.loads((d / "card.json").read_text())
    assert card["fixed"]["model"] == "some-other/model-7B" and card["replication"].startswith("conceptual")


def test_run_passes_the_card_settings_to_the_agent(pc, tmp_path, monkeypatch):
    pc.main(["prepare", "--block", "B04", "--min-tokens", "0"])
    d = tmp_path / "placebo-v4-B04-r1-mt0-fr0"
    monkeypatch.setenv("LADDER_FORMAT_REMINDER", "1")  # the agent's own default is the V5 reminder: run must override
    seen = {}

    class Done:
        returncode = 0

    def fake_run(cmd, env=None, **kw):
        seen["cmd"], seen["env"] = cmd, env
        return Done()

    monkeypatch.setattr(pc.subprocess, "run", fake_run)
    with pytest.raises(SystemExit) as exit_:
        pc.main(["run", str(d)])
    assert exit_.value.code == 0
    assert seen["env"]["LADDER_FORMAT_REMINDER"] == "0"
    assert seen["env"]["LADDER_MODEL"] == pc.V3V4_MODEL and seen["env"]["LADDER_MIN_TOKENS"] == "0"
    assert seen["cmd"][seen["cmd"].index("--min-tokens") + 1] == "0"


def prepared_cell(pc, tmp_path, monkeypatch, block="B05"):
    pc.main(["prepare", "--block", block])
    d = tmp_path / f"placebo-v4-{block}-r1-mt8-fr0"
    monkeypatch.setattr(pc, "machine_facts", lambda url: {})
    return d, json.loads((d / "card.json").read_text())


def write_records(d, recs):
    (d / "records.jsonl").write_text("\n".join(json.dumps(r) for r in recs))


@pytest.mark.parametrize("name,value", [("model", "some-other/model-7B"), ("min_tokens", 0),
                                        ("format_reminder", True), ("temperature", 1.0), ("max_tokens", 512),
                                        ("max_steps", 30)])
def test_finish_marks_the_cell_invalid_when_a_record_setting_differs(pc, tmp_path, monkeypatch, name, value):
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    recs[7]["metrics"][name] = value
    write_records(d, recs)
    pc.main(["finish", str(d)])
    card = json.loads((d / "card.json").read_text())
    assert card["status"] == "invalid" and card["records"]["setting_mismatches"] == 1
    assert name in card["invalid_reasons"][0]
    with pytest.raises(SystemExit) as exit_:
        pc.main(["summary", str(d)])
    assert exit_.value.code not in (0, None)


def test_finish_marks_the_cell_invalid_when_the_server_serves_another_model(pc, tmp_path, monkeypatch):
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    write_records(d, fake_records(card["cell_id"], card["games"], lambda g, arm: True))
    monkeypatch.setattr(pc, "machine_facts", lambda url: {"served_models": ["some-other/model-7B"]})
    pc.main(["finish", str(d)])
    card = json.loads((d / "card.json").read_text())
    assert card["status"] == "invalid" and card["machine"]["served_models"] == ["some-other/model-7B"]


# Finding 3: only the card's declared (game, arm, seed) triples count.

def test_an_extra_game_is_rejected_and_never_summarised(pc, tmp_path, monkeypatch):
    """The audit's reproduction: 20 declared games with memory = placebo, plus one undeclared game where memory wins.
    Before the fix, finish said complete and summary counted 21 games (memory - placebo +0.048)."""
    d, card = prepared_cell(pc, tmp_path, monkeypatch, block="B03")
    declared = fake_records(card["cell_id"], card["games"], lambda g, arm: arm != "none")
    extra = fake_records(card["cell_id"], ["train/not-on-the-card/trial_T0"], lambda g, arm: arm == "retrieved_task")
    write_records(d, declared + extra)
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid" and after["records"]["extra"] == 3
    assert "outside the card" in after["invalid_reasons"][0]
    assert len((d / "per_unit.csv").read_text(encoding="utf-8").splitlines()) == 61  # 20 declared games x 3 arms
    with pytest.raises(pc.CellError):
        pc.summarise(declared + extra, card)
    with pytest.raises(SystemExit) as exit_:
        pc.main(["summary", str(d)])
    assert "outside the card" in str(exit_.value.code)
    s = pc.summarise(declared, card)
    assert s["games_with_all_arms"] == 20 and s["retrieved_task-placebo"]["difference"] == 0.0


def test_a_seed_mismatch_is_rejected(pc, tmp_path, monkeypatch):
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    recs[0]["seed"] = 99
    write_records(d, recs)
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid" and after["records"]["seed_mismatches"] == 1
    with pytest.raises(pc.CellError, match="seed"):
        pc.summarise(recs, card)


def test_a_duplicate_is_rejected_not_silently_overwritten(pc, tmp_path, monkeypatch):
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: arm != "none")
    duplicate = dict(recs[2], solved=False)
    write_records(d, recs + [duplicate])
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid" and after["records"]["duplicates"] == 1
    with pytest.raises(pc.CellError, match="more than once"):
        pc.summarise(recs + [duplicate], card)


# The prompt the agent actually sends, compared with the version's template (no GPU, no ALFWorld).

class FakeEnv:
    def __init__(self):
        self.t = 0

    def reset(self):
        return ("-= Welcome to TextWorld, ALFRED! =-\n\nYou are in the middle of a room.\n\n"
                "Your task is to: put a mug in sinkbasin."), {"admissible_commands": ["go to sinkbasin 1", "help"],
                                                               "won": False}

    def step(self, action):
        self.t += 1
        return f"You arrive at sinkbasin {self.t}.", 0, self.t >= 2, {"won": self.t >= 2,
                                                                       "admissible_commands": ["look"]}

    def close(self):
        pass


def fake_alfworld(monkeypatch):
    import types
    tw = types.ModuleType("textworld")
    gym = types.ModuleType("textworld.gym")
    tw.EnvInfos = lambda **kw: kw
    gym.register_game = lambda *a, **kw: "env-id"
    gym.make = lambda env_id: FakeEnv()
    tw.gym = gym
    alfred = types.ModuleType("alfworld.agents.environment.alfred_tw_env")
    alfred.AlfredDemangler, alfred.AlfredInfos = object, object
    for name, module in {"textworld": tw, "textworld.gym": gym, "alfworld": types.ModuleType("alfworld"),
                         "alfworld.agents": types.ModuleType("alfworld.agents"),
                         "alfworld.agents.environment": types.ModuleType("alfworld.agents.environment"),
                         "alfworld.agents.environment.alfred_tw_env": alfred}.items():
        monkeypatch.setitem(sys.modules, name, module)


TASK = "train/pick_and_place_simple-Mug-None-SinkBasin-9/trial_T0"
BANK = [{"task": f"train/pick_and_place_simple-Mug-None-SinkBasin-{i}/trial_T0", "type": "pick_and_place_simple",
         "family": f"pick_and_place_simple-Mug-None-SinkBasin-{i}",
         "initial_observation": "You are in a kitchen.\n\nYour task is to: put a mug in sinkbasin.",
         "steps": [{"observation": "You pick up the mug.", "action": "take mug 1 from countertop 1"}]} for i in (1, 2)]


@pytest.mark.parametrize("arm", ["none", "retrieved_task"])
@pytest.mark.parametrize("reminder", [False, True])
def test_the_agent_prompt_equals_the_version_template(pc, monkeypatch, arm, reminder):
    """Runs agent.episode on a fake two-step game and compares every prompt it sends with
    instrument/prompt_template.txt (the V3/V4 pin), plus the V5 reminder only when it is switched on."""
    fake_alfworld(monkeypatch)
    agent = pc.load_agent(reminder)
    agent.DATA_ROOT, agent.BANK = "/nowhere", [dict(b) for b in BANK]
    for b in agent.BANK:
        b["goal"] = agent.goal_of(b["initial_observation"])
    monkeypatch.setattr(agent, "count_tokens", lambda text: len(text.split()))
    prompts = []

    def chat(prompt, seed):
        prompts.append(prompt)
        return "<think>go</think><action>go to sinkbasin 1</action>", 10, 0, "stop"

    monkeypatch.setattr(agent, "chat", chat)
    record = agent.episode({"unit": f"u~{TASK}", "task": TASK, "arm": arm, "seed": 1})
    assert record["solved"] is True and len(prompts) == 2
    assert record["metrics"]["format_reminder"] is reminder and record["metrics"]["model"] == pc.V3V4_MODEL

    t = pc.template_sections((TOOLS / "instrument" / "prompt_template.txt").read_text(encoding="utf-8"))
    if arm == "none":
        tail = t["ACTION_INSTR"]
    else:
        block, _ = agent.choose_memory(TASK, "put a mug in sinkbasin", arm, 1, agent.BANK)
        tail = t["MEMORY_WRAPPER"].replace("{retrieved_exp}", block)
    if reminder:
        tail += "\n\n" + agent.FORMAT_REMINDER.strip()
    first_obs = "You are in the middle of a room.\n\nYour task is to: put a mug in sinkbasin."
    step1 = t["TEMPLATE_NO_HIS"].format(current_observation=first_obs, admissible_actions="'go to sinkbasin 1'")
    assert prompts[0].strip() == step1 + "\n\n" + tail
    step2 = t["TEMPLATE"].format(
        task_description="put a mug in sinkbasin", step_count=1, history_length=1,
        action_history=f"[Observation 1: '{first_obs}', Action 1: 'go to sinkbasin 1']",
        current_step=2, current_observation="You arrive at sinkbasin 1.", admissible_actions="'look'")
    assert prompts[1].strip() == step2 + "\n\n" + tail
