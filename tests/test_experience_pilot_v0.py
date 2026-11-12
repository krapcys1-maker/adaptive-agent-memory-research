"""EXP-PILOT-0 (scripts/experience_pilot_v0.py): agent loop, validation, isolation and leakage checks on a fake model.

Tests that need the pinned BFCL checkout (outside Git) are skipped when it is absent, e.g. in CI.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import experience_pilot_v0 as xp  # noqa: E402

DATA = ROOT / "data/lab/experience-pilot-v0"
CFG = json.loads((DATA / "config.json").read_text(encoding="utf-8"))
BFCL_ROOT = (ROOT / CFG["bfcl_root"]).resolve()
needs_bfcl = pytest.mark.skipif(not (BFCL_ROOT / "bfcl_eval").is_dir(), reason="pinned BFCL checkout not present")

DOCS = {"setHeadlights": {"name": "setHeadlights", "parameters": {"type": "dict", "properties": {"mode": {"type": "string"}}, "required": ["mode"]}},
        "pressBrakePedal": {"name": "pressBrakePedal", "parameters": {"type": "dict", "properties": {"pedalPosition": {"type": "float"}}, "required": ["pedalPosition"]}},
        "lockDoors": {"name": "lockDoors", "parameters": {"type": "dict", "properties": {"unlock": {"type": "boolean"}, "door": {"type": "array", "items": {"type": "string"}}},
                                                          "required": ["unlock", "door"]}},
        "fillFuelTank": {"name": "fillFuelTank", "parameters": {"type": "dict", "properties": {"fuelAmount": {"type": "float"}, "x": {"type": "integer"}}, "required": ["fuelAmount"]}}}


# ----------------------------------------------------------------------------- pure functions

def test_validate_call_builds_ordered_repr_string():
    assert xp.validate_call({"name": "lockDoors", "arguments": {"door": ["driver"], "unlock": False}}, DOCS) == ("lockDoors(unlock=False, door=['driver'])", None)


def test_validate_call_accepts_int_for_float_only():
    assert xp.validate_call({"name": "pressBrakePedal", "arguments": {"pedalPosition": 1}}, DOCS)[0] == "pressBrakePedal(pedalPosition=1)"
    assert xp.validate_call({"name": "fillFuelTank", "arguments": {"fuelAmount": 1.0, "x": 2.0}}, DOCS)[0] is None
    assert xp.validate_call({"name": "pressBrakePedal", "arguments": {"pedalPosition": True}}, DOCS)[0] is None


@pytest.mark.parametrize("call,needle", [
    ({"name": "setHeadlights", "arguments": {}}, "missing required"),
    ({"name": "setHeadlights", "arguments": {"mode": "on", "extra": 1}}, "unknown argument"),
    ({"name": "nope", "arguments": {}}, "unknown function"),
    ({"name": "lockDoors", "arguments": {"unlock": True, "door": [1]}}, "must be of type array"),
    ({"name": "setHeadlights"}, "exactly the keys"),
])
def test_validate_call_rejects(call, needle):
    s, err = xp.validate_call(call, DOCS)
    assert s is None and needle in err and err.startswith("invalid call:")


def test_call_string_is_safe_literal():
    s, _ = xp.validate_call({"name": "setHeadlights", "arguments": {"mode": "on'); import os; ('"}}, DOCS)
    node = ast.parse(s, mode="eval").body
    assert isinstance(node, ast.Call) and node.func.id == "setHeadlights" and isinstance(node.keywords[0].value, ast.Constant)


def test_parse_output_whole_output_rules():
    assert xp.parse_output('{"calls": []}', "stop") == []
    assert xp.parse_output('{"calls": []}', "length") is None
    assert xp.parse_output('{"calls": [', "stop") is None
    assert xp.parse_output('{"calls": [], "x": 1}', "stop") is None
    assert xp.parse_output(json.dumps({"calls": [{}] * 7}), "stop") is None


def test_memory_block_limits_and_template():
    row = {"request": "r" * 3000, "label": "FAILED", "steps": [{"call": f"f{i}()", "result": "x" * 500, "error": False} for i in range(12)]}
    item = xp.render_item(1, row)
    assert len(item) <= xp.ITEM_CHARS
    small = {"request": "Lock the doors", "label": "PASSED", "steps": [{"call": "lockDoors(unlock=False, door=['driver'])", "result": "y" * 40, "error": False}] * 9}
    text = xp.render_item(2, small)
    assert text.startswith("[2] Request: Lock the doors\n    Steps:\n") and "\n      …\n" in text and text.endswith("    Outcome: PASSED")
    assert all(len(line) <= len("      lockDoors(unlock=False, door=['driver']) -> ") + xp.STEP_RESULT_CHARS for line in text.splitlines()[2:10])
    block = xp.render_block([small, small])
    assert block.startswith(xp.MEMORY_HEADER + "\n[1] ") and "\n[2] " in block
    assert xp.render_block([]) == ""


def test_mcnemar_exact():
    r = xp.mcnemar([1, 1, 1, 1, 1, 1, 0], [0, 0, 0, 0, 0, 0, 0])
    assert r["x_only"] == 6 and r["y_only"] == 0 and abs(r["p_one_sided_x_gt_y"] - 1 / 64) < 1e-12
    r = xp.mcnemar([1] * 8 + [0] * 2, [0] * 8 + [1] * 2)
    assert abs(r["p_one_sided_x_gt_y"] - 56 / 1024) < 1e-12


def test_names_are_unique_per_call():
    n = xp.Names("t")
    a, b = n.new("s", "N", "task", "eval"), n.new("s", "N", "task", "eval")
    assert a != b
    n.used.add(n.prefix and "xp0_t_x_3")
    n.counter = 2
    with pytest.raises(RuntimeError):
        n.new("x")


def test_e2_plan_balanced_and_seeded():
    test = [f"t{i}" for i in range(30)]
    plan = xp.e2_plan(test)
    assert len(plan) == 30 * len(xp.E2_ARMS) + xp.NPRIME_TASKS
    assert plan == xp.e2_plan(test)
    for i, t in enumerate(test):
        arms = [a for tt, a in plan if tt == t]
        assert sorted(arms) == sorted(xp.E2_ARMS + (["N'"] if i < xp.NPRIME_TASKS else []))


# ----------------------------------------------------------------------------- fake model

class FakeClient:
    """Plays a fixed policy. policy(turn_index, step_index, messages) -> text."""

    def __init__(self, policy):
        self.policy, self.keys, self.seen = policy, set(), []

    def ask(self, key, messages, seed, *, output_schema=None):
        assert key not in self.keys
        self.keys.add(key)
        self.seen.append((key, [dict(m) for m in messages], output_schema))
        t, s = key.rsplit(":", 2)[-2:]
        text = self.policy(int(t[1:]), int(s[1:]), messages)
        return {"text": text, "done_reason": "stop", "usage": {"prompt_eval_count": 100, "eval_count": 10}, "wall_seconds": 0.0}


def gold_policy(bfcl, task_id):
    gt = bfcl.gt[task_id]

    def policy(t, s, messages):
        calls = []
        for c in gt[t]:
            node = ast.parse(c, mode="eval").body
            names = bfcl.signatures[node.func.id]
            args = {names[i]: ast.literal_eval(a) for i, a in enumerate(node.args)}
            args.update({k.arg: ast.literal_eval(k.value) for k in node.keywords})
            calls.append({"name": node.func.id, "arguments": args})
        chunk = calls[s * xp.MAX_CALLS_PER_STEP:(s + 1) * xp.MAX_CALLS_PER_STEP]       # the schema allows at most 6 calls per step
        return json.dumps({"calls": chunk})
    return policy


@pytest.fixture(scope="module")
def bfcl():
    return xp.Bfcl(BFCL_ROOT)


@needs_bfcl
@pytest.mark.parametrize("task_id", ["multi_turn_base_50", "multi_turn_base_65", "multi_turn_base_99"])
def test_gold_policy_solves_and_labels_all_passed(bfcl, task_id):
    names = xp.Names("tg")
    rec = xp.run_episode(bfcl, bfcl.tasks[task_id], FakeClient(gold_policy(bfcl, task_id)), names, stage="t", arm="N", key="t:N:" + task_id, ctx_limit=10 ** 9)
    ev = xp.evaluate_episode(bfcl, rec, names)
    assert ev["solved"] and ev["state_all"] and not ev["replay_mismatch"] and set(ev["labels"]) == {"PASSED"} and ev["progress"] == 1.0
    again = xp.evaluate_episode(bfcl, rec, names)                      # a second evaluation in the same process: fresh names, same result
    assert {k: again[k] for k in ("solved", "labels", "state_turns")} == {k: ev[k] for k in ("solved", "labels", "state_turns")}


@needs_bfcl
def test_reusing_a_bfcl_name_carries_state_over(bfcl):
    """Documents the hazard that 8.1 guards against: same model_name, same task -> the second run starts from the first one's end state."""
    task = bfcl.tasks["multi_turn_base_50"]
    out1, inst1 = bfcl.execute(["fillFuelTank(fuelAmount=5.0)"], task, "xp0_hazard_demo")
    level1 = inst1["VehicleControlAPI"].fuelLevel
    out2, inst2 = bfcl.execute(["fillFuelTank(fuelAmount=5.0)"], task, "xp0_hazard_demo")
    assert inst2["VehicleControlAPI"].fuelLevel == level1 + 5.0
    _, fresh = bfcl.execute(["fillFuelTank(fuelAmount=5.0)"], task, xp.Names("hz").new("fresh"))
    assert fresh["VehicleControlAPI"].fuelLevel == level1


