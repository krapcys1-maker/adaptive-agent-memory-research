"""Regression tests for PR 90 R1–R3. Synthetic inputs and fake models only."""
import copy
import json
from pathlib import Path

import pytest

import test_persona_battery as f
import persona_battery_v1 as v1

pb = f.pb


class Env(f.Env):
    def __init__(self, tmp):
        super().__init__(tmp)
        self.card = tmp / "card.md"
        self.card.write_text(f.SYSTEM, encoding="utf-8")
        self.items["meta"]["card_sha256"] = pb.contract.sha256_file(self.card)
        pb.write_json(self.items_path, self.items)
        cfg = pb.load_json(self.config)
        cfg["script_sha256"] = pb.load_json(v1.CONFIG)["script_sha256"]
        cfg["freeze"] = {"enforce": True}
        cfg["private_inputs_sha256"] = {
            "items.json": pb.contract.sha256_file(self.items_path),
            "card": pb.contract.sha256_file(self.card), "notes": None,
            "persona_system": pb.sha256_text(self.items["persona"]["system"]),
            "persona_system_untagged": pb.sha256_text(self.items["persona"]["system_untagged"]),
        }
        pb.write_json(self.config, cfg)

    def argv(self, stage, *extra):
        return super().argv(stage, "--card", str(self.card), *extra)

    def run(self, stage, writer=None, judge=None, summary=None, *extra):
        return v1.main(self.argv(stage, *extra),
                       generate=f.meter(writer, self.ledger, f.RUN["writer"]) if writer else f.no_call,
                       judge=f.meter(judge, self.ledger, f.RUN["judge"]) if judge else f.no_call,
                       summary_fn=summary or f.summary_for(self.ledger))

    def ctx(self):
        return f.ctx_for(self, card=self.card)

    def seed(self, task=None):
        task = task or next(t for t in pb.p1_tasks(self.ctx()) if t["meta"]["arm"] == "F")
        pb.ps.run_tasks([task], f.Model(), self.work / "p1.jsonl", 1, lambda _: None)


def rewrite_records(env, name, rows):
    pb.contract.write_text_lf(env.work / name, "".join(json.dumps(r) + "\n" for r in rows))


def test_frozen_predecessor_and_versioned_config_are_pinned():
    cfg = pb.load_json(v1.CONFIG)
    assert pb.code_problems(cfg) == []
    assert cfg["script_sha256"]["scripts/persona_battery.py"] == "26a18611542ea98a61fa10554bbbc5348f75076708896b59af0cc39a38e0bea3"
    original = pb.load_json(pb.CONFIG)
    for field in ("parameters", "readings", "calendar", "private_inputs_sha256", "budget", "caps", "kernel"):
        assert cfg[field] == original[field]


def test_unchanged_prepare_and_interrupted_resume_preserve_records(tmp_path):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    env.seed()
    old = (env.work / "p1.jsonl").read_bytes()
    baseline = (env.work / "baseline.json").read_bytes()
    assert env.run("prepare") == 0
    assert (env.work / "baseline.json").read_bytes() == baseline
    model = f.Model()
    assert env.run("run-p1", model) == 0
    assert len(model.seen) == len(pb.p1_tasks(env.ctx())) - 1
    assert (env.work / "p1.jsonl").read_bytes().startswith(old)
    assert env.run("run-p1") == 0  # No additional generation.


@pytest.mark.parametrize("change", ["profile", "honour", "kernel", "config", "items", "manifest", "controls"])
def test_changed_identity_refuses_resume_analysis_and_reprepare_before_calls(tmp_path, monkeypatch, change):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    env.seed()
    baseline = (env.work / "baseline.json").read_bytes()
    if change == "profile":
        monkeypatch.setenv("PERSONA_BATTERY_PROFILE", '{"min_evidence": 1000.0}')
    elif change == "honour":
        monkeypatch.setattr(pb, "HONOUR_RECORD", True)
    elif change == "kernel":
        monkeypatch.setattr(pb.mk, "VERSION", "changed")
    elif change == "config":
        cfg = pb.load_json(env.config)
        cfg["parameters"]["chunk"] += 1
        pb.write_json(env.config, cfg)
    elif change == "items":
        items = pb.load_json(env.items_path)
        items["persona"]["system"] += " A new sentence."
        pb.write_json(env.items_path, items)
    elif change == "manifest":
        data = pb.load_json(env.work / "baseline.json")
        data["execution_manifest"]["execution"]["honour_record"] = True
        pb.write_json(env.work / "baseline.json", data)
        baseline = (env.work / "baseline.json").read_bytes()
    else:
        pb.write_json(env.work / "free_controls.json", {})
    ledger = env.ledger.read_bytes()
    for stage in ("run-p1", "prepare", "analyse"):
        assert env.run(stage) == 1
    assert env.ledger.read_bytes() == ledger
    assert (env.work / "baseline.json").read_bytes() == baseline


