"""PMLAB-DECORR-E1: do two runs of one model family make the same mistakes?

Issue #24. Deterministic, model-free at analysis time, no new API spend — it
reads label files already recorded.

The question, and why it matters
--------------------------------
The independence ladder asserts that a same-family model panel counts as **one**
reviewer, and requires tier I3 to *measure* error correlation rather than assert
it. That measurement has never been made. Until it is, I3 is a label rather than
a tier.

Why the obvious dataset cannot answer it
-----------------------------------------
The project holds one two-reviewer dataset: roles A and B of the same model over
120 queries. Its gold, however, is derived from those very labels —

    resolution: unanimous_roles_a_b   95
                blind_model_adjudication  25
    human_confirmed: False            120

so on 95 items both roles are correct **by construction** and on 25 exactly one
is wrong by construction. An error correlation computed against that gold would
measure the construction, not the reviewers. Issue #24 assumed this dataset
would serve; that assumption was wrong and is corrected here.

What can be measured without any gold
--------------------------------------
One property is decidable from the bytes alone: **did a role cite an evidence
identifier that did not appear in the material it was given?** The job payload
records exactly which records were shown. A citation outside that set is a
fabrication, wrong regardless of anyone's judgement, and detectable with no
model and no adjudicator.

That yields a true I0 ground truth over which error correlation is meaningful.
If both roles fabricate on the same items, the panel is one reviewer. If they
fabricate independently, that is evidence — not proof — of partial
decorrelation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "lab" / "api-screening" / "deepseek-v4-flash-pmlab-v01-annotations-m2-20260822"

EVIDENCE_ID = re.compile(r"E-[0-9A-F]{12}")
CITATION_FIELDS = (
    "gold_evidence_ids",
    "gold_current_ids",
    "forbidden_stale_ids",
    "alternative_acceptable_ids",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def visible_ids_by_query(role_dir: Path) -> dict[str, set[str]]:
    """Which evidence identifiers each query actually showed the model."""
    visible: dict[str, set[str]] = {}
    for job in load_jsonl(role_dir / "jobs.jsonl"):
        shown = set(EVIDENCE_ID.findall(json.dumps(job)))
        for query in job.get("queries", []):
            identifier = query.get("example_id") or query.get("id")
            if identifier:
                visible[str(identifier)] = shown
    return visible


def fabrications(role_dir: Path) -> dict[str, int]:
    """Per query: 1 if the role cited an identifier it was never shown."""
    visible = visible_ids_by_query(role_dir)
    result: dict[str, int] = {}
    for prediction in load_jsonl(role_dir / "predictions.jsonl"):
        identifier = str(prediction.get("example_id", ""))
        if not identifier:
            continue
        cited: set[str] = set()
        for field in CITATION_FIELDS:
            cited.update(prediction.get(field) or [])
        shown = visible.get(identifier)
        if shown is None:
            continue  # the query's payload is not recoverable; excluded, not guessed
        result[identifier] = int(bool(cited - shown))
    return result


def phi(a: list[int], b: list[int]) -> float | None:
    """Correlation between two binary error vectors, or None when undefined."""
    n11 = sum(1 for x, y in zip(a, b) if x and y)
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if not x and y)
    n00 = sum(1 for x, y in zip(a, b) if not x and not y)
    denominator = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    if denominator == 0:
        return None  # one vector is constant; correlation is undefined, not zero
    return (n11 * n00 - n10 * n01) / denominator


def run(dataset: Path) -> dict[str, Any]:
    roles = {slot: fabrications(dataset / slot) for slot in ("A", "B")}
    shared = sorted(set(roles["A"]) & set(roles["B"]))
    a = [roles["A"][k] for k in shared]
    b = [roles["B"][k] for k in shared]

    coefficient = phi(a, b)
    both = sum(1 for x, y in zip(a, b) if x and y)

    gold = ROOT / "data" / "lab" / "api-screening" / "deepseek-v4-flash-pmlab-v01-adjudication-m2-20260823" / "model-reviewed-gold.jsonl"
    provenance: dict[str, int] = {}
    if gold.is_file():
        for row in load_jsonl(gold):
            key = str(row.get("resolution", "?"))
            provenance[key] = provenance.get(key, 0) + 1

    return {
        "experiment_id": "PMLAB-DECORR-E1",
        "tier": "E-exploratory",
        "authority": "development measurement only; analysis is model-free and spends no API budget",
        "dataset": dataset.relative_to(ROOT).as_posix(),
        "queries_compared": len(shared),
        "ground_truth": (
            "I0 mechanical: a citation to an evidence identifier absent from the material the "
            "role was shown is a fabrication, wrong regardless of judgement"
        ),
        "fabrications": {"role_a": sum(a), "role_b": sum(b), "both_same_query": both},
        "error_correlation_phi": None if coefficient is None else round(coefficient, 6),
        "phi_undefined_reason": (
            None
            if coefficient is not None
            else "at least one role produced a constant error vector, so correlation is undefined rather than zero"
        ),
        "gold_provenance_of_the_unusable_dataset": provenance,
        "why_gold_cannot_be_used": (
            "gold is derived from the labels being measured: 95 items are the two roles' unanimous "
            "agreement and 25 are a third same-family role's adjudication, with none human confirmed"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)

    summary = run(DATASET)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if arguments.output:
        destination = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"\nwritten: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
