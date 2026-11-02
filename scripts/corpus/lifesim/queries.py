"""Questions with exact gold for the Day-1 families of LifeSim, and the checks that keep them honest.

Families built here: EP1 (breakfast on a day), SE4 (state now, and identity 'who is X'), SE5
(state as of a date), IN1 (detail of an article read earlier), EP4 (central and peripheral slot
of one situation, as a pair), IN4 (a closing time stated once in a quiet remark), EP3c (count of
errands in a date window) and ME1 (false premise: UNKNOWN with a near-miss trap). ME2 is the
``conf`` field of every query.

What this module provides
-------------------------
* ``candidate_pool(world)``: every answerable target in the world, found from the structure
  alone (facts, situations, observation specs), identical for every coupling cell.
* ``solve_quota(spec, A_all, candidates, k)`` and ``sample_targets(pool, k, coupling, seed,
  A_all)``: the stream-wide arousal decile quotas of a coupling cell. The shape is an
  exponential tilt over the ten deciles of line arousal, solved per world so that the share of
  targets in the top decile divided by 0.10 hits the cell's E_0.10; the quiet-critical mass mu
  is mixed in on deciles 0-1 and the tilt is re-solved, so E_0.10 is the same with and without
  mu. The null cell (E 1, mu 0) is flat. Finite support is reported as shortfall, never hidden.
* ``build_queries(world, cfg, cell)``: the queries of one world (text filled, qids in time order)
  and ``build_queries_ex`` which also returns a report of what was dropped and why.
* ``gold_slow(world, query)``: an independent second solver that scans the raw observation specs
  and facts from the question's own cue; ``slow_answers`` returns every consistent answer.
* ``structural_memory_filter``: drops items that a blind constant guess, a habit guess, an
  ambiguous cue or an ablated world (evidence lines deleted) can still solve.
* ``plain_question``: the trivial default renderer; pass ``verbalise.render_question`` as
  ``render=`` for the real question frames.
* ``evidence_check``, ``realised_enrichment``, ``evidence_line_enrichment``,
  ``check_query_support``, ``make_choice_fork`` and the cue grammar for relative dates.

Structure this module reads (the contract with ``world.py``)
-----------------------------------------------------------
* Facts use the predicate names of ``vocab.SLOTS`` and ``scenes.PREDICATES``: ``breakfast`` (one fact per stated day,
  ``vfrom == vto``), ``lives_in`` / ``works_as`` / ``works_at`` (version chains of the narrator,
  ``vto`` of a version is the day before the next ``vfrom``), ``relation`` (subject = a person
  entity), ``vehicle_colour`` (``src='read'`` for articles, a peripheral fact of a situation
  otherwise), ``companion`` (the central fact of a situation), ``closing_time`` (subject = a shop
  entity), ``errand_visit`` or ``errand`` (the narrator's or another person's visit, object = an
  errand name), ``on_street`` or ``street`` (shop -> street entity), ``car_colour`` (the peripheral
  slot of an EP4 situation), ``decoy_colour`` (the decoy of an article),
  ``visited`` (object = a city entity, hosted by a trip situation next to its companion fact).
* ``Fact.obj`` is an entity id (resolved to the entity's name) or a canonical value. The narrator
  is ``world.extra('narrator')`` or else the subject of the breakfast facts.
* Observation specs carry the verbatim value in a ``Slot`` whose ``fid`` is the fact. An article's
  kind and city come from the line's ``story_kind`` and ``city`` slots if it has them, else from
  the name of the story entity that is the subject of its ``vehicle_colour`` fact ('flood in
  Verdton', see ``story_parts``); remark lines about a shop carry ``Slot('street', ...)`` or the
  shop has an ``on_street`` fact. A fact is 'observed' when some spec mentions it with role assert,
  update or recall; only observed facts can be asked about, and only specs before ``t_ask`` count.
* ``query.cue`` slot names: ``date`` (ISO), ``relative_day`` ('yesterday', '3 days ago'),
  ``relative_window`` ('about two weeks ago'), ``story_kind``, ``city``, ``person``, ``shop``,
  ``street``, ``errand``, ``window_from``, ``window_to``; ``query.ask`` is the asked predicate.

ASSUMED parameters not (yet) fields of TierCfg, read with ``cfg.get(name, default)``:
``in4_min_delay_days`` 14, ``ep1_relative_max_days`` 30, ``central_min_centrality`` 0.5,
``max_const_share`` 0.15, ``ask_minute_lo`` 360, ``ask_minute_hi`` 1380, ``choice_fork_share`` 0,
``choice_options`` 4, ``keep_prior_answerable`` 0 (1 keeps the habit-answerable breakfast days,
flagged by ``tags.prior_answerable``), ``quota_redistribute`` 1 (0 forbids offering one family's
unfillable decile quota to the others). Dials used from TierCfg: queries_per_world, family_mix,
abstain_share, delay_min_days, delay_max_days, anchor_mix, relative_time_share, ep1_competing,
in1_min_other_articles, in4_low_deciles, ep3c_count_range, retell_a_factor. ``query_overgenerate``
is not used as a multiplier: a candidate that fails a check is replaced by the next one of its
decile, which has the same effect (``report.drawn`` counts the attempts).

Streams: ``stream(seed, 'query', family, 'targets')`` shuffles the candidates of each arousal
decile, ``stream(seed, 'query', family, 'build')`` draws cues, delays and ask times (one stream
per family, so a family never shifts another), ``stream(seed, 'query', 'choice', ...)`` the
forced-choice forks; ``scorers`` uses ``stream(seed, 'boot', label)`` for the bootstrap.

Every sum of floats uses ``math.fsum`` (Python 3.12 made ``sum`` compensated and 3.11 did not, so
a plain ``sum`` would differ in the last bit between interpreters).

What this module does NOT do: it renders no text itself (the default ``plain_question`` is a
stand-in), calls no model and no network, reads no clock, uses neither ``random`` nor ``hash()``,
implements none of the v0.1 or v0.2 families, no event-anchored cues ('the morning after I met
X'), no twin cells, and no model-based blind-reader or shuffled-context filters (those are runs,
not structure). The 'hard' tag is computed from the item, the tier's ``hard_share`` is not steered
to. Items whose cue is ambiguous are dropped, never repaired.
"""

from __future__ import annotations

import bisect
import dataclasses
import datetime as _dt
import math
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Sequence

from .rng import dexp, q, stream
from .schema import (CELLS, MINUTES_PER_DAY, Cell, Gold, NearMiss, Query, Slot, Tags, World,
                     date_of, day_of, digest_of, new_id)
from .vocab import COLOURS, NUMBER_WORDS, POOL_ALIASES, SLOTS, STORY_KINDS, closed_vocab, norm

__all__ = [
    "Candidate", "CandidatePool", "Quota", "Draw", "FilterResult", "BuildReport", "BuildResult",
    "AmbiguousGold", "candidate_pool", "solve_quota", "sample_targets", "build_queries",
    "build_queries_ex", "gold_slow", "slow_answers", "structural_memory_filter",
    "ablate_lines", "plain_question", "make_choice_fork", "evidence_check", "realised_enrichment",
    "evidence_line_enrichment", "check_query_support", "stream_arousal", "line_arousal",
    "rank_fraction", "decile_of", "narrator_id", "resolve_relative", "relative_phrase",
    "day_index", "FAMILY_ORDER", "OBSERVING_ROLES", "story_parts", "shuffled_by_decile",
    "ERRAND_PREDS", "STREET_PREDS", "TRIP_COMPANION_PREDS", "wanted_counts",
]

OBSERVING_ROLES = ("assert", "update", "recall")
FAMILY_ORDER = ("EP1", "SE4", "SE5", "IN1", "EP4", "IN4", "EP3c", "ME1")
SE_PREDS = ("lives_in", "works_as", "works_at")
_CAR_PREDS = ("vehicle_colour", "car_colour")
ERRAND_PREDS = ("errand_visit", "errand")
STREET_PREDS = ("on_street", "street")
TRIP_COMPANION_PREDS = ("trip_companion", "companion")
STORY_PREFIXES = tuple(sorted(STORY_KINDS, key=lambda k: (-len(k), k)))
_PLACEHOLDER_QID = new_id("query", 0)
_COLOUR_SET = frozenset(COLOURS)
_BINS = ((1, 3), (4, 14), (15, 60), (61, 180), (181, 10 ** 9))
_KMAX = 60.0


class AmbiguousGold(ValueError):
    """Raised by ``gold_slow`` when the cue is consistent with two or more different answers."""


# ------------------------------------------------------------------------------ data types


@dataclass(frozen=True)
class Candidate:
    """One answerable target found in a world. ``oids`` are all observing lines of the target
    facts (a query keeps those before its ``t_ask``); ``A`` is the mean arousal of the situations
    hosting the target facts; ``t_ready`` is the time of the first observing line (the earliest
    moment the answer could be known); ``day`` is the event day (breakfast day, article day,
    situation day, first valid day of a version); ``value`` is the canonical answer."""

    family: str
    key: str
    ask: str
    fids: tuple[str, ...]
    oids: tuple[str, ...]
    t_ready: int
    day: int
    A: float
    value: str
    info: tuple[tuple[str, str], ...] = ()

    def get(self, name: str, default: str = "") -> str:
        for k, v in self.info:
            if k == name:
                return v
        return default


@dataclass(frozen=True)
class CandidatePool:
    """All candidates of a world by family, in deterministic order; ``digest()`` is identical
    for every coupling cell because the pool is built from the world alone."""

    by_family: tuple[tuple[str, tuple[Candidate, ...]], ...]

    def of(self, family: str) -> tuple[Candidate, ...]:
        for fam, cands in self.by_family:
            if fam == family:
                return cands
        return ()

    def counts(self) -> dict:
        return {fam: len(cands) for fam, cands in self.by_family}

    def digest(self) -> str:
        return digest_of(self.by_family)


@dataclass(frozen=True)
class Quota:
    """Decile quota of one coupling cell: ``probs`` are the target shares of the ten arousal
    deciles, ``counts`` the demanded targets for ``k`` draws, ``supply`` the candidates per
    decile, ``taken`` min(counts, supply) and ``shortfall`` what the support cannot fill.
    ``feasible`` is False when the tilt could not reach E_0.10 (the cell is out of range)."""

    e_target: float
    mu: float
    kappa: float
    probs: tuple[float, ...]
    counts: tuple[int, ...]
    supply: tuple[int, ...]
    taken: tuple[int, ...]
    shortfall: int
    feasible: bool
    k: int

    @property
    def expected_e(self) -> float:
        """E_0.10 of the shape itself (top-decile share divided by 0.10)."""
        return self.probs[9] / 0.1

    @property
    def shortfall_share(self) -> float:
        return self.shortfall / self.k if self.k else 0.0


@dataclass(frozen=True)
class Draw:
    """Targets drawn under a quota, ordered so that every prefix follows the quota."""

    chosen: tuple[Candidate, ...]
    deciles: tuple[int, ...]
    quota: Quota

    @property
    def shortfall(self) -> int:
        return self.quota.shortfall


