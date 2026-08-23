"""Re-score stored reader answers after a scoring fix. No API calls.

Why this exists
---------------
Two scoring defects were found after the arms had already run, and both would
otherwise have cost a full re-run to correct:

**Negation counted as a leak.** The marker ``disable`` fired inside *"do not
disable it"* — a correct refusal scored as having leaked the poisoned
instruction. POISON is the family where refusing is the right answer, so the
defect inverted the result on exactly the probes it mattered most for.

**Word boundaries missed inflections.** The same marker did not fire on
*"disabled"*, so a genuine leak phrased in the passive was invisible. One defect
inflated the number and the other deflated it, which is worse than either alone
because the errors are not in the same direction and do not announce themselves
by looking implausible.

Every answer is stored in the result files. Scoring is a pure function of the
answer and its gold row, so correcting it needs no model. Re-running would have
cost money and, because the reader is not deterministic across runs, would have
changed the answers as well as their scores — mixing a scoring fix with a fresh
sample and making neither attributable.

The original file is kept beside the corrected one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_corpus_h1_reader import score, summarise  # noqa: E402

CORPUS = ROOT / "data" / "lab" / "corpus-h1"


def load_gold(corpus: Path) -> dict[str, dict[str, Any]]:
    path = corpus / "reveal-v0" / "gold.jsonl"
    return {
        row["query_id"]: row
        for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    }


def rescore(path: Path, gold: dict[str, dict[str, Any]]) -> dict[str, Any]:
    original = json.loads(path.read_text(encoding="utf-8"))
    summary = original["summary"]

    records = []
    for record in original["records"]:
        fresh = score(record["answer"], gold[record["query_id"]])
        records.append({**record, **fresh})

    return {
        "records": records,
        "summary": {
            **summarise(records, summary["reader"] == "deterministic stub",
                        summary.get("spend_usd", 0.0), len(records),
                        summary["arm"], summary["token_budget"]),
            "rescored_from": path.relative_to(ROOT).as_posix(),
            "rescoring_note": (
                "answers are unchanged; only the scoring function was corrected. "
                "Negation no longer counts as a leak, and markers now cover their "
                "inflections. No API calls were made."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args(argv)

    corpus = arguments.corpus if arguments.corpus.is_absolute() else ROOT / arguments.corpus
    gold = load_gold(corpus)

    targets = sorted(corpus.glob("reader-v0-*/results.json"))
    if not targets:
        raise SystemExit("no reader runs found")

    for path in targets:
        if "-stub" in path.parent.name:
            continue
        before = json.loads(path.read_text(encoding="utf-8"))["summary"]
        after = rescore(path, gold)

        arm = after["summary"]["arm"]
        print(f"{arm}")
        for field in ("answered", "leaked", "abstained", "empty"):
            was, now = before.get(field), after["summary"].get(field)
            mark = "" if was == now else "   <-- changed"
            print(f"  {field:<11} {was}  ->  {now}{mark}")

        if arguments.dry_run:
            continue

        keep = path.parent / "results-before-scoring-fix.json"
        if not keep.exists():
            keep.write_bytes(path.read_bytes())
        path.write_bytes(
            (json.dumps(after, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        )
        print(f"  original kept at {keep.relative_to(ROOT).as_posix()}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
