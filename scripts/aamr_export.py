#!/usr/bin/env python3
"""Export a finished laboratory task to the public repository: protected-data check, branch, pull request, checks, merge, confirmation.

The laboratory (the coordinator) finishes a task and leaves its products in local folders. This tool takes an *export plan* that says which
files are the publishable result, where they go in the repository, and which files are raw or protected and belong to the private area, and
then does the whole route that ``docs/00-project/coordinator-export-flow.md`` describes:

1. **Protected-data check** of every file to be published. The export is *held* (nothing is pushed, the reason goes into the export record and
   so into the daily report) when a file looks like a secret, a blinding key or sealed data, a raw run, a database or a transcript; when it is too
   large; when its content holds a credential, a personal e-mail address or a machine-local path (unless the plan asks for paths to be replaced
   and the file is not frozen); when a manifest records an absolute path; when it would silently overwrite a file already on the base branch; or
   when the result has no README that opens with its status. Uncertain means held: one held export never stops the others.
2. **Private area.** Raw and protected files named in the plan are copied into the private area (optionally moved) with a relative SHA-256 manifest and
   a pointer file; what stays in the laboratory is state plus the pointer.
3. **Branch and pull request.** A worktree of the canonical clone, one commit (with a manifest of published files, relative paths and SHA-256), a push,
   a pull request with a HANDOFF block.
4. **Checks and merge** (only with ``--merge``): wait for the required checks, merge only when all pass and the pull request is clean.
5. **Confirmation on the base branch:** every published path must exist there with the recorded SHA-256. The export record in the synchronisation
   configuration is updated at each step, so the daily report shows the task as held, in a pull request, or on main.

It writes only to the worktree it creates, the private area and the synchronisation configuration. It never reads the laboratory's database,
``.env`` or sealed material, calls no model and no paid API, and never force-pushes or rewrites history.

Usage::

    python scripts/aamr_export.py check  PLAN.json
    python scripts/aamr_export.py export PLAN.json --config sync.local.json [--merge] [--sanitize-paths]

Exit codes: 0 done (exported, or a pull request opened), 3 held (this export only), 4 failed after the pull request existed (checks failed, not mergeable,
confirmation failed), 2 usage or plan error.
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Protocol

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024
ALLOWED_TARGET_PREFIXES = ("data/lab/", "docs/", "scripts/", "tests/")
PLACEHOLDER = "[machine-local path omitted]"
SECRET_NAME_PATTERNS = (".env", ".env.*", "*.env", "*.pem", "*.key", "*.pfx", "*.p12", "id_rsa*", "*secret*", "*credential*", "key_*", "blind_*",
                        "*sealed*", "*.db", "*.sqlite", "*.sqlite3", "*.bundle", "transcript*", "*.kdbx")
SECRET_DIR_PARTS = {"sealed", "blind", ".git", "state", "sandboxes"}
CONTENT_PATTERNS = {
    "token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b|github_pat_[A-Za-z0-9_]{20,}|\bsk-[A-Za-z0-9_-]{16,}\b|\bAKIA[0-9A-Z]{16}\b|\bxox[baprs]-[A-Za-z0-9-]{10,}\b|\bAIza[0-9A-Za-z_-]{30,}\b"),
    "private_key_block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "bearer_credential": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    "assigned_secret": re.compile(r"(?i)\b(?:api[_-]?key|secret|token|passwd|password)s?\b\s*[:=]\s*['\"][A-Za-z0-9_./+=-]{12,}['\"]"),
    # anchored on the '@' (one character of look-behind) so the scan stays linear on a very long line; the masked excerpt shows only the domain
    "personal_email": re.compile(r"(?<=[\w.+-])@(?:gmail|outlook|hotmail|yahoo|proton|icloud)\.[a-z]+", re.I),
}
LOCAL_PATH = re.compile(r"(?<![A-Za-z\]])[A-Za-z]:(?:\\\\|\\|/)+[A-Za-z0-9_]")
LOCAL_PATH_FULL = re.compile(r"(?<![A-Za-z\]])[A-Za-z]:(?:\\\\|\\|/)+[^\"'`<>|\n]*[A-Za-z0-9_.)]")
TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".csv", ".py", ".toml", ".yaml", ".yml", ".cfg", ".ini", ".html", ".sh", ".ps1", ".out", ".log"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_under(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
    except ValueError:
        return False
    return True


def mask(value: str) -> str:
    return value[:4] + "..." + f"({len(value)} chars)"


# ---------------------------------------------------------------------------------------------
# 1. Protected-data check
# ---------------------------------------------------------------------------------------------

def protected_name(name: str, parts: tuple[str, ...]) -> bool:
    lowered = name.lower()
    return any(fnmatch.fnmatch(lowered, pattern) for pattern in SECRET_NAME_PATTERNS) or any(part.lower() in SECRET_DIR_PARTS for part in parts)


def readme_opens_with_status(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()][:15]
    return any(re.search(r"\*\*Status", line) or re.match(r"(?i)^\s*status\s*:", line) for line in lines)


def check_plan(plan: dict[str, Any], exists_on_base) -> dict[str, Any]:
    """Return {result, problems, withheld, files}. ``exists_on_base(rel)`` says whether a repository path already exists on the base branch."""
    problems: list[dict[str, str]] = []
    files: list[dict[str, Any]] = []
    run_dir = Path(plan["run_dir"]) if plan.get("run_dir") else None
    sanitize = bool(plan.get("sanitize_paths"))
    readme_ok = False
    total = 0
    seen_targets = set()

    def add(code: str, path: str, detail: str) -> None:
        problems.append({"code": code, "path": path, "detail": detail})

    for entry in plan.get("publish", []):
        src, dest = Path(entry["from"]), entry["to"]
        label = dest
        if dest.startswith(("/", "\\")) or ".." in Path(dest).parts or re.match(r"^[A-Za-z]:", dest):
            add("bad_target", label, "the target must be a relative path inside the repository")
            continue
        if not dest.startswith(ALLOWED_TARGET_PREFIXES):
            add("bad_target", label, f"the target must start with one of {ALLOWED_TARGET_PREFIXES}")
        if dest in seen_targets:
            add("bad_target", label, "two files for one target")
        seen_targets.add(dest)
        if not src.is_file():
            add("missing_source", label, "the source file does not exist")
            continue
        size = src.stat().st_size
        total += size
        if protected_name(src.name, src.parts[:-1]):
            add("protected_name", label, "the name or folder looks like a secret, a blinding key, sealed data, a database or a transcript")
        if run_dir is not None and is_under(src, run_dir):
            add("raw_run_file", label, "the file lies inside the raw run folder, which is private")
        if size > MAX_FILE_BYTES:
            add("too_large", label, f"{size} bytes exceeds the limit of {MAX_FILE_BYTES}; publish a manifest and keep the file private")
        if Path(dest).name.lower() == "readme.md" and readme_opens_with_status(src.read_text(encoding="utf-8", errors="replace")):
            readme_ok = True
        if exists_on_base(dest) and not entry.get("update"):
            add("would_overwrite", label, "the path already exists on the base branch; frozen or published files are never replaced silently")
        frozen = bool(entry.get("frozen"))
        sanitized = False
        if size <= MAX_FILE_BYTES and (src.suffix.lower() in TEXT_SUFFIXES or src.suffix == ""):      # a file over the limit is held anyway
            text = src.read_text(encoding="utf-8", errors="replace")
            for code, pattern in CONTENT_PATTERNS.items():
                match = pattern.search(text)
                if match and not entry.get("reviewed_false_positive") == code:
                    add(code, label, f"matches a {code.replace('_', ' ')} pattern: {mask(match.group(0))}")
            if LOCAL_PATH.search(text):
                if frozen and entry.get("accept_local_paths"):
                    pass  # published byte for byte; the plan names an erratum that explains it (checked below)
                elif sanitize and not frozen:
                    sanitized = True
                else:
                    add("local_path", label, "the content holds a machine-local absolute path (use relative paths, or sanitize a file that is not frozen)")
            if src.name.endswith("raw-freeze.json") or entry.get("manifest"):
                try:
                    data = json.loads(text)
                except ValueError:
                    data = None
                if isinstance(data, dict):
                    absolute = [k for k in ([data.get("raw_root")] + list(data.get("files", {}) if isinstance(data.get("files"), dict) else []))
                                if isinstance(k, str) and re.match(r"^[A-Za-z]:[\\/]|^/", k)]
                    if absolute:
                        add("absolute_manifest_path", label, "a manifest records an absolute path; new manifests use paths relative to the run folder")
        files.append({"from": str(src), "to": dest, "bytes": size, "sha256": sha256_file(src), "frozen": frozen, "sanitize": sanitized})
    if entries_accepting_paths(plan) and not any(e["to"].lower().endswith(("erratum.md", "erratum_local_paths.md")) or "ERRATUM" in e["to"].upper() for e in plan.get("publish", [])):
        add("erratum_missing", "plan", "a frozen file is published with local paths but no erratum file is part of the publication")
    if plan.get("require_readme", True) and not readme_ok:
        add("no_readme_status", "plan", "the publication needs a README.md whose first lines state the status (a line with **Status ...**)")
    if total > MAX_TOTAL_BYTES:
        add("too_large", "plan", f"{total} bytes in total exceeds {MAX_TOTAL_BYTES}")
    if not plan.get("publish"):
        add("nothing_to_publish", "plan", "the plan lists no file to publish")
    withheld = [item.get("what", item.get("to", "")) for item in plan.get("private", [])]
    result = "hold" if problems else ("withheld" if withheld else "clean")
    return {"result": result, "problems": problems, "withheld": withheld, "files": files}


def entries_accepting_paths(plan: dict[str, Any]) -> bool:
    return any(entry.get("accept_local_paths") for entry in plan.get("publish", []))


# ---------------------------------------------------------------------------------------------
# Git and GitHub
# ---------------------------------------------------------------------------------------------

def run(cmd: list[str], cwd: Path | str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    if check and proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])} failed ({proc.returncode}): {proc.stderr.strip()[:300]}")
    return proc


class GitHub(Protocol):
    def pr_create(self, base: str, head: str, title: str, body: str) -> tuple[int, str]: ...
    def checks(self, number: int) -> tuple[str, str]: ...      # ("pending" | "success" | "failure", detail)
    def merge(self, number: int) -> None: ...


class GhCli:
    """The real thing: the ``gh`` command line."""

    def __init__(self, slug: str):
        self.slug = slug

    def pr_create(self, base: str, head: str, title: str, body: str) -> tuple[int, str]:
        out = run(["gh", "pr", "create", "-R", self.slug, "--base", base, "--head", head, "--title", title, "--body", body]).stdout.strip()
        url = out.splitlines()[-1]
        return int(url.rstrip("/").rsplit("/", 1)[-1]), url

    def checks(self, number: int) -> tuple[str, str]:
        data = json.loads(run(["gh", "pr", "view", str(number), "-R", self.slug, "--json", "mergeStateStatus,statusCheckRollup"]).stdout)
        rollup = data.get("statusCheckRollup") or []
        states = [(c.get("conclusion") or c.get("status") or "").upper() for c in rollup]
        if any(s in ("FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "STARTUP_FAILURE", "ACTION_REQUIRED") for s in states):
            return "failure", ",".join(sorted(set(states)))
        if not states or any(s in ("IN_PROGRESS", "QUEUED", "PENDING", "WAITING", "") for s in states) or data.get("mergeStateStatus") not in ("CLEAN", "HAS_HOOKS"):
            return "pending", f"{data.get('mergeStateStatus')} {len(states)} checks"
        return "success", f"{len(states)} checks"

    def merge(self, number: int) -> None:
        run(["gh", "pr", "merge", str(number), "-R", self.slug, "--merge"])


def git(repo: Path | str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git", "-C", str(repo), "--no-optional-locks", *args], check=check)


# ---------------------------------------------------------------------------------------------
# Export record in the synchronisation configuration
# ---------------------------------------------------------------------------------------------

def update_record(config_path: Path, task_id: str, patch: dict[str, Any], drop: tuple[str, ...] = ()) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    record = cfg.setdefault("exports", {}).setdefault(task_id, {})
    record.update(patch)
    for key in drop:
        record.pop(key, None)
    tmp = config_path.with_suffix(config_path.suffix + ".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, config_path)
    return record


def today() -> str:
    return datetime.date.today().isoformat()


# ---------------------------------------------------------------------------------------------
# 2./3./4./5. The export
# ---------------------------------------------------------------------------------------------

def sanitize_text(text: str) -> tuple[str, int]:
    return LOCAL_PATH_FULL.subn(PLACEHOLDER, text)


def stage_private(plan: dict[str, Any], private_root: Path, move: bool) -> list[dict[str, Any]]:
    """Copy raw and protected material into the private area with a relative SHA-256 manifest and a pointer; optionally move (copy, verify, then remove)."""
    out = []
    for item in plan.get("private", []):
        src, rel = Path(item["from"]), item["to"]
        dest = private_root / rel
        dest.mkdir(parents=True, exist_ok=True)
        sources = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
        base = src.parent if src.is_file() else src
        manifest = {}
        for f in sources:
            target = dest / f.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            if sha256_file(target) != sha256_file(f):
                raise RuntimeError(f"copy of {f.name} does not match its source")
            manifest[f.relative_to(base).as_posix()] = sha256_file(target)
        (dest / "MANIFEST.sha256.json").write_text(json.dumps({"files": manifest, "note": "paths are relative to this folder"}, indent=1) + "\n", encoding="utf-8")
        location = Path(rel).as_posix()
        if move:
            for f in sources:
                f.unlink()
            if src.is_dir():
                for p in sorted(src.rglob("*"), reverse=True):
                    if p.is_dir() and not any(p.iterdir()):
                        p.rmdir()
            (src.parent / (src.name + ".MOVED.json")).write_text(
                json.dumps({"moved_to": f"private/{location}", "files": len(manifest), "note": "raw material moved to the private area; verify with MANIFEST.sha256.json there"}, indent=1) + "\n",
                encoding="utf-8")
        out.append({"to": f"private/{location}", "files": len(manifest), "moved": bool(move), "what": item.get("what", "")})
    return out


def pr_body(plan: dict[str, Any], check: dict[str, Any], private: list[dict[str, Any]], readme_dir: str) -> str:
    lines = [f"## Where this work lives", f"- Target: `{readme_dir}`", f"- Branch: `{plan['branch']}`",
             f"- Task id in the laboratory: `{plan['id']}`", "- Frozen files touched: none (the export refuses to overwrite an existing path)",
             "- Protected-data check: **" + check["result"] + "** (run by `scripts/aamr_export.py`; every published file checked for secrets, blinding material, "
             "raw runs, personal e-mail addresses, machine-local paths, size and absolute manifest paths)", ""]
    if private:
        lines += ["## Withheld (private, pinned by SHA-256)"] + [f"- {p['what'] or p['to']}: {p['files']} file(s), manifest with relative paths" for p in private] + [""]
    lines += ["## HANDOFF", f"Branch and head: {plan['branch']}", "In Git / only local: published files in Git; raw and protected files in the private area",
              "Tests run and result: the repository's required checks run on this pull request", "Frozen files touched: none", "Held for the owner: see the README", "",
              "Generated by the export flow of the laboratory (`scripts/aamr_export.py`)."]
    return "\n".join(lines)


def export(plan: dict[str, Any], config_path: Path, gh: GitHub, *, merge: bool = False, wait_s: float = 1800, poll_s: float = 20,
           identity: tuple[str, str] = ("export-flow", "export-flow@users.noreply.invalid"), move_private: bool = False,
           sleeper=time.sleep, log=print) -> int:
    canonical = Path(plan["canonical"])
    base, remote, task_id = plan.get("base", "main"), plan.get("remote", "origin"), plan["id"]
    private_root = Path(plan["private_root"])
    plan = dict(plan)
    git(canonical, "fetch", "-q", remote)

    def exists_on_base(rel: str) -> bool:
        return git(canonical, "cat-file", "-e", f"{remote}/{base}:{rel}", check=False).returncode == 0

    check = check_plan(plan, exists_on_base)
    (private_root / "exports" / task_id).mkdir(parents=True, exist_ok=True)
    (private_root / "exports" / task_id / "protected-check.json").write_text(json.dumps(check, indent=1) + "\n", encoding="utf-8")
    targets = [f["to"] for f in check["files"]]
    if check["result"] == "hold":
        reasons = "; ".join(f"{p['code']} ({p['path']})" for p in check["problems"][:6])
        update_record(config_path, task_id, {"targets": targets, "hold": f"protected-data check held this export: {reasons}", "hold_since": today(),
                                              "protected_check": {"checked_on": today(), "result": "hold", "withheld": [], "by": "aamr_export.py"}})
        log(f"HELD: {task_id}: {reasons}")
        return 3
    readme = next((f for f in check["files"] if Path(f["to"]).name.lower() == "readme.md"), check["files"][0])
    readme_dir = readme["to"].rsplit("/", 1)[0] + "/" if "/" in readme["to"] else ""
    work_root = Path(plan["work_root"])
    worktree = work_root / plan["branch"].replace("/", "-")
    git(canonical, "worktree", "add", "-q", "-b", plan["branch"], str(worktree), f"{remote}/{base}")
    try:
        published = []
        for f in check["files"]:
            dest = worktree / f["to"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            edits = ["none"]
            if f["sanitize"]:
                text, n = sanitize_text(Path(f["from"]).read_text(encoding="utf-8", errors="replace"))
                dest.write_text(text, encoding="utf-8", newline="")
                edits = [f"replaced {n} machine-local path(s) with '{PLACEHOLDER}'"]
            else:
                shutil.copy2(f["from"], dest)
            published.append({"path": f["to"][len(readme_dir):] if f["to"].startswith(readme_dir) else f["to"], "target": f["to"], "sha256": sha256_file(dest),
                              "sha256_source": f["sha256"], "bytes": dest.stat().st_size, "edits": edits})
        private = stage_private(plan, private_root, move_private)
        manifest = {"task": task_id, "published": published, "private": private, "paths_are_relative": True,
                    "protected_check": {"result": check["result"], "withheld": check["withheld"]}}
        (worktree / readme_dir / "PUBLISHED_FILES.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        ident = ["-c", f"user.name={identity[0]}", "-c", f"user.email={identity[1]}"]
        git(worktree, "add", "-A")
        message = plan.get("commit_message") or f"Export of the finished laboratory task {task_id}: result, manifest and README"
        git(worktree, *ident, "commit", "-q", "-m", message + "\n\nProtected-data check: " + check["result"] + ".")
        blob_ids = {p["target"]: git(worktree, "rev-parse", f"HEAD:{p['target']}").stdout.strip() for p in published}  # what was committed
        git(worktree, "push", "-q", "-u", remote, plan["branch"])
        number, url = gh.pr_create(base, plan["branch"], plan.get("title") or f"Export: {task_id}", pr_body(plan, check, private, readme_dir))
        record = {"targets": targets, "branch": plan["branch"], "pr": number,
                  "protected_check": {"checked_on": today(), "result": check["result"], "withheld": check["withheld"], "by": "aamr_export.py"},
                  "private_location": [p["to"] for p in private]}
        update_record(config_path, task_id, record, drop=("hold", "hold_since"))
        log(f"pull request #{number}: {url}")
        if not merge:
            return 0
        waited = 0.0
        while True:
            state, detail = gh.checks(number)
            if state != "pending" or waited >= wait_s:
                break
            sleeper(poll_s)
            waited += poll_s
        if state != "success":
            update_record(config_path, task_id, {"hold": f"pull request #{number} not merged: checks {state} ({detail})", "hold_since": today()})
            log(f"NOT MERGED: checks {state} ({detail})")
            return 4
        gh.merge(number)
        git(canonical, "fetch", "-q", remote)
        wrong = [target for target, blob in blob_ids.items()
                 if git(canonical, "rev-parse", f"{remote}/{base}:{target}", check=False).stdout.strip() != blob]   # missing or different on the base branch
        if wrong:
            update_record(config_path, task_id, {"hold": f"merged, but not confirmed on {base}: {wrong[:3]}", "hold_since": today()})
            log(f"NOT CONFIRMED: {wrong}")
            return 4
        head = git(canonical, "rev-parse", f"{remote}/{base}").stdout.strip()
        update_record(config_path, task_id, {"confirmed_on_main": head[:12], "merged": True}, drop=("hold", "hold_since"))
        log(f"confirmed on {base} at {head[:7]}")
        return 0
    finally:
        git(canonical, "worktree", "remove", "--force", str(worktree), check=False)
        git(canonical, "branch", "-D", plan["branch"], check=False)


def load_plan(path: Path) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    for key in ("id", "canonical", "work_root", "private_root", "branch", "publish"):
        if key not in plan:
            raise SystemExit(f"plan error: missing '{key}'")
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("check", "export"))
    parser.add_argument("plan")
    parser.add_argument("--config", help="the synchronisation configuration whose 'exports' record is updated")
    parser.add_argument("--merge", action="store_true", help="wait for the required checks and merge when all pass")
    parser.add_argument("--sanitize-paths", action="store_true", help="replace machine-local paths in files that are not frozen")
    parser.add_argument("--move-private", action="store_true", help="move raw files to the private area instead of copying")
    parser.add_argument("--identity-name", default="export-flow")
    parser.add_argument("--identity-email", default="export-flow@users.noreply.invalid")
    parser.add_argument("--wait-seconds", type=float, default=1800)
    args = parser.parse_args(argv)
    plan = load_plan(Path(args.plan))
    if args.sanitize_paths:
        plan["sanitize_paths"] = True
    canonical = Path(plan["canonical"])
    if args.command == "check":
        remote, base = plan.get("remote", "origin"), plan.get("base", "main")
        git(canonical, "fetch", "-q", remote)
        result = check_plan(plan, lambda rel: git(canonical, "cat-file", "-e", f"{remote}/{base}:{rel}", check=False).returncode == 0)
        print(json.dumps({k: result[k] for k in ("result", "problems", "withheld")}, indent=1))
        return 3 if result["result"] == "hold" else 0
    if not args.config or "repo" not in plan:
        parser.error("export needs --config and a 'repo' (OWNER/NAME) in the plan")
    return export(plan, Path(args.config), GhCli(plan["repo"]), merge=args.merge, wait_s=args.wait_seconds,
                  identity=(args.identity_name, args.identity_email), move_private=args.move_private)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    raise SystemExit(main())
