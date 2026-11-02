"""Record contract of the memory benchmark: one JSONL record per judgment or answer, a summary that carries the SHA-256 of the record file, and an
offline verifier that recomputes every aggregate from the records with no model call (the pattern of OmniMemEval, kept small)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_text_lf(path: Path, text: str, exclusive: bool = False) -> None:
    """Write a text file with LF line endings on every platform (a digest recorded for a file must not depend on the operating system). `exclusive`: fail with
    FileExistsError when the file exists."""
    with open(path, "x" if exclusive else "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def load_jsonl(path: Path) -> List[dict]:
    """Every record of a JSONL file. A last line that was cut short (no final newline, not valid JSON: a crash in the middle of a write) is ignored with a warning on
    stderr; any other bad line raises ValueError that names the file and the line."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as handle:
        lines = handle.read().split("\n")
    rows: List[dict] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except ValueError as exc:
            if number == len(lines):                                          # nothing follows it: the unterminated last line
                print("warning: %s: ignored a torn last line (%d characters)" % (path, len(line)), file=sys.stderr)
                continue
            raise ValueError("%s line %d is not valid JSON: %s" % (path, number, exc)) from None
    return rows


def repair_tail(path: Path) -> Optional[str]:
    """Make an append safe after a write that was cut short: when the file does not end with a newline, a last line that is a complete record gets its newline and a
    torn fragment (never a record) is cut off, so that the next record is not glued to it. Returns what was done, None when nothing was needed."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return None
    with open(path, "rb+") as handle:
        data = handle.read()
        if data.endswith(b"\n"):
            return None
        cut = data.rfind(b"\n") + 1
        last = data[cut:]
        try:
            json.loads(last.decode("utf-8"))
        except ValueError:                                                    # includes UnicodeDecodeError
            handle.truncate(cut)
            done = "cut a torn last line of %d bytes" % len(last)
        else:
            handle.seek(0, 2)
            handle.write(b"\n")
            done = "added the missing final newline"
    print("warning: %s: %s" % (path, done), file=sys.stderr)
    return done


def append_jsonl(path: Path, rows: Sequence[dict]) -> None:
    repair_tail(path)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_summary(path: Path, records_path: Path, aggregates: Dict, meta: Dict) -> Dict:
    """Aggregates, the digest of the record file they were computed from, and the metadata of the run (commit, thresholds hash, models, seeds)."""
    summary = {"records_file": Path(records_path).name, "records_sha256": sha256_file(records_path), "records": len(load_jsonl(records_path)), "aggregates": aggregates, "meta": meta}
    write_text_lf(path, json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return summary


def verify_summary(summary_path: Path, records_path: Path, aggregate_fn: Callable[[List[dict]], Dict]) -> Dict[str, bool]:
    """True/True when the record file is the one that was summarised and every aggregate recomputes to the stored value."""
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    records = load_jsonl(records_path)
    recomputed = json.loads(json.dumps(aggregate_fn(records), sort_keys=True))
    return {"records_sha256": summary["records_sha256"] == sha256_file(records_path), "aggregates": recomputed == summary["aggregates"]}
