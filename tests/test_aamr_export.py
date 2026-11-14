"""Tests of scripts/aamr_export.py on fictional laboratory tasks: a local bare repository is the 'GitHub', a fake pull-request client merges into it.
No network, no model, nothing from the real laboratory."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import aamr_export as ex  # noqa: E402

README = "# Fictional task\n\n**Status: completed, a fictional development result.**\n\nHeadline numbers and limits.\n"
FAKE_TOKEN = "ghp_" + "aB3dE5fG7hJ9kL1m" * 2


def g(cwd: Path, *args: str) -> str:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


class FakeGitHub:
    """Pull requests against a local bare repository: merging is a real merge commit pushed to its main."""

    def __init__(self, origin: Path, tmp: Path):
        self.origin, self.tmp, self.prs, self.state, self.merged = origin, tmp, {}, ("success", "3 checks"), []

    def pr_create(self, base, head, title, body):
        number = len(self.prs) + 7
        self.prs[number] = {"base": base, "head": head, "title": title, "body": body}
        return number, f"https://example.invalid/pull/{number}"

    def checks(self, number):
        return self.state

    def merge(self, number):
        pr = self.prs[number]
        clone = self.tmp / f"merge-{number}"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(clone)], check=True, capture_output=True)
        g(clone, "checkout", "-q", pr["base"])
        g(clone, "merge", "-q", "--no-ff", "-m", f"Merge pull request #{number}", f"origin/{pr['head']}")
        g(clone, "push", "-q", "origin", pr["base"])
        self.merged.append(number)


@pytest.fixture()
def world(tmp_path: Path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    root = tmp_path / "AAMR"
    canonical = root / "repo"
    root.mkdir()
    subprocess.run(["git", "clone", "-q", str(origin), str(canonical)], check=True, capture_output=True)
    g(canonical, "checkout", "-q", "-b", "main")
    (canonical / "docs").mkdir()
    (canonical / "docs" / "x.md").write_text("published\n", encoding="utf-8")
    g(canonical, "add", "-A")
    g(canonical, "commit", "-q", "-m", "base")
    g(canonical, "push", "-q", "-u", "origin", "main")
    lab = tmp_path / "lab"
    run_dir, out_dir = lab / "run", lab / "out"
    (run_dir / "sessions").mkdir(parents=True)
    (out_dir).mkdir(parents=True)
    (run_dir / "DONE.json").write_text("{}", encoding="utf-8")
    (run_dir / "sessions" / "s1.jsonl").write_text('{"task": 1, "solved": true}\n' * 50, encoding="utf-8")
    (out_dir / "README.md").write_text(README, encoding="utf-8")
    (out_dir / "REPORT.md").write_text("# Report\n\nresult 1 of 2\n", encoding="utf-8")
    (out_dir / "results.json").write_text(json.dumps({"solved": 1, "of": 2}), encoding="utf-8")
    (out_dir / "raw-freeze.json").write_text(json.dumps({"files": {"sessions/s1.jsonl": ex.sha256_file(run_dir / "sessions" / "s1.jsonl")}}), encoding="utf-8")
    return {"origin": origin, "root": root, "canonical": canonical, "run": run_dir, "out": out_dir, "config": tmp_path / "sync.json", "tmp": tmp_path,
            "gh": FakeGitHub(origin, tmp_path)}


def make_plan(w, **extra) -> dict:
    plan = {"id": "FAKE-1", "repo": "owner/name", "canonical": str(w["canonical"]), "work_root": str(w["root"] / "work"), "private_root": str(w["root"] / "private"),
            "branch": "claude/export-fake-1", "run_dir": str(w["run"]), "title": "Export: FAKE-1",
            "publish": [{"from": str(w["out"] / name), "to": f"data/lab/fake-1/{name}"} for name in ("README.md", "REPORT.md", "results.json", "raw-freeze.json")],
            "private": [{"from": str(w["run"]), "to": "raw/fake-1/run", "what": "raw run of the fictional task, pinned by SHA-256 in raw-freeze.json"}]}
    plan.update(extra)
    return plan


def run_export(w, plan, **kw):
    lines = []
    code = ex.export(plan, w["config"], w["gh"], identity=("t", "t@example.invalid"), log=lines.append, sleeper=lambda s: None, **kw)
    return code, lines


def record(w):
    return json.loads(w["config"].read_text(encoding="utf-8"))["exports"]["FAKE-1"]


def problems(w, plan):
    ex.git(w["canonical"], "fetch", "-q", "origin")
    check = ex.check_plan(plan, lambda rel: ex.git(w["canonical"], "cat-file", "-e", f"origin/main:{rel}", check=False).returncode == 0)
    return check["result"], {p["code"] for p in check["problems"]}


# ------------------------------------------------------------------------------------------------- the whole route
def test_full_route_finished_task_to_main(world):
    w = world
    code, log = run_export(w, make_plan(w), merge=True, move_private=True)
    assert code == 0, log
    # the result is on main, with its README and a manifest that uses relative paths and SHA-256
    ex.git(w["canonical"], "fetch", "-q", "origin")
    for name in ("README.md", "REPORT.md", "results.json", "raw-freeze.json", "PUBLISHED_FILES.json"):
        assert ex.git(w["canonical"], "cat-file", "-e", f"origin/main:data/lab/fake-1/{name}", check=False).returncode == 0, name
    manifest = json.loads(ex.git(w["canonical"], "show", "origin/main:data/lab/fake-1/PUBLISHED_FILES.json").stdout)
    assert manifest["paths_are_relative"] is True and manifest["protected_check"]["result"] == "withheld"
    assert all(not Path(p["path"]).is_absolute() and len(p["sha256"]) == 64 for p in manifest["published"])
    assert w["gh"].merged == [7] and "HANDOFF" in w["gh"].prs[7]["body"] and "withheld" in w["gh"].prs[7]["body"].lower()
    # raw data is in the private area with a manifest and a pointer; the laboratory keeps no copy, only a pointer to the place
    private = w["root"] / "private" / "raw" / "fake-1" / "run"
    assert (private / "sessions" / "s1.jsonl").is_file() and (private / "MANIFEST.sha256.json").is_file()
    assert json.loads((private / "MANIFEST.sha256.json").read_text())["files"]["sessions/s1.jsonl"] == ex.sha256_file(private / "sessions" / "s1.jsonl")
    assert not (w["run"] / "sessions" / "s1.jsonl").exists() and (w["run"] / ".." / "run.MOVED.json").exists()
    # the export record shows it, and the worktree and the local branch are gone
    rec = record(w)
    assert rec["pr"] == 7 and rec["merged"] is True and rec["confirmed_on_main"] and rec["protected_check"]["result"] == "withheld"
    assert "hold" not in rec and rec["private_location"] == ["private/raw/fake-1/run"]
    assert not (w["root"] / "work" / "claude-export-fake-1").exists()
    assert "claude/export-fake-1" not in ex.git(w["canonical"], "branch").stdout


def test_without_merge_the_pull_request_stays_open_and_main_is_untouched(world):
    w = world
    before = ex.git(w["canonical"], "rev-parse", "origin/main").stdout.strip()
    code, _ = run_export(w, make_plan(w), merge=False)
    assert code == 0 and w["gh"].merged == [] and record(w)["pr"] == 7 and "merged" not in record(w)
    ex.git(w["canonical"], "fetch", "-q", "origin")
    assert ex.git(w["canonical"], "rev-parse", "origin/main").stdout.strip() == before
    assert ex.git(w["canonical"], "cat-file", "-e", "origin/claude/export-fake-1:data/lab/fake-1/README.md", check=False).returncode == 0
    assert (w["run"] / "sessions" / "s1.jsonl").exists()          # copied, not moved, unless asked


def test_failing_checks_do_not_merge_and_the_report_gets_a_reason(world):
    w = world
    w["gh"].state = ("failure", "FAILURE")
    code, log = run_export(w, make_plan(w), merge=True)
    assert code == 4 and w["gh"].merged == [] and "NOT MERGED" in log[-1]
    assert "not merged" in record(w)["hold"] and record(w)["pr"] == 7


def test_pending_checks_time_out_without_merging(world):
    w = world
    w["gh"].state = ("pending", "BLOCKED 3 checks")
    code, _ = run_export(w, make_plan(w), merge=True, wait_s=3, poll_s=1)
    assert code == 4 and w["gh"].merged == []


# ------------------------------------------------------------------------------------------- uncertain data: hold this export only
@pytest.mark.parametrize("name,content,code", [
    ("notes.txt", f"token = {FAKE_TOKEN}\n", "token"),
    ("config.txt", 'api_key = "abcdefghijklmnop1234"\n', "assigned_secret"),
    ("who.md", "contact someone@gmail.com\n", "personal_email"),
    ("paths.md", "see D:\\somewhere\\folder\\file.txt\n", "local_path"),
    ("key.pem", "x", "protected_name"),
    (".env", "A=1\n", "protected_name"),
    ("KEY_v1.json", "{}", "protected_name"),
    ("blind_labels.csv", "a,b\n", "protected_name"),
    ("transcript.jsonl", "{}\n", "protected_name"),
    ("run.db", "x", "protected_name"),
])
def test_uncertain_files_hold_the_export_and_nothing_is_pushed(world, name, content, code):
    w = world
    (w["out"] / name).write_text(content, encoding="utf-8")
    plan = make_plan(w)
    plan["publish"].append({"from": str(w["out"] / name), "to": f"data/lab/fake-1/{name}"})
    result, codes = problems(w, plan)
    assert result == "hold" and code in codes
    exit_code, log = run_export(w, plan, merge=True)
    assert exit_code == 3 and w["gh"].prs == {} and log[0].startswith("HELD")
    rec = record(w)
    assert code in rec["hold"] and rec["protected_check"]["result"] == "hold" and rec["hold_since"]
    assert FAKE_TOKEN not in json.dumps(rec) and FAKE_TOKEN not in (w["root"] / "private" / "exports" / "FAKE-1" / "protected-check.json").read_text(encoding="utf-8")
    ex.git(w["canonical"], "fetch", "-q", "origin")
    assert "claude/export-fake-1" not in ex.git(w["canonical"], "branch", "-r").stdout


def test_a_raw_run_file_is_never_published(world):
    w = world
    plan = make_plan(w)
    plan["publish"].append({"from": str(w["run"] / "sessions" / "s1.jsonl"), "to": "data/lab/fake-1/s1.jsonl"})
    result, codes = problems(w, plan)
    assert result == "hold" and "raw_run_file" in codes


def test_a_large_file_is_held(world):
    w = world
    big = w["out"] / "big.json"
    big.write_bytes(b"x" * (ex.MAX_FILE_BYTES + 1))
    plan = make_plan(w)
    plan["publish"].append({"from": str(big), "to": "data/lab/fake-1/big.json"})
    assert "too_large" in problems(w, plan)[1]


def test_the_content_scan_stays_linear_on_a_very_long_line(world):
    import time
    w = world
    long_line = w["out"] / "long.txt"
    long_line.write_bytes(b"x" * (ex.MAX_FILE_BYTES - 10))      # one 5 MB line without a newline or an '@': the shape that made a naive e-mail pattern quadratic
    plan = make_plan(w)
    plan["publish"].append({"from": str(long_line), "to": "data/lab/fake-1/long.txt"})
    started = time.monotonic()
    assert problems(w, plan) == ("withheld", set())
    assert time.monotonic() - started < 20


def test_an_address_is_found_and_only_its_domain_is_shown(world):
    w = world
    (w["out"] / "who.md").write_text("write to someone@gmail.com please\n", encoding="utf-8")
    plan = make_plan(w)
    plan["publish"].append({"from": str(w["out"] / "who.md"), "to": "data/lab/fake-1/who.md"})
    check = ex.check_plan(plan, lambda rel: False)
    detail = next(p["detail"] for p in check["problems"] if p["code"] == "personal_email")
    assert "someone" not in detail


def test_a_manifest_with_an_absolute_raw_root_is_held_because_new_manifests_are_relative(world):
    w = world
    (w["out"] / "raw-freeze.json").write_text(json.dumps({"raw_root": "/data/run", "files": {}}), encoding="utf-8")
    result, codes = problems(w, make_plan(w))
    assert result == "hold" and "absolute_manifest_path" in codes


def test_the_publication_needs_a_readme_that_opens_with_its_status(world):
    w = world
    (w["out"] / "README.md").write_text("# Title\n\nNo status line here.\n", encoding="utf-8")
    assert problems(w, make_plan(w))[1] == {"no_readme_status"}
    plan = make_plan(w)
    plan["publish"] = [e for e in plan["publish"] if not e["to"].endswith("README.md")]
    assert "no_readme_status" in problems(w, plan)[1]


def test_an_existing_path_is_never_overwritten_silently(world):
    w = world
    plan = make_plan(w)
    plan["publish"][1]["to"] = "docs/x.md"          # already on main
    assert "would_overwrite" in problems(w, plan)[1]
    plan["publish"][1]["update"] = True
    assert "would_overwrite" not in problems(w, plan)[1]


def test_targets_must_stay_inside_the_repository_folders(world):
    w = world
    for bad in ("../escape.md", "/abs.md", "C:/abs.md", "secrets/x.md"):
        plan = make_plan(w)
        plan["publish"][1]["to"] = bad
        assert "bad_target" in problems(w, plan)[1], bad


def test_a_file_that_is_not_frozen_can_have_its_paths_replaced_and_the_manifest_says_so(world):
    w = world
    (w["out"] / "REPORT.md").write_text("# Report\n\nrun folder `D:\\old\\layout\\run` and more\n", encoding="utf-8")
    assert "local_path" in problems(w, make_plan(w))[1]
    plan = make_plan(w, sanitize_paths=True)
    assert problems(w, plan) == ("withheld", set())
    code, _ = run_export(w, plan, merge=False)
    assert code == 0
    ex.git(w["canonical"], "fetch", "-q", "origin")
    report = ex.git(w["canonical"], "show", "origin/claude/export-fake-1:data/lab/fake-1/REPORT.md").stdout
    assert "D:" not in report and ex.PLACEHOLDER in report
    manifest = json.loads(ex.git(w["canonical"], "show", "origin/claude/export-fake-1:data/lab/fake-1/PUBLISHED_FILES.json").stdout)
    entry = next(p for p in manifest["published"] if p["target"].endswith("REPORT.md"))
    assert entry["edits"][0].startswith("replaced 1 machine-local path") and entry["sha256"] != entry["sha256_source"]


def test_a_frozen_file_with_local_paths_needs_an_erratum_in_the_same_publication(world):
    w = world
    (w["out"] / "frozen.json").write_text(json.dumps({"note": "D:\\old\\folder\\x"}), encoding="utf-8")
    plan = make_plan(w)
    plan["publish"].append({"from": str(w["out"] / "frozen.json"), "to": "data/lab/fake-1/frozen.json", "frozen": True})
    assert "local_path" in problems(w, plan)[1]
    plan["publish"][-1]["accept_local_paths"] = True
    assert "erratum_missing" in problems(w, plan)[1]
    (w["out"] / "ERRATUM.md").write_text("# Erratum\n\nthe frozen file records a machine path\n", encoding="utf-8")
    plan["publish"].append({"from": str(w["out"] / "ERRATUM.md"), "to": "data/lab/fake-1/ERRATUM.md"})
    assert problems(w, plan) == ("withheld", set())


def test_one_held_export_does_not_stop_the_next_one(world):
    w = world
    (w["out"] / "notes.txt").write_text(f"{FAKE_TOKEN}\n", encoding="utf-8")
    bad = make_plan(w)
    bad["publish"].append({"from": str(w["out"] / "notes.txt"), "to": "data/lab/fake-1/notes.txt"})
    assert run_export(w, bad, merge=True)[0] == 3
    good = make_plan(w, id="FAKE-2", branch="claude/export-fake-2")
    for e in good["publish"]:
        e["to"] = e["to"].replace("fake-1", "fake-2")
    assert run_export(w, good, merge=True)[0] == 0
    cfg = json.loads(w["config"].read_text(encoding="utf-8"))["exports"]
    assert "hold" in cfg["FAKE-1"] and cfg["FAKE-2"]["merged"] is True and "hold" not in cfg["FAKE-2"]


def test_the_export_record_feeds_the_daily_report(world):
    """held, in a pull request, and on main are all visible to scripts/aamr_sync_report.py through the record this tool writes."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import aamr_sync_report as sync
    w = world
    (w["out"] / "notes.txt").write_text(f"{FAKE_TOKEN}\n", encoding="utf-8")
    held = make_plan(w, id="HELD-1", branch="claude/export-held-1")
    held["publish"].append({"from": str(w["out"] / "notes.txt"), "to": "data/lab/fake-1/notes.txt"})
    assert run_export(w, held, merge=False)[0] == 3
    done = make_plan(w, id="DONE-1", branch="claude/export-done-1")
    for e in done["publish"]:
        e["to"] = e["to"].replace("fake-1", "done-1")
    assert run_export(w, done, merge=True)[0] == 0
    ex.git(w["canonical"], "fetch", "-q", "origin")
    marker = w["run"] / "DONE.json"
    exports = json.loads(w["config"].read_text(encoding="utf-8"))["exports"]
    tasks = [{"id": "HELD-1", "finished_marker": str(marker)}, {"id": "DONE-1", "finished_marker": str(marker)}]
    for task in tasks:        # what the report does itself when it loads the configuration: the record supplies the target and the hold
        record = exports[task["id"]]
        task["published_paths"] = list(record["targets"])
        if record.get("hold"):
            task["owner_hold"] = record["hold"]
    findings, rows = sync.review_tasks(tasks, w["canonical"], "origin/main")
    findings += sync.review_exports(tasks, rows, exports, True, 14, __import__("time").time())
    state = {r["id"]: r for r in rows}
    assert state["DONE-1"]["state"] == "on main" and "check withheld" in state["DONE-1"]["export"]
    assert state["HELD-1"]["state"].startswith("held by owner") and "hold since" in state["HELD-1"]["export"]
    assert any(f.code == "EXPORT_PROTECTED_CHECK_OPEN" and f.where == "HELD-1" for f in findings)
    assert not [f for f in findings if f.where == "DONE-1" and f.code.startswith("EXPORT_")]