@dataclass(frozen=True)
class FilterResult:
    """Outcome of ``structural_memory_filter``: kept queries and (qid, reason) of dropped ones."""

    kept: tuple[Query, ...]
    dropped: tuple[tuple[str, str], ...]


class BuildReport:
    """What ``build_queries_ex`` did: per family the number requested and kept, the drop counts
    by reason, the quota (with shortfall) and the draw sizes. Not part of any digest."""

    def __init__(self) -> None:
        self.requested: dict = {}
        self.kept: dict = {}
        self.drops: dict = {}
        self.quotas: dict = {}
        self.drawn: dict = {}
        self.pooled_shortfall = 0
        self.pooled_demand = 0

    def drop(self, family: str, reason: str, n: int = 1) -> None:
        if n <= 0:
            return
        key = (family, reason)
        self.drops[key] = self.drops.get(key, 0) + n

    def dropped(self, family: str | None = None, reason: str | None = None) -> int:
        return sum(n for (f, r), n in self.drops.items()
                   if (family is None or f == family) and (reason is None or r == reason))

    def shortfall(self, family: str | None = None) -> int:
        """Pooled shortfall after redistribution (the G-SUPPORT quantity) if ``family`` is None,
        else that family's own shortfall before redistribution."""
        if family is None:
            return self.pooled_shortfall
        qt = self.quotas.get(family)
        return qt.shortfall if qt is not None else 0

    @property
    def shortfall_share(self) -> float:
        return self.pooled_shortfall / self.pooled_demand if self.pooled_demand else 0.0


@dataclass(frozen=True)
class BuildResult:
    queries: tuple[Query, ...]
    report: BuildReport
    pool: CandidatePool


# ------------------------------------------------------------- arousal, deciles, quotas


def _sit(world: World, sid: str):
    try:
        return world.situation(sid)
    except KeyError:
        return None


def line_arousal(world: World, spec: Any) -> float:
    """Arousal of one observation line: the situation's A, times ``retell_a_factor`` when every
    mention of the line is a recall (a retelling)."""
    sit = _sit(world, spec.sid)
    if sit is None:
        return 0.0
    a = sit.A
    if spec.mentions and all(m.role == "recall" for m in spec.mentions):
        a = a * world.cfg.retell_a_factor
    return q(a)


def stream_arousal(world: World) -> list[float]:
    """Arousal of every line of the stream, in stream order (``A_all``)."""
    return [line_arousal(world, o) for o in world.obs_specs]


def rank_fraction(a: float, sorted_all: Sequence[float]) -> float:
    """Mid-rank percentile of ``a`` among ``sorted_all`` (ties share their mid rank), in [0, 1]."""
    n = len(sorted_all)
    if n == 0:
        return 0.5
    lo = bisect.bisect_left(sorted_all, a)
    hi = bisect.bisect_right(sorted_all, a)
    return (lo + hi) / (2.0 * n)


def decile_of(a: float, sorted_all: Sequence[float]) -> int:
    """Stream-wide arousal decile 0-9 of a value (9 = the top tenth of lines)."""
    return min(9, int(rank_fraction(a, sorted_all) * 10.0))


def _spec_params(spec: Any) -> tuple[float, float]:
    if hasattr(spec, "e_target"):
        return float(spec.e_target), float(spec.mu)
    if isinstance(spec, dict):
        return float(spec["e_target"]), float(spec.get("mu", 0.0))
    e, mu = spec
    return float(e), float(mu)


def _tilt_top(kappa: float, mu: float) -> float:
    w = [dexp(kappa * (j - 4.5)) for j in range(10)]
    return (1.0 - mu) * w[9] / math.fsum(w)


def _shape(e: float, mu: float) -> tuple[float, tuple[float, ...], bool]:
    mu = min(1.0, max(0.0, mu))
    target = 0.1 * e
    feasible = True
    if target >= _tilt_top(_KMAX, mu):
        kappa, feasible = _KMAX, False
    elif target <= _tilt_top(-_KMAX, mu):
        kappa, feasible = -_KMAX, False
    else:
        lo, hi = -_KMAX, _KMAX
        for _ in range(100):
            mid = (lo + hi) / 2.0
            if _tilt_top(mid, mu) < target:
                lo = mid
            else:
                hi = mid
        kappa = round((lo + hi) / 2.0, 9) + 0.0
    w = [dexp(kappa * (j - 4.5)) for j in range(10)]
    s = math.fsum(w)
    p = [(1.0 - mu) * x / s for x in w]
    p[0] += mu * 0.5
    p[1] += mu * 0.5
    return kappa, tuple(round(x, 12) + 0.0 for x in p), feasible


def _largest_remainder(probs: Sequence[float], k: int) -> list[int]:
    raw = [p * k for p in probs]
    base = [int(math.floor(x + 1e-9)) for x in raw]
    rem = max(0, k - sum(base))
    order = sorted(range(len(probs)), key=lambda j: (-(raw[j] - base[j]), j))
    for j in order[:rem]:
        base[j] += 1
    return base


def solve_quota(spec: Any, A_all: Sequence[float], candidates: Sequence[Any], k: int | None = None,
                e_target: float | None = None, counts: Sequence[int] | None = None) -> Quota:
    """Decile quota of a coupling cell for a candidate set.

    ``spec`` is a ``Cell`` (or an (E_0.10, mu) pair); ``A_all`` the arousal of every line of the
    stream (it defines the deciles); ``candidates`` objects with an ``A`` attribute (or plain
    numbers) give the support per decile. With ``k`` the quota is also turned into integer counts
    by largest remainder and the shortfall against the support is computed; ``e_target``
    overrides the cell's E_0.10 (used when other families have fixed arousal) and ``counts``
    replaces the largest-remainder counts (used to diffuse rounding across families)."""
    e, mu = _spec_params(spec)
    if e_target is not None:
        e = e_target
    srt = sorted(A_all)
    supply = [0] * 10
    for c in candidates:
        supply[decile_of(float(getattr(c, "A", c)), srt)] += 1
    kappa, probs, feasible = _shape(e, mu)
    if k is None:
        return Quota(e, mu, kappa, probs, (), tuple(supply), (), 0, feasible, 0)
    cnt = list(counts) if counts is not None else _largest_remainder(probs, k)
    taken = [min(c, s) for c, s in zip(cnt, supply)]
    return Quota(e, mu, kappa, probs, tuple(cnt), tuple(supply), tuple(taken),
                 sum(cnt) - sum(taken), feasible, k)


def sample_targets(pool: Sequence[Candidate], k: int, coupling: Any, seed: int,
                   A_all: Sequence[float], family: str = "targets",
                   e_target: float | None = None) -> Draw:
    """Draw ``k`` targets from ``pool`` under the decile quota of ``coupling``.

    Within a decile candidates are drawn uniformly without replacement from a canonical order
    (sorted by key), so the result does not depend on the order of ``pool``. The chosen targets
    are ordered by their rank inside their decile relative to the decile's quota, so that any
    prefix of the result approximates the quota (truncating keeps the dial)."""
    quota = solve_quota(coupling, A_all, pool, k, e_target)
    lists = shuffled_by_decile(pool, A_all, seed, family)
    keyed: list[tuple[float, int, str, Candidate]] = []
    for j in range(10):
        n = quota.taken[j]
        for i, c in enumerate(lists[j][:n]):
            keyed.append(((i + 0.5) / n, j, c.key, c))
    keyed.sort(key=lambda t: (t[0], t[1], t[2]))
    return Draw(tuple(t[3] for t in keyed), tuple(t[1] for t in keyed), quota)


def shuffled_by_decile(pool: Sequence[Candidate], A_all: Sequence[float], seed: int,
                       family: str = "targets") -> list[list[Candidate]]:
    """The candidates of each stream-arousal decile in a seeded random order (a full shuffle of
    a canonical order sorted by key). ``sample_targets`` takes the first ``taken[j]`` of each
    list; ``build_queries`` walks the lists until the decile's quota is met, so a candidate that
    fails a check is replaced by the next one of the same decile."""
    srt = sorted(A_all)
    by_decile: list[list[Candidate]] = [[] for _ in range(10)]
    for c in pool:
        by_decile[decile_of(c.A, srt)].append(c)
    rng = stream(seed, "query", family, "targets")
    return [rng.sample(sorted(by_decile[j], key=lambda c: c.key), len(by_decile[j])) for j in range(10)]


def realised_enrichment(queries: Sequence[Query], A_all: Sequence[float], frac: float = 0.10) -> float:
    """Item-level enrichment E_R: the share of answerable queries whose ``target_arousal`` lies in
    the top ``frac`` of stream arousal (mid-rank), divided by ``frac``. 1.0 is the null."""
    srt = sorted(A_all)
    items = [x for x in queries if x.family != "ME1"]
    if not items:
        return 0.0
    hit = sum(1 for x in items if rank_fraction(x.tags.target_arousal, srt) >= 1.0 - frac)
    return hit / len(items) / frac


def evidence_line_enrichment(world: World, queries: Sequence[Query], frac: float = 0.10) -> float:
    """Line-level E_R: the share of distinct evidence lines (over all queries) in the top
    ``frac`` of stream arousal, divided by ``frac``."""
    A = {o.oid: a for o, a in zip(world.obs_specs, stream_arousal(world))}
    srt = sorted(A.values())
    oids = sorted({oid for x in queries for oid in x.evidence_oids})
    if not oids:
        return 0.0
    hit = sum(1 for oid in oids if rank_fraction(A[oid], srt) >= 1.0 - frac)
    return hit / len(oids) / frac


# ------------------------------------------------------- question semantics (shared by both solvers)


def narrator_id(world: World) -> str:
    """Subject id of the narrator's own facts: ``world.extra('narrator')``, else the most
    frequent subject of the breakfast facts, else of the version chains and errands, else ''."""
    v = world.extra("narrator", None)
    if isinstance(v, str) and v:
        return v
    for preds in (("breakfast",), SE_PREDS, ("errand",)):
        counts: dict = {}
        for f in world.facts:
            if f.pred in preds:
                counts[f.subj] = counts.get(f.subj, 0) + 1
        if counts:
            return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return ""


def story_parts(name: str) -> tuple[str, str]:
    """(story kind, city) of a story name written 'flood in Verdton' or 'road closure in Karmont';
    ('', '') if the name does not have that form."""
    for kind in STORY_PREFIXES:
        if name.startswith(kind + " in ") and len(name) > len(kind) + 4:
            return kind, name[len(kind) + 4:]
    return "", ""


def day_index(start_date: str, iso: str) -> int:
    """Day index of an ISO date, given the ISO date of day 0."""
    return (_dt.date.fromisoformat(iso) - _dt.date.fromisoformat(start_date)).days


_REL_DAYS = re.compile(r"^(\d+) days ago$")
_REL_WEEKS = re.compile(r"^about (\w+) weeks? ago$")
_REL_MONTHS = re.compile(r"^about (\w+) months? ago$")


def _num(tok: str) -> int | None:
    if tok.isdigit():
        return int(tok)
    if tok in NUMBER_WORDS[:21]:
        return NUMBER_WORDS.index(tok)
    return None


