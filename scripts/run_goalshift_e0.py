#!/usr/bin/env python3
"""AAM-E0 harness: delayed relevance at fixed budgets (exploratory, synthetic, tier E).

Subcommands
-----------
generate     write worlds (history, cues, labels) for the given seeds, or the config digests
stage0       construct checks on the development seeds 0-4 ($0, local)
stage1       retrieval-level run on the test seeds 100-119 ($0, local); one look, only after
             Stage 0 passed on the same scripts and the configuration was frozen
stage2-plan  build the reader prompts for the answer-level run and project the cost (no network)
stage2-run   the paid answer-level run; refuses without --i-have-authorisation and --cap-usd

Nothing here calls a model except ``stage2-run``, which the lead runs, not a builder.
This is a synthetic world written by an agent: a result about it is not a result about
real agents, and a null here is a complete answer.

Metric. ``gold`` is STRICT: the gold answer (the reference code) is present in the text the
arm delivers. ``gold_id`` (the gold event's id is present, even as a summary whose text lacks
the code) is a secondary column. v0.1 made the id measure primary, which credited Sum for
information its 8-word summary never held.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus import goalshift as gs  # noqa: E402
from corpus.goalshift_arms import (ARM_NAMES, ORACLE_ARMS, ArmConfig, CachedEmbedder,  # noqa: E402
                                   Engine, HashingEmbedder, SentenceTransformerBackend, dot,
                                   importance)

OUT = ROOT / "data" / "lab" / "aam-e0-delayed-relevance"
DEV_SEEDS = tuple(range(0, 5))
TEST_SEEDS = tuple(range(100, 120))
CONTEXT_BUDGETS = (100, 250, 500)
RETAINED = (0.10, 0.25)
NO_R_ARMS = ("A", "F1", "F2", "B3")
COMPARATORS = ("Del", "Sum", "Sum-raw")
PRIMARY = {"cell": "C3", "C": 250, "R": 0.10}
PRACTICAL_THRESHOLD = 0.15
SUMRAW_BAND = 0.05
EPS = 1e-9  # rates are multiples of 1/80; compare with a tolerance, never raw float subtraction
BOOT_DRAWS = 10000
BOOT_SEED = 20261101
MAX_CAP_USD = 5.0

#: Stage 0 gate thresholds. The numeric ones were written before the first Stage 0 run; the
#: headroom/oracle/shuffle/importance gates were re-specified after the verifiers' review
#: (see the README), before any rerun.
GATES = {
    "headroom_low": 0.2, "headroom_high": 0.8,
    "c1_overlap_mean": (0.30, 0.50), "c1_overlap_each": (0.20, 0.60),
    "min_decoys": 2, "oracle_min": 0.95, "shuffle_margin": 0.10,
    "sem_similar_min_gap": 0.15, "sem_low_max_gap": 0.10, "sem_c2_c3_min_diff": 0.10,
    "importance_rank_share": (0.30, 0.70),
}
STAGE2_ARMS = ("A", "F2", "Del", "Sum-raw", "D")
READER = {"model": "deepseek-v4-flash", "base_url": "https://api.deepseek.com/v1",
          "parameters": {"temperature": 0, "max_tokens": 300}}
PRICE = {"input": 0.27, "output": 1.10}

#: D's sensitivity variants (secondary table; the first row is the primary configuration).
VARIANTS = (
    ("primary: concept df>=2, stem>=4 letters, cluster/query threshold 0.55", {}),
    ("v0.1 concept rule: any df, stem>=3 letters", {"min_concept_df": 1, "min_concept_len": 3}),
    ("cluster/query threshold 0.45", {"cluster_threshold": 0.45, "query_threshold": 0.45}),
    ("cluster/query threshold 0.65", {"cluster_threshold": 0.65, "query_threshold": 0.65}),
)

#: C3, C=250, R=10%, seeds 0-4, MiniLM, from the committed Stage 0 of generator goalshift-v0.1
#: (rate by event id, strict rate). Kept for the side-by-side table; v0.1 is superseded.
PREVIOUS_V01 = {
    "Del": (0.20, 0.20), "Sum": (0.35, 0.00), "Sum-raw": (0.05, 0.05), "D": (0.10, 0.10),
    "O": (0.95, 0.95), "S": (0.15, 0.15), "F2": (0.25, 0.25),
}

AVG_FIELDS = ("gold", "gold_id", "decoys", "neg", "words", "chars4", "linked", "fa", "n_ctx",
              "n_traces", "stored", "gold_stored")

# ---------------------------------------------------------------------------- utils


def parse_seeds(text: str) -> list[int]:
    seeds: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            seeds.extend(range(int(a), int(b) + 1))
        elif part:
            seeds.append(int(part))
    return seeds


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def script_digests() -> dict[str, str]:
    files = {"scripts/corpus/goalshift.py": ROOT / "scripts/corpus/goalshift.py",
             "scripts/corpus/goalshift_arms.py": ROOT / "scripts/corpus/goalshift_arms.py",
             "scripts/run_goalshift_e0.py": Path(__file__).resolve()}
    return {name: sha256_file(p) for name, p in files.items()}


def build_embedder(kind: str, model_dir: str | None):
    if kind == "hashing":
        return HashingEmbedder()
    if kind == "minilm":
        if not model_dir:
            raise SystemExit("--model-dir is required for --embedder minilm")
        return SentenceTransformerBackend(model_dir)
    raise SystemExit("unknown embedder %r" % kind)


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, indent=1, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def environment() -> dict[str, Any]:
    """Versions that can move a dense result. Bit-equality is claimed only for a fixed one."""
    import platform
    from importlib import metadata

    out: dict[str, Any] = {"python": platform.python_version(), "platform": platform.platform()}
    for pkg in ("torch", "sentence-transformers", "transformers", "numpy"):
        try:
            out[pkg] = metadata.version(pkg)
        except Exception:  # noqa: BLE001 - absent package is a normal case
            out[pkg] = None
    return out


def config_dict() -> dict[str, Any]:
    return {
        "experiment": "AAM-E0 delayed relevance at fixed budgets",
        "status": "exploratory, tier E, not registered; synthetic worlds authored by an agent",
        "generator_version": gs.GENERATOR_VERSION,
        "dev_seeds": list(DEV_SEEDS), "test_seeds": list(TEST_SEEDS),
        "world": {"events": gs.N_EVENTS, "days": gs.N_DAYS, "phases": [list(p) for p in gs.PHASES],
                  "domains": list(gs.DOMAINS), "cells": list(gs.CELLS),
                  "probes_per_cell": gs.PROBES_PER_CELL, "words_per_event": [gs.LEN_MIN, gs.LEN_MAX],
                  "target_days": list(gs.TARGET_DAYS), "min_gap_days": gs.MIN_GAP_DAYS,
                  "c1_target_overlap": gs.C1_TARGET_OVERLAP, "roles": list(gs.ROLE_NAMES),
                  "role_balance": "alternate worlds take alternate halves of the 8 roles",
                  "consequence_probs": list(gs.CONSEQUENCE_PROBS),
                  "write_time_fields": "consequence and novelty drawn by position only, "
                                       "independent of kind and text (uninformative by construction)"},
        "budgets": {"context_words": list(CONTEXT_BUDGETS), "retained_share": list(RETAINED),
                    "unit": "whitespace-split words (corpus H1 convention); chars/4 reported as a second column"},
        "arms": list(ARM_NAMES), "arm_config": ArmConfig().as_dict(),
        "metric": {"primary": "gold = reference code present in the delivered text (strict)",
                   "secondary": "gold_id = gold event id present (a summary counts)"},
        "primary": {"cell": PRIMARY["cell"], "context_words": PRIMARY["C"],
                    "retained_share": PRIMARY["R"], "comparators": list(COMPARATORS),
                    "practical_threshold": PRACTICAL_THRESHOLD, "sum_raw_band": SUMRAW_BAND,
                    "comparison_tolerance": EPS,
                    "bootstrap": {"draws": BOOT_DRAWS, "seed": BOOT_SEED, "resample": "scenarios",
                                  "interval": 0.95}},
        "sensitivity_variants": [[n, o] for n, o in VARIANTS],
        "stage0_gates": {k: (list(v) if isinstance(v, tuple) else v) for k, v in GATES.items()},
        "stage2": {"arms": list(STAGE2_ARMS), "reader": READER, "scoring": "gold_answer contained in answer",
                   "max_cap_usd": MAX_CAP_USD,
                   "ledger": "data/lab/aam-e0-delayed-relevance/stage2-ledger.json (JSON lines)"},
        "script_sha256": script_digests(),
    }


# ---------------------------------------------------------------------- evaluation


def score(world: dict[str, Any], probe: dict[str, Any], res: dict[str, Any], C: int,
          R: float | None) -> dict[str, Any]:
    """One record. ``gold`` is strict (the reference code is in the delivered text);
    ``gold_id`` credits a summary of the gold event; ``gold_stored`` says whether the
    arm had kept anything of the gold event at all (None for arms with no store)."""
    ids = [c["event_id"] for c in res["context"]]
    text = " ".join(c["text"] for c in res["context"]).lower()
    gold_ev = probe["gold_event_id"]
    gold_text = probe["gold_answer"].lower() in text
    decoys = sum(1 for d in probe["decoy_ids"] if d in ids)
    meta = res["meta"]
    stored_ids = meta.get("stored_ids")
    return {
        "seed": world["seed"], "probe_id": probe["probe_id"], "cell": probe["cell"],
        "role": probe.get("role"), "arm": res["arm"], "C": C, "R": R,
        "gold": int(gold_text), "gold_id": int(gold_ev in ids),
        "gold_stored": None if stored_ids is None else int(gold_ev in stored_ids),
        "decoys": decoys, "neg": int(decoys > 0 and not gold_text), "words": res["words"],
        "chars4": sum(len(c["text"]) for c in res["context"]) / 4.0,
        "linked": len(res["link_ids"]), "fa": sum(1 for i in res["link_ids"] if i != gold_ev),
        "n_ctx": len(ids), "n_traces": meta.get("n_traces", 0), "stored": meta.get("stored", 0),
    }


def combine(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Average the per-shuffle records of the S control into one record per probe."""
    out = dict(recs[0])
    for k in AVG_FIELDS:
        vals = [r[k] for r in recs if r[k] is not None]
        out[k] = (sum(vals) / len(vals)) if vals else None
    out["n_shuffles"] = len(recs)
    return out


