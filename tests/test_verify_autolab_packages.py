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
import hashlib
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
EARLY1 = ROOT / "tests" / "fixtures" / "autolab-synthetic-early-stop-look1"
EARLY2 = ROOT / "tests" / "fixtures" / "autolab-synthetic-early-stop-look2"
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
    # every published package, however many the laboratory has exported by now (a fixed count failed the CI of
    # each new export pull request: V5B, 2026-11-19)
    n = len(sorted(p for p in (ROOT / "data" / "lab").glob("autolab-*") if p.is_dir()))
    assert n >= 2
    assert out.count("N/V baseline: the N/V fields equal the baseline entry") == n
    assert "all %d package(s) verified" % n in out


@pytest.mark.parametrize("package", [V3, V4, V5B, TWO_SEEDS, EARLY1, EARLY2], ids=["v3", "v4", "v5b-shape", "two-seeds", "early-look1", "early-look2"])
def test_each_package_passes_alone(package: Path) -> None:
    result = run("--package", str(package))
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr
    assert "all 1 package(s) verified" in result.stdout
    assert "N/V baseline: the N/V fields equal the baseline entry" in result.stdout


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
    assert has("checks.leakage") and has("checks.raw_integrity") and has("power_at_sesoi")
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
    assert_fails_on(run("--package", str(package)), "complete unit x arm x seed grid (completeness)", "= run.records 900",
                    V4_RESULT + ": primary.retrieved_task (retrieved_task - placebo) n = 300", "completeness records 900 of expected 900")


def test_duplicated_row_fails(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)
    columns, rows = read_rows(package)
    rows.insert(5, dict(rows[4]))
    write_rows(package, columns, rows)
    assert_fails_on(run("--package", str(package)), "per_unit.csv: one row per (cycle, unit, arm, seed)", "= run.records 300")


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
    result = run("--package", str(package))
    assert "N/V   per_unit.csv column top1_similarity" in result.stdout            # reported, no table error
    assert "PASS  per_unit.csv: cycle and seed are integers" in result.stdout
    assert_fails_on(result, "N/V baseline: per_unit.csv column top1_similarity")   # and the new N/V field must be reviewed


def test_update_baseline_writes_only_the_given_file(tmp_path: Path) -> None:
    target = tmp_path / "baseline.json"
    result = run("--package", str(V4), "--baseline", str(target), "--update-baseline")
    assert result.returncode == 0, result.stdout[-2000:]
    data = json.loads(target.read_text(encoding="utf-8"))
    assert list(data["packages"]) == ["autolab-alfworld-ladder-r4-v4"]
    assert any("min_tokens" in f for f in data["packages"]["autolab-alfworld-ladder-r4-v4"])
    assert "baseline entry autolab-alfworld-ladder-r4-v4: new entry" in result.stdout and "\n  + " in result.stdout