def resolve_relative(phrase: str, ask_day: int) -> tuple[int, int] | None:
    """Day window (first, last) that a relative date phrase denotes when asked on ``ask_day``:
    'yesterday' and 'N days ago' are one exact day; 'about N weeks ago' is +-3 days around 7N;
    'about N months ago' is +-15 days around 30N. None if the phrase is not in the grammar."""
    p = phrase.strip().lower()
    if p == "yesterday":
        return (ask_day - 1, ask_day - 1)
    m = _REL_DAYS.match(p)
    if m:
        d = ask_day - int(m.group(1))
        return (d, d)
    m = _REL_WEEKS.match(p)
    if m and _num(m.group(1)):
        c = ask_day - 7 * _num(m.group(1))
        return (c - 3, c + 3)
    m = _REL_MONTHS.match(p)
    if m and _num(m.group(1)):
        c = ask_day - 30 * _num(m.group(1))
        return (c - 15, c + 15)
    return None


def relative_phrase(delay: int, fuzzy: bool = False, max_exact: int = 30) -> str | None:
    """The relative date phrase for an event ``delay`` days before the question: exact ('yesterday',
    'N days ago' up to ``max_exact``) or, with ``fuzzy``, 'about N weeks ago' (10-59 days) and
    'about N months ago' (60 days and more). None if no phrase fits."""
    if delay < 1:
        return None
    if delay == 1:
        return "yesterday"
    if not fuzzy:
        return "%d days ago" % delay if delay <= max_exact else None
    if delay < 10:
        return "%d days ago" % delay
    if delay < 60:
        w = int(delay / 7.0 + 0.5)
        return "about %s week%s ago" % (NUMBER_WORDS[w], "" if w == 1 else "s")
    m = min(12, int(delay / 30.0 + 0.5))
    return "about %s month%s ago" % (NUMBER_WORDS[m], "" if m == 1 else "s")


def _cue_window(cues: dict, ask_day: int, start: str) -> tuple[int, int] | None:
    if "date" in cues:
        d = day_index(start, cues["date"])
        return (d, d)
    if "relative_day" in cues:
        return resolve_relative(cues["relative_day"], ask_day)
    if "relative_window" in cues:
        return resolve_relative(cues["relative_window"], ask_day)
    return None


# -------------------------------------------------------------------- fast-path index


class _Index:
    """Read-only lookups over one world for the fast path (candidate pool and query building)."""

    def __init__(self, world: World, cfg: Any = None) -> None:
        self.world = world
        self.cfg = cfg or world.cfg
        self.start = world.cfg.start_date
        self.last_day = world.cfg.days - 1
        self.narr = narrator_id(world)
        self.by_pred: dict = {}
        for f in world.facts:
            self.by_pred.setdefault(f.pred, []).append(f)
        self.ent = {e.eid: e for e in world.entities}
        self.fact = {f.fid: f for f in world.facts}
        self.spec = {o.oid: o for o in world.obs_specs}
        self.A_lines = stream_arousal(world)
        self.A_of = {o.oid: a for o, a in zip(world.obs_specs, self.A_lines)}
        self.sorted_A = sorted(self.A_lines)
        self.obs: dict = {}
        for o in world.obs_specs:
            for m in o.mentions:
                if m.role in OBSERVING_ROLES:
                    self.obs.setdefault(m.fid, []).append((o.t_obs, o.oid, m.role))
        self.host: dict = {}
        for s in world.situations:
            for fid in s.facts:
                self.host[fid] = s

    def value(self, f: Any) -> str:
        e = self.ent.get(f.obj)
        return e.name if e is not None else f.obj

    def lines(self, fid: str, before: int | None = None) -> list:
        ls = self.obs.get(fid, [])
        return ls if before is None else [x for x in ls if x[0] < before]

    def first_t(self, fid: str) -> int | None:
        ls = self.obs.get(fid)
        return ls[0][0] if ls else None

    def fact_A(self, fid: str) -> float:
        s = self.host.get(fid)
        if s is not None:
            return s.A
        ls = self.obs.get(fid, [])
        return math.fsum(self.A_of[o] for _, o, _ in ls) / len(ls) if ls else 0.0

    def slot(self, oid: str, name: str) -> str:
        for s in self.spec[oid].slots:
            if s.name == name:
                return s.value
        return ""

    def facts_of(self, pred: str) -> list:
        return self.by_pred.get(pred, [])

    def facts_of_any(self, preds: Sequence[str]) -> list:
        return [f for p in preds for f in self.by_pred.get(p, [])]

    def story(self, oid: str, f: Any) -> tuple[str, str]:
        """(kind, city) of the story an article line tells: the line's own ``story_kind`` and
        ``city`` slots if it has them, else parsed from the name of the story entity."""
        kind, city = self.slot(oid, "story_kind"), self.slot(oid, "city")
        if kind or city:
            return kind, city
        ent = self.ent.get(f.subj)
        return story_parts(ent.name) if ent is not None and ent.kind == "story" else ("", "")


def _mean(xs: Sequence[float]) -> float:
    return math.fsum(xs) / len(xs) if xs else 0.0


# ------------------------------------------------------------------- candidate pool


def _ep1_candidates(ix: _Index) -> list[Candidate]:
    out = []
    prior = ix.world.prior("breakfast")
    top3 = set(prior.top(3)) if prior else set()
    for f in ix.facts_of("breakfast"):
        if f.vto != f.vfrom or f.src != "lived":
            continue
        ls = ix.lines(f.fid)
        if len(ls) != 1 or ls[0][2] != "assert":
            continue
        t, oid, _ = ls[0]
        out.append(Candidate("EP1", f.fid, "breakfast", (f.fid,), (oid,), t, f.vfrom,
                             q(ix.fact_A(f.fid)), ix.value(f),
                             (("prior_answerable", "1"),) if ix.value(f) in top3 else ()))
    return out


def _se_candidates(ix: _Index) -> list[Candidate]:
    out = []
    chains: dict = {}
    for pred in SE_PREDS:
        for f in ix.facts_of(pred):
            if ix.narr and f.subj != ix.narr:
                continue
            chains.setdefault((f.subj, pred), []).append(f)
    for (subj, pred), fs in sorted(chains.items()):
        fs.sort(key=lambda f: (f.vfrom, f.fid))
        chain = ",".join(f.fid for f in fs)
        for i, f in enumerate(fs):
            ls = ix.lines(f.fid)
            if not ls:
                continue
            info = (("subj", subj), ("pred", pred), ("i", str(i)), ("n", str(len(fs))),
                    ("vto", "" if f.vto is None else str(f.vto)), ("chain", chain))
            for fam in ("SE4", "SE5"):
                out.append(Candidate(fam, "%s#%s" % (fam, f.fid), pred, (f.fid,),
                                     tuple(o for _, o, _ in ls), ls[0][0], f.vfrom,
                                     q(ix.fact_A(f.fid)), ix.value(f), info))
    for f in ix.facts_of("relation"):
        ls = ix.lines(f.fid)
        ent = ix.ent.get(f.subj)
        if len(ls) != 1 or ls[0][2] != "assert" or ent is None:
            continue
        out.append(Candidate("SE4", "SE4#%s" % f.fid, "relation", (f.fid,), (ls[0][1],), ls[0][0],
                             f.vfrom, q(ix.fact_A(f.fid)), ix.value(f),
                             (("person", ent.name), ("i", "0"), ("n", "1"))))
    return out


def _in1_candidates(ix: _Index) -> list[Candidate]:
    out = []
    for f in ix.facts_of("vehicle_colour"):
        if f.src != "read":
            continue
        ls = ix.lines(f.fid)
        if not ls:
            continue
        oid = ls[0][1]
        kind, city = ix.story(oid, f)
        if not kind and not city:
            continue
        decoys = sorted({s.value for s in ix.spec[oid].slots
                         if s.fid != f.fid and s.value in _COLOUR_SET and s.value != ix.value(f)})
        info = (("story_kind", kind), ("city", city), ("decoys", "|".join(decoys)),
                ("read_day", str(ix.spec[oid].day)))
        out.append(Candidate("IN1", f.fid, "vehicle_colour", (f.fid,), tuple(o for _, o, _ in ls),
                             ls[0][0], ix.spec[oid].day, q(ix.fact_A(f.fid)), ix.value(f), info))
    return out


def _ep4_candidates(ix: _Index) -> list[Candidate]:
    thr = float(ix.cfg.get("central_min_centrality", 0.5))
    out = []
    for s in ix.world.situations:
        cf, pf = [], []
        for fid in s.facts:
            f = ix.fact.get(fid)
            if f is None or not ix.lines(fid):
                continue
            if f.pred == "companion" and f.centrality >= thr:
                cf.append(f)
            elif f.pred in _CAR_PREDS and f.src == "lived" and f.centrality < thr:
                pf.append(f)
        if len(cf) != 1 or len(pf) != 1:
            continue
        c, p = cf[0], pf[0]
        lc, lp = ix.lines(c.fid), ix.lines(p.fid)
        oids = tuple(sorted({o for _, o, _ in lc} | {o for _, o, _ in lp}))
        info = (("sid", s.sid), ("cfid", c.fid), ("pfid", p.fid), ("cval", ix.value(c)),
                ("pval", ix.value(p)), ("coids", ",".join(o for _, o, _ in lc)),
                ("poids", ",".join(o for _, o, _ in lp)), ("cpred", c.pred), ("ppred", p.pred))
        out.append(Candidate("EP4", s.sid, "companion", (c.fid, p.fid), oids,
                             max(lc[0][0], lp[0][0]), s.day, q(s.A), ix.value(c), info))
    return out


def _in4_candidates(ix: _Index) -> list[Candidate]:
    low = int(ix.cfg.in4_low_deciles)
    out = []
    for f in ix.facts_of("closing_time"):
        ls = ix.lines(f.fid)
        shop = ix.ent.get(f.subj)
        if len(ls) != 1 or ls[0][2] != "assert" or shop is None:
            continue
        t, oid, _ = ls[0]
        dec = decile_of(ix.A_of[oid], ix.sorted_A)
        if dec >= low:
            continue
        street = ix.slot(oid, "street")
        if not street:
            for sf in ix.facts_of_any(STREET_PREDS):
                if sf.subj == f.subj and sf.obj in ix.ent:
                    street = ix.ent[sf.obj].name
                    break
        out.append(Candidate("IN4", f.fid, "closing_time", (f.fid,), (oid,), t,
                             day_of(t), q(ix.fact_A(f.fid)), ix.value(f),
                             (("shop", shop.name), ("street", street), ("decile", str(dec)))))
    return out


