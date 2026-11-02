"""The baseline systems of the LifeSim ladder and the online retention gate.

What this module provides
-------------------------
Every system is a ``lifesim.interface.LifeMemory``: it ingests ``Record`` objects in time order,
answers ``query(question, asked_at, budget)`` from what it stored, and delivers a context of at most
``budget`` whitespace words, filled by the one policy ``fill_to_budget`` (rank order, stop at the
first item that does not fit) and given in chronological order. A query sees only records with
``timestamp < asked_at``.

* Blind floors: ``Prior`` (B0a: the generator prior's mode for the slot the question is about),
  ``Heuristic`` (B0h: the value of that slot's closed vocabulary seen most often in the stream so
  far) and ``Abstainer`` (always UNKNOWN: scores the abstain share). They find the slot with
  ``infer_slot`` from the question TEXT alone and deliver no context.
* Evidence-level retrievers (no reader; the answer text is empty): ``Recency`` (B1), ``RandomK``,
  ``BM25`` (B2: Okapi BM25 with k1 = 1.2 and b = 0.75, Lucene idf ``ln(1 + (N - df + 0.5) /
  (df + 0.5))``, query-side stop words only), ``BM25Time`` (B2t = S-LEX: BM25 plus a date window
  read from the question: ISO dates, 'yesterday', 'N days ago', 'about N weeks/months ago',
  'between A and B'; records inside the window rank ahead of the others, ``hard=True`` drops the
  others; a question without a date cue is plain BM25), ``DenseStore`` (C1, with an INJECTABLE
  embedder) and ``HybridStore`` (C2 = S-HYB: BM25Time and dense fused by reciprocal rank fusion,
  k = 60, depth 100). ``hashing_embedder`` is a deterministic feature-hashing stand-in that tests
  and the free grid use instead of MiniLM.
* Oracles: ``OracleText`` (the evidence lines of the bound query, in the context),
  ``OracleStruct`` (answers from the structure with the independent solver ``gold_slow``) and
  ``OracleStore`` (BM25Time over a store that holds only the needed lines). The oracles are the only
  systems that read a ``Query`` (``needs_query``; the harness binds it).
* ``GatedMemory(inner, policy, R, seed, need)``: the retention gate, OUTSIDE the product and ONLINE.
  Capacity ``K(t) = floor(R x words seen)`` in whole records (exact rational arithmetic; the store
  never exceeds it and is within one record of it); a new record is admitted and the lowest-weight
  records are evicted until the store fits, so the new record can be rejected at once. Weights are
  fixed at write time except GM. Ties break by a random draw from ``stream(seed, 'gate', policy)``
  (one draw per record, so CONST readings behave like GU), except GR (oldest first).
  At R = 1.0 nothing is ever evicted and the store is byte-identical across policies. Policies:

  ===== ==========================================================================================
  ALL   keep everything (unbounded; R is ignored; compared only with complete-store arms)
  GU    uniform random retention
  GR    recency: keep the newest words (FIFO)
  GN    text novelty: share of the line's distinct tokens never seen before in the stream
  GM    re-mention count: +1 each time a later line repeats a rare token of the line (rare = seen
        in at most max(3, 1% of the lines so far) lines), the frequency-importance confound
  GS    text surprise: mean unigram surprisal of the line's tokens under the stream so far
  GH    the channel reading ``Record.heartbeat`` (a missing reading counts as the running median)
  GTN   the reading's percentile among earlier readings of the SAME channel kind (diary, chat, ...),
        a diagnostic for compositional circularity (type base rates removed)
  GO    ORACLE bound: 1 for the lines in ``need`` (the lines that evidence a query), else 0
  GA    exploratory: number of lexicon affect words in the text (text sentiment as heartbeat)
  GL    learned salience (W4): NOT IMPLEMENTED (raises NotImplementedError)
  ===== ==========================================================================================

  Salience policies (GH, GTN) read only ``Record.heartbeat``; no policy but GO reads anything that
  names the future, and ``bind(query)`` is never read by a gate.

Conventions and ASSUMED numbers (not generator parameters): BM25 k1 1.2 and b 0.75; the stop word
list of the query side; RRF k 60 and depth 100; the GM rarity rule; the unigram smoothing add-one.
Scores that decide a ranking are rounded to 9 decimals and ties break by (newer first, id); all
sums run in a fixed order (sorted terms), so rankings do not depend on ``PYTHONHASHSEED``.

What this module does NOT do: it calls no model and no network, reads no clock, uses neither
``random`` nor ``hash()`` (hashing is blake2b), reads no gold (only the oracles read the query they
are bound to), has no reader (answer text is empty for retrievers), no query-time learning, no
stemming, no real MiniLM (inject an embedder), no learned salience (GL), and does not implement
black-box products (HindsightLife is W3).
"""

