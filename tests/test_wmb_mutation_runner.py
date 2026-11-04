"""Runner protocol tests; kernel behavior is exercised by the registered run."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wmb_mutation_runner", ROOT / "scripts/wmb/mutate_kernel.py")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


@pytest.mark.parametrize("version,path", [("0.1.0", runner.FROZEN), ("0.2.0", runner.LIVE)])
def test_catalogue_is_unique_applicable_and_compiles_without_touching_source(version, path):
    before = (ROOT / path).read_bytes()
    text = (ROOT / path).read_text(encoding="utf-8")
    entries = runner.catalogue(version)
    assert len(entries) >= 38 and len({m.name for m in entries}) == len(entries)
    for entry in entries:
        changed = runner.apply(text, entry)
        assert changed != text
        assert text.count(entry.old) == 1
    assert (ROOT / path).read_bytes() == before


@pytest.mark.parametrize("source", ["missing", "old old"])
def test_a_drifted_or_ambiguous_mutation_refuses(source):
    with pytest.raises(ValueError, match="expected one"):
        runner.apply(source, runner.Mutation("bad", "old", "new"))


@pytest.mark.parametrize("outcome,reason,expected", [("killed", "", 0), ("survived", "", 1),
                                                      ("error", "", 1), ("survived", "explicit test equivalence reason", 0)])
def test_only_test_failures_kill_and_survivors_need_an_explicit_reason(tmp_path, monkeypatch, outcome, reason, expected):
    original = runner.catalogue("0.1.0")[0]
    monkeypatch.setattr(runner, "catalogue", lambda _: [runner.dataclasses.replace(original, equivalent_reason=reason)])
    calls = []
    def fake(*args):
        calls.append(args)
        return dict(outcome="survived" if len(calls) == 1 else outcome, seconds=0.0, detail="synthetic executor result")
    monkeypatch.setattr(runner, "run_copy", fake)
    out = tmp_path / "report.json"
    assert runner.main(["--json", str(out)]) == expected
    report = json.loads(out.read_text())
    assert len(calls) == 2 and report["files_unchanged"] is True
    assert report["counts"][outcome] == 1


def test_failing_baseline_never_runs_a_mutant(monkeypatch):
    calls = []
    def fail(*args):
        calls.append(args)
        return dict(outcome="error", seconds=0.0, detail="collection failed")
    monkeypatch.setattr(runner, "run_copy", fail)
    assert runner.main(["--only", "build-as-of-inclusive"]) == 2
    assert len(calls) == 1


def test_existing_output_or_source_can_never_be_overwritten(tmp_path, monkeypatch):
    def forbidden(*_):
        raise AssertionError("should refuse before running pytest")
    monkeypatch.setattr(runner, "run_copy", forbidden)
    for path in [ROOT / runner.FROZEN, tmp_path / "report.json"]:
        if not path.exists():
            path.write_text("keep me", encoding="utf-8")
        before = path.read_bytes()
        assert runner.main(["--only", "build-as-of-inclusive", "--json", str(path)]) == 2
        assert path.read_bytes() == before


def test_timeout_terminates_the_process_tree_and_is_an_error(monkeypatch):
    stopped = []
    class Process:
        pid = 424242
        def communicate(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired("fake", timeout)
            return "", ""
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *a, **k: Process())
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: stopped.append(a))
    monkeypatch.setattr(runner.os, "killpg", lambda *a: stopped.append(a), raising=False)
    source = (ROOT / runner.FROZEN).read_text(encoding="utf-8")
    result = runner.run_copy(ROOT / runner.FROZEN, [Path("tests/test_wmb_memory_kernel.py")], source, 0.1)
    assert stopped and result["outcome"] == "error" and "timed out" in result["detail"]
