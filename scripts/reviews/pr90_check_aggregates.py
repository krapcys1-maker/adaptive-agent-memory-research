"""Read-only recomputation of PR 90 summaries; prints counts/differences, no text.

Use the run's original PERSONA_BATTERY_* settings. --expected is the saved
aggregate JSON. This deliberately does not call analyse(), which writes sheets.
It checks numerical reproducibility, not label correctness or model replication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import persona_battery as pb  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("items", "notes", "card", "workdir", "expected"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    work = args.workdir
    files = set(work.rglob("*")) | {args.items, args.notes, args.card, args.expected}
    before = {p: digest(p) for p in files if p.is_file()}
    expected = pb.load_json(args.expected)
    ctx = pb.load_context(argparse.Namespace(
        config=pb.CONFIG, items=args.items, notes=args.notes, card=args.card,
        workdir=work, ledger=None, writer_url=None, judge_url=None,
        embedder="none", workers=1,
    ))

    def labels(folder, stem, label_file, classes):
        mapping = folder / (stem + "_sheet_map.json")
        return pb.read_labels(folder / label_file, pb.load_json(mapping), classes) if mapping.exists() else None

    p1, p2, p3 = (pb.ps.load_jsonl(work / name) for name in ("p1.jsonl", "p2.jsonl", "p3.jsonl"))
    answers = pb.ps.load_jsonl(work / "p7" / "answers.jsonl")
    h1 = labels(work, "p1_unanswered", "p1_unanswered_labels.json", pb.UNANSWERED_CLASSES)
    h3 = labels(work, "p3_blind", "p3_blind_labels.json", pb.BLIND_CLASSES)
    h7 = labels(work / "p7", "hand", "hand_labels.json", pb.HAND_CLASSES)
    h7b = labels(work / "p7", "hand", "hand_labels_2.json", pb.HAND_CLASSES)
    free = pb.load_json(work / "free_controls.json")
    summaries = {
        "p1": pb.p1_summary(ctx, p1, h1) if p1 else None,
        "p2": pb.p2_summary(ctx, p2) if p2 else None,
        "p3": pb.p3_summary(ctx, p3, h3) if p3 else None,
        "p7": pb.p7_summary(ctx, answers, h7, h7b) if answers else None,
    }
    actual = dict(summaries, free_controls=free)
    actual["readings"] = {
        stage: (None if summary is None else
                pb.p1_readings(summary) if stage == "p1" else
                getattr(pb, stage + "_readings")(summary, free))
        for stage, summary in summaries.items()
    }
    rows = {"p1": p1, "p2": p2, "p3": p3, "p7_answers": answers,
            "p7_labels": pb.ps.load_jsonl(work / "p7" / "labels2.jsonl")}
    actual["records"] = {name: len(records) for name, records in rows.items()}
    differences = []

    def compare(left, right, path):
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(left.keys() | right.keys()):
                compare(left.get(key), right.get(key), path + "/" + key)
        elif left != right:
            differences.append(path)

    for name, value in actual.items():
        compare(value, expected.get(name), name)
    unchanged = all(p.exists() and digest(p) == sha for p, sha in before.items())
    same_files = {p for p in work.rglob("*") if p.is_file()} == {p for p in before if p.is_relative_to(work)}
    result = {
        "records": actual["records"],
        "duplicate_keys": {name: len(records) - len({r["key"] for r in records}) for name, records in rows.items()},
        "compared_sections": sorted(actual),
        "differences": differences,
        "input_files_checked": len(before),
        "input_files_unchanged": unchanged and same_files,
        "provenance_not_relabelled": True,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if differences or not unchanged or not same_files:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
