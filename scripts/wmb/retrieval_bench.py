"""WMB-R1: lexical versus hybrid retrieval on the account's own notes.

Preregistration: data/lab/wmb-r1-retrieval/README.md and config.json. Commands (all resumable, all offline except `judge` and `questions`):
  prepare   embeddings, the rankings of every method for every task, the pool of pairs to judge, the control pairs, the free implementation controls
  judge     the relevance judge over the pairs (flash through the judge proxy)
  questions the paraphrased questions of part U3 and their answerability check
  analyse   every reading of the README from the record files alone
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm_backends as backends  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402
from wmb import contract, memory_kernel as mk, stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data" / "lab" / "wmb-r1-retrieval" / "config.json"
METHODS = ("LEX_BM25", "LEX_KERNEL", "LEX_TFIDF", "EMB_MINILM", "HYB_KERNEL")
SCALE = ("SAME", "RELATED", "UNRELATED")
LABEL = re.compile(r"\b(SAME|RELATED|UNRELATED)\b", re.I)
ID_BASE = 9999
Generate = Callable[[str, str, int, dict], dict]


def load_config(path: Path = CONFIG) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_inputs(notes_path: Path, prep_path: Path) -> Tuple[List[sbm.Item], List[str]]:
    with open(notes_path, encoding="utf-8") as handle:
        items = sbm.parse_items(handle)
    briefs = [str(b) for b in json.loads(Path(prep_path).read_text(encoding="utf-8"))["briefs"]]
    if len(briefs) != len(items):
        raise ValueError("%d briefs for %d notes" % (len(briefs), len(items)))
    return items, briefs


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


def hybrid_profile(tau_lex: float, tau_emb: float) -> dict:
    """Both gates at 5% of their calibrated values so that every pair with some overlap is a candidate; the strength is then 20 times max(cover / tau_lex, cos / tau_emb)."""
    return {"name": "r1-hybrid", "k": 10 ** 6, "embed": "required", "lex_tau": 0.05 * tau_lex, "tau": 0.05 * tau_emb, "min_evidence": 0.0, "names": False, "timeout_ms": 10 ** 7}


def kernel_ranking(index: mk.Index, query: str, now: str, profile: dict, task_type: str = "note") -> List[Tuple[int, float]]:
    result = mk.retrieve(index, query, task_type, now, profile)
    if result["status"] != "ok":
        raise RuntimeError("kernel status %s: %s" % (result["status"], result["error"]))
    return [(note_index(i.id), float(s)) for i, s in zip(result["items"], result["scores"])]


def choose_threshold(top1: Sequence[float], share: float) -> float:
    """E5's rule: the value above which `share` of the values lie."""
    ordered = sorted(top1)
    return ordered[min(len(ordered) - 1, int((1 - share) * len(ordered)))]


def prepare_rankings(items: Sequence[sbm.Item], briefs: Sequence[str], note_vectors: np.ndarray, brief_vectors: np.ndarray, cfg: dict) -> dict:
    """Per method and eligible task: the full candidate ranking [(note, score)], plus the calibrated thresholds. Memory of task i = notes j < i."""
    n, warm = len(items), cfg["tasks"]["warmup"]
    times = synthetic_times(items)
    stems = [mk.tokens(it.text) for it in items]
    qstems = [mk.tokens(b) for b in briefs]
    kitems = kernel_items(items, times)
    bm25, tfidf, emb, lex_kernel = {}, {}, {}, {}
    cache = {b: brief_vectors[i] for i, b in enumerate(briefs)}
    indexes: Dict[int, mk.Index] = {}
    for i in range(warm, n):
        corpus = Corpus(range(i), stems, note_vectors)
        bm25[i] = rank_pairs(corpus.bm25(qstems[i], cfg["bm25"]["k1"], cfg["bm25"]["b"]), corpus.docs, True)
        tfidf[i] = rank_pairs(corpus.tfidf(qstems[i]), corpus.docs, True)
        emb[i] = rank_pairs(corpus.cosine(brief_vectors[i]), corpus.docs, False)
        vectors = {note_id(j): note_vectors[j].tolist() for j in range(i)}
        indexes[i] = mk.build_index(kitems[:i], times[i], lambda texts: [cache[t].tolist() for t in texts], vectors)
        lex_kernel[i] = kernel_ranking(indexes[i], briefs[i], times[i], LEX_PROFILE)
    share = cfg["tasks"]["candidate_share_for_calibration"]
    tau_lex = choose_threshold([(lex_kernel[i][0][1] * LEX_PROFILE["lex_tau"]) if lex_kernel[i] else 0.0 for i in range(warm, n)], share)
    tau_emb = choose_threshold([emb[i][0][1] for i in range(warm, n)], share)
    profile = hybrid_profile(tau_lex, tau_emb)
    hyb = {i: kernel_ranking(indexes[i], briefs[i], times[i], profile) for i in range(warm, n)}
    return {"times": times, "tau_lex": tau_lex, "tau_emb": tau_emb, "rankings": {"LEX_BM25": bm25, "LEX_KERNEL": lex_kernel, "LEX_TFIDF": tfidf, "EMB_MINILM": emb, "HYB_KERNEL": hyb}}


