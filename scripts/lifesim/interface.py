"""The interface between a LifeSim world and a memory system.

What this module provides
-------------------------
* The data types a system exchanges with the harness, re-exported from the schema:
  ``Record`` (what is ingested per observation: id = oid, text, timestamp in minutes,
  channel kind, ``source`` only in the provenance arm, ``heartbeat`` only for systems that
  accept it), ``ContextItem`` and ``LifeAnswer``.
* ``LifeMemory``: the base class of every system. ``reset(meta)`` (the card only),
  ``ingest(batch) -> Cost``, ``query(question, asked_at, budget) -> LifeAnswer`` and
  ``stats()``. The base class enforces the protocol: records arrive in non-decreasing time
  order (online, single pass), a heartbeat is stripped unless ``accepts_heartbeat``, a query
  sees only records with ``timestamp < asked_at`` (the convention of ``queries.gold_slow``), and
  the delivered context is truncated to the budget with the overflow logged
  (``enforce_budget``). A query is read-only unless ``query_mutates_state`` says otherwise.
* ``count_units`` (whitespace words, the arena unit), ``fill_to_budget`` (the ONE fill policy
  of all arms: rank order, add while it fits, stop at the first item that does not fit, so a
  context is always a prefix of the ranking and recall is monotone in the budget; an optional
  padding pass fills the remainder), ``make_answer`` and ``meta_pairs``.
* ``wrap_arena_adapter(adapter, budget_param)``: an arena ``MemoryAdapter`` (reset, ingest,
  query, see ``scripts/arena/adapter.py``) as a ``LifeMemory`` (the card is ingested as record 0
  and the context budget is written to the adapter attribute ``budget_param`` before a query).
  ``ArenaView(memory, budget)`` / ``as_arena_adapter`` is the inverse: a ``LifeMemory`` as an
  arena adapter, which ``arena.adapter.validate_adapter`` accepts.
* The harness pieces needed to run a system at evidence level (no reader, no model):
  ``records_from_world``, ``run_stream`` (reset, ingest in time order, queries interleaved and
  read-only), ``evidence_metrics`` (gold-in-context: complete@C and recall@C, stored-gold) and
  ``summarise_evidence`` (per family and macro).

Conventions: time is integer minutes since 00:00 of day 0; a query asked at ``t_ask`` sees the
records with ``t_obs < t_ask``; the budget ``C`` is counted in whitespace words; the context is
delivered in chronological order. A system never receives a ``Query`` except the oracles, which
the harness binds with ``bind(query)`` (``needs_query`` is True for them only).

What this module does NOT do: it calls no model and no network, reads no clock (so ingest and
query costs report model calls and tokens and leave wall time unobservable), uses neither
``random`` nor ``hash()``, owns no system logic (see ``systems``), does not implement the ingest
granularity dial (records are delivered in the batches between queries), and does not reconstruct
a context that a black box did not report (ids it reports that the harness never ingested are
kept as ids with the metadata flag ``unobservable_ids``).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Callable, Iterable, NamedTuple, Sequence

from corpus.lifesim.schema import (CHANNELS, MINUTES_PER_DAY, Card, ContextItem, LifeAnswer, Obs,
                                   Query, Record, World)

try:  # the arena contract is optional: the rest of the module works without it
    from arena.adapter import Answer as ArenaAnswer
    from arena.adapter import Cost, Measure, MUTATION_MODES

    HAVE_ARENA = True
except ImportError:  # pragma: no cover - exercised only where scripts/arena is not importable
    HAVE_ARENA = False
    ArenaAnswer = None  # type: ignore[assignment,misc]
    MUTATION_MODES = ("read_only", "mutates_by_design", "unknown")

    @dataclass(frozen=True)
    class Measure:  # type: ignore[no-redef]
        """Minimal stand-in for ``arena.adapter.Measure``."""

        value: int | None = 0
        observability: str = "native"
        lower_bound: bool = False

        def __add__(self, other: "Measure") -> "Measure":
            if self.value is None or other.value is None:
                return Measure(None, "unobservable")
            return Measure(self.value + other.value, self.observability, self.lower_bound or other.lower_bound)

    @dataclass(frozen=True)
    class Cost:  # type: ignore[no-redef]
        """Minimal stand-in for ``arena.adapter.Cost``."""

        model_calls: Measure = Measure()
        input_tokens: Measure = Measure()
        output_tokens: Measure = Measure()
        wall_microseconds: Measure = Measure()
        _FIELDS = ("model_calls", "input_tokens", "output_tokens", "wall_microseconds")

        def __add__(self, other: "Cost") -> "Cost":
            return Cost(**{f: getattr(self, f) + getattr(other, f) for f in Cost._FIELDS})

__all__ = [
    "Record", "ContextItem", "LifeAnswer", "Card", "Cost", "Measure", "MUTATION_MODES", "HAVE_ARENA",
    "LifeMemory", "Fill", "count_units", "fill_to_budget", "enforce_budget", "make_answer", "meta_pairs",
    "meta_dict", "zero_cost", "cost_pairs", "card_record", "ArenaWrapped", "wrap_arena_adapter",
    "ArenaView", "as_arena_adapter", "records_from_world", "run_stream", "evidence_metrics",
    "summarise_evidence", "visible", "CARD_ID",
]

CARD_ID = "card"


# ------------------------------------------------------------------------------ small helpers


def count_units(text: str) -> int:
    """Whitespace-separated words, the arena unit for stored words and context words."""
    return len(text.split())


def visible(timestamp: int, asked_at: int) -> bool:
    """A record is visible to a query iff it was observed strictly before the question."""
    return timestamp < asked_at


def meta_pairs(values: dict | None = None, **more: Any) -> tuple[tuple[str, str], ...]:
    """Sorted (key, str(value)) pairs for ``LifeAnswer.metadata``."""
    merged = dict(values or {})
    merged.update(more)
    return tuple((str(k), str(v)) for k, v in sorted(merged.items()))


def meta_dict(answer: LifeAnswer) -> dict:
    """The metadata pairs of an answer as a dict of strings."""
    return dict(answer.metadata)


def zero_cost() -> Any:
    """Cost of an operation with no model call: zero calls and tokens, wall time unobservable
    (the library reads no clock; the runner may measure it)."""
    return Cost(model_calls=Measure(0), input_tokens=Measure(0), output_tokens=Measure(0),
                wall_microseconds=Measure(None, "unobservable"))


def cost_pairs(cost: Any) -> tuple[tuple[str, float], ...]:
    """The known fields of a ``Cost`` as ``LifeAnswer.cost`` pairs."""
    out = []
    for name in ("model_calls", "input_tokens", "output_tokens", "wall_microseconds"):
        m = getattr(cost, name, None)
        if m is not None and getattr(m, "value", None) is not None:
            out.append((name, float(m.value)))
    return tuple(out)


class Fill(NamedTuple):
    """Result of ``fill_to_budget``: the chosen items, their words, and how many of them came
    from the ranked prefix (the rest is padding)."""

    items: tuple
    words: int
    n_ranked: int


def fill_to_budget(ranked: Iterable[Any], budget: int, *, size: Callable[[Any], int] | None = None,
                   pad: Iterable[Any] = (), key: Callable[[Any], Any] | None = None) -> Fill:
    """THE fill policy of every arm: take items in rank order while they fit, stop at the first that
    does not (so the result is a prefix of the ranking and monotone in ``budget``). With ``pad`` the
    remaining words are then filled from the padding sequence, skipping items already chosen (by
    ``key``, default identity) and items that do not fit. Reported padded (``items``) and unpadded
    (``items[:n_ranked]``)."""
    sz = size or (lambda it: count_units(it.text))
    chosen: list = []
    used = 0
    for it in ranked:
        w = sz(it)
        if used + w > budget:
            break
        chosen.append(it)
        used += w
    n_ranked = len(chosen)
    padding = list(pad)
    if padding:
        kf = key or id
        taken = {kf(it) for it in chosen}
        for it in padding:
            k = kf(it)
            if k in taken:
                continue
            w = sz(it)
            if used + w <= budget:
                chosen.append(it)
                taken.add(k)
                used += w
    return Fill(tuple(chosen), used, n_ranked)


def make_answer(text: str = "", records: Iterable[Record] = (), *, abstained: bool = False,
                confidence: int | None = None, evidence_ids: Sequence[str] | None = None,
                model_calls: int = 0, input_tokens: int = 0, output_tokens: int = 0,
                **metadata: Any) -> LifeAnswer:
    """A ``LifeAnswer`` whose context is ``records`` in chronological order (ties by id)."""
    recs = sorted(records, key=lambda r: (r.timestamp, r.id))
    ctx = tuple(ContextItem(text=r.text, timestamp=r.timestamp, oid=r.id) for r in recs)
    words = sum(count_units(r.text) for r in recs)
    ev = tuple(evidence_ids) if evidence_ids is not None else tuple(r.id for r in recs)
    return LifeAnswer(
        text=text, evidence_ids=ev, context=ctx, context_tokens=words, abstained=abstained,
        confidence=confidence,
        cost=(("input_tokens", float(input_tokens)), ("model_calls", float(model_calls)),
              ("output_tokens", float(output_tokens))),
        metadata=meta_pairs(metadata))


def enforce_budget(answer: LifeAnswer, budget: int) -> tuple[LifeAnswer, int]:
    """Truncate the delivered context to ``budget`` words (a prefix of the context, whole items) and log
    the overflow: returns (answer, words removed). An answer within budget is returned unchanged."""
    total = sum(count_units(c.text) for c in answer.context)
    if total <= budget:
        return answer, 0
    kept: list[ContextItem] = []
    used = 0
    for c in answer.context:
        w = count_units(c.text)
        if used + w > budget:
            break
        kept.append(c)
        used += w
    dropped = {c.oid for c in answer.context} - {c.oid for c in kept}
    meta = dict(answer.metadata)
    meta["overflow_words"] = str(total - used)
    return dataclasses.replace(
        answer, context=tuple(kept), context_tokens=used,
        evidence_ids=tuple(e for e in answer.evidence_ids if e not in dropped),
        metadata=meta_pairs(meta)), total - used


# --------------------------------------------------------------------------------- LifeMemory


def card_record(meta: Any) -> Record | None:
    """The card (name and role) as the text of record 0, or None when there is no card."""
    if meta is None:
        return None
    name = getattr(meta, "name", None) if not isinstance(meta, dict) else meta.get("name")
    role = getattr(meta, "role", "diarist") if not isinstance(meta, dict) else meta.get("role", "diarist")
    if not name:
        return None
    return Record(id=CARD_ID, text="The diarist is %s, a %s." % (name, role), timestamp=0, channel="note")


class LifeMemory:
    """Base class of every LifeSim system. Subclasses implement ``_reset``, ``_ingest(records)`` and
    ``_query(question, asked_at, budget)`` and may override ``_ingest_cost``, ``stored_ids``, ``_stats``.

    Class attributes: ``name``; ``accepts_heartbeat`` (the harness strips the channel reading from
    the records of a system that does not accept it); ``query_mutates_state`` (one of
    ``MUTATION_MODES``); ``needs_query`` (oracles only: the harness calls ``bind(query)`` before a
    query); ``supports_forget`` (the system can drop a stored record: required of the inner store of
    a ``GatedMemory``)."""

    name = "life-memory"
    accepts_heartbeat = False
    query_mutates_state = "read_only"
    needs_query = False
    supports_forget = False

    def __init__(self) -> None:
        self._card: Any = None
        self._bound: Any = None
        self._last_ts: int | None = None
        self._n_records = 0
        self._n_words = 0
        self._reset()

    # -- protocol
    def reset(self, meta: Any = None) -> None:
        """Discard all state. ``meta`` is the card (a ``Card`` or a dict with name and role) and nothing else."""
        self._card = meta
        self._bound = None
        self._last_ts = None
        self._n_records = 0
        self._n_words = 0
        self._reset()

    def ingest(self, batch: Sequence[Record]) -> Any:
        """Store records, which must arrive in non-decreasing time order. Returns a ``Cost``."""
        recs: list[Record] = []
        for r in batch:
            if not isinstance(r, Record):
                raise TypeError("ingest takes Record objects, got %r" % (type(r),))
            if r.channel not in CHANNELS:
                raise ValueError("unknown channel %r" % (r.channel,))
            if self._last_ts is not None and r.timestamp < self._last_ts:
                raise ValueError("records must arrive in non-decreasing time order "
                                 "(got %d after %d)" % (r.timestamp, self._last_ts))
            self._last_ts = r.timestamp
            if r.heartbeat is not None and not self.accepts_heartbeat:
                r = dataclasses.replace(r, heartbeat=None)
            recs.append(r)
            self._n_records += 1
            self._n_words += count_units(r.text)
        self._ingest(recs)
        return self._ingest_cost(recs)

    def query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        """Answer from memory alone. The context is truncated to ``budget`` words (overflow logged)."""
        if not isinstance(question, str):
            raise TypeError("question must be a string")
        if budget < 0:
            raise ValueError("budget must be non-negative")
        answer = self._query(question, int(asked_at), int(budget))
        answer, _ = enforce_budget(answer, int(budget))
        return answer

    def bind(self, query: Any) -> None:
        """Hand the current ``Query`` to an oracle. Systems with ``needs_query`` False must never read it."""
        self._bound = query

    def stats(self) -> dict:
        """Counters of the system (records and words ingested, plus whatever the subclass adds)."""
        out = {"name": self.name, "records_ingested": self._n_records, "words_ingested": self._n_words,
               "stored_records": len(self.stored_ids())}
        out.update(self._stats())
        return out

    def stored_ids(self) -> tuple[str, ...]:
        """Ids of the records currently in the store, in arrival order."""
        return ()

    def drop(self, oids: Iterable[str]) -> None:
        """Forget stored records (only where ``supports_forget``)."""
        raise NotImplementedError("%s cannot forget records" % self.name)

    # -- to override
    def _reset(self) -> None:
        pass

    def _ingest(self, records: Sequence[Record]) -> None:
        pass

    def _ingest_cost(self, records: Sequence[Record]) -> Any:
        return zero_cost()

    def _query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        raise NotImplementedError

    def _stats(self) -> dict:
        return {}


# ------------------------------------------------------------------------- arena: both ways


class ArenaWrapped(LifeMemory):
    """An arena ``MemoryAdapter`` presented as a ``LifeMemory`` (``wrap_arena_adapter``).

    ``reset(card)`` resets the adapter and ingests the card as record 0; ``ingest`` forwards the
    records as dicts ``{id, day, timestamp, text, channel[, source][, heartbeat]}``; a query writes the
    context budget to the adapter attribute ``budget_param`` (a name, or a callable ``f(adapter,
    budget)``), calls ``adapter.query(question, asked_at)`` and maps the arena ``Answer``. Ids the
    adapter reports that were ingested become context items; unknown ids stay ids only."""

    def __init__(self, adapter: Any, budget_param: str | Callable[[Any, int], None] | None = None, *,
                 asked_at_unit: str = "minute", name: str | None = None,
                 accepts_heartbeat: bool = False) -> None:
        if asked_at_unit not in ("minute", "day"):
            raise ValueError("asked_at_unit must be 'minute' or 'day'")
        self._adapter = adapter
        self._budget_param = budget_param
        self._unit = asked_at_unit
        self.name = name or "arena:" + str(getattr(adapter, "name", "adapter"))
        self.accepts_heartbeat = accepts_heartbeat
        self.query_mutates_state = getattr(adapter, "query_mutates_state", "unknown")
        self._by_id: dict[str, Record] = {}
        super().__init__()

    def _dict_of(self, r: Record) -> dict:
        d = {"id": r.id, "day": r.timestamp // MINUTES_PER_DAY, "timestamp": r.timestamp, "text": r.text,
             "channel": r.channel}
        if r.source:
            d["source"] = r.source
        if r.heartbeat is not None:
            d["heartbeat"] = r.heartbeat
        return d

    def _reset(self) -> None:
        self._adapter.reset()
        self._by_id = {}
        self._ingest_cost_total = zero_cost()
        card = card_record(self._card)
        if card is not None:
            self._by_id[card.id] = card
            self._ingest_cost_total = self._adapter.ingest([self._dict_of(card)])

    def _ingest(self, records: Sequence[Record]) -> None:
        for r in records:
            self._by_id[r.id] = r
        self._last_cost = self._adapter.ingest([self._dict_of(r) for r in records])

    def _ingest_cost(self, records: Sequence[Record]) -> Any:
        return self._last_cost

    def stored_ids(self) -> tuple[str, ...]:
        return tuple(self._by_id)

    def _query(self, question: str, asked_at: int, budget: int) -> LifeAnswer:
        bp = self._budget_param
        if callable(bp):
            bp(self._adapter, budget)
        elif bp:
            setattr(self._adapter, bp, budget)
        at = asked_at if self._unit == "minute" else asked_at // MINUTES_PER_DAY
        ans = self._adapter.query(question, at)
        known = [self._by_id[i] for i in ans.evidence_ids if i in self._by_id]
        unknown = [i for i in ans.evidence_ids if i not in self._by_id]
        words = sum(count_units(r.text) for r in known)
        meta = {str(k): v for k, v in dict(getattr(ans, "system_metadata", {}) or {}).items()}
        if unknown:
            meta["unobservable_ids"] = ",".join(unknown)
        return LifeAnswer(
            text=ans.text, evidence_ids=tuple(ans.evidence_ids),
            context=tuple(ContextItem(text=r.text, timestamp=r.timestamp, oid=r.id)
                          for r in sorted(known, key=lambda r: (r.timestamp, r.id))),
            context_tokens=int(ans.context_tokens or words), abstained=bool(ans.abstained),
            cost=cost_pairs(ans.cost), metadata=meta_pairs(meta))


def wrap_arena_adapter(adapter: Any, budget_param: str | Callable[[Any, int], None] | None = None,
                       **kwargs: Any) -> ArenaWrapped:
    """An arena ``MemoryAdapter`` as a ``LifeMemory`` (see ``ArenaWrapped``)."""
    return ArenaWrapped(adapter, budget_param, **kwargs)


class ArenaView:
    """A ``LifeMemory`` presented as an arena ``MemoryAdapter`` (``as_arena_adapter``).

    Records are dicts with ``id``, ``text`` and ``timestamp`` (minutes) or ``day``; a batch is sorted by
    time before it is ingested. ``asked_at`` is in days (``asked_at_unit='day'``, the arena fixtures)
    or minutes; None means after the last record. The arena cannot hold an answer that is both
    abstained and non-empty, so an abstention is reported with empty text."""

    def __init__(self, memory: LifeMemory, budget: int, *, asked_at_unit: str = "day",
                 channel: str = "note", name: str | None = None) -> None:
        if not HAVE_ARENA:  # pragma: no cover
            raise ImportError("arena.adapter is not importable")
        self._mem = memory
        self._budget = int(budget)
        self._unit = asked_at_unit
        self._channel = channel
        self.name = name or "view:" + memory.name
        self.query_mutates_state = memory.query_mutates_state
        self._last = 0

    def reset(self) -> None:
        self._mem.reset(None)
        self._last = 0

    def ingest(self, records: list[dict]) -> Any:
        recs = []
        for d in records:
            ts = d.get("timestamp")
            if ts is None:
                ts = int(d.get("day", 0)) * MINUTES_PER_DAY
            ch = d.get("channel", self._channel)
            recs.append(Record(id=str(d["id"]), text=str(d["text"]), timestamp=int(ts),
                               channel=ch if ch in CHANNELS else self._channel,
                               heartbeat=d.get("heartbeat")))
        recs.sort(key=lambda r: r.timestamp)
        if recs:
            self._last = max(self._last, recs[-1].timestamp)
        return self._mem.ingest(recs)

    def query(self, question: str, asked_at: Any = None) -> Any:
        if asked_at is None:
            at = self._last + 1
        else:
            at = int(asked_at) * (MINUTES_PER_DAY if self._unit == "day" else 1)
        la = self._mem.query(question, at, self._budget)
        return ArenaAnswer(text="" if la.abstained else la.text, evidence_ids=list(la.evidence_ids),
                           context_tokens=la.context_tokens, abstained=la.abstained,
                           cost=zero_cost(), system_metadata=dict(la.metadata))


def as_arena_adapter(memory: LifeMemory, budget: int, **kwargs: Any) -> ArenaView:
    """A ``LifeMemory`` as an arena ``MemoryAdapter`` (see ``ArenaView``)."""
    return ArenaView(memory, budget, **kwargs)


# --------------------------------------------------------------------------------- the harness


def records_from_world(world: World, obs: Sequence[Obs], *, channel: Any = None,
                       provenance: bool = False) -> list[Record]:
    """One ``Record`` per observation in stream order: id = oid, text, timestamp = t_obs, channel kind,
    ``source`` only in the provenance arm (the teller's entity id), ``heartbeat`` = the channel reading
    (``channel`` or ``world.channel``; None where there is none). H is never part of the text."""
    ch = channel if channel is not None else world.channel
    if len(obs) != len(world.obs_specs):
        raise ValueError("obs must hold one line per observation spec")
    out = []
    for spec, o in zip(world.obs_specs, obs):
        if spec.oid != o.oid:
            raise ValueError("obs and obs_specs are not in the same order (%s vs %s)" % (spec.oid, o.oid))
        hb = ch.value(o.oid) if ch is not None else None
        out.append(Record(id=o.oid, text=o.text, timestamp=o.t_obs, channel=o.channel,
                          source=spec.source if provenance else "", heartbeat=hb))
    return out


def run_stream(memory: LifeMemory, records: Sequence[Record], queries: Sequence[Query], budget: int, *,
               card: Any = None, on_query: Callable[[Query, LifeAnswer, LifeMemory], None] | None = None
               ) -> list[tuple[Query, LifeAnswer]]:
    """Online single pass: reset (card only), then for every query in time order ingest the records
    observed before it and ask it. Queries are read-only; oracles are bound to the current query
    (the only place a ``Query`` reaches a system). ``on_query(query, answer, memory)`` is called right after
    each question, while the store is in the state the question saw (use it for stored-gold:
    ``evidence_metrics(query, answer, memory.stored_ids())``). Returns (query, answer) pairs in query order."""
    memory.reset(card)
    recs = sorted(range(len(records)), key=lambda i: (records[i].timestamp, i))
    ordered = [records[i] for i in recs]
    pos = 0
    out: list[tuple[Query, LifeAnswer]] = []
    for q in sorted(queries, key=lambda x: (x.t_ask, x.qid)):
        end = pos
        while end < len(ordered) and ordered[end].timestamp < q.t_ask:
            end += 1
        if end > pos:
            memory.ingest(ordered[pos:end])
            pos = end
        if memory.needs_query:
            memory.bind(q)
        ans = memory.query(q.text, q.t_ask, budget)
        if on_query is not None:
            on_query(q, ans, memory)
        out.append((q, ans))
    return out


def evidence_metrics(query: Query, answer: LifeAnswer, stored: Iterable[str] | None = None) -> dict:
    """Gold-in-context at evidence level for one answer: ``complete`` (every evidence line is in the
    delivered context), ``recall`` (share of the evidence lines in it), ``n_evidence`` and the context
    words; with ``stored`` (the ids in the store at the time) also ``stored_complete`` and
    ``stored_recall``. Abstention items (no evidence) have ``complete`` and ``recall`` None."""
    ev = tuple(query.evidence_oids)
    in_ctx = {c.oid for c in answer.context}
    row = {"qid": query.qid, "family": query.family, "n_evidence": len(ev),
           "context_words": sum(count_units(c.text) for c in answer.context)}
    if ev:
        got = sum(1 for o in ev if o in in_ctx)
        row["complete"] = got == len(ev)
        row["recall"] = got / len(ev)
    else:
        row["complete"] = None
        row["recall"] = None
    if stored is not None:
        st = set(stored)
        if ev:
            got_s = sum(1 for o in ev if o in st)
            row["stored_complete"] = got_s == len(ev)
            row["stored_recall"] = got_s / len(ev)
        else:
            row["stored_complete"] = None
            row["stored_recall"] = None
    return row


def summarise_evidence(rows: Sequence[dict], keys: Sequence[str] = ("complete", "recall")) -> dict:
    """Mean of each key over the rows that have it, per family, and the macro mean over families
    (equal family weights): ``{'by_family': {fam: {key: mean, 'n': n}}, 'macro': {key: mean}}``."""
    import math

    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["family"], []).append(r)
    fams: dict[str, dict] = {}
    for fam in sorted(by):
        entry: dict = {}
        for k in keys:
            vals = [float(r[k]) for r in by[fam] if r.get(k) is not None]
            entry[k] = math.fsum(vals) / len(vals) if vals else None
            entry["n_" + k] = len(vals)
        entry["n"] = len(by[fam])
        fams[fam] = entry
    macro = {}
    for k in keys:
        vals = [e[k] for e in fams.values() if e[k] is not None]
        macro[k] = math.fsum(vals) / len(vals) if vals else None
    return {"by_family": fams, "macro": macro}
