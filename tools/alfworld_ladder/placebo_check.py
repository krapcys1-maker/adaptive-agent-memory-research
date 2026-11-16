"""Placebo check: one volunteer cell = one frozen block of 20 games × the arms none, placebo, retrieved_task.

Why: in the lab's V3 run, a token-matched placebo block alone added about 13 points over no memory. It also
suppressed an artefact: in the other arms the model often ended its answer at once (empty answers). V4 forbids
that with vLLM `min_tokens = 8`. A cell checks whether these effects replicate on other hardware and software.

Steps (inside the environment with alfworld, textworld and a vLLM server for the model on port 8001):

    python placebo_check.py prepare --pool v4 --block B03 --replicate 1          # writes data/contrib/<cell-id>/
    python placebo_check.py run data/contrib/<cell-id>                           # runs all episodes (GPU)
    python placebo_check.py finish data/contrib/<cell-id>                        # fills the card, checks completeness
    python placebo_check.py summary data/contrib/<cell-id>                       # prints the comparison

`--min-tokens 0` reproduces the V3 artefact; run it as a second cell on the same block to compare.
The cell id is placebo-<pool>-<block>-r<replicate>-mt<min_tokens>. Claim the block on the cell board first.
Never add valid_unseen games: prepare refuses any game outside the frozen pools.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CONTRIB_ROOT = os.environ.get("AAMR_CONTRIB_ROOT", os.path.join(REPO, "data", "contrib"))
POOLS = os.path.join(HERE, "contrib", "pools.json")
ARMS = ["none", "placebo", "retrieved_task"]
FIXED_FILES = {"agent": os.path.join(HERE, "agent.py"), "placebo": os.path.join(HERE, "instrument", "placebo.txt"),
               "bank": os.path.join(HERE, "data", "bank.jsonl")}


def sha_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def cell_dir(pool: str, block: str, rep: int, mt: int) -> tuple[str, str]:
    cid = f"placebo-{pool}-{block}-r{rep}-mt{mt}"
    return cid, os.path.join(CONTRIB_ROOT, cid)


def cmd_prepare(a) -> None:
    pools = json.load(open(POOLS, encoding="utf-8"))
    if a.pool not in pools or a.block not in pools[a.pool]["blocks"]:
        sys.exit(f"unknown pool/block {a.pool}/{a.block}; see {POOLS}")
    games = pools[a.pool]["blocks"][a.block]
    if any(not g.startswith("train/") for g in games):
        sys.exit("refusing: a block game is outside train")
    cid, d = cell_dir(a.pool, a.block, a.replicate, a.min_tokens)
    if os.path.exists(os.path.join(d, "records.jsonl")):
        sys.exit(f"{d} already has records; use a new replicate number")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "batch.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for g in games:
            for arm in ARMS:  # all arms of a game side by side: they share machine state and load
                f.write(json.dumps({"unit": f"{cid}~{g}", "task": g, "arm": arm, "seed": a.replicate}) + "\n")
    try:
        commit = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = None
    card = {
        "cell_id": cid, "pool": a.pool, "block": a.block, "replicate": a.replicate, "games": games,
        "pool_games_sha256": pools[a.pool]["games_sha256"], "arms": ARMS,
        "fixed": {"model": "Qwen/Qwen3-4B-Instruct-2507-FP8", "temperature": 0.7, "max_tokens": 2048,
                  "min_tokens": a.min_tokens, "max_steps": 50, "history_length": 50, "k": 2,
                  "sha256": {k: sha_file(p) for k, p in FIXED_FILES.items()}, "harness_commit": commit},
        "machine": {"gpu": None, "driver": None, "vllm_version": None, "quantisation_kernel": a.kernel,
                    "os": platform.platform()},
        "started_at": None, "finished_at": None, "status": "prepared", "notes": a.notes or "",
    }
    json.dump(card, open(os.path.join(d, "card.json"), "w", encoding="utf-8", newline="\n"), indent=1)
    print(f"prepared {cid}: {len(games)} games x {len(ARMS)} arms -> {d}")


def load_card(d: str) -> dict:
    return json.load(open(os.path.join(d, "card.json"), encoding="utf-8"))


def save_card(d: str, card: dict) -> None:
    json.dump(card, open(os.path.join(d, "card.json"), "w", encoding="utf-8", newline="\n"), indent=1)


def cmd_run(a) -> None:
    card = load_card(a.cell)
    for k, p in FIXED_FILES.items():
        if sha_file(p) != card["fixed"]["sha256"][k]:
            sys.exit(f"{k} changed since prepare ({p}); prepare a new cell")
    card["started_at"], card["status"] = card["started_at"] or now(), "running"
    save_card(a.cell, card)
    r = subprocess.run([sys.executable, FIXED_FILES["agent"], "--batch", os.path.join(a.cell, "batch.jsonl"),
                        "--out", os.path.join(a.cell, "records.jsonl"), "--parallel", str(a.parallel),
                        "--min-tokens", str(card["fixed"]["min_tokens"])]
                       + (["--data-root", os.path.join(os.environ["ALFWORLD_DATA"], "json_2.1.1")]
                          if os.environ.get("ALFWORLD_DATA") else []))
    card = load_card(a.cell)
    card["status"] = "ran" if r.returncode == 0 else f"run exited {r.returncode}"
    save_card(a.cell, card)
    sys.exit(r.returncode)


def machine_facts(base_url: str) -> dict:
    out = {}
    try:
        q = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=20).stdout.strip().splitlines()
        if q:
            out["gpu"], out["driver"] = [x.strip() for x in q[0].split(",")][:2]
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        with urllib.request.urlopen(base_url + "/version", timeout=5) as r:
            out["vllm_version"] = json.load(r).get("version")
    except Exception:
        pass
    return out


def read_records(d: str) -> list:
    p = os.path.join(d, "records.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def cmd_finish(a) -> None:
    card = load_card(a.cell)
    card["machine"].update({k: v for k, v in machine_facts(a.base_url).items() if v})
    recs = read_records(a.cell)
    want = {(f"{card['cell_id']}~{g}", arm) for g in card["games"] for arm in card["arms"]}
    got = {(r["unit"], r["arm"]) for r in recs}
    missing, dup = sorted(want - got), len(recs) - len(got)
    card["finished_at"] = now()
    card["records"] = {"expected": len(want), "present": len(got & want), "missing": len(missing), "duplicates": dup}
    card["status"] = "complete" if not missing and not dup else "incomplete"
    save_card(a.cell, card)
    print(json.dumps(card["records"]), card["status"])
    if missing:
        print("missing (first 5):", missing[:5])


def summarise(recs: list) -> dict:
    by = defaultdict(dict)
    for r in recs:
        by[r["unit"]][r["arm"]] = r
    full = [u for u, v in by.items() if all(a in v for a in ARMS)]
    out = {"games_with_all_arms": len(full)}
    for arm in ARMS:
        rs = [by[u][arm] for u in full]
        steps = sum(r["metrics"]["steps"] for r in rs) or 1
        out[arm] = {"solved": sum(bool(r["solved"]) for r in rs),
                    "empty_retries_per_step": round(sum(r["metrics"].get("empty_retries", 0) for r in rs) / steps, 3),
                    "untagged_per_step": round(sum(r["metrics"].get("invalid_no_action_tag", 0) for r in rs) / steps, 3),
                    "memory_tokens_mean": round(sum(r["metrics"]["memory_tokens"] for r in rs) / max(1, len(rs)))}
    for a, b in (("placebo", "none"), ("retrieved_task", "placebo"), ("retrieved_task", "none")):
        g = sum(by[u][a]["solved"] and not by[u][b]["solved"] for u in full)
        l = sum(by[u][b]["solved"] and not by[u][a]["solved"] for u in full)
        out[f"{a}-{b}"] = {"wins": g, "losses": l, "difference": round((g - l) / max(1, len(full)), 3)}
    return out


def cmd_summary(a) -> None:
    s = summarise(read_records(a.cell))
    print(json.dumps(s, indent=1))
    print("A single block of 20 games is far too small to decide anything; the maintainer pools cells by block.")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--pool", default="v4")
    p.add_argument("--block", required=True)
    p.add_argument("--replicate", type=int, default=1)
    p.add_argument("--min-tokens", type=int, default=8, choices=[0, 8])
    p.add_argument("--kernel", default=None, help="quantisation kernel reported in the vLLM log")
    p.add_argument("--notes", default=None)
    p.set_defaults(f=cmd_prepare)
    for name, f in (("run", cmd_run), ("finish", cmd_finish), ("summary", cmd_summary)):
        q = sub.add_parser(name)
        q.add_argument("cell")
        q.add_argument("--parallel", type=int, default=24)
        q.add_argument("--base-url", default="http://127.0.0.1:8001")
        q.set_defaults(f=f)
    a = ap.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