def build_pool(rankings: dict, tasks: Sequence[int], per_method_top: int, methods: Sequence[str]) -> Dict[int, List[int]]:
    """For every task the sorted union of the first `per_method_top` candidates of the listed methods."""
    return {i: sorted({j for m in methods for j, _ in rankings[m][i][:per_method_top]}) for i in tasks}


def control_pairs(cfg: dict, tasks: Sequence[int], stems_brief: Sequence[Sequence[str]], stems_note: Sequence[Sequence[str]], note_vectors: np.ndarray,
                  brief_vectors: np.ndarray) -> Dict[str, List[Tuple[int, int]]]:
    """Positive: (task k, note k). Negative: (task i, note j < i) with no shared content stem and a MiniLM cosine below the limit. Seeded."""
    gate, rng = cfg["judge"]["gate"], random.Random(cfg["judge"]["seed"])
    pos = sorted(rng.sample(list(tasks), gate["positive_control_n"]))
    far: List[Tuple[int, int]] = []
    for i in tasks:
        qs = set(stems_brief[i])
        for j in range(i):
            if not qs & set(stems_note[j]) and float(brief_vectors[i] @ note_vectors[j]) < gate["negative_control_max_cosine"]:
                far.append((i, j))
    neg = sorted(rng.sample(far, min(gate["negative_control_n"], len(far))))
    return {"positive": [(k, k) for k in pos], "negative": neg}


def self_retrieval(items: Sequence[sbm.Item], briefs: Sequence[str], note_vectors: np.ndarray, brief_vectors: np.ndarray, tasks: Sequence[int], cfg: dict, tau_lex: float,
                   tau_emb: float) -> Dict[str, float]:
    """C1: the brief of note k against all notes, non-causally: the share of tasks for which note k is the first candidate, per method."""
    times = synthetic_times(items)
    stems = [mk.tokens(it.text) for it in items]
    corpus = Corpus(range(len(items)), stems, note_vectors)
    cache = {b: brief_vectors[i] for i, b in enumerate(briefs)}
    index = mk.build_index(kernel_items(items, times), "9999-01-01", lambda texts: [cache[t].tolist() for t in texts], {note_id(j): note_vectors[j].tolist() for j in range(len(items))})
    hits = Counter()
    for k in tasks:
        q = mk.tokens(briefs[k])
        first = {"LEX_BM25": rank_pairs(corpus.bm25(q, cfg["bm25"]["k1"], cfg["bm25"]["b"]), corpus.docs, True), "LEX_TFIDF": rank_pairs(corpus.tfidf(q), corpus.docs, True),
                 "EMB_MINILM": rank_pairs(corpus.cosine(brief_vectors[k]), corpus.docs, False),
                 "LEX_KERNEL": kernel_ranking(index, briefs[k], "9999-01-01", LEX_PROFILE), "HYB_KERNEL": kernel_ranking(index, briefs[k], "9999-01-01", hybrid_profile(tau_lex, tau_emb))}
        for m, ranking in first.items():
            hits[m] += 1 if ranking and ranking[0][0] == k else 0
    return {m: hits[m] / len(tasks) for m in METHODS}


def causality_violations(rankings: dict) -> int:
    """C2: candidates at or after the task."""
    return sum(1 for m in rankings for i, ranking in rankings[m].items() for j, _ in ranking if j >= i)


def reference_agreement(items: Sequence[sbm.Item], briefs: Sequence[str], note_vectors: np.ndarray, brief_vectors: np.ndarray, rankings: dict, tasks: Sequence[int],
                        cfg: dict, tau_lex: float, tau_emb: float, n: int = 30) -> Dict[str, object]:
    """C3: on a seeded sample of tasks the kernel's first candidate and score agree with a plain re-implementation of its coverage and of the hybrid strength."""
    stems = [mk.tokens(it.text) for it in items]
    rng = random.Random(cfg["judge"]["seed"] + 3)
    worst_lex, worst_hyb, same_first = 0.0, 0.0, 0
    sample = sorted(rng.sample(list(tasks), min(n, len(tasks))))
    for i in sample:
        corpus = Corpus(range(i), stems, note_vectors)
        cover = corpus.coverage(mk.tokens(briefs[i]))
        ref = rank_pairs(cover, corpus.docs, True)
        got = rankings["LEX_KERNEL"][i]
        worst_lex = max(worst_lex, abs(ref[0][1] - got[0][1] * LEX_PROFILE["lex_tau"]) if ref and got else 0.0)
        cos = corpus.cosine(brief_vectors[i])
        strength = np.maximum(cover / tau_lex, cos / tau_emb)
        ref_h = rank_pairs(strength, corpus.docs, False)
        got_h = rankings["HYB_KERNEL"][i]
        worst_hyb = max(worst_hyb, abs(ref_h[0][1] - got_h[0][1] * 0.05))
        same_first += 1 if ref and got and ref[0][0] == got[0][0] and ref_h[0][0] == got_h[0][0] else 0
    return {"tasks": len(sample), "same_first_candidate": same_first, "max_abs_diff_coverage": worst_lex, "max_abs_diff_hybrid_strength": worst_hyb}