def run_eval(seeds, embedder, arms=ARM_NAMES, Cs=CONTEXT_BUDGETS, Rs=RETAINED,
             cfg: ArmConfig | None = None, timing: list | None = None):
    """Records for every (probe, arm, C, R). Wall-clock goes to ``timing`` (if given), never
    into the records, so a rerun of the same seeds is byte-identical."""
    records: list[dict[str, Any]] = []
    worlds: dict[int, dict[str, Any]] = {}
    cached = embedder if isinstance(embedder, CachedEmbedder) else CachedEmbedder(embedder)
    cfg = cfg or ArmConfig()
    for seed in seeds:
        world = gs.generate(seed)
        worlds[seed] = world
        labels = {eid: lab["concepts"] for eid, lab in world["labels"]["events"].items()}
        engine = Engine(world["events"], cached, cfg, labels, seed)
        cue_of = {c["probe_id"]: c for c in world["cues"]}
        for probe in world["labels"]["probes"]:
            cue = cue_of[probe["probe_id"]]
            for arm in arms:
                oracle = [probe["concept"]] if arm in ORACLE_ARMS else None
                for C in Cs:
                    for R in ([None] if arm in NO_R_ARMS else list(Rs)):
                        r_val = 0.0 if R is None else R
                        if arm == "S":
                            recs, ms = [], 0.0
                            for k in range(cfg.shuffles):
                                res = engine.run(arm, cue["cue"], cue["goal"], cue["day"], C, r_val,
                                                 None, shuffle=k)
                                ms += res["ms"]
                                recs.append(score(world, probe, res, C, R))
                            records.append(combine(recs))
                        else:
                            res = engine.run(arm, cue["cue"], cue["goal"], cue["day"], C, r_val,
                                             oracle)
                            ms = res["ms"]
                            records.append(score(world, probe, res, C, R))
                        if timing is not None:
                            timing.append({"arm": arm, "C": C, "R": R, "ms": ms})
    return records, worlds


def timing_summary(timing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple, list[float]] = {}
    for t in timing:
        groups.setdefault((t["arm"], t["C"], t["R"]), []).append(t["ms"])
    return [{"arm": a, "C": c, "R": r, "mean_ms": round(mean(v), 3), "n": len(v)}
            for (a, c, r), v in sorted(groups.items(), key=lambda kv: (
                ARM_NAMES.index(kv[0][0]), kv[0][1], -1 if kv[0][2] is None else kv[0][2]))]


def _mean_or_none(vals: list[Any]) -> float | None:
    vals = [v for v in vals if v is not None]
    return round(mean(vals), 4) if vals else None


