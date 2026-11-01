"""Arms for the delayed-relevance experiment (AAM-E0).

Every arm answers one question: given the cue and the active goal on a given day, which
stored experiences go into a context of at most ``C`` words? All arms see the same
events (nothing dated after the cue day), are given the same retained-memory budget
``R`` (a share of the visible archive's words) and the same context budget ``C``, and
fill the context with the shared rule of ``corpus.arms._fill``. The arm's only freedom
is which events, in what order, in which form (raw text, summary).

Arms
----
A        nothing (floor)
F1       whole-archive BM25 (sqlite FTS5, porter stemming); no forgetting, a reference
F2       whole-archive dense retrieval; no forgetting, a reference
B3       recency window
Del      active-only: newest events plus the highest write-time-importance events, raw,
         under R; everything else is dormant and unreachable
Sum      newest events raw plus lead-truncated extractive summaries of the most
         important older events under R; dense index over what is stored; returns the
         summary text
Sum-raw  as Sum, but a summary hit expands to its raw event
D        traces under R: up to five TF-IDF concepts per older event, mapped to concept
         clusters by greedy cosine clustering at a fixed threshold, plus a pointer to
         the raw event; cue and goal concepts activate clusters, one hop of spreading
         through co-occurrence (weight 0.5, capped), activated events ranked by summed
         activation, raw events fetched; every fetch is logged with the concept link
O        oracle: the generator's own role/topic labels as the concepts, with CHEAPER
         traces (cost = distinct labels + 1, usually 2). It stores about three times as
         many traces as D at the same R, so it is NOT a same-footing upper bound on D
Oc       oracle on D's footing: exactly D's stored events and D's trace costs, with the
         generator's labels as the concepts (perfect association at D's coverage)
S        D with the pointers shuffled among the stored older events (lower bound); the
         harness averages ``cfg.shuffles`` independent shuffles per probe

Write-time importance is a static score of two authored fields known when the event is
written: novelty (0-1) and consequence (0-3). In goalshift-v0.2 both are independent of
the event's kind and text (see ``corpus.goalshift._write_time_fields``), so importance
is uninformative about which events are targets, by construction.

The retained-memory budget R is split: ``recent_share`` of it holds the newest events
raw (every forgetting arm), the rest holds the arm's representation of older events
(raw text for Del, summaries for Sum and Sum-raw, traces for D, O, S), taken in
importance order until the budget is spent. A trace costs one word per cluster plus one
for the pointer. Nothing here is tuned on the test seeds.

The dense backend is imported lazily and is injectable: tests use ``HashingEmbedder``.
"""

from __future__ import annotations

import hashlib
import math
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Protocol

from corpus.arms import _before, _cost, _fill
from corpus.goalshift import content_tokens, stream

ARM_NAMES = ("A", "F1", "F2", "B3", "Del", "Sum", "Sum-raw", "D", "O", "Oc", "S")
TRACE_ARMS = ("D", "O", "Oc", "S")
ORACLE_ARMS = ("O", "Oc")


@dataclass
class ArmConfig:
    recent_share: float = 0.4
    novelty_weight: float = 0.5
    summary_words: int = 8
    concepts_per_event: int = 5
    #: a concept stem must occur in at least this many visible events and have at least
    #: this many letters (fixed a priori, before the test seeds: one-off names and the
    #: stemmer's fragments, 'don' from 'done', are not concepts)
    min_concept_df: int = 2
    min_concept_len: int = 4
    shuffles: int = 20
    cluster_threshold: float = 0.55
    query_threshold: float = 0.55
    goal_weight: float = 0.5
    spread_weight: float = 0.5
    spread_cap: float = 1.0
    spread_cooc_norm: float = 3.0
    spread_neighbours: int = 8
    query_mode: str = "cue_goal"  # "cue_goal" or "cue"

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


