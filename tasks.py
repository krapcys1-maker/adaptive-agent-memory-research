#!/usr/bin/env python3
"""One entry point for every gate this project enforces.

    python tasks.py check     everything a pull request must pass
    python tasks.py fast      the sub-second subset, for a git hook
    python tasks.py test      the test suite alone
    python tasks.py audit     the two audits alone
    python tasks.py --list    show the targets and what they run

Why a Python script and not a Makefile
--------------------------------------
`make` is not present on a default Windows install, and this project is
developed on Windows and tested on Linux (CONTRIBUTING.md is explicit that a
setup which only works for the maintainer is a defect). A Makefile would work
for whoever wrote it and silently exclude everyone else, so the entry point is
written in the one interpreter every contributor is guaranteed to have --
they cannot run any gate without it.

It uses only the standard library, so `python tasks.py check` works on a fresh
clone before `requirements-dev.txt` is installed; it will simply fail on the
first gate with a real error rather than an ImportError about the runner.

Portability is not incidental here: subprocesses are launched with
`sys.executable` rather than the string "python" (on Windows "python" may be
the Microsoft Store alias stub, and inside a virtualenv it may not be the
interpreter running this file), and with an argument list rather than
`shell=True`, so nothing depends on a POSIX shell.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


class Gate:
    """One command, with the name CI knows it by."""

    def __init__(self, name: str, args: list[str], why: str, seconds: float) -> None:
        self.name = name
        self.args = args
        self.why = why
        self.seconds = seconds

    @property
    def display(self) -> str:
        return "python " + " ".join(self.args)


# Order matters: this is the order the jobs appear in .github/workflows/ci.yml,
# so a failure here is the failure CI would report first.
TESTS = Gate(
    "tests",
    ["-m", "pytest", "-q"],
    "the test suite (CI job: Tests)",
    12.0,
)
MEMORY_INTEGRITY = Gate(
    "memory-integrity",
    ["scripts/verify_memory_integrity.py", "--format", "text"],
    "invariants of the append-only memory log (CI job: Project-memory integrity)",
    0.2,
)
CLAIM_AUDIT = Gate(
    "claim-audit",
    ["scripts/audit_repository_claims.py", "--format", "text"],
    "declared hashes, registry paths, cross-references (CI job: Repository claim audit)",
    13.6,
)
# Not a CI job. It reports on the source pipeline rather than gating on it, so
# it is deliberately absent from `check`: adding it there would mean claiming
# CI enforces something it does not.
SOURCE_PIPELINE = Gate(
    "source-pipeline",
    ["scripts/audit_source_pipeline.py"],
    "discovered / cited / read source counts (reporting only, not a CI gate)",
    0.2,
)

TARGETS: dict[str, tuple[str, list[Gate]]] = {
    "check": (
        "every gate CI runs, in CI's order",
        [TESTS, MEMORY_INTEGRITY, CLAIM_AUDIT],
    ),
    "test": ("the test suite alone", [TESTS]),
    "audit": ("both audits, without the test suite", [CLAIM_AUDIT, SOURCE_PIPELINE]),
    "fast": (
        "the subset that finishes in well under five seconds",
        [MEMORY_INTEGRITY, SOURCE_PIPELINE],
    ),
}


def run_gate(gate: Gate, index: int, total: int) -> tuple[bool, float]:
    # Printed before the command runs, so an interrupted or hanging gate is
    # still attributable to a name.
    print(f"\n[{index}/{total}] {gate.name}: {gate.why}", flush=True)
    print(f"      $ {gate.display}", flush=True)

    started = time.monotonic()
    completed = subprocess.run([sys.executable, *gate.args], cwd=REPO_ROOT)
    elapsed = time.monotonic() - started

    status = "ok" if completed.returncode == 0 else f"FAILED (exit {completed.returncode})"
    print(f"      {gate.name}: {status} in {elapsed:.1f}s", flush=True)
    return completed.returncode == 0, elapsed


def run_target(name: str) -> int:
    description, gates = TARGETS[name]

    print(f"tasks.py {name} - {description}")
    print(f"  {len(gates)} gate(s), roughly {sum(g.seconds for g in gates):.0f}s total")

    failed: list[str] = []
    total_elapsed = 0.0
    for index, gate in enumerate(gates, start=1):
        ok, elapsed = run_gate(gate, index, len(gates))
        total_elapsed += elapsed
        if not ok:
            failed.append(gate.name)
            # Keep going. Stopping at the first failure hides the others, and
            # the whole point is to answer "did I break anything?" in one run.

    print()
    if failed:
        # Non-zero exit, so this is usable as a git hook.
        print(f"tasks.py {name}: FAILED in {total_elapsed:.1f}s - {', '.join(failed)}")
        return 1

    print(f"tasks.py {name}: all {len(gates)} gate(s) passed in {total_elapsed:.1f}s")
    return 0


def print_targets() -> None:
    print("targets:\n")
    for name, (description, gates) in TARGETS.items():
        print(f"  {name:<7} {description}")
        print(f"  {'':<7} ~{sum(g.seconds for g in gates):.0f}s")
        for gate in gates:
            print(f"  {'':<7}   {gate.display}")
        print()
    print("Timings are from one Windows laptop and are there to tell the fast")
    print("path from the slow one, not to be a benchmark.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", nargs="?", default="check", choices=sorted(TARGETS))
    parser.add_argument(
        "--list",
        action="store_true",
        help="show the targets and the commands they run, then exit",
    )
    args = parser.parse_args(argv)

    if args.list:
        print_targets()
        return 0
    return run_target(args.target)


if __name__ == "__main__":
    raise SystemExit(main())
