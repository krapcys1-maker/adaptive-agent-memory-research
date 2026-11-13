"""No code may hard-wire a path that exists only on one person's machine.

A default such as ``D:\\<someone's folder>\\data.jsonl`` makes a script work for its author
and fail for every other contributor, and it publishes the author's directory layout. Paths
outside the repository belong in a command-line argument, an environment variable or a
config file that the user supplies; paths inside it are built from the repository root.

The scan covers the code that contributors import or run (``scripts/``, ``tools/``,
``tasks.py``). Lines that are hash-frozen by an experiment manifest cannot be edited without
breaking the claim audit, so they are listed in KNOWN with the reason and are allowed only
as they stand, byte for byte. A new occurrence anywhere fails this test.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A drive letter followed by a separator and a name (C:\Users, D:/data), not a regex class
# such as [A-Za-z]:\\ ; or a POSIX home directory of a named user.
ABSOLUTE = re.compile(r"(?<![A-Za-z\]])[A-Za-z]:[\\/]+[A-Za-z0-9_]|(?<![\w.])/(?:home|Users)/[A-Za-z0-9_.-]+/")

# (path, SHA-256 of the stripped line), so this file does not repeat the paths. The three
# defaults of --notes, --prep and --workdir in the WMB-R1 runner are hash-frozen by
# data/lab/wmb-r1-retrieval/config.json and other WMB manifests (see
# `python scripts/pinned_files.py scripts/wmb/retrieval_bench.py`). They can be overridden on
# the command line; a successor version must not keep them.
KNOWN = {
    ("scripts/wmb/retrieval_bench.py", "ab3b3c4ad3a26191f62c7a5abdf8e768dc6c262b377dde7659aeca33abd13d6e"),  # --notes
    ("scripts/wmb/retrieval_bench.py", "bf1722a16e4ad421337639b9170f23583db7f4cabf402b2df7ee47e7e2f9090c"),  # --prep
    ("scripts/wmb/retrieval_bench.py", "66ad9ee1c2c35978ca284c8a0750da9d3aa651498899e8eb3086a2d37fb906a1"),  # --workdir
}


def scanned_files():
    yield ROOT / "tasks.py"
    for base in ("scripts", "tools"):
        yield from sorted((ROOT / base).rglob("*.py"))


def occurrences():
    """(path, line number, SHA-256 of the stripped line, stripped line) for every match."""
    for path in scanned_files():
        relative = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if ABSOLUTE.search(line):
                stripped = line.strip()
                yield relative, number, hashlib.sha256(stripped.encode("utf-8")).hexdigest(), stripped


def test_pattern_catches_drive_and_home_paths_but_not_regex_classes():
    assert ABSOLUTE.search(r'Path(r"D:\Work\notes.jsonl")')
    assert ABSOLUTE.search('open("C:/Users/someone/x.txt")')
    assert ABSOLUTE.search('"/home/someone/data"')
    assert ABSOLUTE.search('"/Users/someone/data"')
    assert not ABSOLUTE.search(r'PATTERNS = [r"[A-Za-z]:\\\\", r"[A-Za-z]:/(?:Users|Work)"]')
    assert not ABSOLUTE.search('url = "http://127.0.0.1:11434/api/chat"')
    assert not ABSOLUTE.search('ROOT / "data/lab/x.json"')


def test_no_new_machine_local_absolute_paths_in_code():
    new = [f"{p}:{n}: {line}" for p, n, digest, line in occurrences() if (p, digest) not in KNOWN]
    assert not new, ("machine-local absolute paths in code; take them from an argument, an environment "
                     "variable or the repository root instead:\n" + "\n".join(new))


def test_known_frozen_occurrences_still_exist_so_the_allowance_cannot_go_stale():
    present = {(p, digest) for p, _, digest, _ in occurrences()}
    assert KNOWN <= present, "a KNOWN entry no longer occurs; remove it: " + repr(sorted(KNOWN - present))
