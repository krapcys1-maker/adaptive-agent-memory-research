"""Exact, deterministic scorers for LifeSim answers, plus the small statistics around them.

What this module provides
-------------------------
* ``normalise``: the one text normaliser (it IS ``vocab.norm``: NFKC, casefold, accents
  stripped, punctuation to spaces).
* ``parse_answer``: splits a reply into the answer body and the ``CONF: 0-100`` field.
* ``extract_candidates(text, vocab)``: the distinct canonical values of a closed
  vocabulary found in a text by longest match, with aliases (``Vocab.matches``); for the
  time pool and the count pool it first runs the time normaliser or the integer parser.
* ``parse_times`` ('6pm', '18:00', 'six in the evening', 'half past six' -> 'HH:MM'),
  ``parse_numbers``/``parse_integers`` (digits, number words, 'twice'), ``parse_dates``
  (ISO dates, '14 March 2027', 'March 14th, 2027', '14/03/2027'), ``parse_letters``
  (option letters of a forced-choice question), ``parse_yes_no`` and ``is_abstention``
  (the UNKNOWN lexicon).
* ``score(query, answer)`` -> ``ScoreRecord`` and ``Scorer`` (caches the closed vocabularies
  of one world). The rule for every closed-vocabulary family: correct iff the candidate
  set equals {gold}; two or more candidates is a hedge and is wrong; no candidate is
  'unmatched' and is wrong and logged; ``error_type`` of a single wrong candidate comes
  from the query's ``near_miss`` list (stale, adjacent_day, confuser, habit), else
  'commission'. Counts need exactly one integer; times exactly one time; ME1 needs an
  abstention with no candidate; the cost-weighted score is +1 correct, 0 abstain, -1 wrong.
* ``cluster_bootstrap`` (10,000 draws over worlds by default) and ``cluster_bootstrap_diff``,
  plus ``brier``, ``ece``, ``auroc`` and ``confident_wrong_rate`` for the ME2 confidence field.

Conventions and caveats
-----------------------
* ``score(query, answer)`` takes a string or any object with ``.text`` (optionally
  ``.abstained`` and ``.confidence``, e.g. ``LifeAnswer``). Entity-valued questions (cities,
  people, shops) need the world's entity names to detect a hedge reliably: pass ``world=`` (or
  ``vocab=``), or use ``Scorer(world)``. Without them only the static pools are known and the
  fallback vocabulary is the gold value, its aliases, the near-miss values and the options.
* A reply that restates the question is not special-cased: a candidate that is also a cue
  value counts like any other.
* CONF: a missing or out-of-range field sets ``parse_ok`` False but never changes whether the
  answer is correct (a system that cannot report confidence is not penalised in accuracy).
  A reply whose body is empty is a ``parse_failure``.
* Time answers without am/pm and with an hour below 12 are read as afternoon or evening
  (``prefer_pm``), because the closing-time pool runs from 14:00 to 19:45; this is a reading
  rule of the scorer, written down here, not a claim about people.

Every sum of floats uses ``math.fsum`` (Python 3.12 made ``sum`` compensated and 3.11 did not, so a
plain ``sum`` would differ in the last bit between interpreters).

What this module does NOT do: it calls no model and no judge, reads no clock, uses neither
``random`` nor ``hash()`` nor numpy/scipy, does not handle inflection beyond the vocabulary
aliases, does not understand free text answers (it only finds closed-vocabulary values in
them), does not score the v0.1/v0.2 families beyond the generic entity, count, time, date,
letter, yes/no and class rules, and does not decide which items are kept (``queries`` does).
"""

from __future__ import annotations

import datetime as _dt
import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Sequence

from .rng import stream as _stream
from .schema import Query, ScoreRecord
from .vocab import NUMBER_WORDS, POOLS, Vocab, closed_vocab, norm, pool_vocab

__all__ = [
    "normalise", "Parsed", "parse_answer", "extract_candidates", "parse_times", "parse_numbers",
    "parse_integers", "parse_dates", "parse_letters", "parse_yes_no", "is_abstention",
    "ABSTAIN_STRONG", "ABSTAIN_WEAK", "score", "Scorer", "Bootstrap", "cluster_bootstrap",
    "cluster_bootstrap_diff", "brier", "ece", "auroc", "confident_wrong_rate",
]

normalise = norm

# ------------------------------------------------------------------------ low-level folding


def _fold(text: str) -> str:
    """Casefold and strip accents but keep punctuation (times and decimals need it)."""
    t = unicodedata.normalize("NFKC", text).casefold()
    t = unicodedata.normalize("NFD", t)
    return "".join(ch for ch in t if unicodedata.category(ch) != "Mn")


_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
    "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=lambda m: (-len(m), m)))
_UNITS = {w: i for i, w in enumerate(NUMBER_WORDS[:20])}  # zero .. nineteen
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
         "eighty": 80, "ninety": 90}
_ONCE = {"once": 1, "twice": 2, "thrice": 3}
_HOUR_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
               "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
