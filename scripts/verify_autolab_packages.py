#!/usr/bin/env python3
"""Recompute the published numbers of every autolab result package from the package alone, offline.

An autolab package (``data/lab/autolab-*``, written by the private laboratory through ``scripts/aamr_export.py``) holds
a README with the results, ``knowledge.jsonl`` (the laboratory's objects: program, protocol, run, result, audits,
findings, decisions, report), ``PROVENANCE.json``, ``PUBLISHED_FILES.json`` and ``per_unit.csv`` (one row per
task x arm x seed). This script never sees the laboratory's database or the raw episode logs. It recomputes, from
``per_unit.csv`` only:

* per-arm solved counts and rates;
* every primary contrast (variant - placebo) and every secondary contrast the package states: number of pairs, gains,
  losses, paired difference, discordance and the paired Wald interval at the package's z (the method is recoverable:
  the protocol says "przedzial Walda dla par" and the stored z is the 1 - 0.025/k normal quantile);
* the interval state of each contrast, with the state rule the package's own hypotheses state
  (practical: lower >= SESOI; positive: 0 < lower < SESOI; equivalent: -SESOI < lower and upper < SESOI;
  negative: upper < 0; otherwise inconclusive);
* the per-step process counters (empty retries, untagged answers, invalid actions), step-weighted as pre-registered
  (sum of the counter over all episodes of an arm divided by the sum of their steps), their difference
  memory - placebo, and the pre-registered format criterion (difference <= tolerance, or a 95% interval that includes 0);
* finding verdicts, Brier scores and the per-direction status where they follow from the above;

and compares each with the number declared in the README and in ``knowledge.jsonl``. Numbers match when they agree
to the precision they are declared with (rounding only). It also checks the export manifest's SHA-256 digests and the
provenance hashes of the objects.

Anything the package states that cannot be recomputed from the package (a bootstrap interval whose resampling seed is
not published, a counter that is not a column of ``per_unit.csv``, simulation-based calibration, leakage checks that
need the private family file, the raw-log digest) is printed as ``N/V`` ("not verifiable from the package") with the
reason, never passed silently. ``WARN`` marks two statements of the package that disagree with each other where the
package does not say which one rules; it does not change the exit status.

Properties: standard library only, no network, reads only files inside the package folders, writes nothing.

Exit status: 0 every verifiable check passed in every package; 1 at least one recomputed or declared number differs
(the per-field list is printed at the end); 2 usage error, or a required file is missing or unreadable.

Usage: python scripts/verify_autolab_packages.py [--repo PATH] [--package DIR ...]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import re
import sys
from pathlib import Path
from statistics import NormalDist
from typing import Any, Dict, List, Optional, Sequence, Tuple

PACKAGE_GLOB = "data/lab/autolab-*"
REQUIRED_FILES = ("README.md", "knowledge.jsonl", "per_unit.csv")
KEY_COLUMNS = ("cycle", "unit", "arm", "seed")
OUTCOME = "solved"
STEPS = "steps"
# Per-step process counters: a per_unit.csv column whose rate is sum(counter) / sum(steps) per arm.
STEP_COUNTERS = ("empty_retries", "invalid_no_action_tag", "invalid_actions")
# Columns that are described in the README but carry no declared number to compare with.
DESCRIPTIVE_COLUMNS = ("memory_tokens", "n_memory_sources", "error")
STATES = ("practical", "positive", "equivalent", "negative", "inconclusive")
POSITIVE_STATES = {"practical", "positive"}
NULL_STATES = {"equivalent", "negative"}
LEVEL_NAMES = {"rozwojowy": "developmental"}            # knowledge.jsonl (Polish) -> README (English)
BOOTSTRAP_REPLICATES = 4000
BOOTSTRAP_SEED = 20261118
MINUS = "\u2212"
NUMBER = r"[+\-\u2212]?\d+(?:\.\d+)?"


class InputError(Exception):
    """A required file is missing, outside the package, or cannot be parsed at all."""


# --------------------------------------------------------------------------- reporting
class Report:
    def __init__(self, package: str) -> None:
        self.package = package
        self.failures: List[str] = []
        self.unverifiable: List[str] = []
        self.warnings: List[str] = []
        self.passed = 0

    def check(self, field: str, ok: bool, detail: str = "") -> bool:
        print(("PASS  " if ok else "FAIL  ") + field + (("  | " + detail) if detail else ""))
        if ok:
            self.passed += 1
        else:
            self.failures.append(field + (("  | " + detail) if detail else ""))
        return ok

    def nv(self, field: str, why: str) -> None:
        print("N/V   " + field + "  | not verifiable from the package: " + why)
        self.unverifiable.append(field)

    def warn(self, field: str, why: str) -> None:
        print("WARN  " + field + "  | " + why)
        self.warnings.append(field)

    @staticmethod
    def note(text: str) -> None:
        print("NOTE  " + text)


def number(text: str) -> float:
    return float(text.replace(MINUS, "-").replace("+", ""))


def show(ci: Optional[Tuple[float, float]]) -> str:
    return "n/a" if ci is None else "[%.4f, %.4f]" % ci


def places(text: str) -> int:
    text = text.strip()
    return len(text.split(".", 1)[1]) if "." in text else 0


def agrees(recomputed: float, declared: Any, decimals: Optional[int] = None) -> bool:
    """True when ``recomputed`` rounds to ``declared``: a string keeps its own number of decimals, a JSON number is
    compared at ``decimals`` places (the precision the laboratory stores), an int must be equal."""
    if isinstance(declared, bool) or declared is None:
        return False
    if isinstance(declared, str):
        value, dp = number(declared), places(declared)
    elif isinstance(declared, int) and decimals is None:
        return recomputed == declared
    else:
        value, dp = float(declared), (6 if decimals is None else decimals)
    return abs(recomputed - value) <= 0.5 * 10 ** (-dp) + 1e-9


# --------------------------------------------------------------------------- reading the package
def read_bytes(package: Path, name: str) -> bytes:
    path = (package / name).resolve()
    try:
        path.relative_to(package.resolve())
    except ValueError:
        raise InputError("refusing to read outside the package: " + str(path))
    try:
        return path.read_bytes()
    except OSError as exc:
        raise InputError("cannot read %s/%s: %s" % (package.name, name, exc))


def read_text(package: Path, name: str) -> str:
    try:
        return read_bytes(package, name).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError("%s/%s is not UTF-8: %s" % (package.name, name, exc))


def load_objects(package: Path) -> List[Dict[str, Any]]:
    objects = []
    for i, line in enumerate(read_text(package, "knowledge.jsonl").splitlines(), 1):
        if line.strip():
            try:
                objects.append(json.loads(line))
            except ValueError as exc:
                raise InputError("knowledge.jsonl line %d is not JSON: %s" % (i, exc))
    return objects


class Knowledge:
    def __init__(self, objects: List[Dict[str, Any]]) -> None:
        self.objects = objects
        self.by_id = {o["id"]: o for o in objects}

    def kind(self, kind: str) -> List[Dict[str, Any]]:
        return [o for o in self.objects if o["kind"] == kind]

    def one(self, kind: str) -> Optional[Dict[str, Any]]:
        found = self.kind(kind)
        return found[-1] if found else None

    def parent(self, obj: Dict[str, Any], kind: str) -> Optional[Dict[str, Any]]:
        for pid in obj.get("parents", []):
            if pid.startswith(kind + ":") and pid in self.by_id:
                return self.by_id[pid]
        return None


class Table:
    """per_unit.csv, keyed by (cycle, unit, arm, seed). Structural problems are reported, not fatal, so that the
    numeric consequences of a removed or duplicated row are listed too."""

    def __init__(self, text: str, rep: Report) -> None:
        reader = csv.DictReader(io.StringIO(text))
        self.columns = list(reader.fieldnames or [])
        missing = [c for c in KEY_COLUMNS + (OUTCOME,) if c not in self.columns]
        if missing:
            raise InputError("per_unit.csv lacks the column(s) %s" % ", ".join(missing))
        self.rows: Dict[Tuple[int, str, str, int], Dict[str, int]] = {}
        self.n_rows = 0
        bad_values: List[str] = []
        duplicates: List[str] = []
        numeric = [c for c in self.columns if c not in ("unit", "arm")]
        for line, raw in enumerate(reader, 2):
            self.n_rows += 1
            values: Dict[str, int] = {}
            for col in numeric:
                cell = (raw.get(col) or "").strip()
                if not re.fullmatch(r"\d+", cell):
                    bad_values.append("line %d %s=%r" % (line, col, cell))
                    cell = "0"
                values[col] = int(cell)
            if values[OUTCOME] not in (0, 1):
                bad_values.append("line %d solved=%d" % (line, values[OUTCOME]))
            key = (values["cycle"], raw["unit"], raw["arm"], values["seed"])
            if key in self.rows:
                duplicates.append("line %d repeats cycle %d / %s / %s / seed %d" % ((line,) + key))
                continue
            self.rows[key] = values
        rep.check("per_unit.csv: every cell is a non-negative integer and solved is 0 or 1", not bad_values,
                  "; ".join(bad_values[:5]) + (" ..." if len(bad_values) > 5 else ""))
        rep.check("per_unit.csv: one row per (cycle, unit, arm, seed)", not duplicates,
                  "; ".join(duplicates[:5]) + (" ..." if len(duplicates) > 5 else "") if duplicates else "%d rows" % self.n_rows)

    def cycles(self) -> List[int]:
        return sorted({k[0] for k in self.rows})

    def units(self, cycle: Optional[int] = None) -> List[str]:
        return sorted({k[1] for k in self.rows if cycle is None or k[0] == cycle})

    def arms(self) -> List[str]:
        return sorted({k[2] for k in self.rows})

    def seeds(self) -> List[int]:
        return sorted({k[3] for k in self.rows})

    def arm_rows(self, cycle: int, arm: str) -> Dict[Tuple[str, int], Dict[str, int]]:
        return {(k[1], k[3]): v for k, v in self.rows.items() if k[0] == cycle and k[2] == arm}


# --------------------------------------------------------------------------- statistics
def paired(table: Table, cycle: int, a: str, b: str, z: float) -> Dict[str, Any]:
    """a - b over the (unit, seed) pairs present in both arms; paired Wald interval."""
    ra, rb = table.arm_rows(cycle, a), table.arm_rows(cycle, b)
    keys = sorted(set(ra) & set(rb))
    n = len(keys)
    gains = sum(1 for k in keys if ra[k][OUTCOME] == 1 and rb[k][OUTCOME] == 0)
    losses = sum(1 for k in keys if ra[k][OUTCOME] == 0 and rb[k][OUTCOME] == 1)
    if n == 0:
        return {"n": 0, "gains": 0, "losses": 0, "diff": float("nan"), "discordance": float("nan"), "ci": (float("nan"),) * 2}
    diff, disc = (gains - losses) / n, (gains + losses) / n
    se = math.sqrt(max(disc - diff * diff, 0.0) / n)
    return {"n": n, "gains": gains, "losses": losses, "diff": diff, "discordance": disc, "ci": (diff - z * se, diff + z * se)}


def interval_states(lo: float, hi: float, sesoi: float) -> List[str]:
    out = []
    if lo >= sesoi:
        out.append("practical")
    elif lo > 0:
        out.append("positive")
    if -sesoi < lo and hi < sesoi:
        out.append("equivalent")
    if hi < 0:
        out.append("negative")
    return out or ["inconclusive"]


def step_rate(rows: Dict[Any, Dict[str, int]], counter: str) -> float:
    steps = sum(r[STEPS] for r in rows.values())
    return sum(r[counter] for r in rows.values()) / steps if steps else float("nan")


def ratio_bootstrap(table: Table, cycle: int, a: str, b: str, counters: Sequence[str]) -> Dict[str, Tuple[float, float]]:
    """Percentile interval of step_rate(a) - step_rate(b), resampling (unit, seed) pairs with a fixed seed.
    Used only as an approximate reference for the laboratory's bootstrap interval, whose seed is not published."""
    ra, rb = table.arm_rows(cycle, a), table.arm_rows(cycle, b)
    keys = sorted(set(ra) & set(rb))
    if not keys:
        return {}
    cols = [STEPS] + list(counters)
    va = [[ra[k][c] for c in cols] for k in keys]
    vb = [[rb[k][c] for c in cols] for k in keys]
    rng = random.Random(BOOTSTRAP_SEED)
    n, m = len(keys), len(cols)
    draws: Dict[str, List[float]] = {c: [] for c in counters}
    for _ in range(BOOTSTRAP_REPLICATES):
        sa, sb = [0] * m, [0] * m
        for _i in range(n):
            j = rng.randrange(n)
            xa, xb = va[j], vb[j]
            for c in range(m):
                sa[c] += xa[c]
                sb[c] += xb[c]
        for c, name in enumerate(counters, 1):
            if sa[0] and sb[0]:
                draws[name].append(sa[c] / sa[0] - sb[c] / sb[0])
    out = {}
    for name, values in draws.items():
        values.sort()
        if values:
            out[name] = (values[int(0.025 * len(values))], values[int(math.ceil(0.975 * len(values))) - 1])
    return out


