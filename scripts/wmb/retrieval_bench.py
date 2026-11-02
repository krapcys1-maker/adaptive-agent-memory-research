"""WMB-R1: lexical versus hybrid retrieval on the account's own notes.

Preregistration: data/lab/wmb-r1-retrieval/README.md (amended) and config.json. Commands (resumable; only `judge`, `questions` and `audit` call a model, through the
flash-only proxies, and they refuse to start above the ledger stop of the config):
  prepare    verify the input digests, embed, rank every method for every task on the causal indexes, pool, control pairs, repeat sample, decisive pairs (exported blind),
             the label-free overlap table and the free controls C1 to C3 (C4 is scripts/wmb/retrieval_c4.py, run separately; its c4.json in the workdir is read by the paid stages)
  judge      the relevance judge: gate collection (controls), perturbed repeat, pooled pairs
  sample     after the judge: the stratified sample of 30 pooled pairs for the assistant to label
  questions  part U3: paraphrased questions and their answerability check (once, never regenerated)
  audit      part U3: answerability of the retrieved non-source notes of the lowest-overlap tercile
  analyse    every reading of the README from the record files alone
Before a paid stage starts: the input digests, the free controls and (but for the gate) the judge's gate controls, the freeze (the first paid stage of any kind takes the baseline
of the files and needs the assistant's labels of the decisive pairs; every later stage and `analyse` compare with it, with the filled digests of config.json and with the prompt hashes),
the ledger stop, a proxy that passes the preflight on its /arena/summary, and one run at a time per workdir (lock file). Exit codes: 0 done; 1 refused or failed before a call (a bad
input, a missing precondition, a digest or freeze mismatch); 2 stopped (budget, spend cap, outage or format breaker, proxy preflight, a control, a lock); 3 `judge --stage all` stopped
on purpose after a failed gate control.
`p1_readings` is the whole decision chain of part U1 as one function of arrays and labels (an independent re-implementation exists in retrieval_bench_ref.py).
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import platform
import random
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm_backends as backends  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402
from wmb import contract, memory_kernel as mk, stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data" / "lab" / "wmb-r1-retrieval" / "config.json"
METHODS = ("LEX_BM25", "LEX_KERNEL", "LEX_TFIDF", "EMB_MINILM", "HYB_KERNEL")        # the pool, U2 and U3
RANKED = METHODS + ("HYB_SHIPPED",)                                                  # every method ranked on the causal indexes (HYB_SHIPPED is exploratory)
TRIO = ("EMB_MINILM", "LEX_KERNEL", "HYB_KERNEL")                                    # the methods of the verdict
CONTRASTS = (("EMB_MINILM", "LEX_KERNEL"), ("HYB_KERNEL", "LEX_KERNEL"))             # P1 and P1b: A against B
SCALE = ("SAME", "RELATED", "UNRELATED")
GOOD = {"strict": ("SAME",), "lenient": ("SAME", "RELATED")}
HELPS, SUFFICIENT, UNRESOLVED = "EMBEDDER_HELPS_GATE", "LEXICAL_SUFFICIENT_FOR_GATE", "UNRESOLVED"
BASE_VERDICTS = (HELPS, SUFFICIENT, UNRESOLVED)
HYBRID_FACTOR = 0.05                                                                 # the hybrid's gates sit at 5% of tau_lex and tau_emb: its score is 20 x the strength
ID_BASE = 9999
STORED = 20                                                                          # candidates kept per method and task in prep.json
Generate = Callable[[str, str, int, dict], dict]
SummaryFn = Callable[[str], dict]


class InputMismatch(ValueError):
    """An input file does not have the digest the preregistration names."""


class BudgetStop(RuntimeError):
    """The ledger shows the slice's spend at or above the stop of the config: no stage may start."""


class RunAborted(RuntimeError):
    """A stage was stopped by a breaker: consecutive calls without a reply, or too many replies that are not an answer."""


class ControlsNotPassed(RuntimeError):
    """A control has not passed (a free one of `prepare`, C4, or the judge's positive or negative control): no paid stage may start."""


class PreflightFailed(RuntimeError):
    """The proxy of a stage is not fit for it (summary unavailable, thinking enabled, overrides, another run id or ledger): nothing was sent to it."""


class FrozenMismatch(ValueError):
    """A file, script, prompt or config the run was frozen on is not what it was."""


class LockHeld(RuntimeError):
    """Another run holds the lock of this workdir, or a crashed run left it behind."""


ERROR_BREAKER = 25                                                                   # consecutive calls without any reply that abort a stage
NONE_BREAKER = 25                                                                    # consecutive results without a usable answer (of any class) that abort a stage
FORMAT_WINDOW = 100                                                                  # a stage that has made this many calls is checked once for the share of format failures ...
FORMAT_MAX_SHARE = 0.10                                                              # ... and aborted when more than this share of them failed
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")                                   # the proxies receive the private note texts: they run on this machine


