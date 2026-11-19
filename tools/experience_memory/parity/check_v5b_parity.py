"""Acceptance check: the package reproduces the V5B ``retrieved_task`` memory exactly.

For each (unit, seed) the check runs the package and the instrument code of program ALFWORLD-LADDER-R4-V5B on the
same bank and the same goal, and compares:

- the chosen bank items (ids, in order);
- the rendered memory block, byte for byte (UTF-8);
- the placebo block, byte for byte, with the same deterministic stand-in token counter on both sides
  (a whitespace count; the lab used the model's tokenizer through vLLM, which this check does not need);
- ``top1_similarity`` and ``memory_similarity`` as the instrument reports them (rounded to 4 places);
- that the package excluded nothing (V5B units share no family with the bank).

Two modes:

- ``private`` (default): the lab's private V5B folder (instrument code, its 360-item bank, the units and their
  goals), given by ``--v5b-dir`` or the environment variable ``EXPERIENCE_MEMORY_V5B_DIR``; without either, the
  lab layout is tried (``private/lab-alfworld-ladder-v5b`` next to the repository clone or its worktree folder).
  Every input must match the program's SHA-256 pins. If the folder is absent the check prints ``SKIPPED`` and
  exits 0; ``--require`` makes absence an error. Nothing from the folder is written anywhere. Counts are printed;
  on a mismatch its details (unit and bank ids, digests) are printed to the terminal as well, so do not paste
  that output into a public place.
- ``public``: the public copy of the instrument and its public bank (the V3/V4 bank of 710 items), with goals of
  the public bank as queries. The reference is the pinned V5B code: the working copy of
  ``tools/alfworld_ladder/agent.py`` if it still equals the pin, else the pinned version from git history. This
  runs in CI (``tests/test_experience_memory.py``).

Exit code: 0 = no mismatch (or skipped), 1 = at least one mismatch, 2 = a required input is missing, differs
from the pins, or the check would compare nothing.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import random
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable

HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
REPO = PACKAGE_ROOT.parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from experience_memory import (ExperienceBank, ExperienceMemory, placebo_block)  # noqa: E402
from experience_memory.alfworld import from_lab_record  # noqa: E402

PUBLIC_AGENT = REPO / "tools" / "alfworld_ladder" / "agent.py"
PUBLIC_BANK = REPO / "tools" / "alfworld_ladder" / "data" / "bank.jsonl"

# SHA-256 pins of the V5B program envelope (ALFWORLD-LADDER-R4-V5B, runner pins): the instrument code and the bank
# the program ran with. The private check refuses other inputs; the public instrument must equal the pinned code.
V5B_PINS = {
    "src/agent.py": "c5c5eea0545eba11fbd27435296a80bb88e0c31e707762862f98417caba9636a",
    "data/bank.jsonl": "67a747a0a548f1554a3d2dcb5eef64ca7b025cd4eabac8ced3d1e5103a3d8ef8",
    "data/units.json": "65112a6627d49fa560e6d33ae78a5ec84148c676af91419ce4a593c01437a1b9",
    "data/families.json": "b94ce0e0ed56d4792453d67aab684948e4e0ab29c7e02e0fdb2ee271e3a0b0ba",
    # not in the envelope: the goals of the units as the game reports them, dumped before the program started
    "data/unit_goals.json": "afedda7b6408a12433ffb18954b03bf288a8b1faa75c134269a50fd553553838",
}
PRIVATE_NAME = "lab-alfworld-ladder-v5b"


def default_private_dir() -> Path:
    """``EXPERIENCE_MEMORY_V5B_DIR``, else ``private/<name>`` beside the clone (``<root>/repo``) or beside its
    worktree folder (``<root>/work/<branch>``)."""
    env = os.environ.get("EXPERIENCE_MEMORY_V5B_DIR")
    if env:
        return Path(env)
    candidates = [REPO.parent / "private" / PRIVATE_NAME, REPO.parent.parent / "private" / PRIVATE_NAME]
    return next((c for c in candidates if c.is_dir()), candidates[0])


def whitespace_tokens(text: str) -> int:
    return len(text.split())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_reference(agent_path: Path, source: bytes | None = None) -> ModuleType:
    """Import the instrument's agent.py (its top level needs only the standard library).

    ``source`` replaces the file's bytes (a version from git history); ``__file__`` stays ``agent_path``, so the
    instrument finds its ``instrument/placebo.txt`` where it lives."""
    if source is None:
        spec = importlib.util.spec_from_file_location("v5b_reference_agent", agent_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    module = ModuleType("v5b_reference_agent")
    module.__file__ = str(agent_path)
    exec(compile(source, str(agent_path), "exec"), module.__dict__)
    return module


def pinned_public_source() -> tuple[bytes | None, str]:
    """The pinned V5B instrument from the public repository: the working copy if it equals the pin, else the
    newest version in git history that does. Returns (bytes or None, where it came from)."""
    pin = V5B_PINS["src/agent.py"]
    if PUBLIC_AGENT.is_file() and sha256_file(PUBLIC_AGENT) == pin:
        return PUBLIC_AGENT.read_bytes(), "working copy"
    rel = PUBLIC_AGENT.relative_to(REPO).as_posix()
    try:
        commits = subprocess.run(["git", "log", "--format=%H", "--", rel], cwd=REPO, capture_output=True,
                                 check=True).stdout.decode().split()
        for commit in commits:
            blob = subprocess.run(["git", "show", f"{commit}:{rel}"], cwd=REPO, capture_output=True).stdout
            if hashlib.sha256(blob).hexdigest() == pin:
                return blob, f"git {commit[:12]}"
    except (OSError, subprocess.CalledProcessError):
        pass
    return None, "not found"


def read_records(bank_path: Path) -> list[dict[str, Any]]:
    with open(bank_path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compare(ref: ModuleType, records: list[dict[str, Any]], queries: Iterable[tuple[str, str, str | None]],
            seeds: Iterable[int], count_tokens: Callable[[str], int] = whitespace_tokens,
            check_placebo: bool = True) -> dict[str, Any]:
    """Compare package and reference for every (query, seed). ``queries`` are (query_id, goal, family)."""
    ref_bank = copy.deepcopy(records)
    for b in ref_bank:  # what the instrument's init() does
        b["goal"] = ref.goal_of(b["initial_observation"])
    bank = ExperienceBank(from_lab_record(r) for r in records)
    memory = ExperienceMemory(bank)
    seeds = list(seeds)
    queries = list(queries)
    if not seeds or not queries:
        raise ValueError("nothing to compare: no seed or no query")
    ref.count_tokens = count_tokens  # the instrument's placebo calls this module-level function
    n, mismatches, excluded_units = 0, [], 0
    for query_id, goal, family in queries:
        for seed in seeds:
            n += 1
            ref_block, ref_sources = ref.choose_memory(query_id, goal, "retrieved_task", seed, ref_bank)
            ref_sim = ref.similarity_metrics(goal, ref_sources, ref_bank)
            shown = memory.for_task(goal, query_id=query_id, query_family=family, seed=seed)
            got_sim = {"top1_similarity": round(shown.retrieval.top1_similarity, 4),
                       "memory_similarity": round(sum(p.score for p in shown.retrieval.picks)
                                                  / len(shown.retrieval.picks), 4)}
            problems = []
            if list(shown.block.item_ids) != list(ref_sources):
                problems.append({"field": "items", "package": list(shown.block.item_ids), "v5b": ref_sources})
            if shown.block.text.encode("utf-8") != ref_block.encode("utf-8"):
                problems.append({"field": "block", "package_sha256": hashlib.sha256(shown.block.text.encode()).hexdigest(),
                                 "v5b_sha256": hashlib.sha256(ref_block.encode()).hexdigest(),
                                 "first_difference_at": next((i for i, (a, b) in enumerate(zip(shown.block.text, ref_block))
                                                              if a != b), min(len(shown.block.text), len(ref_block)))})
            if got_sim != ref_sim:
                problems.append({"field": "similarity", "package": got_sim, "v5b": ref_sim})
            if shown.retrieval.excluded_ids:
                excluded_units += 1
                problems.append({"field": "excluded", "package": list(shown.retrieval.excluded_ids), "v5b": []})
            if check_placebo:
                ref_placebo, _ = ref.choose_memory(query_id, goal, "placebo", seed, ref_bank)
                got_placebo = placebo_block(shown.block, count_tokens).text
                if got_placebo.encode("utf-8") != ref_placebo.encode("utf-8"):
                    problems.append({"field": "placebo",
                                     "package_tokens": count_tokens(got_placebo), "v5b_tokens": count_tokens(ref_placebo)})
            if problems:
                mismatches.append({"query_id": query_id, "seed": seed, "problems": problems})
    return {"comparisons": n, "queries": n // max(1, len(seeds)), "seeds": seeds, "mismatches": mismatches,
            "units_with_exclusions": excluded_units, "bank_items": len(records)}


def run_private(folder: Path, seeds: list[int], sample: int | None, sample_seed: int, require: bool) -> int:
    agent = folder / "src" / "agent.py"
    bank_path = folder / "data" / "bank.jsonl"
    units_path, goals_path, families_path = (folder / "data" / n for n in ("units.json", "unit_goals.json",
                                                                             "families.json"))
    needed = [agent, bank_path, units_path, goals_path, families_path]
    missing = [str(p) for p in needed if not p.is_file()]
    if missing:
        print(f"SKIPPED: the private V5B instrument is not available ({len(missing)} input(s) missing, "
              f"first: {missing[0]})")
        return 2 if require else 0
    if sample is not None and sample < 1:
        print("ERROR: --sample must be at least 1")
        return 2
    wrong = [rel for rel, digest in V5B_PINS.items() if sha256_file(folder / rel) != digest]
    if wrong:
        print(f"ERROR: inputs differ from the V5B program pins: {', '.join(wrong)}")
        return 2
    ref = load_reference(agent)
    units = json.loads(units_path.read_text(encoding="utf-8"))
    goals = json.loads(goals_path.read_text(encoding="utf-8"))
    families = json.loads(families_path.read_text(encoding="utf-8"))
    if sample is not None and sample < len(units):
        units = random.Random(sample_seed).sample(units, sample)
    queries = [(task, goals[task], families[task]) for task in units]
    result = compare(ref, read_records(bank_path), queries, seeds)
    result["mode"] = "private"
    result["inputs_match_v5b_pins"] = True
    result["instrument_equals_public_agent"] = (agent.read_bytes().replace(b"\r\n", b"\n")
                                                == PUBLIC_AGENT.read_bytes().replace(b"\r\n", b"\n")
                                                if PUBLIC_AGENT.is_file() else None)
    return report(result)


def public_queries(records: list[dict[str, Any]], n: int, sample_seed: int) -> list[tuple[str, str, None]]:
    """Goals of public bank items as queries, under synthetic ids (so no item is excluded as the query itself)."""
    from experience_memory.alfworld import goal_of
    picked = random.Random(sample_seed).sample(records, min(n, len(records)))
    return [(f"query/{i}", goal_of(r["initial_observation"]), None) for i, r in enumerate(picked)]


def run_public(seeds: list[int], sample: int | None, sample_seed: int) -> int:
    source, origin = pinned_public_source()
    if source is None or not PUBLIC_BANK.is_file():
        print("ERROR: the pinned public instrument or the public bank is missing")
        return 2
    if sample is not None and sample < 1:
        print("ERROR: --sample must be at least 1")
        return 2
    records = read_records(PUBLIC_BANK)
    result = compare(load_reference(PUBLIC_AGENT, source), records,
                     public_queries(records, sample or 60, sample_seed), seeds)
    result["mode"] = "public"
    result["reference"] = origin
    return report(result)


def report(result: dict[str, Any]) -> int:
    summary = {k: v for k, v in result.items() if k != "mismatches"}
    summary["mismatch_count"] = len(result["mismatches"])
    print(json.dumps(summary, indent=1))
    for m in result["mismatches"]:
        print("MISMATCH", json.dumps(m))
    print("PASS: 0 mismatches" if not result["mismatches"] else f"FAIL: {len(result['mismatches'])} mismatch(es)")
    return 1 if result["mismatches"] else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", nargs="?", choices=("private", "public"), default="private")
    ap.add_argument("--v5b-dir", type=Path, default=None, help="the private V5B folder (default: see the module doc)")
    ap.add_argument("--seeds", default="0-9", help="seeds to check, e.g. 0-9 or 0,4,6")
    ap.add_argument("--sample", type=int, default=None, help="check only this many units (seeded sample)")
    ap.add_argument("--sample-seed", type=int, default=0)
    ap.add_argument("--require", action="store_true", help="exit 2 instead of skipping if the private folder is absent")
    a = ap.parse_args(argv)
    seeds: list[int] = []
    for part in a.seeds.split(","):
        lo, _, hi = part.partition("-")
        seeds.extend(range(int(lo), int(hi) + 1) if hi else [int(lo)])
    if not seeds:
        print(f"ERROR: --seeds {a.seeds!r} selects no seed")
        return 2
    if a.mode == "public":
        return run_public(seeds, a.sample, a.sample_seed)
    return run_private(a.v5b_dir or default_private_dir(), seeds, a.sample, a.sample_seed, a.require)


if __name__ == "__main__":
    sys.exit(main())