from __future__ import annotations

import bisect
import hashlib
import heapq
import re
from collections import Counter
from fractions import Fraction
from typing import Any, Callable, Iterable, Sequence

from corpus.lifesim import queries as Qm
from corpus.lifesim.rng import dln, stream
from corpus.lifesim.schema import GATE_POLICIES, MINUTES_PER_DAY, LifeAnswer, Prior as PriorRow, Record, World
from corpus.lifesim.verbalise import affect_scan
from corpus.lifesim.vocab import Vocab, closed_vocab, norm

from .interface import (LifeMemory, count_units, fill_to_budget, make_answer)

__all__ = [
    "tokens", "query_terms", "parse_window", "infer_slot", "BM25Index", "Prior", "Heuristic", "Abstainer",
    "Recency", "RandomK", "BM25", "BM25Time", "DenseStore", "HybridStore", "hashing_embedder",
    "OracleText", "OracleStruct", "OracleStore", "GatedMemory", "ladder_factories", "LADDER_ORDER", "rrf_scores",
    "STOP_WORDS", "K1", "B", "STORES", "make_store", "make_gate",
]

K1 = 1.2  # ASSUMED: Okapi BM25 term-frequency saturation
B = 0.75  # ASSUMED: Okapi BM25 length normalisation
RRF_K = 60  # ASSUMED: reciprocal rank fusion constant
DENSE_DEPTH = 100  # ASSUMED: ranks of each list that enter the fusion

#: Query-side stop words: function words and the instruction boilerplate of the question frames.
STOP_WORDS = frozenset("""
a an the of to in on at by is was were are be been am do did does done have had has i me my mine we you your it
its this that these those what which who whom whose when where how why with for from and or if so as than then
can could would should will shall may might please tell say know remember help check quick quickly forgot
answer reply unknown conf give finish end never stated mentioned came up going looking back over notes note
look out settle wonder just let us
""".split())

_ISO = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
_REL = re.compile(r"\b(yesterday|\d+ days ago|about \w+ (?:week|weeks|month|months) ago)\b")


# ---------------------------------------------------------------------- text helpers


def tokens(text: str) -> list[str]:
    """Index tokens: ``vocab.norm`` (NFKC, casefold, accents stripped, punctuation to space), split."""
    return norm(text).split()


def query_terms(question: str) -> list[str]:
    """Distinct query tokens in sorted order: ISO dates removed (the window handles them), stop words
    dropped."""
    stripped = _ISO.sub(" ", question)
    return sorted({t for t in tokens(stripped) if t not in STOP_WORDS})


def parse_window(question: str, asked_at: int, start_date: str) -> tuple[int, int] | None:
    """Day window (first, last) that the date cues of a question denote, or None.

    ISO dates give single days, 'yesterday', 'N days ago' and 'about N weeks/months ago' are resolved
    against the day of ``asked_at`` with ``queries.resolve_relative``; several cues give their hull
    (so 'between A and B' is [A, B])."""
    ask_day = asked_at // MINUTES_PER_DAY
    wins: list[tuple[int, int]] = []
    for m in _ISO.finditer(question):
        try:
            d = Qm.day_index(start_date, m.group(0))
        except ValueError:
            continue
        wins.append((d, d))
    for m in _REL.finditer(question.lower()):
        w = Qm.resolve_relative(m.group(1), ask_day)
        if w is not None:
            wins.append(w)
    if not wins:
        return None
    return min(w[0] for w in wins), max(w[1] for w in wins)


def infer_slot(question: str) -> str:
    """The slot a question is about, from its text alone: breakfast, closing_time, visit_count,
    vehicle_colour (an article's car), car_colour (the car parked outside), lives_in, works_at, works_as,
    companion, relation, or '' if no rule fits. Keyword rules over the stems shared by the dev and
    test question frames (a blind baseline gets no help from the query's structured fields)."""
    q = " " + norm(question) + " "

    def has(*words: str) -> bool:
        return any((" %s " % w) in q for w in words)

    if has("breakfast"):
        return "breakfast"
    if has("close", "closes", "closing", "shut", "shuts"):
        return "closing_time"
    if "how many" in q or "how often" in q:
        return "visit_count"
    if has("colour", "color"):
        return "car_colour" if has("parked", "outside", "standing") else "vehicle_colour"
    if (has("organisation", "employer", "employed") or "where do i work" in q
            or "where did i work" in q or "where i work" in q):
        return "works_at"
    if "with me" in q or has("joined", "accompanied") or "went with" in q or "came with" in q:
        return "companion"
    if has("job", "living", "work", "occupation"):
        return "works_as"
    if has("live", "lived", "home", "city", "town"):
        return "lives_in"
    if has("related", "relation", "relative") or " to me " in q or re.search(r" who (?:\w+ )?(?:is|was) ", q):
        return "relation"
    return ""


