"""Scenes, the cast and situation-first hosting of facts for LifeSim.

What this module provides
-------------------------
* ``SCENES``: one ``SceneSpec`` per scene (routine, minor, major, move, health, purchase,
  remark, trip, article): when it happens, how many people are in it, and the ranges from
  which its appraisal features (goal relevance g, stakes k, coping p, norm, conduciveness c,
  surprisal in bits) are drawn. ``sample_feats`` draws a ``Feats`` with a FIXED number of
  draws. Every range is ASSUMED; the scene table is tuned so that arousal under M1/M2 is
  right-skewed (mean about 0.2, about 3/4 of situations below 0.3) and corr(n, k) stays
  small (mundane surprises and scheduled high-stakes events are generated on purpose).
* ``PREDICATES``: the fact vocabulary (predicate -> slot name, vocabulary id, whether the
  object is an entity id or a canonical value, family, single-valued chain or not).
* ``make_cast``: the narrator, people, cities, streets, shops (each on a street) and
  employers with invented names of the world's partition, plus the generator's routine
  models (``Prior``) for breakfast, colours, closing times, relations, jobs, cities, counts.
* ``host_facts(situation, rng, kinds, state)``: SITUATION-FIRST hosting. The situation
  (with its arousal) already exists; this attaches the fact specs of the requested kinds to
  it (breakfast, companion + car colour, visits, closing time, article, trip, chain
  versions, week-one disclosures). ``stratified_pick`` is the decile-stratified assignment
  of kinds to situations that ``world`` uses, so that every fact type has the same arousal
  profile (G-HOST by construction) and every decile has support (G-SUPPORT).
* ``schedule_day``: the skeleton of one day (which scenes happen when, and whether the
  narrator wrote a line about them).

Draw discipline: every sampler uses a fixed number of draws per call, so one event's
content never shifts another's.

ASSUMED parameters this module reads through ``cfg.get(name, default)`` because ``TierCfg``
has no field for them yet (the integration step promotes them): ``host_top_boost`` (1.0:
weight of the top arousal decile in hosting, equal for every fact type; raise it to widen the
support of strongly positive coupling cells),
``max_hosted_per_situation`` (3), ``ep4_pairs_per_30d`` (8.0), ``visit_rate_scale`` (1.0),
``visit_other_share`` (0.4), ``disclosure_share`` (0.6 of the people are introduced in week
one) and ``decoy_margin`` (0.1 added to ``in1_decoy_share`` so that at least half of the stories
carry a decoy colour). The per-errand visit rates ``ERRAND_RATES`` and the scene table are ASSUMED
too.

What this module does NOT do: it builds no world, writes no text, assigns no fact or line
ids, draws no query and scores nothing. Realism of a scene mix is not claimed: hosting
deliberately lets every fact type appear in situations of every arousal level, so a detail
may be incidental to its situation (an odd place for a breakfast to be mentioned).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Sequence

from .rng import Rng, q, stream, zipf_probs
from .schema import Entity, Feats, Prior, Situation, TierCfg, new_id
from . import vocab as V

__all__ = [
    "SceneSpec", "SCENES", "NONROUTINE_ORDER", "PredSpec", "PREDICATES", "FactSpec", "Cast",
    "make_cast", "choose_actors", "sample_feats", "schedule_day", "host_facts", "ALWAYS_WRITTEN",
    "stratified_pick", "decile_of_rank", "role_of", "CHAIN_PREDS", "ERRAND_RATES",
    "slot_name", "EXTRA_PARAMS", "param",
]


# ------------------------------------------------------------ parameters not yet in TierCfg

#: ASSUMED parameters read through ``cfg.get(name, default)`` (``cfg.with_extra(name=value)`` sets
#: them); the integration step promotes them to ``TierCfg`` fields. name -> (default, meaning).
EXTRA_PARAMS: dict[str, tuple[float, str]] = {
    "host_top_boost": (1.0, "weight of the top arousal decile in hosting, equal for every fact type"),
    "max_hosted_per_situation": (3, "most fact kinds one situation hosts"),
    "ep4_pairs_per_30d": (8.0, "central + peripheral pairs (EP4) per 30 days"),
    "visit_rate_scale": (1.0, "multiplier of the per-errand visit rates (EP3c)"),
    "visit_other_share": (0.4, "look-alike visits of other people per visit of the narrator"),
    "disclosure_share": (0.6, "share of the people introduced (relation stated once) in week one"),
    "decoy_margin": (0.1, "added to in1_decoy_share so that at least half of the stories carry a decoy"),
    "channel_lag_lines": (6, "readings by which the LAG arm trails the TRUE channel"),
}


def param(cfg: TierCfg, name: str) -> Any:
    """Value of an ``EXTRA_PARAMS`` entry for a config (its default if the config does not set it)."""
    return cfg.get(name, EXTRA_PARAMS[name][0])


# ----------------------------------------------------------------------------- scenes


@dataclass(frozen=True)
class SceneSpec:
    """Where and how a scene is drawn. All ranges are (low, high) uniform bounds."""

    name: str
    hours: tuple[int, int]        # start minute-of-day window
    n_actors: tuple[int, int]     # people in the scene (inclusive)
    g: tuple[float, float]        # goal relevance
    k: tuple[float, float]        # stakes
    p: tuple[float, float]        # coping potential (control)
    norm: tuple[float, float]     # |norm violation|, sign drawn at random
    c: tuple[float, float]        # signed conduciveness
    p_sched: float                # probability that the event was expected (scheduled)
    bits_sched: tuple[float, float]
    bits_unsched: tuple[float, float]
    channels: tuple[tuple[str, float], ...]  # (channel, weight) of its lines
    big: float = 0.0              # probability that the event is a big one (major ranges)


NONROUTINE_ORDER = ("minor", "major", "move", "health", "purchase", "remark", "trip", "article")
#: Scenes that are always written down (the rest follow ``p_immediate_diary``).
ALWAYS_WRITTEN = ("article", "remark", "major", "health", "move", "trip")

# Surprisal is tuned so that the mean surprise n is about 0.35 in every common scene: scenes then
# differ in stakes and relevance but not in surprise, which keeps corr(n, k) small (mundane
# surprises and scheduled high-stakes events both exist on purpose).
SCENES: dict[str, SceneSpec] = {s.name: s for s in (
    SceneSpec("routine", (400, 1380), (0, 1), (0.0, 0.12), (0.0, 0.12), (0.7, 1.0), (0.0, 0.1),
              (-0.15, 0.25), 0.80, (0.5, 3.5), (4.0, 8.0),
              (("log", 0.45), ("diary", 0.35), ("note", 0.2))),
    SceneSpec("minor", (480, 1320), (1, 2), (0.05, 0.50), (0.05, 0.45), (0.4, 1.0), (0.0, 0.3),
              (-0.5, 0.6), 0.80, (0.5, 3.5), (4.0, 8.0),
              (("diary", 0.55), ("chat", 0.3), ("note", 0.15)), 0.10),
    SceneSpec("major", (540, 1260), (1, 3), (0.72, 1.0), (0.72, 1.0), (0.1, 0.7), (0.0, 0.7),
              (-1.0, 1.0), 0.35, (0.5, 3.5), (6.0, 11.0),
              (("diary", 0.6), ("chat", 0.3), ("note", 0.1))),
    SceneSpec("move", (540, 1080), (0, 2), (0.5, 1.0), (0.5, 0.9), (0.3, 0.9), (0.0, 0.3),
              (-0.3, 0.9), 0.50, (0.5, 3.5), (5.0, 10.0),
              (("diary", 0.7), ("note", 0.3))),
    SceneSpec("health", (480, 1200), (0, 2), (0.4, 0.95), (0.45, 1.0), (0.1, 0.7), (0.0, 0.2),
              (-1.0, 0.1), 0.35, (0.5, 3.5), (5.0, 10.0),
              (("diary", 0.7), ("chat", 0.3))),
    SceneSpec("purchase", (540, 1200), (0, 1), (0.05, 0.50), (0.10, 0.60), (0.5, 1.0), (0.0, 0.15),
              (-0.3, 0.7), 0.80, (0.5, 3.5), (4.0, 8.0),
              (("diary", 0.5), ("note", 0.3), ("chat", 0.2)), 0.06),
    SceneSpec("remark", (600, 1140), (1, 1), (0.0, 0.02), (0.0, 0.02), (0.8, 1.0), (0.0, 0.02),
              (-0.1, 0.2), 0.90, (0.2, 1.5), (3.0, 5.0),
              (("dialogue", 0.5), ("chat", 0.5))),
    SceneSpec("trip", (420, 1200), (0, 3), (0.4, 0.95), (0.3, 0.9), (0.4, 0.95), (0.0, 0.3),
              (0.0, 0.9), 0.50, (0.5, 3.5), (5.0, 9.0),
              (("diary", 0.7), ("note", 0.3))),
    SceneSpec("article", (360, 1320), (0, 0), (0.0, 0.15), (0.0, 0.30), (0.7, 1.0), (0.0, 0.1),
              (-0.4, 0.3), 0.60, (0.5, 3.5), (4.0, 8.0),
              (("article", 1.0),)),
)}

#: A big event drawn inside another scene (a wedding, a diagnosis): the major ranges but mostly
#: expected, so high stakes do not come with high surprise (corr(n, k) stays small).
_BIG = replace(SCENES["major"], p_sched=0.65)


def _u(rng: Rng, bounds: tuple[float, float]) -> float:
    return bounds[0] + (bounds[1] - bounds[0]) * rng.u()


def sample_feats(scene: str, rng: Rng, bond: float = 0.0) -> Feats:
    """Draw the appraisal features of a situation of ``scene`` (exactly 9 draws).

    ``bond`` is the bond of the main other actor (0 when alone). A scene with ``big > 0`` is
    sometimes a big event (the major ranges with a mostly expected outcome). Articles are
    handled by ``world``: their features, A and V are copied from a donor drawn from a balanced
    sequence of arousal deciles, so a story is as loud as a moment of the stream."""
    s = SCENES[scene]
    if rng.u() < s.big:
        s = _BIG
    sched = rng.chance(s.p_sched)
    bits = _u(rng, s.bits_sched if sched else s.bits_unsched)
    g = _u(rng, s.g)
    k = _u(rng, s.k)
    p = _u(rng, s.p)
    nrm = _u(rng, s.norm)
    sign = -1.0 if rng.chance(0.5) else 1.0
    c = _u(rng, s.c)
    return Feats(goal_rel=g, surprisal_bits=bits, stakes=k, bond=bond, control=p,
                 norm=sign * nrm, conduciveness=c)


def choose_actors(scene: str, rng: Rng, persons: Sequence[Entity]) -> tuple[str, ...]:
    """People in a scene, drawn without replacement with weight 0.15 + bond."""
    s = SCENES[scene]
    n = rng.ri(s.n_actors[0], s.n_actors[1])
    pool = list(persons)
    out: list[str] = []
    for _ in range(min(n, len(pool))):
        i = rng.weighted_by([0.15 + e.bond for e in pool])
        out.append(pool.pop(i).eid)
    return tuple(out)


def schedule_day(rng: Rng, day: int, cfg: TierCfg, n_target: int) -> list[tuple[int, str, bool]]:
    """Skeleton of one day: (minute, scene, has_line) for every situation.

    Non-routine scenes arrive as Poisson counts at ``scene_rate / 30`` per day. A line about
    the situation exists with probability ``p_immediate_diary`` (always for articles, remarks,
    major, health, move and trip events, which are written down). Routine situations then fill the day up to
    ``n_target`` lines (at least one)."""
    out: list[tuple[int, str, bool]] = []
    for scene in NONROUTINE_ORDER:
        count = rng.poisson(cfg.scene_rate(scene) / 30.0)
        lo, hi = SCENES[scene].hours
        for _ in range(count):
            minute = rng.ri(lo, hi)
            has = rng.chance(cfg.p_immediate_diary) if scene not in ALWAYS_WRITTEN else True
            out.append((minute, scene, has))
    n_lines = sum(1 for _, _, h in out if h)
    lo, hi = SCENES["routine"].hours
    for _ in range(max(1, n_target - n_lines)):
        out.append((rng.ri(lo, hi), "routine", True))
    return out


# -------------------------------------------------------------------------- predicates


@dataclass(frozen=True)
class PredSpec:
    """Meaning of a fact predicate. ``obj_kind`` is 'entity' (obj is an entity id) or
    'value' (obj is the canonical string). ``vocab_id`` names the closed vocabulary of the
    object. ``chain`` marks single-valued attributes with versions (supersedes)."""

    slot: str
    vocab_id: str
    obj_kind: str
    family: str
    chain: bool = False


PREDICATES: dict[str, PredSpec] = {
    "breakfast": PredSpec("breakfast", "pool:dishes", "value", "EP1"),
    "lives_in": PredSpec("lives_in", "kind:city", "entity", "SE4/SE5", chain=True),
    "works_as": PredSpec("works_as", "pool:jobs", "value", "SE4/SE5", chain=True),
    "relation": PredSpec("relation", "pool:relations", "value", "SE4/SE5"),
    "read_story": PredSpec("story", "kind:story", "entity", "IN1"),
    "vehicle_colour": PredSpec("vehicle_colour", "pool:colours", "value", "IN1"),
    "decoy_colour": PredSpec("decoy_colour", "pool:colours", "value", "IN1"),
    "companion": PredSpec("companion", "kind:person", "entity", "EP4"),
    "car_colour": PredSpec("car_colour", "pool:colours", "value", "EP4"),
    "closing_time": PredSpec("closing_time", "pool:times", "value", "IN4"),
    "on_street": PredSpec("street", "kind:street", "entity", "IN4"),
    "errand_visit": PredSpec("errand", "pool:errands", "value", "EP3c"),
    "visited": PredSpec("visited", "kind:city", "entity", "ME1"),
    "trip_companion": PredSpec("travel_companion", "kind:person", "entity", "ME1"),
}
CHAIN_PREDS = tuple(p for p, s in PREDICATES.items() if s.chain)
#: Visits per 30 days of the six errand types (ASSUMED; heavy and light errands give counts 1-8).
ERRAND_RATES = (("dentist", 0.6), ("barber", 1.0), ("library", 1.6), ("gym", 2.4),
                ("pharmacy", 3.2), ("market", 4.4))


def slot_name(pred: str) -> str:
    return PREDICATES[pred].slot


def role_of(centrality: float) -> str:
    """'central' (linked to an active goal) when centrality >= 0.5, else 'peripheral'."""
    return "central" if centrality >= 0.5 else "peripheral"


def decile_of_rank(rank: int, n: int) -> int:
    """Decile 0-9 of the rank-th smallest (0-based) of n values."""
    return min(9, (10 * rank) // max(1, n))


# ------------------------------------------------------------------------------- cast


@dataclass
class Cast:
    """Entities of a world by kind, the shop->street map and the habit dish list."""

    narrator: Entity
    persons: list[Entity] = field(default_factory=list)
    cities: list[Entity] = field(default_factory=list)
    streets: list[Entity] = field(default_factory=list)
    shops: list[Entity] = field(default_factory=list)
    orgs: list[Entity] = field(default_factory=list)
    shop_street: dict[str, str] = field(default_factory=dict)
    dishes: list[str] = field(default_factory=list)

    def all_entities(self) -> list[Entity]:
        return [self.narrator] + self.persons + self.cities + self.streets + self.shops + self.orgs


_BOND_BANDS = ((0.55, (0.70, 1.00)), (0.85, (0.40, 0.75)), (1.01, (0.05, 0.40)))
_ORG_WORDS = ("Works", "Group", "Labs", "Council", "Press", "Trust")


def make_cast(seed: int, cfg: TierCfg, partition: str) -> tuple[Cast, dict[str, Prior]]:
    """The cast and the routine models of a world, from the streams 'cast' and 'habits'."""
    rc = stream(seed, "cast")
    used: set = set()
    nid = [0]

    def eid() -> str:
        nid[0] += 1
        return new_id("entity", nid[0])

    narrator_name = V.make_names(rc, 1, partition, "person", used)[0]
    cast = Cast(narrator=Entity(eid=eid(), kind="person", name=narrator_name, bond=1.0))
    for name in V.make_names(rc, cfg.n_persons, partition, "person", used):
        u = rc.u()
        band = _BOND_BANDS[0 if u < 0.15 else (1 if u < 0.55 else 2)][1]
        cast.persons.append(Entity(eid=eid(), kind="person", name=name, bond=band[0] + (band[1] - band[0]) * rc.u()))
    for name in V.make_names(rc, cfg.n_cities, partition, "city", used):
        cast.cities.append(Entity(eid=eid(), kind="city", name=name))
    for base in V.make_names(rc, cfg.n_streets, partition, "street", used):
        cast.streets.append(Entity(eid=eid(), kind="street", name=base + " Street", aliases=(base,)))
    for base in V.make_names(rc, cfg.n_shops, partition, "shop", used):
        kind = rc.choice(V.SHOP_TYPES)
        cast.shops.append(Entity(eid=eid(), kind="shop", name=base + " " + kind.title(), aliases=(base,)))
    for base in V.make_names(rc, cfg.n_orgs, partition, "org", used):
        cast.orgs.append(Entity(eid=eid(), kind="org", name=base + " " + rc.choice(_ORG_WORDS)))
    street_ids = [s.eid for s in cast.streets]
    for shop in cast.shops:
        cast.shop_street[shop.eid] = street_ids[rc.below(len(street_ids))]

    rh = stream(seed, "habits")
    n_foods = rh.ri(cfg.n_foods_min, cfg.n_foods_max)
    cast.dishes = rh.sample(V.DISHES, n_foods)
    priors = {
        "breakfast": Prior(slot="breakfast", values=tuple(cast.dishes),
                           probs=zipf_probs(n_foods, cfg.habit_zipf_s)),
    }

    def uniform(slot: str, values: Sequence[str]) -> Prior:
        return Prior(slot=slot, values=tuple(values), probs=tuple(1.0 / len(values) for _ in values))

    priors["vehicle_colour"] = uniform("vehicle_colour", V.COLOURS)
    priors["car_colour"] = uniform("car_colour", V.COLOURS)
    priors["closing_time"] = uniform("closing_time", V.TIMES)
    priors["relation"] = uniform("relation", V.RELATIONS)
    priors["works_as"] = uniform("works_as", V.JOBS)
    priors["lives_in"] = uniform("lives_in", [c.eid for c in cast.cities])
    priors["visit_count"] = uniform("visit_count", V.COUNTS[:8])
    return cast, priors


# ----------------------------------------------------------------------- fact hosting


@dataclass(frozen=True)
class FactSpec:
    """A fact to attach to a situation; the world assigns ids, validity and surprisal.

    ``subj`` '' means the narrator; ``span`` is the number of days the fact stays valid after
    the situation's day (0 = that day only, -1 = open-ended); ``mention`` is the role of the
    line that first states it; ``recalls`` asks for later 'recall' lines while it is valid
    (only used for chain versions that get superseded); ``source`` is the teller or author."""

    pred: str
    subj: str
    obj: str
    src: str = "lived"
    centrality: float = 0.0
    span: int = 0
    chain: bool = False
    role: str = ""
    mention: str = "assert"
    source: str = ""


def _centrality(sit: Situation, central: bool, cfg: TierCfg) -> float:
    g = sit.feats.goal_rel
    if central:
        return q(0.55 + 0.45 * g)
    return q(0.05 + 0.1 * g) if cfg.periphery_goal_relevant == 0 else q(0.55 + 0.45 * g)


def _pick_other(rng: Rng, values: Sequence[str], exclude: Sequence[str]) -> str:
    pool = [v for v in values if v not in exclude] or list(values)
    return pool[rng.below(len(pool))]


def host_facts(sit: Situation, rng: Rng, kinds: Sequence[str], state: dict[str, Any]) -> list[FactSpec]:
    """Fact specs of the requested ``kinds`` for one already-existing situation.

    ``kinds`` entries are 'name' or 'name:arg': breakfast, companion, visit:<errand>,
    visit_other:<errand>, closing_time, article, trip, first:lives_in, first:works_as,
    update:lives_in, update:works_as, disclose:<person eid>. ``state`` carries the cast,
    ``cfg``, the priors, the entity-id counter ('next_eid'), 'new_entities', 'used_shops'
    and 'history' (values already taken by each chain). The situation's own appraisal is
    never changed by what it hosts."""
    cast: Cast = state["cast"]
    cfg: TierCfg = state["cfg"]
    out: list[FactSpec] = []
    for token in kinds:
        kind, _, arg = token.partition(":")
        if kind == "breakfast":
            prior = state["priors"]["breakfast"]
            out.append(FactSpec("breakfast", "", prior.values[rng.weighted(prior.probs)], span=0))
        elif kind == "companion":
            who = sit.actors[0] if sit.actors else cast.persons[rng.below(len(cast.persons))].eid
            out.append(FactSpec("companion", "", who, centrality=_centrality(sit, True, cfg),
                                role="central"))
            out.append(FactSpec("car_colour", "", V.COLOURS[rng.below(len(V.COLOURS))],
                                centrality=_centrality(sit, False, cfg), role="peripheral"))
        elif kind in ("visit", "visit_other"):
            who = ""
            if kind == "visit_other":
                who = sit.actors[0] if sit.actors else cast.persons[rng.below(len(cast.persons))].eid
            out.append(FactSpec("errand_visit", who, arg, centrality=q(0.1 + 0.3 * sit.feats.goal_rel)))
        elif kind == "closing_time":
            free = [s for s in cast.shops if s.eid not in state["used_shops"]]
            if not free:
                continue
            shop = free[rng.below(len(free))]
            state["used_shops"].append(shop.eid)
            teller = sit.actors[0] if sit.actors else ""
            out.append(FactSpec("on_street", shop.eid, cast.shop_street[shop.eid], src="told", source=teller,
                                centrality=0.05, span=-1))
            out.append(FactSpec("closing_time", shop.eid, V.TIMES[rng.below(len(V.TIMES))], src="told",
                                source=teller, centrality=0.05, span=-1))
        elif kind == "article":
            out.extend(_article(sit, rng, state))
        elif kind == "trip":
            city = cast.cities[rng.below(len(cast.cities))]
            out.append(FactSpec("visited", "", city.eid, span=rng.ri(2, 6), centrality=_centrality(sit, True, cfg)))
            if sit.actors:
                out.append(FactSpec("trip_companion", "", sit.actors[0], centrality=_centrality(sit, True, cfg),
                                    role="central"))
        elif kind in ("first", "update"):
            hist: list[str] = state["history"].setdefault(arg, [])
            if arg == "lives_in":
                value = _pick_other(rng, [c.eid for c in cast.cities], hist)
            else:
                value = _pick_other(rng, V.JOBS, hist)
            hist.append(value)
            out.append(FactSpec(arg, "", value, chain=True, span=-1, centrality=0.9,
                                mention="update" if kind == "update" else "assert"))
        elif kind == "disclose":
            rel = V.RELATIONS[rng.below(len(V.RELATIONS))]
            out.append(FactSpec("relation", arg, rel, src="told", span=-1, centrality=0.5,
                                source=arg))
        else:
            raise ValueError("unknown hosting kind %r" % (token,))
    return out


def _article(sit: Situation, rng: Rng, state: dict[str, Any]) -> list[FactSpec]:
    """A third-party story read by the narrator: story entity, car colour, maybe a decoy."""
    cast: Cast = state["cast"]
    cfg: TierCfg = state["cfg"]
    taken = state["story_keys"]
    for _ in range(200):
        kind = V.STORY_KINDS[rng.below(len(V.STORY_KINDS))]
        city = cast.cities[rng.below(len(cast.cities))]
        if (kind, city.eid) not in taken:
            break
    else:  # pragma: no cover - 31 kinds x >= 24 cities leave room for any realistic tier
        raise RuntimeError("story pool exhausted")
    taken.append((kind, city.eid))
    state["next_eid"] += 1
    story = Entity(eid=new_id("entity", state["next_eid"]), kind="story", name="%s in %s" % (kind, city.name),
                   aliases=())
    state["new_entities"].append(story)
    colour = V.COLOURS[rng.below(len(V.COLOURS))]
    decoy = _pick_other(rng, V.COLOURS, [colour])
    has_decoy = rng.chance(min(1.0, cfg.in1_decoy_share + param(cfg, "decoy_margin")))
    central = not rng.chance(cfg.peripheral_share)
    out = [FactSpec("read_story", "", story.eid, src="read", centrality=0.1),
           FactSpec("vehicle_colour", story.eid, colour, src="read", role=role_of(0.7 if central else 0.1),
                    centrality=q(0.7 if central else 0.1))]
    if has_decoy:
        out.append(FactSpec("decoy_colour", story.eid, decoy, src="read", centrality=0.1))
    return out


# --------------------------------------------------------------- stratified assignment


def stratified_pick(rng: Rng, pool: Sequence[int], deciles: Sequence[int], n: int,
                    weights: Sequence[float]) -> tuple[list[int], int]:
    """Pick up to ``n`` distinct items of ``pool`` with decile counts following ``weights``.

    ``deciles[i]`` is the decile (0-9) of item ``i``. Quotas use largest remainders; a decile
    without enough eligible items hands its shortfall to the other deciles at random. Returns
    (picked items, shortfall) where shortfall counts items that could not be placed at all."""
    buckets: list[list[int]] = [[] for _ in range(10)]
    for i in pool:
        buckets[deciles[i]].append(i)
    for b in buckets:
        rng.shuffle(b)
    total = float(sum(weights))
    quota = [n * w / total for w in weights]
    base = [int(x) for x in quota]
    order = sorted(range(10), key=lambda d: (-(quota[d] - base[d]), rng.u()))
    for d in order[: n - sum(base)]:
        base[d] += 1
    picked: list[int] = []
    short = 0
    for d in range(10):
        take = min(base[d], len(buckets[d]))
        picked.extend(buckets[d][:take])
        short += base[d] - take
        buckets[d] = buckets[d][take:]
    if short:
        left = [i for b in buckets for i in b]
        rng.shuffle(left)
        extra = left[:short]
        picked.extend(extra)
        short -= len(extra)
    return picked, short