_HOUR_RE = "|".join(sorted(_HOUR_WORDS, key=lambda w: (-len(w), w)))
_MIN_WORDS = {
    "fifteen": 15, "thirty": 30, "forty five": 45, "forty-five": 45, "fortyfive": 45,
    "ten": 10, "twenty": 20, "twenty five": 25, "twenty-five": 25, "thirty five": 35,
    "thirty-five": 35, "forty": 40, "fifty": 50, "fifty five": 55, "fifty-five": 55,
    "oh five": 5, "o five": 5, "oh-five": 5, "oh ten": 10, "oh-ten": 10,
}
_MIN_RE = "|".join(sorted((re.escape(k) for k in _MIN_WORDS), key=lambda k: (-len(k), k)))
_PAST_TO_MIN = {"five": 5, "ten": 10, "twenty": 20, "twenty five": 25, "twenty-five": 25,
                "quarter": 15, "half": 30}
_PAST_TO_RE = "|".join(sorted((re.escape(k) for k in _PAST_TO_MIN), key=lambda k: (-len(k), k)))

_DATE_STRIP = [
    re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"),
    re.compile(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"),
    re.compile(r"\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?"),
    re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:%s)\b\.?(?:,?\s*\d{4})?" % _MONTH_RE),
    re.compile(r"\b(?:%s)\b\.?\s+\d{1,2}(?:st|nd|rd|th)?\b(?:,?\s*\d{4})?" % _MONTH_RE),
]


def _strip_dates_and_times(folded: str) -> str:
    out = folded
    for rx in _DATE_STRIP:
        out = rx.sub(lambda m: " " * len(m.group(0)), out)
    return out


# ------------------------------------------------------------------------ numbers and counts

_NUM_TOKEN = re.compile(r"(?<![a-z0-9.])(\d+(?:\.\d+)?)(?![a-z0-9])|([a-z]+)")


def parse_numbers(text: str) -> list:
    """Numbers found in a text, in order: digits (also decimals), number words
    ('three', 'twenty-one'), 'once', 'twice', 'thrice'. Dates and clock times are removed
    first so that '2027-03-14' or '18:00' never count as numbers. Integer-valued numbers
    are ints, others floats."""
    t = _strip_dates_and_times(_fold(text))
    toks = []
    for m in _NUM_TOKEN.finditer(t):
        toks.append(("n", m.group(1)) if m.group(1) is not None else ("w", m.group(2)))
    out: list = []
    i = 0
    while i < len(toks):
        kind, tok = toks[i]
        if kind == "n":
            v = float(tok) if "." in tok else int(tok)
            if isinstance(v, float) and v == int(v):
                v = int(v)
            out.append(v)
            i += 1
            continue
        if tok in _TENS:
            nxt = toks[i + 1][1] if i + 1 < len(toks) and toks[i + 1][0] == "w" else ""
            if nxt in _UNITS and 1 <= _UNITS[nxt] <= 9:
                out.append(_TENS[tok] + _UNITS[nxt])
                i += 2
                continue
            out.append(_TENS[tok])
        elif tok in _UNITS:
            out.append(_UNITS[tok])
        elif tok in _ONCE:
            out.append(_ONCE[tok])
        i += 1
    return out


def parse_integers(text: str) -> list[int]:
    """The integer-valued numbers of ``parse_numbers`` (as ints), in order."""
    return [v for v in parse_numbers(text) if isinstance(v, int)]


# ------------------------------------------------------------------------------------ times

_T_COLON = re.compile(r"(?<![\d:.])(\d{1,2})[:.]([0-5]\d)(?![\d])(?:\s*(a\.?\s?m\.?|p\.?\s?m\.?)(?![a-z]))?")
_T_AMPM = re.compile(r"(?<![\d:.])(\d{1,2})\s*(a\.?\s?m\.?|p\.?\s?m\.?)(?![a-z])")
_T_OCLOCK = re.compile(r"(?<![\d:.])(\d{1,2})\s*o'?\s?clock")
_T_HQ = re.compile(r"\b(half|quarter)\s+(past|to)\s+(\d{1,2}|%s)\b" % _HOUR_RE)
_T_MINPT = re.compile(r"\b(%s|\d{1,2})\s+(?:minutes\s+)?(past|to)\s+(\d{1,2}|%s)\b" % (_PAST_TO_RE, _HOUR_RE))
_T_WORDMIN = re.compile(r"\b(%s)[ -]+(%s)\b" % (_HOUR_RE, _MIN_RE))
_T_WORDPER = re.compile(r"\b(%s)\s+(?:o'?\s?clock|(a\.?\s?m\.?|p\.?\s?m\.?)(?![a-z])|in the (morning|afternoon|evening)|at night)" % _HOUR_RE)
_T_NOON = re.compile(r"\b(noon|midday|midnight)\b")
_T_MIL = re.compile(r"(?<![\d:.])([01]\d|2[0-3])([0-5]\d)\s*(?:h|hrs|hours)\b")
_T_PERIOD_AFTER = re.compile(r"^\s*(?:,\s*)?(?:(a\.?\s?m\.?|p\.?\s?m\.?)(?![a-z])|(?:in the |this |at )?(morning|afternoon|evening|night))")


