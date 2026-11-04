"""Read-only public-data comparison of both frozen lexical kernel lines (#72).

Protocol: docs/00-project/lexical-gate-evaluation-protocol-2026-11-04.md.
Standard library only; no defaults, source data, weights or private R1 text change.
Run: python scripts/wmb/lexical_gate_eval.py --output NEW_RESULTS.json
"""
from __future__ import annotations

import argparse
import dataclasses
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
KERNEL_PATHS = (Path("scripts/wmb/memory_kernel.py"), Path("scripts/wmb/kernel/memory_kernel.py"))
BS = (0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0)
LEX_TAUS, TOP_TERMS = (0.05, 0.10, 0.15, 0.20, 0.30, 0.45), (0, 3, 5, 10, 20)
RESAMPLES, SEED = 2000, 1729
NOW_PERSONA = "2026-12-01T00:00:00Z"


def load_kernel(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def end_of_day(day):
    return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day - 1, hours=23, minutes=59)).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclasses.dataclass
class Suite:
    name: str
    items: list
    questions: list
    task_type: str
    files: list
    exclusions: list
    limitation: str


def suites(root=ROOT):
    h = root / "data/lab/corpus-h1"
    files = [h / "prefix-v0/history.jsonl", h / "reveal-v0/queries.jsonl", h / "reveal-v0/gold.jsonl"]
    history, queries, gold = (rows(p) for p in files)
    answers = {r["query_id"]: r["gold_event_id"] for r in gold}
    result = [Suite("H1", [(r["event_id"], r["timestamp"], r["text"]) for r in history],
                    [(q["query_id"], q["question"], end_of_day(q["asked_on_day"]), {answers[q["query_id"]]}) for q in queries],
                    "note", files, [], "Authored single-event retrieval gold; not downstream answer success.")]
    path = root / "data/lab/aam-e6-persona/persona.json"
    persona = json.loads(path.read_text(encoding="utf-8"))
    bio = persona["biography"]
    questions, exclusions = [], []
    for q in persona["fact_questions"]:
        patterns = [re.compile(r"(?<!\w)" + re.escape(k).replace(r"\ ", r"\s+") + r"(?!\w)", re.I) for k in q["keys"]]
        matched = {b["id"] for b in bio if any(p.search(b["text"]) for p in patterns)}
        if matched:
            questions.append((q["id"], q["q"], NOW_PERSONA, matched))
        else:
            exclusions.append({"id": q["id"], "reason": "no biography item contains an authored answer key"})
    result.append(Suite("E6", [(b["id"], b["date"], b["text"]) for b in bio], questions,
                        "personal", [path], exclusions, "R1-style any-answer-key match proxy; a hit need not fully support a multi-key answer."))
    for split in ("dev", "valid"):
        h = root / ("data/lab/corpus-h2/" + split)
        files = [h / (n + ".jsonl") for n in ("events", "queries", "gold")]
        history, queries, gold = (rows(p) for p in files)
        answers = {r["query_id"]: r["gold_event_id"] for r in gold}
        items = [(r["event_id"], end_of_day(r["recorded_on"])[:10] + "T00:00:00Z", r["text"]) for r in history]
        result.append(Suite("H2-" + split, items,
                            [(q["query_id"], q["question"], end_of_day(q["asked_on"]), {answers[q["query_id"]]}) for q in queries],
                            "note", files, [], "Recorded-time availability only: no oracle valid-time or supersession filtering; not a temporal answer resolver or sealed confirmation."))
    return result


def rank_grid():
    settings = [(b, 1.2) for b in BS] + [(0.75, 0.5), (0.75, 2.0)]
    return [dict(b=b, k1=k1, max_terms=cap, top_terms=10, names=False, embed="off", k=10,
                 lex_tau=1e-9, min_evidence=0.0) for (b, k1), cap in itertools.product(settings, (20, 0))]


def gate_grid():
    return [dict(b=0.75, k1=1.2, max_terms=20, top_terms=top, names=False, embed="off", k=3,
                 lex_tau=tau, min_evidence=1.4) for tau, top in itertools.product(LEX_TAUS, TOP_TERMS)]


def difference(base, tested, resamples=RESAMPLES, seed=SEED):
    if len(base) != len(tested) or not base:
        raise ValueError("paired non-empty observations required")
    delta = [b - a for a, b in zip(base, tested)]
    mean = sum(delta) / len(delta)
    if len(set(delta)) == 1:
        low = high = mean
    else:
        rng = random.Random(seed)
        boot = sorted(sum(rng.choices(delta, k=len(delta))) / len(delta) for _ in range(resamples))
        low, high = boot[int(0.025 * resamples)], boot[min(resamples - 1, int(0.975 * resamples))]
    return {"difference": round(mean, 6), "ci95": [round(low, 6), round(high, 6)],
            "coverage_only": sum(a and not b for a, b in zip(base, tested)),
            "tested_only": sum(b and not a for a, b in zip(base, tested))}


