"""Unit tests for AAMR-NIGHT-2 (scripts/aamr_night2.py, scripts/aamr_night2_analysis.py). No model call."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import aamr_night2 as n2  # noqa: E402
import aamr_night2_analysis as an  # noqa: E402
import experience_pilot_v0 as p0  # noqa: E402
import experience_xfer_v1 as xv  # noqa: E402

N1 = n2.N1RUN
pytestmark = pytest.mark.skipif(not (N1 / "sessions" / "sD.jsonl").exists(), reason="NIGHT-1 raw data not available")


@pytest.fixture(scope="module")
def bfcl():
    return n2.n1.bfcl_from(n2.load_config())


def row_of(domain, pred):
    return next(r for r in n2.success_pool(domain) if pred(r))


def values_text(masked_row):
    """Argument values and error messages of a masked trace, parameter names removed (they are not values)."""
    parts = []
    for s in masked_row["steps"]:
        parts.append(re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*=", "=", s["call"].split("(", 1)[1] if "(" in s["call"] else s["call"]))
        if s["result"].startswith("error"):
            parts.append(s["result"])
    return re.sub(r"<[^<>]*>", "<>", "\n".join(parts))          # markers like <file_name1> are not values


def test_import_leaves_night1_untouched_and_activate_redirects():
    names = ("RUN", "NWORK", "NDATA", "OUT", "CONFIG_PATH", "PROTOCOL_PATH")
    saved = {k: getattr(n2.n1, k) for k in names}
    active = n2.ACTIVE
    try:
        if not active:
            assert "aamr-night2" not in str(n2.n1.RUN)
        n2.activate()
        assert n2.n1.RUN == n2.RUN and "aamr-night2" in str(n2.RUN)
        assert n2.n1.CONFIG_PATH == n2.CONFIG_PATH and n2.n1.PROTOCOL_PATH == n2.PROTOCOL_PATH
        assert "aamr-night1-2026-11-12" in str(n2.N1RUN)
    finally:
        for k, v in saved.items():
            setattr(n2.n1, k, v)
        n2.ACTIVE = active


def test_budgets_and_guards():
    cfg = n2.load_config()
    b = cfg["budgets"]
    assert b["total_local"] == 21500
    assert sum(v for k, v in b.items() if k != "total_local") <= 21500
    assert cfg["paid_calls"] == 0 and cfg["base_url"].startswith("http://127.0.0.1")
    n2.guard_environment(cfg)
    with pytest.raises(n2.ProtocolError):
        n2.guard_environment(dict(cfg, base_url="https://api.deepseek.com"))


def test_task_sets_have_no_tradingbot_and_are_disjoint(bfcl):
    train, test = n2.all_train(), n2.all_test(bfcl)
    assert len(train) == 60 and len(test) == 88
    assert not set(train) & set(test)
    assert not any(100 <= xv.task_number(t) <= 149 for t in train + test)
    with pytest.raises(RuntimeError):
        xv.guard_task("multi_turn_base_120")


def test_mask_tmp_trace_marker_in_call_and_request():
    r = row_of("GFS", lambda x: "tmp directory" in x["request"])
    m, vals = n2.mask_row(r)
    assert m["steps"][0]["call"] == "cd(folder=<folder>)"
    assert "<folder> directory" in m["request"] and "tmp" not in m["request"]
    assert "tmp" in vals


def test_mask_budget_from_earlier_result_task_196_turn_2():
    r = row_of("TRAVEL", lambda x: x["source_task"] == "multi_turn_base_196" and x["turn"] == 2)
    m, _ = n2.mask_row(r)
    assert any("budget_limit=<from an earlier result>" in s["call"] for s in m["steps"])


def test_mask_ticket_priority_from_request():
    r = row_of("TRAVEL", lambda x: "high priority of 4" in x["request"])
    m, _ = n2.mask_row(r)
    assert any("priority=<priority>" in s["call"] for s in m["steps"])
    assert "priority of <priority>" in m["request"]


def test_success_results_show_keys_and_errors_are_masked():
    r = row_of("GFS", lambda x: "tmp directory" in x["request"])
    m, _ = n2.mask_row(r)
    assert m["steps"][1]["result"] == "ok {current_directory_content}"
    assert m["steps"][0]["result"].startswith("error: cd: <v>")


def test_header_sentence_and_no_masked_value_visible_in_any_block(bfcl):
    for d in n2.DOMAINS:
        rows = {p0.pool_row_id(r): r for r in n2.success_pool(d)}
        for plan in (n2.test_plan(d), n2.leave_one_out_plan(d, bfcl)):
            for key, ids in plan.items():
                for k in (1, 2):
                    rs = [rows[i] for i in ids][:k]
                    if not rs:
                        continue
                    masked, block_vals = n2.mask_rows(rs)
                    for m, own in masked:
                        vt = values_text(m)
                        for v in block_vals:
                            assert not n2.visible(v, vt), (key, v, vt[:200])
                        for v in own:
                            assert not n2.visible(v, m["request"]), (key, v)
                    blk = n2.masked_block(rs)
                    assert blk.split("\n", 1)[0].endswith(n2.HEADER_SENTENCE)
                    assert len(blk) <= n2.BLOCK_CAP


def test_presentations_share_the_retrieved_traces(bfcl):
    plans = {d: n2.test_plan(d) for d in n2.DOMAINS}
    pr = {p: n2.providers(plans, p) for p in ("R+", "M2", "M1")}
    for d in n2.DOMAINS:
        for key in list(plans[d])[:15]:
            t, ti = key.rsplit(":", 1)
            ids = {p: pr[p][d](t, int(ti), "")[1] for p in pr}
            assert ids["M2"] == ids["R+"] == plans[d][key]
            assert ids["M1"] == plans[d][key][:1]


def test_raw_presentation_equals_night1_rplus_block():
    mem = n2.n1_memory("TRAVEL")
    old = n2.n1.rplus_provider(mem)
    new = n2.providers({d: n2.test_plan(d) for d in n2.DOMAINS}, "R+")["TRAVEL"]
    for key in list(mem["rplus_plan"])[:20]:
        t, ti = key.rsplit(":", 1)
        assert old(t, int(ti), "")[0] == new(t, int(ti), "")[0]


def test_vc_test_plan_is_the_pilot_exposure():
    ex = p0.read_json(p0.DATA / "exposure.json")["retrieval"]
    assert n2.test_plan("VC") == {k: v["R+"] for k, v in ex.items()}


def test_leave_one_out_plan_excludes_own_task(bfcl):
    for d in n2.DOMAINS:
        plan = n2.leave_one_out_plan(d, bfcl)
        assert len({k.rsplit(":", 1)[0] for k in plan}) == 20
        for key, ids in plan.items():
            t = key.rsplit(":", 1)[0]
            assert all(not i.startswith(t + ":") for i in ids)
            assert len(ids) <= 2


def test_copy_loss_measure_reproduces_reference_on_night1():
    d = an.an1.by_arm(an.rows_of(N1, "sD"))
    lost = [t for t in d["N"] if an.solved(d["N"][t]) and not an.solved(d["R+"][t])]
    copies = [t for t in lost if any(an.copy_evidence(d["R+"][t], d["N"][t])[1:])]
    assert len(lost) == 9 and len(copies) == 8
    i, vals, fns = an.copy_evidence(d["R+"]["multi_turn_base_182"], d["N"]["multi_turn_base_182"])
    assert vals == ["get_flight_cost:SSV"]


def test_changes_classify_copy_and_memory():
    rows = an.rows_of(N1, "sD")
    dd = an.an1.by_arm(rows)
    tasks = an.an1.complete_tasks(dd, ["N", "R+"], list(dict.fromkeys(r["task"] for r in rows)))
    ch = an.changes(dd, "R+", tasks)
    assert ch["losses_by_cause"].get("copy") == 8 and len(ch["gains"]) == 14


def b1_as_e2_rows():
    out = []
    for r in n2.read_rows(N1 / "sessions" / "b1.jsonl"):
        out.append(dict(r, domain="VC", note_text=r["source"]))
    return out


def test_tournament_on_night1_b1_rejects_qwen_fuel_and_keeps_oracle_and_flash():
    g, _ = an._by_sig(b1_as_e2_rows())
    fuel = g[("VC",) + an.FUEL]
    w, t = an.tournament(fuel, ["O", "Q", "F"])
    assert t["Q"]["regressions"] >= 1 and not t["Q"]["admissible"]
    assert t["O"]["admissible"] and t["F"]["admissible"]
    assert w == "F"                                         # passed 4 vs 3 (OCENA_NIGHT1 2.7)


def test_tournament_tie_order_and_none_only():
    def rows(res, pas):
        return {(f"t{i}", 0, 0): {"resolved": a, "turn_passed": b} for i, (a, b) in enumerate(zip(res, pas))}
    by = {"none": rows([0, 1], [0, 1]), "D": rows([1, 1], [1, 1]), "X": rows([1, 1], [1, 1]), "G0": rows([1, 1], [1, 0])}
    w, t = an.tournament(by, ["D", "X", "Q", "G0"])
    assert w == "D" and not t["G0"]["admissible"]
    w, _ = an.tournament({"none": rows([1], [1]), "Q": rows([0], [0])}, ["D", "X", "Q", "G0"])
    assert w is None


def test_e2_selection_falls_back_when_tool_invalid():
    rows = []
    for src, (res, pas) in {"none": (1, 1), "O": (1, 0), "S": (1, 1), "P": (1, 1), "Q": (1, 1), "F": (0, 0)}.items():
        rows.append({"domain": "VC", "function": an.FUEL[0], "error_key": an.FUEL[1], "task": "a", "turn": 0, "step": 0, "source": src,
                     "resolved": bool(res), "turn_passed": bool(pas), "note_text": src})
    det = {d: [] for d in an.DOMAINS}
    q = {d: [] for d in an.DOMAINS}
    q["VC"] = [{"function": "f", "error_key": "k", "text": "q", "source": "Q"}]
    sel = an.e2_selection(rows, det, q)
    assert not sel["tool_control"]["valid"] and sel["set_used"] == "fallback_D_else_Q"
    assert sel["sets"]["VC"] == [{"function": "f", "error_key": "k", "text": "q", "source": "Q"}]


def test_build_x_needs_two_tasks_and_uses_template():
    def fork(task, calls):
        return ({"task": task}, {"resolved": True, "turn_passed": True,
                                 "fork_steps": [{"calls": [{"valid": True, "call": c, "result": r, "error": e} for c, r, e in calls]}]})
    a = fork("t1", [("displayCarStatus(option='fuel')", '{"fuelLevel": 10.0}', False), ("fillFuelTank(fuelAmount=40.0)", '{"fuelLevel": 50.0}', False)])
    b = fork("t2", [("displayCarStatus(option='fuel')", '{"fuelLevel": 5.0}', False), ("fillFuelTank(fuelAmount=45.0)", '{"fuelLevel": 50.0}', False)])
    assert n2.build_x([], [a], "fillFuelTank", "m") is None
    x = n2.build_x([], [a, b], "fillFuelTank", "Cannot fill gas above the tank capacity.")
    assert x.startswith('fillFuelTank: error "Cannot fill gas above the tank capacity." was resolved in earlier tasks by calling displayCarStatus and then fillFuelTank again. Examples: ')
    assert "fillFuelTank(fuelAmount=40.0) -> ok" in x and " | " in x and len(x) <= n2.NOTE_CAP


def test_g0_text_is_the_spec_text():
    assert n2.g0_text("cd").startswith("cd: this error was also returned in earlier tasks, and repeating the call with guessed arguments")
    assert n2.g0_text("cd").endswith("and base the new arguments on what it returns.")


def test_states_at_most_eight_and_training_only():
    train = set(n2.all_train())
    for d in n2.DOMAINS:
        _, pts = n2.states(d)
        c = Counter((p["function"], p["error_key"]) for p in pts)
        assert max(c.values()) <= 8 and all(p["task"] in train for p in pts)
        assert len({(p["task"], p["function"], p["error_key"]) for p in pts}) == len(pts)


def test_fork_history_of_census_state_is_byte_identical_to_night1_request():
    att = {}
    want = set()
    _, pts = n2.states("GFS")
    recs = n2.training_records()
    for pt in pts[:6]:
        rec, _ = recs[pt["task"]]
        if pt["step"] + 1 < len([s for s in rec["turns"][pt["turn"]]["steps"] if "key" in s]):
            want.add(f"census:N:{pt['task']}:t{pt['turn']}:s{pt['step'] + 1}")
    with open(N1 / "attempts.jsonl", encoding="utf-8") as f:
        for line in f:
            if '"key": "census:' in line:
                a = json.loads(line)
                if a["key"] in want and a.get("request"):
                    att[a["key"]] = a["request"]["messages"]
    bfcl = n2.n1.bfcl_from(n2.load_config())
    checked = 0
    for pt in pts[:6]:
        key = f"census:N:{pt['task']}:t{pt['turn']}:s{pt['step'] + 1}"
        if key not in att:
            continue
        hist, res = n2.n1.rebuild_history(bfcl, bfcl.tasks[pt["task"]], recs[pt["task"]][0], pt["turn"], pt["step"])
        hist.append({"role": "user", "content": "RESULTS: " + json.dumps(res, ensure_ascii=False)})
        assert hist == att[key]
        checked += 1
    assert checked >= 2


def test_gateway_text_mode_and_json_mode_payloads():
    cfg = n2.load_config()
    gw = n2.Gateway2(cfg, run=n2.NWORK2 / "unit-scratch", transport=lambda *a, **k: {})
    msgs = [{"role": "user", "content": "x"}]
    assert "format" not in gw.payload("q14", msgs, n2.TEXT_MODE, 7)
    old = n2.n1.Gateway(cfg, run=n2.NWORK2 / "unit-scratch", transport=lambda *a, **k: {})
    assert gw.payload("q14", msgs, {"type": "object"}, 7) == old.payload("q14", msgs, {"type": "object"}, 7)
    assert gw.payload("q9", msgs, None, 7)["think"] is False


def test_reasoningbank_prompts_verbatim_and_parse():
    src = Path(__file__).resolve().parents[2] / "sota-research-2026-11-12/external/google-research_reasoning-bank/third_party/src/minisweagent/memory/instruction.py"
    if src.exists():
        assert src.read_text(encoding="utf-8") in (Path(n2.HERE) / "reasoningbank_prompts.py").read_text(encoding="utf-8")
    text = ("```\n# Memory Item 1\n## Title Lock doors first\n## Description Start needs locked doors.\n## Content Lock all doors, press the brake, "
            "then start.\n\n# Memory Item 2\n## Title Read fuel\n## Description d\n## Content c\n```")
    items = n2.parse_rb(text)
    assert [i["title"] for i in items] == ["Lock doors first", "Read fuel"] and items[0]["content"].startswith("Lock all doors")
    rec, ev = n2.training_records()["multi_turn_base_4"]
    msgs, query = n2.rb_messages(rec, ev)
    assert msgs[0]["content"] in (n2.rbp.SUCCESSFUL_SI.strip(), n2.rbp.FAILED_SI.strip())
    assert msgs[1]["content"].startswith("## Query and Trajectory Generated Using Previous Memory")
    assert ("The result is CORRECT." in msgs[1]["content"]) == bool(ev["solved"])
    second = n2.parse_rb("# Memory Item 1\n## Title T\n## Description D one\n## Description the actual content")
    assert second == [{"title": "T", "description": "D one", "content": "the actual content"}]
    blk = n2.rb_block_text({"items": items})
    assert blk.startswith(p0.MEMORY_HEADER) and len(blk) <= n2.BLOCK_CAP


def test_g_tools_from_training_only():
    tools = n2.g_tools("GFS")
    assert tools[0] == "cd" and "authenticate_twitter" not in tools
    assert 10 <= len(tools) + len(n2.g_tools("TRAVEL")) <= 60


def table(**solved):
    return {a: {"solved": s} for a, s in solved.items()}


def pairs(**lost):
    return {a: {"lost": l, "p_one_sided": 0.001} for a, l in lost.items()}


def test_rules_h14_main_competitors_e5_recommendation():
    assert an.h14(table(**{"R+": 30, "M2": 31, "M1": 30}), pairs(**{"R+": 5, "M2": 1, "M1": 2}), {})["verdict"] == "supported"
    assert an.h14(table(**{"R+": 30, "M2": 27, "M1": 26}), pairs(**{"R+": 5, "M2": 1, "M1": 1}), {})["verdict"] == "refuted"
    assert an.h14(table(**{"R+": 30, "M2": 30, "M1": 30}), pairs(**{"R+": 2, "M2": 1, "M1": 1}), {})["verdict"] == "untestable"
    per = {d: {"tasks": 30, "N": 5, "V0": 9} for d in an.DOMAINS}
    m = an.main_test(table(N=20, V0=30, **{"N'": 20}), {"V0": {"lost": 2, "p_one_sided": 0.001}}, per)
    assert m["verdict"] == "supported"
    assert an.main_test(table(N=20, V0=24), {"V0": {"lost": 2, "p_one_sided": 0.2}}, per)["verdict"] == "refuted"
    assert an.main_test(table(N=20, V0=27), {"V0": {"lost": 3, "p_one_sided": 0.02}}, per)["verdict"] == "intermediate"
    c = an.competitor_rule(table(N=20, K=30, **{"C-RB": 25, "C-G": 24}), pairs(K=2, **{"C-RB": 2, "C-G": 1}))
    assert c["verdict"] == "K_ahead" and c["C"] == "C-RB" and c["K_minus_N"] == 10
    assert an.e5_rule(table(N=10, K=15), pairs(K=3))["verdict"] == "repeated"
    assert an.recommendation({"verdict": "supported"}, c, {"verdict": "repeated"}) == "GOTOWE DO EGZAMINU"
    assert an.recommendation({"verdict": "refuted"}, c, {"verdict": "repeated"}) == "WRÓCIĆ DO SKŁADNIKÓW"
    assert an.recommendation({"verdict": "intermediate"}, c, {"verdict": "repeated"}) == "POPRAWIĆ NAJSŁABSZY SKŁADNIK"


def test_selection_rules_e_star_and_k():
    def mk(task, arm, ok):
        return {"task": task, "arm": arm, "episode": {"turns": []}, "evaluation": {"solved": ok, "error_results": 0, "invalid_calls": 0,
                "invalid_outputs": 0, "model_calls": 1, "status": "completed"}}
    rows = []
    for i in range(4):
        rows += [mk(f"multi_turn_base_{50 + i}", "N", i < 2), mk(f"multi_turn_base_{50 + i}", "R+", i < 3), mk(f"multi_turn_base_{50 + i}", "M2", i < 3), mk(f"multi_turn_base_{50 + i}", "M1", i < 3), mk(f"multi_turn_base_{50 + i}", "N'", i < 2)]
    assert an.select_e_star(rows)["E_star"] == "M1"
    rows = [mk("multi_turn_base_51", "N", False), mk("multi_turn_base_51", "V0", True), mk("multi_turn_base_51", "V0q", False), mk("multi_turn_base_52", "N", False), mk("multi_turn_base_52", "V0", True), mk("multi_turn_base_52", "V0q", False)]
    assert an.select_k(rows)["K"] == "V0"
    rows = [mk("multi_turn_base_51", "N", False), mk("multi_turn_base_51", "V0", True), mk("multi_turn_base_51", "V0q", True)]
    assert an.select_k(rows)["K"] == "V0q"