def judge_prompt(cfg: dict, brief: str, note: str) -> str:
    return cfg["judge"]["user_template"].format(brief=brief, note=note)


def parse_label(raw: str) -> Optional[str]:
    found = {m.upper() for m in LABEL.findall(raw)}
    return next(iter(found)) if len(found) == 1 else None


def run_judge(pairs: Sequence[dict], items: Sequence[sbm.Item], briefs: Sequence[str], cfg: dict, generate: Generate, out: Path, workers: int = 8) -> int:
    """Judge every pair of kind/i/j/seed_offset not yet in `out`; one JSONL record per pair. A reply that is not one word of the scale is retried once with another seed."""
    done = {(r["kind"], r["i"], r["j"], r["seed_offset"]) for r in contract.load_jsonl(out)}
    todo = [p for p in pairs if (p["kind"], p["i"], p["j"], p["seed_offset"]) not in done]
    lock = threading.Lock()
    judge = cfg["judge"]
    opts = {"temperature": judge["temperature"], "top_p": 1.0, "num_predict": judge["max_tokens"]}

    def one(pair: dict) -> None:
        prompt, label, raw = judge_prompt(cfg, briefs[pair["i"]], items[pair["j"]].text), None, ""
        for attempt in range(2):
            raw = str(generate(judge["system"], prompt, judge["seed"] + pair["seed_offset"] + attempt * judge["retry_seed_offset"], opts)["text"])
            label = parse_label(raw)
            if label:
                break
        with lock:
            contract.append_jsonl(out, [{"kind": pair["kind"], "i": pair["i"], "j": pair["j"], "seed_offset": pair["seed_offset"], "label": label, "raw": raw.strip()[:24]}])

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, todo))
    return len(todo)


class StaticCollection:
    """A collection queried without a time limit (parts U2 and U3): the same five methods over the same documents, the kernel driven through the same permissive profiles."""

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
        q, bm = mk.tokens(query), self.cfg["bm25"]
        docs = self.corpus.docs
        return {"LEX_BM25": rank_pairs(self.corpus.bm25(q, bm["k1"], bm["b"]), docs, True), "LEX_TFIDF": rank_pairs(self.corpus.tfidf(q), docs, True),
                "EMB_MINILM": rank_pairs(self.corpus.cosine(vector), docs, False), "LEX_KERNEL": kernel_ranking(self.index, query, "9999-01-01", LEX_PROFILE, task_type),
                "HYB_KERNEL": kernel_ranking(self.index, query, "9999-01-01", hybrid_profile(self.tau_lex, self.tau_emb), task_type)}


def gold_rank(ranking: Sequence[Tuple[int, float]], gold: set) -> Optional[int]:
    """1-based position of the first gold document, None when it is not among the candidates."""
    for position, (j, _) in enumerate(ranking, 1):
        if j in gold:
            return position
    return None


def recall_at(ranks: Sequence[Optional[int]], k: int) -> float:
    return sum(1 for r in ranks if r is not None and r <= k) / len(ranks) if ranks else float("nan")


def reciprocal_rank(ranks: Sequence[Optional[int]]) -> float:
    return sum(1.0 / r for r in ranks if r) / len(ranks) if ranks else float("nan")


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
    """For every fact question the biography items (by position) that contain one of its keys."""
    bio = persona["biography"]
    return [{j for j, b in enumerate(bio) if any(key_pattern(k).search(b["text"]) for k in q["keys"])} for q in persona["fact_questions"]]


def fired(scores: np.ndarray, idx: np.ndarray, q: float) -> np.ndarray:
    """Positions (into idx) of the tasks fired at fraction q: the ceil(q * T) highest scores, ties by original task number, tasks without a candidate (-inf) never."""
    t = len(idx)
    order = np.lexsort((idx, -scores[idx]))
    take = order[: math.ceil(q * t - 1e-9)]
    return take[np.isfinite(scores[idx][take])]


def hits_at(scores: np.ndarray, relevant: np.ndarray, idx: np.ndarray, q: float) -> Tuple[int, int]:
    """(hits, false injections) of the fire set at fraction q; `relevant[i]` is whether the method's first candidate for task i is relevant."""
    chosen = fired(scores, idx, q)
    h = int(relevant[idx][chosen].sum())
    return h, len(chosen) - h


def paired_hits_difference(a: np.ndarray, rel_a: np.ndarray, b: np.ndarray, rel_b: np.ndarray, q: float, draws: int, seed: int, alpha: float = 0.05) -> dict:
    """D = hits(a) - hits(b) at fraction q, with a percentile interval from a paired bootstrap over tasks; the fire sets are recomputed inside every resample."""
    t = len(a)
    base = np.arange(t)
    d = hits_at(a, rel_a, base, q)[0] - hits_at(b, rel_b, base, q)[0]
    rng = np.random.default_rng(seed)
    out = np.empty(draws)
    for k in range(draws):
        idx = rng.integers(0, t, t)
        out[k] = hits_at(a, rel_a, idx, q)[0] - hits_at(b, rel_b, idx, q)[0]
    return {"d": int(d), "lo": float(np.percentile(out, 100 * alpha / 2)), "hi": float(np.percentile(out, 100 * (1 - alpha / 2)))}


