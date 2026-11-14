"""Audit helpers: read-only loaders for K1 frozen data. Never writes under [machine-local path omitted]"""
import json, collections, math
from pathlib import Path
import numpy as np
BASE = Path("[machine-local path omitted]")
ARMS = ("N", "P", "X", "S", "M")
BLOCKS = ("S1", "S2", "S3")
def rows(p):
    with open(p, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)
def tasks_index():
    t = json.load(open(BASE / "stim/k1_tasks.json", encoding="utf-8"))
    idx = {}
    for d, parts in t.items():
        for part, ts in parts.items():
            for x in ts:
                idx[x] = ("E3" if part == "test" else "E1", d, part)
    return idx
def outcome(e):
    if e.get("eval_status") != "ok":
        return None
    if e["status"] in ("forced_termination", "context_overflow"):
        return 0
    return 1 if e.get("solved") else 0
def load_eval(block):
    return {(e["task"], e["arm"]): e for e in rows(BASE / f"eval/{block}.jsonl")}
def Y():
    out = {}
    for b in BLOCKS:
        for k, e in load_eval(b).items():
            out[(k[0], k[1], b)] = outcome(e)
    return out
def ymeans(Yd, idx):
    y = {}
    for t in idx:
        y[t] = {a: np.mean([Yd[(t, a, b)] for b in BLOCKS]) for a in ARMS}
    return y