def _ep3c_candidates(ix: _Index) -> list[Candidate]:
    lo_c, hi_c = ix.cfg.ep3c_count_range
    groups: dict = {}
    for f in ix.facts_of_any(ERRAND_PREDS):
        if f.src != "lived" or (ix.narr and f.subj != ix.narr) or not ix.lines(f.fid):
            continue
        groups.setdefault(ix.value(f), []).append(f)
    out = []
    for errand, fs in sorted(groups.items()):
        fs.sort(key=lambda f: (f.vfrom, f.fid))
        n = len(fs)
        for i in range(n):
            if i > 0 and fs[i - 1].vfrom == fs[i].vfrom:
                continue
            for j in range(i, min(n, i + hi_c)):
                if j + 1 < n and fs[j + 1].vfrom == fs[j].vfrom:
                    continue
                count = j - i + 1
                if count < lo_c:
                    continue
                sel = fs[i:j + 1]
                lines = sorted({(t, o) for f in sel for t, o, _ in ix.lines(f.fid)})
                info = (("errand", errand), ("count", str(count)), ("v_first", str(sel[0].vfrom)),
                        ("v_last", str(sel[-1].vfrom)),
                        ("v_prev", str(fs[i - 1].vfrom) if i > 0 else "-1"),
                        ("v_next", str(fs[j + 1].vfrom) if j + 1 < n else "-1"))
                out.append(Candidate("EP3c", "EP3c#%s#%d-%d" % (errand, i, j), "visit_count",
                                     tuple(f.fid for f in sel), tuple(o for _, o in lines),
                                     max(ix.first_t(f.fid) for f in sel), sel[-1].vfrom,
                                     q(_mean([ix.fact_A(f.fid) for f in sel])), str(count), info))
    return out


def _me1_candidates(ix: _Index) -> list[Candidate]:
    out = []
    observed_bf = {f.vfrom for f in ix.facts_of("breakfast") if ix.lines(f.fid)}
    for d in range(1, ix.last_day):
        if d in observed_bf or not ((d - 1) in observed_bf or (d + 1) in observed_bf):
            continue
        out.append(Candidate("ME1", "ME1#bk#%d" % d, "breakfast", (), (), 0, d, 0.0, "UNKNOWN",
                             (("type", "breakfast"), ("day", str(d)))))
    visited = {f.obj for f in ix.facts_of("visited") if ix.lines(f.fid)}
    home = {f.obj for f in ix.facts_of("lives_in")}
    trips = [f for f in ix.facts_of("visited") if ix.lines(f.fid)]
    if trips:
        for e in ix.world.entities_of("city"):
            if e.eid in visited or e.eid in home:
                continue
            out.append(Candidate("ME1", "ME1#trip#%s" % e.eid, "companion", (), (), 0, 0, 0.0,
                                 "UNKNOWN", (("type", "trip"), ("city", e.name))))
    stated = {f.subj for f in ix.facts_of("closing_time") if ix.lines(f.fid)}
    if stated:
        for e in ix.world.entities_of("shop"):
            if e.eid in stated:
                continue
            out.append(Candidate("ME1", "ME1#shop#%s" % e.eid, "closing_time", (), (), 0, 0, 0.0,
                                 "UNKNOWN", (("type", "shop"), ("shop", e.name))))
    return out


def candidate_pool(world: World, cfg: Any = None) -> CandidatePool:
    """Every answerable target of the world by family (EP1, SE4, SE5, IN1, EP4, IN4, EP3c, ME1),
    from the structure alone: no cell, no seed, no text. ``pool.digest()`` is therefore the same
    for every coupling cell. Lists are in a deterministic order (sorted by key). ``cfg`` (default
    ``world.cfg``) supplies the few dials the pool depends on (``ep3c_count_range``,
    ``in4_low_deciles``, ``central_min_centrality``)."""
    ix = _Index(world, cfg)
    parts: dict = {fam: [] for fam in FAMILY_ORDER}
    for c in (_ep1_candidates(ix) + _se_candidates(ix) + _in1_candidates(ix)
              + _ep4_candidates(ix) + _in4_candidates(ix) + _ep3c_candidates(ix)
              + _me1_candidates(ix)):
        parts[c.family].append(c)
    return CandidatePool(tuple((fam, tuple(sorted(parts[fam], key=lambda c: c.key)))
                               for fam in FAMILY_ORDER))


# ----------------------------------------------------------------------- cues and queries


def _pick_delay(rng: Any, lo: int, hi: int) -> int | None:
    """A delay in [lo, hi] days: a delay bin (1-3, 4-14, 15-60, 61-180, 181+) chosen uniformly
    among those that intersect the range, then a day uniformly inside it."""
    if hi < lo:
        return None
    bins = [(max(a, lo), min(b, hi)) for a, b in _BINS if max(a, lo) <= min(b, hi)]
    a, b = bins[rng.below(len(bins))]
    return rng.ri(a, b)


def _ask_minute(rng: Any, cfg: Any) -> int:
    return rng.ri(int(cfg.get("ask_minute_lo", 360)), int(cfg.get("ask_minute_hi", 1380)))


def _near(gold_value: str, items: Sequence[tuple[str, str]], limit: int = 8) -> tuple[NearMiss, ...]:
    seen = {gold_value}
    out = []
    for kind, v in items:
        if v and v not in seen:
            seen.add(v)
            out.append(NearMiss(kind=kind, value=v))
            if len(out) >= limit:
                break
    return tuple(out)


def _pool_aliases(vocab_id: str, value: str) -> tuple[str, ...]:
    scheme, _, ident = vocab_id.partition(":")
    if scheme == "pool":
        return tuple(sorted(a for a, c in POOL_ALIASES.get(ident, ()) if c == value))
    return ()


def _gold(ix: _Index, kind: str, value: str, ask: str, near: Sequence[tuple[str, str]]) -> Gold:
    vid = SLOTS[ask]
    aliases = _pool_aliases(vid, value)
    if vid.startswith("kind:"):
        for e in ix.world.entities:
            if e.name == value and e.aliases:
                aliases = tuple(e.aliases)
                break
    return Gold(kind=kind, value=value, aliases=aliases, vocab_id=vid, near_miss=_near(value, near))


def _make_query(ix: _Index, cand: Candidate, fam: str, t_ask: int, cue: Sequence[Slot], ask: str,
                gold: Gold, ev_fids: Sequence[str], *, anchor: str, n_conf: int,
                partition: str, update_count: int = 0, role: str = "", pair_id: str = "",
                relative: bool = False, prior_answerable: bool = False,
                tag_A: float | None = None, centrality: float | None = None,
                qid: str = _PLACEHOLDER_QID) -> Query:
    ev = sorted({(t, o) for fid in ev_fids for t, o, _ in ix.lines(fid, before=t_ask)})
    ev_oids = tuple(dict.fromkeys(o for _, o in ev))
    last_t = max((t for t, _ in ev), default=None)
    delay = day_of(t_ask) - day_of(last_t) if last_t is not None else 0
    facts = [ix.fact[fid] for fid in ev_fids]
    a = cand.A if tag_A is None else tag_A
    cen = _mean([f.centrality for f in facts]) if centrality is None else centrality
    hard = (fam == "ME1" or anchor in ("relation", "description", "relative_date", "none")
            or (fam == "EP3c" and len(ev_oids) >= 5) or (fam in ("SE4", "SE5") and update_count >= 3)
            or (role == "peripheral" and delay >= 60))
    tags = Tags(delay_days=delay, anchor_kind=anchor, n_confusers=n_conf, n_evidence=len(ev_oids),
                target_arousal=a, arousal_decile=decile_of(a, ix.sorted_A) if ev_oids else -1,
                centrality=cen, surprisal_bits=_mean([f.surprisal_bits for f in facts]),
                update_count=update_count, relative_time=relative, partition=partition,
                prior_answerable=prior_answerable, role=role, pair_id=pair_id, hard=hard)
    return Query(qid=qid, family=fam, t_ask=t_ask, text="", fmt="open", gold=gold,
                 evidence_oids=ev_oids, evidence_fids=tuple(ev_fids), tags=tags, cue=tuple(cue),
                 ask=ask, conf=True)


def _date_cue(ix: _Index, day: int, ask_day: int, rng: Any, p_rel: float, max_exact: int
              ) -> tuple[tuple[Slot, ...], str, bool, tuple[Slot, ...]]:
    """(preferred cue, anchor kind, relative?, absolute fallback cue) for an event day."""
    absolute = (Slot(name="date", value=date_of(ix.start, day)),)
    if rng.u() < p_rel:
        phrase = relative_phrase(ask_day - day, fuzzy=False, max_exact=max_exact)
        if phrase:
            return (Slot(name="relative_day", value=phrase),), "relative_date", True, absolute
    return absolute, "date", False, absolute


def _other_bf(ix: _Index, t_ask: int) -> list[tuple[int, str]]:
    return sorted((f.vfrom, ix.value(f)) for f in ix.facts_of("breakfast")
                  if ix.first_t(f.fid) is not None and ix.first_t(f.fid) < t_ask)


def _build_ep1(ix: _Index, cell: Cell, cand: Candidate, rng: Any, partition: str) -> list[Query]:
    cfg = ix.cfg
    anchor_day = day_of(cand.t_ready)
    lo = max(int(cfg.delay_min_days), 1, cell.lag_days)
    hi = min(int(cfg.delay_max_days), ix.last_day - anchor_day)
    delay = _pick_delay(rng, lo, hi)
    if delay is None:
        return []
    ask_day = anchor_day + delay
    t_ask = ask_day * MINUTES_PER_DAY + _ask_minute(rng, cfg)
    bf = _other_bf(ix, t_ask)
    others = [(d, v) for d, v in bf if d != cand.day]
    c_lo, c_hi = cfg.ep1_competing
    if len(others) < c_lo:
        return []
    prior = ix.world.prior("breakfast")
    top3 = prior.top(3) if prior else ()
    D = cand.day
    near = ([("adjacent_day", v) for d, v in others if abs(d - D) == 1]
            + [("confuser", v) for d, v in sorted(others, key=lambda x: (abs(x[0] - D), x[0]))
               if 2 <= abs(d - D) <= 7]
            + [("habit", v) for v in top3])
    cue, anchor, rel, fallback = _date_cue(ix, D, ask_day, rng, cfg.relative_time_share,
                                           int(cfg.get("ep1_relative_max_days", 30)))
    gold = _gold(ix, "entity", cand.value, "breakfast", near)
    out = []
    for cu, an, rl in ((cue, anchor, rel), (fallback, "date", False)):
        out.append(_make_query(ix, cand, "EP1", t_ask, cu, "breakfast", gold, cand.fids, anchor=an,
                               n_conf=min(len(others), c_hi), partition=partition, relative=rl,
                               prior_answerable=cand.value in top3))
        if cu == fallback:
            break
    return out