def _hour_value(token: str) -> int:
    return _HOUR_WORDS[token] if token in _HOUR_WORDS else int(token)


def _resolve_hour(hour: int, mer: str | None, prefer_pm: bool, padded: bool = False) -> int | None:
    """Hour on the 24-hour clock from an hour and an optional meridiem; None if invalid."""
    if hour < 0 or hour > 23:
        return None
    if hour == 0 or hour >= 13:
        return hour
    if mer == "pm":
        return hour % 12 + 12
    if mer == "am":
        return hour % 12
    if padded or hour == 12:
        return hour
    return hour + 12 if prefer_pm else hour


def _mer_of(token: str | None) -> str | None:
    if not token:
        return None
    t = token.replace(".", "").replace(" ", "")
    return "pm" if t.startswith("p") else "am" if t.startswith("a") else None


def _period_after(folded: str, end: int) -> str | None:
    m = _T_PERIOD_AFTER.match(folded[end:end + 32])
    if not m:
        return None
    if m.group(1):
        return _mer_of(m.group(1))
    return "am" if m.group(2) == "morning" else "pm"


def parse_times(text: str, prefer_pm: bool = True) -> list[str]:
    """Clock times found in a text as canonical 'HH:MM' strings, distinct, in order of first
    occurrence. Understands '18:00', '6:30 pm', '6pm', '6 o'clock', 'six in the evening',
    'six thirty', 'half past six', 'quarter to seven', 'ten past six', 'noon', '1830 hrs'.
    A bare hour with no minutes and no marker ('6') is not a time. Clock times below 12 with
    no am/pm are read as pm when ``prefer_pm`` (see the module docstring); a zero-padded
    hour such as '08:00' is read as 24-hour time. Calendar dates are ignored."""
    t = _fold(text)
    for rx in _DATE_STRIP[:2]:
        t = rx.sub(lambda m: " " * len(m.group(0)), t)
    taken: list[tuple[int, int]] = []
    found: list[tuple[int, str]] = []

    def free(a: int, b: int) -> bool:
        return all(b <= s or a >= e for s, e in taken)

    def add(a: int, b: int, hour: int | None, minute: int) -> None:
        if hour is not None and 0 <= minute <= 59 and free(a, b):
            taken.append((a, b))
            found.append((a, "%02d:%02d" % (hour, minute)))

    for m in _T_COLON.finditer(t):
        h = int(m.group(1))
        mer = _mer_of(m.group(3)) or _period_after(t, m.end())
        padded = len(m.group(1)) == 2 and m.group(1)[0] == "0"
        add(m.start(), m.end(), _resolve_hour(h, mer, prefer_pm, padded), int(m.group(2)))
    for m in _T_AMPM.finditer(t):
        add(m.start(), m.end(), _resolve_hour(int(m.group(1)), _mer_of(m.group(2)), prefer_pm), 0)
    for m in _T_OCLOCK.finditer(t):
        mer = _period_after(t, m.end())
        add(m.start(), m.end(), _resolve_hour(int(m.group(1)), mer, prefer_pm), 0)
    for m in _T_HQ.finditer(t):
        h = _hour_value(m.group(3))
        base = 15 if m.group(1) == "quarter" else 30
        if m.group(2) == "to":
            h, minute = h - 1, 60 - base
        else:
            minute = base
        mer = _period_after(t, m.end())
        hh = _resolve_hour(h % 12 if h % 12 else 12, mer, prefer_pm)
        add(m.start(), m.end(), hh, minute)
    for m in _T_MINPT.finditer(t):
        key = m.group(1)
        mins = _PAST_TO_MIN[key] if key in _PAST_TO_MIN else int(key)
        h = _hour_value(m.group(3))
        if m.group(2) == "to":
            h, minute = h - 1, 60 - mins
        else:
            minute = mins
        mer = _period_after(t, m.end())
        add(m.start(), m.end(), _resolve_hour(h % 12 if h % 12 else 12, mer, prefer_pm), minute)
    for m in _T_WORDMIN.finditer(t):
        mer = _period_after(t, m.end())
        add(m.start(), m.end(), _resolve_hour(_HOUR_WORDS[m.group(1)], mer, prefer_pm),
            _MIN_WORDS[m.group(2)])
    for m in _T_WORDPER.finditer(t):
        if m.group(2):
            mer = _mer_of(m.group(2))
        elif m.group(3):
            mer = "am" if m.group(3) == "morning" else "pm"
        elif "night" in m.group(0):
            mer = "pm"
        else:
            mer = None
        add(m.start(), m.end(), _resolve_hour(_HOUR_WORDS[m.group(1)], mer, prefer_pm), 0)
    for m in _T_NOON.finditer(t):
        add(m.start(), m.end(), 0 if m.group(1) == "midnight" else 12, 0)
    for m in _T_MIL.finditer(t):
        add(m.start(), m.end(), int(m.group(1)), int(m.group(2)))
    found.sort()
    out: list[str] = []
    for _, v in found:
        if v not in out:
            out.append(v)
    return out


