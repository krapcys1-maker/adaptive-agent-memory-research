"""The structure of a LifeSim life: frozen dataclasses, JSON round trip, stable digests.

Principle: structure first, text second. Every queryable thing is a row of structured
state (``Entity``, ``Fact``, ``Situation``, ``ObsSpec``); text is rendered from rows by
``verbalise`` and gold is computed from rows. This module is the single place where the
types of the whole slice live, so that no other module has to edit it:

* data rows: ``Entity Fact Feats Situation Mention Slot ObsSpec Obs Prior Card Channel World``
* questions and scoring: ``NearMiss Gold Tags Query Cell ScoreRecord``
* configuration: ``TierCfg`` (every generator parameter that is an assumption, each
  documented as ASSUMED in its field metadata; presets ``TIERS`` for L0-L3)
* system protocol types (data only, the behaviour lives in ``lifesim.interface``):
  ``Record ContextItem LifeAnswer``
* helpers: id formats, minute/day/date arithmetic, seed epochs and partitions,
  canonical JSON, ``digest_of``, JSONL and world files (``save_world``/``load_world``).

Conventions every module must follow
------------------------------------
* Time is an integer: ``t_obs`` and ``t_ask`` are minutes since 00:00 of day 0;
  ``Fact.vfrom``/``vto`` and ``Situation.day`` are day indexes (``vto`` inclusive,
  ``None`` = still valid). ISO dates come from ``TierCfg.start_date`` via ``date_of``.
* Every object is constructed with keyword arguments, validates its enumerations,
  turns lists into tuples, turns ints into floats where a float is declared, and
  quantises declared float fields to 6 decimals (``rng.q``), so a digest never depends
  on the last bit of a library result. Floats that you compute yourself and store
  elsewhere must go through ``rng.q`` too.
* ``digest()`` is the SHA-256 of the canonical JSON (sorted keys, no spaces, ASCII).
  ``World.digest()`` is the digest of the *structure* only: it ignores ``cfg``,
  ``channel`` and every rendering choice, so it is the same under any verbaliser,
  coupling cell, channel arm and gate policy.
* Ids are opaque and assigned once at generation (``new_id``); deleting events never
  renumbers, so per-event streams ``stream(seed, "life", sid)`` stay valid.
* Dataclasses hold no dicts; mappings are tuples of pairs.

What this module does NOT do: it generates nothing, scores nothing and renders nothing;
it does not check that a world is consistent (``world.check_world`` does); it does not
read the clock, call a model, or use ``random``/``hash()``.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import functools
import hashlib
import json
import math
import types
import typing
from dataclasses import dataclass, field, fields, is_dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar, Iterable

from . import GENERATOR_ID
from .rng import entropy_bits as _entropy_bits
from .rng import q

SCHEMA_VERSION = "lifesim-schema-1"

# ----------------------------------------------------------------------- enumerations

MINUTES_PER_DAY = 1440
PARTITIONS = ("dev", "test")
CHANNELS = ("diary", "chat", "article", "log", "note", "dialogue")
SRC_KINDS = ("lived", "told", "read")
MENTION_ROLES = ("assert", "update", "retract", "recall")
NEAR_MISS_KINDS = ("stale", "adjacent_day", "confuser", "habit")
GOLD_KINDS = ("entity", "count", "time", "date", "letter", "class", "order", "bool", "unknown")
FORMATS = ("open", "choice")
ENTITY_KINDS = ("person", "city", "street", "shop", "org", "place", "story", "pet", "item")
SCENE_NAMES = ("routine", "minor", "major", "move", "health", "purchase", "remark", "trip",
               "article")
ANCHOR_KINDS = ("name", "date", "relation", "description", "relative_date", "none")
MAPPINGS = ("M1", "M2", "M3")
AFFECT_MODES = ("A0", "A1", "A2")
REHEARSAL_LEVELS = ("off", "natural", "strong")
ROLES = ("", "central", "peripheral")
ERROR_TYPES = ("", "omission", "commission", "stale", "adjacent_day", "confuser", "habit",
               "hedge", "unmatched", "fabricated", "hallucination_on_abstain",
               "parse_failure", "other")
CHANNEL_ARMS = ("TRUE", "SHUF_TYPE", "SHUF_LIFE", "TIME_SHIFT", "RANDOM", "CONST", "INVERTED",
                "NUISANCE_ONLY", "LAG", "ABSENT", "ORACLE", "LEAKY")
GATE_POLICIES = ("ALL", "GU", "GR", "GN", "GM", "GS", "GH", "GTN", "GO", "GA", "GL")
#: Day-1 families (SE4 and SE5 share one specification row); the rest are v0.1/v0.2.
DAY1_FAMILIES = ("EP1", "SE4", "SE5", "IN1", "EP4", "IN4", "EP3c", "ME1")
FAMILIES = DAY1_FAMILIES + (
    "ME2", "EP2", "EP3a", "EP5", "IN2", "IN3", "SE3", "AU1", "AU3", "SO1", "FM1", "FM2",
    "FM3", "CH-R", "SE1", "SE2", "AU2", "AU4", "AU5", "SO2", "SO3", "PR1", "PR2", "PR3",
    "PR4", "ME3", "ME4", "FM4", "FM5", "CH-A")
#: Lower edges of the delay bins (days): 1-3, 4-14, 15-60, 61-180, 181+.
DELAY_BIN_EDGES = (1, 4, 15, 61, 181)

# ------------------------------------------------------------ seeds, epochs, partitions

DEV_SEEDS = range(0, 1000)
CONFIRM_SEEDS = range(5000, 5100)
#: ASSUMED placeholders for the sealed test epochs (the sealing tool registers the real
#: seed pools); half-open ranges. Only these render the test partition by default.
TEST_EPOCHS = {"E1": range(10000, 11000), "E2": range(20000, 21000)}


def seed_epoch(seed: int) -> str:
    """'dev' (0-999), 'confirm' (5000-5099), 'test' (sealed epochs E1/E2) or 'adhoc'."""
    if seed in DEV_SEEDS:
        return "dev"
    if seed in CONFIRM_SEEDS:
        return "confirm"
    if any(seed in r for r in TEST_EPOCHS.values()):
        return "test"
    return "adhoc"


def partition_of_seed(seed: int) -> str:
    """'test' for sealed test-epoch seeds, 'dev' for everything else."""
    return "test" if seed_epoch(seed) == "test" else "dev"


# ---------------------------------------------------------------------- id formats

_ID_FORMATS = {"entity": ("e", 4), "fact": ("f", 5), "situation": ("s", 5), "obs": ("o", 5),
               "query": ("q", 4)}


def new_id(kind: str, n: int) -> str:
    """Opaque id for the n-th object of a kind: e0001, f00001, s00001, o00001, q0001.

    n counts from 1 in generation order; ids sort like numbers while n has at most the
    given number of digits (4 for entities and queries, 5 for the rest)."""
    prefix, width = _ID_FORMATS[kind]
    return "%s%0*d" % (prefix, width, n)


# ------------------------------------------------------------------ time arithmetic


def to_minutes(day: int, minute: int = 0) -> int:
    return day * MINUTES_PER_DAY + minute


def day_of(t: int) -> int:
    """Day index of a minute timestamp."""
    return t // MINUTES_PER_DAY


def minute_of(t: int) -> int:
    """Minute of the day (0-1439) of a minute timestamp."""
    return t % MINUTES_PER_DAY


def date_of(start_date: str, day: int) -> str:
    """ISO date (YYYY-MM-DD) of a day index, given the ISO date of day 0."""
    return (_dt.date.fromisoformat(start_date) + _dt.timedelta(days=day)).isoformat()


def weekday_of(start_date: str, day: int) -> int:
    """Weekday of a day index: 0 = Monday ... 6 = Sunday."""
    return (_dt.date.fromisoformat(start_date) + _dt.timedelta(days=day)).weekday()


def iso_of(start_date: str, t: int) -> str:
    """ISO timestamp (YYYY-MM-DDTHH:MM) of a minute timestamp."""
    m = minute_of(t)
    return "%sT%02d:%02d" % (date_of(start_date, day_of(t)), m // 60, m % 60)


def delay_bin(days: int) -> int:
    """Index 0-4 of the delay bin of a delay in days (bins 1-3, 4-14, 15-60, 61-180, 181+)."""
    idx = 0
    for i, edge in enumerate(DELAY_BIN_EDGES):
        if days >= edge:
            idx = i
    return idx


# ------------------------------------------------- generic JSON conversion machinery


def _in(value: Any, allowed: Iterable[Any], label: str) -> None:
    if value not in allowed:
        raise ValueError("%s must be one of %s, got %r" % (label, tuple(allowed), value))


@functools.lru_cache(maxsize=None)
def _plan(cls: type) -> tuple:
    hints = typing.get_type_hints(cls)
    return tuple((f.name, hints[f.name]) for f in dataclasses.fields(cls))


def _convert(tp: Any, data: Any) -> Any:
    """Check ``data`` against the type hint ``tp`` and normalise it (lists to tuples,
    ints to floats, dicts to dataclasses). Raises TypeError/ValueError on mismatch."""
    if tp is str:
        if type(data) is not str:
            raise TypeError("expected str, got %r" % (data,))
        return data
    if tp is int:
        if type(data) is not int:
            raise TypeError("expected int, got %r" % (data,))
        return data
    if tp is float:
        if type(data) is float:
            if data != data or data == math.inf or data == -math.inf:
                raise ValueError("expected a finite float, got %r" % (data,))
            return data
        if type(data) is int:
            return float(data)
        raise TypeError("expected a number, got %r" % (data,))
    if tp is bool:
        if type(data) is not bool:
            raise TypeError("expected bool, got %r" % (data,))
        return data
    if tp is Any:
        return data
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is typing.Union or origin is types.UnionType:
        if data is None:
            if type(None) in args:
                return None
            raise TypeError("None is not allowed here")
        rest = [a for a in args if a is not type(None)]
        if len(rest) == 1:
            return _convert(rest[0], data)
        for a in rest:  # first member that accepts the value
            try:
                return _convert(a, data)
            except (TypeError, ValueError):
                continue
        raise TypeError("no union member accepts %r" % (data,))
    if origin is tuple:
        if not isinstance(data, (tuple, list)):
            raise TypeError("expected a tuple, got %r" % (data,))
        if len(args) == 2 and args[1] is Ellipsis:
            elem = args[0]
            if elem is str:
                if all(type(x) is str for x in data):
                    return data if type(data) is tuple else tuple(data)
                raise TypeError("expected a tuple of str, got %r" % (data,))
            return tuple(x if type(x) is elem else _convert(elem, x) for x in data)
        if len(args) != len(data):
            raise ValueError("expected %d items, got %d" % (len(args), len(data)))
        return tuple(_convert(a, x) for a, x in zip(args, data))
    if is_dataclass(tp):
        if isinstance(data, tp):
            return data
        if isinstance(data, dict):
            return _from_dict(tp, data)
        raise TypeError("expected a %s, got %r" % (tp.__name__, data))
    raise TypeError("unsupported type hint %r" % (tp,))


def _from_dict(cls: type, data: dict) -> Any:
    plan = _plan(cls)
    names = {name for name, _ in plan}
    unknown = set(data) - names
    if unknown:
        raise ValueError("%s: unknown keys %s" % (cls.__name__, sorted(unknown)))
    kwargs = {}
    for name, tp in plan:
        if name in data:
            try:
                kwargs[name] = _convert(tp, data[name])
            except (TypeError, ValueError) as exc:
                raise type(exc)("%s.%s: %s" % (cls.__name__, name, exc)) from None
    return cls(**kwargs)


def to_jsonable(obj: Any) -> Any:
    """Dataclasses, tuples and scalars to plain JSON types (tuples become lists)."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, (tuple, list)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError("non-finite float cannot be stored: %r" % (obj,))
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    raise TypeError("cannot serialise %r" % (type(obj),))


