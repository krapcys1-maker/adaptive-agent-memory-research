"""Read-only cost-normalization of surviving per-query records (issue 38).

Never infer a historical ranking from a fresh search. Missing token counts are
reported as unavailable, not zero; no metric is computed on a biased subset.
Only explicit whitespace-count schemas used by the named runners are supported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from retrieval_metrics import definition, efficiency

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = [
    "data/lab/corpus-h1/baseline-v0.1-rerun-2026-11-01/results.json",
    "data/lab/corpus-h1/address-probe-v0/results.json",
    "data/lab/pmlab-xlang-e1/execution-v0/results.json",
    "data/lab/pmlab-xlang-e2/execution-v0/results.json",
    "data/lab/pmlab-assoc-e3/execution-v0/results.json",
]


def summarize(data):
    rows = data.get("records", [])
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError("expected a list of per-query record objects")
    keys = {key for r in rows for key in r}
    specs = {}
    for key in sorted(keys):
        match = re.fullmatch(r"recall@(\d+)", key)
        if match:
            specs[key] = (key, "retrieved_tokens@" + match[1])
        match = re.fullmatch(r"(b\d+)_hit@(\d+)", key)
        if match:
            specs[match[1] + "@" + match[2]] = (key, match[1] + "_retrieved_tokens@" + match[2])
        match = re.fullmatch(r"(lexical|addressed)_gold", key)
        if match:
            specs[match[1]] = (key, match[1] + "_tokens")
    group_field = "stratum" if "stratum" in keys else "language" if "language" in keys else None
    groups = sorted({r[group_field] for r in rows}) if group_field else ["all"]
    result = {}
    for group in groups:
        subset = [r for r in rows if not group_field or r[group_field] == group]
        metrics = {}
        for name, (hit, cost) in specs.items():
            available = [r for r in subset if r.get(hit) is not None and r.get(cost) is not None]
            if len(available) != len(subset):
                metrics[name] = {"status": "unavailable", "queries": len(subset),
                                 "missing_cost_or_recall_rows": len(subset) - len(available),
                                 "recall_per_1k_tokens": None}
            else:
                metrics[name] = dict(status="recomputed", **efficiency([r[hit] for r in subset], [r[cost] for r in subset]))
        result[group] = metrics
    complete = bool(specs) and all(m["status"] == "recomputed" for block in result.values() for m in block.values())
    return {"experiment_id": data.get("summary", {}).get("experiment_id"),
            "interpretation_caveats": {key: data.get("summary", {})[key] for key in
                                       ("authority", "safety_caveat", "gold_recall_is_tautological", "what_is_oracle", "not_measured")
                                       if key in data.get("summary", {})},
            "status": "recomputed" if complete else "unavailable-or-incomplete",
            "grouping": group_field or "all", "groups": result,
            "limitation": None if complete else "Historical costs/rankings were not fully recorded; no fresh-search reconstruction or complete-case-only estimate was substituted."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output must be a new file, preserving historical artifacts")
    paths = args.input or [ROOT / p for p in DEFAULT_INPUTS]
    records = []
    for path in paths:
        raw = path.read_bytes()
        label = path.resolve().relative_to(ROOT).as_posix() if path.resolve().is_relative_to(ROOT) else path.name
        records.append(dict(source=label, source_sha256=hashlib.sha256(raw).hexdigest(),
                            **summarize(json.loads(raw))))
        if path.read_bytes() != raw:
            raise ValueError("input changed during read-only analysis")
    report = {"definition": definition("original runner's recorded item-text whitespace counts"),
              "historical_results_overwritten": False, "records": records}
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    for row in records:
        print(row["source"], row["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