# ------------------------------------------------------------------------- embedders


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder:
    """Deterministic bag-of-stems hashing embedder for tests. It has no notion of
    synonyms, so it cannot reproduce semantic retrieval; it only exercises the code."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for _, st in content_tokens(text) or [(w, w) for w in text.lower().split()]:
                h = hashlib.md5(st.encode("utf-8")).digest()
                vec[int.from_bytes(h[:4], "big") % self.dim] += 1.0 if h[4] & 1 else -1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


class SentenceTransformerBackend:
    """all-MiniLM-L6-v2 from a local directory. Imported lazily; never downloads."""

    def __init__(self, model_dir: str) -> None:
        import os

        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_dir, device="cpu")

    def encode(self, texts: list[str]) -> list[list[float]]:
        arr = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False,
                                batch_size=64)
        return [list(map(float, row)) for row in arr]


class CachedEmbedder:
    def __init__(self, inner: Embedder) -> None:
        self.inner = inner
        self.cache: dict[str, list[float]] = {}

    def encode(self, texts: list[str]) -> list[list[float]]:
        missing = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if missing:
            for t, v in zip(missing, self.inner.encode(missing)):
                self.cache[t] = v
        return [self.cache[t] for t in texts]


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# --------------------------------------------------------------------------- helpers


def importance(event: dict[str, Any], weight: float) -> float:
    """Static write-time score: novelty and consequence only."""
    return weight * float(event["novelty"]) + (1.0 - weight) * float(event["consequence"]) / 3.0


def _raw(event: dict[str, Any]) -> dict[str, Any]:
    return {"event_id": event["event_id"], "text": event["text"], "form": "raw",
            "day": event["day"], "position": event["position"]}


def _has_digit(word: str) -> bool:
    return any(ch.isdigit() for ch in word)


class Engine:
    """All arms over one world's events. States that depend only on the visible
    archive and R are cached per (day, R)."""

    def __init__(self, events: list[dict[str, Any]], embedder: Embedder,
                 cfg: ArmConfig | None = None,
                 concept_labels: dict[str, list[str]] | None = None, seed: int = 0) -> None:
        self.events = sorted(events, key=lambda e: e["position"])
        self.by_id = {e["event_id"]: e for e in self.events}
        self.emb = embedder if isinstance(embedder, CachedEmbedder) else CachedEmbedder(embedder)
        self.cfg = cfg or ArmConfig()
        self.labels = concept_labels or {}
        self.seed = seed
        self._cache: dict[Any, Any] = {}

    # -- shared pieces ------------------------------------------------------------

    def visible(self, day: int) -> list[dict[str, Any]]:
        key = ("vis", day)
        if key not in self._cache:
            self._cache[key] = _before(self.events, day)
        return self._cache[key]

    def _query(self, cue: str, goal: str) -> str:
        return cue if self.cfg.query_mode == "cue" else cue + " " + goal

    def _imp(self, e: dict[str, Any]) -> float:
        return importance(e, self.cfg.novelty_weight)

    def _vec(self, text: str) -> list[float]:
        return self.emb.encode([text])[0]

    def _partition(self, day: int, R: float) -> dict[str, Any]:
        key = ("part", day, R)
        if key in self._cache:
            return self._cache[key]
        visible = self.visible(day)
        archive_words = sum(_cost(e) for e in visible)
        r_words = int(R * archive_words)
        newest = sorted(visible, key=lambda e: (-e["day"], -e["position"]))
        recent = _fill(newest, int(r_words * self.cfg.recent_share))
        rid = {e["event_id"] for e in recent}
        rest = [e for e in visible if e["event_id"] not in rid]
        rest.sort(key=lambda e: (-self._imp(e), -e["day"], e["position"]))
        part = {"visible": visible, "archive_words": archive_words, "R_words": r_words,
                "recent": recent, "rest_ranked": rest,
                "rest_budget": r_words - sum(_cost(e) for e in recent)}
        self._cache[key] = part
        return part

    def _bm25_order(self, events: list[dict[str, Any]], query: str) -> list[str]:
        terms = sorted({surface for surface, _ in content_tokens(query)})
        if not terms or not events:
            return []
        con = sqlite3.connect(":memory:")
        try:
            con.execute("CREATE VIRTUAL TABLE ev USING fts5(eid UNINDEXED, text, "
                        "tokenize='porter unicode61')")
            con.executemany("INSERT INTO ev (eid, text) VALUES (?, ?)",
                            [(e["event_id"], e["text"]) for e in events])
            expr = " OR ".join('"%s"' % t for t in terms)
            rows = con.execute("SELECT eid FROM ev WHERE ev MATCH ? ORDER BY bm25(ev), eid",
                               (expr,)).fetchall()
        finally:
            con.close()
        return [row[0] for row in rows]

    def _dense_order(self, items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        if not items:
            return []
        qv = self._vec(query)
        vecs = self.emb.encode([i["text"] for i in items])
        scored = sorted(zip(items, vecs), key=lambda iv: (-dot(qv, iv[1]), iv[0]["position"]))
        return [i for i, _ in scored]

    # -- public entry -------------------------------------------------------------

    def run(self, arm: str, cue: str, goal: str, day: int, C: int, R: float,
            oracle_concepts: list[str] | None = None, shuffle: int = 0) -> dict[str, Any]:
        t0 = time.perf_counter()
        query = self._query(cue, goal)
        log: list[dict[str, Any]] = []
        meta: dict[str, Any] = {}
        if arm == "A":
            ctx: list[dict[str, Any]] = []
        elif arm == "B3":
            visible = self.visible(day)
            ctx = _fill(sorted(visible, key=lambda e: (-e["day"], -e["position"])), C)
            ctx = [_raw(e) for e in ctx]
        elif arm == "F1":
            visible = self.visible(day)
            order = self._bm25_order(visible, query)
            ctx = [_raw(e) for e in _fill([self.by_id[i] for i in order], C)]
        elif arm == "F2":
            visible = self.visible(day)
            ctx = [_raw(e) for e in _fill(self._dense_order(visible, query), C)]
        elif arm == "Del":
            part = self._partition(day, R)
            kept = _fill(part["rest_ranked"], part["rest_budget"])
            active = part["recent"] + kept
            order = self._bm25_order(active, query)
            seen = set(order)
            tail = sorted((e for e in active if e["event_id"] not in seen),
                          key=lambda e: (-self._imp(e), e["position"]))
            ordered = [self.by_id[i] for i in order] + tail
            ctx = [_raw(e) for e in _fill(ordered, C)]
            meta["stored"] = len(active)
            meta["stored_ids"] = [e["event_id"] for e in active]
        elif arm in ("Sum", "Sum-raw"):
            part = self._partition(day, R)
            items = [dict(_raw(e)) for e in part["recent"]]
            spent = 0
            for e in part["rest_ranked"]:
                text = " ".join(e["text"].split()[: self.cfg.summary_words])
                cost = len(text.split())
                if spent + cost > part["rest_budget"]:
                    continue
                spent += cost
                items.append({"event_id": e["event_id"], "text": text, "form": "summary",
                              "day": e["day"], "position": e["position"]})
            ordered = self._dense_order(items, query)
            if arm == "Sum":
                ctx = _fill(ordered, C)
            else:
                ctx = [_raw(self.by_id[i["event_id"]]) | {"expanded": i["form"] == "summary"}
                       for i in _fill_expanded(ordered, self.by_id, C)]
            meta["stored"] = len(items)
            meta["stored_ids"] = [i["event_id"] for i in items]
        elif arm in TRACE_ARMS:
            ctx, log, meta = self._trace_run(arm, cue, goal, day, C, R, oracle_concepts or [],
                                             shuffle)
        else:
            raise ValueError("unknown arm %r" % arm)
        ms = (time.perf_counter() - t0) * 1000.0
        words = sum(len(c["text"].split()) for c in ctx)
        meta["visible"] = len(self.visible(day))
        return {"arm": arm, "context": ctx, "words": words, "log": log, "meta": meta,
                "ms": ms, "link_ids": [entry["event_id"] for entry in log]}

    # -- traces ------------------------------------------------------------------

    def _concepts(self, day: int) -> tuple[dict[str, list[str]], dict[str, str]]:
        """Up to five TF-IDF concept stems per visible event (idf over the visible
        archive). Returns the concepts and one surface form per stem."""
        key = ("concepts", day)
        if key in self._cache:
            return self._cache[key]
        visible = self.visible(day)
        n = len(visible)
        tf: dict[str, dict[str, int]] = {}
        df: dict[str, int] = {}
        surface: dict[str, str] = {}
        for e in visible:
            counts: dict[str, int] = {}
            for s, st in content_tokens(e["text"]):
                if _has_digit(s):
                    continue
                counts[st] = counts.get(st, 0) + 1
                surface.setdefault(st, s)
            tf[e["event_id"]] = counts
            for st in counts:
                df[st] = df.get(st, 0) + 1
        concepts: dict[str, list[str]] = {}
        for e in visible:
            scored = [(c * math.log(n / df[st]), st) for st, c in tf[e["event_id"]].items()
                      if self.cfg.min_concept_df <= df[st] < n
                      and len(st) >= self.cfg.min_concept_len]
            scored.sort(key=lambda x: (-x[0], x[1]))
            concepts[e["event_id"]] = [st for _, st in scored[: self.cfg.concepts_per_event]]
        self._cache[key] = (concepts, surface)
        return concepts, surface

    @staticmethod
    def _cooc(stored: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        cooc: dict[str, dict[str, int]] = {}
        for it in stored:
            cs = sorted(it["clusters"])
            for a in cs:
                for b in cs:
                    if a != b:
                        cooc.setdefault(a, {})[b] = cooc.get(a, {}).get(b, 0) + 1
        return cooc

    def _trace_state(self, arm: str, day: int, R: float, k: int = 0) -> dict[str, Any]:
        key = ("trace", arm, day, R, k if arm == "S" else 0)
        if key in self._cache:
            return self._cache[key]
        if arm == "S":
            # D's stored set and clusters; only the pointers are permuted (shuffle number k)
            base = self._trace_state("D", day, R)
            stored = [dict(it) for it in base["stored"]]
            idx = [i for i, it in enumerate(stored) if it["form"] == "trace"]
            pointers = [stored[i]["pointer"] for i in idx]
            stream(self.seed, "shuffle", day, R, k).shuffle(pointers)
            for i, ptr in zip(idx, pointers):
                stored[i]["pointer"] = ptr
            state = dict(base, stored=stored)
            self._cache[key] = state
            return state
        if arm == "Oc":
            # D's stored set and D's trace cost; the clusters are the generator's labels
            base = self._trace_state("D", day, R)
            stored = [dict(it, clusters=set(self.labels.get(it["event_id"], [])))
                      for it in base["stored"]]
            state = dict(base, stored=stored, cooc=self._cooc(stored), cluster_of=None)
            self._cache[key] = state
            return state
        part = self._partition(day, R)
        if arm == "O":
            concept_sets = {e["event_id"]: list(self.labels.get(e["event_id"], []))
                            for e in part["visible"]}
            cluster_of = None
            seeds: dict[str, list[float]] = {}
            surface: dict[str, str] = {}
        else:
            concept_sets, surface = self._concepts(day)
            cluster_of = None
        # stored items: recent raw, then traces of older events in importance order
        stored: list[dict[str, Any]] = []
        for e in part["recent"]:
            stored.append({"event_id": e["event_id"], "pointer": e["event_id"], "form": "recent"})
        spent = 0
        traces: list[dict[str, Any]] = []
        if arm == "O":
            for e in part["rest_ranked"]:
                labs = concept_sets[e["event_id"]]
                cost = len(set(labs)) + 1
                if spent + cost > part["rest_budget"]:
                    continue
                spent += cost
                traces.append({"event_id": e["event_id"], "pointer": e["event_id"],
                               "form": "trace"})
        else:
            cl = self._clusters(day, R, concept_sets, surface, part)
            cluster_of = cl["cluster_of"]
            seeds = cl["seeds"]
            for e in part["rest_ranked"]:
                ids = {cluster_of[s] for s in concept_sets[e["event_id"]] if s in cluster_of}
                cost = len(ids) + 1
                if spent + cost > part["rest_budget"]:
                    continue
                spent += cost
                traces.append({"event_id": e["event_id"], "pointer": e["event_id"],
                               "form": "trace"})
        stored.extend(traces)
        for it in stored:
            if arm == "O":
                it["clusters"] = set(concept_sets[it["event_id"]])
            else:
                it["clusters"] = {cluster_of[s] for s in concept_sets[it["event_id"]]
                                  if s in cluster_of}
        state = {"stored": stored, "cooc": self._cooc(stored), "cluster_of": cluster_of,
                 "seeds": seeds, "surface": surface, "n_dormant": len(part["rest_ranked"]),
                 "n_traces": len(traces), "trace_words": spent, "day": day}
        self._cache[key] = state
        return state

    def _clusters(self, day: int, R: float, concept_sets: dict[str, list[str]],
                  surface: dict[str, str], part: dict[str, Any]) -> dict[str, Any]:
        """Greedy leader clustering of the concept stems that occur in stored items.
        The stored set is fixed by importance and the trace cost, which depends on the
        clusters, so clusters are built from the stems of all visible events and then
        the budget is applied; this errs towards a richer vocabulary than a true
        sequential ingest would have, never towards the future."""
        key = ("clusters", day)
        if key in self._cache:
            return self._cache[key]
        dfc: dict[str, int] = {}
        for stems in concept_sets.values():
            for st in stems:
                dfc[st] = dfc.get(st, 0) + 1
        vocab = sorted(dfc, key=lambda s: (-dfc[s], s))
        vecs = self.emb.encode([surface[s] for s in vocab]) if vocab else []
        seeds: dict[str, list[float]] = {}
        cluster_of: dict[str, str] = {}
        for st, v in zip(vocab, vecs):
            best, best_c = None, -2.0
            for cid, sv in seeds.items():
                c = dot(v, sv)
                if c > best_c:
                    best, best_c = cid, c
            if best is not None and best_c >= self.cfg.cluster_threshold:
                cluster_of[st] = best
            else:
                seeds[st] = v
                cluster_of[st] = st
        out = {"cluster_of": cluster_of, "seeds": seeds}
        self._cache[key] = out
        return out

    def _map_query_word(self, state: dict[str, Any], surface: str, st: str) -> str | None:
        cluster_of = state["cluster_of"]
        if st in cluster_of:
            return cluster_of[st]
        key = ("qmap", state["day"], surface)  # clusters depend on the day only
        if key in self._cache:
            return self._cache[key]
        seeds = state["seeds"]
        out = None
        if seeds:
            v = self._vec(surface)
            best, best_c = None, -2.0
            for cid, sv in seeds.items():
                c = dot(v, sv)
                if c > best_c:
                    best, best_c = cid, c
            out = best if best is not None and best_c >= self.cfg.query_threshold else None
        self._cache[key] = out
        return out

    def _trace_run(self, arm: str, cue: str, goal: str, day: int, C: int, R: float,
                   oracle: list[str], shuffle: int = 0):
        cfg = self.cfg
        state = self._trace_state(arm, day, R, shuffle)
        direct: dict[str, float] = {}
        sources: dict[str, list[str]] = {}
        if arm in ORACLE_ARMS:
            for c in oracle:
                direct[c] = direct.get(c, 0.0) + 1.0
                sources.setdefault(c, []).append(c)
        else:
            for text, weight in ((cue, 1.0), (goal, cfg.goal_weight)):
                seen: set[str] = set()
                for s, st in content_tokens(text):
                    if _has_digit(s) or st in seen:
                        continue
                    seen.add(st)
                    c = self._map_query_word(state, s, st)
                    if c is not None:
                        direct[c] = direct.get(c, 0.0) + weight
                        sources.setdefault(c, []).append(s)
        spread: dict[str, float] = {}
        spread_from: dict[str, list[str]] = {}
        for c, a in sorted(direct.items()):
            neigh = sorted(state["cooc"].get(c, {}).items(), key=lambda kv: (-kv[1], kv[0]))
            for n, cnt in neigh[: cfg.spread_neighbours]:
                add = cfg.spread_weight * a * min(1.0, cnt / cfg.spread_cooc_norm)
                spread[n] = min(cfg.spread_cap, spread.get(n, 0.0) + add)
                spread_from.setdefault(n, []).append(c)
        total = {c: direct.get(c, 0.0) + spread.get(c, 0.0) for c in set(direct) | set(spread)}
        scored = []
        for it in state["stored"]:
            s = sum(total.get(c, 0.0) for c in it["clusters"])
            if s > 0:
                scored.append((s, it))
        scored.sort(key=lambda x: (-x[0], -self._imp(self.by_id[x[1]["pointer"]]),
                                   x[1]["pointer"]))
        ordered, seen_ptr, why = [], set(), {}
        for s, it in scored:
            if it["pointer"] in seen_ptr:
                continue
            seen_ptr.add(it["pointer"])
            ordered.append(self.by_id[it["pointer"]])
            why[it["pointer"]] = (s, it)
        fetched = _fill(ordered, C)
        log = []
        for e in fetched:
            s, it = why[e["event_id"]]
            links = []
            for c in sorted(it["clusters"]):
                if c in direct:
                    links.append({"cluster": c, "via": "direct", "query_words": sources.get(c, [])})
                elif c in spread:
                    links.append({"cluster": c, "via": "spread",
                                  "from": sorted(set(spread_from.get(c, [])))})
            log.append({"event_id": e["event_id"], "score": round(s, 4),
                        "stored_as": it["event_id"], "links": links,
                        "via": "direct" if any(l["via"] == "direct" for l in links) else "spread"})
        meta = {"stored": len(state["stored"]), "n_traces": state["n_traces"],
                "n_dormant": state["n_dormant"], "trace_words": state["trace_words"],
                "n_direct": len(direct), "n_spread": len(spread),
                "stored_ids": [it["event_id"] for it in state["stored"]]}
        return [_raw(e) for e in fetched], log, meta


def _fill_expanded(ordered: list[dict[str, Any]], by_id: dict[str, dict[str, Any]],
                   budget: int) -> list[dict[str, Any]]:
    """Fill with the raw event behind each stored item, in the arm's order."""
    raw_items = [by_id[i["event_id"]] | {"form": i["form"]} for i in ordered]
    return _fill(raw_items, budget)
