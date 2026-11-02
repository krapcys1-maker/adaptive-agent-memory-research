"""Names, answer pools and closed vocabularies for LifeSim.

What this module provides
-------------------------
* ``make_names(rng, n, partition, kind, used)``: invented names from syllable
  inventories that are disjoint between the ``dev`` and ``test`` partitions. Every
  name is built from consonant-vowel syllables (plus an optional coda or town suffix)
  whose consonants all belong to the partition's own consonant set, and the two sets
  share no letter, so no name can occur in both partitions. Names are never English
  pool words and never a substring of each other.
* The static answer pools: ``COLOURS`` (40, with aliases), ``DISHES`` (120), ``JOBS``,
  ``RELATIONS``, ``TIMES`` (24 quarter-hour closing times), ``COUNTS`` (1-24), and the
  composition pools ``SHOP_TYPES``, ``STORY_KINDS``, ``ERRANDS``, ``WEEKDAYS``,
  ``MONTHS``. Every answer pool has at least 24 values, so blind chance is at most 1/24.
* ``Vocab`` and ``closed_vocab(world, slot)``: the closed vocabulary of a slot (static
  pool or the world's invented entities of a kind) with its alias map and a reference
  longest-match routine over normalised tokens. ``scorers.extract_candidates`` is
  expected to build on ``Vocab.matches``.
* ``norm``: the one text normaliser (NFKC, casefold, accents stripped, punctuation to
  spaces) used for every alias key; ``scorers.normalise`` should be this function.

Vocabulary ids are ``pool:<pool id>`` or ``kind:<entity kind>``; ``Gold.vocab_id`` uses
the same strings, so ``closed_vocab(world, gold.vocab_id)`` always works.

What this module does NOT do: it does not handle inflection (plurals, tenses) beyond
the aliases listed, parse times or number words (``scorers`` does), choose which values
a world uses (``world``/``scenes`` do), or know any real person, place or brand. Pools
are shared by both partitions; only names, and later clause banks and question frames,
are partitioned.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from .rng import Rng

if TYPE_CHECKING:  # pragma: no cover
    from .schema import World

__all__ = [
    "norm", "make_names", "partition_of_name", "Vocab", "closed_vocab", "pool_vocab",
    "kind_vocab", "SLOTS", "POOLS", "POOL_ALIASES", "VOWELS", "CONSONANTS", "CODAS",
    "SUFFIXES", "SYLLABLES", "COLOURS", "COLOUR_ALIASES", "DISHES", "DISH_ALIASES", "JOBS",
    "RELATIONS", "SHOP_TYPES", "STORY_KINDS", "ERRANDS", "TIMES", "COUNTS", "WEEKDAYS",
    "MONTHS", "NUMBER_WORDS", "RESERVED", "JOB_ALIASES", "PARTITION_NAMES",
]

# ------------------------------------------------------------------------- normaliser

_NON_WORD = re.compile(r"[\W_]+")


def norm(text: str) -> str:
    """NFKC, casefold, strip accents, turn every run of punctuation into one space."""
    t = unicodedata.normalize("NFKC", text).casefold()
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return _NON_WORD.sub(" ", t).strip()


# ---------------------------------------------------------------------- name inventories

PARTITION_NAMES = ("dev", "test")
VOWELS = "aeiou"
#: Disjoint consonant sets: every consonant of a name comes from its partition's set.
CONSONANTS = {"dev": "bdgkmnrst", "test": "fhjlpvwyc"}
CODAS = {"dev": "nrsm", "test": "lpf"}
SUFFIXES = {
    "dev": ("burg", "mont", "stad", "gard", "kirk", "mark", "dam", "ton", "berg", "dorn"),
    "test": ("ville", "pool", "vale", "hill", "hall", "loch", "cove", "flow"),
}
SYLLABLES = {p: tuple(c + v for c in CONSONANTS[p] for v in VOWELS) for p in PARTITION_NAMES}

# kind -> (probability of 3 syllables, probability of a coda, probability of a town suffix)
_SHAPES = {
    "person": (0.4, 0.30, 0.0),
    "city": (0.4, 0.15, 0.5),
    "street": (0.2, 0.30, 0.0),
    "shop": (0.2, 0.40, 0.0),
    "org": (0.4, 0.40, 0.0),
}


def partition_of_name(name: str) -> str | None:
    """'dev' or 'test' if all consonants of the name belong to that partition, else None."""
    letters = {ch for ch in name.casefold() if ch.isalpha() and ch not in VOWELS}
    for p in PARTITION_NAMES:
        if letters and letters <= set(CONSONANTS[p]):
            return p
    return None


def _one_name(rng: Rng, partition: str, kind: str) -> str:
    p3, pc, ps = _SHAPES[kind]
    cons = CONSONANTS[partition]
    n_syl = 3 if rng.chance(p3) else 2
    s = ""
    for _ in range(n_syl):
        c = rng.choice(cons)
        v = rng.choice(VOWELS)
        s += c + v
    if kind == "city" and rng.chance(ps):
        s += rng.choice(SUFFIXES[partition])
    elif rng.chance(pc):
        s += rng.choice(CODAS[partition])
    return s.capitalize()


def make_names(rng: Rng, n: int, partition: str, kind: str = "person",
               used: set | None = None) -> list[str]:
    """``n`` distinct invented names for a partition ('dev' or 'test').

    ``kind`` is person | city | street | shop | org and only shapes the name (syllable
    count, coda, town suffix); the caller adds words such as 'Pharmacy' or 'Street'.
    ``used`` is a set of casefolded names already taken in the world; it is updated, and
    no new name equals, contains or is contained in a used one, so names stay unique and
    never nest. Names are at least 4 letters and never a pool word (``RESERVED``)."""
    if partition not in PARTITION_NAMES:
        raise ValueError("partition must be 'dev' or 'test', got %r" % (partition,))
    if kind not in _SHAPES:
        raise ValueError("kind must be one of %s, got %r" % (tuple(_SHAPES), kind))
    taken = used if used is not None else set()
    out: list[str] = []
    attempts = 0
    while len(out) < n:
        attempts += 1
        if attempts > 5000 * (n + 1):
            raise RuntimeError("name pool exhausted")
        name = _one_name(rng, partition, kind)
        key = name.casefold()
        if len(key) < 4 or key in RESERVED:
            continue
        if any(key in u or u in key for u in taken):
            continue
        taken.add(key)
        out.append(name)
    return out


# --------------------------------------------------------------------------- the pools

COLOURS = (
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown", "black", "white",
    "grey", "silver", "gold", "beige", "turquoise", "teal", "navy", "maroon", "burgundy",
    "crimson", "scarlet", "violet", "lavender", "magenta", "cyan", "olive", "lime", "mint",
    "ivory", "cream", "tan", "khaki", "peach", "coral", "salmon", "indigo", "charcoal",
    "bronze", "copper", "mustard",
)
COLOUR_ALIASES = (
    ("gray", "grey"), ("navy blue", "navy"), ("lime green", "lime"), ("olive green", "olive"),
    ("mint green", "mint"), ("charcoal grey", "charcoal"), ("charcoal gray", "charcoal"),
    ("silver grey", "silver"), ("silver gray", "silver"), ("golden", "gold"),
    ("ivory white", "ivory"), ("bordeaux", "burgundy"), ("aqua", "cyan"),
)

DISHES = (
    # eggs
    "scrambled eggs", "fried eggs", "poached eggs", "boiled eggs", "cheese omelette",
    "ham omelette", "eggs benedict", "shakshuka", "spanish tortilla", "egg sandwich",
    # bread and pastry
    "toast with jam", "toast with honey", "avocado toast", "french toast",
    "bagel with cream cheese", "sesame bagel", "croissant", "pain au chocolat",
    "brioche with butter", "baguette with butter", "rye bread with cheese",
    "sourdough with ham", "cheese sandwich", "ham sandwich", "tuna sandwich",
    "bacon sandwich", "cinnamon roll", "blueberry muffin", "scones with jam",
    "crumpets with butter", "english muffin", "danish pastry", "apple turnover",
    "cheese pastry",
    # griddle
    "pancakes with syrup", "blueberry waffles", "crepes with lemon", "potato pancakes",
    "banana pancakes", "dutch pancake",
    # cereal and grains
    "porridge", "muesli", "granola with yoghurt", "cornflakes", "bran flakes",
    "rice pudding", "semolina pudding", "buckwheat groats", "overnight oats",
    "chia pudding", "congee", "grits", "puffed rice", "ricotta toast", "sweet potato hash",
    "date and walnut bread",
    # dairy and fruit
    "yoghurt with berries", "cottage cheese with fruit", "fruit salad", "banana smoothie",
    "berry smoothie", "green smoothie", "apple slices with peanut butter", "mango lassi",
    "melon slices", "fruit bowl", "kefir with oats", "quark with honey",
    # savoury and cooked
    "bacon and eggs", "sausage and beans", "beans on toast", "full english breakfast",
    "hash browns", "breakfast burrito", "sausage roll", "bacon roll",
    "ham and cheese toastie", "smoked salmon on rye", "kippers", "grilled tomatoes",
    "corned beef hash", "chorizo and potatoes", "spinach and feta pie", "cheese borek",
    "meat pie", "veggie sausage", "tofu scramble",
    # from elsewhere
    "masala dosa", "idli with chutney", "aloo paratha", "poha", "upma",
    "miso soup with rice", "tamagoyaki", "natto on rice", "pho", "arepa with cheese",
    "empanada", "churros with chocolate", "pastel de nata", "pierogi",
    "blini with sour cream", "syrniki", "kasha with butter", "ful medames", "manakish",
    "labneh with olives", "halloumi and tomato", "simit", "bureka",
    # odds and ends
    "peanut butter sandwich", "chocolate crepe", "protein shake", "coffee and a roll",
    "tea and biscuits", "hot chocolate and toast", "leftover pizza", "leftover pasta",
    "cold rice with egg", "soup and bread",
)
DISH_ALIASES = (
    ("cheese omelet", "cheese omelette"), ("ham omelet", "ham omelette"),
    ("oatmeal", "porridge"), ("granola with yogurt", "granola with yoghurt"),
    ("yogurt with berries", "yoghurt with berries"),
    ("scrambled egg", "scrambled eggs"), ("fried egg", "fried eggs"),
    ("poached egg", "poached eggs"), ("boiled egg", "boiled eggs"),
    ("eggs and bacon", "bacon and eggs"), ("full english", "full english breakfast"),
    ("english breakfast", "full english breakfast"), ("chocolate croissant", "pain au chocolat"),
    ("waffles", "blueberry waffles"), ("sausage and baked beans", "sausage and beans"),
)

JOBS = (
    "baker", "nurse", "electrician", "plumber", "teacher", "carpenter", "accountant",
    "architect", "pharmacist", "dentist", "doctor", "engineer", "journalist", "translator",
    "librarian", "chef", "waiter", "cashier", "mechanic", "pilot", "paramedic",
    "firefighter", "photographer", "gardener", "florist", "tailor", "butcher", "barber",
    "courier", "bookkeeper", "lawyer", "surveyor", "actuary", "curator", "optician",
    "physiotherapist", "veterinarian", "welder", "locksmith", "roofer", "painter",
    "designer", "programmer", "analyst", "auditor", "receptionist", "social worker",
    "tutor", "coach", "bus driver", "taxi driver", "cleaner", "security guard", "midwife",
    "chemist", "historian", "mason", "brewer",
)
JOB_ALIASES = (
    ("vet", "veterinarian"), ("developer", "programmer"), ("software developer", "programmer"),
    ("solicitor", "lawyer"), ("attorney", "lawyer"), ("fireman", "firefighter"),
    ("physio", "physiotherapist"), ("physician", "doctor"),
)

RELATIONS = (
    "sister", "brother", "mother", "father", "cousin", "aunt", "uncle", "niece", "nephew",
    "grandmother", "grandfather", "neighbour", "colleague", "boss", "landlord", "tenant",
    "flatmate", "classmate", "mentor", "godmother", "godfather", "stepbrother",
    "stepsister", "partner", "old friend", "best friend", "barber", "dentist", "doctor",
    "accountant", "trainer", "therapist", "babysitter", "cleaner",
)
RELATION_ALIASES = (
    ("neighbor", "neighbour"), ("co worker", "colleague"), ("coworker", "colleague"),
    ("grandma", "grandmother"), ("grandpa", "grandfather"), ("mum", "mother"),
    ("mom", "mother"), ("dad", "father"), ("landlady", "landlord"), ("flat mate", "flatmate"),
)

SHOP_TYPES = (
    "pharmacy", "bakery", "butcher", "florist", "bookshop", "hardware store", "greengrocer",
    "newsagent", "barber shop", "hair salon", "cafe", "bistro", "delicatessen",
    "off licence", "post office", "stationery shop", "toy shop", "shoe shop", "fishmonger",
    "cheese shop", "tea room", "record shop", "jeweller", "optician", "laundrette",
    "dry cleaner", "garden centre", "bike shop", "pet shop", "tailor",
)
SHOP_TYPE_ALIASES = (("bookstore", "bookshop"), ("drugstore", "pharmacy"), ("chemist", "pharmacy"),
                     ("deli", "delicatessen"), ("hardware shop", "hardware store"))

STORY_KINDS = (
    "flood", "fire", "strike", "festival", "road closure", "bridge collapse", "marathon",
    "election", "heatwave", "storm", "power cut", "train delay", "factory closure",
    "museum opening", "trial", "robbery", "rescue", "parade", "concert", "street fair",
    "protest", "shipwreck", "landslide", "drought", "regatta", "auction", "carnival",
    "airport delay", "bus crash", "gas leak", "cargo spill",
)

ERRANDS = (
    "dentist", "doctor", "gym", "library", "barber", "hairdresser", "post office", "bank",
    "vet", "dry cleaner", "pharmacy", "optician", "physio", "market", "bakery",
    "supermarket", "cinema", "swimming pool", "laundrette", "garage", "tax office",
    "town hall", "hospital", "florist", "butcher", "chiropractor", "dermatologist",
    "notary", "cobbler", "car wash",
)

#: Saturday closing times: 14:00 to 19:45 in quarter hours, 24 values.
TIMES = tuple("%02d:%02d" % (h, m) for h in range(14, 20) for m in (0, 15, 30, 45))
COUNTS = tuple(str(i) for i in range(1, 25))
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december")
NUMBER_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty", "twenty one", "twenty two", "twenty three",
    "twenty four",
)
COUNT_ALIASES = tuple((NUMBER_WORDS[i], str(i)) for i in range(1, 25))

POOLS = {
    "colours": COLOURS, "dishes": DISHES, "jobs": JOBS, "relations": RELATIONS,
    "shop_types": SHOP_TYPES, "story_kinds": STORY_KINDS, "errands": ERRANDS,
    "times": TIMES, "counts": COUNTS, "weekdays": WEEKDAYS, "months": MONTHS,
}
POOL_ALIASES = {
    "colours": COLOUR_ALIASES, "dishes": DISH_ALIASES, "jobs": JOB_ALIASES,
    "relations": RELATION_ALIASES, "shop_types": SHOP_TYPE_ALIASES, "counts": COUNT_ALIASES,
}

#: Predicate / slot name -> vocabulary id. Pass a 'pool:<id>' or 'kind:<kind>' string
#: to closed_vocab directly for anything not listed here.
SLOTS = {
    "breakfast": "pool:dishes", "dish": "pool:dishes",
    "vehicle_colour": "pool:colours", "car_colour": "pool:colours", "colour": "pool:colours",
    "works_as": "pool:jobs", "job": "pool:jobs",
    "relation": "pool:relations", "closing_time": "pool:times", "time": "pool:times",
    "visit_count": "pool:counts", "count": "pool:counts", "errand": "pool:errands",
    "story_kind": "pool:story_kinds", "shop_type": "pool:shop_types",
    "weekday": "pool:weekdays", "month": "pool:months",
    "lives_in": "kind:city", "city": "kind:city", "visited": "kind:city",
    "works_at": "kind:org", "employer": "kind:org",
    "companion": "kind:person", "person": "kind:person", "told_by": "kind:person",
    "shop": "kind:shop", "street": "kind:street",
}

#: Words that must never be generated as names: every pool value and alias, plus a few
#: ordinary words that the syllable grammar could spell.
RESERVED = frozenset(
    [norm(v) for pool in POOLS.values() for v in pool]
    + [norm(a) for al in POOL_ALIASES.values() for a, _ in al]
    + [
        # ordinary words the consonant-vowel grammar can spell
        "banana", "tomato", "karate", "sonata", "tuna", "tuba", "soda", "sedan", "robin",
        "sonar", "mono", "memo", "demo", "gene", "menu", "sumo", "saga", "toga", "polo",
        "lava", "cola", "hula", "pupil", "sari", "taro", "mimosa", "kimono", "domino",
        "bikini", "ramen", "yoyo", "fava", "tiger", "bison",
        # well-known real places the grammar can spell
        "roma", "rome", "riga", "baku", "sudan", "niger", "togo", "gabon", "kobe", "nara",
        "tunis", "dakar", "turin", "rimini", "fiji", "fuji", "java", "pula",
    ])


# ----------------------------------------------------------------- closed vocabularies


@dataclass(frozen=True)
class Vocab:
    """A closed vocabulary: canonical values plus (alias, canonical) pairs.

    ``index`` maps every normalised surface form (value or alias) to its canonical
    value; building it raises ValueError if one surface form names two values.
    ``matches`` is the reference longest-match routine for candidate extraction."""

    vocab_id: str
    values: tuple[str, ...]
    aliases: tuple[tuple[str, str], ...] = ()

    @cached_property
    def index(self) -> dict:
        idx: dict = {}
        canon = set(self.values)
        for v in self.values:
            idx[norm(v)] = v
        for alias, target in self.aliases:
            if target not in canon:
                raise ValueError("alias %r points at %r which is not in %s"
                                 % (alias, target, self.vocab_id))
            key = norm(alias)
            if idx.get(key, target) != target:
                raise ValueError("surface form %r names both %r and %r in %s"
                                 % (alias, idx[key], target, self.vocab_id))
            idx[key] = target
        return idx

    @cached_property
    def max_words(self) -> int:
        """Token count of the longest surface form (0 for an empty vocabulary)."""
        return max((len(k.split()) for k in self.index), default=0)

    def __len__(self) -> int:
        return len(self.values)

    def canonical(self, surface: str) -> str | None:
        """Canonical value of an exact surface form (after ``norm``), else None."""
        return self.index.get(norm(surface))

    def spans(self, text: str) -> list[tuple[int, int, str]]:
        """Longest-match scan over the normalised tokens of ``text``, left to right and
        non-overlapping: a list of (first token, end token, canonical value)."""
        toks = norm(text).split()
        idx = self.index
        out: list[tuple[int, int, str]] = []
        i, n = 0, len(toks)
        while i < n:
            hit = None
            for length in range(min(self.max_words, n - i), 0, -1):
                canon = idx.get(" ".join(toks[i:i + length]))
                if canon is not None:
                    hit = (i, i + length, canon)
                    break
            if hit is None:
                i += 1
            else:
                out.append(hit)
                i = hit[1]
        return out

    def matches(self, text: str) -> list[str]:
        """Distinct canonical values found in ``text``, in order of first occurrence."""
        seen: list[str] = []
        for _, _, canon in self.spans(text):
            if canon not in seen:
                seen.append(canon)
        return seen

    def with_aliases(self, extra: tuple[tuple[str, str], ...]) -> "Vocab":
        return Vocab(self.vocab_id, self.values, self.aliases + tuple(extra))


def pool_vocab(pool_id: str) -> Vocab:
    """The vocabulary of a static pool (all of its values, not a world's subset)."""
    return Vocab("pool:" + pool_id, POOLS[pool_id], POOL_ALIASES.get(pool_id, ()))


def kind_vocab(world: "World", kind: str) -> Vocab:
    """The names (and aliases) of all of the world's entities of a kind."""
    ents = world.entities_of(kind)
    values = tuple(e.name for e in ents)
    aliases = tuple((a, e.name) for e in ents for a in e.aliases)
    return Vocab("kind:" + kind, values, aliases)


def closed_vocab(world: "World", slot: str) -> Vocab:
    """The closed vocabulary of a slot for a world.

    ``slot`` is a predicate name from ``SLOTS`` ('breakfast', 'lives_in', ...) or a
    vocabulary id ('pool:colours', 'kind:person'). Static pools return the whole pool;
    entity kinds return all entities of that kind in the world, mentioned or not."""
    vid = SLOTS.get(slot, slot)
    scheme, _, ident = vid.partition(":")
    if scheme == "pool" and ident in POOLS:
        return pool_vocab(ident)
    if scheme == "kind":
        return kind_vocab(world, ident)
    raise KeyError("unknown slot or vocabulary id: %r" % (slot,))


def _self_check() -> None:
    for pid in ("colours", "dishes", "jobs", "relations", "shop_types", "story_kinds",
                "errands", "times", "counts"):
        pool = POOLS[pid]
        if len(pool) < 24 or len(set(pool)) != len(pool):
            raise ValueError("pool %s must hold at least 24 distinct values" % pid)
    if len(COLOURS) != 40 or len(DISHES) != 120 or len(TIMES) != 24:
        raise ValueError("COLOURS must hold 40, DISHES 120 and TIMES 24 values")
    for pid in POOLS:
        pool_vocab(pid).index  # raises on any ambiguous alias


_self_check()