# ------------------------------------------------------------------------- BM25 engine


class BM25Index:
    """Okapi BM25 over a dynamic document set with an inverted index (documents can be removed).

    idf = ln(1 + (N - df + 0.5) / (df + 0.5)) (deterministic ``dln``); the term score is
    idf x tf (k1 + 1) / (tf + k1 (1 - b + b dl / avgdl)); a document's score sums over the sorted
    distinct query terms. Only documents with ``timestamp < asked_at`` are scored."""

    def __init__(self, k1: float = K1, b: float = B) -> None:
        self.k1 = k1
        self.b = b
        self.docs: dict[str, tuple[int, int, tuple[str, ...]]] = {}  # oid -> (timestamp, length, terms)
        self.postings: dict[str, dict[str, int]] = {}
        self.total_len = 0

    def __len__(self) -> int:
        return len(self.docs)

    def add(self, oid: str, toks: Sequence[str], timestamp: int) -> None:
        if oid in self.docs:
            self.remove(oid)
        tf = Counter(toks)
        self.docs[oid] = (timestamp, len(toks), tuple(tf))
        self.total_len += len(toks)
        for t, c in tf.items():
            self.postings.setdefault(t, {})[oid] = c

    def remove(self, oid: str) -> None:
        item = self.docs.pop(oid, None)
        if item is None:
            return
        _, length, terms = item
        self.total_len -= length
        for t in terms:
            post = self.postings.get(t)
            if post is not None:
                post.pop(oid, None)
                if not post:
                    del self.postings[t]

    def idf(self, term: str) -> float:
        n = len(self.docs)
        df = len(self.postings.get(term, ()))
        return dln(1.0 + (n - df + 0.5) / (df + 0.5))

    def scores(self, terms: Iterable[str], asked_at: int | None = None) -> dict[str, float]:
        """BM25 score of every document that contains at least one term (and is visible)."""
        n = len(self.docs)
        if n == 0:
            return {}
        avg = self.total_len / n
        out: dict[str, float] = {}
        for t in sorted(set(terms)):
            post = self.postings.get(t)
            if not post:
                continue
            idf = self.idf(t)
            for oid, tf in post.items():
                ts, dl, _ = self.docs[oid]
                if asked_at is not None and ts >= asked_at:
                    continue
                denom = tf + self.k1 * (1.0 - self.b + self.b * dl / avg)
                out[oid] = out.get(oid, 0.0) + idf * tf * (self.k1 + 1.0) / denom
        return out

    def ranking(self, terms: Iterable[str], asked_at: int | None = None) -> list[tuple[str, float]]:
        """(oid, score) by decreasing score rounded to 9 decimals, then newer first, then id."""
        sc = self.scores(terms, asked_at)
        return sorted(((o, s) for o, s in sc.items()),
                      key=lambda os_: (-round(os_[1], 9), -self.docs[os_[0]][0], os_[0]))


# ---------------------------------------------------------------------- store base class


class _Store(LifeMemory):
    """A system that keeps every ingested record (arrival order) and can forget some."""

    supports_forget = True

    def _reset(self) -> None:
        self._recs: dict[str, Record] = {}

    def _ingest(self, records: Sequence[Record]) -> None:
        for r in records:
            self._add(r)

    def _add(self, r: Record) -> None:
        self._recs[r.id] = r

    def _remove(self, oid: str) -> None:
        self._recs.pop(oid, None)

    def drop(self, oids: Iterable[str]) -> None:
        for o in list(oids):
            self._remove(o)

    def stored_ids(self) -> tuple[str, ...]:
        return tuple(self._recs)

    def _visible(self, asked_at: int) -> list[Record]:
        return [r for r in self._recs.values() if r.timestamp < asked_at]

    def _ranked_records(self, question: str, asked_at: int) -> list[Record]:  # pragma: no cover - abstract
        raise NotImplementedError

    def _query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        ranked = self._ranked_records(question, asked_at)
        fill = fill_to_budget(ranked, budget)
        return make_answer("", fill.items, n_ranked=fill.n_ranked, n_candidates=len(ranked))


class Recency(_Store):
    """B1: the newest records that fit."""

    name = "B1-recency"

    def _ranked_records(self, question: str, asked_at: int) -> list[Record]:
        return [r for r in reversed(self._recs.values()) if r.timestamp < asked_at]