def bootstrap_tolerance(ci: Tuple[float, float]) -> float:
    # Two percentile bootstraps of the same data with different seeds differ by Monte Carlo noise of the order of
    # 0.1 standard errors per endpoint at 1000 replicates; a quarter of the half-width (about half a standard error)
    # plus the declared rounding is a generous bound for "the same method on the same data".
    return 0.25 * (ci[1] - ci[0]) / 2


# --------------------------------------------------------------------------- README parsing
def readme_sections(text: str) -> Tuple[str, Dict[str, str]]:
    parts = re.split(r"^## ", text, flags=re.MULTILINE)
    head, sections = parts[0], {}
    for part in parts[1:]:
        title, _, body = part.partition("\n")
        sections[title.strip()] = body
    return head, sections


def md_tables(body: str) -> List[List[List[str]]]:
    tables, current = [], []
    for line in body.splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                continue
            current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


INTERVAL = re.compile(r"\[(" + NUMBER + r")[,;] (" + NUMBER + r")\]")
# "invalid_no_action_tag per step, arm - placebo +0.034 [+0.014, +0.053] > 0.03" (README, English)
# "invalid_no_action_tag na krok wariant - placebo +0.034 [+0.014; +0.053] > 0.03" (knowledge.jsonl, Polish)
# "empty_retries +0.582 [+0.459; +0.725]" (post-hoc audit, Polish)
COUNTER_CLAIM = re.compile(r"\b(" + "|".join(STEP_COUNTERS) + r"|min_tokens|[a-z_]+)\b(?: per step, arm \u2212 placebo| na krok wariant \u2212 placebo)? (" +
                           NUMBER + r") \[(" + NUMBER + r")[,;] (" + NUMBER + r")\](?: > (" + NUMBER + r"))?")


