"""Text for LifeSim: observation lines, question frames, a lexicon scan and a planted naive renderer.

What this module provides
-------------------------
* ``render(world, cfg, seed, partition)``: one ``Obs`` per ``ObsSpec`` (same order, same oid,
  same ``t_obs`` and channel). V1 (declarative diary voice: diary, note, article, log) and V2
  (informal chat voice: chat, dialogue). Every ``Slot.value`` appears verbatim (case-sensitive),
  as an exact canonical string, so evidence containment is machine-checkable
  (``missing_slots``). V3 (formal log or news) raises ``NotImplementedError``.
* Clause banks, template families and frames. Each channel kind has 24 skeleton families (12
  per partition); each scene has 40-80 frames per partition (a frame = skeleton x opener x
  joiner); head clauses, wrappers (told, read, update, retract, recall), adjuncts and padding
  come from banks split into disjoint ``dev`` and ``test`` halves. ``test`` seeds render only
  the ``test`` half (``render`` refuses anything else); a ``dev`` world may be rendered with the
  ``test`` banks as a renderer-OOD stress.
* Length: the line length is the spec's ``target_len`` (drawn at world build from one
  distribution independent of kind, arousal and evidence status). ``pad_to_length`` fills the
  gap with neutral clauses that each carry a small fact (a subject and a predicate, no digit,
  no pool word, no name, no affect word) so that short bodies are not recognisable as filler.
* Affect (``cfg.affect``): A0 renders zero affect words (``affect_scan`` is the lexicon scan
  that proves it); A1 adds affect phrases with a count independent of arousal; A2 correlates the
  count with the line's arousal (``cfg.r_aff``); A1 and A2 share one marginal count
  distribution. Polarity follows V. ``dramatic_decoy_share`` adds strong phrases to low-A lines.
* ``render_question(query, frame_partition)``: question text from ``Query.family``, ``cue``,
  ``ask``, ``options``, ``fmt`` and ``conf`` only (never the gold). At least 8 frames per family
  per partition (questions and requests, none of them an observation frame); every cue value appears
  verbatim; options and the 'CONF: 0-100' request are appended.
* ``render_planted_naive``: a deliberately flawed renderer (length and affect leak arousal and
  evidence status) kept as the positive-control fixture of the gates G-LEN and G-AFF.
  NEVER use it for a result. ``validate_paraphrase`` is the deterministic slot verifier of the
  renderer-OOD flash pass.

Conventions the other modules rely on
-------------------------------------
* Fact slots (``Slot.fid`` set) become head clauses by the slot name of the predicate:
  breakfast, lives_in, works_as, works_at, relation, story, vehicle_colour, decoy_colour (a
  second vehicle: van, bus, ...), car_colour, companion, closing_time, street, errand, visited;
  an unknown name gets the generic clause 'the <name> was <value>'. Context slots (no fid)
  become adjuncts (city, street, shop, person, story_kind, ...). A slot whose value is a
  substring of another slot's value (story_kind inside 'flood in Verdton') is not repeated.
  The subject of a clause comes from ``Fact.subj``: the narrator is 'I'; another entity is named
  (a shop closing at 18:00, a person who is my cousin). The teller (``ObsSpec.source``) is never
  named: the source kind (lived, told, read) is carried by wording alone.
* Question cue slots: ``date`` ('on D'), ``window_from`` and ``window_to`` ('between A and B'),
  ``relative_day`` and ``relative_window`` (verbatim); every other cue is a subject cue
  (story_kind, city, person, shop, street, errand, ...). Unknown cues are appended verbatim.
* ASSUMED parameters read with ``cfg.get(name, default)`` because ``TierCfg`` has no field for
  them yet (the integration step promotes them): ``aff_t1`` 0.25 and ``aff_t2`` 1.25 (latent
  thresholds for one and two affect phrases: P(>=1) 0.40, P(>=2) 0.11), ``aff_low_a`` 0.3 (a line
  is low-A, a candidate for a dramatic decoy, below this), ``aff_pos_floor`` 0.05 (smallest
  chance of the less likely polarity), ``pad_plain_p`` 0.75 and ``pad_plain_weight`` 0.15 (how
  strongly padding prefers clauses without a closing tail word such as 'that week').

Properties downstream code may rely on
--------------------------------------
* A line depends only on (seed, partition, its own spec, the facts and entities it cites,
  ``cfg``): deleting other events never changes it (byte-clean ablated worlds), in every affect
  mode. The A2 latent uses the config's target mean and SD of arousal, so the A2 affect count
  keeps A1's marginal only while a world's arousal follows those moments.
* ``ObsSpec.frame`` '' draws the core (the slot-bearing text) from the oid's stream; any other
  string draws it from that string's stream, so twin lines with the same frame, scene, channel
  and slots have a string-identical core and differ in their padding. A core is identical under
  A0 (the default); under A1/A2 a twin whose affect draw differs can differ in one closing tail
  word when the line is exactly 1-3 words short.
* The narrator is ``world.extra('narrator')`` or else the subject of the breakfast facts.
* A line whose core is longer than ``target_len`` is longer than its target (never cut): this is
  reported as ``LineParts.overflow`` and happens for about 1 line in 1000 at 30 words.
* Surface tells that remain are content, not wording: lines with more slots have fewer pad
  sentences, and names and digits sit only in slot-bearing lines (G-TELL reads the world).

What this module does NOT do
----------------------------
It calls no model and no network and reads no clock; it uses neither ``random`` nor ``hash()``.
It builds no world and draws no query (``world`` and ``queries`` do). It does not run the flash
paraphrase pass (only the slot verifier of that pass) and does not implement V3 or Polish. It
does not apply ``narrator_narrowing`` (omitting a peripheral slot is a structural choice made
when the specs are built; this module never drops a slot). It does not claim that its prose is
natural: the clause banks are small authored English, a proxy for natural language. It never
names a teller, never writes a date or a month into a line and no weekday except the fixed
'on Saturdays' of a closing-time remark (the record carries the time), and puts no digit into
padding. Lines of one partition use only that partition's clause banks.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .rng import Rng, stream
from .schema import CHANNELS, SCENE_NAMES, Obs, ObsSpec, Query, TierCfg, World, partition_of_seed
from .vocab import Vocab, norm, pool_vocab

__all__ = [
    "render", "render_parts", "render_all_parts", "render_v3", "render_question", "pad_to_length", "affect_scan", "AFFECT_LEXICON",
    "missing_slots", "word_count", "render_planted_naive", "validate_paraphrase", "LineParts",
    "BANKS", "bank_strings", "template_family_count", "frame_count", "frames_of",
    "question_stems", "pad_clause_set", "STYLE_OF_CHANNEL", "PAD_LENGTHS",
]

PARTS = ("dev", "test")

#: Voice of each channel kind: V1 declarative diary voice, V2 informal chat voice.
STYLE_OF_CHANNEL = {"diary": "V1", "note": "V1", "article": "V1", "log": "V1",
                    "chat": "V2", "dialogue": "V2"}

# ------------------------------------------------------------------------ bank machinery

#: Every authored bank by name; each holds the two disjoint halves {"dev": ..., "test": ...}.
BANKS: dict = {}


_ASSIGNED: dict = {}  # authored string -> its partition (one string never sits in both)


def _B(name: str, text: str) -> dict:
    """Register a bank from lines of text. New entries alternate between dev and test; a string
    that an earlier bank already holds keeps that bank's partition, so the halves stay disjoint
    across the whole module."""
    items = tuple(ln.strip() for ln in text.strip().split("\n") if ln.strip())
    if len(set(items)) != len(items):
        raise ValueError("bank %s has duplicate entries" % name)
    dev: list = []
    test: list = []
    toggle = 0
    for it in items:
        part = _ASSIGNED.get(it)
        if part is None:
            part = "dev" if toggle % 2 == 0 else "test"
            toggle += 1
            _ASSIGNED[it] = part
        (dev if part == "dev" else test).append(it)
    halves = {"dev": tuple(dev), "test": tuple(test)}
    BANKS[name] = halves
    return halves


def bank_strings(partition: str) -> frozenset:
    """Every authored template string of a partition (for disjointness checks)."""
    out: set = set()
    for halves in BANKS.values():
        out.update(halves[partition])
    return frozenset(out)


# ------------------------------------------------------------------------ text segments

Seg = tuple  # (text, protected): protected segments (slot values, names) are never altered

_PH = re.compile(r"\{(\w+)\}")


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def _fill(tpl: str, vals: dict) -> list:
    """Split a template into segments; vals maps a placeholder to a str (literal), a
    (text, True) pair (protected) or a list of segments."""
    segs: list = []
    pos = 0
    for m in _PH.finditer(tpl):
        if m.start() > pos:
            segs.append((tpl[pos:m.start()], False))
        v = vals[m.group(1)]
        if isinstance(v, str):
            segs.append((v, False))
        elif isinstance(v, tuple):
            segs.append(v)
        else:
            segs.extend(v)
        pos = m.end()
    if pos < len(tpl):
        segs.append((tpl[pos:], False))
    return [s for s in segs if s[0]]


def _text(segs: Iterable) -> str:
    return "".join(s[0] for s in segs)


def _cap(segs: list) -> list:
    """Capitalise the first character if it is literal (a slot value keeps its own case)."""
    if segs and not segs[0][1] and segs[0][0]:
        t = segs[0][0]
        return [(t[0].upper() + t[1:], False)] + segs[1:]
    return segs


def _lower(segs: list) -> list:
    """Lower-case the first literal character unless it starts 'I' (informal voice)."""
    if segs and not segs[0][1] and segs[0][0]:
        t = segs[0][0]
        if t[0] == "I" and (len(t) == 1 or not t[1].isalpha() or t[1] == "'"):
            return segs
        return [(t[0].lower() + t[1:], False)] + segs[1:]
    return segs


def word_count(text: str) -> int:
    """Whitespace words (the arena's unit)."""
    return len(text.split())


# ------------------------------------------------------------------ head clause banks
# Placeholders: {S} subject (I or a name), {s} verb suffix, {am} {have} {do}, {v} the value,
# {a_v} 'a'/'an' + value, {n} vehicle noun, {on_st} optional ' on <street>'.
# Templates without {S} are used only when the narrator is the subject.

_B("head.dish.V1", """
{S} had {v} for breakfast
breakfast was {v}
{S} ate {v} for breakfast
for breakfast {S} made {v}
{S} started the day with {v}
my breakfast was {v}
what {S} had for breakfast was {v}
{S} ordered {v} for breakfast
""")
_B("head.dish.V2", """
had {v} for breakfast
breakfast: {v}
just had {v} for breakfast
made myself {v} this morning
{S} ate {v} this morning
so breakfast was {v}
{S} went with {v} for breakfast
ate {v} for breakfast btw
""")
_B("head.colour.V1", """
{a_v} {n} was parked outside
the {n} was {v}
there was {a_v} {n} nearby
{a_v} {n} stood by the kerb
the {n} outside was {v}
I noticed {a_v} {n}
{a_v} {n} drove past
the {n} beside it was {v}
""")
_B("head.colour.V2", """
saw {a_v} {n} out front
the {n} was {v}
there was {a_v} {n} outside
{a_v} {n} pulled up
{a_v} {n} was blocking the road
the {n} there was {v}
spotted {a_v} {n}
{a_v} {n} sat across the road
""")
_B("head.colour_read.V1", """
{a_v} {n} was among the vehicles
{a_v} {n} was seen at the scene
one witness described {a_v} {n}
the report mentioned {a_v} {n}
photos showed {a_v} {n}
{a_v} {n} appeared in the pictures
the {n} involved was {v}
a witness recalled {a_v} {n}
""")
_B("head.colour_read.V2", """
{a_v} {n} was among the vehicles
the {n} in the pictures was {v}
a witness saw {a_v} {n}
{a_v} {n} was at the scene
photos showed {a_v} {n}
the {n} involved was {v}
{a_v} {n} showed up in the report
they mention {a_v} {n}
""")
_B("head.job.V1", """
{S} work{s} as {a_v}
{S} {am} {a_v} by trade
{S} became {a_v}
{S} {have} a job as {a_v}
{S} trained as {a_v}
{S} earn{s} a living as {a_v}
{S} took a post as {a_v}
{S} {am} employed as {a_v}
""")
_B("head.job.V2", """
{S} work{s} as {a_v}
I'm {a_v} these days
{S} {am} {a_v} by trade
work as {a_v}
{S} {have} a job as {a_v}
{S} became {a_v}
job-wise I'm {a_v}
{S} trained as {a_v}
""")
_B("upd.job.V1", """
{S} now work{s} as {a_v}
{S} switched careers and became {a_v}
{S} {have} started work as {a_v}
{S} took up work as {a_v}
{S} moved into work as {a_v}
{S} {have} changed jobs and work{s} as {a_v}
""")
_B("upd.job.V2", """
{S} now work{s} as {a_v}
switched jobs, now {a_v}
{S} {have} started as {a_v}
new job as {a_v}
{S} took up work as {a_v}
changed careers and now {a_v}
""")
_B("head.home.V1", """
{S} live{s} in {v}
{S} {have} a flat in {v}
{S} settled in {v}
{S} call{s} {v} home
{S} stay{s} in {v}
{S} {am} based in {v}
{S} reside{s} in {v}
{S} {am} living in {v}
""")
_B("head.home.V2", """
live in {v}
{S} live{s} in {v}
{S} {have} a flat in {v}
based in {v}
{S} {am} in {v}
{S} stay{s} in {v}
home is {v}
{S} settled in {v}
""")
_B("upd.home.V1", """
{S} moved to {v}
{S} now live{s} in {v}
{S} relocated to {v}
{S} {have} moved to {v}
{S} packed up and moved to {v}
{S} settled into a new place in {v}
""")
_B("upd.home.V2", """
moved to {v}
{S} now live{s} in {v}
{S} {have} moved to {v}
now based in {v}
{S} relocated to {v}
new place in {v}
""")
_B("head.trip.V1", """
{S} visited {v}
{S} spent a few days in {v}
{S} travelled to {v}
{S} stopped over in {v}
{S} took a trip to {v}
{S} was in {v} for the weekend
{S} went to {v}
{S} spent time in {v}
""")
_B("head.trip.V2", """
went to {v}
visited {v}
was in {v} for a bit
{S} headed to {v}
{S} took a trip to {v}
spent a few days in {v}
{S} travelled to {v}
stopped in {v}
""")
_B("head.org_job.V1", """
{S} work{s} at {v}
{S} {have} a post at {v}
{S} {am} employed by {v}
{S} joined {v}
{S} {am} on the staff at {v}
{S} turn{s} up at {v} each day
""")
_B("head.org_job.V2", """
work at {v}
{S} work{s} at {v}
{S} joined {v}
{S} {have} a post at {v}
based at {v}
{S} {am} employed by {v}
""")
_B("head.errand.V1", """
{S} went to the {v}
{S} had an appointment at the {v}
{S} stopped by the {v}
{S} spent an hour at the {v}
{S} visited the {v}
{S} dropped in at the {v}
{S} was at the {v} in the morning
{S} made a trip to the {v}
""")
_B("head.errand.V2", """
went to the {v}
stopped by the {v}
had to go to the {v}
{S} was at the {v}
popped into the {v}
{S} went to the {v}
{S} visited the {v}
{S} made it to the {v}
""")
_B("head.count.V1", """
{S} counted {v} visits so far
that made {v} visits
{S} {have} gone {v} times in all
the tally stood at {v}
the running total was {v}
{S} made {v} trips in total
""")
_B("head.count.V2", """
that's {v} visits now
total so far: {v}
{v} visits so far
tally: {v}
running total is {v}
{S} made {v} trips
""")
_B("head.story.V1", """
there was {a_v}
{a_v} took place
{a_v} made the news
{a_v} was reported
the paper covered {a_v}
the main item was {a_v}
{a_v} was in the headlines
much of the coverage was about {a_v}
""")
_B("head.story.V2", """
there was {a_v}
{a_v} happened
{a_v} made the front page
{a_v} was all over the news
there was news of {a_v}
{a_v} was reported
the news was about {a_v}
{a_v} got covered
""")
_B("head.relation.V1", """
{S} is my {v}
my {v} is {S}
{S} happens to be my {v}
{S} is, in fact, my {v}
I should say that {S} is my {v}
{S} is my {v}, by the way
""")
_B("head.relation.V2", """
{S} is my {v}
my {v} is {S}
btw {S} is my {v}
fyi {S} is my {v}
{S} is actually my {v}
{S}'s my {v}
""")
_B("head.relation_alone.V1", """
{S} spoke with my {v}
my {v} called
my {v} came by
{S} saw my {v}
{S} wrote to my {v}
{S} had lunch with my {v}
""")
_B("head.relation_alone.V2", """
talked to my {v}
my {v} called
my {v} came by
saw my {v}
wrote to my {v}
{S} met my {v}
""")
_B("head.time.V1", """
{S}{on_st} closes at {v} on Saturdays
{S}{on_st} shuts at {v} on Saturdays
on Saturdays {S}{on_st} closes at {v}
closing time at {S}{on_st} is {v} on Saturdays
{S}{on_st} stays open until {v} on Saturdays
{S}{on_st} locks up at {v} on Saturdays
""")
_B("head.time.V2", """
{S}{on_st} closes at {v} on Saturdays
{S}{on_st} shuts at {v} on Saturdays
closing time on Saturdays at {S}{on_st} is {v}
{S}{on_st} locks up at {v} on Saturdays
{S}{on_st} is open until {v} on Saturdays
on Saturdays {S}{on_st} closes at {v}
""")
_B("head.street_of.V1", """
{S} is on {v}
{S} stands on {v}
you will find {S} on {v}
{S} sits on {v}
{S} is located on {v}
{S} lies on {v}
""")
_B("head.street_of.V2", """
{S} is on {v}
{S} sits on {v}
{S} stands on {v}
you find {S} on {v}
{S} is located on {v}
{S} is down on {v}
""")
_B("head.companion.V1", """
{S} was with {v}
{v} was there with {S}
{S} spent the time with {v}
{S} had {v} for company
{S} was together with {v}
{S} was accompanied by {v}
""")
_B("head.companion.V2", """
was with {v}
{S} was with {v}
{v} was there
spent the time with {v}
{S} was together with {v}
had {v} along
""")
_B("head.other.V1", """
the {label} was {v}
the {label} turned out to be {v}
{label}: {v}
the {label} came to {v}
""")
_B("head.other.V2", """
the {label} was {v}
{label} is {v}
the {label} is {v}
{label} = {v}
for the record the {label} was {v}
the {label} turned out as {v}
""")
_B("head.lone_person.V1", """
{S} met {v}
{S} ran into {v}
{S} saw {v}
{S} talked to {v}
{S} bumped into {v}
{S} spoke with {v}
{S} passed {v} in the street
{S} had a call with {v}
""")
_B("head.lone_person.V2", """
met {v}
ran into {v}
talked to {v}
saw {v} today
caught up with {v}
{S} met {v}
{S} spoke with {v}
{S} bumped into {v}
""")
_B("head.lone_arg.V1", """
{S} was {ad}
{S} spent some time {ad}
{S} ended up {ad}
{S} stopped {ad}
""")
_B("head.lone_arg.V2", """
was {ad}
ended up {ad}
{S} spent some time {ad}
{S} stopped {ad}
{S} showed up {ad}
turned up {ad}
{S} spent a while {ad}
""")

# adjuncts for context slots: {v} is the value
_B("adj.person.V1", """
with {v}
alongside {v}
together with {v}
in company with {v}
""")
_B("adj.person.V2", """
with {v}
along with {v}
together with {v}
w/ {v}
accompanied by {v}
joined by {v}
plus {v}
""")
_B("adj.city.V1", """
in {v}
over in {v}
around {v}
near {v}
""")
_B("adj.city.V2", """
in {v}
over in {v}
around {v}
down in {v}
out in {v}
up in {v}
somewhere in {v}
""")
_B("adj.street.V1", """
on {v}
along {v}
close to {v}
off {v}
""")
_B("adj.street.V2", """
on {v}
along {v}
off {v}
up on {v}
""")
_B("adj.shop.V1", """
at {v}
outside {v}
near {v}
by {v}
""")
_B("adj.shop.V2", """
at {v}
outside {v}
near {v}
by {v}
""")
_B("adj.story_kind.V1", """
during the {v}
amid the {v}
after the {v}
around the {v}
""")
_B("adj.story_kind.V2", """
during the {v}
amid the {v}
after the {v}
around the {v}
""")
_B("adj.generic.V1", """
regarding {v}
concerning {v}
about {v}
relating to {v}
""")
_B("adj.generic.V2", """
re {v}
as for {v}
on the subject of {v}
with regard to {v}
""")

# wrappers around a finished clause {c}
_B("wrap.told.V1", """
I was told that {c}
someone mentioned that {c}
I heard that {c}
word is that {c}
I was informed that {c}
it was said that {c}
""")
_B("wrap.told.V2", """
heard that {c}
someone said {c}
apparently {c}
word is {c}
got told that {c}
was told {c}
""")
_B("wrap.read.V1", """
I read that {c}
the paper said that {c}
according to the article, {c}
the news reported that {c}
an article noted that {c}
I saw in the paper that {c}
""")
_B("wrap.read.V2", """
read that {c}
the article said {c}
saw in the news that {c}
news says {c}
per the article, {c}
paper says {c}
""")
_B("wrap.update.V1", """
these days {c}
by now {c}
as of now {c}
nowadays {c}
since then {c}
at this point {c}
""")
_B("wrap.update.V2", """
now {c}
these days {c}
as of now {c}
by now {c}
update: {c}
newest: {c}
""")
_B("wrap.retract.V1", """
it turns out it is not true that {c}
I was wrong earlier, it is not the case that {c}
scratch that, it is not true that {c}
correction: it is not true that {c}
earlier I said that {c}, but that was wrong
I take back that {c}
""")
_B("wrap.retract.V2", """
scratch that, not true that {c}
correction: not true that {c}
ignore what I said, it's not true that {c}
take back that {c}
not true that {c}, my mistake
retracting: {c}
""")
_B("wrap.recall.V1", """
I told someone again that {c}
I mentioned once more that {c}
I went over it again: {c}
I repeated that {c}
I brought it up again and said that {c}
I retold it: {c}
""")
_B("wrap.recall.V2", """
told someone again that {c}
mentioned again that {c}
went over it again: {c}
repeated that {c}
brought it up again: {c}
retold it: {c}
""")
_B("wrap.teller.V1", """
{t} told me that {c}
{t} said that {c}
according to {t}, {c}
{t} mentioned that {c}
""")
_B("wrap.teller.V2", """
{t} told me {c}
{t} said {c}
per {t}, {c}
{t} mentioned {c}
""")


# ------------------------------------------------------------- openers, joiners, adjusters

_SCENE_OPEN_TEXT = {
    "routine": """
This morning
At breakfast
Before leaving the house
Over the first hour of the day
At the kitchen table
Early on
As the day began
While the kettle boiled
Before work
In the first quiet hour
""",
    "minor": """
Earlier today
On the way into town
Around midday
Between other things
During a short outing
Sometime after lunch
On a small errand
In passing
Later that afternoon
Out and about
""",
    "major": """
Today something happened
News from today
A day to record
The main event of the day
Today brought a turn
One thing stands out from today
For the record
Looking back on today
The day turned on one thing
Worth writing down
""",
    "move": """
On the housing front
About where I live
Regarding the flat
As for my address
On the move
In moving matters
Concerning my home
Regarding the move
About my place
On the subject of my address
""",
    "health": """
On the health front
At the clinic
Regarding my check-up
For the record, health-wise
On the medical side
At the surgery
In health matters
About my appointment
Concerning my health
Medically speaking
""",
    "purchase": """
Shopping note
On the purchase front
Out spending
A buying note
On a shopping trip
Regarding a purchase
Concerning something bought
On the shopping side
While shopping
About a purchase
""",
    "remark": """
Heard in passing
Someone said something
A remark worth keeping
Overheard today
A small piece of information
Picked up today
Word from today
One thing I learned
A passing comment
A detail to remember
""",
    "trip": """
On the trip
Away from home
While travelling
During the journey
On the road
Away for a few days
On a short break
Out of town
At my destination
Along the way
""",
    "article": """
In the paper
Reading the news
From today's reading
In the local news
A story I read
On the news pages
From the papers
Reading note
In today's paper
News I came across
""",
}
for _scene, _txt in _SCENE_OPEN_TEXT.items():
    _B("open.scene." + _scene, _txt)
if set(_SCENE_OPEN_TEXT) != set(SCENE_NAMES):
    raise ValueError("every scene needs an opener bank")

_B("open.kind.diary", """
Dear diary
Diary entry
Writing this down
Later on
For the day
Evening entry
My notes
A line for today
To remember
Short entry
Logging the day
Put on paper
""")
_B("open.kind.note", """
Note
Noted
Jotted down
For the record
To remember
Writing this down
Quick note
Memo
On file
Kept for later
Put on paper
Short entry
""")
_B("open.kind.log", """
Logged
Entry
Record
Log entry
Filed
Registered
Logbook
Daily log
Item logged
Observed
Tally entry
Recorded
""")
_B("open.kind.article", """
In the paper
Local news
News item
From the paper
Read today
Front page item
Page three
In the news
Press item
News report
Newspaper item
Report
""")
_B("open.kind.chat", """
so
ok so
btw
oh and
quick update
fyi
also
right so
update
by the way
one more thing
just so you know
""")
_B("open.kind.dialogue", """
Well
Listen
You know
Look
Right
As it happens
So then
Actually
Come to think of it
By the way
Oh yes
Just so you know
""")

#: Joiners: 'inline token|sentence start' pairs. A token starting with , or ; attaches to the
#: previous clause; any other token is set between spaces.
_B("join.V1", """
;|Then
, and|Also
, then|After that
, while|Meanwhile
;|Later
, and|Next
, then|Besides
, while|Separately
""")
_B("join.V2", """
and|also
, then|then
+|and
, plus|plus
and|and then
, then|next
+|also
, plus|then
""")

# neutral tail words of 1, 2 and 3 words (they end a clause: 'went to the gym that day')
_B("adj.w1", """
today
earlier
then
later
""")
_B("adj.w2", """
that day
that time
that week
at home
""")
_B("adj.w3", """
at that time
just after noon
in the end
before the evening
""")
_B("tag.dialogue", """
she said
he said
they said
I said
someone said
came the reply
""")

# ------------------------------------------------------------------ neutral padding facts
# Subject + predicate pairs per domain. A pad clause is 'Subject predicate [tail word(s)].' and
# carries one small fact. No digit, no pool word, no name, no affect word (checked by tests).

_PAD_DOMAINS = {
    "weather": ("""
the wind
the rain
the fog
the haze
a light drizzle
the clouds
the breeze
the sun
""", """
picked up after lunch
eased off by noon
came and went
held off until evening
lingered all day
returned in the evening
faded by the afternoon
changed towards dusk
"""),
    "transit": ("""
the tram
the platform
the late bus
the ticket queue
the morning train
the crossing
the ring road
the footbridge
""", """
stayed crowded until the last stop
kept moving slowly
emptied out near the terminal
filled up fast
looked busy at noon
stayed quiet for a while
cleared by the afternoon
got busier after lunch
"""),
    "street": ("""
the pavement
the lamp posts
the shutters
the corner stall
the cobbles
the benches
the fountain
the old wall
""", """
looked freshly cleaned
stayed quiet for hours
gleamed after the rain
sat half in shade
caught the afternoon light
stood unchanged since spring
had been repaired overnight
needed a fresh coat of paint
"""),
    "home": ("""
the heating
the kettle
the radio
the washing machine
the hallway light
the oven timer
the clock
the fridge
""", """
stayed on all morning
needed attention
kept humming quietly
rattled for a while
ran without a problem
sat unused for hours
made a new noise
stopped for a moment
"""),
    "objects": ("""
the umbrella
my keys
the paper bag
a loose button
the bike chain
the parcel
my scarf
the spare charger
""", """
stayed in the hall
ended up under the table
went missing for an hour
turned up in a coat pocket
sat by the door all day
got left behind
travelled in my bag
waited on the shelf
"""),
    "sounds": ("""
a dog nearby
the church bells
a distant drill
the lift
the builders next door
the delivery van
the sweeper
the radio next door
""", """
went quiet after lunch
kept going through the afternoon
started up early
stopped for a while
carried on for an hour
came back later
paused for a moment
moved on around noon
"""),
    "light": ("""
the light
the shadows
the afternoon
the morning
the day
the hour
the evening
the sunset
""", """
faded early
passed quickly
dragged on
felt long
went by unnoticed
shifted slowly
ended early
started late
"""),
    "belongings": ("""
my shoes
my coat
my bag
my jacket
my phone
my watch
my sleeves
my pockets
""", """
got damp on the way
stayed dry
needed a quick wipe
felt heavy by the end
sat on the chair
rested by the door
stayed unused
dried near the radiator
"""),
}
for _dom, (_subj, _pred) in _PAD_DOMAINS.items():
    _B("pad.subj." + _dom, _subj)
    _B("pad.pred." + _dom, _pred)


def _pad_base(partition: str) -> tuple:
    """(subject, predicate, domain, n_words) for every pad clause base of a partition."""
    out = []
    for dom in _PAD_DOMAINS:
        for s in BANKS["pad.subj." + dom][partition]:
            for p in BANKS["pad.pred." + dom][partition]:
                out.append((s, p, dom, len(s.split()) + len(p.split())))
    return tuple(out)


_PAD_BASE = {p: _pad_base(p) for p in PARTS}
#: Pad clause lengths (words, final tail word(s) included) that every partition can form.
PAD_LENGTHS = tuple(range(4, 13))
_TAIL_WORDS = {1: "adj.w1", 2: "adj.w2", 3: "adj.w3"}

# --------------------------------------------------------------------- affect lexicon

_AFFECT_WORDS = """
happy glad pleased delighted thrilled overjoyed elated ecstatic relieved proud grateful cheerful
amused excited joyful joy sad unhappy upset angry furious livid annoyed irritated frustrated
anxious nervous worried uneasy afraid scared frightened terrified horrified shocked stunned
shaken devastated heartbroken miserable gutted distressed panicked panic dread dreadful awful
terrible horrible wonderful amazing fantastic brilliant excellent lovely nasty unpleasant
pleasant delightful enjoyed hated loved lonely ashamed embarrassed overwhelmed stressed tense
restless agitated alarmed thrilling frightening scary exciting
""".split()
_AFFECT_PHRASES = (
    "heart was pounding", "heart pounded", "hands were shaking", "could not believe",
    "could not stop shaking", "over the moon", "on edge", "felt sick", "burst into tears",
    "tears of joy", "lost for words", "could not stop smiling", "cannot stop smiling",
)
AFFECT_LEXICON = tuple(sorted(set(_AFFECT_WORDS) | set(_AFFECT_PHRASES)))
_AFFECT_VOCAB = Vocab("affect", AFFECT_LEXICON)


def affect_scan(text: str) -> list:
    """Affect lexicon entries found in ``text`` (longest match, non-overlapping, with repeats).

    Under A0 every rendered line must give ``[]``; under A1/A2 each inserted affect phrase gives
    exactly one entry, so ``len(affect_scan(text))`` is the number of affect phrases."""
    return [canon for _, _, canon in _AFFECT_VOCAB.spans(text)]


_B("aff.pos_mild", """
I felt pleased about it
that left me glad
it made me happy
I was quietly cheerful
I felt grateful for it
it left me amused
I felt proud of that
that made me relieved
""")
_B("aff.pos_strong", """
I was absolutely thrilled
I was over the moon
I felt overjoyed
I was ecstatic
I was delighted beyond words
I could not stop smiling
tears of joy ran down my face
I felt elated
""")
_B("aff.neg_mild", """
I felt uneasy about it
that left me annoyed
I was a little worried
it made me nervous
I felt irritated
that left me upset
I felt a bit sad
I was slightly anxious
""")
_B("aff.neg_strong", """
I was terrified
my heart was pounding
I was absolutely furious
I felt devastated
I could not stop shaking
I was horrified
I felt completely panicked
my hands were shaking
""")


_B("noun.vehicle", """
van
bus
lorry
taxi
truck
minibus
coach
tractor
""")

# ----------------------------------------------------------- skeletons and frames


def _skeletons() -> dict:
    """24 template families per channel kind, 12 per partition: (opener mode 0 none / 1 front /
    2 label, order mode 0 given / 1 reversed or adjunct-fronted, tail 0/1, split 0 one sentence /
    1 one sentence per clause)."""
    combos = [(o, w, t, s) for o in (0, 1, 2) for w in (0, 1) for t in (0, 1) for s in (0, 1)]
    out = {}
    for kind in CHANNELS:
        items = list(combos)
        stream(0, "skeletons", kind).shuffle(items)
        out[kind] = {"dev": tuple(items[0::2]), "test": tuple(items[1::2])}
    return out


SKELETONS = _skeletons()
_N_SKEL, _N_OPEN, _N_JOIN = 12, 5, 4
_FRAME_CACHE: dict = {}


def template_family_count(kind: str, partition: str) -> int:
    """Number of template families (skeletons) of a channel kind in a partition."""
    return len(SKELETONS[kind][partition])


def frames_of(scene: str, partition: str) -> tuple:
    """The frames of a scene in a partition: distinct (skeleton, opener, joiner) index triples,
    40 to 80 of them (40 + 5 x the scene's position), drawn once from the full 240-triple space."""
    key = (scene, partition)
    if key not in _FRAME_CACHE:
        space = [(a, b, c) for a in range(_N_SKEL) for b in range(_N_OPEN) for c in range(_N_JOIN)]
        n = 40 + 5 * SCENE_NAMES.index(scene)
        _FRAME_CACHE[key] = tuple(sorted(stream(0, "frames", partition, scene).sample(space, n)))
    return _FRAME_CACHE[key]


def frame_count(scene: str, partition: str) -> int:
    return len(frames_of(scene, partition))


# ------------------------------------------------------------------------- padding

_PAD_BY_LEN: dict = {p: {} for p in PARTS}
for _p in PARTS:
    for _s, _pr, _dom, _b in _PAD_BASE[_p]:
        for _tl in (0, 1, 2, 3):
            _PAD_BY_LEN[_p].setdefault(_b + _tl, []).append((_s, _pr, _tl))
    for _L in PAD_LENGTHS:
        if _L not in _PAD_BY_LEN[_p]:
            raise ValueError("pad bank of %s cannot form a clause of %d words" % (_p, _L))


PAD_PLAIN_P = 0.75  # ASSUMED (cfg extra pad_plain_p): chance of preferring a clause without a tail word
PAD_PLAIN_WEIGHT = 0.15  # ASSUMED (cfg extra pad_plain_weight): weight of a length with no plain clause


def _pad_clause(rng: Rng, length: int, partition: str, used: set | None = None,
                plain_p: float = PAD_PLAIN_P) -> str:
    """One pad clause of exactly ``length`` words. A clause without a tail word is preferred
    (with chance ``plain_p``); a clause or a subject already ``used`` in the line is avoided."""
    rows = _PAD_BY_LEN[partition][length]
    if used:
        fresh = [r for r in rows if r[0] not in used and (r[0], r[1]) not in used]
        rows = fresh or rows
    plain = [r for r in rows if r[2] == 0]
    if plain and (len(plain) == len(rows) or rng.chance(plain_p)):
        rows = plain
    s, p, tl = rows[rng.below(len(rows))]
    if used is not None:
        used.add(s)
        used.add((s, p))
    words = "%s %s" % (s, p)
    if tl:
        words += " " + rng.choice(BANKS[_TAIL_WORDS[tl]][partition])
    return words


def _plan_pad(rng: Rng, remaining: int, partition: str, plain_w: float = PAD_PLAIN_WEIGHT) -> list:
    """Clause lengths that sum to ``remaining`` and never leave a gap of 1-3 words. Lengths for
    which a clause without a tail word exists are favoured, so most pad clauses read plainly."""
    plain = {L for L, rows in _PAD_BY_LEN[partition].items() if any(r[2] == 0 for r in rows)}
    out = []
    while remaining > 0:
        opts = [L for L in PAD_LENGTHS if L <= remaining and (remaining - L == 0 or remaining - L >= 4)]
        L = opts[rng.weighted_by([1.0 if x in plain else plain_w for x in opts])]
        out.append(L)
        remaining -= L
    return out


def pad_to_length(rng: Rng, n_words: int, partition: str) -> list:
    """Neutral clauses (each one small fact, ending in a full stop) totalling exactly ``n_words``
    words. 0 gives []; 1-3 words cannot form a clause and raise ValueError (the renderer closes
    such a gap with a tail word on the last core clause instead)."""
    if n_words < 0 or 1 <= n_words <= 3:
        raise ValueError("pad_to_length needs 0 or at least 4 words, got %d" % n_words)
    if partition not in PARTS:
        raise ValueError("partition must be 'dev' or 'test', got %r" % (partition,))
    return [_cap([(_pad_clause(rng, L, partition), False)])[0][0] + "." for L in _plan_pad(rng, n_words, partition)]


def pad_clause_set(partition: str) -> frozenset:
    """Every pad clause the renderer can emit in a partition (capitalised, with its full stop)."""
    out = set()
    for length, rows in _PAD_BY_LEN[partition].items():
        for s, p, tl in rows:
            base = "%s %s" % (s, p)
            tails = BANKS[_TAIL_WORDS[tl]][partition] if tl else ("",)
            for t in tails:
                txt = (base + (" " + t if t else "")).strip()
                out.add(txt[0].upper() + txt[1:] + ".")
    return frozenset(out)


# ----------------------------------------------------------------------- the context

_FACT_GROUP = {
    "breakfast": "dish", "lives_in": "home", "works_as": "job", "works_at": "org_job",
    "relation": "relation", "story": "story", "vehicle_colour": "colour", "car_colour": "colour",
    "decoy_colour": "colour", "companion": "companion", "closing_time": "time",
    "street": "street_of", "errand": "errand", "visited": "trip", "visit_count": "count",
}
_CTX_GROUP = {"city": "city", "street": "street", "shop": "shop", "person": "person",
              "companion": "person", "story_kind": "story_kind", "org": "shop", "place": "shop"}


@dataclass
class _Item:
    name: str
    value: str
    fid: str
    group: str
    head: bool
    role: str
    src: str
    subj: str  # display name of a non-narrator subject, else ''


class _Ctx:
    """Per-world lookups shared by all lines of one render call."""

    def __init__(self, world: World, cfg: TierCfg, seed: int, partition: str) -> None:
        self.world, self.cfg, self.seed, self.partition = world, cfg, seed, partition
        self.sit = {s.sid: s for s in world.situations}
        nid = world.extra("narrator", "")
        if not isinstance(nid, str):
            nid = ""
        if not nid:
            for f in world.facts:
                if f.pred == "breakfast":
                    nid = f.subj
                    break
        self.narrator_id = nid
        self.card_name = world.card.name
        specs = world.obs_specs
        retell = cfg.retell_a_factor
        la = []
        for o in specs:
            s = self.sit.get(o.sid)
            a = s.A if s is not None else 0.0
            if o.mentions and all(m.role == "recall" for m in o.mentions):
                a *= retell
            la.append(a)
        self.line_a = {o.oid: a for o, a in zip(specs, la)}

    def subject(self, fid: str) -> str:
        """Display name of the subject of a fact when it is not the narrator, else ''."""
        try:
            f = self.world.fact(fid)
        except KeyError:
            return ""
        if f.subj in ("", self.narrator_id):
            return ""
        try:
            e = self.world.entity(f.subj)
        except KeyError:
            return ""
        if e.name == self.card_name or e.kind not in ("person", "shop", "org", "pet"):
            return ""
        return e.name

    def fact_src(self, fid: str, default: str) -> str:
        try:
            return self.world.fact(fid).src
        except KeyError:
            return default


def _items(ctx: _Ctx, spec: ObsSpec) -> list:
    roles = {m.fid: m.role for m in spec.mentions}
    default_src = "read" if spec.channel == "article" else "lived"
    slots = list(spec.slots)
    out = []
    for i, sl in enumerate(slots):
        covered = False
        for j, o in enumerate(slots):
            if j == i:
                continue
            if sl.value == o.value and j < i:
                covered = True
            elif sl.value != o.value and sl.value in o.value:
                covered = True
        if covered:
            continue
        if sl.fid:
            group = _FACT_GROUP.get(sl.name)
            if group is None:
                group = "colour" if sl.name.endswith(("_colour", "_color")) else "other"
            out.append(_Item(sl.name, sl.value, sl.fid, group, True, roles.get(sl.fid, "assert"),
                             ctx.fact_src(sl.fid, default_src), ctx.subject(sl.fid)))
        else:
            out.append(_Item(sl.name, sl.value, "", _CTX_GROUP.get(sl.name, "generic"), False,
                             "assert", default_src, ""))
    return out


# --------------------------------------------------------------- clause construction


def _pick(rng: Rng, bank_name: str, partition: str, compact: bool, need_subject: bool = False):
    cands = list(BANKS[bank_name][partition])
    if need_subject:
        keep = [t for t in cands if "{S}" in t]
        cands = keep or cands
    if compact:
        cands.sort(key=lambda t: (len(t.split()), t))
        cands = cands[:2]
    return cands[rng.below(len(cands))]


def _subject_vals(subj: str) -> dict:
    if subj:
        return {"S": (subj, True), "s": "s", "am": "is", "have": "has", "do": "does"}
    return {"S": "I", "s": "", "am": "am", "have": "have", "do": "do"}


def _val_vals(item: _Item, noun: str) -> dict:
    return {"v": (item.value, True),
            "a_v": [(_article(item.value) + " ", False), (item.value, True)],
            "n": noun, "label": item.name.replace("_", " ")}


def _head_clause(ctx: _Ctx, item: _Item, style: str, rng: Rng, compact: bool, on_st: list,
                 noun: str) -> list:
    g, part = item.group, ctx.partition
    if g == "colour" and (item.src == "read"):
        name = "head.colour_read." + style
    elif item.role == "update" and ("upd.%s.%s" % (g, style)) in BANKS:
        name = "upd.%s.%s" % (g, style)
    elif g == "relation" and not item.subj:
        name = "head.relation_alone." + style
    elif g in ("time", "street_of") and not item.subj:
        name = "head.other." + style
    elif ("head.%s.%s" % (g, style)) in BANKS and g not in ("other",):
        name = "head.%s.%s" % (g, style)
    else:
        name = "head.other." + style
    tpl = _pick(rng, name, part, compact, need_subject=bool(item.subj))
    vals = _subject_vals(item.subj)
    vals.update(_val_vals(item, noun))
    vals["on_st"] = on_st
    if g in ("time", "street_of") and not item.subj:
        vals["S"] = "the shop"
    return _fill(tpl, vals)


def _adjunct(ctx: _Ctx, item: _Item, style: str, rng: Rng, compact: bool = False) -> list:
    name = "adj.%s.%s" % (item.group, style)
    if name not in BANKS:
        name = "adj.generic." + style
    tpl = _pick(rng, name, ctx.partition, compact)
    return _fill(tpl, {"v": (item.value, True)})


def _wrap_clause(ctx: _Ctx, segs: list, item: _Item, style: str, rng: Rng, compact: bool,
                 teller: str) -> list:
    part = ctx.partition
    if item.role == "retract":
        kind = "retract"
    elif item.role == "recall":
        kind = "recall"
    elif item.role == "update" and ("upd.%s.%s" % (item.group, style)) not in BANKS:
        kind = "update"
    elif item.src in ("told", "read") and not compact:
        kind = "teller" if (item.src == "told" and teller) else item.src
    else:
        return segs
    if compact and kind in ("told", "read", "teller"):
        return segs
    tpl = _pick(rng, "wrap.%s.%s" % (kind, style), part, compact)
    vals = {"c": segs}
    if kind == "teller":
        vals["t"] = (teller, True)
    return _fill(tpl, vals)


# ---------------------------------------------------------------------------- core line


@dataclass
class _Clause:
    head: list
    adjuncts: list = field(default_factory=list)
    wrapped: bool = False

    def segs(self) -> list:
        out = list(self.head)
        for a in self.adjuncts:
            out.append((" ", False))
            out.extend(a)
        return out


def _build_core(ctx: _Ctx, spec: ObsSpec, items: list, kind: str, style: str, scene: str,
                rng: Rng, frame: tuple, level: int) -> tuple:
    """(sentences, n_fallbacks): sentences are lists of segments without final punctuation."""
    part = ctx.partition
    compact = level >= 1
    sk_i, op_i, jn_i = frame
    opener_mode, order_mode, tail_mode, split_mode = SKELETONS[kind][part][sk_i]
    if level >= 2:
        opener_mode, tail_mode = 0, 0
    heads = [it for it in items if it.head]
    args = [it for it in items if not it.head]
    teller = ""
    for it in list(args):
        if it.name == "told_by":
            teller = it.value
            args.remove(it)
    on_st: list = []
    time_heads = [h for h in heads if h.group == "time"]
    if time_heads:
        sh = time_heads[0]
        street = next((h for h in heads if h.group == "street_of" and h.subj == sh.subj), None)
        if street is None:
            street = next((a for a in args if a.name == "street"), None)
        if street is not None:
            on_st = [(" on ", False), (street.value, True)]
            if street in heads:
                heads.remove(street)
            else:
                args.remove(street)
    narrator_names = {h.subj for h in heads if h.subj}
    args = [a for a in args if a.value not in narrator_names]
    clauses: list = []
    for h in heads:
        noun = "car"
        if h.name == "decoy_colour":
            noun = rng.choice(BANKS["noun.vehicle"][part])
        c = _Clause(_head_clause(ctx, h, style, rng, compact, on_st if h.group == "time" else [], noun))
        clauses.append((c, h))
    if not clauses:
        persons = [a for a in args if a.group == "person"]
        if persons:
            p = persons[0]
            args.remove(p)
            tpl = _pick(rng, "head.lone_person." + style, part, compact)
            segs = _fill(tpl, dict(_subject_vals(""), v=(p.value, True)))
            clauses.append((_Clause(segs), _Item(p.name, p.value, "", "person", True, "assert",
                                                 p.src, "")))
        elif args:
            a = args.pop(0)
            tpl = _pick(rng, "head.lone_arg." + style, part, compact)
            segs = _fill(tpl, dict(_subject_vals(""), ad=_adjunct(ctx, a, style, rng)))
            clauses.append((_Clause(segs), _Item(a.name, a.value, "", a.group, True, "assert", a.src, "")))
        else:
            segs = [(_pad_clause(rng, 6 + rng.below(4), part), False)]
            clauses.append((_Clause(segs), _Item("", "", "", "other", True, "assert", "lived", "")))
    if args:
        first = clauses[0][0]
        for a in args:
            first.adjuncts.append(_adjunct(ctx, a, style, rng, compact))
    sents_in: list = []
    src_done: set = set()
    for c, it in clauses:
        orig = c.segs()
        if it.role in ("assert", "update") and it.src in src_done:
            it = dataclasses.replace(it, src="lived")  # the source wording is stated once per line
        w = _wrap_clause(ctx, orig, it, style, rng, compact, teller)
        if w is not orig and it.role in ("assert", "update") and it.src in ("told", "read"):
            src_done.add(it.src)
        sents_in.append((w, c, w is not orig))
    if order_mode == 1 and len(sents_in) > 1:
        sents_in.reverse()
    joins = BANKS["join." + style][part]
    inline, start = joins[jn_i % len(joins)].split("|")
    sentences: list = []
    if split_mode == 0:
        sep = (inline + " ") if inline[0] in ",;" else (" " + inline + " ")
        cur: list = []
        for k, (w, c, was_wrapped) in enumerate(sents_in):
            if k:
                cur.append((sep, False))
            cur.extend(w)
        sentences.append(cur)
    else:
        for k, (w, c, was_wrapped) in enumerate(sents_in):
            if k:
                sentences.append([(start + " ", False)] + list(w))
            elif (order_mode == 1 and not was_wrapped and len(c.adjuncts) == 1
                  and not c.head[0][1] and level < 2):
                adj = c.adjuncts[0]
                sentences.append(list(adj) + [(", ", False)] + list(c.head))
            else:
                sentences.append(list(w))
    if opener_mode:
        if style == "V1" and kind == "diary":
            ob = BANKS["open.scene." + scene][part]
        else:
            ob = BANKS["open.kind." + kind][part]
        op = ob[op_i % len(ob)]
        sep = ", " if opener_mode == 1 else ": "
        sentences[0] = [(op + sep, False)] + sentences[0]
    if tail_mode and sentences:
        tw = rng.choice(BANKS["adj.w%d" % (2 + rng.below(2))][part])
        sentences[-1] = sentences[-1] + [(" " + tw, False)]
    # containment invariant: every slot value must be in the core; add a plain clause if not
    fallbacks = 0
    joined = " ".join(_text(s) for s in sentences)
    for sl in spec.slots:
        if sl.value not in joined:
            it = _Item(sl.name, sl.value, sl.fid, "other", True, "assert", "lived", "")
            tpl = _pick(rng, "head.other." + style, part, True)
            seg = _fill(tpl, dict(_subject_vals(""), **_val_vals(it, "car")))
            sentences.append(seg)
            joined += " " + _text(seg)
            fallbacks += 1
    sentences = [_cap(s) if (style == "V1" or kind == "dialogue") else _lower(s) for s in sentences]
    return sentences, fallbacks


# ------------------------------------------------------------------- affect sentences


def _affect_sentences(ctx: _Ctx, spec: ObsSpec, rng: Rng) -> list:
    """Affect phrases of a line (sentences as segment lists); [] under A0.

    One latent z = r x (A - mean) / SD + sqrt(1 - r^2) x noise, with the target mean and SD of
    arousal from the config (a fixed transform, so a line never depends on other lines); one
    phrase if z > aff_t1 and a second if z > aff_t2. A1 uses r = 0, A2 uses ``cfg.r_aff``."""
    cfg = ctx.cfg
    if cfg.affect == "A0":
        return []
    r = min(max(float(cfg.r_aff), 0.0), 0.99) if cfg.affect == "A2" else 0.0
    za = min(max((ctx.line_a[spec.oid] - cfg.a_target_mean) / cfg.a_target_sd, -3.0), 3.0)
    z = r * za + math.sqrt(1.0 - r * r) * rng.normal()
    n = (1 if z > cfg.get("aff_t1", 0.25) else 0) + (1 if z > cfg.get("aff_t2", 1.25) else 0)
    strong = [i == 1 for i in range(n)]
    low_a = cfg.get("aff_low_a", 0.3)
    if ctx.line_a[spec.oid] < low_a and cfg.dramatic_decoy_share > 0 and rng.chance(cfg.dramatic_decoy_share):
        strong.append(True)
    sit = ctx.sit.get(spec.sid)
    v = sit.V if sit is not None else 0.0
    floor = cfg.get("aff_pos_floor", 0.05)
    p_pos = min(max(0.5 + 0.5 * v, floor), 1.0 - floor)
    out = []
    for st in strong:
        name = "aff.%s_%s" % ("pos" if rng.chance(p_pos) else "neg", "strong" if st else "mild")
        out.append([(rng.choice(BANKS[name][ctx.partition]), False)])
    return out


def _typos(sentences: list, rate: float, rng: Rng) -> list:
    """Swap two inner letters of some literal words (never inside a protected segment)."""
    out = []
    for segs in sentences:
        new = []
        for text, prot in segs:
            if prot:
                new.append((text, prot))
                continue
            parts = re.split(r"(\s+)", text)
            for i, w in enumerate(parts):
                core = w.strip(",.;:!?\"'()")
                if len(core) >= 5 and core.isalpha() and rng.chance(rate):
                    k = 1 + rng.below(len(core) - 3)
                    sw = core[:k] + core[k + 1] + core[k] + core[k + 2:]
                    parts[i] = w.replace(core, sw, 1)
            new.append(("".join(parts), False))
        out.append(new)
    return out


# ------------------------------------------------------------------------ one line


@dataclass(frozen=True)
class LineParts:
    """A rendered line and its pieces (for tests and gates; ``text`` is what a system sees).

    ``core`` is the slot-bearing text (opener, clauses, tail); ``pre`` and ``post`` are the
    neutral padding sentences before and after it; ``affect`` the affect sentences; ``overflow``
    the words by which the line is longer than its target (the core did not fit)."""

    oid: str
    kind: str
    style: str
    scene: str
    frame: tuple
    skeleton: tuple
    core: str
    pre: tuple
    post: tuple
    affect: tuple
    tag: str
    text: str
    n_words: int
    target_len: int
    overflow: int
    fallbacks: int


def _check_partition(seed: int, partition: str) -> None:
    if partition not in PARTS:
        raise ValueError("partition must be 'dev' or 'test', got %r" % (partition,))
    if partition_of_seed(seed) == "test" and partition != "test":
        raise ValueError("test seeds render only the test partition")


def _render_line(ctx: _Ctx, spec: ObsSpec) -> LineParts:
    part, cfg = ctx.partition, ctx.cfg
    kind = spec.channel
    style = STYLE_OF_CHANNEL[kind]
    sit = ctx.sit.get(spec.sid)
    scene = sit.scene if sit is not None else "minor"
    fr = frames_of(scene, part)
    items = _items(ctx, spec)
    target = spec.target_len
    rng_pad = stream(ctx.seed, "verb", part, "pad", spec.oid)
    rng_aff = stream(ctx.seed, "verb", part, "aff", spec.oid)
    affect = _affect_sentences(ctx, spec, rng_aff)
    aff_words = sum(word_count(_text(s)) for s in affect)
    tag = rng_pad.choice(BANKS["tag.dialogue"][part]) if kind == "dialogue" else ""
    tag_words = word_count(tag)
    key = spec.frame or spec.oid
    for level in (0, 1, 2):
        rng_core = stream(ctx.seed, "verb", part, "core", key)
        frame = fr[rng_core.below(len(fr))]
        sentences, fallbacks = _build_core(ctx, spec, items, kind, style, scene, rng_core, frame, level)
        core_words = sum(word_count(_text(s)) for s in sentences)
        if core_words + aff_words + tag_words <= target or level == 2:
            break
    remaining = target - core_words - aff_words - tag_words
    if 1 <= remaining <= 3:  # no room for a pad clause: close the gap with tail words
        tw = rng_core.choice(BANKS[_TAIL_WORDS[remaining]][part])
        if affect:
            affect[-1] = affect[-1] + [(" " + tw, False)]
        else:
            sentences[-1] = sentences[-1] + [(" " + tw, False)]
        remaining = 0
    used_pad: set = set()
    plain_p, plain_w = cfg.get("pad_plain_p", PAD_PLAIN_P), cfg.get("pad_plain_weight", PAD_PLAIN_WEIGHT)
    pads = ([[(_pad_clause(rng_pad, L, part, used_pad, plain_p), False)]
             for L in _plan_pad(rng_pad, remaining, part, plain_w)] if remaining > 3 else [])
    k_pre = rng_pad.below(len(pads) + 1)
    casing = _cap if (style == "V1" or kind == "dialogue") else _lower
    units: list = [("pad", [casing(p)]) for p in pads[:k_pre]]
    units.append(("core", sentences))
    units.extend(("pad", [casing(p)]) for p in pads[k_pre:])
    n_pre = k_pre
    for a in affect:
        units.insert(rng_aff.below(len(units) + 1), ("aff", [casing(a)]))
    flat = [s for _, ss in units for s in ss]
    if cfg.typo_rate > 0:
        rng_typo = stream(ctx.seed, "verb", part, "typo", spec.oid)
        flat = _typos(flat, cfg.typo_rate, rng_typo)
    # re-split the typo'd sentences back into units (one sentence per unit except the core)
    pos = 0
    texts = []
    for name, ss in units:
        texts.append((name, [_text(x) + "." for x in flat[pos:pos + len(ss)]]))
        pos += len(ss)
    body = " ".join(t for _, ts in texts for t in ts)
    text = ('"%s" %s.' % (body, tag)) if kind == "dialogue" else body
    core_txt = " ".join(t for n, ts in texts if n == "core" for t in ts)
    idx = [n for n, _ in texts].index("core")
    pre = tuple(t for n, ts in texts[:idx] if n == "pad" for t in ts)
    post = tuple(t for n, ts in texts[idx + 1:] if n == "pad" for t in ts)
    aff_txt = tuple(t for n, ts in texts if n == "aff" for t in ts)
    n_words = word_count(text)
    return LineParts(
        oid=spec.oid, kind=kind, style=style, scene=scene, frame=frame,
        skeleton=SKELETONS[kind][part][frame[0]], core=core_txt, pre=pre, post=post, affect=aff_txt,
        tag=tag, text=text, n_words=n_words, target_len=target, overflow=max(0, n_words - target),
        fallbacks=fallbacks)


def render_parts(world: World, cfg: TierCfg, seed: int, partition: str, oid: str) -> LineParts:
    """The pieces of one line (same text as ``render`` gives for that oid)."""
    _check_partition(seed, partition)
    _check_v3(cfg)
    return _render_line(_Ctx(world, cfg, seed, partition), world.obs_spec(oid))


def render_all_parts(world: World, cfg: TierCfg, seed: int, partition: str) -> list:
    """``LineParts`` of every line, in stream order (one pass; what gates such as G-POS read)."""
    _check_partition(seed, partition)
    _check_v3(cfg)
    ctx = _Ctx(world, cfg, seed, partition)
    return [_render_line(ctx, o) for o in world.obs_specs]


def _check_v3(cfg: TierCfg) -> None:
    if cfg.v_mix[2] > 0:
        raise NotImplementedError("V3 (formal log or news) is not implemented in lifesim-v0.1")


def render_v3(*args, **kwargs):
    """The V3 renderer (formal log or news) is a v0.1 item and is not built."""
    raise NotImplementedError("V3 (formal log or news) is not implemented in lifesim-v0.1")


def render(world: World, cfg: TierCfg, seed: int, partition: str) -> list:
    """One ``Obs`` per ``ObsSpec`` of the world, in the same order, with the same oid, t_obs and
    channel, every ``Slot.value`` verbatim and the length of the spec's ``target_len``.

    ``partition`` selects the clause banks ('dev' or 'test'); a sealed test seed accepts only
    'test'. Each line draws from its own streams ``stream(seed, 'verb', partition, ...)`` keyed
    by its oid (or by ``ObsSpec.frame`` for the core text), so deleting events never changes
    another line. Text dials read from ``cfg``: affect, r_aff, dramatic_decoy_share, typo_rate,
    retell_a_factor, v_mix (a V3 share raises NotImplementedError)."""
    _check_partition(seed, partition)
    _check_v3(cfg)
    ctx = _Ctx(world, cfg, seed, partition)
    return [Obs(oid=o.oid, t_obs=o.t_obs, channel=o.channel, text=_render_line(ctx, o).text)
            for o in world.obs_specs]


def missing_slots(spec: ObsSpec, text: str) -> list:
    """The slots of a spec whose value is not verbatim in ``text`` (evidence containment)."""
    return [s for s in spec.slots if s.value not in text]


# ------------------------------------------------------------ the planted naive renderer

_NAIVE_EMPHASIS = (
    "My heart was pounding.", "I could not believe it.", "I was absolutely terrified.",
    "I felt devastated.", "I was over the moon.", "My hands were shaking.",
    "I was furious about it.", "I felt completely panicked.", "I was thrilled.",
    "I was horrified.",
)


def render_planted_naive(world: World, cfg: TierCfg, seed: int, partition: str,
                         leaks: Sequence[str] = ("length", "affect")) -> list:
    """PLANTED ARTEFACT, a positive control for the gates G-LEN and G-AFF. Never use for a result.

    A deliberately naive renderer: one 'Noted: <slot> <value>.' sentence per slot and no
    padding. ``leaks`` may contain 'length' (the line grows with its number of slots, so
    evidence-bearing lines are longer, and with the line's arousal, through neutral filler) and
    'affect' (emphasis sentences with affect words whose number grows with arousal, whatever
    ``cfg.affect`` says). Without 'length' the line is padded to ``target_len`` as usual."""
    _check_partition(seed, partition)
    ctx = _Ctx(world, cfg, seed, partition)
    out = []
    for spec in world.obs_specs:
        rng = stream(seed, "verb", partition, "naive", spec.oid)
        a = min(max(ctx.line_a[spec.oid], 0.0), 1.0)
        sents = ["I wrote down the %s as %s for later." % (s.name.replace("_", " "), s.value) for s in spec.slots]
        if "affect" in leaks:
            for _ in range(int(8.0 * a + rng.u())):
                sents.append(rng.choice(_NAIVE_EMPHASIS))
        if "length" in leaks:
            sents.insert(0, "Today I wrote this down for later.")
            for _ in range(int(8.0 * a + rng.u())):
                sents.append(_cap([(_pad_clause(rng, 6, partition), False)])[0][0] + ".")
        else:
            r = spec.target_len - sum(word_count(s) for s in sents)
            if r >= 4:
                sents.extend(pad_to_length(rng, r, partition))
            elif 1 <= r <= 3 and sents:
                sents[-1] = sents[-1][:-1] + " " + rng.choice(BANKS[_TAIL_WORDS[r]][partition]) + "."

        out.append(Obs(oid=spec.oid, t_obs=spec.t_obs, channel=spec.channel, text=" ".join(sents)))
    return out


# ------------------------------------------------------- slot verifier of the flash pass

_NUM = re.compile(r"\d+")
_CAPW = re.compile(r"(?<![.!?\"]\s)(?<!^)\b[A-Z][a-z]+")


def validate_paraphrase(spec: ObsSpec, template_text: str, candidate: str) -> tuple:
    """(accepted, reason) for a paraphrased line, the deterministic half of the renderer-OOD flash
    pass: every slot string verbatim, no new numeral, colour or proper noun, the same affect
    entries, and a length of 0.8-1.3 x ``target_len``. A rejected line keeps its template text."""
    miss = missing_slots(spec, candidate)
    if miss:
        return False, "slot missing: %s" % miss[0].value
    if set(_NUM.findall(candidate)) - set(_NUM.findall(template_text)):
        return False, "new numeral"
    cols = pool_vocab("colours")
    if set(cols.matches(candidate)) - set(cols.matches(template_text)):
        return False, "new colour"
    known = {norm(w) for w in re.findall(r"[A-Z][a-z]+", template_text)}
    for w in re.findall(r"(?<=[a-z,;:] )[A-Z][a-z]+", candidate):
        if norm(w) not in known:
            return False, "new proper noun: %s" % w
    if sorted(affect_scan(candidate)) != sorted(affect_scan(template_text)):
        return False, "affect words changed"
    n = word_count(candidate)
    if not (0.8 * spec.target_len <= n <= 1.3 * spec.target_len):
        return False, "length %d outside 0.8-1.3 of %d" % (n, spec.target_len)
    return True, ""


# ------------------------------------------------------------------------- questions
# Ask clauses (a question about one predicate) in direct form ('What did I have for breakfast')
# and embedded form ('what I had for breakfast'). {S} is the subject noun phrase of the cue.

_ASK_TEXT = {
    "breakfast": ("""
What did I have for breakfast
What was my breakfast
What did I eat for breakfast
Which breakfast did I have
""", """
what I had for breakfast
what my breakfast was
what I ate for breakfast
which breakfast I had
"""),
    "colour": ("""
What colour was the car
Which colour was the car
What was the colour of the car
What colour did the car have
""", """
what colour the car was
which colour the car was
the colour of the car
what colour the car had
"""),
    "car_colour": ("""
What colour was the car parked outside
Which colour was the car parked outside
What was the colour of the car parked outside
What colour was the car standing outside
""", """
what colour the car parked outside was
which colour the car parked outside was
the colour of the car parked outside
what colour the car standing outside was
"""),
    "city": ("""
Which city do I live in
Where do I live
Which town is my home
In which city do I live
""", """
which city I live in
where I live
which town is my home
in which city I live
"""),
    "city_past": ("""
Which city did I live in
Where did I live
Which town was my home
In which city did I live
""", """
which city I lived in
where I lived
which town was my home
in which city I lived
"""),
    "job": ("""
What is my job
What do I do for a living
What work do I do
What is my occupation
""", """
what my job is
what I do for a living
what work I do
what my occupation is
"""),
    "job_past": ("""
What was my job
What did I do for a living
What work did I do
What was my occupation
""", """
what my job was
what I did for a living
what work I did
what my occupation was
"""),
    "org": ("""
Where do I work
Which organisation do I work for
Where am I employed
Who is my employer
""", """
where I work
which organisation I work for
where I am employed
who my employer is
"""),
    "org_past": ("""
Where did I work
Which organisation did I work for
Where was I employed
Who was my employer
""", """
where I worked
which organisation I worked for
where I was employed
who my employer was
"""),
    "relation": ("""
Who is {S}
What is {S} to me
How is {S} related to me
What relation is {S} to me
""", """
who {S} is
what {S} is to me
how {S} is related to me
what relation {S} is to me
"""),
    "time": ("""
At what time does {S} close on Saturdays
When does {S} close on Saturdays
What is the Saturday closing time of {S}
What time does {S} shut on Saturdays
""", """
at what time {S} closes on Saturdays
when {S} closes on Saturdays
the Saturday closing time of {S}
what time {S} shuts on Saturdays
"""),
    "count": ("""
How many times did I go to {S}
How often did I visit {S}
How many visits did I make to {S}
How many trips did I make to {S}
""", """
how many times I went to {S}
how often I visited {S}
how many visits I made to {S}
how many trips I made to {S}
"""),
    "person": ("""
Who was with me
Who came with me
Who was there with me
Who joined me
""", """
who was with me
who came with me
who was there with me
who joined me
"""),
    "companion_trip": ("""
Who came with me when I visited {S}
Who was with me on my visit to {S}
Who went with me to {S}
Who joined me on the trip to {S}
""", """
who came with me when I visited {S}
who was with me on my visit to {S}
who went with me to {S}
who joined me on the trip to {S}
"""),
    "generic": ("""
What was the {label}
What was my {label}
Which {label} was it
What is known about the {label}
""", """
what the {label} was
what my {label} was
which {label} it was
what is known about the {label}
"""),
}
for _g, (_d, _e) in _ASK_TEXT.items():
    _B("ask.%s.direct" % _g, _d)
    _B("ask.%s.embedded" % _g, _e)

_STEMS = {
    "EP1": """
{Qd}{W}?
Do you remember {Qe}{W}?
Can you tell me {Qe}{W}?
Remind me {Qe}{W}.
Quick check: {Qd}{W}?
I cannot recall {Qe}{W}, do you know?
Looking back over my notes, can you say {Qe}{W}?
Help me out: {Qd}{W}?
Think back and say {Qe}{W}.
{Qd}{W}, if you remember?
Could you work out {Qe}{W}?
Going by what I wrote, can you say {Qe}{W}?
Tell me {Qe}{W}.
For my records: {Qd}{W}?
Please look up {Qe}{W}.
I need to know {Qe}{W}.
""",
    "SE": """
{Qd}{W}?
Do you know {Qe}{W}?
Can you tell me {Qe}{W}?
Please state {Qe}{W}.
Check the record: {Qd}{W}?
I need to confirm {Qe}{W}.
Quick question: {Qd}{W}?
Remind me {Qe}{W}.
Settle this for me: {Qd}{W}?
Do you recall {Qe}{W}?
Tell me {Qe}{W}.
From what you have read, can you say {Qe}{W}?
Help me remember {Qe}{W}.
{Qd}{W}, as far as you know?
Look it up for me: {Qd}{W}?
I forgot {Qe}{W}.
""",
    "IN1": """
{Qd} in the article about {S} that I read{W}?
In the article about {S} that I read{W}, {Qdl}?
Do you remember {Qe} in the article about {S} that I read{W}?
I read an article about {S}{W}. {Qd}?
Tell me {Qe} in the article about {S} that I read{W}.
About the story on {S} that I read{W}: {Qd}?
{Qd} in the report on {S} that I read{W}?
Can you say {Qe} in the news item about {S} that I came across{W}?
Regarding the article about {S} that I read{W}, {Qdl}?
Remind me {Qe} in the article about {S} that I read{W}.
From the story about {S} that I read{W}, {Qdl}?
In the piece about {S} that I read{W}, {Qdl}?
Help me: {Qd} in the article on {S} that I read{W}?
I read about {S}{W}. Do you remember {Qe}?
Think of the article about {S} that I read{W}: {Qd}?
Please say {Qe} in the article about {S} that I read{W}.
""",
    "EP4": """
{Qd} when I got the news{W}?
Do you remember {Qe} when I got the news{W}?
Can you tell me {Qe} at the moment I heard{W}?
{Qd} at the moment I heard the news{W}?
Think back to when I got the news{W}: {Qd}?
Remind me {Qe} when I got the news{W}.
When I got the news{W}, {Qdl}?
Looking back at the day I heard{W}, {Qdl}?
I keep wondering {Qe} when the news came{W}.
At the time the news reached me{W}, {Qdl}?
Tell me {Qe} the moment I learned of it{W}.
{Qd} when it happened{W}?
Do you recall {Qe} when I heard{W}?
For my records: {Qd} when I was told{W}?
Try to recall {Qe} when the news arrived{W}.
{Qd} when the news came{W}?
""",
    "IN4": """
{Qd}?
Do you know {Qe}?
Can you tell me {Qe}?
I need to know {Qe}.
Quick question: {Qd}?
Remind me {Qe}.
Please look up {Qe}.
Help me out: {Qd}?
Going by my notes, can you say {Qe}?
Tell me {Qe}.
I forgot {Qe}.
{Qd}, as far as you know?
Check the record: {Qd}?
Could you work out {Qe}?
Think back and say {Qe}.
Do you remember {Qe}?
""",
    "EP3c": """
{Qd}{W}?
Do you remember {Qe}{W}?
Can you work out {Qe}{W}?
Count for me {Qe}{W}.
Quick tally: {Qd}{W}?
Tell me {Qe}{W}.
From my notes, can you say {Qe}{W}?
I lost count: {Qd}{W}?
Please add up {Qe}{W}.
Help me out: {Qd}{W}?
Check the record and tell me {Qe}{W}.
{Qd}{W}, as far as you can tell?
I need the number: {Qd}{W}?
Looking at my diary, can you say {Qe}{W}?
Remind me {Qe}{W}.
Work out {Qe}{W}.
""",
    "TRIP": """
{Qd}?
Do you remember {Qe}?
Can you tell me {Qe}?
Remind me {Qe}.
Quick question: {Qd}?
Tell me {Qe}.
Think back and say {Qe}.
Help me out: {Qd}?
I forgot {Qe}.
{Qd}, if you remember?
Going by my notes, can you say {Qe}?
Please look up {Qe}.
Do you know {Qe}?
For my records: {Qd}?
Could you work out {Qe}?
I need to know {Qe}.
""",
}
#: A stem another family already uses gets a family tag before its final punctuation, so every
#: question frame of the module is a distinct string and each family keeps 8 frames per partition.
_STEM_TAG = {"SE": ", please", "IN4": ", if you can", "EP3c": ", thanks", "TRIP": ", for me",
             "EP4": ", honestly"}
_seen_stems: set = set()
for _f, _t in _STEMS.items():
    _lines = []
    for _ln in _t.strip().split("\n"):
        _ln = _ln.strip()
        if _ln in _seen_stems:
            _ln = _ln[:-1] + _STEM_TAG.get(_f, ", really") + _ln[-1]
        _lines.append(_ln)
    _seen_stems.update(_lines)
    _B("stem." + _f, "\n".join(_lines))
_B("qsuf.conf", """
Answer, then give CONF: 0-100.
Then add CONF: 0-100 for how sure you are.
End with CONF: 0-100.
After the answer, state CONF: 0-100.
Please finish with CONF: 0-100.
Add a line CONF: 0-100 after your answer.
""")
_B("qsuf.abstain", """
If it was never stated, reply UNKNOWN.
Say UNKNOWN if nothing was ever said about it.
Reply UNKNOWN when it was not mentioned.
If you find no record, answer UNKNOWN.
Answer UNKNOWN if it never came up.
If it is not in the notes, reply UNKNOWN.
""")
_B("qsuf.options", """
Options:
Choose one:
Pick from:
The options are:
""")
_B("qtail.S", """
regarding {S}
concerning {S}
about {S}
relating to {S}
""")

_FAMILY_STEMS = {"EP1": ("EP1",), "SE4": ("SE",), "SE5": ("SE",), "IN1": ("IN1",), "EP4": ("EP4",),
                 "IN4": ("IN4",), "EP3c": ("EP3c",), "ME1": ("EP1", "IN4", "TRIP")}
_FAMILY_ASK = {"EP1": "breakfast", "SE4": "lives_in", "SE5": "works_as", "IN1": "vehicle_colour",
               "EP4": "companion", "IN4": "closing_time", "EP3c": "visit_count", "ME1": "breakfast"}
_ASK_GROUP = {"breakfast": "breakfast", "dish": "breakfast", "vehicle_colour": "colour",
              "colour": "colour", "car_colour": "car_colour", "lives_in": "city", "city": "city",
              "works_as": "job", "job": "job", "works_at": "org", "relation": "relation",
              "closing_time": "time", "time": "time", "visit_count": "count", "count": "count",
              "companion": "person", "person": "person"}
_GROUP_STEMS = {"breakfast": "EP1", "colour": "IN1", "car_colour": "EP4", "city": "SE", "city_past": "SE",
                "job": "SE", "job_past": "SE", "org": "SE", "org_past": "SE", "relation": "SE",
                "time": "IN4", "count": "EP3c", "person": "EP4", "companion_trip": "TRIP",
                "generic": "EP1"}
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TEMPORAL = ("date", "relative_day", "relative_window", "window_from", "window_to")


def question_stems(family: str, partition: str) -> tuple:
    """The question frames (stems) a family can use in a partition."""
    names = _FAMILY_STEMS.get(family, ("EP1",))
    return tuple(s for n in names for s in BANKS["stem." + n][partition])


def _hidx(key: str, n: int) -> int:
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % n


def _when_phrase(cue: Sequence) -> tuple:
    """(phrase, temporal slots) of the temporal cues; the phrase is '' if there are none."""
    tem = [s for s in cue if s.name in _TEMPORAL or _ISO.match(s.value)]
    d = {s.name: s.value for s in tem}
    parts = []
    if "window_from" in d and "window_to" in d:
        parts.append("between %s and %s" % (d.pop("window_from"), d.pop("window_to")))
    for s in tem:
        if s.name in d:
            parts.append(("on " + s.value) if _ISO.match(s.value) else s.value)
    return " ".join(parts), tem


def _subject_np(subs: Sequence) -> str:
    d: dict = {}
    for s in subs:
        d.setdefault(s.name, []).append(s.value)
    parts = []
    if "story_kind" in d:
        p = "the " + d.pop("story_kind")[0]
        if "city" in d:
            p += " in " + d.pop("city")[0]
        parts.append(p)
    if "shop" in d:
        p = "the " + d.pop("shop")[0]
        if "street" in d:
            p += " on " + d.pop("street")[0]
        parts.append(p)
    elif "street" in d:
        parts.append(d.pop("street")[0])
    for name in ("person", "city"):
        if name in d:
            parts.extend(d.pop(name))
    if "errand" in d:
        parts.extend("the " + v for v in d.pop("errand"))
    for vals in d.values():
        parts.extend(vals)
    return " and ".join(parts)


def render_question(query: Query, frame_partition: str, *, abstain_hint: bool = True) -> str:
    """Question text of a query in the question frames of ``frame_partition``.

    Reads only family, cue, ask, options, fmt, conf (and qid / twin_of to pick a frame): a query
    and its ``twin_of`` twin get the same frame; the gold is never read. Every cue value is
    verbatim in the text, the options are listed as 'A) ...', the request 'CONF: 0-100' is
    appended when ``query.conf``, and (unless ``abstain_hint`` is False) every open question
    ends with the same hint to reply UNKNOWN when nothing was stated, so that abstention
    items are not recognisable by their wording."""
    part = frame_partition
    if part not in PARTS:
        raise ValueError("frame_partition must be 'dev' or 'test', got %r" % (part,))
    fam = query.family
    when, tem = _when_phrase(query.cue)
    subs = [s for s in query.cue if s not in tem]
    names = {s.name for s in subs}
    ask = query.ask or _FAMILY_ASK.get(fam, "")
    group = _ASK_GROUP.get(ask, "generic")
    if group == "person" and "city" in names and "story_kind" not in names:
        group = "companion_trip"
    elif group in ("city", "job", "org") and when:
        group += "_past"
    snp = _subject_np(subs)
    key = "%s|%s|%s" % (fam, query.twin_of or query.qid, part)
    stem_bank = BANKS["stem." + _GROUP_STEMS[group]][part]
    if fam in ("EP1", "SE4", "SE5", "IN1", "EP4", "IN4", "EP3c"):
        stem_bank = BANKS["stem." + _FAMILY_STEMS[fam][0]][part]
    stem = stem_bank[_hidx(key + "|stem", len(stem_bank))]
    qd = BANKS["ask.%s.direct" % group][part]
    qe = BANKS["ask.%s.embedded" % group][part]
    qd_t, qe_t = qd[_hidx(key + "|qd", len(qd))], qe[_hidx(key + "|qe", len(qe))]
    default_s = {"relation": "that person", "time": "the shop", "count": "that place",
                 "companion_trip": "that place"}
    label = ask.replace("_", " ") if ask else "answer"
    s_in_q = "{S}" in qd_t or "{S}" in qe_t
    qvals = {"S": snp or default_s.get(group, ""), "label": label}
    qd_t, qe_t = qd_t.format(**qvals), qe_t.format(**qvals)
    stem_s = "{S}" in stem
    text = stem.format(Qd=qd_t, Qdl=qd_t[:1].lower() + qd_t[1:], Qe=qe_t,
                       S=snp or "the story", W=(" " + when) if when else "")
    placed_s = s_in_q or stem_s
    if snp and not placed_s:
        tail = BANKS["qtail.S"][part][_hidx(key + "|tail", len(BANKS["qtail.S"][part]))].format(S=snp)
        text = text[:-1] + " " + tail + text[-1]
    if when and "{W}" not in stem:
        text = text[:-1] + " " + when + text[-1]
    for s in query.cue:  # containment invariant for cues of an unknown kind
        if s.value not in text:
            text = text[:-1] + " (" + s.value + ")" + text[-1]
    if query.fmt == "choice":
        lead = BANKS["qsuf.options"][part][_hidx(key + "|opt", len(BANKS["qsuf.options"][part]))]
        text += " " + lead + " " + " ".join("%s) %s" % ("ABCDEFGH"[i], o) for i, o in enumerate(query.options)) + "."
    elif abstain_hint:
        b = BANKS["qsuf.abstain"][part]
        text += " " + b[_hidx(key + "|abs", len(b))]
    if query.conf:
        b = BANKS["qsuf.conf"][part]
        text += " " + b[_hidx(key + "|conf", len(b))]
    return text


# ------------------------------------------------------------------------- self-check


def _self_check() -> None:
    """Import-time guard: disjoint halves, fillable templates, enough frames and families."""
    seen: dict = {}
    clashes = []
    for name, halves in BANKS.items():
        if len(halves["dev"]) < 2 or len(halves["test"]) < 2:
            raise ValueError("bank %s needs at least two entries in each partition" % name)
        for part in PARTS:
            for item in halves[part]:
                other = seen.get(item)
                if other is not None and other[1] != part:
                    clashes.append("%r (%s and %s)" % (item, other[0], name))
                seen[item] = (name, part)
    if clashes:
        raise ValueError("clauses in both partitions: " + "; ".join(clashes))
    dummy = {"S": "X", "s": "", "am": "am", "have": "have", "do": "do", "v": "v", "a_v": "a v",
             "n": "car", "label": "l", "on_st": "", "ad": "in Y", "c": "c", "t": "T",
             "Qd": "Q", "Qdl": "q", "Qe": "q", "W": "", "S_": ""}
    for name, halves in BANKS.items():
        if name.startswith(("pad.", "noun.", "adj.w", "tag.", "aff.", "open.", "join.", "qsuf.")):
            continue
        for part in PARTS:
            for tpl in halves[part]:
                _PH.sub(lambda m: dummy[m.group(1)], tpl)
    for fam in ("EP1", "SE4", "SE5", "IN1", "EP4", "IN4", "EP3c", "ME1"):
        for part in PARTS:
            if len(question_stems(fam, part)) < 8:
                raise ValueError("%s needs at least 8 question frames in %s" % (fam, part))
    for k in (1, 2, 3):
        for part in PARTS:
            for tw in BANKS["adj.w%d" % k][part]:
                if len(tw.split()) != k:
                    raise ValueError("tail word %r must have %d words" % (tw, k))
    for scene in SCENE_NAMES:
        for part in PARTS:
            if not 40 <= frame_count(scene, part) <= 80:
                raise ValueError("a scene needs 40-80 frames")
    for kind in CHANNELS:
        for part in PARTS:
            if template_family_count(kind, part) < 12:
                raise ValueError("a kind needs at least 12 template families")


_self_check()
