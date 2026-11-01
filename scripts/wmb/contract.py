"""Record contract of the memory benchmark: one JSONL record per judgment or answer, a summary that carries the SHA-256 of the record file, and an
offline verifier that recomputes every aggregate from the records with no model call (the pattern of OmniMemEval, kept small)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Dict, List, Sequence


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_jsonl(path: Path) -> List[dict]:
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def append_jsonl(path: Path, rows: Sequence[dict]) -> None:
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_summary(path: Path, records_path: Path, aggregates: Dict, meta: Dict) -> Dict:
    """Aggregates, the digest of the record file they were computed from, and the metadata of the run (commit, thresholds hash, models, seeds)."""
    summary = {"records_file": Path(records_path).name, "records_sha256": sha256_file(records_path), "records": len(load_jsonl(records_path)), "aggregates": aggregates, "meta": meta}
    Path(path).write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def verify_summary(summary_path: Path, records_path: Path, aggregate_fn: Callable[[List[dict]], Dict]) -> Dict[str, bool]:
    """True/True when the record file is the one that was summarised and every aggregate recomputes to the stored value."""
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    records = load_jsonl(records_path)
    recomputed = json.loads(json.dumps(aggregate_fn(records), sort_keys=True))
    return {"records_sha256": summary["records_sha256"] == sha256_file(records_path), "aggregates": recomputed == summary["aggregates"]}
