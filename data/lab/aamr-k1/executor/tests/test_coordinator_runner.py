"""K1 executor under the REAL coordinator runner (aamr_coord.lab.runner), in the coordinator's isolated test world
(fixture `env` of D:/kordynator/tests/conftest.py: temporary DB, config and workspace; production DB, config and Task
Scheduler untouched). Launch command = the integration template: night_wrapper.py -> K1 supervisor (fake transport).

Run (from this directory; nothing is written to D:/kordynator):
  set PYTHONDONTWRITEBYTECODE=1 & set PYTHONPATH=D:/kordynator;D:/kordynator/tests
  python -B -m pytest test_coordinator_runner.py -p conftest -p no:cacheprovider -q
Needs a prepared base: tests/_tmp/u1 (from run_tests.py U1) is copied to the pytest temporary directory."""
import json
import shutil
import sys
import time
from pathlib import Path

import pytest

from aamr_coord.config import Experiment
from aamr_coord.lab import runner as runner_mod
from aamr_coord.lab.registry import Registry
from aamr_coord.lab.runner import kill_owned, process_created

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
PREPARED = HERE / "_tmp" / "u1"
WRAPPER = Path("D:/kordynator/aamr_coord/lab/night_wrapper.py")
NAME = "K1"
PY = [sys.executable, "-I", "-X", "utf8", "-B"]


def launch(base: Path) -> list:
    return ([sys.executable, str(WRAPPER), "--run-dir", str(base / "run"), "--out-dir", str(base / "out"), "--stop-codes", "3,4",
             "--log", str(base / "meta" / "supervisor.log"), "--"]
            + PY + [str(CODE / "supervisor.py"), "--base", str(base), "--transport", "fake"])


@pytest.fixture
def k1lab(env, tmp_path, monkeypatch):
    if not (PREPARED / "meta" / "MANIFEST.json").exists():
        pytest.skip("run tests/run_tests.py U1 first (prepared base tests/_tmp/u1)")
    monkeypatch.setattr(runner_mod, "gpu_used_mib", lambda: 300)
    spawned = []
    real = runner_mod.spawn

    def track(*a, **k):
        pid = real(*a, **k)
        spawned.append((pid, process_created(pid)))
        return pid

    monkeypatch.setattr(runner_mod, "spawn", track)

    def make(tamper=False):
        c = env(level=1)
        base = tmp_path / "k1base"
        shutil.copytree(PREPARED, base, ignore=shutil.ignore_patterns("run", "eval", "report", "out", "state.json", "*.log", "RAW.json"))
        if tamper:
            f = base / "stim" / "k1_tasks.json"
            f.write_text(f.read_text(encoding="utf-8") + " ", encoding="utf-8")
        spec = tmp_path / "SPEC_K1_test_frozen.md"
        spec.write_text("K1 protocol (test copy)", encoding="utf-8")
        c.cfg.experiments[:] = [Experiment(
            name=NAME, run_dir=base / "run", out_dir=base / "out", spec=spec, reviewed_by=None, scheduled_task="",
            required_outputs=["raw-freeze.json"], launch=launch(base), launch_cwd=CODE, max_launches=6, max_hours=None)]
        c.cfg.raw["runner"] = {"enabled": True, "backoff_minutes": 0}
        c.cfg.raw.setdefault("lab", {}).setdefault("experiments", {})[NAME] = {
            "baseline_arm": "N", "test_sessions": ["S1", "S2"], "memory_arms": ["M", "X", "S"], "placebo_arms": ["P"],
            "test_tasks": "file:" + str(base / "stim" / "k1_test_tasks_88.json"),
            "pin": [str(CODE / "supervisor.py"), str(CODE / "worker.py"), str(CODE / "k1_config.json"), str(base / "meta" / "MANIFEST.json")]}
        reg = Registry(c)
        reg.propose(NAME, {"title": "K1 test", "protocol_path": str(spec), "models": {"subject": "fake"},
                           "hypotheses": [{"id": "K1-MP", "statement": "s", "falsification": "f"}],
                           "datasets": [{"name": "BFCL multi-turn 148", "split": "dev"}]})
        reg.admit(NAME, by="owner")
        c.base = base
        return c

    yield make
    for pid, created in spawned:
        kill_owned(pid, created)


def rstate(c):
    return c.s.get_watch(f"runner:{NAME}") or {}


def ticks_until(c, cond, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        c.tick()
        if cond():
            return True
        time.sleep(1.0)
    return False


def test_runner_runs_k1_to_done_with_leak_check(k1lab):
    c = k1lab()
    assert ticks_until(c, lambda: rstate(c).get("finished") or rstate(c).get("closed"), timeout=900), "runner did not finish"
    assert rstate(c).get("finished") and not rstate(c).get("closed"), rstate(c)
    assert (c.base / "run" / "DONE.json").exists() and (c.base / "out" / "raw-freeze.json").exists()
    rep = (c.cfg.workspace / "lab" / NAME / "RUN_REPORT.md").read_text(encoding="utf-8")
    ver = json.loads((c.cfg.workspace / "lab" / NAME / "verification.json").read_text(encoding="utf-8"))
    lk = ver["levels"]["leakage"]
    print("RUN_REPORT head:", rep[:400].replace("\n", " | "))
    print("leakage:", {k: lk.get(k) for k in ("status", "memory_sources", "test_tasks", "overlap")})
    assert "**done**" in rep and "Kontrola przecieków: pass" in rep
    assert lk["status"] == "pass" and lk["test_tasks"] == 88 and not lk["overlap"]
    assert (c.base / "report" / "K1_RAPORT.md").exists()


def test_runner_stops_on_l8_tamper_without_relaunch(k1lab):
    c = k1lab(tamper=True)
    assert ticks_until(c, lambda: rstate(c).get("closed") or rstate(c).get("finished"), timeout=180)
    for _ in range(5):
        c.tick()
        time.sleep(0.5)
    st = json.loads((c.base / "run" / "STOPPED.json").read_text(encoding="utf-8"))
    print("STOPPED:", st["wrapped_rc"], st["log_tail"][-1:])
    assert st["wrapped_rc"] == 3 and not (c.base / "run" / "DONE.json").exists()
    assert rstate(c).get("launches") == 1 and rstate(c).get("closed") and not rstate(c).get("finished")
