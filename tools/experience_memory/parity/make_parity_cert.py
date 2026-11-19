"""Write and check the parity certificate of the experience_memory package.

The certificate (``tools/experience_memory/PARITY_CERT.json``) says, in a form the lab's goal code checks:
this version of the package, at this commit, reproduces the memory arm of program ALFWORLD-LADDER-R4-V5B byte for
byte on the program's own instrument and unit set, with 0 mismatches. It pins

- ``component``: package name, ``__version__`` and the last commit that changed the package code;
- ``instrument``: the SHA-256 of the program's instrument files and of its unit set, as the published program
  record declares them (``data/lab/autolab-alfworld-ladder-r4-v5b/knowledge.jsonl``, record of kind ``program``);
- ``unit_set``: how many units were compared and with which seeds;
- ``test``: the parity result (comparisons, mismatches), the command, and the log with its SHA-256.

Two steps, so that the certificate is never written by hand:

1. ``run`` (lab machine only, needs the private V5B folder): checks that the package code is committed and equal
   to its last commit, that the private instrument files hash to the published program record, runs
   ``check_v5b_parity.py private`` and writes the log ``parity/PARITY_LOG.txt``. Refuses on any mismatch.
2. ``build``: writes the certificate from the log alone; ``check`` recomputes it and compares (CI does this in
   ``tests/test_experience_memory_parity_cert.py``).

The log holds only digests and counts (no unit ids, no bank items); a run with a mismatch is refused, so the
mismatch details that would name units never reach it.

Limit: CI cannot re-run the private check, so it verifies the certificate against the log, git and the published
program record, not the log against a fresh run. The log's authenticity rests on the run on the lab machine; anyone
with the private folder can re-run ``run`` and compare the log's SHA-256 (the run is deterministic).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
REPO = PACKAGE_ROOT.parents[1]
sys.path.insert(0, str(HERE))
import check_v5b_parity as parity  # noqa: E402

NAME = "experience_memory"
PROGRAM = "ALFWORLD-LADDER-R4-V5B"
PACKAGE_DIR = "tools/experience_memory/experience_memory"
PACKAGE_INIT = PACKAGE_DIR + "/__init__.py"
PARITY_SCRIPT = "tools/experience_memory/parity/check_v5b_parity.py"
PROGRAM_RECORD = "data/lab/autolab-alfworld-ladder-r4-v5b/knowledge.jsonl"
LOG = "tools/experience_memory/parity/PARITY_LOG.txt"
CERT = "tools/experience_memory/PARITY_CERT.json"
SEEDS = "0-9"
COMMAND = f"python {PARITY_SCRIPT} private --seeds {SEEDS} --require"
SEPARATOR = "--- parity output ---"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True, text=True).stdout.strip()


def lf_sha256(text: str) -> str:
    """SHA-256 after CRLF -> LF, as the lab's goal code computes it."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def program_envelope(record_path: Path = REPO / PROGRAM_RECORD) -> dict:
    """The envelope of the program as published (payload of the record of kind ``program``)."""
    with open(record_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                if rec.get("kind") == "program" and (rec.get("payload") or {}).get("id") == PROGRAM:
                    return rec["payload"]
    raise ValueError(f"no program record of {PROGRAM} in {record_path}")


def instrument_files(envelope: dict) -> dict[str, str]:
    """``instrument/<name>`` -> SHA-256, from the envelope (whose keys are machine-local paths)."""
    out = {}
    for path, digest in (envelope.get("instrument") or {}).get("sha256", {}).items():
        out["instrument/" + path.replace("\\", "/").rsplit("/", 1)[-1]] = digest
    return dict(sorted(out.items()))


def package_version(source: str) -> str:
    for line in source.splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise ValueError("no __version__ in the package")


# --- step 1: run (lab machine) --------------------------------------------------------------------------------


def run(folder: Path) -> int:
    commit = git("log", "-1", "--format=%H", "HEAD", "--", PACKAGE_DIR)
    dirty = git("status", "--porcelain", "--", PACKAGE_DIR, PARITY_SCRIPT)
    if dirty or git("diff", "--name-only", commit, "--", PACKAGE_DIR):
        print("refusing: the package code or the parity script has uncommitted changes")
        return 2
    on_main = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "origin/main"], cwd=REPO,
                             capture_output=True).returncode == 0
    if not on_main:  # the lab accepts only a commit on AAMR main (a squash or rebase merge would drop it)
        print(f"refusing: the package commit {commit[:12]} is not on origin/main; merge the package first "
              "(with a merge commit) and certify the merged code")
        return 2
    env = program_envelope()
    files = instrument_files(env)
    for rel, digest in files.items():
        p = folder / rel
        if not p.is_file() or parity.sha256_file(p) != digest:
            print(f"refusing: {rel} of the private folder does not match the published program record")
            return 2
    units_sha = env["domain_params"]["units_sha256"]
    if units_sha != parity.V5B_PINS["data/units.json"]:
        print("refusing: the parity check pins another unit set than the published program record")
        return 2
    out = io.StringIO()
    with redirect_stdout(out):
        code = parity.main(["private", "--v5b-dir", str(folder), "--seeds", SEEDS, "--require"])
    output = out.getvalue()
    if code != 0 or "MISMATCH" in output:
        print(output)
        print(f"refusing: the parity check exited {code}; no log is written")
        return 1
    header = {
        "component": {"name": NAME, "version": package_version((REPO / PACKAGE_INIT).read_text(encoding="utf-8")),
                      "commit": commit},
        "program": PROGRAM,
        "command": COMMAND,
        "parity_script_sha256": lf_sha256((REPO / PARITY_SCRIPT).read_text(encoding="utf-8")),
        "instrument_files": files,
        "units_sha256": units_sha,
        "runner_pins": parity.V5B_PINS,
    }
    text = f"experience_memory parity log\n{json.dumps(header, indent=1)}\n{SEPARATOR}\n{output}"
    (REPO / LOG).write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    print(f"wrote {LOG}")
    return 0


