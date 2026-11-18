"""verify_autolab_packages.py recomputes the published numbers of the autolab packages from the packages alone.

The tests run the verifier against the real V3 and V4 packages, and against copies in tmp in which exactly one thing
is altered: a solved cell, a removed row, a duplicated row, a swapped arm label, a declared number in the README or
in knowledge.jsonl. Every alteration must change the exit status and name the field that caught it, so that a check
which stops checking is noticed by a failing test. The real package folders are only read, never written.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, List

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_autolab_packages.py"
V3 = ROOT / "data" / "lab" / "autolab-alfworld-ladder-r4-v3"
V4 = ROOT / "data" / "lab" / "autolab-alfworld-ladder-r4-v4"
V3_RESULT = "cycle 1 result:e9d6bf59f88b0c4b"
V4_RESULT = "cycle 1 result:ccc9c8b402d50ac0"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")


def failed(out: str) -> List[str]:
    return [line[len("FAIL  "):] for line in out.splitlines() if line.startswith("FAIL  ")]


def assert_fails_on(result: subprocess.CompletedProcess, *fields: str) -> None:
    assert result.returncode == 1, result.stdout[-3000:] + result.stderr
    fails = failed(result.stdout)
    for field in fields:
        assert any(f.startswith(field) for f in fails), "no FAIL line starts with %r; FAIL lines:\n%s" % (field, "\n".join(fails))
    assert "MISMATCHES in " in result.stdout


def copy_package(src: Path, tmp_path: Path) -> Path:
    dest = tmp_path / src.name
    shutil.copytree(src, dest)
    return dest


def edit_text(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, "the text to alter is not in " + str(path)  # an alteration that changes nothing proves nothing
    path.write_bytes(text.replace(old, new, 1).encode("utf-8"))


def read_rows(package: Path) -> tuple[list[str], list[dict]]:
    reader = csv.DictReader(io.StringIO((package / "per_unit.csv").read_text(encoding="utf-8")))
    return list(reader.fieldnames or []), list(reader)


def write_rows(package: Path, columns: list[str], rows: list[dict]) -> None:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    (package / "per_unit.csv").write_bytes(out.getvalue().encode("utf-8"))


def edit_object(package: Path, object_id: str, change: Callable[[dict], None]) -> None:
    path = package / "knowledge.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        obj = json.loads(line)
        if obj["id"] == object_id:
            change(obj["payload"])
            lines[i] = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
            path.write_bytes("".join(lines).encode("utf-8"))
            return
    raise AssertionError("no object " + object_id)


# --------------------------------------------------------------------------- the real packages
def test_real_packages_pass() -> None:
    result = run()
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr
    out = result.stdout
    assert not failed(out)
    assert "== autolab-alfworld-ladder-r4-v3 ==" in out and "== autolab-alfworld-ladder-r4-v4 ==" in out
    assert "all 2 package(s) verified" in out


@pytest.mark.parametrize("package", [V3, V4], ids=["v3", "v4"])
def test_each_real_package_passes_alone(package: Path) -> None:
    result = run("--package", str(package))
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr
    assert "all 1 package(s) verified" in result.stdout


def test_recomputed_numbers_are_pinned() -> None:
    out = run().stdout
    # V4: solved counts, the primary contrast and the pre-registered format criterion
    assert "success_rate[retrieved_task] = 0.686667  | recomputed 206 solved / 300 = 0.686667" in out
    assert "success_rate[placebo] = 0.446667  | recomputed 134 solved / 300 = 0.446667" in out
    assert "primary.retrieved_task (retrieved_task - placebo) gains = 91  | recomputed 91" in out
    assert "primary.retrieved_task (retrieved_task - placebo) ci = [0.177091, 0.302909] (paired Wald)  | recomputed [0.177091, 0.302909]" in out
    assert "secondary.placebo-none (placebo - none) state = equivalent" in out
    assert "process_balance.per_arm[retrieved_task][invalid_no_action_tag].diff = 0.0337 (arm - placebo, step-weighted)  | recomputed 0.0337" in out
    assert "process_balance.per_arm[retrieved_task][invalid_no_action_tag].imbalanced = True" in out
    assert "README Status: retrieved_task = measurement_problem" in out
    # V3: the primary contrast is inconclusive at SESOI 0.18, the post-hoc untagged criterion fails
    assert "primary.retrieved_task (retrieved_task - placebo) ci = [-0.041752, 0.181752] (paired Wald)  | recomputed [-0.041752, 0.181752]" in out
    assert "rule gives inconclusive at SESOI 0.18" in out
    assert "README Caveats: criterion FAILED  | recomputed: fails" in out


def test_unverifiable_fields_are_listed_not_passed() -> None:
    out = run().stdout
    nv = [line for line in out.splitlines() if line.startswith("N/V   ")]
    def has(text: str) -> bool:
        return any(text in line for line in nv)
    assert has("README Measurement checks: min_tokens per step [retrieved_task] = 0.307") and has("min_tokens is not a column of per_unit.csv")
    assert has("[invalid_no_action_tag].ci (exact digits)")                  # bootstrap seed not published
    assert has("Early check after the first chunk")                          # chunk membership not in the table
    assert has("PUBLISHED_FILES.json: per_unit.csv")                        # V3 table added after the export manifest
    assert has("leakage.ok") and has("raw_integrity.ok") and has("(power, alpha, false close)")
    assert "WARN  cycle 1 finding:e7402eac3345ea88 (H3)" in out             # verdict rule and expected_state disagree


# --------------------------------------------------------------------------- one alteration each
@pytest.mark.parametrize("source,result_id", [(V3, V3_RESULT), (V4, V4_RESULT)], ids=["v3", "v4"])
def test_changed_solved_cell_fails(tmp_path: Path, source: Path, result_id: str) -> None:
    package = copy_package(source, tmp_path)
    columns, rows = read_rows(package)
    row = next(r for r in rows if r["arm"] == "retrieved_task" and r["solved"] == "1")
    row["solved"] = "0"
    write_rows(package, columns, rows)
    result = run("--package", str(package))
    # V3's per_unit.csv is not in its export manifest, so only the recomputation can catch this there
    assert_fails_on(result, result_id + ": success_rate[retrieved_task]", result_id + ": primary.retrieved_task (retrieved_task - placebo) diff",
                    "README Results cycle 1: solved[retrieved_task]")


def test_removed_row_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    columns, rows = read_rows(package)
    gone = next(i for i, r in enumerate(rows) if r["arm"] == "placebo")
    del rows[gone]
    write_rows(package, columns, rows)
    result = run("--package", str(package))
    assert_fails_on(result, "cycle 1: complete unit x arm x seed grid (completeness)", "cycle 1: rows = run.records 900",
                    V4_RESULT + ": primary.retrieved_task (retrieved_task - placebo) n = 300",
                    "cycle 1 audit:ff4e4912acd1a5e9: completeness records 900 of expected 900")


def test_duplicated_row_fails(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    columns, rows = read_rows(package)
    rows.insert(5, dict(rows[4]))
    write_rows(package, columns, rows)
    result = run("--package", str(package))
    assert_fails_on(result, "per_unit.csv: one row per (cycle, unit, arm, seed)", "cycle 1: rows = run.records 300")


@pytest.mark.parametrize("source,result_id", [(V3, V3_RESULT), (V4, V4_RESULT)], ids=["v3", "v4"])
def test_swapped_arm_label_fails(tmp_path: Path, source: Path, result_id: str) -> None:
    package = copy_package(source, tmp_path)
    columns, rows = read_rows(package)
    by_unit: dict = {}
    for r in rows:
        by_unit.setdefault(r["unit"], {})[r["arm"]] = r
    unit = next(u for u, arms in by_unit.items() if arms["retrieved_task"]["solved"] != arms["placebo"]["solved"])
    by_unit[unit]["retrieved_task"]["arm"], by_unit[unit]["placebo"]["arm"] = "placebo", "retrieved_task"
    write_rows(package, columns, rows)
    result = run("--package", str(package))
    # the grid is still complete, so only the numbers can show the swap
    assert "PASS  cycle 1: complete unit x arm x seed grid (completeness)" in result.stdout
    assert_fails_on(result, result_id + ": success_rate[placebo]", result_id + ": success_rate[retrieved_task]",
                    result_id + ": primary.retrieved_task (retrieved_task - placebo) gains")


def test_changed_number_in_readme_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", "| placebo | 0.45 |", "| placebo | 0.46 |")
    result = run("--package", str(package))
    assert_fails_on(result, "README Results cycle 1: solved[placebo] = 0.46", "PUBLISHED_FILES.json: sha256 and size of README.md")


def test_changed_gains_in_readme_fails(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    edit_text(package / "README.md", "| 20 / 13 |", "| 21 / 13 |")
    result = run("--package", str(package))
    assert_fails_on(result, "README Results cycle 1: retrieved_task")
    assert any("gains / losses 21 / 13" in f for f in failed(result.stdout))


def test_changed_format_criterion_in_readme_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", "+0.034 [+0.014, +0.053]", "+0.044 [+0.014, +0.053]")
    result = run("--package", str(package))
    assert any("invalid_no_action_tag +0.044 (step-weighted arm - placebo)" in f for f in failed(result.stdout)), result.stdout[-3000:]
    assert result.returncode == 1


def test_changed_number_in_knowledge_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_object(package, "result:ccc9c8b402d50ac0", lambda p: p["primary"]["retrieved_task"].update(gains=92))
    result = run("--package", str(package))
    assert_fails_on(result, V4_RESULT + ": primary.retrieved_task (retrieved_task - placebo) gains = 92",
                    "knowledge.jsonl: object hashes and parent order")


def test_bootstrap_interval_far_from_the_data_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)

    def change(p: dict) -> None:
        p["checks"]["measurement_sensitivity"]["process_balance"]["per_arm"]["retrieved_task"]["invalid_no_action_tag"]["ci"] = [0.03, 0.07]
    edit_object(package, "audit:ff4e4912acd1a5e9", change)
    result = run("--package", str(package))
    assert_fails_on(result, "cycle 1 audit:ff4e4912acd1a5e9 (code): process_balance.per_arm[retrieved_task][invalid_no_action_tag].ci = [0.03, 0.07], approximately")


def test_changed_state_label_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_object(package, "result:ccc9c8b402d50ac0", lambda p: p["secondary"]["placebo-none"].update(state="negative"))
    result = run("--package", str(package))
    assert_fails_on(result, V4_RESULT + ": secondary.placebo-none (placebo - none) state = negative")


# --------------------------------------------------------------------------- input errors and unknown fields
def test_missing_table_is_an_input_error(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    (package / "per_unit.csv").unlink()
    result = run("--package", str(package))
    assert result.returncode == 2
    assert "has no per_unit.csv" in result.stderr


def test_unknown_column_is_reported_not_verifiable(tmp_path: Path) -> None:
    # V3's per_unit.csv is outside its export manifest, so a new column changes no pinned digest
    package = copy_package(V3, tmp_path)
    columns, rows = read_rows(package)
    for r in rows:
        r["top1_similarity"] = "0"
    write_rows(package, columns + ["top1_similarity"], rows)
    result = run("--package", str(package))
    assert result.returncode == 0, result.stdout[-3000:]
    assert "N/V   per_unit.csv column top1_similarity" in result.stdout


# --------------------------------------------------------------------------- the rules themselves
def load_module():
    spec = importlib.util.spec_from_file_location("verify_autolab_packages", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_state_rule() -> None:
    m = load_module()
    assert m.interval_states(0.177, 0.303, 0.12) == ["practical"]
    assert m.interval_states(0.04, 0.22, 0.18) == ["positive"]
    assert m.interval_states(-0.071, 0.024, 0.12) == ["equivalent"]
    assert m.interval_states(-0.042, 0.182, 0.18) == ["inconclusive"]
    assert m.interval_states(-0.30, -0.15, 0.12) == ["negative"]
    assert m.interval_states(0.01, 0.10, 0.12) == ["positive", "equivalent"]   # the package names this case twice


def test_rounding_tolerance() -> None:
    m = load_module()
    assert m.agrees(0.446667, "0.45") and not m.agrees(0.446667, "0.44")
    assert m.agrees(0.0337, "+0.034") and not m.agrees(0.0337, "+0.035")
    assert m.agrees(0.177091, 0.177091, 6) and not m.agrees(0.177091, 0.177093, 6)
    assert m.agrees(91, 91) and not m.agrees(91, 92)
    assert not m.agrees(0.5, None)
