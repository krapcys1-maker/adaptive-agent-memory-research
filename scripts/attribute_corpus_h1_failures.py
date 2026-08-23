"""Which stage failed? Attribute every wrong answer to a pipeline stage.

"Answered fell from 0.857 to 0.845" gives no direction. "Of 13 failures, 11 were
the index never surfacing the record and 2 were the reader ignoring it" says
what to build next.

The stage vocabulary is not new here
------------------------------------
``PMLAB-FORG-F1`` defined it and this corpus never used it:

``F2`` indexing/addressing   a direct read finds the record; the index does not
``F3`` validity/selection    the retrieved set holds the gold, and selection
                             takes a superseded competitor instead
``F4`` reader utilization    the gold is in the prompt and the reader does not
                             use it
``F5`` action/evaluation     an answer was produced and not delivered — here,
                             truncated away by the output cap

``F0`` and ``F1`` cover capture and the durable-record contract. Neither can
occur in these runs: the corpus is generated whole and read from disk, so no
probe can fail to have been written. They are reported as structurally
unreachable rather than omitted, because a taxonomy that quietly drops its
first two levels invites the reader to assume they were checked.

How each is decided, mechanically
----------------------------------
Every test is decidable from the stored run and the corpus, with no model and no
judgement:

- the gold record is absent from what the arm retained            → ``F2``
- gold present, and the answer contains a wrong-answer marker
  supplied by a superseded competitor that was also retained      → ``F3``
- gold present, answer neither correct nor trapped                → ``F4``
- the answer is empty                                             → ``F5``

An abstention is **not** a failure and is counted apart. A system that knows it
does not know beats one that confabulates, and folding the two together would
rank the confabulator higher.

The ``F3``/``F4`` boundary is the one that carries weight, because the two point
at different work. ``F3`` says the memory layer failed to mark one record as
superseded by another — a bookkeeping problem. ``F4`` says the reader had
everything it needed and still got it wrong — a prompting or model problem.
Conflating them would send effort at whichever was guessed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_corpus_h1_reader import _present  # noqa: E402
from trace_corpus_h1_answer import load  # noqa: E402

CORPUS = ROOT / "data" / "lab" / "corpus-h1"

STAGES = {
    "F2": "indexing/addressing — the record exists and the index did not surface it",
    "F3": "validity/selection — gold was retrieved and a superseded record was answered from",
    "F4": "reader utilization — gold was in the prompt and was not used",
    "F5": "action/evaluation — an answer was produced and truncated away",
}


def attribute(record: dict[str, Any], gold: dict[str, Any]) -> str | None:
    """The stage that failed, or None when the probe did not fail."""
    if record.get("abstained"):
        return None  # counted separately; not a failure
    if record.get("answered"):
        return None
    if record.get("empty"):
        return "F5"

    retained = set(record.get("retained_ids") or [])
    if gold["gold_event_id"] not in retained:
        return "F2"

    forbidden = gold.get("forbidden_event_id")
    if record.get("leaked") and forbidden and forbidden in retained:
        return "F3"

    return "F4"


def run(corpus: Path, arms: list[str]) -> dict[str, Any]:
    gold = {g["query_id"]: g for g in load(corpus / "reveal-v0" / "gold.jsonl")}
    report: dict[str, Any] = {"stages": STAGES, "by_arm": {}}

    for arm in arms:
        path = corpus / f"reader-v0-{arm}" / "results.json"
        if not path.is_file():
            continue
        records = json.loads(path.read_text(encoding="utf-8"))["records"]

        if any(r.get("retained_ids") is None for r in records):
            report["by_arm"][arm] = {
                "unattributable": (
                    "this run predates retained_ids; F2 and F4 cannot be separated "
                    "without knowing what reached the prompt. Re-run to attribute."
                )
            }
            continue

        stages, families = Counter(), {}
        abstained = sum(1 for r in records if r.get("abstained"))
        for item in records:
            stage = attribute(item, gold[item["query_id"]])
            if stage:
                stages[stage] += 1
                families.setdefault(stage, Counter())[item["family"]] += 1

        report["by_arm"][arm] = {
            "probes": len(records),
            "answered": sum(1 for r in records if r.get("answered")),
            "abstained_not_a_failure": abstained,
            "failures": sum(stages.values()),
            "by_stage": dict(sorted(stages.items())),
            "by_stage_and_family": {s: dict(c) for s, c in sorted(families.items())},
            "F0_F1": "structurally unreachable: the corpus is generated whole and read from disk",
        }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--arms", nargs="*", default=["recency", "fts5", "rank-oracle"])
    parser.add_argument("--out", type=Path, default=None)
    arguments = parser.parse_args(argv)

    corpus = arguments.corpus if arguments.corpus.is_absolute() else ROOT / arguments.corpus
    report = run(corpus, arguments.arms)

    print("Failure attribution by pipeline stage (PMLAB-FORG-F1 vocabulary)\n")
    for arm, block in report["by_arm"].items():
        if "unattributable" in block:
            print(f"  {arm}: {block['unattributable']}\n")
            continue
        print(f"  {arm}   {block['answered']}/{block['probes']} answered, "
              f"{block['abstained_not_a_failure']} abstained, {block['failures']} failed")
        for stage, count in block["by_stage"].items():
            families = block["by_stage_and_family"][stage]
            spread = ", ".join(f"{f} {n}" for f, n in sorted(families.items(), key=lambda x: -x[1]))
            print(f"      {stage}  {count:>3}   {STAGES[stage][:52]}")
            print(f"             {spread}")
        print()

    if arguments.out:
        destination = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"written: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