def load_config(path: Path = CONFIG) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def json_text(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def write_json(path: Path, data: object) -> None:
    contract.write_text_lf(path, json_text(data))                            # LF on every platform: a digest recorded for the file must not depend on the operating system


INPUT_KEYS = ("opublikowane.jsonl", "replay/prep.json", "data/lab/aam-e6-persona/persona.json")


def verify_inputs(cfg: dict, notes: Path, prep: Path, persona: Path) -> Dict[str, str]:
    """The sha256 of the three inputs against config.json; InputMismatch on any difference, on an input the config declares no digest for and on a digest for an unknown input."""
    paths = dict(zip(INPUT_KEYS, (notes, prep, persona)))
    declared = cfg.get("inputs_sha256", {})
    seen, bad = {}, ["%s: no such input" % key for key in declared if key not in paths]
    for key, path in paths.items():
        if key not in declared:
            bad.append("%s: config.json declares no digest for it" % key)
            continue
        got = contract.sha256_file(Path(path))
        seen[key] = got
        if got != declared[key]:
            bad.append("%s: %s... != %s..." % (key, got[:12], declared[key][:12]))
    if bad:
        raise InputMismatch("input digest mismatch: " + "; ".join(bad))
    return seen


def load_inputs(notes_path: Path, prep_path: Path) -> Tuple[List[sbm.Item], List[str]]:
    with open(notes_path, encoding="utf-8") as handle:
        items = sbm.parse_items(handle)
    briefs = [str(b) for b in json.loads(Path(prep_path).read_text(encoding="utf-8"))["briefs"]]
    if len(briefs) != len(items):
        raise ValueError("%d briefs for %d notes" % (len(briefs), len(items)))
    return items, briefs


def eligible_tasks(n: int, cfg: dict) -> List[int]:
    return list(range(cfg["tasks"]["warmup"], n))


def synthetic_times(items: Sequence[sbm.Item]) -> List[str]:
    """Day 08:00 plus the rank within the day in minutes: earlier notes of the same day are earlier in time, as E5 counted them."""
    seen: Dict[object, int] = {}
    out = []
    for it in items:
        rank = seen.get(it.day, 0)
        seen[it.day] = rank + 1
        if rank >= 900:
            raise ValueError("more than 900 notes on %s" % it.day)
        out.append("%sT%02d:%02d:00" % (it.day.isoformat(), 8 + rank // 60, rank % 60))
    return out


def note_id(j: int) -> str:
    """Ascending id order is descending recency, so the kernel's tie-break on id prefers the more recent note, as E5 did."""
    return "n%04d" % (ID_BASE - j)


def note_index(identifier: str) -> int:
    return ID_BASE - int(identifier[1:])


def rank_pairs(scores: np.ndarray, docs: Sequence[int], positive_only: bool) -> List[Tuple[int, float]]:
    """(doc, score) best first, ties towards the more recent doc; lexical scores must be above zero to be a candidate."""
    pairs = [(int(j), float(s)) for j, s in zip(docs, scores) if (s > 0 or not positive_only)]
    return sorted(pairs, key=lambda p: (-p[1], -p[0]))


class Corpus:
    """The documents (indices) one query may see, with the statistics the lexical methods need, computed over exactly those documents."""

    def __init__(self, docs: Sequence[int], stems: Sequence[Sequence[str]], vectors: np.ndarray) -> None:
        self.docs = list(docs)
        self.n = len(self.docs)
        self.tf = [Counter(stems[j]) for j in self.docs]
        self.length = np.array([len(stems[j]) for j in self.docs], dtype=float)
        self.avgdl = float(self.length.mean()) if self.n else 0.0
        self.df: Counter = Counter()
        for counts in self.tf:
            self.df.update(counts.keys())
        self.vectors = vectors[self.docs] if self.n else np.zeros((0, vectors.shape[1]))

    def bm25(self, query: Sequence[str], k1: float, b: float) -> np.ndarray:
        out = np.zeros(self.n)
        terms = sorted(set(query))
        for d, counts in enumerate(self.tf):
            total = 0.0
            for t in terms:
                f = counts.get(t, 0)
                if f:
                    idf = math.log(1.0 + (self.n - self.df[t] + 0.5) / (self.df[t] + 0.5))
                    total += idf * f * (k1 + 1.0) / (f + k1 * (1.0 - b + b * self.length[d] / self.avgdl))
            out[d] = total
        return out

    def tfidf(self, query: Sequence[str]) -> np.ndarray:
        def idf(t: str) -> float:
            return math.log((1.0 + self.n) / (1.0 + self.df.get(t, 0))) + 1.0

        q = Counter(query)
        qw = {t: (1.0 + math.log(f)) * idf(t) for t, f in q.items()}
        qn = math.sqrt(sum(w * w for w in qw.values())) or 1.0
        out = np.zeros(self.n)
        for d, counts in enumerate(self.tf):
            dn = math.sqrt(sum(((1.0 + math.log(f)) * idf(t)) ** 2 for t, f in counts.items())) or 1.0
            dot = sum(qw[t] * (1.0 + math.log(counts[t])) * idf(t) for t in qw if t in counts)
            out[d] = dot / (qn * dn)
        return out

    def cosine(self, vector: np.ndarray) -> np.ndarray:
        return self.vectors @ vector if self.n else np.zeros(0)

    def coverage(self, query: Sequence[str]) -> np.ndarray:
        """Independent reference of the kernel's lexical score: idf mass of the query found in the document over the idf mass of the query."""
        terms = sorted(set(query))
        idf = {t: math.log(1.0 + (max(1, self.n) - self.df.get(t, 0) + 0.5) / (self.df.get(t, 0) + 0.5)) for t in terms}
        mass = sum(idf.values()) or 1.0
        return np.array([sum(idf[t] for t in terms if t in counts) / mass for counts in self.tf])


def kernel_items(items: Sequence[sbm.Item], times: Sequence[str]) -> List[mk.Item]:
    return [mk.Item(note_id(j), "note", "account_history", times[j], it.text) for j, it in enumerate(items)]


LEX_PROFILE = {"name": "r1-lexical", "k": 10 ** 6, "embed": "off", "lex_tau": 1e-6, "min_evidence": 0.0, "names": False, "timeout_ms": 10 ** 7}


def hybrid_profile(tau_lex: float, tau_emb: float, factor: float = HYBRID_FACTOR) -> dict:
    """Both gates at 5% of their values so that every pair with some overlap is a candidate; the score is then 20 x max(coverage / tau_lex, cosine / tau_emb)."""
    return {"name": "r1-hybrid", "k": 10 ** 6, "embed": "required", "lex_tau": factor * tau_lex, "tau": factor * tau_emb, "min_evidence": 0.0, "names": False, "timeout_ms": 10 ** 7}


def shipped_profiles(cfg: dict) -> Tuple[dict, dict]:
    """The shipped lexical and hybrid profiles (gates as shipped, evidence floor included) with the timeout lifted and k = 1."""
    w = cfg["shipped_weights"]
    base = {"k": 1, "lex_tau": w["lex_tau"], "min_evidence": w["min_evidence"], "names": False, "timeout_ms": 10 ** 7}
    return dict(base, name="r1-shipped-lexical", embed="off", tau=w["tau"]), dict(base, name="r1-shipped-hybrid", embed="required", tau=w["tau"])


def kernel_result(index: mk.Index, query: str, now: str, profile: dict, task_type: str = "note") -> dict:
    result = mk.retrieve(index, query, task_type, now, profile)
    if result["status"] != "ok":
        raise RuntimeError("kernel status %s: %s" % (result["status"], result["error"]))
    return result


def kernel_ranking(index: mk.Index, query: str, now: str, profile: dict, task_type: str = "note") -> List[Tuple[int, float]]:
    result = kernel_result(index, query, now, profile, task_type)
    return [(note_index(i.id), float(s)) for i, s in zip(result["items"], result["scores"])]


def choose_threshold(top1: Sequence[float], share: float) -> float:
    """E5's rule: the value at position int((1 - share) * T) of the ascending values (int(0.8 * 214) = 171)."""
    ordered = sorted(top1)
    return ordered[min(len(ordered) - 1, int((1 - share) * len(ordered)))]


def base_rankings(corpus: Corpus, index: mk.Index, query: str, vector: np.ndarray, now: str, bm: dict, task_type: str = "note") -> Dict[str, List[Tuple[int, float]]]:
    q = mk.tokens(query)
    return {"LEX_BM25": rank_pairs(corpus.bm25(q, bm["k1"], bm["b"]), corpus.docs, True), "LEX_TFIDF": rank_pairs(corpus.tfidf(q), corpus.docs, True),
            "EMB_MINILM": rank_pairs(corpus.cosine(vector), corpus.docs, False), "LEX_KERNEL": kernel_ranking(index, query, now, LEX_PROFILE, task_type)}


def hybrid_rankings(index: mk.Index, query: str, now: str, tau_lex: float, tau_emb: float, shipped: dict, task_type: str = "note") -> Dict[str, List[Tuple[int, float]]]:
    return {"HYB_KERNEL": kernel_ranking(index, query, now, hybrid_profile(tau_lex, tau_emb), task_type),
            "HYB_SHIPPED": kernel_ranking(index, query, now, hybrid_profile(shipped["lex_tau"], shipped["tau"]), task_type)}


def prepare_rankings(items: Sequence[sbm.Item], briefs: Sequence[str], note_vectors: np.ndarray, brief_vectors: np.ndarray, cfg: dict) -> dict:
    """Per method and eligible task: the full candidate ranking [(note, score)]; the calibrated thresholds; the shipped profiles' first candidates; the per-task kernel
    indexes (for control C2; not stored). The memory of task i is the notes j < i only, in a kernel index of their own."""
    n, warm = len(items), cfg["tasks"]["warmup"]
    times = synthetic_times(items)
    stems = [mk.tokens(it.text) for it in items]
    kitems = kernel_items(items, times)
    cache = {b: brief_vectors[k] for k, b in enumerate(briefs)}
    embedder = lambda texts: [cache[t].tolist() for t in texts]  # noqa: E731
    all_vectors = {note_id(j): note_vectors[j].tolist() for j in range(n)}
    tasks = list(range(warm, n))
    rankings: Dict[str, Dict[int, List[Tuple[int, float]]]] = {m: {} for m in RANKED}
    indexes: Dict[int, mk.Index] = {}
    for i in tasks:
        corpus = Corpus(range(i), stems, note_vectors)
        indexes[i] = mk.build_index(kitems[:i], times[i], embedder, all_vectors)
        for m, ranking in base_rankings(corpus, indexes[i], briefs[i], brief_vectors[i], times[i], cfg["bm25"]).items():
            rankings[m][i] = ranking
    share = cfg["tasks"]["candidate_share_for_calibration"]
    tau_lex = choose_threshold([(rankings["LEX_KERNEL"][i][0][1] * LEX_PROFILE["lex_tau"]) if rankings["LEX_KERNEL"][i] else 0.0 for i in tasks], share)
    tau_emb = choose_threshold([rankings["EMB_MINILM"][i][0][1] for i in tasks], share)
    lex_shipped, hyb_shipped = shipped_profiles(cfg)
    shipped: Dict[int, dict] = {}
    for i in tasks:
        for m, ranking in hybrid_rankings(indexes[i], briefs[i], times[i], tau_lex, tau_emb, cfg["shipped_weights"]).items():
            rankings[m][i] = ranking
        lex, hyb = kernel_result(indexes[i], briefs[i], times[i], lex_shipped), kernel_result(indexes[i], briefs[i], times[i], hyb_shipped)
        shipped[i] = {"lexical": note_index(lex["items"][0].id) if lex["items"] else -1, "hybrid": note_index(hyb["items"][0].id) if hyb["items"] else -1}
    return {"times": times, "tau_lex": tau_lex, "tau_emb": tau_emb, "rankings": rankings, "indexes": indexes, "shipped": shipped}


def build_pool(rankings: dict, tasks: Sequence[int], per_method_top: int, methods: Sequence[str]) -> Dict[int, List[int]]:
    """For every task the sorted union of the first `per_method_top` candidates of the listed methods."""
    return {i: sorted({j for m in methods for j, _ in rankings[m][i][:per_method_top]}) for i in tasks}


def columns(get: Callable[[str, int], Sequence], tasks: Sequence[int], methods: Iterable[str]) -> Tuple[Dict[str, List[float]], Dict[str, List[int]]]:
    """scores[m][t] and first[m][t]: the score and note index of the method's first candidate for the t-th task (-inf and -1 when it has none)."""
    scores: Dict[str, List[float]] = {}
    first: Dict[str, List[int]] = {}
    for m in methods:
        rows = [get(m, i) for i in tasks]
        scores[m] = [float(r[0][1]) if r else float("-inf") for r in rows]
        first[m] = [int(r[0][0]) if r else -1 for r in rows]
    return scores, first


# ------------------------------------------------------------------------------------------------------------------- fire sets, overlap, decisive pairs

def fire_order(scores: Sequence[float], tasks: Sequence[int]) -> np.ndarray:
    """Positions sorted by score descending, ties by task number ascending (a score of -inf sorts last)."""
    return np.lexsort((np.asarray(tasks), -np.asarray(scores, dtype=float)))


def fire_positions(scores: Sequence[float], tasks: Sequence[int], q: float) -> np.ndarray:
    """Positions of the tasks fired at fraction q: the ceil(round(q * T, 9)) highest scores; a task with score -inf never fires, so fewer may fire."""
    s = np.asarray(scores, dtype=float)
    take = fire_order(s, tasks)[: stats.fire_size(q, len(s))]
    return take[np.isfinite(s[take])]


def hit_table(scores: Sequence[float], relevant: np.ndarray, tasks: Sequence[int], qs: Sequence[float]) -> Dict[str, dict]:
    out = {}
    for q in qs:
        take = fire_positions(scores, tasks, q)
        h = int(np.asarray(relevant, dtype=bool)[take].sum())
        out[str(q)] = {"hits": h, "false_injections": int(len(take) - h)}
    return out


def overlap_row(shared: int, same_first: int, only_a: int, only_b: int) -> dict:
    """discordant = only A + only B + shared tasks with different first candidates; decisive pairs = only A + only B + 2 x different-first; max |D| = max(only A, only B) + different-first."""
    different = shared - same_first
    return {"shared": shared, "same_first": same_first, "only_a": only_a, "only_b": only_b, "discordant_tasks": only_a + only_b + different,
            "decisive_pairs": only_a + only_b + 2 * different, "max_abs_d": max(only_a, only_b) + different}


def overlap_table(scores: Dict[str, List[float]], first: Dict[str, List[int]], tasks: Sequence[int], cfg: dict) -> List[dict]:
    """The label-free overlap table of the README, for the contrasts HYB_KERNEL / EMB_MINILM against LEX_KERNEL and q in the sweep."""
    rows = []
    for a, b in (("HYB_KERNEL", "LEX_KERNEL"), ("EMB_MINILM", "LEX_KERNEL")):
        for q in cfg["readings"]["sweep"]:
            fa, fb = set(fire_positions(scores[a], tasks, q).tolist()), set(fire_positions(scores[b], tasks, q).tolist())
            shared = fa & fb
            rows.append(dict(overlap_row(len(shared), sum(1 for t in shared if first[a][t] == first[b][t]), len(fa - fb), len(fb - fa)), contrast="%s vs %s" % (a, b), q=q))
    return rows


def format_overlap(rows: Sequence[dict]) -> str:
    head = "%-30s %5s %7s %11s %7s %7s %11s %9s %8s" % ("contrast", "q", "shared", "same first", "only A", "only B", "discordant", "decisive", "max |D|")
    lines = [head]
    for r in rows:
        lines.append("%-30s %5.2f %7d %11d %7d %7d %11d %9d %8d" % (r["contrast"], r["q"], r["shared"], r["same_first"], r["only_a"], r["only_b"], r["discordant_tasks"],
                                                                     r["decisive_pairs"], r["max_abs_d"]))
    return "\n".join(lines)


def decisive_pairs(scores: Dict[str, List[float]], first: Dict[str, List[int]], tasks: Sequence[int], q: float, contrasts: Sequence[Tuple[str, str]] = CONTRASTS) -> List[dict]:
    """At fraction q, for each contrast (A, B): the first candidate of the method that fires on a task fired by exactly one of them, and both first candidates on a task
    fired by both with different first candidates; the union over the contrasts. `found_by` lists the methods (LEX_KERNEL, EMB_MINILM, HYB_KERNEL) that fire the pair."""
    fire = {m: set(fire_positions(scores[m], tasks, q).tolist()) for m in scores}
    where = {int(i): t for t, i in enumerate(tasks)}
    found = set()
    for a, b in contrasts:
        for t in sorted(fire[a] | fire[b]):
            if t in fire[a] and t in fire[b]:
                if first[a][t] != first[b][t]:
                    found.update({(int(tasks[t]), first[a][t]), (int(tasks[t]), first[b][t])})
            else:
                found.add((int(tasks[t]), first[a][t] if t in fire[a] else first[b][t]))
    out = []
    for i, j in sorted(found):
        t = where[i]
        out.append({"i": i, "j": j, "found_by": sorted(m for m in TRIO if m in scores and t in fire[m] and first[m][t] == j)})
    return out


def origin_of(found_by: Sequence[str]) -> str:
    """Which side found a decisive pair: by LEX_KERNEL only (or with the hybrid), by EMB_MINILM only, by both, or by the hybrid alone."""
    lex, emb = "LEX_KERNEL" in found_by, "EMB_MINILM" in found_by
    if lex and emb:
        return "both"
    return "minilm_only" if emb else ("lexical_only" if lex else "hybrid_only")


def export_decisive(pairs: Sequence[dict], items: Sequence[sbm.Item], briefs: Sequence[str], seed: int) -> Tuple[List[dict], Dict[str, dict]]:
    """What the assistant reads (key, brief, note; shuffled; no method names, no scores) and the keys it is joined with afterwards."""
    order = list(pairs)
    random.Random(seed).shuffle(order)
    public, keys = [], {}
    for n, p in enumerate(order, 1):
        key = "d%03d" % n
        public.append({"key": key, "brief": briefs[p["i"]], "note": items[p["j"]].text})
        keys[key] = {"i": p["i"], "j": p["j"], "origin": origin_of(p["found_by"]), "found_by": p["found_by"]}
    return public, keys


def control_pairs(cfg: dict, tasks: Sequence[int], stems_brief: Sequence[Sequence[str]], stems_note: Sequence[Sequence[str]], note_vectors: np.ndarray,
                  brief_vectors: np.ndarray) -> Dict[str, list]:
    """Positive: (brief k, note k) for k drawn from the eligible tasks. Negative: (brief i, note j < i), 30 random and 30 hard (MiniLM cosine in the window and at most
    `max_shared_stems` shared content stems); seeded, distinct."""
    gate, rng = cfg["judge"]["gate"], random.Random(cfg["seeds"]["controls"])
    pos = sorted(rng.sample(list(tasks), min(gate["positive_control_n"], len(tasks))))
    everything = [(i, j) for i in tasks for j in range(i)]
    random_neg = sorted(rng.sample(everything, min(gate["negative_control_random"], len(everything))))
    taken = set(random_neg)
    lo, hi = gate["negative_control_hard_cosine"]
    hard_pool = []
    for i in tasks:
        cos = note_vectors[:i] @ brief_vectors[i]
        qs = set(stems_brief[i])
        for j in np.flatnonzero((cos >= lo) & (cos < hi)):
            if (i, int(j)) not in taken and len(qs & set(stems_note[int(j)])) <= gate["negative_control_hard_max_shared_stems"]:
                hard_pool.append((i, int(j)))
    hard = sorted(rng.sample(hard_pool, min(gate["negative_control_hard"], len(hard_pool))))
    return {"positive": [[k, k] for k in pos], "negative": [[i, j, "random"] for i, j in random_neg] + [[i, j, "hard"] for i, j in hard], "hard_candidates": len(hard_pool)}


def repeat_sample(cfg: dict, pooled: Sequence[Tuple[int, int]], decisive: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """A seeded 10% of the pooled pairs plus every decisive pair (judged a second time with the options in reverse order)."""
    gate = cfg["judge"]["gate"]
    rng = random.Random(cfg["seeds"]["repeat"])
    drawn = rng.sample(sorted(pooled), int(round(gate["repeat_share"] * len(pooled))))
    return sorted(set(drawn) | (set(decisive) if gate["repeat_includes_decisive_pairs"] else set()))


def stratified_sample(first_pass: Dict[Tuple[int, int], Optional[str]], decisive: Iterable[Tuple[int, int]], cfg: dict) -> List[Tuple[int, int, str]]:
    """A seeded sample of pooled pairs other than the decisive ones, an equal number per judge label (10 each for 30), shuffled."""
    per = cfg["judge"]["gate"]["stratified_sample_n"] // len(SCALE)
    rng = random.Random(cfg["seeds"]["stratified_sample"])
    skip = set(decisive)
    chosen: List[Tuple[int, int, str]] = []
    for lab in SCALE:
        pool = sorted(k for k, v in first_pass.items() if v == lab and k not in skip)
        chosen += [(i, j, lab) for i, j in rng.sample(pool, min(per, len(pool)))]
    rng.shuffle(chosen)
    return chosen


# ----------------------------------------------------------------------------------------------------------------------------- free implementation controls

def self_retrieval(items: Sequence[sbm.Item], briefs: Sequence[str], note_vectors: np.ndarray, brief_vectors: np.ndarray, tasks: Sequence[int], cfg: dict, tau_lex: float,
                   tau_emb: float) -> Dict[str, dict]:
    """C1, non-causal (all notes): per method the share of tasks k for which note k is among the first three candidates of the brief of note k (`top3`) and the first one
    (`first`, reported only), and the share for which note k is first for the brief of note k + 1 (`shift_first`, over the tasks k with k + 1 a note)."""
    times = synthetic_times(items)
    stems = [mk.tokens(it.text) for it in items]
    n = len(items)
    corpus = Corpus(range(n), stems, note_vectors)
    cache = {b: brief_vectors[k] for k, b in enumerate(briefs)}
    index = mk.build_index(kernel_items(items, times), "9999-01-01", lambda texts: [cache[t].tolist() for t in texts], {note_id(j): note_vectors[j].tolist() for j in range(n)})
    top3, first, shift = Counter(), Counter(), Counter()
    wanted = set(tasks)
    for j in tasks:                                                     # the query is the brief of note j
        ranked = base_rankings(corpus, index, briefs[j], brief_vectors[j], "9999-01-01", cfg["bm25"])
        ranked.update(hybrid_rankings(index, briefs[j], "9999-01-01", tau_lex, tau_emb, cfg["shipped_weights"]))
        for m, ranking in ranked.items():
            top3[m] += 1 if j in [x for x, _ in ranking[:3]] else 0
            first[m] += 1 if ranking and ranking[0][0] == j else 0
            shift[m] += 1 if (j - 1) in wanted and ranking and ranking[0][0] == j - 1 else 0
    shifted = sum(1 for j in tasks if (j - 1) in wanted)
    return {m: {"top3": top3[m] / len(tasks), "first": first[m] / len(tasks), "shift_first": shift[m] / shifted if shifted else 0.0} for m in RANKED}


def causality_violations(rankings: dict) -> int:
    """C2, part 1: candidates at or after the task."""
    return sum(1 for m in rankings for i, ranking in rankings[m].items() for j, _ in ranking if j >= i)


def index_checks(indexes: Dict[int, mk.Index], items: Sequence[sbm.Item], tasks: Sequence[int], cfg: dict, n: int = 25) -> dict:
    """C2, part 2: for a seeded sample of tasks the kernel index holds exactly the notes j < i and its document frequencies are those recomputed from the first i notes."""
    stems = [frozenset(mk.tokens(it.text)) for it in items]
    rng = random.Random(cfg["seeds"]["controls"] + 2)
    sample = sorted(rng.sample(list(tasks), min(n, len(tasks))))
    bad = []
    for i in sample:
        df: Counter = Counter()
        for j in range(i):
            df.update(stems[j])
        if set(indexes[i].items) != {note_id(j) for j in range(i)} or dict(df) != indexes[i].df:
            bad.append(i)
    return {"checked": len(sample), "mismatching_tasks": bad, "index_ok": not bad}


def reference_agreement(items: Sequence[sbm.Item], briefs: Sequence[str], note_vectors: np.ndarray, brief_vectors: np.ndarray, rankings: dict, tasks: Sequence[int],
                        cfg: dict, tau_lex: float, tau_emb: float, n: int = 30) -> dict:
    """C3: on a seeded sample of tasks the kernel's first candidate and score agree with a plain re-implementation of its coverage and of the hybrid strength."""
    stems = [mk.tokens(it.text) for it in items]
    rng = random.Random(cfg["seeds"]["c3"])
    sample = sorted(rng.sample(list(tasks), min(n, len(tasks))))
    worst_lex, worst_hyb, same_lex, same_hyb = 0.0, 0.0, 0, 0
    for i in sample:
        corpus = Corpus(range(i), stems, note_vectors)
        cover = corpus.coverage(mk.tokens(briefs[i]))
        ref, got = rank_pairs(cover, corpus.docs, True), rankings["LEX_KERNEL"][i]
        if ref and got:
            worst_lex = max(worst_lex, abs(ref[0][1] - got[0][1] * LEX_PROFILE["lex_tau"]))
            same_lex += 1 if ref[0][0] == got[0][0] else 0
        else:
            same_lex += 1 if not ref and not got else 0
        strength = np.maximum(cover / tau_lex, corpus.cosine(brief_vectors[i]) / tau_emb)
        ref_h, got_h = rank_pairs(strength, corpus.docs, False), rankings["HYB_KERNEL"][i]
        if ref_h and got_h:
            worst_hyb = max(worst_hyb, abs(ref_h[0][1] - got_h[0][1] * HYBRID_FACTOR))
            same_hyb += 1 if ref_h[0][0] == got_h[0][0] else 0
    return {"tasks": len(sample), "rank1_identical_lex": same_lex, "rank1_identical_hyb": same_hyb, "max_abs_diff_coverage": worst_lex, "max_abs_diff_hybrid_strength": worst_hyb}


def controls_pass(controls: dict, cfg: dict) -> Dict[str, bool]:
    r, tol = cfg["readings"], cfg["readings"]["c3_tolerance"]
    sr, ref = controls["self_retrieval"], controls["reference_agreement"]
    tau = controls.get("tau") or {}
    return {"c1_self_retrieval_top3": all(v["top3"] >= r["self_retrieval_top3_min"] for v in sr.values()),
            "c1_shifted_brief_first": all(v["shift_first"] < r["self_retrieval_shift_max"] for v in sr.values()),
            "c2_no_candidate_at_or_after_the_task": controls["causality"]["violations"] == 0, "c2_causal_index": bool(controls["causality"]["index_ok"]),
            "c3_rank1_identical": ref["rank1_identical_lex"] == ref["tasks"] and ref["rank1_identical_hyb"] == ref["tasks"],
            "c3_coverage": ref["max_abs_diff_coverage"] <= tol["coverage"], "c3_hybrid_strength": ref["max_abs_diff_hybrid_strength"] <= tol["hybrid_strength"],
            "tau_emb_matches_e5": bool(tau.get("tau_emb_matches_e5"))}              # the embedder is the pinned one: its calibrated threshold is E5's


# ------------------------------------------------------------------------------------------------------------------------------------------- the judge

QUOTES = re.compile("[\"'\u201c\u201d\u2018\u2019\u00ab\u00bb*]")
REFUSAL = re.compile(r"^\W*(?:i['\u2019]?m sorry|i am sorry|sorry|i can(?:no|['\u2019])t|i cannot|i won['\u2019]t|i will not|i['\u2019]?m unable|i am unable|i must decline|as an ai)", re.I)


def normalise_reply(raw: str) -> str:
    """Whitespace, quotes and asterisks removed, then one final full stop, then upper case."""
    text = QUOTES.sub("", re.sub(r"\s+", "", str(raw)))
    return (text[:-1] if text.endswith(".") else text).upper()


def parse_choice(raw: str, allowed: Sequence[str]) -> Optional[str]:
    """Strict: the normalised reply must be exactly one of `allowed`; 'not related', 'SAME or RELATED' or a sentence that contains a label are format failures."""
    text = normalise_reply(raw)
    return text if text in allowed else None


def parse_label(raw: str) -> Optional[str]:
    return parse_choice(raw, SCALE)


def failure_class(raw: str) -> str:
    """empty | refusal | unparseable (an exception in the call is class `error`, decided by the caller)."""
    if not str(raw).strip():
        return "empty"
    return "refusal" if REFUSAL.search(str(raw).strip()) else "unparseable"


def call_failure_class(exc: Exception) -> str:
    """A call that raised: `empty` when the backend says the completion was empty, otherwise `error`."""
    return "empty" if "empty completion" in str(exc) else "error"


def error_only(result: dict) -> bool:
    """No reply was obtained at all (every failed call raised an error): the proxy or the network, not a judgement."""
    return result["label"] is None and bool(result["failures"]) and all(f == "error" for f in result["failures"])


def call_choice(generate: Generate, system: str, prompt: str, seed: int, opts: dict, allowed: Sequence[str], attempts: int = 2) -> dict:
    """One request, retried once with the same request when the reply is not exactly one of `allowed` (or the call fails). A spend-cap refusal is not caught.
    Returns label (None after the retry), the raw reply, the classes of the failed calls and the number of calls made."""
    failures: List[str] = []
    raw = ""
    for _ in range(attempts):
        try:
            raw = str(generate(system, prompt, seed, opts).get("text", ""))
        except backends.SpendCapRefused:
            raise
        except Exception as exc:                                         # the backend raises ValueError('empty completion ...') for an empty reply
            raw = type(exc).__name__
            failures.append(call_failure_class(exc))
            continue
        label = parse_choice(raw, allowed)
        if label:
            return {"label": label, "raw": raw.strip()[:40], "failures": failures, "calls": len(failures) + 1}
        failures.append(failure_class(raw))
    return {"label": None, "raw": raw.strip()[:40], "failures": failures, "calls": attempts}


def call_text(generate: Generate, system: str, prompt: str, seed: int, opts: dict, attempts: int = 2) -> dict:
    failures: List[str] = []
    for _ in range(attempts):
        try:
            text = str(generate(system, prompt, seed, opts).get("text", "")).strip()
        except backends.SpendCapRefused:
            raise
        except Exception as exc:
            failures.append(call_failure_class(exc))
            continue
        if text:
            return {"text": text, "failures": failures}
        failures.append("empty")
    return {"text": "", "failures": failures}


def judge_prompt(cfg: dict, brief: str, note: str, reverse: bool = False) -> str:
    return cfg["judge"]["user_template_reversed" if reverse else "user_template"].format(brief=brief, note=note)


def judge_options(cfg: dict) -> dict:
    return {"temperature": cfg["judge"]["temperature"], "num_predict": cfg["judge"]["max_tokens"]}


def choice_info(result: dict) -> dict:
    """What the engine needs to know about a call_choice result."""
    failures = result["failures"]
    return {"error_only": error_only(result), "calls": result["calls"], "failed": len(failures), "none": result["label"] is None,
            "replied": result["label"] is not None or any(f != "error" for f in failures)}


def text_info(reply: dict, produced: bool) -> dict:
    """The same for a call_text result (`produced`: it yielded a usable text)."""
    failures = reply["failures"]
    return {"error_only": (not produced) and bool(failures) and all(f == "error" for f in failures), "calls": len(failures) + (1 if produced else 0), "failed": len(failures),
            "none": not produced, "replied": produced or any(f != "error" for f in failures)}


def record_results(todo: Sequence, ask: Callable[[object], Tuple[dict, dict]], out: Path, workers: int = 8, before_chunk: Optional[Callable[[], object]] = None,
                   chunk: int = 100, after_chunk: Optional[Callable[[int], object]] = None, tally: Optional[dict] = None, keep_errors: bool = True) -> int:
    """The one place where the results of a stage (judged pairs, questions, answerability checks, audit checks) reach their record file. `ask(item)` returns
    (row, info): the record and {error_only, calls, failed, none, replied}.
    - A result that got no reply at all (every attempt raised: the proxy or the network, not a judgement) is held and written only together with a later result that
      did get a reply (`keep_errors`, the judge: an isolated error is a format failure like the others); ERROR_BREAKER of them in a row abort the stage and nothing is
      written for them, so a resume asks them again. Without `keep_errors` (the one-shot stages: questions, answerability, audit, where a record is never asked again) such a
      result is never written, whatever follows; the pass ends with RunAborted when any was dropped, and the next run asks exactly those.
    - After an abort or a spend-cap refusal nothing more is written, not even the result of a call that was already in flight.
    - Format failures: when the stage has made FORMAT_WINDOW calls and more than FORMAT_MAX_SHARE of them failed, or NONE_BREAKER results in a row have no usable answer,
      the stage aborts (what was recorded stays: those are replies).
    `before_chunk` runs before and `after_chunk(number of results that got a reply)` after each chunk of `chunk` items; `tally` receives the counts."""
    tally = tally if tally is not None else {}
    for key in ("calls", "failed", "replies", "rows", "dropped_unrecorded", "streak", "error_run"):
        tally.setdefault(key, 0)
    tally.setdefault("window_checked", False)
    lock, stop = threading.Lock(), threading.Event()
    pending: List[dict] = []                                                  # rows of results that got no reply at all, kept until a later result shows the proxy answers

    def abort(message: str) -> None:
        stop.set()
        tally["dropped_unrecorded"] += len(pending)
        pending.clear()
        raise RunAborted(message)

    def one(item: object) -> None:
        if stop.is_set():
            return
        try:
            row, info = ask(item)
        except backends.SpendCapRefused:
            stop.set()
            raise
        with lock:
            if stop.is_set():                                                 # aborted while this call was in flight: nothing more is recorded
                return
            tally["calls"] += info["calls"]
            tally["failed"] += info["failed"]
            tally["replies"] += 1 if info["replied"] else 0
            tally["streak"] = tally["streak"] + 1 if info["none"] else 0
            tally["error_run"] = tally["error_run"] + 1 if info["error_only"] else 0
            if info["error_only"]:
                if keep_errors:
                    pending.append(row)
                else:
                    tally["dropped_unrecorded"] += 1
                if tally["error_run"] >= ERROR_BREAKER:
                    abort("%d calls in a row got no reply (the proxy or the network looks down); nothing was recorded for them, fix it and resume" % tally["error_run"])
            else:
                contract.append_jsonl(out, pending + [row])
                tally["rows"] += len(pending) + 1
                pending.clear()
            if tally["streak"] >= NONE_BREAKER:
                abort("%d results in a row have no usable answer (empty, unparseable, refused or no reply); the replies recorded so far stay, fix the cause and resume" % tally["streak"])
            if not tally["window_checked"] and tally["calls"] >= FORMAT_WINDOW:
                tally["window_checked"] = True
                if tally["failed"] > FORMAT_MAX_SHARE * tally["calls"]:
                    abort("%d of the first %d calls of the stage were format failures (more than %d%%); the replies recorded so far stay, fix the cause and resume" % (
                        tally["failed"], tally["calls"], round(100 * FORMAT_MAX_SHARE)))

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for start in range(0, len(todo), chunk):
            if before_chunk:
                before_chunk()
            replies = tally["replies"]
            list(pool.map(one, todo[start: start + chunk]))
            if after_chunk:
                after_chunk(tally["replies"] - replies)
    if pending:                                                               # isolated errors at the very end are format failures like the others
        contract.append_jsonl(out, pending)
        tally["rows"] += len(pending)
        pending.clear()
    if tally["dropped_unrecorded"]:
        raise RunAborted("%d result(s) got no reply and were not recorded (the proxy or the network failed); run the command again, it asks exactly those" % tally["dropped_unrecorded"])
    return len(todo)


def run_judge(pairs: Sequence[dict], items: Sequence[sbm.Item], briefs: Sequence[str], cfg: dict, generate: Generate, out: Path, workers: int = 8,
              before_chunk: Optional[Callable[[], object]] = None, chunk: int = 100, after_chunk: Optional[Callable[[int], object]] = None, tally: Optional[dict] = None) -> int:
    """Judge every pair {kind, i, j[, stratum]} not yet in `out` (one JSONL record each). kind `rep` is shown with the options in reverse order. The request, seed
    included, is the same on the retry. A spend-cap refusal stops the run."""
    done = {(r["kind"], r["i"], r["j"]) for r in contract.load_jsonl(out)}
    todo = [p for p in pairs if (p["kind"], p["i"], p["j"]) not in done]
    judge, opts = cfg["judge"], judge_options(cfg)

    def ask(pair: dict) -> Tuple[dict, dict]:
        prompt = judge_prompt(cfg, briefs[pair["i"]], items[pair["j"]].text, pair["kind"] == "rep")
        result = call_choice(generate, judge["system"], prompt, judge["seed"], opts, SCALE)
        row = {"kind": pair["kind"], "i": pair["i"], "j": pair["j"]}
        if "stratum" in pair:
            row["stratum"] = pair["stratum"]
        return dict(row, **result), choice_info(result)

    return record_results(todo, ask, out, workers, before_chunk, chunk, after_chunk, tally)


# ------------------------------------------------------------------------------------------------------------------------------ budget and the proxies

def ledger_spend(path: Optional[Path], cfg: dict) -> dict:
    """What the spend ledger holds: the slice (its own run ids; per run id the number of lines and the spend), the scope (every run id starting with the scope, the 12 USD
    cap's view) and what could not be read. A line that is torn, is not a JSON object or has no usable `usd` (null, missing, not a number, negative) belongs to no run: it is
    skipped and counted in `skipped_lines`, never summed. A line of the slice made with a model other than the budget's is counted in `foreign_model_entries`."""
    if path is None or not Path(path).exists():
        raise ValueError("a spend ledger is required for any model call (--ledger), and %s does not exist" % path)
    budget = cfg["budget"]
    scope, mine, entries, skipped, foreign = 0.0, 0.0, 0, 0, 0
    runs = {run: {"entries": 0, "usd": 0.0} for run in budget["run_ids"]}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entries += 1
        try:
            entry = json.loads(line)
        except ValueError:                                                  # a torn line: it belongs to no run and is not summed
            skipped += 1
            continue
        try:
            usd = float(entry["usd"]) if isinstance(entry, dict) and entry.get("usd") is not None else None
        except (TypeError, ValueError):
            usd = None
        if usd is None or not math.isfinite(usd) or usd < 0:
            skipped += 1
            continue
        run = str(entry.get("run_id", ""))
        if run.startswith(budget["scope"]):
            scope += usd
        if run in runs:
            mine += usd
            runs[run]["entries"] += 1
            runs[run]["usd"] += usd
            if entry.get("model") is not None and entry["model"] != budget["model"]:
                foreign += 1
    return {"scope_usd": round(scope, 6), "slice_usd": round(mine, 6), "entries": entries, "skipped_lines": skipped, "foreign_model_entries": foreign,
            "runs": {run: {"entries": v["entries"], "usd": round(v["usd"], 6)} for run, v in runs.items()}}


def budget_problem(spend: dict, cfg: dict) -> Optional[str]:
    """Why no call may be made on this ledger state: the slice's spend has reached `stop_at_usd` (at the stop the next call could only pass it) or a call of the slice was made with
    another model."""
    if spend["foreign_model_entries"]:
        return "the ledger holds %d call(s) of the slice's run ids made with a model other than %s" % (spend["foreign_model_entries"], cfg["budget"]["model"])
    if spend["slice_usd"] >= cfg["budget"]["stop_at_usd"]:
        return "the slice has spent %.4f USD, the stop is %.2f USD" % (spend["slice_usd"], cfg["budget"]["stop_at_usd"])
    return None


def assert_budget(path: Optional[Path], cfg: dict) -> dict:
    """Refuse (BudgetStop) when budget_problem says so."""
    spend = ledger_spend(path, cfg)
    problem = budget_problem(spend, cfg)
    if problem:
        raise BudgetStop(problem)
    return spend


def proxy_summary(base_url: str, timeout: float = 15.0) -> dict:
    """GET /arena/summary of a metering proxy (the base url may end in /v1)."""
    root = base_url.rstrip("/")
    root = root[:-3] if root.endswith("/v1") else root
    with urllib.request.urlopen(root + "/arena/summary", timeout=timeout) as handle:
        return json.load(handle)


def summary_problems(summary: object) -> List[str]:
    """Thinking disabled, no decoding overrides, no refused or unknown-usage calls."""
    if not isinstance(summary, dict) or "calls" not in summary:
        return ["summary unavailable"]
    problems = []
    for key, text in (("refused_calls", "refused calls"), ("unknown_usage_calls", "calls of unknown usage"), ("decoding_overrides", "decoding overrides")):
        if summary.get(key):
            problems.append("%s: %s" % (text, summary[key]))
    thinking = (summary.get("arena_enforced_decoding") or {}).get("thinking")
    if not (isinstance(thinking, dict) and thinking.get("type") == "disabled"):
        problems.append("thinking is not disabled")
    return problems


def safe_summary(fn: SummaryFn, url: str) -> dict:
    try:
        return fn(url)
    except Exception as exc:
        return {"unavailable": type(exc).__name__}


# ------------------------------------------------------------------------------------------------------------- files of a run and the stages of the judge

(PREP, PAIRS, LABELS, VECTORS, RESULTS, SUMMARY, STAGES, BASELINE) = ("prep.json", "pairs.json", "labels.jsonl", "vectors.npz", "results.json", "summary.json", "stages.jsonl",
                                                                       "budget_baseline.json")
(DECISIVE, DECISIVE_KEYS, DECISIVE_ASSISTANT) = ("decisive.json", "decisive_keys.json", "decisive_labels_assistant.json")
(STRATIFIED, STRATIFIED_KEYS, STRATIFIED_ASSISTANT) = ("stratified.json", "stratified_keys.json", "stratified_labels_assistant.json")
(QUESTIONS, ANSWERS, AUDIT) = ("questions.jsonl", "answerable.jsonl", "audit.jsonl")


def default_embed(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> Callable[[Sequence[str]], np.ndarray]:
    os.environ["HF_HUB_OFFLINE"] = "1"                                       # before the import: no network, the model comes from the local cache
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from sentence_transformers import SentenceTransformer  # imported here: the module is usable without it
    model = SentenceTransformer(model_name, device="cpu")
    return lambda texts: np.asarray(model.encode(list(texts), normalize_embeddings=True, batch_size=32, show_progress_bar=False), dtype=float)


def find_minilm_weights(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> Optional[Path]:
    """The weights file of the model in the local Hugging Face cache (None when it is not there)."""
    root = Path(os.environ.get("HF_HUB_CACHE") or (Path(os.environ.get("HF_HOME") or (Path.home() / ".cache" / "huggingface")) / "hub"))
    folder = root / ("models--" + model_name.replace("/", "--")) / "snapshots"
    hits = sorted(folder.glob("*/model.safetensors")) if folder.exists() else []
    return hits[0] if hits else None


def package_version(name: str) -> Optional[str]:
    """The version of an installed package: the one its module reports when it is already imported (torch says 2.10.0+cpu where its metadata says 2.10.0, and the pin of
    config.json is the former), else the one of its metadata, None when it is not installed."""
    loaded = getattr(sys.modules.get(name.replace("-", "_")), "__version__", None)
    if isinstance(loaded, str):
        return loaded
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return None


def environment_record(cfg: dict) -> dict:
    """The versions of Python and of the libraries, and the sha256 of the MiniLM weights file of the local cache, against the pins of config.json (recorded, not enforced:
    the calibrated threshold of the embedder is, as the control `tau_emb_matches_e5`)."""
    weights = find_minilm_weights()
    got = {"python": platform.python_version(), "numpy": package_version("numpy"), "scipy": package_version("scipy"), "torch": package_version("torch"),
           "sentence_transformers": package_version("sentence-transformers"), "minilm_weights_sha256": contract.sha256_file(weights) if weights else None}
    pinned = cfg.get("environment", {})
    return dict(got, matches_pinned={key: got[key] == pinned[key] for key in got if key in pinned})


PREPARE_GUARDS = (LABELS, BASELINE, DECISIVE_ASSISTANT, STRATIFIED, STRATIFIED_KEYS, STRATIFIED_ASSISTANT, QUESTIONS, ANSWERS, AUDIT)   # files that depend on the pairs of a prepare (the baseline is taken before the first call of any stage)


def nonempty(path: Path) -> bool:
    return Path(path).exists() and Path(path).stat().st_size > 0


def cmd_prepare(args: argparse.Namespace, embed: Callable[[Sequence[str]], np.ndarray]) -> dict:
    """Everything that needs no model call. The free controls it runs are C1 to C3 only: C4 (the analysis against its independent re-implementation on planted labels) is
    scripts/wmb/retrieval_c4.py, run separately on the prep.json this writes (its c4.json is read by the paid stages when it exists in the workdir). It refuses to overwrite the
    pairs of a run that labels or judge records already depend on, unless --force-prepare."""
    cfg = load_config(args.config)
    digests = {} if args.allow_input_mismatch else verify_inputs(cfg, args.notes, args.prep, args.persona)
    items, briefs = load_inputs(args.notes, args.prep)
    work = Path(args.workdir)
    held = [name for name in PREPARE_GUARDS if nonempty(work / name)]
    if held and not args.force_prepare:
        raise ValueError("%s exist in %s: labels and records depend on the pairs of the earlier prepare, which this one would overwrite (the keys of the decisive pairs would point to "
                         "other pairs); use a fresh workdir, or --force-prepare to overwrite on purpose" % (", ".join(held), work))
    work.mkdir(parents=True, exist_ok=True)
    nv, bv = embed([i.text for i in items]), embed(briefs)
    np.savez(work / VECTORS, notes=nv, briefs=bv)
    prep = prepare_rankings(items, briefs, nv, bv, cfg)
    tasks = eligible_tasks(len(items), cfg)
    rankings = prep["rankings"]
    scores, first = columns(lambda m, i: rankings[m][i], tasks, RANKED)
    overlap = overlap_table(scores, first, tasks, cfg)
    decisive = decisive_pairs(scores, first, tasks, cfg["readings"]["primary_q"])
    pool = build_pool(rankings, tasks, cfg["pool"]["per_method_top"], cfg["pool"]["methods"])
    if any(p["j"] not in pool[p["i"]] for p in decisive):
        raise ValueError("a decisive pair is not in the pool")
    stems_b, stems_n = [mk.tokens(b) for b in briefs], [mk.tokens(it.text) for it in items]
    ctl = control_pairs(cfg, tasks, stems_b, stems_n, nv, bv)
    flat = [(i, j) for i in tasks for j in pool[i]]
    repeat = repeat_sample(cfg, flat, [(p["i"], p["j"]) for p in decisive])
    public, keys = export_decisive(decisive, items, briefs, cfg["judge"]["seed"])
    controls = {"self_retrieval": self_retrieval(items, briefs, nv, bv, tasks, cfg, prep["tau_lex"], prep["tau_emb"]),
                "causality": dict(violations=causality_violations(rankings), **index_checks(prep["indexes"], items, tasks, cfg)),
                "reference_agreement": reference_agreement(items, briefs, nv, bv, rankings, tasks, cfg, prep["tau_lex"], prep["tau_emb"]),
                "tau": {"tau_emb": prep["tau_emb"], "tau_emb_e5": cfg["reference_threshold_e5"], "tau_emb_matches_e5": abs(prep["tau_emb"] - cfg["reference_threshold_e5"]) < 5e-4,
                        "tau_lex": prep["tau_lex"]}}
    stored = {m: {str(i): [[j, s] for j, s in r[i][:STORED]] for i in tasks} for m, r in rankings.items()}
    write_json(work / PREP, {"times": prep["times"], "tau_lex": prep["tau_lex"], "tau_emb": prep["tau_emb"], "eligible": tasks, "rankings": stored, "overlap": overlap,
                             "shipped": {str(i): v for i, v in prep["shipped"].items()}, "controls": controls, "input_sha256": digests, "environment": environment_record(cfg)})
    write_json(work / PAIRS, {"pool": {str(i): pool[i] for i in tasks}, "positive": ctl["positive"], "negative": ctl["negative"], "hard_candidates": ctl["hard_candidates"],
                              "repeat": [list(p) for p in repeat], "decisive": [[p["i"], p["j"]] for p in decisive]})
    write_json(work / DECISIVE, public)
    write_json(work / DECISIVE_KEYS, keys)
    print(format_overlap(overlap))
    return {"tasks": len(tasks), "pool_pairs": len(flat), "decisive_pairs": len(decisive), "repeat_pairs": len(repeat), "controls_pass": controls_pass(controls, cfg),
            "tau_lex": prep["tau_lex"], "tau_emb": prep["tau_emb"], "tau_emb_matches_e5": controls["tau"]["tau_emb_matches_e5"], "decisive_keys_sha256": decisive_keys_digest(keys),
            "sha256": {name: contract.sha256_file(work / name) for name in (PREP, PAIRS, VECTORS, DECISIVE, DECISIVE_KEYS)}}


def judge_pairs(work: Path, stage: str, cfg: dict) -> List[dict]:
    pairs = read_json(work / PAIRS)
    rng = random.Random(cfg["judge"]["seed"])
    if stage == "gate":
        flat = [{"kind": "pos", "i": i, "j": j} for i, j in pairs["positive"]] + [{"kind": "neg", "i": i, "j": j, "stratum": s} for i, j, s in pairs["negative"]]
    elif stage == "repeat":
        flat = [{"kind": "rep", "i": i, "j": j} for i, j in pairs["repeat"]]
    elif stage == "pool":
        flat = [{"kind": "pool", "i": int(i), "j": j} for i, js in sorted(pairs["pool"].items(), key=lambda kv: int(kv[0])) for j in js]
    else:
        raise ValueError("unknown stage %r" % stage)
    rng.shuffle(flat)                                                         # a fixed shuffle: the judge sees no order by task or method
    return flat


def run_id_for(role: str, cfg: dict) -> str:
    """The run id the config assigns to the proxy of a role (`judge` or `writer`)."""
    ids = list(cfg["budget"]["run_ids"])
    named = [r for r in ids if r.endswith("-" + role)]
    return named[0] if len(named) == 1 else ids[0 if role == "judge" else 1]


def same_path(a: object, b: object) -> bool:
    norm = lambda p: os.path.normcase(os.path.realpath(str(p)))  # noqa: E731
    return norm(a) == norm(b)


def identity_problems(summary: object, run_id: str, ledger: Optional[Path], cfg: dict) -> List[str]:
    """A spend guard that cannot be blind: the proxy must say that it runs as the run id of the config (the guard sums the ledger lines of that id) and that it writes the ledger
    the guard reads, and its run cap must not be above the slice's."""
    if not isinstance(summary, dict):
        return []
    out = []
    got = summary.get("run_id")
    if got is None:
        out.append("the proxy does not report its run id (restart it from this branch: its /arena/summary then reports run_id and ledger_path)")
    elif got != run_id:
        out.append("the proxy runs as run id %r, the config expects %r" % (got, run_id))
    reported = summary.get("ledger_path")
    if reported is not None and ledger is not None and not same_path(reported, ledger):
        out.append("the proxy writes the ledger %s, the guard reads %s" % (reported, ledger))
    if "run_cap_usd" in summary:
        cap, limit = summary["run_cap_usd"], cfg["budget"]["run_cap_usd_each"]
        if isinstance(cap, bool) or not isinstance(cap, (int, float)) or cap > limit:
            out.append("the proxy's run cap is %r, the slice allows at most %s USD per proxy" % (cap, limit))
    return out


def preflight_problems(summary: object, run_id: str, ledger: Optional[Path], cfg: dict) -> List[str]:
    """Everything that must be right with a proxy before a stage sends it a single note."""
    problems = summary_problems(summary)
    return problems if "summary unavailable" in problems else problems + identity_problems(summary, run_id, ledger, cfg)


class StageGuard:
    """What a running stage checks around each chunk of calls: the ledger before the chunk (the stop) and after it (the proxy must have written to this ledger under this run id
    when it answered, else the spend guard is blind)."""

    def __init__(self, ledger: Optional[Path], cfg: dict, run_id: str, spend: dict) -> None:
        self.ledger, self.cfg, self.run_id, self.spend = ledger, cfg, run_id, spend
        self.tally: dict = {}

    def before_chunk(self) -> None:
        self.spend = assert_budget(self.ledger, self.cfg)

    def after_chunk(self, replies: int) -> None:
        now = ledger_spend(self.ledger, self.cfg)
        grew = now["runs"].get(self.run_id, {}).get("entries", 0) > self.spend["runs"].get(self.run_id, {}).get("entries", 0)
        self.spend = now
        if replies > 0 and not grew:
            raise BudgetStop("%d call(s) of this chunk were answered but the ledger %s gained no line of run id %s: the ledger path or the run id does not match the proxy, "
                             "so the spend guard would be blind" % (replies, self.ledger, self.run_id))


# ---------------------------------------------------------------------------------------------------------------------------- one run at a time: the lock

def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":                                                       # os.kill(pid, 0) would terminate the process on Windows
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype, kernel32.OpenProcess.argtypes = ctypes.c_void_p, [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(0x1000, False, pid)                     # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5                               # ERROR_ACCESS_DENIED: the process exists
        try:
            code = ctypes.c_ulong()
            known = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return (not known) or code.value == 259                           # 259 = STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def describe_lock(path: Path) -> str:
    try:
        info = json.loads(Path(path).read_text(encoding="utf-8"))
        pid = int(info["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        return "the lock file %s exists and cannot be read; if no other run is using this workdir, delete it" % path
    started = info.get("started", "?")
    if pid_alive(pid):
        return "another run holds the lock %s (process %d, started %s): wait for it to finish; delete the file only if that process is not a run of this workdir" % (path, pid, started)
    return ("stale lock %s: left by process %d (started %s), which is no longer running (a crash or a kill); if no other run is using this workdir, delete the file and resume"
            % (path, pid, started))


@contextlib.contextmanager
def workdir_lock(work: Path, name: str):
    """One exclusive lock file per workdir and appending command (`judge`, `questions`, `audit`; the three judge stages share labels.jsonl): created with O_EXCL, it holds the
    pid and is removed on exit. A second launch, or the leftover of a crashed run, is refused with a message that says which."""
    Path(work).mkdir(parents=True, exist_ok=True)
    path = Path(work) / ("%s.lock" % name)
    for _ in range(50):
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            raise LockHeld(describe_lock(path)) from None
        except PermissionError:                                               # Windows: the file is still open elsewhere (being read or deleted); look again in a moment
            time.sleep(0.01)
    else:
        raise LockHeld("the lock file %s cannot be created (permission denied)" % path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "command": name, "started": datetime.now(timezone.utc).isoformat(timespec="seconds")}) + "\n")
        yield path
    finally:
        for _ in range(100):                                                  # Windows refuses to delete a file that another process has open at that instant
            try:
                path.unlink()
                break
            except FileNotFoundError:
                break
            except OSError:
                time.sleep(0.01)


# --------------------------------------------------------------------------------------------------------------- what the run was frozen on

FROZEN_FILES = (PREP, PAIRS, VECTORS, DECISIVE, DECISIVE_KEYS, DECISIVE_ASSISTANT)       # digested before the first paid call (Amendment 2)
RECORD_FILES = (LABELS, QUESTIONS, ANSWERS, AUDIT)                                    # the results of paid calls (stages.jsonl only describes how the stages went)


def decisive_keys_digest(keys: Iterable[str]) -> str:
    """sha256 of the sorted decisive keys, one per line: what binds the assistant's label file to the key set it labelled."""
    return hashlib.sha256("\n".join(sorted(keys)).encode("utf-8")).hexdigest()


def prompt_digests(cfg: dict) -> Dict[str, str]:
    """config.json judge.prompt_sha256_of: sha256 of system + two newlines + user_template (UTF-8), the reversed prompt likewise with user_template_reversed."""
    j = cfg["judge"]
    return {"prompt_sha256": hashlib.sha256((j["system"] + "\n\n" + j["user_template"]).encode("utf-8")).hexdigest(),
            "prompt_reversed_sha256": hashlib.sha256((j["system"] + "\n\n" + j["user_template_reversed"]).encode("utf-8")).hexdigest()}


def assistant_label_problems(work: Path, items: Optional[Sequence[sbm.Item]] = None, briefs: Optional[Sequence[str]] = None) -> List[str]:
    """Why the assistant's label file does not cover the decisive pairs (empty: it does). Both files must exist as JSON objects, the decisive key set must not be empty, and the
    labels must be exactly one valid label per decisive key and nothing else (the sha256 of the sorted keys is the same on both sides). With the notes and briefs, the pairs of
    decisive_keys.json must also be the ones decisive.json shows (what the assistant read): keys that were re-assigned to other pairs after the labelling are found."""
    work = Path(work)
    missing = ["%s is missing" % name for name in (DECISIVE_KEYS, DECISIVE_ASSISTANT) if not (work / name).exists()]
    if missing:
        return missing
    try:
        keys, mine = read_json(work / DECISIVE_KEYS), read_json(work / DECISIVE_ASSISTANT)
    except ValueError as exc:
        return ["a decisive file is not valid JSON: %s" % exc]
    if not isinstance(keys, dict) or not keys:
        return ["%s holds no decisive pair" % DECISIVE_KEYS]
    if not isinstance(mine, dict):
        return ["%s must be a JSON object {key: label}" % DECISIVE_ASSISTANT]
    problems = []
    if decisive_keys_digest(mine) != decisive_keys_digest(keys):
        problems.append("the keys of %s are not the decisive keys (sha256 of the sorted keys %s... against %s...; %d missing, %d extra)" % (
            DECISIVE_ASSISTANT, decisive_keys_digest(mine)[:12], decisive_keys_digest(keys)[:12], len(set(keys) - set(mine)), len(set(mine) - set(keys))))
    bad = sorted(k for k in keys if mine.get(k) not in SCALE)
    if bad:
        problems.append("%d decisive key(s) have no valid label (SAME, RELATED or UNRELATED), for example %s" % (len(bad), bad[:3]))
    if items is not None and briefs is not None and (work / DECISIVE).exists():
        try:
            public = read_json(work / DECISIVE)
        except ValueError:
            return problems + ["%s is not valid JSON" % DECISIVE]
        shown = {r["key"]: r for r in public if isinstance(r, dict) and "key" in r} if isinstance(public, list) else {}

        def differs(key: str) -> bool:
            try:
                return key not in shown or shown[key].get("brief") != briefs[keys[key]["i"]] or shown[key].get("note") != items[keys[key]["j"]].text
            except (IndexError, KeyError, TypeError):
                return True

        differing = sorted(k for k in keys if differs(k)) + sorted(set(shown) - set(keys))
        if differing:
            problems.append("%s does not describe the pairs that %s shows the assistant (%d key(s) differ, for example %s): the labels would attach to other pairs" % (
                DECISIVE_KEYS, DECISIVE, len(differing), differing[:3]))
    return problems


def assistant_labels_complete(work: Path) -> bool:
    """The assistant's label file exists and holds a valid label for every decisive pair, and for nothing else (README: it labels them before the judge is called)."""
    return not assistant_label_problems(work)


def require_assistant_labels(work: Path, items: Optional[Sequence[sbm.Item]] = None, briefs: Optional[Sequence[str]] = None) -> None:
    problems = assistant_label_problems(work, items, briefs)
    if problems:
        raise ValueError("the assistant's labels of the decisive pairs (%s, one valid label per key of %s) must exist before any model call: %s" % (DECISIVE_ASSISTANT, DECISIVE_KEYS,
                                                                                                                                                  "; ".join(problems)))


def code_fingerprint(cfg: dict, config_path: Optional[Path]) -> str:
    """One digest of the config file and of every script of the freeze list: what ran, in a stage record."""
    parts = ["config " + (contract.sha256_file(Path(config_path)) if config_path else "?")]
    parts += ["%s %s" % (rel, d["sha256"]) for rel, d in sorted(script_digests(cfg).items())]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def frozen_verdict(work: Path, cfg: dict, config_path: Optional[Path] = None) -> dict:
    """Is everything the run was frozen on still what it was? The files whose digests were taken before the first paid call, the config, every script digest that is filled in
    config.json and the two prompt hashes. Unfilled (null) digests are listed in `unfrozen`, they are not a difference. The stage records' code fingerprint against the code now is
    reported, not enforced."""
    work, problems = Path(work), []
    out: dict = {"baseline_present": (work / BASELINE).exists()}
    files: Dict[str, dict] = {}
    if out["baseline_present"]:
        base = read_json(work / BASELINE)
        for name, digest in sorted(base.get("sha256_before_the_first_call", {}).items()):
            now = contract.sha256_file(work / name) if (work / name).exists() else None
            files[name] = {"baseline": digest, "now": now, "match": now == digest}
            if now != digest:
                problems.append("%s changed after the first paid call (%s... then, %s now)" % (name, digest[:12], (now[:12] + "...") if now else "missing"))
        if base.get("config_sha256") and config_path is not None:
            now = contract.sha256_file(Path(config_path))
            out["config"] = {"baseline": base["config_sha256"], "now": now, "match": now == base["config_sha256"]}
            if now != base["config_sha256"]:
                problems.append("the config changed after the first paid call (%s... then, %s... now)" % (base["config_sha256"][:12], now[:12]))
        if base.get("decisive_keys_sha256") and (work / DECISIVE_KEYS).exists():
            now = decisive_keys_digest(read_json(work / DECISIVE_KEYS))
            if now != base["decisive_keys_sha256"]:
                problems.append("the decisive key set changed after the first paid call")
    else:
        stray = [name for name in RECORD_FILES if nonempty(work / name)]
        if stray:
            problems.append("%s exist but %s is missing: the digests of the first paid call cannot be checked" % (", ".join(stray), BASELINE))
    scripts = script_digests(cfg)
    problems += ["%s differs from the digest frozen in config.json" % rel for rel, d in sorted(scripts.items()) if d["match"] is False]
    prompts = {}
    for key, got in prompt_digests(cfg).items():
        frozen = cfg["judge"].get(key)
        prompts[key] = {"sha256": got, "frozen": frozen, "match": None if frozen is None else got == frozen}
        if frozen is not None and got != frozen:
            problems.append("the %s prompt differs from the digest frozen in config.json" % key.replace("_sha256", ""))
    out.update(files=files, prompts=prompts, unfrozen=sorted(rel for rel, d in scripts.items() if d["frozen"] is None) + sorted(k for k, p in prompts.items() if p["frozen"] is None))
    seen = {r.get("code_sha256") for r in contract.load_jsonl(work / STAGES)}
    out["stage_records_same_code_as_now"] = (seen == {code_fingerprint(cfg, config_path)}) if seen and config_path is not None else None
    out["ok"], out["problems"] = not problems, problems
    return out


def verify_frozen(work: Path, cfg: dict, config_path: Path) -> dict:
    """Before every paid stage: the run is what it was frozen on (the files of the baseline, the config, the filled script digests, the prompt hashes; a workdir that has no
    baseline yet only has its scripts and prompts checked, and must not hold paid results)."""
    verdict = frozen_verdict(work, cfg, config_path)
    if not verdict["ok"]:
        raise FrozenMismatch("the run is not what was frozen: " + "; ".join(verdict["problems"]))
    return verdict


def take_baseline(work: Path, cfg: dict, spend: dict, config_path: Path) -> None:
    """The first paid stage of any kind, once its proxy has passed the preflight and right before its first call: it needs the assistant's valid label file (hence all six files
    exist), and it writes the baseline of the digests, the spend already in the scope and the config digest. Later stages find it and compare."""
    work = Path(work)
    if (work / BASELINE).exists():
        return
    require_assistant_labels(work)
    absent = [name for name in FROZEN_FILES if not (work / name).exists()]
    if absent:
        raise ValueError("%s missing from %s (run prepare first)" % (", ".join(absent), work))
    baseline = {"scope": cfg["budget"]["scope"], "scope_usd": spend["scope_usd"], "slice_usd": spend["slice_usd"],
                "sha256_before_the_first_call": {name: contract.sha256_file(work / name) for name in FROZEN_FILES},
                "decisive_keys_sha256": decisive_keys_digest(read_json(work / DECISIVE_KEYS)), "config_sha256": contract.sha256_file(Path(config_path))}
    try:
        contract.write_text_lf(work / BASELINE, json_text(baseline), exclusive=True)
    except FileExistsError:
        pass                                                                  # another command took it a moment ago


# ------------------------------------------------------------------------------------------------------------------------ one stage of model calls

def proxy_calls_delta(before: object, after: object) -> Optional[int]:
    if isinstance(before, dict) and isinstance(after, dict) and isinstance(before.get("calls"), int) and isinstance(after.get("calls"), int):
        return after["calls"] - before["calls"]
    return None


def run_stage(name: str, url: str, todo: Callable[[StageGuard], int], args: argparse.Namespace, cfg: dict, summary_fn: SummaryFn, role: str = "judge") -> dict:
    """One stage of model calls. Before the first note is sent: the budget (the ledger stop), the freeze (the comparison with the baseline, the filled digests) and the proxy
    (its summary must be available, thinking disabled, no overrides, and it must run as the run id of the config on the ledger read here); then the first paid stage of any kind
    takes the baseline. During it: the ledger is read before and after each chunk. In every case, also when the stage stops or is refused, a record with the summaries and the
    ledger before and after goes to stages.jsonl."""
    work = Path(args.workdir)
    spend = ledger_spend(args.ledger, cfg)
    stop = budget_problem(spend, cfg)
    if stop:                                                                  # a stage that cannot start leaves its record, too
        contract.append_jsonl(work / STAGES, [{"stage": name, "role": role, "url": url, "pairs_asked": 0, "outcome": "refused before any call: " + stop, "ledger_before": spend,
                                               "ledger_after": spend, "problems_before": [], "problems_after": []}])
        raise BudgetStop(stop)
    if spend["skipped_lines"]:
        print("warning: the spend ledger holds %d line(s) that are not run records (torn, not an object or without a usable usd); they were skipped" % spend["skipped_lines"], file=sys.stderr)
    verify_frozen(work, cfg, args.config)
    run_id = run_id_for(role, cfg)
    before = safe_summary(summary_fn, url)
    problems = preflight_problems(before, run_id, args.ledger, cfg)
    record = {"stage": name, "role": role, "url": url, "run_id": run_id, "pairs_asked": 0, "summary_before": before, "problems_before": problems, "ledger_before": spend,
              "code_sha256": code_fingerprint(cfg, args.config)}
    if problems:
        contract.append_jsonl(work / STAGES, [dict(record, outcome="refused before any call: " + "; ".join(problems), summary_after=before, problems_after=problems, ledger_after=spend)])
        raise PreflightFailed("the proxy at %s is not fit for the stage %s, nothing was sent: %s" % (url, name, "; ".join(problems)))
    take_baseline(work, cfg, spend, args.config)
    guard = StageGuard(args.ledger, cfg, run_id, spend)
    outcome, asked, blind = "completed", 0, None
    try:
        asked = todo(guard)
    except BaseException as exc:
        outcome = "stopped by %s: %s" % (type(exc).__name__, str(exc)[:300])
        raise
    finally:
        after = safe_summary(summary_fn, url)
        try:
            ledger_after = ledger_spend(args.ledger, cfg)
        except (OSError, ValueError):
            ledger_after = None
        delta = proxy_calls_delta(before, after)
        gained = None if ledger_after is None else ledger_after["runs"].get(run_id, {}).get("entries", 0) - spend["runs"].get(run_id, {}).get("entries", 0)
        if delta and delta > 0 and gained == 0:
            blind = "the proxy reports %d call(s) during the stage but the ledger gained no line of run id %s: the ledger path or the run id does not match the proxy" % (delta, run_id)
        tally = guard.tally
        if blind and outcome == "completed":
            outcome = "blind spend guard: " + blind
        record.update(pairs_asked=asked, outcome=outcome, summary_after=after,
                      problems_after=summary_problems(after), ledger_after=ledger_after, proxy_calls_delta=delta, ledger_run_entries_delta=gained,
                      recorded_calls=tally.get("calls", 0), format_failures=tally.get("failed", 0), replies=tally.get("replies", 0), rows_written=tally.get("rows", 0),
                      unrecorded_dropped=tally.get("dropped_unrecorded", 0))
        contract.append_jsonl(work / STAGES, [record])
    if blind:
        raise BudgetStop(blind)
    return record


# ------------------------------------------------------------------------------------------------- what must hold before a paid stage starts

def planned_sets(pairs: dict) -> Dict[str, set]:
    """The planned (i, j) pairs of pairs.json by kind of record."""
    return {"pos": {(int(i), int(j)) for i, j in pairs.get("positive", [])}, "neg": {(int(p[0]), int(p[1])) for p in pairs.get("negative", [])},
            "pool": {(int(i), int(j)) for i, js in pairs.get("pool", {}).items() for j in js}, "rep": {(int(i), int(j)) for i, j in pairs.get("repeat", [])}}


def coverage(records: Sequence[dict], kind: str, planned: set) -> dict:
    """The records of a kind against the planned pairs, as sets: planned pairs without a record, records of pairs that were not planned, records beyond the first of a pair."""
    got = [(r["i"], r["j"]) for r in records if r["kind"] == kind]
    seen = set(got)
    return {"expected": len(planned), "n": len(got), "missing": len(planned - seen), "unplanned": len(seen - planned), "duplicates": len(got) - len(seen),
            "complete": bool(planned) and seen == planned and len(got) == len(seen)}


def gate_controls_report(records: Sequence[dict], cfg: dict, pairs: Optional[dict] = None) -> dict:
    """The positive and the negative control of the judge: all planned pairs of pairs.json judged (as sets, no record missing, none foreign or repeated), at least the configured
    number of them, and the SAME counts. Without `pairs` the number of records is compared with the configured number instead."""
    g = cfg["judge"]["gate"]
    out: dict = {}
    for key, kind, need_n, test in (("positive", "pos", g["positive_control_n"], lambda s: s >= g["positive_control_min_same"]),
                                    ("negative", "neg", g["negative_control_n"], lambda s: s <= g["negative_control_max_same"])):
        rows = [r for r in records if r["kind"] == kind]
        same = sum(1 for r in rows if r["label"] == "SAME")
        if pairs is None:
            cov = {"expected": need_n, "n": len(rows), "missing": max(0, need_n - len(rows)), "unplanned": 0, "duplicates": 0, "complete": len(rows) >= need_n}
        else:
            cov = coverage(records, kind, planned_sets(pairs)[kind])
            cov["complete"] = cov["complete"] and cov["expected"] >= need_n
        out[key] = dict(cov, same=same, ok=cov["complete"] and test(same))
    out["ok"] = out["positive"]["ok"] and out["negative"]["ok"]
    return out


def gate_controls_ok(records: Sequence[dict], cfg: dict, pairs: Optional[dict] = None) -> bool:
    return gate_controls_report(records, cfg, pairs)["ok"]


def c4_status(work: Path) -> Tuple[str, str]:
    """('absent' | 'pass' | 'fail', detail) for the control C4 report that scripts/wmb/retrieval_c4.py writes (c4.json)."""
    path = Path(work) / "c4.json"
    if not path.exists():
        return "absent", ""
    try:
        report = read_json(path)
    except ValueError:
        return "fail", "c4.json is not valid JSON"
    needed = ("implementations_identical", "helps_at_zero_ok", "helps_rises_with_gain")
    failed = [k for k in needed if not (isinstance(report, dict) and report.get(k) is True)]
    return ("fail", "control C4 does not report a pass (%s)" % ", ".join(failed)) if failed else ("pass", "")


def refuse_or_warn(problems: List[str], args: argparse.Namespace) -> None:
    if not problems:
        return
    if args.continue_on_gate_failure:
        print("warning: --continue-on-gate-failure: continuing although " + "; ".join(problems), file=sys.stderr)
        return
    raise ControlsNotPassed("; ".join(problems) + " (--continue-on-gate-failure overrides)")


def require_free_controls(work: Path, cfg: dict, args: argparse.Namespace) -> None:
    """Before any paid stage: the free controls C1 to C3 that `prepare` stored in prep.json are all true, and C4 reports a pass when c4.json exists (a missing one warns)."""
    problems = []
    failed = sorted(k for k, ok in controls_pass(read_json(Path(work) / PREP)["controls"], cfg).items() if not ok)
    if failed:
        problems.append("the free control(s) %s failed" % ", ".join(failed))
    status, detail = c4_status(work)
    if status == "absent":
        print("warning: no c4.json in %s: control C4 (scripts/wmb/retrieval_c4.py) has not been run" % work, file=sys.stderr)
    elif status == "fail":
        problems.append(detail)
    refuse_or_warn(problems, args)


def require_gate_controls(work: Path, cfg: dict, args: argparse.Namespace) -> None:
    """Before every paid stage but the gate: the positive and the negative control of the judge have passed (the README rule 'the gate controls run before the pool')."""
    report = gate_controls_report(contract.load_jsonl(Path(work) / LABELS), cfg, read_json(Path(work) / PAIRS))
    if not report["ok"]:
        refuse_or_warn(["the judge's gate controls have not passed (positive: %d of %d planned judged, %d SAME; negative: %d of %d planned judged, %d SAME)" % (
            report["positive"]["n"], report["positive"]["expected"], report["positive"]["same"], report["negative"]["n"], report["negative"]["expected"], report["negative"]["same"])], args)


def check_inputs(args: argparse.Namespace, cfg: dict) -> Dict[str, str]:
    """The three input digests against config.json, before anything is read from them (--allow-input-mismatch: tests only)."""
    return {} if args.allow_input_mismatch else verify_inputs(cfg, args.notes, args.prep, args.persona)


def cmd_judge(args: argparse.Namespace, generate: Generate, summary_fn: SummaryFn) -> dict:
    cfg = load_config(args.config)
    check_inputs(args, cfg)
    items, briefs = load_inputs(args.notes, args.prep)
    work = Path(args.workdir)
    require_assistant_labels(work, items, briefs)
    ledger_spend(args.ledger, cfg)                                            # no ledger, no model call
    stages = ("gate", "repeat", "pool") if args.stage == "all" else (args.stage,)
    ran: dict = {}
    with workdir_lock(work, "judge"):
        require_free_controls(work, cfg, args)
        for stage in stages:
            if stage != "gate":
                require_gate_controls(work, cfg, args)
            pairs = judge_pairs(work, stage, cfg)
            run_stage(stage, args.judge_url, lambda guard, pairs=pairs: run_judge(pairs, items, briefs, cfg, generate, work / LABELS, args.workers, before_chunk=guard.before_chunk,
                                                                                  after_chunk=guard.after_chunk, tally=guard.tally), args, cfg, summary_fn, role="judge")
            ran[stage] = len(pairs)
            if stage == "gate" and args.stage == "all" and not args.continue_on_gate_failure and not gate_controls_ok(contract.load_jsonl(work / LABELS), cfg, read_json(work / PAIRS)):
                ran["stopped"] = "the positive or negative control failed: the pooled pairs were not judged (--continue-on-gate-failure overrides)"
                break
    return ran


def cmd_sample(args: argparse.Namespace) -> dict:
    """The stratified sample of the README: it needs every pooled pair judged (the same pairs from the same labels, whenever it runs) and never replaces a sample the assistant may
    have labelled."""
    cfg = load_config(args.config)
    check_inputs(args, cfg)
    items, briefs = load_inputs(args.notes, args.prep)
    work = Path(args.workdir)
    records = contract.load_jsonl(work / LABELS)
    pool = coverage(records, "pool", planned_sets(read_json(work / PAIRS))["pool"])
    if not pool["complete"]:
        raise ValueError("the pool is not completely judged (%d of %d planned pairs have no record, %d records are not planned or repeated): run `judge --stage pool` first" % (
            pool["missing"], pool["expected"], pool["unplanned"] + pool["duplicates"]))
    keys = read_json(work / DECISIVE_KEYS)
    chosen = stratified_sample(pool_label_table(records), {(k["i"], k["j"]) for k in keys.values()}, cfg)
    outputs = ((STRATIFIED, [{"key": "s%03d" % n, "brief": briefs[i], "note": items[j].text} for n, (i, j, _) in enumerate(chosen, 1)]),
               (STRATIFIED_KEYS, {"s%03d" % n: {"i": i, "j": j, "judge_label": lab} for n, (i, j, lab) in enumerate(chosen, 1)}))
    for name, content in outputs:
        if (work / name).exists() and read_json(work / name) != json.loads(json.dumps(content)):
            raise ValueError("%s exists and differs from the sample these labels give: the assistant's labels would attach to other pairs (delete the sample files on purpose to draw it again)" % name)
    for name, content in outputs:
        write_json(work / name, content)
    return {"pairs": len(chosen), "per_label": dict(Counter(lab for _, _, lab in chosen))}


# ----------------------------------------------------------------------------------------------------------------------------------- P1: the decision chain

BOOT_CHUNK = stats.CHUNK_DRAWS


def relevance_arrays(first: Dict[str, Sequence[int]], tasks: Sequence[int], labels: Dict[Tuple[int, int], Optional[str]], good: Sequence[str] = ("SAME",)) -> Dict[str, np.ndarray]:
    """Per method: is the first candidate of each task relevant (a pair absent from `labels`, or labelled None, is not)."""
    ok = set(good)
    return {m: np.array([bool(j >= 0 and labels.get((int(i), int(j))) in ok) for i, j in zip(tasks, js)], dtype=bool) for m, js in first.items()}


def tasks_with_same(labels: Dict[Tuple[int, int], Optional[str]]) -> int:
    return len({i for (i, _), lab in labels.items() if lab == "SAME"})


def hit_counts(counts: np.ndarray, order: np.ndarray, relw: np.ndarray, cuts: np.ndarray) -> np.ndarray:
    """Relevant fired copies per resample. counts (c, T): multiplicity of each task in each resample; order: the task positions best first (score, task number);
    relw (V, T): relevance (and finite score) of the task in rank slot k, per label variant; cuts (c, Q): how many copies fire. Copies of one task are identical
    (same score, same relevance), so which copy sits at the cut does not matter. Returns (V, c, Q)."""
    ranked = counts[:, order]
    cum = np.cumsum(ranked, axis=1)
    before = cum - ranked
    out = np.empty((relw.shape[0], counts.shape[0], cuts.shape[1]), dtype=np.int64)
    for k in range(cuts.shape[1]):
        cut = cuts[:, k: k + 1]
        fired = np.minimum(cum, cut) - np.minimum(before, cut)
        out[:, :, k] = np.rint(fired @ relw.T).astype(np.int64).T
    return out


def bootstrap_hit_differences(arms: Dict[str, Tuple[np.ndarray, np.ndarray]], contrasts: Sequence[Tuple[str, str]], qs: Sequence[float], seed: int, draws: int,
                              day_of_task: Optional[np.ndarray] = None, n_days: int = 0, chunk: int = BOOT_CHUNK) -> dict:
    """hits(A) - hits(B) at each fraction in `qs`, for each contrast, label variant and resample, the fire sets recomputed inside every resample. The task bootstrap
    resamples the T tasks (stats.bootstrap_indices(T, draws, seed)); the day-block bootstrap resamples the days (stats.bootstrap_indices(n_days, draws, seed)) and takes
    all tasks of a picked day, the cut at ceil(q * size of the resample). Returns {"full": (C, V, Q), "task": (C, V, draws, Q), "day": same or None}."""
    names = sorted({m for pair in contrasts for m in pair})
    any_arm = arms[names[0]]
    T, V, Q = len(any_arm[0]), any_arm[1].shape[0], len(qs)

    def diffs(counts: np.ndarray, cuts: np.ndarray) -> np.ndarray:
        hits = {m: hit_counts(counts, arms[m][0], arms[m][1], cuts) for m in names}
        return np.stack([hits[a] - hits[b] for a, b in contrasts])

    full = diffs(np.ones((1, T), dtype=np.int64), np.array([[stats.fire_size(q, T) for q in qs]], dtype=np.int64))[:, :, 0, :]
    task = np.empty((len(contrasts), V, draws, Q), dtype=np.int32)
    row = 0
    for block in stats.bootstrap_chunks(T, draws, seed, chunk):
        cuts = np.tile(np.array([[stats.fire_size(q, T) for q in qs]], dtype=np.int64), (len(block), 1))
        task[:, :, row: row + len(block), :] = diffs(stats.multiplicity(block, T), cuts)
        row += len(block)
    day = None
    if day_of_task is not None:
        day = np.empty_like(task)
        row = 0
        for block in stats.bootstrap_chunks(n_days, draws, seed, chunk):
            counts = stats.multiplicity(block, n_days)[:, day_of_task]
            size = counts.sum(axis=1)
            sizes, back = np.unique(size, return_inverse=True)
            cuts = np.stack([np.array([stats.fire_size(q, int(s)) for s in sizes], dtype=np.int64)[back] for q in qs], axis=1)
            day[:, :, row: row + len(block), :] = diffs(counts, cuts)
            row += len(block)
    return {"full": full, "task": task, "day": day}


def interval_report(res: dict, c: int, v: int, qi: int, alpha: float) -> dict:
    """d, and the interval: the wider of the task-bootstrap and the day-block interval at each end."""
    t_lo, t_hi = stats.interval_of(res["task"][c, v, :, qi], alpha)
    d_lo, d_hi = stats.interval_of(res["day"][c, v, :, qi], alpha) if res["day"] is not None else (t_lo, t_hi)
    return {"d": int(res["full"][c, v, qi]), "lo": float(min(t_lo, d_lo)), "hi": float(max(t_hi, d_hi)), "task_lo": float(t_lo), "task_hi": float(t_hi), "day_lo": float(d_lo),
            "day_hi": float(d_hi)}


def mean_interval_report(res: dict, c: int, v: int, alpha: float) -> dict:
    """The same for the mean over the fractions (D_bar): integer sums are sorted, then divided."""
    q_n = res["full"].shape[2]
    t_lo, t_hi = stats.interval_of(res["task"][c, v].sum(axis=-1), alpha)
    d_lo, d_hi = stats.interval_of(res["day"][c, v].sum(axis=-1), alpha) if res["day"] is not None else (t_lo, t_hi)
    return {"d": float(res["full"][c, v].sum() / q_n), "lo": min(t_lo, d_lo) / q_n, "hi": max(t_hi, d_hi) / q_n, "task_lo": t_lo / q_n, "task_hi": t_hi / q_n, "day_lo": d_lo / q_n,
            "day_hi": d_hi / q_n}


def base_verdict(d_emb: dict, d_hyb: dict, margin: float) -> str:
    if d_emb["lo"] > 0 and d_emb["d"] >= margin:
        return HELPS
    if d_emb["hi"] < margin and d_hyb["hi"] < margin:
        return SUFFICIENT
    return UNRESOLVED


def resolve_verdict(by_seed: Sequence[str], prevalence_ok: bool) -> str:
    if not prevalence_ok:
        return "NOT_EVALUABLE (prevalence)"
    return by_seed[0] if len(set(by_seed)) == 1 else "UNRESOLVED (resampling boundary)"


def make_arms(scores: Dict[str, np.ndarray], tasks: Sequence[int], rels: Sequence[Dict[str, np.ndarray]], methods: Iterable[str]) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    arms = {}
    for m in methods:
        order, finite = fire_order(scores[m], tasks), np.isfinite(scores[m])
        arms[m] = (order, np.stack([(rel[m] & finite)[order].astype(float) for rel in rels]))
    return arms


def p1_readings(scores: Dict[str, Sequence[float]], first: Dict[str, Sequence[int]], days: Sequence[str], tasks: Sequence[int], labels: Dict[Tuple[int, int], Optional[str]],
                cfg: dict, assistant_labels: Optional[Dict[Tuple[int, int], Optional[str]]] = None, draws: Optional[int] = None) -> dict:
    """The primary reading of part U1 (README: Readings). Strict relevance (`SAME`). Fire sets: ceil(round(q * n, 9)) tasks of a multiset of n tasks fire, the highest
    scores, ties by task number then position in the resample, -inf never. D_emb and D_hyb at primary_q with the paired task bootstrap and the day-block bootstrap
    (interval = the wider at each end); the verdict is recomputed with the stability seeds and `draws` (default draws_primary) applies to every seed. With
    assistant_labels the pairs they hold replace the judge's labels in a second evaluation; a differing verdict is `UNRESOLVED (labels)`."""
    spec = cfg["readings"]
    boot, q0, margin = spec["bootstrap"], spec["primary_q"], spec["margin_tasks"]
    n_draws = int(draws) if draws is not None else int(boot["draws_primary"])
    s = {m: np.asarray(v, dtype=float) for m, v in scores.items()}
    names, day_of_task = stats.day_groups(days)
    merged = dict(labels)
    if assistant_labels is not None:
        merged.update(assistant_labels)
    variants = [labels] + ([merged] if assistant_labels is not None else [])
    rels = [relevance_arrays(first, tasks, lab) for lab in variants]
    arms = make_arms(s, tasks, rels, TRIO)
    seeds = [boot["seed"]] + list(boot["stability_seeds"])
    verdicts: List[List[str]] = [[] for _ in variants]
    primary: List[Tuple[dict, dict]] = []
    for k, seed in enumerate(seeds):
        res = bootstrap_hit_differences(arms, CONTRASTS, [q0], seed, n_draws, day_of_task, len(names))
        for v in range(len(variants)):
            d_emb, d_hyb = interval_report(res, 0, v, 0, boot["alpha"]), interval_report(res, 1, v, 0, boot["alpha"])
            verdicts[v].append(base_verdict(d_emb, d_hyb, margin))
            if k == 0:
                primary.append((d_emb, d_hyb))
    rule = cfg["judge"]["prevalence_rule_min_tasks_with_same"]
    same_n = tasks_with_same(labels)
    verdict_judge = resolve_verdict(verdicts[0], same_n >= rule)
    verdict_assistant = resolve_verdict(verdicts[1], tasks_with_same(merged) >= rule) if assistant_labels is not None else None
    verdict = verdict_judge
    if assistant_labels is not None and verdict_assistant != verdict_judge and verdict_judge in BASE_VERDICTS:
        verdict = "UNRESOLVED (labels)"
    d_emb, d_hyb = primary[0]
    return {"tasks_with_same": same_n, "prevalence_ok": same_n >= rule, "hits": {m: hit_table(s[m], rels[0][m], tasks, spec["sweep"]) for m in s},
            "d_emb": d_emb, "d_hyb": d_hyb, "verdict_by_seed": {str(seed): verdicts[0][k] for k, seed in enumerate(seeds)}, "verdict_judge": verdict_judge,
            "verdict_assistant": verdict_assistant, "verdict": verdict,
            "fusion_flag": "refit_channel_weights" if verdict == HELPS and d_hyb["d"] < d_emb["d"] / 2 else None}


def secondary_readings(scores: Dict[str, Sequence[float]], first: Dict[str, Sequence[int]], days: Sequence[str], tasks: Sequence[int], labels: Dict[Tuple[int, int], Optional[str]],
                       cfg: dict, draws: Optional[int] = None) -> dict:
    """Descriptive, unadjusted intervals (draws_other draws, the same stream and seed): every method against LEX_KERNEL at each q of the sweep, under strict and lenient
    relevance; D_bar over the grid for EMB_MINILM and HYB_KERNEL. D_hyb at q = 0.10 is not read (identical fire sets: zero by construction)."""
    spec = cfg["readings"]
    boot = spec["bootstrap"]
    n_draws = int(draws) if draws is not None else int(boot["draws_other"])
    s = {m: np.asarray(v, dtype=float) for m, v in scores.items()}
    names, day_of_task = stats.day_groups(days)
    modes = list(GOOD)
    rels = [relevance_arrays(first, tasks, labels, GOOD[mode]) for mode in modes]
    others = [m for m in s if m != "LEX_KERNEL"]
    arms = make_arms(s, tasks, rels, list(s))
    out: dict = {"draws": n_draws, "differences": {mode: {} for mode in modes}, "d_bar": {mode: {} for mode in modes}, "d_bar_grid": spec["d_bar_grid"]}
    contrasts = [(m, "LEX_KERNEL") for m in others]
    res = bootstrap_hit_differences(arms, contrasts, spec["sweep"], boot["seed"], n_draws, day_of_task, len(names))
    for v, mode in enumerate(modes):
        for c, (a, b) in enumerate(contrasts):
            out["differences"][mode]["%s-%s" % (a, b)] = {str(q): interval_report(res, c, v, qi, boot["alpha"]) for qi, q in enumerate(spec["sweep"])
                                                          if not (a == "HYB_KERNEL" and q == min(spec["sweep"]))}
    bar = [(m, "LEX_KERNEL") for m in ("EMB_MINILM", "HYB_KERNEL") if m in s]
    res = bootstrap_hit_differences(arms, bar, spec["d_bar_grid"], boot["seed"], n_draws, day_of_task, len(names))
    for v, mode in enumerate(modes):
        for c, (a, b) in enumerate(bar):
            out["d_bar"][mode]["%s-%s" % (a, b)] = mean_interval_report(res, c, v, boot["alpha"])
    return out


def operating_point(scores: Sequence[float], relevant: np.ndarray, tasks: Sequence[int], bar: float = 0.8, step: float = 0.02, grid: int = 50) -> Optional[dict]:
    """The largest q on the grid at which the cumulative precision of the first candidates of the fired tasks is at least `bar`, and its coverage (fired / T)."""
    best = None
    for k in range(1, grid + 1):
        q = round(k * step, 2)
        take = fire_positions(scores, tasks, q)
        if len(take) and int(np.asarray(relevant, dtype=bool)[take].sum()) / len(take) >= bar:
            best = {"q": q, "fired": int(len(take)), "hits": int(np.asarray(relevant, dtype=bool)[take].sum()), "coverage": len(take) / len(scores)}
    return best


def permutation_reference(scores: Dict[str, List[float]], first: Dict[str, List[int]], tasks: Sequence[int], pool: Dict[str, List[int]],
                          labels: Dict[Tuple[int, int], Optional[str]], cfg: dict) -> dict:
    """Labels permuted within each task's pool; D_emb at the primary q and its analytic mean: sum over tasks of the share of relevant pooled pairs times the difference of
    the two methods' first-candidate fire indicators. A reference, not a criterion."""
    spec = cfg["readings"]
    a, b = CONTRASTS[0]
    fa, fb = (set(fire_positions(scores[m], tasks, spec["primary_q"]).tolist()) for m in (a, b))
    where = {int(i): t for t, i in enumerate(tasks)}
    share = {i: (sum(1 for j in pool[str(i)] if labels.get((i, j)) == "SAME") / len(pool[str(i)])) if pool[str(i)] else 0.0 for i in tasks}
    analytic = sum(share[i] * ((where[i] in fa) - (where[i] in fb)) for i in tasks)
    rng, values = random.Random(cfg["seeds"]["c4_shuffle"]), []
    for _ in range(spec["shuffle_draws"]):
        flags: Dict[Tuple[int, int], bool] = {}
        for i in tasks:
            js = pool[str(i)]
            marks = [labels.get((i, j)) == "SAME" for j in js]
            rng.shuffle(marks)
            flags.update({(i, j): m for j, m in zip(js, marks)})
        values.append(sum(1 for t in fa if flags.get((tasks[t], first[a][t]), False)) - sum(1 for t in fb if flags.get((tasks[t], first[b][t]), False)))
    return {"draws": len(values), "mean_d": float(np.mean(values)), "sd_d": float(np.std(values)), "min_d": int(min(values)), "max_d": int(max(values)),
            "analytic_mean_d": float(analytic)}


# ------------------------------------------------------------------------------------------------------------------------------------ the judge gate

def pool_label_table(records: Sequence[dict], kind: str = "pool") -> Dict[Tuple[int, int], Optional[str]]:
    return {(r["i"], r["j"]): r["label"] for r in records if r["kind"] == kind}


def decisive_audit(first_pass: Dict[Tuple[int, int], Optional[str]], keys: Dict[str, dict], assistant: Dict[str, str], minimum: float) -> dict:
    """Agreement of the judge with the assistant on SAME versus not-SAME over the decisive pairs; a pair without a valid judge label counts as a disagreement. Wilson 95%
    intervals per origin (reported, not gated)."""
    rows = []
    for key, info in sorted(keys.items()):
        judge, mine = first_pass.get((info["i"], info["j"])), assistant.get(key)
        rows.append((info["origin"], judge, mine, judge is not None and mine in SCALE and (judge == "SAME") == (mine == "SAME")))
    n, agree = len(rows), sum(1 for r in rows if r[3])
    by_origin = {}
    for origin in sorted({r[0] for r in rows}):
        sub = [r for r in rows if r[0] == origin]
        k = sum(1 for r in sub if r[3])
        lo, hi = stats.wilson(k, len(sub))
        by_origin[origin] = {"n": len(sub), "agree": k, "agreement": k / len(sub), "wilson_lo": lo, "wilson_hi": hi}
    complete = n > 0 and all(r[2] in SCALE for r in rows)
    return {"n": n, "agree": agree, "agreement": agree / n if n else None, "min_agreement": minimum, "complete": complete, "by_origin": by_origin,
            "without_valid_judge_label": sum(1 for r in rows if r[1] is None), "pass": complete and n > 0 and agree / n >= minimum}


def judge_gate_report(records: Sequence[dict], cfg: dict, pairs: dict, keys: Dict[str, dict], assistant: Dict[str, str]) -> dict:
    """Gate checks 1 to 5 of the README. Every check also requires that the calls it rests on were made: the controls and the pool are complete when the SET of their records
    is the set of the planned pairs of pairs.json (no planned pair without a record, no foreign or repeated record), not when a count is reached."""
    g = cfg["judge"]["gate"]
    kinds = {k: [r for r in records if r["kind"] == k] for k in ("pos", "neg", "pool", "rep")}
    neg = kinds["neg"]
    planned = planned_sets(pairs)
    controls = gate_controls_report(records, cfg, pairs)

    def block(name: str, extra: dict) -> dict:
        found = dict(controls[name])
        ok = found.pop("ok")
        return dict(found, **extra, **{"pass": ok})

    positive = block("positive", {"min_same": g["positive_control_min_same"]})
    strata = {}
    for name in ("random", "hard"):
        sub = [r for r in neg if r.get("stratum") == name]
        strata[name] = {"n": len(sub), "unrelated": sum(1 for r in sub if r["label"] == "UNRELATED"), "unrelated_share": (sum(1 for r in sub if r["label"] == "UNRELATED") / len(sub)) if sub else None}
    negative = block("negative", {"max_same": g["negative_control_max_same"], "strata": strata,
                                  "e3a_reference_unrelated_share_of_230_random_pairs": {"first_scale": 0.709, "second_scale": 0.817, "required": 0.90}})
    first, again_all = pool_label_table(records), pool_label_table(records, "rep")
    wanted = planned["rep"]
    again = {k: v for k, v in again_all.items() if k in wanted}
    both = [k for k in again if k in first]
    was_same = [k for k in both if first[k] == "SAME"]
    persisted = sum(1 for k in was_same if again[k] == "SAME")
    valid = [k for k in both if first[k] and again[k]]
    persistence = persisted / len(was_same) if was_same else None
    repeat = {"expected": len(wanted), "n": len(both), "unplanned": len(set(again_all) - wanted), "first_pass_same": len(was_same), "same_again": persisted, "persistence": persistence,
              "min_persistence": g["repeat_min_same_persistence"], "identical_three_way_share": (sum(1 for k in valid if first[k] == again[k]) / len(valid)) if valid else None,
              "kappa_same_vs_not_same": stats.cohen_kappa([first[k] == "SAME" for k in both], [again[k] == "SAME" for k in both]) if both else None,
              "pass": bool(wanted) and wanted <= set(again) and persistence is not None and persistence >= g["repeat_min_same_persistence"]}
    audit = decisive_audit(first, keys, assistant, g["decisive_audit_min_agreement"])
    calls = sum(r.get("calls", 1) for r in records)
    failed = sum(len(r.get("failures", [])) for r in records)
    classes = Counter(c for r in records for c in r.get("failures", []))
    fmt = {"calls": calls, "format_failures": failed, "share": failed / calls if calls else None, "max_share": g["format_failure_max"], "by_class": dict(sorted(classes.items())),
           "pairs_without_valid_label": sorted([r["kind"], r["i"], r["j"]] for r in records if r["label"] is None), "pass": calls > 0 and failed / calls <= g["format_failure_max"]}
    pool = coverage(records, "pool", planned["pool"])
    pool["pass"] = pool.pop("complete")
    checks = {"positive_control": positive["pass"], "negative_control": negative["pass"], "perturbed_repeat": repeat["pass"], "decisive_audit": audit["pass"], "format_failures": fmt["pass"],
              "pool_complete": pool["pass"]}
    return {"positive": positive, "negative": negative, "repeat": repeat, "decisive_audit": audit, "format": fmt, "pool": pool, "checks": checks, "passes": all(checks.values())}


def audited_labels(keys: Dict[str, dict], assistant: Dict[str, str]) -> Dict[Tuple[int, int], str]:
    return {(info["i"], info["j"]): assistant[key] for key, info in keys.items() if assistant.get(key) in SCALE}


# --------------------------------------------------------------------------------------------------------------------------------------- U3 and U2

class StaticCollection:
    """A collection queried without a time limit (parts U2 and U3): the five methods over the same documents, the kernel driven through the same permissive profiles."""

    def __init__(self, texts: Sequence[str], origins: Sequence[str], times: Sequence[str], vectors: np.ndarray, cfg: dict, tau_lex: float, tau_emb: float) -> None:
        self.cfg, self.tau_lex, self.tau_emb = cfg, tau_lex, tau_emb
        self.n = len(texts)
        self.stems = [mk.tokens(t) for t in texts]
        self.corpus = Corpus(range(self.n), self.stems, vectors)
        self.cache: Dict[str, np.ndarray] = {}
        kitems = [mk.Item(note_id(j), "note" if origins[j] == "account_history" else "event", origins[j], times[j], texts[j]) for j in range(self.n)]
        self.index = mk.build_index(kitems, "9999-01-01", lambda batch: [self.cache[t].tolist() for t in batch], {note_id(j): vectors[j].tolist() for j in range(self.n)})

    def rank(self, query: str, vector: np.ndarray, task_type: str) -> Dict[str, List[Tuple[int, float]]]:
        self.cache[query] = vector
        out = base_rankings(self.corpus, self.index, query, vector, "9999-01-01", self.cfg["bm25"], task_type)
        out["HYB_KERNEL"] = kernel_ranking(self.index, query, "9999-01-01", hybrid_profile(self.tau_lex, self.tau_emb), task_type)
        return {m: out[m] for m in METHODS}


def gold_rank(ranking: Sequence[Tuple[int, float]], gold: set) -> Optional[int]:
    """1-based position of the first gold document, None when it is not among the candidates."""
    for position, (j, _) in enumerate(ranking, 1):
        if j in gold:
            return position
    return None


def recall_at(ranks: Sequence[Optional[int]], k: int) -> Optional[float]:
    return sum(1 for r in ranks if r is not None and r <= k) / len(ranks) if ranks else None


def reciprocal_rank(ranks: Sequence[Optional[int]]) -> Optional[float]:
    return sum(1.0 / r for r in ranks if r) / len(ranks) if ranks else None


def question_overlap(question: str, note: str) -> float:
    """Share of the question's distinct content stems that occur in the note."""
    q, n = set(mk.tokens(question)), set(mk.tokens(note))
    return len(q & n) / len(q) if q else 0.0


def sample_u3_notes(items: Sequence[sbm.Item], cfg: dict) -> List[int]:
    """Per length tercile (words) of all notes, `per_length_tercile` notes drawn by seed."""
    spec = cfg["u3"]
    order = sorted(range(len(items)), key=lambda j: (len(items[j].text.split()), j))
    third = len(order) // 3
    groups = [order[:third], order[third:2 * third], order[2 * third:]]
    rng = random.Random(spec["seed"])
    return sorted(j for g in groups for j in rng.sample(g, spec["per_length_tercile"]))


def key_pattern(key: str) -> "re.Pattern[str]":
    return re.compile(r"(?<!\w)" + re.escape(key) + r"(?!\w)", re.I)


def persona_gold(persona: dict) -> List[set]:
    """For every fact question the biography items (by position) that contain one of its keys as a whole word, case-insensitively."""
    bio = persona["biography"]
    return [{j for j, b in enumerate(bio) if any(key_pattern(k).search(b["text"]) for k in q["keys"])} for q in persona["fact_questions"]]


def tercile_slices(values: Sequence[float], keys: Optional[Sequence[int]] = None) -> List[List[int]]:
    """Positions sorted by (value, key), cut into floor(n/3), floor(n/3) and the rest; the lowest tercile is the first."""
    order = sorted(range(len(values)), key=lambda k: (values[k], keys[k] if keys is not None else k))
    third = len(order) // 3
    return [order[:third], order[third:2 * third], order[2 * third:]]


def ranking_metrics(ranks: Dict[str, List[Optional[int]]], at: Sequence[int]) -> dict:
    return {m: dict({"recall@%d" % k: recall_at(r, k) for k in at}, mrr=reciprocal_rank(r), n=len(r)) for m, r in ranks.items()}


def mean_difference_interval(a: Sequence[int], b: Sequence[int], draws: int, seed: int, alpha: float = 0.05) -> Optional[dict]:
    """Mean of a - b over questions with the README interval of a paired bootstrap on the splitmix stream; integer sums are sorted, then divided by n."""
    d = np.asarray(a, dtype=np.int64) - np.asarray(b, dtype=np.int64)
    n = len(d)
    if n == 0:
        return None
    sums = np.empty(draws, dtype=np.int64)
    row = 0
    for block in stats.bootstrap_chunks(n, draws, seed):
        sums[row: row + len(block)] = d[block].sum(axis=1)
        row += len(block)
    lo, hi = stats.interval_of(sums, alpha)
    return {"d": float(d.sum() / n), "lo": lo / n, "hi": hi / n, "n": n}


def verdict_p2(result: Optional[dict], margin: float) -> str:
    """`EMBEDDER_RESCUES` when the lower bound is above 0 and D3 >= margin; otherwise 'not EMBEDDER_RESCUES' (there is no NO_RESCUE verdict)."""
    return "EMBEDDER_RESCUES" if result and result["lo"] > 0 and result["d"] >= margin else "not EMBEDDER_RESCUES"


def question_prompt(cfg: dict, note: str) -> str:
    return cfg["u3"]["writer"]["user_template"].format(note=note)


def answer_prompt(cfg: dict, note: str, question: str) -> str:
    return cfg["u3"]["answerability"]["user_template"].format(note=note, question=question)


def answer_options(cfg: dict) -> dict:
    a = cfg["u3"]["answerability"]
    return {"temperature": a["temperature"], "num_predict": a["max_tokens"]}


def digest_if_present(path: Path) -> Optional[str]:
    return contract.sha256_file(path) if Path(path).exists() else None


def cmd_questions(args: argparse.Namespace, writer: Generate, judge: Generate, summary_fn: SummaryFn) -> dict:
    """Part U3: the paraphrased questions (writer proxy), then their answerability check (judge proxy). Both stages hold the results that got no reply at all and write them
    only after a later success, so a proxy outage leaves nothing behind and a resume asks the missing ones; the command reports how many questions are empty and how many
    answers have no label."""
    cfg = load_config(args.config)
    check_inputs(args, cfg)
    items, briefs = load_inputs(args.notes, args.prep)
    work = Path(args.workdir)
    require_assistant_labels(work, items, briefs)
    ledger_spend(args.ledger, cfg)                                            # no ledger, no model call
    spec = cfg["u3"]
    w, a = spec["writer"], spec["answerability"]
    with workdir_lock(work, "questions"):
        require_free_controls(work, cfg, args)
        require_gate_controls(work, cfg, args)

        def generate_questions(guard: StageGuard) -> int:
            have = {r["k"] for r in contract.load_jsonl(work / QUESTIONS)}
            todo = [k for k in sample_u3_notes(items, cfg) if k not in have]

            def ask(k: int) -> Tuple[dict, dict]:
                reply = call_text(writer, w["system"], question_prompt(cfg, items[k].text), w["seed"], {"temperature": w["temperature"], "num_predict": w["max_tokens"]})
                lines = [x.strip() for x in reply["text"].splitlines() if x.strip()]
                return {"k": k, "question": lines[0] if lines else "", "failures": reply["failures"]}, text_info(reply, bool(lines))

            return record_results(todo, ask, work / QUESTIONS, args.workers, guard.before_chunk, 100, guard.after_chunk, guard.tally, keep_errors=False)

        def check_answers(guard: StageGuard) -> int:
            done = {r["k"] for r in contract.load_jsonl(work / ANSWERS)}
            todo = [r for r in contract.load_jsonl(work / QUESTIONS) if r["k"] not in done and r["question"]]

            def ask(row: dict) -> Tuple[dict, dict]:
                result = call_choice(judge, a["system"], answer_prompt(cfg, items[row["k"]].text, row["question"]), a["seed"], answer_options(cfg), ("YES", "NO"))
                return {"k": row["k"], "answer": result["label"], "raw": result["raw"], "failures": result["failures"], "calls": result["calls"]}, choice_info(result)

            return record_results(todo, ask, work / ANSWERS, args.workers, guard.before_chunk, 100, guard.after_chunk, guard.tally, keep_errors=False)

        run_stage("questions", args.writer_url, generate_questions, args, cfg, summary_fn, role="writer")
        run_stage("answerability", args.judge_url, check_answers, args, cfg, summary_fn, role="judge")
        questions, answers = contract.load_jsonl(work / QUESTIONS), contract.load_jsonl(work / ANSWERS)
        out = {"questions": len(questions), "expected_questions": spec["questions"], "checked": len(answers), "empty_questions": sum(1 for q in questions if not q["question"]),
               "answers_without_label": sum(1 for r in answers if r["answer"] is None)}
        for name in (QUESTIONS, ANSWERS):
            out[name + "_sha256"] = digest_if_present(work / name)
    return out


def retained_questions(questions: Sequence[dict], answers: Sequence[dict]) -> Tuple[List[dict], dict]:
    """The questions with an answerability YES, ordered by note index; the gate (at least min_yes of all questions) and the count dropped."""
    said = {r["k"]: r["answer"] for r in answers}
    kept = sorted((q for q in questions if q["question"] and said.get(q["k"]) == "YES"), key=lambda q: q["k"])
    yes = sum(1 for q in questions if q["question"] and said.get(q["k"]) == "YES")
    return kept, {"questions": len(questions), "retained": len(kept), "dropped": len(questions) - len(kept), "answerable_share": yes / len(questions) if questions else None}


def u3_rankings(items: Sequence[sbm.Item], note_vectors: np.ndarray, kept: Sequence[dict], embed: Callable, cfg: dict, tau_lex: float, tau_emb: float) -> List[Dict[str, List[Tuple[int, float]]]]:
    coll = StaticCollection([it.text for it in items], ["account_history"] * len(items), synthetic_times(items), note_vectors, cfg, tau_lex, tau_emb)
    vectors = embed([q["question"] for q in kept])
    return [coll.rank(q["question"], v, "note") for q, v in zip(kept, vectors)]


def audit_targets(kept: Sequence[dict], low: Sequence[int], rankings: Sequence[dict], cfg: dict) -> List[dict]:
    """For the lowest-tercile questions and EMB_MINILM and LEX_KERNEL: each of the first three candidates that is not the source note (distinct pairs, at most the cap)."""
    seen, out = set(), []
    for pos in low:
        for m in ("EMB_MINILM", "LEX_KERNEL"):
            for j, _ in rankings[pos][m][:3]:
                if j != kept[pos]["k"] and (kept[pos]["k"], j) not in seen:
                    seen.add((kept[pos]["k"], j))
                    out.append({"k": kept[pos]["k"], "j": j})
    return out[: cfg["u3"]["audit_retrieved_max_calls"]]


def low_tercile(kept: Sequence[dict], items: Sequence[sbm.Item]) -> Tuple[List[float], List[List[int]]]:
    overlap = [question_overlap(q["question"], items[q["k"]].text) for q in kept]
    return overlap, tercile_slices(overlap, [q["k"] for q in kept])


def cmd_audit(args: argparse.Namespace, embed: Callable, judge: Generate, summary_fn: SummaryFn) -> dict:
    cfg = load_config(args.config)
    check_inputs(args, cfg)
    items, briefs = load_inputs(args.notes, args.prep)
    work = Path(args.workdir)
    prep = read_json(work / PREP)
    questions = contract.load_jsonl(work / QUESTIONS)
    kept, info = retained_questions(questions, contract.load_jsonl(work / ANSWERS))
    if not info["answerable_share"] or info["answerable_share"] < cfg["u3"]["answerability"]["min_yes"] or len(questions) != cfg["u3"]["questions"]:
        return {"audited": 0, "note": "the answerability gate failed or the question set is not the planned %d questions: P2 is not issued, nothing to audit" % cfg["u3"]["questions"]}
    require_assistant_labels(work, items, briefs)
    ledger_spend(args.ledger, cfg)                                            # no ledger, no model call
    with np.load(work / VECTORS) as z:
        notes = z["notes"]
    rankings = u3_rankings(items, notes, kept, embed, cfg, prep["tau_lex"], prep["tau_emb"])
    targets = audit_targets(kept, low_tercile(kept, items)[1][0], rankings, cfg)
    a = cfg["u3"]["answerability"]
    with workdir_lock(work, "audit"):
        require_free_controls(work, cfg, args)
        require_gate_controls(work, cfg, args)

        def audit(guard: StageGuard) -> int:
            done = {(r["k"], r["j"]) for r in contract.load_jsonl(work / AUDIT)}
            todo = [t for t in targets if (t["k"], t["j"]) not in done]
            question = {q["k"]: q["question"] for q in kept}

            def ask(t: dict) -> Tuple[dict, dict]:
                result = call_choice(judge, a["system"], answer_prompt(cfg, items[t["j"]].text, question[t["k"]]), a["seed"], answer_options(cfg), ("YES", "NO"))
                return {"k": t["k"], "j": t["j"], "answer": result["label"], "raw": result["raw"], "failures": result["failures"], "calls": result["calls"]}, choice_info(result)

            return record_results(todo, ask, work / AUDIT, args.workers, guard.before_chunk, 100, guard.after_chunk, guard.tally, keep_errors=False)

        run_stage("audit", args.judge_url, audit, args, cfg, summary_fn, role="judge")
        rows = contract.load_jsonl(work / AUDIT)
    return {"targets": len(targets), "audited": len(rows), "answers_without_label": sum(1 for r in rows if r["answer"] is None), AUDIT + "_sha256": digest_if_present(work / AUDIT)}


def u3_report(items: Sequence[sbm.Item], note_vectors: np.ndarray, questions: Sequence[dict], answers: Sequence[dict], audit_rows: Sequence[dict], embed: Callable,
              cfg: dict, tau_lex: float, tau_emb: float) -> dict:
    spec, boot = cfg["u3"], cfg["readings"]["bootstrap"]
    kept, info = retained_questions(questions, answers)
    complete = len(questions) == spec["questions"]                            # P2 rests on the planned set of questions (40 per length tercile), not on whatever was generated
    gate = info["answerable_share"] is not None and info["answerable_share"] >= spec["answerability"]["min_yes"] and complete
    report: dict = dict(info, answerability_gate_passes=gate, questions_expected=spec["questions"], questions_complete=complete)
    if len(kept) < 3:
        return report
    rankings = u3_rankings(items, note_vectors, kept, embed, cfg, tau_lex, tau_emb)
    ranks = {m: [gold_rank(r[m], {q["k"]}) for q, r in zip(kept, rankings)] for m in METHODS}
    overlap, terciles = low_tercile(kept, items)
    low = terciles[0]
    report.update({"overall": ranking_metrics(ranks, spec["recall_at"]), "overlap_cut_points": [overlap[t[-1]] for t in terciles[:2] if t],
                   "by_overlap_tercile": {name: ranking_metrics({m: [ranks[m][k] for k in t] for m in METHODS}, spec["recall_at"]) for name, t in zip(("low", "middle", "high"), terciles)},
                   "note": "gold = the source note; another note may also answer a question (see recall_any@3 when the audit has run)"})

    def top3(m: str, k: int) -> int:
        return 1 if (ranks[m][k] or 10 ** 9) <= 3 else 0

    d3 = {name: mean_difference_interval([top3(a, k) for k in low], [top3("LEX_KERNEL", k) for k in low], spec["p2"]["bootstrap_draws"], boot["seed"], boot["alpha"])
          for name, a in (("d3_emb", "EMB_MINILM"), ("d3_hyb", "HYB_KERNEL"))}
    report["p2"] = dict(d3, tercile_questions=len(low), verdict=verdict_p2(d3["d3_emb"], spec["p2"]["margin_rescue"]) if gate else None,
                        issued=gate)
    if audit_rows:
        yes = {(r["k"], r["j"]) for r in audit_rows if r["answer"] == "YES"}
        have = {(r["k"], r["j"]) for r in audit_rows}
        wanted = audit_targets(kept, low, rankings, cfg)
        any3 = {}
        for m in ("EMB_MINILM", "LEX_KERNEL"):
            got = sum(1 for k in low if top3(m, k) or any((kept[k]["k"], j) in yes for j, _ in rankings[k][m][:3] if j != kept[k]["k"]))
            any3[m] = got / len(low)
        report["recall_any_at_3"] = dict(any3, audited_pairs=len(have), planned_pairs=len(wanted), complete={(t["k"], t["j"]) for t in wanted} <= have)
    return report


def names_arm_note(ranks: Dict[str, List[Optional[int]]], scored: int) -> Optional[str]:
    """The name channel is an arm of U2 only if it changes something: when KERNEL_NAMES has the same gold rank as HYB_KERNEL on every scored question, the arm says nothing."""
    if ranks["KERNEL_NAMES"] == ranks["HYB_KERNEL"]:
        return ("the name channel changed the gold rank of none of the %d scored questions: KERNEL_NAMES equals HYB_KERNEL, so this arm says nothing about the name problem on this persona"
                % scored)
    return None


def u2_report(items: Sequence[sbm.Item], note_vectors: np.ndarray, persona: dict, embed: Callable, cfg: dict, tau_lex: float, tau_emb: float) -> dict:
    bio = persona["biography"]
    texts = [b["text"] for b in bio] + [it.text for it in items]
    vectors = np.vstack([embed([b["text"] for b in bio]), note_vectors])
    times = [str(b["date"]) for b in bio] + synthetic_times(items)
    coll = StaticCollection(texts, ["fiction_autobio"] * len(bio) + ["account_history"] * len(items), times, vectors, cfg, tau_lex, tau_emb)
    gold = persona_gold(persona)
    names_profile = dict(hybrid_profile(tau_lex, tau_emb), names=True, name="r1-names")
    methods = list(METHODS) + ["KERNEL_NAMES"]
    ranks: Dict[str, List[Optional[int]]] = {m: [] for m in methods}
    qvecs = embed([q["q"] for q in persona["fact_questions"]])
    scored = [k for k, g in enumerate(gold) if g]
    for k in scored:
        q = persona["fact_questions"][k]
        rankings = coll.rank(q["q"], qvecs[k], "personal")
        rankings["KERNEL_NAMES"] = kernel_ranking(coll.index, q["q"], "9999-01-01", names_profile, "personal")
        for m in methods:
            ranks[m].append(gold_rank(rankings[m], gold[k]))
    styles = [persona["fact_questions"][k]["style"] for k in scored]
    by_style = {s: ranking_metrics({m: [r for r, st in zip(ranks[m], styles) if st == s] for m in methods}, cfg["u2"]["recall_at"]) for s in sorted(set(styles))}
    excluded = [persona["fact_questions"][k].get("id", str(k)) for k, g in enumerate(gold) if not g]
    out = {"questions": len(persona["fact_questions"]), "scored": len(scored), "excluded_empty_gold": excluded, "overall": ranking_metrics(ranks, cfg["u2"]["recall_at"]), "by_style": by_style}
    note = names_arm_note(ranks, len(scored))
    if note:
        out["note"] = note
    return out


# --------------------------------------------------------------------------------------------------------------------------------- the whole analysis

def method_tables(scores: Dict[str, List[float]], first: Dict[str, List[int]], tasks: Sequence[int], labels: Dict[Tuple[int, int], Optional[str]], mode: str,
                  top3: Dict[str, List[List[int]]], sweep: Sequence[float]) -> dict:
    """Per method and q: fired, shortfall (fewer than ceil(qT) tasks have a candidate), hits, false injections, precision, hits@3 (a relevant note among the first three)."""
    good = set(GOOD[mode])
    rel = relevance_arrays(first, tasks, labels, GOOD[mode])
    out = {}
    for m in scores:
        s = np.asarray(scores[m])
        out[m] = {}
        for q in sweep:
            take = fire_positions(s, tasks, q)
            h = int(rel[m][take].sum())
            out[m][str(q)] = {"fired": int(len(take)), "shortfall": stats.fire_size(q, len(s)) - int(len(take)), "hits": h, "false_injections": int(len(take) - h),
                              "precision": h / len(take) if len(take) else None,
                              "hits_at_3": sum(1 for t in take if any(labels.get((int(tasks[t]), j)) in good for j in top3[m][t]))}
    return out


def wilson_block(hits: int, n: int) -> dict:
    lo, hi = stats.wilson(hits, n)
    return {"n": n, "hits": hits, "false_injections": n - hits, "precision": hits / n if n else None, "wilson_lo": lo, "wilson_hi": hi}


def u1_block(prep: dict, items: Sequence[sbm.Item], records: Sequence[dict], pairs: dict, keys: Dict[str, dict], assistant: Dict[str, str], cfg: dict) -> dict:
    tasks = prep["eligible"]
    methods = [m for m in RANKED if m in prep["rankings"]]
    scores, first = columns(lambda m, i: prep["rankings"][m][str(i)], tasks, methods)
    top3 = {m: [[j for j, _ in prep["rankings"][m][str(i)][:3]] for i in tasks] for m in methods}
    days = [items[i].day.isoformat() for i in tasks]
    raw = pool_label_table(records)
    audited = audited_labels(keys, assistant)
    judge_labels = dict(raw)
    for pair, lab in audited.items():
        if judge_labels.get(pair) is None:                                   # a decisive pair without a valid judge label takes the assistant's label
            judge_labels[pair] = lab
    p1 = p1_readings(scores, first, days, tasks, judge_labels, cfg, assistant_labels=audited)
    sweep = cfg["readings"]["sweep"]
    q0 = cfg["readings"]["primary_q"]
    rel = relevance_arrays(first, tasks, judge_labels)
    e5 = np.asarray(scores["EMB_MINILM"]) >= cfg["reference_threshold_e5"]
    fire_e5 = set(np.flatnonzero(e5).tolist())
    tables = {mode: method_tables(scores, first, tasks, judge_labels, mode, top3, sweep) for mode in GOOD}
    shipped = prep.get("shipped", {})
    lex_fired = [i for i in tasks if shipped.get(str(i), {}).get("lexical", -1) >= 0]
    emb_only = [i for i in tasks if shipped.get(str(i), {}).get("lexical", -1) < 0 and shipped.get(str(i), {}).get("hybrid", -1) >= 0]
    discordant = [r for r in prep["overlap"] if r["q"] == q0]
    return {"tasks": len(tasks), "p1": p1,
            "context": {"tasks_with_same": p1["tasks_with_same"], "discordant_tasks_at_primary_q": {r["contrast"]: r["discordant_tasks"] for r in discordant},
                        "pairs_without_valid_label": sum(1 for v in raw.values() if v is None)},
            "methods": tables["strict"], "lenient": {"methods": tables["lenient"], "tasks_with_same_or_related": len({i for (i, _), v in judge_labels.items() if v in ("SAME", "RELATED")}),
                                                      "note": "descriptive; the verdict uses strict relevance only"},
            "ref_e5": {"threshold": cfg["reference_threshold_e5"], "fired": int(e5.sum()), "fire_rate": float(e5.mean()), "hits": int((e5 & rel["EMB_MINILM"]).sum()),
                       "false_injections": int((e5 & ~rel["EMB_MINILM"]).sum()), "same_tasks_as_emb_minilm_at_primary_q": fire_e5 == set(fire_positions(scores["EMB_MINILM"], tasks, q0).tolist())},
            "secondary": secondary_readings(scores, first, days, tasks, judge_labels, cfg),
            "operating_point": {m: operating_point(scores[m], rel[m], tasks) for m in methods},
            "shipped_thresholds": {"lexical_profile_fired": wilson_block(sum(1 for i in lex_fired if judge_labels.get((i, shipped[str(i)]["lexical"])) == "SAME"), len(lex_fired)),
                                   "embedding_gate_only": wilson_block(sum(1 for i in emb_only if judge_labels.get((i, shipped[str(i)]["hybrid"])) == "SAME"), len(emb_only))},
            "permutation_reference": permutation_reference(scores, first, tasks, pairs["pool"], judge_labels, cfg)}


def stratified_report(records: Sequence[dict], work: Path) -> Optional[dict]:
    if not ((work / STRATIFIED_KEYS).exists() and (work / STRATIFIED_ASSISTANT).exists()):
        return None
    keys, mine = read_json(work / STRATIFIED_KEYS), read_json(work / STRATIFIED_ASSISTANT)
    rows = [(v["judge_label"], mine.get(k)) for k, v in sorted(keys.items()) if mine.get(k) in SCALE]
    agree = sum(1 for j, m in rows if (j == "SAME") == (m == "SAME"))
    return {"n": len(rows), "agreement_same_vs_not": agree / len(rows) if rows else None, "identical_three_way": (sum(1 for j, m in rows if j == m) / len(rows)) if rows else None,
            "note": "descriptive; the reader is a language model too"}


def decision(p1: Optional[str], p2: Optional[str], gate_ok: bool, controls_ok: bool) -> str:
    if not gate_ok:
        return "NOT_APPLIED: the judge gate failed"
    if not controls_ok:
        return "NOT_APPLIED: an implementation control failed"
    if p1 is None or p1.startswith("NOT_EVALUABLE"):
        return "NOT_APPLIED: P1 is missing or not evaluable (prevalence)"
    if p1 == HELPS:
        return "ADD_EMBEDDER_PROFILE_FOR_NOTE_WRITING_MEMORY"
    if p1 == SUFFICIENT:
        if p2 is None:
            return "NOT_APPLIED: P2 is missing (the answerability gate failed or the questions were not run)"
        return "LEXICAL_FOR_NOTES_EMBEDDER_ONLY_FOR_QUESTION_RECALL_LATER" if p2 == "EMBEDDER_RESCUES" else "STAY_LEXICAL"
    return "LEXICAL_IN_SHADOW_REVISIT_WITH_MORE_TASKS"


def compute_results(work: Path, items: Sequence[sbm.Item], persona: dict, cfg: dict, embed: Callable, records: Sequence[dict]) -> dict:
    work = Path(work)
    prep, pairs = read_json(work / PREP), read_json(work / PAIRS)
    with np.load(work / VECTORS) as z:
        notes = z["notes"]
    keys = read_json(work / DECISIVE_KEYS) if (work / DECISIVE_KEYS).exists() else {}
    assistant = read_json(work / DECISIVE_ASSISTANT) if (work / DECISIVE_ASSISTANT).exists() else {}
    gate = judge_gate_report(records, cfg, pairs, keys, assistant)
    checks = controls_pass(prep["controls"], cfg)
    stages = contract.load_jsonl(work / STAGES)
    results: dict = {"judge_gate": gate, "gate_failed": not gate["passes"], "controls": prep["controls"], "controls_checks": checks, "controls_ok": all(checks.values()),
                     "proxy_problems": {"%s#%d" % (s["stage"], n): s["problems_after"] for n, s in enumerate(stages) if s.get("problems_after")}, "overlap_table": prep["overlap"]}
    p1 = None
    if gate["passes"]:
        results["u1"] = u1_block(prep, items, records, pairs, keys, assistant, cfg)
        p1 = results["u1"]["p1"]["verdict"]
        results["fusion_flag"] = results["u1"]["p1"]["fusion_flag"]
        sample = stratified_report(records, work)
        if sample:
            results["stratified_sample"] = sample
    results["u3"] = u3_report(items, notes, contract.load_jsonl(work / QUESTIONS), contract.load_jsonl(work / ANSWERS), contract.load_jsonl(work / AUDIT), embed, cfg,
                              prep["tau_lex"], prep["tau_emb"])
    results["u2"] = u2_report(items, notes, persona, embed, cfg, prep["tau_lex"], prep["tau_emb"])
    p2 = results["u3"].get("p2", {}).get("verdict")
    results["decision"] = decision(p1, p2, gate["passes"], results["controls_ok"])
    return json.loads(json.dumps(results, sort_keys=True))


def script_digests(cfg: dict) -> dict:
    out = {}
    for rel, frozen in cfg["script_sha256"].items():
        path = ROOT / rel
        got = contract.sha256_file(path) if path.exists() else None
        out[rel] = {"sha256": got, "frozen": frozen, "match": None if frozen is None else got == frozen}
    return out


def verdict_line(results: dict) -> str:
    """The verdict with what the README prints beside it: tasks with a SAME note, discordant tasks, pairs without a valid label."""
    u1 = results.get("u1")
    if not u1:
        return "P1 not read: the judge gate failed (%s); decision %s" % (", ".join(k for k, v in results["judge_gate"]["checks"].items() if not v), results["decision"])
    p1, ctx = u1["p1"], u1["context"]
    return "P1 %s | D_emb %d [%.1f, %.1f] | D_hyb %d [%.1f, %.1f] | tasks with a SAME note %d | discordant tasks %s | pairs without a valid label %d | decision %s" % (
        p1["verdict"], p1["d_emb"]["d"], p1["d_emb"]["lo"], p1["d_emb"]["hi"], p1["d_hyb"]["d"], p1["d_hyb"]["lo"], p1["d_hyb"]["hi"], ctx["tasks_with_same"],
        json.dumps(ctx["discordant_tasks_at_primary_q"], sort_keys=True), ctx["pairs_without_valid_label"], results["decision"])


def cmd_analyse(args: argparse.Namespace, embed: Callable) -> dict:
    cfg = load_config(args.config)
    digests = check_inputs(args, cfg)
    items, _ = load_inputs(args.notes, args.prep)
    persona = read_json(args.persona)
    work = Path(args.workdir)
    frozen = frozen_verdict(work, cfg, args.config)
    if not frozen["ok"]:
        raise FrozenMismatch("the run is not what was frozen: " + "; ".join(frozen["problems"]))
    records = contract.load_jsonl(work / LABELS)
    results = compute_results(work, items, persona, cfg, embed, records)
    print(verdict_line(results))
    write_json(Path(args.out) if args.out else work / RESULTS, results)
    meta = {"config_sha256": contract.sha256_file(Path(args.config)), "script_sha256": script_digests(cfg), "frozen": frozen, "environment": environment_record(cfg),
            "environment_at_prepare": read_json(work / PREP).get("environment"), "input_sha256": digests, "bootstrap_seed": cfg["readings"]["bootstrap"]["seed"],
            "gate_failed": results["gate_failed"], "prep_sha256": contract.sha256_file(work / PREP), "pairs_sha256": contract.sha256_file(work / PAIRS)}
    for name in (VECTORS, DECISIVE, DECISIVE_KEYS, DECISIVE_ASSISTANT, STRATIFIED, STRATIFIED_KEYS, STRATIFIED_ASSISTANT, QUESTIONS, ANSWERS, AUDIT, STAGES, BASELINE):
        if (work / name).exists():
            meta[name + "_sha256"] = contract.sha256_file(work / name)
    contract.write_summary(Path(args.summary) if args.summary else work / SUMMARY, work / LABELS, results, meta)
    return results


def configure_endpoints(args: argparse.Namespace) -> None:
    """--model, --judge-url and --writer-url default from config.json (budget.model, models.judge_proxy, models.writer_proxy). Only the model of the budget may be used, and the
    proxies must be on this machine: they receive the private note texts."""
    cfg = load_config(args.config)
    args.model = args.model or cfg["budget"]["model"]
    args.judge_url = args.judge_url or cfg["models"]["judge_proxy"]
    args.writer_url = args.writer_url or cfg["models"]["writer_proxy"]
    if args.model != cfg["budget"]["model"]:
        raise ValueError("only %s may be used for paid calls (the owner's instruction), not %r" % (cfg["budget"]["model"], args.model))
    for flag, url in (("--judge-url", args.judge_url), ("--writer-url", args.writer_url)):
        if urllib.parse.urlparse(url).hostname not in LOOPBACK_HOSTS:
            raise ValueError("%s %s is not a loopback address: the proxies receive private note texts and must run on this machine" % (flag, url))


def main(argv: Optional[List[str]] = None, generate: Optional[Generate] = None, writer: Optional[Generate] = None, embed: Optional[Callable] = None,
         summary_fn: Optional[SummaryFn] = None) -> int:
    parser = argparse.ArgumentParser(description="WMB-R1: lexical versus hybrid retrieval on the account's own notes.")
    parser.add_argument("command", choices=("prepare", "judge", "sample", "questions", "audit", "analyse"))
    parser.add_argument("--notes", type=Path, default=Path(r"D:\Pamiec LLM\NIE_DANE\opublikowane.jsonl"))
    parser.add_argument("--prep", type=Path, default=Path(r"D:\Pamiec LLM\NIE_DANE\replay\prep.json"))
    parser.add_argument("--persona", type=Path, default=ROOT / "data" / "lab" / "aam-e6-persona" / "persona.json")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--workdir", type=Path, default=Path(r"D:\Pamiec LLM\NIE_DANE\wmb_r1"))
    parser.add_argument("--stage", choices=("gate", "repeat", "pool", "all"), default="all")
    parser.add_argument("--judge-url", default=None, help="default: models.judge_proxy of config.json (a loopback address)")
    parser.add_argument("--writer-url", default=None, help="default: models.writer_proxy of config.json (a loopback address)")
    parser.add_argument("--model", default=None, help="default and only allowed value: budget.model of config.json")
    parser.add_argument("--ledger", type=Path, help="the spend ledger the stages read before starting (required for judge, questions and audit)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--allow-input-mismatch", action="store_true", help="tests only: skip the digest check of the three inputs")
    parser.add_argument("--continue-on-gate-failure", action="store_true", help="go on although a control has failed (the free controls, C4 or the judge's gate controls); the table is then not applied")
    parser.add_argument("--force-prepare", action="store_true", help="prepare: overwrite the pairs although labels or records of an earlier prepare depend on them")
    args = parser.parse_args(argv)
    summarise = summary_fn or proxy_summary
    try:
        if args.command in ("judge", "questions", "audit"):
            configure_endpoints(args)
        if args.command == "prepare":
            out = cmd_prepare(args, embed or default_embed())
        elif args.command == "analyse":
            out = cmd_analyse(args, embed or default_embed())
        elif args.command == "judge":
            out = cmd_judge(args, generate or backends.openai_generate(args.judge_url, args.model), summarise)
        elif args.command == "sample":
            out = cmd_sample(args)
        elif args.command == "audit":
            out = cmd_audit(args, embed or default_embed(), generate or backends.openai_generate(args.judge_url, args.model), summarise)
        else:
            out = cmd_questions(args, writer or backends.openai_generate(args.writer_url, args.model), generate or backends.openai_generate(args.judge_url, args.model), summarise)
    except (BudgetStop, RunAborted, backends.SpendCapRefused, ControlsNotPassed, PreflightFailed, LockHeld) as exc:
        print("stopped: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as exc:                       # RuntimeError: a kernel call whose status is not ok aborts the run
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, sort_keys=True, default=str)[:4000])
    return 3 if isinstance(out, dict) and out.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())