@pytest.mark.parametrize("change", ["duplicate", "unknown", "digest", "metadata"])
def test_corrupt_records_refuse_analysis_and_any_resume(tmp_path, change):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    env.seed()
    rows = env.records("p1.jsonl")
    if change == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif change == "unknown":
        rows[0]["key"] = "unknown"
    elif change == "digest":
        rows[0]["psha"] = "wrong"
    else:
        rows[0]["arm"] = "K"
    rewrite_records(env, "p1.jsonl", rows)
    assert env.run("analyse") == 1
    assert env.run("run-p3") == 1  # Validates even records in another stage.


def test_prepare_cannot_adopt_answers_without_a_manifest(tmp_path):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    env.seed()
    (env.work / "baseline.json").unlink()
    assert env.run("prepare") == 1
    assert env.run("run-p1") == 1


def test_one_answer_cannot_pass_the_registered_instrument(tmp_path):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    env.seed()
    report = v1.analyse(env.ctx())
    assert report["coverage"]["p1"]["actual"] == 1
    assert report["coverage"]["p1"]["expected"] == 291
    assert report["coverage"]["p1"]["status"] == "partial"
    assert report["readings"]["p1"]["instrument_ok"] is None
    assert report["provenance"] == pb.load_json(env.work / "baseline.json")["execution_manifest"]["execution"]


def test_analysis_does_not_relabel_an_honour_run(tmp_path, monkeypatch):
    env = Env(tmp_path)
    monkeypatch.setattr(pb, "HONOUR_RECORD", True)
    assert env.run("prepare") == 0
    env.seed()
    report = v1.analyse(env.ctx())
    assert report["provenance"]["honour_record"] is True
    monkeypatch.setattr(pb, "HONOUR_RECORD", False)
    with pytest.raises(ValueError, match="identity changed"):
        v1.analyse(env.ctx())


def test_completed_p2_only_is_valid_without_other_stages(tmp_path):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    assert env.run("run-p2", f.Model()) == 0
    report = v1.analyse(env.ctx())
    assert report["coverage"]["p2"]["readings_ready"] is True
    assert report["readings"]["p2"]["retrieval_finds_write_back"] is True
    assert report["coverage"]["p1"]["status"] == "not_started"
    assert report["readings"]["p1"] is None


def test_completed_p1_only_does_not_require_unrelated_labels_or_stages(tmp_path):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    assert env.run("run-p1", f.Model()) == 0
    report = v1.analyse(env.ctx())
    assert report["coverage"]["p1"]["readings_ready"] is True
    assert report["readings"]["p1"]["instrument_ok"] is True
    assert report["coverage"]["p2"]["status"] == "not_started"


def test_labels_and_dependent_steps_need_complete_prerequisites(tmp_path):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    assert env.run("run-p7", None, None, None, "--step", "label") == 1
    assert env.run("run-p2", None, None, None, "--step", "s2") == 1


def test_all_stages_and_hand_labels_match_predecessor_statistics(tmp_path):
    env = Env(tmp_path)
    env.full_run(f.Model(), f.fake_judge)
    first = v1.analyse(env.ctx())
    assert first["coverage"]["p1"]["readings_ready"] is True
    assert first["coverage"]["p3"]["readings_ready"] is False
    f.unanswered_labels(env)
    f.blind_labels(env)
    f.hand_labels(env, {"direct": "claim", "accusation": "implicit_denial", "indirect": "other", "pressure": "other", "benign": "other"})
    report = v1.analyse(env.ctx())
    original = pb.analyse(env.ctx())
    for key in ("p1", "p2", "p3", "p7", "readings", "records", "free_controls"):
        assert report[key] == original[key], key
    assert all(report["coverage"][name]["readings_ready"] for name in ("p1", "p2", "p3", "p7"))
    assert not pb.find_item_text(report, env.items)


def test_legacy_analysis_requires_explicit_provenance_and_is_read_only(tmp_path):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    env.seed()
    baseline = pb.load_json(env.work / "baseline.json")
    provenance = baseline.pop("execution_manifest")["execution"]
    baseline.pop("execution_manifest_sha256")
    pb.write_json(env.work / "baseline.json", baseline)
    supplied = tmp_path / "historical-results.json"
    pb.write_json(supplied, {"provenance": provenance})
    before = {p.relative_to(env.work): p.read_bytes() for p in env.work.rglob("*") if p.is_file()}
    assert env.run("analyse") == 1
    assert env.run("prepare") == 1
    assert env.run("run-p1") == 1
    report = v1.analyse(env.ctx(), supplied)
    assert report["provenance"] == provenance
    assert report["analysis_provenance"]["execution_identity"] == "legacy-declared"
    after = {p.relative_to(env.work): p.read_bytes() for p in env.work.rglob("*") if p.is_file()}
    assert before == after
    provenance["honour_record"] = True
    pb.write_json(supplied, {"provenance": provenance})
    with pytest.raises(ValueError, match="mismatch"):
        v1.analyse(env.ctx(), supplied)


def test_exports_cannot_overwrite_saved_artifacts(tmp_path):
    env = Env(tmp_path)
    assert env.run("prepare") == 0
    for dest in (env.work / "results.json", env.config):
        assert env.run("analyse", None, None, None, "--json", str(dest)) == 1