def verdict_p1(result: dict, margin: float) -> str:
    if result["lo"] > 0 and result["d"] >= margin:
        return "EMBEDDER_HELPS_GATE"
    if result["hi"] < margin:
        return "LEXICAL_SUFFICIENT_FOR_GATE"
    return "UNRESOLVED"


def verdict_p2(result: dict, rescue_margin: float, none_below: float) -> str:
    if result["lo"] > 0 and result["d"] >= rescue_margin:
        return "EMBEDDER_RESCUES"
    if result["hi"] < none_below:
        return "NO_RESCUE"
    return "UNRESOLVED"


# ---------------------------------------------------------------------------------------------- files of a run

PREP, PAIRS, LABELS, HAND, HAND_LABELS, QUESTIONS, ANSWERS, VECTORS, RESULTS, SUMMARY = (
    "prep.json", "pairs.json", "labels.jsonl", "hand_sample.json", "hand_labels.json", "questions.jsonl", "answerable.jsonl", "vectors.npz", "results.json", "summary.json")
STORED = 20                                   # candidates kept per method and task in prep.json (the pool needs 5, hits@3 needs 3)


def default_embed(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> Callable[[Sequence[str]], np.ndarray]:
    from sentence_transformers import SentenceTransformer  # imported here: the module is usable without it
    model = SentenceTransformer(model_name, device="cpu")
    return lambda texts: np.asarray(model.encode(list(texts), normalize_embeddings=True, batch_size=32, show_progress_bar=False), dtype=float)


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def eligible_tasks(n: int, cfg: dict) -> List[int]:
    return list(range(cfg["tasks"]["warmup"], n))


def cmd_prepare(args: argparse.Namespace, embed: Callable[[Sequence[str]], np.ndarray]) -> dict:
    cfg = load_config(args.config)
    items, briefs = load_inputs(args.notes, args.prep)
    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)
    nv, bv = embed([i.text for i in items]), embed(briefs)
    np.savez(work / VECTORS, notes=nv, briefs=bv)
    prep = prepare_rankings(items, briefs, nv, bv, cfg)
    tasks = eligible_tasks(len(items), cfg)
    stems_b, stems_n = [mk.tokens(b) for b in briefs], [mk.tokens(it.text) for it in items]
    pool = build_pool(prep["rankings"], tasks, cfg["pool"]["per_method_top"], cfg["pool"]["methods"])
    pairs = control_pairs(cfg, tasks, stems_b, stems_n, nv, bv)
    rng = random.Random(cfg["judge"]["seed"] + 5)
    flat = [(i, j) for i in tasks for j in pool[i]]
    repeat = sorted(rng.sample(flat, int(round(cfg["judge"]["gate"]["repeat_share"] * len(flat)))))
    controls = {"self_retrieval": self_retrieval(items, briefs, nv, bv, tasks, cfg, prep["tau_lex"], prep["tau_emb"]),
                "causality_violations": causality_violations(prep["rankings"]),
                "reference_agreement": reference_agreement(items, briefs, nv, bv, prep["rankings"], tasks, cfg, prep["tau_lex"], prep["tau_emb"]),
                "tau_emb_matches_e5": abs(prep["tau_emb"] - cfg["reference_threshold_e5"]) < 5e-4}
    stored = {m: {str(i): [[j, s] for j, s in r[i][:STORED]] for i in tasks} for m, r in prep["rankings"].items()}
    write_json(work / PREP, {"times": prep["times"], "tau_lex": prep["tau_lex"], "tau_emb": prep["tau_emb"], "eligible": tasks, "rankings": stored, "controls": controls})
    write_json(work / PAIRS, {"pool": {str(i): pool[i] for i in tasks}, "positive": pairs["positive"], "negative": pairs["negative"], "repeat": repeat})
    return {"tasks": len(tasks), "pool_pairs": len(flat), "controls": controls, "tau_lex": prep["tau_lex"], "tau_emb": prep["tau_emb"]}


def judge_pairs(work: Path, stage: str, seed: int) -> List[dict]:
    pairs = read_json(work / PAIRS)
    rng = random.Random(seed)
    if stage == "gate":
        return [{"kind": "pos", "i": i, "j": j, "seed_offset": 0} for i, j in pairs["positive"]] + [{"kind": "neg", "i": i, "j": j, "seed_offset": 0} for i, j in pairs["negative"]]
    if stage == "repeat":
        return [{"kind": "pool", "i": i, "j": j, "seed_offset": 1} for i, j in pairs["repeat"]]
    flat = [{"kind": "pool", "i": int(i), "j": j, "seed_offset": 0} for i, js in pairs["pool"].items() for j in js]
    rng.shuffle(flat)
    return flat


def cmd_judge(args: argparse.Namespace, generate: Generate) -> dict:
    cfg = load_config(args.config)
    items, briefs = load_inputs(args.notes, args.prep)
    work = Path(args.workdir)
    stages = ("gate", "pool", "repeat") if args.stage == "all" else (args.stage,)
    ran = {}
    for stage in stages:
        ran[stage] = run_judge(judge_pairs(work, stage, cfg["judge"]["seed"]), items, briefs, cfg, generate, work / LABELS, args.workers)
    return ran