class RandomK(_Store):
    """Random records that fit; the draw depends on (seed, asked_at) only."""

    name = "random-k"

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed
        super().__init__()

    def _ranked_records(self, question: str, asked_at: int) -> list[Record]:
        vis = self._visible(asked_at)
        stream(self._seed, "gate", "RandomK", asked_at).shuffle(vis)
        return vis


class BM25(_Store):
    """B2: Okapi BM25 over the stored records (zero-score records are not delivered)."""

    name = "B2-bm25"

    def __init__(self, k1: float = K1, b: float = B) -> None:
        self._k1 = k1
        self._b = b
        super().__init__()

    def _reset(self) -> None:
        super()._reset()
        self._index = BM25Index(self._k1, self._b)

    def _add(self, r: Record) -> None:
        super()._add(r)
        self._index.add(r.id, tokens(r.text), r.timestamp)

    def _remove(self, oid: str) -> None:
        super()._remove(oid)
        self._index.remove(oid)

    def _ranked_ids(self, question: str, asked_at: int) -> list[str]:
        return [o for o, _ in self._index.ranking(query_terms(question), asked_at)]

    def _ranked_records(self, question: str, asked_at: int) -> list[Record]:
        return [self._recs[o] for o in self._ranked_ids(question, asked_at)]


class BM25Time(BM25):
    """B2t = S-LEX: BM25 with the date window of the question (see the module docstring).

    ``margin`` widens the window by that many days on both sides; ``hard`` removes the records outside
    it (the default keeps them behind the window, because an as-of or aggregate question can be
    answered by a line outside the window it names)."""

    name = "B2t-bm25-time"

    def __init__(self, start_date: str = "2027-01-01", margin: int = 0, hard: bool = False,
                 k1: float = K1, b: float = B) -> None:
        self._start = start_date
        self._margin = margin
        self._hard = hard
        super().__init__(k1, b)

    def window(self, question: str, asked_at: int) -> tuple[int, int] | None:
        w = parse_window(question, asked_at, self._start)
        if w is None:
            return None
        return w[0] - self._margin, w[1] + self._margin

    def _ranked_ids(self, question: str, asked_at: int) -> list[str]:
        ranking = self._index.ranking(query_terms(question), asked_at)
        w = self.window(question, asked_at)
        if w is None:
            return [o for o, _ in ranking]
        inside, outside = [], []
        for o, _ in ranking:
            day = self._index.docs[o][0] // MINUTES_PER_DAY
            (inside if w[0] <= day <= w[1] else outside).append(o)
        return inside if self._hard else inside + outside


# ---------------------------------------------------------------------- dense and hybrid


