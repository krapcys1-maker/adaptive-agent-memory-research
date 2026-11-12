"""Tests for AAMR-NIGHT-1 (no model calls: a fake transport stands in for Ollama and DeepSeek)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import aamr_night1 as n1  # noqa: E402
import experience_pilot_v0 as p0  # noqa: E402
import experience_xfer_v1 as xv  # noqa: E402

PILOT_OK = (p0.WORK / "raw" / "e1a").exists()
BFCL_OK = (p0.ROOT / n1.load_config()["bfcl_root"]).exists()


class FakeOllama:
    """Answers /api/chat with scripted texts; counts calls; can fail on demand."""

    def __init__(self, script=None, fail_at=None):
        self.calls, self.script, self.fail_at = 0, script or (lambda payload: '{"calls": []}'), set(fail_at or [])

    def __call__(self, path, body=None, timeout=None):
        if path == "/api/chat":
            self.calls += 1
            if self.calls in self.fail_at:
                raise ConnectionError("simulated outage")
            return {"model": body["model"], "done": True, "done_reason": "stop", "message": {"content": self.script(body)},
                    "prompt_eval_count": 10, "eval_count": 5}
        if path == "/api/version":
            return {"version": "test"}
        return {"models": []}


@pytest.fixture()
def run(tmp_path, monkeypatch):
    monkeypatch.setattr(n1, "RUN", tmp_path)
    return tmp_path


def cfg(**budget):
    c = n1.load_config()
    c = json.loads(json.dumps(c))
    c["budgets"].update(budget)
    c["extra_ledger_dirs"] = []
    c["retry"]["backoff_seconds"] = [0, 0, 0]
    return c


# ----------------------------------------------------------------------------- frozen texts and splits

def test_oracle_and_placebo_match_the_frozen_spec():
    spec = (p0.ROOT.parent / "direction-review-2026-11-12" / "OCENA_KIERUNKU.md").read_text(encoding="utf-8")
    blocks = [b.strip() for b in spec.split("```text")[1:]]
    blocks = [b.split("```")[0].strip() for b in blocks]
    assert n1.ORACLE == blocks[0]
    assert n1.PLACEBO == blocks[1]
    assert abs(len(n1.PLACEBO) - len(n1.ORACLE)) <= 0.1 * len(n1.ORACLE)
    assert n1.STALE.count("40") == 2 and "50" not in n1.STALE


@pytest.mark.skipif(not BFCL_OK, reason="BFCL checkout missing")
def test_vc_split_equals_pilot_split_and_travel_excludes_empty_gt():
    pilot = p0.read_json(p0.DATA / "split.json")
    sp = n1.split("VC")
    assert sp["train"] == pilot["train"] and sp["test"] == pilot["test"]
    bfcl = n1.bfcl_from(n1.load_config())
    tr = n1.split("TRAVEL", bfcl)
    assert sorted(tr["excluded_empty_gt"]) == ["multi_turn_base_167", "multi_turn_base_180"]
    assert len(tr["test"]) + len(n1.split("GFS", bfcl)["test"]) == 58
    for d in ("GFS", "TRAVEL"):
        assert all(not 100 <= xv.task_number(t) <= 149 for t in n1.split(d)["train"] + n1.split(d)["test"])


def test_deterministic_lessons_unchanged_from_s1():
    rows, sha = n1.det_lessons_vc()
    assert len(rows) == 3 and all(r["function"] == "startEngine" for r in rows)
    assert n1.xv.note_text(rows[0]) == n1._orig_note_text(rows[0])
    assert n1.xv.note_text(n1.given("f", "k", "TEXT", "x")) == "TEXT"


# ----------------------------------------------------------------------------- durable files and gateway

def test_repair_tail_cuts_a_torn_line(tmp_path):
    p = tmp_path / "a.jsonl"
    p.write_bytes(b'{"a": 1}\n{"b": 2')
    assert n1.repair_tail(p)
    assert n1.read_rows(p) == [{"a": 1}]


def test_gateway_cache_budget_and_retry(run):
    fake = FakeOllama(fail_at=[1])
    gw = n1.Gateway(cfg(A=3), run, transport=fake, sleep=lambda s: None)
    msgs = [{"role": "user", "content": "x"}]
    r = gw.ask("k1", "q14", msgs, None, "A", 7)                 # first attempt fails, second succeeds
    assert r["text"] == '{"calls": []}' and fake.calls == 2 and gw.by_bucket["A"] == 2
    gw2 = n1.Gateway(cfg(A=3), run, transport=fake, sleep=lambda s: None)   # a restart reads the ledger and the cache
    assert gw2.by_bucket["A"] == 2
    assert gw2.ask("k1", "q14", msgs, None, "A", 7)["text"] == r["text"] and fake.calls == 2
    with pytest.raises(n1.ProtocolError):
        gw2.ask("k1", "q14", [{"role": "user", "content": "other"}], None, "A", 7)
    gw2.ask("k2", "q14", msgs, None, "A", 7)
    with pytest.raises(n1.BudgetExhausted):
        gw2.ask("k3", "q14", msgs, None, "A", 7)


def test_total_cap_counts_every_bucket(run):
    gw = n1.Gateway(cfg(total_local=2), run, transport=FakeOllama(), sleep=lambda s: None)
    gw.ask("a", "q14", [{"role": "user", "content": "1"}], None, "A", 7)
    gw.ask("b", "q14", [{"role": "user", "content": "2"}], None, "D", 7)
    with pytest.raises(n1.BudgetExhausted) as e:
        gw.ask("c", "q14", [{"role": "user", "content": "3"}], None, "E", 7)
    assert str(e.value) == "total_local"


def test_q9_payload_disables_thinking_and_presence_penalty(run):
    gw = n1.Gateway(cfg(), run, transport=FakeOllama())
    p = gw.payload("q9", [], None, 7)
    assert p["think"] is False and p["options"]["presence_penalty"] == 0 and p["options"]["temperature"] == 0
    assert "think" not in gw.payload("q14", [], None, 7)


# ----------------------------------------------------------------------------- Flash client

class FakeFlash:
    def __init__(self):
        self.calls = 0

    def __call__(self, path, body=None):
        if path == "/models":
            return {"data": [{"id": "deepseek-flash"}]}
        self.calls += 1
        return {"model": "deepseek-flash", "choices": [{"message": {"content": '{"note": "use x"}'}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 50}}


def test_flash_caps_cache_and_privacy(run):
    c = cfg()
    c["flash"]["max_calls"] = 2
    fake = FakeFlash()
    f = n1.Flash(c, run, key_loader=lambda: "secret", transport=fake)
    m = [{"role": "user", "content": "hello"}]
    f.ask("a", m)
    f.ask("a", m)
    assert fake.calls == 1
    with pytest.raises(n1.ProtocolError):
        f.ask("p", [{"role": "user", "content": "see D:\\\\project\\\\x"}])
    f.ask("b", [{"role": "user", "content": "two"}])
    with pytest.raises(n1.BudgetExhausted):
        f.ask("c", [{"role": "user", "content": "three"}])
    s = f.spent()
    assert s["reserved_calls"] == 2 and s["reserved_usd"] == 0.02 and fake.calls == 2
    f2 = n1.Flash(c, run, key_loader=lambda: "secret", transport=fake)       # restart: ledger still binds
    with pytest.raises(n1.BudgetExhausted):
        f2.ask("d", [{"role": "user", "content": "four"}])


def test_flash_unavailable_without_key(run):
    def boom():
        raise SystemExit("no key")
    f = n1.Flash(cfg(), run, key_loader=boom, transport=FakeFlash())
    assert f.open() is False and f.unavailable
    with pytest.raises(n1.BudgetExhausted):
        f.ask("a", [{"role": "user", "content": "x"}])


def test_privacy_patterns():
    assert n1.privacy_violations("C:\\\\Users\\\\user\\\\x")
    assert n1.privacy_violations("mail someone@gmail.com")
    assert not n1.privacy_violations("fillFuelTank(fuelAmount=30.0) -> {\"fuelLevel\": 40.0}")


# ----------------------------------------------------------------------------- notes and checks

@pytest.mark.skipif(not BFCL_OK, reason="BFCL checkout missing")
def test_note_checks_flag_unknown_tools_and_test_only_tokens():
    bfcl = n1.bfcl_from(n1.load_config())
    allowed = n1.allowed_identifiers(bfcl, "VehicleControlAPI")
    fnames = {d["name"] for d in bfcl.docs["VehicleControlAPI"]}
    ok = n1.check_note("fillFuelTank: call displayCarStatus(option='fuel') first.", allowed, fnames, (set(), set()))
    assert ok["ok"]
    bad = n1.check_note("fillFuelTank: call checkFuelGauge() first.", allowed, fnames, (set(), set()))
    assert not bad["ok"] and "checkFuelGauge" in bad["unknown_calls"]
    leak = n1.check_note("fillFuelTank: fill 37.5 gallons.", allowed, fnames, ({"37.5"}, set()))
    assert leak["leaked_tokens"] == ["37.5"]
    nums, strs = n1.test_only_tokens(bfcl, "VC")
    assert "50" not in nums                                  # in the tool description, not test-only


def test_parse_note():
    assert n1.parse_note('{"note": "read the level"}', "stop", "fillFuelTank")[0] == "fillFuelTank: read the level"
    assert n1.parse_note('{"note": "fillFuelTank needs x"}', "stop", "fillFuelTank")[0] == "fillFuelTank needs x"
    assert n1.parse_note("nope", "stop", "f")[1] == "not json"
    assert n1.parse_note('{"note":<|endoftext|> "ok"}', "stop", "f")[0] == "f: ok"
    assert n1.parse_note('{"note": "x"}', "length", "f")[1] == "length"
    assert len(n1.parse_note(json.dumps({"note": "a" * 2000}), "stop", "f")[0]) == n1.NOTE_CAP


@pytest.mark.skipif(not BFCL_OK, reason="BFCL checkout missing")
def test_writer_input_uses_training_tasks_only():
    bfcl = n1.bfcl_from(n1.load_config())
    pool = n1.vc_pool()
    train = set(p0.read_json(p0.DATA / "split.json")["train"])
    sigs = n1.signatures(pool)
    assert any((s["function"], s["error_key"]) == n1.FUEL_SIG for s in sigs) and len(sigs) == 5
    for s in sigs:
        occ = n1.occurrences(pool, s)
        assert occ and {r["source_task"] for r in occ} <= train
        msgs = n1.writer_messages(bfcl, s, occ)
        assert not n1.privacy_violations(json.dumps(msgs)) and len(json.dumps(msgs).encode()) < 30000


# ----------------------------------------------------------------------------- fork reconstruction against the pilot's real requests

@pytest.mark.skipif(not (PILOT_OK and BFCL_OK), reason="pilot raw data missing")
def test_rebuilt_history_equals_pilot_requests_byte_for_byte():
    bfcl = n1.bfcl_from(n1.load_config())
    recs, _ = n1.pilot_training_records()
    attempts = {}
    for stage in ("e1a", "e1b"):
        for a in p0.read_jsonl(p0.latest_completed(stage) / "attempts.jsonl"):
            attempts[a["key"]] = a["request"]["messages"]
    pool = n1.vc_pool()
    train = p0.read_json(p0.DATA / "split.json")["train"]
    pts = n1.replay_points(recs, train, n1.signatures(pool))
    assert len(pts) == 19
    checked = 0
    for pt in pts:
        rec = recs[pt["task"]]
        hist, res = n1.rebuild_history(bfcl, bfcl.tasks[pt["task"]], rec, pt["turn"], pt["step"])
        nxt = f"{rec['key']}:t{pt['turn']}:s{pt['step'] + 1}"
        if nxt in attempts:
            assert hist + [{"role": "user", "content": "RESULTS: " + json.dumps(res, ensure_ascii=False)}] == attempts[nxt]
            checked += 1
    assert checked >= 10


# ----------------------------------------------------------------------------- session resume with the real environment

@pytest.mark.skipif(not BFCL_OK, reason="BFCL checkout missing")
def test_session_resume_never_repeats_a_call_and_notes_are_delivered(run):
    c = cfg()
    bfcl = n1.bfcl_from(c)

    def script(payload):
        last = payload["messages"][-1]["content"]
        if last.startswith("RESULTS") or n1.xv.NOTE_PREFIX in last:
            return '{"calls": []}'
        return '{"calls": [{"name": "fillFuelTank", "arguments": {"fuelAmount": 500.0}}]}'

    fake = FakeOllama(script=script, fail_at=[7])
    gw = n1.Gateway(c, run, transport=fake, sleep=lambda s: None)
    flash = n1.Flash(c, run, key_loader=lambda: "k", transport=FakeFlash())
    ctx = n1.Ctx(c, gw=gw, flash=flash, bfcl=bfcl)
    tasks = p0.read_json(p0.DATA / "split.json")["test"][:2]
    det, _ = n1.det_lessons_vc()
    arms = {"N": {"bucket": "A"}, "TrO": {"bucket": "A", "tr": n1.lesson_map(det + [n1.given(*n1.FUEL_SIG, n1.ORACLE, "oracle")])}}
    c["retry"]["max_attempts_per_call"] = 1                       # make the outage fatal for this process
    with pytest.raises(n1.TransientFailure):
        n1.run_session(ctx, "t", "q14", tasks, arms, 1)
    first = len(n1.read_rows(run / "sessions" / "t.jsonl"))
    calls_before = fake.calls
    ctx2 = n1.Ctx(c, gw=n1.Gateway(c, run, transport=fake, sleep=lambda s: None), flash=flash, bfcl=bfcl)
    out = n1.run_session(ctx2, "t", "q14", tasks, arms, 1)
    assert out["status"] == "done" and out["episodes"] == 4 and first < 4
    resp = [r["key"] for r in n1.read_rows(run / "responses.jsonl")]
    assert len(resp) == len(set(resp))                            # every answered call was sent exactly once
    sent = [a["key"] for a in n1.read_rows(run / "attempts.jsonl")]
    assert [k for k in set(sent) if sent.count(k) > 1] == ["t:TrO:multi_turn_base_67:t1:s0"]   # only the failed call was resent
    rows = n1.read_rows(run / "sessions" / "t.jsonl")
    assert len({(r["task"], r["arm"]) for r in rows}) == 4
    shown = [n for r in rows if r["arm"] == "TrO" for t in r["episode"]["turns"] for s in t["steps"] for n in s.get("notes", [])]
    fuel_turns = [x for r in rows if r["arm"] == "TrO" for x in __import__("aamr_night1_analysis").fuel_turns(r["episode"], r["evaluation"])]
    if fuel_turns:
        assert any("fillFuelTank|" in n for n in shown)
    assert fake.calls > calls_before