@needs_bfcl
def test_silent_model_fails_first_turn(bfcl):
    names = xp.Names("ts")
    rec = xp.run_episode(bfcl, bfcl.tasks["multi_turn_base_50"], FakeClient(lambda t, s, m: '{"calls": []}'), names, stage="t", arm="N", key="t:N:x", ctx_limit=10 ** 9)
    ev = xp.evaluate_episode(bfcl, rec, names)
    assert not ev["solved"] and ev["checker_error_type"] == "multi_turn:empty_turn_model_response" and ev["labels"][0] == "FAILED"


@needs_bfcl
def test_invalid_output_and_invalid_call_are_not_executed(bfcl):
    script = {0: "not json", 1: '{"calls": [{"name": "setHeadlights", "arguments": {"mode": 3}}]}', 2: '{"calls": []}'}
    names = xp.Names("ti")
    client = FakeClient(lambda t, s, m: script.get(s, '{"calls": []}'))
    rec = xp.run_episode(bfcl, bfcl.tasks["multi_turn_base_50"], client, names, stage="t", arm="N", key="t:N:y", ctx_limit=10 ** 9)
    steps = rec["turns"][0]["steps"]
    assert steps[0].get("invalid_output") and not steps[1]["calls"][0]["valid"] and xp.executed_turns(rec)[0] == []
    second_messages = client.seen[1][1]
    assert second_messages[-1]["content"].startswith("RESULTS: ") and "invalid output" in second_messages[-1]["content"]
    ev = xp.evaluate_episode(bfcl, rec, names)
    assert ev["invalid_outputs"] == 1 and ev["invalid_calls"] == 1 and not ev["solved"]


