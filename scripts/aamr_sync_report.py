#!/usr/bin/env python3
"""Daily synchronisation report: is the work on this machine also on GitHub?

The project has one source of truth, the GitHub repository. Agents and people also work in
local clones, worktrees, and folders outside Git. This report lists every place where work
exists only locally, so that nothing valuable stays on one disk without being visible.

It is read-only. It never writes into a scanned repository or folder (the one opt-in exception is
``--fetch-canonical``, which refreshes the remote-tracking refs of the canonical clone), never
opens a file whose name looks like a secret, a blinding key, or sealed data (such files are
listed by name only), and needs no network, paid API, or model. The GitHub section reads
through ``gh`` with list/GET commands only, or from a JSON file, so it can be tested offline.

Local findings
    LOCAL_ONLY_BRANCH        commits on a local branch that no remote-tracking ref contains and whose
                             patches have no copy on GitHub (compared by stable patch id)
    LOCAL_COPY_ON_GITHUB     commits with other ids on GitHub (cherry-picked or rebased): nothing is missing
    PUSHED_NOT_MERGED        branch is on the remote but not in the main line
    DETACHED_UNREACHABLE     detached HEAD with commits no branch or remote contains
    NO_REMOTE                repository without any remote (needs a backup instead)
    DIRTY / UNTRACKED        uncommitted work; untracked files are compared with the main line
    STASH                    stash entries
    STALE_WORKTREE_MISSING   a registered worktree whose folder is gone
    STALE_WORKTREE_MERGED    clean worktree of a branch already in the main line (candidate)
    BEHIND_MAIN              a main checkout far behind the remote main line
    NON_GIT_CHANGED          files in a folder outside Git that are new or changed
    FINISHED_NOT_PUBLISHED   a task that is done locally whose result is not on the main line
    FINISHED_IN_PR           a finished result that waits in an open pull request
    FINISHED_NO_EXPORT_TARGET  a finished task with no declared place for its result in the repository

GitHub findings
    PR_CI_FAILING / PR_CI_PENDING / PR_NOT_CLEAN / PR_STALE / PR_NO_ISSUE_LINK
    ISSUE_RESOLVED_BUT_OPEN / ISSUE_NO_ACCEPTANCE / ISSUE_STALE
    BRANCH_MERGED_UNDELETED / BRANCH_UNMERGED_OLD
    EXPERIMENT_NO_README / EXPERIMENT_NOT_INDEXED

Usage::

    python scripts/aamr_sync_report.py local  --config sync.local.json --out reports/
    python scripts/aamr_sync_report.py github --repo OWNER/NAME --tree PATH_TO_CLONE
    python scripts/aamr_sync_report.py github --input-json snapshot.json --tree PATH_TO_CLONE
    python scripts/aamr_sync_report.py all    --config sync.local.json --repo OWNER/NAME

The configuration file holds local paths and therefore stays out of the repository
(``sync.local.json`` is ignored by Git); see
``docs/00-project/aamr-sync-config.example.json``. The reports name local paths too:
write them to a folder that Git ignores (``sync-reports/``) and do not publish them.

Exit code: 0 nothing to report, 1 warnings, 2 alerts.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ALERT, WARN, INFO = "ALERT", "WARN", "INFO"
SEVERITY_ORDER = {ALERT: 0, WARN: 1, INFO: 2}

# A name that matches is listed but never opened or hashed.
SECRET_NAME_PATTERNS = (
    ".env", ".env.*", "*.env", "*.key", "*.pem", "*.p12", "id_rsa*", "*secret*", "*credential*",
    "*password*", "*api_key*", "*apikey*", "key_*", "blind_*",
)
# A directory with this name is listed but never entered.
SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache", "sealed", "blind"}
RESEARCH_PREFIXES = ("docs/", "data/", "scripts/", "tests/", "tools/", "memory/")
MAX_HASH_BYTES = 64 * 1024 * 1024


@dataclass
class Finding:
    severity: str
    code: str
    where: str
    detail: str


def is_secret_name(name: str) -> bool:
    lowered = name.lower()
    return any(fnmatch.fnmatch(lowered, pattern) for pattern in SECRET_NAME_PATTERNS)


# ---------------------------------------------------------------------------------------------
# Git helpers (read-only)
# ---------------------------------------------------------------------------------------------

def git(repo: Path | str, *args: str) -> tuple[int, str]:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    try:
        proc = subprocess.run(
            ["git", "--no-optional-locks", "-c", "core.quotepath=off", "-C", str(repo), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 99, str(exc)
    return proc.returncode, proc.stdout.strip("\n")


def find_repositories(roots: Iterable[str], depth: int) -> list[Path]:
    """Folders that contain a ``.git`` entry, one per repository (linked worktrees share one)."""
    seen: dict[str, Path] = {}

    def walk(path: Path, remaining: int) -> None:
        if (path / ".git").exists():
            code, common = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
            key = os.path.normcase(common) if code == 0 and common else os.path.normcase(str(path))
            primary = Path(common).parent if code == 0 and common and Path(common).name == ".git" else path
            seen.setdefault(key, primary if primary.exists() else path)
            return
        if remaining == 0:
            return
        try:
            children = sorted(p for p in path.iterdir() if p.is_dir() and p.name not in SKIP_DIR_NAMES)
        except OSError:
            return
        for child in children:
            walk(child, remaining - 1)

    for root in roots:
        base = Path(root)
        if base.is_dir():
            walk(base, depth)
    return sorted(seen.values())


def list_worktrees(repo: Path) -> list[dict[str, str]]:
    code, out = git(repo, "worktree", "list", "--porcelain")
    items: list[dict[str, str]] = []
    current: dict[str, str] = {}
    if code != 0:
        return items
    for line in out.splitlines() + [""]:
        if not line.strip():
            if current:
                items.append(current)
            current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value or "true"
    return items


def patch_ids(repo: Path | str, revs: list[str], limit: int | None = None) -> dict[str, str]:
    """Stable patch id -> commit id for the non-merge commits selected by ``revs``.

    Two commits with the same patch id carry the same change, so a commit that was cherry-picked or rebased
    onto another line is recognised even though its commit id differs.
    """
    log = ["git", "--no-optional-locks", "-C", str(repo), "log", "-p", "--no-merges", "--format=commit %H"]
    if limit:
        log += ["-n", str(limit)]
    try:
        first = subprocess.run(log + revs, capture_output=True, timeout=300)
        second = subprocess.run(["git", "patch-id", "--stable"], input=first.stdout, capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    ids: dict[str, str] = {}
    for line in second.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) == 2:
            ids[parts[0]] = parts[1]
    return ids


def ref_exists(repo: Path, ref: str) -> bool:
    return git(repo, "rev-parse", "--verify", "-q", ref)[0] == 0


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    return git(repo, "merge-base", "--is-ancestor", ancestor, descendant)[0] == 0


def path_in_ref(repo: Path, ref: str, relpath: str) -> bool:
    return git(repo, "cat-file", "-e", f"{ref}:{relpath}")[0] == 0


# ---------------------------------------------------------------------------------------------
# Local repositories
# ---------------------------------------------------------------------------------------------

def review_repository(repo: Path, cfg: dict[str, Any], now: float,
                      known_patch_ids: set[str] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    label = str(repo)
    main_ref = cfg.get("remote_main", "origin/main")
    local_only_hours = float(cfg.get("local_only_hours", 24))
    stale_days = float(cfg.get("stale_worktree_days", 14))
    behind_limit = int(cfg.get("behind_threshold", 20))
    allowed_local = {entry["branch"]: entry.get("reason", "") for entry in cfg.get("local_only_allowed", [])}
    private_repos = [p.lower() for p in cfg.get("private_repos", [])]

    _, remotes = git(repo, "remote")
    has_remote = bool(remotes.strip())
    has_main = has_remote and ref_exists(repo, main_ref)

    if not has_remote:
        private = any(p in label.lower().replace("\\", "/") for p in private_repos)
        findings.append(Finding(
            INFO if private else ALERT, "NO_REMOTE", label,
            "repository has no remote; all its branches exist only on this disk"
            + (" (declared private: it needs a verified backup)" if private else "")))
    else:
        common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")[1])
        stamps = [(common / name).stat().st_mtime for name in ("FETCH_HEAD", "packed-refs") if (common / name).exists()]
        age_days = (now - max(stamps)) / 86400 if stamps else None
        if age_days is None or age_days > float(cfg.get("fetch_stale_days", 7)):
            findings.append(Finding(
                INFO, "REMOTE_REFS_STALE", label,
                "remote-tracking refs were not refreshed recently; branch states below are conservative"))

    _, refs = git(repo, "for-each-ref", "--format=%(refname:short)|%(committerdate:unix)", "refs/heads")
    branch_tips: dict[str, float] = {}
    for line in refs.splitlines():
        name, _, stamp = line.rpartition("|")
        branch_tips[name] = float(stamp or 0)

    if has_remote:
        known: set[str] | None = None
        for name, stamp in sorted(branch_tips.items()):
            _, count = git(repo, "rev-list", "--count", name, "--not", "--remotes")
            unpublished = int(count or 0)
            if unpublished:
                age_hours = (now - stamp) / 3600
                if known is None:  # patches that exist on a remote: this repository's remotes and the canonical clone's
                    known = set(patch_ids(repo, ["--remotes"], 800)) | (known_patch_ids or set())
                mine = patch_ids(repo, [name, "--not", "--remotes"])
                missing = [c for pid, c in mine.items() if pid not in known] if mine else [None] * unpublished
                where = f"{label} [{name}]"
                if name in allowed_local:
                    findings.append(Finding(
                        INFO, "LOCAL_ONLY_BRANCH", where,
                        f"{unpublished} commit(s) not on any remote under their own ids, {len(missing)} patch(es) "
                        f"with no copy on GitHub; held on purpose: {allowed_local[name]}"))
                elif not missing:
                    findings.append(Finding(
                        INFO, "LOCAL_COPY_ON_GITHUB", where,
                        f"{unpublished} commit(s) have other ids on GitHub (cherry-picked or rebased): every patch is there"))
                else:
                    findings.append(Finding(
                        ALERT if age_hours > local_only_hours else WARN, "LOCAL_ONLY_BRANCH", where,
                        f"{unpublished} commit(s) not on any remote, {len(missing)} patch(es) with no copy on GitHub; "
                        f"tip is {age_hours / 24:.1f} days old"))
            elif has_main and not is_ancestor(repo, name, main_ref):
                _, cherry = git(repo, "cherry", main_ref, name)
                unique = sum(1 for row in cherry.splitlines() if row.startswith("+"))
                if unique:
                    findings.append(Finding(INFO, "PUSHED_NOT_MERGED", f"{label} [{name}]",
                                            f"on the remote, {unique} patch(es) not in {main_ref}"))

    for wt in list_worktrees(repo):
        path = Path(wt.get("worktree", ""))
        branch = wt.get("branch", "").replace("refs/heads/", "")
        if not path.exists():
            findings.append(Finding(WARN, "STALE_WORKTREE_MISSING", str(path),
                                    "registered worktree whose folder no longer exists (git worktree prune)"))
            continue
        detached = "detached" in wt
        if detached:
            _, orphan = git(path, "rev-list", "--count", "HEAD", "--not", "--branches", "--remotes")
            if int(orphan or 0):
                findings.append(Finding(ALERT, "DETACHED_UNREACHABLE", str(path),
                                        f"detached HEAD carries {orphan} commit(s) no branch or remote contains"))
        _, status = git(path, "status", "--porcelain=v1", "-unormal")
        rows = [row for row in status.splitlines() if row.strip()]
        tracked = [row for row in rows if not row.startswith("??")]
        untracked = [row[3:] for row in rows if row.startswith("??")]
        if tracked:
            findings.append(Finding(WARN, "DIRTY", str(path),
                                    f"{len(tracked)} modified/staged path(s): " + ", ".join(r[3:] for r in tracked[:8])))
        if untracked:
            findings.append(Finding(WARN, "UNTRACKED", str(path), compare_untracked(path, untracked, main_ref, has_main)))
        if branch == main_ref.split("/", 1)[-1] and has_main:
            _, behind = git(path, "rev-list", "--count", f"HEAD..{main_ref}")
            if int(behind or 0) > behind_limit:
                findings.append(Finding(WARN, "BEHIND_MAIN", str(path),
                                        f"checkout is {behind} commit(s) behind {main_ref}"))
        if branch and has_main and not tracked and not untracked and branch != main_ref.split("/", 1)[-1]:
            tip_age = (now - branch_tips.get(branch, now)) / 86400
            if is_ancestor(repo, branch, main_ref) and tip_age > stale_days:
                findings.append(Finding(INFO, "STALE_WORKTREE_MERGED", str(path),
                                        f"branch {branch} is fully in {main_ref}, clean, tip {tip_age:.0f} days old: "
                                        "a removal candidate (needs the owner's consent)"))

    _, stash = git(repo, "stash", "list")
    if stash.strip():
        findings.append(Finding(WARN, "STASH", label, f"{len(stash.splitlines())} stash entr(y/ies)"))
    return findings


def expand_untracked(worktree: Path, entries: list[str], limit: int = 300) -> list[str]:
    """Turn ``dir/`` entries of ``git status`` into file paths (secret-like folders are not entered)."""
    files: list[str] = []
    for entry in entries:
        name = entry.strip().strip('"')
        if not name.endswith("/"):
            files.append(name)
            continue
        for current, dirs, names in os.walk(worktree / name):
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES and not is_secret_name(d)]
            files.extend((Path(current) / n).relative_to(worktree).as_posix() for n in names)
            if len(files) >= limit:
                return files[:limit]
    return files[:limit]


def compare_untracked(worktree: Path, entries: list[str], main_ref: str, has_main: bool) -> str:
    """Describe untracked files by comparing each with the main line; secret-like names are never opened."""
    groups: dict[str, list[str]] = {}
    for name in expand_untracked(worktree, entries):
        if is_secret_name(Path(name).name):
            verdict = "secret-like name, not opened"
        elif has_main and name.startswith(RESEARCH_PREFIXES):
            code, blob = git(worktree, "hash-object", "--", name)
            code2, in_main = git(worktree, "rev-parse", "-q", "--verify", f"{main_ref}:{name}")
            if code == 0 and code2 == 0 and blob == in_main:
                verdict = "identical to the main line"
            elif code2 == 0:
                verdict = "differs from the main line"
            else:
                verdict = "not on the main line"
        else:
            verdict = "outside the research folders"
        groups.setdefault(verdict, []).append(name)
    total = sum(len(v) for v in groups.values())
    parts = [f"{verdict} ({len(names)}): " + ", ".join(names[:6]) + (", ..." if len(names) > 6 else "")
             for verdict, names in sorted(groups.items())]
    return f"{total} untracked file(s); " + "; ".join(parts)


# ---------------------------------------------------------------------------------------------
# Folders outside Git
# ---------------------------------------------------------------------------------------------

def scan_folder(root: Path) -> tuple[dict[str, list[Any]], list[str]]:
    """Return ({relpath: [size, mtime_ns]}, secret-like names). Contents are not read here."""
    files: dict[str, list[Any]] = {}
    secret_names: list[str] = []
    for current, dirs, names in os.walk(root):
        kept = []
        for d in dirs:
            if d in SKIP_DIR_NAMES or is_secret_name(d):
                secret_names.append(str(Path(current, d).relative_to(root)).replace("\\", "/") + "/")
            else:
                kept.append(d)
        dirs[:] = kept
        for name in names:
            rel = str(Path(current, name).relative_to(root)).replace("\\", "/")
            if is_secret_name(name):
                secret_names.append(rel)
                continue
            try:
                info = os.stat(Path(current, name))
            except OSError:
                continue
            files[rel] = [info.st_size, info.st_mtime_ns]
    return files, secret_names


def hash_file(path: Path) -> str | None:
    if path.stat().st_size > MAX_HASH_BYTES:
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def review_non_git(entry: dict[str, Any], manifest_dir: Path, update: bool) -> list[Finding]:
    root = Path(entry["path"])
    label = entry.get("label") or root.name
    if not root.is_dir():
        return [Finding(WARN, "NON_GIT_MISSING", str(root), "declared folder does not exist")]
    manifest_path = manifest_dir / f"{label}.json"
    files, secrets = scan_folder(root)
    previous: dict[str, Any] = {}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8")).get("files", {})
    findings: list[Finding] = []
    new = sorted(set(files) - set(previous))
    removed = sorted(set(previous) - set(files))
    changed = sorted(p for p in files if p in previous and files[p] != previous[p][:2])
    if not previous:
        findings.append(Finding(INFO, "NON_GIT_BASELINE", str(root),
                                f"no manifest yet; {len(files)} file(s) would be recorded as the baseline"))
    elif new or changed or removed:
        findings.append(Finding(WARN, "NON_GIT_CHANGED", str(root),
                                f"{len(new)} new, {len(changed)} changed, {len(removed)} removed since the last manifest: "
                                + ", ".join((new + changed + removed)[:10])))
    if secrets:
        findings.append(Finding(INFO, "SECRET_LIKE_PRESENT", str(root),
                                f"{len(secrets)} secret-like name(s) present, not opened: " + ", ".join(secrets[:8])))
    if update:
        manifest_dir.mkdir(parents=True, exist_ok=True)
        rows = {}
        for rel, (size, mtime) in files.items():
            old = previous.get(rel)
            digest = old[2] if old and old[:2] == [size, mtime] else hash_file(root / rel)
            rows[rel] = [size, mtime, digest]
        manifest_path.write_text(json.dumps({"root_label": label, "files": rows}, indent=1), encoding="utf-8")
    return findings


# ---------------------------------------------------------------------------------------------
# Finished tasks whose results are not on GitHub
# ---------------------------------------------------------------------------------------------

STATE_MAIN = "on main"
STATE_IN_PR = "in PR"
STATE_PUSHED = "pushed, no open PR"
STATE_REMOTE = "on a remote branch (PR status unknown)"
STATE_HELD = "held by owner"
STATE_LOCAL = "finished only locally"
STATE_NO_TARGET = "finished, no export target declared"
STATE_RUNNING = "not finished"


def classify_publication(canonical: Path, main_ref: str, paths: list[str],
                         open_pr_heads: dict[str, int] | None) -> tuple[str, str]:
    """Where the result files are: on the main line, on a remote branch (with or without an open PR), or nowhere."""
    if all(path_in_ref(canonical, main_ref, p) for p in paths):
        return STATE_MAIN, main_ref
    _, refs = git(canonical, "for-each-ref", "--format=%(refname:short)", "refs/remotes")
    holders = [r for r in refs.splitlines()
               if r and not r.endswith("/HEAD") and r != main_ref and all(path_in_ref(canonical, r, p) for p in paths)]
    if not holders:
        return STATE_LOCAL, ""
    if open_pr_heads is None:
        return STATE_REMOTE, holders[0]
    for ref in holders:
        branch = ref.split("/", 1)[-1]
        if branch in open_pr_heads:
            return f"{STATE_IN_PR} #{open_pr_heads[branch]}", ref
    return STATE_PUSHED, holders[0]


def review_tasks(tasks: list[dict[str, Any]], canonical: Path | None, main_ref: str,
                 open_pr_heads: dict[str, int] | None = None) -> tuple[list[Finding], list[dict[str, str]]]:
    """One row per task. A task is finished when its marker exists; its result is published when every path in
    ``published_paths`` (or the single ``published_path``) is on the main line."""
    findings: list[Finding] = []
    rows: list[dict[str, str]] = []
    for task in tasks:
        name = task["id"]
        source = task.get("source", "configuration")
        marker = Path(task["finished_marker"])
        if not marker.exists():
            rows.append({"id": name, "source": source, "state": STATE_RUNNING})
            continue
        paths = task.get("published_paths") or ([task["published_path"]] if task.get("published_path") else [])
        hold = task.get("owner_hold")
        if not paths:
            findings.append(Finding(WARN, "FINISHED_NO_EXPORT_TARGET", name,
                                    "finished locally, but no path in the repository is declared for its result"
                                    + (f"; held: {hold}" if hold else "")))
            rows.append({"id": name, "source": source, "state": STATE_NO_TARGET})
            continue
        if canonical is None:
            findings.append(Finding(WARN, "FINISHED_NOT_PUBLISHED", name, "no canonical repository configured to check against"))
            rows.append({"id": name, "source": source, "state": "unknown"})
            continue
        state, ref = classify_publication(canonical, main_ref, paths, open_pr_heads)
        label = state
        if state == STATE_MAIN:
            pass
        elif state.startswith(STATE_IN_PR):
            findings.append(Finding(INFO, "FINISHED_IN_PR", name, f"result is on {ref} ({state}), not yet on {main_ref}"))
        elif state in (STATE_PUSHED, STATE_REMOTE):
            why = "no open pull request carries it" if state == STATE_PUSHED else "its pull request is unknown"
            findings.append(Finding(WARN, "FINISHED_NOT_PUBLISHED", name,
                                    f"result is on {ref} but {why}" + (f"; held: {hold}" if hold else "")))
        elif hold:
            label = f"{STATE_HELD} ({hold})"
            findings.append(Finding(INFO, "FINISHED_NOT_PUBLISHED", name,
                                    f"finished; {', '.join(paths[:3])} is on no remote branch; publication is held: {hold}"))
        else:
            findings.append(Finding(ALERT, "FINISHED_NOT_PUBLISHED", name,
                                    f"finished (marker present); {', '.join(paths[:3])} is on no remote branch"))
        rows.append({"id": name, "source": source, "state": label})
    return findings, rows


PROTECTED_RESULTS = ("clean", "withheld")


def _days_since(day: str, now: float) -> float | None:
    try:
        stamp = datetime.fromisoformat(day.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return (now - stamp.timestamp()) / 86400


def review_exports(tasks: list[dict[str, Any]], rows: list[dict[str, str]], exports: dict[str, Any],
                   require_record: bool, hold_max_days: float, now: float) -> list[Finding]:
    """Check the export record of every finished task: a target, a protected-data check, a branch or pull request, or a hold.

    The record lives in the synchronisation configuration (``exports``), never in the coordinator's database, so nothing
    here needs a migration of the running laboratory. A task that is already on the main line is reported softly (note);
    a task that is not is reported as a warning, so the gap shows up before the work is exported, not after.
    """
    findings: list[Finding] = []
    states = {row["id"]: row["state"] for row in rows}
    for task in tasks:
        name = task["id"]
        state = states.get(name)
        if state is None or state == STATE_RUNNING:
            continue
        record = exports.get(name)
        row = next(r for r in rows if r["id"] == name)
        soft = INFO if state == STATE_MAIN else WARN
        if record is None:
            if require_record:
                findings.append(Finding(soft, "EXPORT_NO_RECORD", name,
                                        "finished, but no export record (target, protected-data check, branch or pull request, or hold)"))
            continue
        parts = []
        check = record.get("protected_check")
        if not isinstance(check, dict) or not check.get("checked_on"):
            findings.append(Finding(soft, "EXPORT_NO_PROTECTED_CHECK", name,
                                    "the export record has no protected-data check (checked_on, result, withheld)"))
            parts.append("check missing")
        elif check.get("result") not in PROTECTED_RESULTS:
            findings.append(Finding(WARN, "EXPORT_PROTECTED_CHECK_OPEN", name,
                                    f"the protected-data check has result {check.get('result')!r}; it must be one of {PROTECTED_RESULTS}"))
            parts.append("check open")
        elif check["result"] == "withheld" and not check.get("withheld"):
            findings.append(Finding(WARN, "EXPORT_PROTECTED_CHECK_INCOMPLETE", name,
                                    "the check says material is withheld but does not list what"))
            parts.append("check incomplete")
        else:
            parts.append(f"check {check['result']} {check['checked_on']}")
        if record.get("pr"):
            parts.append(f"PR #{record['pr']}")
        elif record.get("branch"):
            parts.append(f"branch {record['branch']}")
        if record.get("branch") and state == STATE_LOCAL:
            findings.append(Finding(ALERT, "EXPORT_BRANCH_MISSING", name,
                                    f"the record names branch {record['branch']!r}, but the result is on no remote branch"))
        hold = record.get("hold")
        if hold:
            age = _days_since(str(record.get("hold_since", "")), now)
            if age is None:
                findings.append(Finding(WARN, "EXPORT_HOLD_STALE", name, f"held ({hold}) without a valid hold_since date"))
            elif age > hold_max_days:
                findings.append(Finding(WARN, "EXPORT_HOLD_STALE", name,
                                        f"held for {age:.0f} days (limit {hold_max_days:.0f}): {hold}"))
            parts.append(f"hold since {record.get('hold_since', '?')}")
        row["export"] = "; ".join(parts) or "record without details"
    for name in sorted(set(exports) - {t["id"] for t in tasks}):
        findings.append(Finding(INFO, "EXPORT_RECORD_UNKNOWN_TASK", name,
                                "an export record names a task the coordinator and the configuration do not know (stale?)"))
    return findings


# ---------------------------------------------------------------------------------------------
# Read-only adapter for the coordinator's declared experiments and closed missions
# ---------------------------------------------------------------------------------------------

REQUIRED_OUTPUT_FALLBACK = ("REPORT.md", "results.json", "raw-freeze.json", "PROTOCOL.md")


def _read_toml(path: Path) -> dict[str, Any]:
    """Parse one coordinator configuration file and keep only [paths] and [[experiments]].

    Everything else in the file (agents, tokens, limits) is dropped at once and never reaches a report.
    """
    import tomllib

    with open(path, "rb") as handle:
        raw = tomllib.load(handle)
    return {"paths": {k: v for k, v in raw.get("paths", {}).items() if k == "local_root"},
            "experiments": [{k: e.get(k) for k in ("name", "run_dir", "out_dir", "required_outputs")}
                            for e in raw.get("experiments", []) if isinstance(e, dict) and e.get("name")]}


def _repository_relative(out_dir: Path) -> str | None:
    """The part of an experiment folder that lives inside the repository: from ``data/`` onwards."""
    parts = out_dir.as_posix().split("/")
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == "data":
            return "/".join(parts[index:])
    return None


def discover_coordinator_tasks(spec: dict[str, Any], overrides: dict[str, Any]) -> list[dict[str, Any]]:
    """Experiments declared in the coordinator's configuration files, plus closed missions.

    Only files named in ``spec`` are read: the configuration files (reduced to paths and experiments) and the
    names in the missions report folder. The coordinator's database, state folder, ``.env`` and sealed or blinded
    material are never opened. An experiment is finished when ``DONE.json`` exists in its run folder (the
    coordinator's own rule); its result is expected at the repository path that mirrors ``out_dir``.
    """
    experiments: dict[str, dict[str, Any]] = {}
    local_root: Path | None = None
    for config_path in spec.get("configs", []):
        parsed = _read_toml(Path(config_path))
        if parsed["paths"].get("local_root"):
            local_root = Path(parsed["paths"]["local_root"])
        for entry in parsed["experiments"]:
            experiments[entry["name"]] = {**experiments.get(entry["name"], {}), **{k: v for k, v in entry.items() if v}}
    tasks: list[dict[str, Any]] = []
    for name, entry in sorted(experiments.items()):
        run_dir, out_dir = entry.get("run_dir"), entry.get("out_dir")
        if not run_dir or not out_dir:
            continue
        base = local_root or Path(".")
        run_path, out_path = base / run_dir, base / out_dir
        relative = _repository_relative(out_path)
        outputs = entry.get("required_outputs") or list(REQUIRED_OUTPUT_FALLBACK)
        task: dict[str, Any] = {"id": name, "source": "coordinator experiment", "finished_marker": str(run_path / "DONE.json")}
        if relative:
            existing = [f"{relative}/{o}" for o in outputs if (out_path / o).exists()]
            task["published_paths"] = existing or [f"{relative}/{outputs[0]}"]
        task.update(overrides.get(name, {}))
        tasks.append(task)
    missions_dir = spec.get("missions_dir")
    if missions_dir and Path(missions_dir).is_dir():
        targets = spec.get("mission_targets", {})
        for report in sorted(Path(missions_dir).glob("*.md")):
            name = report.stem
            task = {"id": f"mission {name}", "source": "coordinator mission", "finished_marker": str(report)}
            if name in targets:
                task["published_paths"] = list(targets[name]) if isinstance(targets[name], list) else [targets[name]]
            task.update(overrides.get(f"mission {name}", {}))
            tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------------------------
# GitHub (pull requests, issues, branches, experiment descriptions)
# ---------------------------------------------------------------------------------------------

def _age_days(stamp: str, now: float) -> float:
    return (now - datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()) / 86400


def review_prs(prs: list[dict[str, Any]], now: float, stale_days: float = 7) -> list[Finding]:
    findings: list[Finding] = []
    for pr in prs:
        where = f"PR #{pr['number']}"
        checks = pr.get("statusCheckRollup") or []
        outcomes = [(c.get("conclusion") or c.get("state") or c.get("status") or "").upper() for c in checks]
        if any(o in ("FAILURE", "ERROR", "TIMED_OUT", "STARTUP_FAILURE") for o in outcomes):
            findings.append(Finding(ALERT, "PR_CI_FAILING", where, f"{pr['title'][:70]}: a check is failing"))
        elif any(o in ("IN_PROGRESS", "QUEUED", "PENDING", "") for o in outcomes) and outcomes:
            findings.append(Finding(INFO, "PR_CI_PENDING", where, "checks are still running or queued"))
        if pr.get("mergeStateStatus") in ("DIRTY", "BEHIND"):
            findings.append(Finding(WARN, "PR_NOT_CLEAN", where, f"merge state {pr['mergeStateStatus']}"))
        if pr.get("updatedAt") and _age_days(pr["updatedAt"], now) > stale_days:
            findings.append(Finding(WARN, "PR_STALE", where, f"no update for {_age_days(pr['updatedAt'], now):.0f} days"))
        if "#" not in (pr.get("body") or ""):
            findings.append(Finding(INFO, "PR_NO_ISSUE_LINK", where, "the description references no issue or pull request"))
    return findings


ACCEPTANCE_HINTS = ("acceptance", "done when", "definition of done", "- [ ]", "success criteri", "deliverable")


def review_issues(issues: list[dict[str, Any]], merged_prs: list[dict[str, Any]], now: float,
                  stale_days: float = 45) -> list[Finding]:
    findings: list[Finding] = []
    closed_by: dict[int, int] = {}
    for pr in merged_prs:
        for ref in pr.get("closingIssuesReferences") or []:
            closed_by[int(ref["number"])] = int(pr["number"])
    for issue in issues:
        number = issue["number"]
        where = f"Issue #{number}"
        if number in closed_by:
            findings.append(Finding(WARN, "ISSUE_RESOLVED_BUT_OPEN", where,
                                    f"still open although merged PR #{closed_by[number]} declared that it closes it"))
        body = (issue.get("body") or "").lower()
        if issue.get("body") is not None and not any(hint in body for hint in ACCEPTANCE_HINTS):
            findings.append(Finding(INFO, "ISSUE_NO_ACCEPTANCE", where, "no acceptance criterion found in the description"))
        comments = issue.get("comments")
        count = len(comments) if isinstance(comments, list) else (comments or 0)
        if issue.get("updatedAt") and _age_days(issue["updatedAt"], now) > stale_days and not count:
            findings.append(Finding(WARN, "ISSUE_STALE", where, "no comment and no update for a long time"))
    return findings


def review_branches(tree: Path, main_ref: str, now: float, stale_days: float = 14) -> list[Finding]:
    findings: list[Finding] = []
    _, merged = git(tree, "branch", "-r", "--merged", main_ref, "--format=%(refname:short)")
    merged_names = [b for b in merged.splitlines() if b and not b.endswith(("/HEAD", main_ref.split("/", 1)[-1]))]
    if merged_names:
        findings.append(Finding(INFO, "BRANCH_MERGED_UNDELETED", str(tree),
                                f"{len(merged_names)} remote branch(es) already in {main_ref}; deleting them needs the owner's consent"))
    _, unmerged = git(tree, "branch", "-r", "--no-merged", main_ref, "--format=%(refname:short)|%(committerdate:unix)")
    for row in unmerged.splitlines():
        name, _, stamp = row.rpartition("|")
        if name.endswith("/HEAD") or not stamp:
            continue
        age = (now - float(stamp)) / 86400
        if age > stale_days:
            findings.append(Finding(WARN, "BRANCH_UNMERGED_OLD", name, f"not in {main_ref}; tip is {age:.0f} days old"))
    return findings


def review_experiments(tree: Path) -> list[Finding]:
    lab = tree / "data" / "lab"
    if not lab.is_dir():
        return []
    index_text = ""
    for rel in ("docs/11-research-laboratory/lab-map.md", "docs/00-project/REPOSITORY_MAP.md", "README.md"):
        candidate = tree / rel
        if candidate.exists():
            index_text += candidate.read_text(encoding="utf-8", errors="replace")
    no_readme = [d.name for d in sorted(lab.iterdir()) if d.is_dir() and not any(d.glob("README*"))]
    not_indexed = [d.name for d in sorted(lab.iterdir()) if d.is_dir() and d.name not in index_text]
    findings = []
    if no_readme:
        findings.append(Finding(INFO, "EXPERIMENT_NO_README", "data/lab",
                                f"{len(no_readme)} experiment folder(s) without a README: " + ", ".join(no_readme[:10])))
    if not_indexed:
        findings.append(Finding(INFO, "EXPERIMENT_NOT_INDEXED", "data/lab",
                                f"{len(not_indexed)} experiment folder(s) not named in the lab map, repository map, or README: "
                                + ", ".join(not_indexed[:10])))
    return findings


def fetch_github(repo: str) -> dict[str, Any]:
    exe = shutil.which("gh")
    if not exe:
        raise FileNotFoundError("gh is not installed")

    def run(*args: str) -> Any:
        proc = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip()[:300])
        return json.loads(proc.stdout or "null")

    return {
        "prs": run("pr", "list", "-R", repo, "--state", "open", "--limit", "100", "--json",
                   "number,title,isDraft,updatedAt,mergeStateStatus,statusCheckRollup,body"),
        "issues": run("issue", "list", "-R", repo, "--state", "open", "--limit", "300", "--json",
                      "number,title,updatedAt,body,comments"),
        "merged_prs": run("pr", "list", "-R", repo, "--state", "merged", "--limit", "200", "--json",
                          "number,closingIssuesReferences"),
    }


# ---------------------------------------------------------------------------------------------
# Rendering and entry point
# ---------------------------------------------------------------------------------------------

def render(findings: list[Finding], task_rows: list[dict[str, str]], title: str, now: float) -> str:
    ordered = sorted(findings, key=lambda f: (SEVERITY_ORDER[f.severity], f.code, f.where))
    stamp = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    counts = {s: sum(1 for f in findings if f.severity == s) for s in (ALERT, WARN, INFO)}
    lines = [f"# {title}", "", f"Generated {stamp}. Alerts: {counts[ALERT]}, warnings: {counts[WARN]}, notes: {counts[INFO]}.", ""]
    if task_rows:
        with_export = any("export" in r for r in task_rows)
        if with_export:
            lines += ["## Tasks and their results on GitHub", "", "| Task | Source | State | Export record |", "|---|---|---|---|"]
            lines += [f"| {r['id']} | {r.get('source', '')} | {r['state']} | {r.get('export', 'none')} |" for r in task_rows]
        else:
            lines += ["## Tasks and their results on GitHub", "", "| Task | Source | State |", "|---|---|---|"]
            lines += [f"| {r['id']} | {r.get('source', '')} | {r['state']} |" for r in task_rows]
        lines.append("")
    for severity in (ALERT, WARN, INFO):
        group = [f for f in ordered if f.severity == severity]
        if not group:
            continue
        lines += [f"## {severity} ({len(group)})", ""]
        lines += [f"- `{f.code}` {f.where}: {f.detail}" for f in group]
        lines.append("")
    if not findings:
        lines.append("Nothing to report.")
    return "\n".join(lines) + "\n"


def exit_code(findings: list[Finding]) -> int:
    if any(f.severity == ALERT for f in findings):
        return 2
    return 1 if any(f.severity == WARN for f in findings) else 0


def open_pr_heads_from_github(repo: str) -> dict[str, int] | None:
    """Head branch -> number of the open pull requests (``gh`` list only); None when it cannot be read."""
    exe = shutil.which("gh")
    if not exe:
        return None
    proc = subprocess.run([exe, "pr", "list", "-R", repo, "--state", "open", "--limit", "200", "--json", "number,headRefName"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if proc.returncode != 0:
        return None
    return {row["headRefName"]: int(row["number"]) for row in json.loads(proc.stdout or "[]")}


def run_local(cfg: dict[str, Any], now: float, update_manifests: bool,
              open_pr_heads: dict[str, int] | None = None,
              fetch_canonical: bool = False) -> tuple[list[Finding], list[dict[str, str]]]:
    findings: list[Finding] = []
    canonical_path = Path(cfg["canonical_repo"]) if cfg.get("canonical_repo") else None
    if fetch_canonical and canonical_path is not None:
        git(canonical_path, "fetch", "-q", "--prune", "origin")  # the only write: remote-tracking refs of the canonical clone
    canonical_ids = set(patch_ids(canonical_path, ["--remotes"], 800)) if canonical_path is not None else set()
    for repo in find_repositories(cfg.get("roots", []), int(cfg.get("repos_depth", 3))):
        findings += review_repository(repo, cfg, now, canonical_ids)
    manifest_dir = Path(cfg.get("manifest_dir", "sync-manifests"))
    for entry in cfg.get("non_git_folders", []):
        findings += review_non_git(entry, manifest_dir, update_manifests)
    canonical = canonical_path
    tasks = list(cfg.get("tasks", []))
    if cfg.get("coordinator"):
        known = {task["id"] for task in tasks}
        tasks += [task for task in discover_coordinator_tasks(cfg["coordinator"], cfg.get("task_overrides", {}))
                  if task["id"] not in known]
    exports = cfg.get("exports", {})
    for task in tasks:  # an export record may supply the target and the hold of a task the coordinator does not describe
        record = exports.get(task["id"])
        if record:
            if record.get("targets") and not task.get("published_paths") and not task.get("published_path"):
                task["published_paths"] = list(record["targets"])
            if record.get("hold") and not task.get("owner_hold"):
                task["owner_hold"] = record["hold"]
    task_findings, rows = review_tasks(tasks, canonical, cfg.get("remote_main", "origin/main"), open_pr_heads)
    export_findings = review_exports(tasks, rows, exports, bool(cfg.get("require_export_record")),
                                     float(cfg.get("hold_max_days", 14)), now)
    return findings + task_findings + export_findings, rows


def run_github(snapshot: dict[str, Any], tree: Path | None, main_ref: str, now: float) -> list[Finding]:
    findings = review_prs(snapshot.get("prs", []), now)
    findings += review_issues(snapshot.get("issues", []), snapshot.get("merged_prs", []), now)
    if tree is not None:
        findings += review_branches(tree, main_ref, now)
        findings += review_experiments(tree)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("local", "github", "all"))
    parser.add_argument("--config", help="JSON file with local paths (kept out of Git)")
    parser.add_argument("--repo", help="OWNER/NAME for the GitHub section")
    parser.add_argument("--input-json", help="GitHub snapshot file instead of calling gh")
    parser.add_argument("--tree", help="a clone of the repository for branch and experiment checks")
    parser.add_argument("--remote-main", default="origin/main")
    parser.add_argument("--out", help="directory for the dated report files")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--update-manifests", action="store_true", help="record the folder manifests after reporting")
    parser.add_argument("--fetch-canonical", action="store_true",
                        help="run git fetch --prune in the canonical clone first (refreshes its remote-tracking refs only)")
    args = parser.parse_args(argv)

    now = time.time()
    cfg: dict[str, Any] = {}
    if args.config:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    cfg.setdefault("remote_main", args.remote_main)
    findings: list[Finding] = []
    rows: list[dict[str, str]] = []
    if args.command in ("local", "all"):
        if not args.config:
            parser.error("the local section needs --config")
        repo_name = args.repo or cfg.get("repo")
        heads = open_pr_heads_from_github(repo_name) if repo_name else None
        local_findings, rows = run_local(cfg, now, args.update_manifests, heads, args.fetch_canonical)
        findings += local_findings
    if args.command in ("github", "all"):
        if args.input_json:
            snapshot = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        elif args.repo:
            snapshot = fetch_github(args.repo)
        else:
            parser.error("the github section needs --repo or --input-json")
        tree = Path(args.tree or cfg.get("canonical_repo") or "") if (args.tree or cfg.get("canonical_repo")) else None
        findings += run_github(snapshot, tree, cfg["remote_main"], now)

    title = {"local": "Local synchronisation report", "github": "GitHub review", "all": "Synchronisation report"}[args.command]
    text = json.dumps({"findings": [asdict(f) for f in findings], "tasks": rows}, indent=1) if args.format == "json" \
        else render(findings, rows, title, now)
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = "json" if args.format == "json" else "md"
        (out_dir / f"{datetime.fromtimestamp(now, timezone.utc):%Y-%m-%d}-{args.command}.{suffix}").write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(text)
    return exit_code(findings)


if __name__ == "__main__":
    raise SystemExit(main())
