"""K1 supervisor (NIGHT-2 pattern, from the pilot's supervisor.py): verifies L8, refuses the real model until every owner
decision is approved and the spec is frozen, runs the worker phases T, A, S with bounded restarts (persisted across
launches), freezes raw data, runs the checker and the analysis in separate processes. Starts only the frozen worker command
(L6a); the worker installs its own hook. Never unloads models, never touches the coordinator.

Exit codes (for the coordinator's night_wrapper: --stop-codes 3,4):
  0  done (report written)                 -> wrapper writes out/raw-freeze.json and run/DONE.json
  3  stop for the owner (hook violation, protocol error, preflight, L8, missing approval, restart limit, repeated error)
  4  budget gate before A / T-length failure / hard limit outside a sampled block (owner decision)
  other (crash)                            -> the coordinator relaunches; this supervisor resumes from its state
Usage: python -I -X utf8 -B supervisor.py --base DIR --transport {ollama,fake,replay} [--stop-after-T]
--stop-after-T: manual owner checkpoint (start checklist, step T). Runs only stage T (non-experimental calls), holds
run/supervisor.lock meanwhile (the coordinator runner and night_wrapper will not start a second supervisor), exits 0.
A later launch without the flag (the runner's command) resumes at the budget gate before block A."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import k1_lib as kl  # noqa: E402

A = sys.argv[1:]
BASE = Path(A[A.index("--base") + 1]).resolve()
T = A[A.index("--transport") + 1]
STOP_T = "--stop-after-T" in A
L = kl.layout(BASE)
cfg = kl.load_cfg()
SUP = cfg["supervisor"]
PY = [sys.executable, "-I", "-X", "utf8", "-B"]
STATE = L["meta"] / "state.json"
state = kl.read_json(STATE) if STATE.exists() else {"started_at": None, "restarts": 0, "errors": {}, "events": []}


def now():
    return datetime.now(timezone.utc).isoformat()


def note(msg, **kw):
    state["events"].append(dict({"at": now(), "msg": msg}, **kw))
    state["events"] = state["events"][-400:]
    L["meta"].mkdir(parents=True, exist_ok=True)
    kl.write_json(STATE, state, indent=1)
    with open(L["meta"] / "supervisor.log", "a", encoding="utf-8") as f:
        f.write(f"{now()} {msg} {json.dumps(kw) if kw else ''}\n")
    print(msg, kw if kw else "", flush=True)


def heartbeat(stage):
    if L["run"].exists():                         # best effort (see worker.heartbeat: WinError 5 while the runner reads it)
        for i in range(5):
            try:
                kl.write_json(L["run"] / "heartbeat.json", {"at": now(), "stage": stage, "pid": os.getpid()})
                return
            except PermissionError:
                time.sleep(0.05 * (i + 1))


def stop(msg, code=kl.SUP_STOP):
    note("STOP: " + msg)
    raise SystemExit(code)


def approvals() -> list:
    """Real model only: k1_lib.approval_problems (decisions, technical choices, frozen spec and FREEZE.json copies)."""
    return kl.approval_problems(cfg)


def block_of_last_heartbeat():
    try:
        return kl.read_json(L["run"] / "heartbeat.json").get("stage")
    except (OSError, ValueError):
        return None


def run_worker(phase):
    cmd = PY + [str(CODE / "worker.py"), "--base", str(BASE), "--phase", phase, "--transport", T]
    while True:
        with open(L["meta"] / "worker.log", "a", encoding="utf-8") as log:
            p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
            while p.poll() is None:
                time.sleep(1 if T != "ollama" else 30)
                hb = L["run"] / "heartbeat.json"
                if hb.exists() and time.time() - hb.stat().st_mtime > SUP["stall_seconds"]:
                    p.kill()
                    note("worker stalled; killed", phase=phase)
            rc = p.returncode
        if rc == kl.EXIT_DONE:
            note("worker phase done", phase=phase)
            return
        if rc in (kl.EXIT_HOOK, kl.EXIT_FATAL, kl.EXIT_PREFLIGHT):
            stop({kl.EXIT_HOOK: "audit hook violation", kl.EXIT_FATAL: "fatal protocol error",
                  kl.EXIT_PREFLIGHT: "preflight failed"}[rc] + f" (phase {phase}, exit {rc}); owner decision")
        if rc == kl.EXIT_GATE:
            stop(f"budget gate, T-length or hard limit (phase {phase}); owner decision", kl.SUP_GATE)
        if rc != kl.EXIT_TRANSIENT:                                  # another exception: second one ends the block (spec 7.2)
            blk = block_of_last_heartbeat() if phase == "S" else phase
            state["errors"][str(blk)] = state["errors"].get(str(blk), 0) + 1
            if state["errors"][str(blk)] >= SUP["max_errors_per_block"]:
                if phase == "A":                                     # C4 (owner 2026-11-13): A is INCOMPLETE, then stop
                    kl.write_json(L["run"] / "A_INCOMPLETE.json", {"reason": f"second error in block A (exit {rc})", "at": now(),
                                                                    "status": "NIEUKOŃCZONY"})
                    stop(f"worker error twice in block A (exit {rc}); block A marked NIEUKOŃCZONY, no further attempts")
                if phase == "S" and blk in kl.SAMPLED:
                    kl.write_json(L["run"] / f"{blk}_ABORTED.json", {"reason": f"second error in block (exit {rc})", "at": now()})
                    note("sampled block aborted after a second error; block incomplete", block=blk, rc=rc)
                else:
                    stop(f"worker error twice in phase {phase} (exit {rc})")
        state["restarts"] += 1
        if state["restarts"] > SUP["max_restarts"]:
            stop(f"more than {SUP['max_restarts']} restarts in this run")
        note("worker restart", phase=phase, rc=rc, restarts=state["restarts"])
        time.sleep(SUP["restart_wait_seconds"] if T == "ollama" else 0)


def completed_blocks():
    a = ["A"] if (L["run"] / "A_DONE.json").exists() and not (L["run"] / "A_INCOMPLETE.json").exists() else []
    return a + [b for b in kl.SAMPLED if (L["run"] / f"{b}_DONE.json").exists()]


def freeze(blocks):
    files = [L["run"] / "sessions" / f"{b}.jsonl" for b in blocks] + [L["run"] / "attempts.jsonl", L["run"] / "responses.jsonl"]
    files += [L["run"] / f for f in ("T.json", "c_d.json", "P_check.json", "STIM_T_FROZEN.json", "T_m.json") if (L["run"] / f).exists()]
    man = {"at": now(), "files": {str(f): kl.sha_file(f) for f in files if f.exists()}}
    kl.write_json(L["meta"] / "RAW.json", man, indent=1)
    note("raw data frozen", blocks=blocks)


def run(script, *args):
    heartbeat(f"supervisor:{script}")
    p = subprocess.run(PY + [str(CODE / script), "--base", str(BASE)] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    with open(L["meta"] / "pipeline.log", "a", encoding="utf-8") as f:
        f.write(f"{now()} {script} {args} rc={p.returncode}\n{p.stdout}\n{p.stderr}\n")
    if p.returncode != 0:
        stop(f"{script} {args} failed: {p.stderr.strip()[-300:]}")
    return p.stdout


def main():
    if "--check-approvals" in A:                      # gate only: no state file, no run dir, no worker, no model
        miss = approvals()
        print("APPROVALS COMPLETE" if not miss else "approvals missing: " + "; ".join(miss), flush=True)
        raise SystemExit(0 if not miss else kl.SUP_STOP)
    diff = kl.verify_manifest(L)
    if diff:
        stop(f"L8 manifest differs: {diff[:3]}")
    if T == "ollama":
        miss = approvals()
        if miss:
            stop("real model refused: owner approvals missing: " + "; ".join(miss))
    if T == "replay":
        stop("the replay transport is a worker test option; the supervisor does not run it")
    state["started_at"] = state["started_at"] or now()
    note("start", base=str(BASE), transport=T)
    if not (L["run"] / "T_DONE.json").exists():
        if STOP_T:
            L["run"].mkdir(parents=True, exist_ok=True)
            lock = L["run"] / "supervisor.lock"
            if lock.exists():
                stop("run/supervisor.lock exists: another supervisor may be running; not starting stage T")
            lock.write_text(str(os.getpid()))
            try:
                run_worker("T")
            finally:
                lock.unlink(missing_ok=True)
        else:
            run_worker("T")
    if STOP_T:
        heartbeat("supervisor:stopped-after-T")
        note("stopped after stage T as requested (owner checkpoint); next launch continues at the gate before A")
        return
    if not (L["run"] / "A_DONE.json").exists() and not (L["run"] / "A_INCOMPLETE.json").exists():
        run_worker("A")
    if not (L["run"] / "S_DONE.json").exists():
        run_worker("S")
    blocks = completed_blocks()
    freeze(blocks)
    run("checker.py", "--blocks", *blocks)
    out = run("analyze.py", "--final")
    heartbeat("supervisor:done")
    note("done", blocks=blocks, analysis=out.strip()[-200:])


if __name__ == "__main__":
    main()