def test_update_baseline_refuses_a_package_with_a_fail(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", "| placebo | 0.45 |", "| placebo | 0.46 |")
    target = tmp_path / "baseline.json"
    result = run("--package", str(package), "--baseline", str(target), "--update-baseline")
    assert result.returncode == 1
    assert "refusing to update the baseline entry of autolab-alfworld-ladder-r4-v4" in result.stderr
    assert not target.exists()


@pytest.mark.parametrize("content,message", [(None, "does not exist"), ("{}", "has no 'packages' object"),
                                             ('{"packages": []}', "has no 'packages' object"), ("{not json", "is not valid JSON")],
                         ids=["missing", "empty", "wrong-type", "malformed"])
def test_baseline_fails_closed(tmp_path: Path, content, message: str) -> None:
    target = tmp_path / "baseline.json"
    if content is not None:
        target.write_text(content, encoding="utf-8")
    assert_fails_on(run("--package", str(V4), "--baseline", str(target)), message)


def test_package_without_a_baseline_entry_fails(tmp_path: Path) -> None:
    renamed = tmp_path / "autolab-alfworld-ladder-r4-v4b"
    shutil.copytree(V4, renamed)
    result = run("--package", str(renamed))
    assert_fails_on(result, "N/V baseline: entry for autolab-alfworld-ladder-r4-v4b")
    assert "--update-baseline" in result.stdout


def test_stale_baseline_entry_fails(tmp_path: Path) -> None:
    data = json.loads((ROOT / "scripts" / "verify_autolab_packages.baseline.json").read_text(encoding="utf-8"))
    data["packages"]["autolab-alfworld-ladder-r4-v4"].append("README text 'a sentence that a later change could hide behind'")
    target = tmp_path / "baseline.json"
    target.write_text(json.dumps(data), encoding="utf-8")
    assert_fails_on(run("--package", str(V4), "--baseline", str(target)), "N/V baseline: stale entry README text 'a sentence")


def test_early_stop_fixtures_are_verified() -> None:
    out = run("--package", str(EARLY1), "--package", str(EARLY2)).stdout
    assert "stopped at look 1 of 2 pre-registered" in out and "stopped at look 2 of 2 pre-registered" in out
    assert "103 units = ceil(look 0.34 x planned 300)" in out and "201 units = ceil(look 0.67 x planned 300)" in out
    assert "z = 3.8992 (sequential threshold of the run's look)" in out and "z = 2.7777 (sequential threshold of the run's look)" in out
    assert "report: units_used = 300" in out
    assert "states of the stop look = recomputed primary states" in out


def test_tampered_early_stop_fails(tmp_path: Path) -> None:
    package = copy_package(EARLY2, tmp_path)
    run_obj = next(json.loads(x) for x in (package / "knowledge.jsonl").read_text(encoding="utf-8").splitlines() if json.loads(x)["kind"] == "run")
    stop = run_obj["payload"]["sequential"]["decision"]
    edit_object(package, stop, lambda p: p["states"].update(mismatched_type="practical"))
    assert_fails_on(run("--package", str(package)), stop + ": states of the stop look = recomputed primary states")


def test_extra_table_cell_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_text(package / "README.md", "| `finding:00fa0192dfd13db2` |", "| `finding:00fa0192dfd13db2` | p < 0.001 |")
    assert_fails_on(run("--package", str(package)), "has the 9 cells of its header")


def test_placebo_tokens_halved_fails(tmp_path: Path) -> None:
    package = copy_package(V3, tmp_path)               # V3's audit predates the lab's placebo-length check
    columns, rows = read_rows(package)
    for r in rows:
        if r["arm"] == "placebo":
            r["memory_tokens"] = str(int(r["memory_tokens"]) // 2)
    write_rows(package, columns, rows)
    assert_fails_on(run("--package", str(package)), "placebo memory tokens >= 0.8 x retrieved_task")


def test_failed_check_with_a_valid_verdict_fails(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_object(package, "audit:ff4e4912acd1a5e9", lambda p: p["checks"]["leakage"].update(ok=False))
    assert_fails_on(run("--package", str(package)), "follow the checks' ok and severity", "N/V baseline: cycle 1 audit:ff4e4912acd1a5e9: checks.leakage (ok = False)")


def test_changed_model_calls_is_visible(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)
    edit_object(package, "report:81d81227fb6cc53c", lambda p: p.update(model_calls=9999))
    assert_fails_on(run("--package", str(package)), "N/V baseline: report: model_calls = 9999")


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


def test_expected_state_verdict_rule_matches_the_lab() -> None:
    """program.hypothesis_verdict (lab code from 2026-11-19): V4 H3 expected positive_below_sesoi, state practical."""
    m = load_module()
    h3 = {"predicted": "positive", "expected_state": "positive_below_SESOI"}
    assert m.expected_state_verdict(h3, "practical", [0.177, 0.303], 0.12) == ("refuted", "expected_state=positive_below_sesoi")
    assert m.lab_verdict("positive", "practical", True, False, hyp=h3, ci=[0.177, 0.303], sesoi=0.12) == "refuted"
    assert m.lab_verdict("positive", "practical", True, False) == "supported"          # older packages: direction only
    pr = {"predicted": "positive", "expected_state": "practical"}
    assert m.expected_state_verdict(pr, "positive", [0.02, 0.10], 0.12)[0] == "refuted"
    assert m.expected_state_verdict(pr, "positive", [0.05, 0.28], 0.12)[0] == "inconclusive"
    assert m.expected_state_verdict({"predicted": "null", "expected_state": "negative"}, "equivalent", [-0.05, 0.05], 0.12)[0] == "inconclusive"
    assert m.expected_state_verdict({"predicted": "null"}, "equivalent", [-0.05, 0.05], 0.12) == ("supported", "kierunek predicted")
    assert m.expected_state_verdict(pr, "inconclusive", [-0.1, 0.3], 0.12)[0] == "inconclusive"
    assert m.lab_verdict("positive", "practical", True, True, hyp=pr, ci=[0.2, 0.3], sesoi=0.12) == "disputed"
    assert m.expected_state_verdict({"predicted": "positive", "expected_state": "positive_below_sesoi"}, "equivalent", [-0.01, 0.08], 0.12)[0] == "inconclusive"
    eq = {"predicted": "null", "expected_state": "equivalent"}
    assert m.expected_state_verdict(eq, "negative", [-0.10, -0.01], 0.12)[0] == "supported"
    assert m.expected_state_verdict(eq, "negative", [-0.2, -0.01], 0.12)[0] == "inconclusive"
    assert m.expected_state_verdict(eq, "negative", [-0.3, -0.13], 0.12)[0] == "refuted"


# --------------------------------------------------------------------------- package-local N/V baseline (2026-11-19)
def _pin_in_manifest(package: Path, name: str) -> None:
    man = json.loads((package / "PUBLISHED_FILES.json").read_text(encoding="utf-8"))
    data = (package / name).read_bytes()
    entry = {"path": name, "target": "data/lab/%s/%s" % (package.name, name), "sha256": hashlib.sha256(data).hexdigest(),
             "sha256_source": hashlib.sha256(data).hexdigest(), "bytes": len(data), "edits": ["none"]}
    man["published"] = [e for e in man["published"] if e.get("path") != name] + [entry]
    (package / "PUBLISHED_FILES.json").write_text(json.dumps(man, indent=1), encoding="utf-8")


def _renamed_v4(tmp_path: Path) -> Path:
    """V4 under a name with no entry in the shared baseline (a new package, as an export would add it)."""
    dest = tmp_path / "autolab-alfworld-ladder-r4-v4b"
    shutil.copytree(V4, dest)
    return dest


def test_package_local_baseline_written_by_the_export_passes_when_pinned(tmp_path: Path) -> None:
    package = _renamed_v4(tmp_path)
    w = run("--package", str(package), "--write-package-baseline")
    assert w.returncode == 0 and (package / "NV_BASELINE.json").is_file(), w.stdout + w.stderr
    assert_fails_on(run("--package", str(package)), "NV_BASELINE.json is pinned by the export manifest")
    _pin_in_manifest(package, "NV_BASELINE.json")
    result = run("--package", str(package))
    assert result.returncode == 0, result.stdout[-3000:]
    assert "entry from the package's own NV_BASELINE.json" in result.stdout


def test_package_local_baseline_must_equal_the_nv_set(tmp_path: Path) -> None:
    package = _renamed_v4(tmp_path)
    assert run("--package", str(package), "--write-package-baseline").returncode == 0
    doc = json.loads((package / "NV_BASELINE.json").read_text(encoding="utf-8"))
    dropped = doc["fields"].pop(0)
    (package / "NV_BASELINE.json").write_text(json.dumps(doc), encoding="utf-8")
    _pin_in_manifest(package, "NV_BASELINE.json")
    assert_fails_on(run("--package", str(package)), "N/V baseline: " + dropped[:40])


def test_package_local_baseline_is_refused_for_a_failing_package(tmp_path: Path) -> None:
    package = _renamed_v4(tmp_path)
    edit_text(package / "README.md", "| retrieved_task | 0.69 |", "| retrieved_task | 0.70 |")
    w = run("--package", str(package), "--write-package-baseline")
    assert w.returncode == 1 and not (package / "NV_BASELINE.json").exists()
    assert "refusing to write NV_BASELINE.json" in w.stderr


def test_malformed_or_foreign_package_baseline_fails(tmp_path: Path) -> None:
    package = _renamed_v4(tmp_path)
    (package / "NV_BASELINE.json").write_text(json.dumps({"package": "another", "fields": []}), encoding="utf-8")
    _pin_in_manifest(package, "NV_BASELINE.json")
    assert_fails_on(run("--package", str(package)), "NV_BASELINE.json must be")


def test_shared_baseline_entry_wins_over_the_package_file(tmp_path: Path) -> None:
    package = copy_package(V4, tmp_path)               # V4 has an entry in the shared baseline
    (package / "NV_BASELINE.json").write_text(json.dumps({"package": package.name, "fields": []}), encoding="utf-8")
    _pin_in_manifest(package, "NV_BASELINE.json")
    result = run("--package", str(package))
    assert "entry from the package's own" not in result.stdout


# --------------------------------------------------------------------------- null Brier with measurement_problem
def _replace_ids(value, mapping: dict[str, str]):
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [_replace_ids(x, mapping) for x in value]
    if isinstance(value, dict):
        return {mapping.get(k, k): _replace_ids(v, mapping) for k, v in value.items()}
    return value


def _rehash_package(package: Path) -> dict[str, str]:
    """Recompute knowledge.jsonl hashes/ids, README id references, PROVENANCE.json and PUBLISHED_FILES.json."""
    kpath = package / "knowledge.jsonl"
    objs = [json.loads(line) for line in kpath.read_text(encoding="utf-8").splitlines() if line.strip()]
    mapping: dict[str, str] = {}
    for o in objs:
        o["parents"] = [_replace_ids(p, mapping) for p in o["parents"]]
        o["payload"] = _replace_ids(o["payload"], mapping)
        body = {"kind": o["kind"], "program": o.get("program"), "payload": o["payload"], "parents": sorted(set(o["parents"]))}
        sha = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        if o.get("redacted"):
            o["sha256_redacted"] = sha
        else:
            old_id = o["id"]
            new_id = "%s:%s" % (o["kind"], sha[:16])
            o["sha256"] = sha
            o["id"] = new_id
            if new_id != old_id:
                mapping[old_id] = new_id
    kpath.write_bytes(("".join(json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n" for o in objs)).encode("utf-8"))
    if mapping:
        rpath = package / "README.md"
        readme = rpath.read_text(encoding="utf-8")
        for old_id, new_id in mapping.items():
            readme = readme.replace(old_id, new_id)
        rpath.write_bytes(readme.encode("utf-8"))
    prov_path = package / "PROVENANCE.json"
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    prov["knowledge_sha256"] = hashlib.sha256(kpath.read_bytes()).hexdigest()
    prov_path.write_bytes((json.dumps(prov, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    man_path = package / "PUBLISHED_FILES.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    for entry in man.get("published", []):
        p = package / entry["path"]
        if p.is_file():
            data = p.read_bytes()
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            entry["sha256_source"] = entry["sha256"]
            entry["bytes"] = len(data)
    man_path.write_bytes((json.dumps(man, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return mapping


def _v5b_with_null_brier_mp(tmp_path: Path, name: str = "autolab-synthetic-v5b-null-brier", brier_mean: float = 0.16) -> tuple[Path, str]:
    """Copy V5B-shape under a fresh name, set brier=None on the measurement_problem arm (mismatched_type) and rehash."""
    dest = tmp_path / name
    shutil.copytree(V5B, dest)
    edit_object(dest, "finding:7faec13a258c7b28", lambda p: p.update(brier=None))
    edit_object(dest, "report:e7d72ac2fc31c5c1", lambda p: p.update(brier_mean=brier_mean))
    mapping = _rehash_package(dest)
    return dest, mapping.get("finding:7faec13a258c7b28", "finding:7faec13a258c7b28")


def test_null_brier_confirmed_measurement_problem_passes(tmp_path: Path) -> None:
    package, fid = _v5b_with_null_brier_mp(tmp_path)
    w = run("--package", str(package), "--write-package-baseline")
    assert w.returncode == 0, w.stdout[-3000:] + w.stderr
    _pin_in_manifest(package, "NV_BASELINE.json")
    result = run("--package", str(package))
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr
    assert "PASS  cycle 1 %s (H2): brier not scored: measurement_problem confirmed (untagged_not_truncated diff +0.101" % fid in result.stdout
    assert "PASS  report: brier_mean = 0.16  | mean of 1 scored finding Brier scores 0.1600 (1 unscored excluded)" in result.stdout
    assert "all 1 package(s) verified" in result.stdout


def test_null_brier_confirmed_measurement_problem_must_be_excluded_from_brier_mean(tmp_path: Path) -> None:
    # brier_mean still averages the unscored finding (0.16 and 0.09 -> 0.125) instead of excluding it
    package, fid = _v5b_with_null_brier_mp(tmp_path, brier_mean=0.125)
    result = run("--package", str(package))
    assert "PASS  cycle 1 %s (H2): brier not scored: measurement_problem confirmed" % fid in result.stdout
    assert_fails_on(result, "report: brier_mean = 0.125")


def test_null_brier_all_findings_unscored_requires_null_brier_mean(tmp_path: Path) -> None:
    package = tmp_path / "autolab-alfworld-ladder-r4-v4-null-brier"
    shutil.copytree(V4, package)
    for fid in ("finding:00fa0192dfd13db2", "finding:102266bf120db7a3", "finding:e7402eac3345ea88"):
        edit_object(package, fid, lambda p: p.update(brier=None))
    edit_object(package, "report:81d81227fb6cc53c", lambda p: p.update(brier_mean=None))
    _rehash_package(package)
    w = run("--package", str(package), "--write-package-baseline")
    assert w.returncode == 0, w.stdout[-3000:] + w.stderr
    _pin_in_manifest(package, "NV_BASELINE.json")
    result = run("--package", str(package))
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr
    assert "PASS  report: brier_mean = None  | all 3 finding Brier scores unscored (expected None)" in result.stdout
    # a non-null brier_mean when all findings are unscored must fail
    edit_object(package, "report:81d81227fb6cc53c", lambda p: p.update(brier_mean=0.36))
    assert_fails_on(run("--package", str(package)), "report: brier_mean = 0.36")


def test_null_brier_claimed_measurement_problem_when_criterion_passes_fails(tmp_path: Path) -> None:
    # (a) arm is marked measurement_problem and brier=None, but per_unit.csv shows the format criterion passes (balanced)
    package, fid = _v5b_with_null_brier_mp(tmp_path, name="autolab-synthetic-v5b-mp-passes-data")
    columns, rows = read_rows(package)
    placebo_by_unit = {r["unit"]: r["untagged_not_truncated"] for r in rows if r["arm"] == "placebo"}
    for r in rows:
        if r["arm"] == "mismatched_type":
            r["untagged_not_truncated"] = placebo_by_unit[r["unit"]]
    write_rows(package, columns, rows)
    assert_fails_on(run("--package", str(package)),
                    "%s (H2): brier = None (measurement_problem claimed, but pre-registered format criteria passed)" % fid)

    # (b) clean arm (retrieved_task) falsely marked measurement_problem with brier=None while its data pass
    clean_pkg = copy_package(V5B, tmp_path)
    edit_object(clean_pkg, "finding:de80c241f8c2275d", lambda p: p.update(
        brier=None,
        measurement_problem=["proces: untagged_not_truncated na krok wariant \u2212 placebo +0.050 [+0.035; +0.065] > 0.03 (kryterium ustalone przed pomiarem) \u2014 tre\u015b\u0107 i format/proces nie s\u0105 rozdzielone"],
    ))
    assert_fails_on(run("--package", str(clean_pkg)),
                    "finding:de80c241f8c2275d (H1): brier = None (measurement_problem claimed, but pre-registered format criteria passed)")


def test_null_brier_unresolved_under_imbalance_only_fails(tmp_path: Path) -> None:
    # Under format_rule='imbalance_only', an 'unresolved' criterion (|diff| <= 0.03, CI crossing 0.03) PASSES
    package, fid = _v5b_with_null_brier_mp(tmp_path, name="autolab-synthetic-v5b-unresolved")
    columns, rows = read_rows(package)
    units = sorted({r["unit"] for r in rows if r["arm"] == "mismatched_type"})
    zero_units = set(units[50:])
    for r in rows:
        if r["arm"] == "mismatched_type" and r["unit"] in zero_units:
            r["untagged_not_truncated"] = "0"
    write_rows(package, columns, rows)
    result = run("--package", str(package))
    assert "unresolved at \u00b10.03" in result.stdout
    assert_fails_on(result, "%s (H2): brier = None (measurement_problem claimed, but pre-registered format criteria passed)" % fid)


def test_null_brier_without_measurement_problem_mark_fails(tmp_path: Path) -> None:
    # (a) clean arm: brier=None with no measurement_problem mark
    clean_pkg = copy_package(V5B, tmp_path)
    edit_object(clean_pkg, "finding:de80c241f8c2275d", lambda p: p.update(brier=None))
    assert_fails_on(run("--package", str(clean_pkg)),
                    "finding:de80c241f8c2275d (H1): brier = None ((p_positive 0.6 - [state in practical/positive])^2)",
                    "brier is null without a measurement_problem mark")

    # (b) arm whose format criterion genuinely fails in per_unit.csv, but finding omits measurement_problem
    unmarked_pkg, fid = _v5b_with_null_brier_mp(tmp_path, name="autolab-synthetic-v5b-unmarked")
    edit_object(unmarked_pkg, fid, lambda p: p.pop("measurement_problem"))
    assert_fails_on(run("--package", str(unmarked_pkg)),
                    "%s (H2): brier = None ((p_positive 0.3 - [state in practical/positive])^2)" % fid,
                    "brier is null without a measurement_problem mark")


def test_null_brier_with_unrelated_measurement_problem_text_fails(tmp_path: Path) -> None:
    package, fid = _v5b_with_null_brier_mp(tmp_path, name="autolab-synthetic-v5b-unrelated-mp")
    edit_object(package, fid, lambda p: p.update(measurement_problem=["b\u0142\u0119dy ramienia > 5%"]))
    assert_fails_on(run("--package", str(package)),
                    "%s (H2): brier = None (measurement_problem does not name the failing format criterion)" % fid)
