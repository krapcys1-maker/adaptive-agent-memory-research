"""The verify alias must inspect the selected log, without initializing a store."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.project_memory import cli
from tools.project_memory.memory_store import MemoryStore

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("fmt", ["text", "json"])
@pytest.mark.parametrize("broken", [False, True])
def test_selected_root_matches_the_shared_script_and_preserves_bytes(tmp_path, capsys, fmt, broken):
    store = MemoryStore(tmp_path)
    store.add(kind="finding", title="Synthetic fact", summary="Synthetic evidence.", source_refs=["test"], confidence="high")
    path = tmp_path / "memory/events.jsonl"
    if broken:
        with path.open("ab") as handle:
            handle.write(path.read_bytes().splitlines()[0] + b"\n")  # Duplicate id.
    before = path.read_bytes()
    expected = subprocess.run([sys.executable, str(ROOT / "scripts/verify_memory_integrity.py"),
                               "--events", str(path), "--format", fmt], capture_output=True, text=True, encoding="utf-8")
    actual = cli.main(["--root", str(tmp_path), "verify", "--format", fmt])
    output = capsys.readouterr()
    assert actual == expected.returncode == int(broken)
    assert output.out == expected.stdout and output.err == expected.stderr
    if fmt == "json":
        report = json.loads(output.out)
        assert bool(report["summary"]["violations"]) == broken
    assert path.read_bytes() == before


def test_missing_log_is_an_error_and_never_creates_a_store(tmp_path, capsys):
    assert cli.main(["--root", str(tmp_path), "verify"]) == 1
    assert "not found" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_default_root_and_direct_script_report_the_same_canonical_log():
    alias = subprocess.run([sys.executable, str(ROOT / "tools/project_memory/cli.py"), "verify", "--format", "json"],
                           cwd=ROOT.parent, capture_output=True, text=True, encoding="utf-8")
    direct = subprocess.run([sys.executable, str(ROOT / "scripts/verify_memory_integrity.py"), "--format", "json"],
                            capture_output=True, text=True, encoding="utf-8")
    assert alias.returncode == direct.returncode == 0
    assert json.loads(alias.stdout) == json.loads(direct.stdout)


def test_another_roots_python_code_is_never_imported(tmp_path):
    foreign = tmp_path / "scripts"
    foreign.mkdir()
    (foreign / "verify_memory_integrity.py").write_text("raise AssertionError('foreign code executed')", encoding="utf-8")
    assert cli.main(["--root", str(tmp_path), "verify"]) == 1