# ------------------------------------------------------------------------------------ dates

_D_ISO = re.compile(r"(?<!\d)(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?!\d)")
_D_DMY_WORD = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(%s)\b\.?(?:,?\s*(\d{4}))?" % _MONTH_RE)
_D_MDY_WORD = re.compile(r"\b(%s)\b\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s*(\d{4}))?" % _MONTH_RE)
_D_NUM = re.compile(r"(?<![\d.])(\d{1,2})[./](\d{1,2})[./](\d{4})(?!\d)")


def parse_dates(text: str, default_year: int | None = None) -> list[str]:
    """Calendar dates in a text as ISO 'YYYY-MM-DD', distinct, in order of occurrence:
    '2027-03-14', '14 March 2027', 'March 14th, 2027', '14/03/2027' and '14.03.2027'
    (day first). A date without a year needs ``default_year``; impossible dates are ignored."""
    t = _fold(text)
    taken: list[tuple[int, int]] = []
    found: list[tuple[int, str]] = []

    def put(a: int, b: int, y: int | None, mo: int, d: int) -> None:
        if y is None or any(not (b <= s or a >= e) for s, e in taken):
            return
        try:
            iso = _dt.date(y, mo, d).isoformat()
        except ValueError:
            return
        taken.append((a, b))
        found.append((a, iso))

    for m in _D_ISO.finditer(t):
        put(m.start(), m.end(), int(m.group(1)), int(m.group(2)), int(m.group(3)))
    for m in _D_DMY_WORD.finditer(t):
        y = int(m.group(3)) if m.group(3) else default_year
        put(m.start(), m.end(), y, _MONTHS[m.group(2)], int(m.group(1)))
    for m in _D_MDY_WORD.finditer(t):
        y = int(m.group(3)) if m.group(3) else default_year
        put(m.start(), m.end(), y, _MONTHS[m.group(1)], int(m.group(2)))
    for m in _D_NUM.finditer(t):
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if b > 12 and a <= 12:  # clearly month first (03/14/2027)
            a, b = b, a
        put(m.start(), m.end(), y, b, a)
    found.sort()
    out: list[str] = []
    for _, v in found:
        if v not in out:
            out.append(v)
    return out


# ------------------------------------------------------------------ letters, yes/no, abstention

_LETTERS = "abcdefgh"
_L_WHOLE = re.compile(r"^\s*[\(\[]?([a-h])[\)\]]?[\s.:\-]*$", re.I)
_L_START = re.compile(r"^\s*[\(\[]?([a-h])[\)\].:]\s+\S", re.I)
_L_PHRASE = re.compile(r"\b(?:answer|option|choice|letter)\s*(?:is|:|=)?\s*[\(\[]?([a-h])\b(?![a-z])", re.I)
_L_CHOOSE = re.compile(r"\b(?:choose|pick|select|go with)\s+[\(\[]?([a-h])\b(?![a-z])", re.I)
_L_LISTCHECK = re.compile(
    r"^\s*(?:[\(\[]?[a-h][\)\]]?\s*(?:,|/|&|or|and)\s*)+[\(\[]?[a-h][\)\]]?[\s.]*$", re.I)
_L_ISOLATED = re.compile(r"(?<![a-z])([a-h])(?![a-z])", re.I)


def parse_letters(text: str, n_options: int = 4) -> list[str]:
    """Option letters (A, B, ...) named by a reply to a forced-choice question: the whole reply
    is a letter ('B', '(b)', 'B)'), it starts with one ('B) porridge'), it lists several ('B or C',
    'A, B'), or it says 'answer is B', 'option C', 'I choose D'. A stray 'a' or 'I' inside a sentence is not a letter. Distinct,
    upper case, in order; letters beyond ``n_options`` are ignored."""
    found: list[tuple[int, str]] = []
    for rx in (_L_WHOLE, _L_START, _L_PHRASE, _L_CHOOSE):
        for m in rx.finditer(text):
            found.append((m.start(1), m.group(1).upper()))
    if _L_LISTCHECK.match(text):  # 'B or C', 'A, B and D', 'b/c': every letter is named
        for m in _L_ISOLATED.finditer(text):
            found.append((m.start(1), m.group(1).upper()))
    found.sort()
    out: list[str] = []
    for _, letter in found:
        if _LETTERS.index(letter.lower()) < n_options and letter not in out:
            out.append(letter)
    return out


_YES = frozenset(["yes", "yeah", "yep", "yup", "true", "correct", "affirmative"])
_NO = frozenset(["no", "nope", "false", "incorrect", "negative"])


def parse_yes_no(text: str) -> list[str]:
    """'yes' and/or 'no' found among the words of a reply (both = a hedge)."""
    toks = norm(text).split()
    out: list[str] = []
    for tok in toks:
        v = "yes" if tok in _YES else "no" if tok in _NO else ""
        if v and v not in out:
            out.append(v)
    return out


