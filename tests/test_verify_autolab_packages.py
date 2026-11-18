"""verify_autolab_packages.py recomputes the published numbers of the autolab packages from the packages alone.

The tests run the verifier against the real V3 and V4 packages, against two synthetic packages in tests/fixtures, and
against copies in tmp in which exactly one thing is altered: a solved cell, a removed or duplicated row, a swapped arm
label, a declared number in the README or in knowledge.jsonl, a removed caveat or section, extra prose. Every alteration
must change the exit status and name the field that caught it, so that a check which stops checking is noticed by a
failing test. The real package folders are only read, never written.

The fixtures were generated once from synthetic episode records with the laboratory's own analysis, audit, per-unit
export and README code (private, read-only), so they have the exact shape a new export has: sequential thresholds,
four arms, family size 2, the `imbalance_only` format rule, behaviour counters, a pre-registered counter outside the
V3/V4 set (`untagged_not_truncated`), float and empty cells (autolab-synthetic-v5b-shape); two seeds, a zero-variance
contrast and a disputed verdict (autolab-synthetic-two-seeds). They are not results and are never exported.
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
V5B = ROOT / "tests" / "fixtures" / "autolab-synthetic-v5b-shape"
TWO_SEEDS = ROOT / "tests" / "fixtures" / "autolab-synthetic-two-seeds"
V3_RESULT = "cycle 1 result:e9d6bf59f88b0c4b"
V4_RESULT = "cycle 1 result:ccc9c8b402d50ac0"
MINUS = "\u2212"
DASH = "\u2014"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")


def lines(out: str, prefix: str) -> List[str]:
    return [line[len(prefix):] for line in out.splitlines() if line.startswith(prefix)]


def assert_fails_on(result: subprocess.CompletedProcess, *fields: str) -> None:
    assert result.returncode == 1, result.stdout[-3000:] + result.stderr
    fails = lines(result.stdout, "FAIL  ")
    for field in fields:
        assert any(field in f for f in fails), "no FAIL line contains %r; FAIL lines:\n%s" % (field, "\n".join(fails))
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
    text = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, line in enumerate(text):
        obj = json.loads(line)
        if obj["id"] == object_id:
            change(obj["payload"])
            text[i] = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
            path.write_bytes("".join(text).encode("utf-8"))
            return
    raise AssertionError("no object " + object_id)


# --------------------------------------------------------------------------- the real packages and the fixtures
def test_real_packages_pass() -> None:
    result = run()
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr
    out = result.stdout
    assert not lines(out, "FAIL  ")
    assert "== autolab-alfworld-ladder-r4-v3 ==" in out and "== autolab-alfworld-ladder-r4-v4 ==" in out
    assert out.count("N/V baseline: no new not-verifiable field") == 2
    assert "all 2 package(s) verified" in out


@pytest.mark.parametrize("package", [V3, V4, V5B, TWO_SEEDS], ids=["v3", "v4", "v5b-shape", "two-seeds"])
def test_each_package_passes_alone(package: Path) -> None:
    result = run("--package", str(package))
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr
    assert "all 1 package(s) verified" in result.stdout
    assert "N/V baseline: no new not-verifiable field" in result.stdout


def test_recomputed_numbers_are_pinned() -> None:
    out = run().stdout
    assert "success_rate[retrieved_task] = 0.686667  | recomputed 206 solved / 300 = 0.686667" in out
    assert "primary.retrieved_task (retrieved_task - placebo) ci = [0.177091, 0.302909] (paired Wald)  | recomputed [0.177091, 0.302909]" in out
    assert "secondary.placebo-none (placebo - none) state = equivalent" in out
    # the lab's bootstrap reproduces to the last stored digit with its default seed and replicate count
    assert "process_balance.per_arm[retrieved_task][invalid_no_action_tag].ci = [0.014, 0.0527]  | recomputed [0.0140, 0.0527] (lab default bootstrap" in out
    assert "process_balance.per_arm[retrieved_task][empty_retries].ci = [0.4586, 0.7251]  | recomputed [0.4586, 0.7251]" in out
    assert "process_balance.per_arm[retrieved_task][invalid_no_action_tag].imbalanced = True" in out
    assert "noise_vs_calibration.observed_lower_bound = 0.312137" in out
    assert "README Status: retrieved_task = measurement_problem" in out
    assert "primary.retrieved_task (retrieved_task - placebo) ci = [-0.041752, 0.181752] (paired Wald)  | recomputed [-0.041752, 0.181752]" in out
    assert "README Caveats: untagged criterion FAILED  | recomputed: fails" in out


def test_unverifiable_fields_are_listed_not_passed() -> None:
    out = run().stdout
    nv = lines(out, "N/V   ")

    def has(text: str) -> bool:
        return any(text in line for line in nv)
    assert has("process counter min_tokens") and has("min_tokens is not a column of per_unit.csv")
    assert has("Early check after the first chunk")
    assert has("PUBLISHED_FILES.json: per_unit.csv")                        # V3 table added after the export manifest
    assert has("checks.leakage") and has("checks.raw_integrity") and has("(power, alpha, false close)")
    assert "WARN  cycle 1 finding:e7402eac3345ea88 (H3)" in out
    assert "the lab's verdict rule reads only the predicted direction" in out


def test_v5b_shaped_fixture_is_verified() -> None:
    out = run("--package", str(V5B)).stdout
    assert "z = 2.2736 (sequential threshold of the final analysis)  | pre-registered 2.2736" in out
    assert "family_size = 2" in out
    assert "[mismatched_type][untagged_not_truncated].state = imbalanced" in out
    assert "[mismatched_type][untagged_not_truncated].rule = imbalance_only" in out
    assert "README Process criteria mismatched_type / untagged_not_truncated: difference +0.101" in out
    assert "report.arms[mismatched_type].status = measurement_problem" in out
    assert "N/V   per_unit.csv column top1_similarity" in out                # float and empty cells: no table error
    assert "PASS  per_unit.csv: cycle and seed are integers" in out


def test_two_seed_fixture_is_verified() -> None:
    out = run("--package", str(TWO_SEEDS)).stdout
    assert "N/V   cycle 1 run:" in out and "rows of seeds [1]" in out
    assert "seed = 0 (first protocol seed)" in out
    assert "secondary.placebo-none (placebo - none) ci = [-0.0245, 0.0245] (paired Wald)" in out   # se = 1/n at zero variance
    assert "verdict = disputed" in out


# --------------------------------------------------------------------------- one alteration each
@pytest.mark.parametrize("source,result_id", [(V3, V3_RESULT), (V4, V4_RESULT)], ids=["v3", "v4"])
def test_changed_solved_cell_fails(tmp_path: Path, source: Path, result_id: str) -> None:
    package = copy_package(source, tmp_path)
    columns, rows = read_rows(package)
    row = next(r for r in rows if r["arm"] == "retrieved_task" and r["solved"] == "1")
    row["solved"] = "0"
    write_rows(package, columns, rows)
    # V3's per_unit.csv is not in its export manifest, so only the recomputation can catch this there
    assert_fails_on(run("--package", str(package)), result_id + ": success_rate[retrieved_task]",
                    result_id + ": primary.retrieved_task (retrieved_task - placebo) diff", "README Results cycle 1: solved[retrieved_task]")


def test_removed_row_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    columns, rows = read_rows(package)
    del rows[next(i for i, r in enumerate(rows) if r["arm"] == "placebo")]
    write_rows(package, columns, rows)
    assert_fails_on(run("--package", str(package)), "complete unit x arm x seed grid (completeness)", "rows = run.records 900",
                    V4_RESULT + ": primary.retrieved_task (retrieved_task - placebo) n = 300", "completeness records 900 of expected 900")


def test_duplicated_row_fails(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    columns, rows = read_rows(package)
    rows.insert(5, dict(rows[4]))
    write_rows(package, columns, rows)
    assert_fails_on(run("--package", str(package)), "per_unit.csv: one row per (cycle, unit, arm, seed)", "rows = run.records 300")


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
    assert any("complete unit x arm x seed grid" in line for line in lines(result.stdout, "PASS  "))   # only the numbers show the swap
    assert_fails_on(result, result_id + ": success_rate[placebo]", result_id + ": success_rate[retrieved_task]",
                    result_id + ": primary.retrieved_task (retrieved_task - placebo) gains")


def test_changed_number_in_readme_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", "| placebo | 0.45 |", "| placebo | 0.46 |")
    assert_fails_on(run("--package", str(package)), "README Results cycle 1: solved[placebo] = 0.46", "PUBLISHED_FILES.json: sha256 and size of README.md")


def test_changed_gains_in_readme_fails(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    edit_text(package / "README.md", "| 20 / 13 |", "| 21 / 13 |")
    assert_fails_on(run("--package", str(package)), "gains / losses 21 / 13")


def test_changed_format_criterion_in_readme_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", "+0.034 [+0.014, +0.053]", "+0.044 [+0.014, +0.053]")
    assert_fails_on(run("--package", str(package)), "README Caveats: measurement problem", "N/V baseline: README text")


def test_removed_caveat_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", "- The measurement was interrupted by an infrastructure failure", "The measurement was interrupted by an infrastructure failure")
    assert_fails_on(run("--package", str(package)), "README Caveats: 'The measurement was interrupted")


@pytest.mark.parametrize("heading,field", [("## Status of each direction", "README: section 'Status of each direction' present"),
                                           ("## Caveats", "README: section 'Caveats' present"),
                                           ("## Decisions", "README: section 'Decisions' present")], ids=["status", "caveats", "decisions"])
def test_removed_section_fails(tmp_path: Path, heading: str, field: str) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", heading + "\n", "")
    assert_fails_on(run("--package", str(package)), field)


def test_changed_status_line_fails(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    edit_text(package / "README.md", "**Status:** completed", "**Status:** running")
    assert_fails_on(run("--package", str(package)), "README: status running")


def test_changed_direction_status_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", "- retrieved_task: measurement_problem " + DASH + " measurement problem, so neither established nor closed",
              "- retrieved_task: established")
    assert_fails_on(run("--package", str(package)), "README Status: retrieved_task = measurement_problem")


def test_added_prose_fails_the_baseline(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", "## Decisions\n", "## Decisions\n\nThe memory arm is clearly better on every task type.\n")
    assert_fails_on(run("--package", str(package)), "N/V baseline: README text 'The memory arm is clearly better")


def test_changed_number_in_knowledge_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_object(package, "result:ccc9c8b402d50ac0", lambda p: p["primary"]["retrieved_task"].update(gains=92))
    assert_fails_on(run("--package", str(package)), V4_RESULT + ": primary.retrieved_task (retrieved_task - placebo) gains = 92",
                    "knowledge.jsonl: object hashes and parent order")


def test_bootstrap_interval_off_by_one_digit_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)

    def change(p: dict) -> None:
        p["checks"]["measurement_sensitivity"]["process_balance"]["per_arm"]["retrieved_task"]["invalid_no_action_tag"]["ci"] = [0.0141, 0.0527]
    edit_object(package, "audit:ff4e4912acd1a5e9", change)
    result = run("--package", str(package))
    assert any("[invalid_no_action_tag].ci (exact digits)" in f for f in lines(result.stdout, "N/V   "))
    assert_fails_on(result, "N/V baseline: cycle 1 audit:ff4e4912acd1a5e9 (code): process_balance.per_arm[retrieved_task][invalid_no_action_tag].ci (exact digits)")


def test_bootstrap_interval_far_from_the_data_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)

    def change(p: dict) -> None:
        p["checks"]["measurement_sensitivity"]["process_balance"]["per_arm"]["retrieved_task"]["invalid_no_action_tag"]["ci"] = [0.03, 0.07]
    edit_object(package, "audit:ff4e4912acd1a5e9", change)
    assert_fails_on(run("--package", str(package)), "process_balance.per_arm[retrieved_task][invalid_no_action_tag].ci = [0.03, 0.07]")


def test_changed_state_label_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_object(package, "result:ccc9c8b402d50ac0", lambda p: p["secondary"]["placebo-none"].update(state="negative"))
    assert_fails_on(run("--package", str(package)), V4_RESULT + ": secondary.placebo-none (placebo - none) state = negative")


def test_removed_measurement_problem_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_object(package, "finding:00fa0192dfd13db2", lambda p: p.pop("measurement_problem"))
    assert_fails_on(run("--package", str(package)), "finding:00fa0192dfd13db2 (H1): measurement_problem = the code audit's problems")


def test_memory_tokens_zero_in_the_memory_arm_fails(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    columns, rows = read_rows(package)
    for r in rows:
        if r["arm"] == "retrieved_task":
            r["memory_tokens"] = "0"
    write_rows(package, columns, rows)
    assert_fails_on(run("--package", str(package)), "per_arm[retrieved_task].problems: recomputable problems")


def test_new_criterion_counter_is_recomputed(tmp_path: Path) -> None:
    package = copy_package(V5B, tmp_path)
    columns, rows = read_rows(package)
    for r in rows:
        if r["arm"] == "mismatched_type":
            r["untagged_not_truncated"] = "0"
    write_rows(package, columns, rows)
    assert_fails_on(run("--package", str(package)), "process_balance.per_arm[mismatched_type][untagged_not_truncated].diff",
                    "process_balance.per_arm[mismatched_type][untagged_not_truncated].ci = ",
                    "README Process criteria mismatched_type / untagged_not_truncated: difference")


def test_relabelled_cycle_is_reported_not_a_crash(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    columns, rows = read_rows(package)
    for r in rows:
        r["cycle"] = "2"
    write_rows(package, columns, rows)
    result = run("--package", str(package))
    assert_fails_on(result, "per_unit.csv: cycle 2 has a run object", "every unit of the run has rows")
    assert "Traceback" not in result.stdout + result.stderr


# --------------------------------------------------------------------------- input errors, unknown fields, baseline
@pytest.mark.parametrize("name", ["per_unit.csv", "PUBLISHED_FILES.json", "PROVENANCE.json"])
def test_missing_required_file_is_an_input_error(tmp_path: Path, name: str) -> None:
    package = copy_package(V3, tmp_path)
    (package / name).unlink()
    result = run("--package", str(package))
    assert result.returncode == 2
    assert "has no %s" % name in result.stderr


def test_malformed_knowledge_is_an_input_error(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    with open(package / "knowledge.jsonl", "a", encoding="utf-8") as fh:
        fh.write("{not json\n")
    result = run("--package", str(package))
    assert result.returncode == 2
    assert "is not JSON" in result.stderr


def test_unknown_column_with_realistic_cells(tmp_path: Path) -> None:
    # exporter-shaped: floats, a 1.0, and empty cells for arms without the metric
    package = copy_package(V3, tmp_path)
    columns, rows = read_rows(package)
    for i, r in enumerate(rows):
        r["top1_similarity"] = "" if r["arm"] in ("none", "placebo") else ("1.0" if i % 7 == 0 else "0.%04d" % (i % 9999))
    write_rows(package, columns + ["top1_similarity"], rows)
    without = run("--package", str(package), "--baseline", str(tmp_path / "no-baseline.json"))
    assert without.returncode == 0, without.stdout[-3000:]
    assert "N/V   per_unit.csv column top1_similarity" in without.stdout
    assert "has no entry in no-baseline.json" in without.stdout
    assert_fails_on(run("--package", str(package)), "N/V baseline: per_unit.csv column top1_similarity")


def test_update_baseline_writes_only_the_given_file(tmp_path: Path) -> None:
    target = tmp_path / "baseline.json"
    result = run("--package", str(V4), "--baseline", str(target), "--update-baseline")
    assert result.returncode == 0, result.stdout[-2000:]
    data = json.loads(target.read_text(encoding="utf-8"))
    assert list(data["packages"]) == ["autolab-alfworld-ladder-r4-v4"]
    assert any("min_tokens" in f for f in data["packages"]["autolab-alfworld-ladder-r4-v4"])


# --------------------------------------------------------------------------- the lab rules themselves
def load_module():
    spec = importlib.util.spec_from_file_location("verify_autolab_packages", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_state_rule_in_the_lab_order() -> None:
    m = load_module()
    assert m.interval_state(0.177, 0.303, 0.12) == "practical"
    assert m.interval_state(0.04, 0.22, 0.18) == "positive"
    assert m.interval_state(-0.071, 0.024, 0.12) == "equivalent"
    assert m.interval_state(-0.042, 0.182, 0.18) == "inconclusive"
    assert m.interval_state(-0.30, -0.15, 0.12) == "negative"
    assert m.interval_state(0.01, 0.10, 0.12) == "positive"        # positive before equivalent, as Rule.label
    assert m.interval_state(-0.10, -0.01, 0.12) == "negative"      # negative before equivalent


def test_paired_interval_with_zero_variance_uses_one_over_n() -> None:
    m = load_module()
    lo, hi = m.paired_ci(0, 0, 80, 1.959964)
    assert abs(lo + 1.959964 / 80) < 1e-12 and abs(hi - 1.959964 / 80) < 1e-12
    lo, hi = m.paired_ci(10, 0, 10, 1.959964)
    assert abs(lo - (1 - 1.959964 / 10)) < 1e-12


def test_verdict_rule() -> None:
    m = load_module()
    assert m.lab_verdict("positive", "practical", True, False) == "supported"
    assert m.lab_verdict("null", "practical", True, False) == "refuted"
    assert m.lab_verdict("null", "equivalent", True, False) == "supported"
    assert m.lab_verdict("positive", "inconclusive", True, False) == "inconclusive"
    assert m.lab_verdict("positive", "practical", True, True) == "disputed"
    assert m.lab_verdict("positive", "practical", False, True) == "invalid"


def test_rounding_tolerance() -> None:
    m = load_module()
    assert m.agrees(0.446667, "0.45") and not m.agrees(0.446667, "0.44")
    assert m.agrees(0.0337, "+0.034") and not m.agrees(0.0337, "+0.035")
    assert m.agrees(m.r6(-1.959964 / 80), MINUS + "0.025")
    assert m.agrees(0.177091, 0.177091, 6) and not m.agrees(0.177091, 0.177093, 6)
    assert m.agrees(91, 91) and not m.agrees(91, 92)
    assert not m.agrees(0.5, None)
