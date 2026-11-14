"""K1 v0.4, W6: missing cells, INVALID and block A as code, with regression tests on synthetic records.

Record outcome per (task, arm, block): 1 / 0 from the checker; status limit-of-steps, context overflow and invalid output
are 0 (section 7.1); "technical_error" (an executor or checker exception confined to one episode, after the NIGHT-2 retries)
is a missing cell (None); an absent key means the episode was never attempted.
Run: python -I -X utf8 -B t_w6_cells.py"""
from __future__ import annotations

from pathlib import Path

SAMPLED = ("S1", "S2", "S3")
ARMS5 = ("N", "P", "X", "S", "M")
MAX_EXCLUDED = 7                     # "co najmniej 8 wykluczonych" -> INVALID


def outcome(rec):
    """rec: dict with 'status' and, if the checker ran, 'solved'. Returns 1, 0 or None (missing)."""
    if rec["status"] == "technical_error":
        return None
    if rec["status"] in ("forced_termination", "context_overflow"):
        return 0
    return 1 if rec.get("solved") else 0


def analyse_sampled(Y, tasks, stopped_by=None):
    """Y: {(task, arm, block): record}. Returns dict(invalid, y, used_blocks, excluded, completed)."""
    if stopped_by:
        return {"invalid": f"program zatrzymała kontrola {stopped_by}", "y": {}, "excluded": [], "completed": []}
    if not tasks:
        return {"invalid": "brak zadań do analizy", "y": {}, "excluded": [], "completed": []}
    completed = [b for b in SAMPLED if all((i, a, b) in Y for i in tasks for a in ARMS5)]
    if len(completed) < 2:
        return {"invalid": "mniej niż 2 ukończone bloki próbkowane", "y": {}, "excluded": [], "completed": completed}
    y, used, excluded = {}, {}, []
    for i in tasks:
        B = [b for b in completed if all(outcome(Y[(i, a, b)]) is not None for a in ARMS5)]
        if not B:
            excluded.append(i)
            continue
        used[i] = B
        y[i] = {a: sum(outcome(Y[(i, a, b)]) for b in B) / len(B) for a in ARMS5}
    invalid = f"wykluczono {len(excluded)} zadań (co najmniej 8)" if len(excluded) > MAX_EXCLUDED else None
    return {"invalid": invalid, "y": y, "used_blocks": used, "excluded": excluded, "completed": completed}


def analyse_block_a(YA, tasks):
    """Block A (temperature 0, arms N, M, P): a task enters M - P when it has a result in M and P."""
    inc = [i for i in tasks if all((i, a) in YA and outcome(YA[(i, a)]) is not None for a in ("M", "P"))]
    excluded = [i for i in tasks if i not in inc]
    invalid = f"blok A: wykluczono {len(excluded)} zadań (co najmniej 8)" if len(excluded) > MAX_EXCLUDED else None
    d = {i: outcome(YA[(i, "M")]) - outcome(YA[(i, "P")]) for i in inc}
    return {"invalid": invalid, "d": d, "excluded": excluded}


def full(tasks, solved=lambda i, a, b: (len(i) + ord(a[0]) + ord(b[-1])) % 3 == 0):
    return {(i, a, b): {"status": "completed", "solved": solved(i, a, b)} for i in tasks for a in ARMS5 for b in SAMPLED}


if __name__ == "__main__":
    T = [f"t{i}" for i in range(148)]
    log = []
    P = lambda *a: (print(*a), log.append(" ".join(map(str, a))))
    n = 0

    r = analyse_sampled(full(T), T); assert r["invalid"] is None and not r["excluded"] and r["completed"] == list(SAMPLED); n += 1
    Y = full(T); del Y[("t5", "X", "S3")]                                      # S3 never finished one episode -> S3 incomplete
    r = analyse_sampled(Y, T); assert r["invalid"] is None and r["completed"] == ["S1", "S2"] and r["used_blocks"]["t0"] == ["S1", "S2"]; n += 1
    Y = full(T)
    for i in T:
        del Y[(i, "M", "S2")]; del Y[(i, "M", "S3")]
    r = analyse_sampled(Y, T); assert r["invalid"] == "mniej niż 2 ukończone bloki próbkowane"; n += 1
    for k in (7, 8):                                                           # boundary of the exclusion rule
        Y = full(T)
        for i in T[:k]:
            for b in SAMPLED:
                Y[(i, "X", b)] = {"status": "technical_error"}
        r = analyse_sampled(Y, T)
        assert (r["invalid"] is None) == (k == 7) and len(r["excluded"]) == k, (k, r["invalid"]); n += 1
    Y = full(T, solved=lambda i, a, b: a == "M" and b == "S1")                 # pairing: a technical error in S1 drops S1 for that task, all arms
    Y[("t3", "P", "S1")] = {"status": "technical_error"}
    r = analyse_sampled(Y, T)
    assert r["used_blocks"]["t3"] == ["S2", "S3"] and r["y"]["t3"]["M"] == 0.0 and r["y"]["t4"]["M"] == 1 / 3; n += 1
    Y = full(T); Y[("t1", "N", "S1")] = {"status": "forced_termination"}       # step limit is a 0, not a missing cell
    r = analyse_sampled(Y, T); assert r["used_blocks"]["t1"] == list(SAMPLED) and r["y"]["t1"]["N"] == sum(
        outcome(Y[("t1", "N", b)]) for b in SAMPLED) / 3; n += 1
    Y = full(T); Y[("t1", "S", "S2")] = {"status": "context_overflow"}
    assert analyse_sampled(Y, T)["used_blocks"]["t1"] == list(SAMPLED); n += 1
    assert analyse_sampled(full(T), T, stopped_by="L3")["invalid"] == "program zatrzymała kontrola L3"; n += 1
    assert analyse_sampled({}, [])["invalid"] == "brak zadań do analizy"; n += 1                       # empty scope is not a pass
    assert analyse_sampled({}, T)["invalid"] == "mniej niż 2 ukończone bloki próbkowane"; n += 1
    YA = {(i, a): {"status": "completed", "solved": a == "M"} for i in T for a in ("N", "M", "P")}
    del YA[("t0", "N")]                                                        # N missing does not matter for M - P
    r = analyse_block_a(YA, T); assert r["invalid"] is None and "t0" in r["d"] and r["d"]["t0"] == 1; n += 1
    for k in (7, 8):
        YA2 = dict(YA)
        for i in T[:k]:
            YA2[(i, "P")] = {"status": "technical_error"}
        r = analyse_block_a(YA2, T); assert (r["invalid"] is None) == (k == 7) and len(r["excluded"]) == k; n += 1
    P(f"W6 cell rules: {n} cases (complete run; incomplete block; <2 blocks; 7 vs 8 excluded; pairing within block; step limit and "
      f"context overflow are 0; L-stop; empty scope; block A with N missing; block A 7 vs 8 excluded)")
    P("RESULT W6: PASS")
    Path(__file__).with_suffix(".out").write_text("\n".join(log) + "\n", encoding="utf-8")
