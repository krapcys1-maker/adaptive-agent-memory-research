"""Worlds for LifeSim: build, check, delete events, digest.

What this module provides
-------------------------
* ``build_world(seed, cfg) -> World``: one synthetic life, STRUCTURE FIRST (cast, facts,
  situations with appraisal, observation specs with mentions and slots; no text, no queries).
  Order of work: cast and routine models (streams ``cast``, ``habits``) -> the day skeleton and
  one ``Situation`` per event with its own stream ``(seed, "life", sid)`` (features, A, V,
  mood) -> a hosting plan (stream ``host``) -> the facts of each situation (stream
  ``(seed, "life", sid, "facts")``) -> the lines (stream ``(seed, "life", sid, "lines")``).
  SITUATION-FIRST HOSTING: arousal exists before any fact is attached; the fact types are
  then assigned to situations stratified by arousal decile of the stream with the SAME decile
  weights for every type (``host_top_boost`` raises the top decile equally for all), so fact
  type is independent of arousal by construction (G-HOST) and each decile has support
  (G-SUPPORT). Need and queries are generated AFTER the stream, by ``queries`` (not here).
* ``check_world(world) -> list[str]``: every invariant of a well-formed world; ``[]`` = pass.
* ``delete_events(world, sids)``: the ablation operator. It removes the situations, the facts
  they host and ALL their lines (a line only ever mentions facts of its own situation, and
  later references to a fact are 'recall' lines of the same situation), extends ``ablated``,
  renumbers nothing, and keeps the readings of the surviving lines of an attached channel.
  Surviving rows are untouched except that a fact whose predecessor was deleted gets
  ``supersedes = ''``.
* ``world_digest`` (= ``world.digest()``), and helpers for the layers above: ``situation_deciles``,
  ``arousal_deciles`` (by line), ``host_profile``, ``chi_square_independence``, ``slots_for``.

Structure conventions that ``queries`` can rely on (see ``scenes.PREDICATES``): entity e0001 is the
narrator (``Card.name``) and a fact about the narrator has ``subj`` = that id. ``Fact.obj`` is an
entity id when ``PREDICATES[pred].obj_kind == 'entity'`` and a canonical string otherwise. Facts:
breakfast (valid that day only; at most one a day), lives_in / works_as (version chains linked by
``supersedes``; the first version stated in week one, updates strictly after it, each superseded
version re-mentioned ``se_stale_mentions`` times by 'recall' lines while it holds, the newest stated
once), relation (a person's relation to the narrator, told once in week one), read_story +
vehicle_colour (+ decoy_colour) of a story entity (src 'read', one 'article' line), companion
(central) + car_colour (peripheral) hosted together in one situation and one line, closing_time +
on_street of a shop (one told remark, never repeated, at most 80% of the shops), errand_visit (the
narrator's visits and look-alike visits of other people), visited + trip_companion (trips; every life
of 20 days or more has at least one, planted if the Poisson draw gave none, so the false-premise
family always has a real trip to be confused with). Never stated anywhere, on purpose: the people not
introduced, the shops without a remark, the cities never visited, most days' breakfast.
A line's ``frame`` is '' (plain), 'retell' (rehearsal retelling), 'recall' (later reference to a chain
version) or 'incidental' (an update mentioned in passing). Every line mentions only facts hosted by its
own situation. Only situations with a plain line (frame '' or 'incidental') can host facts.
``world.extra('hosting')`` records {generator, n_updates, shortfall, decile_weights, chains}; a
non-zero shortfall means a fact kind found fewer eligible situations than it asked for.

Appraisal: one mapping (M1/M2, ``cfg.mappings``) per world; mood is the covariate ``Situation.mood``
(the mood entering the day). If corr(surprise n, stakes k) would exceed 0.8 x ``max_corr_nk`` the
most 'unexpected and high-stakes' events are made expected instead (``_repair_surprise_stakes``).
Articles copy the features, A and V of donor situations drawn from a balanced sequence of arousal
deciles. ASSUMED parameters are the ``TierCfg`` fields plus ``scenes.EXTRA_PARAMS`` (read through
``scenes.param``); the scene table of ``scenes`` is ASSUMED as a whole.

What this module does NOT do: it renders no text, builds no queries or gold, applies no channel
(``channel`` does), reads no clock and uses no model; it does not claim any scene mix resembles
a human life, and it guarantees nothing about worlds built from a TierCfg that violates
``check_world`` (tiny custom sizes can fail the pool-size checks on purpose).
"""

from __future__ import annotations

import dataclasses
import math
from typing import Sequence

from . import scenes as S
from . import vocab as V
from .appraisal import appraise, mood_step, pearson, surprisal_bits
from .channel import obs_arousal, restrict_channel
from .rng import q, stream
from .schema import (Card, Fact, Mention, MINUTES_PER_DAY, ObsSpec, Situation, Slot, TierCfg, World,
                     new_id)