#: Explicit statements of not knowing: they always make a reply an abstention.
ABSTAIN_STRONG = tuple(sorted(norm(p) for p in (
    "unknown", "i don't know", "i do not know", "i dont know", "don't know", "do not know",
    "i don't recall", "i do not recall", "i can't recall", "i cannot recall", "can't recall",
    "cannot recall", "can not recall", "i don't remember", "i do not remember",
    "i can't remember", "i cannot remember", "don't remember", "do not remember",
    "no memory of", "no recollection", "not mentioned", "never mentioned", "was not mentioned",
    "wasn't mentioned", "not stated", "never stated", "wasn't stated", "no record",
    "no records", "not recorded", "no information", "no data", "not in my notes",
    "not in the notes", "not in the log", "never said", "didn't say", "did not say",
    "never told me", "i was never told", "you never told me", "no mention", "nothing about",
    "nothing was said", "can't say", "cannot say", "can't tell", "cannot tell",
    "can't determine", "cannot determine", "unable to determine", "unable to answer",
    "not able to answer", "insufficient information", "not enough information",
    "no such trip", "no such", "never happened", "did not happen", "didn't happen",
    "no idea", "i have no idea",
)))
#: Soft statements of doubt: an abstention only when no candidate value is in the reply.
ABSTAIN_WEAK = tuple(sorted(norm(p) for p in (
    "not sure", "i'm not sure", "unsure", "uncertain", "no clue", "can't be sure",
    "not certain", "i am not sure",
)))


def _has_phrase(padded: str, phrases: Sequence[str]) -> bool:
    return any((" %s " % p) in padded for p in phrases)


def is_abstention(text: str, has_candidates: bool = False) -> bool:
    """True if the reply declines to answer: a strong phrase (UNKNOWN, 'I don't know', 'no
    record', ...) or, when no candidate value is present, a weak one ('not sure')."""
    padded = " %s " % norm(text)
    if _has_phrase(padded, ABSTAIN_STRONG):
        return True
    return (not has_candidates) and _has_phrase(padded, ABSTAIN_WEAK)


# --------------------------------------------------------------------------- reply parsing

_CONF = re.compile(
    r"(?:[\(\[]\s*)?\bconf(?:idence)?\b(?:\s+level)?\s*[:=]?\s*\(?\s*(\d{1,3}(?:\.\d+)?)(?!\d)\s*(?:%|/\s*100)?\s*[\)\]]?"
    r"(?!\s*[-\u2013]\s*\d)(?![\d.]*[a-z])", re.I)


@dataclass(frozen=True)
class Parsed:
    """A reply split into the answer body and the CONF field.

    ``conf`` is the 0-100 integer (None when missing or out of range); ``conf_found`` says that a
    CONF field was present at all; ``parse_ok`` is False when the body is empty or, with
    ``conf_required``, when the CONF field is missing or invalid."""

    body: str
    conf: int | None
    conf_found: bool
    parse_ok: bool


def parse_answer(text: str, conf_required: bool = True) -> Parsed:
    """Split a reply into answer body and ``CONF: 0-100``.

    Accepted forms: 'CONF: 85', 'CONFIDENCE = 85%', 'conf 85/100'. The last CONF field wins and
    all of them are removed from the body. A literal echo of the instruction ('CONF: 0-100'),
    a value above 100 and a fraction below 1 (0.85, ambiguous) are invalid; other decimals are
    rounded half up."""
    raw = text if isinstance(text, str) else str(text)
    conf: int | None = None
    found = False
    for m in _CONF.finditer(raw):
        found = True
        val = float(m.group(1))
        if val > 100 or 0 < val < 1:
            conf = None
        else:
            conf = int(math.floor(val + 0.5))
    body = _CONF.sub(" ", raw).strip()
    ok = bool(body) and (conf is not None or not conf_required)
    return Parsed(body=body, conf=conf, conf_found=found, parse_ok=ok)


# -------------------------------------------------------------------- candidate extraction


def _canon_number(v: Any) -> str:
    return str(v)


_LIST_SPLIT = re.compile(r"[,;/|\n\r()\[\]{}]+")


def extract_candidates(text: str, vocab: Vocab, prefer_pm: bool = True) -> list[str]:
    """Distinct canonical values of ``vocab`` found in ``text``, by longest match over the
    normalised tokens with aliases, in order of first occurrence. Commas, semicolons, slashes,
    bars, line breaks and brackets separate candidates ('silver, grey' lists two colours; it is
    not the alias 'silver grey'); other punctuation is stripped by the normaliser first. The time pool goes through
    ``parse_times`` and the count pool through the integer parser first, so '6pm' and 'three'
    are found; every parsed time or integer is kept even when it is not in the pool (a wrong
    answer, not an unmatched one)."""
    vid = vocab.vocab_id
    if vid == "pool:times":
        return parse_times(text, prefer_pm=prefer_pm)
    if vid == "pool:counts":
        out: list[str] = []
        for v in parse_numbers(text):
            s = _canon_number(v)
            if s not in out:
                out.append(s)
        return out
    found: list[str] = []
    for segment in _LIST_SPLIT.split(text):  # list punctuation separates candidates
        for c in vocab.matches(segment):
            if c not in found:
                found.append(c)
    return found