def summarise(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for r in records:
        for cell in (r["cell"], "ALL"):
            groups.setdefault((r["arm"], cell, r["C"], r["R"]), []).append(r)
    out = []
    for (arm, cell, C, R), rs in sorted(groups.items(), key=lambda kv: (
            ARM_NAMES.index(kv[0][0]), kv[0][1], kv[0][2], -1 if kv[0][3] is None else kv[0][3])):
        linked = sum(r["linked"] for r in rs)
        out.append({
            "arm": arm, "cell": cell, "C": C, "R": R, "n": len(rs),
            "gold": round(mean([r["gold"] for r in rs]), 4),
            "gold_id": round(mean([r["gold_id"] for r in rs]), 4),
            "gold_stored": _mean_or_none([r["gold_stored"] for r in rs]),
            "decoys": round(mean([r["decoys"] for r in rs]), 4),
            "neg": round(mean([r["neg"] for r in rs]), 4),
            "words": round(mean([r["words"] for r in rs]), 2),
            "chars4": round(mean([r["chars4"] for r in rs]), 2),
            "false_assoc_rate": (round(sum(r["fa"] for r in rs) / linked, 4) if linked else None),
            "n_ctx": round(mean([r["n_ctx"] for r in rs]), 2),
        })
    return out


def lookup(summary: list[dict[str, Any]], arm: str, cell: str, C: int, R: float | None):
    r_key = None if arm in NO_R_ARMS else R
    for row in summary:
        if row["arm"] == arm and row["cell"] == cell and row["C"] == C and row["R"] == r_key:
            return row
    raise KeyError((arm, cell, C, R))


def per_seed(records, arm, cell, C, R, field="gold") -> dict[int, float]:
    r_key = None if arm in NO_R_ARMS else R
    by: dict[int, list[float]] = {}
    for r in records:
        if (r["arm"] == arm and (cell == "ALL" or r["cell"] == cell) and r["C"] == C
                and r["R"] == r_key):
            by.setdefault(r["seed"], []).append(r[field])
    return {s: mean(v) for s, v in by.items()}


def cond_rate(records, arm: str, C: int, R: float, field: str = "gold") -> float:
    """Rate among probes whose gold event the arm had stored (retrieval given storage)."""
    rs = [r for r in records if r["arm"] == arm and r["C"] == C and r["R"] == R
          and r["gold_stored"] == 1]
    return mean([r[field] for r in rs]) if rs else float("nan")


def paired_bootstrap(diffs: list[float], draws: int = BOOT_DRAWS, seed: int = BOOT_SEED,
                     level: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap over scenarios (paired differences). With 20 scenarios the
    interval is coarse and discrete; lo > 0 is a blunt criterion, not a calibrated test."""
    if not diffs:
        return float("nan"), float("nan")
    rng = gs.Lcg(seed)
    n = len(diffs)
    means = []
    for _ in range(draws):
        total = 0.0
        for _i in range(n):
            total += diffs[rng.below(n)]
        means.append(total / n)
    means.sort()
    lo = means[int(((1 - level) / 2) * draws)]
    hi = means[min(draws - 1, int((1 - (1 - level) / 2) * draws))]
    return lo, hi


def best_comparator(summary: list[dict[str, Any]],
                    field: str = "gold") -> tuple[str, dict[str, float]]:
    rates = {a: lookup(summary, a, PRIMARY["cell"], PRIMARY["C"], PRIMARY["R"])[field]
             for a in COMPARATORS}
    best = sorted(rates, key=lambda a: (-rates[a], COMPARATORS.index(a)))[0]
    return best, rates


def sensitivity(seeds, embedder) -> list[dict[str, Any]]:
    """D under alternative concept rules and cluster thresholds (C=250). Secondary only."""
    rows = []
    for name, override in VARIANTS:
        recs, _ = run_eval(seeds, embedder, arms=("D",), Cs=(250,), cfg=ArmConfig(**override))
        summ = summarise(recs)
        row: dict[str, Any] = {"variant": name}
        for R in RETAINED:
            for cell in ("C1", "C2", "C3"):
                row["%s R=%d%%" % (cell, round(R * 100))] = lookup(summ, "D", cell, 250, R)["gold"]
        rows.append(row)
    return rows


ROLE_ARMS = ("Del", "Sum-raw", "F2", "D", "Oc", "S")


def role_rows(records) -> list[list[Any]]:
    """C3 gold by role at C=250, R=10% (F2 has no R)."""
    roles = sorted({r["role"] for r in records if r["cell"] == "C3" and r["role"]})
    rows = []
    for role in roles:
        row: list[Any] = [role]
        n = None
        for arm in ROLE_ARMS:
            rs = [r for r in records if r["arm"] == arm and r["cell"] == "C3" and r["role"] == role
                  and r["C"] == 250 and r["R"] == (None if arm in NO_R_ARMS else 0.10)]
            n = len(rs)
            row.append("%.3f" % mean([r["gold"] for r in rs]) if rs else "-")
        rows.append([row[0], n] + row[1:])
    return rows


# ------------------------------------------------------------------------- Stage 0


def structure_checks(seeds, worlds) -> dict[str, Any]:
    problems: list[str] = []
    overlaps = {c: [] for c in gs.CELLS}
    goal_overlaps = {c: [] for c in gs.CELLS}
    rare_hits = {c: [] for c in gs.CELLS}
    decoy_counts: list[int] = []
    code_re = re.compile(r"\b[bcdfghjkmnpqrstvwxz]{2}\d{4}\b")
    for seed in seeds:
        w = worlds[seed]
        if gs.digest(gs.generate(seed)) != gs.digest(w):
            problems.append("seed %d: generator not deterministic" % seed)
        if gs.generate(seed, history=False)["cues"] != w["cues"]:
            problems.append("seed %d: cue file differs without the history" % seed)
        events = w["events"]
        by_id = {e["event_id"]: e for e in events}
        if len(events) != gs.N_EVENTS:
            problems.append("seed %d: %d events" % (seed, len(events)))
        for e in events:
            n = gs.word_count(e["text"])
            if not (gs.LEN_MIN <= n <= gs.LEN_MAX):
                problems.append("seed %d: %s has %d words" % (seed, e["event_id"], n))
            if not code_re.search(e["text"].lower()):
                problems.append("seed %d: %s carries no reference code" % (seed, e["event_id"]))
        probes = w["labels"]["probes"]
        counts = {c: sum(1 for p in probes if p["cell"] == c) for c in gs.CELLS}
        if any(v != gs.PROBES_PER_CELL for v in counts.values()):
            problems.append("seed %d: cell counts %s" % (seed, counts))
        cue_of = {c["probe_id"]: c for c in w["cues"]}
        stem_df: dict[str, int] = {}
        for e in events:
            for st in gs.stems_of(e["text"]):
                stem_df[st] = stem_df.get(st, 0) + 1
        for p in probes:
            cue = cue_of[p["probe_id"]]
            target = by_id[p["gold_event_id"]]
            if not (gs.TARGET_DAYS[0] <= target["day"] <= gs.TARGET_DAYS[1]):
                problems.append("%s: target day %d" % (p["probe_id"], target["day"]))
            if cue["day"] - target["day"] < gs.MIN_GAP_DAYS or not (21 <= cue["day"] <= 30):
                problems.append("%s: gap/cue day" % p["probe_id"])
            if p["gold_answer"] not in target["text"].lower():
                problems.append("%s: gold answer not in target" % p["probe_id"])
            if p["gold_answer"] in (cue["cue"] + " " + cue["goal"] + " " + str(cue["day"])).lower():
                problems.append("%s: gold answer leaked into the cue/goal" % p["probe_id"])
            if re.search(r"\be\d{3}\b", cue["cue"] + " " + cue["goal"]):
                problems.append("%s: an event id appears in the cue" % p["probe_id"])
            if len(p["decoy_ids"]) < GATES["min_decoys"]:
                problems.append("%s: only %d decoys" % (p["probe_id"], len(p["decoy_ids"])))
            for d in p["decoy_ids"]:
                if by_id[d]["day"] >= cue["day"]:
                    problems.append("%s: decoy %s is not before the cue" % (p["probe_id"], d))
            decoy_counts.append(len(p["decoy_ids"]))
            ov = gs.overlap_fraction(cue["cue"], target["text"])
            if abs(ov - p["overlap"]) > 1e-3:
                problems.append("%s: stored overlap differs from measured" % p["probe_id"])
            overlaps[p["cell"]].append(ov)
            goal_overlaps[p["cell"]].append(gs.overlap_fraction(cue["goal"], target["text"]))
            unique = {st for st in gs.stems_of(target["text"]) if stem_df[st] == 1}
            rare_hits[p["cell"]].append(len(gs.stems_of(cue["cue"] + " " + cue["goal"]) & unique))
    return {"problems": problems, "overlaps": overlaps, "goal_overlaps": goal_overlaps,
            "target_unique_hits": rare_hits, "min_decoys": min(decoy_counts) if decoy_counts else 0}


def semantic_stats(worlds, embedder) -> dict[str, Any]:
    cached = embedder if isinstance(embedder, CachedEmbedder) else CachedEmbedder(embedder)
    per_cell: dict[str, dict[str, list[float]]] = {
        c: {"target": [], "baseline": [], "decoy": [], "rank1": [], "top11": [], "rank": []}
        for c in gs.CELLS}
    for w in worlds.values():
        cue_of = {c["probe_id"]: c for c in w["cues"]}
        for p in w["labels"]["probes"]:
            cue = cue_of[p["probe_id"]]
            vis = [e for e in w["events"] if e["day"] <= cue["day"]]
            qv = cached.encode([cue["cue"]])[0]
            vecs = cached.encode([e["text"] for e in vis])
            sims = {e["event_id"]: dot(qv, v) for e, v in zip(vis, vecs)}
            gold = p["gold_event_id"]
            others = [s for i, s in sims.items() if i != gold]
            cell = per_cell[p["cell"]]
            cell["target"].append(sims[gold])
            cell["baseline"].append(mean(others))
            cell["decoy"].append(mean([sims[d] for d in p["decoy_ids"] if d in sims]))
            order = sorted(sims, key=lambda i: -sims[i])
            rank = order.index(gold) + 1
            cell["rank"].append(float(rank))
            cell["rank1"].append(1.0 if rank == 1 else 0.0)
            cell["top11"].append(1.0 if rank <= 11 else 0.0)
    out = {}
    for c, d in per_cell.items():
        out[c] = {"target_cos": round(mean(d["target"]), 4),
                  "baseline_cos": round(mean(d["baseline"]), 4),
                  "decoy_cos": round(mean(d["decoy"]), 4),
                  "gap": round(mean(d["target"]) - mean(d["baseline"]), 4),
                  "target_rank1": round(mean(d["rank1"]), 4),
                  "target_in_top11": round(mean(d["top11"]), 4),
                  "mean_rank": round(mean(d["rank"]), 2)}
    return out


def importance_stats(worlds, cfg: ArmConfig) -> dict[str, Any]:
    """Where the targets sit in the write-time importance ranking. In goalshift-v0.2 the
    fields are independent of kind, so the share should be about 0.5 in every cell."""
    pct = {c: [] for c in gs.CELLS}
    nov = {"target": [], "decoy": [], "filler": []}
    cons = {"target": [], "decoy": [], "filler": []}
    for w in worlds.values():
        labs = w["labels"]["events"]
        for e in w["events"]:
            kind = labs[e["event_id"]]["kind"]
            k = "target" if kind == "target" else "decoy" if kind.startswith("decoy") else "filler"
            nov[k].append(e["novelty"])
            cons[k].append(e["consequence"])
        for p in w["labels"]["probes"]:
            cue_day = p["cue_day"]
            vis = [e for e in w["events"] if e["day"] <= cue_day]
            order = sorted(vis, key=lambda e: (-importance(e, cfg.novelty_weight), e["position"]))
            idx = [e["event_id"] for e in order].index(p["gold_event_id"])
            pct[p["cell"]].append((idx + 1) / len(vis))
    return {"target_importance_rank_share": {c: round(mean(v), 4) for c, v in pct.items()},
            "mean_novelty": {k: round(mean(v), 4) for k, v in nov.items()},
            "mean_consequence": {k: round(mean(v), 4) for k, v in cons.items()}}


def md_table(header: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if x is None else str(x) for x in r) + " |")
    return "\n".join(out) + "\n"


def _fmt(x: Any) -> str:
    return "-" if x is None else "%.3f" % x


def rate_table(summary, Cs=CONTEXT_BUDGETS, Rs=RETAINED, field="gold", arms=ARM_NAMES) -> str:
    rows = []
    for arm in arms:
        for cell in ("C1", "C2", "C3", "ALL"):
            row: list[Any] = [arm, cell]
            for C in Cs:
                cells = [_fmt(lookup(summary, arm, cell, C, R)[field]) for R in Rs]
                row.append(" / ".join(cells) if arm not in NO_R_ARMS else cells[0])
            rows.append(row)
    return md_table(["arm", "cell"] + ["C=%d (R=10%% / 25%%)" % C for C in Cs], rows)


def stage0(args) -> int:
    seeds = parse_seeds(args.seeds)
    if any(100 <= s <= 119 for s in seeds):
        raise SystemExit("stage0 refuses the test seeds 100-119")
    embedder = CachedEmbedder(build_embedder(args.embedder, args.model_dir))
    cfg = ArmConfig()
    timing: list[dict[str, Any]] = []
    records, worlds = run_eval(seeds, embedder, cfg=cfg, timing=timing)
    summary = summarise(records)
    structure = structure_checks(seeds, worlds)
    sem = semantic_stats(worlds, embedder)
    imp = importance_stats(worlds, cfg)
    sens = sensitivity(seeds, embedder)
    best, comp_rates = best_comparator(summary)
    best_id, comp_rates_id = best_comparator(summary, "gold_id")
    gates: list[dict[str, Any]] = []

    def gate(name: str, passed: bool, value: str) -> None:
        gates.append({"name": name, "passed": bool(passed), "value": value})

    gate("headroom (strict gold): best of Del/Sum/Sum-raw in C3 at C=250, R=10%% in [%.1f, %.1f]"
         % (GATES["headroom_low"], GATES["headroom_high"]),
         GATES["headroom_low"] - EPS <= comp_rates[best] <= GATES["headroom_high"] + EPS,
         "%s = %.3f (%s); by event id the best is %s = %.3f" % (
             best, comp_rates[best], ", ".join("%s %.3f" % (a, comp_rates[a]) for a in COMPARATORS),
             best_id, comp_rates_id[best_id]))
    ov1 = structure["overlaps"]["C1"]
    lo, hi = GATES["c1_overlap_mean"]
    elo, ehi = GATES["c1_overlap_each"]
    gate("overlap C1: mean in [%.2f, %.2f], each in [%.2f, %.2f]" % (lo, hi, elo, ehi),
         lo <= mean(ov1) <= hi and all(elo <= x <= ehi for x in ov1),
         "mean %.3f, min %.3f, max %.3f" % (mean(ov1), min(ov1), max(ov1)))
    ov0 = structure["overlaps"]["C2"] + structure["overlaps"]["C3"]
    go0 = structure["goal_overlaps"]["C2"] + structure["goal_overlaps"]["C3"]
    gate("overlap C2 and C3: zero (cue and goal vs target, stemmed content words, the arms' own "
         "token space)",
         max(ov0) == 0 and max(go0) == 0 and not any(structure["target_unique_hits"]["C2"])
         and not any(structure["target_unique_hits"]["C3"]),
         "max cue overlap %.3f, max goal overlap %.3f" % (max(ov0), max(go0)))
    s1, s2, s3 = sem["C1"]["gap"], sem["C2"]["gap"], sem["C3"]["gap"]
    gate("semantic: C1 and C2 cue-target cosine exceeds the archive baseline by >= %.2f; C3 by <= %.2f; "
         "C2 - C3 >= %.2f (embedder: %s)" % (GATES["sem_similar_min_gap"], GATES["sem_low_max_gap"],
                                            GATES["sem_c2_c3_min_diff"], args.embedder),
         s1 >= GATES["sem_similar_min_gap"] and s2 >= GATES["sem_similar_min_gap"]
         and s3 <= GATES["sem_low_max_gap"] and (s2 - s3) >= GATES["sem_c2_c3_min_diff"],
         "gaps C1 %.3f, C2 %.3f, C3 %.3f" % (s1, s2, s3))
    gate("decoys: every probe has >= %d decoys, all dated before its cue" % GATES["min_decoys"],
         structure["min_decoys"] >= GATES["min_decoys"]
         and not any("decoy" in p for p in structure["problems"]),
         "min decoys per probe %d" % structure["min_decoys"])
    gate("structure and leakage: determinism, cue file identical without history, 150 events of "
         "12-35 words each with a code, 4/4/4 probes, target day 2-9, gap >= 14, no id or gold "
         "code in the cue",
         not structure["problems"], "%d problems%s" % (
             len(structure["problems"]),
             ("; first: " + structure["problems"][0]) if structure["problems"] else ""))
    rlo, rhi = GATES["importance_rank_share"]
    shares = imp["target_importance_rank_share"]
    gate("write-time importance is uninformative: target rank share in [%.2f, %.2f] in every cell "
         "(0 = top, 0.5 = chance)" % (rlo, rhi),
         all(rlo <= v <= rhi for v in shares.values()),
         ", ".join("%s %.3f" % (c, v) for c, v in shares.items()))
    o_min = GATES["oracle_min"]
    parts, ok_o = [], True
    for arm, R in (("O", 0.10), ("O", 0.25), ("Oc", 0.10), ("Oc", 0.25)):
        cr = cond_rate(records, arm, 250, R)
        stored = lookup(summary, arm, "ALL", 250, R)["gold_stored"]
        parts.append("%s R=%d%%: %.3f given stored (gold stored %.3f, unconditional %.3f)"
                     % (arm, round(R * 100), cr, stored, lookup(summary, arm, "ALL", 250, R)["gold"]))
        ok_o = ok_o and cr >= o_min - EPS
    o25 = lookup(summary, "O", "ALL", 250, 0.25)["gold"]
    ok_o = ok_o and o25 >= o_min - EPS
    gate("oracle retrieval path: O and Oc reach the gold >= %.2f of the time when they stored it "
         "(C=250, R=10%% and 25%%), and O >= %.2f unconditionally at R=25%%" % (o_min, o_min),
         ok_o, "; ".join(parts))
    ok_s, parts = True, []
    for R in RETAINED:
        rs = [r for r in records if r["arm"] == "S" and r["C"] == 250 and r["R"] == R]
        chance = mean([(r["gold_stored"] or 0) * min(1.0, r["n_ctx"] / max(1.0, r["n_traces"]))
                       for r in rs])
        s_rate = mean([r["gold"] for r in rs])
        d_rate = lookup(summary, "D", "ALL", 250, R)["gold"]
        parts.append("R=%d%%: S %.3f (mean of %d shuffles) vs chance %.3f; D %.3f"
                     % (round(R * 100), s_rate, cfg.shuffles, chance, d_rate))
        ok_s = ok_s and s_rate <= chance + GATES["shuffle_margin"]
    gate("shuffled S near chance at C=250 (S <= P(gold has a trace) x fetched/traces + %.2f)"
         % GATES["shuffle_margin"], ok_s, "; ".join(parts))
    passed = all(g["passed"] for g in gates)
    results = {
        "stage": 0, "seeds": seeds, "embedder": args.embedder, "passed": passed, "gates": gates,
        "generator_version": gs.GENERATOR_VERSION,
        "best_comparator": best, "comparator_rates": comp_rates,
        "best_comparator_by_id": best_id, "comparator_rates_by_id": comp_rates_id,
        "summary": summary, "sensitivity_D": sens,
        "semantic": sem, "importance": imp, "structure": {
            k: v for k, v in structure.items() if k != "overlaps" and k != "goal_overlaps"},
        "overlap_stats": {c: {"mean": round(mean(v), 4), "min": round(min(v), 4),
                              "max": round(max(v), 4), "n": len(v)}
                          for c, v in structure["overlaps"].items()},
        "environment": environment(),
        "script_sha256": script_digests(), "arm_config": cfg.as_dict(), "records": records,
    }
    out = Path(args.out)
    write_json(out / "results.json", results)
    write_json(out / "timing.json", {
        "note": "wall-clock; not part of the deterministic outputs",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mean_ms": timing_summary(timing)})
    write_text(out / "report.md", stage0_report(results, summary, sem, imp, structure, gates, sens))
    for g in gates:
        print(("PASS " if g["passed"] else "FAIL ") + g["name"] + " -> " + g["value"])
    print("Stage 0 %s" % ("PASSED" if passed else "FAILED"))
    return 0 if passed else 1


def previous_table(summary) -> str:
    rows = []
    for arm in ("Del", "Sum", "Sum-raw", "F2", "D", "O", "S"):
        new = lookup(summary, arm, "C3", 250, 0.10)
        old = PREVIOUS_V01[arm]
        rows.append([arm, "%.2f" % old[0], "%.2f" % old[1], "%.2f" % new["gold_id"], "%.2f" % new["gold"]])
    return md_table(["arm (C3, C=250, R=10%)", "v0.1 by id", "v0.1 strict", "v0.2 by id", "v0.2 strict (primary)"],
                    rows)


def stage0_report(results, summary, sem, imp, structure, gates, sens) -> str:
    lines = ["# AAM-E0 Stage 0 report: construct checks on the development seeds\n",
             "Status: exploratory, tier E, synthetic worlds written by an agent, no spend, no model, "
             "no network. Development seeds %s. Generator `%s`. Embedder: `%s`. Wall-clock is in "
             "`timing.json`, not here.\n"
             % (results["seeds"], results["generator_version"], results["embedder"]),
             "A passed gate says the generator behaves as designed. It says nothing about real "
             "agents or about arm D. A failed gate is a finding about the world, reported as such.\n",
             "## Verdict\n", "**Stage 0 %s.**\n" % ("PASSED" if results["passed"] else "FAILED"),
             md_table(["gate", "result", "measured"],
                      [[g["name"], "PASS" if g["passed"] else "FAIL", g["value"]] for g in gates])]
    lines.append("Best comparator on the primary cell (C3, C=250, R=10%%): **%s** by strict gold "
                 "(%s); **%s** by event id (%s). The decision rules use the strict measure. They "
                 "differ because a lead-truncated 8-word summary is credited by id for an event whose "
                 "reference code it does not contain.\n"
                 % (results["best_comparator"], results["comparator_rates"],
                    results["best_comparator_by_id"], results["comparator_rates_by_id"]))
    if not results["passed"]:
        lines.append("A failed gate stops the study: Stage 1 refuses to run and the test seeds were "
                     "not generated.\n")
    lines.append("## Old generator against new, side by side\n")
    lines.append(previous_table(summary))
    lines.append("v0.1 drew the authored consequence by event kind (targets about twice as consequential "
                 "as filler) and computed novelty against earlier events only, which fell with time and "
                 "favoured the day 2-9 targets. Its importance ranking therefore told every forgetting "
                 "arm which events were targets (gold's mean rank share among dormant events 0.13-0.22 "
                 "against 0.5 for an uninformative score). In v0.2 both write-time fields are drawn by "
                 "position only. The v0.1 column is from the committed v0.1 Stage 0 (seeds 0-4, MiniLM); "
                 "n is 20 probes per cell, so one probe is 0.05.\n")
    lines.append("## Measured overlap (cue content words also in the target, stemmed, in the arms' own "
                 "token space)\n")
    lines.append(md_table(["cell", "n", "mean", "min", "max"],
                          [[c, v["n"], v["mean"], v["min"], v["max"]]
                           for c, v in results["overlap_stats"].items()]))
    lines.append("## Semantic similarity (cosine, cue vs target; baseline = cue vs every other "
                 "visible event)\n")
    lines.append(md_table(["cell", "target", "baseline", "gap", "decoys", "target rank 1", "in top 11",
                           "mean rank"],
                          [[c, v["target_cos"], v["baseline_cos"], v["gap"], v["decoy_cos"],
                            v["target_rank1"], v["target_in_top11"], v["mean_rank"]]
                           for c, v in sem.items()]))
    lines.append("## Gold-in-context, strict (reference code present in the delivered text), C x R\n")
    lines.append(rate_table(summary))
    lines.append("## Gold stored (the arm kept something of the gold event: raw, summary or trace)\n")
    lines.append(rate_table(summary, field="gold_stored",
                            arms=("Del", "Sum", "Sum-raw", "D", "O", "Oc", "S")))
    lines.append("Gold-in-context cannot exceed gold stored. The gap between the two is the loss "
                 "'stored but not retrieved'; the shortfall of gold stored below 1 is the loss 'not "
                 "stored' (a budget effect, not a retrieval effect). O keeps cheaper traces than D "
                 "(about 2 words each against up to 6), so at the same R it stores far more; Oc has "
                 "D's stored set and D's costs and is the like-for-like oracle.\n")
    lines.append("## By event id (a summary of the gold event counts even without the code)\n")
    lines.append(rate_table(summary, field="gold_id"))
    lines.append("## Decoy intrusion (mean decoys in context)\n")
    lines.append(rate_table(summary, field="decoys"))
    lines.append("## D under other concept rules and thresholds (secondary; C=250)\n")
    scols = [k for k in sens[0] if k != "variant"]
    lines.append(md_table(["variant"] + scols, [[r["variant"]] + [r[k] for k in scols] for r in sens]))
    lines.append("## Write-time importance\n")
    lines.append(md_table(["measure", "value"],
                          [["target importance rank share, C1", imp["target_importance_rank_share"]["C1"]],
                           ["target importance rank share, C2", imp["target_importance_rank_share"]["C2"]],
                           ["target importance rank share, C3", imp["target_importance_rank_share"]["C3"]],
                           ["mean novelty target / decoy / filler",
                            "%(target)s / %(decoy)s / %(filler)s" % imp["mean_novelty"]],
                           ["mean consequence target / decoy / filler",
                            "%(target)s / %(decoy)s / %(filler)s" % imp["mean_consequence"]]]))
    lines.append("Rank share is the target's position in the importance ordering of the archive "
                 "visible at the cue (0 = most important, 0.5 = no information). Because importance is "
                 "uninformative by construction, an arm that forgets by importance keeps a random subset "
                 "of the older events, and its chance of holding the target is about its coverage.\n")
    lines.append("## Notes and honest limits\n")
    lines.append(NOTES)
    return "\n".join(lines)


NOTES = """\
- Strict gold is primary: the reference code must be in the delivered text. By event id (secondary) a
  lead-truncated 8-word summary counts as the gold event although it does not hold the answer.
- Write-time importance is uninformative by construction (v0.2). This follows the specification's
  low-salience targets and removes a leak found in v0.1, at the cost that forgetting arms keep a
  random subset of the older events; their headroom is then set by their coverage, not by retrieval.
- O stores traces at about 2 words each, D at up to 6 (distinct clusters plus a pointer). At the same
  R, O therefore stores about three times as many events; O is an oracle with cheaper traces, not a
  same-footing upper bound on D. Oc (D's stored set and costs, oracle concepts) is the like-for-like
  oracle. 'Gold stored' separates a loss from not storing from a loss from not retrieving.
- The oracle gate tests the retrieval path (reach the gold when it is stored) and unconditional O at
  R=25%, where the budget is not binding. It does not claim that O is near 1 at R=10%.
- S is the mean of 20 independent pointer shuffles per probe (a spread, not one draw). Its gate is
  loose by nature; read the paired D minus S contrast instead.
- Summaries are lead-truncated extracts, a weaker stand-in for a model summary.
- Concept phrases for D are stemmed content words, not multiword phrases. D keeps a concept only if it
  occurs in at least 2 visible events and has at least 4 letters (fixed a priori, before the test
  seeds, after a dev diagnostic by a verifier showed one-off names and stemmer fragments dominated
  the concepts). D's sensitivity to that rule and to the cluster threshold is in the secondary table.
  Do not read 'not tuned' as 'robust'.
- Free resources are not charged to R: D's cluster vocabulary, seed vectors and co-occurrence table
  (built from all visible events, including dormant ones, so richer than a sequential ingest) and the
  dense index of Sum and Sum-raw. R measures only the stored trace or summary words.
- Cell C3 mixes roles of different difficulty (some are close paraphrases of the cue for a dense
  model, others are abstract). Roles are balanced across the test seeds (alternate worlds take
  alternate halves of the eight); tables per role are in the Stage 1 report.
- Overlap is measured in the arms' own token space (one stop-word list and crude stemmer shared by
  the generator, the overlap measure and D), so D's direct lexical route is blocked by construction.
- Every event carries a reference code, so the code tag says nothing about which event is a target.
  The reader question still says 'reference code'; a Stage 2 reader could pick any code in the context.
- The semantic gate thresholds were written before the first semantic measurement. The generator was
  revised after the first run (C2 cue wording) and again after the verifiers' review; both are tuning
  of the generator on development seeds, which the plan allows, and the C2/C3 separation is partly a
  product of that.
- Sentence templates are shared across worlds; names, numbers and codes are fresh. No arm is trained.
- Bit-equality of the dense results is claimed only for a fixed environment (see `environment` in
  `results.json`): the 0.55 cosine thresholds could move at the margin on another torch or hardware.
"""


# ------------------------------------------------------------------------- Stage 1


def verdict(d: float, best: float, lo: float, sum_raw: float, f2: float) -> dict[str, Any]:
    """The decision rules. Rates are multiples of 1/80, so comparisons carry a tolerance:
    a difference of exactly 0.15 counts as 0.15."""
    diff = d - best
    statements = []
    if diff >= PRACTICAL_THRESHOLD - EPS and lo > 0:
        primary = ("SUPPORTED: D exceeds the best of Del/Sum/Sum-raw by %.3f (threshold %.2f) and "
                   "the 95%% interval's lower bound %.3f is above zero." % (diff, PRACTICAL_THRESHOLD, lo))
    else:
        primary = ("NOT SUPPORTED: D minus the best of Del/Sum/Sum-raw is %.3f (threshold %.2f); the "
                   "95%% interval's lower bound is %.3f." % (diff, PRACTICAL_THRESHOLD, lo))
    if sum_raw >= d - SUMRAW_BAND - EPS:
        statements.append("a summary index with expansion is at least as good (Sum-raw %.3f vs D %.3f; "
                          "within %.2f or better)" % (sum_raw, d, SUMRAW_BAND))
    if f2 >= d - EPS:
        statements.append("no better than conventional retrieval; at most a smaller index "
                          "(F2 %.3f >= D %.3f)" % (f2, d))
    return {"primary": primary, "statements": statements, "difference": round(diff, 4),
            "ci_lower": round(lo, 4)}


def require_frozen_and_stage0() -> tuple[dict[str, Any], dict[str, Any]]:
    """The gate in front of every path that touches the test seeds: the configuration is
    frozen on the current scripts, and a passing Stage 0 was run on those same scripts, on
    the development seeds, with the real embedder."""
    cfg_path = OUT / "config.json"
    if not cfg_path.exists():
        raise SystemExit("config.json is missing: freeze it with `generate --write-config` first")
    config = json.loads(cfg_path.read_text(encoding="utf-8"))
    digests = script_digests()
    if config.get("script_sha256") != digests:
        raise SystemExit("the scripts differ from the digests frozen in config.json; "
                         "refusing to generate test seeds")
    s0_path = OUT / "stage0" / "results.json"
    if not s0_path.exists():
        raise SystemExit("Stage 0 has not been run")
    s0 = json.loads(s0_path.read_text(encoding="utf-8"))
    if not s0.get("passed"):
        raise SystemExit("Stage 0 did not pass; Stage 1 refuses to run (report the failure, "
                         "do not tune on the test seeds)")
    if s0.get("script_sha256") != digests:
        raise SystemExit("Stage 0 was run on different scripts than the current ones (digests "
                         "differ); rerun Stage 0, then re-freeze")
    if s0.get("seeds") != list(DEV_SEEDS):
        raise SystemExit("Stage 0 did not run on exactly the development seeds %s" % (list(DEV_SEEDS),))
    if s0.get("embedder") != "minilm":
        raise SystemExit("Stage 0 did not use the real embedder (minilm)")
    return config, s0


def paired_contrast(records, a: str, b: str, field: str = "gold") -> tuple[float, float, float]:
    """Mean of (a minus b) over scenarios on the primary cell/C/R, with its bootstrap interval."""
    c, cC, cR = PRIMARY["cell"], PRIMARY["C"], PRIMARY["R"]
    a_ps = per_seed(records, a, c, cC, cR, field)
    b_ps = per_seed(records, b, c, cC, cR, field)
    diffs = [a_ps[s] - b_ps[s] for s in sorted(a_ps)]
    lo, hi = paired_bootstrap(diffs)
    return mean(diffs), lo, hi


def stage1(args) -> int:
    config, s0 = require_frozen_and_stage0()
    out = Path(args.out)
    if (out / "results.json").exists():
        raise SystemExit("Stage 1 already has results in %s; one look only" % out)
    if args.dev_dry_run:
        seeds = parse_seeds(args.seeds) if args.seeds else list(DEV_SEEDS)
        if any(s not in DEV_SEEDS for s in seeds):
            raise SystemExit("--dev-dry-run takes development seeds only")
        if out.resolve() == (OUT / "stage1").resolve():
            raise SystemExit("--dev-dry-run must write somewhere other than the real stage1 directory")
    else:
        if args.embedder != "minilm":
            raise SystemExit("Stage 1 on the test seeds needs --embedder minilm")
        seeds = list(config["test_seeds"])
        if args.seeds and parse_seeds(args.seeds) != seeds:
            raise SystemExit("Stage 1 runs exactly the frozen test seeds %s-%s" % (seeds[0], seeds[-1]))
    embedder = CachedEmbedder(build_embedder(args.embedder, args.model_dir))
    cfg = ArmConfig()
    timing: list[dict[str, Any]] = []
    records, worlds = run_eval(seeds, embedder, cfg=cfg, timing=timing)
    summary = summarise(records)
    best = s0["best_comparator"]  # chosen on the development seeds only, by strict gold
    best_id = s0.get("best_comparator_by_id", best)
    c, cC, cR = PRIMARY["cell"], PRIMARY["C"], PRIMARY["R"]

    def contrast(other: str, field: str = "gold") -> tuple[float, float, float]:
        return paired_contrast(records, "D", other, field)

    diff, lo, hi = contrast(best)
    d_rate = lookup(summary, "D", c, cC, cR)["gold"]
    best_rate = lookup(summary, best, c, cC, cR)["gold"]
    sr = lookup(summary, "Sum-raw", c, cC, cR)["gold"]
    f2 = lookup(summary, "F2", c, cC, cR)["gold"]
    v = verdict(d_rate, best_rate, lo, sr, f2)
    comparators = {}
    for name in COMPARATORS + ("F2", "S", "Oc"):
        m, l2, h2 = contrast(name)
        comparators[name] = {"rate": lookup(summary, name, c, cC, cR)["gold"],
                             "diff_D_minus": round(m, 4), "ci": [round(l2, 4), round(h2, 4)]}
    m_id, lo_id, hi_id = contrast(best_id, "gold_id")
    v_id = verdict(lookup(summary, "D", c, cC, cR)["gold_id"],
                   lookup(summary, best_id, c, cC, cR)["gold_id"], lo_id,
                   lookup(summary, "Sum-raw", c, cC, cR)["gold_id"],
                   lookup(summary, "F2", c, cC, cR)["gold_id"])
    results = {
        "stage": 1, "dry_run": bool(args.dev_dry_run), "generator_version": gs.GENERATOR_VERSION,
        "seeds": seeds, "n_scenarios": len(seeds), "embedder": args.embedder,
        "best_comparator_chosen_on_dev": best,
        "primary": {"cell": c, "C": cC, "R": cR, "metric": "strict gold (reference code in the text)",
                    "D": d_rate, "best_comparator_rate": best_rate,
                    "difference": round(diff, 4), "ci95": [round(lo, 4), round(hi, 4)],
                    "bootstrap": {"draws": BOOT_DRAWS, "seed": BOOT_SEED}},
        "verdict": v, "comparators": {k: comparators[k] for k in COMPARATORS},
        "controls_contrast": {k: comparators[k] for k in ("F2", "S", "Oc")},
        "primary_by_id": {"best_comparator_chosen_on_dev": best_id,
                          "D": lookup(summary, "D", c, cC, cR)["gold_id"],
                          "best_comparator_rate": lookup(summary, best_id, c, cC, cR)["gold_id"],
                          "difference": round(m_id, 4), "ci95": [round(lo_id, 4), round(hi_id, 4)],
                          "verdict": v_id, "metric": "gold event id present (a summary counts)"},
        "F2": f2, "O": lookup(summary, "O", c, cC, cR)["gold"],
        "Oc": lookup(summary, "Oc", c, cC, cR)["gold"],
        "S": lookup(summary, "S", c, cC, cR)["gold"],
        "summary": summary, "sensitivity_D": sensitivity(seeds, embedder),
        "role_table_header": ["role", "n"] + list(ROLE_ARMS), "role_table": role_rows(records),
        "environment": environment(), "script_sha256": script_digests(),
        "config_sha256": hashlib.sha256((OUT / "config.json").read_bytes()).hexdigest(),
    }
    write_json(out / "results.json", results)
    with (out / "records.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for r in records:
            handle.write(json.dumps(r, sort_keys=True) + "\n")
    write_json(out / "timing.json", {
        "note": "wall-clock; not part of the deterministic outputs",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mean_ms": timing_summary(timing)})
    write_text(out / "report.md", stage1_report(results, summary))
    print(v["primary"])
    for s in v["statements"]:
        print("also: " + s)
    return 0


def stage1_report(results, summary) -> str:
    p, v = results["primary"], results["verdict"]
    lines = ["# AAM-E0 Stage 1 report: retrieval-level run on the test seeds\n",
             "Status: exploratory, tier E, synthetic worlds written by an agent, no independent review. "
             "%sGenerator `%s`. Seeds %s-%s (%d scenarios, %d probes). Embedder `%s`. Environment and "
             "wall-clock: `results.json` and `timing.json`.\n"
             % ("**DRY RUN on development seeds, not a result.** " if results["dry_run"] else "",
                results["generator_version"], results["seeds"][0], results["seeds"][-1],
                results["n_scenarios"], results["n_scenarios"] * 12, results["embedder"]),
             "## Verdict, exactly as the rules say\n", "**%s**\n" % v["primary"]]
    for s in v["statements"]:
        lines.append("- Also: %s.\n" % s)
    if not v["statements"]:
        lines.append("- Neither the Sum-raw rule nor the F2 rule fired.\n")
    lines.append("## Primary comparison (strict gold, the pre-declared measure)\n")
    lines.append(md_table(["quantity", "value"], [
        ["cell / C / R", "%s / %d words / %d%%" % (p["cell"], p["C"], round(p["R"] * 100))],
        ["D gold-in-context", p["D"]],
        ["best comparator chosen on dev seeds", "%s (%s)" % (results["best_comparator_chosen_on_dev"],
                                                          p["best_comparator_rate"])],
        ["D minus best, mean over scenarios", p["difference"]],
        ["paired bootstrap 95%% interval", p["ci95"]],
        ["F2 (dense over everything)", results["F2"]],
        ["O (oracle concepts, cheaper traces)", results["O"]],
        ["Oc (oracle concepts, D's stored set and costs)", results["Oc"]],
        ["S (shuffled pointers, mean of 20 shuffles)", results["S"]]]))
    lines.append("The comparator was chosen on 20 development probes, a noisy draw, not a finding. The "
                 "interval is a percentile bootstrap over %d scenarios: discrete and coarse, so lower "
                 "bound above zero is a blunt criterion.\n" % results["n_scenarios"])
    ps = results["primary_by_id"]
    lines.append("## Secondary: the same comparison by event id (a summary counts)\n")
    lines.append(md_table(["quantity", "value"], [
        ["D", ps["D"]], ["best comparator chosen on dev (by id)",
                         "%s (%s)" % (ps["best_comparator_chosen_on_dev"], ps["best_comparator_rate"])],
        ["D minus best, mean over scenarios", ps["difference"]], ["95% interval", ps["ci95"]]]))
    lines.append("Reading: %s\n" % ps["verdict"]["primary"])
    lines.append("## D against each comparator and control (same cell, C, R; strict gold)\n")
    rows = [[k, o["rate"], o["diff_D_minus"], o["ci"]] for k, o in results["comparators"].items()]
    rows += [[k, o["rate"], o["diff_D_minus"], o["ci"]] for k, o in results["controls_contrast"].items()]
    lines.append(md_table(["comparator or control", "rate", "D minus it", "95% interval"], rows))
    lines.append("## Where D loses: stored or retrieved (C3, C=250)\n")
    rows = []
    for arm in ("Del", "Sum-raw", "D", "O", "Oc", "S"):
        for R in RETAINED:
            row = lookup(summary, arm, "C3", 250, R)
            stored = row["gold_stored"]
            rows.append([arm, "%d%%" % round(R * 100), _fmt(stored), _fmt(row["gold"]),
                         _fmt(None if stored is None else stored - row["gold"])])
    lines.append(md_table(["arm", "R", "gold stored", "gold in context", "stored but not retrieved"], rows))
    lines.append("## C3 by role (strict gold, C=250, R=10%, F2 without R)\n")
    lines.append(md_table(results["role_table_header"], results["role_table"]))
    lines.append("Cell C3 mixes roles that are paraphrases of the cue for a dense model with abstract "
                 "ones; with 20 scenarios each role has only about 10 worlds x 1 probe.\n")
    lines.append("## Gold-in-context, strict, every arm, cell, C and R\n")
    lines.append(rate_table(summary))
    lines.append("## Gold stored\n")
    lines.append(rate_table(summary, field="gold_stored",
                            arms=("Del", "Sum", "Sum-raw", "D", "O", "Oc", "S")))
    lines.append("## By event id\n")
    lines.append(rate_table(summary, field="gold_id"))
    lines.append("## Decoy intrusion (mean decoys in context)\n")
    lines.append(rate_table(summary, field="decoys"))
    lines.append("## Negative transfer (decoy present and gold absent)\n")
    lines.append(rate_table(summary, field="neg"))
    lines.append("## False-association rate of the trace arms (fetched events that are not gold, "
                 "all fetched through a concept link), C=250, R=10%\n")
    rows = []
    for arm in ("D", "O", "Oc", "S"):
        for cell in ("C1", "C2", "C3", "ALL"):
            row = lookup(summary, arm, cell, 250, 0.10)
            rows.append([arm, cell, row["false_assoc_rate"], row["n_ctx"]])
    lines.append(md_table(["arm", "cell", "false-association rate", "events fetched"], rows))
    lines.append("## D under other concept rules and thresholds (secondary; C=250)\n")
    sens = results["sensitivity_D"]
    scols = [k for k in sens[0] if k != "variant"]
    lines.append(md_table(["variant"] + scols, [[r["variant"]] + [r[k] for k in scols] for r in sens]))
    lines.append("## Limits\n")
    lines.append(NOTES)
    lines.append("- Costs of the write-time work (concept extraction, clustering) are not charged to "
                 "any arm in this model-free stage; wall-clock per retrieval is in `timing.json`.\n"
                 "- The audit of about 30 fetched associations for the false-association label has "
                 "not been done; the rate above uses the generator's gold label only.\n")
    return "\n".join(lines)


# ------------------------------------------------------------------------- Stage 2


def reader_prompt_parts():
    from arena.fixed_reader import READER_PARAMS, READER_PROMPT, user_message  # noqa: E402
    return READER_PROMPT, READER_PARAMS, user_message


def stage2_plan(args) -> int:
    READER_PROMPT, READER_PARAMS, user_message = reader_prompt_parts()
    if READER_PARAMS != READER["parameters"]:
        raise SystemExit("reader parameters changed upstream; update the specification first")
    seeds = parse_seeds(args.seeds) if args.seeds else list(TEST_SEEDS)
    if any(100 <= s <= 119 for s in seeds):
        require_frozen_and_stage0()
        s1_path = OUT / "stage1" / "results.json"
        if not s1_path.exists() or json.loads(s1_path.read_text(encoding="utf-8")).get("dry_run", True):
            raise SystemExit("Stage 2 on the test seeds needs a real Stage 1 result first")
    embedder = CachedEmbedder(build_embedder(args.embedder, args.model_dir))
    arms = [a for a in args.arms.split(",")]
    cases = []
    cached = embedder
    for seed in seeds:
        world = gs.generate(seed)
        labels = {eid: lab["concepts"] for eid, lab in world["labels"]["events"].items()}
        engine = Engine(world["events"], cached, None, labels, seed)
        cue_of = {c["probe_id"]: c for c in world["cues"]}
        for probe in world["labels"]["probes"]:
            cue = cue_of[probe["probe_id"]]
            for arm in arms:
                res = engine.run(arm, cue["cue"], cue["goal"], cue["day"], args.C, args.R,
                                 [probe["concept"]] if arm in ORACLE_ARMS else None)
                texts = None if arm == "A" else [c["text"] for c in res["context"]]
                cases.append({"seed": seed, "probe_id": probe["probe_id"], "cell": probe["cell"],
                              "arm": arm, "question": cue["question"], "context": texts,
                              "gold_answer": probe["gold_answer"],
                              "gold_in_context": int(probe["gold_answer"].lower() in
                                                     " ".join(c["text"] for c in res["context"]).lower())})
    in_tokens = sum((len(READER_PROMPT) + len(user_message(c["question"], c["context"]))) // 3
                    for c in cases)
    per_rep = in_tokens / 1e6 * PRICE["input"] + len(cases) * READER["parameters"]["max_tokens"] / 1e6 * PRICE["output"]
    plan = {"stage": 2, "kind": "plan", "reader": READER, "reader_prompt_sha256":
            hashlib.sha256(READER_PROMPT.encode()).hexdigest(), "seeds": seeds, "arms": arms,
            "C": args.C, "R": args.R, "repeats": args.repeats, "cases": cases,
            "calls": len(cases) * args.repeats,
            "projected_usd_upper_bound": round(per_rep * args.repeats, 4),
            "projection_note": "prompt tokens estimated as characters/3 (conservative for codes and "
                               "numbers); completion at the max_tokens ceiling; DeepSeek list prices; "
                               "an estimate with a safety factor, not a guarantee. The hard cap, "
                               "checked before every call, is what protects the spend.",
            "script_sha256": script_digests()}
    write_json(Path(args.out) / "plan.json", plan)
    print("plan: %d cases x %d repeats = %d calls, projected estimate $%.4f"
          % (len(cases), args.repeats, plan["calls"], plan["projected_usd_upper_bound"]))
    return 0


def run_stage2(plan: dict[str, Any], client: Any, cap_usd: float, ledger_path: Path,
               out_dir: Path, pilot_calls: int | None = None) -> dict[str, Any]:
    """The paid loop. ``client`` is an OpenAI-compatible client (or a test double). The
    hard cap is checked before every call by FixedDecoding and the shared ledger. The model
    is always the frozen READER model, whatever the plan file says."""
    from arena.decoding import FixedDecoding, SpendCapReached  # noqa: E402
    from arena.spend_ledger import SpendLedger, TotalCapReached  # noqa: E402

    READER_PROMPT, READER_PARAMS, user_message = reader_prompt_parts()
    ledger_path = Path(ledger_path)
    if "arena" in ledger_path.parts and ledger_path.name == "spend-ledger.jsonl":
        raise SystemExit("refusing to write into the V1/V2/V3 arena ledger")
    raw_path = out_dir / "outputs.jsonl"
    if raw_path.exists() and raw_path.stat().st_size > 0:
        raise SystemExit("%s is not empty; refusing to append duplicate rows" % raw_path)
    ledger = SpendLedger(ledger_path, total_cap_usd=cap_usd, run_id="aam-e0-stage2",
                         cap_scope="aam-e0-stage2")
    wrapped = FixedDecoding(client, fixed={"temperature": READER["parameters"]["temperature"]},
                            spend_cap_usd=cap_usd, shared_ledger=ledger)
    out_dir.mkdir(parents=True, exist_ok=True)
    stopped = None
    done: list[dict[str, Any]] = []
    calls = 0
    limit = pilot_calls if pilot_calls is not None else plan["calls"]
    with raw_path.open("w", encoding="utf-8", newline="\n") as handle:
        try:
            for rep in range(plan["repeats"]):
                for case in plan["cases"]:
                    if calls >= limit:
                        raise StopIteration
                    response = wrapped.chat.completions.create(
                        model=READER["model"],
                        messages=[{"role": "system", "content": READER_PROMPT},
                                  {"role": "user", "content": user_message(case["question"], case["context"])}],
                        max_tokens=READER_PARAMS["max_tokens"])
                    calls += 1
                    answer = (response.choices[0].message.content or "").strip()
                    row = {"probe_id": case["probe_id"], "arm": case["arm"], "cell": case["cell"],
                           "repeat": rep, "answer": answer,
                           "correct": int(case["gold_answer"].lower() in answer.lower()),
                           "gold_in_context": case["gold_in_context"]}
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                    handle.flush()
                    done.append(row)
        except StopIteration:
            pass
        except (SpendCapReached, TotalCapReached) as stop:
            stopped = str(stop)
    summary: dict[str, Any] = {}
    for arm in plan["arms"]:
        rows = [r for r in done if r["arm"] == arm]
        summary[arm] = {"n": len(rows), "correct": round(mean([r["correct"] for r in rows]), 4) if rows else None}
    return {"calls": calls, "spent_usd": round(wrapped.spent_usd, 6), "cap_usd": cap_usd,
            "stopped_by_cap": stopped, "by_arm": summary}


def make_live_client(base_url: str):  # pragma: no cover - needs a key and the network
    from openai import OpenAI

    from arena.run_pilot import load_key

    return OpenAI(api_key=load_key(), base_url=base_url)


def stage2_run(args) -> int:
    if not args.i_have_authorisation:
        print("stage2-run refused: pass --i-have-authorisation (the owner's go-ahead for this "
              "spend) and --cap-usd. Nothing was called.", file=sys.stderr)
        return 2
    cap = args.cap_usd
    if cap is None or not math.isfinite(cap) or cap <= 0 or cap > MAX_CAP_USD:
        print("stage2-run refused: --cap-usd must be a finite positive hard cap of at most $%.2f."
              % MAX_CAP_USD, file=sys.stderr)
        return 2
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    if plan.get("reader") != READER:
        print("stage2-run refused: the plan's reader differs from the frozen READER (model, "
              "endpoint, parameters). Nothing was called.", file=sys.stderr)
        return 2
    pilot = args.pilot_calls
    n_calls = pilot if pilot is not None else plan["calls"]
    projected = plan["projected_usd_upper_bound"] * n_calls / max(1, plan["calls"])
    if projected > cap:
        print("stage2-run refused: projected estimate $%.4f exceeds the cap $%.2f."
              % (projected, cap), file=sys.stderr)
        return 2
    client = make_live_client(READER["base_url"])
    summary = run_stage2(plan, client, cap, Path(args.ledger), Path(args.out), pilot)
    write_json(Path(args.out) / "summary.json", summary)
    print(json.dumps(summary, indent=1))
    return 0


# ----------------------------------------------------------------------- generate


def generate_cmd(args) -> int:
    if args.write_config:
        write_json(OUT / "config.json", config_dict())
        print("wrote %s" % (OUT / "config.json"))
        return 0
    seeds = parse_seeds(args.seeds)
    if any(100 <= s <= 119 for s in seeds):
        if not args.allow_test_seeds:
            raise SystemExit("seeds 100-119 are the frozen test seeds; pass --allow-test-seeds only for Stage 1")
        require_frozen_and_stage0()
    for seed in seeds:
        world = gs.generate(seed, history=not args.no_history)
        gs.write_world(world, Path(args.out) / ("seed-%03d" % seed))
        print("seed %d digest %s" % (seed, gs.digest(world)[:16]))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def emb(sp):
        sp.add_argument("--embedder", choices=("minilm", "hashing"), default="minilm")
        sp.add_argument("--model-dir", default=None,
                        help="local all-MiniLM-L6-v2 directory (read-only; never downloaded)")

    g = sub.add_parser("generate")
    g.add_argument("--seeds", default="0-4")
    g.add_argument("--out", default=str(OUT / "dev-worlds"))
    g.add_argument("--no-history", action="store_true")
    g.add_argument("--allow-test-seeds", action="store_true")
    g.add_argument("--write-config", action="store_true",
                   help="write config.json with the current script digests, then exit")
    g.set_defaults(fn=generate_cmd)

    s0 = sub.add_parser("stage0")
    s0.add_argument("--seeds", default="0-4")
    s0.add_argument("--out", default=str(OUT / "stage0"))
    emb(s0)
    s0.set_defaults(fn=stage0)

    s1 = sub.add_parser("stage1")
    s1.add_argument("--seeds", default=None)
    s1.add_argument("--out", default=str(OUT / "stage1"))
    s1.add_argument("--dev-dry-run", action="store_true",
                    help="mechanics check on development seeds, written outside the real stage1 directory")
    emb(s1)
    s1.set_defaults(fn=stage1)

    s2p = sub.add_parser("stage2-plan")
    s2p.add_argument("--seeds", default=None)
    s2p.add_argument("--arms", default=",".join(STAGE2_ARMS))
    s2p.add_argument("--C", type=int, default=250)
    s2p.add_argument("--R", type=float, default=0.10)
    s2p.add_argument("--repeats", type=int, default=3)
    s2p.add_argument("--out", default=str(OUT / "stage2"))
    emb(s2p)
    s2p.set_defaults(fn=stage2_plan)

    s2r = sub.add_parser("stage2-run")
    s2r.add_argument("--plan", default=str(OUT / "stage2" / "plan.json"))
    s2r.add_argument("--i-have-authorisation", action="store_true")
    s2r.add_argument("--cap-usd", type=float, default=None)
    s2r.add_argument("--pilot-calls", type=int, default=None)
    s2r.add_argument("--ledger", default=str(OUT / "stage2-ledger.json"))
    s2r.add_argument("--out", default=str(OUT / "stage2"))
    s2r.set_defaults(fn=stage2_run)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