def hashing_embedder(dim: int = 64) -> Callable[[Sequence[str]], list[list[float]]]:
    """A deterministic bag-of-words feature-hashing embedder (blake2b buckets, unigrams and bigrams).
    A stand-in for MiniLM in tests and in the free grid; it embeds lexical overlap, not meaning."""

    def bucket(tok: str) -> int:
        return int.from_bytes(hashlib.blake2b(tok.encode("utf-8"), digest_size=4).digest(), "big") % dim

    def embed(texts: Sequence[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * dim
            tk = tokens(t)
            for x in tk:
                v[bucket(x)] += 1.0
            for x, y in zip(tk, tk[1:]):
                v[bucket(x + " " + y)] += 0.5
            out.append(v)
        return out

    return embed


def _unit(v: Sequence[float]) -> list[float]:
    s = 0.0
    for x in v:
        s += x * x
    n = s ** 0.5
    return [x / n for x in v] if n > 0 else [0.0] * len(v)


class DenseStore(_Store):
    """C1: cosine similarity of an injected embedder, ``embedder(list_of_texts) -> list_of_vectors``.
    Scores are rounded to 9 decimals; zero or negative similarity is still ranked (a dense retriever has
    no 'no match')."""

    name = "C1-dense"

    def __init__(self, embedder: Callable[[Sequence[str]], Sequence[Sequence[float]]],
                 depth: int | None = None) -> None:
        self._embedder = embedder
        self._depth = depth
        super().__init__()

    def _reset(self) -> None:
        super()._reset()
        self._vec: dict[str, list[float]] = {}

    def _ingest(self, records: Sequence[Record]) -> None:
        if records:
            vecs = self._embedder([r.text for r in records])
            for r, v in zip(records, vecs):
                self._recs[r.id] = r
                self._vec[r.id] = _unit(v)

    def _remove(self, oid: str) -> None:
        super()._remove(oid)
        self._vec.pop(oid, None)

    def _dense_ranking(self, question: str, asked_at: int, depth: int | None) -> list[Record]:
        qv = _unit(self._embedder([question])[0])
        vis = self._visible(asked_at)
        scored = []
        for r in vis:
            v = self._vec[r.id]
            s = 0.0
            for a, b_ in zip(qv, v):
                s += a * b_
            scored.append((round(s, 9), r))
        scored.sort(key=lambda sr: (-sr[0], -sr[1].timestamp, sr[1].id))
        out = [r for _, r in scored]
        return out if depth is None else out[:depth]

    def _ranked_records(self, question: str, asked_at: int) -> list[Record]:
        return self._dense_ranking(question, asked_at, self._depth)


def rrf_scores(rankings: Sequence[Sequence[str]], k: int = RRF_K) -> dict[str, float]:
    """Reciprocal rank fusion: the score of an id is the sum over the rankings that hold it of 1 / (k + rank),
    rank counted from 1."""
    score: dict[str, float] = {}
    for lst in rankings:
        for rank, oid in enumerate(lst, start=1):
            score[oid] = score.get(oid, 0.0) + 1.0 / (k + rank)
    return score


class HybridStore(_Store):
    """C2 = S-HYB: reciprocal rank fusion of the BM25Time ranking and the dense ranking,
    score(r) = sum over the lists of 1 / (rrf_k + rank), rank from 1, each list cut at ``depth``."""

    name = "C2-hybrid"

    def __init__(self, embedder: Callable[[Sequence[str]], Sequence[Sequence[float]]],
                 start_date: str = "2027-01-01", rrf_k: int = RRF_K, depth: int = DENSE_DEPTH,
                 margin: int = 0, hard: bool = False) -> None:
        self._embedder = embedder
        self._start = start_date
        self._rrf_k = rrf_k
        self._depth = depth
        self._margin = margin
        self._hard = hard
        super().__init__()

    def _reset(self) -> None:
        super()._reset()
        self._lex = BM25Time(self._start, self._margin, self._hard)
        self._dense = DenseStore(self._embedder)

    def _ingest(self, records: Sequence[Record]) -> None:
        for r in records:
            self._recs[r.id] = r
        self._lex._ingest(records)
        self._dense._ingest(records)

    def _remove(self, oid: str) -> None:
        super()._remove(oid)
        self._lex._remove(oid)
        self._dense._remove(oid)

    def _ranked_records(self, question: str, asked_at: int) -> list[Record]:
        lex = self._lex._ranked_ids(question, asked_at)[:self._depth]
        den = [r.id for r in self._dense._dense_ranking(question, asked_at, self._depth)]
        score = rrf_scores((lex, den), self._rrf_k)
        order = sorted(score, key=lambda o: (-round(score[o], 12), -self._recs[o].timestamp, o))
        return [self._recs[o] for o in order]


# ------------------------------------------------------------------------- blind answerers


class _Answerer(LifeMemory):
    """A system without a store that answers from the question (and perhaps counts of the stream)."""

    def _answer(self, text: str, **meta: Any) -> LifeAnswer:
        return make_answer(text, (), confidence=None, **meta)


class Abstainer(_Answerer):
    """Always UNKNOWN: scores the abstain share, nothing else."""

    name = "always-abstain"

    def _query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        return make_answer("UNKNOWN", (), abstained=True, confidence=0)


class Prior(_Answerer):
    """B0a: the mode of the generator prior of the slot the question is about (no stream, no context)."""

    name = "B0a-prior"

    def __init__(self, priors: World | Iterable[PriorRow]) -> None:
        rows = priors.priors if isinstance(priors, World) else priors
        self._modes = {p.slot: p.mode() for p in rows}
        super().__init__()

    def _query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        slot = infer_slot(question)
        value = self._modes.get(slot)
        if value is None:
            return make_answer("UNKNOWN", (), abstained=True, confidence=0, slot=slot)
        return make_answer(value, (), confidence=0, slot=slot)


_HEURISTIC_VOCAB = {"breakfast": "breakfast", "vehicle_colour": "vehicle_colour", "car_colour": "car_colour",
                    "lives_in": "lives_in", "works_as": "works_as", "works_at": "works_at",
                    "relation": "relation", "closing_time": "closing_time", "companion": "companion"}


class Heuristic(_Answerer):
    """B0h: the value of the asked slot's closed vocabulary that occurs in the most lines so far (habit /
    constant guess from the stream). Slots without a vocabulary fall back to the prior mode; unknown
    slots abstain. ``vocab_for(slot)`` returns the ``Vocab`` (``Heuristic.for_world`` builds them from the
    world's answer space, which makes this the strongest blind guess, a floor and not a reader)."""

    name = "B0h-heuristic"

    def __init__(self, vocab_for: Callable[[str], Vocab | None], priors: Iterable[PriorRow] = ()) -> None:
        self._vocab_for = vocab_for
        self._modes = {p.slot: p.mode() for p in priors}
        super().__init__()

    @classmethod
    def for_world(cls, world: World) -> "Heuristic":
        cache: dict[str, Vocab | None] = {}

        def vocab_for(slot: str) -> Vocab | None:
            if slot not in cache:
                key = _HEURISTIC_VOCAB.get(slot)
                try:
                    cache[slot] = closed_vocab(world, key) if key else None
                except KeyError:
                    cache[slot] = None
            return cache[slot]

        return cls(vocab_for, world.priors)

    def _reset(self) -> None:
        self._texts: list[tuple[int, str]] = []
        self._counts: dict[str, Counter] = {}
        self._ptr: dict[str, int] = {}

    def _ingest(self, records: Sequence[Record]) -> None:
        self._texts.extend((r.timestamp, r.text) for r in records)

    def _query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        slot = infer_slot(question)
        voc = self._vocab_for(slot) if slot else None
        if voc is None:
            value = self._modes.get(slot)
            if value is None:
                return make_answer("UNKNOWN", (), abstained=True, confidence=0, slot=slot)
            return make_answer(value, (), confidence=0, slot=slot)
        cnt = self._counts.setdefault(slot, Counter())
        i = self._ptr.get(slot, 0)
        for ts, text in self._texts[i:]:
            for v in voc.matches(text):
                cnt[v] += 1
        self._ptr[slot] = len(self._texts)
        if not cnt:
            return make_answer("UNKNOWN", (), abstained=True, confidence=0, slot=slot)
        best = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        return make_answer(best, (), confidence=0, slot=slot)


# --------------------------------------------------------------------------------- oracles


class OracleText(_Store):
    """The evidence lines of the bound query as the context (chronological, within the budget); fails only
    where the evidence exceeds the budget. Needs ``bind(query)``."""

    name = "oracle-text"
    needs_query = True

    def _query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        q = self._bound
        if q is None:
            raise RuntimeError("OracleText needs bind(query) before a query")
        ev = [self._recs[o] for o in q.evidence_oids if o in self._recs and self._recs[o].timestamp < asked_at]
        ev.sort(key=lambda r: (r.timestamp, r.id))
        fill = fill_to_budget(ev, budget)
        return make_answer("", fill.items, n_evidence=len(q.evidence_oids), exceeds_budget=len(fill.items) < len(ev))


class OracleStruct(LifeMemory):
    """Answers from the structure: the gold of the bound query found by the independent solver
    ``gold_slow`` (``source='fast'`` takes ``query.gold``). Delivers no context. Needs ``bind(query)``."""

    name = "oracle-struct"
    needs_query = True

    def __init__(self, world: World, source: str = "slow") -> None:
        if source not in ("slow", "fast"):
            raise ValueError("source must be 'slow' or 'fast'")
        self._world = world
        self._source = source
        super().__init__()

    def _query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        q = self._bound
        if q is None:
            raise RuntimeError("OracleStruct needs bind(query) before a query")
        try:
            gold = Qm.gold_slow(self._world, q) if self._source == "slow" else q.gold
            text, unknown = gold.value, gold.kind == "unknown"
        except Qm.AmbiguousGold:
            text, unknown = "AMBIGUOUS", False
        return make_answer(text, (), abstained=unknown, confidence=100, evidence_ids=q.evidence_oids)


class OracleStore(BM25Time):
    """BM25Time over a store that holds only the lines in ``need`` (capture is perfect, retrieval is not):
    the decomposition's stored-gold ceiling for the lexical store."""

    name = "oracle-store"

    def __init__(self, need: Iterable[str], start_date: str = "2027-01-01", margin: int = 0,
                 hard: bool = False) -> None:
        self._need = frozenset(need)
        super().__init__(start_date, margin, hard)

    def _ingest(self, records: Sequence[Record]) -> None:
        for r in records:
            if r.id in self._need:
                self._add(r)


# --------------------------------------------------------------------------------- the gate


class GatedMemory(LifeMemory):
    """The online retention gate around a store (see the module docstring for the policies).

    ``inner`` must support forgetting (a ``_Store``); ``R`` in (0, 1]; ``need`` is read by GO only.
    ``stats()`` reports capacity, stored words, words seen, evictions and rejections; ``stored_ids()``
    is the retained set in arrival order."""

    accepts_heartbeat = True

    def __init__(self, inner: LifeMemory, policy: str, R: float, seed: int = 0, *,
                 need: Iterable[str] = (), name: str | None = None) -> None:
        if policy not in GATE_POLICIES:
            raise ValueError("policy must be one of %s, got %r" % (GATE_POLICIES, policy))
        if policy == "GL":
            raise NotImplementedError("GL (learned salience) is part of W4 and is not implemented")
        if not (0.0 < R <= 1.0):
            raise ValueError("R must be in (0, 1], got %r" % (R,))
        if not inner.supports_forget:
            raise TypeError("the inner store of a gate must support forgetting")
        self._inner = inner
        self._policy = policy
        self._R = float(R)
        self._ratio = Fraction(repr(float(R)))
        self._seed = seed
        self._need = frozenset(need)
        self.name = name or "gate:%s@%g>%s" % (policy, R, inner.name)
        self.query_mutates_state = "read_only"
        super().__init__()

    # -- state
    def _reset(self) -> None:
        self._inner.reset(self._card)
        self._rng = stream(self._seed, "gate", self._policy)
        self._seen_words = 0
        self._stored_words = 0
        self._seq = 0
        self._store: dict[str, Record] = {}
        self._words: dict[str, int] = {}
        self._cur: dict[str, tuple] = {}
        self._heap: list[tuple] = []
        self._evicted = 0
        self._rejected = 0
        self._tok_seen: set[str] = set()
        self._tok_counts: Counter = Counter()
        self._tok_total = 0
        self._lines_seen = 0
        self._df: Counter = Counter()
        self._post: dict[str, set[str]] = {}
        self._toks: dict[str, tuple[str, ...]] = {}
        self._h_sorted: list[float] = []
        self._chan_hist: dict[str, list[float]] = {}

    @property
    def capacity(self) -> int | None:
        """K(t) = floor(R x words seen) (None for the unbounded policy ALL)."""
        if self._policy == "ALL":
            return None
        return (self._ratio.numerator * self._seen_words) // self._ratio.denominator

    def stored_ids(self) -> tuple[str, ...]:
        return tuple(self._store)

    def weights(self) -> dict[str, float]:
        """Current retention weight of every retained record (introspection for tests and reports)."""
        return {oid: self._cur[oid][0] for oid in self._store}

    # -- weights
    def _weight(self, r: Record) -> float:
        p = self._policy
        if p in ("ALL", "GU"):
            return 0.0
        if p == "GR":
            return float(r.timestamp)
        if p == "GO":
            return 1.0 if r.id in self._need else 0.0
        if p == "GA":
            return float(len(affect_scan(r.text)))
        if p == "GH":
            h = r.heartbeat
            if h is None:
                hs = self._h_sorted
                return hs[len(hs) // 2] if hs else 0.5
            bisect.insort(self._h_sorted, h)
            return float(h)
        if p == "GTN":
            h = r.heartbeat
            if h is None:
                return 0.5
            hist = self._chan_hist.setdefault(r.channel, [])
            n = len(hist)
            val = ((bisect.bisect_left(hist, h) + bisect.bisect_right(hist, h)) / 2.0) / n if n else 0.5
            bisect.insort(hist, h)
            return round(val, 9)
        toks = tokens(r.text)
        if p == "GN":
            distinct = set(toks)
            fresh = sum(1 for t in distinct if t not in self._tok_seen)
            self._tok_seen |= distinct
            return round(fresh / len(distinct), 9) if distinct else 0.0
        if p == "GS":
            denom = self._tok_total + len(self._tok_counts) + 1.0
            s = 0.0
            for t in toks:
                s += -dln((self._tok_counts.get(t, 0) + 1.0) / denom)
            self._tok_counts.update(toks)
            self._tok_total += len(toks)
            return round(s / len(toks), 9) if toks else 0.0
        if p == "GM":
            return 0.0  # starts at zero; _gm_bump raises it when later lines repeat its rare tokens
        raise AssertionError(p)  # pragma: no cover

    def _gm_bump(self, r: Record) -> None:
        """GM: before the new line is registered, +1 on every retained line that shares a rare token with it."""
        distinct = sorted(set(tokens(r.text)))
        cap = max(3, int(0.01 * self._lines_seen))
        bumped: set[str] = set()
        for t in distinct:
            if 1 <= self._df.get(t, 0) <= cap:
                bumped |= self._post.get(t, set())
        for oid in sorted(bumped):
            w, tb, seq = self._cur[oid]
            self._cur[oid] = (w + 1.0, tb, seq)
            heapq.heappush(self._heap, (w + 1.0, tb, seq, oid))
        self._lines_seen += 1
        self._df.update(distinct)
        self._pending_toks = tuple(distinct)

    def _evict_lowest(self) -> str:
        while True:
            w, tb, seq, oid = heapq.heappop(self._heap)
            if self._cur.get(oid) == (w, tb, seq):
                return oid

    # -- protocol
    def _ingest(self, records: Sequence[Record]) -> None:
        in_batch: set[str] = set()
        removed_old: list[str] = []
        policy = self._policy
        for r in records:
            if r.id in self._store or r.id in in_batch:
                raise ValueError("duplicate record id %r" % (r.id,))
            w = count_units(r.text)
            self._seen_words += w
            seq = self._seq
            self._seq += 1
            tb = self._rng.u()
            if policy == "GM":
                self._gm_bump(r)
            weight = self._weight(r)
            if policy == "GR":
                tb = float(seq)
            self._store[r.id] = r
            self._words[r.id] = w
            self._cur[r.id] = (weight, tb, seq)
            self._stored_words += w
            heapq.heappush(self._heap, (weight, tb, seq, r.id))
            in_batch.add(r.id)
            if policy == "GM":
                self._toks[r.id] = self._pending_toks
                for t in self._pending_toks:
                    self._post.setdefault(t, set()).add(r.id)
            if policy == "ALL":
                continue
            cap = self.capacity
            while self._stored_words > cap:
                oid = self._evict_lowest()
                self._stored_words -= self._words.pop(oid)
                del self._store[oid]
                del self._cur[oid]
                if policy == "GM":
                    for t in self._toks.pop(oid, ()):
                        s = self._post.get(t)
                        if s is not None:
                            s.discard(oid)
                self._evicted += 1
                if oid in in_batch:
                    self._rejected += 1
                    in_batch.discard(oid)
                else:
                    removed_old.append(oid)
        survivors = [r for r in records if r.id in in_batch]
        if removed_old:
            self._inner.drop(removed_old)
        if survivors:
            self._inner.ingest(survivors)

    def _query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        return self._inner.query(question, asked_at, budget)

    def bind(self, query: Any) -> None:
        # Never read here: a gate has no use for a query (GO gets its need set at construction).
        self._bound = query
        if self._inner.needs_query:
            self._inner.bind(query)

    def _stats(self) -> dict:
        return {"policy": self._policy, "R": self._R, "capacity": self.capacity,
                "stored_words": self._stored_words, "words_seen": self._seen_words,
                "evicted": self._evicted, "rejected_at_arrival": self._rejected,
                "inner": self._inner.name}


# ---------------------------------------------------------------------------------- factories

STORES = ("S-LEX", "S-HYB")


def make_store(kind: str, start_date: str = "2027-01-01",
               embedder: Callable[[Sequence[str]], Sequence[Sequence[float]]] | None = None) -> _Store:
    """The retrieval store of experiment X1: ``S-LEX`` = BM25 plus the date window, ``S-HYB`` = that plus a dense
    store (``embedder`` is required: inject MiniLM, or ``hashing_embedder`` for the free grid) fused by RRF."""
    if kind == "S-LEX":
        return BM25Time(start_date)
    if kind == "S-HYB":
        if embedder is None:
            raise ValueError("S-HYB needs an embedder")
        return HybridStore(embedder, start_date)
    raise ValueError("store must be one of %s, got %r" % (STORES, kind))


def make_gate(world: World, policy: str, R: float, seed: int = 0, *, store: str = "S-LEX",
              need: Iterable[str] = (), embedder: Callable[[Sequence[str]], Sequence[Sequence[float]]] | None = None
              ) -> GatedMemory:
    """``GatedMemory`` over the chosen store for one world: the arm GH[...] / GU / GR / ... of X1 at retention
    ratio ``R``. The channel arm is not a property of the gate: it is the ``heartbeat`` of the records the
    harness feeds it (``records_from_world(world, obs, channel=make_channel(...))``)."""
    return GatedMemory(make_store(store, world.cfg.start_date, embedder), policy, R, seed, need=need)


LADDER_ORDER = ("B0a", "B0h", "B1", "random", "B2", "B2t", "oracle_text", "oracle_struct", "oracle_store")


def ladder_factories(world: World, *, need: Iterable[str] = (), seed: int = 0,
                     start_date: str | None = None) -> dict[str, Callable[[], LifeMemory]]:
    """Factories of the evidence-level ladder of X0 for one world, in ``LADDER_ORDER``: blind floors
    (B0a prior, B0h heuristic), B1 recency, random, B2 BM25, B2t BM25 with the date window, and the three
    oracles (the oracle store holds the lines in ``need``)."""
    sd = start_date or world.cfg.start_date
    need = frozenset(need)
    return {
        "B0a": lambda: Prior(world),
        "B0h": lambda: Heuristic.for_world(world),
        "B1": lambda: Recency(),
        "random": lambda: RandomK(seed),
        "B2": lambda: BM25(),
        "B2t": lambda: BM25Time(sd),
        "oracle_text": lambda: OracleText(),
        "oracle_struct": lambda: OracleStruct(world),
        "oracle_store": lambda: OracleStore(need, sd),
    }