def _fallback_vocab(query: Query) -> Vocab:
    g = query.gold
    values: list[str] = []
    head = () if g.kind == "unknown" else (g.value,)
    for v in head + tuple(n.value for n in g.near_miss) + tuple(query.options):
        if v and v not in values:
            values.append(v)
    aliases = tuple((a, g.value) for a in g.aliases if g.value in values and a != g.value
                    and norm(a) not in {norm(v) for v in values})
    try:
        voc = Vocab(g.vocab_id or "gold", tuple(values), aliases)
        voc.index  # noqa: B018 - raises on an ambiguous alias
        return voc
    except ValueError:
        return Vocab(g.vocab_id or "gold", tuple(values), ())


def _vocab_for(query: Query, vocab: Vocab | None, world: Any) -> Vocab:
    if vocab is not None:
        return vocab
    vid = query.gold.vocab_id
    if vid:
        scheme, _, ident = vid.partition(":")
        if scheme == "pool" and ident in POOLS:
            return pool_vocab(ident)
        if world is not None:
            try:
                return closed_vocab(world, vid)
            except KeyError:
                pass
    return _fallback_vocab(query)


def _options_vocab(base: Vocab, options: Sequence[str]) -> Vocab:
    """The vocabulary of a forced-choice question: its options, with the base aliases that
    point at an option."""
    opts = tuple(options)
    optset = set(opts)
    aliases = tuple((a, c) for a, c in _alias_pairs(base) if c in optset)
    try:
        voc = Vocab(base.vocab_id, opts, aliases)
        voc.index  # noqa: B018
        return voc
    except ValueError:
        return Vocab(base.vocab_id, opts, ())


def _alias_pairs(voc: Vocab) -> tuple:
    # all surface forms that differ from their canonical value, as (surface, canonical)
    pairs = [(k, v) for k, v in voc.index.items() if norm(v) != k]
    return tuple(sorted(pairs))


def _unpack(answer: Any) -> tuple[str, bool, int | None]:
    if isinstance(answer, str):
        return answer, False, None
    text = getattr(answer, "text", None)
    if text is None:
        raise TypeError("answer must be a string or have a .text attribute, got %r" % (type(answer),))
    conf = getattr(answer, "confidence", None)
    if conf is not None and not (isinstance(conf, int) and not isinstance(conf, bool) and 0 <= conf <= 100):
        conf = None
    return text, bool(getattr(answer, "abstained", False)), conf


def _error_from_near_miss(query: Query, cand: str) -> str:
    key = cand
    for nm in query.gold.near_miss:
        if nm.value == key or norm(nm.value) == norm(key):
            return nm.kind
    return "commission"


def _kind_candidates(query: Query, body: str, vocab: Vocab, prefer_pm: bool) -> list[str]:
    kind = query.gold.kind
    if kind == "time":
        return parse_times(body, prefer_pm=prefer_pm)
    if kind == "count":
        out: list[str] = []
        for v in parse_numbers(body):
            s = _canon_number(v)
            if s not in out:
                out.append(s)
        return out
    if kind == "date":
        return parse_dates(body)
    if kind == "bool":
        return parse_yes_no(body)
    if kind == "letter":
        return parse_letters(body, max(len(query.options), 4))
    return extract_candidates(body, vocab, prefer_pm=prefer_pm)