def hand_sample(labels: Sequence[dict], cfg: dict) -> List[Tuple[int, int]]:
    """Stratified by the judge's label: 14 SAME, 13 RELATED, 13 UNRELATED where they exist, seeded; the rest of the 40 filled from the other strata."""
    rng = random.Random(cfg["judge"]["seed"] + 7)
    by = {lab: sorted((r["i"], r["j"]) for r in labels if r["kind"] == "pool" and r["seed_offset"] == 0 and r["label"] == lab) for lab in SCALE}
    want = {"SAME": 14, "RELATED": 13, "UNRELATED": 13}
    chosen: List[Tuple[int, int]] = []
    for lab in SCALE:
        chosen += rng.sample(by[lab], min(want[lab], len(by[lab])))
    spare = [p for lab in SCALE for p in by[lab] if p not in chosen]
    n = cfg["judge"]["gate"]["hand_sample_n"]
    chosen += rng.sample(spare, min(len(spare), max(0, n - len(chosen))))
    rng.shuffle(chosen)
    return chosen[:n]


def cmd_hand_sample(args: argparse.Namespace) -> dict:
    cfg = load_config(args.config)
    items, briefs = load_inputs(args.notes, args.prep)
    work = Path(args.workdir)
    chosen = hand_sample(contract.load_jsonl(work / LABELS), cfg)
    write_json(work / HAND, [{"key": "%d-%d" % (i, j), "task": briefs[i], "note": items[j].text} for i, j in chosen])
    return {"pairs": len(chosen)}


def question_prompt(cfg: dict, note: str) -> str:
    return cfg["u3"]["writer"]["user_template"].format(note=note)


def cmd_questions(args: argparse.Namespace, writer: Generate, judge: Generate) -> dict:
    cfg = load_config(args.config)
    items, _ = load_inputs(args.notes, args.prep)
    work = Path(args.workdir)
    spec = cfg["u3"]
    chosen = sample_u3_notes(items, cfg)
    have = {r["k"] for r in contract.load_jsonl(work / QUESTIONS)}
    lock = threading.Lock()
    w = spec["writer"]

    def ask(k: int) -> None:
        text = str(writer(w["system"], question_prompt(cfg, items[k].text), w["seed"] + k, {"temperature": w["temperature"], "top_p": 1.0, "num_predict": w["max_tokens"]})["text"]).strip()
        with lock:
            contract.append_jsonl(work / QUESTIONS, [{"k": k, "question": text.splitlines()[0].strip() if text else ""}])

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(ask, [k for k in chosen if k not in have]))
    a = spec["answerability"]
    done = {r["k"] for r in contract.load_jsonl(work / ANSWERS)}

    def check(row: dict) -> None:
        raw = str(judge(a["system"], a["user_template"].format(note=items[row["k"]].text, question=row["question"]), a["seed"], {"temperature": a["temperature"], "top_p": 1.0,
                                                                                                                              "num_predict": 20})["text"]).strip().upper()
        with lock:
            contract.append_jsonl(work / ANSWERS, [{"k": row["k"], "answer": "YES" if re.match(r"^\W*YES\b", raw) else ("NO" if re.match(r"^\W*NO\b", raw) else None)}])

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(check, [r for r in contract.load_jsonl(work / QUESTIONS) if r["k"] not in done]))
    return {"questions": len(contract.load_jsonl(work / QUESTIONS)), "checked": len(contract.load_jsonl(work / ANSWERS))}


# ---------------------------------------------------------------------------------------------- analysis

SETS = {"strict": {"SAME"}, "lenient": {"SAME", "RELATED"}}
COMPARISONS = (("HYB_KERNEL", "LEX_KERNEL"), ("LEX_BM25", "LEX_KERNEL"), ("LEX_TFIDF", "LEX_KERNEL"), ("EMB_MINILM", "LEX_KERNEL"), ("HYB_KERNEL", "EMB_MINILM"))


def label_table(labels: Sequence[dict], kind: str = "pool", seed_offset: int = 0) -> Dict[Tuple[int, int], Optional[str]]:
    return {(r["i"], r["j"]): r["label"] for r in labels if r["kind"] == kind and r["seed_offset"] == seed_offset}