@needs_bfcl
def test_step_limit_forces_termination(bfcl):
    names = xp.Names("tf")
    loop = '{"calls": [{"name": "setHeadlights", "arguments": {"mode": "on"}}]}'
    rec = xp.run_episode(bfcl, bfcl.tasks["multi_turn_base_50"], FakeClient(lambda t, s, m: loop), names, stage="t", arm="N", key="t:N:z", ctx_limit=10 ** 9)
    assert rec["status"] == "forced_termination" and len(rec["turns"][0]["steps"]) == xp.MAX_STEPS
    assert not xp.evaluate_episode(bfcl, rec, names)["solved"]


@needs_bfcl
def test_context_overflow_ends_episode(bfcl):
    names = xp.Names("tc")
    rec = xp.run_episode(bfcl, bfcl.tasks["multi_turn_base_50"], FakeClient(lambda t, s, m: '{"calls": []}'), names, stage="t", arm="N", key="t:N:w", ctx_limit=100)
    assert rec["status"] == "context_overflow"


@needs_bfcl
def test_memory_block_only_in_current_turn_and_identical_system_prompt(bfcl):
    task_id = "multi_turn_base_65"
    assert len(bfcl.gt[task_id]) >= 2
    row = {"source_task": "multi_turn_base_1", "turn": 0, "order": 0, "request": "Lock all doors", "label": "PASSED",
           "steps": [{"call": "lockDoors(unlock=False, door=['driver'])", "result": "{}", "error": False}]}
    memory = lambda tid, ti, req: ([row], {"pool": "test"})
    c1, c2 = FakeClient(gold_policy(bfcl, task_id)), FakeClient(gold_policy(bfcl, task_id))
    r1 = xp.run_episode(bfcl, bfcl.tasks[task_id], c1, xp.Names("m1"), stage="t", arm="R", key="t:R", ctx_limit=10 ** 9, memory=memory)
    r2 = xp.run_episode(bfcl, bfcl.tasks[task_id], c2, xp.Names("m2"), stage="t", arm="N", key="t:N", ctx_limit=10 ** 9)
    assert r1["system_sha256"] == r2["system_sha256"] and r1["schema_sha256"] == r2["schema_sha256"]
    assert all(m1[2] == m2[2] and m1[1][0] == m2[1][0] for m1, m2 in zip(c1.seen, c2.seen))
    for _, messages, _ in c1.seen:
        assert sum(xp.MEMORY_HEADER in m["content"] for m in messages) == 1
        assert xp.MEMORY_HEADER in [m for m in messages if m["role"] == "user" and not m["content"].startswith("RESULTS:")][-1]["content"]