def score(query: Query, answer: Any, vocab: Vocab | None = None, world: Any = None,
          prefer_pm: bool = True) -> ScoreRecord:
    """Score one answer against a query's exact gold (see the module docstring for the rule).

    ``vocab`` or ``world`` supply the closed vocabulary for entity-valued questions; ``answer``
    is a string or an object with ``.text`` (and optionally ``.abstained``, ``.confidence``)."""
    text, flag_abstain, flag_conf = _unpack(answer)
    parsed = parse_answer(text, conf_required=query.conf)
    conf = parsed.conf if parsed.conf is not None else flag_conf
    conf_ok = (not query.conf) or conf is not None
    body = parsed.body
    gold = query.gold
    voc = _vocab_for(query, vocab, world)
    extra = tuple((a, gold.value) for a in gold.aliases
                  if a != gold.value and gold.value in voc.values and norm(a) not in voc.index)
    if extra:  # aliases the gold record lists but the vocabulary does not know
        voc = voc.with_aliases(extra)

    if query.fmt == "choice":
        opts = tuple(query.options)
        ovoc = _options_vocab(voc, opts)
        cands: list[str] = []
        by_kind = _kind_candidates(query, body, ovoc, prefer_pm)
        for c in by_kind:
            if c in opts and c not in cands:
                cands.append(c)
        if gold.kind not in ("letter", "bool"):
            for letter in parse_letters(body, len(opts)):
                c = opts[_LETTERS.index(letter.lower())]
                if c not in cands:
                    cands.append(c)
        elif gold.kind == "letter":
            cands = [c for c in by_kind]
    else:
        cands = _kind_candidates(query, body, voc, prefer_pm)

    abstained = flag_abstain or is_abstention(body, has_candidates=bool(cands))
    n = len(cands)
    empty = not body.strip()
    base = dict(qid=query.qid, family=query.family, candidates=tuple(cands), conf=conf)
    parse_ok = conf_ok  # an empty reply is returned as a parse failure before this is used

    if gold.kind == "unknown":
        if abstained and n == 0:
            return ScoreRecord(correct=True, score=1.0, abstained=True, parse_ok=parse_ok,
                               cost_weighted=1.0, **base)
        if abstained:  # abstains and still names a value: a hedge
            return ScoreRecord(correct=False, score=0.0, error_type="hedge", abstained=True,
                               hedged=True, parse_ok=parse_ok, cost_weighted=-1.0, **base)
        if empty:
            return ScoreRecord(correct=False, score=0.0, error_type="parse_failure",
                               parse_ok=False, cost_weighted=0.0, **base)
        return ScoreRecord(correct=False, score=0.0, error_type="hallucination_on_abstain",
                           unmatched=(n == 0), hedged=(n > 1), parse_ok=parse_ok,
                           cost_weighted=-1.0, **base)

    if abstained and n == 0:
        return ScoreRecord(correct=False, score=0.0, error_type="omission", abstained=True,
                           parse_ok=parse_ok, cost_weighted=0.0, **base)
    if empty:
        return ScoreRecord(correct=False, score=0.0, error_type="parse_failure", parse_ok=False,
                           cost_weighted=0.0, **base)
    if abstained:  # abstains and names a value
        return ScoreRecord(correct=False, score=0.0, error_type="hedge", abstained=True,
                           hedged=True, parse_ok=parse_ok, cost_weighted=-1.0, **base)
    if n == 0:
        return ScoreRecord(correct=False, score=0.0, error_type="unmatched", unmatched=True,
                           parse_ok=parse_ok, cost_weighted=-1.0, **base)
    if n >= 2:
        return ScoreRecord(correct=False, score=0.0, error_type="hedge", hedged=True,
                           parse_ok=parse_ok, cost_weighted=-1.0, **base)

    cand = cands[0]
    accepted = {gold.value} | set(gold.aliases)
    abs_error = None
    within_one = None
    if gold.kind == "count":
        try:
            abs_error = abs(float(cand) - float(gold.value))
            within_one = abs_error <= 1.0
        except ValueError:
            pass
    ok = cand in accepted or (gold.kind in ("entity", "class") and norm(cand) in {norm(a) for a in accepted})
    sc = 1.0 if ok else 0.0
    if gold.kind == "date" and not ok:
        try:
            d1 = _dt.date.fromisoformat(cand)
            d0 = _dt.date.fromisoformat(gold.value)
            abs_error = float(abs((d1 - d0).days))
            within_one = abs_error <= 1.0
            tol = max(1.0, 0.1 * float(query.tags.delay_days))
            sc = 0.5 if abs_error <= tol else 0.0
        except ValueError:
            pass
    elif gold.kind == "date" and ok:
        abs_error, within_one = 0.0, True
    if ok:
        return ScoreRecord(correct=True, score=sc, parse_ok=parse_ok, cost_weighted=1.0,
                           abs_error=abs_error, within_one=within_one, **base)
    return ScoreRecord(correct=False, score=sc, error_type=_error_from_near_miss(query, cand),
                       parse_ok=parse_ok, cost_weighted=-1.0, abs_error=abs_error,
                       within_one=within_one, **base)


class Scorer:
    """Scores answers for one world: caches the closed vocabularies by ``vocab_id``."""

    def __init__(self, world: Any = None, prefer_pm: bool = True) -> None:
        self.world = world
        self.prefer_pm = prefer_pm
        self._cache: dict[str, Vocab] = {}

    def vocab_for(self, query: Query) -> Vocab:
        vid = query.gold.vocab_id
        if vid and vid in self._cache:
            return self._cache[vid]
        voc = _vocab_for(query, None, self.world)
        if vid and self.world is not None:
            self._cache[vid] = voc
        return voc

    def score(self, query: Query, answer: Any) -> ScoreRecord:
        return score(query, answer, vocab=self.vocab_for(query), prefer_pm=self.prefer_pm)


# ------------------------------------------------------------------------------ statistics


@dataclass(frozen=True)
class Bootstrap:
    """A cluster-bootstrap summary: the point estimate on the original clusters and the
    percentile interval ``[lo, hi]`` at level ``1 - alpha``; ``se`` is the bootstrap SD."""

    estimate: float
    lo: float
    hi: float
    se: float
    n_clusters: int
    n_boot: int
    alpha: float


def _cluster_sums(clusters: Sequence[Any]) -> list[tuple[float, int]]:
    out: list[tuple[float, int]] = []
    for c in clusters:
        if isinstance(c, (int, float)):
            out.append((float(c), 1))
        else:
            vals = [float(x) for x in c]
            out.append((math.fsum(vals), len(vals)))
    return out