__all__ = [
    "TierCfg", "build_world", "check_world", "delete_events", "world_digest", "slots_for",
    "situation_deciles", "arousal_deciles", "host_profile", "chi_square_independence",
    "GENERATOR_VERSION",
]

GENERATOR_VERSION = "lifesim-world-1"
_SURPRISAL_SLOT = {"breakfast": "breakfast", "vehicle_colour": "vehicle_colour",
                   "decoy_colour": "vehicle_colour", "car_colour": "car_colour",
                   "closing_time": "closing_time", "relation": "relation", "works_as": "works_as",
                   "lives_in": "lives_in"}


def world_digest(world: World) -> str:
    """SHA-256 of the world's structure (= ``world.digest()``)."""
    return world.digest()


# ------------------------------------------------------------------------------ slots


def _display(ents: dict, f: Fact) -> str:
    return ents[f.obj].name if S.PREDICATES[f.pred].obj_kind == "entity" else f.obj


def _display_or_none(ents: dict, f: Fact) -> str | None:
    """Like ``_display`` but None when the object entity does not exist (check_world must not crash)."""
    try:
        return _display(ents, f)
    except KeyError:
        return None


def slots_for(ents: dict, narrator_eid: str, facts: Sequence[Fact]) -> tuple[Slot, ...]:
    """Slots of a line that states ``facts``: one per fact (its object, verbatim) plus a context
    slot (fid '') naming each non-narrator subject (a person, a shop, a story)."""
    keys = {(S.slot_name(f.pred), _display(ents, f)) for f in facts}
    out: list[Slot] = []
    seen: set = set()

    def add(name: str, value: str, fid: str) -> None:
        if (name, value, fid) not in seen:
            seen.add((name, value, fid))
            out.append(Slot(name=name, value=value, fid=fid))

    for f in facts:
        if f.subj != narrator_eid:
            subj = ents[f.subj]
            if (subj.kind, subj.name) not in keys:
                add(subj.kind, subj.name, "")
        add(S.slot_name(f.pred), _display(ents, f), f.fid)
    return tuple(out)


# ----------------------------------------------------------------------- situations


