"""verify_arena_numbers.py recomputes the ledger's Entry H numbers from tracked files.

The tests run the script against the real tracked result files, against copies in
which exactly one input is altered, and against malformed inputs. Every alteration
must change the exit status and name the check that caught it, so that a check
which stops checking is noticed by a failing test.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, List, Tuple

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "arena" / "verify_arena_numbers.py"
LEDGER = Path("docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md")
FRESH = Path("data/lab/arena/raw-provenance-fresh-replication-v1/results.json")
E3_ARMS = Path("data/lab/arena/base-plus-x-v2/e3-arms.json")
E3_JUDGED = Path("data/lab/arena/base-plus-x-v2/e3-judged.json")
E3_ANALYSIS = Path("data/lab/arena/base-plus-x-v2/e3-analysis.json")
BREADTH_ARMS = Path("data/lab/arena/mem0-breadth-arms.json")
BREADTH_JUDGED = Path("data/lab/arena/mem0-breadth-judged.json")
NEEDED = [LEDGER, FRESH, E3_ARMS, E3_JUDGED, E3_ANALYSIS, BREADTH_ARMS, BREADTH_JUDGED]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")


def copy_inputs(dest: Path) -> None:
    for rel in NEEDED:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)


def edit_json(path: Path, change: Callable[[Any], None]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def edit_text(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, "the text to alter is not in " + str(path)  # an alteration that changes nothing proves nothing
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def first(rows: List[dict], **match: Any) -> dict:
    for row in rows:
        if all(row.get(k) == v for k, v in match.items()):
            return row
    raise AssertionError("no row matches %r" % (match,))


# --------------------------------------------------------------------------- the real files
def test_real_tracked_files_pass() -> None:
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    assert "recomputed 5/8, 6/8, 4/8" in out
    assert "recomputed 5/9, 6/9, 4/9" in out
    assert "recomputed 17" in out
    assert "FAIL" not in out
    assert "0e5e2d1a" in out and "6a27ffc2" in out


def test_statistics_and_overhead_lines_are_pinned() -> None:
    out = run().stdout
    assert "exact McNemar p = 0.250 (one-sided), 0.500 (two-sided)" in out
    assert "Clopper-Pearson interval for the repair rate 0.015 to 0.364" in out
    assert "mean of per-unit ratios 21.36x (min 5.6x, max 32.1x); pooled ratio 20.96x" in out
    assert "overhead rounds to the ledger's ~21.4x (quoted in Entry Q)" in out
    assert "carries 5.6x to 32.1x more context than compact" in out
    assert "(4/8 against 6/8 in the fresh replication, 4/9 against 6/9 in E3)" in out


def test_prints_token_counts_for_both_arms_per_unit() -> None:
    out = run().stdout
    line = [row for row in out.splitlines() if row.strip().startswith("0e5e2d1a") and "single-session-assistant" in row]
    assert line, out
    assert "109" in line[0] and "609" in line[0]
    e3 = [row for row in out.splitlines() if row.strip().startswith("6a27ffc2") and "knowledge-update" in row]
    assert e3, out
    assert "100" in e3[0] and "2988" in e3[0] and "29.9x" in e3[0]


def test_reproduce_md_shows_the_real_output_of_the_script() -> None:
    """The output pasted into REPRODUCE.md must be what the committed script prints, byte for byte."""
    text = (ROOT / "REPRODUCE.md").read_text(encoding="utf-8")
    start = text.index("== Entry H: fresh replication")
    end = text.index("all checks passed", start) + len("all checks passed")
    assert text[start:end] == run().stdout.rstrip("\n")


def test_help_exits_zero() -> None:
    result = run("--help")
    assert result.returncode == 0
    assert "--repo" in result.stdout


def test_not_a_checkout_exits_two(tmp_path: Path) -> None:
    assert run("--repo", str(tmp_path)).returncode == 2


def test_missing_input_exits_two(tmp_path: Path) -> None:
    copy_inputs(tmp_path)
    (tmp_path / E3_ARMS).unlink()
    result = run("--repo", str(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr


def test_a_result_file_that_resolves_outside_the_repository_is_refused(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside.json"
    copy_inputs(repo)
    shutil.copyfile(ROOT / FRESH, outside)
    target = repo / FRESH
    target.unlink()
    try:
        target.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("this platform or account cannot create symbolic links")
    result = run("--repo", str(repo))
    assert result.returncode == 2, result.stdout + result.stderr
    assert "refusing to read outside the repository" in result.stderr


# --------------------------------------------------------------------------- one altered input, exit 1
def flip_fresh_plus_raw_label(tmp: Path) -> None:
    def change(d: Any) -> None:
        judged = d["results"][0]["arms"]["mem0_compact_plus_raw"]["judged"]
        judged["label"] = not judged["label"]
    edit_json(tmp / FRESH, change)


def add_a_token_to_fresh_plus_raw(tmp: Path) -> None:
    def change(d: Any) -> None:
        arm = d["results"][0]["arms"]["mem0_compact_plus_raw"]
        arm["context_tokens"] = arm["context_tokens"] + 1
    edit_json(tmp / FRESH, change)


def change_fresh_spend(tmp: Path) -> None:
    edit_json(tmp / FRESH, lambda d: d["spend"].__setitem__("total_usd", 0.5))


def make_a_fresh_unit_unobservable(tmp: Path) -> None:
    def change(d: Any) -> None:
        d["results"][0]["arms"]["mem0_compact_plus_raw"]["gold_state"]["observable"] = False
    edit_json(tmp / FRESH, change)


def flip_e3_plus_raw_label(tmp: Path) -> None:
    def change(d: Any) -> None:
        row = first(d["judgements"], _arm="mem0_compact_plus_raw")
        row["label"] = not row["label"]
    edit_json(tmp / E3_JUDGED, change)


def flip_the_compact_label_of_the_e3_repair(tmp: Path) -> None:
    def change(d: Any) -> None:
        row = first(d["judgements"], _arm="mem0_original", question_id="6a27ffc2")
        row["label"] = not row["label"]
    edit_json(tmp / BREADTH_JUDGED, change)


def edit_the_stored_e3_scores(tmp: Path) -> None:
    edit_json(tmp / E3_ANALYSIS, lambda d: d["scores"].__setitem__("compact_plus_raw", "7/9"))


def remove_the_stored_e3_fix_key(tmp: Path) -> None:
    edit_json(tmp / E3_ANALYSIS, lambda d: d.pop("COMPACT_WRONG_RAW_FIXES"))


def remove_an_e3_unit(tmp: Path) -> None:
    def change(d: Any) -> None:
        d["arms"].remove(first(d["arms"], arm="mem0_compact_plus_raw"))
    edit_json(tmp / E3_ARMS, change)


def ledger_overhead(tmp: Path) -> None:
    edit_text(tmp / LEDGER, "~21.4x token overhead", "~21.5x token overhead")


def ledger_unit_total(tmp: Path) -> None:
    edit_text(tmp / LEDGER, "across 17 combined observable units", "across 18 combined observable units")


def ledger_replication_spend(tmp: Path) -> None:
    edit_text(tmp / LEDGER, "replication $0.575419", "replication $0.575420")


def ledger_e3_triple(tmp: Path) -> None:
    edit_text(tmp / LEDGER, "compact 5/9, compact+raw **6/9**, raw-only 4/9", "compact 5/9, compact+raw **7/9**, raw-only 4/9")


def ledger_fresh_triple(tmp: Path) -> None:
    edit_text(tmp / LEDGER, "compact 5/8, compact+raw **6/8**, raw-only 4/8", "compact 4/8, compact+raw **6/8**, raw-only 4/8")


def ledger_fresh_repair_id(tmp: Path) -> None:
    edit_text(tmp / LEDGER, "1 repair (`0e5e2d1a`", "1 repair (`0e5e2d1b`")


def ledger_e3_repair_id(tmp: Path) -> None:
    edit_text(tmp / LEDGER, "1 repair (`6a27ffc2`", "1 repair (`6a27ffc3`")


def ledger_regression_statement(tmp: Path) -> None:
    edit_text(tmp / LEDGER, "Zero regressions in both runs", "One regression in one run")


CHANGED: List[Tuple[str, Callable[[Path], None], str]] = [
    ("fresh plus-raw label flipped", flip_fresh_plus_raw_label, "fresh: compact / compact+raw / raw-only correct"),
    ("fresh plus-raw token added", add_a_token_to_fresh_plus_raw, "compact_plus_raw tokens == compact tokens + raw_only tokens"),
    ("fresh spend changed", change_fresh_spend, "fresh: recorded spend"),
    ("fresh unit made unobservable", make_a_fresh_unit_unobservable, "fresh: all 8 units observable"),
    ("E3 plus-raw label flipped", flip_e3_plus_raw_label, "E3: compact / compact+raw / raw-only correct"),
    ("E3 compact label of the repair flipped", flip_the_compact_label_of_the_e3_repair, "E3: compact / compact+raw / raw-only correct"),
    ("stored E3 scores edited", edit_the_stored_e3_scores, "E3: agrees with the stored e3-analysis.json"),
    ("stored E3 fix key removed", remove_the_stored_e3_fix_key, "E3: agrees with the stored e3-analysis.json"),
    ("E3 unit removed", remove_an_e3_unit, "combined observable units"),
    ("ledger overhead changed", ledger_overhead, "mean per-unit overhead rounds"),
    ("ledger unit total changed", ledger_unit_total, "combined observable units"),
    ("ledger replication spend changed", ledger_replication_spend, "fresh: recorded spend"),
    ("ledger E3 counts changed", ledger_e3_triple, "E3: compact / compact+raw / raw-only correct"),
    ("ledger fresh counts changed", ledger_fresh_triple, "fresh: compact / compact+raw / raw-only correct"),
    ("ledger fresh repair id changed", ledger_fresh_repair_id, "fresh: repairs"),
    ("ledger E3 repair id changed", ledger_e3_repair_id, "E3: repairs"),
    ("ledger no-regression statement changed", ledger_regression_statement, "regressions = 0"),
]


@pytest.mark.parametrize("alter, expected", [(c[1], c[2]) for c in CHANGED], ids=[c[0] for c in CHANGED])
def test_one_altered_input_is_caught_by_the_named_check(tmp_path: Path, alter: Callable[[Path], None], expected: str) -> None:
    copy_inputs(tmp_path)
    alter(tmp_path)
    result = run("--repo", str(tmp_path))
    assert result.returncode == 1, result.stdout + result.stderr
    failed = [line for line in result.stdout.splitlines() if line.startswith("FAIL")]
    assert any(expected in line for line in failed), "expected a FAIL line containing %r\n%s" % (expected, result.stdout)


# --------------------------------------------------------------------------- malformed input, exit 2
def ledger_not_utf8(tmp: Path) -> None:
    (tmp / LEDGER).write_bytes(b"\xff\xfe\x00 not utf-8")


def ledger_without_the_overhead_figure(tmp: Path) -> None:
    edit_text(tmp / LEDGER, "~21.4x token overhead", "a large token overhead")


def fresh_judgement_is_a_string(tmp: Path) -> None:
    def change(d: Any) -> None:
        d["results"][0]["arms"]["mem0_compact"]["judged"] = "correct"
    edit_json(tmp / FRESH, change)


def fresh_label_is_not_a_boolean(tmp: Path) -> None:
    def change(d: Any) -> None:
        d["results"][0]["arms"]["mem0_compact"]["judged"]["label"] = None
    edit_json(tmp / FRESH, change)


def e3_judgement_listed_twice(tmp: Path) -> None:
    def change(d: Any) -> None:
        row = first(d["judgements"], _arm="mem0_compact_plus_raw")
        d["judgements"].insert(0, dict(row, label=not row["label"]))
    edit_json(tmp / E3_JUDGED, change)


def fresh_file_truncated(tmp: Path) -> None:
    (tmp / FRESH).write_text('{"results": [', encoding="utf-8")


MALFORMED: List[Tuple[str, Callable[[Path], None]]] = [
    ("ledger is not UTF-8", ledger_not_utf8),
    ("ledger no longer quotes the overhead", ledger_without_the_overhead_figure),
    ("a judgement is a string", fresh_judgement_is_a_string),
    ("a label is not a boolean", fresh_label_is_not_a_boolean),
    ("a unit is judged twice", e3_judgement_listed_twice),
    ("a result file is truncated", fresh_file_truncated),
]


@pytest.mark.parametrize("alter", [m[1] for m in MALFORMED], ids=[m[0] for m in MALFORMED])
def test_malformed_input_exits_two_not_one(tmp_path: Path, alter: Callable[[Path], None]) -> None:
    copy_inputs(tmp_path)
    alter(tmp_path)
    result = run("--repo", str(tmp_path))
    assert result.returncode == 2, result.stdout + result.stderr
    assert "input error" in result.stderr
    assert "Traceback" not in result.stderr