@needs_bfcl
def test_normalise_call_maps_positional_and_numbers(bfcl):
    a = xp.normalise_call("pressBrakePedal(pedalPosition=1)", bfcl.signatures)
    b = xp.normalise_call("pressBrakePedal(1.0)", bfcl.signatures)
    assert a == b


# ----------------------------------------------------------------------------- frozen artefacts (leakage), checked once they exist

def _split():
    p = DATA / "split.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def test_split_disjoint_and_sized():
    split = _split()
    if split is None:
        pytest.skip("split not created yet")
    assert not set(split["train"]) & set(split["test"]) and len(split["train"]) == 20 and len(split["test"]) == 30


def test_pools_have_no_test_provenance_and_placebo_has_no_test_functions():
    split = _split()
    pools = DATA / "pools"
    if split is None or not pools.exists():
        pytest.skip("pools not built yet")
    test = set(split["test"])
    for name in ("A", "A_plus", "G", "F"):
        rows = xp.read_jsonl(pools / f"{name}.jsonl")
        assert rows and not any(r["source_task"] in test for r in rows)
    vc = {f"multi_turn_base_{i}" for i in range(50, 100)}
    assert all(r["source_task"] not in vc for r in xp.read_jsonl(pools / "F.jsonl"))
    if BFCL_ROOT.is_dir():
        b = xp.Bfcl(BFCL_ROOT)
        vc_names = {d["name"] for t in vc for d in b.functions(b.tasks[t])}
        assert not any(s["call"].split("(")[0] in vc_names for r in xp.read_jsonl(pools / "F.jsonl") for s in r["steps"])
    plan = json.loads((DATA / "exposure.json").read_text(encoding="utf-8"))["retrieval"]
    a_ids = {xp.pool_row_id(r) for r in xp.read_jsonl(pools / "A.jsonl")}
    ap_ids = {xp.pool_row_id(r) for r in xp.read_jsonl(pools / "A_plus.jsonl")}
    for key, mem in plan.items():
        assert key.rsplit(":", 1)[0] in test
        assert set(mem["R"]) <= a_ids and set(mem["R+"]) <= ap_ids and set(mem["S"]) <= ap_ids
        assert not any(i.rsplit(":", 1)[0] in test for arm in ("R", "R+", "S", "O") for i in mem[arm])