def rankings(mk, index, suite, profile):
    out = []
    for ident, question, now, gold in suite.questions:
        result = mk.retrieve(index, question, suite.task_type, now, profile)
        if result["status"] not in ("ok", "degraded"):
            raise ValueError("retrieval failed in %s/%s: %s" % (suite.name, ident, result["status"]))
        out.append([it.id for it in result["items"]])
    return out


def hits(suite, ranked, k):
    return [int(bool(set(ids[:k]) & gold)) for (_, _, _, gold), ids in zip(suite.questions, ranked)]


def gate_row(mk, index, suite, profile, negative_questions):
    ranked = rankings(mk, index, suite, profile)
    unrelated = []
    for q in negative_questions:
        result = mk.retrieve(index, q, suite.task_type, NOW_PERSONA, profile)
        if result["status"] not in ("ok", "degraded"):
            raise ValueError("unrelated retrieval failed")
        unrelated.append(bool(result["items"]))
    n, u = len(ranked), len(unrelated)
    return {"profile": profile, "queries": n, "fired": sum(bool(r) for r in ranked),
            "fired_share": round(sum(bool(r) for r in ranked) / n, 6),
            "gold_shown": sum(hits(suite, ranked, 3)), "gold_shown_share": round(sum(hits(suite, ranked, 3)) / n, 6),
            "unrelated_queries": u, "unrelated_fired": sum(unrelated),
            "unrelated_fired_share": round(sum(unrelated) / u, 6)}


def evaluate(selected=None):
    modules = [load_kernel(ROOT / p, "lexical_eval_" + str(i)) for i, p in enumerate(KERNEL_PATHS)]
    all_suites = suites()
    negatives = {s.name: [q[1] for q in next(t for t in all_suites if t.name == ("H1" if s.name == "E6" else "E6")).questions] for s in all_suites}
    results = []
    for suite in all_suites:
        if selected and suite.name not in selected:
            continue
        origin = "fiction_autobio" if suite.name == "E6" else "account_history"
        indices = [mk.build_index([mk.Item(i, "event", origin, date, text) for i, date, text in suite.items], "2099-01-01") for mk in modules]
        if any(len(idx.items) != len(suite.items) for idx in indices):
            raise ValueError("an adapter item was rejected")
        base_profile = dict(k=10, lex_tau=1e-9, min_evidence=0.0, embed="off", names=False)
        base = rankings(modules[0], indices[0], suite, base_profile)
        base_hits = {k: hits(suite, base, k) for k in (1, 3, 10)}
        rank_rows = []
        for profile in rank_grid():
            ranked = rankings(modules[1], indices[1], suite, profile)
            metrics = {}
            for k in (1, 3, 10):
                tested = hits(suite, ranked, k)
                metrics[str(k)] = dict(recall=round(sum(tested) / len(tested), 6), **difference(base_hits[k], tested))
            rank_rows.append({"profile": profile, "metrics": metrics, "rankings": ranked})
        coverage_profile = dict(modules[0].PROFILES["lexical"], k=3, names=False)
        result = {"suite": suite.name, "items": len(suite.items), "queries": len(suite.questions),
                  "query_ids": [q[0] for q in suite.questions], "exclusions": suite.exclusions,
                  "limitation": suite.limitation,
                  "negative_bank": "H1 operational questions" if suite.name == "E6" else "E6 personal fact questions",
                  "input_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in suite.files},
                  "coverage": {"profile": base_profile, "recall": {str(k): round(sum(v) / len(v), 6) for k, v in base_hits.items()}, "rankings": base},
                  "rank_rows": rank_rows,
                  "coverage_gate": gate_row(modules[0], indices[0], suite, coverage_profile, negatives[suite.name]),
                  "gate_rows": [gate_row(modules[1], indices[1], suite, p, negatives[suite.name]) for p in gate_grid()]}
        results.append(result)
        print(suite.name, "queries", len(suite.questions), "coverage", result["coverage"]["recall"], flush=True)
    return {"protocol": "docs/00-project/lexical-gate-evaluation-protocol-2026-11-04.md",
            "tier": "descriptive exploratory; no tuned default selected", "license": "repository Apache-2.0 authored fixtures",
            "bootstrap_resamples": RESAMPLES, "bootstrap_seed": SEED,
            "kernel_sha256": {p.as_posix(): hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in KERNEL_PATHS},
            "suites": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--suite", action="append", choices=("H1", "E6", "H2-dev", "H2-valid"))
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output must be new; historical results are never overwritten")
    before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in KERNEL_PATHS}
    result = evaluate(args.suite)
    if any(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != sha for p, sha in before.items()):
        raise ValueError("kernel source changed during evaluation")
    result["kernel_files_unchanged"] = True
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
