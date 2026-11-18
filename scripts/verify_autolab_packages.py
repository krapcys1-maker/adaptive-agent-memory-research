#!/usr/bin/env python3
"""Recompute the published numbers of every autolab result package from the package alone, offline.

An autolab package (``data/lab/autolab-*``, written by the private laboratory through ``scripts/aamr_export.py``) holds
a README, ``knowledge.jsonl`` (the laboratory's objects: program, protocol, run, result, audits, findings, decisions,
report), ``PROVENANCE.json``, ``PUBLISHED_FILES.json`` and ``per_unit.csv`` (one row per task x arm x seed). This
script never sees the laboratory's database or the raw episode logs. From ``per_unit.csv`` it recomputes, with the
laboratory's own rules (cited below by the lab function that applies them):

* per-arm solved rates and every primary contrast (variant - placebo) and secondary contrast (arm - baseline): pairs,
  gains, losses, difference, discordance and the paired Wald interval (``rulecheck.paired_ci``: se = 1/n when the
  variance is 0); the lab analyses the first seed of the protocol only (``experiment.analyze``), and so does this script;
* the interval z: the fixed-sample normal quantile 1 - 0.025/k with k = max(family_size, number of treatments), or, when
  the result says ``z_sequential``, the pre-registered sequential threshold stated in the run or the protocol;
* the interval state in the lab's order (``Rule.label``: practical, positive, negative, equivalent, else inconclusive);
* the per-step process counters (``experiment.process_balance``): step-weighted rates per arm, the difference
  variant - placebo, its bootstrap interval, the state balanced / imbalanced / unresolved / not_computable and the
  pre-registered format criterion with the package's format rule; the bootstrap uses the LAB'S DEFAULT resampling
  parameters (seed 20261116, 2000 replicates), which the packages do not state;
* the measurement-sensitivity problems that follow from the table (placebo rate range, error excess, memory delivery,
  placebo block length, metric coverage, process problems) and their copies in findings and report;
* finding verdicts (``program._s_conclude``: invalid / supported / refuted / inconclusive / disputed), Brier scores,
  ``negative_result`` and the per-direction ``measurement_problem`` status;

and compares each with the number declared in ``knowledge.jsonl`` and the README, to the precision it is declared with
(rounding only). The README is accounted line by line: every line is either checked against the objects and the
recomputation, or listed as ``N/V``. It also checks the export manifest digests (required), ``PROVENANCE.json``
(required) and the provenance hashes of the objects.

Anything the package states that cannot be recomputed from the package is printed as ``N/V`` ("not verifiable from the
package") with the reason. The set of N/V fields of each package is pinned in
``scripts/verify_autolab_packages.baseline.json``: a field that becomes N/V and is not in the baseline FAILS, so lost
coverage is visible in CI (``--update-baseline`` rewrites the entries of the checked packages). ``WARN`` marks two
statements of the package that disagree with each other where the package does not say which one rules; it does not
change the exit status.

Properties: standard library only, no network, reads only files inside the package folders and the baseline, writes
nothing unless ``--update-baseline`` is given.

Exit status: 0 every verifiable check passed in every package; 1 at least one recomputed or declared number differs,
or the N/V set grew beyond the baseline (the per-field list is printed at the end); 2 usage error, or a package folder
lacks a required file or holds unreadable JSON.

Usage: python scripts/verify_autolab_packages.py [--repo PATH] [--package DIR ...] [--baseline FILE] [--update-baseline]
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
import traceback
from pathlib import Path
from statistics import NormalDist
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

PACKAGE_GLOB = "data/lab/autolab-*"
BASELINE_NAME = "verify_autolab_packages.baseline.json"
REQUIRED_FILES = ("README.md", "knowledge.jsonl", "per_unit.csv", "PUBLISHED_FILES.json", "PROVENANCE.json")
KEY_COLUMNS = ("cycle", "unit", "arm", "seed")
OUTCOME = "solved"
STEPS = "steps"
# columns the exporter derives itself (not lab metrics): they never enter the process balance
EXPORTER_COLUMNS = ("n_memory_sources", "error")

# ---- laboratory constants, copied from the lab code that applies them (aamr_coord/autolab/experiment.py, program.py,
# export.py, lab/rulecheck.py); none of them is stated in the packages, so every use is labelled "lab default"
LAB_BOOT_SEED = 20261116            # experiment.process_balance(seed=20261116)
LAB_BOOT_N = 2000                   # experiment.process_balance(n_boot=2000)
LAB_PROCESS_TOL = 0.03              # experiment.PROCESS_TOL
LAB_PROCESS_SKIP = {"steps", "max_steps", "max_tokens", "memory_tokens", "tokens", "seconds"}
FORMAT_MARKERS = ("empty", "no_action_tag", "untagged", "unparsed", "parse")
PLACEBO_RANGE = (0.10, 0.90)
ERROR_EXCESS_MAX = 0.05
PLACEBO_LENGTH_MIN_RATIO = 0.8
METRICS_COVERAGE_MIN = 0.95
SUPPORT = {"practical", "positive"}
CLOSE = {"equivalent", "negative"}
SUPPORT_UNDERMINING = ("b\u0142\u0119dy ramienia", "proces:", "kontrakt ramienia", "placebo niedopasowane", "przeciek niesprawdzalny")
LEVEL_EN = {"rozwojowy": "developmental", "zreplikowany": "replicated", "historyczny": "historical"}
ACTION_EN = {
    "stop_program": "program finished", "continue": "next cycle", "rules": "rules applied to the results",
    "halt": "halted", "run_despite_power_block": "measured despite a power-only objection",
    "resume_after_export_halt": "export retried", "requeue_after_deadline": "measurement resumed after the time limit",
    "resume_after_infrastructure_failure": "measurement resumed after an infrastructure failure",
    "requeue_after_task_failures": "measurement resumed after tasks without a result",
    "instrument_hold": "instrument objections recorded", "post_hoc_annotation": "annotation added after the result",
    "veto": "owner veto", "ideate": "new variants proposed", "no_rivals": "fewer than two rival hypotheses",
}
CAVEAT_EN = {
    "run_despite_power_block": "Measured although the reviewers' only remaining objection was statistical power "
                               "(risk of an inconclusive result).",
    "instrument_hold": "Measured despite objections from the instrument review; the instrument files are pinned to "
                       "the reviewed versions.",
    "measurement_hold": "Placebo success rate outside the range in which an effect can be detected; results carry a "
                        "measurement-problem flag.",
    "dispute_hold": "A second auditor dispute about this direction; the lab continued with replication instead of "
                    "waiting.",
    "director_stop_request": "The director role asked to stop; the code rules decided to continue.",
    "requeue_after_deadline": "The measurement hit the cycle time limit and was resumed from the saved records with a "
                              "longer limit.",
    "resume_after_export_halt": "The export was retried after an incomplete copy; no data were lost.",
    "resume_after_infrastructure_failure": "The measurement was interrupted by an infrastructure failure (a batch "
                                           "orphaned by a killed worker blocked the output file); the saved records "
                                           "were kept and only the missing tasks were run again.",
    "requeue_after_task_failures": "Some tasks returned no valid result (an infrastructure failure); the saved records "
                                   "were kept and only the missing tasks were run again.",
}
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
        if field not in self.unverifiable:
            self.unverifiable.append(field)

    def warn(self, field: str, why: str) -> None:
        print("WARN  " + field + "  | " + why)
        self.warnings.append(field)

    @staticmethod
    def note(text: str) -> None:
        print("NOTE  " + text)


def number(text: str) -> float:
    return float(text.replace(MINUS, "-").replace("+", ""))


def places(text: str) -> int:
    text = text.strip()
    return len(text.split(".", 1)[1]) if "." in text else 0


def agrees(recomputed: Optional[float], declared: Any, decimals: Optional[int] = None) -> bool:
    """True when ``recomputed`` rounds to ``declared``: a string keeps its own number of decimals, a JSON number is
    compared at ``decimals`` places (the precision the laboratory stores), an int without ``decimals`` must be equal."""
    if recomputed is None or isinstance(declared, bool) or declared is None:
        return recomputed is None and declared is None
    if isinstance(recomputed, float) and math.isnan(recomputed):
        return False
    if isinstance(declared, str):
        try:
            value, dp = number(declared), places(declared)
        except ValueError:
            return False
    elif isinstance(declared, int) and decimals is None:
        return recomputed == declared
    elif isinstance(declared, (int, float)):
        value, dp = float(declared), (6 if decimals is None else decimals)
    else:
        return False
    return abs(recomputed - value) <= 0.5 * 10 ** (-dp) + 1e-9


def r4(x: float) -> float:
    """The lab stores process rates at 4 places and formats the stored value."""
    return round(x, 4)


def r6(x: float) -> float:
    """The lab stores rates, differences and intervals at 6 places and formats the stored value."""
    return round(x, 6)


def show(ci: Optional[Sequence[float]]) -> str:
    return "n/a" if ci is None else "[%.4f, %.4f]" % (ci[0], ci[1])


def short(text: str, n: int = 60) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n] + "..."


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


def read_json(package: Path, name: str) -> Any:
    try:
        return json.loads(read_text(package, name))
    except ValueError as exc:
        raise InputError("%s/%s is not valid JSON: %s" % (package.name, name, exc))


def load_objects(package: Path) -> List[Dict[str, Any]]:
    objects = []
    for i, line in enumerate(read_text(package, "knowledge.jsonl").splitlines(), 1):
        if line.strip():
            try:
                obj = json.loads(line)
            except ValueError as exc:
                raise InputError("knowledge.jsonl line %d is not JSON: %s" % (i, exc))
            if not isinstance(obj, dict) or not all(k in obj for k in ("id", "kind", "payload", "parents")):
                raise InputError("knowledge.jsonl line %d is not a laboratory object (id, kind, payload, parents)" % i)
            objects.append(obj)
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

    def parent(self, obj: Dict[str, Any], kind: str, where: Optional[Callable[[Dict[str, Any]], bool]] = None) -> Optional[Dict[str, Any]]:
        for pid in obj.get("parents", []):
            o = self.by_id.get(pid)
            if o is not None and o["kind"] == kind and (where is None or where(o)):
                return o
        return None


def parse_cell(cell: str) -> Any:
    cell = cell.strip()
    if cell == "":
        return None
    if re.fullmatch(r"-?\d+", cell):
        return int(cell)
    try:
        return float(cell)
    except ValueError:
        return cell


class Table:
    """per_unit.csv keyed by (cycle, unit, arm, seed). Only the key columns and ``solved`` must be integers; any other
    cell may be an integer, a float or empty (the exporter writes floats as floats and a missing metric as an empty
    cell). A column the verifier computes from is checked for numeric values where it is used."""

    def __init__(self, text: str, rep: Report) -> None:
        reader = csv.DictReader(io.StringIO(text))
        self.columns = list(reader.fieldnames or [])
        missing = [c for c in KEY_COLUMNS + (OUTCOME,) if c not in self.columns]
        if missing:
            raise InputError("per_unit.csv lacks the column(s) %s" % ", ".join(missing))
        self.rows: Dict[Tuple[int, str, str, int], Dict[str, Any]] = {}
        self.n_rows = 0
        bad: List[str] = []
        duplicates: List[str] = []
        for line, raw in enumerate(reader, 2):
            self.n_rows += 1
            values = {c: parse_cell(raw.get(c) or "") for c in self.columns if c not in ("unit", "arm")}
            for c in ("cycle", "seed"):
                if not isinstance(values[c], int):
                    bad.append("line %d %s=%r" % (line, c, raw.get(c)))
                    values[c] = -1
            if values[OUTCOME] not in (0, 1):
                bad.append("line %d solved=%r" % (line, raw.get(OUTCOME)))
                values[OUTCOME] = 0
            if not raw.get("unit") or not raw.get("arm"):
                bad.append("line %d has an empty unit or arm" % line)
            key = (values["cycle"], raw.get("unit") or "", raw.get("arm") or "", values["seed"])
            if key in self.rows:
                duplicates.append("line %d repeats cycle %s / %s / %s / seed %s" % ((line,) + key))
                continue
            self.rows[key] = values
        rep.check("per_unit.csv: cycle and seed are integers, solved is 0 or 1, unit and arm are named", not bad,
                  "; ".join(bad[:5]) + (" ..." if len(bad) > 5 else ""))
        rep.check("per_unit.csv: one row per (cycle, unit, arm, seed)", not duplicates,
                  "; ".join(duplicates[:5]) + (" ..." if len(duplicates) > 5 else "") if duplicates else "%d rows" % self.n_rows)

    def cycles(self) -> List[int]:
        return sorted({k[0] for k in self.rows})

    def units(self, cycle: Optional[int] = None, seed: Optional[int] = None) -> List[str]:
        return sorted({k[1] for k in self.rows if (cycle is None or k[0] == cycle) and (seed is None or k[3] == seed)})

    def arms(self, cycle: Optional[int] = None) -> List[str]:
        return sorted({k[2] for k in self.rows if cycle is None or k[0] == cycle})

    def seeds(self, cycle: Optional[int] = None) -> List[int]:
        return sorted({k[3] for k in self.rows if cycle is None or k[0] == cycle})

    def arm_rows(self, cycle: int, arm: str, seed: int) -> Dict[str, Dict[str, Any]]:
        return {k[1]: v for k, v in self.rows.items() if k[0] == cycle and k[2] == arm and k[3] == seed}

    def is_number(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)


# --------------------------------------------------------------------------- statistics (the lab's rules)
def family(protocol: Dict[str, Any]) -> int:
    """experiment.family: max(family_size, number of treatments, 1)."""
    return max(int(protocol.get("family_size") or 0), len(protocol.get("treatments") or []), 1)


def family_z(k: int) -> float:
    return NormalDist().inv_cdf(1 - 0.05 / (2 * max(k, 1)))


def paired_ci(gains: int, losses: int, n: int, z: float) -> Tuple[float, float]:
    """rulecheck.paired_ci (deff 1): Wald for paired proportions; se = 1/n when the variance is 0."""
    d = (gains - losses) / n
    var = max(((gains + losses) / n - d * d) / n, 0.0)
    se = math.sqrt(var) if var > 0 else 1.0 / n
    return d - z * se, d + z * se


def interval_state(lo: float, hi: float, sesoi: float) -> str:
    """rulecheck.Rule.label, kind ci_states, in the lab's order."""
    if lo >= sesoi:
        return "practical"
    if lo > 0:
        return "positive"
    if hi < 0:
        return "negative"
    if lo > -sesoi and hi < sesoi:
        return "equivalent"
    return "inconclusive"