def _quantile(sorted_vals: Sequence[float], p: float) -> float:
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = p * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def cluster_bootstrap(clusters: Sequence[Any], statistic: str = "mean_of_means",
                      n_boot: int = 10000, alpha: float = 0.05, seed: int = 0,
                      label: str = "boot") -> Bootstrap:
    """Percentile bootstrap over clusters (worlds are the unit), deterministic in ``seed``.

    ``clusters`` has one element per world: a number (that world's statistic, e.g. accuracy) or
    a sequence of per-query scores. ``statistic`` is 'mean_of_means' (the mean of the world
    means; the macro score) or 'pooled' (all queries pooled; large worlds weigh more). Draws use
    ``stream(seed, 'boot', label)``; the default is 10,000 draws."""
    if statistic not in ("mean_of_means", "pooled"):
        raise ValueError("statistic must be 'mean_of_means' or 'pooled'")
    if not clusters:
        raise ValueError("cluster_bootstrap needs at least one cluster")
    data = _cluster_sums(clusters)
    n = len(data)

    means = [d[0] / d[1] for d in data]

    def stat(idx: Sequence[int]) -> float:
        if statistic == "pooled":
            tot = math.fsum(data[i][0] for i in idx)
            cnt = sum(data[i][1] for i in idx)
            return tot / cnt if cnt else 0.0
        return math.fsum(means[i] for i in idx) / len(idx)

    point = stat(range(n))
    rng = _stream(seed, "boot", label)
    draws = []
    for _ in range(n_boot):
        draws.append(stat([rng.below(n) for _ in range(n)]))
    draws.sort()
    m0 = draws[0]
    mean = m0 + math.fsum(d - m0 for d in draws) / len(draws)    # shifted: constant draws give var 0
    var = math.fsum((d - mean) ** 2 for d in draws) / max(1, len(draws) - 1)
    return Bootstrap(estimate=point, lo=_quantile(draws, alpha / 2.0),
                     hi=_quantile(draws, 1.0 - alpha / 2.0), se=math.sqrt(var),
                     n_clusters=n, n_boot=n_boot, alpha=alpha)


def cluster_bootstrap_diff(a: Sequence[Any], b: Sequence[Any], **kwargs: Any) -> Bootstrap:
    """Paired contrast of two arms over the same worlds: bootstrap of the per-world mean
    differences ``mean(a_i) - mean(b_i)`` (the SIGNAL contrasts of the experiments)."""
    if len(a) != len(b):
        raise ValueError("paired clusters need equal length")
    diffs = []
    for x, y in zip(a, b):
        mx = float(x) if isinstance(x, (int, float)) else math.fsum(x) / len(x)
        my = float(y) if isinstance(y, (int, float)) else math.fsum(y) / len(y)
        diffs.append(mx - my)
    return cluster_bootstrap(diffs, **kwargs)


def brier(confs: Sequence[float], correct: Sequence[bool]) -> float:
    """Brier score of confidences (0-100) against correctness (lower is better)."""
    if len(confs) != len(correct) or not confs:
        raise ValueError("brier needs equally many confidences and outcomes, at least one")
    return math.fsum((c / 100.0 - (1.0 if ok else 0.0)) ** 2 for c, ok in zip(confs, correct)) / len(confs)


def ece(confs: Sequence[float], correct: Sequence[bool], bins: int = 10) -> float:
    """Expected calibration error with equal-width confidence bins over 0-100 (100 goes in the
    last bin): the count-weighted mean of |accuracy - mean confidence| per bin."""
    if len(confs) != len(correct) or not confs:
        raise ValueError("ece needs equally many confidences and outcomes, at least one")
    n = len(confs)
    sums = [[0, 0.0, 0.0] for _ in range(bins)]
    for c, ok in zip(confs, correct):
        b = min(bins - 1, int(c / 100.0 * bins))
        sums[b][0] += 1
        sums[b][1] += c / 100.0
        sums[b][2] += 1.0 if ok else 0.0
    total = 0.0
    for cnt, sc, sa in sums:
        if cnt:
            total += cnt / n * abs(sa / cnt - sc / cnt)
    return total


def auroc(confs: Sequence[float], correct: Sequence[bool]) -> float | None:
    """Probability that a correct answer has a higher confidence than a wrong one (ties count
    half); None if all answers are right or all are wrong."""
    pos = [c for c, ok in zip(confs, correct) if ok]
    neg = [c for c, ok in zip(confs, correct) if not ok]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for q_ in neg:
            wins += 1.0 if p > q_ else 0.5 if p == q_ else 0.0
    return wins / (len(pos) * len(neg))


def confident_wrong_rate(records: Sequence[ScoreRecord], threshold: int = 80) -> float | None:
    """Share of answers with CONF >= threshold that are wrong (None if no such answer)."""
    hi = [r for r in records if r.conf is not None and r.conf >= threshold]
    if not hi:
        return None
    return sum(1 for r in hi if not r.correct) / len(hi)
