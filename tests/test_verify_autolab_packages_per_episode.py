"""Tests for verify_autolab_packages.py: per-episode means table recomputation, per-step split and pair coverage."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import os
import random
import subprocess
import sys
from pathlib import Path
from statistics import NormalDist
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _verifier_path() -> Path:
    env = os.environ.get("VERIFY_AUTOLAB_SCRIPT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1] / "scripts" / "verify_autolab_packages.py"


def _load_verifier():
    path = _verifier_path()
    spec = importlib.util.spec_from_file_location("verify_autolab_packages", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["verify_autolab_packages"] = mod
    spec.loader.exec_module(mod)
    return mod


V = _load_verifier()

ARMS = ["none", "placebo", "retrieved_task", "retrieved_steps", "retrieved_plan"]
TREATMENTS = ["retrieved_task", "retrieved_steps", "retrieved_plan"]


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _make_obj(kind: str, program: str, payload: Dict[str, Any], parents: Sequence[str],
              cycle: Optional[int], created_by: str = "code") -> Dict[str, Any]:
    ps = sorted(set(parents))
    body = {"kind": kind, "program": program, "payload": payload, "parents": ps}
    sha = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    return {
        "id": f"{kind}:{sha[:16]}",
        "kind": kind,
        "program": program,
        "cycle": cycle,
        "created_at": "2026-11-21T12:00:00+00:00",
        "created_by": created_by,
        "sha256": sha,
        "parents": ps,
        "payload": payload,
    }


def _paired_ci(g: int, lo_cnt: int, n: int, z: float) -> Tuple[float, float]:
    d = (g - lo_cnt) / n
    var = max(((g + lo_cnt) / n - d * d) / n, 0.0)
    se = var ** 0.5 if var > 0 else 1.0 / n
    return d - z * se, d + z * se


def _state(lo: float, hi: float, sesoi: float) -> str:
    if lo >= sesoi:
        return "practical"
    if lo > 0:
        return "positive"
    if hi < 0:
        return "negative"
    if lo > -sesoi and hi < sesoi:
        return "equivalent"
    return "inconclusive"


def _compute_process_balance(rows: List[Dict[str, Any]], crit: Dict[str, float], behaviour: Sequence[str],
                             rule: str, *, pair_coverage: bool = True) -> Dict[str, Any]:
    by: Dict[str, Dict[str, Dict[str, Any]]] = {}
    present: set = set()
    for r in rows:
        if r["seed"] != 0:
            continue
        present |= {k for k, v in r.items() if v != "" and v is not None}
        by.setdefault(r["arm"], {})[r["unit"]] = r
    skip = {"cycle", "unit", "arm", "seed", "solved", "n_memory_sources", "error",
            "steps", "max_steps", "max_tokens", "memory_tokens", "tokens", "seconds"}
    keys = sorted({k for ms in by.values() for m in ms.values() for k, v in m.items()
                   if isinstance(v, int) and not isinstance(v, bool) and k not in skip and not k.startswith("max_")}
                  | set(crit))

    def rate(ms, units, k):
        st = sum(float(ms[u]["steps"]) for u in units)
        return sum(float(ms[u].get(k) or 0) for u in units) / st if st else 0.0

    def is_num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    rates = {a: {k: round(rate(ms, list(ms), k), 4) for k in keys} for a, ms in sorted(by.items())}
    pl = by["placebo"]
    beh = set(behaviour) - set(crit)
    rng = random.Random(V.LAB_BOOT_SEED)
    per_arm: Dict[str, Dict[str, Any]] = {}
    for a in TREATMENTS:
        ms = by[a]
        units = sorted(set(ms) & set(pl))
        samples = [[rng.choice(units) for _ in units] for _ in range(V.LAB_BOOT_N)]
        out = {}
        for k in keys:
            tol = crit.get(k, V.LAB_PROCESS_TOL)
            fmt = k in crit or (k not in beh and any(m in k.lower() for m in V.FORMAT_MARKERS))
            if pair_coverage:
                cu = [u for u in units if is_num(ms[u].get(k)) and is_num(pl[u].get(k))]
                cov = {
                    "variant": sum(1 for u in units if is_num(ms[u].get(k))),
                    "placebo": sum(1 for u in units if is_num(pl[u].get(k))),
                    "complete_pairs": len(cu),
                    "pairs": len(units),
                }
                if not cu:
                    one = ("variant" if cov["variant"] and not cov["placebo"] else
                           "placebo" if cov["placebo"] and not cov["variant"] else None)
                    entry: Dict[str, Any] = {
                        "diff": None, "ci": None, "tolerance": tol, "preregistered": k in crit,
                        "format_counter": k in crit or fmt, "imbalanced": False, "state": "not_computable",
                        "coverage": cov,
                    }
                    if one:
                        entry["one_sided"] = one
                    out[k] = entry
                    continue
                use, smp = units, samples
            else:
                use, smp = units, samples
            d = rate(ms, use, k) - rate(pl, use, k)
            bs = sorted(rate(ms, s, k) - rate(pl, s, k) for s in smp)
            lo, hi = bs[int(0.025 * V.LAB_BOOT_N)], bs[int(0.975 * V.LAB_BOOT_N) - 1]
            imb = abs(d) > tol and not lo <= 0 <= hi
            st = "imbalanced" if imb else "balanced" if (-tol <= lo and hi <= tol) else "unresolved"
            entry = {
                "diff": round(d, 4), "ci": [round(lo, 4), round(hi, 4)], "tolerance": tol,
                "preregistered": k in crit, "format_counter": fmt, "imbalanced": imb, "state": st,
            }
            if k in crit and rule != "equivalence":
                entry["rule"] = rule
            out[k] = entry
        per_arm[a] = out
    return {
        "checked": True, "rates": rates, "per_arm": per_arm, "criteria": crit, "not_computable": [],
        "metrics_coverage": 1.0, "behaviour_counters": sorted(beh), "format_rule": rule,
    }


def _write_manifest(pkg: Path, pid: str) -> None:
    pub = []
    for p in sorted(pkg.iterdir()):
        if p.name == "PUBLISHED_FILES.json":
            continue
        data = p.read_bytes()
        h = hashlib.sha256(data).hexdigest()
        pub.append({"path": p.name, "target": f"data/lab/{pkg.name}/{p.name}",
                    "sha256": h, "sha256_source": h, "bytes": len(data), "edits": ["none"]})
    doc = {"task": f"autolab {pid}", "published": pub, "private": [], "paths_are_relative": True}
    (pkg / "PUBLISHED_FILES.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")


def _build_package(
    tmp_path: Path,
    *,
    n_units: int = 24,
    split_tables: bool = True,
    min_tokens_by_arm: Optional[Dict[str, int]] = None,
    include_per_episode_cols: bool = True,
    include_min_tokens_in_csv: bool = True,
    include_min_tokens_in_per_episode: bool = False,
    omit_per_episode_cols: Sequence[str] = (),
    extra_per_episode_cols: Sequence[str] = (),
    extra_per_step_cols: Sequence[str] = (),
    pair_coverage: bool = True,
    extra_seed_rows: bool = False,
) -> Path:
    pid = "V6-VERIFIER-TEST"
    sesoi = 0.12
    crit = {"empty_retries": 0.03, "untagged_not_truncated": 0.03}
    behaviour = ["invalid_no_action_tag"]
    rule = "imbalance_only"
    units = [f"u{i:03d}" for i in range(n_units)]
    seeds = [0, 1] if extra_seed_rows else [0]

    rows: List[Dict[str, Any]] = []
    for seed in seeds:
        for i, u in enumerate(units):
            base_block = 800 + (i % 4) * 10
            for arm in ARMS:
                if seed == 1:
                    rows.append({
                        "cycle": 1, "unit": u, "arm": arm, "seed": 1, "solved": 0, "steps": 999,
                        "empty_retries": 0, "invalid_no_action_tag": 0, "invalid_actions": 0,
                        "memory_tokens": 99999, "truncated": 0, "untagged_not_truncated": 0,
                        "top1_similarity": 0.99, "memory_similarity": 0.99, "tokens": 999999,
                        "content_tokens": 99999, "matched_block_tokens": 99999,
                        "block_length_diff": 0.5, "min_tokens": 8,
                        "plan_digit_count": 99 if arm == "retrieved_plan" else "",
                        "steps_observation_count": 99 if arm == "retrieved_steps" else "",
                        "n_memory_sources": 0, "error": 0,
                    })
                    continue
                if arm == "none":
                    solved, steps, mem_tok, content_tok, matched_tok = int(i % 2 == 0), 35, 0, 0, 0
                    untagged, trunc, inv = (1 if i % 6 == 0 else 0), (1 if i % 5 == 0 else 0), 4
                elif arm == "placebo":
                    solved, steps, mem_tok, content_tok, matched_tok = int(i % 2 == 0), 37, base_block, 0, base_block
                    untagged, trunc, inv = (1 if i % 4 == 0 else 0), (1 if i % 5 == 0 else 0), 5
                elif arm == "retrieved_plan":
                    solved, steps, mem_tok, content_tok, matched_tok = int(i % 4 != 0), 30, base_block + 2, 112 + (i % 4), base_block
                    untagged, trunc, inv = 3, (1 if i % 4 == 0 else 0), 6
                elif arm == "retrieved_steps":
                    solved, steps, mem_tok, content_tok, matched_tok = int(i % 4 != 0), 28, base_block + 1, 196 + (i % 4), base_block
                    untagged, trunc, inv = (1 if i % 4 == 0 else 0), (1 if i % 4 == 0 else 0), 7
                else:
                    solved, steps, mem_tok, content_tok, matched_tok = int(i % 4 != 0), 26, base_block, base_block, base_block
                    untagged, trunc, inv = (1 if i % 4 == 0 else 0), (1 if i % 4 == 0 else 0), 8
                rows.append({
                    "cycle": 1, "unit": u, "arm": arm, "seed": 0, "solved": solved, "steps": steps,
                    "empty_retries": 0, "invalid_no_action_tag": trunc + untagged, "invalid_actions": inv,
                    "memory_tokens": mem_tok, "truncated": trunc, "untagged_not_truncated": untagged,
                    "top1_similarity": round(0.5 + 0.1 * (i % 5), 4),
                    "memory_similarity": round(0.5 + 0.08 * (i % 5), 4) if arm.startswith("retrieved_") else "",
                    "tokens": steps * 2000 + mem_tok,
                    "content_tokens": content_tok,
                    "matched_block_tokens": matched_tok,
                    "block_length_diff": round((mem_tok - base_block) / base_block, 6) if arm != "none" else "",
                    "min_tokens": (min_tokens_by_arm or {}).get(arm, 8),
                    "plan_digit_count": 0 if arm == "retrieved_plan" else "",
                    "steps_observation_count": 0 if arm == "retrieved_steps" else "",
                    "n_memory_sources": 2 if arm.startswith("retrieved_") else 0,
                    "error": 0,
                })

    pb = _compute_process_balance(rows, crit, behaviour, rule, pair_coverage=pair_coverage)

    # Results (seed 0)
    z = NormalDist().inv_cdf(1 - 0.05 / (2 * len(TREATMENTS)))
    seed0_by: Dict[str, Dict[str, int]] = {}
    for r in rows:
        if r["seed"] == 0:
            seed0_by.setdefault(r["arm"], {})[r["unit"]] = r["solved"]
    success_rate = {a: round(sum(seed0_by[a][u] for u in units) / n_units, 6) for a in ARMS}

    def contrast(a: str, b: str) -> Dict[str, Any]:
        g = sum(1 for u in units if seed0_by[a][u] == 1 and seed0_by[b][u] == 0)
        lo_cnt = sum(1 for u in units if seed0_by[a][u] == 0 and seed0_by[b][u] == 1)
        lo, hi = _paired_ci(g, lo_cnt, n_units, z)
        return {
            "gains": g, "losses": lo_cnt, "n": n_units, "diff": round((g - lo_cnt) / n_units, 6),
            "ci": [round(lo, 6), round(hi, 6)], "state": _state(lo, hi, sesoi),
            "discordance": round((g + lo_cnt) / n_units, 6),
        }

    primary = {a: contrast(a, "placebo") for a in TREATMENTS}
    secondary = {f"{a}-none": contrast(a, "none") for a in [*TREATMENTS, "placebo"]}

    # Measurement problems (only untagged_not_truncated on retrieved_plan is imbalanced)
    per_arm_ms: Dict[str, Dict[str, Any]] = {}
    for a in TREATMENTS:
        probs = []
        v = pb["per_arm"][a]["untagged_not_truncated"]
        if v["imbalanced"]:
            probs.append(
                f"proces: untagged_not_truncated na krok wariant − placebo {v['diff']:+.3f} "
                f"[{v['ci'][0]:+.3f}; {v['ci'][1]:+.3f}] > {v['tolerance']} (kryterium ustalone przed pomiarem) "
                "— treść i format/proces nie są rozdzielone"
            )
        per_arm_ms[a] = {"error_rate": 0.0, "problems": probs}

    env = {
        "id": pid, "goal": "Verify per-episode metrics table", "domain": "command-run", "sesoi": sesoi,
        "domain_params": {
            "experiment": "v6-verifier-test", "baseline": "none", "placebo": "placebo",
            "format_criteria": crit, "behaviour_counters": behaviour, "format_rule": rule,
            "arm_contracts": {
                "placebo": {"block_length_diff": {"max_abs": 0.03}, "content_tokens": {"eq": 0}},
                "retrieved_plan": {"block_length_diff": {"max_abs": 0.03}, "content_tokens": {"min": 1}, "plan_digit_count": {"eq": 0}},
                "retrieved_steps": {"block_length_diff": {"max_abs": 0.03}, "content_tokens": {"min": 1}, "steps_observation_count": {"eq": 0}},
                "retrieved_task": {"block_length_diff": {"eq": 0.0}, "content_tokens": {"min": 1}, "memory_tokens": {"min": 1}},
            },
        },
    }
    raw_sha = "a" * 64
    proto = {
        "arms": list(ARMS), "treatments": list(TREATMENTS), "n_units": n_units, "seeds": seeds,
        "sesoi": sesoi, "discordance_assumed": 0.80, "family_size": len(TREATMENTS),
    }
    run_p = {
        "raw_file": "raw.jsonl", "raw_sha256": raw_sha, "records": len(rows), "units": units,
        "arms": list(ARMS), "seeds": seeds, "domain": "command-run:v6-verifier-test",
        "measurement": {"errors_counted_as_unsolved": 0},
    }
    res_p = {
        "estimand": "wariant \u2212 placebo (efekt tre\u015bci)", "primary": primary, "secondary": secondary,
        "success_rate": success_rate, "z": round(z, 6), "family_size": len(TREATMENTS), "seed": 0,
        "n_units": n_units, "raw_sha256": raw_sha,
    }
    z_noise = NormalDist().inv_cdf(1 - 0.025 / len(TREATMENTS))
    obs_lo = max(c["discordance"] - z_noise * (max(c["discordance"] * (1 - c["discordance"]), 0.0) / n_units) ** 0.5
                 for c in primary.values())
    audit_p = {
        "by": "code", "verdict": "valid", "blocking": [], "warnings": [],
        "checks": {
            "completeness": {"expected": len(rows), "ok": True, "records": len(rows)},
            "fresh_units": {"count": 0, "ok": True, "reused_or_unknown": []},
            "leakage": {"ok": True, "leaked": [], "family_twins": []},
            "raw_integrity": {"ok": True, "sha256": raw_sha},
            "recompute": {"ok": True, "fields": [], "mismatches": []},
            "rule_null_calibration": {"ok": True, "severity": "info"},
            "noise_vs_calibration": {
                "ok": True, "assumed": 0.80, "observed_max": max(c["discordance"] for c in primary.values()),
                "observed_lower_bound": round(obs_lo, 6), "significant_arms": {}, "severity": "warning",
            },
            "measurement_sensitivity": {
                "ok": True, "severity": "info", "placebo_rate": round(success_rate["placebo"], 4),
                "placebo_problem": False, "tokens_reported": True, "memory_delivery_checked": True,
                "placebo_length_checked": True, "per_arm": per_arm_ms, "process_balance": pb,
            },
        },
    }

    objs: List[Dict[str, Any]] = []
    prog_obj = _make_obj("program", pid, env, [], None, "owner")
    objs.append(prog_obj)
    hyp_objs = {}
    for arm, pred in (("retrieved_task", "positive"), ("retrieved_steps", "positive"), ("retrieved_plan", "null")):
        h = _make_obj("hypothesis", pid, {"arm": arm, "predicted": pred, "statement": f"{arm} vs placebo"}, [prog_obj["id"]], 1, "theorist")
        hyp_objs[arm] = h
        objs.append(h)
    proto_obj = _make_obj("protocol", pid, proto, [prog_obj["id"], *[h["id"] for h in hyp_objs.values()]], 1)
    objs.append(proto_obj)
    run_obj = _make_obj("run", pid, run_p, [proto_obj["id"]], 1)
    objs.append(run_obj)
    res_obj = _make_obj("result", pid, res_p, [run_obj["id"]], 1)
    objs.append(res_obj)
    audit_obj = _make_obj("audit", pid, audit_p, [run_obj["id"], res_obj["id"]], 1)
    objs.append(audit_obj)

    finding_objs = []
    report_findings = []
    report_arms = {}
    meas_probs = {}
    for arm, pred in (("retrieved_task", "positive"), ("retrieved_steps", "positive"), ("retrieved_plan", "null")):
        c = primary[arm]
        st = c["state"]
        verdict = (("supported" if pred == "positive" else "refuted") if st in ("practical", "positive")
                   else ("refuted" if pred == "positive" else "supported") if st in ("equivalent", "negative")
                   else "inconclusive")
        probs = list(per_arm_ms[arm]["problems"])
        fp = {
            "arm": arm, "hypothesis": f"{arm} vs placebo", "predicted": pred, "state": st, "verdict": verdict,
            "level": "rozwojowy", "diff": c["diff"], "ci": c["ci"], "n": c["n"],
            "discordance": c["discordance"], "k": len(TREATMENTS), "measurement_problem": probs,
        }
        fo = _make_obj("finding", pid, fp, [hyp_objs[arm]["id"], res_obj["id"], audit_obj["id"]], 1)
        finding_objs.append(fo)
        objs.append(fo)
        report_findings.append({"arm": arm, "ci": c["ci"], "diff": c["diff"], "id": fo["id"],
                                "level": "rozwojowy", "state": st, "verdict": verdict})
        report_arms[arm] = {"findings": [fo["id"]], "status": "measurement_problem" if probs else "open"}
        if probs:
            meas_probs[arm] = probs

    dec_obj = _make_obj("decision", pid, {"action": "stop_program"}, [f["id"] for f in finding_objs], 1)
    objs.append(dec_obj)
    rep_p = {
        "program": pid, "goal": env["goal"], "cycles": 1, "role_calls": 4, "units_used": n_units,
        "arms": report_arms, "caveats": [], "decisions": [dec_obj["id"]], "final_decision": dec_obj["id"],
        "findings": report_findings, "measurement_problems": meas_probs,
        "scope": {"data": "command-run:v6-verifier-test", "arms_tested": list(TREATMENTS), "placebo": "placebo",
                  "units_tested": n_units, "runs": 1, "sesoi": sesoi},
    }
    objs.append(_make_obj("report", pid, rep_p, [dec_obj["id"], *[f["id"] for f in finding_objs]], 1))

    # Write package directory
    pkg = tmp_path / f"autolab-{pid.lower()}"
    pkg.mkdir(parents=True, exist_ok=True)
    kb_text = "".join(_canonical(o) + "\n" for o in objs)
    (pkg / "knowledge.jsonl").write_bytes(kb_text.encode("utf-8"))

    csv_cols = [
        "cycle", "unit", "arm", "seed", "solved", "steps", "empty_retries", "invalid_no_action_tag",
        "invalid_actions", "memory_tokens", "truncated", "untagged_not_truncated",
        "top1_similarity", "memory_similarity", "tokens",
    ]
    if include_per_episode_cols:
        csv_cols += ["block_length_diff", "content_tokens", "matched_block_tokens",
                     "plan_digit_count", "steps_observation_count"]
    if include_min_tokens_in_csv:
        csv_cols.append("min_tokens")
    csv_cols += ["n_memory_sources", "error"]

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(csv_cols)
    for r in sorted(rows, key=lambda x: (x["cycle"], x["unit"], x["arm"], x["seed"])):
        w.writerow([r.get(c, "") for c in csv_cols])
    (pkg / "per_unit.csv").write_text(buf.getvalue(), encoding="utf-8")

    prov = {
        "program": pid, "goal": env["goal"], "domain": "command-run", "objects": len(objs),
        "knowledge_sha256": hashlib.sha256(kb_text.encode("utf-8")).hexdigest(),
        "integrity_problems": [],
        "raw": [{"run": run_obj["id"], "raw_sha256": raw_sha, "records": len(rows),
                 "file": "raw.jsonl", "location": f"private/autolab/{pid}/raw/c1/raw.jsonl"}],
        "generated_by": "test", "exported_at": "2026-11-21T12:00:00+00:00", "note": "test",
    }
    (pkg / "PROVENANCE.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")

    # Build README matching exporter format
    all_rate_keys = sorted({k for v in pb["rates"].values() for k in v})
    step_keys = (["empty_retries", "invalid_actions", "invalid_no_action_tag", "truncated", "untagged_not_truncated"]
                 if split_tables else list(all_rate_keys))
    step_keys = sorted(set(step_keys) | set(extra_per_step_cols))

    lines = [
        "**Status:** completed", "", f"# Lab program {pid}", "", f"**Question (owner):** {env['goal']}", "",
        "Domain: `command-run`", f"Cycles: 1; role calls: 4; units: {n_units}.", "",
        f"## Results (cycle 1, n = {n_units} units, {len(ARMS)} arms)", "",
        "| arm | solved |", "|---|---|",
        *[f"| {a} | {success_rate[a]:.2f} |" for a in sorted(ARMS)], "",
        "| comparison | difference | 95% interval | gains / losses | state |", "|---|---|---|---|---|",
        *[f"| {a} \u2212 placebo (primary) | {primary[a]['diff']:+.3f} | [{primary[a]['ci'][0]:+.3f}, {primary[a]['ci'][1]:+.3f}] | "
          f"{primary[a]['gains']} / {primary[a]['losses']} | {primary[a]['state']} |" for a in sorted(primary)],
        *[f"| {name} | {secondary[name]['diff']:+.3f} | [{secondary[name]['ci'][0]:+.3f}, {secondary[name]['ci'][1]:+.3f}] | "
          f"{secondary[name]['gains']} / {secondary[name]['losses']} | {secondary[name]['state']} |" for name in sorted(secondary)],
        "", "## Findings (negative ones included)", "",
        "| arm | hypothesis | cycle | state | verdict | level | difference | interval | id |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for idx, fo in enumerate(finding_objs, 1):
        q = fo["payload"]
        lines.append(f"| {q['arm']} | H{idx} (predicted {q['predicted']}) | 1 | {q['state']} | {q['verdict']} | "
                     f"developmental | {q['diff']:+.3f} | [{q['ci'][0]:+.3f}, {q['ci'][1]:+.3f}] | `{fo['id']}` |")

    all_probs = sorted({x for f in finding_objs for x in f["payload"]["measurement_problem"]})
    lines += ["", "## Caveats", ""]
    for x in all_probs:
        lines.append("- Measurement problem: " + V.problem_en(x))
    for note in V.Verifier.rule_notes(pb):
        lines.append("- " + note)

    lines += [
        "", "## Measurement checks (per step, by arm)", "",
        "| arm | " + " | ".join(step_keys) + " |",
        "|---|" + "---|" * len(step_keys),
        *[f"| {a} | " + " | ".join(f"{pb['rates'][a].get(k, 0):.3f}" for k in step_keys) + " |"
          for a in sorted(pb["rates"])],
        "", "### Process criteria (arm \u2212 placebo, per step)", "",
        "| arm | counter | kind | tolerance | difference | 95% interval | state |", "|---|---|---|---|---|---|---|",
    ]
    for a in sorted(pb["per_arm"]):
        for k in sorted(pb["per_arm"][a]):
            v = pb["per_arm"][a][k]
            if not (v["preregistered"] or k in set(behaviour)):
                continue
            kind = "behaviour" if k in set(behaviour) else f"criterion ({v.get('rule', 'equivalence')})"
            lines.append(f"| {a} | `{k}` | {kind} | {v['tolerance']} | {v['diff']:+.3f} | "
                         f"[{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}] | {v['state']} |")
    lines += ["", "Code audit verdict: **valid** (completeness, recomputation, leakage, raw-data integrity)."]

    if split_tables:
        ep_cols = [
            "block_length_diff", "content_tokens", "matched_block_tokens", "memory_similarity",
            "memory_tokens", "plan_digit_count", "steps", "steps_observation_count", "tokens", "top1_similarity",
        ]
        if include_min_tokens_in_per_episode:
            ep_cols.append("min_tokens")
        ep_cols = sorted((set(ep_cols) | set(extra_per_episode_cols)) - set(omit_per_episode_cols))
        by_arm0: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            if r["seed"] == 0:
                by_arm0.setdefault(r["arm"], []).append(r)
        ep_rows = []
        for a in sorted(by_arm0):
            cells = []
            for c in ep_cols:
                vals = [float(r[c]) for r in by_arm0[a] if isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool)]
                cells.append(f"{sum(vals) / len(vals):.3f}" if vals else "\u2014")
            ep_rows.append(f"| {a} | " + " | ".join(cells) + " |")
        lines += [
            "", "## Per-episode metrics (mean by arm)", "",
            "| arm | " + " | ".join(ep_cols) + " |",
            "|---|" + "---|" * len(ep_cols),
            *ep_rows,
        ]

    lines += [
        "", "## Decisions", "", f"- `{dec_obj['id']}` (cycle 1): program finished",
        "", "## Status of each direction", "",
        *[f"- {a}: {v['status']}" + (" \u2014 measurement problem, so neither established nor closed"
                                     if v["status"] == "measurement_problem" else "")
          for a, v in sorted(report_arms.items())],
        "", "## Scope of the conclusions", "",
        f"The conclusions apply only to the task population `command-run:v6-verifier-test`, the arms {list(TREATMENTS)} "
        f"against the placebo `placebo`, the measurement conditions of the envelope and the scale of {n_units} units in "
        "1 run(s). Do not generalise to other tasks, models, prompts or scales.",
        "",
        "Per-task records (one row per task \u00d7 arm \u00d7 seed: solved, steps, empty and untagged answers, memory tokens, "
        "the counters required by the protocol; an empty cell = not reported, not zero): `per_unit.csv`. The raw episode "
        "logs stay private.",
        "",
        "All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.",
        "Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.",
    ]
    (pkg / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_manifest(pkg, pid)
    return pkg


def test_recomputes_per_episode_table_with_zero_new_nv_fields(tmp_path):
    pkg = _build_package(tmp_path)
    rep = V.verify_package(pkg)
    assert rep.failures == [], rep.failures
    # None of the per-episode metrics, per-step rates, audit process counters or new per_unit columns may be N/V
    for field in rep.unverifiable:
        assert not field.startswith("README Per-episode metrics"), field
        assert not field.startswith("README Measurement checks"), field
        assert "process counter" not in field, field
        assert ".coverage" not in field and ".one_sided" not in field, field
        for col in ("content_tokens", "matched_block_tokens", "min_tokens", "plan_digit_count",
                    "steps_observation_count", "block_length_diff", "memory_tokens", "steps",
                    "tokens", "top1_similarity", "memory_similarity"):
            assert field != f"per_unit.csv column {col}", field

    # CLI end-to-end: --write-package-baseline followed by full check
    script = str(_verifier_path())
    r1 = subprocess.run([sys.executable, "-I", "-B", script, "--package", str(pkg),
                         "--baseline", str(tmp_path / "none.json"), "--write-package-baseline"],
                        capture_output=True, text=True, encoding="utf-8")
    assert r1.returncode == 0, r1.stdout + r1.stderr
    _write_manifest(pkg, "V6-VERIFIER-TEST")
    r2 = subprocess.run([sys.executable, "-I", "-B", script, "--package", str(pkg),
                         "--baseline", str(tmp_path / "none.json")],
                        capture_output=True, text=True, encoding="utf-8")
    assert r2.returncode == 0, r2.stdout + r2.stderr


def test_tampered_per_episode_mean_fails(tmp_path):
    pkg = _build_package(tmp_path)
    rd = (pkg / "README.md").read_text(encoding="utf-8")
    # retrieved_plan content_tokens mean is 113.500 -> tamper to 114.500
    assert "| retrieved_plan | 0.002 | 113.500 |" in rd
    (pkg / "README.md").write_text(rd.replace("| retrieved_plan | 0.002 | 113.500 |",
                                              "| retrieved_plan | 0.002 | 114.500 |", 1), encoding="utf-8")
    _write_manifest(pkg, "V6-VERIFIER-TEST")
    rep = V.verify_package(pkg)
    assert any("README Per-episode metrics: content_tokens [retrieved_plan]" in f for f in rep.failures), rep.failures


def test_missing_per_episode_column_in_per_unit_csv_fails_not_nv(tmp_path):
    pkg = _build_package(tmp_path, include_per_episode_cols=False)
    rep = V.verify_package(pkg)
    assert any("README Per-episode metrics: every column is in per_unit.csv" in f for f in rep.failures), rep.failures
    assert not any(f.startswith("README Per-episode metrics") for f in rep.unverifiable), rep.unverifiable


def test_missing_reading_dash_vs_zero_is_enforced(tmp_path):
    # Arm without readings (none / plan_digit_count) reporting 0.000 instead of em-dash must FAIL
    pkg1 = _build_package(tmp_path / "case1")
    rd1 = (pkg1 / "README.md").read_text(encoding="utf-8")
    old_none = [ln for ln in rd1.splitlines() if ln.startswith("| none | \u2014 | 0.000 |")][0]
    cells = [c.strip() for c in old_none.strip().strip("|").split("|")]
    # plan_digit_count is column index 6
    assert cells[6] == "\u2014"
    cells[6] = "0.000"
    new_none = "| " + " | ".join(cells) + " |"
    (pkg1 / "README.md").write_text(rd1.replace(old_none, new_none, 1), encoding="utf-8")
    _write_manifest(pkg1, "V6-VERIFIER-TEST")
    rep1 = V.verify_package(pkg1)
    assert any("README Per-episode metrics: plan_digit_count [none]" in f for f in rep1.failures), rep1.failures

    # Arm with explicit 0 readings (retrieved_plan / plan_digit_count) reporting em-dash instead of 0.000 must FAIL
    pkg2 = _build_package(tmp_path / "case2")
    rd2 = (pkg2 / "README.md").read_text(encoding="utf-8")
    old_plan = [ln for ln in rd2.splitlines() if ln.startswith("| retrieved_plan | 0.002 |")][0]
    cells2 = [c.strip() for c in old_plan.strip().strip("|").split("|")]
    assert cells2[6] == "0.000"
    cells2[6] = "\u2014"
    new_plan = "| " + " | ".join(cells2) + " |"
    (pkg2 / "README.md").write_text(rd2.replace(old_plan, new_plan, 1), encoding="utf-8")
    _write_manifest(pkg2, "V6-VERIFIER-TEST")
    rep2 = V.verify_package(pkg2)
    assert any("README Per-episode metrics: plan_digit_count [retrieved_plan]" in f for f in rep2.failures), rep2.failures


def test_per_step_counter_in_per_episode_table_fails(tmp_path):
    pkg = _build_package(tmp_path, extra_per_episode_cols=["empty_retries"])
    rep = V.verify_package(pkg)
    assert any("contains no per-step event counters" in f for f in rep.failures), rep.failures


def test_non_per_step_metric_left_in_measurement_checks_fails_when_split(tmp_path):
    pkg = _build_package(tmp_path, extra_per_step_cols=["content_tokens"])
    rep = V.verify_package(pkg)
    assert any("README Measurement checks: columns = the audit's counters" in f for f in rep.failures), rep.failures


def test_silently_dropped_non_setting_audit_metric_fails(tmp_path):
    pkg = _build_package(tmp_path, omit_per_episode_cols=["matched_block_tokens"])
    rep = V.verify_package(pkg)
    assert any("covers non-per-step audit metric matched_block_tokens" in f for f in rep.failures), rep.failures


def test_varying_setting_recomputed_and_required_in_per_episode_table(tmp_path):
    varying = {"none": 0, "placebo": 8, "retrieved_task": 8, "retrieved_steps": 8, "retrieved_plan": 8}
    pkg_ok = _build_package(tmp_path / "ok", min_tokens_by_arm=varying, include_min_tokens_in_per_episode=True)
    rep_ok = V.verify_package(pkg_ok)
    assert rep_ok.failures == [], rep_ok.failures
    assert not any("min_tokens" in f for f in rep_ok.unverifiable), rep_ok.unverifiable

    pkg_bad = _build_package(tmp_path / "bad", min_tokens_by_arm=varying, include_min_tokens_in_per_episode=False)
    rep_bad = V.verify_package(pkg_bad)
    assert any("covers non-per-step audit metric min_tokens" in f for f in rep_bad.failures), rep_bad.failures


def test_one_sided_coverage_mismatch_in_audit_fails(tmp_path):
    pkg = _build_package(tmp_path)
    kb_lines = [json.loads(x) for x in (pkg / "knowledge.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    for o in kb_lines:
        if o["kind"] == "audit":
            o["payload"]["checks"]["measurement_sensitivity"]["process_balance"]["per_arm"]["retrieved_plan"][
                "plan_digit_count"]["coverage"]["variant"] = 10
            o["redacted"] = True
            body = {"kind": o["kind"], "program": o["program"], "payload": o["payload"], "parents": sorted(set(o["parents"]))}
            o["sha256_redacted"] = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    kb_text = "".join(_canonical(o) + "\n" for o in kb_lines)
    (pkg / "knowledge.jsonl").write_bytes(kb_text.encode("utf-8"))
    prov = json.loads((pkg / "PROVENANCE.json").read_text(encoding="utf-8"))
    prov["knowledge_sha256"] = hashlib.sha256(kb_text.encode("utf-8")).hexdigest()
    (pkg / "PROVENANCE.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    _write_manifest(pkg, "V6-VERIFIER-TEST")
    rep = V.verify_package(pkg)
    assert any("plan_digit_count].coverage" in f for f in rep.failures), rep.failures


def test_legacy_package_without_per_episode_table_stays_compatible(tmp_path):
    pkg = _build_package(
        tmp_path,
        split_tables=False,
        include_per_episode_cols=False,
        include_min_tokens_in_csv=False,
        pair_coverage=False,
    )
    rep = V.verify_package(pkg)
    assert rep.failures == [], rep.failures
    assert any(f.startswith("README Measurement checks: content_tokens per step") for f in rep.unverifiable)


def test_per_episode_averages_first_seed_only(tmp_path):
    pkg = _build_package(tmp_path, extra_seed_rows=True)
    rep = V.verify_package(pkg)
    assert rep.failures == [], rep.failures


# --- review fixes (Sonnet review of the Gemini patch, 2026-11-21: I1, I2, I4) ---

def _per_episode_rows(rd: str):
    lines = rd.splitlines()
    start = lines.index("## Per-episode metrics (mean by arm)")
    return lines, [i for i in range(start + 1, len(lines)) if lines[i].startswith("|")]


def test_coarse_per_episode_cell_fails_format(tmp_path):
    # I1: '113.5' agrees with 113.500 at its own precision; the exporter always writes 3 decimals
    pkg = _build_package(tmp_path)
    rd = (pkg / "README.md").read_text(encoding="utf-8")
    assert "| retrieved_plan | 0.002 | 113.500 |" in rd
    (pkg / "README.md").write_text(rd.replace("| retrieved_plan | 0.002 | 113.500 |",
                                              "| retrieved_plan | 0.002 | 113.5 |", 1), encoding="utf-8")
    _write_manifest(pkg, "V6-VERIFIER-TEST")
    rep = V.verify_package(pkg)
    assert any("content_tokens [retrieved_plan] = 113.5 (format)" in f for f in rep.failures), rep.failures


def test_dropped_float_column_fails(tmp_path):
    # I2: top1_similarity is a float metric (not in process_balance.rates); dropping it must not pass silently
    pkg = _build_package(tmp_path)
    rd = (pkg / "README.md").read_text(encoding="utf-8")
    lines, rows = _per_episode_rows(rd)
    for i in rows:
        cells = lines[i].strip().strip("|").split("|")
        lines[i] = "|" + "|".join(cells[:-1]) + "|"
    assert "top1_similarity" not in "\n".join(lines[rows[0]:rows[-1] + 1])
    (pkg / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_manifest(pkg, "V6-VERIFIER-TEST")
    rep = V.verify_package(pkg)
    assert any("covers per_unit.csv metric top1_similarity" in f for f in rep.failures), rep.failures


def test_new_format_forces_pair_coverage_mode(tmp_path, monkeypatch):
    # I4: stripping `coverage` from the declared audit must not switch a new-format package to the legacy computation
    pkg = _build_package(tmp_path)

    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k not in ("coverage", "one_sided")}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return x
    kf = pkg / "knowledge.jsonl"
    out = []
    for line in kf.read_text(encoding="utf-8").splitlines():
        o = json.loads(line)
        if o.get("kind") == "audit":
            o["payload"] = strip(o["payload"])
        out.append(json.dumps(o, ensure_ascii=False))
    kf.write_text("\n".join(out) + "\n", encoding="utf-8")
    _write_manifest(pkg, "V6-VERIFIER-TEST")
    seen = []
    orig = V.Verifier.balance

    def spy(self, *a, **kw):
        seen.append(kw.get("pair_coverage"))
        return orig(self, *a, **kw)
    monkeypatch.setattr(V.Verifier, "balance", spy)
    V.verify_package(pkg)
    assert seen and all(seen), seen