def _build_se(ix: _Index, cell: Cell, cand: Candidate, rng: Any, partition: str) -> list[Query]:
    cfg = ix.cfg
    fam, ask = cand.family, cand.ask
    f = ix.fact[cand.fids[0]]
    first_day = day_of(cand.t_ready)
    chain = [ix.fact[x] for x in cand.get("chain").split(",")] if cand.get("chain") else [f]
    i = int(cand.get("i", "0"))
    lo_d = max(int(cfg.delay_min_days), 1, cell.lag_days)
    hi_d = int(cfg.delay_max_days)
    if ask == "relation":  # identity: 'who is X', no versions
        anchor_day = first_day
        delay = _pick_delay(rng, lo_d, min(hi_d, ix.last_day - anchor_day))
        if delay is None:
            return []
        t_ask = (anchor_day + delay) * MINUTES_PER_DAY + _ask_minute(rng, cfg)
        gold = _gold(ix, "entity", cand.value, "relation", [])
        return [_make_query(ix, cand, fam, t_ask, (Slot(name="person", value=cand.get("person")),),
                            "relation", gold, cand.fids, anchor="name", n_conf=0,
                            partition=partition)]

    def near_for(t_ask: int) -> list:
        stale = [("stale", ix.value(x)) for x in chain if x.fid != f.fid
                 and ix.first_t(x.fid) is not None and ix.first_t(x.fid) < t_ask]
        others = [("confuser", ix.value(g)) for g in ix.facts_of(ask)
                  if g.subj != f.subj and ix.first_t(g.fid) is not None and ix.first_t(g.fid) < t_ask]
        return stale + others

    if fam == "SE4":
        anchor_day = first_day
        hi = min(hi_d, ix.last_day - anchor_day, (f.vto - anchor_day) if f.vto is not None else 10 ** 9)
        lo = max(lo_d, f.vfrom - anchor_day)
        delay = _pick_delay(rng, lo, hi)
        if delay is None:
            return []
        t_ask = (anchor_day + delay) * MINUTES_PER_DAY + _ask_minute(rng, cfg)
        gold = _gold(ix, "entity", cand.value, ask, near_for(t_ask))
        return [_make_query(ix, cand, fam, t_ask, (), ask, gold, cand.fids, anchor="none",
                            n_conf=len(chain) - 1, partition=partition, update_count=i)]
    # SE5: as of a past date inside the knowable validity of the version
    d_lo = max(f.vfrom, first_day)
    d_hi = min(f.vto if f.vto is not None else ix.last_day, ix.last_day - 1)
    if d_hi < d_lo:
        return []
    D = rng.ri(d_lo, d_hi)
    lo = max(lo_d, 1)
    hi = min(hi_d, ix.last_day - D)
    delay = _pick_delay(rng, lo, hi)
    if delay is None:
        return []
    ask_day = D + delay
    t_ask = ask_day * MINUTES_PER_DAY + _ask_minute(rng, cfg)
    cue, anchor, rel, fallback = _date_cue(ix, D, ask_day, rng, cfg.relative_time_share, 30)
    gold = _gold(ix, "entity", cand.value, ask, near_for(t_ask))
    n_versions = sum(1 for x in chain if ix.first_t(x.fid) is not None and ix.first_t(x.fid) < t_ask)
    out = []
    for cu, an, rl in ((cue, anchor, rel), (fallback, "date", False)):
        out.append(_make_query(ix, cand, fam, t_ask, cu, ask, gold, cand.fids, anchor=an,
                               n_conf=max(0, n_versions - 1), partition=partition, relative=rl,
                               update_count=i))
        if cu == fallback:
            break
    return out


def _build_in1(ix: _Index, cell: Cell, cand: Candidate, rng: Any, partition: str) -> list[Query]:
    cfg = ix.cfg
    anchor_day = cand.day
    lo = max(int(cfg.delay_min_days), 1, cell.lag_days)
    hi = min(int(cfg.delay_max_days), ix.last_day - anchor_day)
    delay = _pick_delay(rng, lo, hi)
    if delay is None:
        return []
    ask_day = anchor_day + delay
    t_ask = ask_day * MINUTES_PER_DAY + _ask_minute(rng, cfg)
    others = [g for g in ix.facts_of("vehicle_colour") if g.src == "read" and g.fid != cand.key
              and ix.first_t(g.fid) is not None and ix.first_t(g.fid) < t_ask]
    if len(others) < int(cfg.in1_min_other_articles):
        return []
    kind, city = cand.get("story_kind"), cand.get("city")
    decoys = [d for d in cand.get("decoys").split("|") if d]
    near = ([("confuser", d) for d in decoys]
            + [("confuser", ix.value(g)) for g in sorted(
                others, key=lambda g: (abs(ix.host[g.fid].day - anchor_day) if g.fid in ix.host else 9999, g.fid))])
    gold = _gold(ix, "entity", cand.value, "vehicle_colour", near)
    u = rng.u()
    p_rel, p_any = cfg.relative_time_share, cfg.anchor_mix
    use_city = bool(city) and (not kind or rng.u() >= p_any)
    base: list = []
    if kind:
        base.append(Slot(name="story_kind", value=kind))
    if use_city:
        base.append(Slot(name="city", value=city))
    full: list = ([Slot(name="story_kind", value=kind)] if kind else []) + (
        [Slot(name="city", value=city)] if city else [])
    absolute = (Slot(name="date", value=date_of(ix.start, anchor_day)),)
    if u < p_rel:
        phrase = relative_phrase(delay, fuzzy=True)
        date_part = (Slot(name="relative_window" if "about" in phrase else "relative_day",
                          value=phrase),)
        anchor, rel = "relative_date", True
    elif u < p_rel + p_any:
        date_part, anchor, rel = (), ("name" if use_city else "description"), False
    else:
        date_part, anchor, rel = absolute, "date", False
    attempts = [(tuple(base) + date_part, anchor, rel),
                (tuple(full) + absolute, "date", False)]
    out = []
    for cu, an, rl in attempts:
        out.append(_make_query(ix, cand, "IN1", t_ask, cu, "vehicle_colour", gold, cand.fids,
                               anchor=an, n_conf=len(others), partition=partition, relative=rl))
    return out


def _build_ep4(ix: _Index, cell: Cell, cand: Candidate, rng: Any, partition: str) -> list[Query]:
    cfg = ix.cfg
    anchor_day = cand.day
    lo = max(int(cfg.delay_min_days), 1, cell.lag_days)
    hi = min(int(cfg.delay_max_days), ix.last_day - anchor_day)
    delay = _pick_delay(rng, lo, hi)
    if delay is None:
        return []
    ask_day = anchor_day + delay
    minute = _ask_minute(rng, cfg)
    t_c = ask_day * MINUTES_PER_DAY + minute
    t_p = min(t_c + 1, (ask_day + 1) * MINUTES_PER_DAY - 1)
    cue, anchor, rel, fallback = _date_cue(ix, anchor_day, ask_day, rng, cfg.relative_time_share, 30)
    cf, pf = ix.fact[cand.get("cfid")], ix.fact[cand.get("pfid")]
    out = []
    for role, fact, ask, t_ask in (("central", cf, "companion", t_c),
                                   ("peripheral", pf, pf.pred, t_p)):
        near = []
        n_conf = 0
        for g in ix.facts_of(fact.pred):
            hs = ix.host.get(g.fid)
            if g.fid == fact.fid or hs is None or abs(hs.day - anchor_day) > 7:
                continue
            if ix.first_t(g.fid) is None or ix.first_t(g.fid) >= t_ask:
                continue
            n_conf += 1
            near.append(("confuser", ix.value(g)))
        gold = _gold(ix, "entity", ix.value(fact), ask, near)
        for cu, an, rl in ((cue, anchor, rel), (fallback, "date", False)):
            out.append(_make_query(ix, cand, "EP4", t_ask, cu, ask, gold, (fact.fid,), anchor=an,
                                   n_conf=n_conf, partition=partition, relative=rl, role=role,
                                   pair_id=cand.get("sid"), tag_A=cand.A))
            if cu == fallback:
                break
    return out


def _build_in4(ix: _Index, cell: Cell, cand: Candidate, rng: Any, partition: str) -> list[Query]:
    cfg = ix.cfg
    anchor_day = day_of(cand.t_ready)
    lo = max(int(cfg.delay_min_days), 1, cell.lag_days, int(cfg.get("in4_min_delay_days", 14)))
    hi = min(int(cfg.delay_max_days), ix.last_day - anchor_day)
    delay = _pick_delay(rng, lo, hi)
    if delay is None:
        return []
    t_ask = (anchor_day + delay) * MINUTES_PER_DAY + _ask_minute(rng, cfg)
    f = ix.fact[cand.key]
    others = [g for g in ix.facts_of("closing_time") if g.fid != f.fid and ix.first_t(g.fid) is not None
              and ix.first_t(g.fid) < t_ask]
    near = [("confuser", ix.value(g)) for g in sorted(others, key=lambda g: (abs((ix.first_t(g.fid) or 0) - cand.t_ready), g.fid))]
    gold = _gold(ix, "time", cand.value, "closing_time", near)
    cue = [Slot(name="shop", value=cand.get("shop"))]
    if cand.get("street"):
        cue.append(Slot(name="street", value=cand.get("street")))
    return [_make_query(ix, cand, "IN4", t_ask, cue, "closing_time", gold, cand.fids, anchor="name",
                        n_conf=len(others), partition=partition)]


def _build_ep3c(ix: _Index, cell: Cell, cand: Candidate, rng: Any, partition: str) -> list[Query]:
    cfg = ix.cfg
    v_first, v_last = int(cand.get("v_first")), int(cand.get("v_last"))
    v_prev, v_next = int(cand.get("v_prev")), int(cand.get("v_next"))
    anchor_day = day_of(cand.t_ready)
    lo = max(int(cfg.delay_min_days), 1, cell.lag_days, v_last + 1 - anchor_day)
    hi = min(int(cfg.delay_max_days), ix.last_day - anchor_day)
    delay = _pick_delay(rng, lo, hi)
    if delay is None:
        return []
    ask_day = anchor_day + delay
    t_ask = ask_day * MINUTES_PER_DAY + _ask_minute(rng, cfg)
    d1 = rng.ri(max(0, v_prev + 1), v_first)
    d2_hi = min((v_next - 1) if v_next >= 0 else ix.last_day, ask_day - 1)
    if d2_hi < v_last:
        return []
    d2 = rng.ri(v_last, d2_hi)
    errand, count = cand.get("errand"), int(cand.get("count"))
    mine, look = 0, 0
    wide = 0
    for f in ix.facts_of_any(ERRAND_PREDS):
        if ix.value(f) != errand or ix.first_t(f.fid) is None or ix.first_t(f.fid) >= t_ask:
            continue
        in_win = d1 <= f.vfrom <= d2
        if ix.narr and f.subj != ix.narr:
            look += 1 if in_win else 0
        else:
            mine += 1 if in_win else 0
            wide += 1 if d1 - 7 <= f.vfrom <= d2 + 7 else 0
    if mine != count:
        return []
    near = []
    if wide != count:
        near.append(("adjacent_day", str(wide)))
    if look:
        near.append(("confuser", str(count + look)))
    gold = _gold(ix, "count", str(count), "visit_count", near)
    cue = (Slot(name="errand", value=errand), Slot(name="window_from", value=date_of(ix.start, d1)),
           Slot(name="window_to", value=date_of(ix.start, d2)))
    return [_make_query(ix, cand, "EP3c", t_ask, cue, "visit_count", gold, cand.fids, anchor="date",
                        n_conf=look, partition=partition)]


