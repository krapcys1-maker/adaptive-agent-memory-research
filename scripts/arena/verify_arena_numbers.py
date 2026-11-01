#!/usr/bin/env python3
"""Recompute the numbers the evidence ledger quotes for Entry H, offline.

Entry H of docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md claims that
appending the raw source session behind Mem0's top-1 retrieval hit to its
compact context ("compact_plus_raw") repaired one unit in each of two samples
(E3: 9 observable units; fresh replication: 8 units), with no regressions.

This script reads the tracked result files, recomputes every number the ledger
quotes for Entry H, compares them with the numbers it parses out of the ledger
text, and prints per-unit context token counts for compact versus
compact_plus_raw, because the plus-raw arm is about twenty times longer and the
data cannot separate "more of the right text" from "simply more text".

Properties: standard library only, no network, no API key, no files outside the
repository, writes nothing.

Exit status: 0 every check passed; 1 at least one recomputed number differs
from the ledger's quoted number; 2 usage error or a required file is missing
or malformed.

Usage: python scripts/arena/verify_arena_numbers.py [--repo PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from math import comb
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LEDGER = Path("docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md")
FRESH = Path("data/lab/arena/raw-provenance-fresh-replication-v1/results.json")
E3_ARMS = Path("data/lab/arena/base-plus-x-v2/e3-arms.json")
E3_JUDGED = Path("data/lab/arena/base-plus-x-v2/e3-judged.json")
E3_ANALYSIS = Path("data/lab/arena/base-plus-x-v2/e3-analysis.json")
BREADTH_ARMS = Path("data/lab/arena/mem0-breadth-arms.json")
BREADTH_JUDGED = Path("data/lab/arena/mem0-breadth-judged.json")

ARMS = ("mem0_compact", "mem0_compact_plus_raw", "mem0_raw_only")


class InputError(Exception):
    """A required file is missing, outside the repository, or malformed."""


class Report:
    def __init__(self) -> None:
        self.failures: List[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        print(("PASS  " if ok else "FAIL  ") + name + (("  | " + detail) if detail else ""))
        if not ok:
            self.failures.append(name)

    @staticmethod
    def note(text: str) -> None:
        print("NOTE  " + text)


def read_text(repo: Path, rel: Path) -> str:
    path = (repo / rel).resolve()
    try:
        path.relative_to(repo)
    except ValueError:
        raise InputError("refusing to read outside the repository: " + str(path))
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError("cannot read " + str(rel) + ": " + str(exc))


def load_json(repo: Path, rel: Path) -> Any:
    try:
        return json.loads(read_text(repo, rel))
    except ValueError as exc:
        raise InputError("not valid JSON: " + str(rel) + ": " + str(exc))


def label_true(judged: Any) -> bool:
    return bool(judged.get("label") is True)


# --------------------------------------------------------------------------- ledger
def entry_h_text(ledger: str) -> str:
    start = ledger.find("## Entry H")
    if start < 0:
        raise InputError("ledger has no 'Entry H' heading")
    end = ledger.find("\n---", start)
    return ledger[start:end if end > 0 else len(ledger)]


def quoted(ledger: str) -> Dict[str, Any]:
    """Numbers the ledger quotes for Entry H, parsed from its prose."""
    h = entry_h_text(ledger)
    triples = re.findall(r"compact (\d+)/(\d+), compact\+raw \*\*(\d+)/(\d+)\*\*, raw-only (\d+)/(\d+)", h)
    repairs = re.findall(r"1 repair \(`([0-9a-f]{8})`", h)
    spend = re.search(r"replication \$(\d+\.\d+)", h)
    units = re.search(r"across (\d+) combined observable units", h)
    overhead = re.search(r"~(\d+\.\d)x token overhead", ledger)
    if len(triples) != 2 or len(repairs) != 2 or not spend or not units:
        raise InputError("could not parse the Entry H figures out of the ledger text")
    return {
        "e3": tuple(int(x) for x in triples[0]),
        "fresh": tuple(int(x) for x in triples[1]),
        "e3_repair": repairs[0],
        "fresh_repair": repairs[1],
        "fresh_spend": spend.group(1),
        "units_total": int(units.group(1)),
        "zero_regressions": "Zero regressions in both runs" in h,
        "overhead": float(overhead.group(1)) if overhead else None,
    }


# --------------------------------------------------------------------------- statistics
def mcnemar_exact(b: int, c: int) -> Tuple[float, float]:
    n = b + c
    if n == 0:
        return 1.0, 1.0
    k = min(b, c)
    one = sum(comb(n, i) for i in range(0, k + 1)) / 2.0 ** n
    return one, min(1.0, 2 * one)


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    def cdf(x: int, p: float) -> float:
        return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, x + 1))

    lo, hi = 0.0, 1.0
    if k > 0:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if 1 - cdf(k - 1, m) < alpha / 2:
                a = m
            else:
                b = m
        lo = (a + b) / 2
    if k < n:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if cdf(k, m) > alpha / 2:
                a = m
            else:
                b = m
        hi = (a + b) / 2
    return lo, hi


# --------------------------------------------------------------------------- recompute
def fresh_sample(repo: Path) -> Dict[str, Any]:
    data = load_json(repo, FRESH)
    rows = []
    for unit in data["results"]:
        arms = unit["arms"]
        rows.append({
            "id": unit["question_id"],
            "type": unit["question_type"],
            "label": {a: label_true(arms[a]["judged"]) for a in ARMS},
            "tokens": {a: int(arms[a]["context_tokens"]) for a in ARMS},
            "observable": bool(arms["mem0_compact_plus_raw"]["gold_state"]["observable"]),
        })
    return {"rows": rows, "spend": data["spend"]["total_usd"]}


def e3_sample(repo: Path) -> Dict[str, Any]:
    arms = load_json(repo, E3_ARMS)["arms"]
    plus_arms = {a["question_id"]: a for a in arms if a["arm"] == "mem0_compact_plus_raw"}
    observable = sorted(plus_arms)
    judged = load_json(repo, E3_JUDGED)["judgements"]
    plus = {j["question_id"]: label_true(j) for j in judged if j["_arm"] == "mem0_compact_plus_raw"}
    only = {j["question_id"]: label_true(j) for j in judged if j["_arm"] == "mem0_raw_only"}
    compact = {j["question_id"]: label_true(j)
               for j in load_json(repo, BREADTH_JUDGED)["judgements"] if j["_arm"] == "mem0_original"}
    compact_tokens = {a["question_id"]: int(a["context_tokens"])
                      for a in load_json(repo, BREADTH_ARMS)["arms"] if a["arm"] == "mem0_original"}
    rows = []
    for q in observable:
        rows.append({
            "id": q,
            "type": plus_arms[q]["question_type"],
            "label": {"mem0_compact": compact[q], "mem0_compact_plus_raw": plus[q], "mem0_raw_only": only[q]},
            "compact_tokens": compact_tokens[q],
            "raw_session_tokens": int(plus_arms[q]["provenance_tokens"]),
        })
    analysis = load_json(repo, E3_ANALYSIS)
    return {"rows": rows, "analysis_fixes": analysis.get("COMPACT_WRONG_RAW_FIXES"),
            "analysis_scores": analysis.get("scores")}


def flips(rows: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    rep = [r["id"] for r in rows if not r["label"]["mem0_compact"] and r["label"]["mem0_compact_plus_raw"]]
    reg = [r["id"] for r in rows if r["label"]["mem0_compact"] and not r["label"]["mem0_compact_plus_raw"]]
    return rep, reg


def tally(rows: List[Dict[str, Any]]) -> Tuple[int, ...]:
    out: List[int] = [len(rows)]
    for a in ARMS:
        out.append(sum(1 for r in rows if r["label"][a]))
    return tuple(out)


def run(repo: Path) -> int:
    rep = Report()
    q = quoted(read_text(repo, LEDGER))
    fresh = fresh_sample(repo)
    e3 = e3_sample(repo)

    print("== Entry H: fresh replication (8 gold-blind units) ==")
    n, c, p, o = tally(fresh["rows"])
    qf = q["fresh"]
    rep.check("fresh: compact / compact+raw / raw-only correct = ledger " + "%d/%d, %d/%d, %d/%d" % (qf[0], qf[1], qf[2], qf[3], qf[4], qf[5]),
              (c, n, p, n, o, n) == qf, "recomputed %d/%d, %d/%d, %d/%d" % (c, n, p, n, o, n))
    f_rep, f_reg = flips(fresh["rows"])
    rep.check("fresh: repairs = [%s] (ledger), regressions = 0" % q["fresh_repair"],
              f_rep == [q["fresh_repair"]] and f_reg == [] and q["zero_regressions"], "repairs=%s regressions=%s" % (f_rep, f_reg))
    rep.check("fresh: all 8 units observable", all(r["observable"] for r in fresh["rows"]) and n == 8)
    rep.check("fresh: recorded spend = ledger $%s" % q["fresh_spend"], "%.6f" % float(fresh["spend"]) == q["fresh_spend"],
              "results.json says %s" % fresh["spend"])

    print("\n== Entry H: E3 original sample (9 observable units) ==")
    n3, c3, p3, o3 = tally(e3["rows"])
    q3 = q["e3"]
    rep.check("E3: compact / compact+raw / raw-only correct = ledger %d/%d, %d/%d, %d/%d" % (q3[0], q3[1], q3[2], q3[3], q3[4], q3[5]),
              (c3, n3, p3, n3, o3, n3) == q3, "recomputed %d/%d, %d/%d, %d/%d" % (c3, n3, p3, n3, o3, n3))
    e_rep, e_reg = flips(e3["rows"])
    rep.check("E3: repairs = [%s] (ledger), regressions = 0" % q["e3_repair"],
              e_rep == [q["e3_repair"]] and e_reg == [] and q["zero_regressions"], "repairs=%s regressions=%s" % (e_rep, e_reg))
    rep.check("E3: agrees with the stored e3-analysis.json",
              e3["analysis_fixes"] == e_rep and e3["analysis_scores"] == {
                  "compact_native_base_9_observable": "%d/%d" % (c3, n3),
                  "compact_plus_raw": "%d/%d" % (p3, n3), "raw_only": "%d/%d" % (o3, n3)},
              "stored scores %s" % (e3["analysis_scores"],))

    print("\n== Entry H: combined ==")
    total = n + n3
    rep.check("combined observable units = ledger %d" % q["units_total"], total == q["units_total"], "recomputed %d" % total)
    b, cc = len(f_rep) + len(e_rep), len(f_reg) + len(e_reg)
    rep.note("combined: %d repairs, %d regressions in %d observable units." % (b, cc, total))
    types = dict((r["id"], r["type"]) for r in fresh["rows"] + e3["rows"])
    rep.note("question types of the repaired units: %s" % ", ".join("%s = %s" % (u, types[u]) for u in f_rep + e_rep))
    one, two = mcnemar_exact(b, cc)
    lo, hi = clopper_pearson(b, total)
    rep.note("exact McNemar p = %.3f (one-sided), %.3f (two-sided); 95%% Clopper-Pearson interval for the repair rate %.3f to %.3f. "
             "This is a small-sample descriptive result, not a significance claim." % (one, two, lo, hi))

    print("\n== Context length: compact vs compact_plus_raw (the length confound) ==")
    print("fresh replication, tokens as stored in results.json")
    print("  %-10s %-26s %8s %8s %8s %8s" % ("unit", "type", "compact", "+raw", "raw_only", "ratio"))
    ratios = []
    additive = True
    for r in fresh["rows"]:
        t = r["tokens"]
        ratio = t["mem0_compact_plus_raw"] / float(t["mem0_compact"])
        ratios.append(ratio)
        additive = additive and t["mem0_compact_plus_raw"] == t["mem0_compact"] + t["mem0_raw_only"]
        print("  %-10s %-26s %8d %8d %8d %7.1fx" % (r["id"], r["type"], t["mem0_compact"], t["mem0_compact_plus_raw"], t["mem0_raw_only"], ratio))
    mean_ratio = sum(ratios) / len(ratios)
    pooled = sum(r["tokens"]["mem0_compact_plus_raw"] for r in fresh["rows"]) / float(sum(r["tokens"]["mem0_compact"] for r in fresh["rows"]))
    print("  mean of per-unit ratios %.2fx (min %.1fx, max %.1fx); pooled ratio %.2fx" % (mean_ratio, min(ratios), max(ratios), pooled))
    rep.check("fresh: compact_plus_raw tokens == compact tokens + raw_only tokens for every unit", additive)
    if q["overhead"] is not None:
        rep.check("fresh: mean per-unit overhead rounds to the ledger's ~%.1fx" % q["overhead"], round(mean_ratio, 1) == q["overhead"],
                  "recomputed %.2fx" % mean_ratio)
    print("E3 sample, DERIVED: the E3 files store no token count for the plus-raw context, so it is taken as compact tokens")
    print("(mem0-breadth-arms.json) + raw session tokens (e3-arms.json); the fresh data above shows this sum is exact there.")
    print("  %-14s %-18s %8s %8s %8s" % ("unit", "type", "compact", "+raw", "ratio"))
    for r in e3["rows"]:
        plus_tokens = r["compact_tokens"] + r["raw_session_tokens"]
        print("  %-14s %-18s %8d %8d %7.1fx" % (r["id"], r["type"], r["compact_tokens"], plus_tokens, plus_tokens / float(r["compact_tokens"])))
    rep.note("The plus-raw arm carries roughly 5x to 32x more context than compact. raw_only is about as long as plus-raw yet scored "
             "lower (4/8 and 4/9 against 6/8 and 6/9), so length alone does not explain the repairs; but no arm here holds length "
             "fixed while removing the relevant text, so these files cannot rule length out either.")

    print("")
    if rep.failures:
        print("%d check(s) FAILED: a recomputed number differs from the ledger." % len(rep.failures))
        return 1
    print("all checks passed")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recompute, offline, the numbers the evidence ledger quotes for Entry H and print per-unit "
                    "context token counts for compact vs compact_plus_raw. Exit 0 = all match, 1 = a number differs, "
                    "2 = usage error or missing/malformed input.")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]),
                        help="repository root (default: the checkout this script is in)")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    if not (repo / "data" / "lab" / "arena").is_dir():
        print("not a repository checkout (no data/lab/arena): " + str(repo), file=sys.stderr)
        return 2
    try:
        return run(repo)
    except InputError as exc:
        print("input error: " + str(exc), file=sys.stderr)
        return 2
    except (KeyError, IndexError, TypeError) as exc:
        print("input error: unexpected structure in a result file (%s: %s)" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