def test_the_command_line_check_reports_a_hold_without_changing_anything(world, capsys):
    w = world
    (w["out"] / "notes.txt").write_text(f"{FAKE_TOKEN}\n", encoding="utf-8")
    plan = make_plan(w)
    plan["publish"].append({"from": str(w["out"] / "notes.txt"), "to": "data/lab/fake-1/notes.txt"})
    plan_file = w["tmp"] / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    assert ex.main(["check", str(plan_file)]) == 3
    out = capsys.readouterr().out
    assert '"result": "hold"' in out and FAKE_TOKEN not in out
    assert not w["config"].exists()


# ------------------------------------------------------------------------------------------- guards against a double publication
def lock_file(w) -> Path:
    return w["config"].parent / ex.LOCK_NAME


def test_a_second_export_of_a_confirmed_id_does_nothing(world):
    w = world
    assert run_export(w, make_plan(w), merge=True)[0] == 0 and len(w["gh"].prs) == 1
    code, log = run_export(w, make_plan(w), merge=True)
    assert code == 0 and log[0].startswith("ALREADY EXPORTED") and len(w["gh"].prs) == 1 and w["gh"].merged == [7]


def test_an_id_with_an_unmerged_pull_request_is_refused_not_duplicated(world):
    w = world
    assert run_export(w, make_plan(w), merge=False)[0] == 0
    code, log = run_export(w, make_plan(w), merge=False)
    assert code == ex.EXIT_BUSY and log[0].startswith("BUSY") and "#7" in log[0] and len(w["gh"].prs) == 1