def method_arrays(prep: dict, tasks: Sequence[int], lab: Dict[Tuple[int, int], Optional[str]], mode: str, methods: Sequence[str] = METHODS) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Per method: the score of the first candidate (-inf when there is none), whether it is relevant, whether one of the first three is."""
    good = SETS[mode]
    out = {}
    for m in methods:
        scores, first, three = np.full(len(tasks), -np.inf), np.zeros(len(tasks), dtype=bool), np.zeros(len(tasks), dtype=bool)
        for t, i in enumerate(tasks):
            ranking = prep["rankings"][m][str(i)]
            if ranking:
                scores[t] = ranking[0][1]
                first[t] = lab.get((i, ranking[0][0])) in good
                three[t] = any(lab.get((i, j)) in good for j, _ in ranking[:3])
        out[m] = (scores, first, three)
    return out


def u1_block(prep: dict, labels: Sequence[dict], cfg: dict, mode: str) -> dict:
    tasks, spec = prep["eligible"], cfg["readings"]
    arrays = method_arrays(prep, tasks, label_table(labels), mode)
    idx = np.arange(len(tasks))
    table = {}
    for m in METHODS:
        scores, first, three = arrays[m]
        table[m] = {}
        for q in spec["sweep"]:
            hits, false = hits_at(scores, first, idx, q)
            table[m][str(q)] = {"hits": hits, "false_injections": false, "hits_at_3": int(three[idx][fired(scores, idx, q)].sum())}
    e5 = arrays["EMB_MINILM"][0] >= cfg["reference_threshold_e5"]
    table["REF_E5"] = {"fire_rate": float(e5.mean()), "hits": int((e5 & arrays["EMB_MINILM"][1]).sum()), "false_injections": int((e5 & ~arrays["EMB_MINILM"][1]).sum())}
    compare = {}
    for a, b in COMPARISONS:
        compare["%s-%s" % (a, b)] = {str(q): paired_hits_difference(arrays[a][0], arrays[a][1], arrays[b][0], arrays[b][1], q, spec["bootstrap"]["draws"], spec["bootstrap"]["seed"])
                                     for q in spec["sweep"]}
    primary = compare["HYB_KERNEL-LEX_KERNEL"][str(spec["primary_q"])]
    return {"relevance": mode, "tasks": len(tasks), "methods": table, "differences": compare, "p1": dict(primary, verdict=verdict_p1(primary, spec["margin_tasks"]))}


def shuffle_check(prep: dict, pool: Dict[str, List[int]], labels: Sequence[dict], cfg: dict, mode: str) -> dict:
    """C4: labels permuted within every task's pool; the verdict must almost never be EMBEDDER_HELPS_GATE."""
    spec, tasks = cfg["readings"], prep["eligible"]
    lab = label_table(labels)
    rng = random.Random(spec["bootstrap"]["seed"] + 11)
    helps, diffs = 0, []
    for s in range(spec["shuffle_draws"]):
        shuffled: Dict[Tuple[int, int], Optional[str]] = {}
        for i in tasks:
            js = pool[str(i)]
            values = [lab.get((i, j)) for j in js]
            rng.shuffle(values)
            shuffled.update({(i, j): v for j, v in zip(js, values)})
        arrays = method_arrays(prep, tasks, shuffled, mode, ("HYB_KERNEL", "LEX_KERNEL"))
        res = paired_hits_difference(arrays["HYB_KERNEL"][0], arrays["HYB_KERNEL"][1], arrays["LEX_KERNEL"][0], arrays["LEX_KERNEL"][1], spec["primary_q"], 200, spec["bootstrap"]["seed"] + s)
        diffs.append(res["d"])
        helps += 1 if verdict_p1(res, spec["margin_tasks"]) == "EMBEDDER_HELPS_GATE" else 0
    share = helps / spec["shuffle_draws"]
    return {"shuffles": spec["shuffle_draws"], "helps_share": share, "mean_d": float(np.mean(diffs)), "passes": share <= spec["shuffle_max_helps_share"]}


def judge_gate_report(labels: Sequence[dict], hand: Sequence[dict], hand_labels: Dict[str, str], cfg: dict) -> dict:
    g = cfg["judge"]["gate"]
    pos, neg = [r for r in labels if r["kind"] == "pos"], [r for r in labels if r["kind"] == "neg"]
    first, second = label_table(labels), label_table(labels, "pool", 1)
    both = [k for k in second if k in first and first[k] and second[k]]
    agree = sum(1 for k in both if first[k] == second[k]) / len(both) if both else None
    judged = {"%d-%d" % k: v for k, v in first.items()}
    graded = [(judged[h["key"]], hand_labels[h["key"]]) for h in hand if h["key"] in hand_labels and judged.get(h["key"])]
    hand_agree = sum(1 for j, m in graded if (j == "SAME") == (m == "SAME")) / len(graded) if graded else None
    fail = sum(1 for r in labels if r["label"] is None) / len(labels) if labels else None
    report = {"positive_same": sum(1 for r in pos if r["label"] == "SAME"), "positive_n": len(pos), "negative_unrelated": sum(1 for r in neg if r["label"] == "UNRELATED"), "negative_n": len(neg),
              "repeat_agreement": agree, "repeat_n": len(both), "hand_agreement": hand_agree, "hand_n": len(graded), "format_failure_share": fail}
    report["checks"] = {"positive": len(pos) >= g["positive_control_n"] and report["positive_same"] >= g["positive_control_min_same"],
                        "negative": len(neg) >= g["negative_control_n"] and report["negative_unrelated"] >= g["negative_control_min_unrelated"],
                        "repeat": agree is not None and agree >= g["repeat_min_agreement"],
                        "hand": hand_agree is not None and len(graded) >= g["hand_sample_n"] and hand_agree >= g["hand_sample_min_agreement"],
                        "format": fail is not None and fail <= g["format_failure_max"]}
    report["passes"] = all(report["checks"].values())
    return report


