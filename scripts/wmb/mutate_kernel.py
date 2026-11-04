"""Reproducible, standard-library-only mutation check for both WMB kernel lines.

Default: python scripts/wmb/mutate_kernel.py --workers 4 --json PRIVATE/report.json
Live line: add --module scripts/wmb/kernel/memory_kernel.py
--test-file may be repeated to select suites; otherwise the corresponding original
suite and the additive boundary suite are used. --only selects named mutants.

Every registered old text must occur exactly once. Baseline tests must pass before
any mutant runs. Each change is compiled and tested in a separate temporary tree,
never in the checkout. Pytest exit 1 kills a mutant; collection/infrastructure
errors and timeouts are errors, never kills. Survivors fail unless their catalogue
entry carries an explicit equivalence reason. No performance/coverage claim is
made beyond this finite catalogue. Historical throwaway harnesses are not claimed
to have been recovered; the catalogue reconstructs their documented properties.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
FROZEN = Path("scripts/wmb/memory_kernel.py")
LIVE = Path("scripts/wmb/kernel/memory_kernel.py")


@dataclasses.dataclass(frozen=True)
class Mutation:
    name: str
    old: str
    new: str
    equivalent_reason: str = ""


COMMON = [
    ("build-as-of-inclusive", "if key > idx.as_of_key:", "if key >= idx.as_of_key:"),
    ("retrieve-strict-future", "index.keys[ident] >= now_key", "index.keys[ident] > now_key"),
    ("replacement-effective-boundary", "index.superseded_by[ident] < now_key", "index.superseded_by[ident] <= now_key"),
    ("replacement-ignores-date", "index.superseded_by[ident] < now_key", "True"),
    ("fiction-unrestricted", 'it.origin == "fiction_autobio" and not persona_ok', 'False'),
    ("persona-task-scope", 'persona_ok = task_type in prof["persona_task_types"]', 'persona_ok = True'),
    ("names-task-scope", 'if prof["names"] and task_type in prof["name_task_types"]:', 'if prof["names"]:'),
    ("names-disabled", 'if prof["names"] and task_type in prof["name_task_types"]:', 'if False:'),
    ("embedding-gate", 'if cos is not None and cos >= tau:', 'if cos is not None:'),
    ("embedding-reason", 'reasons.append("embedding")', 'pass'),
    ("lexical-reason", 'reasons.append("lexical")', 'pass'),
    ("name-reason", 'reasons.append("name")', 'pass'),
    ("top-k", 'top = found[: int(prof["k"])]', 'top = found'),
    ("ranking", 'found.sort(key=lambda row: (row[0], row[1], row[2]))', 'found.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)'),
    ("normalize-vectors", 'out[i] /= norm', 'out[i] *= norm'),
    ("reject-vector-count", 'if len(produced) != len(missing):', 'if False:'),
    ("reject-vector-dimensions", 'if len(sizes) > 1:', 'if False:'),
    ("duplicate-counter", 'idx.rejected["duplicate"] += 1', 'idx.rejected["duplicate"] += 0'),
    ("future-counter", 'idx.rejected["future"] += 1', 'idx.rejected["future"] += 0'),
    ("month-precision", 'int(month or 1)', 'int(month or 12)'),
    ("day-precision", 'int(day or 1)', 'int(day or 2)'),
    ("hour-precision", 'int(hour or 0)', 'int(hour or 1)'),
    ("zone-sign", '(-1 if zone[0] == "-" else 1)', '(1 if zone[0] == "-" else -1)'),
    ("calibration-order", 'ordered = sorted(best_scores)', 'ordered = sorted(best_scores, reverse=True)'),
    ("calibration-quantile", '(1 - share) * len(ordered)', 'share * len(ordered)'),
    ("calibration-rounding", '* 1e4) / 1e4', '* 1e2) / 1e2'),
    ("guard-future-flag", 'flags.append("future_item")', 'pass'),
    ("guard-support-flag", 'flags.append("unsupported_reference")', 'pass'),
    ("guard-spurious-flag", 'flags.append("spurious_reference")', 'pass'),
    ("guard-fiction-flag", 'flags.append("fiction_out_of_scope")', 'pass'),
    ("guard-ok", '"ok": not flags', '"ok": True'),
    ("guard-callback-count", '"callbacks": len(refs)', '"callbacks": 0'),
    ("log-raw-ids-opt-in", 'if raw_ids:', 'if True:'),
    ("log-raw-ids-content", 'record["ids"] = [i.id for i in items]', 'record["ids"] = []'),
]

EXTRA = {
    "0.1.0": [
        ("rare-df-boundary", 'index.df.get(t, 0) <= prof["rare_df"]', 'index.df.get(t, 0) < prof["rare_df"]'),
        ("rare-name-length", 'and len(t) >= 3)', 'and len(t) >= 2)'),
        ("stem-ies-boundary", 'len(word) > 4 and word.endswith("ies")', 'len(word) > 5 and word.endswith("ies")'),
        ("stem-ss", 'and not word.endswith("ss")', 'and True'),
        ("stem-possessive", 'if word.endswith("\'s"):', 'if False:'),
        ("analyse-stop-words", 'if root in STOP or len(root) < 2:', 'if len(root) < 2:'),
        ("analyse-inside-name", 'if not initial or (surface.isupper() and len(surface) >= 3):', 'if False:'),
        ("query-length-cap", 'query = query[:MAX_QUERY_CHARS]', 'query = query'),
        ("guard-two-content-words", '< 2 for s in refs', '< 1 for s in refs'),
        ("calibration-no-queries", 'if not best_scores:\n        return None', 'if not best_scores:\n        return 0.0'),
        ("calibration-no-future", 'if index.keys[ident] >= key:', 'if index.keys[ident] > key:'),
        ("render-order", 'sorted(zip(keys, items), key=lambda pair: (pair[0], pair[1].id))', 'sorted(zip(keys, items), key=lambda pair: (pair[0], pair[1].id), reverse=True)'),
        ("render-trace-mode", 'if mode == "trace" and it.trace and it.trace.get("gist"):', 'if False:'),
        ("render-angle", '("Angle: " + it.trace["angle"])', '("" + it.trace["angle"])'),
        ("log-query-privacy", 'hmac_fn(key if key is not None else result.get("_query", ""))', '(key if key is not None else result.get("_query", ""))'),
    ],
    "0.2.0": [
        ("rare-df-boundary", 'df.get(t, 0) <= prof["rare_df"]', 'df.get(t, 0) < prof["rare_df"]'),
        ("rare-name-length", 'and len(t) >= 3)', 'and len(t) >= 2)'),
        ("stem-irregular", 'if w in IRREGULAR:', 'if False:'),
        ("stem-possessive", 'if w.endswith("\'s"):', 'if False:'),
        ("analyse-inside-name", 'if not initial or _acronym(surface):', 'if False:'),
        ("analyse-invisible", 'text[:MAX_TEXT_CHARS].translate(_INVISIBLE)', 'text[:MAX_TEXT_CHARS]'),
        ("query-length-cap", 'if isinstance(query, str):\n        query = query[:MAX_QUERY_CHARS]', 'if isinstance(query, str):\n        query = query'),
        ("guard-three-content-words", 'if len(shared) >= 3:', 'if len(shared) >= 2:'),
        ("guard-distinctive-boundary", '>= DISTINCT * hapax', '> DISTINCT * hapax'),
        ("calibration-no-queries", 'if not best_scores:\n            return None', 'if not best_scores:\n            return 0.0'),
        ("calibration-invalid-share", 'if not 0.0 <= share <= 1.0 or channel', 'if not -1.0 <= share <= 2.0 or channel'),
        ("calibration-positive-floor", 'return threshold if threshold > 0.0 else None', 'return threshold'),
        ("render-order", 'return sorted(rows, key=lambda row: (row[1], row[2], row[0]))', 'return sorted(rows, key=lambda row: (row[1], row[2], row[0]), reverse=True)'),
        ("render-trace-mode", 'if mode == "trace" and isinstance(trace, dict)', 'if False and isinstance(trace, dict)'),
        ("log-query-privacy", 'keyed(key if key is not None else result.get("_query", ""))', '(key if key is not None else result.get("_query", ""))'),
    ],
}


def catalogue(version):
    if version not in EXTRA:
        raise ValueError("no registered catalogue for version " + version)
    return [Mutation(*spec) for spec in COMMON + EXTRA[version]]


def apply(source, mutant):
    count = source.count(mutant.old)
    if count != 1 or mutant.old == mutant.new:
        raise ValueError("%s: expected one old text, found %d" % (mutant.name, count))
    changed = source.replace(mutant.old, mutant.new, 1)
    compile(changed, mutant.name, "exec")
    return changed


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_copy(module, tests, source, timeout):
    """Keep the temporary tree alive until pytest (and its children) has exited."""
    with tempfile.TemporaryDirectory(prefix="wmb-mutant-") as directory:
        tree = Path(directory)
        assets = {FROZEN, LIVE, Path("scripts/wmb/kernel/README.md"), *tests}
        for rel in assets:
            target = tree / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, target)
        target = tree / (LIVE if 'VERSION = "0.2.0"' in source else FROZEN)
        target.write_text(source, encoding="utf-8", newline="\n")
        env = os.environ.copy()
        for name in ("PYTHONPATH", "PYTEST_ADDOPTS", "WMB_KERNEL_V2_FILE"):
            env.pop(name, None)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        command = [sys.executable, "-m", "pytest", "-x", "-q", *map(str, tests)]
        started = time.monotonic()
        try:
            process = subprocess.Popen(command, cwd=tree, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding="utf-8", errors="replace",
                                       start_new_session=os.name != "nt",
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise
            outcome = "survived" if process.returncode == 0 else "killed" if process.returncode == 1 else "error"
            detail = (stdout + stderr)[-5000:]
        except subprocess.TimeoutExpired:
            outcome, detail = "error", "pytest timed out (not counted as a kill)"
        return {"outcome": outcome, "seconds": round(time.monotonic() - started, 3), "detail": detail}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=Path, default=FROZEN)
    parser.add_argument("--test-file", type=Path, action="append")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--only", action="append")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.workers < 1 or args.timeout <= 0:
            raise ValueError("workers and timeout must be positive")
        module = args.module.resolve() if args.module.is_absolute() else (ROOT / args.module).resolve()
        source = module.read_text(encoding="utf-8")
        version = "0.2.0" if 'VERSION = "0.2.0"' in source else "0.1.0" if 'VERSION = "0.1.0"' in source else "unknown"
        mutants = catalogue(version)
        if args.only:
            unknown = set(args.only) - {m.name for m in mutants}
            if unknown:
                raise ValueError("unknown mutants: " + ", ".join(sorted(unknown)))
            mutants = [m for m in mutants if m.name in args.only]
        # Validate the entire selected catalogue before spending time on tests.
        changes = [(m, apply(source, m)) for m in mutants]
        if args.list:
            print("\n".join(m.name for m, _ in changes))
            return 0
        primary = "test_wmb_kernel_v2.py" if version == "0.2.0" else "test_wmb_memory_kernel.py"
        tests = args.test_file or [Path("tests/test_wmb_memory_kernel_mutants.py"), Path("tests") / primary]
        tests = [(p.resolve().relative_to(ROOT) if p.is_absolute() else p) for p in tests]
        if any(".." in p.parts or not (ROOT / p).is_file() for p in tests):
            raise ValueError("test files must exist inside the repository")
        preserved = {p: digest(p) for p in {module, ROOT / FROZEN, ROOT / LIVE, *(ROOT / p for p in tests)}}
        if args.json and (args.json.exists() or args.json.resolve() in {p.resolve() for p in preserved}):
            raise ValueError("JSON output requires a new file, never a source or existing artifact")
        baseline = run_copy(module, tests, source, args.timeout)
        if baseline["outcome"] != "survived":
            raise ValueError("baseline must pass before mutation:\n" + baseline["detail"])

        def evaluate(pair):
            m, changed = pair
            return dict(name=m.name, equivalent_reason=m.equivalent_reason,
                        **run_copy(module, tests, changed, args.timeout))

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(evaluate, changes))
        unchanged = all(digest(p) == sha for p, sha in preserved.items())
        for r in results:
            print("%-37s %-9s %7.2fs %s" % (r["name"], r["outcome"], r["seconds"], r["equivalent_reason"]))
        counts = {outcome: sum(r["outcome"] == outcome for r in results) for outcome in ("killed", "survived", "error")}
        report = {"version": version, "source_sha256": digest(module),
                  "test_sha256": {str(p): digest(ROOT / p) for p in tests},
                  "catalogue_sha256": hashlib.sha256(json.dumps([dataclasses.asdict(m) for m, _ in changes], sort_keys=True).encode()).hexdigest(),
                  "baseline": baseline, "counts": counts, "files_unchanged": unchanged, "mutants": results}
        if args.json:
            with args.json.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(report, indent=2) + "\n")
        print(json.dumps(dict(counts, files_unchanged=unchanged), sort_keys=True))
        return int(not unchanged or any(r["outcome"] == "error" or (r["outcome"] == "survived" and not r["equivalent_reason"]) for r in results))
    except (OSError, ValueError, SyntaxError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