def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, no spaces, ASCII only, finite numbers only."""
    return json.dumps(to_jsonable(obj), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def digest_of(obj: Any) -> str:
    """SHA-256 hex digest of the canonical JSON of a dataclass, tuple, dict or scalar."""
    return hashlib.sha256(canonical_json(obj).encode("ascii")).hexdigest()


class _Schema:
    """Mixin giving every row type to_dict/to_json/from_dict/from_json/digest, plus
    normalisation on construction (see the module docstring)."""

    _Q: ClassVar[tuple] = ()      # float fields (or tuples of floats) quantised on construction
    _QND: ClassVar[int] = 6       # decimals kept by the quantiser

    def __post_init__(self) -> None:
        cls = type(self)
        for name, tp in _plan(cls):
            v = getattr(self, name)
            try:
                nv = _convert(tp, v)
            except (TypeError, ValueError) as exc:
                raise type(exc)("%s.%s: %s" % (cls.__name__, name, exc)) from None
            if name in cls._Q:
                nv = _quantise(nv, cls._QND)
            if nv is not v:
                object.__setattr__(self, name, nv)
        self._check()

    def _check(self) -> None:
        """Subclass hook: validate enumerations and ranges (raise ValueError)."""

    def to_dict(self) -> dict:
        return to_jsonable(self)

    def to_json(self, indent: int | None = None) -> str:
        if indent is None:
            return canonical_json(self)
        return json.dumps(to_jsonable(self), sort_keys=True, indent=indent, ensure_ascii=True,
                          allow_nan=False)

    @classmethod
    def from_dict(cls, data: dict):
        return _from_dict(cls, data)

    @classmethod
    def from_json(cls, text: str):
        return _from_dict(cls, json.loads(text))

    def digest(self) -> str:
        return digest_of(self)


def _quantise(v: Any, nd: int) -> Any:
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return q(v, nd)
    if isinstance(v, tuple):
        return tuple(_quantise(x, nd) for x in v)
    return v


# ------------------------------------------------------------------------ data rows


@dataclass(frozen=True)
class Slot(_Schema):
    """A named canonical string that a line must contain verbatim (or a question cue).

    ``fid`` links the slot to the fact whose object it renders ('' for context slots)."""

    name: str
    value: str
    fid: str = ""

    def _check(self) -> None:
        if not self.value:
            raise ValueError("Slot.value must not be empty")


@dataclass(frozen=True)
class Mention(_Schema):
    """A line's relation to a fact: asserts it, updates it (new version), retracts it, or
    recalls it (a retelling or a later reference)."""

    fid: str
    role: str = "assert"

    def _check(self) -> None:
        _in(self.role, MENTION_ROLES, "Mention.role")


@dataclass(frozen=True)
class Entity(_Schema):
    """A named thing in the world. ``bond`` in [0, 1] is closeness to the narrator."""

    eid: str
    kind: str
    name: str
    aliases: tuple[str, ...] = ()
    bond: float = 0.0
    _Q = ("bond",)

    def _check(self) -> None:
        _in(self.kind, ENTITY_KINDS, "Entity.kind")
        if not self.name:
            raise ValueError("Entity.name must not be empty")


@dataclass(frozen=True)
class Fact(_Schema):
    """A bitemporal fact: ``subj pred obj`` valid on days vfrom..vto (inclusive; None = open).

    Observation time lives in ``ObsSpec``/``Mention``. ``supersedes`` is the fid of the
    version this one replaces ('' = none). ``centrality`` in [0, 1]: 1 means linked to an
    active goal. ``obj`` is always a string (an entity id, a canonical value or digits)."""

    fid: str
    subj: str
    pred: str
    obj: str
    vfrom: int
    vto: int | None = None
    src: str = "lived"
    centrality: float = 0.0
    supersedes: str = ""
    surprisal_bits: float = 0.0
    _Q = ("centrality", "surprisal_bits")

    def _check(self) -> None:
        _in(self.src, SRC_KINDS, "Fact.src")
        if self.vto is not None and self.vto < self.vfrom:
            raise ValueError("Fact.vto < vfrom")

    def valid_on(self, day: int) -> bool:
        return self.vfrom <= day and (self.vto is None or day <= self.vto)


@dataclass(frozen=True)
class Feats(_Schema):
    """Appraisal inputs of a situation, all exact from generator state.

    goal_rel g in [0, 1]; conduciveness c in [-1, 1]; surprisal_bits (bits under the
    generator's own routine model; surprise n = clip(bits / TierCfg.surprise_bits_scale,
    0, 1)); stakes k in [0, 1]; bond b in [0, 1] of the main other actor; control p
    (coping potential) in [0, 1]; norm in [-1, 1] (|norm| is the violation v, the sign
    is v_signed of the valence formula)."""

    goal_rel: float = 0.0
    surprisal_bits: float = 0.0
    stakes: float = 0.0
    bond: float = 0.0
    control: float = 0.5
    norm: float = 0.0
    conduciveness: float = 0.0
    _Q = ("goal_rel", "surprisal_bits", "stakes", "bond", "control", "norm", "conduciveness")

    def surprise(self, scale: float = 8.0) -> float:
        """n = clip(surprisal_bits / scale, 0, 1)."""
        return min(1.0, max(0.0, self.surprisal_bits / scale))


@dataclass(frozen=True)
class Situation(_Schema):
    """Something that happened to or was seen by the narrator, with its appraisal.

    A (arousal) and V (valence) are generator variables, not claims about experience.
    ``facts`` are the fids this situation hosts (situation-first hosting). ``mood`` is
    M_t at the situation. ``turning``/``topic`` mark a stance turning point (v0.1)."""

    sid: str
    day: int
    minute: int
    scene: str
    actors: tuple[str, ...] = ()
    place: str = ""
    feats: Feats = field(default_factory=Feats)
    A: float = 0.0
    V: float = 0.0
    facts: tuple[str, ...] = ()
    turning: bool = False
    topic: str = ""
    mood: float = 0.0
    _Q = ("A", "V", "mood")

    def _check(self) -> None:
        _in(self.scene, SCENE_NAMES, "Situation.scene")
        if not 0 <= self.minute < MINUTES_PER_DAY:
            raise ValueError("Situation.minute out of range")

    @property
    def t(self) -> int:
        """Minute timestamp of the situation."""
        return self.day * MINUTES_PER_DAY + self.minute


@dataclass(frozen=True)
class ObsSpec(_Schema):
    """What one observation (a line the systems will read) must say: structure, not text.

    ``mentions`` say which facts the line asserts/updates/retracts/recalls; ``slots`` are
    the canonical strings that must appear verbatim; ``source`` is an optional entity id
    of the teller or author ('' = narrator; shown to systems only in the provenance arm);
    ``frame`` is an optional frame selector for the verbaliser ('' = it chooses from its
    own stream); ``target_len`` is the target word count, drawn at world build from one
    distribution independent of kind, arousal and evidence status."""

    oid: str
    t_obs: int
    channel: str
    sid: str
    mentions: tuple[Mention, ...] = ()
    slots: tuple[Slot, ...] = ()
    source: str = ""
    frame: str = ""
    target_len: int = 45

    def _check(self) -> None:
        _in(self.channel, CHANNELS, "ObsSpec.channel")
        if self.target_len < 1:
            raise ValueError("ObsSpec.target_len must be positive")

    @property
    def day(self) -> int:
        return self.t_obs // MINUTES_PER_DAY


@dataclass(frozen=True)
class Obs(_Schema):
    """One rendered observation: all a system ever sees of the stream (plus channel H)."""

    oid: str
    t_obs: int
    channel: str
    text: str

    def _check(self) -> None:
        _in(self.channel, CHANNELS, "Obs.channel")


@dataclass(frozen=True)
class Prior(_Schema):
    """The generator's own distribution over the values of a slot (a routine model).

    Used for surprisal, for the blind-prior baselines and for chance = sum of squared
    shares. Probabilities are quantised to 9 decimals."""

    slot: str
    values: tuple[str, ...]
    probs: tuple[float, ...]
    _Q = ("probs",)
    _QND = 9

    def _check(self) -> None:
        if len(self.values) != len(self.probs) or not self.values:
            raise ValueError("Prior needs equally many values and probabilities, at least one")
        if any(p < 0 for p in self.probs):
            raise ValueError("Prior probabilities must be non-negative")

    def p_of(self, value: str) -> float:
        for v, p in zip(self.values, self.probs):
            if v == value:
                return p
        return 0.0

    def chance(self) -> float:
        """Accuracy of always guessing by the prior: the sum of squared shares."""
        return sum(p * p for p in self.probs)

    def mode(self) -> str:
        best = 0
        for i, p in enumerate(self.probs):
            if p > self.probs[best]:
                best = i
        return self.values[best]

    def top(self, k: int) -> tuple[str, ...]:
        order = sorted(range(len(self.values)), key=lambda i: (-self.probs[i], i))
        return tuple(self.values[i] for i in order[:k])

    def entropy_bits(self) -> float:
        return _entropy_bits(self.probs)


@dataclass(frozen=True)
class Card(_Schema):
    """What a system is told about the narrator at reset (record 0): name and role only."""

    name: str
    role: str = "diarist"


@dataclass(frozen=True)
class Channel(_Schema):
    """Channel H arrays for one (arm, reliability, nu, seed): one value per observation.

    ``h[i]`` belongs to ``oids[i]`` (None = no reading, e.g. dropout or arm ABSENT).
    ``realised_corr`` is corr(H, A) measured on this world; ``sigma`` the solved noise
    scale; ``x`` the nuisance activity series (diagnostics). Not part of World.digest()."""

    arm: str
    reliability: float
    nu: float
    seed: int
    oids: tuple[str, ...] = ()
    h: tuple[float | None, ...] = ()
    sigma: float = 0.0
    realised_corr: float = 0.0
    x: tuple[float, ...] = ()
    meta: tuple[tuple[str, float], ...] = ()
    _Q = ("h", "sigma", "realised_corr", "x")

    def _check(self) -> None:
        _in(self.arm, CHANNEL_ARMS, "Channel.arm")
        if len(self.oids) != len(self.h):
            raise ValueError("Channel needs one h per oid")

    def value(self, oid: str) -> float | None:
        return self._lookup.get(oid)

    @cached_property
    def _lookup(self) -> dict:
        return dict(zip(self.oids, self.h))


# ------------------------------------------------------------- questions and scoring


@dataclass(frozen=True)
class NearMiss(_Schema):
    """A plausible wrong answer and why it is plausible (stale, adjacent_day, confuser, habit)."""

    kind: str
    value: str

    def _check(self) -> None:
        _in(self.kind, NEAR_MISS_KINDS, "NearMiss.kind")


@dataclass(frozen=True)
class Gold(_Schema):
    """The exact answer of a query. ``value`` is canonical (a pool value, an entity name,
    'HH:MM', digits, a letter or 'UNKNOWN'); ``vocab_id`` names the closed vocabulary
    ('pool:<id>' or 'kind:<entity kind>', see vocab.closed_vocab)."""

    kind: str
    value: str
    aliases: tuple[str, ...] = ()
    vocab_id: str = ""
    near_miss: tuple[NearMiss, ...] = ()

    def _check(self) -> None:
        _in(self.kind, GOLD_KINDS, "Gold.kind")

    def accepted(self) -> tuple[str, ...]:
        """Canonical value followed by its aliases."""
        return (self.value,) + tuple(a for a in self.aliases if a != self.value)


@dataclass(frozen=True)
class Tags(_Schema):
    """Stratification tags of a query (see the specification's Query tags)."""

    delay_days: int = 0
    anchor_kind: str = "none"
    n_confusers: int = 0
    n_evidence: int = 1
    target_arousal: float = 0.0
    arousal_decile: int = -1
    centrality: float = 0.0
    surprisal_bits: float = 0.0
    update_count: int = 0
    relative_time: bool = False
    need_label: str = ""
    partition: str = "dev"
    prior_answerable: bool = False
    role: str = ""
    pair_id: str = ""
    hard: bool = False
    extra: tuple[tuple[str, str], ...] = ()
    _Q = ("target_arousal", "centrality", "surprisal_bits")

    def _check(self) -> None:
        _in(self.anchor_kind, ANCHOR_KINDS, "Tags.anchor_kind")
        _in(self.partition, PARTITIONS, "Tags.partition")
        _in(self.role, ROLES, "Tags.role")
        if not -1 <= self.arousal_decile <= 9:
            raise ValueError("Tags.arousal_decile must be -1 (unknown) or 0-9")

    def get(self, name: str, default: str | None = None) -> str | None:
        for k, v in self.extra:
            if k == name:
                return v
        return default


@dataclass(frozen=True)
class Query(_Schema):
    """A question with exact gold. ``text`` is rendered by ``verbalise.render_question``
    from the structure below (pass '' when building): ``family``, ``cue`` (slots whose
    canonical strings the question must contain), ``ask`` (the asked predicate/slot id),
    ``options`` (forced-choice options, ``fmt == 'choice'``) and ``conf`` (append the
    'CONF: 0-100' request). Never given to systems."""

    qid: str
    family: str
    t_ask: int
    text: str
    fmt: str
    gold: Gold
    evidence_oids: tuple[str, ...] = ()
    evidence_fids: tuple[str, ...] = ()
    tags: Tags = field(default_factory=Tags)
    cue: tuple[Slot, ...] = ()
    ask: str = ""
    options: tuple[str, ...] = ()
    conf: bool = True
    twin_of: str = ""

    def _check(self) -> None:
        _in(self.family, FAMILIES, "Query.family")
        _in(self.fmt, FORMATS, "Query.fmt")
        if self.fmt == "choice" and len(self.options) < 2:
            raise ValueError("a forced-choice Query needs at least two options")


@dataclass(frozen=True)
class Cell(_Schema):
    """A coupling cell: realised enrichment target E_0.10, rehearsal level, mundane-decisive
    mass mu on deciles 0-1, and the delayed-relevance lag in days (0 = none).

    ``rehearsal`` is 0 for off; the X1 cells use 0.3 or 0. The cell parameterises
    ``queries.build_queries`` only; it is not part of a world's structure or digest."""

    name: str
    e_target: float
    rehearsal: float
    mu: float
    lag_days: int = 0

    def _check(self) -> None:
        if self.e_target <= 0 or not 0 <= self.mu <= 1 or not 0 <= self.rehearsal <= 1:
            raise ValueError("Cell needs e_target > 0 and mu, rehearsal in [0, 1]")


#: The five X1 cells (coupling E_0.10 / rehearsal / mu). C+ strong positive, C-half dose,
#: C0 null, C0r null with rehearsal off, C- adverse and quiet-critical.
CELLS = {
    "C+": Cell("C+", 4.0, 0.3, 0.2),
    "C-half": Cell("C-half", 2.0, 0.3, 0.2),
    "C0": Cell("C0", 1.0, 0.3, 0.0),
    "C0r": Cell("C0r", 1.0, 0.0, 0.0),
    "C-": Cell("C-", 0.3, 0.0, 0.6),
}
E_GRID = (0.2, 0.5, 1.0, 2.0, 4.0)
MU_GRID = (0.0, 0.1, 0.3, 0.6)
LAG_GRID = (7, 30, 120)


def grid_cell(e_target: float, mu: float, rehearsal: float = 0.0, lag_days: int = 0) -> Cell:
    """A cell of the X0 gate grid (E_0.10 x mu), named 'E<e>_mu<mu>'."""
    return Cell("E%g_mu%g" % (e_target, mu), e_target, rehearsal, mu, lag_days)


@dataclass(frozen=True)
class ScoreRecord(_Schema):
    """Outcome of scoring one answer. ``score`` is 1.0 or 0.0 for exact-match families;
    ``cost_weighted`` is +1 correct, 0 abstain, -1 wrong (ME1 reporting). ``candidates``
    are the closed-vocabulary matches found in the answer; ``hedged`` means two or more;
    ``unmatched`` means none (logged); ``conf`` is the parsed 0-100 confidence."""

    qid: str
    family: str
    correct: bool
    score: float
    error_type: str = ""
    candidates: tuple[str, ...] = ()
    abstained: bool = False
    hedged: bool = False
    unmatched: bool = False
    parse_ok: bool = True
    conf: int | None = None
    cost_weighted: float = 0.0
    abs_error: float | None = None
    within_one: bool | None = None

    def _check(self) -> None:
        _in(self.error_type, ERROR_TYPES, "ScoreRecord.error_type")
        if self.conf is not None and not 0 <= self.conf <= 100:
            raise ValueError("ScoreRecord.conf must be 0-100")


# ------------------------------------------------------- system protocol (data only)


@dataclass(frozen=True)
class Record(_Schema):
    """What a system ingests per observation (id = oid, timestamp in minutes). ``source``
    is filled only in the provenance arm; ``heartbeat`` only for systems that accept it."""

    id: str
    text: str
    timestamp: int
    channel: str
    source: str = ""
    heartbeat: float | None = None
    _Q = ("heartbeat",)


@dataclass(frozen=True)
class ContextItem(_Schema):
    """One item of the context a system delivered with an answer."""

    text: str
    timestamp: int
    oid: str


@dataclass(frozen=True)
class LifeAnswer(_Schema):
    """An answer plus the context that produced it. ``cost`` and ``metadata`` are tuples of
    pairs (model_calls, input_tokens, ... / free notes); ``confidence`` is the parsed
    0-100 value if the reader gave one. Behaviour lives in ``lifesim.interface``."""

    text: str
    evidence_ids: tuple[str, ...] = ()
    context: tuple[ContextItem, ...] = ()
    context_tokens: int = 0
    abstained: bool = False
    confidence: int | None = None
    cost: tuple[tuple[str, float], ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()


# -------------------------------------------------------------- configuration: TierCfg


def _date_check(text: str) -> None:
    try:
        _dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("TierCfg.start_date must be an ISO date: %r" % (text,)) from exc


def _a(default: Any, doc: str) -> Any:
    """A numeric generator parameter that is an ASSUMPTION (swept +-50%)."""
    return field(default=default, metadata={"doc": "ASSUMED: " + doc, "assumed": True})


def _s(default: Any, doc: str) -> Any:
    """A structural setting (a mode, a name, a date): not an assumption."""
    return field(default=default, metadata={"doc": "STRUCTURAL: " + doc, "assumed": False})


@dataclass(frozen=True)
class TierCfg(_Schema):
    """Every generator parameter that is an assumption, with presets for tiers L0-L3.

    The dataclass defaults are the L1 values; ``TierCfg.for_tier('L0'..'L3')`` and the
    module constant ``TIERS`` give the presets. Each field's metadata carries a ``doc``
    that starts with ASSUMED (a number someone chose, to be swept +-50%) or STRUCTURAL
    (a mode, name or date). Tier sizes are estimates from toy densities, re-measured in
    X0 and frozen by digest after calibration. A conclusion that flips under a +-50%
    sweep is labelled parameter-dependent. Need one more parameter without editing this
    file? Put it in ``extra`` (``with_extra``/``get``) and document it as ASSUMED in
    your module docstring; the integration step promotes it to a field."""

    # ---- identity (structural)
    tier: str = _s("L1", "tier name L0 smoke | L1 short life | L2 year | L3 top")
    start_date: str = _s("2027-01-01", "ISO date of day 0")
    name_partition: str = _s("auto", "'dev' | 'test' | 'auto' (auto = partition_of_seed(seed))")
    affect: str = _s("A0", "text affect: A0 none | A1 independent of arousal | A2 correlated")
    rehearsal: str = _s("off", "retelling of high-arousal situations: off | natural | strong")
    h_repr: str = _s("scalar", "channel H representation: scalar | bpm | z | 3level")

    # ---- size and stream
    days: int = _a(180, "length of the life in days (L0 30, L1 180, L2 365, L3 1000)")
    obs_per_day: float = _a(6.1, "mean observations per day (Poisson); about 180 / 1,100 / 2,200 / 6,000 per life")
    obs_min: int = _a(3, "fewest observations on a day (dial range 3-12)")
    obs_max: int = _a(10, "most observations on a day")
    words_min: int = _a(30, "shortest observation target length in words")
    words_max: int = _a(60, "longest observation target length in words")
    queries_per_world: int = _a(160, "queries per world (L0 80, L1 160, L2 220, L3 260)")
    context_words: int = _a(600, "context budget C in words (L0 400, L1 600, L2 800, L3 1000)")
    retention_ratios: tuple[float, ...] = _a((1.0, 0.25), "storage ratios R evaluated at this tier")
    target_lo: float = _a(0.65, "lower end of the target macro accuracy of the best non-oracle arm")
    target_hi: float = _a(0.85, "upper end of that target (L3 aims at 0.35-0.45, rule <= 0.50)")
    hard_share: float = _a(0.15, "share of hard-type queries (aggregate, many updates, no anchor, trap, peripheral at long delay; L3 >= 0.6)")
    min_pool: int = _a(24, "smallest allowed answer pool (blind chance <= 1/24)")
    family_mix: tuple[tuple[str, float], ...] = _a(
        (("EP1", 0.22), ("SE4", 0.12), ("SE5", 0.12), ("IN1", 0.16), ("EP4", 0.16),
         ("IN4", 0.10), ("EP3c", 0.12)),
        "share of the answerable queries per Day-1 family (sums to 1); ME1 gets abstain_share of all queries on top")
    query_overgenerate: float = _a(1.5, "queries generated per kept query before the memory-dependence filters")
    delay_min_days: int = _a(1, "smallest query delay in days")
    delay_max_days: int = _a(175, "largest query delay in days: days - 5 (L0 25, L1 175, L2 360, L3 995)")

    # ---- cast (entity counts; every entity pool must reach min_pool)
    n_persons: int = _a(40, "named people (L0 24, L1 40, L2 60, L3 100)")
    n_cities: int = _a(30, "invented cities and towns")
    n_streets: int = _a(30, "invented streets")
    n_shops: int = _a(30, "invented shops")
    n_orgs: int = _a(12, "invented employers and organisations")
    n_foods_min: int = _a(40, "smallest breakfast habit pool per world")
    n_foods_max: int = _a(60, "largest breakfast habit pool per world")
    habit_zipf_s: float = _a(0.6, "Zipf exponent of the breakfast habit prior (0.5-0.7; entropy >= 4.5 bits)")

    # ---- event rates, per 30 days
    routine_rate: float = _a(8.0, "breakfast statements per 30 days (EP1 competing episodes)")
    scene_rates: tuple[tuple[str, float], ...] = _a(
        (("minor", 20.0), ("major", 1.5), ("move", 0.2), ("health", 0.8), ("purchase", 3.0),
         ("remark", 4.0), ("trip", 0.5), ("article", 12.0)),
        "expected situations of each non-routine scene per 30 days")

    # ---- appraisal mappings (M1 additive, M2 noisy-OR, M3 prediction error)
    m1_w: tuple[float, ...] = _a((0.30, 0.25, 0.25, 0.15, 0.05), "M1 weights of g, n, k, b*g, (1-p)[c<0]")
    m1_eps_sd: float = _a(0.05, "M1 noise SD")
    m1_cap_base: float = _a(0.35, "M1 cap intercept: A <= base + slope * g")
    m1_cap_slope: float = _a(0.65, "M1 cap slope on goal relevance")
    m2_w: tuple[float, ...] = _a((0.50, 0.60, 0.50, 0.40, 0.60), "M2 noisy-OR weights of n, g, (1-p)g, v, k*g")
    m3_noise_sd: float = _a(0.05, "M3 prediction-error noise SD")
    v_gain_c: float = _a(1.5, "valence gain on conduciveness: V = tanh(gain_c*c + gain_norm*v_signed)")
    v_gain_norm: float = _a(0.3, "valence gain on signed norm violation")
    surprise_bits_scale: float = _a(8.0, "bits that map to surprise n = 1")
    mappings: tuple[str, ...] = _s(("M1", "M2"), "mappings drawn per world (M3 only in the held-out test cell)")
    mood_decay: float = _a(0.9, "mood memory: M_t = decay*M_{t-1} + gain*mean_day(V*A)")
    mood_gain: float = _a(0.1, "mood update gain")
    mood_quiet_decay: float = _a(0.97, "mood decay per quiet day")
    mood_probe_threshold: float = _a(0.15, "take stance probes when |M| is below this")
    a_target_mean: float = _a(0.22, "target mean arousal (right-skewed)")
    a_target_sd: float = _a(0.12, "target SD of arousal")
    a_frac_below_03: float = _a(0.77, "target share of situations with A < 0.3")
    a_high_threshold: float = _a(0.7, "A at or above this counts as high arousal")
    a_high_per_month: tuple[float, float] = _a((3.0, 6.0), "expected high-arousal lines per month (range)")
    max_corr_nk: float = _a(0.3, "largest allowed corr(surprise n, stakes k)")

    # ---- channel H
    nu: float = _a(0.3, "nuisance share of the channel before noise")
    x_burst_rate: float = _a(0.5, "nuisance activity bursts per day")
    reliability_grid: tuple[float, ...] = _a((0.0, 0.3, 0.5, 0.7, 0.9, 1.0), "reliability r_H = corr(H, A) ladder")
    reliability_primary: float = _a(0.7, "primary reliability")
    retell_a_factor: float = _a(0.5, "arousal of a retelling line as a fraction of the situation's")
    dropout: float = _a(0.1, "share of readings dropped in the fault arm")
    sign_reversal: float = _a(0.15, "share of sign-reversed readings in the fault arm")

    # ---- rehearsal and mentions
    rehearsal_p_natural: float = _a(0.8, "retelling probability within a day for A above the minimum (natural)")
    rehearsal_p_strong: float = _a(1.0, "retelling probability (strong)")
    rehearsal_repeats_strong: int = _a(3, "number of retellings (strong)")
    rehearsal_a_min: float = _a(0.7, "smallest arousal that is retold")
    p_immediate_diary: float = _a(0.7, "probability of a diary line on the day of a situation")

    # ---- text
    r_aff: float = _a(0.0, "correlation between arousal and affect phrases under A2 (0-0.8)")
    dramatic_decoy_share: float = _a(0.0, "share of low-A lines worded dramatically (0 or 0.1)")
    narrator_narrowing: float = _a(0.0, "share of peripheral detail the narrator omits (0, 0.5, 1)")
    typo_rate: float = _a(0.0, "typo rate in the renderer-OOD cell (0-0.03)")
    flash_share: float = _a(0.0, "share of lines paraphrased in the renderer-OOD cell (0-0.3)")
    v_mix: tuple[float, float, float] = _a((0.7, 0.3, 0.0), "shares of V1 diary, V2 chat, V3 log renderers")

    # ---- difficulty dials
    anchor_mix: float = _a(0.2, "share of cues with no rare-name or absolute-date anchor (0-0.8)")
    relative_time_share: float = _a(0.2, "share of cues with a relative date (0-0.8)")
    name_rarity: float = _a(0.4, "rarity of names in cues (0-1)")
    n_confusers_max: int = _a(4, "most same-type confusing facts per item (L0 2, L1 4, L2 8, L3 12)")
    shared_slots: int = _a(1, "slots a confuser shares with the target (1-3)")
    same_frame_share: float = _a(0.5, "share of confusers in the same frame as the target (>= 0.5)")
    update_rate: float = _a(2.0, "updates per attribute-year (0-6)")
    incidental_update_share: float = _a(0.2, "share of updates only implied later (0-0.8)")
    chain_depth_max: int = _a(2, "longest version chain (0-5)")
    disorder: float = _a(0.05, "share of updates narrated out of order (0-0.3)")
    peripheral_share: float = _a(0.3, "share of facts hosted at peripheral positions (0-0.8)")
    periphery_goal_relevant: int = _a(0, "1 if peripheral facts are goal relevant, else 0")
    pi_peripheral_need: float = _a(0.3, "share of needed emotional details that are peripheral (0.1-0.5)")
    abstain_share: float = _a(0.08, "share of ME1 items (0.05-0.15 by tier)")

    # ---- Day-1 family parameters
    ep1_competing: tuple[int, int] = _a((1, 60), "EP1: number of competing breakfast episodes (range)")
    in1_confusers: tuple[int, int] = _a((6, 12), "IN1: confusing articles per attribute type (range)")
    in1_decoy_share: float = _a(0.5, "IN1: share of items with a decoy colour in the same article")
    in1_min_other_articles: int = _a(6, "IN1: other articles carrying a vehicle colour")
    ep3c_count_range: tuple[int, int] = _a((1, 8), "EP3c: gold counts, stratified")
    ep3c_evidence: tuple[int, int] = _a((2, 10), "EP3c: evidence lines (range)")
    in4_low_deciles: int = _a(2, "IN4: the remark sits in the lowest this-many arousal deciles")
    se_stale_mentions: int = _a(6, "SE4/SE5: times the old value is mentioned before the update")

    # ---- character layer (v0.1+; all constants ASSUMED, swept +-50%)
    n_topics: int = _a(12, "stance topics")
    tp_per_year: float = _a(2.0, "turning points per year (0-3)")
    tp_min_centrality: float = _a(0.6, "centrality needed for a turning point")
    tp_min_goal: float = _a(0.6, "goal relevance needed for a turning point")
    tp_refractory_days: int = _a(30, "refractory window after a turning point")
    eta_ordinary: float = _a(0.25, "ordinary-event gain: eta = this * A^2 * |V|")
    eta_turning: float = _a(0.9, "turning-point gain: eta = this * |V|")
    locality: tuple[float, float, float] = _a((1.0, 0.4, 0.05), "stance locality: direct, same value, distant")
    experiencer_weights: tuple[float, float, float] = _a((1.0, 0.25, 0.1), "own, witnessed, hearsay")
    habituation: float = _a(0.5, "weight of a similar event inside the habituation window")
    habituation_days: int = _a(3, "habituation window in days")
    caps: tuple[float, float, float, float] = _a((0.10, 0.20, 0.30, 0.40), "stance caps: per event, per 30 days, per turning point, per year")
    persistent_share: tuple[float, float] = _a((0.6, 0.2), "persistent share of a shift: turning point, ordinary")
    half_lives: tuple[float, float] = _a((365.0, 60.0), "half-lives in days: persistent, transient")

    # ---- escape hatch for parameters not yet promoted to fields
    extra: tuple[tuple[str, float], ...] = _a((), "name/value pairs for parameters not yet promoted to fields")

    def _check(self) -> None:
        _in(self.name_partition, PARTITIONS + ("auto",), "TierCfg.name_partition")
        _in(self.affect, AFFECT_MODES, "TierCfg.affect")
        _in(self.rehearsal, REHEARSAL_LEVELS, "TierCfg.rehearsal")
        _date_check(self.start_date)
        if self.words_min > self.words_max or self.obs_min > self.obs_max:
            raise ValueError("TierCfg: min above max")
        if self.days < 1:
            raise ValueError("TierCfg.days must be positive")
        for m in self.mappings:
            _in(m, MAPPINGS, "TierCfg.mappings")
        for fam, share in self.family_mix:
            _in(fam, tuple(f for f in DAY1_FAMILIES if f != "ME1"), "TierCfg.family_mix")
            if share < 0:
                raise ValueError("TierCfg.family_mix shares must be non-negative")
        if abs(sum(share for _, share in self.family_mix) - 1.0) > 1e-9:
            raise ValueError("TierCfg.family_mix must sum to 1")

    # -- helpers
    def get(self, name: str, default: Any = None) -> Any:
        """Value of a field, else of an ``extra`` entry, else ``default``."""
        if name in {f.name for f in fields(self)}:
            return getattr(self, name)
        for k, v in self.extra:
            if k == name:
                return v
        return default

    def with_extra(self, **params: float) -> "TierCfg":
        merged = dict(self.extra)
        merged.update(params)
        return dataclasses.replace(self, extra=tuple(sorted(merged.items())))

    def scene_rate(self, scene: str) -> float:
        return dict(self.scene_rates).get(scene, 0.0)

    def expected_obs(self) -> float:
        return self.days * self.obs_per_day

    def expected_words(self) -> float:
        return self.expected_obs() * (self.words_min + self.words_max) / 2.0

    def resolved_partition(self, seed: int) -> str:
        return partition_of_seed(seed) if self.name_partition == "auto" else self.name_partition

    @classmethod
    def assumed_float_names(cls) -> tuple[str, ...]:
        """Names of ASSUMED plain-float fields: the ones a +-50% sweep scales."""
        hints = typing.get_type_hints(cls)
        return tuple(f.name for f in fields(cls)
                     if f.metadata.get("assumed") and hints[f.name] is float)

    @classmethod
    def describe(cls) -> tuple[dict, ...]:
        """One record per field (name, type, L1 default, doc, assumed): the source of the
        parameter table in data/lab/aam-lifesim/config.json."""
        base = cls()
        return tuple({"name": f.name, "type": str(f.type), "default": to_jsonable(getattr(base, f.name)),
                      "doc": f.metadata["doc"], "assumed": f.metadata["assumed"]}
                     for f in fields(cls))

    @classmethod
    def for_tier(cls, tier: str) -> "TierCfg":
        """The preset of tier L0, L1, L2 or L3."""
        return cls(**_TIER_PRESETS[tier])


_TIER_PRESETS: dict[str, dict] = {
    "L0": dict(tier="L0", days=30, obs_per_day=6.0, queries_per_world=80, context_words=400,
               retention_ratios=(1.0,), target_lo=0.80, target_hi=1.0, hard_share=0.0,
               delay_max_days=25, n_persons=24, n_cities=24, n_streets=24, n_shops=24,
               n_orgs=12, n_confusers_max=2, update_rate=1.0, incidental_update_share=0.0,
               chain_depth_max=1, disorder=0.0, peripheral_share=0.2, anchor_mix=0.0,
               relative_time_share=0.0, name_rarity=0.2, abstain_share=0.05),
    "L1": dict(tier="L1", days=180, obs_per_day=6.1, queries_per_world=160, context_words=600,
               retention_ratios=(1.0, 0.25), target_lo=0.65, target_hi=0.85, hard_share=0.15,
               delay_max_days=175, n_persons=40, n_cities=30, n_streets=30, n_shops=30,
               n_orgs=12, n_confusers_max=4, update_rate=2.0, incidental_update_share=0.2,
               chain_depth_max=2, disorder=0.05, peripheral_share=0.3, anchor_mix=0.2,
               relative_time_share=0.2, name_rarity=0.4, abstain_share=0.08),
    "L2": dict(tier="L2", days=365, obs_per_day=6.0, queries_per_world=220, context_words=800,
               retention_ratios=(1.0, 0.25, 0.10), target_lo=0.45, target_hi=0.65,
               hard_share=0.35, delay_max_days=360, n_persons=60, n_cities=40, n_streets=40,
               n_shops=40, n_orgs=16, n_confusers_max=8, update_rate=3.0,
               incidental_update_share=0.4, chain_depth_max=3, disorder=0.15,
               peripheral_share=0.4, anchor_mix=0.4, relative_time_share=0.4, name_rarity=0.6,
               abstain_share=0.10),
    "L3": dict(tier="L3", days=1000, obs_per_day=6.0, queries_per_world=260, context_words=1000,
               retention_ratios=(1.0, 0.10), target_lo=0.0, target_hi=0.50, hard_share=0.60,
               delay_max_days=995, n_persons=100, n_cities=60, n_streets=60, n_shops=60,
               n_orgs=24, n_confusers_max=12, update_rate=4.0, incidental_update_share=0.6,
               chain_depth_max=5, disorder=0.30, peripheral_share=0.5, anchor_mix=0.6,
               relative_time_share=0.6, name_rarity=0.8, abstain_share=0.15),
}

TIERS = {name: TierCfg.for_tier(name) for name in ("L0", "L1", "L2", "L3")}


# ------------------------------------------------------------------------------ World


@dataclass(frozen=True)
class World(_Schema):
    """One synthetic life: structure only (no text, no queries).

    Rows are unique by id and ``obs_specs`` are sorted by ``t_obs`` (the stream order);
    ``verbalise.render`` returns one ``Obs`` per spec in the same order.
    ``mapping`` is the appraisal mapping drawn for this world (M1/M2/M3), ``partition``
    the name partition used. ``priors`` are the generator's routine models (blind
    baselines and chance come from them). ``ablated`` lists the situation ids removed by
    ``delete_events``. ``extras`` is a module-private store of JSON text per key (goals,
    schedules, ...) for structure that does not deserve a type. ``channel`` is the slot
    for the channel arrays attached with ``with_channel``; it is not part of the digest.

    ``digest()`` hashes the structure: schema version, seed, partition, mapping, card,
    entities, facts, situations, obs_specs, priors, ablated and extras; never ``cfg``,
    ``channel`` or anything rendered."""

    seed: int
    cfg: TierCfg
    entities: tuple[Entity, ...] = ()
    facts: tuple[Fact, ...] = ()
    situations: tuple[Situation, ...] = ()
    obs_specs: tuple[ObsSpec, ...] = ()
    card: Card = field(default_factory=lambda: Card(name=""))
    priors: tuple[Prior, ...] = ()
    mapping: str = "M1"
    partition: str = "dev"
    ablated: tuple[str, ...] = ()
    extras: tuple[tuple[str, str], ...] = ()
    channel: Channel | None = None

    def _check(self) -> None:
        _in(self.mapping, MAPPINGS, "World.mapping")
        _in(self.partition, PARTITIONS, "World.partition")
        for label, rows, key in (("entities", self.entities, "eid"), ("facts", self.facts, "fid"),
                                 ("situations", self.situations, "sid"),
                                 ("obs_specs", self.obs_specs, "oid")):
            ids = [getattr(r, key) for r in rows]
            if len(set(ids)) != len(ids):
                raise ValueError("World.%s has duplicate ids" % label)
        times = [o.t_obs for o in self.obs_specs]
        if any(b < a for a, b in zip(times, times[1:])):
            raise ValueError("World.obs_specs must be sorted by t_obs")

    # -- structure and digest
    def structure(self) -> dict:
        """The jsonable structure that ``digest()`` hashes."""
        return {
            "schema": SCHEMA_VERSION, "generator": GENERATOR_ID, "seed": self.seed,
            "partition": self.partition, "mapping": self.mapping,
            "card": to_jsonable(self.card), "entities": to_jsonable(self.entities),
            "facts": to_jsonable(self.facts), "situations": to_jsonable(self.situations),
            "obs_specs": to_jsonable(self.obs_specs), "priors": to_jsonable(self.priors),
            "ablated": list(self.ablated), "extras": to_jsonable(self.extras),
        }

    @cached_property
    def _digest(self) -> str:
        return digest_of(self.structure())

    def digest(self) -> str:
        return self._digest

    # -- lookups (built once per world)
    @cached_property
    def _ix(self) -> dict:
        host: dict = {}
        for s in self.situations:
            for fid in s.facts:
                host[fid] = s.sid
        mentions: dict = {}
        for o in self.obs_specs:
            for m in o.mentions:
                mentions.setdefault(m.fid, []).append((o.oid, m.role))
        return {
            "entity": {e.eid: e for e in self.entities},
            "fact": {f.fid: f for f in self.facts},
            "situation": {s.sid: s for s in self.situations},
            "obs": {o.oid: o for o in self.obs_specs},
            "host": host,
            "mentions": {k: tuple(v) for k, v in mentions.items()},
        }

    def entity(self, eid: str) -> Entity:
        return self._ix["entity"][eid]

    def fact(self, fid: str) -> Fact:
        return self._ix["fact"][fid]

    def situation(self, sid: str) -> Situation:
        return self._ix["situation"][sid]

    def obs_spec(self, oid: str) -> ObsSpec:
        return self._ix["obs"][oid]

    def host(self, fid: str) -> Situation:
        """The situation that hosts a fact."""
        return self._ix["situation"][self._ix["host"][fid]]

    def mentions_of(self, fid: str) -> tuple[tuple[str, str], ...]:
        """(oid, role) of every observation that mentions the fact."""
        return self._ix["mentions"].get(fid, ())

    def entities_of(self, kind: str) -> tuple[Entity, ...]:
        return tuple(e for e in self.entities if e.kind == kind)

    def prior(self, slot: str) -> Prior | None:
        for p in self.priors:
            if p.slot == slot:
                return p
        return None

    # -- conveniences
    @property
    def n_days(self) -> int:
        return self.cfg.days

    def date_of(self, day: int) -> str:
        return date_of(self.cfg.start_date, day)

    def with_channel(self, channel: Channel | None) -> "World":
        return dataclasses.replace(self, channel=channel)

    def extra(self, key: str, default: Any = None) -> Any:
        """Decoded value of an ``extras`` entry."""
        for k, v in self.extras:
            if k == key:
                return json.loads(v)
        return default

    def with_extra(self, key: str, value: Any) -> "World":
        merged = dict(self.extras)
        merged[key] = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                                 allow_nan=False)
        return dataclasses.replace(self, extras=tuple(sorted(merged.items())))


# ------------------------------------------------------------------- JSONL and files


def dumps_jsonl(items: Iterable[Any]) -> str:
    """One canonical JSON document per line, LF line ends, empty string for no items."""
    lines = [canonical_json(x) for x in items]
    return "\n".join(lines) + "\n" if lines else ""


def write_text_lf(path: str | Path, text: str) -> None:
    """Write UTF-8 text with LF line ends on every platform (bytes in, bytes out)."""
    Path(path).write_bytes(text.encode("utf-8"))


def write_jsonl(path: str | Path, items: Iterable[Any]) -> None:
    write_text_lf(path, dumps_jsonl(items))


def read_jsonl(path: str | Path, cls: type) -> list:
    """Read a JSONL file written by ``write_jsonl`` back into ``cls`` objects."""
    text = Path(path).read_bytes().decode("utf-8")
    return [cls.from_dict(json.loads(line)) for line in text.split("\n") if line]


def save_world(world: World, directory: str | Path) -> Path:
    """Write world.json (entities, facts, cfg, priors, card, digest), situations.jsonl,
    obs_specs.jsonl and, if present, channel.json. Byte-identical for equal worlds."""
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    head = {
        "schema": SCHEMA_VERSION, "generator": GENERATOR_ID, "seed": world.seed,
        "partition": world.partition, "mapping": world.mapping, "digest": world.digest(),
        "card": to_jsonable(world.card), "cfg": to_jsonable(world.cfg),
        "entities": to_jsonable(world.entities), "facts": to_jsonable(world.facts),
        "priors": to_jsonable(world.priors), "ablated": list(world.ablated),
        "extras": to_jsonable(world.extras),
    }
    write_text_lf(d / "world.json", canonical_json(head) + "\n")
    write_jsonl(d / "situations.jsonl", world.situations)
    write_jsonl(d / "obs_specs.jsonl", world.obs_specs)
    if world.channel is not None:
        write_text_lf(d / "channel.json", canonical_json(world.channel) + "\n")
    return d


def load_world(directory: str | Path) -> World:
    """Inverse of ``save_world``; raises ValueError if the stored digest does not match."""
    d = Path(directory)
    head = json.loads((d / "world.json").read_bytes().decode("utf-8"))
    if head["schema"] != SCHEMA_VERSION:
        raise ValueError("schema version mismatch: %r" % (head["schema"],))
    chan_path = d / "channel.json"
    channel = (Channel.from_json(chan_path.read_bytes().decode("utf-8"))
               if chan_path.exists() else None)
    world = World(
        seed=head["seed"], cfg=TierCfg.from_dict(head["cfg"]),
        entities=tuple(Entity.from_dict(x) for x in head["entities"]),
        facts=tuple(Fact.from_dict(x) for x in head["facts"]),
        situations=tuple(read_jsonl(d / "situations.jsonl", Situation)),
        obs_specs=tuple(read_jsonl(d / "obs_specs.jsonl", ObsSpec)),
        card=Card.from_dict(head["card"]),
        priors=tuple(Prior.from_dict(x) for x in head["priors"]),
        mapping=head["mapping"], partition=head["partition"],
        ablated=tuple(head["ablated"]),
        extras=tuple((k, v) for k, v in head["extras"]), channel=channel)
    if world.digest() != head["digest"]:
        raise ValueError("world digest mismatch after load")
    return world