def tercile_slices(values: Sequence[float]) -> List[List[int]]:
    order = sorted(range(len(values)), key=lambda k: (values[k], k))
    third = len(order) // 3
    return [order[:third], order[third:2 * third], order[2 * third:]]


def ranking_metrics(ranks: Dict[str, List[Optional[int]]], at: Sequence[int]) -> dict:
    return {m: dict({"recall@%d" % k: round(recall_at(r, k), 6) for k in at}, mrr=round(reciprocal_rank(r), 6), n=len(r)) for m, r in ranks.items()}


def bootstrap_mean_difference(a: Sequence[float], b: Sequence[float], draws: int, seed: int, alpha: float = 0.05) -> dict:
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    means = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(draws)]) if len(d) else np.array([float("nan")])
    return {"d": float(d.mean()) if len(d) else float("nan"), "lo": float(np.percentile(means, 100 * alpha / 2)), "hi": float(np.percentile(means, 100 * (1 - alpha / 2))), "n": int(len(d))}


def u3_report(items: Sequence[sbm.Item], note_vectors: np.ndarray, questions: Sequence[dict], answers: Sequence[dict], embed: Callable, cfg: dict, tau_lex: float, tau_emb: float) -> dict:
    spec, readings = cfg["u3"], cfg["readings"]
    said = {r["k"]: r["answer"] for r in answers}
    kept = [q for q in questions if q["question"] and said.get(q["k"]) == "YES"]
    yes_share = (sum(1 for q in questions if said.get(q["k"]) == "YES") / len(questions)) if questions else None
    report: dict = {"questions": len(questions), "retained": len(kept), "answerable_share": yes_share, "gate_passes": yes_share is not None and yes_share >= spec["answerability"]["min_yes"]}
    if len(kept) < 9:
        return report
    coll = StaticCollection([it.text for it in items], ["account_history"] * len(items), synthetic_times(items), note_vectors, cfg, tau_lex, tau_emb)
    qvec = embed([q["question"] for q in kept])
    ranks: Dict[str, List[Optional[int]]] = {m: [] for m in METHODS}
    for q, v in zip(kept, qvec):
        rankings = coll.rank(q["question"], v, "note")
        for m in METHODS:
            ranks[m].append(gold_rank(rankings[m], {q["k"]}))
    overlap = [question_overlap(q["question"], items[q["k"]].text) for q in kept]
    terciles = tercile_slices(overlap)
    low = terciles[0]
    report.update({"overall": ranking_metrics(ranks, spec["recall_at"]), "overlap_cut_points": [round(overlap[t[-1]], 4) for t in terciles[:2]],
                   "by_overlap_tercile": {name: ranking_metrics({m: [ranks[m][k] for k in t] for m in METHODS}, spec["recall_at"]) for name, t in zip(("low", "middle", "high"), terciles)}})
    a = [1.0 if (ranks["HYB_KERNEL"][k] or 10 ** 9) <= 3 else 0.0 for k in low]
    b = [1.0 if (ranks["LEX_KERNEL"][k] or 10 ** 9) <= 3 else 0.0 for k in low]
    p2 = bootstrap_mean_difference(a, b, readings["bootstrap"]["draws"], readings["bootstrap"]["seed"])
    report["p2"] = dict(p2, verdict=verdict_p2(p2, 0.15, 0.10))
    wrong = [(k, ranks["LEX_KERNEL"][k]) for k in range(len(kept))]
    report["note"] = "gold = the source note; another note may also answer a question"
    del wrong
    return report


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
    answerable = [k for k, g in enumerate(gold) if g]
    for k in answerable:
        q = persona["fact_questions"][k]
        rankings = coll.rank(q["q"], qvecs[k], "personal")
        rankings["KERNEL_NAMES"] = kernel_ranking(coll.index, q["q"], "9999-01-01", names_profile, "personal")
        for m in methods:
            ranks[m].append(gold_rank(rankings[m], gold[k]))
    styles = [persona["fact_questions"][k]["style"] for k in answerable]
    by_style = {s: ranking_metrics({m: [r for r, st in zip(ranks[m], styles) if st == s] for m in methods}, cfg["u2"]["recall_at"]) for s in sorted(set(styles))}
    return {"questions": len(persona["fact_questions"]), "with_gold": len(answerable), "overall": ranking_metrics(ranks, cfg["u2"]["recall_at"]), "by_style": by_style}


def decision(p1: Optional[str], p2: Optional[str], gate_ok: bool, controls_ok: bool) -> str:
    if not (gate_ok and controls_ok) or p1 is None:
        return "NOT_APPLIED: a gate or a control failed or a part is missing"
    if p1 == "EMBEDDER_HELPS_GATE":
        return "ADD_EMBEDDER_PROFILE_FOR_NOTE_WRITING_MEMORY"
    if p1 == "LEXICAL_SUFFICIENT_FOR_GATE":
        return "LEXICAL_FOR_NOTES_EMBEDDER_ONLY_FOR_QUESTION_RECALL_LATER" if p2 == "EMBEDDER_RESCUES" else "STAY_LEXICAL"
    return "LEXICAL_IN_SHADOW_REVISIT_WITH_MORE_TASKS"


