"""Pilot summary: success per arm, discordant pairs, time, errors, cycle-time estimate. Prints JSON."""
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

d = sys.argv[1] if len(sys.argv) > 1 else "pilot"
rows = [json.loads(l) for l in open(os.path.join(d, "pilot_out.jsonl"))]
log = open(os.path.join(d, "pilot_run.log"), encoding="utf-8", errors="replace").read()
by = defaultdict(dict)
for r in rows:
    by[r["unit"]][r["arm"]] = r
arms = ["none", "placebo", "retrieved_task"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(c - h, 3), round(c + h, 3))


out = {"results": len(rows), "games": len(by), "episode_errors_logged": log.count("episode error")}
for a in arms:
    rs = [r for r in rows if r["arm"] == a]
    k = sum(r["solved"] for r in rs)
    out[a] = {"n": len(rs), "solved": k, "rate": round(k / max(1, len(rs)), 3), "wilson95": wilson(k, len(rs)),
              "mean_steps": round(sum(r["metrics"]["steps"] for r in rs) / max(1, len(rs)), 1),
              "mean_seconds_concurrent": round(sum(r["metrics"]["seconds"] for r in rs) / max(1, len(rs)), 1),
              "mean_memory_tokens": round(sum(r["metrics"]["memory_tokens"] for r in rs) / max(1, len(rs)), 1),
              "invalid_actions_per_episode": round(sum(r["metrics"]["invalid_actions"] for r in rs) / max(1, len(rs)), 2)}


def disc(a, b):
    pairs = [(u[a]["solved"], u[b]["solved"]) for u in by.values() if a in u and b in u]
    n = len(pairs)
    dd = sum(x != y for x, y in pairs)
    return {"pairs": n, "discordant": dd, "rate": round(dd / max(1, n), 3), "wilson95": wilson(dd, n),
            f"{a}_only": sum(x and not y for x, y in pairs), f"{b}_only": sum(y and not x for x, y in pairs)}


out["retrieved_vs_placebo"] = disc("retrieved_task", "placebo")
out["retrieved_vs_none"] = disc("retrieved_task", "none")
out["placebo_vs_none"] = disc("placebo", "none")
# placebo length check: per game, placebo tokens vs retrieved tokens
diffs = [u["placebo"]["metrics"]["memory_tokens"] - u["retrieved_task"]["metrics"]["memory_tokens"]
         for u in by.values() if "placebo" in u and "retrieved_task" in u]
out["placebo_minus_memory_tokens"] = {"mean": round(sum(diffs) / max(1, len(diffs)), 1),
                                      "min": min(diffs) if diffs else None, "max": max(diffs) if diffs else None}
st = os.path.getmtime(os.path.join(d, "pilot_batch_started")) if os.path.exists(os.path.join(d, "pilot_batch_started")) else None
out["wall_note"] = "see PILOT.md for wall-clock time"
print(json.dumps(out, indent=1))
