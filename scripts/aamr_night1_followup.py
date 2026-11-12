"""AAMR-NIGHT-1 follow-up analysis (EXPLORATORY, written after the results were read).

Reads only the frozen raw sessions (hashes checked against data/lab/aamr-night1/raw-freeze.json); never calls a model.
For every task whose outcome differs between a memory arm and N it finds the first model step where the two
trajectories diverge and asks whether any memory (a note after an error, or an R+ block) had been shown before it.
Before the first memory item both arms see byte-identical inputs, so a divergence there is run-to-run noise,
not an effect of memory. Also: stale-lesson compliance, token overhead of memory, error results.

    python scripts/aamr_night1_followup.py      -> data/lab/aamr-night1/followup.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aamr_night1_analysis as an  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data/lab/aamr-night1"
SESSIONS = ("sA", "sC", "sD", "sE")


def verify_freeze():
    fr = json.loads((LAB / "raw-freeze.json").read_text(encoding="utf-8"))
    root = Path(fr["raw_root"])
    bad = [rel for rel, h in fr["files"].items() if hashlib.sha256((root / rel).read_bytes()).hexdigest() != h]
    if bad:
        raise SystemExit(f"raw files changed since freeze: {bad}")
    return root, len(fr["files"])


def steps_with_memory(rec):
    """Flat list of (turn, step, text, memory_seen_before_this_step, memory_labels_before)."""
    out, seen, labels = [], False, []
    for t in rec["turns"]:
        if t.get("memory", {}).get("block_chars"):
            seen = True
            labels.append("block")
        for i, s in enumerate(t["steps"]):
            if "key" not in s:
                continue
            out.append((t["index"], i, s["text"], seen, list(labels)))
            if s.get("notes"):          # a note appended to this step's results is visible from the next step on
                seen = True
                labels.extend(s["notes"])
    return out


def divergence(a, n):
    sa, sn = steps_with_memory(a), steps_with_memory(n)
    for k in range(min(len(sa), len(sn))):
        if sa[k][2] != sn[k][2] or sa[k][0] != sn[k][0]:
            return {"turn": sa[k][0], "step": sa[k][1], "memory_before": sa[k][3], "labels": sa[k][4][-3:]}
    if len(sa) != len(sn):
        k = min(len(sa), len(sn))
        longer = sa if len(sa) > len(sn) else sn
        return {"turn": longer[k][0], "step": longer[k][1], "memory_before": (sa[k][3] if k < len(sa) else sa[-1][3]),
                "labels": (sa[k][4] if k < len(sa) else sa[-1][4])[-3:], "length_only": True}
    return None


def changed_outcomes(rows, arm):
    d = an.by_arm(rows)
    out = {"gains": [], "losses": []}
    for task, rec in d.get(arm, {}).items():
        base = d["N"].get(task)
        if base is None:
            continue
        a, b = rec["evaluation"]["solved"], base["evaluation"]["solved"]
        if a == b:
            continue
        dv = divergence(rec["episode"], base["episode"])
        row = {"task": task, "divergence": dv,
               "cause": "no_divergence" if dv is None else ("memory" if dv["memory_before"] else "noise_before_memory"),
               "first_fail_arm": rec["evaluation"]["first_fail"], "first_fail_N": base["evaluation"]["first_fail"]}
        out["gains" if a else "losses"].append(row)
    return out


def divergence_rate(rows, arm):
    d = an.by_arm(rows)
    n_div, n_noise, n = 0, 0, 0
    for task, rec in d.get(arm, {}).items():
        base = d["N"].get(task)
        if base is None:
            continue
        n += 1
        dv = divergence(rec["episode"], base["episode"])
        if dv is not None:
            n_div += 1
            n_noise += not dv["memory_before"]
    return {"episodes": n, "diverged": n_div, "diverged_before_any_memory": n_noise}


def stale_compliance(rows):
    d = an.by_arm(rows)
    out = {}
    for arm in ("TrO", "TrS", "TrP", "TrW", "TrQ", "TrF"):
        c, passed, turns = Counter(), 0, 0
        for task, rec in d.get(arm, {}).items():
            for ft in an.fuel_turns(rec["episode"], rec["evaluation"]):
                turns += 1
                passed += ft["passed"]
                c[ft["compliance"] or "no_refill"] += 1
        if turns:
            out[arm] = {"capacity_turns": turns, "passed": passed, "compliance": dict(c)}
    return out


def overhead(rows):
    d = an.by_arm(rows)
    tasks = an.complete_tasks(d, list(d), sorted(d["N"]))
    base = sum(an.prompt_tokens(d["N"][t]["episode"]) for t in tasks)
    res = {}
    for arm in d:
        tok = sum(an.prompt_tokens(d[arm][t]["episode"]) for t in tasks)
        calls = sum(d[arm][t]["evaluation"]["model_calls"] for t in tasks)
        errs = sum(d[arm][t]["evaluation"]["error_results"] for t in tasks)
        res[arm] = {"prompt_tokens": tok, "vs_N_pct": round(100 * (tok - base) / base, 1), "model_calls": calls, "error_results": errs}
    return res


def main():
    root, nfiles = verify_freeze()
    out = {"status": "exploratory, written after results were read", "raw_files_verified": nfiles, "sessions": {}}
    for s in SESSIONS:
        rows = an.rows_of(root, s)
        arms = sorted({r["arm"] for r in rows} - {"N"})
        sec = {"changed_outcomes": {}, "divergence": {}, "overhead": overhead(rows)}
        for arm in arms:
            ch = changed_outcomes(rows, arm)
            sec["changed_outcomes"][arm] = {
                "gains": len(ch["gains"]), "losses": len(ch["losses"]),
                "gains_by_cause": dict(Counter(x["cause"] for x in ch["gains"])),
                "losses_by_cause": dict(Counter(x["cause"] for x in ch["losses"])),
                "detail": ch}
            sec["divergence"][arm] = divergence_rate(rows, arm)
        if s in ("sA", "sC", "sE"):
            sec["fuel_compliance"] = stale_compliance(rows)
        out["sessions"][s] = sec
    (LAB / "followup.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for s, sec in out["sessions"].items():
        print(f"== {s}")
        for arm, v in sec["changed_outcomes"].items():
            dv = sec["divergence"][arm]
            print(f"  {arm:4} +{v['gains']} -{v['losses']}  gains {v['gains_by_cause']}  losses {v['losses_by_cause']}  "
                  f"diverged {dv['diverged']}/{dv['episodes']} (before memory {dv['diverged_before_any_memory']})")
        print("  overhead", {a: (v["vs_N_pct"], v["error_results"]) for a, v in sec["overhead"].items()})
        if "fuel_compliance" in sec:
            print("  fuel", sec["fuel_compliance"])


if __name__ == "__main__":
    main()
