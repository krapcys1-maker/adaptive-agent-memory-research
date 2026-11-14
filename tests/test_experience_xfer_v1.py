"""EXP-XFER-1 (scripts/experience_xfer_v1.py): lesson compiler, loop extensions, probe measures and leakage checks on a fake model.

Tests that need the pinned BFCL checkout or the normative prototype (both outside Git) are skipped when absent, e.g. in CI.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import experience_pilot_v0 as p0  # noqa: E402
import experience_xfer_v1 as xf  # noqa: E402

CFG = json.loads((xf.XDATA / "config.json").read_text(encoding="utf-8"))
BFCL_ROOT = (ROOT / CFG["bfcl_root"]).resolve()
needs_bfcl = pytest.mark.skipif(not (BFCL_ROOT / "bfcl_eval").is_dir(), reason="pinned BFCL checkout not present")
PROTOTYPE = xf.XWORK / "reanalysis" / "03_lesson_compiler_prototype.py"
POOL_A = p0.read_jsonl(xf.PDATA / "pools" / "A.jsonl")
SPLIT = p0.read_json(xf.PDATA / "split.json")


class FakeClient:
    """script(key, messages) -> list of raw calls. Records every request it receives."""

    def __init__(self, script):
        self.script, self.calls = script, []

    def ask(self, key, messages, seed, *, output_schema=None):
        self.calls.append({"key": key, "messages": copy.deepcopy(messages), "schema": output_schema})
        return {"text": json.dumps({"calls": self.script(key, messages)}), "done_reason": "stop",
                "usage": {"prompt_eval_count": 10, "eval_count": 5}, "wall_seconds": 0.01}


@pytest.fixture(scope="module")
def bfcl():
    return xf.bfcl_from_config(CFG)


START = {"name": "startEngine", "arguments": {"ignitionMode": "START"}}


def one_call_then_stop(call):
    def script(key, messages):
        return [] if messages[-1]["content"].startswith("RESULTS") else [call]
    return script


# ----------------------------------------------------------------------------- compiler

def test_error_key_masks_values_but_keeps_conditions_apart():
    a = xf.error_key('{"error": "All doors must be locked before starting the engine. Here are the unlocked doors: driver"}', {"ignitionMode": "START"})
    b = xf.error_key('{"error": "All doors must be locked before starting the engine. Here are the unlocked doors: rear_left, driver"}', {"ignitionMode": "START"})
    assert a == b == "all doors must be locked before starting the engine"
    assert xf.error_key('{"error": "cd: a/b: Unsupported path. Only one folder level at a time is supported."}', {"folder": "a/b"}) == "cd: <arg>: unsupported path"
    assert xf.error_key('{"error": "Invalid option"}', {"option": "on"}) == "invalid option"
    assert xf.error_key("Error during execution: No available route for the given airports.", {}) == "no available route for the given airports"
    assert xf.error_key('{"error": "Order with ID 12 not found.Here is the list"}', {"order_id": 12.0}) == "order with id <n> not found"


def synthetic_pool():
    steps = [{"call": "f(x=1)", "error": True, "result": '{"error": "First condition is not met."}'},
             {"call": "g(mode='a')", "error": False, "result": "{}"},
             {"call": "h()", "error": False, "result": "{}"},
             {"call": "f(x=2)", "error": True, "result": '{"error": "Second condition is not met."}'},
             {"call": "f(x=3)", "error": False, "result": "{}"},
             {"call": "k()", "error": True, "result": '{"error": "This one never gets resolved."}'}]
    return [{"source_task": t, "turn": 0, "label": "X", "steps": steps} for t in ("t1", "t2")]


def test_compiler_rules_on_synthetic_pool():
    lessons, rejected = xf.compile_lessons(synthetic_pool())
    first = next(l for l in lessons if l["error_key"].startswith("first"))
    second = next(l for l in lessons if l["error_key"].startswith("second"))
    assert first["fix_calls"] == ["g(mode='a')", "h()"] and first["arg_fix"] == []          # execution order; a new error is not a success
    assert second["fix_calls"] == [] and second["arg_fix"] == ["x=3.0"]
    assert first["source_turns"] == ["t1:t0", "t2:t0"]
    assert [r["function"] for r in xf.open_problems(rejected)] == ["k"]
    one_task, _ = xf.compile_lessons(synthetic_pool()[:1])
    assert one_task == []                                                                  # support of two tasks is required
    assert len(xf.compile_lessons(synthetic_pool()[:1], min_tasks=1)[0]) == 2


def test_compiler_ignores_checker_labels():
    relabelled = [dict(r, label="FAILED") for r in POOL_A]
    assert xf.compile_lessons(relabelled) == xf.compile_lessons(POOL_A)


def test_compiler_on_pilot_pool_gives_the_registered_lessons():
    lessons, rejected = xf.compile_lessons(POOL_A)
    assert [(l["function"], l["error_key"], l["tasks_resolved"], l["fix_calls"], l["arg_fix"]) for l in lessons] == [
        ("startEngine", "brake pedal needs to be pressed when starting the engine", 18, ["pressBrakePedal(pedalPosition=1.0)"], []),
        ("startEngine", "all doors must be locked before starting the engine", 14,
         ["lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])"], []),
        ("startEngine", "must press the brake fully before starting the engine", 2, ["pressBrakePedal(pedalPosition=1.0)"], [])]
    assert sorted(r["function"] for r in xf.open_problems(rejected)) == ["estimate_distance", "fillFuelTank"]
    block = xf.render_lesson_block(lessons)
    assert block.startswith(xf.LESSON_HEADER + "\n- startEngine: error \"Brake pedal") and len(block) == 698
    assert xf.render_lesson_block(lessons, {"lockDoors"}) == "" and xf.render_lesson_block([]) == ""


@pytest.mark.skipif(not PROTOTYPE.exists(), reason="normative prototype (outside Git) not present")
def test_compiler_equals_normative_prototype():
    spec = importlib.util.spec_from_file_location("xfer_prototype", PROTOTYPE)
    proto = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(proto)
    for pool, mt in ((POOL_A, 2), (POOL_A, 1), (synthetic_pool(), 2)):
        assert xf.compile_lessons(pool, min_tasks=mt) == proto.compile_lessons(pool, min_tasks=mt)
    lessons, _ = xf.compile_lessons(POOL_A)
    assert xf.render_lesson_block(lessons) == proto.render_block(lessons)
    assert [xf.note_text(l) for l in lessons] == [proto.note_text(l) for l in lessons]
    assert (xf.MIN_TASKS, xf.SHARE, xf.MSG_CHARS, xf.MAX_NOTES, xf.BLOCK_CHARS, xf.LESSON_HEADER) == (
        proto.MIN_TASKS, proto.SHARE, proto.MSG_CHARS, proto.MAX_NOTES, proto.BLOCK_CHARS, proto.HEADER)


def test_note_text_has_the_combined_form():
    les = {"function": "f", "example_message": "m", "fix_calls": ["g()"], "arg_fix": ["x=1.0"], "tasks_resolved": 2}
    assert xf.note_text(les) == 'f: error "m" was resolved by first calling g() and using x=1.0. Seen in 2 tasks.'


def test_lessons_come_from_training_tasks_only():
    lessons, _ = xf.compile_lessons(POOL_A)
    sources = {s.rsplit(":", 1)[0] for l in lessons for s in l["source_turns"]}
    assert sources and sources <= set(SPLIT["train"]) and not sources & set(SPLIT["test"])
    assert {r["source_task"] for r in POOL_A} <= set(SPLIT["train"])


# ----------------------------------------------------------------------------- prompts and guards

def test_system_v2_adds_exactly_one_line():
    v1, v2 = p0.SYSTEM_TEMPLATE.splitlines(), xf.SYSTEM_V2.splitlines()
    extra = [l for l in v2 if l not in v1]
    assert len(v2) == len(v1) + 1 and len(extra) == 1 and "do not guess" in extra[0]
    assert [l for l in v2 if l in v1] == v1


def test_reserved_trading_tasks_are_refused():
    for bad in ("multi_turn_base_100", "multi_turn_miss_param_149"):
        with pytest.raises(RuntimeError):
            xf.guard_task(bad)
    xf.guard_task("multi_turn_base_99")
    xf.guard_task("multi_turn_base_150")


def test_plans_are_deterministic_and_complete():
    test = SPLIT["test"]
    plan = xf.s1c_plan(test, ["Tp", "Tr", "G"])
    assert plan == xf.s1c_plan(test, ["Tp", "Tr", "G"]) and len(plan) == 90
    assert all(sorted(a for t2, a in plan if t2 == t) == ["G", "Tp", "Tr"] for t in test)
    entries = [{"id": f"multi_turn_miss_param_{n}", "probe_turn": 0} for n in (53, 50, 99)]
    probe = xf.s1d_plan(entries, xf.PROBE_ARMS)
    assert [e["id"] for e, _ in probe[::4]] == ["multi_turn_miss_param_50", "multi_turn_miss_param_53", "multi_turn_miss_param_99"]
    assert probe == xf.s1d_plan(list(reversed(entries)), xf.PROBE_ARMS)


def test_guidance_block_uses_the_lesson_header():
    block = xf.render_guidance_block({"startEngine": "Lock doors first.", "other": "x"}, {"startEngine"})
    assert block == xf.LESSON_HEADER + "\n- startEngine: Lock doors first."
    assert xf.render_guidance_block({"other": "x"}, {"startEngine"}) == ""


PILOT_README = "data/lab/experience-pilot-v0/README.md"


def test_pilot_files_are_unchanged():
    """The pilot is frozen at the commit named in the config.

    Every pilot file must be identical to that commit, except the README, which may only grow: the audit
    amendments of 13 November 2026 were appended under a "## Amendments" heading. The frozen text must stay
    a byte-exact prefix, and whatever follows it must start with that heading.
    """
    paths = ["scripts/experience_pilot_v0.py", "scripts/experience_pilot_v0_analysis.py", "tests/test_experience_pilot_v0.py",
             "data/lab/experience-pilot-v0", f":(exclude){PILOT_README}"]
    try:
        r = subprocess.run(["git", "diff", "--quiet", CFG["pilot_commit"], "--"] + paths, cwd=ROOT, capture_output=True, timeout=60)
        shown = subprocess.run(["git", "show", f"{CFG['pilot_commit']}:{PILOT_README}"], cwd=ROOT, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git not available")
    if r.returncode not in (0, 1) or shown.returncode != 0:
        pytest.skip("pilot commit not available in this checkout")
    assert r.returncode == 0, "pilot files differ from the frozen pilot commit"
    frozen, current = shown.stdout, (ROOT / PILOT_README).read_bytes()
    assert current.startswith(frozen), "the frozen pilot README text was changed, not only extended"
    appended = current[len(frozen):].lstrip(b"\r\n")
    assert appended == b"" or appended.startswith(b"## Amendments"), "only an Amendments section may follow the frozen README"


def test_ledger_and_stage_use_this_experiments_raw_root(tmp_path, monkeypatch):
    monkeypatch.setattr(xf, "XWORK", tmp_path)
    assert xf.ledger() == {"calls": 0, "seconds": 0.0, "runs": []}
    assert xf.remaining(CFG)["calls"] == 3600
    seen = {}

    def factory(cfg, out, max_calls):
        seen["max_calls"], seen["out"] = max_calls, out
        return FakeClient(lambda k, m: [])

    st = xf.XStage("unit", CFG, 7, factory)
    assert seen["max_calls"] == 7 and tmp_path in seen["out"].parents
    (st.out / "attempts.jsonl").write_text('{"key": "a"}\n{"key": "b"}\n', encoding="utf-8")
    st.close("completed")
    led = xf.ledger()
    assert led["calls"] == 2 and led["runs"][0]["stage"] == "unit" and xf.remaining(CFG)["calls"] == 3598
    assert xf.latest_completed("unit") == st.out


# ----------------------------------------------------------------------------- loop (needs BFCL)

@needs_bfcl
@pytest.mark.parametrize("arm", ["N", "R+"])
def test_loop_builds_the_same_messages_as_the_pilot_loop(bfcl, arm):
    task = bfcl.tasks["multi_turn_base_53"]
    a, b = FakeClient(one_call_then_stop(START)), FakeClient(one_call_then_stop(START))
    pilot = p0.run_episode(bfcl, task, a, p0.Names("eq_pilot_" + arm), stage="t", arm=arm, key="k", ctx_limit=7600,
                           memory=p0.memory_provider(arm) if arm != "N" else None)
    mine = xf.run_episode_x(bfcl, task, b, p0.Names("eq_mine_" + arm), stage="t", arm=arm, key="k", ctx_limit=7600,
                            block=xf.rplus_base_provider() if arm != "N" else None)
    assert [c["messages"] for c in a.calls] == [c["messages"] for c in b.calls] and len(a.calls) == 8
    assert [c["schema"] for c in a.calls] == [c["schema"] for c in b.calls]
    assert xf.texts(pilot) == xf.texts(mine) and pilot["status"] == mine["status"] == "completed"
    strip = lambda t: {k: v for k, v in t["memory"].items() if k != "block_text"}
    assert [strip(t) for t in pilot["turns"]] == [strip(t) for t in mine["turns"]]
    if arm == "R+":
        assert a.calls[0]["messages"][1]["content"].startswith(p0.MEMORY_HEADER)


@needs_bfcl
def test_tp_block_is_shown_every_turn_and_leaves_the_history(bfcl):
    lessons, _ = xf.compile_lessons(POOL_A)
    task = bfcl.tasks["multi_turn_base_53"]
    client = FakeClient(lambda k, m: [])
    rec = xf.run_episode_x(bfcl, task, client, p0.Names("tp"), stage="t", arm="Tp", key="k", ctx_limit=7600,
                           block=xf.lessons_block_provider(bfcl, lessons, "sha"))
    block = xf.render_lesson_block(lessons, bfcl.function_names(task))
    assert len(client.calls) == 4 and block
    for i, call in enumerate(client.calls):
        users = [m["content"] for m in call["messages"] if m["role"] == "user"]
        assert users[-1] == block + "\n\n" + task["question"][i][0]["content"]
        assert all(xf.LESSON_HEADER not in u for u in users[:-1])                       # earlier blocks are gone
        assert call["messages"][0]["content"] == p0.system_prompt(bfcl, task)
    assert all(t["memory"]["block_text"] == block and len(t["memory"]["items"]) == 3 for t in rec["turns"])


@needs_bfcl
def test_tr_note_follows_a_matching_error_once_per_episode(bfcl):
    lessons, _ = xf.compile_lessons(POOL_A)
    task = bfcl.tasks["multi_turn_base_53"]

    def script(key, messages):                       # two failing starts, then stop the turn
        return [START] if key.endswith(("s0", "s1")) else []

    client = FakeClient(script)
    rec = xf.run_episode_x(bfcl, task, client, p0.Names("tr"), stage="t", arm="Tr", key="k", ctx_limit=7600, tr_lessons=xf.tr_map(lessons))
    first_turn = [c for c in client.calls if ":t0:" in c["key"]]
    after_first = first_turn[1]["messages"][-1]["content"]
    after_second = first_turn[2]["messages"][-1]["content"]
    assert after_first.startswith("RESULTS: [") and "\n\n" + xf.NOTE_PREFIX + "startEngine: error \"All doors must be locked" in after_first
    assert after_first.count(xf.NOTE_PREFIX) == 1 and xf.NOTE_PREFIX not in after_second
    assert first_turn[0]["messages"][-1]["content"] == task["question"][0][0]["content"]  # no block at the start of a turn
    notes = [n for t in rec["turns"] for s in t["steps"] for n in s.get("notes", [])]
    assert notes == ["startEngine|all doors must be locked before starting the engine"]  # later turns repeat the error, not the note
    later = [c for c in client.calls if ":t1:s0" in c["key"]][0]["messages"]
    assert any(xf.NOTE_PREFIX in m["content"] for m in later)                            # the note stays in the history like results
    n_arm = FakeClient(script)
    xf.run_episode_x(bfcl, task, n_arm, p0.Names("tr_n"), stage="t", arm="N", key="k", ctx_limit=7600)
    assert all(xf.NOTE_PREFIX not in m["content"] for c in n_arm.calls for m in c["messages"])


@needs_bfcl
def test_probe_episode_stops_after_the_probe_turn_and_uses_v2(bfcl):
    task = bfcl.probe_tasks["multi_turn_miss_param_53"]
    assert [i for i, t in enumerate(bfcl.probe_gt[task["id"]]) if not t] == [3]
    client = FakeClient(lambda k, m: [])
    rec = xf.run_episode_x(bfcl, task, client, p0.Names("probe"), stage="t", arm="N", key="k", ctx_limit=7600,
                           system_template=xf.SYSTEM_V2, stop_after_turn=3)
    assert len(rec["turns"]) == 4 and len(task["question"]) == 5 and rec["status"] == "completed"
    system = client.calls[0]["messages"][0]["content"]
    assert system.startswith(xf.SYSTEM_V2) and system[len(xf.SYSTEM_V2):] == p0.system_prompt(bfcl, task)[len(p0.SYSTEM_TEMPLATE):]


@needs_bfcl
def test_probe_measures_count_proposed_calls_even_when_invalid(bfcl):
    task = bfcl.probe_tasks["multi_turn_miss_param_53"]

    def run(name, calls_at_probe, block=None):
        def script(key, messages):
            return calls_at_probe if ":t3:s0" in key else []
        rec = xf.run_episode_x(bfcl, task, FakeClient(script), p0.Names(name), stage="t", arm=name, key="k", ctx_limit=7600,
                               system_template=xf.SYSTEM_V2, stop_after_turn=3, block=block)
        return xf.evaluate_probe(bfcl, rec, p0.Names(name + "_ev"), 3)

    quiet = run("quiet", [])
    assert quiet["reached"] and quiet["proposed"] is False and quiet["executed"] is False and quiet["state_changed"] is False
    invalid = run("invalid", [{"name": "post_tweet", "arguments": {}}])                  # the typical attempt: a required argument is missing
    assert invalid["proposed"] is True and invalid["executed"] is False and invalid["state_changed"] is False
    acted = run("acted", [{"name": "setHeadlights", "arguments": {"mode": "on"}}])
    assert acted["proposed"] is True and acted["executed"] is True and acted["state_changed"] is True and acted["imported_argument"] is False
    block = lambda task_id, ti, request: ("memory says the handle is @SomebodyElse", ["x"], None)
    copied = run("copied", [{"name": "post_tweet", "arguments": {"content": "Tire pressures are optimal!", "mentions": ["@SomebodyElse"]}}], block)
    assert copied["imported_argument"] is True and copied["imported_values"] == ["@SomebodyElse"]  # the content is in the request


@needs_bfcl
def test_probe_not_reached_when_an_earlier_turn_is_terminated(bfcl):
    task = bfcl.probe_tasks["multi_turn_miss_param_53"]
    rec = xf.run_episode_x(bfcl, task, FakeClient(lambda k, m: [START]), p0.Names("loop"), stage="t", arm="N", key="k", ctx_limit=7600,
                           system_template=xf.SYSTEM_V2, stop_after_turn=3)
    assert rec["status"] == "forced_termination" and len(rec["turns"]) == 1
    ev = xf.evaluate_probe(bfcl, rec, p0.Names("loop_ev"), 3)
    assert ev["reached"] is False and ev["proposed"] is None


@needs_bfcl
def test_g1p_rules_and_reserved_ids(bfcl):
    rep = xf.probe_entries(bfcl, ["multi_turn_base_53", "multi_turn_base_195", "multi_turn_base_180"])
    assert rep["multi_turn_miss_param_53"]["ok"] and rep["multi_turn_miss_param_53"]["probe_turn"] == 3
    assert rep["multi_turn_miss_param_195"]["request_identical_to_base"] and not rep["multi_turn_miss_param_195"]["ok"]
    assert rep["multi_turn_miss_param_180"]["empty_turns"] > 1 and not rep["multi_turn_miss_param_180"]["ok"]
    with pytest.raises(RuntimeError):
        xf.probe_entries(bfcl, ["multi_turn_base_120"])
    with pytest.raises(RuntimeError):
        bfcl.execute([], bfcl.tasks["multi_turn_base_120"], "never_used")


@needs_bfcl
def test_probe_plan_strata_and_retrieval(bfcl):
    g1p = {"ok": ["multi_turn_miss_param_53", "multi_turn_miss_param_58"],
           "entries": xf.probe_entries(bfcl, ["multi_turn_base_53", "multi_turn_base_58"])}
    plan = xf.build_probe_plan(bfcl, SPLIT, g1p)
    by = {e["id"]: e for e in plan["entries"]}
    far, near = by["multi_turn_miss_param_53"], by["multi_turn_miss_param_58"]
    assert far["stratum"] == "far" and not far["near_exact"] and near["stratum"] == "near"
    assert all(len(e["r_plus"]) == e["probe_turn"] + 1 and e["r_plus_items"] == e["r_plus"][-1] for e in plan["entries"])
    pool_ids = {p0.pool_row_id(r) for r in p0.read_jsonl(xf.PDATA / "pools" / "A_plus.jsonl")}
    assert all(i in pool_ids for e in plan["entries"] for turn in e["r_plus"] for i in turn)
    assert near["near_exact"] == (near["same_turn_shown"] and not near["config_differs"])
    provider = xf.rplus_probe_provider(plan)
    text, ids, meta = provider(near["id"], near["probe_turn"], "ignored")
    assert ids == near["r_plus_items"] and text.startswith(p0.MEMORY_HEADER) and meta["pool"] == "A_plus"


@needs_bfcl
def test_guidance_request_lists_the_tool_history(bfcl):
    messages, n = xf.guidance_request(bfcl, "startEngine", POOL_A)
    text = messages[0]["content"]
    assert len(messages) == 1 and 0 < n <= xf.G_HISTORY
    assert "Tool: startEngine(ignitionMode: string)" in text and "| success: false" in text and "| success: true" in text
    assert text.rstrip().endswith('Return JSON {"guidance": "<text>"}.') and text.count("\n1. request: ") == 1


# ----------------------------------------------------------------------------- whole S1 pipeline on a fake model

PILOT_ATTEMPTS = xf.PILOT_E2 / "attempts.jsonl"


class PipelineFake(FakeClient):
    """Replays the pilot's real outputs in S1a (and checks that the prompts are byte-identical to the pilot's requests);
    elsewhere answers with one failing startEngine per turn. Writes attempts.jsonl so that the ledger counts its calls."""

    def __init__(self, out, pilot_requests, pilot_texts):
        super().__init__(None)
        self.out, self.pilot_requests, self.pilot_texts = out, pilot_requests, pilot_texts

    def request(self, path, body=None):
        return {"models": [{"size": 1, "size_vram": 1}]}

    def ask(self, key, messages, seed, *, output_schema=None):
        p0.append_jsonl(self.out / "attempts.jsonl", {"key": key})
        self.calls.append({"key": key})
        if key.startswith("g2:"):
            calls = {"g2:short-1": [{"name": "setHeadlights", "arguments": {"mode": "on"}}], "g2:short-2": []}.get(
                key, [{"name": "setHeadlights", "arguments": {"mode": "off"}}])
            text = json.dumps({"calls": calls})
        elif key.startswith("s1a:"):
            pilot_key = "e2:" + key[len("s1a:"):]
            assert messages == self.pilot_requests[pilot_key]["messages"], "prompt differs from the pilot's request: " + key
            assert output_schema == self.pilot_requests[pilot_key]["format"]
            text = self.pilot_texts[pilot_key]
        elif key.startswith("s1b:writer:"):
            assert output_schema == xf.G_SCHEMA and len(messages) == 1
            text = json.dumps({"guidance": "Core function: starts the engine.   Common issues: doors and brake."})
        else:
            text = json.dumps({"calls": [] if messages[-1]["content"].startswith("RESULTS") else [START]})
        return {"text": text, "done_reason": "stop", "usage": {"prompt_eval_count": 10, "eval_count": 5}, "wall_seconds": 0.01}


@needs_bfcl
@pytest.mark.skipif(not PILOT_ATTEMPTS.exists(), reason="pilot raw run (outside Git) not present")
def test_s1_pipeline_end_to_end_on_a_fake_model(tmp_path, monkeypatch):
    import shutil
    import experience_xfer_v1_analysis as an
    wanted = {f"e2:{arm}:{t}" for t in SPLIT["test"][:xf.DETERMINISM_TASKS] for arm in ("N", "R+")}
    pilot_requests = {}
    with open(PILOT_ATTEMPTS, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["key"].rsplit(":", 2)[0] in wanted:
                pilot_requests[row["key"]] = row["request"]
    pilot_texts = {s["key"]: s["text"] for r in p0.read_jsonl(xf.PILOT_E2 / "episodes.jsonl") for t in r["turns"] for s in t["steps"] if "key" in s}
    real = xf.XDATA
    before = {q.name: p0.file_sha(q) for q in real.glob("*") if q.is_file()}
    xdata, xwork = tmp_path / "data", tmp_path / "work"
    xdata.mkdir()
    shutil.copy(xf.XDATA / "config.json", xdata / "config.json")
    monkeypatch.setattr(xf, "XDATA", xdata)
    monkeypatch.setattr(xf, "XWORK", xwork)
    cfg = xf.load_config()
    factory = lambda cfg_, out, max_calls: PipelineFake(out, pilot_requests, pilot_texts)

    s0 = xf.stage_s0(cfg)
    assert s0["checker_skips_empty_ground_truth_turn"] and not s0["irrelevance_checker_called_from_multi_turn_checker"]
    assert s0["vc_probe_entries_ok"] == 50 and s0["vc_probe_near"] == 20 and s0["vc_probe_far"] == 30

    s1a = xf.stage_s1a(cfg, factory)
    assert s1a["identical_to_pilot"] and s1a["base_arms_to_run"] == ["Tp", "Tr", "G"] and len(s1a["episodes"]) == 10

    s1b = xf.stage_s1b(cfg, factory)
    assert s1b["lessons"] == 3 and s1b["lesson_tools"] == ["startEngine"] and s1b["arm_G_valid"] and s1b["projection_s1c"]["ok"]
    assert s1b["probe_counts"]["entries"] == 50 and s1b["probe_counts"]["near"] == 20 and s1b["probe_counts"]["near_exact"] <= 11
    g = p0.read_json(xdata / "g-guidance.json")
    assert g["guidance"] == {"startEngine": "Core function: starts the engine. Common issues: doors and brake."}
    lessons = p0.read_jsonl(xdata / "lessons.jsonl")
    assert {s.rsplit(":", 1)[0] for l in lessons for s in l["source_turns"]} <= set(SPLIT["train"])
    plan = p0.read_json(xdata / "probe-plan.json")
    assert all((e["stratum"] == "near") == (e["base_id"] in SPLIT["train"]) for e in plan["entries"])

    assert xf.stage_s1c(cfg, factory)["episodes"] == 90
    assert xf.stage_s1d(cfg, factory)["episodes"] == 200
    assert xf.stage_s1e(cfg, factory)["episodes"] == 30
    frozen = xf.stage_freeze(cfg)
    out = an.main(cfg)
    assert frozen["calls"] == xf.ledger()["calls"] > 0
    assert out["arms"] == ["N", "R+", "Tp", "Tr", "G", "T*"] and not out["incomplete_arms"]
    assert out["per_arm"]["N"]["solved"] == 10 and out["per_arm"]["R+"]["solved"] == 14            # the frozen pilot numbers
    assert out["per_arm"]["N"]["error_events"] == 45 and out["per_arm"]["N"]["error_results"] == 85
    assert out["per_arm"]["N"]["first_attempt_errors"] == out["per_arm"]["N"]["first_attempt_turns"] == 23
    assert out["per_arm"]["R+"]["error_events"] == 30 and out["per_arm"]["R+"]["first_attempt_errors"] == 13
    assert out["pairs"]["R+-N"]["solved"]["x_only"] == 6 and out["pairs"]["R+-N"]["solved"]["y_only"] == 2
    assert out["pairs"]["R+-N"]["layers"]["mem_layer=C"] == {"n": 38, "x_pass": 28, "y_pass": 28, "diff_pp": 0.0}
    # the fake model fails startEngine once in every turn of every new arm
    tr_notes = [n for r in p0.read_jsonl(xf.latest_completed("s1c") / "episodes.jsonl") if r["arm"] == "Tr"
                for t in r["turns"] for s in t["steps"] for n in s.get("notes", [])]
    assert tr_notes and len(tr_notes) <= 3 * 30
    assert out["probe"]["per_arm"]["N"]["all"]["uar"] == 1.0 and out["gates"]["C_probe_discriminates"]["pass"] is False
    assert out["probe"]["paired_vs_N"]["R+-N"]["all"]["pairs"] == 50
    assert set(out["gates"]) >= {"A_channel_works", "B_no_gross_harm", "D_llm_writer_not_clearly_better", "s2_may_start", "tstar_triggered"}
    assert (xdata / "lesson-usage.jsonl").exists() and (xdata / "results-s1.json").exists()
    assert {q.name: p0.file_sha(q) for q in real.glob("*") if q.is_file()} == before, "the dry run must not write into the repository"
