"""K1: read-only check before the manual stage T (CHECKLISTA_STARTOWA_K1.md, sections B-C). No model, no Ollama call,
no write anywhere. Prints every condition and READY / NOT READY. Lives outside code/ so it is not part of the L8 manifest.
Run: python -I -X utf8 -B tools/pre_T_check.py"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import k1_lib as kl  # noqa: E402

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
L = kl.layout(ROOT / "base")
cfg = kl.load_cfg()
FROZEN = Path("D:/aamr-audit-2026-11-13/k1/v1.0.1")
rows = []


def check(name, ok, detail=""):
    rows.append(ok)
    print(f"[{'OK ' if ok else 'NO '}] {name}{': ' + str(detail) if detail else ''}")


fz = json.loads((FROZEN / "FREEZE.json").read_text(encoding="utf-8"))
check("frozen spec v1.0.1 sha = FREEZE.json", sha(FROZEN / "SPEC_K1_PLACEBO_v1.0.1.md") == fz["spec_sha256"])
check("FREEZE.json sha = config", sha(FROZEN / "FREEZE.json") == cfg.get("spec_freeze_json_sha256"))
check("executor copies byte-identical and = config", sha(cfg["spec"]) == fz["spec_sha256"] == cfg["spec_frozen_sha256"]
      and sha(Path(cfg["spec"]).parent / "FREEZE.json") == sha(FROZEN / "FREEZE.json"))
check("FREEZE.json files present and unchanged", all(Path("D:/aamr-audit-2026-11-13", f).exists()
                                                     and sha(Path("D:/aamr-audit-2026-11-13", f)) == h for f, h in fz["files"].items()))
check("stimuli = external references pinned in FREEZE.json", all(sha(f) == h for f, h in fz["external_references"].items()
                                                                  if f.endswith(".json")))
proto = {f: fz["files"][f"k1/v0.4/testy/{f}"] for f in ("k1_audit_hook.py", "k1_l4.py", "k1_length.py", "k1_v04_reading.py", "t_w6_cells.py")}
check("prototype modules = FREEZE.json", all(sha(ROOT / "code" / f) == h for f, h in proto.items()))
check("L8 manifest of base/ unchanged", not kl.verify_manifest(L), kl.verify_manifest(L)[:3])
check("real-model gate: approvals complete (k1_lib.approval_problems)", not kl.approval_problems(cfg), kl.approval_problems(cfg))
check("runner disabled in the integration entry", "enabled = false" in (ROOT / "integration" / "k1.coordinator.local.toml").read_text(encoding="utf-8"))
check("production coordinator.local.toml not created yet", not Path("D:/kordynator/coordinator.local.toml").exists())
check("no run yet (base/run absent or without T.json)", not (L["run"] / "T.json").exists())
check("no supervisor.lock", not (L["run"] / "supervisor.lock").exists())
ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_Process -Filter \"name='python.exe' or name='pythonw.exe'\" | "
                     "Where-Object { $_.CommandLine -like '*pilot-nm*' -or $_.CommandLine -like '*aamr-k1-executor*supervisor*' } | "
                     "Measure-Object | Select-Object -ExpandProperty Count"], capture_output=True, text=True)
check("no pilot or K1 supervisor process alive", ps.stdout.strip() == "0", ps.stdout.strip())
pilot = Path("D:/aamr-audit-2026-11-13/pilot-nm")
check("pilot finished (C2_DONE.json, public report)", (pilot / "run" / "C2_DONE.json").exists() and (pilot / "report" / "public.json").exists())
tl = kl.read_json(L["stim"] / "k1_T_tasks.json")
check("stage-T task lists present", all(len(tl[k][d]) for k in ("cal", "len", "recal", "len2") for d in kl.DOMAINS) and len(tl["m_tasks"]) == 12)
print("\nREADY for the manual stage T" if all(rows) else "\nNOT READY for the manual stage T")
print("Still to check by hand (needs the Ollama server, not done here): `ollama ps` empty, GPU < 2000 MiB, Ollama version noted.")