def _make_situations(seed: int, cfg: TierCfg, cast: S.Cast, mapping: str) -> tuple[list[Situation], list[bool]]:
    rs = stream(seed, "life", "skeleton")
    rd = stream(seed, "mention", "daily")
    raw: list[tuple[int, int, str, bool]] = []
    for day in range(cfg.days):
        n_target = rd.poisson_between(cfg.obs_per_day, cfg.obs_min, cfg.obs_max)
        for minute, scene, has in S.schedule_day(rs, day, cfg, n_target):
            raw.append((day, minute, scene, has))
    if cfg.days >= 20 and not any(r[2] == "trip" for r in raw):  # ME1 needs one real trip as the trap
        lo, hi = S.SCENES["trip"].hours
        raw.append((rs.ri(cfg.days // 5, cfg.days - 1 - cfg.days // 5), rs.ri(lo, hi), "trip", True))
    raw.sort(key=lambda r: (r[0], r[1]))
    bond_of = {e.eid: e.bond for e in cast.persons}
    sits: list[Situation] = []
    has_line: list[bool] = []
    for i, (day, minute, scene, has) in enumerate(raw):
        sid = new_id("situation", i + 1)
        ev = stream(seed, "life", sid)
        actors = S.choose_actors(scene, ev, cast.persons)
        feats = S.sample_feats(scene, ev, bond_of[actors[0]] if actors else 0.0)
        a, v = appraise(feats, mapping, ev, cfg)
        shop_i = ev.below(len(cast.shops))
        city_i = ev.below(len(cast.cities))
        place = cast.shops[shop_i].eid if scene == "purchase" else (
            cast.cities[city_i].eid if scene == "trip" else "")
        sits.append(Situation(sid=sid, day=day, minute=minute, scene=scene, actors=actors, place=place,
                              feats=feats, A=a, V=v))
        has_line.append(has)
    # Articles are as loud as a moment of the stream: each copies the features, A and V of a donor
    # (any non-article situation) drawn from a balanced sequence of the donors' arousal deciles, so
    # that third-party stories span the deciles evenly just like every other hosted fact type.
    arts = [i for i, s in enumerate(sits) if s.scene == "article"]
    donors = [i for i, s in enumerate(sits) if s.scene != "article"]
    if arts and donors:
        ra = stream(seed, "life", "skeleton", "articles")
        ranked = sorted(donors, key=lambda j: (sits[j].A, j))
        buckets: list[list[int]] = [[] for _ in range(10)]
        for r, j in enumerate(ranked):
            buckets[S.decile_of_rank(r, len(ranked))].append(j)
        deck = list(range(10))
        ra.shuffle(deck)
        seq = [deck[k % 10] for k in range(len(arts))]
        ra.shuffle(seq)
        for i, d in zip(arts, seq):
            donor = sits[buckets[d][ra.below(len(buckets[d]))]]
            sits[i] = dataclasses.replace(sits[i], feats=donor.feats, A=donor.A, V=donor.V)
    _repair_surprise_stakes(seed, cfg, mapping, sits)
    mood = 0.0
    j = 0
    out: list[Situation] = []
    for day in range(cfg.days):
        k = j
        while k < len(sits) and sits[k].day == day:
            k += 1
        day_sits = sits[j:k]
        out.extend(dataclasses.replace(s, mood=mood) for s in day_sits)
        mood = mood_step(mood, [(s.A, s.V) for s in day_sits], cfg)
        j = k
    return out, has_line


def _repair_surprise_stakes(seed: int, cfg: TierCfg, mapping: str, sits: list[Situation]) -> None:
    """Keep corr(surprise n, stakes k) below 0.8 x ``max_corr_nk`` by making the most 'unexpected
    high-stakes' events expected instead (their surprisal is redrawn from the scheduled range and
    A, V are recomputed). Small worlds with few big events are the ones that need it."""
    limit = 0.8 * cfg.max_corr_nk
    scale = cfg.surprise_bits_scale
    for attempt in range(60):
        ns = [s.feats.surprise(scale) for s in sits]
        ks = [s.feats.stakes for s in sits]
        if pearson(ns, ks) <= limit:
            return
        mn = sum(ns) / len(ns)
        mk = sum(ks) / len(ks)
        i, best = -1, 0.0
        for j in range(len(sits)):  # the most 'unexpected and high-stakes' event is the one to repair
            if ns[j] > mn and ks[j] > mk and (ns[j] - mn) * (ks[j] - mk) > best:
                i, best = j, (ns[j] - mn) * (ks[j] - mk)
        if i < 0:
            return
        s = sits[i]
        ev = stream(seed, "life", s.sid, "repair", attempt)
        feats = dataclasses.replace(s.feats, surprisal_bits=q(0.5 + 3.0 * ev.u()))
        a, v = appraise(feats, mapping, ev, cfg)
        sits[i] = dataclasses.replace(s, feats=feats, A=a, V=v)


# --------------------------------------------------------------------------- hosting


def _plan_hosting(seed: int, cfg: TierCfg, cast: S.Cast, sits: list[Situation], has_line: list[bool]):
    """Assign fact kinds to situations. Returns (plan, shortfall, decile weights)."""
    rh = stream(seed, "host")
    n = len(sits)
    line_idx = [i for i in range(n) if has_line[i]]
    order = sorted(line_idx, key=lambda i: (sits[i].A, i))
    deciles = [0] * n
    for r, i in enumerate(order):
        deciles[i] = S.decile_of_rank(r, len(order))
    weights = [1.0] * 9 + [float(S.param(cfg, "host_top_boost"))]
    cap = int(S.param(cfg, "max_hosted_per_situation"))
    plan: dict[int, list[str]] = {i: [] for i in range(n)}
    short: dict[str, int] = {}

    def free(i: int) -> bool:
        return len(plan[i]) < cap

    def lived(i: int) -> bool:
        return sits[i].scene not in ("article", "remark")

    # 1. forced by the scene: articles, remarks (closing times), trips
    max_closing = int(0.8 * len(cast.shops))
    n_closing = 0
    for i in line_idx:
        sc = sits[i].scene
        if sc == "article":
            plan[i].append("article")
        elif sc == "remark" and n_closing < max_closing:
            plan[i].append("closing_time")
            n_closing += 1
        elif sc == "trip":
            plan[i].append("trip")
    # 2. week one: first identity facts and the introductions of rare names
    week = min(7, cfg.days)
    wk = [i for i in line_idx if sits[i].day < week and lived(i)]
    for token in ("first:lives_in", "first:works_as"):
        cands = [i for i in wk if free(i)]
        if cands:
            plan[cands[rh.below(len(cands))]].append(token)
    n_disc = int(round(S.param(cfg, "disclosure_share") * len(cast.persons)))
    for p in rh.sample([e.eid for e in cast.persons], n_disc):
        cands = [i for i in wk if free(i)]
        if cands:
            plan[cands[rh.below(len(cands))]].append("disclose:" + p)
    # 3. updates of the identity chains, one per window, decile drawn with the common weights
    lo_day = week + 1  # updates come strictly after week one, where the first versions are stated
    hi_day = cfg.days - 2
    n_updates = {}
    for chain in S.CHAIN_PREDS:
        if hi_day < lo_day:  # no room for an update in a life this short
            n_updates[chain] = 0
            continue
        n_up = min(cfg.chain_depth_max, max(1, rh.poisson(cfg.update_rate * cfg.days / 365.0)))
        n_updates[chain] = n_up
        width = (hi_day - lo_day + 1) / n_up
        for j in range(n_up):
            w_lo = lo_day + int(j * width)
            w_hi = max(w_lo, lo_day + int((j + 1) * width) - 1)
            cands = [i for i in line_idx if w_lo <= sits[i].day <= w_hi and lived(i) and free(i)]
            if not cands:
                continue
            d = rh.weighted_by(weights)
            pool = [i for i in cands if deciles[i] == d] or cands
            plan[pool[rh.below(len(pool))]].append("update:" + chain)
    # 4. central + peripheral pairs (EP4)
    n_pairs = int(round(S.param(cfg, "ep4_pairs_per_30d") * cfg.days / 30.0))
    cands = [i for i in line_idx if lived(i) and sits[i].actors and free(i)]
    picked, sf = S.stratified_pick(rh, cands, deciles, n_pairs, weights)
    for i in picked:
        plan[i].append("companion")
    short["companion"] = sf
    # 5. visits of the narrator and look-alike visits of others (EP3c)
    scale = float(S.param(cfg, "visit_rate_scale"))
    other = float(S.param(cfg, "visit_other_share"))
    tokens: list[str] = []
    for name, rate in S.ERRAND_RATES:
        cnt = int(round(rate * scale * cfg.days / 30.0))
        tokens += ["visit:" + name] * cnt + ["visit_other:" + name] * int(round(cnt * other))
    cands = [i for i in line_idx if lived(i) and free(i)]
    picked, sf = S.stratified_pick(rh, cands, deciles, len(tokens), weights)
    rh.shuffle(tokens)
    seen: set = set()
    for i, tok in zip(sorted(picked), tokens):
        key = (sits[i].day, tok)
        if key not in seen:
            seen.add(key)
            plan[i].append(tok)
    short["visit"] = sf
    # 6. breakfast statements, at most one per day
    by_day: dict[int, list[int]] = {}
    for i in line_idx:
        if lived(i) and free(i):
            by_day.setdefault(sits[i].day, []).append(i)
    day_cands = [by_day[d][rh.below(len(by_day[d]))] for d in sorted(by_day)]
    n_b = min(len(day_cands), int(round(cfg.routine_rate * cfg.days / 30.0)))
    picked, sf = S.stratified_pick(rh, day_cands, deciles, n_b, weights)
    for i in picked:
        plan[i].append("breakfast")
    short["breakfast"] = sf
    return plan, short, n_updates, weights


# ----------------------------------------------------------------------------- lines


def _make_lines(seed: int, cfg: TierCfg, cast: S.Cast, sits: list[Situation], has_line: list[bool],
                hosted: dict, facts_by: dict, ents: dict, fact_source: dict) -> list[ObsSpec]:
    """All lines of the world as ObsSpecs sorted by time with fresh oids."""
    drafts: list[tuple[int, int, int, dict]] = []
    narrator = cast.narrator.eid
    end_of_life = cfg.days * MINUTES_PER_DAY - 1

    for i, sit in enumerate(sits):
        rl = stream(seed, "life", sit.sid, "lines")
        hs = [(facts_by[fid], role) for fid, role in hosted.get(sit.sid, [])]
        day_end = sit.day * MINUTES_PER_DAY + MINUTES_PER_DAY - 1
        base_t = sit.t
        k = 0

        def draft(t: int, channel: str, pairs, frame: str, source: str) -> None:
            nonlocal k
            drafts.append((t, i, k, dict(
                channel=channel, sid=sit.sid, frame=frame, source=source,
                mentions=tuple(Mention(fid=f.fid, role=r) for f, r in pairs),
                slots=slots_for(ents, narrator, [f for f, _ in pairs]) if pairs else (),
                target_len=rl.ri(cfg.words_min, cfg.words_max))))
            k += 1

        if has_line[i]:
            spec = S.SCENES[sit.scene]
            channel = spec.channels[rl.weighted_by([w for _, w in spec.channels])][0]
            outlet = cast.orgs[rl.below(len(cast.orgs))].eid
            incidental = rl.chance(cfg.incidental_update_share)
            t = min(day_end, base_t + rl.ri(2, 90))
            source = ""
            for f, _ in hs:
                if f.src == "told" and fact_source.get(f.fid):
                    source = fact_source[f.fid]
                elif f.src == "read":
                    source = outlet
            upd = any(r == "update" for _, r in hs)
            draft(t, channel, hs, "incidental" if (upd and incidental) else "", source)
        if cfg.rehearsal != "off" and sit.A >= cfg.rehearsal_a_min:
            if cfg.rehearsal == "natural":
                n_re = 1 if rl.chance(cfg.rehearsal_p_natural) else 0
            else:
                n_re = cfg.rehearsal_repeats_strong if rl.chance(cfg.rehearsal_p_strong) else 0
            central = [(f, "recall") for f, _ in hs if f.centrality >= 0.5]
            for r in range(n_re):
                if cfg.rehearsal == "natural":
                    t2 = min(day_end, base_t + rl.ri(60, 600))
                else:
                    t2 = min(end_of_life, base_t + r * MINUTES_PER_DAY + rl.ri(60, 300))
                draft(t2, "chat" if rl.chance(0.6) else "dialogue", central, "retell", "")
        for f, _ in hs:
            if f.pred in S.CHAIN_PREDS and f.vto is not None:
                n_rec = min(cfg.se_stale_mentions, f.vto - f.vfrom)
                if n_rec > 0:
                    days = rl.sample(list(range(f.vfrom + 1, f.vto + 1)), n_rec)
                    for d in sorted(days):
                        draft(d * MINUTES_PER_DAY + rl.ri(420, 1320), "chat" if rl.chance(0.4) else "diary",
                              [(f, "recall")], "recall", "")
    drafts.sort(key=lambda d: (d[0], d[1], d[2]))
    return [ObsSpec(oid=new_id("obs", n + 1), t_obs=t, **fields) for n, (t, _, _, fields) in enumerate(drafts)]


# ---------------------------------------------------------------------- build_world


def build_world(seed: int, cfg: TierCfg) -> World:
    """Build the structure of one life (deterministic in (seed, cfg); see the module docstring)."""
    for name in ("n_persons", "n_cities", "n_streets", "n_shops", "n_orgs"):
        if getattr(cfg, name) < 1:
            raise ValueError("build_world needs %s >= 1" % name)
    partition = cfg.resolved_partition(seed)
    cast, priors = S.make_cast(seed, cfg, partition)
    mapping = cfg.mappings[stream(seed, "character", "mapping").below(len(cfg.mappings))]
    sits, has_line = _make_situations(seed, cfg, cast, mapping)
    plan, short, n_updates, weights = _plan_hosting(seed, cfg, cast, sits, has_line)

    base_entities = cast.all_entities()
    state = {"cast": cast, "cfg": cfg, "priors": priors, "next_eid": len(base_entities),
             "new_entities": [], "used_shops": [], "history": {}, "story_keys": []}
    ents = {e.eid: e for e in base_entities}
    narrator = cast.narrator.eid
    facts: list[Fact] = []
    index: dict[str, int] = {}
    chain_cur: dict[tuple, str] = {}
    hosted: dict[str, list] = {}
    sit_facts: dict[str, list] = {}
    fact_source: dict[str, str] = {}
    for i, sit in enumerate(sits):
        kinds = plan.get(i)
        if not kinds:
            continue
        specs = S.host_facts(sit, stream(seed, "life", sit.sid, "facts"), kinds, state)
        for e in state["new_entities"]:
            ents[e.eid] = e
        for sp in specs:
            fid = new_id("fact", len(facts) + 1)
            subj = sp.subj or narrator
            supersedes = ""
            if sp.chain:
                prev = chain_cur.get((subj, sp.pred))
                if prev is not None:
                    pf = facts[index[prev]]
                    facts[index[prev]] = dataclasses.replace(pf, vto=sit.day - 1)
                    supersedes = prev
                chain_cur[(subj, sp.pred)] = fid
            slot = _SURPRISAL_SLOT.get(sp.pred)
            bits = surprisal_bits(priors[slot], sp.obj) if slot in priors else 0.0
            facts.append(Fact(fid=fid, subj=subj, pred=sp.pred, obj=sp.obj, vfrom=sit.day,
                              vto=None if sp.span < 0 else sit.day + sp.span, src=sp.src,
                              centrality=sp.centrality, supersedes=supersedes, surprisal_bits=bits))
            index[fid] = len(facts) - 1
            hosted.setdefault(sit.sid, []).append((fid, sp.mention))
            sit_facts.setdefault(sit.sid, []).append(fid)
            fact_source[fid] = sp.source
    entities = base_entities + list(state["new_entities"])
    facts_by = {f.fid: f for f in facts}
    specs_out = _make_lines(seed, cfg, cast, sits, has_line, hosted, facts_by, ents, fact_source)
    final_sits = tuple(dataclasses.replace(s, facts=tuple(sit_facts.get(s.sid, ()))) for s in sits)
    world = World(seed=seed, cfg=cfg, entities=tuple(entities), facts=tuple(facts), situations=final_sits,
                  obs_specs=tuple(specs_out), card=Card(name=cast.narrator.name, role="diarist"),
                  priors=tuple(priors[k] for k in sorted(priors)), mapping=mapping, partition=partition)
    chains = {p: [f.fid for f in facts if f.pred == p] for p in S.CHAIN_PREDS}
    info = {"generator": GENERATOR_VERSION, "n_updates": n_updates, "shortfall": short,
            "decile_weights": weights, "chains": chains}
    return world.with_extra("hosting", info)


# ------------------------------------------------------------------- deciles and profile


def _bears_line(spec: ObsSpec) -> bool:
    return spec.frame not in ("retell", "recall")


def _situation_ranks(world: World) -> tuple[dict[str, int], int]:
    """Rank (0-based, by arousal then creation order) of every situation that has a plain line."""
    have = {o.sid for o in world.obs_specs if _bears_line(o)}
    idx = [i for i, s in enumerate(world.situations) if s.sid in have]
    order = sorted(idx, key=lambda i: (world.situations[i].A, i))
    return {world.situations[i].sid: r for r, i in enumerate(order)}, len(order)


def situation_deciles(world: World) -> dict[str, int]:
    """Arousal decile (0-9) of every situation with a plain line, by rank of A (the hosting deciles)."""
    ranks, n = _situation_ranks(world)
    return {sid: S.decile_of_rank(r, n) for sid, r in ranks.items()}


def arousal_deciles(world: World) -> dict[str, int]:
    """Arousal decile (0-9) of every LINE by rank of its channel arousal (retellings at their factor)."""
    a = obs_arousal(world)
    order = sorted(range(len(a)), key=lambda i: (a[i], i))
    out = {}
    for r, i in enumerate(order):
        out[world.obs_specs[i].oid] = S.decile_of_rank(r, len(a))
    return out


def host_profile(world: World, bins: int = 10) -> dict[str, list[int]]:
    """For every predicate, the number of its facts hosted in each of ``bins`` arousal bins of the
    stream (bins=10 deciles, bins=3 terciles), the table behind the G-HOST chi-square."""
    ranks, n = _situation_ranks(world)
    out: dict[str, list[int]] = {}
    for f in world.facts:
        sid = world.host(f.fid).sid
        if sid not in ranks:
            continue
        b = min(bins - 1, (bins * ranks[sid]) // max(1, n))
        out.setdefault(f.pred, [0] * bins)[b] += 1
    return out


def _gamma_q(a: float, x: float) -> float:
    """Regularised upper incomplete gamma Q(a, x) (statistics only; uses the C library)."""
    if x <= 0.0:
        return 1.0
    if x < a + 1.0:
        ap, s = a, 1.0 / a
        d = s
        for _ in range(1000):
            ap += 1.0
            d *= x / ap
            s += d
            if abs(d) < abs(s) * 1e-15:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    b = x + 1.0 - a
    c = 1e300
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi_square_independence(table: Sequence[Sequence[float]]) -> tuple[float, int, float]:
    """Pearson chi-square test of independence of a contingency table: (chi2, dof, p).

    Empty rows and columns are dropped; a table that is left with fewer than 2 rows or columns
    returns (0.0, 0, 1.0)."""
    rows = [list(r) for r in table if sum(r) > 0]
    if not rows:
        return 0.0, 0, 1.0
    keep = [j for j in range(len(rows[0])) if sum(r[j] for r in rows) > 0]
    rows = [[r[j] for j in keep] for r in rows]
    if len(rows) < 2 or len(keep) < 2:
        return 0.0, 0, 1.0
    total = float(sum(sum(r) for r in rows))
    rs = [sum(r) for r in rows]
    cs = [sum(r[j] for r in rows) for j in range(len(rows[0]))]
    chi2 = 0.0
    for i, r in enumerate(rows):
        for j, o in enumerate(r):
            e = rs[i] * cs[j] / total
            chi2 += (o - e) * (o - e) / e
    dof = (len(rows) - 1) * (len(rows[0]) - 1)
    return chi2, dof, _gamma_q(dof / 2.0, chi2 / 2.0)


# ------------------------------------------------------------------------- check_world

_LIMIT = 60


def check_world(world: World) -> list[str]:
    """All invariants of a well-formed world; an empty list means it passes."""
    cfg = world.cfg
    P: list[str] = []

    def bad(msg: str) -> None:
        if len(P) < _LIMIT:
            P.append(msg)

    ents = {e.eid: e for e in world.entities}
    facts = {f.fid: f for f in world.facts}
    sits = {s.sid: s for s in world.situations}
    ablated = bool(world.ablated)
    if not world.entities or world.entities[0].name != world.card.name:
        bad("the first entity must be the narrator named like the card")
        return P
    # cast
    for kind in ("city", "street", "shop"):
        if len(world.entities_of(kind)) < cfg.min_pool:
            bad("fewer than min_pool=%d entities of kind %s" % (cfg.min_pool, kind))
    if len(world.entities_of("person")) - 1 < min(cfg.n_persons, cfg.min_pool):
        bad("too few people")
    names = [e.name.casefold() for e in world.entities]
    if len(set(names)) != len(names):
        bad("duplicate entity names")
    for e in world.entities:
        if not 0.0 <= e.bond <= 1.0:
            bad("bond out of range for %s" % e.eid)
        if e.kind in ("person", "city", "street", "shop", "org"):
            if V.partition_of_name(e.name.split()[0]) != world.partition:
                bad("name %r is not of the %s partition" % (e.name, world.partition))
    # priors
    pb = world.prior("breakfast")
    if pb is None or len(pb.values) < cfg.n_foods_min or pb.entropy_bits() < 4.5 \
            or sum(sorted(pb.probs)[-3:]) >= 0.30:
        bad("breakfast prior needs >= %d values, entropy >= 4.5 bits and top-3 mass < 0.30" % cfg.n_foods_min)
    for p in world.priors:
        if abs(sum(p.probs) - 1.0) > 1e-6:
            bad("prior %s does not sum to 1" % p.slot)
    # situations
    host_count: dict[str, int] = {}
    for s in world.situations:
        if not 0 <= s.day < cfg.days:
            bad("%s: day %d outside the life" % (s.sid, s.day))
        if not (0.0 <= s.A <= 1.0 and -1.0 <= s.V <= 1.0 and -1.0 <= s.mood <= 1.0):
            bad("%s: A, V or mood out of range" % s.sid)
        if world.mapping == "M1" and s.A > cfg.m1_cap_base + cfg.m1_cap_slope * s.feats.goal_rel + 1e-6:
            bad("%s: arousal above the relevance cap" % s.sid)
        for a in s.actors:
            if a not in ents or ents[a].kind != "person":
                bad("%s: unknown actor %s" % (s.sid, a))
        if s.place and s.place not in ents:
            bad("%s: unknown place" % s.sid)
        for fid in s.facts:
            host_count[fid] = host_count.get(fid, 0) + 1
            if fid not in facts:
                bad("%s hosts unknown fact %s" % (s.sid, fid))
    for fid in facts:
        if host_count.get(fid, 0) != 1:
            bad("fact %s is hosted %d times" % (fid, host_count.get(fid, 0)))
    if world.situations:
        sc = cfg.surprise_bits_scale
        nk = pearson([s.feats.surprise(sc) for s in world.situations], [s.feats.stakes for s in world.situations])
        if abs(nk) > cfg.max_corr_nk:
            bad("corr(surprise, stakes) = %.3f exceeds %.2f" % (nk, cfg.max_corr_nk))
        mean_a = sum(s.A for s in world.situations) / len(world.situations)
        if not 0.05 <= mean_a <= 0.5:
            bad("mean arousal %.3f is implausible" % mean_a)
    # facts
    for f in world.facts:
        spec = S.PREDICATES.get(f.pred)
        if spec is None:
            bad("%s: unknown predicate %s" % (f.fid, f.pred))
            continue
        if f.subj not in ents:
            bad("%s: unknown subject" % f.fid)
        if spec.obj_kind == "entity":
            if f.obj not in ents or ents[f.obj].kind != spec.vocab_id.split(":")[1]:
                bad("%s: object %s is not an entity of %s" % (f.fid, f.obj, spec.vocab_id))
        elif spec.vocab_id.startswith("pool:") and f.obj not in V.POOLS[spec.vocab_id.split(":")[1]]:
            bad("%s: object %r is not in %s" % (f.fid, f.obj, spec.vocab_id))
        if f.pred == "breakfast" and pb is not None and f.obj not in pb.values:
            bad("%s: dish outside the habit pool" % f.fid)
        if not 0.0 <= f.centrality <= 1.0 or not 0 <= f.vfrom < cfg.days:
            bad("%s: centrality or vfrom out of range" % f.fid)
        if f.supersedes and f.supersedes not in facts:
            bad("%s: supersedes unknown fact" % f.fid)
        if host_count.get(f.fid) == 1 and f.vfrom != world.host(f.fid).day:
            bad("%s: vfrom differs from the host day" % f.fid)
    for pred in S.CHAIN_PREDS:
        by_subj: dict[str, list[Fact]] = {}
        for f in world.facts:
            if f.pred == pred:
                by_subj.setdefault(f.subj, []).append(f)
        for chain in by_subj.values():
            chain.sort(key=lambda f: (f.vfrom, f.fid))
            for prev, nxt in zip(chain, chain[1:]):
                if nxt.supersedes not in (prev.fid, "") or (nxt.supersedes == "" and not ablated):
                    bad("%s: broken %s chain" % (nxt.fid, pred))
                if prev.vto != nxt.vfrom - 1 or prev.obj == nxt.obj:
                    bad("%s: chain versions must be contiguous and differ" % nxt.fid)
            if chain and chain[-1].vto is not None:
                bad("%s: the last %s version must be open" % (chain[-1].fid, pred))
    for s in world.situations:
        preds = [facts[fid].pred for fid in s.facts if fid in facts]
        if "car_colour" in preds and "companion" not in preds:
            bad("%s: a peripheral car colour without its central companion" % s.sid)
        if "vehicle_colour" in preds and "read_story" not in preds:
            bad("%s: a vehicle colour without the story that carries it" % s.sid)
        if "closing_time" in preds and "on_street" not in preds:
            bad("%s: a closing time without the shop's street" % s.sid)
    shops_seen: set = set()
    for f in world.facts:
        if f.pred == "closing_time":
            if f.subj in shops_seen:
                bad("%s: a shop's closing time is stated twice" % f.fid)
            shops_seen.add(f.subj)
    # lines
    mention_n: dict[str, list[str]] = {}
    per_day: dict[int, int] = {}
    for o in world.obs_specs:
        sit = sits.get(o.sid)
        if sit is None:
            bad("%s: unknown situation" % o.oid)
            continue
        per_day[o.day] = per_day.get(o.day, 0) + 1
        if not 0 <= o.t_obs < cfg.days * MINUTES_PER_DAY or o.t_obs < sit.t:
            bad("%s: time outside the life or before its situation" % o.oid)
        if not cfg.words_min <= o.target_len <= cfg.words_max:
            bad("%s: target_len outside the word range" % o.oid)
        if o.source and o.source not in ents:
            bad("%s: unknown source" % o.oid)
        fids_here = {m.fid for m in o.mentions}
        for m in o.mentions:
            f = facts.get(m.fid)
            if f is None or m.fid not in sit.facts:
                bad("%s mentions %s, which its situation does not host" % (o.oid, m.fid))
                continue
            mention_n.setdefault(m.fid, []).append(m.role)
            if m.role == "recall" and (o.day < f.vfrom or (
                    S.PREDICATES[f.pred].chain and f.vto is not None and o.day > f.vto)):
                bad("%s: recall of %s outside its validity" % (o.oid, m.fid))
            if m.role != "recall" and o.day < f.vfrom:
                bad("%s: states %s before it holds" % (o.oid, m.fid))
        if o.frame == "retell" and any(m.role != "recall" for m in o.mentions):
            bad("%s: a retelling may only recall" % o.oid)
        slot_fids = set()
        for sl in o.slots:
            if sl.fid:
                f = facts.get(sl.fid)
                slot_fids.add(sl.fid)
                if f is None or sl.fid not in fids_here or sl.value != _display_or_none(ents, f) \
                        or sl.name != S.slot_name(f.pred):
                    bad("%s: slot %s does not render its fact" % (o.oid, sl.name))
        if slot_fids != fids_here:
            bad("%s: mentions and slots disagree" % o.oid)
    for fid, f in facts.items():
        roles = mention_n.get(fid, [])
        if not any(r != "recall" for r in roles):
            bad("fact %s is never stated" % fid)
        if f.pred in ("breakfast", "relation", "closing_time"):
            stated = sum(1 for r in roles if r != "recall")
            if stated != 1 or (cfg.rehearsal == "off" and len(roles) != 1):
                bad("fact %s (%s) must be stated exactly once (retellings aside)" % (fid, f.pred))
    if not ablated and world.obs_specs:
        for d in range(cfg.days):
            if per_day.get(d, 0) < 1:
                bad("day %d has no line" % d)
        mean_obs = len(world.obs_specs) / cfg.days
        if not 0.8 * cfg.obs_per_day <= mean_obs <= 1.3 * cfg.obs_per_day:
            bad("mean %.2f lines a day is far from obs_per_day=%.1f" % (mean_obs, cfg.obs_per_day))
    if world.extra("hosting") is None:
        bad("extras lack the hosting record")
    return P


# ------------------------------------------------------------------------ delete_events


def delete_events(world: World, sids: Sequence[str]) -> World:
    """World without the given situations: their facts and all their lines disappear.

    Nothing is renumbered or rewritten except that a surviving fact whose predecessor was
    deleted gets ``supersedes = ''`` and the 'chains' list in the hosting record loses the
    deleted facts. ``ablated`` records the removed situation ids; an attached channel keeps the
    readings of the surviving lines."""
    ordered = list(dict.fromkeys(sids))
    known = {s.sid for s in world.situations}
    unknown = [s for s in ordered if s not in known]
    if unknown:
        raise ValueError("unknown situations: %s" % (unknown,))
    drop = set(ordered)
    drop_facts = {fid for s in world.situations if s.sid in drop for fid in s.facts}
    situations = tuple(s for s in world.situations if s.sid not in drop)
    facts = tuple(dataclasses.replace(f, supersedes="") if f.supersedes in drop_facts else f
                  for f in world.facts if f.fid not in drop_facts)
    obs_specs = tuple(o for o in world.obs_specs if o.sid not in drop)
    channel = None
    if world.channel is not None:
        channel = restrict_channel(world.channel, [o.oid for o in obs_specs])
    ablated = tuple(world.ablated) + tuple(s for s in ordered if s not in world.ablated)
    out = dataclasses.replace(world, situations=situations, facts=facts, obs_specs=obs_specs,
                              ablated=ablated, channel=channel)
    info = world.extra("hosting")
    if info is not None:
        info = dict(info)
        info["chains"] = {p: [fid for fid in fids if fid not in drop_facts]
                          for p, fids in info.get("chains", {}).items()}
        out = out.with_extra("hosting", info)
    return out