def _build_me1(ix: _Index, cell: Cell, cand: Candidate, rng: Any, partition: str) -> list[Query]:
    cfg = ix.cfg
    typ = cand.get("type")
    lo = max(int(cfg.delay_min_days), 1, cell.lag_days)
    if typ == "breakfast":
        D = int(cand.get("day"))
        hi = min(int(cfg.delay_max_days), ix.last_day - D)
        delay = _pick_delay(rng, lo, hi)
        if delay is None:
            return []
        ask_day = D + delay
        t_ask = ask_day * MINUTES_PER_DAY + _ask_minute(rng, cfg)
        bf = _other_bf(ix, t_ask)
        near = ([("adjacent_day", v) for d, v in bf if abs(d - D) == 1]
                + [("confuser", v) for d, v in bf if 2 <= abs(d - D) <= 7])
        if not any(k == "adjacent_day" for k, _ in near):
            return []
        cue, anchor, rel, _fb = _date_cue(ix, D, ask_day, rng, cfg.relative_time_share,
                                          int(cfg.get("ep1_relative_max_days", 30)))
        gold = Gold(kind="unknown", value="UNKNOWN", vocab_id=SLOTS["breakfast"],
                    near_miss=_near("UNKNOWN", near))
        return [_me1_query(ix, cand, t_ask, cue, "breakfast", gold, anchor, rel, partition,
                           delay=delay, n_conf=len(bf))]
    ask_day = rng.ri(max(lo, ix.last_day // 2), ix.last_day)
    t_ask = ask_day * MINUTES_PER_DAY + _ask_minute(rng, cfg)
    if typ == "trip":
        city = cand.get("city")
        near = []
        for f in ix.facts_of("visited"):
            hs = ix.host.get(f.fid)
            if hs is None or ix.first_t(f.fid) is None or ix.first_t(f.fid) >= t_ask:
                continue
            for fid in hs.facts:
                g = ix.fact.get(fid)
                if g is not None and g.pred in TRIP_COMPANION_PREDS and ix.first_t(g.fid) is not None \
                        and ix.first_t(g.fid) < t_ask:
                    near.append(("confuser", ix.value(g)))
        if not near:
            return []
        gold = Gold(kind="unknown", value="UNKNOWN", vocab_id=SLOTS["companion"],
                    near_miss=_near("UNKNOWN", near))
        return [_me1_query(ix, cand, t_ask, (Slot(name="city", value=city),), "companion", gold,
                           "name", False, partition, delay=0, n_conf=len(near))]
    shop = cand.get("shop")
    near = [("confuser", ix.value(g)) for g in ix.facts_of("closing_time")
            if ix.first_t(g.fid) is not None and ix.first_t(g.fid) < t_ask]
    if not near:
        return []
    gold = Gold(kind="unknown", value="UNKNOWN", vocab_id=SLOTS["closing_time"],
                near_miss=_near("UNKNOWN", near))
    return [_me1_query(ix, cand, t_ask, (Slot(name="shop", value=shop),), "closing_time", gold,
                       "name", False, partition, delay=0, n_conf=len(near))]


def _me1_query(ix: _Index, cand: Candidate, t_ask: int, cue: Sequence[Slot], ask: str, gold: Gold,
               anchor: str, rel: bool, partition: str, delay: int, n_conf: int) -> Query:
    tags = Tags(delay_days=delay, anchor_kind=anchor, n_confusers=n_conf, n_evidence=0,
                relative_time=rel, partition=partition, hard=True)
    return Query(qid=_PLACEHOLDER_QID, family="ME1", t_ask=t_ask, text="", fmt="open", gold=gold,
                 tags=tags, cue=tuple(cue), ask=ask, conf=True)


_BUILDERS = {"EP1": _build_ep1, "SE4": _build_se, "SE5": _build_se, "IN1": _build_in1,
             "EP4": _build_ep4, "IN4": _build_in4, "EP3c": _build_ep3c, "ME1": _build_me1}


# ----------------------------------------------------------- the independent second solver


def _slow_scan(world: World, t_ask: int) -> Iterator[tuple[Any, Any, Any]]:
    """(spec, mention, fact) for every observing mention in a spec strictly before ``t_ask``."""
    for spec in world.obs_specs:
        if spec.t_obs >= t_ask:
            break
        for m in spec.mentions:
            if m.role not in OBSERVING_ROLES:
                continue
            try:
                fact = world.fact(m.fid)
            except KeyError:
                continue
            yield spec, m, fact


def _slow_value(world: World, spec: Any, fact: Any) -> str:
    for s in spec.slots:
        if s.fid == fact.fid:
            return s.value
    try:
        return world.entity(fact.obj).name
    except KeyError:
        return fact.obj


def _slow_slot(spec: Any, name: str) -> str:
    for s in spec.slots:
        if s.name == name:
            return s.value
    return ""


def _valid_in(fact: Any, lo: int, hi: int) -> bool:
    return fact.vfrom <= hi and (fact.vto is None or fact.vto >= lo)


def slow_answers(world: World, query: Query) -> list[str]:
    """Every answer consistent with the question, found by a naive scan of the raw observation
    specs and facts from the query's own ``ask``, ``cue`` and ``t_ask`` (it reads neither the
    evidence lists nor the tags nor the candidate pool). One element means a unique answer; none
    means the log does not contain it (UNKNOWN, or a count of 0 for ``visit_count``); two or more
    mean the cue is ambiguous. Values are the verbatim slot strings of the observing lines."""
    ask, t_ask = query.ask, query.t_ask
    cues = {s.name: s.value for s in query.cue}
    start = world.cfg.start_date
    ask_day = day_of(t_ask)
    window = _cue_window(cues, ask_day, start)
    narr = narrator_id(world)
    vals: list[str] = []

    def add(v: str) -> None:
        if v not in vals:
            vals.append(v)

    if ask == "breakfast":
        if window is None:
            return []
        for spec, _m, f in _slow_scan(world, t_ask):
            if f.pred == "breakfast" and _valid_in(f, window[0], window[1]):
                add(_slow_value(world, spec, f))
    elif ask in SE_PREDS:
        lo, hi = window if window is not None else (ask_day, ask_day)
        for spec, _m, f in _slow_scan(world, t_ask):
            if f.pred == ask and (not narr or f.subj == narr) and _valid_in(f, lo, hi):
                add(_slow_value(world, spec, f))
    elif ask == "relation":
        eids = {e.eid for e in world.entities if e.name == cues.get("person") and e.kind == "person"}
        for spec, _m, f in _slow_scan(world, t_ask):
            if f.pred == "relation" and f.subj in eids and _valid_in(f, ask_day, ask_day):
                add(_slow_value(world, spec, f))
    elif ask in _CAR_PREDS and ("story_kind" in cues or "city" in cues):  # IN1: an article
        for spec, _m, f in _slow_scan(world, t_ask):
            if f.pred != ask or (f.src != "read" and spec.channel != "article"):
                continue
            kind, city = _slow_slot(spec, "story_kind"), _slow_slot(spec, "city")
            if not kind and not city:
                try:
                    ent = world.entity(f.subj)
                except KeyError:
                    ent = None
                kind, city = story_parts(ent.name) if ent is not None and ent.kind == "story" else ("", "")
            if "story_kind" in cues and kind != cues["story_kind"]:
                continue
            if "city" in cues and city != cues["city"]:
                continue
            if window is not None and not window[0] <= spec.day <= window[1]:
                continue
            add(_slow_value(world, spec, f))
    elif ask in _CAR_PREDS or (ask == "companion" and "city" not in cues):  # EP4: day of a situation
        if window is None:
            return []
        preds = (ask,)
        for spec, _m, f in _slow_scan(world, t_ask):
            sit = _sit(world, spec.sid)
            if f.pred in preds and f.src == "lived" and sit is not None and f.fid in sit.facts \
                    and window[0] <= sit.day <= window[1]:
                add(_slow_value(world, spec, f))
    elif ask == "companion":  # ME1 false premise: a trip to a named city
        eids = {e.eid for e in world.entities if e.name == cues.get("city") and e.kind == "city"}
        trips = set()
        for spec, _m, f in _slow_scan(world, t_ask):
            if f.pred == "visited" and f.obj in eids:
                sit = _sit(world, spec.sid)
                if sit is not None:
                    trips.add(sit.sid)
        for spec, _m, f in _slow_scan(world, t_ask):
            sit = _sit(world, spec.sid)
            if f.pred in TRIP_COMPANION_PREDS and sit is not None and sit.sid in trips and f.fid in sit.facts:
                add(_slow_value(world, spec, f))
    elif ask == "closing_time":
        eids = {e.eid for e in world.entities if e.name == cues.get("shop") and e.kind == "shop"}
        for spec, _m, f in _slow_scan(world, t_ask):
            if f.pred == "closing_time" and f.subj in eids:
                add(_slow_value(world, spec, f))
    elif ask == "visit_count":
        try:
            d1 = day_index(start, cues["window_from"])
            d2 = day_index(start, cues["window_to"])
        except (KeyError, ValueError):
            return ["0"]
        seen = set()
        for spec, _m, f in _slow_scan(world, t_ask):
            if f.pred not in ERRAND_PREDS or f.fid in seen or (narr and f.subj != narr):
                continue
            if _slow_value(world, spec, f) == cues.get("errand") and d1 <= f.vfrom <= d2:
                seen.add(f.fid)
        return [str(len(seen))]
    return vals


def gold_slow(world: World, query: Query) -> Gold:
    """The gold of a query by the independent scan (see ``slow_answers``). Raises
    ``AmbiguousGold`` if two or more answers are consistent. The kind is entity, time or count
    from the asked predicate; no consistent answer gives ``Gold(kind='unknown')``."""
    vals = slow_answers(world, query)
    vid = SLOTS.get(query.ask, query.gold.vocab_id)
    if query.ask == "visit_count":
        return Gold(kind="count", value=vals[0], vocab_id=vid)
    if not vals:
        return Gold(kind="unknown", value="UNKNOWN", vocab_id=vid)
    if len(vals) > 1:
        raise AmbiguousGold("%s %s: %d consistent answers %s" % (query.family, query.ask, len(vals), vals))
    return Gold(kind="time" if query.ask == "closing_time" else "entity", value=vals[0], vocab_id=vid)


# ----------------------------------------------------------- ablation and the memory filter


def ablate_lines(world: World, oids: Sequence[str]) -> World:
    """The world with the given observation lines deleted (facts and situations stay), the
    'ablated world' of the memory-dependence check."""
    drop = set(oids)
    return dataclasses.replace(world, obs_specs=tuple(o for o in world.obs_specs if o.oid not in drop))


def _hard_checks(world: World, queries: Sequence[Query], drop_prior_answerable: bool,
                 check_ablation: bool) -> tuple[list[Query], list[tuple[str, str]]]:
    prior = world.prior("breakfast")
    top3 = set(prior.top(3)) if prior else set()
    kept: list[Query] = []
    dropped: list[tuple[str, str]] = []
    for x in queries:
        vals = slow_answers(world, x)
        if x.family == "ME1":
            if vals:
                dropped.append((x.qid, "me1_not_absent"))
            else:
                kept.append(x)
        elif x.gold.value not in vals:
            dropped.append((x.qid, "gold_not_derivable"))
        elif len(vals) > 1:
            dropped.append((x.qid, "ambiguous"))
        elif drop_prior_answerable and (x.tags.prior_answerable
                                        or (x.ask == "breakfast" and x.gold.value in top3)):
            dropped.append((x.qid, "habit_top3"))
        elif check_ablation and x.gold.value in slow_answers(ablate_lines(world, x.evidence_oids), x):
            dropped.append((x.qid, "ablated_world_solvable"))
        else:
            kept.append(x)
    return kept, dropped


def _units(queries: Sequence[Query]) -> list[list[Query]]:
    """Group queries into selection units: the two queries of an EP4 pair stay together."""
    units: list[list[Query]] = []
    index: dict = {}
    for x in queries:
        key = (x.family, x.tags.pair_id) if x.tags.pair_id else None
        if key is not None and key in index:
            index[key].append(x)
            continue
        u = [x]
        units.append(u)
        if key is not None:
            index[key] = u
    return units


def _cap_select(units: Sequence[Sequence[Query]], share: float, n_nominal: int, n_max: int
                ) -> list[Sequence[Query]]:
    """Greedy selection under the constant-guess cap: accept units in order while no
    (family, ask, gold value) occurs more than max(1, floor(share * n_nominal)) times, up to
    ``n_max`` units; then re-apply the cap with the size actually reached until nothing changes."""

    def one_pass(items: Sequence[Sequence[Query]], n_ref: int, limit: int) -> list:
        cap = max(1, int(math.floor(share * n_ref + 1e-9)))
        counts: dict = {}
        out: list = []
        for u in items:
            if len(out) >= limit:
                break
            keys = [(x.family, x.ask, x.gold.value) for x in u]
            if all(counts.get(k, 0) < cap for k in keys):
                out.append(u)
                for k in keys:
                    counts[k] = counts.get(k, 0) + 1
        return out

    cur = one_pass(units, n_nominal, n_max)
    while True:
        nxt = one_pass(cur, len(cur), len(cur))
        if len(nxt) == len(cur):
            return cur
        cur = nxt


def structural_memory_filter(world: World, queries: Sequence[Query],
                             max_const_share: float | None = None,
                             drop_prior_answerable: bool = True,
                             check_ablation: bool = True) -> FilterResult:
    """Drop the items a blind guess or an ablated world can solve.

    An item is dropped if: its gold is not what the slow scan derives ('gold_not_derivable'),
    the cue has a second consistent answer ('ambiguous'), an ME1 item is not absent from the log
    ('me1_not_absent'), its gold is in the habit top-3 of the breakfast prior ('habit_top3';
    kept when ``drop_prior_answerable`` is False, flagged by ``tags.prior_answerable``), its gold
    is still derivable after its evidence lines are deleted ('ablated_world_solvable'), or its
    gold value occurs more often within its (family, ask) group than a constant guess may score
    ('constant_guess_cap': at most max(1, floor(share * n)) items per value, iterated to a fixed
    point; share ``max_const_share`` or ``cfg.max_const_share``, default 0.15; the two queries
    of an EP4 pair stand or fall together). ME1 is exempt from the constant-guess rule
    (always-abstain is reported through the cost-weighted score)."""
    share = (float(max_const_share) if max_const_share is not None
             else float(world.cfg.get("max_const_share", 0.15)))
    kept, dropped = _hard_checks(world, queries, drop_prior_answerable, check_ablation)
    ans = [x for x in kept if x.family != "ME1"]
    units = _units(ans)
    chosen = _cap_select(units, share, len(units), len(units))
    keep_ids = {id(x) for u in chosen for x in u}
    out = []
    for x in kept:
        if x.family == "ME1" or id(x) in keep_ids:
            out.append(x)
        else:
            dropped.append((x.qid, "constant_guess_cap"))
    return FilterResult(tuple(out), tuple(dropped))


# ----------------------------------------------------------------- default question text

_WHEN = ("date", "relative_day", "relative_window")


def _when(cues: dict) -> str:
    if "date" in cues:
        return "on %s" % cues["date"]
    for k in ("relative_day", "relative_window"):
        if k in cues:
            return cues[k]
    return ""


def plain_question(query: Query, partition: str = "dev") -> str:
    """A trivial, readable rendering of a query: the stand-in for ``verbalise.render_question``
    (same signature). Every cue value appears verbatim; choice options are listed; the CONF
    request is appended when ``query.conf``."""
    c = {s.name: s.value for s in query.cue}
    w = _when(c)
    ask, fam = query.ask, query.family
    if ask == "breakfast":
        t = "What did I have for breakfast %s?" % w
    elif ask == "lives_in":
        t = "Which city do I live in now?" if not w else "Which city did I live in %s?" % w
    elif ask == "works_as":
        t = "What is my job now?" if not w else "What was my job %s?" % w
    elif ask == "works_at":
        t = "Where do I work now?" if not w else "Where did I work %s?" % w
    elif ask == "relation":
        t = "What is %s to me?" % c.get("person", "this person")
    elif ask in _CAR_PREDS and ("story_kind" in c or "city" in c):
        topic = ("the %s" % c["story_kind"]) if "story_kind" in c else "the story"
        if "city" in c:
            topic += " in %s" % c["city"]
        t = "What colour was the car in the article about %s that I read%s?" % (
            topic, (" " + w) if w else "")
    elif ask in _CAR_PREDS:
        t = "What colour was the car parked outside %s?" % w
    elif ask == "companion" and "city" in c:
        t = "When I visited %s, who came with me?" % c["city"]
    elif ask == "companion":
        t = "Who was with me %s when I got the news?" % w
    elif ask == "closing_time":
        t = "At what time does the %s%s close on Saturdays?" % (
            c.get("shop", "shop"), (" on %s" % c["street"]) if "street" in c else "")
    elif ask == "visit_count":
        t = "How many times did I go to the %s between %s and %s?" % (
            c.get("errand", "place"), c.get("window_from", "?"), c.get("window_to", "?"))
    else:
        t = "Question about %s (%s)?" % (ask, fam)
    if query.fmt == "choice":
        t += " Options: " + " ".join("%s) %s" % ("ABCDEFGH"[i], o) for i, o in enumerate(query.options))
    if query.conf:
        t += " Answer, then give CONF: 0-100."
    return t


# ----------------------------------------------------------------------- choice forks


def make_choice_fork(world: World, query: Query, n_options: int = 4, seed: int | None = None) -> Query | None:
    """The forced-choice fork of an open query: the same cue, options = the gold plus lures from
    the same life (near-miss values first, then other values of the same predicate), in a
    seeded random order. ``twin_of`` names the open query. None if too few lures exist."""
    if query.family == "ME1" or query.gold.kind == "unknown":
        return None
    gold = query.gold.value
    lures = [nm.value for nm in query.gold.near_miss]
    if query.gold.kind == "count":
        n = int(gold)
        lures += [str(v) for v in (n + 1, n - 1, n + 2, n - 2, n + 3) if v >= 0]
    else:
        lures += sorted({_slow_fact_value(world, f) for f in world.facts if f.pred == query.ask})
        try:
            lures += list(closed_vocab(world, query.gold.vocab_id).values)
        except KeyError:
            pass
    opts = [gold]
    for v in lures:
        if v != gold and v not in opts:
            opts.append(v)
        if len(opts) >= n_options:
            break
    if len(opts) < n_options:
        return None
    rng = stream(world.seed if seed is None else seed, "query", "choice", query.qid)
    rng.shuffle(opts)
    return dataclasses.replace(query, fmt="choice", options=tuple(opts), twin_of=query.qid)


def _slow_fact_value(world: World, f: Any) -> str:
    try:
        return world.entity(f.obj).name
    except KeyError:
        return f.obj


# ------------------------------------------------------------------ evidence containment


def evidence_check(world: World, query: Query, obs: Sequence[Any] | None = None) -> list[str]:
    """Problems with the evidence of a query ([] = fine): every cited line exists, precedes
    ``t_ask`` and carries the answer verbatim in a slot (the errand name for counts), and, when
    rendered ``obs`` are given, in its text; an ME1 item cites nothing and its premise is absent."""
    problems: list[str] = []
    texts = {o.oid: o.text for o in obs} if obs is not None else {}
    if query.family == "ME1":
        if query.evidence_oids:
            problems.append("ME1 must cite no lines")
        if slow_answers(world, query):
            problems.append("ME1 premise is not absent from the log")
        return problems
    if not query.evidence_oids:
        problems.append("no evidence lines")
    cues = {s.name: s.value for s in query.cue}
    want = cues.get("errand") if query.ask == "visit_count" else query.gold.value
    for oid in query.evidence_oids:
        try:
            spec = world.obs_spec(oid)
        except KeyError:
            problems.append("unknown line %s" % oid)
            continue
        if spec.t_obs >= query.t_ask:
            problems.append("line %s is not before t_ask" % oid)
        if not any(s.value == want for s in spec.slots):
            problems.append("line %s has no slot with %r" % (oid, want))
        if texts and norm(want) not in norm(texts.get(oid, "")):
            problems.append("text of %s does not contain %r" % (oid, want))
    return problems


def check_query_support(world: World, min_per_family: int = 1) -> list[str]:
    """Problems that stop ``build_queries`` from using a world ([] = fine): families with fewer
    than ``min_per_family`` candidates, and a missing narrator. Use it to check ``world.py``
    output against the structure described in the module docstring."""
    problems = []
    if not narrator_id(world):
        problems.append("no narrator subject found (no breakfast, chain or errand facts)")
    for fam, cands in candidate_pool(world).by_family:
        if len(cands) < min_per_family:
            problems.append("family %s has %d candidates (need %d)" % (fam, len(cands), min_per_family))
    return problems


# ------------------------------------------------------------------------- build_queries


def wanted_counts(cfg: Any) -> dict:
    """Queries wanted per family: ME1 gets ``abstain_share`` of ``queries_per_world`` (rounded),
    the rest follows ``family_mix`` by largest remainder; EP4 is raised to an even number because
    its queries come in central-peripheral pairs."""
    total = int(cfg.queries_per_world)
    n_me1 = int(round(total * cfg.abstain_share))
    mix = dict(cfg.family_mix)
    fams = [f for f in FAMILY_ORDER if f != "ME1" and f in mix]
    want = _split_counts(total - n_me1, [(f, mix[f]) for f in fams])
    want["ME1"] = n_me1
    if want.get("EP4", 0) % 2:
        want["EP4"] += 1
    return want


def _split_counts(total: int, shares: Sequence[tuple[str, float]]) -> dict:
    probs = [s for _, s in shares]
    counts = _largest_remainder(probs, total)
    return {fam: c for (fam, _), c in zip(shares, counts)}


def _first_consistent(world: World, attempts: Sequence[Query]) -> tuple[Query | None, str]:
    """The first attempt whose independent scan gives exactly its gold (for ME1: nothing at all);
    else None and the reason of the last failure ('ambiguous' or 'mismatch')."""
    why = "mismatch"
    for x in attempts:
        got = slow_answers(world, x)
        if got == [x.gold.value] or (x.gold.kind == "unknown" and not got):
            return x, ""
        why = "ambiguous" if x.gold.value in got and len(got) > 1 else "mismatch"
    return None, why


def _me1_order(rng: Any, cands: Sequence[Candidate]) -> list[Candidate]:
    """False-premise candidates in a seeded order that cycles through the trap types (a day with no
    breakfast line, an unvisited city, a shop with no closing time) so that one type does not
    swamp the others: breakfast, shop, trip, breakfast, ..., each type in random order."""
    by_type: dict = {}
    for c in sorted(cands, key=lambda c: c.key):
        by_type.setdefault(c.get("type"), []).append(c)
    lists = {t: rng.sample(v, len(v)) for t, v in sorted(by_type.items())}
    cycle = [t for t in ("breakfast", "shop", "trip", "breakfast") if t in lists]
    cycle += [t for t in sorted(lists) if t not in cycle]
    pos = {t: 0 for t in lists}
    out: list[Candidate] = []
    while any(pos[t] < len(lists[t]) for t in lists):
        for t in cycle:
            if pos[t] < len(lists[t]):
                out.append(lists[t][pos[t]])
                pos[t] += 1
    return out


class _Ctx:
    """Everything a family build needs, shared by all families of one ``build_queries_ex`` call."""

    def __init__(self, world: World, ix: _Index, cell: Cell, part: str, report: "BuildReport",
                 keep_habit: bool) -> None:
        self.world, self.ix, self.cell, self.part = world, ix, cell, part
        self.report, self.keep_habit = report, keep_habit


class _FamState:
    """Progress of one family: the units (a query, or the two queries of an EP4 pair) accepted so
    far, how often each (family, ask, value) was used, and the position in each decile's list."""

    def __init__(self, fam: str, n_units: int, cap: int, rng: Any) -> None:
        self.fam, self.n_units, self.cap, self.rng = fam, n_units, cap, rng
        self.builder = _BUILDERS[fam]
        self.value_counts: dict = {}
        self.units: list[list[Query]] = []
        self.tried = 0
        self.lists: list[list[Candidate]] = [[] for _ in range(10)]
        self.pos = [0] * 10
        self.got = [0] * 10
        self.got_first = [0] * 10
        self.quota: Quota | None = None


def _try(ctx: _Ctx, st: _FamState, cand: Candidate) -> bool:
    """Turn one candidate into a unit; True if it was accepted (the unit is appended)."""
    fam, report = st.fam, ctx.report
    st.tried += 1
    attempts = st.builder(ctx.ix, ctx.cell, cand, st.rng, ctx.part)
    if not attempts:
        report.drop(fam, "no_feasible_ask")
        return False
    if fam == "EP4":
        groups = [[x for x in attempts if x.tags.role == r] for r in ("central", "peripheral")]
    else:
        groups = [attempts]
    picked = []
    for g in groups:
        ok, why = _first_consistent(ctx.world, g)
        if ok is None:
            report.drop(fam, why if fam != "EP4" else "pair_incomplete")
            return False
        picked.append(ok)
    good, dropped = _hard_checks(ctx.world, picked, not ctx.keep_habit, True)
    for _qid, reason in dropped:
        report.drop(fam, reason)
    if len(good) != len(picked):
        return False
    if fam != "ME1":
        keys = [(x.family, x.ask, x.gold.value) for x in picked]
        if any(st.value_counts.get(kk, 0) >= st.cap for kk in keys):
            report.drop(fam, "constant_guess_cap")
            return False
        for kk in keys:
            st.value_counts[kk] = st.value_counts.get(kk, 0) + 1
    st.units.append([dataclasses.replace(x, qid="%s:%04d:%d" % (fam, len(st.units), j))
                     for j, x in enumerate(picked)])
    return True


def _advance(ctx: _Ctx, st: _FamState, j: int) -> bool:
    """Try the untried candidates of decile ``j`` in order until one is accepted."""
    lst = st.lists[j]
    while st.pos[j] < len(lst):
        cand = lst[st.pos[j]]
        st.pos[j] += 1
        if _try(ctx, st, cand):
            st.got[j] += 1
            return True
    return False


def build_queries_ex(world: World, cfg: Any = None, cell: Cell | str | None = None,
                     render: Callable[[Query, str], str] | None = None,
                     partition: str | None = None) -> BuildResult:
    """Build the queries of a world for a coupling cell and report what happened.

    Per family the number wanted follows ``cfg.family_mix`` (ME1 gets ``abstain_share`` of
    ``queries_per_world``). The shaped families (all but IN4, whose remarks are quiet by
    construction, and ME1, which cites nothing) get the cell's decile quota with the rounding
    diffused across families, and IN4's fixed share is compensated in their E, so the pooled
    E_0.10 tracks the cell. Within each decile (the top first) a family walks its candidates in
    seeded random order: a candidate becomes a query if its cue and ask time exist, the
    independent scan confirms its gold, the memory-dependence checks pass and the constant-guess
    cap is not exceeded; otherwise the next candidate of the decile replaces it (this realises
    ``query_overgenerate``; the number tried is ``report.drawn``). Quota that a family cannot fill
    from its own candidates is offered round-robin to the other shaped families (set the extra
    parameter ``quota_redistribute`` to 0 to forbid it); what no family can fill is the pooled
    shortfall ``report.pooled_shortfall`` (the G-SUPPORT quantity), and each family's own
    shortfall before redistribution is in ``report.quotas``. The result is sorted by ``t_ask``
    with qids ``q0001...`` and the text rendered by ``render(query, partition)`` (default
    ``plain_question``). Deterministic in (world, cfg, cell, partition)."""
    cfg = cfg or world.cfg
    cell = CELLS[cell] if isinstance(cell, str) else (cell or CELLS["C0"])
    part = partition or world.partition
    render_fn = render or plain_question
    ix = _Index(world, cfg)
    pool = candidate_pool(world, cfg)
    report = BuildReport()
    ctx = _Ctx(world, ix, cell, part, report, bool(cfg.get("keep_prior_answerable", 0)))
    A_all = ix.A_lines
    want = wanted_counts(cfg)
    fams = [f for f in FAMILY_ORDER if f != "ME1" and f in want]
    n_ans = max(1, sum(want[f] for f in fams))
    s_fixed = want.get("IN4", 0) / n_ans
    e_shaped = min(9.9, cell.e_target / (1.0 - s_fixed)) if s_fixed < 0.9 else cell.e_target
    share = float(cfg.get("max_const_share", 0.15))
    _kappa, shape_probs, _feasible = _shape(e_shaped, cell.mu)
    carry = [0.0] * 10
    states: dict = {}
    for fam in FAMILY_ORDER:
        k = want.get(fam, 0)
        report.requested[fam] = k
        cands = [c for c in pool.of(fam) if ctx.keep_habit or c.get("prior_answerable") != "1"]
        report.kept[fam] = 0
        if k <= 0 or not cands:
            continue
        n_units = k // 2 if fam == "EP4" else k
        st = _FamState(fam, n_units, max(1, int(math.floor(share * n_units + 1e-9))),
                       stream(world.seed, "query", fam, "build"))
        states[fam] = st
        if fam in ("IN4", "ME1"):
            order = (_me1_order(st.rng, cands) if fam == "ME1"
                     else st.rng.sample(sorted(cands, key=lambda c: c.key), len(cands)))
            for cand in order:
                if len(st.units) >= n_units:
                    break
                _try(ctx, st, cand)
            continue
        raw = [p * n_units + c for p, c in zip(shape_probs, carry)]
        base = [max(0, int(math.floor(x + 1e-9))) for x in raw]
        for j in sorted(range(10), key=lambda j: (-(raw[j] - base[j]), j))[:max(0, n_units - sum(base))]:
            base[j] += 1
        carry = [r - b for r, b in zip(raw, base)]
        st.quota = solve_quota(cell, A_all, cands, n_units, e_shaped, counts=base)
        st.lists = shuffled_by_decile(cands, A_all, world.seed, fam)
    shaped = [states[f] for f in FAMILY_ORDER if f in states and states[f].quota is not None]
    for j in range(9, -1, -1):
        for st in shaped:
            while st.got[j] < st.quota.counts[j]:
                if not _advance(ctx, st, j):
                    break
    for st in shaped:
        st.got_first = list(st.got)
    pooled_short = 0
    redistribute = bool(cfg.get("quota_redistribute", 1))
    for j in range(9, -1, -1):
        deficit = sum(st.quota.counts[j] for st in shaped) - sum(st.got[j] for st in shaped)
        progress = redistribute
        while deficit > 0 and progress:
            progress = False
            for st in shaped:
                if deficit > 0 and _advance(ctx, st, j):
                    deficit -= 1
                    progress = True
        pooled_short += max(0, deficit)
    report.pooled_shortfall = pooled_short
    report.pooled_demand = sum(sum(st.quota.counts) for st in shaped)
    made: dict = {}
    for fam in FAMILY_ORDER:
        st = states.get(fam)
        if st is None:
            made[fam] = []
            continue
        if st.quota is not None:
            report.quotas[fam] = dataclasses.replace(
                st.quota, taken=tuple(st.got_first),
                shortfall=sum(max(0, c - g) for c, g in zip(st.quota.counts, st.got_first)))
        units = st.units
        if fam != "ME1":
            before = len(units)
            units = [list(u) for u in _cap_select(units, share, len(units), len(units))]
            report.drop(fam, "constant_guess_cap", before - len(units))
        report.drawn[fam] = st.tried
        made[fam] = [x for u in units for x in u]
        report.kept[fam] = len(made[fam])
    allq = [x for fam in FAMILY_ORDER for x in made.get(fam, [])]
    order = {fam: i for i, fam in enumerate(FAMILY_ORDER)}
    allq.sort(key=lambda x: (x.t_ask, order[x.family], x.qid))
    final = []
    for i, x in enumerate(allq, start=1):
        x = dataclasses.replace(x, qid=new_id("query", i))
        final.append(dataclasses.replace(x, text=render_fn(x, part)))
    fork_share = float(cfg.get("choice_fork_share", 0.0))
    if fork_share > 0.0:
        rng = stream(world.seed, "query", "choice", "select")
        forks = []
        for x in final:
            if x.family != "ME1" and rng.chance(fork_share):
                fk = make_choice_fork(world, x, int(cfg.get("choice_options", 4)))
                if fk is not None:
                    forks.append(fk)
        nxt = len(final)
        for fk in forks:
            nxt += 1
            fk = dataclasses.replace(fk, qid=new_id("query", nxt))
            final.append(dataclasses.replace(fk, text=render_fn(fk, part)))
    return BuildResult(tuple(final), report, pool)


def build_queries(world: World, cfg: Any = None, cell: Cell | str | None = None,
                  render: Callable[[Query, str], str] | None = None,
                  partition: str | None = None) -> list[Query]:
    """The queries of a world for a coupling cell (see ``build_queries_ex``): a list sorted by
    ``t_ask`` with qids ``q0001...``, text filled by ``render`` (default ``plain_question``;
    pass ``verbalise.render_question`` for the real question frames)."""
    return list(build_queries_ex(world, cfg, cell, render, partition).queries)
