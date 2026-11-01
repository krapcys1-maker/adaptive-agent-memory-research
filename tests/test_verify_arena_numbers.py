"""verify_arena_numbers.py recomputes the ledger's Entry H numbers from tracked files.

The tests run the script against the real tracked result files, and against a
tampered copy of the ledger to prove that a differing number is not waved through.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "arena" / "verify_arena_numbers.py"
LEDGER = Path("docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md")
NEEDED = [
    LEDGER,
    Path("data/lab/arena/raw-provenance-fresh-replication-v1/results.json"),
    Path("data/lab/arena/base-plus-x-v2/e3-arms.json"),
    Path("data/lab/arena/base-plus-x-v2/e3-judged.json"),
    Path("data/lab/arena/base-plus-x-v2/e3-analysis.json"),
    Path("data/lab/arena/mem0-breadth-arms.json"),
    Path("data/lab/arena/mem0-breadth-judged.json"),
]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")


def copy_inputs(dest: Path) -> None:
    for rel in NEEDED:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)


def test_real_tracked_files_pass() -> None:
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    assert "recomputed 5/8, 6/8, 4/8" in out
    assert "recomputed 5/9, 6/9, 4/9" in out
    assert "recomputed 17" in out
    assert "FAIL" not in out
    assert "0e5e2d1a" in out and "6a27ffc2" in out


def test_prints_token_counts_for_both_arms_per_unit() -> None:
    out = run().stdout
    line = [row for row in out.splitlines() if row.strip().startswith("0e5e2d1a") and "single-session-assistant" in row]
    assert line, out
    assert "109" in line[0] and "609" in line[0]
    assert "mean of per-unit ratios 21.36x" in out


def test_help_exits_zero() -> None:
    result = run("--help")
    assert result.returncode == 0
    assert "--repo" in result.stdout


def test_differing_ledger_number_exits_one(tmp_path: Path) -> None:
    copy_inputs(tmp_path)
    ledger = tmp_path / LEDGER
    text = ledger.read_text(encoding="utf-8")
    assert "compact 5/8, compact+raw **6/8**" in text
    ledger.write_text(text.replace("compact 5/8, compact+raw **6/8**", "compact 4/8, compact+raw **6/8**"), encoding="utf-8")
    result = run("--repo", str(tmp_path))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL" in result.stdout


def test_missing_input_exits_two(tmp_path: Path) -> None:
    copy_inputs(tmp_path)
    (tmp_path / "data/lab/arena/base-plus-x-v2/e3-arms.json").unlink()
    result = run("--repo", str(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr


def test_not_a_checkout_exits_two(tmp_path: Path) -> None:
    assert run("--repo", str(tmp_path)).returncode == 2
