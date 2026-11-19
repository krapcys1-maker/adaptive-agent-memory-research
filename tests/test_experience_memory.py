"""Tests of tools/experience_memory: standard library + pytest, fake model and fake token counts, no GPU, no network."""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import tomllib
from contextlib import redirect_stdout
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "tools" / "experience_memory"
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "parity"))

import experience_memory as em  # noqa: E402
from experience_memory import retrieval as em_retrieval  # noqa: E402
from experience_memory.alfworld import from_lab_record, goal_of, room_of  # noqa: E402
import check_v5b_parity as parity  # noqa: E402

FIXTURE = REPO / "tests" / "fixtures" / "experience-memory-synthetic"


def ws(text: str) -> int:
    return len(text.split())


def traj(item_id, goal, family=None, ttype="pick", n_steps=3, **kw):
    return em.Trajectory(item_id=item_id, goal=goal, task_type=ttype, family_id=family or item_id,
                         steps=tuple(em.Step(f"go to shelf {i}", f"You arrive at shelf {i}.") for i in range(n_steps)),
                         initial_observation="You are in a room.", **kw)


@pytest.fixture(scope="module")
def fixture_bank():
    with open(FIXTURE / "bank.jsonl", encoding="utf-8") as f:
        return em.ExperienceBank(from_lab_record(json.loads(line)) for line in f if line.strip())


@pytest.fixture(scope="module")
def expected():
    return json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))


# --- the synthetic fixture pins the measured rule --------------------------------------------------------------


def test_fixture_was_generated_from_the_v5b_instrument(expected):
    assert expected["reference_sha256"] == parity.V5B_PINS["src/agent.py"]
    assert expected["k"] == 2 and len(expected["cases"]) >= 20


def test_fixture_picks_scores_and_block_digests(fixture_bank, expected):
    memory = em.ExperienceMemory(fixture_bank)
    for case in expected["cases"]:
        shown = memory.for_task(case["goal"], query_id=case["query_id"], query_family=case["query_family"],
                                seed=case["seed"])
        assert list(shown.block.item_ids) == case["expected_items"], case
        if "expected_block_sha256" in case:
            assert hashlib.sha256(shown.block.text.encode("utf-8")).hexdigest() == case["expected_block_sha256"], case
            assert [round(p.score, 6) for p in shown.retrieval.picks] == case["expected_scores"]
        if "expected_excluded" in case:
            assert list(shown.retrieval.excluded_ids) == case["expected_excluded"]


def test_fixture_first_block_bytes(fixture_bank, expected):
    case = expected["cases"][0]
    shown = em.ExperienceMemory(fixture_bank).for_task(case["goal"], query_id=case["query_id"],
                                                       query_family=None, seed=case["seed"])
    assert shown.block.text.encode("utf-8") == (FIXTURE / "expected_block_0.txt").read_bytes()


# --- parity with the public copy of the V5B instrument (runs in CI) -----------------------------------------------


def test_public_instrument_is_the_v5b_pinned_code():
    assert parity.sha256_file(parity.PUBLIC_AGENT) == parity.V5B_PINS["src/agent.py"]


def test_parity_with_public_instrument_on_public_bank():
    records = parity.read_records(parity.PUBLIC_BANK)
    ref = parity.load_reference(parity.PUBLIC_AGENT)
    result = parity.compare(ref, records, parity.public_queries(records, 25, 3), seeds=[0, 6])
    assert result["comparisons"] == 50
    assert result["mismatches"] == []


def test_prompt_text_equals_instrument():
    ref = parity.load_reference(parity.PUBLIC_AGENT)
    assert em.MEMORY_WRAPPER == ref.MEMORY_WRAPPER
    assert em.ACTION_INSTR == ref.ACTION_INSTR
    assert em.FORMAT_REMINDER == ref.FORMAT_REMINDER
    assert em.STOPWORDS == ref.STOP
    filler = (REPO / "tools" / "alfworld_ladder" / "instrument" / "placebo.txt").read_text(encoding="utf-8")
    assert list(em.DEFAULT_FILLER) == [ln for ln in filler.strip().split("\n") if ln.strip() and not ln.startswith("#")]


