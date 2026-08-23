"""Comparative lab: the contract every system must satisfy, and the analysis.

Issue #51. Model-free — it consumes per-probe records that other runs produce.

Why the contract comes before the first system is read
------------------------------------------------------
A comparison across systems is void unless they were run identically. Written
after the first system is in hand, a contract gets shaped by what that system
happens to emit, and every later system is then measured against one system's
conveniences.

So it is frozen first, and ``validate`` refuses rather than warns. A table
quietly mixing a run at one token budget with a run at another is worse than no
table: it looks like a finding.

Two levels of error correlation, not one
-----------------------------------------
Phi over a binary error vector answers *do these two systems fail on the same
probes*. It cannot answer *do they fail the same way*, and collapsing failure
types into one number destroys exactly the structure this track exists to find.

So each failure type gets its own one-hot vector and its own phi. Two systems
can share an overall error rate, fail on the same probes, and still diverge
completely once the type is separated — which would be a finding a single
coefficient hides.

The constant-vector case is not a bug
--------------------------------------
``PMLAB-DECORR-E1`` closed because two roles of one model produced constant
error vectors and phi does not exist for those. Architectural difference does not
guarantee variance: a system scoring 0 of 120 or 120 of 120 on some failure type
still yields a constant vector, and phi for that pair is **undefined and reported
as such**. That is the correct result and the reason this module never
substitutes 0.0.

The interaction term
--------------------
Adding two mechanisms to one base:

    interaction = S(A+B) - S(A) - S(B) + S0

    ≈ 0   additive — the mechanisms address different failures
    < 0   redundant, or they interfere
    > 0   synergistic

That is a number rather than an impression. "+6 and +8 giving +14" is additive
to within noise; giving +8 is heavy redundancy; giving +17 is a positive
interaction of about +3 over the sum of independent effects.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

# Every field a per-probe record must carry. A run missing any of these cannot
# enter a comparison, because the missing field is exactly what a later question
# will need and nobody re-runs a system to add a column.
REQUIRED_FIELDS = (
    "probe_id", "system", "success", "abstained",
    "failure_stage", "failure_type", "retrieved_tokens",
)

# The stage a failure is attributed to. Extends PMLAB-FORG-F1's vocabulary with
# the two stages that only exist once memory is structured.
STAGES = ("none", "address", "retrieval", "state", "conflict", "reasoning", "answer")

FAILURE_TYPES = (
    "address_failure", "retrieval_failure", "state_failure",
    "conflict_failure", "reasoning_failure", "abstention_miss",
)

# Conditions that must be identical across every system in one comparison.
CONTRACT = (
    "corpus_id", "probe_set_sha256", "reader_model", "prompt_sha256",
    "token_budget", "judge", "abstention_policy", "failure_taxonomy_version",
)


def validate(runs: dict[str, dict[str, Any]]) -> None:
    """Refuse to compare runs that were not produced under one contract."""
    if len(runs) < 2:
        raise SystemExit("fewer than two systems; nothing to compare")

    for field in CONTRACT:
        values = {name: run.get("contract", {}).get(field) for name, run in runs.items()}
        if None in values.values():
            raise SystemExit(f"contract field {field!r} missing from: "
                             f"{[n for n, v in values.items() if v is None]}")
        if len(set(values.values())) > 1:
            raise SystemExit(
                f"refusing to compare: systems did not share {field!r} — {values}. "
                "A comparison across differing conditions measures the condition."
            )

    probes = {name: {r["probe_id"] for r in run["records"]} for name, run in runs.items()}
    first = next(iter(probes.values()))
    for name, ids in probes.items():
        if ids != first:
            missing, extra = len(first - ids), len(ids - first)
            raise SystemExit(f"{name} was scored on a different probe set: "
                             f"{missing} missing, {extra} extra")

    for name, run in runs.items():
        for record in run["records"]:
            absent = [f for f in REQUIRED_FIELDS if f not in record]
            if absent:
                raise SystemExit(f"{name}: a record is missing {absent}")


def phi(a: list[int], b: list[int]) -> float | None:
    """Correlation of two binary vectors, or None when it does not exist.

    Never 0.0 for a constant vector. A system that never commits a given failure
    type yields a constant vector and no correlation exists for that pair — a
    correct result, and the one PMLAB-DECORR-E1 was built to report honestly.
    """
    n11 = sum(1 for x, y in zip(a, b) if x and y)
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if not x and y)
    n00 = sum(1 for x, y in zip(a, b) if not x and not y)
    denominator = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    if denominator == 0:
        return None
    return (n11 * n00 - n10 * n01) / denominator


def interaction(s0: float, sa: float, sb: float, sab: float) -> dict[str, float | str]:
    """S(A+B) - S(A) - S(B) + S0, with a reading attached."""
    value = sab - sa - sb + s0
    if abs(value) < 0.01:
        reading = "additive — the mechanisms address different failures"
    elif value < 0:
        reading = "redundant, or the mechanisms interfere"
    else:
        reading = "synergistic — the pair exceeds the sum of independent effects"
    return {
        "delta_a": round(sa - s0, 6), "delta_b": round(sb - s0, 6),
        "delta_ab": round(sab - s0, 6), "interaction": round(value, 6), "reading": reading,
    }


def correlate(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Binary error correlation, then one vector per failure type."""
    order = sorted(runs)
    probes = sorted({r["probe_id"] for r in runs[order[0]]["records"]})

    by_system: dict[str, dict[str, dict[str, Any]]] = {
        name: {r["probe_id"]: r for r in run["records"]} for name, run in runs.items()
    }

    binary = {name: [int(not by_system[name][p]["success"]) for p in probes] for name in order}
    typed: dict[str, dict[str, list[int]]] = {
        name: {t: [int(by_system[name][p].get("failure_type") == t) for p in probes]
               for t in FAILURE_TYPES}
        for name in order
    }

    pairs: dict[str, Any] = {}
    for index, first in enumerate(order):
        for second in order[index + 1:]:
            key = f"{first} vs {second}"
            overall = phi(binary[first], binary[second])
            per_type = {}
            for failure in FAILURE_TYPES:
                value = phi(typed[first][failure], typed[second][failure])
                per_type[failure] = {
                    "phi": None if value is None else round(value, 6),
                    "undefined_because": (
                        None if value is not None
                        else "at least one system's vector for this type is constant; "
                             "no correlation exists, and 0.0 would claim one"
                    ),
                }
            pairs[key] = {
                "phi_any_failure": None if overall is None else round(overall, 6),
                "by_failure_type": per_type,
                "note": ("two systems can share an overall error rate, fail on the same probes, and "
                         "still diverge once the type is separated"),
            }

    return {"probes": len(probes), "systems": order, "pairs": pairs}


def load(paths: list[Path]) -> dict[str, dict[str, Any]]:
    runs = {}
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        runs[payload["system"]] = payload
    return runs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path, help="per-system run files")
    parser.add_argument("--out", type=Path, default=None)
    arguments = parser.parse_args(argv)

    runs = load(arguments.runs)
    validate(runs)
    report = correlate(runs)

    print(f"Comparative lab — {len(report['systems'])} systems, {report['probes']} probes\n")
    for pair, block in report["pairs"].items():
        overall = block["phi_any_failure"]
        print(f"  {pair}")
        print(f"    phi(any failure)  {'undefined' if overall is None else f'{overall:+.3f}'}")
        for failure, cell in block["by_failure_type"].items():
            value = cell["phi"]
            print(f"      {failure:<20} {'undefined' if value is None else f'{value:+.3f}'}")
        print()

    if arguments.out:
        destination = arguments.out if arguments.out.is_absolute() else Path(arguments.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"written: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