# --------------------------------------------------------------------------- verification of one package
class Verifier:
    def __init__(self, package: Path, rep: Report) -> None:
        self.package = package
        self.rep = rep
        self.k = Knowledge(load_objects(package))
        self.readme = read_text(package, "README.md")
        self.table = Table(read_text(package, "per_unit.csv"), rep)
        self.recomputed: Dict[int, Dict[str, Any]] = {}

    # ---------------------------------------------------------------- package integrity
    def manifest_and_provenance(self) -> None:
        rep, pkg = self.rep, self.package
        present = sorted(p.name for p in pkg.iterdir() if p.is_file())
        if (pkg / "PUBLISHED_FILES.json").is_file():
            manifest = json.loads(read_text(pkg, "PUBLISHED_FILES.json"))
            listed = set()
            for entry in manifest.get("published", []):
                name = entry["path"]
                listed.add(name)
                if not (pkg / name).is_file():
                    rep.check("PUBLISHED_FILES.json: %s exists" % name, False, "listed in the manifest but missing")
                    continue
                data = read_bytes(pkg, name)
                digest = hashlib.sha256(data).hexdigest()
                rep.check("PUBLISHED_FILES.json: sha256 and size of %s" % name,
                          digest == entry.get("sha256") and len(data) == entry.get("bytes"),
                          "file %s / %d bytes, manifest %s / %s bytes" % (digest[:12], len(data), str(entry.get("sha256"))[:12], entry.get("bytes")))
            for name in present:
                if name not in listed and name != "PUBLISHED_FILES.json":
                    rep.nv("PUBLISHED_FILES.json: %s" % name, "the file is in the package folder but not in its export manifest, so its "
                           "bytes are not pinned by the export; its numbers are still recomputed below")
        else:
            rep.nv("PUBLISHED_FILES.json", "the package has no export manifest")
        bad = []
        seen = set()
        for o in self.k.objects:
            body = {"kind": o["kind"], "program": o["program"], "payload": o["payload"], "parents": sorted(set(o["parents"]))}
            sha = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
            if o.get("redacted"):
                if sha != o.get("sha256_redacted"):
                    bad.append(o["id"] + " (redacted copy)")
            elif sha != o.get("sha256") or not o["id"].endswith(sha[:16]):
                bad.append(o["id"])
            bad += [o["id"] + " parent " + p for p in o["parents"] if p not in seen]
            seen.add(o["id"])
        rep.check("knowledge.jsonl: object hashes and parent order (as verify_provenance.py)", not bad, "; ".join(bad[:4]) or "%d objects" % len(self.k.objects))
        redacted = sum(1 for o in self.k.objects if o.get("redacted"))
        if redacted:
            rep.nv("knowledge.jsonl: original hashes of %d redacted object(s)" % redacted,
                   "machine-local paths were replaced; only the redacted copy's hash can be recomputed, the id is the hash of the private original")
        if (pkg / "PROVENANCE.json").is_file():
            prov = json.loads(read_text(pkg, "PROVENANCE.json"))
            digest = hashlib.sha256(read_bytes(pkg, "knowledge.jsonl")).hexdigest()
            rep.check("PROVENANCE.json: knowledge_sha256", prov.get("knowledge_sha256") == digest, "knowledge.jsonl %s" % digest[:12])
            rep.check("PROVENANCE.json: objects = %s" % prov.get("objects"), prov.get("objects") == len(self.k.objects), "knowledge.jsonl has %d" % len(self.k.objects))
            runs = {r["id"]: r["payload"] for r in self.k.kind("run")}
            for raw in prov.get("raw", []):
                run = runs.get(raw.get("run"), {})
                rep.check("PROVENANCE.json: raw records of %s = %s" % (raw.get("run"), raw.get("records")),
                          raw.get("records") == run.get("records") and raw.get("raw_sha256") == run.get("raw_sha256"),
                          "run object: %s records, raw %s" % (run.get("records"), str(run.get("raw_sha256"))[:12]))
                rep.nv("PROVENANCE.json: raw_sha256 of %s" % raw.get("run"), "the raw episode log is private (%s)" % raw.get("location"))
        else:
            rep.nv("PROVENANCE.json", "the package has no provenance file")

    # ---------------------------------------------------------------- per_unit.csv against the run
    def structure(self) -> None:
        rep, t = self.rep, self.table
        protocol = self.protocol()
        arms = list(protocol.get("arms") or [])
        seeds = list(protocol.get("seeds") or [])
        rep.check("per_unit.csv: arms = protocol arms %s" % arms, t.arms() == sorted(arms), "table has %s" % t.arms())
        rep.check("per_unit.csv: seeds = protocol seeds %s" % seeds, t.seeds() == sorted(seeds), "table has %s" % t.seeds())
        if len(seeds) > 1:
            rep.nv("pairing over several seeds", "the package does not state whether pairs are (unit, seed) or units averaged over seeds; "
                   "pairs are taken as (unit, seed) here")
        runs = self.k.kind("run")
        for run in runs:
            cycle = run.get("cycle")
            p = run["payload"]
            units = sorted(p.get("units") or [])
            have = t.units(cycle)
            missing, extra = sorted(set(units) - set(have)), sorted(set(have) - set(units))
            rep.check("cycle %s: units in per_unit.csv = the %d units of %s" % (cycle, len(units), run["id"]), not missing and not extra,
                      "missing %s; not in the run %s" % (missing[:3], extra[:3]) if missing or extra else "%d units" % len(have))
            grid_missing = ["%s/%s/seed %d" % (u, a, s) for u in units for a in p.get("arms", []) for s in p.get("seeds", [])
                            if (cycle, u, a, s) not in t.rows]
            rep.check("cycle %s: complete unit x arm x seed grid (completeness)" % cycle, not grid_missing,
                      "missing %d row(s): %s" % (len(grid_missing), "; ".join(grid_missing[:3])) if grid_missing else
                      "%d units x %d arms x %d seed(s)" % (len(units), len(p.get("arms", [])), len(p.get("seeds", []))))
            rows = sum(1 for k in t.rows if k[0] == cycle)
            rep.check("cycle %s: rows = run.records %s" % (cycle, p.get("records")), rows == p.get("records") and t.n_rows == sum(
                r["payload"].get("records", 0) for r in runs), "%d distinct rows, %d lines" % (rows, t.n_rows))
            errors = sum(1 for k, v in t.rows.items() if k[0] == cycle and v.get("error", 0))
            measured = (p.get("measurement") or {}).get("errors_counted_as_unsolved")
            if measured is None:
                rep.nv("cycle %s: errors counted as unsolved" % cycle, "the run object does not state it (the table has %d row(s) with error != 0)" % errors)
            else:
                rep.check("cycle %s: rows with error = run.measurement.errors_counted_as_unsolved %s" % (cycle, measured), errors == measured, "table %d" % errors)
            rep.nv("cycle %s: units_sha256 / raw_sha256 of %s" % (cycle, run["id"]), "they hash private files (the unit list file and the raw log)")
        other = [c for c in t.columns if c not in KEY_COLUMNS + (OUTCOME, STEPS) + STEP_COUNTERS + DESCRIPTIVE_COLUMNS]
        for col in other:
            rep.nv("per_unit.csv column %s" % col, "no number declared in the package is computed from it by a rule this verifier knows")

    def protocol(self) -> Dict[str, Any]:
        run = self.k.one("run")
        proto = self.k.parent(run, "protocol") if run else None
        proto = proto or self.k.one("protocol")
        return proto["payload"] if proto else {}

    def program(self) -> Dict[str, Any]:
        prog = self.k.one("program")
        return prog["payload"] if prog else {}

    def placebo(self) -> str:
        return (self.program().get("domain_params") or {}).get("placebo") or "placebo"

    def sesoi(self) -> float:
        protocol, program = self.protocol(), self.program()
        if protocol.get("sesoi") != program.get("sesoi"):
            self.rep.check("SESOI: protocol %s = program %s" % (protocol.get("sesoi"), program.get("sesoi")), False)
        return float(protocol.get("sesoi", program.get("sesoi")))

    # ---------------------------------------------------------------- result objects
    def results(self) -> None:
        rep, t = self.rep, self.table
        sesoi, placebo = self.sesoi(), self.placebo()
        for res in self.k.kind("result"):
            cycle = res.get("cycle")
            p = res["payload"]
            tag = "cycle %s %s" % (cycle, res["id"])
            k = int(p.get("family_size", 1))
            z = NormalDist().inv_cdf(1 - 0.025 / k)
            rep.check("%s: z = %s (normal quantile 1 - 0.025/k, k = %d)" % (tag, p.get("z"), k), agrees(z, p.get("z"), 6), "recomputed %.6f" % z)
            units = t.units(cycle)
            rep.check("%s: n_units = %s" % (tag, p.get("n_units")), len(units) == p.get("n_units"), "recomputed %d" % len(units))
            rec: Dict[str, Any] = {"z": z, "rates": {}, "contrasts": {}, "k": k, "sesoi": sesoi}
            for arm in t.arms():
                rows = t.arm_rows(cycle, arm)
                solved = sum(r[OUTCOME] for r in rows.values())
                rate = solved / len(rows) if rows else float("nan")
                rec["rates"][arm] = rate
                declared = (p.get("success_rate") or {}).get(arm)
                rep.check("%s: success_rate[%s] = %s" % (tag, arm, declared), agrees(rate, declared, 6),
                          "recomputed %d solved / %d = %.6f" % (solved, len(rows), rate))
            for arm in sorted(set((p.get("success_rate") or {})) - set(t.arms())):
                rep.check("%s: success_rate[%s] has rows in per_unit.csv" % (tag, arm), False, "no rows for this arm")
            contrasts = [("primary", arm, arm, placebo, body) for arm, body in (p.get("primary") or {}).items()]
            for name, body in (p.get("secondary") or {}).items():
                a, _, b = name.partition("-")
                contrasts.append(("secondary", name, a, b, body))
            for group, name, a, b, body in contrasts:
                c = paired(t, cycle, a, b, z)
                rec["contrasts"][(group, name)] = c
                where = "%s: %s.%s (%s - %s)" % (tag, group, name, a, b)
                for key in ("n", "gains", "losses"):
                    rep.check("%s %s = %s" % (where, key, body.get(key)), c[key] == body.get(key), "recomputed %d" % c[key])
                for key in ("diff", "discordance"):
                    rep.check("%s %s = %s" % (where, key, body.get(key)), agrees(c[key], body.get(key), 6), "recomputed %.6f" % c[key])
                ci = body.get("ci") or [None, None]
                rep.check("%s ci = %s (paired Wald)" % (where, ci), agrees(c["ci"][0], ci[0], 6) and agrees(c["ci"][1], ci[1], 6),
                          "recomputed [%.6f, %.6f]" % c["ci"])
                self.check_state("%s state" % where, c["ci"], sesoi, body.get("state"))
                for key in sorted(set(body) - {"n", "gains", "losses", "diff", "discordance", "ci", "state"}):
                    rep.nv("%s %s" % (where, key), "no rule in the package says how this field is computed")
            for key in sorted(set(p) - {"z", "n_units", "family_size", "success_rate", "primary", "secondary", "estimand", "raw_sha256", "seed"}):
                rep.nv("%s: %s" % (tag, key), "no rule in the package says how this field is computed")
            if "seed" in p:
                rep.check("%s: seed = %s" % (tag, p["seed"]), [p["seed"]] == t.seeds(), "table seeds %s" % t.seeds())
            rep.nv("%s: raw_sha256" % tag, "hash of the private raw log")
            self.recomputed[cycle] = rec

    def check_state(self, field: str, ci: Tuple[float, float], sesoi: float, declared: Any) -> None:
        candidates = interval_states(ci[0], ci[1], sesoi)
        near = [b for b in (sesoi, -sesoi, 0.0) for x in ci if abs(x - b) < 1e-6]
        if near:
            self.rep.nv(field, "an interval end lies within rounding of a state boundary (%s), so the state depends on unpublished digits" % near)
            return
        self.rep.check("%s = %s" % (field, declared), declared in candidates,
                       "rule gives %s at SESOI %s for [%.6f, %.6f]" % (" or ".join(candidates), sesoi, ci[0], ci[1]))
        if len(candidates) > 1 and declared in candidates:
            self.rep.nv(field + " (name)", "the interval satisfies %s; the package does not say which name the code uses" % " and ".join(candidates))

    # ---------------------------------------------------------------- process counters (format criterion)
    def process(self) -> Dict[int, Dict[str, Any]]:
        """Recompute per-step rates and memory - placebo differences, check the code audits' process_balance."""
        rep, t = self.rep, self.table
        criteria_prog = (self.program().get("domain_params") or {}).get("format_criteria")
        placebo = self.placebo()
        variants = list(self.protocol().get("treatments") or [])
        counters = [c for c in STEP_COUNTERS if c in t.columns]
        out: Dict[int, Dict[str, Any]] = {}
        for cycle in t.cycles():
            rates = {arm: {c: step_rate(t.arm_rows(cycle, arm), c) for c in counters} for arm in t.arms()}
            boot = {arm: ratio_bootstrap(t, cycle, arm, placebo, counters) for arm in variants}
            out[cycle] = {"rates": rates, "boot": boot, "criteria": criteria_prog}
        for audit in self.k.kind("audit"):
            checks = (audit["payload"].get("checks") or {})
            ms = checks.get("measurement_sensitivity") or {}
            pb = ms.get("process_balance")
            cycle = audit.get("cycle")
            if cycle not in out:
                continue
            tag = "cycle %s %s (%s)" % (cycle, audit["id"], audit["payload"].get("by"))
            if "placebo_rate" in ms:
                rate = self.recomputed.get(cycle, {}).get("rates", {}).get(placebo, float("nan"))
                rep.check("%s: placebo_rate = %s" % (tag, ms["placebo_rate"]), agrees(rate, ms["placebo_rate"], 4), "recomputed %.4f" % rate)
            if not pb:
                continue
            criteria = pb.get("criteria") or {}
            if criteria_prog is None:
                rep.nv("%s: format criteria %s fixed before the run" % (tag, criteria),
                       "the program in the package has no format_criteria; the README cites the private instrument file for them")
                out[cycle]["criteria"] = criteria
            else:
                rep.check("%s: criteria = program format_criteria %s" % (tag, criteria_prog), criteria == criteria_prog, "audit %s" % criteria)
            for arm, values in (pb.get("rates") or {}).items():
                for counter, declared in values.items():
                    field = "%s: process_balance.rates[%s][%s] = %s" % (tag, arm, counter, declared)
                    if counter not in counters:
                        rep.nv(field, "%s is not a column of per_unit.csv" % counter)
                    elif arm not in out[cycle]["rates"]:
                        rep.check(field, False, "no rows for arm %s" % arm)
                    else:
                        got = out[cycle]["rates"][arm][counter]
                        rep.check(field + " (step-weighted)", agrees(got, declared, 4), "recomputed %.4f" % got)
            for arm, per in (pb.get("per_arm") or {}).items():
                for counter, body in per.items():
                    field = "%s: process_balance.per_arm[%s][%s]" % (tag, arm, counter)
                    if counter not in counters:
                        rep.nv(field, "%s is not a column of per_unit.csv (declared diff %s, ci %s, state %s)" % (
                            counter, body.get("diff"), body.get("ci"), body.get("state", "imbalanced=%s" % body.get("imbalanced"))))
                        continue
                    self.check_counter(field, cycle, arm, counter, body, criteria, out)
        return out

    def counter_result(self, cycle: int, arm: str, counter: str, out: Dict[int, Dict[str, Any]]) -> Tuple[float, Optional[Tuple[float, float]]]:
        rates = out[cycle]["rates"]
        diff = rates[arm][counter] - rates[self.placebo()][counter]
        return diff, out[cycle]["boot"].get(arm, {}).get(counter)

    def criterion(self, diff: float, ci: Optional[Tuple[float, float]], tol: float) -> Optional[bool]:
        """Imbalanced = difference above the tolerance and a 95% interval that excludes 0 (the package's words:
        'memory - placebo <= tolerance or a 95% bootstrap interval that includes 0' passes). None = not decidable."""
        if diff <= tol + 1e-12:
            return False if diff >= -tol else None
        if ci is None:
            return None
        margin = bootstrap_tolerance(ci)
        if ci[0] > margin:
            return True
        if ci[0] < -margin:
            return False
        return None

    def check_counter(self, field: str, cycle: int, arm: str, counter: str, body: Dict[str, Any], criteria: Dict[str, Any],
                      out: Dict[int, Dict[str, Any]]) -> None:
        rep = self.rep
        diff, ci = self.counter_result(cycle, arm, counter, out)
        rep.check("%s.diff = %s (arm - %s, step-weighted)" % (field, body.get("diff"), self.placebo()), agrees(diff, body.get("diff"), 4), "recomputed %.4f" % diff)
        dci = body.get("ci")
        if ci is not None and dci:
            tol = bootstrap_tolerance(ci) + 0.5e-4
            ok = abs(ci[0] - dci[0]) <= tol and abs(ci[1] - dci[1]) <= tol
            rep.check("%s.ci = %s, approximately (bootstrap)" % (field, dci), ok,
                      "own paired bootstrap (seed %d, %d replicates) [%.4f, %.4f], tolerance %.4f" % (BOOTSTRAP_SEED, BOOTSTRAP_REPLICATES, ci[0], ci[1], tol))
            rep.nv("%s.ci (exact digits)" % field, "a bootstrap interval; the package publishes neither its resampling seed nor its number of "
                   "replicates, so only agreement within Monte Carlo error is checked")
        if "preregistered" in body:
            rep.check("%s.preregistered = %s" % (field, body["preregistered"]), body["preregistered"] == (counter in criteria), "criteria %s" % sorted(criteria))
        tol = body.get("tolerance")
        if counter in criteria:
            rep.check("%s.tolerance = %s" % (field, tol), tol == criteria[counter], "criteria %s" % criteria[counter])
        elif tol is not None:
            rep.nv("%s.tolerance = %s" % (field, tol), "the counter is not pre-registered and the package does not state where its tolerance comes from")
        if tol is None:
            return
        verdict = self.criterion(diff, ci, float(tol))
        declared_flags = [("imbalanced", body.get("imbalanced"))] + ([("state", body.get("state") == "imbalanced")] if "state" in body else [])
        for name, flag in declared_flags:
            if name == "state" and body.get("state") not in ("balanced", "imbalanced"):
                rep.nv("%s.state = %s" % (field, body.get("state")), "unknown state name")
                continue
            if verdict is None:
                rep.nv("%s.%s = %s" % (field, name, body.get(name)), "the decision depends on whether the unpublished bootstrap interval includes 0 "
                       "(own interval %s), or the difference is below -tolerance, which the criterion's wording does not cover" % show(ci))
            else:
                why = ("diff %.4f <= tolerance %s" % (diff, tol)) if diff <= float(tol) else \
                    ("diff %.4f > tolerance %s and the interval %s %s 0" % (diff, tol, show(ci), "excludes" if verdict else "includes"))
                rep.check("%s.%s = %s" % (field, name, body.get(name)), flag == verdict,
                          "criterion: %s -> %s" % (why, "imbalanced" if verdict else "balanced"))

    def claim(self, field: str, text: str, cycle: int, arm: str, out: Dict[int, Dict[str, Any]], criteria: Dict[str, Any]) -> bool:
        """Check every '<counter> +d [lo, hi] (> tol)' claim in a sentence; returns True if one was found."""
        found = False
        for m in COUNTER_CLAIM.finditer(text):
            counter, d, lo, hi, tol = m.groups()
            if counter not in STEP_COUNTERS:
                continue
            found = True
            if counter not in self.table.columns:
                self.rep.nv("%s: %s" % (field, m.group(0)), "%s is not a column of per_unit.csv" % counter)
                continue
            diff, ci = self.counter_result(cycle, arm, counter, out)
            self.rep.check("%s: %s %s (step-weighted arm - placebo)" % (field, counter, d), agrees(diff, d), "recomputed %.4f" % diff)
            if ci is not None:
                width = bootstrap_tolerance(ci) + 0.5 * 10 ** (-places(lo))
                self.rep.check("%s: %s interval [%s, %s], approximately (bootstrap)" % (field, counter, lo, hi),
                               abs(ci[0] - number(lo)) <= width and abs(ci[1] - number(hi)) <= width,
                               "own bootstrap [%.4f, %.4f], tolerance %.4f; exact digits not verifiable (seed not published)" % (ci[0], ci[1], width))
            if tol is not None:
                self.rep.check("%s: %s threshold %s = pre-registered criterion" % (field, counter, tol), criteria.get(counter) is not None and
                               agrees(float(criteria[counter]), tol), "criteria %s" % criteria)
                verdict = self.criterion(diff, ci, number(tol))
                if verdict is None:
                    self.rep.nv("%s: %s exceeds the criterion" % (field, counter), "decision depends on the unpublished bootstrap")
                else:
                    self.rep.check("%s: %s exceeds the criterion" % (field, counter), verdict, "recomputed diff %.4f, own interval %s" % (diff, show(ci)))
        return found

    # ---------------------------------------------------------------- findings, report
    def verdict(self, predicted: str, state: str) -> Optional[str]:
        if state == "inconclusive":
            return "inconclusive"
        if predicted == "positive":
            return "supported" if state in POSITIVE_STATES else "refuted" if state in NULL_STATES else None
        if predicted == "null":
            return "supported" if state in NULL_STATES else "refuted" if state in POSITIVE_STATES else None
        return None

    def findings(self, process: Dict[int, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        rep = self.rep
        derived: Dict[str, Dict[str, Any]] = {}
        for f in self.k.kind("finding"):
            p, cycle = f["payload"], f.get("cycle")
            tag = "cycle %s %s" % (cycle, f["id"])
            rec = self.recomputed.get(cycle)
            c = rec["contrasts"].get(("primary", p.get("arm"))) if rec else None
            if c is None:
                rep.check("%s: arm %s has a primary contrast" % (tag, p.get("arm")), False)
                continue
            hyp = self.k.parent(f, "hypothesis")
            hp = hyp["payload"] if hyp else {}
            label = hp.get("id", "?")
            for key in ("n",):
                rep.check("%s (%s): %s = %s" % (tag, label, key, p.get(key)), c[key] == p.get(key), "recomputed %d" % c[key])
            for key in ("diff", "discordance"):
                rep.check("%s (%s): %s = %s" % (tag, label, key, p.get(key)), agrees(c[key], p.get(key), 6), "recomputed %.6f" % c[key])
            ci = p.get("ci") or [None, None]
            rep.check("%s (%s): ci = %s" % (tag, label, ci), agrees(c["ci"][0], ci[0], 6) and agrees(c["ci"][1], ci[1], 6), "recomputed [%.6f, %.6f]" % c["ci"])
            rep.check("%s (%s): k = %s" % (tag, label, p.get("k")), p.get("k") == rec["k"], "family_size %d" % rec["k"])
            self.check_state("%s (%s): state" % (tag, label), c["ci"], rec["sesoi"], p.get("state"))
            state = p.get("state")
            if hyp is None:
                rep.nv("%s: verdict / predicted" % tag, "the finding has no hypothesis parent")
            else:
                rep.check("%s (%s): predicted = hypothesis.predicted %s" % (tag, label, hp.get("predicted")), p.get("predicted") == hp.get("predicted"),
                          "finding says %s" % p.get("predicted"))
                want = self.verdict(hp.get("predicted"), state)
                if want is None:
                    rep.nv("%s (%s): verdict = %s" % (tag, label, p.get("verdict")), "no stated rule for predicted %r and state %r" % (hp.get("predicted"), state))
                else:
                    rep.check("%s (%s): verdict = %s" % (tag, label, p.get("verdict")), p.get("verdict") == want,
                              "rule (hypothesis falsification texts): predicted %s, state %s -> %s" % (hp.get("predicted"), state, want))
                expected = hp.get("expected_state")
                if expected and state != expected and p.get("verdict") == "supported":
                    text = str(hp.get("falsification") or "")
                    mention = (" Its falsification text mentions the state '%s': %r." % (state, text[:160])) if state in text else ""
                    rep.warn("%s (%s): verdict supported with state %s, hypothesis expected_state %s" % (tag, label, state, expected),
                             "the verdict follows the predicted direction (%s), but the hypothesis states a narrower expected state.%s "
                             "The package does not say which of the two rules decides the verdict." % (hp.get("predicted"), mention))
                if "p_positive" in hp and "brier" in p:
                    outcome = 1.0 if state in POSITIVE_STATES else 0.0
                    brier = (float(hp["p_positive"]) - outcome) ** 2
                    rep.check("%s (%s): brier = %s ((p_positive %s - [state positive or practical])^2)" % (tag, label, p["brier"], hp["p_positive"]),
                              agrees(brier, p["brier"], 4), "recomputed %.4f" % brier)
                    derived[f["id"]] = {"brier": brier}
            if "negative_result" in p:
                rep.nv("%s (%s): negative_result = %s" % (tag, label, p["negative_result"]), "the package states no rule for this flag")
            if p.get("level") not in LEVEL_NAMES:
                rep.nv("%s (%s): level = %s" % (tag, label, p.get("level")), "an evidence level the package does not define")
            problems = p.get("measurement_problem") or []
            criteria = process.get(cycle, {}).get("criteria") or {}
            for text in problems:
                if not self.claim("%s (%s): measurement_problem" % (tag, label), text, cycle, p.get("arm"), process, criteria):
                    rep.nv("%s (%s): measurement_problem %r" % (tag, label, text[:60]), "no counter claim this verifier can parse")
            derived.setdefault(f["id"], {}).update({"state": state, "verdict": p.get("verdict"), "arm": p.get("arm"), "cycle": cycle,
                                                    "diff": c["diff"], "ci": c["ci"], "label": label, "predicted": hp.get("predicted"),
                                                    "level": p.get("level")})
        return derived

    def derived_status(self, arm: str, process: Dict[int, Dict[str, Any]]) -> Optional[str]:
        """measurement_problem when a pre-registered format counter is imbalanced; otherwise the status follows decision
        rules (replication, retry with a larger n) that the package records but does not state as a computable rule."""
        for cycle, data in process.items():
            criteria = data.get("criteria") or {}
            for counter, tol in criteria.items():
                if counter not in self.table.columns or arm not in data["boot"]:
                    continue
                diff, ci = self.counter_result(cycle, arm, counter, process)
                if self.criterion(diff, ci, float(tol)):
                    return "measurement_problem"
        return None

    def report_object(self, process: Dict[int, Dict[str, Any]], findings: Dict[str, Dict[str, Any]]) -> None:
        rep = self.rep
        obj = self.k.one("report")
        if obj is None:
            rep.nv("report", "the package has no report object")
            return
        p = obj["payload"]
        units = len(self.table.units())
        rep.check("report: units_used = %s" % p.get("units_used"), p.get("units_used") == units, "per_unit.csv has %d units" % units)
        rep.check("report: cycles = %s" % p.get("cycles"), p.get("cycles") == len(self.table.cycles()), "per_unit.csv has cycles %s" % self.table.cycles())
        briers = [v["brier"] for v in findings.values() if "brier" in v]
        if briers and "brier_mean" in p:
            mean = sum(briers) / len(briers)
            rep.check("report: brier_mean = %s" % p["brier_mean"], agrees(mean, p["brier_mean"], 4), "mean of %d recomputed Brier scores %.4f" % (len(briers), mean))
        for item in p.get("findings") or []:
            f = findings.get(item.get("id"))
            if f is None:
                rep.check("report.findings %s is a finding object" % item.get("id"), False)
                continue
            ok = agrees(f["diff"], item.get("diff"), 6) and agrees(f["ci"][0], (item.get("ci") or [None])[0], 6) and \
                agrees(f["ci"][1], (item.get("ci") or [None, None])[1], 6) and item.get("state") == f["state"] and item.get("verdict") == f["verdict"]
            rep.check("report.findings %s: diff, ci, state, verdict" % item["id"], ok, "recomputed %.6f [%.6f, %.6f] %s %s" % (f["diff"], f["ci"][0], f["ci"][1], f["state"], f["verdict"]))
        for arm, body in (p.get("arms") or {}).items():
            want = self.derived_status(arm, process)
            if want is None:
                rep.nv("report.arms[%s].status = %s" % (arm, body.get("status")), "no pre-registered format criterion fails, so the status follows decision rules "
                       "(replication on fresh units, a larger retry) that are not computable from the package")
            elif body.get("status") == want:
                rep.check("report.arms[%s].status = %s" % (arm, body.get("status")), True, "a pre-registered format criterion fails")
            else:
                later = [d for d in self.k.kind("decision") if d["payload"].get("action") == "post_hoc_annotation"
                         and d["payload"].get("measurement_problem")]
                if later:
                    rep.note("report.arms[%s].status = %s predates %s, which records the measurement problem after the result; "
                             "the README status is checked against the recomputed criterion" % (arm, body.get("status"), later[-1]["id"]))
                else:
                    rep.check("report.arms[%s].status = %s" % (arm, body.get("status")), False, "a pre-registered format criterion fails -> %s" % want)
        for key in ("role_calls", "model_calls"):
            if key in p:
                rep.nv("report: %s = %s" % (key, p[key]), "model calls are not part of the published tables")
        mp =p.get("measurement_problems") or {}
        for arm, texts in mp.items():
            for text in texts:
                for cycle in process:
                    if not self.claim("report.measurement_problems[%s]" % arm, text, cycle, arm, process, process[cycle].get("criteria") or {}):
                        rep.nv("report.measurement_problems[%s] %r" % (arm, text[:60]), "no counter claim this verifier can parse")

    def noise_check(self) -> None:
        rep = self.rep
        assumed = self.protocol().get("discordance_assumed")
        for audit in self.k.kind("audit"):
            nv = (audit["payload"].get("checks") or {}).get("noise_vs_calibration")
            cycle = audit.get("cycle")
            rec = self.recomputed.get(cycle)
            if not nv or not rec:
                continue
            tag = "cycle %s %s: noise_vs_calibration" % (cycle, audit["id"])
            prim = [c for (g, _), c in rec["contrasts"].items() if g == "primary"]
            if not prim:
                continue
            worst = max(prim, key=lambda c: c["discordance"])
            # The laboratory takes the bound from the discordance as it stores it (rounded to 6 places): with the
            # unrounded 110/300 of V4 the bound is 0.3121362, with the stored 0.366667 it is 0.3121365 -> 0.312137.
            disc = round(worst["discordance"], 6)
            lower = disc - rec["z"] * math.sqrt(disc * (1 - disc) / worst["n"])
            rep.check("%s.observed_max = %s" % (tag, nv.get("observed_max")), agrees(worst["discordance"], nv.get("observed_max"), 6),
                      "largest primary discordance %.6f" % worst["discordance"])
            rep.check("%s.observed_lower_bound = %s" % (tag, nv.get("observed_lower_bound")), agrees(lower, nv.get("observed_lower_bound"), 6),
                      "Wald lower bound at 2.5%%/k of the stored discordance %.6f: %.7f" % (disc, lower))
            rep.check("%s.assumed = %s (protocol discordance_assumed)" % (tag, nv.get("assumed")), nv.get("assumed") == assumed)
            if lower <= float(nv.get("assumed", assumed)):
                rep.check("%s.ok = %s" % (tag, nv.get("ok")), nv.get("ok") is True, "lower bound %.4f <= assumed %.2f, so the rule cannot fire" % (lower, assumed))
            else:
                rep.nv("%s.ok = %s" % (tag, nv.get("ok")), "the rule also needs the power at the observed noise, a simulation not in the package")
            completeness = (audit["payload"].get("checks") or {}).get("completeness")
            if completeness:
                n_rows = sum(1 for k in self.table.rows if k[0] == cycle)
                rep.check("cycle %s %s: completeness records %s of expected %s" % (cycle, audit["id"], completeness.get("records"), completeness.get("expected")),
                          completeness.get("records") == n_rows and completeness.get("expected") == len(self.table.units(cycle)) * len(self.table.arms()) * len(self.table.seeds()),
                          "per_unit.csv: %d rows, grid %d" % (n_rows, len(self.table.units(cycle)) * len(self.table.arms()) * len(self.table.seeds())))
            for name in ("leakage", "fresh_units", "raw_integrity", "rule_null_calibration", "recompute"):
                if name in (audit["payload"].get("checks") or {}):
                    why = {"leakage": "needs the private family file and the memory sources of each episode",
                           "fresh_units": "needs the laboratory's ledger of used units",
                           "raw_integrity": "hashes the private raw log",
                           "rule_null_calibration": "a simulation whose specification is not in the package",
                           "recompute": "the laboratory's own recomputation from the raw log; this script's recomputation from per_unit.csv is the public counterpart"}[name]
                    rep.nv("cycle %s %s: %s.ok" % (cycle, audit["id"], name), why)
        for cal in self.k.kind("calibration"):
            rep.nv("%s (power, alpha, false close)" % cal["id"], "Monte Carlo calibration of the design before the run; its simulation specification is private (spec_sha256 only)")

    # ---------------------------------------------------------------- README
    def readme_checks(self, process: Dict[int, Dict[str, Any]], findings: Dict[str, Dict[str, Any]]) -> None:
        rep, t = self.rep, self.table
        head, sections = readme_sections(self.readme)
        program, report = self.program(), (self.k.one("report") or {}).get("payload", {})
        m = re.search(r"\*\*Question \(owner\):\*\* (.+)", head)
        rep.check("README: question = program goal", bool(m) and m.group(1).strip() == program.get("goal"), "")
        m = re.search(r"^Domain: `([^`]+)`", head, flags=re.MULTILINE)
        rep.check("README: domain = program domain %s" % program.get("domain"), bool(m) and m.group(1) == program.get("domain"))
        m = re.search(r"Cycles: (\d+); role calls: (\d+); units: (\d+)\.", head)
        if not m:
            rep.check("README: 'Cycles: ..; role calls: ..; units: ..' line", False, "not found")
        else:
            rep.check("README: cycles %s" % m.group(1), int(m.group(1)) == len(t.cycles()), "per_unit.csv cycles %s" % t.cycles())
            rep.check("README: units %s" % m.group(3), int(m.group(3)) == len(t.units()), "per_unit.csv has %d units" % len(t.units()))
            rep.check("README: role calls %s = report.role_calls" % m.group(2), int(m.group(2)) == report.get("role_calls"), "report %s" % report.get("role_calls"))
            rep.nv("README: role calls %s" % m.group(2), "the number of model calls is not in the published tables (only checked against report.role_calls)")
        handled = set()
        for title, body in sections.items():
            mres = re.match(r"Results \(cycle (\d+), n = (\d+) units, (\d+) arms\)", title)
            if mres:
                handled.add(title)
                self.readme_results(int(mres.group(1)), int(mres.group(2)), int(mres.group(3)), body)
            elif title.startswith("Findings"):
                handled.add(title)
                self.readme_findings(body, findings)
            elif title == "Caveats":
                handled.add(title)
                self.readme_caveats(body, process)
            elif title.startswith("Measurement checks"):
                handled.add(title)
                self.readme_measurement(body, process)
            elif title == "Decisions":
                handled.add(title)
                self.readme_decisions(body, process)
            elif title.startswith("Status of each direction"):
                handled.add(title)
                self.readme_status(body, process)
            elif title.startswith("Scope of the conclusions"):
                handled.add(title)
                self.readme_scope(body)
        for title in sections:
            if title not in handled:
                rep.nv("README section '%s'" % title, "a section this verifier does not know")

    def readme_results(self, cycle: int, n: int, n_arms: int, body: str) -> None:
        rep, t = self.rep, self.table
        tag = "README Results cycle %d" % cycle
        rec = self.recomputed.get(cycle)
        rep.check("%s: n = %d units" % (tag, n), n == len(t.units(cycle)), "per_unit.csv %d" % len(t.units(cycle)))
        rep.check("%s: %d arms" % (tag, n_arms), n_arms == len(t.arms()), "per_unit.csv %s" % t.arms())
        if rec is None:
            rep.check("%s: a result object for the cycle" % tag, False)
            return
        tables = md_tables(body)
        for table in tables:
            header = [h.lower() for h in table[0]]
            if header[:2] == ["arm", "solved"]:
                seen = set()
                for row in table[1:]:
                    arm = row[0]
                    seen.add(arm)
                    rate = rec["rates"].get(arm)
                    rep.check("%s: solved[%s] = %s" % (tag, arm, row[1]), rate is not None and agrees(rate, row[1]),
                              "recomputed %s" % ("%.4f" % rate if rate is not None else "no rows"))
                rep.check("%s: solved table lists every arm" % tag, seen == set(t.arms()), "table %s, per_unit.csv %s" % (sorted(seen), t.arms()))
            elif header[:1] == ["comparison"]:
                for row in table[1:]:
                    cells = dict(zip(header, row))
                    label = cells["comparison"]
                    mp = re.fullmatch(r"(\S+) \u2212 (\S+) \(primary\)", label)
                    key = ("primary", mp.group(1)) if mp else ("secondary", label)
                    c = rec["contrasts"].get(key)
                    if c is None:
                        rep.check("%s: comparison '%s' is a contrast of the result object" % (tag, label), False)
                        continue
                    field = "%s: %s" % (tag, label)
                    rep.check("%s difference %s" % (field, cells.get("difference")), agrees(c["diff"], cells.get("difference", "nan")), "recomputed %.4f" % c["diff"])
                    mi = INTERVAL.fullmatch(cells.get("95% interval", ""))
                    rep.check("%s interval %s" % (field, cells.get("95% interval")), bool(mi) and agrees(c["ci"][0], mi.group(1)) and agrees(c["ci"][1], mi.group(2)),
                              "recomputed [%.4f, %.4f]" % c["ci"])
                    mg = re.fullmatch(r"(\d+) / (\d+)", cells.get("gains / losses", ""))
                    rep.check("%s gains / losses %s" % (field, cells.get("gains / losses")), bool(mg) and (int(mg.group(1)), int(mg.group(2))) == (c["gains"], c["losses"]),
                              "recomputed %d / %d" % (c["gains"], c["losses"]))
                    self.check_state("%s state" % field, c["ci"], rec["sesoi"], cells.get("state"))
                    if key[0] == "primary":
                        rep.check("%s: primary contrast is against the placebo %s" % (field, self.placebo()), mp.group(2) == self.placebo())
                listed = {("primary", re.sub(r" \u2212 .*", "", r[0])) if "(primary)" in r[0] else ("secondary", r[0]) for r in table[1:]}
                rep.check("%s: comparison table lists every contrast of the result" % tag, listed == set(rec["contrasts"]),
                          "README %s, result %s" % (sorted(listed), sorted(rec["contrasts"])))
            else:
                rep.nv("%s: table with columns %s" % (tag, table[0]), "a table this verifier does not know")

    def readme_findings(self, body: str, findings: Dict[str, Dict[str, Any]]) -> None:
        rep = self.rep
        for table in md_tables(body):
            header = [h.lower() for h in table[0]]
            for row in table[1:]:
                cells = dict(zip(header, row))
                fid = cells.get("id", "").strip("`")
                f = findings.get(fid)
                tag = "README Findings %s" % fid
                if f is None:
                    rep.check("%s: is a finding object" % tag, False)
                    continue
                mh = re.fullmatch(r"(\S+) \(predicted (\S+)\)", cells.get("hypothesis", ""))
                rep.check("%s: hypothesis %s" % (tag, cells.get("hypothesis")), bool(mh) and (mh.group(1), mh.group(2)) == (f["label"], f["predicted"]),
                          "knowledge.jsonl: %s predicted %s" % (f["label"], f["predicted"]))
                rep.check("%s: arm %s, cycle %s" % (tag, cells.get("arm"), cells.get("cycle")), cells.get("arm") == f["arm"] and cells.get("cycle") == str(f["cycle"]))
                rep.check("%s: state %s, verdict %s" % (tag, cells.get("state"), cells.get("verdict")), (cells.get("state"), cells.get("verdict")) == (f["state"], f["verdict"]),
                          "finding: %s, %s" % (f["state"], f["verdict"]))
                rep.check("%s: difference %s" % (tag, cells.get("difference")), agrees(f["diff"], cells.get("difference", "nan")), "recomputed %.4f" % f["diff"])
                mi = INTERVAL.fullmatch(cells.get("interval", ""))
                rep.check("%s: interval %s" % (tag, cells.get("interval")), bool(mi) and agrees(f["ci"][0], mi.group(1)) and agrees(f["ci"][1], mi.group(2)),
                          "recomputed [%.4f, %.4f]" % f["ci"])
                level = LEVEL_NAMES.get(f["level"])
                if level is None:
                    rep.nv("%s: level %s" % (tag, cells.get("level")), "unknown level %r in knowledge.jsonl" % f["level"])
                else:
                    rep.check("%s: level %s" % (tag, cells.get("level")), cells.get("level") == level, "knowledge.jsonl %s" % f["level"])
            listed = {r[dict((h.lower(), i) for i, h in enumerate(table[0]))["id"]].strip("`") for r in table[1:]}
            rep.check("README Findings: every finding object is listed", listed == set(findings), "README %d, knowledge.jsonl %d" % (len(listed), len(findings)))

    def readme_caveats(self, body: str, process: Dict[int, Dict[str, Any]]) -> None:
        rep = self.rep
        for line in [ln[2:].strip() for ln in body.splitlines() if ln.startswith("- ")]:
            self.readme_sentence("README Caveats", line, process)

    def readme_sentence(self, where: str, line: str, process: Dict[int, Dict[str, Any]]) -> None:
        rep = self.rep
        cycle = self.table.cycles()[-1] if self.table.cycles() else None
        variants = list(self.protocol().get("treatments") or [])
        arm = variants[0] if len(variants) == 1 else None
        short = line[:70] + ("..." if len(line) > 70 else "")
        if re.search(r"first chunk|early check", line, flags=re.I):
            rep.nv("%s: '%s'" % (where, short), "a check on the first chunk of the run; per_unit.csv does not record which episodes made up that chunk")
            return
        checked = False
        mprefix = re.match(r"(?:Measurement problem: process|[^:]*): (\w+):", line)
        if mprefix and mprefix.group(1) in variants:
            arm = mprefix.group(1)
        if arm is not None and cycle is not None:
            criteria = process.get(cycle, {}).get("criteria") or {}
            checked = self.claim("%s: '%s'" % (where, short), line, cycle, arm, process, criteria)
            mrates = re.search(r"empty retries per step: placebo (" + NUMBER + r"), memory (" + NUMBER + r"), no memory (" + NUMBER + r")", line)
            if mrates:
                checked = True
                rates = process[cycle]["rates"]
                base = self.program().get("domain_params", {}).get("baseline", "none")
                for name, value, a in (("placebo", mrates.group(1), self.placebo()), ("memory", mrates.group(2), arm), ("no memory", mrates.group(3), base)):
                    rep.check("%s: empty retries per step, %s = %s" % (where, name, value), agrees(rates[a]["empty_retries"], value), "recomputed %.4f" % rates[a]["empty_retries"])
            mfail = re.search(r"untagged answers per step, memory \u2212 placebo \u2264 (" + NUMBER + r")[^)]*\) (FAILED|PASSED): (" + NUMBER + r") \[(" + NUMBER + r"), (" + NUMBER + r")\]", line)
            if mfail:
                checked = True
                text = "invalid_no_action_tag per step, arm \u2212 placebo %s [%s, %s] > %s" % (mfail.group(3), mfail.group(4), mfail.group(5), mfail.group(1))
                self.claim("%s: untagged-answer criterion" % where, text, cycle, arm, process, criteria)
                diff, ci = self.counter_result(cycle, arm, "invalid_no_action_tag", process)
                verdict = self.criterion(diff, ci, number(mfail.group(1)))
                if verdict is None:
                    rep.nv("%s: criterion %s" % (where, mfail.group(2)), "decision depends on the unpublished bootstrap")
                else:
                    rep.check("%s: criterion %s" % (where, mfail.group(2)), (mfail.group(2) == "FAILED") == verdict, "recomputed: %s" % ("fails" if verdict else "passes"))
        if not checked:
            numbers = re.findall(r"\d+\.\d+|\d+/\d+", line)
            if numbers:
                rep.nv("%s: '%s'" % (where, short), "numbers %s in a sentence no rule here recomputes" % numbers[:4])
            else:
                rep.nv("%s: '%s'" % (where, short), "a statement about the run's history, not a number in the tables")

    def readme_measurement(self, body: str, process: Dict[int, Dict[str, Any]]) -> None:
        rep = self.rep
        cycle = self.table.cycles()[-1]
        rates = process[cycle]["rates"]
        for table in md_tables(body):
            header = table[0]
            for row in table[1:]:
                arm = row[0]
                for col, value in zip(header[1:], row[1:]):
                    field = "README Measurement checks: %s per step [%s] = %s" % (col, arm, value)
                    if col not in STEP_COUNTERS or col not in self.table.columns:
                        rep.nv(field, "%s is not a column of per_unit.csv" % col)
                    elif arm not in rates:
                        rep.check(field, False, "no rows for arm %s" % arm)
                    else:
                        rep.check(field + " (step-weighted)", agrees(rates[arm][col], value), "recomputed %.4f" % rates[arm][col])
        m = re.search(r"Code audit verdict: \*\*(\w+)\*\* \(([^)]*)\)", self.readme)
        if m:
            audits = [a for a in self.k.kind("audit") if (a["payload"].get("by") or "") == "code"]
            rep.check("README: code audit verdict %s = audit object" % m.group(1), bool(audits) and audits[-1]["payload"].get("verdict") == m.group(1),
                      "audit %s" % (audits[-1]["payload"].get("verdict") if audits else None))
            rep.note("of the audit's parts (%s), completeness and the recomputation of the result are re-done above from per_unit.csv; "
                     "leakage and raw-data integrity need private files" % m.group(2))

    def readme_decisions(self, body: str, process: Dict[int, Dict[str, Any]]) -> None:
        rep = self.rep
        listed = []
        for line in body.splitlines():
            m = re.match(r"- `(decision:[0-9a-f]+)` \(cycle (\d+)\): (.*)", line)
            if not m:
                continue
            listed.append(m.group(1))
            d = self.k.by_id.get(m.group(1))
            rep.check("README Decisions: %s (cycle %s) is a decision object" % (m.group(1), m.group(2)), d is not None and d["kind"] == "decision" and str(d.get("cycle")) == m.group(2))
            if d is not None and " \u2014 " in m.group(3):
                self.readme_sentence("README Decisions %s" % m.group(1), m.group(3).split(" \u2014 ", 1)[1], process)
        decisions = [d["id"] for d in self.k.kind("decision")]
        rep.check("README Decisions: every decision object is listed", sorted(listed) == sorted(decisions), "README %d, knowledge.jsonl %d" % (len(listed), len(decisions)))
        rep.nv("README Decisions: labels", "the English labels of decision actions are written by the exporter; only ids and cycles are checked")

    def readme_status(self, body: str, process: Dict[int, Dict[str, Any]]) -> None:
        rep = self.rep
        for line in body.splitlines():
            m = re.match(r"- (\S+): (\S+)", line)
            if not m:
                continue
            arm, status = m.group(1), m.group(2)
            want = self.derived_status(arm, process)
            if want is None:
                rep.nv("README Status: %s = %s" % (arm, status), "no pre-registered format criterion fails, so the status follows decision rules "
                       "(replication on fresh units, a larger retry) that are not computable from the package")
            else:
                rep.check("README Status: %s = %s" % (arm, status), status == want, "a pre-registered format criterion fails -> %s" % want)

    def readme_scope(self, body: str) -> None:
        rep = self.rep
        scope = (self.k.one("report") or {}).get("payload", {}).get("scope") or {}
        m = re.search(r"task population `([^`]+)`, the arms (\[[^\]]*\]) against the placebo `([^`]+)`.*scale of (\d+) units in (\d+) run", body, flags=re.S)
        if not m:
            rep.nv("README Scope", "the sentence has an unknown form")
        else:
            runs = self.k.kind("run")
            rep.check("README Scope: population %s = run domain" % m.group(1), all(r["payload"].get("domain") == m.group(1) for r in runs) and scope.get("data") == m.group(1))
            rep.check("README Scope: arms %s = protocol treatments" % m.group(2), m.group(2) == str(list(self.protocol().get("treatments") or [])))
            rep.check("README Scope: placebo %s" % m.group(3), m.group(3) == self.placebo())
            rep.check("README Scope: %s units in %s run(s)" % (m.group(4), m.group(5)), (int(m.group(4)), int(m.group(5))) == (len(self.table.units()), len(runs)),
                      "per_unit.csv %d units, %d run object(s)" % (len(self.table.units()), len(runs)))
        mn = re.search(r"notes that did not change the protocol: (\d+)", self.readme)
        if mn:
            notes = (self.k.one("report") or {}).get("payload", {}).get("role_notes") or []
            rep.check("README: %s reviewer and auditor notes = report.role_notes" % mn.group(1), int(mn.group(1)) == len(notes), "report has %d" % len(notes))

    def run(self) -> None:
        print("-- package files, manifest and provenance")
        self.manifest_and_provenance()
        print("-- per_unit.csv against the run objects")
        self.structure()
        print("-- result objects (solved rates, contrasts, intervals, states)")
        self.results()
        print("-- process counters and the pre-registered format criterion")
        process = self.process()
        print("-- findings, audits and report")
        findings = self.findings(process)
        self.noise_check()
        self.report_object(process, findings)
        print("-- README")
        self.readme_checks(process, findings)


# --------------------------------------------------------------------------- entry point
def verify_package(package: Path) -> Report:
    rep = Report(package.name)
    print("== %s ==" % package.name)
    for name in REQUIRED_FILES:
        if not (package / name).is_file():
            raise InputError("%s has no %s" % (package.name, name))
    Verifier(package, rep).run()
    t = rep.passed + len(rep.failures)
    print("%s: %d passed, %d FAILED, %d not verifiable from the package, %d warning(s) out of %d checks" % (
        package.name, rep.passed, len(rep.failures), len(rep.unverifiable), len(rep.warnings), t))
    print("")
    return rep


def discover(repo: Path) -> List[Path]:
    return sorted(p for p in repo.glob(PACKAGE_GLOB) if p.is_dir())


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recompute, offline and from the package alone, the published numbers of autolab result packages "
                    "(per_unit.csv + README + knowledge.jsonl). Exit 0 = all verifiable checks pass, 1 = a number differs, "
                    "2 = usage error or a required file is missing or unreadable.")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]), help="repository root (default: the checkout this script is in)")
    parser.add_argument("--package", action="append", default=[], metavar="DIR",
                        help="check only this package folder (repeatable); default: every %s folder of the repository" % PACKAGE_GLOB)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    repo = Path(args.repo).resolve()
    packages = [Path(p).resolve() for p in args.package] if args.package else discover(repo)
    if not packages:
        print("no autolab package found under %s/%s" % (repo, PACKAGE_GLOB), file=sys.stderr)
        return 2
    reports = []
    try:
        for package in packages:
            if not package.is_dir():
                raise InputError("not a folder: %s" % package)
            reports.append(verify_package(package))
    except InputError as exc:
        print("input error: " + str(exc), file=sys.stderr)
        return 2
    except (KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
        print("input error: unexpected structure or content in a package file (%s: %s)" % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    failed = [r for r in reports if r.failures]
    for r in reports:
        if r.failures:
            print("MISMATCHES in %s:" % r.package)
            for field in r.failures:
                print("  - " + field)
    for r in reports:
        if r.warnings:
            print("WARNINGS in %s (statements of the package that disagree with each other):" % r.package)
            for field in r.warnings:
                print("  - " + field)
    if failed:
        print("%d of %d package(s) FAILED verification." % (len(failed), len(reports)))
        return 1
    print("all %d package(s) verified: every number recomputable from the package matches; %d field(s) not verifiable from the package (listed as N/V)." % (
        len(reports), sum(len(r.unverifiable) for r in reports)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