def compute_results(work: Path, items: Sequence[sbm.Item], persona: dict, cfg: dict, embed: Callable, labels: Sequence[dict]) -> dict:
    prep, pairs = read_json(work / PREP), read_json(work / PAIRS)
    notes = np.load(work / VECTORS)["notes"]
    hand = read_json(work / HAND) if (work / HAND).exists() else []
    hand_labels = read_json(work / HAND_LABELS) if (work / HAND_LABELS).exists() else {}
    gate = judge_gate_report(labels, hand, hand_labels, cfg)
    tasks, rule = prep["eligible"], cfg["judge"]["prevalence_rule_min_tasks_with_same"]
    lab = label_table(labels)
    with_same = sum(1 for i in tasks if any(lab.get((i, j)) == "SAME" for j in pairs["pool"][str(i)]))
    primary_mode = "strict" if with_same >= rule else "lenient"
    controls = prep["controls"]
    controls_ok = (all(v >= cfg["readings"]["self_retrieval_min"] for v in controls["self_retrieval"].values()) and controls["causality_violations"] == 0
                   and controls["reference_agreement"]["same_first_candidate"] == controls["reference_agreement"]["tasks"])
    results: dict = {"judge_gate": gate, "controls": controls, "tasks_with_same_in_pool": with_same, "primary_relevance": primary_mode, "controls_ok": controls_ok}
    questions, answers = contract.load_jsonl(work / QUESTIONS), contract.load_jsonl(work / ANSWERS)
    results["u3"] = u3_report(items, notes, questions, answers, embed, cfg, prep["tau_lex"], prep["tau_emb"])
    results["u2"] = u2_report(items, notes, persona, embed, cfg, prep["tau_lex"], prep["tau_emb"])
    p1 = None
    if labels:
        results["u1"] = {mode: u1_block(prep, labels, cfg, mode) for mode in ("strict", "lenient")}
        results["c4_shuffle"] = shuffle_check(prep, pairs["pool"], labels, cfg, primary_mode)
        p1 = results["u1"][primary_mode]["p1"]["verdict"]
    p2 = results["u3"].get("p2", {}).get("verdict")
    results["decision"] = decision(p1, p2, gate["passes"] and results.get("c4_shuffle", {}).get("passes", False), controls_ok)
    return json.loads(json.dumps(results, sort_keys=True))


def cmd_analyse(args: argparse.Namespace, embed: Callable) -> dict:
    cfg = load_config(args.config)
    items, _ = load_inputs(args.notes, args.prep)
    persona = read_json(args.persona)
    work = Path(args.workdir)
    labels = contract.load_jsonl(work / LABELS)
    results = compute_results(work, items, persona, cfg, embed, labels)
    write_json(Path(args.out) if args.out else work / RESULTS, results)
    meta = {"config_sha256": contract.sha256_file(Path(args.config)), "script_sha256": contract.sha256_file(Path(__file__)),
            "prep_sha256": contract.sha256_file(work / PREP), "pairs_sha256": contract.sha256_file(work / PAIRS), "bootstrap_seed": cfg["readings"]["bootstrap"]["seed"]}
    for name in (QUESTIONS, ANSWERS, HAND, HAND_LABELS):
        if (work / name).exists():
            meta[name + "_sha256"] = contract.sha256_file(work / name)
    contract.write_summary(Path(args.summary) if args.summary else work / SUMMARY, work / LABELS, results, meta)
    return results


def main(argv: Optional[List[str]] = None, generate: Optional[Generate] = None, writer: Optional[Generate] = None, embed: Optional[Callable] = None) -> int:
    parser = argparse.ArgumentParser(description="WMB-R1: lexical versus hybrid retrieval on the account's own notes.")
    parser.add_argument("command", choices=("prepare", "judge", "hand-sample", "questions", "analyse"))
    parser.add_argument("--notes", type=Path, default=Path(r"D:\Pamiec LLM\NIE_DANE\opublikowane.jsonl"))
    parser.add_argument("--prep", type=Path, default=Path(r"D:\Pamiec LLM\NIE_DANE\replay\prep.json"))
    parser.add_argument("--persona", type=Path, default=ROOT / "data" / "lab" / "aam-e6-persona" / "persona.json")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--workdir", type=Path, default=Path(r"D:\Pamiec LLM\NIE_DANE\wmb_r1"))
    parser.add_argument("--stage", choices=("gate", "pool", "repeat", "all"), default="all")
    parser.add_argument("--judge-url", default="http://127.0.0.1:8798/v1")
    parser.add_argument("--writer-url", default="http://127.0.0.1:8799/v1")
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command in ("prepare", "analyse"):
            embedder = embed or default_embed()
            out = cmd_prepare(args, embedder) if args.command == "prepare" else cmd_analyse(args, embedder)
        elif args.command == "judge":
            out = cmd_judge(args, generate or backends.openai_generate(args.judge_url, args.model))
        elif args.command == "hand-sample":
            out = cmd_hand_sample(args)
        else:
            out = cmd_questions(args, writer or backends.openai_generate(args.writer_url, args.model), generate or backends.openai_generate(args.judge_url, args.model))
    except (OSError, ValueError, backends.SpendCapRefused) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, sort_keys=True)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