def test_allow_reexport_overrides_the_refusal_with_a_new_branch(world):
    w = world
    assert run_export(w, make_plan(w), merge=False)[0] == 0
    again = make_plan(w, branch="claude/export-fake-1-again")
    code, _ = run_export(w, again, merge=False, allow_reexport=True)
    assert code == 0 and len(w["gh"].prs) == 2


def test_a_fresh_lock_stops_the_export_before_anything_happens(world):
    w = world
    lock_file(w).write_text('{"pid": 1, "task": "someone else"}', encoding="utf-8")
    code, log = run_export(w, make_plan(w), merge=True)
    assert code == ex.EXIT_BUSY and "another export" in log[0] and w["gh"].prs == {}
    assert lock_file(w).exists()                                       # not ours: left alone
    assert not (w["config"].exists() and "FAKE-1" in json.loads(w["config"].read_text(encoding="utf-8")).get("exports", {}))
    assert not (w["root"] / "work").exists() and not (w["root"] / "private" / "raw").exists()


def test_a_stale_lock_left_by_a_dead_run_is_replaced(world):
    w = world
    lock_file(w).write_text('{"pid": 1, "task": "dead"}', encoding="utf-8")
    old = __import__("time").time() - 3 * 3600
    os.utime(lock_file(w), (old, old))
    assert run_export(w, make_plan(w), merge=True)[0] == 0
    assert not lock_file(w).exists()


