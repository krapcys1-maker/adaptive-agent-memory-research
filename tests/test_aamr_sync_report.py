"""Tests for scripts/aamr_sync_report.py on throw-away repositories (no network, no models)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import aamr_sync_report as sync  # noqa: E402

DAY = 86400


def g(cwd: Path, *args: str, when: float | None = None) -> str:
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid", GIT_TERMINAL_PROMPT="0",
               GIT_OPTIONAL_LOCKS="0")  # the helper itself must not refresh the index it observes
    if when is not None:
        stamp = f"{int(when)} +0000"
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def commit_file(repo: Path, rel: str, text: str, when: float | None = None) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    g(repo, "add", rel)
    g(repo, "commit", "-q", "-m", f"add {rel}", when=when)


@pytest.fixture()
def world(tmp_path: Path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
    g(work, "checkout", "-q", "-b", "main")
    commit_file(work, "docs/x.md", "published\n")
    commit_file(work, "README.md", "readme\n")
    g(work, "push", "-q", "-u", "origin", "main")
    return {"origin": origin, "work": work, "root": tmp_path}


def codes(findings, code=None):
    return [f for f in findings if code is None or f.code == code]


def review(repo: Path, **cfg):
    return sync.review_repository(repo, {"remote_main": "origin/main", **cfg}, time.time())


def test_secret_like_names():
    for name in (".env", ".env.bak-1", "x.env", "KEY_v1.json", "blind_labels_v1.csv", "my_secret.txt", "id_rsa", "a.pem"):
        assert sync.is_secret_name(name), name
    for name in ("README.md", "results.json", "tokenizer.py", "sealed_note_removed.txt"):
        assert not sync.is_secret_name(name), name


def test_unpushed_branch_is_an_alert_after_a_day_and_a_warning_before(world):
    work = world["work"]
    g(work, "checkout", "-q", "-b", "claude/old")
    commit_file(work, "docs/old.md", "x", when=time.time() - 3 * DAY)
    g(work, "checkout", "-q", "-b", "claude/new")
    commit_file(work, "docs/new.md", "y")
    g(work, "checkout", "-q", "main")
    found = {f.where.split("[")[-1].rstrip("]"): f for f in codes(review(work), "LOCAL_ONLY_BRANCH")}
    assert found["claude/old"].severity == sync.ALERT
    assert found["claude/new"].severity == sync.WARN


def test_allowed_local_branch_is_visible_but_not_an_alert(world):
    work = world["work"]
    g(work, "checkout", "-q", "-b", "claude/held")
    commit_file(work, "docs/held.md", "x", when=time.time() - 3 * DAY)
    g(work, "checkout", "-q", "main")
    cfg = {"local_only_allowed": [{"branch": "claude/held", "reason": "owner decision pending"}]}
    found = codes(review(work, **cfg), "LOCAL_ONLY_BRANCH")
    assert len(found) == 1 and found[0].severity == sync.INFO and "owner decision pending" in found[0].detail


def test_pushed_branch_then_merged_branch_disappears_from_the_report(world):
    work = world["work"]
    g(work, "checkout", "-q", "-b", "claude/topic")
    commit_file(work, "docs/topic.md", "z")
    g(work, "push", "-q", "-u", "origin", "claude/topic")
    g(work, "checkout", "-q", "main")
    findings = review(work)
    assert not codes(findings, "LOCAL_ONLY_BRANCH")
    assert [f.where for f in codes(findings, "PUSHED_NOT_MERGED")] == [f"{work} [claude/topic]"]
    g(work, "merge", "-q", "--no-ff", "-m", "merge", "claude/topic")
    g(work, "push", "-q", "origin", "main")
    findings = review(work)
    assert not codes(findings, "PUSHED_NOT_MERGED") and not codes(findings, "LOCAL_ONLY_BRANCH")


def test_squash_merged_branch_is_patch_equivalent_not_reported(world):
    work = world["work"]
    g(work, "checkout", "-q", "-b", "claude/sq")
    commit_file(work, "docs/sq.md", "s")
    g(work, "push", "-q", "-u", "origin", "claude/sq")
    g(work, "checkout", "-q", "main")
    g(work, "merge", "-q", "--squash", "claude/sq")
    g(work, "commit", "-q", "-m", "squash")
    g(work, "push", "-q", "origin", "main")
    assert not codes(review(work), "PUSHED_NOT_MERGED")


def test_cherry_picked_commits_are_recognised_by_patch_id(world):
    work, root = world["work"], world["root"]
    g(work, "checkout", "-q", "-b", "claude/local-copy")
    commit_file(work, "docs/same1.md", "one\n")
    commit_file(work, "docs/same2.md", "two\n")
    g(work, "checkout", "-q", "main")
    other = root / "other"
    subprocess.run(["git", "clone", "-q", str(world["origin"]), str(other)], check=True, capture_output=True)
    g(other, "checkout", "-q", "-b", "claude/remote-copy")
    commit_file(other, "docs/same1.md", "one\n", when=time.time() - 5000)  # the same change under another commit id
    g(other, "push", "-q", "-u", "origin", "claude/remote-copy")
    g(work, "fetch", "-q", "origin")
    only = [f for f in codes(review(work), "LOCAL_ONLY_BRANCH") if "claude/local-copy" in f.where]
    assert len(only) == 1 and "2 commit(s) not on any remote, 1 patch(es) with no copy" in only[0].detail
    commit_file(other, "docs/same2.md", "two\n", when=time.time() - 4000)
    g(other, "push", "-q", "origin", "claude/remote-copy")
    # the work clone has not fetched the second copy; the canonical clone's patch ids are passed in instead
    canonical_ids = set(sync.patch_ids(other, ["--remotes"], 800))
    found = sync.review_repository(work, {"remote_main": "origin/main"}, time.time(), canonical_ids)
    assert not [f for f in found if f.code == "LOCAL_ONLY_BRANCH" and "claude/local-copy" in f.where]
    copy = [f for f in found if f.code == "LOCAL_COPY_ON_GITHUB"]
    assert len(copy) == 1 and "every patch is there" in copy[0].detail


def test_dirty_and_untracked_files_are_compared_with_the_main_line(world):
    work = world["work"]
    (work / "README.md").write_text("changed\n", encoding="utf-8")
    g(work, "rm", "-q", "--cached", "docs/x.md")  # now untracked but identical to the main line
    (work / "docs" / "new.md").write_text("fresh\n", encoding="utf-8")
    (work / ".env").write_text("TOKEN=do-not-read\n", encoding="utf-8")
    findings = review(work)
    assert any(f.code == "DIRTY" for f in findings)
    untracked = codes(findings, "UNTRACKED")[0].detail
    assert "identical to the main line (1): docs/x.md" in untracked
    assert "not on the main line (1): docs/new.md" in untracked
    assert "secret-like name, not opened (1): .env" in untracked


def test_detached_head_with_orphan_commit_is_an_alert(world):
    work = world["work"]
    g(work, "checkout", "-q", "--detach")
    commit_file(work, "docs/orphan.md", "o")
    assert codes(review(work), "DETACHED_UNREACHABLE")[0].severity == sync.ALERT


def test_repository_without_remote(tmp_path):
    repo = tmp_path / "private-coord"
    repo.mkdir()
    g(repo, "init", "-q", "-b", "main")
    commit_file(repo, "a.txt", "a")
    assert codes(review(repo), "NO_REMOTE")[0].severity == sync.ALERT
    assert codes(review(repo, private_repos=["private-coord"]), "NO_REMOTE")[0].severity == sync.INFO


def test_missing_worktree_is_reported(world):
    work, root = world["work"], world["root"]
    wt = root / "wt-gone"
    g(work, "worktree", "add", "-q", "-b", "claude/wt", str(wt))
    shutil.rmtree(wt)
    assert codes(review(work), "STALE_WORKTREE_MISSING")


def test_merged_clean_worktree_is_only_a_removal_candidate(world):
    work, root = world["work"], world["root"]
    wt = root / "wt-merged"
    g(work, "worktree", "add", "-q", "-b", "claude/merged", str(wt))
    commit_file(wt, "docs/m.md", "m", when=time.time() - 30 * DAY)
    g(work, "merge", "-q", "--no-ff", "-m", "m", "claude/merged")
    g(work, "push", "-q", "origin", "main")
    found = codes(review(work), "STALE_WORKTREE_MERGED")
    assert found and found[0].severity == sync.INFO and "consent" in found[0].detail


def test_finished_tasks_not_on_github(world):
    work, root = world["work"], world["root"]
    done = root / "DONE.json"
    done.write_text("{}", encoding="utf-8")
    tasks = [
        {"id": "T-missing", "finished_marker": str(done), "published_path": "data/lab/t-missing/README.md"},
        {"id": "T-held", "finished_marker": str(done), "published_path": "data/lab/t-held/README.md", "owner_hold": "owner decision"},
        {"id": "T-live", "finished_marker": str(done), "published_path": "docs/x.md"},
        {"id": "T-running", "finished_marker": str(root / "no-such-file"), "published_path": "docs/none.md"},
        {"id": "T-notarget", "finished_marker": str(done)},
    ]
    g(work, "checkout", "-q", "-b", "claude/t-branch")
    commit_file(work, "data/lab/t-branch/README.md", "b")
    g(work, "push", "-q", "-u", "origin", "claude/t-branch")
    g(work, "checkout", "-q", "main")
    tasks.append({"id": "T-branch", "finished_marker": str(done), "published_path": "data/lab/t-branch/README.md"})
    findings, rows = sync.review_tasks(tasks, work, "origin/main")
    by_id = {f.where: f for f in findings}
    assert by_id["T-missing"].severity == sync.ALERT
    assert by_id["T-held"].severity == sync.INFO and "held" in by_id["T-held"].detail
    assert by_id["T-branch"].severity == sync.WARN
    assert by_id["T-notarget"].code == "FINISHED_NO_EXPORT_TARGET"
    assert "T-live" not in by_id and "T-running" not in by_id
    states = {r["id"]: r["state"] for r in rows}
    assert states["T-live"] == "on main" and states["T-running"] == "not finished"
    assert states["T-missing"] == "finished only locally"
    assert states["T-held"].startswith("held by owner")
    assert states["T-branch"] == "on a remote branch (PR status unknown)"
    assert states["T-notarget"] == "finished, no export target declared"


def test_four_states_are_told_apart(world):
    work, root = world["work"], world["root"]
    done = root / "DONE.json"
    done.write_text("{}", encoding="utf-8")
    g(work, "checkout", "-q", "-b", "claude/in-pr")
    commit_file(work, "data/lab/in-pr/README.md", "a")
    g(work, "push", "-q", "-u", "origin", "claude/in-pr")
    g(work, "checkout", "-q", "-b", "claude/no-pr", "main")
    commit_file(work, "data/lab/no-pr/README.md", "b")
    g(work, "push", "-q", "-u", "origin", "claude/no-pr")
    g(work, "checkout", "-q", "main")
    tasks = [{"id": name, "finished_marker": str(done), "published_path": f"data/lab/{name}/README.md"}
             for name in ("in-pr", "no-pr", "local", "docs")]
    tasks[-1]["published_path"] = "docs/x.md"
    tasks.append({"id": "held", "finished_marker": str(done), "published_path": "data/lab/held/README.md", "owner_hold": "owner"})
    findings, rows = sync.review_tasks(tasks, work, "origin/main", {"claude/in-pr": 77})
    states = {r["id"]: r["state"] for r in rows}
    assert states == {"in-pr": "in PR #77", "no-pr": "pushed, no open PR", "local": "finished only locally",
                      "docs": "on main", "held": "held by owner (owner)"}
    severity = {f.where: f.severity for f in findings}
    assert severity == {"in-pr": sync.INFO, "no-pr": sync.WARN, "local": sync.ALERT, "held": sync.INFO}


def write_fake_coordinator(root: Path) -> dict:
    """A fictional coordinator home: configuration with secrets, a database, an environment file, finished and running runs."""
    local_root = root / "lroot"
    (local_root / "GH" / "run1").mkdir(parents=True)
    (local_root / "GH" / "run1" / "DONE.json").write_text("{}", encoding="utf-8")
    out = local_root / "GH" / "wt" / "data" / "lab" / "fake-1"
    out.mkdir(parents=True)
    (out / "REPORT.md").write_text("report", encoding="utf-8")
    (out / "results.json").write_text("{}", encoding="utf-8")
    (local_root / "GH" / "run2").mkdir(parents=True)  # a running experiment: no DONE.json
    home = root / "coord"
    (home / "state").mkdir(parents=True)
    (home / "state" / "coordinator.db").write_bytes(b"SQLite format 3 SUPERSECRET-DB")
    (home / ".env").write_text("TOKEN=SUPERSECRET-ENV\n", encoding="utf-8")
    (home / "coordinator.toml").write_text(
        f'[paths]\nhome = "{home.as_posix()}"\nlocal_root = "{local_root.as_posix()}"\n'
        '[[experiments]]\nname = "FAKE-1"\nrun_dir = "GH/run1"\nout_dir = "GH/wt/data/lab/fake-1"\n'
        'required_outputs = ["REPORT.md", "results.json", "raw-freeze.json"]\n'
        '[agents.x]\napi_key = "SUPERSECRET-123"\n', encoding="utf-8")
    (home / "coordinator.local.toml").write_text(
        '[[experiments]]\nname = "FAKE-2"\nrun_dir = "GH/run2"\nout_dir = "GH/wt/data/lab/fake-2"\n'
        '[agents.y]\ntoken = "SUPERSECRET-456"\n', encoding="utf-8")
    missions = home / "reports" / "missions"
    missions.mkdir(parents=True)
    (missions / "M-PLAN.md").write_text("closed mission", encoding="utf-8")
    (missions / "M-MAPPED.md").write_text("closed mission", encoding="utf-8")
    return {"configs": [str(home / "coordinator.toml"), str(home / "coordinator.local.toml")],
            "missions_dir": str(missions), "mission_targets": {"M-MAPPED": "docs/mapped/README.md"}}


def test_coordinator_adapter_discovers_finished_work_without_listing_it_by_hand(world, monkeypatch):
    spec = write_fake_coordinator(world["root"])
    opened: list[str] = []
    real_open = open
    monkeypatch.setattr("builtins.open", lambda f, *a, **k: (opened.append(Path(str(f)).name), real_open(f, *a, **k))[1])
    tasks = {t["id"]: t for t in sync.discover_coordinator_tasks(spec, {})}
    assert set(tasks) == {"FAKE-1", "FAKE-2", "mission M-PLAN", "mission M-MAPPED"}
    assert tasks["FAKE-1"]["published_paths"] == ["data/lab/fake-1/REPORT.md", "data/lab/fake-1/results.json"]
    assert Path(tasks["FAKE-1"]["finished_marker"]).exists() and not Path(tasks["FAKE-2"]["finished_marker"]).exists()
    assert tasks["mission M-MAPPED"]["published_paths"] == ["docs/mapped/README.md"]
    assert "published_paths" not in tasks["mission M-PLAN"]
    assert sorted(set(opened)) == ["coordinator.local.toml", "coordinator.toml"]  # nothing else was opened


def test_coordinator_secrets_never_reach_the_report(world):
    spec = write_fake_coordinator(world["root"])
    cfg = {"canonical_repo": str(world["work"]), "remote_main": "origin/main", "coordinator": spec, "roots": [],
           "manifest_dir": str(world["root"] / "m")}
    findings, rows = sync.run_local(cfg, time.time(), update_manifests=False)
    text = sync.render(findings, rows, "Report", time.time()) + json.dumps([vars(f) for f in findings])
    assert "SUPERSECRET" not in text and "api_key" not in text
    states = {r["id"]: (r["source"], r["state"]) for r in rows}
    assert states["FAKE-1"] == ("coordinator experiment", "finished only locally")
    assert states["FAKE-2"] == ("coordinator experiment", "not finished")
    assert states["mission M-PLAN"] == ("coordinator mission", "finished, no export target declared")
    assert states["mission M-MAPPED"][1] == "finished only locally"
    assert any(f.code == "FINISHED_NO_EXPORT_TARGET" and f.where == "mission M-PLAN" for f in findings)


def test_coordinator_task_moves_from_local_to_pr_to_main(world):
    work, root = world["work"], world["root"]
    spec = write_fake_coordinator(root)
    cfg = {"canonical_repo": str(work), "remote_main": "origin/main", "coordinator": spec, "roots": [], "manifest_dir": str(root / "m")}

    def state(heads=None, fetch=False):
        _, rows = sync.run_local(cfg, time.time(), False, heads, fetch)
        return {r["id"]: r["state"] for r in rows}["FAKE-1"]

    assert state() == "finished only locally"
    other = root / "other"
    subprocess.run(["git", "clone", "-q", str(world["origin"]), str(other)], check=True, capture_output=True)
    g(other, "checkout", "-q", "-b", "claude/fake-1")
    commit_file(other, "data/lab/fake-1/REPORT.md", "report")
    commit_file(other, "data/lab/fake-1/results.json", "{}")
    g(other, "push", "-q", "-u", "origin", "claude/fake-1")
    assert state() == "finished only locally"  # the canonical clone has not fetched: stale on purpose
    assert state(fetch=True) == "on a remote branch (PR status unknown)"
    assert state({"claude/fake-1": 9}) == "in PR #9"
    assert state({"claude/other": 3}) == "pushed, no open PR"
    g(other, "checkout", "-q", "main")
    g(other, "merge", "-q", "--no-ff", "-m", "merge", "claude/fake-1")
    g(other, "push", "-q", "origin", "main")
    assert state(fetch=True) == "on main"


def test_override_marks_a_discovered_task_as_held(world):
    work, root = world["work"], world["root"]
    spec = write_fake_coordinator(root)
    cfg = {"canonical_repo": str(work), "remote_main": "origin/main", "coordinator": spec, "roots": [],
           "manifest_dir": str(root / "m"), "task_overrides": {"FAKE-1": {"owner_hold": "owner decision"}}}
    findings, rows = sync.run_local(cfg, time.time(), False)
    assert {r["id"]: r["state"] for r in rows}["FAKE-1"] == "held by owner (owner decision)"
    assert not [f for f in findings if f.where == "FAKE-1" and f.severity == sync.ALERT]


def test_non_git_folder_tracks_changes_and_never_hashes_secrets(tmp_path, monkeypatch):
    folder = tmp_path / "loose"
    (folder / "sealed").mkdir(parents=True)
    (folder / "sealed" / "a.txt").write_text("secret-a", encoding="utf-8")
    (folder / ".env").write_text("K=v", encoding="utf-8")
    (folder / "KEY_v1.json").write_text("{}", encoding="utf-8")
    (folder / "blind_labels_v1.csv").write_text("x", encoding="utf-8")
    (folder / "notes.txt").write_text("hello", encoding="utf-8")
    hashed: list[str] = []
    real = sync.hash_file
    monkeypatch.setattr(sync, "hash_file", lambda p: hashed.append(Path(p).name) or real(p))
    manifests = tmp_path / "manifests"
    entry = {"path": str(folder), "label": "loose"}

    first = sync.review_non_git(entry, manifests, update=True)
    assert [f.code for f in first if f.code == "NON_GIT_BASELINE"]
    assert hashed == ["notes.txt"]
    secret_note = codes(first, "SECRET_LIKE_PRESENT")[0].detail
    for name in (".env", "KEY_v1.json", "blind_labels_v1.csv", "sealed/"):
        assert name in secret_note

    assert not codes(sync.review_non_git(entry, manifests, update=False), "NON_GIT_CHANGED")
    time.sleep(0.01)
    (folder / "new_result.md").write_text("new", encoding="utf-8")
    changed = codes(sync.review_non_git(entry, manifests, update=False), "NON_GIT_CHANGED")
    assert changed and "new_result.md" in changed[0].detail
    assert hashed == ["notes.txt"]  # reporting alone hashed nothing and wrote no manifest


def test_report_run_does_not_touch_scanned_repositories(world):
    work, root = world["work"], world["root"]
    (work / "docs" / "scratch.md").write_text("u", encoding="utf-8")
    before = (g(work, "status", "--porcelain"), (work / ".git" / "index").stat().st_mtime_ns,
              sorted(p.name for p in (work / ".git").iterdir()))
    cfg = {"roots": [str(root)], "repos_depth": 2, "remote_main": "origin/main", "manifest_dir": str(root / "m")}
    findings, _ = sync.run_local(cfg, time.time(), update_manifests=False)
    after = (g(work, "status", "--porcelain"), (work / ".git" / "index").stat().st_mtime_ns,
             sorted(p.name for p in (work / ".git").iterdir()))
    assert before == after
    assert codes(findings, "UNTRACKED")


def test_repositories_are_found_once_even_with_worktrees(world):
    work, root = world["work"], world["root"]
    g(work, "worktree", "add", "-q", "-b", "claude/second", str(root / "second-checkout"))
    found = sync.find_repositories([str(root)], 2)
    assert [p.resolve() for p in found if p.name == "work"] == [work.resolve()]
    assert len([p for p in found if p.name == "second-checkout"]) == 0


# ---- GitHub section -------------------------------------------------------------------------

NOW = time.time()


def iso(days_ago: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - days_ago * DAY))


def test_pull_request_review():
    prs = [
        {"number": 1, "title": "failing", "updatedAt": iso(1), "mergeStateStatus": "BLOCKED", "body": "Closes #5",
         "statusCheckRollup": [{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]},
        {"number": 2, "title": "old", "updatedAt": iso(20), "mergeStateStatus": "DIRTY", "body": "no link",
         "statusCheckRollup": [{"conclusion": "SUCCESS"}]},
        {"number": 3, "title": "running", "updatedAt": iso(0.1), "mergeStateStatus": "CLEAN", "body": "see #4",
         "statusCheckRollup": [{"status": "IN_PROGRESS", "conclusion": ""}]},
    ]
    found = {(f.where, f.code): f.severity for f in sync.review_prs(prs, NOW)}
    assert found[("PR #1", "PR_CI_FAILING")] == sync.ALERT
    assert found[("PR #2", "PR_STALE")] == sync.WARN and found[("PR #2", "PR_NOT_CLEAN")] == sync.WARN
    assert found[("PR #2", "PR_NO_ISSUE_LINK")] == sync.INFO
    assert found[("PR #3", "PR_CI_PENDING")] == sync.INFO
    assert ("PR #1", "PR_NO_ISSUE_LINK") not in found


def test_issue_review():
    issues = [
        {"number": 10, "updatedAt": iso(1), "body": "Acceptance: a test passes", "comments": []},
        {"number": 11, "updatedAt": iso(90), "body": "just an idea", "comments": []},
        {"number": 12, "updatedAt": iso(90), "body": "- [ ] item", "comments": [{"id": 1}]},
    ]
    merged = [{"number": 99, "closingIssuesReferences": [{"number": 10}]}]
    found = {(f.where, f.code) for f in sync.review_issues(issues, merged, NOW)}
    assert ("Issue #10", "ISSUE_RESOLVED_BUT_OPEN") in found
    assert ("Issue #11", "ISSUE_NO_ACCEPTANCE") in found and ("Issue #11", "ISSUE_STALE") in found
    assert ("Issue #12", "ISSUE_STALE") not in found and ("Issue #12", "ISSUE_NO_ACCEPTANCE") not in found


def test_branch_and_experiment_review(world):
    work = world["work"]
    g(work, "checkout", "-q", "-b", "claude/merged-one")
    commit_file(work, "data/lab/exp-a/README.md", "a")
    commit_file(work, "data/lab/exp-b/result.json", "{}")
    (work / "docs" / "11-research-laboratory").mkdir(parents=True)
    commit_file(work, "docs/11-research-laboratory/lab-map.md", "exp-a is listed here\n")
    g(work, "push", "-q", "-u", "origin", "claude/merged-one")
    g(work, "checkout", "-q", "main")
    g(work, "merge", "-q", "--no-ff", "-m", "m", "claude/merged-one")
    g(work, "push", "-q", "origin", "main")
    g(work, "checkout", "-q", "-b", "claude/ancient")
    commit_file(work, "docs/ancient.md", "x", when=time.time() - 40 * DAY)
    g(work, "push", "-q", "-u", "origin", "claude/ancient")
    g(work, "checkout", "-q", "main")
    branch_findings = {f.code: f for f in sync.review_branches(work, "origin/main", time.time())}
    assert "BRANCH_MERGED_UNDELETED" in branch_findings
    assert branch_findings["BRANCH_MERGED_UNDELETED"].detail.startswith("1 remote branch")  # claude/merged-one only: origin/HEAD and main are not counted
    assert branch_findings["BRANCH_UNMERGED_OLD"].where.endswith("claude/ancient")
    experiments = {f.code: f.detail for f in sync.review_experiments(work)}
    assert "exp-b" in experiments["EXPERIMENT_NO_README"] and "exp-a" not in experiments["EXPERIMENT_NO_README"]
    assert "exp-b" in experiments["EXPERIMENT_NOT_INDEXED"] and "exp-a" not in experiments["EXPERIMENT_NOT_INDEXED"]


# ---- Rendering and command line -------------------------------------------------------------

def test_exit_codes_and_rendering():
    assert sync.exit_code([]) == 0
    assert sync.exit_code([sync.Finding(sync.INFO, "X", "w", "d")]) == 0
    assert sync.exit_code([sync.Finding(sync.WARN, "X", "w", "d")]) == 1
    assert sync.exit_code([sync.Finding(sync.WARN, "X", "w", "d"), sync.Finding(sync.ALERT, "Y", "w", "d")]) == 2
    text = sync.render([sync.Finding(sync.ALERT, "FINISHED_NOT_PUBLISHED", "T-1", "detail")],
                       [{"id": "T-1", "source": "coordinator experiment", "state": "finished only locally"}], "Report", NOW)
    assert "## Tasks and their results on GitHub" in text
    assert "| T-1 | coordinator experiment | finished only locally |" in text
    assert "## ALERT (1)" in text


def test_command_line_github_section_from_a_file(world, tmp_path, capsys):
    snapshot = tmp_path / "snap.json"
    snapshot.write_text(json.dumps({"prs": [], "issues": [], "merged_prs": []}), encoding="utf-8")
    out = tmp_path / "reports"
    code = sync.main(["github", "--input-json", str(snapshot), "--tree", str(world["work"]), "--out", str(out)])
    assert code in (0, 1)
    assert list(out.glob("*-github.md"))
    assert "GitHub review" in capsys.readouterr().out


def test_command_line_local_needs_a_config(capsys):
    with pytest.raises(SystemExit):
        sync.main(["local"])


# --------------------------------------------------------------------------------------------------------------------
# Export records: target, protected-data check, branch or pull request, hold (fictional tasks only)
# --------------------------------------------------------------------------------------------------------------------
CHECK = {"checked_on": "2026-11-14", "result": "clean", "withheld": [], "by": "agent"}


def export_run(work: Path, root: Path, tasks: list[dict], exports: dict, require=False, hold_max_days=14.0, now=None):
    now = now or time.time()
    findings, rows = sync.review_tasks(tasks, work, "origin/main")
    findings += sync.review_exports(tasks, rows, exports, require, hold_max_days, now)
    return findings, {r["id"]: r for r in rows}


def finished(root: Path, name: str, path: str | None = None) -> dict:
    done = root / "DONE.json"
    done.write_text("{}", encoding="utf-8")
    task = {"id": name, "finished_marker": str(done)}
    if path:
        task["published_path"] = path
    return task


def codes_of(findings, name):
    return sorted((f.code, f.severity) for f in findings if f.where == name and f.code.startswith("EXPORT_"))


def test_export_record_complete_and_on_main_is_quiet_and_shown_in_the_table(world):
    work, root = world["work"], world["root"]
    tasks = [finished(root, "T-ok", "docs/x.md")]
    findings, rows = export_run(work, root, tasks, {"T-ok": {"protected_check": CHECK, "pr": 12}})
    assert codes_of(findings, "T-ok") == []
    assert rows["T-ok"]["export"] == "check clean 2026-11-14; PR #12"
    text = sync.render(findings, list(rows.values()), "R", time.time())
    assert "| Task | Source | State | Export record |" in text and "check clean 2026-11-14; PR #12" in text


def test_a_finished_task_without_a_protected_check_is_a_warning_before_export_and_a_note_after(world):
    work, root = world["work"], world["root"]
    tasks = [finished(root, "T-local", "data/lab/t-local/README.md"), finished(root, "T-main", "docs/x.md")]
    exports = {"T-local": {"targets": ["data/lab/t-local/README.md"]}, "T-main": {}}
    findings, rows = export_run(work, root, tasks, exports)
    assert codes_of(findings, "T-local") == [("EXPORT_NO_PROTECTED_CHECK", sync.WARN)]
    assert codes_of(findings, "T-main") == [("EXPORT_NO_PROTECTED_CHECK", sync.INFO)]
    assert rows["T-local"]["export"] == "check missing"


def test_the_protected_check_must_have_a_known_result_and_list_what_is_withheld(world):
    work, root = world["work"], world["root"]
    tasks = [finished(root, "T-open", "docs/x.md"), finished(root, "T-vague", "docs/x.md"), finished(root, "T-good", "docs/x.md")]
    exports = {"T-open": {"protected_check": {**CHECK, "result": "maybe"}},
               "T-vague": {"protected_check": {**CHECK, "result": "withheld", "withheld": []}},
               "T-good": {"protected_check": {**CHECK, "result": "withheld", "withheld": ["raw run (326 MB), hashes published"]}}}
    findings, rows = export_run(work, root, tasks, exports)
    assert codes_of(findings, "T-open") == [("EXPORT_PROTECTED_CHECK_OPEN", sync.WARN)]
    assert codes_of(findings, "T-vague") == [("EXPORT_PROTECTED_CHECK_INCOMPLETE", sync.WARN)]
    assert codes_of(findings, "T-good") == []
    assert rows["T-good"]["export"].startswith("check withheld")


def test_a_record_that_names_a_branch_nobody_pushed_is_an_alert(world):
    work, root = world["work"], world["root"]
    tasks = [finished(root, "T-nobranch", "data/lab/t-nobranch/README.md")]
    findings, _ = export_run(work, root, tasks, {"T-nobranch": {"protected_check": CHECK, "branch": "claude/t-nobranch"}})
    assert ("EXPORT_BRANCH_MISSING", sync.ALERT) in codes_of(findings, "T-nobranch")
    assert any(f.code == "FINISHED_NOT_PUBLISHED" and f.severity == sync.ALERT for f in findings)


def test_a_hold_goes_stale_and_needs_a_date(world):
    work, root = world["work"], world["root"]
    now = time.mktime((2026, 11, 14, 12, 0, 0, 0, 0, 0))
    tasks = [finished(root, n, f"data/lab/{n}/README.md") for n in ("T-fresh", "T-old", "T-nodate", "T-baddate")]
    exports = {"T-fresh": {"protected_check": CHECK, "hold": "owner decision", "hold_since": "2026-11-12"},
               "T-old": {"protected_check": CHECK, "hold": "owner decision", "hold_since": "2026-09-01"},
               "T-nodate": {"protected_check": CHECK, "hold": "owner decision"},
               "T-baddate": {"protected_check": CHECK, "hold": "owner decision", "hold_since": "yesterday"}}
    findings, rows = export_run(work, root, tasks, exports, now=now)
    assert codes_of(findings, "T-fresh") == []
    assert codes_of(findings, "T-old") == [("EXPORT_HOLD_STALE", sync.WARN)]
    assert codes_of(findings, "T-nodate") == [("EXPORT_HOLD_STALE", sync.WARN)]
    assert codes_of(findings, "T-baddate") == [("EXPORT_HOLD_STALE", sync.WARN)]
    assert rows["T-fresh"]["export"].endswith("hold since 2026-11-12")


def test_require_export_record_flags_finished_tasks_without_one_and_ignores_running_ones(world):
    work, root = world["work"], world["root"]
    tasks = [finished(root, "T-none-local", "data/lab/x/README.md"), finished(root, "T-none-main", "docs/x.md"),
             {"id": "T-running", "finished_marker": str(root / "no-such-marker")}]
    exports = {"T-ghost": {"protected_check": CHECK}}
    findings, _ = export_run(work, root, tasks, exports, require=True)
    assert codes_of(findings, "T-none-local") == [("EXPORT_NO_RECORD", sync.WARN)]
    assert codes_of(findings, "T-none-main") == [("EXPORT_NO_RECORD", sync.INFO)]
    assert codes_of(findings, "T-running") == []
    assert codes_of(findings, "T-ghost") == [("EXPORT_RECORD_UNKNOWN_TASK", sync.INFO)]
    off, _ = export_run(work, root, tasks, {}, require=False)
    assert not [f for f in off if f.code.startswith("EXPORT_")]


def test_run_local_takes_the_target_and_the_hold_from_the_export_record_of_a_coordinator_mission(world):
    work, root = world["work"], world["root"]
    spec = write_fake_coordinator(root)
    cfg = {"canonical_repo": str(work), "remote_main": "origin/main", "coordinator": spec, "roots": [],
           "manifest_dir": str(root / "m"), "require_export_record": True,
           "exports": {"mission M-PLAN": {"targets": ["docs/x.md"], "protected_check": CHECK, "pr": 3},
                       "FAKE-1": {"protected_check": CHECK, "hold": "owner decision", "hold_since": "2999-01-01"}}}
    findings, rows = sync.run_local(cfg, time.time(), False)
    states = {r["id"]: r for r in rows}
    assert states["mission M-PLAN"]["state"] == "on main"      # the target came from the record, not from the coordinator
    assert states["mission M-PLAN"]["export"] == "check clean 2026-11-14; PR #3"
    assert states["FAKE-1"]["state"].startswith("held by owner")
    assert ("EXPORT_NO_RECORD", sync.WARN) in codes_of(findings, "mission M-MAPPED")
    assert codes_of(findings, "FAKE-1") == []


def test_export_records_and_the_report_never_open_the_coordinator_database(world, monkeypatch):
    work, root = world["work"], world["root"]
    spec = write_fake_coordinator(root)
    opened = []
    real_open = open

    def spy(path, *args, **kwargs):
        opened.append(str(path))
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", spy)
    cfg = {"canonical_repo": str(work), "remote_main": "origin/main", "coordinator": spec, "roots": [],
           "manifest_dir": str(root / "m"), "exports": {"FAKE-1": {"protected_check": CHECK}}}
    findings, rows = sync.run_local(cfg, time.time(), False)
    text = sync.render(findings, rows, "R", time.time())
    assert not [p for p in opened if p.endswith((".db", ".env"))]
    assert "SUPERSECRET" not in text


def test_all_uses_the_repository_named_in_the_configuration_for_the_github_section(world, tmp_path, monkeypatch, capsys):
    """`all` read the repository from the configuration for the local section but demanded --repo for the GitHub section."""
    seen = []

    def fake_fetch(repo):
        seen.append(repo)
        return {"prs": [], "issues": [], "merged_prs": []}

    monkeypatch.setattr(sync, "fetch_github", fake_fetch)
    monkeypatch.setattr(sync, "open_pr_heads_from_github", lambda repo: {})
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"canonical_repo": str(world["work"]), "remote_main": "origin/main", "roots": [],
                               "repo": "owner/name", "manifest_dir": str(tmp_path / "m")}), encoding="utf-8")
    code = sync.main(["all", "--config", str(cfg)])
    assert seen == ["owner/name"]
    assert code in (0, 1)
    capsys.readouterr()
    cfg.write_text(json.dumps({"canonical_repo": str(world["work"]), "remote_main": "origin/main", "roots": [],
                               "manifest_dir": str(tmp_path / "m")}), encoding="utf-8")
    with pytest.raises(SystemExit):
        sync.main(["all", "--config", str(cfg)])      # without a repository anywhere it still stops with a usage error
