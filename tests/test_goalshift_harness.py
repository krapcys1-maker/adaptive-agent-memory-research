"""Tests for the AAM-E0 harness: statistics, verdict rules, gates, and the Stage 2 guard rails.

No network, no key, no model. The paid loop is exercised with a fake chat client."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_goalshift_e0 as h  # noqa: E402
from corpus.goalshift_arms import CachedEmbedder, HashingEmbedder  # noqa: E402


class FakeCompletions:
    def __init__(self, answer, prompt_tokens, completion_tokens):
        self.answer, self.p, self.c = answer, prompt_tokens, completion_tokens
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        msg = SimpleNamespace(content=self.answer(kwargs) if callable(self.answer) else self.answer)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                               usage=SimpleNamespace(prompt_tokens=self.p, completion_tokens=self.c))


class FakeClient:
    def __init__(self, answer="no idea", prompt_tokens=100, completion_tokens=10):
        self.completions = FakeCompletions(answer, prompt_tokens, completion_tokens)
        self.chat = SimpleNamespace(completions=self.completions)


def _plan(n_cases=2, repeats=3):
    cases = [{"seed": 0, "probe_id": "s000-q%02d" % i, "cell": "C3", "arm": "D",
              "question": "What is the code?", "context": ["Some event text ref ab1234."],
              "gold_answer": "ab1234", "gold_in_context": 1} for i in range(n_cases)]
    return {"stage": 2, "kind": "plan", "reader": h.READER, "arms": ["D"], "cases": cases,
            "repeats": repeats, "calls": n_cases * repeats, "projected_usd_upper_bound": 0.01}


def _write_plan(tmp_path, **changes):
    plan = _plan()
    plan.update(changes)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return str(path)


def _ok_stage0(**changes):
    s0 = {"passed": True, "best_comparator": "Sum-raw", "best_comparator_by_id": "Sum",
          "script_sha256": h.script_digests(), "seeds": list(h.DEV_SEEDS), "embedder": "minilm"}
    s0.update(changes)
    return s0


def _freeze(tmp_path, monkeypatch, s0=None, config=None):
    monkeypatch.setattr(h, "OUT", tmp_path)
    (tmp_path / "config.json").write_text(json.dumps(config or h.config_dict()), encoding="utf-8")
    (tmp_path / "stage0").mkdir(exist_ok=True)
    (tmp_path / "stage0" / "results.json").write_text(json.dumps(s0 or _ok_stage0()), encoding="utf-8")


def test_parse_seeds():
    assert h.parse_seeds("0-4") == [0, 1, 2, 3, 4]
    assert h.parse_seeds("1,3,5-6") == [1, 3, 5, 6]


def test_bootstrap_is_deterministic_and_brackets_the_mean():
    diffs = [0.1, 0.2, 0.0, 0.3, 0.1, 0.2]
    a, b = h.paired_bootstrap(diffs, draws=2000), h.paired_bootstrap(diffs, draws=2000)
    assert a == b
    assert a[0] <= sum(diffs) / len(diffs) <= a[1]
    assert h.paired_bootstrap([0.0] * 5, draws=500) == (0.0, 0.0)


def test_verdict_follows_the_rules_exactly():
    v = h.verdict(0.60, 0.30, 0.10, 0.20, 0.30)
    assert v["primary"].startswith("SUPPORTED") and not v["statements"]
    v = h.verdict(0.60, 0.30, -0.01, 0.20, 0.30)  # interval includes zero
    assert v["primary"].startswith("NOT SUPPORTED")
    v = h.verdict(0.40, 0.30, 0.0, 0.38, 0.10)
    assert v["primary"].startswith("NOT SUPPORTED")
    assert any("summary index with expansion is at least as good" in s for s in v["statements"])
    v = h.verdict(0.40, 0.10, 0.1, 0.0, 0.45)
    assert any("no better than conventional retrieval" in s for s in v["statements"])
    v = h.verdict(0.45, 0.30, 0.1, 0.0, 0.1)  # 0.15 difference is the threshold, inclusive
    assert v["primary"].startswith("SUPPORTED")
    v = h.verdict(0.40, 0.20, 0.1, 0.0, 0.0)  # 0.20 is above the threshold
    assert v["primary"].startswith("SUPPORTED")
    v = h.verdict(0.40, 0.2501, 0.1, 0.0, 0.0)  # just under 0.15
    assert v["primary"].startswith("NOT SUPPORTED")


def test_verdict_threshold_is_inclusive_on_the_whole_grid_of_rates():
    """Rates are k/80 rounded to 4 places; a gap of exactly 12/80 = 0.15 must be SUPPORTED
    (raw float subtraction fails 16 of 69 such pairs, e.g. 0.35 - 0.20)."""
    pairs = [(round(a / 80, 4), round((a - 12) / 80, 4)) for a in range(12, 81)]
    assert len(pairs) == 69
    for d, best in pairs:
        assert h.verdict(d, best, 0.05, 0.0, 0.0)["primary"].startswith("SUPPORTED"), (d, best)
    assert h.verdict(0.35, 0.20, 0.01, 0.0, 0.0)["primary"].startswith("SUPPORTED")
    assert h.verdict(0.70, 0.55, 0.01, 0.0, 0.0)["primary"].startswith("SUPPORTED")
    # one probe short (11/80) is not enough
    assert h.verdict(0.3125, 0.175, 0.05, 0.0, 0.0)["primary"].startswith("NOT SUPPORTED")


def test_sum_raw_band_is_inclusive_on_the_grid():
    for a in range(4, 81):
        d, sr = round(a / 80, 4), round((a - 4) / 80, 4)  # exactly 0.05 below D
        assert h.verdict(d, d, 0.0, sr, 0.0)["statements"], (d, sr)
    assert not h.verdict(0.5, 0.5, 0.0, 0.4375, 0.0)["statements"]  # 0.0625 below: no statement


def test_best_comparator_is_chosen_from_the_summary():
    rows = [{"arm": a, "cell": "C3", "C": 250, "R": 0.10, "gold": g}
            for a, g in (("Del", 0.2), ("Sum", 0.3), ("Sum-raw", 0.25))]
    assert h.best_comparator(rows)[0] == "Sum"


def test_a_tie_between_comparators_resolves_to_del_first():
    rows = [{"arm": a, "cell": "C3", "C": 250, "R": 0.10, "gold": 0.25}
            for a in ("Sum-raw", "Sum", "Del")]
    assert h.best_comparator(rows)[0] == "Del"
    rows = [{"arm": a, "cell": "C3", "C": 250, "R": 0.10, "gold": g}
            for a, g in (("Del", 0.1), ("Sum", 0.25), ("Sum-raw", 0.25))]
    assert h.best_comparator(rows)[0] == "Sum"


def test_config_digests_cover_the_three_scripts():
    cfg = h.config_dict()
    assert set(cfg["script_sha256"]) == {"scripts/corpus/goalshift.py",
                                         "scripts/corpus/goalshift_arms.py",
                                         "scripts/run_goalshift_e0.py"}
    assert cfg["dev_seeds"] == [0, 1, 2, 3, 4] and cfg["test_seeds"][0] == 100
    assert cfg["stage2"]["reader"]["model"] == "deepseek-v4-flash"
    assert cfg["metric"]["primary"].startswith("gold = reference code")


# ---------------------------------------------------------------- scoring and statistics


def _res(texts, ids, arm="D", link_ids=(), meta=None):
    return {"arm": arm, "context": [{"event_id": i, "text": t} for i, t in zip(ids, texts)],
            "words": sum(len(t.split()) for t in texts), "ms": 1.0, "link_ids": list(link_ids),
            "meta": meta or {}}


_PROBE = {"probe_id": "s000-q00", "cell": "C3", "role": "single_owner", "gold_event_id": "e005",
          "gold_answer": "ab1234", "decoy_ids": ["e007", "e008"]}


def test_score_is_strict_on_the_reference_code_and_reports_the_id_separately():
    world = {"seed": 0}
    hit = h.score(world, _PROBE, _res(["x ref ab1234 y", "other"], ["e005", "e007"], link_ids=["e005", "e007"],
                                      meta={"stored_ids": ["e005", "e007"]}), 250, 0.1)
    assert hit["gold"] == 1 and hit["gold_id"] == 1 and hit["gold_stored"] == 1
    assert hit["decoys"] == 1 and hit["neg"] == 0 and hit["fa"] == 1 and hit["linked"] == 2
    # a summary of the gold event: present by id, answer absent -> strict miss, negative transfer
    summ = h.score(world, _PROBE, _res(["x lead words only", "decoy"], ["e005", "e007"],
                                       meta={"stored_ids": ["e005"]}), 250, 0.1)
    assert summ["gold"] == 0 and summ["gold_id"] == 1 and summ["neg"] == 1
    miss = h.score(world, _PROBE, _res(["nothing"], ["e009"], meta={"stored_ids": ["e009"]}), 250, 0.1)
    assert miss["gold"] == 0 and miss["gold_id"] == 0 and miss["gold_stored"] == 0 and miss["decoys"] == 0
    none = h.score(world, _PROBE, _res([], []), 100, None)
    assert none["gold_stored"] is None and none["neg"] == 0
    assert "ms" not in hit and "recorded_at" not in hit


def _recs(d_vals, b_vals, arm_b="Del"):
    out = []
    for seed, (d, b) in enumerate(zip(d_vals, b_vals)):
        for arm, v in (("D", d), (arm_b, b)):
            for k in range(4):
                out.append({"seed": seed, "arm": arm, "cell": "C3", "C": 250, "R": 0.10,
                            "gold": 1 if k < round(v * 4) else 0})
    return out


def test_paired_contrast_has_the_right_sign_and_interval():
    recs = _recs([1.0] * 6 + [0.5] * 4, [0.25] * 10)
    m, lo, hi = h.paired_contrast(recs, "D", "Del")
    assert m == pytest.approx(0.6 * 0.75 + 0.4 * 0.25) and lo > 0 and hi >= m >= lo
    m2, lo2, hi2 = h.paired_contrast(recs, "Del", "D")
    assert m2 == pytest.approx(-m) and hi2 < 0
    recs = _recs([0.5] * 10, [0.5] * 10)
    assert h.paired_contrast(recs, "D", "Del")[0] == 0.0


def test_run_eval_is_deterministic_and_free_of_wall_clock():
    emb = CachedEmbedder(HashingEmbedder())
    t1, t2 = [], []
    a, _ = h.run_eval([0], emb, arms=("D", "S", "Del"), Cs=(250,), Rs=(0.10,), timing=t1)
    b, _ = h.run_eval([0], CachedEmbedder(HashingEmbedder()), arms=("D", "S", "Del"), Cs=(250,),
                      Rs=(0.10,), timing=t2)
    assert a == b and t1 and len(t1) == len(t2)
    blob = json.dumps(a)
    assert '"ms"' not in blob and "recorded_at" not in blob
    s_rows = [r for r in a if r["arm"] == "S"]
    assert s_rows and all(r["n_shuffles"] == h.ArmConfig().shuffles for r in s_rows)


def test_cond_rate_uses_only_probes_where_the_gold_was_stored():
    recs = [{"arm": "O", "C": 250, "R": 0.1, "gold_stored": s, "gold": g}
            for s, g in ((1, 1), (1, 0), (0, 0), (0, 0))]
    assert h.cond_rate(recs, "O", 250, 0.1) == 0.5
    assert h.cond_rate([], "O", 250, 0.1) != h.cond_rate([], "O", 250, 0.1)  # nan


# ------------------------------------------------------------------------- Stage 2 guards


def test_stage2_run_refuses_without_authorisation_or_cap(tmp_path, capsys):
    plan = _write_plan(tmp_path)
    assert h.main(["stage2-run", "--plan", plan]) == 2
    assert h.main(["stage2-run", "--plan", plan, "--i-have-authorisation"]) == 2
    assert h.main(["stage2-run", "--plan", plan, "--i-have-authorisation", "--cap-usd", "0"]) == 2
    assert h.main(["stage2-run", "--plan", plan, "--i-have-authorisation",
                   "--cap-usd", "0.0001"]) == 2  # projection above the cap
    assert "refused" in capsys.readouterr().err


def test_stage2_run_requires_the_authorisation_flag_even_with_a_valid_cap(tmp_path, capsys):
    plan = _write_plan(tmp_path)
    assert h.main(["stage2-run", "--plan", plan, "--cap-usd", "1.0"]) == 2
    assert "i-have-authorisation" in capsys.readouterr().err


@pytest.mark.parametrize("cap", ["nan", "inf", "-inf", "-1", "0", str(h.MAX_CAP_USD + 1)])
def test_stage2_run_refuses_bad_caps(tmp_path, cap):
    plan = _write_plan(tmp_path)
    assert h.main(["stage2-run", "--plan", plan, "--i-have-authorisation", "--cap-usd=" + cap]) == 2


def test_stage2_run_ignores_a_tampered_endpoint_or_model_in_the_plan(tmp_path, capsys):
    bad = dict(h.READER, base_url="https://attacker.example/v1")
    assert h.main(["stage2-run", "--plan", _write_plan(tmp_path, reader=bad),
                   "--i-have-authorisation", "--cap-usd", "1.0"]) == 2
    bad = dict(h.READER, model="other-model")
    assert h.main(["stage2-run", "--plan", _write_plan(tmp_path, reader=bad),
                   "--i-have-authorisation", "--cap-usd", "1.0"]) == 2
    assert "frozen READER" in capsys.readouterr().err


def test_stage2_loop_stops_below_the_cap_and_scores_mechanically(tmp_path):
    client = FakeClient(answer="The code is ab1234.", prompt_tokens=1_000_000, completion_tokens=0)
    summary = h.run_stage2(_plan(), client, cap_usd=0.5, ledger_path=tmp_path / "led.json",
                           out_dir=tmp_path / "out")
    assert summary["calls"] == 1  # 0.27 spent; the next call could cost 0.405 more
    assert summary["spent_usd"] <= 0.5 and summary["stopped_by_cap"]
    rows = [json.loads(l) for l in (tmp_path / "out" / "outputs.jsonl").read_text().splitlines()]
    assert rows[0]["correct"] == 1
    assert len(client.completions.calls) == 1
    assert client.completions.calls[0]["temperature"] == 0
    assert client.completions.calls[0]["model"] == "deepseek-v4-flash"
    lines = (tmp_path / "led.json").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["run_id"] == "aam-e0-stage2"


def test_stage2_loop_uses_the_frozen_model_whatever_the_plan_says(tmp_path):
    client = FakeClient()
    plan = _plan(1, 1)
    plan["reader"] = dict(h.READER, model="not-the-frozen-model")
    h.run_stage2(plan, client, cap_usd=1.0, ledger_path=tmp_path / "l.json", out_dir=tmp_path / "o")
    assert client.completions.calls[0]["model"] == h.READER["model"]


def test_stage2_loop_runs_to_completion_under_a_loose_cap_and_marks_wrong_answers(tmp_path):
    client = FakeClient(answer="I cannot tell", prompt_tokens=200, completion_tokens=20)
    summary = h.run_stage2(_plan(2, 2), client, cap_usd=1.0, ledger_path=tmp_path / "l.json",
                           out_dir=tmp_path / "o")
    assert summary["calls"] == 4 and summary["stopped_by_cap"] is None
    assert summary["by_arm"]["D"]["correct"] == 0.0


def test_stage2_pilot_limit(tmp_path):
    client = FakeClient()
    summary = h.run_stage2(_plan(2, 3), client, cap_usd=1.0, ledger_path=tmp_path / "l.json",
                           out_dir=tmp_path / "o", pilot_calls=2)
    assert summary["calls"] == 2


def test_stage2_refuses_to_append_to_existing_outputs(tmp_path):
    out = tmp_path / "o"
    out.mkdir()
    (out / "outputs.jsonl").write_text('{"x": 1}\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        h.run_stage2(_plan(), FakeClient(), 1.0, tmp_path / "l.json", out)


def test_stage2_never_writes_to_the_arena_ledger(tmp_path):
    bad = tmp_path / "data" / "lab" / "arena" / "spend-ledger.jsonl"
    with pytest.raises(SystemExit):
        h.run_stage2(_plan(), FakeClient(), 1.0, bad, tmp_path / "o")


# ------------------------------------------------------------------- the test-seed gate


def test_generate_refuses_the_frozen_test_seeds(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "OUT", tmp_path / "empty")
    with pytest.raises(SystemExit):
        h.main(["generate", "--seeds", "100", "--out", str(tmp_path)])
    with pytest.raises(SystemExit) as info:  # the flag alone is not enough: needs a freeze and Stage 0
        h.main(["generate", "--seeds", "100", "--allow-test-seeds", "--out", str(tmp_path)])
    assert "config.json" in str(info.value)
    assert h.main(["generate", "--seeds", "0", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "seed-000" / "cues.jsonl").exists()


def test_stage0_refuses_test_seeds():
    with pytest.raises(SystemExit):
        h.main(["stage0", "--seeds", "105", "--embedder", "hashing"])


def test_stage2_plan_on_the_test_seeds_needs_the_freeze(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "OUT", tmp_path / "empty")
    with pytest.raises(SystemExit) as info:
        h.main(["stage2-plan", "--embedder", "hashing", "--out", str(tmp_path / "p")])
    assert "config.json" in str(info.value)
    _freeze(tmp_path, monkeypatch)  # frozen and Stage 0 passed, but no Stage 1 result
    with pytest.raises(SystemExit) as info:
        h.main(["stage2-plan", "--embedder", "hashing", "--out", str(tmp_path / "p")])
    assert "Stage 1" in str(info.value)


def test_stage1_refuses_without_a_passing_stage0(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "OUT", tmp_path)
    with pytest.raises(SystemExit):  # no config
        h.main(["stage1", "--embedder", "hashing"])
    (tmp_path / "config.json").write_text(json.dumps(h.config_dict()), encoding="utf-8")
    with pytest.raises(SystemExit):  # no stage 0
        h.main(["stage1", "--embedder", "hashing"])
    (tmp_path / "stage0").mkdir()
    (tmp_path / "stage0" / "results.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    with pytest.raises(SystemExit) as info:
        h.main(["stage1", "--embedder", "hashing"])
    assert "did not pass" in str(info.value)


def test_stage1_refuses_when_scripts_changed_since_the_freeze(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "OUT", tmp_path)
    cfg = h.config_dict()
    cfg["script_sha256"]["scripts/corpus/goalshift.py"] = "0" * 64
    (tmp_path / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(SystemExit) as info:
        h.main(["stage1", "--embedder", "hashing"])
    assert "digests" in str(info.value)


def test_the_digest_bypass_flag_is_gone():
    with pytest.raises(SystemExit):
        h.main(["stage1", "--allow-digest-mismatch"])


def test_stage1_refuses_a_stage0_that_ran_on_other_scripts_seeds_or_embedder(tmp_path, monkeypatch):
    stale = dict(h.script_digests(), **{"scripts/corpus/goalshift_arms.py": "1" * 64})
    for bad, needle in ((_ok_stage0(script_sha256=stale), "different scripts"),
                        (_ok_stage0(seeds=[0]), "development seeds"),
                        (_ok_stage0(embedder="hashing"), "real embedder")):
        _freeze(tmp_path, monkeypatch, s0=bad)
        with pytest.raises(SystemExit) as info:
            h.main(["stage1", "--embedder", "minilm", "--model-dir", "x", "--out", str(tmp_path / "s1")])
        assert needle in str(info.value)


def test_stage1_on_the_test_seeds_needs_the_real_embedder_and_the_frozen_seed_list(tmp_path, monkeypatch):
    _freeze(tmp_path, monkeypatch)
    with pytest.raises(SystemExit) as info:
        h.main(["stage1", "--embedder", "hashing", "--out", str(tmp_path / "s1")])
    assert "minilm" in str(info.value)
    with pytest.raises(SystemExit) as info:
        h.main(["stage1", "--embedder", "minilm", "--model-dir", "x", "--seeds", "100-103",
                "--out", str(tmp_path / "s1")])
    assert "frozen test seeds" in str(info.value)
    with pytest.raises(SystemExit):  # a dry run takes development seeds only
        h.main(["stage1", "--dev-dry-run", "--embedder", "hashing", "--seeds", "100",
                "--out", str(tmp_path / "s1")])
    with pytest.raises(SystemExit):  # and never writes into the real stage1 directory
        h.main(["stage1", "--dev-dry-run", "--embedder", "hashing", "--seeds", "0"])


def test_stage1_refuses_a_second_look(tmp_path, monkeypatch):
    _freeze(tmp_path, monkeypatch)
    out = tmp_path / "s1"
    out.mkdir()
    (out / "results.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as info:
        h.main(["stage1", "--dev-dry-run", "--embedder", "hashing", "--seeds", "0", "--out", str(out)])
    assert "one look" in str(info.value)


# ------------------------------------------------------------------- end to end (hashing)


@pytest.fixture(scope="module")
def stage0_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("s0")
    code = h.main(["stage0", "--seeds", "0", "--embedder", "hashing", "--out", str(out)])
    return code, out


def test_stage0_end_to_end_with_the_hashing_embedder(stage0_run):
    code, out = stage0_run
    assert code in (0, 1)  # a non-semantic embedder is expected to fail the semantic gate
    results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert results["seeds"] == [0] and results["gates"] and "records" in results
    assert results["passed"] == all(g["passed"] for g in results["gates"]) == (code == 0)
    names = " | ".join(g["name"] for g in results["gates"])
    for needle in ("headroom", "overlap C1", "overlap C2", "semantic", "decoys", "structure",
                   "importance", "oracle", "shuffled"):
        assert needle in names
    assert (out / "report.md").read_text(encoding="utf-8").startswith("# AAM-E0 Stage 0")
    blob = (out / "results.json").read_text(encoding="utf-8") + (out / "report.md").read_text(encoding="utf-8")
    assert "recorded_at" not in blob and '"ms"' not in blob
    assert "recorded_at" in (out / "timing.json").read_text(encoding="utf-8")
    assert {"Oc", "gold_stored", "gold_id"} <= set(results["summary"][0]) | {r["arm"] for r in results["summary"]}


def test_stage0_gates_really_gate(tmp_path, monkeypatch, stage0_run):
    """A failing oracle path or headroom must fail the whole stage (mutants: gate disabled,
    passed forced True)."""
    monkeypatch.setattr(h, "cond_rate", lambda *a, **k: 0.0)
    out = tmp_path / "s0"
    assert h.main(["stage0", "--seeds", "0", "--embedder", "hashing", "--out", str(out)]) == 1
    res = json.loads((out / "results.json").read_text(encoding="utf-8"))
    oracle = next(g for g in res["gates"] if g["name"].startswith("oracle"))
    assert res["passed"] is False and oracle["passed"] is False
    monkeypatch.undo()
    monkeypatch.setitem(h.GATES, "headroom_low", 0.999)
    monkeypatch.setitem(h.GATES, "headroom_high", 1.0)
    out2 = tmp_path / "s0b"
    assert h.main(["stage0", "--seeds", "0", "--embedder", "hashing", "--out", str(out2)]) == 1
    res2 = json.loads((out2 / "results.json").read_text(encoding="utf-8"))
    assert next(g for g in res2["gates"] if g["name"].startswith("headroom"))["passed"] is False


def test_stage2_plan_runs_end_to_end_with_the_hashing_embedder(tmp_path):
    plan_dir = tmp_path / "plan"
    assert h.main(["stage2-plan", "--seeds", "0", "--embedder", "hashing", "--repeats", "1",
                   "--out", str(plan_dir)]) == 0
    plan = json.loads((plan_dir / "plan.json").read_text(encoding="utf-8"))
    assert plan["calls"] == 12 * len(h.STAGE2_ARMS)
    assert plan["reader"]["model"] == "deepseek-v4-flash"
    assert all(c["context"] is None for c in plan["cases"] if c["arm"] == "A")


def test_stage1_dry_run_end_to_end_on_development_seeds_with_the_hashing_embedder(tmp_path, monkeypatch):
    """Mechanics only: dev seeds stand in for the test seeds, which are never generated here."""
    _freeze(tmp_path, monkeypatch, s0=_ok_stage0(best_comparator="Sum", best_comparator_by_id="Del"))
    out = tmp_path / "s1"
    assert h.main(["stage1", "--dev-dry-run", "--seeds", "0-1", "--embedder", "hashing",
                   "--out", str(out)]) == 0
    res = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert res["dry_run"] is True and res["seeds"] == [0, 1]
    assert res["best_comparator_chosen_on_dev"] == "Sum" and res["n_scenarios"] == 2
    assert res["verdict"]["primary"].startswith(("SUPPORTED", "NOT SUPPORTED"))
    assert res["primary_by_id"]["best_comparator_chosen_on_dev"] == "Del"
    assert set(res["comparators"]) == {"Del", "Sum", "Sum-raw"}
    assert set(res["controls_contrast"]) == {"F2", "S", "Oc"}
    assert res["role_table"] and len(res["sensitivity_D"]) == len(h.VARIANTS)
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "DRY RUN" in report and "Verdict, exactly as the rules say" in report
    assert "stored but not retrieved" in report and "by role" in report
    assert len((out / "records.jsonl").read_text(encoding="utf-8").splitlines()) > 100
    assert "ms" not in json.loads((out / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert (out / "timing.json").exists()
    # a second run into the same directory is refused
    with pytest.raises(SystemExit):
        h.main(["stage1", "--dev-dry-run", "--seeds", "0", "--embedder", "hashing", "--out", str(out)])