def test_the_lock_is_released_after_success_after_a_hold_and_after_a_failure(world):
    w = world
    assert run_export(w, make_plan(w), merge=True)[0] == 0 and not lock_file(w).exists()
    (w["out"] / "notes.txt").write_text(f"{FAKE_TOKEN}\n", encoding="utf-8")
    held = make_plan(w, id="FAKE-2", branch="claude/export-fake-2")
    held["publish"].append({"from": str(w["out"] / "notes.txt"), "to": "data/lab/fake-1/notes.txt"})
    assert run_export(w, held, merge=True)[0] == 3 and not lock_file(w).exists()
    w["gh"].state = ("failure", "FAILURE")
    failing = make_plan(w, id="FAKE-3", branch="claude/export-fake-3")
    for e in failing["publish"]:
        e["to"] = e["to"].replace("fake-1", "fake-3")
    assert run_export(w, failing, merge=True)[0] == 4 and not lock_file(w).exists()


def test_two_different_ids_one_after_the_other_both_go_out(world):
    w = world
    assert run_export(w, make_plan(w), merge=True)[0] == 0
    second = make_plan(w, id="FAKE-2", branch="claude/export-fake-2")
    for e in second["publish"]:
        e["to"] = e["to"].replace("fake-1", "fake-2")
    assert run_export(w, second, merge=True)[0] == 0 and w["gh"].merged == [7, 8]