@pytest.mark.parametrize("mutation", ["stopwords", "obs_chars", "tie_salt"])
def test_parity_check_detects_a_changed_rule(monkeypatch, mutation):
    """The check is not vacuous: a one-detail change in the package is reported as a mismatch."""
    if mutation == "stopwords":
        monkeypatch.setattr(em_retrieval, "STOPWORDS", frozenset())
    elif mutation == "obs_chars":
        monkeypatch.setattr(em.WalkthroughFormatter, "__init__", lambda self, obs_chars=239: setattr(self, "obs_chars", obs_chars))
    else:
        real = em_retrieval.stable_hash
        monkeypatch.setattr(em_retrieval, "stable_hash", lambda *p: real(*p, "x"))
    records = parity.read_records(parity.PUBLIC_BANK)
    ref = parity.load_reference(parity.PUBLIC_AGENT)
    result = parity.compare(ref, records, parity.public_queries(records, 25, 3), seeds=[0], check_placebo=False)
    assert result["mismatches"], mutation


def test_private_check_skips_cleanly_when_absent(tmp_path):
    out = io.StringIO()
    with redirect_stdout(out):
        assert parity.main(["private", "--v5b-dir", str(tmp_path / "absent")]) == 0
    assert out.getvalue().startswith("SKIPPED")
    with redirect_stdout(io.StringIO()):
        assert parity.main(["private", "--v5b-dir", str(tmp_path / "absent"), "--require"]) == 2