def lab_verdict(predicted: Optional[str], state: str, audit_valid: bool, disputed: bool) -> Optional[str]:
    """program._s_conclude."""
    if not audit_valid:
        return "invalid"
    if state in SUPPORT:
        verdict = "supported" if predicted == "positive" else "refuted"
    elif state in CLOSE:
        verdict = "refuted" if predicted == "positive" else "supported"
    else:
        verdict = "inconclusive"
    return "disputed" if disputed else verdict


# --------------------------------------------------------------------------- README helpers
def split_sections(lines: List[str]) -> Tuple[Tuple[int, int], Dict[str, Tuple[int, int, int]]]:
    """(head range, {title: (heading line, body start, body end)})."""
    heads = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    sections = {}
    for j, i in enumerate(heads):
        end = heads[j + 1] if j + 1 < len(heads) else len(lines)
        sections[lines[i][3:].strip()] = (i, i + 1, end)
    return (0, heads[0] if heads else len(lines)), sections


def md_tables(lines: List[str], start: int, end: int) -> List[List[Tuple[int, List[str]]]]:
    """Tables in lines[start:end], each a list of (line index, cells); separator rows are included as cells too."""
    tables: List[List[Tuple[int, List[str]]]] = []
    current: List[Tuple[int, List[str]]] = []
    for i in range(start, end):
        line = lines[i]
        if line.strip().startswith("|"):
            current.append((i, [c.strip() for c in line.strip().strip("|").split("|")]))
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def is_separator(cells: List[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


INTERVAL = re.compile(r"\[(" + NUMBER + r")[,;] (" + NUMBER + r")\]")
PROCESS_EN = re.compile(r"process: (\S+) per step, arm \u2212 placebo (" + NUMBER + r") \[(" + NUMBER + r"), (" + NUMBER + r")\]")
PROCESS_PL = re.compile(r"proces: (\S+)(?: na krok wariant \u2212 placebo)? (" + NUMBER + r") \[(" + NUMBER + r"); (" + NUMBER + r")\]")


def problem_en(x: str) -> str:
    """export._problem_en for the process problems (the English README wording of a Polish problem text)."""
    pre = r"( \(kryterium ustalone przed pomiarem\))?"
    num = r"([+-]?[\d.]+)"
    m = re.fullmatch(r"proces: (\S+) na krok wariant \u2212 placebo " + num + r" \[" + num + "; " + num + r"\] > " + num + pre +
                     r" \u2014 tre\u015b\u0107 i format/proces nie s\u0105 rozdzielone", x)
    if m:
        return ("process: %s per step, arm \u2212 placebo %s [%s, %s] > %s%s \u2014 content and format/process effects are not separated"
                % (m[1], m[2], m[3], m[4], m[5], " (pre-registered criterion)" if m[6] else ""))
    m = re.fullmatch(r"proces: (\S+) na krok wariant \u2212 placebo " + num + r" \[" + num + "; " + num + r"\] nierozstrzygni\u0119ty \u2014 przedzia\u0142 "
                     r"nie mie\u015bci si\u0119 w \u00b1" + num + pre + r"; neutralno\u015b\u0107 placebo niewykazana", x)
    if m:
        return ("process: %s per step, arm \u2212 placebo %s [%s, %s] unresolved \u2014 the interval is not within \u00b1%s%s; placebo "
                "neutrality not shown" % (m[1], m[2], m[3], m[4], m[5], " (pre-registered criterion)" if m[6] else ""))
    m = re.fullmatch(r"proces: kryterium (\S+)" + pre + r" niepoliczalne \u2014 licznik nieobecny w rekordach polecenia; neutralno\u015b\u0107 "
                     r"placebo niesprawdzona", x)
    if m:
        return ("process: criterion %s%s cannot be computed \u2014 the counter is absent from the command's records; placebo "
                "neutrality not checked" % (m[1], " (pre-registered criterion)" if m[2] else ""))
    return x


def problem_kind(text: str) -> Optional[Tuple[str, str]]:
    """A measurement-sensitivity problem text -> (kind, detail); None = a problem this script cannot recompute."""
    if text.startswith("proces: metryki tylko w"):
        return ("coverage", "")
    if text.startswith("proces: kryteria "):
        return ("criteria_not_computed", "")
    m = re.match(r"proces: kryterium (\S+)", text) or re.match(r"proces: (\S+)", text)
    if m:
        return ("process", m.group(1))
    if text.startswith("skuteczno\u015b\u0107 placebo"):
        return ("placebo_range", "")
    if text.startswith("b\u0142\u0119dy ramienia"):
        return ("errors", "")
    if text.startswith("rami\u0119 nie dosta\u0142o pami\u0119ci"):
        return ("no_memory", "")
    if text.startswith("placebo niedopasowane"):
        return ("placebo_length", "")
    return None


# --------------------------------------------------------------------------- verification of one package
class Verifier:
    def __init__(self, package: Path, rep: Report) -> None:
        self.package = package
        self.rep = rep
        self.k = Knowledge(load_objects(package))
        self.readme_lines = read_text(package, "README.md").splitlines()
        self.used: Set[int] = set()
        self.table = Table(read_text(package, "per_unit.csv"), rep)
        self.cycles: Dict[Any, Dict[str, Any]] = {}       # cycle -> recomputed result
        self.process: Dict[str, Dict[str, Any]] = {}      # audit id -> recomputed process balance + problems
        self.findings: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------- the program's settings
    def program(self) -> Dict[str, Any]:
        prog = self.k.one("program")
        return prog["payload"] if prog else {}

    def domain_params(self) -> Dict[str, Any]:
        return self.program().get("domain_params") or {}

    def placebo(self) -> str:
        return self.domain_params().get("placebo") or "placebo"

    def baseline(self) -> str:
        return self.domain_params().get("baseline") or "none"

    def protocol_of(self, run: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        proto = self.k.parent(run, "protocol") if run else None
        proto = proto or self.k.one("protocol")
        return proto["payload"] if proto else {}

    def run_of(self, obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        run = self.k.parent(obj, "run")
        if run is None:
            res = self.k.parent(obj, "result")
            run = self.k.parent(res, "run") if res else None
        return run

    # ---------------------------------------------------------------- package integrity
    def integrity(self) -> None:
        rep, pkg = self.rep, self.package
        manifest = read_json(pkg, "PUBLISHED_FILES.json")
        prog = self.program()
        rep.check("PUBLISHED_FILES.json: task = 'autolab %s'" % prog.get("id"), manifest.get("task") == "autolab %s" % prog.get("id"),
                  "manifest says %r" % manifest.get("task"))
        listed = set()
        for entry in manifest.get("published", []):
            name = entry.get("path")
            listed.add(name)
            if not name or not (pkg / name).is_file():
                rep.check("PUBLISHED_FILES.json: %s exists" % name, False, "listed in the manifest but missing")
                continue
            data = read_bytes(pkg, name)
            digest = hashlib.sha256(data).hexdigest()
            rep.check("PUBLISHED_FILES.json: sha256 and size of %s" % name,
                      digest == entry.get("sha256") and len(data) == entry.get("bytes"),
                      "file %s / %d bytes, manifest %s / %s bytes" % (digest[:12], len(data), str(entry.get("sha256"))[:12], entry.get("bytes")))
        for name in sorted(p.name for p in pkg.iterdir() if p.is_file()):
            if name not in listed and name != "PUBLISHED_FILES.json":
                rep.nv("PUBLISHED_FILES.json: %s" % name, "the file is in the package folder but not in its export manifest, so its bytes "
                       "are not pinned by the export; its numbers are still recomputed")
        if manifest.get("private"):
            rep.nv("PUBLISHED_FILES.json: private area (%d item(s))" % len(manifest["private"]), "the withheld files are private by design")
        bad = []
        seen: Set[str] = set()
        for o in self.k.objects:
            body = {"kind": o["kind"], "program": o.get("program"), "payload": o["payload"], "parents": sorted(set(o["parents"]))}
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
            rep.nv("knowledge.jsonl: original hashes of the redacted objects", "machine-local paths were replaced in %d object(s); only the "
                   "redacted copy's hash can be recomputed, the id is the hash of the private original" % redacted)
        prov = read_json(pkg, "PROVENANCE.json")
        digest = hashlib.sha256(read_bytes(pkg, "knowledge.jsonl")).hexdigest()
        rep.check("PROVENANCE.json: knowledge_sha256", prov.get("knowledge_sha256") == digest, "knowledge.jsonl %s" % digest[:12])
        rep.check("PROVENANCE.json: objects = %s" % prov.get("objects"), prov.get("objects") == len(self.k.objects), "knowledge.jsonl has %d" % len(self.k.objects))
        for key in ("program", "goal", "domain"):
            want = prog.get("id") if key == "program" else prog.get(key)
            rep.check("PROVENANCE.json: %s = program %s" % (key, key), prov.get(key) == want, "PROVENANCE %r" % short(str(prov.get(key))))
        rep.check("PROVENANCE.json: integrity_problems is empty", prov.get("integrity_problems") == [],
                  "declared %r" % (prov.get("integrity_problems"),))
        runs = {r["id"]: r["payload"] for r in self.k.kind("run")}
        listed_runs = []
        for raw in prov.get("raw", []):
            listed_runs.append(raw.get("run"))
            run = runs.get(raw.get("run"), {})
            rep.check("PROVENANCE.json: raw of %s = run object (records %s, sha256)" % (raw.get("run"), raw.get("records")),
                      raw.get("records") == run.get("records") and raw.get("raw_sha256") == run.get("raw_sha256"),
                      "run object: %s records, raw %s" % (run.get("records"), str(run.get("raw_sha256"))[:12]))
        rep.check("PROVENANCE.json: every run object has a raw entry", sorted(listed_runs) == sorted(runs), "PROVENANCE %s, runs %s" % (listed_runs, sorted(runs)))
        rep.nv("PROVENANCE.json: raw_sha256 and location of each run", "the raw episode logs are private")
        rep.nv("PROVENANCE.json: generated_by, exported_at, note", "export metadata, not a result")

    # ---------------------------------------------------------------- per_unit.csv against the run objects
    def structure(self) -> None:
        rep, t = self.rep, self.table
        cycles_seen = set()
        for run in self.k.kind("run"):
            cycle = run.get("cycle")
            cycles_seen.add(cycle)
            p = run["payload"]
            proto = self.protocol_of(run)
            seeds = list(p.get("seeds") or proto.get("seeds") or [])
            arms = list(p.get("arms") or proto.get("arms") or [])
            tag = "cycle %s %s" % (cycle, run["id"])
            rep.check("%s: arms = protocol arms %s" % (tag, proto.get("arms")), arms == list(proto.get("arms") or []), "run %s" % arms)
            rep.check("%s: seeds = protocol seeds %s" % (tag, proto.get("seeds")), seeds == list(proto.get("seeds") or []), "run %s" % seeds)
            rep.check("%s: per_unit.csv arms = run arms" % tag, t.arms(cycle) == sorted(arms), "table %s" % t.arms(cycle))
            rep.check("%s: per_unit.csv seeds = run seeds" % tag, t.seeds(cycle) == sorted(seeds), "table %s" % t.seeds(cycle))
            if len(seeds) > 1:
                rep.nv("%s: rows of seeds %s" % (tag, seeds[1:]), "the lab analyses only the first seed of the protocol (%s; "
                       "experiment.analyze); the other seeds enter no published number" % seeds[0])
            units = list(p.get("units") or [])
            have = t.units(cycle)
            missing, extra = sorted(set(units) - set(have)), sorted(set(have) - set(units))
            early = bool(p.get("sequential"))
            rep.check("%s: every unit of the run has rows" % tag, not missing, "missing %s" % missing[:3] if missing else "%d units" % len(units))
            if extra and early:
                rep.nv("%s: %d unit(s) outside the run's units" % (tag, len(extra)), "the run stopped early at a sequential look; the lab "
                       "analysed only the run's units")
            else:
                rep.check("%s: no rows outside the run's units" % tag, not extra, "not in the run: %s" % extra[:3] if extra else "")
            grid_missing = ["%s/%s/seed %d" % (u, a, s) for u in units for a in arms for s in seeds if (cycle, u, a, s) not in t.rows]
            rep.check("%s: complete unit x arm x seed grid (completeness)" % tag, not grid_missing,
                      "missing %d row(s): %s" % (len(grid_missing), "; ".join(grid_missing[:3])) if grid_missing else
                      "%d units x %d arms x %d seed(s)" % (len(units), len(arms), len(seeds)))
            rows = sum(1 for k in t.rows if k[0] == cycle and k[1] in set(units))
            lines = t.n_rows if len(self.k.kind("run")) == 1 else rows
            rep.check("%s: rows = run.records %s" % (tag, p.get("records")), rows == p.get("records") and lines == p.get("records"),
                      "%d distinct rows, %d lines" % (rows, lines))
            errors = sum(1 for k, v in t.rows.items() if k[0] == cycle and v.get("error"))
            measured = (p.get("measurement") or {}).get("errors_counted_as_unsolved")
            if measured is None:
                rep.nv("%s: errors counted as unsolved" % tag, "the run object does not state it")
            else:
                rep.check("%s: rows with error = run.measurement.errors_counted_as_unsolved %s" % (tag, measured), errors == measured, "table %d" % errors)
            rep.nv("%s: units_sha256, raw_sha256, runner pins, lab_code" % tag, "they hash or name private files and code")
        for cycle in t.cycles():
            if cycle not in cycles_seen:
                rep.check("per_unit.csv: cycle %s has a run object" % cycle, False)
        for col in t.columns:
            if col in KEY_COLUMNS + (OUTCOME,) or col in EXPORTER_COLUMNS:
                continue
            values = [v.get(col) for v in t.rows.values()]
            kinds = sorted({type(x).__name__ for x in values})
            if any(isinstance(x, str) for x in values):
                rep.nv("per_unit.csv column %s" % col, "it holds text values; no rule here computes from it")
            elif col in (STEPS, "memory_tokens") or self.is_process_column(col):
                continue              # used by the process balance and sensitivity checks below
            else:
                rep.nv("per_unit.csv column %s" % col, "no published number is computed from it by a lab rule this script mirrors (values: %s)"
                       % "/".join(k.replace("NoneType", "empty") for k in kinds))
        rep.nv("per_unit.csv column n_memory_sources", "the number of memory items per episode; no published number is computed from it")

    def is_process_column(self, col: str) -> bool:
        """A lab metric that enters the process balance: an integer value in some row, not a size or a time
        (experiment.process_balance keys), or any pre-registered criterion counter."""
        if col in KEY_COLUMNS + (OUTCOME,) or col in EXPORTER_COLUMNS or col in LAB_PROCESS_SKIP or col.startswith("max_"):
            return col in self.all_criteria()
        return any(isinstance(v.get(col), int) for v in self.table.rows.values()) or col in self.all_criteria()

    def all_criteria(self) -> Dict[str, Any]:
        crit = dict(self.domain_params().get("format_criteria") or {})
        for a in self.k.kind("audit"):
            pb = (((a["payload"].get("checks") or {}).get("measurement_sensitivity") or {}).get("process_balance") or {})
            crit.update(pb.get("criteria") or {})
        return crit

    # ---------------------------------------------------------------- result objects
    def results(self) -> None:
        rep, t = self.rep, self.table
        placebo, baseline = self.placebo(), self.baseline()
        for res in self.k.kind("result"):
            p = res["payload"]
            run = self.k.parent(res, "run")
            proto = self.protocol_of(run)
            cycle = res.get("cycle")
            tag = "cycle %s %s" % (cycle, res["id"])
            if run is None:
                rep.check("%s: has a run parent" % tag, False)
                continue
            units = list(run["payload"].get("units") or [])
            seed0 = (proto.get("seeds") or [0])[0]
            arms = list(proto.get("arms") or [])
            treatments = list(proto.get("treatments") or [])
            sesoi = float(proto.get("sesoi", self.program().get("sesoi")))
            if proto.get("sesoi") != self.program().get("sesoi"):
                rep.nv("%s: SESOI protocol %s, program %s" % (tag, proto.get("sesoi"), self.program().get("sesoi")),
                       "the protocol's value is used, as the lab does")
            k = family(proto)
            rep.check("%s: family_size = %s (max(family_size, treatments))" % (tag, p.get("family_size")), p.get("family_size") == k, "recomputed %d" % k)
            rep.check("%s: seed = %s (first protocol seed)" % (tag, p.get("seed")), p.get("seed") == seed0, "protocol seeds %s" % proto.get("seeds"))
            rep.check("%s: n_units = %s" % (tag, p.get("n_units")), p.get("n_units") == len(units), "run has %d units" % len(units))
            z = self.result_z(tag, p, run, proto, k)
            rec: Dict[str, Any] = {"z": z, "rates": {}, "contrasts": {}, "k": k, "sesoi": sesoi, "seed": seed0, "units": units,
                                   "result": res, "treatments": treatments}
            declared_rates = p.get("success_rate") or {}
            rep.check("%s: success_rate lists the protocol arms %s" % (tag, arms), sorted(declared_rates) == sorted(arms), "declared %s" % sorted(declared_rates))
            for arm in arms:
                rows = t.arm_rows(cycle, arm, seed0)
                solved = sum(rows[u][OUTCOME] for u in units if u in rows)
                rate = solved / len(units) if units else float("nan")
                rec["rates"][arm] = rate
                rep.check("%s: success_rate[%s] = %s" % (tag, arm, declared_rates.get(arm)), agrees(rate, declared_rates.get(arm), 6),
                          "recomputed %d solved / %d = %.6f" % (solved, len(units), rate))
            want_primary = {a: (a, placebo) for a in treatments}
            want_secondary = {"%s-%s" % (a, baseline): (a, baseline) for a in treatments + [placebo]}
            for group, want, body in (("primary", want_primary, p.get("primary") or {}), ("secondary", want_secondary, p.get("secondary") or {})):
                rep.check("%s: %s contrasts = %s" % (tag, group, sorted(want)), sorted(body) == sorted(want), "declared %s" % sorted(body))
                for name, (a, b) in want.items():
                    c = self.contrast(cycle, units, seed0, a, b, z)
                    rec["contrasts"][(group, name)] = c
                    if name in body:
                        self.check_contrast("%s: %s.%s (%s - %s)" % (tag, group, name, a, b), c, body[name], sesoi)
            estimand = "wariant \u2212 %s (efekt tre\u015bci)" % placebo
            rep.check("%s: estimand" % tag, p.get("estimand") == estimand, "declared %r" % p.get("estimand"))
            rep.check("%s: raw_sha256 = run raw_sha256" % tag, p.get("raw_sha256") == run["payload"].get("raw_sha256"))
            for key in sorted(set(p) - {"z", "z_sequential", "n_units", "family_size", "success_rate", "primary", "secondary", "estimand", "raw_sha256", "seed"}):
                rep.nv("%s: %s" % (tag, key), "a field no lab rule mirrored here computes")
            self.cycles[cycle] = rec

    def result_z(self, tag: str, p: Dict[str, Any], run: Dict[str, Any], proto: Dict[str, Any], k: int) -> float:
        rep = self.rep
        seq_proto = (proto.get("sequential") or {}).get("z") or []
        if p.get("z_sequential"):
            seq_run = (run["payload"].get("sequential") or {}).get("z")
            want = seq_run if seq_run is not None else (seq_proto[-1] if seq_proto else None)
            if want is None:
                rep.nv("%s: z = %s (sequential)" % (tag, p.get("z")), "the result says z_sequential but neither the run nor the protocol "
                       "states the sequential thresholds; the declared z is used for the intervals")
                return float(p.get("z"))
            rep.check("%s: z = %s (sequential threshold %s)" % (tag, p.get("z"), "of the run's look" if seq_run is not None else "of the final analysis"),
                      agrees(float(want), p.get("z"), 6), "pre-registered %s" % want)
            rep.check("%s: the sequential threshold is one of the protocol's %s" % (tag, seq_proto), any(abs(float(want) - float(x)) < 1e-9 for x in seq_proto))
            rep.nv("%s: the sequential thresholds themselves" % tag, "O'Brien-Fleming thresholds from a lab simulation (experiment.sequential_z); "
                   "taken as pre-registered in the protocol")
            return float(want)
        if seq_proto:
            rep.check("%s: a sequential protocol gives a sequential z" % tag, False, "the protocol has sequential looks but the result has no z_sequential")
        z = family_z(k)
        rep.check("%s: z = %s (normal quantile 1 - 0.025/k, k = %d)" % (tag, p.get("z"), k), agrees(z, p.get("z"), 6), "recomputed %.6f" % z)
        return z

    def contrast(self, cycle: Any, units: List[str], seed: int, a: str, b: str, z: float) -> Dict[str, Any]:
        ra, rb = self.table.arm_rows(cycle, a, seed), self.table.arm_rows(cycle, b, seed)
        keys = [u for u in units if u in ra and u in rb]
        n = len(keys)
        gains = sum(1 for u in keys if ra[u][OUTCOME] == 1 and rb[u][OUTCOME] == 0)
        losses = sum(1 for u in keys if ra[u][OUTCOME] == 0 and rb[u][OUTCOME] == 1)
        if n == 0:
            return {"n": 0, "gains": 0, "losses": 0, "diff": float("nan"), "discordance": float("nan"), "ci": (float("nan"),) * 2}
        return {"n": n, "gains": gains, "losses": losses, "diff": (gains - losses) / n, "discordance": (gains + losses) / n,
                "ci": paired_ci(gains, losses, n, z)}

    def check_contrast(self, where: str, c: Dict[str, Any], body: Dict[str, Any], sesoi: float) -> None:
        rep = self.rep
        for key in ("n", "gains", "losses"):
            rep.check("%s %s = %s" % (where, key, body.get(key)), c[key] == body.get(key), "recomputed %d" % c[key])
        for key in ("diff", "discordance"):
            rep.check("%s %s = %s" % (where, key, body.get(key)), agrees(c[key], body.get(key), 6), "recomputed %.6f" % c[key])
        ci = body.get("ci") or [None, None]
        rep.check("%s ci = %s (paired Wald)" % (where, ci), agrees(c["ci"][0], ci[0], 6) and agrees(c["ci"][1], ci[1], 6),
                  "recomputed [%.6f, %.6f]" % c["ci"])
        self.check_state("%s state" % where, c["ci"], sesoi, body.get("state"))
        for key in sorted(set(body) - {"n", "gains", "losses", "diff", "discordance", "ci", "state"}):
            rep.nv("%s %s" % (where, key), "a field no lab rule mirrored here computes")

    def check_state(self, field: str, ci: Sequence[float], sesoi: float, declared: Any) -> None:
        near = [b for b in (sesoi, -sesoi, 0.0) for x in ci if abs(x - b) < 1e-6]
        if near:
            self.rep.nv(field, "an interval end lies within rounding of a state boundary (%s), so the state depends on digits the "
                        "package does not publish" % near)
            return
        want = interval_state(ci[0], ci[1], sesoi)
        self.rep.check("%s = %s" % (field, declared), declared == want, "lab rule (practical, positive, negative, equivalent, else "
                       "inconclusive) gives %s at SESOI %s for [%.6f, %.6f]" % (want, sesoi, ci[0], ci[1]))

    # ---------------------------------------------------------------- process balance and sensitivity (lab rules)
    def criteria_for(self, pb: Dict[str, Any], tag: str) -> Tuple[Dict[str, Any], set, str]:
        dp = self.domain_params()
        if "format_criteria" in dp:
            crit = dict(dp.get("format_criteria") or {})
            self.rep.check("%s: process_balance.criteria = program format_criteria" % tag, (pb.get("criteria") or {}) == crit,
                           "audit %s, program %s" % (pb.get("criteria"), crit))
        else:
            crit = dict(pb.get("criteria") or {})
            if crit:
                self.rep.nv("%s: format criteria %s fixed before the run" % (tag, sorted(crit)), "the program in the package states no "
                            "format_criteria; the criteria are taken from the audit object")
        behaviour = set(dp.get("behaviour_counters") or pb.get("behaviour_counters") or []) - set(crit)
        rule = dp.get("format_rule") or pb.get("format_rule") or "equivalence"
        if behaviour or "behaviour_counters" in pb:
            self.rep.check("%s: process_balance.behaviour_counters = %s" % (tag, sorted(behaviour)), sorted(pb.get("behaviour_counters") or []) == sorted(behaviour))
        if rule != "equivalence" or "format_rule" in pb:
            self.rep.check("%s: process_balance.format_rule = %s" % (tag, rule), pb.get("format_rule", "equivalence") == rule)
        return crit, behaviour, rule

    def balance(self, cycle: Any, seed0: int, treatments: List[str], crit: Dict[str, Any], behaviour: set, rule: str,
                keys: List[str]) -> Dict[str, Any]:
        """experiment.process_balance over per_unit.csv (records of the first seed with numeric steps)."""
        t = self.table
        rows_seed0 = {k: v for k, v in t.rows.items() if k[0] == cycle and k[3] == seed0}
        by: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for (cyc, unit, arm, seed), v in rows_seed0.items():
            if t.is_number(v.get(STEPS)):
                by.setdefault(arm, {})[unit] = v
        present = {c for c in t.columns if any(v.get(c) is not None for k, v in t.rows.items() if k[0] == cycle)}
        missing = sorted(k for k in crit if k not in present)
        pl = by.get(self.placebo()) or {}

        def rate(ms: Dict[str, Dict[str, Any]], units: Sequence[str], k: str) -> float:
            st = sum(float(ms[u].get(STEPS) or 0) for u in units)
            return sum(float(ms[u].get(k) or 0) for u in units) / st if st else 0.0

        rates = {a: {k: rate(ms, list(ms), k) for k in keys} for a, ms in by.items()}
        rng = random.Random(LAB_BOOT_SEED)
        per_arm: Dict[str, Dict[str, Any]] = {}
        for a in treatments:
            ms = by.get(a) or {}
            units = sorted(set(ms) & set(pl))
            if not units or not pl:
                continue
            samples = [[rng.choice(units) for _ in units] for _ in range(LAB_BOOT_N)]
            out = {}
            for k in keys:
                tol = crit.get(k, LAB_PROCESS_TOL)
                fmt = k in crit or (k not in behaviour and any(x in k.lower() for x in FORMAT_MARKERS))
                if k in missing:
                    out[k] = {"diff": None, "ci": None, "tolerance": tol, "preregistered": True, "format_counter": True,
                              "imbalanced": False, "state": "not_computable"}
                    continue
                d = rate(ms, units, k) - rate(pl, units, k)
                bs = sorted(rate(ms, s, k) - rate(pl, s, k) for s in samples)
                lo, hi = bs[int(0.025 * LAB_BOOT_N)], bs[int(0.975 * LAB_BOOT_N) - 1]
                imb = abs(d) > tol and not lo <= 0 <= hi
                state = "imbalanced" if imb else "balanced" if (-tol <= lo and hi <= tol) else "unresolved"
                out[k] = {"diff": d, "ci": (lo, hi), "tolerance": tol, "preregistered": k in crit, "format_counter": fmt,
                          "imbalanced": imb, "state": state, "rule": rule if k in crit and rule != "equivalence" else None}
            per_arm[a] = out
        n_seed0 = len(rows_seed0)
        covered = sum(len(ms) for ms in by.values())
        return {"rates": rates, "per_arm": per_arm, "missing": missing, "coverage": covered / n_seed0 if n_seed0 else None,
                "has_placebo": bool(pl), "by": by}

    @staticmethod
    def process_problem(v: Dict[str, Any]) -> bool:
        """experiment.process_problems: does this counter raise a measurement problem."""
        st = v.get("state") or ("imbalanced" if v.get("imbalanced") else "balanced")
        if st == "imbalanced" and v.get("format_counter"):
            return True
        if st == "unresolved" and v.get("preregistered") and v.get("rule") != "imbalance_only":
            return True
        return st == "not_computable" and bool(v.get("preregistered"))

    def sensitivity(self) -> None:
        rep, t = self.rep, self.table
        for audit in self.k.kind("audit"):
            ms = (audit["payload"].get("checks") or {}).get("measurement_sensitivity")
            if not ms:
                continue
            run = self.run_of(audit)
            cycle = audit.get("cycle")
            proto = self.protocol_of(run)
            seed0 = (proto.get("seeds") or [0])[0]
            treatments = list(proto.get("treatments") or [])
            placebo = self.placebo()
            tag = "cycle %s %s (%s)" % (cycle, audit["id"], audit["payload"].get("by"))
            recs = {k: v for k, v in t.rows.items() if k[0] == cycle and k[3] == seed0}
            by_arm: Dict[str, List[Dict[str, Any]]] = {}
            for k, v in recs.items():
                by_arm.setdefault(k[2], []).append(v)
            pl = by_arm.get(placebo) or []
            pl_rate = sum(r[OUTCOME] for r in pl) / len(pl) if pl else None
            pl_err = sum(1 for r in pl if r.get("error")) / len(pl) if pl else 0.0
            has_tokens = "memory_tokens" in t.columns and any(t.is_number(r.get("memory_tokens")) for r in recs.values())
            expected: Dict[str, List[Tuple[str, str]]] = {a: [] for a in treatments}
            if "placebo_rate" in ms:
                rep.check("%s: placebo_rate = %s" % (tag, ms["placebo_rate"]), agrees(pl_rate, ms["placebo_rate"], 4),
                          "recomputed %s" % (None if pl_rate is None else "%.4f" % pl_rate))
            if "placebo_problem" in ms:
                want = pl_rate is not None and not PLACEBO_RANGE[0] <= pl_rate <= PLACEBO_RANGE[1]
                rep.check("%s: placebo_problem = %s" % (tag, ms["placebo_problem"]), ms["placebo_problem"] == want, "placebo rate outside %s: %s" % (PLACEBO_RANGE, want))
            if "tokens_reported" in ms:
                rep.check("%s: tokens_reported = %s" % (tag, ms["tokens_reported"]), ms["tokens_reported"] == has_tokens, "memory_tokens cells: %s" % has_tokens)
            if "memory_delivery_checked" in ms:
                rep.check("%s: memory_delivery_checked = %s" % (tag, ms["memory_delivery_checked"]), ms["memory_delivery_checked"] == has_tokens)
            tokens = {a: [float(r["memory_tokens"]) for r in rs if t.is_number(r.get("memory_tokens"))] for a, rs in by_arm.items()}
            pl_vals = tokens.get(placebo) or []
            length_checked = bool(pl_vals) and has_tokens
            if "placebo_length_checked" in ms:
                rep.check("%s: placebo_length_checked = %s" % (tag, ms["placebo_length_checked"]), ms["placebo_length_checked"] == length_checked)
            means = {a: (sum(v) / len(v) if v else None) for a, v in tokens.items()}
            rep.note("%s: mean memory tokens per arm (episodes that report them): %s" % (tag, ", ".join(
                "%s %s" % (a, "-" if m is None else "%.1f" % m) for a, m in sorted(means.items()))))
            for a in treatments:
                rs = by_arm.get(a) or []
                if pl_rate is not None and not PLACEBO_RANGE[0] <= pl_rate <= PLACEBO_RANGE[1]:
                    expected[a].append(("placebo_range", ""))
                err = sum(1 for r in rs if r.get("error")) / len(rs) if rs else 0.0
                n_a, n_p = max(len(rs), 1), max(len(pl), 1)
                pool = (err * n_a + pl_err * n_p) / (n_a + n_p)
                se = (max(pool * (1 - pool), 1e-9) * (1 / n_a + 1 / n_p)) ** 0.5
                if abs(err - pl_err) > ERROR_EXCESS_MAX and abs(err - pl_err) / se > 2.576:
                    expected[a].append(("errors", ""))
                body = (ms.get("per_arm") or {}).get(a) or {}
                if "error_rate" in body:
                    rep.check("%s: per_arm[%s].error_rate = %s" % (tag, a, body["error_rate"]), agrees(err, body["error_rate"], 4), "recomputed %.4f" % err)
                if has_tokens and rs:
                    tok = [float(r.get("memory_tokens") or 0) for r in rs]
                    if sum(tok) / len(tok) == 0:
                        expected[a].append(("no_memory", ""))
                if length_checked:
                    vals = tokens.get(a) or []
                    mean = sum(vals) / len(vals) if vals else 0.0
                    if mean > 0 and sum(pl_vals) / len(pl_vals) < PLACEBO_LENGTH_MIN_RATIO * mean:
                        expected[a].append(("placebo_length", ""))
            pb = ms.get("process_balance")
            if pb:
                self.process_balance_checks(tag, audit, pb, cycle, seed0, treatments, expected)
            self.process[audit["id"]] = {"expected": expected, "ms": ms, "has_pb": bool(pb), "has_length": "placebo_length_checked" in ms,
                                         "has_memory": bool(ms.get("memory_delivery_checked")), "cycle": cycle, "tag": tag}
            for a in treatments:
                declared = list(((ms.get("per_arm") or {}).get(a) or {}).get("problems") or [])
                self.compare_problems("%s: per_arm[%s].problems" % (tag, a), declared, expected[a], self.process[audit["id"]], a, cycle)

    def process_balance_checks(self, tag: str, audit: Dict[str, Any], pb: Dict[str, Any], cycle: Any, seed0: int,
                               treatments: List[str], expected: Dict[str, List[Tuple[str, str]]]) -> None:
        rep, t = self.rep, self.table
        crit, behaviour, rule = self.criteria_for(pb, tag)
        declared_keys = sorted({k for v in (pb.get("rates") or {}).values() for k in v} | {k for v in (pb.get("per_arm") or {}).values() for k in v} | set(crit))
        keys = [k for k in declared_keys if k in t.columns]
        for k in declared_keys:
            if k not in t.columns:
                rep.nv("%s: process counter %s" % (tag, k), "%s is not a column of per_unit.csv (the exporter does not publish it); its rates, "
                       "difference, interval and state are the lab's" % k)
        for col in t.columns:
            if self.is_process_column(col) and col not in declared_keys and col not in (STEPS,):
                rep.check("%s: process_balance covers the integer counter %s" % (tag, col), False,
                          "per_unit.csv has integer values in %s, which the lab's process balance would include" % col)
        bal = self.balance(cycle, seed0, treatments, crit, behaviour, rule, keys)
        for arm, values in (pb.get("rates") or {}).items():
            for k, declared in values.items():
                if k not in keys:
                    continue
                got = bal["rates"].get(arm, {}).get(k)
                rep.check("%s: process_balance.rates[%s][%s] = %s (step-weighted)" % (tag, arm, k, declared), agrees(got, declared, 4),
                          "recomputed %s" % (None if got is None else "%.4f" % got))
        rep.check("%s: process_balance.rates lists the arms with steps" % tag, sorted(pb.get("rates") or {}) == sorted(bal["rates"]),
                  "declared %s, recomputed %s" % (sorted(pb.get("rates") or {}), sorted(bal["rates"])))
        if "not_computable" in pb:
            rep.check("%s: process_balance.not_computable = %s" % (tag, pb["not_computable"]), sorted(pb["not_computable"]) == bal["missing"],
                      "criteria with no value in per_unit.csv: %s" % bal["missing"])
        if "metrics_coverage" in pb:
            rep.check("%s: process_balance.metrics_coverage = %s" % (tag, pb["metrics_coverage"]), agrees(bal["coverage"], pb["metrics_coverage"], 4),
                      "rows with steps / rows of the first seed: %s" % bal["coverage"])
            if crit and bal["coverage"] is not None and bal["coverage"] < METRICS_COVERAGE_MIN:
                for a in expected:
                    expected[a].append(("coverage", ""))
        if crit:
            for a in expected:
                if a not in bal["per_arm"]:
                    expected[a].append(("criteria_not_computed", ""))
        rep.check("%s: process_balance.per_arm lists %s" % (tag, sorted(bal["per_arm"])), sorted(pb.get("per_arm") or {}) == sorted(bal["per_arm"]),
                  "declared %s" % sorted(pb.get("per_arm") or {}))
        for arm, per in (pb.get("per_arm") or {}).items():
            for k, body in per.items():
                field = "%s: process_balance.per_arm[%s][%s]" % (tag, arm, k)
                v = bal["per_arm"].get(arm, {}).get(k)
                if v is None:
                    continue
                self.check_counter(field, body, v)
                if self.process_problem(v):
                    expected.setdefault(arm, []).append(("process", k))
        self.process.setdefault("_balance", {})[audit["id"]] = bal

    def check_counter(self, field: str, body: Dict[str, Any], v: Dict[str, Any]) -> None:
        rep = self.rep
        boot = "lab default bootstrap: seed %d, %d replicates, units resampled with replacement; the package does not state them" % (LAB_BOOT_SEED, LAB_BOOT_N)
        if v["state"] == "not_computable":
            rep.check("%s.diff = %s (not computable)" % (field, body.get("diff")), body.get("diff") is None and body.get("ci") is None,
                      "the counter has no value in per_unit.csv")
        else:
            rep.check("%s.diff = %s (variant - placebo, step-weighted)" % (field, body.get("diff")), agrees(v["diff"], body.get("diff"), 4), "recomputed %.4f" % v["diff"])
            dci = body.get("ci") or [None, None]
            exact = agrees(v["ci"][0], dci[0], 4) and agrees(v["ci"][1], dci[1], 4)
            if exact:
                rep.check("%s.ci = %s" % (field, dci), True, "recomputed %s (%s)" % (show(v["ci"]), boot))
            else:
                margin = 0.25 * (v["ci"][1] - v["ci"][0]) / 2 + 0.5e-4
                near = all(isinstance(x, (int, float)) for x in dci) and abs(v["ci"][0] - dci[0]) <= margin and abs(v["ci"][1] - dci[1]) <= margin
                if near:
                    rep.nv("%s.ci (exact digits)" % field, "does not reproduce exactly with the %s; it agrees within Monte Carlo error "
                           "(recomputed %s)" % (boot, show(v["ci"])))
                else:
                    rep.check("%s.ci = %s" % (field, dci), False, "recomputed %s with the %s" % (show(v["ci"]), boot))
        for key in ("tolerance", "preregistered", "format_counter", "imbalanced", "state"):
            if key in body:
                ok = agrees(float(v[key]), body[key], 4) if key == "tolerance" and isinstance(body[key], (int, float)) else body[key] == v[key]
                why = {"tolerance": "the criterion's tolerance, else the lab default %s" % LAB_PROCESS_TOL,
                       "preregistered": "the counter is a format criterion of the program",
                       "format_counter": "criterion, or a name with a format marker %s and not a behaviour counter" % (FORMAT_MARKERS,),
                       "imbalanced": "|diff| > tolerance and the interval excludes 0",
                       "state": "balanced: interval within +-tolerance; imbalanced: as above; else unresolved"}[key]
                rep.check("%s.%s = %s" % (field, key, body[key]), ok, "recomputed %s (%s)" % (v[key], why))
        if "rule" in body or v.get("rule"):
            rep.check("%s.rule = %s" % (field, body.get("rule")), body.get("rule") == v.get("rule"), "recomputed %s" % v.get("rule"))
        for key in sorted(set(body) - {"diff", "ci", "tolerance", "preregistered", "format_counter", "imbalanced", "state", "rule"}):
            rep.nv("%s.%s" % (field, key), "a field no lab rule mirrored here computes")

    def compare_problems(self, field: str, declared: List[str], expected: List[Tuple[str, str]], info: Dict[str, Any], arm: str,
                         cycle: Any, support_filter: bool = False) -> None:
        """Declared measurement problems against the ones recomputed from the table, for the checks the audit ran."""
        rep = self.rep
        gate = {"process": info["has_pb"], "coverage": info["has_pb"], "criteria_not_computed": info["has_pb"],
                "placebo_length": info["has_length"], "no_memory": info["has_memory"], "placebo_range": True, "errors": True}
        want = [x for x in expected if gate[x[0]]]
        got: List[Tuple[str, str]] = []
        for text in declared:
            kind = problem_kind(text)
            if kind is None:
                rep.nv("%s: %r" % (field, short(text)), "an arm-contract or leakage problem; it needs the raw records or the private family file")
                continue
            if kind[0] == "process":
                self.claim("%s: %r" % (field, short(text, 40)), text, cycle, arm)
            got.append(kind)
        if support_filter:
            want = [x for x in want if x[0] in ("process", "coverage", "criteria_not_computed", "errors", "placebo_length")]
        rep.check("%s: recomputable problems %s" % (field, sorted("%s %s" % x for x in want) or "none"), sorted(got) == sorted(want),
                  "declared %s" % (sorted("%s %s" % x for x in got) or "none"))
        if not info["has_pb"]:
            rep.nv("%s: process problems" % field, "this audit predates the lab's process-balance check, so it makes no statement about them")

    def claim(self, field: str, text: str, cycle: Any, arm: str) -> bool:
        """Check the '<counter> +d [lo, hi]' figures of a process sentence (Polish or English) against the recomputation."""
        m = PROCESS_PL.search(text) or PROCESS_EN.search(text)
        if not m:
            return False
        counter, d, lo, hi = m.groups()
        bal = self.balance_for(cycle)
        v = (bal or {}).get("per_arm", {}).get(arm, {}).get(counter) if bal else None
        if v is None or v["state"] == "not_computable":
            self.rep.nv("%s: %s %s [%s, %s]" % (field, counter, d, lo, hi), "%s is not a column of per_unit.csv, or not computable" % counter)
            return True
        # the lab formats the stored 4-place values (experiment.process_problems), so round to 4 places first
        self.rep.check("%s: %s %s [%s, %s]" % (field, counter, d, lo, hi), agrees(r4(v["diff"]), d) and agrees(r4(v["ci"][0]), lo) and agrees(r4(v["ci"][1]), hi),
                       "recomputed %.4f %s (lab default bootstrap)" % (v["diff"], show(v["ci"])))
        return True

    def balance_for(self, cycle: Any) -> Optional[Dict[str, Any]]:
        bals = self.process.get("_balance", {})
        audits = [a for a in self.k.kind("audit") if a["id"] in bals and a.get("cycle") == cycle]
        return bals[audits[-1]["id"]] if audits else None

    # ---------------------------------------------------------------- findings and report
    def findings_checks(self) -> None:
        rep = self.rep
        for i, f in enumerate(self.k.kind("finding"), 1):
            p, cycle = f["payload"], f.get("cycle")
            tag = "cycle %s %s" % (cycle, f["id"])
            res = self.k.parent(f, "result")
            rec = self.cycles.get(cycle)
            hyp = self.k.parent(f, "hypothesis")
            hp = hyp["payload"] if hyp else {}
            label = hp.get("id", "?")
            c = rec["contrasts"].get(("primary", p.get("arm"))) if rec else None
            if c is None or res is None:
                rep.check("%s: has a result parent with a primary contrast for %s" % (tag, p.get("arm")), False)
                continue
            for key in ("n",):
                rep.check("%s (%s): %s = %s" % (tag, label, key, p.get(key)), c[key] == p.get(key), "recomputed %d" % c[key])
            for key in ("diff", "discordance"):
                rep.check("%s (%s): %s = %s" % (tag, label, key, p.get(key)), agrees(c[key], p.get(key), 6), "recomputed %.6f" % c[key])
            ci = p.get("ci") or [None, None]
            rep.check("%s (%s): ci = %s" % (tag, label, ci), agrees(c["ci"][0], ci[0], 6) and agrees(c["ci"][1], ci[1], 6), "recomputed [%.6f, %.6f]" % c["ci"])
            rep.check("%s (%s): k = %s" % (tag, label, p.get("k")), p.get("k") == rec["k"], "family %d" % rec["k"])
            state = p.get("state")
            self.check_state("%s (%s): state" % (tag, label), c["ci"], rec["sesoi"], state)
            if hyp is None:
                rep.nv("%s: verdict, predicted, brier" % tag, "the finding has no hypothesis parent")
                self.findings.append({"obj": f, "index": i, "label": label, "c": c})
                continue
            rep.check("%s (%s): predicted = hypothesis.predicted %s" % (tag, label, hp.get("predicted")), p.get("predicted") == hp.get("predicted"))
            rep.check("%s (%s): hypothesis = hypothesis.statement" % (tag, label), p.get("hypothesis") == hp.get("statement"))
            code = self.k.parent(f, "audit", lambda o: str(o["payload"].get("by", "")).startswith("code"))
            role = self.k.parent(f, "audit", lambda o: not str(o["payload"].get("by", "")).startswith("code"))
            audit_valid = bool(code) and code["payload"].get("verdict") == "valid"
            rp = role["payload"] if role else {}
            disputed_arms = {cl.get("arm") for cl in rp.get("claims") or [] if isinstance(cl, dict) and cl.get("arm")}
            disputed = bool(rp.get("verdict") == "dispute" and rp.get("claims")) and audit_valid and (not disputed_arms or p.get("arm") in disputed_arms)
            want = lab_verdict(hp.get("predicted"), state, audit_valid, disputed)
            rep.check("%s (%s): verdict = %s" % (tag, label, p.get("verdict")), p.get("verdict") == want,
                      "lab rule (program._s_conclude: code audit %s, role audit %s, predicted %s, state %s; the predicted direction only, "
                      "not expected_state or the falsification text) -> %s" % (code["payload"].get("verdict") if code else None,
                                                                                 rp.get("verdict"), hp.get("predicted"), state, want))
            expected_state = hp.get("expected_state")
            if expected_state and state != expected_state and p.get("verdict") == "supported":
                text = str(hp.get("falsification") or "")
                mention = (" Its falsification text names '%s' among the refuting states: %r." % (state, short(text, 150))) if state in text else ""
                rep.warn("%s (%s): verdict supported with state %s, hypothesis expected_state %s" % (tag, label, state, expected_state),
                         "the lab's verdict rule reads only the predicted direction (%s); the hypothesis pre-registered a narrower expected "
                         "state.%s The package does not say which of the two decides." % (hp.get("predicted"), mention))
            if "negative_result" in p:
                neg = p.get("verdict") == "refuted" or state in CLOSE
                rep.check("%s (%s): negative_result = %s" % (tag, label, p["negative_result"]), p["negative_result"] == neg, "refuted or a closing state: %s" % neg)
            if "p_positive" in hp and "brier" in p:
                brier = (float(hp["p_positive"]) - (1.0 if state in SUPPORT else 0.0)) ** 2
                rep.check("%s (%s): brier = %s ((p_positive %s - [state in practical/positive])^2)" % (tag, label, p["brier"], hp["p_positive"]),
                          agrees(brier, p["brier"], 6), "recomputed %.6f" % brier)
            if p.get("level") not in LEVEL_EN:
                rep.nv("%s (%s): level = %s" % (tag, label, p.get("level")), "an evidence level the lab's exporter does not name")
            else:
                rep.nv("%s (%s): level" % (tag, label), "developmental / replicated depends on earlier findings of the program and sealed "
                       "confirmations, a rule over the program history")
            problems = list(p.get("measurement_problem") or [])
            if code is not None:
                ms = (code["payload"].get("checks") or {}).get("measurement_sensitivity") or {}
                source = list(((ms.get("per_arm") or {}).get(p.get("arm")) or {}).get("problems") or [])
                if state in SUPPORT:
                    source = [x for x in source if x.startswith(SUPPORT_UNDERMINING)]
                rep.check("%s (%s): measurement_problem = the code audit's problems%s" % (tag, label, " that undermine support" if state in SUPPORT else ""),
                          problems == source, "audit %d, finding %d" % (len(source), len(problems)))
            self.findings.append({"obj": f, "index": i, "label": label, "c": c, "verdict_ok": p.get("verdict") == want})

    def report_checks(self) -> None:
        rep = self.rep
        obj = self.k.one("report")
        if obj is None:
            rep.nv("report", "the package has no report object")
            return
        p = obj["payload"]
        units = sum(len(r["units"]) for r in self.cycles.values())
        rep.check("report: units_used = %s" % p.get("units_used"), p.get("units_used") == units, "units of the analysed runs: %d" % units)
        rep.check("report: cycles = %s" % p.get("cycles"), p.get("cycles") == max([c for c in self.cycles if isinstance(c, int)] or [0]),
                  "result cycles %s" % sorted(self.cycles))
        rep.check("report: program and goal", p.get("program") == self.program().get("id") and p.get("goal") == self.program().get("goal"))
        briers = [f["obj"]["payload"].get("brier") for f in self.findings if f["obj"]["payload"].get("brier") is not None]
        if briers and "brier_mean" in p:
            mean = sum(briers) / len(briers)
            rep.check("report: brier_mean = %s" % p["brier_mean"], agrees(mean, p["brier_mean"], 4), "mean of %d finding Brier scores %.4f" % (len(briers), mean))
        fobj = {f["obj"]["id"]: f["obj"]["payload"] for f in self.findings}
        for item in p.get("findings") or []:
            f = fobj.get(item.get("id"))
            ok = f is not None and all(item.get(k) == f.get(k) for k in ("arm", "state", "verdict", "level", "diff", "ci"))
            rep.check("report.findings %s = the finding object" % item.get("id"), ok)
        rep.check("report.findings lists every finding", sorted(x.get("id") for x in p.get("findings") or []) == sorted(fobj))
        order = [o["id"] for o in self.k.objects]
        later = [d["id"] for d in self.k.kind("decision") if order.index(d["id"]) > order.index(obj["id"])]
        rep.check("report.decisions = every decision made before the report", sorted(p.get("decisions") or []) ==
                  sorted(d["id"] for d in self.k.kind("decision") if d["id"] not in later), "decisions after the report: %s" % later)
        for arm, body in (p.get("arms") or {}).items():
            fs = [f["obj"] for f in self.findings if f["obj"]["payload"].get("arm") == arm]
            last = fs[-1]["payload"] if fs else {}
            mp = bool(last.get("measurement_problem")) and last.get("verdict") != "invalid"
            rep.check("report.arms[%s].findings are findings of the arm" % arm, set(body.get("findings") or []) <= {f["id"] for f in fs})
            if mp or body.get("status") == "measurement_problem":
                rep.check("report.arms[%s].status = %s" % (arm, body.get("status")), (body.get("status") == "measurement_problem") == mp,
                          "lab rule: measurement_problem iff the arm's last finding has measurement problems and is not invalid (%s)" % mp)
            else:
                rep.nv("report.arms[%s].status = %s" % (arm, body.get("status")), "without a measurement problem the status follows decision rules "
                       "over the program history (replication, retries, disputes, vetoes)")
        mps = {a: v for a, v in (p.get("measurement_problems") or {}).items()}
        want = {a: (fs[-1]["payload"].get("measurement_problem")) for a in (p.get("arms") or {})
                for fs in [[f["obj"] for f in self.findings if f["obj"]["payload"].get("arm") == a]] if fs
                and (p.get("arms") or {})[a].get("status") == "measurement_problem"}
        if "measurement_problems" in p:
            rep.check("report.measurement_problems = the problems of the arms with that status", mps == want, "declared %d arm(s), expected %d" % (len(mps), len(want)))
        for key in ("role_calls", "model_calls", "provenance", "role_notes", "role_blocks", "ideation", "new_variants"):
            if key in p:
                rep.nv("report: %s" % key, "model-role activity and lab code provenance are not part of the published tables")

    def noise_checks(self) -> None:
        rep = self.rep
        for audit in self.k.kind("audit"):
            checks = audit["payload"].get("checks") or {}
            cycle = audit.get("cycle")
            rec = self.cycles.get(cycle)
            if rec is None:
                continue
            tag = "cycle %s %s" % (cycle, audit["id"])
            nv = checks.get("noise_vs_calibration")
            proto = self.protocol_of(self.run_of(audit))
            if nv:
                # experiment.audit: per primary arm, the Wald lower bound of its stored (6-place) discordance at z = 1 - 0.025/k
                # with k = number of primary arms and n = protocol n_units; the largest bound is published
                prim = {name: c for (g, name), c in rec["contrasts"].items() if g == "primary"}
                k_arms = max(len(prim), 1)
                z_noise = NormalDist().inv_cdf(1 - 0.025 / k_arms)
                n_obs = max(int(proto.get("n_units") or len(rec["units"])), 1)
                bounds = {}
                for name, c in prim.items():
                    o = round(c["discordance"], 6)
                    bounds[name] = o - z_noise * (max(o * (1 - o), 0.0) / n_obs) ** 0.5
                worst = max(c["discordance"] for c in prim.values())
                lower = max(bounds.values())
                rep.check("%s: noise_vs_calibration.observed_max = %s" % (tag, nv.get("observed_max")), agrees(worst, nv.get("observed_max"), 6),
                          "largest primary discordance %.6f" % worst)
                rep.check("%s: noise_vs_calibration.observed_lower_bound = %s" % (tag, nv.get("observed_lower_bound")), agrees(lower, nv.get("observed_lower_bound"), 6),
                          "largest Wald lower bound of the stored discordances at z %.4f (k = %d), n %d: %.7f" % (z_noise, k_arms, n_obs, lower))
                rep.check("%s: noise_vs_calibration.assumed = %s (protocol discordance_assumed)" % (tag, nv.get("assumed")), nv.get("assumed") == proto.get("discordance_assumed"))
                above = sorted(a for a, b in bounds.items() if b > float(proto.get("discordance_assumed") or 0))
                rep.check("%s: noise_vs_calibration.significant_arms = %s" % (tag, sorted(nv.get("significant_arms") or {})),
                          sorted(nv.get("significant_arms") or {}) == above, "arms whose lower bound exceeds the assumed noise: %s" % above)
                if not above:
                    rep.check("%s: noise_vs_calibration.ok = %s" % (tag, nv.get("ok")), nv.get("ok") is True, "no lower bound above the assumed noise, so the rule cannot fire")
                else:
                    rep.nv("%s: noise_vs_calibration.ok" % tag, "the rule also needs the power at the observed noise, a simulation not in the package")
            comp = checks.get("completeness")
            if comp:
                run = self.run_of(audit)
                want = len(rec["units"]) * len((run or {}).get("payload", {}).get("arms") or []) * len((run or {}).get("payload", {}).get("seeds") or [])
                rows = sum(1 for k in self.table.rows if k[0] == cycle and k[1] in set(rec["units"]))
                rep.check("%s: completeness records %s of expected %s" % (tag, comp.get("records"), comp.get("expected")),
                          comp.get("records") == rows and comp.get("expected") == want, "per_unit.csv: %d rows, grid %d" % (rows, want))
            why = {"leakage": "needs the private family file and the memory sources of each episode",
                   "fresh_units": "needs the laboratory's ledger of used units", "raw_integrity": "hashes the private raw log",
                   "rule_null_calibration": "a simulation whose specification is not in the package",
                   "recompute": "the lab's own recomputation from the raw log; this script's recomputation from per_unit.csv is the public counterpart"}
            for name in sorted(set(checks) - {"noise_vs_calibration", "completeness", "measurement_sensitivity"}):
                rep.nv("%s: checks.%s" % (tag, name), why.get(name, "a check this script does not mirror"))
        for cal in self.k.kind("calibration"):
            rep.nv("%s (power, alpha, false close)" % cal["id"], "Monte Carlo calibration of the design before the run; its simulation specification is private")
        for d in self.k.kind("decision"):
            if d["payload"].get("action") == "interim_look":
                rep.nv("%s: interim look (n %s, z %s, states)" % (d["id"], d["payload"].get("n"), d["payload"].get("z")),
                       "the look used the first n complete units in the order of the lab's unit list, which the package does not publish")

    # ---------------------------------------------------------------- README, line by line
    def use(self, i: int) -> None:
        self.used.add(i)

    def find_line(self, text: str, start: int = 0, end: Optional[int] = None) -> Optional[int]:
        lines = self.readme_lines
        for i in range(start, len(lines) if end is None else end):
            if lines[i] == text:
                return i
        return None

    def expect_line(self, field: str, text: str, start: int = 0, end: Optional[int] = None) -> Optional[int]:
        i = self.find_line(text, start, end)
        self.rep.check(field, i is not None, "expected line %r" % short(text, 100) if i is None else "")
        if i is not None:
            self.use(i)
        return i

    def readme(self) -> None:
        rep, lines = self.rep, self.readme_lines
        (h0, h1), sections = split_sections(lines)
        prog = self.program()
        report = (self.k.one("report") or {}).get("payload") or {}
        # head
        m = re.match(r"\*\*Status:\*\* (\S+)( \u2014 .*)?$", lines[0]) if lines else None
        if not m:
            rep.check("README: first line '**Status:** ...'", False, "found %r" % (lines[0] if lines else ""))
        else:
            self.use(0)
            finished = any(d["payload"].get("action") == "stop_program" for d in self.k.kind("decision"))
            if finished:
                rep.check("README: status %s (the program has a stop_program decision)" % m.group(1), m.group(1) == "completed")
            else:
                rep.nv("README: status %s" % m.group(1), "without a stop_program decision the export status is the lab's choice")
            if m.group(2):
                rep.nv("README: status note %r" % short(m.group(2)), "free text of the envelope")
        self.expect_line("README: title '# Lab program %s'" % prog.get("id"), "# Lab program %s" % prog.get("id"), h0, h1)
        for i in range(h0, h1):
            if lines[i].startswith("> "):
                self.use(i)
                rep.nv("README: note %r" % short(lines[i][2:]), "a note of the envelope, free text")
        self.expect_line("README: question = program goal", "**Question (owner):** %s" % prog.get("goal"), h0, h1)
        dom = "Domain: `%s`" % prog.get("domain") + (" \u2014 synthetic world with a known truth (a lab test, not a scientific result)"
                                                     if str(prog.get("domain", "")).startswith("synthetic") else "")
        self.expect_line("README: domain line", dom, h0, h1)
        self.expect_line("README: cycles, role calls, units = report %s / %s / %s" % (report.get("cycles"), report.get("role_calls"), report.get("units_used")),
                         "Cycles: %s; role calls: %s; units: %s." % (report.get("cycles"), report.get("role_calls"), report.get("units_used")), h0, h1)
        prior = report.get("prior_analyses_of_dataset") or []
        if prior:
            self.expect_line("README: earlier analyses = %d" % len(prior), "Earlier analyses of this data set in the lab: %d \u2014 multiplicity at the "
                             "data-set level." % len(prior), h0, h1)
        handled: Set[str] = set()
        for res in self.k.kind("result"):
            if not res["payload"].get("success_rate"):
                continue
            title = next((s for s in sections if s.startswith("Results (cycle %s," % res.get("cycle"))), None)
            if not rep.check("README: section 'Results (cycle %s, ...)' present" % res.get("cycle"), title is not None):
                continue
            handled.add(title)
            self.readme_results(res, title, sections[title])
        title = next((s for s in sections if s == "Findings (negative ones included)"), None)
        if rep.check("README: section 'Findings (negative ones included)' present", title is not None):
            handled.add(title)
            self.readme_findings(sections[title])
        audits = [a for a in self.k.kind("audit") if (a["payload"].get("checks") or {}).get("measurement_sensitivity")]
        pbal = ((audits[-1]["payload"]["checks"]["measurement_sensitivity"].get("process_balance") or {}) if audits else {})
        probs = sorted({x for f in self.k.kind("finding") for x in (f["payload"].get("measurement_problem") or [])})
        caveats = list(report.get("caveats") or [])
        rule_notes = self.rule_notes(pbal)
        if "Caveats" in sections:
            handled.add("Caveats")
            self.readme_caveats(sections["Caveats"], caveats, probs, rule_notes)
        else:
            rep.check("README: section 'Caveats' present when there are caveats, measurement problems or rule notes",
                      not (caveats or probs or rule_notes), "%d caveat(s), %d problem(s), %d rule note(s)" % (len(caveats), len(probs), len(rule_notes)))
        if audits:
            title = "Measurement checks (per step, by arm)"
            rates = pbal.get("rates") or {}
            if rates or title in sections:
                if rep.check("README: section '%s' present" % title, title in sections):
                    handled.add(title)
                    self.readme_measurement(sections[title], audits[-1], pbal)
            else:
                self.expect_line("README: code audit verdict line", "Code audit verdict: **%s** (completeness, recomputation, leakage, raw-data integrity)."
                                 % audits[-1]["payload"].get("verdict"))
        vetoed = list(report.get("vetoed_decisions") or [])
        if vetoed:
            self.expect_line("README: vetoed decisions line", "> **The owner VETOED %d decision(s)** \u2014 their conclusions are not applied: %s"
                             % (len(vetoed), ", ".join("`%s`" % v for v in sorted(vetoed))))
        if rep.check("README: section 'Decisions' present", "Decisions" in sections):
            handled.add("Decisions")
            self.readme_decisions(sections["Decisions"], set(vetoed))
        if report.get("arms") or "Status of each direction" in sections:
            if rep.check("README: section 'Status of each direction' present", "Status of each direction" in sections):
                handled.add("Status of each direction")
                self.readme_status(sections["Status of each direction"], report)
        if report.get("scope") or "Scope of the conclusions" in sections:
            if rep.check("README: section 'Scope of the conclusions' present", "Scope of the conclusions" in sections):
                handled.add("Scope of the conclusions")
                self.readme_scope(sections["Scope of the conclusions"], report)
        for title, (hi, _, _) in sections.items():
            if title not in handled:
                self.use(hi)
                rep.nv("README section '%s'" % title, "a section the lab's exporter does not write")
            else:
                self.use(hi)
        # the closing lines, wherever they are
        notes = report.get("role_notes") or []
        if notes:
            self.expect_line("README: %d reviewer and auditor notes = report.role_notes" % len(notes),
                             "Reviewer and auditor notes that did not change the protocol: %d (in `knowledge.jsonl`, kind `discussion`)." % len(notes))
        per_unit = ("Per-task records (one row per task \u00d7 arm \u00d7 seed: solved, steps, empty and untagged answers, memory tokens): "
                    "`per_unit.csv`. The raw episode logs stay private.")
        i = self.find_line(per_unit)
        if i is None:
            rep.nv("README: the per_unit.csv sentence", "the README does not name per_unit.csv (the package predates that sentence)")
        else:
            self.use(i)
            rep.check("README: the per_unit.csv sentence", True)
        self.expect_line("README: closing line on who computed the numbers",
                         "All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.")
        self.expect_line("README: provenance line", "Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.")
        for i, line in enumerate(lines):
            if i not in self.used and line.strip():
                rep.nv("README text %r" % short(line, 70), "free text no rule here checks")

    def readme_results(self, res: Dict[str, Any], title: str, rng: Tuple[int, int, int]) -> None:
        rep = self.rep
        cycle = res.get("cycle")
        rec = self.cycles.get(cycle)
        p = res["payload"]
        tag = "README Results cycle %s" % cycle
        m = re.fullmatch(r"Results \(cycle (\S+), n = (\d+) units, (\d+) arms\)", title)
        rep.check("%s: heading n = %s units, %s arms" % (tag, m.group(2) if m else "?", m.group(3) if m else "?"),
                  bool(m) and rec is not None and int(m.group(2)) == len(rec["units"]) and int(m.group(3)) == len(p.get("success_rate") or {}),
                  "recomputed %s units, %d arms" % (len(rec["units"]) if rec else "?", len(p.get("success_rate") or {})))
        if rec is None:
            return
        tables = md_tables(self.readme_lines, rng[1], rng[2])
        arm_table = next((tb for tb in tables if tb[0][1][:2] == ["arm", "solved"]), None)
        comp_table = next((tb for tb in tables if tb[0][1][:1] == ["comparison"]), None)
        if rep.check("%s: solved table present" % tag, arm_table is not None):
            seen = []
            for i, cells in arm_table:
                self.use(i)
                if is_separator(cells) or cells[:2] == ["arm", "solved"]:
                    continue
                arm = cells[0]
                seen.append(arm)
                rate = rec["rates"].get(arm)
                rep.check("%s: solved[%s] = %s" % (tag, arm, cells[1] if len(cells) > 1 else None), rate is not None and len(cells) == 2 and agrees(r6(rate), cells[1]),
                          "recomputed %s" % ("%.4f" % rate if rate is not None else "no such arm"))
            # export.render_readme_en renders the objects as the lab stores them (canonical JSON, keys sorted)
            rep.check("%s: solved table lists the arms of the result in order" % tag, seen == list(p.get("success_rate") or {}), "README %s" % seen)
        if rep.check("%s: comparison table present" % tag, comp_table is not None):
            header = [h.lower() for h in comp_table[0][1]]
            listed = []
            for i, cells in comp_table:
                self.use(i)
                if is_separator(cells) or cells[0] == "comparison":
                    continue
                c = dict(zip(header, cells))
                label = c.get("comparison", "")
                mp = re.fullmatch(r"(\S+) \u2212 placebo \(primary\)", label)
                key = ("primary", mp.group(1)) if mp else ("secondary", label)
                listed.append(key)
                cc = rec["contrasts"].get(key)
                field = "%s: %s" % (tag, label)
                if not rep.check("%s is a contrast of the result" % field, cc is not None):
                    continue
                rep.check("%s difference %s" % (field, c.get("difference")), agrees(r6(cc["diff"]), c.get("difference", "")), "recomputed %.4f" % cc["diff"])
                mi = INTERVAL.fullmatch(c.get("95% interval", ""))
                rep.check("%s interval %s" % (field, c.get("95% interval")), bool(mi) and agrees(r6(cc["ci"][0]), mi.group(1)) and agrees(r6(cc["ci"][1]), mi.group(2)),
                          "recomputed [%.4f, %.4f]" % cc["ci"])
                mg = re.fullmatch(r"(\d+) / (\d+)", c.get("gains / losses", ""))
                rep.check("%s gains / losses %s" % (field, c.get("gains / losses")), bool(mg) and (int(mg.group(1)), int(mg.group(2))) == (cc["gains"], cc["losses"]),
                          "recomputed %d / %d" % (cc["gains"], cc["losses"]))
                self.check_state("%s state" % field, cc["ci"], rec["sesoi"], c.get("state"))
            # export.render_readme_en: primary, then secondary contrasts, in the key order of the stored result object
            want = [("primary", a) for a in (p.get("primary") or {})] + [("secondary", x) for x in (p.get("secondary") or {})]
            rep.check("%s: comparison table lists every contrast of the result in order" % tag, listed == want, "README %s" % [x[1] for x in listed])

    def readme_findings(self, rng: Tuple[int, int, int]) -> None:
        rep = self.rep
        tables = md_tables(self.readme_lines, rng[1], rng[2])
        if not rep.check("README Findings: table present", bool(tables)):
            return
        table = tables[0]
        header = [h.lower() for h in table[0][1]]
        rows = []
        for i, cells in table:
            self.use(i)
            if is_separator(cells) or cells[0] == "arm":
                continue
            rows.append(dict(zip(header, cells)))
        rep.check("README Findings: one row per finding object, in order", [r.get("id", "").strip("`") for r in rows] == [f["obj"]["id"] for f in self.findings],
                  "README %d rows, knowledge.jsonl %d findings" % (len(rows), len(self.findings)))
        for row, f in zip(rows, self.findings):
            p = f["obj"]["payload"]
            tag = "README Findings %s" % f["obj"]["id"]
            # export.render_readme_en labels findings H1, H2, ... by their running index, not by the hypothesis id
            rep.check("%s: hypothesis %s" % (tag, row.get("hypothesis")), row.get("hypothesis") == "H%d (predicted %s)" % (f["index"], p.get("predicted")),
                      "exporter label: H%d (predicted %s)" % (f["index"], p.get("predicted")))
            rep.check("%s: arm %s, cycle %s" % (tag, row.get("arm"), row.get("cycle")), row.get("arm") == p.get("arm") and row.get("cycle") == str(f["obj"].get("cycle")))
            rep.check("%s: state %s, verdict %s" % (tag, row.get("state"), row.get("verdict")), (row.get("state"), row.get("verdict")) == (p.get("state"), p.get("verdict")),
                      "finding: %s, %s" % (p.get("state"), p.get("verdict")))
            rep.check("%s: level %s" % (tag, row.get("level")), row.get("level") == LEVEL_EN.get(p.get("level"), p.get("level")), "knowledge.jsonl %s" % p.get("level"))
            rep.check("%s: difference %s" % (tag, row.get("difference")), agrees(r6(f["c"]["diff"]), row.get("difference", "")), "recomputed %.4f" % f["c"]["diff"])
            mi = INTERVAL.fullmatch(row.get("interval", ""))
            rep.check("%s: interval %s" % (tag, row.get("interval")), bool(mi) and agrees(r6(f["c"]["ci"][0]), mi.group(1)) and agrees(r6(f["c"]["ci"][1]), mi.group(2)),
                      "recomputed [%.4f, %.4f]" % f["c"]["ci"])

    @staticmethod
    def rule_notes(pb: Dict[str, Any]) -> List[str]:
        """export.process_rule_notes."""
        out = []
        if pb.get("format_rule") == "imbalance_only":
            out.append("Format criteria used the pre-registered rule `imbalance_only`: a counter fails only if the arm \u2212 placebo difference "
                       "exceeds its tolerance AND the 95% interval excludes 0. Under this rule an `unresolved` state means placebo neutrality "
                       "was not shown, only not refuted.")
            for arm, ks in sorted((pb.get("per_arm") or {}).items()):
                for k, v in sorted(ks.items()):
                    if v.get("preregistered") and v.get("state") == "unresolved" and v.get("ci"):
                        out.append("%s: `%s` unresolved \u2014 arm \u2212 placebo %+.3f [%+.3f, %+.3f], tolerance \u00b1%s: placebo neutrality not shown for this "
                                   "counter." % (arm, k, v["diff"], v["ci"][0], v["ci"][1], v["tolerance"]))
        if pb.get("behaviour_counters"):
            out.append("Counters pre-registered as behaviour, not as format failures (their imbalance does not flag a measurement problem): "
                       + ", ".join("`%s`" % x for x in pb["behaviour_counters"]) + "; see the process criteria table below.")
        return out

    def caveat_text(self, c: Dict[str, Any]) -> str:
        """export._caveat_en_safe."""
        if c.get("text_en"):
            return c["text_en"]
        d = self.k.by_id.get(c.get("decision") or "")
        act = ((d or {}).get("payload") or {}).get("action")
        return CAVEAT_EN.get(act) or ((d or {}).get("payload") or {}).get("text_en") or c.get("text") or ""

    def readme_caveats(self, rng: Tuple[int, int, int], caveats: List[Dict[str, Any]], probs: List[str], rule_notes: List[str]) -> None:
        rep, lines = self.rep, self.readme_lines
        start, end = rng[1], rng[2]
        sub = next((i for i in range(start, end) if lines[i].startswith("### ")), end)
        for c in caveats:
            text = self.caveat_text(c)
            i = self.expect_line("README Caveats: %r (report caveat)" % short(text), "- " + text, start, sub)
            if i is not None and re.search(r"first chunk|early check", text, flags=re.I):
                rep.nv("README Caveats: figures of %r" % short(text), "a check on the first chunk of the run; per_unit.csv does not record the chunks")
            elif i is not None and re.search(r"\d\.\d", text):
                self.readme_sentence_numbers("README Caveats", text)
        for x in probs:
            text = "- Measurement problem: " + problem_en(x)
            i = self.expect_line("README Caveats: measurement problem %r" % short(problem_en(x), 50), text, start, sub)
            if i is not None:
                cycle, arm = self.problem_owner(x)
                if not self.claim("README Caveats: measurement problem", problem_en(x), cycle, arm):
                    rep.nv("README Caveats: figures of %r" % short(x), "a problem without per-step figures")
        for x in rule_notes:
            self.expect_line("README Caveats: rule note %r" % short(x, 50), "- " + x, start, sub)
        decisions = self.k.kind("decision")
        for i in range(start, sub):
            line = lines[i]
            if i in self.used or not line.startswith("- "):
                continue
            text = line[2:]
            match = next((d for d in decisions if text in (CAVEAT_EN.get(d["payload"].get("action")), d["payload"].get("text_en"))), None)
            if match is not None:
                self.use(i)
                rep.check("README Caveats: %r = text of %s (%s)" % (short(text), match["id"], match["payload"].get("action")), True)
                self.readme_sentence_numbers("README Caveats", text)
        if sub < end:
            self.use(sub)
            report = (self.k.one("report") or {}).get("payload") or {}
            objections = list(report.get("instrument_objections") or [])
            bullets = [i for i in range(sub, end) if lines[i].startswith("- ")]
            rep.check("README Caveats: %d instrument objection(s) = report.instrument_objections" % len(bullets), len(bullets) == len(objections),
                      "report has %d" % len(objections))
            for i in bullets:
                self.use(i)
                if lines[i][2:] in objections:
                    rep.check("README Caveats: objection %r is in the report" % short(lines[i][2:], 40), True)
                else:
                    rep.nv("README Caveats: objection %r" % short(lines[i][2:], 40), "redacted reviewer text, not found verbatim in the report")

    def problem_owner(self, text: str) -> Tuple[Any, Optional[str]]:
        for f in self.k.kind("finding"):
            if text in (f["payload"].get("measurement_problem") or []):
                return f.get("cycle"), f["payload"].get("arm")
        return None, None

    def readme_sentence_numbers(self, where: str, text: str) -> None:
        """Figures in the V3 post-hoc annotation: 'empty retries per step: placebo a, memory b, no memory c' and the untagged criterion."""
        rep = self.rep
        cycle = self.table.cycles()[-1] if self.table.cycles() else None
        bal = self.balance_for(cycle)
        treatments = list((self.cycles.get(cycle) or {}).get("treatments") or [])
        arm = treatments[0] if len(treatments) == 1 else None
        found = False
        m = re.search(r"empty retries per step: placebo (" + NUMBER + r"), memory (" + NUMBER + r"), no memory (" + NUMBER + r")", text)
        if m and bal and arm:
            found = True
            for name, value, a in (("placebo", m.group(1), self.placebo()), ("memory", m.group(2), arm), ("no memory", m.group(3), self.baseline())):
                got = bal["rates"].get(a, {}).get("empty_retries")
                rep.check("%s: empty retries per step, %s = %s" % (where, name, value), got is not None and agrees(r4(got), value), "recomputed %s" % got)
        m = re.search(r"untagged answers per step, memory \u2212 placebo \u2264 (" + NUMBER + r")[^)]*\) (FAILED|PASSED): (" + NUMBER + r") \[(" + NUMBER + r"), ("
                      + NUMBER + r")\]", text)
        if m and bal and arm:
            found = True
            v = bal["per_arm"].get(arm, {}).get("invalid_no_action_tag")
            if v and v["state"] != "not_computable":
                rep.check("%s: untagged answers %s [%s, %s]" % (where, m.group(3), m.group(4), m.group(5)),
                          agrees(r4(v["diff"]), m.group(3)) and agrees(r4(v["ci"][0]), m.group(4)) and agrees(r4(v["ci"][1]), m.group(5)),
                          "recomputed %.4f %s (lab default bootstrap)" % (v["diff"], show(v["ci"])))
                tol = number(m.group(1))
                fails = abs(v["diff"]) > tol and not v["ci"][0] <= 0 <= v["ci"][1]
                rep.check("%s: untagged criterion %s" % (where, m.group(2)), (m.group(2) == "FAILED") == fails, "recomputed: %s" % ("fails" if fails else "passes"))
        if not found and re.search(r"\d\.\d", text):
            rep.nv("%s: figures in %r" % (where, short(text)), "figures in a sentence no rule here recomputes")

    def readme_measurement(self, rng: Tuple[int, int, int], audit: Dict[str, Any], pb: Dict[str, Any]) -> None:
        rep, lines = self.rep, self.readme_lines
        start, end = rng[1], rng[2]
        sub = next((i for i in range(start, end) if lines[i].startswith("### ")), end)
        bal = (self.process.get("_balance") or {}).get(audit["id"])
        rates = pb.get("rates") or {}
        keys = sorted({k for v in rates.values() for k in v})
        tables = md_tables(lines, start, sub)
        if rep.check("README Measurement checks: rates table present", bool(tables)):
            table = tables[0]
            header = table[0][1]
            rep.check("README Measurement checks: columns = the audit's counters %s" % keys, header == ["arm"] + keys, "README %s" % header[1:])
            seen = []
            for i, cells in table:
                self.use(i)
                if is_separator(cells) or cells[0] == "arm":
                    continue
                arm = cells[0]
                seen.append(arm)
                for col, value in zip(header[1:], cells[1:]):
                    field = "README Measurement checks: %s per step [%s] = %s" % (col, arm, value)
                    declared = (rates.get(arm) or {}).get(col, 0)
                    if col not in self.table.columns:
                        rep.check(field + " (= audit rate)", agrees(float(declared), value), "audit %s" % declared)
                        rep.nv("README Measurement checks: %s per step [%s]" % (col, arm), "%s is not a column of per_unit.csv" % col)
                    else:
                        got = (bal or {}).get("rates", {}).get(arm, {}).get(col)
                        rep.check(field + " (step-weighted)", got is not None and agrees(r4(got), value), "recomputed %s" % (None if got is None else "%.4f" % got))
            rep.check("README Measurement checks: one row per arm of the audit, in order", seen == list(rates), "README %s" % seen)
        if sub < end:
            self.use(sub)
        self.readme_process_table(lines, sub, end, pb, bal)
        self.expect_line("README: code audit verdict = %s" % audit["payload"].get("verdict"),
                         "Code audit verdict: **%s** (completeness, recomputation, leakage, raw-data integrity)." % audit["payload"].get("verdict"), start, end)

    def readme_process_table(self, lines: List[str], sub: int, end: int, pb: Dict[str, Any], bal: Optional[Dict[str, Any]]) -> None:
        """export.process_criteria_table: one row per pre-registered or behaviour counter, checked against the recomputation."""
        rep = self.rep
        beh = set(pb.get("behaviour_counters") or [])
        want = [(arm, k) for arm, ks in sorted((pb.get("per_arm") or {}).items()) for k, v in sorted(ks.items()) if v.get("preregistered") or k in beh]
        tables = md_tables(lines, sub, end) if sub < end else []
        if not want:
            rep.check("README Measurement checks: no process criteria table without criteria or behaviour counters", not tables)
            return
        if not (sub < end and lines[sub] == "### Process criteria (arm \u2212 placebo, per step)" and tables):
            rep.nv("README Measurement checks: the process criteria table", "the README has no 'Process criteria' table (the package predates it); "
                   "the criteria are checked in the audit object above")
            return
        table = tables[0]
        header = [h.lower() for h in table[0][1]]
        seen = []
        for i, cells in table:
            self.use(i)
            if is_separator(cells) or cells[0] == "arm":
                continue
            row = dict(zip(header, cells))
            arm, k = row.get("arm"), row.get("counter", "").strip("`")
            seen.append((arm, k))
            field = "README Process criteria %s / %s" % (arm, k)
            body = ((pb.get("per_arm") or {}).get(arm) or {}).get(k)
            v = ((bal or {}).get("per_arm") or {}).get(arm, {}).get(k)
            if body is None:
                rep.check("%s is a counter of the audit" % field, False)
                continue
            kind = "behaviour" if k in beh else "criterion (%s)" % (body.get("rule") or pb.get("format_rule") or "equivalence")
            rep.check("%s: kind %s, tolerance %s, state %s" % (field, row.get("kind"), row.get("tolerance"), row.get("state")),
                      (row.get("kind"), row.get("tolerance"), row.get("state")) == (kind, str(body.get("tolerance")), str(body.get("state"))),
                      "audit: %s, %s, %s" % (kind, body.get("tolerance"), body.get("state")))
            if v is None:
                rep.nv("%s: difference and interval" % field, "%s is not a column of per_unit.csv" % k)
                continue
            if v["state"] == "not_computable":
                rep.check("%s: difference and interval are empty (not computable)" % field, row.get("difference") == "\u2014" and row.get("95% interval") == "\u2014")
            else:
                mi = INTERVAL.fullmatch(row.get("95% interval", ""))
                rep.check("%s: difference %s, interval %s" % (field, row.get("difference"), row.get("95% interval")),
                          agrees(r4(v["diff"]), row.get("difference", "")) and bool(mi) and agrees(r4(v["ci"][0]), mi.group(1)) and agrees(r4(v["ci"][1]), mi.group(2)),
                          "recomputed %.4f %s (lab default bootstrap)" % (v["diff"], show(v["ci"])))
            rep.check("%s: state %s = recomputed" % (field, row.get("state")), row.get("state") == v["state"], "recomputed %s" % v["state"])
        rep.check("README Process criteria: one row per criterion and behaviour counter", seen == want, "README %d rows, expected %d" % (len(seen), len(want)))

    def readme_decisions(self, rng: Tuple[int, int, int], vetoed: Set[str]) -> None:
        rep = self.rep
        for d in self.k.kind("decision"):
            a = d["payload"].get("action")
            text = ("- `%s` (cycle %s): %s" % (d["id"], d.get("cycle"), ACTION_EN.get(a, a))
                    + (" \u2014 %s" % d["payload"]["text_en"] if d["payload"].get("text_en") else "")
                    + (" \u2014 **VETOED by the owner**" if d["id"] in vetoed else ""))
            i = self.expect_line("README Decisions: %s (%s)" % (d["id"], a), text, rng[1], rng[2])
            if i is not None and d["payload"].get("text_en"):
                self.readme_sentence_numbers("README Decisions %s" % d["id"], d["payload"]["text_en"])
        listed = [ln for ln in self.readme_lines[rng[1]:rng[2]] if ln.startswith("- `decision:")]
        rep.check("README Decisions: one line per decision object", len(listed) == len(self.k.kind("decision")), "README %d, knowledge.jsonl %d" % (len(listed), len(self.k.kind("decision"))))

    def readme_status(self, rng: Tuple[int, int, int], report: Dict[str, Any]) -> None:
        rep = self.rep
        posthoc = {}
        for d in self.k.kind("decision"):
            if d["payload"].get("action") == "post_hoc_annotation" and d["payload"].get("measurement_problem"):
                for aid in d["payload"].get("basis") or []:
                    info = self.process.get(aid)
                    if info:
                        for arm, exp in info["expected"].items():
                            counters = {x[1] for x in exp if x[0] == "process"}
                            if counters & set(d["payload"]["measurement_problem"]):
                                posthoc[arm] = d["id"]
        for arm, v in sorted((report.get("arms") or {}).items()):
            status = v.get("status")
            if arm in posthoc and status != "measurement_problem":
                rep.note("README Status: report status of %s is %s; %s records a measurement problem after the result (recomputed from "
                         "per_unit.csv), so the README must say measurement_problem" % (arm, status, posthoc[arm]))
                status = "measurement_problem"
            line = ("- %s: %s" % (arm, status) + (" (vetoed; was %s)" % v.get("vetoed_status") if status == "vetoed" else "")
                    + (" \u2014 closed despite an auditor dispute; an owner veto would reopen it" if v.get("closed_despite_dispute") else "")
                    + (" \u2014 measurement problem, so neither established nor closed" if status == "measurement_problem" else "")
                    + (" \u2014 replicated positive result, but measured despite open instrument review objections (see Caveats), so not plainly "
                       "established" if status == "established_instrument_disputed" else ""))
            self.expect_line("README Status: %s = %s" % (arm, status), line, rng[1], rng[2])
        listed = [ln for ln in self.readme_lines[rng[1]:rng[2]] if ln.startswith("- ")]
        rep.check("README Status: one line per arm of the report", len(listed) == len(report.get("arms") or {}), "README %d" % len(listed))

    def readme_scope(self, rng: Tuple[int, int, int], report: Dict[str, Any]) -> None:
        scope = report.get("scope") or {}
        runs = self.k.kind("run")
        self.rep.check("report.scope: data = run domain, units_tested = analysed units, runs = run objects, placebo, sesoi",
                       all(r["payload"].get("domain") == scope.get("data") for r in runs) and scope.get("units_tested") == sum(len(c["units"]) for c in self.cycles.values())
                       and scope.get("runs") == len(runs) and scope.get("placebo") == self.placebo() and scope.get("sesoi") == self.program().get("sesoi"),
                       "scope %s / %s / %s" % (scope.get("data"), scope.get("units_tested"), scope.get("runs")))
        text = ("The conclusions apply only to the task population `%s`, the arms %s against the placebo `%s`, the measurement conditions "
                "of the envelope and the scale of %s units in %s run(s). Do not generalise to other tasks, models, prompts or scales."
                % (scope.get("data"), scope.get("arms_tested"), scope.get("placebo"), scope.get("units_tested"), scope.get("runs")))
        self.expect_line("README Scope: the scope sentence = report.scope", text, rng[1], rng[2])

    # ---------------------------------------------------------------- run all
    def run(self) -> None:
        phases = [("package files, manifest and provenance", self.integrity), ("per_unit.csv against the run objects", self.structure),
                  ("result objects (solved rates, contrasts, intervals, states)", self.results),
                  ("measurement sensitivity and process balance (lab rules)", self.sensitivity),
                  ("findings", self.findings_checks), ("audits: noise, completeness", self.noise_checks), ("report", self.report_checks),
                  ("README, line by line", self.readme)]
        for title, phase in phases:
            print("-- " + title)
            try:
                phase()
            except InputError:
                raise
            except Exception as exc:   # a structure this script does not expect: report it, keep checking the rest
                where = traceback.extract_tb(exc.__traceback__)[-1]
                self.rep.check("phase '%s' completed" % title, False, "%s: %s (verify_autolab_packages.py line %d); the package has a structure this "
                               "verifier does not understand, or the verifier has a bug" % (type(exc).__name__, exc, where.lineno))


# --------------------------------------------------------------------------- baseline of N/V fields
def load_baseline(path: Path) -> Dict[str, List[str]]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise InputError("the N/V baseline %s is not valid JSON: %s" % (path, exc))
    return dict(data.get("packages") or {})


def compare_baseline(rep: Report, baseline: Dict[str, List[str]], baseline_path: Path) -> None:
    print("-- N/V baseline")
    if rep.package not in baseline:
        rep.note("%s has no entry in %s: its %d N/V field(s) are not pinned. Review them, then add the package with "
                 "`python scripts/verify_autolab_packages.py --package <dir> --update-baseline`." % (rep.package, baseline_path.name, len(rep.unverifiable)))
        return
    pinned = set(baseline[rep.package])
    new = [f for f in rep.unverifiable if f not in pinned]
    for field in new:
        rep.check("N/V baseline: %s" % field, False, "this field is not verifiable now but was not N/V in the baseline (coverage dropped, or the "
                  "package changed); if intended, review it and run --update-baseline")
    gone = sorted(pinned - set(rep.unverifiable))
    for field in gone:
        rep.note("N/V baseline: %r is no longer N/V (now checked, or no longer stated); run --update-baseline to tighten the baseline" % field)
    if not new:
        rep.check("N/V baseline: no new not-verifiable field (%d pinned)" % len(pinned), True)


def write_baseline(path: Path, reports: List[Report]) -> None:
    current = load_baseline(path)
    for r in reports:
        current[r.package] = sorted(r.unverifiable)
    doc = {"comment": "N/V (not verifiable from the package) fields per autolab package, pinned so that lost coverage fails CI. "
                      "Regenerate the entries of the checked packages with scripts/verify_autolab_packages.py --update-baseline "
                      "after reviewing every new N/V line.",
           "packages": {k: current[k] for k in sorted(current)}}
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("baseline written: %s (%s)" % (path, ", ".join(r.package for r in reports)))


# --------------------------------------------------------------------------- entry point
def verify_package(package: Path) -> Report:
    rep = Report(package.name)
    print("== %s ==" % package.name)
    for name in REQUIRED_FILES:
        if not (package / name).is_file():
            raise InputError("%s has no %s (a published autolab package must have %s)" % (package.name, name, ", ".join(REQUIRED_FILES)))
    Verifier(package, rep).run()
    return rep


def discover(repo: Path) -> List[Path]:
    return sorted(p for p in repo.glob(PACKAGE_GLOB) if p.is_dir())


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recompute, offline and from the package alone, the published numbers of autolab result packages "
                    "(per_unit.csv + README + knowledge.jsonl). Exit 0 = all verifiable checks pass, 1 = a number differs or the N/V "
                    "set grew beyond the baseline, 2 = usage error or a required file is missing or unreadable.")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]), help="repository root (default: the checkout this script is in)")
    parser.add_argument("--package", action="append", default=[], metavar="DIR",
                        help="check only this package folder (repeatable); default: every %s folder of the repository" % PACKAGE_GLOB)
    parser.add_argument("--baseline", default=str(Path(__file__).resolve().parent / BASELINE_NAME), help="the N/V baseline file")
    parser.add_argument("--update-baseline", action="store_true", help="write the current N/V fields of the checked packages into the baseline")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    repo = Path(args.repo).resolve()
    packages = [Path(p).resolve() for p in args.package] if args.package else discover(repo)
    if not packages:
        print("no autolab package found under %s/%s" % (repo, PACKAGE_GLOB), file=sys.stderr)
        return 2
    baseline_path = Path(args.baseline).resolve()
    reports = []
    try:
        baseline = load_baseline(baseline_path)
        for package in packages:
            if not package.is_dir():
                raise InputError("not a folder: %s" % package)
            rep = verify_package(package)
            if not args.update_baseline:
                compare_baseline(rep, baseline, baseline_path)
            print("%s: %d passed, %d FAILED, %d not verifiable from the package, %d warning(s)" % (
                rep.package, rep.passed, len(rep.failures), len(rep.unverifiable), len(rep.warnings)))
            print("")
            reports.append(rep)
    except InputError as exc:
        print("input error: " + str(exc), file=sys.stderr)
        return 2
    if args.update_baseline:
        write_baseline(baseline_path, reports)
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