# --- step 2: build / check (anywhere) ---------------------------------------------------------------------------


def parse_log(text: str) -> tuple[dict, dict]:
    """(header, parity summary) from a log written by :func:`run`."""
    text = text.replace("\r\n", "\n")
    first, rest = text.split("\n", 1)
    if first != "experience_memory parity log" or f"\n{SEPARATOR}\n" not in "\n" + rest:
        raise ValueError("not a parity log")
    head, output = ("\n" + rest).split(f"\n{SEPARATOR}\n", 1)
    header = json.loads(head)
    end = output.find("\n}\n")
    if end < 0:
        raise ValueError("not a parity log: no parity summary")
    summary = json.loads(output[: end + 2])
    if not output.rstrip("\n").endswith("PASS: 0 mismatches"):
        raise ValueError("the parity output does not end with PASS")
    return header, summary


def build_cert(log_text: str) -> dict:
    header, s = parse_log(log_text)
    if s.get("mismatch_count") != 0 or s.get("mode") != "private" or s.get("inputs_match_v5b_pins") is not True:
        raise ValueError("the log does not record a passing private parity run on the pinned inputs")
    return {
        "schema": "aamr-parity-certificate/1",
        "component": header["component"],
        "program": header["program"],
        "instrument": {"pins": sorted(header["instrument_files"].values()),
                       "files": header["instrument_files"],
                       "units_sha256": header["units_sha256"],
                       "runner_pins": header["runner_pins"]},
        "unit_set": {"n": s["queries"], "seeds": s["seeds"], "bank_items": s["bank_items"],
                     "units_with_exclusions": s["units_with_exclusions"]},
        "test": {"comparisons": s["comparisons"], "mismatches": s["mismatch_count"], "command": header["command"],
                 "parity_script_sha256": header["parity_script_sha256"],
                 "compared": "chosen items, memory block bytes, placebo block bytes (whitespace token counter on "
                             "both sides), top1/memory similarity, no exclusion",
                 "log": LOG, "log_sha256": lf_sha256(log_text)},
    }


def render(cert: dict) -> str:
    return json.dumps(cert, indent=1, ensure_ascii=False) + "\n"


def build() -> int:
    text = (REPO / LOG).read_text(encoding="utf-8")
    (REPO / CERT).write_text(render(build_cert(text)), encoding="utf-8", newline="\n")
    print(f"wrote {CERT}")
    return 0


def check() -> int:
    text = (REPO / LOG).read_text(encoding="utf-8")
    want = render(build_cert(text))
    have = (REPO / CERT).read_text(encoding="utf-8").replace("\r\n", "\n")
    if have != want:
        print(f"FAIL: {CERT} differs from the certificate recomputed from {LOG}")
        return 1
    print("PASS: the certificate equals the one recomputed from the log")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=("run", "build", "check"))
    ap.add_argument("--v5b-dir", type=Path, default=None, help="the private V5B folder (run only)")
    a = ap.parse_args(argv)
    if a.step == "run":
        return run(a.v5b_dir or parity.default_private_dir())
    return build() if a.step == "build" else check()


if __name__ == "__main__":
    sys.exit(main())