def test_private_check_refuses_inputs_that_differ_from_the_pins(tmp_path):
    for rel in ("src/agent.py", "data/bank.jsonl", "data/units.json", "data/unit_goals.json", "data/families.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("{}", encoding="utf-8")
    out = io.StringIO()
    with redirect_stdout(out):
        assert parity.main(["private", "--v5b-dir", str(tmp_path)]) == 2
    assert "differ from the V5B program pins" in out.getvalue()


# --- bank: what it refuses ---------------------------------------------------------------------------------------


def test_bank_refuses_test_items_failures_and_duplicates():
    bank = em.ExperienceBank([traj("a", "put a cd in shelf")])
    with pytest.raises(em.LeakageError):
        bank.add(traj("b", "put a cd in shelf", is_test=True))
    with pytest.raises(ValueError, match="successful"):
        bank.add(traj("c", "put a cd in shelf", success=False))
    with pytest.raises(ValueError, match="already"):
        bank.add(traj("a", "put a pen in shelf"))
    assert len(bank) == 1


def test_alfworld_adapter_flags_non_train_games_as_test():
    rec = json.loads((FIXTURE / "bank.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert not from_lab_record(rec).is_test
    for split in ("valid_unseen", "valid_seen"):
        bad = dict(rec, task=rec["task"].replace("train/", f"{split}/", 1))
        with pytest.raises(em.LeakageError):
            em.ExperienceBank([from_lab_record(bad)])


def test_alfworld_goal_and_room():
    obs = "-= Welcome to TextWorld, ALFRED! =-\n\nYou are in a room.\n\nYour task is to: put a cd in shelf."
    assert goal_of(obs) == "put a cd in shelf"
    assert room_of(obs) == "You are in a room."
    assert goal_of("no goal here") == "" and room_of("Your task is to: x.") == ""


def test_bank_jsonl_round_trip(tmp_path):
    bank = em.ExperienceBank([traj("a", "put a cd in shelf"), traj("b", "heat an egg", n_steps=0)])
    bank.to_jsonl(tmp_path / "b.jsonl")
    again = em.ExperienceBank.from_jsonl(tmp_path / "b.jsonl")
    assert [t.to_dict() for t in again] == [t.to_dict() for t in bank]


# --- retrieval ---------------------------------------------------------------------------------------------------


def test_tokenisation_matches_the_v5b_rule():
    assert em.content_words("Put a CD on the shelf. (2x)") == {"cd", "shelf", "x"}
    assert em.goal_jaccard("put a cd in shelf", "put some cd on shelf") == 1.0
    assert em.goal_jaccard("", "") == 0.0


def test_own_family_and_own_id_are_never_shown():
    bank = em.ExperienceBank([traj("a1", "put a cd in shelf", family="F"), traj("a2", "put a cd in shelf", family="F"),
                              traj("q", "put a cd in shelf", family="Q"), traj("b", "put a pen in shelf", family="G")])
    r = em.GoalSimilarityRetriever().retrieve(bank, "put a cd in shelf", query_id="q", query_family="F", seed=0)
    assert set(r.item_ids) == {"b"} and set(r.excluded_ids) == {"a1", "a2", "q"}


def test_query_family_must_be_stated():
    bank = em.ExperienceBank([traj("a", "put a cd in shelf")])
    with pytest.raises(TypeError):
        em.GoalSimilarityRetriever().retrieve(bank, "put a cd in shelf", query_id="q")  # type: ignore[call-arg]


def test_exclusion_does_not_reorder_the_other_items():
    bank = em.ExperienceBank([traj(f"i{n}", "put a cd in shelf", family=f"F{n % 3}") for n in range(12)])
    full = em.GoalSimilarityRetriever(k=12).retrieve(bank, "put a cd in shelf", query_id="q", query_family=None, seed=4)
    part = em.GoalSimilarityRetriever(k=12).retrieve(bank, "put a cd in shelf", query_id="q", query_family="F1", seed=4)
    assert list(part.item_ids) == [i for i in full.item_ids if bank[int(i[1:])].family_id != "F1"]


def test_ties_depend_on_query_and_seed_only():
    bank = em.ExperienceBank([traj(f"i{n}", "put a cd in shelf") for n in range(10)])
    ret = em.GoalSimilarityRetriever()
    a = ret.retrieve(bank, "put a cd in shelf", query_id="q", query_family=None, seed=1).item_ids
    assert a == ret.retrieve(bank, "put a cd in shelf", query_id="q", query_family=None, seed=1).item_ids
    others = {ret.retrieve(bank, "put a cd in shelf", query_id="q", query_family=None, seed=s).item_ids for s in range(8)}
    assert len(others) > 1


def test_k_must_be_positive():
    with pytest.raises(ValueError):
        em.GoalSimilarityRetriever(k=0)


# --- formatting, budget and pluggable formats --------------------------------------------------------------------


def test_walkthrough_rendering_cuts_and_collapses_observations():
    item = em.Trajectory("x", "put a cd in shelf", "pick", "F", (em.Step("take cd 1", "a  b\n c " + "z" * 300),),
                         initial_observation="room\n\ntext")
    text = em.WalkthroughFormatter().render_item(item)
    lines = text.split("\n")
    assert lines[0] == "Task: put a cd in shelf."
    assert lines[1] == "[Observation 1: 'room text', Action 1: 'take cd 1']"
    assert lines[2] == "Final observation: '" + ("a b c " + "z" * 300)[:240] + "'"


def test_budget_drops_whole_low_ranked_items():
    items = [traj("a", "g", n_steps=2), traj("b", "g", n_steps=6)]
    full = em.build_memory_block(items, count_tokens=ws)
    assert em.build_memory_block(items, token_budget=full.n_tokens, count_tokens=ws).text == full.text
    one = em.build_memory_block(items, token_budget=full.n_tokens - 1, count_tokens=ws)
    assert one.item_ids == ("a",) and one.dropped_ids == ("b",) and one.n_tokens <= full.n_tokens - 1
    assert one.text == em.WalkthroughFormatter().wrap([em.WalkthroughFormatter().render_item(items[0])])
    none = em.build_memory_block(items, token_budget=1, count_tokens=ws)
    assert none.is_empty and none.text == "" and none.dropped_ids == ("a", "b")
    assert em.prompt_suffix(none) == em.ACTION_INSTR + em.FORMAT_REMINDER
    with pytest.raises(ValueError):
        em.build_memory_block(items, token_budget=10)


class PlanFormatter:
    """A stand-in for a future format (for example V6's abstract plan): only the plugging is tested."""

    name = "test_plan"

    def render_item(self, item):
        return f"Goal: {item.goal}\nPlan: " + " -> ".join(s.action for s in item.steps)

    def wrap(self, texts):
        return "\n---\n".join(texts)


def test_a_new_format_plugs_in_and_the_placebo_follows_its_layout():
    em.register_formatter("test_plan", PlanFormatter, replace=True)
    assert "test_plan" in em.available_formatters()
    with pytest.raises(ValueError):
        em.register_formatter("walkthrough_v5b", PlanFormatter)
    assert isinstance(em.get_formatter("test_plan"), em.Formatter)
    bank = em.ExperienceBank([traj("a", "put a cd in shelf"), traj("b", "put a cd in shelf")])
    memory = em.ExperienceMemory(bank, formatter="test_plan", count_tokens=ws)
    shown = memory.for_task("put a cd in shelf", query_id="q", query_family=None)
    assert shown.block.formatter == "test_plan" and "\n---\n" in shown.block.text
    placebo = memory.placebo_for(shown)
    assert "\n---\n" in placebo.text and "Retrieved Item" not in placebo.text
    with pytest.raises(KeyError):
        em.get_formatter("no_such_format")


# --- placebo -----------------------------------------------------------------------------------------------------


def test_placebo_is_token_matched_and_content_free(fixture_bank):
    memory = em.ExperienceMemory(fixture_bank, count_tokens=ws)
    for goal in ("put a cd in shelf", "put a hot egg in fridge", "examine the book with the desklamp"):
        shown = memory.for_task(goal, query_id="q", query_family=None)
        placebo = memory.placebo_for(shown)
        longest_line = max(ws(x) for x in em.DEFAULT_FILLER)
        assert abs(placebo.n_tokens - shown.block.n_tokens) <= longest_line
        assert placebo.item_ids == () and placebo.text.count("Retrieved Item") == 2
        body = re.sub(r"Retrieved Item \d+:", "", placebo.text)
        assert not (em.content_words(body) & em.content_words(goal))
    assert memory.placebo_for(shown).text == memory.placebo_for(shown).text


def test_placebo_needs_a_counter():
    bank = em.ExperienceBank([traj("a", "g")])
    memory = em.ExperienceMemory(bank)
    with pytest.raises(ValueError):
        memory.placebo_for(memory.for_task("g", query_id="q", query_family=None))


# --- end to end with a fake model ---------------------------------------------------------------------------------


def fake_model(prompt: str) -> str:
    """Answers with the first action of the first retrieved walkthrough if the prompt shows one, else 'look'."""
    m = re.search(r"Retrieved Item 0:\n.*?Action 1: '([^']*)'", prompt, re.S)
    return f"<think>fake</think><action>{m.group(1) if m else 'look'}</action>"


def test_end_to_end_with_a_fake_model(fixture_bank):
    memory = em.ExperienceMemory(fixture_bank, count_tokens=ws)
    base = "You are an expert agent. Your current observation is: You are in a room."
    shown = memory.for_task("put a cd in shelf", query_id="train/x/trial_1", query_family=None, seed=0)
    prompt = base + em.prompt_suffix(shown.block)
    assert prompt.endswith(em.FORMAT_REMINDER)
    assert fake_model(prompt) == "<think>fake</think><action>go to drawer 1</action>"
    assert fake_model(base + em.prompt_suffix(memory.placebo_for(shown))).endswith("<action>look</action>")
    assert fake_model(base + em.prompt_suffix(None)).endswith("<action>look</action>")
    log = shown.log_record()
    assert log["shown"] == list(shown.block.item_ids) and log["formatter"] == "walkthrough_v5b"
    assert log["block_tokens"] == ws(shown.block.text) and log["excluded"] == []
    json.dumps(log)


def test_pyproject_declares_the_package():
    meta = tomllib.loads((PKG / "pyproject.toml").read_text(encoding="utf-8"))
    assert meta["project"]["name"] == "experience-memory"
    assert meta["project"]["version"] == em.__version__
    assert meta["project"]["dependencies"] == []
