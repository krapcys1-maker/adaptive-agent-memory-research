"""GOALSHIFT: a deterministic generator for the delayed-relevance experiment (AAM-E0).

Status: exploratory, synthetic, authored by an agent. A result on these worlds is a
result about this generator, not about real agents.

What one world contains
-----------------------
150 experiences over 30 days, three goal phases (days 1-10, 11-20, 21-30), each goal
in a different one of six domains. Twelve delayed-relevance probes, four in each of
three cells. Every probe has one target (written on day 2-9, at least 14 days before
the cue), a cue (day 21-30, a task in the *current* goal's domain), a gold answer (a
short reference code that appears in the target and nowhere in the cue), and three
decoys. Everything else is routine filler.

``C1``  lexical overlap high: about 40% of the cue's content words occur in the target.
``C2``  lexical overlap zero after stop-word removal and light stemming; same topic,
        different words. Dense retrieval is expected to win.
``C3``  lexical overlap zero; relevance **by role**. The target is a lesson (an
        unreliable outside party, a failed shortcut, a hard limit, ...) written in
        another domain; the cue is a task in the current domain to which the lesson
        applies. Topical similarity is low by construction and *measured*, not assumed.

Design rules that matter
------------------------
* The cue is rendered from the probe's own random stream and the target text only. It
  does not depend on filler, decoys or ordering, so the cue file is byte-identical
  when the history is not generated (``generate(seed, history=False)``).
* The history builder is told which names the cues use and avoids them, so a cue name
  cannot appear in an unrelated event by accident.
* Overlap is *measured* on stemmed content words (``overlap_fraction``) and enforced by
  rejection sampling; the measured value is stored with every probe.
* Pseudo-random numbers come from a private 64-bit LCG seeded through SHA-256, never
  from ``random`` or the clock, so output is identical on Python 3.11 and 3.12.
* Event ids ("e001"...) are positions in time order and carry no label. The labels
  (kind, probe, role/topic concept) live in a separate structure that arms must not read
  (only the oracle arm O is handed concepts, explicitly).

What this does not do
---------------------
It does not make the roles "real". The role clauses are short authored sentences; a
reader (or an embedding model) can pick up their vocabulary. The Stage 0 report states
how similar cue and target actually are.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "goalshift-v0.2"

N_EVENTS = 150
N_DAYS = 30
PHASES = ((1, 10), (11, 20), (21, 30))
DOMAINS = ("logistics", "hiring", "finance", "product", "security", "data")
CELLS = ("C1", "C2", "C3")
PROBES_PER_CELL = 4
LEN_MIN, LEN_MAX = 12, 35
TARGET_DAYS = (2, 9)
MIN_GAP_DAYS = 14
C1_TARGET_OVERLAP = 0.40
C1_ACCEPT = (0.28, 0.55)

#: Probability of each authored write-time consequence level (0 routine ... 3 major).
#: One distribution for every event, whatever its kind: v0.1 drew it by kind (targets
#: about twice as "consequential" as filler), which told every forgetting arm which events
#: mattered. The write-time fields (consequence and novelty) are now drawn from their own
#: stream, by position only, so they carry no information about kind, text or probe.
CONSEQUENCE_PROBS = (0.55, 0.25, 0.15, 0.05)

ASK = " Which earlier logged item bears on this, and what is its reference code?"

# --------------------------------------------------------------------------- random


class Lcg:
    """A 64-bit linear congruential generator (Knuth MMIX constants)."""

    MASK = (1 << 64) - 1

    def __init__(self, seed: int) -> None:
        self.state = seed & self.MASK
        for _ in range(4):
            self._next()

    def _next(self) -> int:
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) & self.MASK
        return self.state >> 33  # 31 usable bits

    def below(self, n: int) -> int:
        return (self._next() * n) >> 31

    def uniform(self) -> float:
        return self._next() / float(1 << 31)

    def chance(self, p: float) -> bool:
        return self._next() < p * (1 << 31)

    def choice(self, seq):
        return seq[self.below(len(seq))]

    def shuffle(self, items: list) -> None:
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]

    def sample(self, seq, k: int) -> list:
        pool = list(seq)
        self.shuffle(pool)
        return pool[:k]

    def weighted(self, probs) -> int:
        x = self._next() / float(1 << 31)
        acc = 0.0
        for i, p in enumerate(probs):
            acc += p
            if x < acc:
                return i
        return len(probs) - 1


def stream(seed: int, *labels: Any) -> Lcg:
    """An independent random stream per (seed, labels)."""
    key = "|".join([str(seed)] + [str(x) for x in labels]).encode("utf-8")
    return Lcg(int.from_bytes(hashlib.sha256(key).digest()[:8], "big"))


# ------------------------------------------------------------------------ text tools

STOPWORDS = frozenset("""
a about above after again all also am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from
further had has have having he her here hers him his how i if in into is it its itself
just me more most my no nor not now of off on once only or other our out over own same
she should so some such than that the their them then there these they this those
through to too under until up us very was we were what when where which while who whom
why will with would you your yours day days week weeks month months year years hour hours
minute minutes time times today next first last still even yet via per one two three
thousand percent new old get got make made set keep take took without within across among upon
""".split())

_TOKEN = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    """A deliberately crude stemmer: plural, -ing, -ed, -ly, trailing -e."""
    w = word
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    for suffix in ("ing", "ed", "ly"):
        if len(w) > len(suffix) + 2 and w.endswith(suffix):
            w = w[: -len(suffix)]
            break
    if len(w) > 3 and w.endswith("e"):
        w = w[:-1]
    return w


def content_tokens(text: str) -> list[tuple[str, str]]:
    """(surface, stem) for each content word: not a stop word, >= 3 letters, not
    starting with a digit (numbers and ordinals carry no topic)."""
    out = []
    for surface in _TOKEN.findall(text.lower()):
        if len(surface) < 3 or surface in STOPWORDS or surface[0].isdigit():
            continue
        out.append((surface, stem(surface)))
    return out


def stems_of(text: str) -> set[str]:
    return {s for _, s in content_tokens(text)}


def overlap_fraction(cue: str, target: str) -> float:
    """Share of the cue's distinct content stems that also occur in the target."""
    cue_stems = stems_of(cue)
    if not cue_stems:
        return 0.0
    return len(cue_stems & stems_of(target)) / len(cue_stems)


def word_count(text: str) -> int:
    return len(text.split())


# ------------------------------------------------------------------------- slot fill

_ON = ["Bar", "Cal", "Dun", "Fen", "Gar", "Hal", "Kes", "Lor", "Mar", "Nor", "Pel",
       "Quin", "Ros", "Sal", "Tar", "Vel", "Wen", "Yar", "Zor", "Bren", "Cor", "Dal",
       "Eld", "Fal"]
_MID = ["a", "e", "i", "o", "u", "ar", "en", "il", "or", "an"]
_END = ["ford", "mere", "wick", "ton", "dale", "by", "ley", "ham", "stead", "burn",
        "croft", "vik", "more", "worth"]
_FIRST = ["Ines", "Tomas", "Mira", "Jonas", "Petra", "Lukas", "Nadia", "Oskar", "Rhea",
          "Viktor", "Alma", "Bruno", "Clara", "Dario", "Edda", "Felix", "Greta", "Hugo",
          "Ilse", "Jarek", "Katya", "Leon", "Marta", "Nils"]
_GOODS = ["dairy", "textile", "electronics", "timber", "glassware", "paper", "grain",
          "ceramics"]
_ROLES = ["analyst", "designer", "engineer", "coordinator", "auditor", "technician"]
_FEATS = ["checkout", "search", "profile", "invoice", "export", "sharing", "reporting",
          "booking"]
_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
_CODE_LETTERS = "bcdfghjkmnpqrstvwxz"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


class Used:
    """Names and codes already taken in one world, so nothing repeats."""

    def __init__(self, seed_names: list[str] | None = None) -> None:
        self.names: set[str] = set(seed_names or [])
        self.codes: set[str] = set()

    def name(self, r: Lcg) -> str:
        for _ in range(500):
            n = r.choice(_ON)
            if r.chance(0.5):
                n += r.choice(_MID)
            n += r.choice(_END)
            if n not in self.names:
                self.names.add(n)
                return n
        raise RuntimeError("name pool exhausted")

    def person(self, r: Lcg) -> str:
        for _ in range(500):
            n = r.choice(_FIRST) + " " + self.name(r)
            return n
        raise RuntimeError("unreachable")

    def code(self, r: Lcg) -> str:
        for _ in range(500):
            c = (r.choice(_CODE_LETTERS) + r.choice(_CODE_LETTERS)
                 + "%04d" % (1000 + r.below(9000)))
            if c not in self.codes:
                self.codes.add(c)
                return c
        raise RuntimeError("code pool exhausted")


class Fill(dict):
    """Lazy slot values: the same key gives the same value inside one sentence."""

    def __init__(self, r: Lcg, used: Used) -> None:
        super().__init__()
        self.r, self.used = r, used

    def __missing__(self, key: str) -> str:
        r = self.r
        if key in ("o", "o2", "x", "x2", "pl", "pl2"):
            value = self.used.name(r)
        elif key in ("p", "p2"):
            value = self.used.person(r)
        elif key == "n":
            value = str(3 + r.below(17))
        elif key == "d":
            value = ordinal(8 + r.below(20))
        elif key == "goods":
            value = r.choice(_GOODS)
        elif key == "role":
            value = r.choice(_ROLES)
        elif key == "feat":
            value = r.choice(_FEATS)
        elif key == "weekday":
            value = r.choice(_WEEKDAYS)
        else:
            raise KeyError(key)
        self[key] = value
        return value


_TAGS = [" (ref {g})", ", logged as {g}", ", ticket {g}", ", see note {g}",
         " (case {g})", ", entry {g}"]
_TAILS = ["; nothing else came up", " and the follow-up was left for next time",
          ", with no further comments from anyone", " as part of the usual routine",
          ", which the team accepted without discussion"]


def finish(body: str, code: str | None, r: Lcg) -> str | None:
    """Add the reference tag and a full stop; lengthen if short; None if too long."""
    text = body.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    text = text.rstrip(".")
    for _ in range(3):
        if word_count(text) >= LEN_MIN - (2 if code else 0):
            break
        text += r.choice(_TAILS)
    if code:
        text += r.choice(_TAGS).format(g=code)
    text += "."
    if not (LEN_MIN <= word_count(text) <= LEN_MAX):
        return None
    return text


# ---------------------------------------------------------------------- topical data


def _t(tid: str, a: list[str], b: list[str]) -> dict[str, Any]:
    return {"id": tid, "A": a, "B": b}


#: Topical material. A: event-side wording, B: cue-side wording; the two share no
#: content word (tested). The ninth topic of each domain is never a probe topic in a
#: world with eight topical probes; it is used for same-domain decoys.
TOPICS: dict[str, list[dict[str, Any]]] = {
    "logistics": [
        _t("lo1", ["{p} noticed the chilled pallets from {o} arrived warm again, because the reefer trailer had been unplugged at the {pl} yard for {n} hours",
                   "The probe logger on the {o} dairy load read above eight degrees for {n} hours while the refrigerated trailer sat unplugged at the {pl} yard"],
           ["Plan temperature-controlled transport for the perishable orders",
            "We need a cooling procedure for frozen and fresh goods in transit, with checks"]),
        _t("lo2", ["{o} customs paperwork for the {pl} crossing listed the wrong tariff code, so the container sat at the border for {n} days",
                   "The broker at {pl} rejected our import declaration because the harmonised code on the invoice was wrong, and {n} days were lost at the frontier"],
           ["Get the export clearance forms ready for the new overseas lane",
            "Check what permits our foreign deliveries will need"]),
        _t("lo3", ["Two trucks from {o} were booked into the same unloading bay at {pl}, and the second driver waited {n} hours",
                   "The {pl} warehouse double-booked the loading dock on Thursday, and the {o} lorry idled for {n} hours in the queue"],
           ["Design a timetable for incoming consignments at the depot to avoid congestion",
            "Arrange arrival appointments so vehicles do not pile up at the gates"]),
        _t("lo4", ["Glassware from {o} reached {pl} with {n} cracked cartons because the load was stacked three high without dividers"],
           ["Improve how fragile merchandise is protected in transit"]),
        _t("lo5", ["{p} drove a {n}-hour shift to meet the {o} deadline and clipped a gatepost at {pl}"],
           ["Set rules for how long couriers may work before resting"]),
        _t("lo6", ["Returned items at {pl} piled up for {n} weeks because nobody was assigned to inspect and restock them"],
           ["Streamline the handling of goods customers send back"]),
        _t("lo7", ["{p}'s van routes ignored the rush hour near {pl}, so {n} afternoon drops arrived after closing"],
           ["Schedule delivery runs around peak traffic so that customers get their parcels before the shop shuts"]),
        _t("lo8", ["The cycle count at the {o} store in {pl} found {n} units fewer than the system showed, because shelves had been refilled without scanning"],
           ["Reconcile physical inventory with the recorded quantities more reliably"]),
        _t("lo9", ["A dock strike at {pl} froze {o} sea freight for {n} days and the backup port had no free berths"],
           ["Prepare contingency itineraries for maritime consignments when harbours shut"]),
    ],
    "hiring": [
        _t("hi1", ["{p} told the panel the take-home exercise for the {o} candidate ran {n} hours, far over the stated limit, and two applicants withdrew",
                   "Applicants dropped out after the coding assignment from {o} turned out to need {n} hours instead of the advertised two"],
           ["Rethink the technical evaluation stage so fewer job seekers abandon the selection",
            "Cut down the effort asked of software job seekers during the selection process so they stay engaged"]),
        _t("hi2", ["{o} lost its first-choice designer because our written offer arrived {n} days after the verbal one, and they signed elsewhere",
                   "The preferred hire accepted a rival contract while we were still waiting on salary sign-off, {n} days after the chat with {p}"],
           ["Reduce the lag between telling someone we want them and sending the formal agreement",
            "Close the gap between an oral agreement and the paperwork for new joiners"]),
        _t("hi3", ["The new starter at {o} sat idle for {n} days because laptop and accounts were not ready, so {p} had to borrow a spare machine",
                   "{p} saw a first week at {pl} wasted waiting for system access and equipment, {n} days before anything worked"],
           ["Make sure devices, logins and a workstation are prepared before a newcomer's arrival",
            "Plan the first days of newly hired staff so they can be productive immediately"]),
        _t("hi4", ["The referral from {p} at {o} was rejected without feedback, and the friend who recommended them stopped sending names for {n} months"],
           ["Give staff who put forward people they know some news about the outcome, so they carry on doing it"]),
        _t("hi5", ["The advert wording for the {o} analyst post drew only {n} applications from women, and {p} traced it to the macho phrasing"],
           ["Adjust the language of vacancy notices to attract broader talent pools"]),
        _t("hi6", ["A reference call for the {pl} hire revealed {n} previous dismissals that the interview never surfaced"],
           ["Verify applicants' past conduct through former managers before signing"]),
        _t("hi7", ["A counter-proposal from {o} made our new engineer stay put after {n} weeks of notice, and the seat at {pl} sat empty"],
           ["Plan for the possibility that a person we hired gets persuaded by their present company to remain, leaving our vacancy unfilled"]),
        _t("hi8", ["{p} dominated the interview loop at {pl} and the other {n} panelists just agreed, so the scores were not independent"],
           ["Gather assessments from evaluators separately to avoid groupthink"]),
        _t("hi9", ["Converting the {o} contractor to staff took {n} months of legal back-and-forth at {pl}, and they left in the meantime"],
           ["Shorten the process for turning freelancers into permanent employees"]),
    ],
    "finance": [
        _t("fi1", ["Accounts payable paid the {o} bill twice, {n} thousand out the door, because two clerks keyed the same remittance on different days",
                   "A duplicate settlement to {o} went unnoticed for {n} weeks, and the ledger showed two identical transfers from {pl}"],
           ["Tighten controls so a supplier is never reimbursed more than once for one charge",
            "Set up a safeguard against repeat disbursements to vendors"]),
        _t("fi2", ["The {pl} budget assumed a fixed exchange rate, the currency moved {n} percent and the margin of the quarter disappeared",
                   "{p} flagged that euro-denominated costs for {o} jumped {n} percent once the peg slipped, wiping out the expected profit"],
           ["Account for swings in the value of foreign money when forecasting our earnings for the coming twelve months",
            "Decide whether to lock today's price with our bank for invoices we must settle in foreign money"]),
        _t("fi3", ["The auditor asked {o} for the receipts behind the {n} largest travel claims, half were missing, and {p} spent a week reconstructing them",
                   "During the {pl} audit, expense reimbursements lacked supporting paperwork, which cost {n} days of scrambling"],
           ["Make evidence for staff spending easy to produce when examiners arrive",
            "Collect proof of outlays systematically ahead of the yearly review"]),
        _t("fi4", ["{o} paid {n} days late again and nobody chased them until {p} noticed the cash gap"],
           ["Set up automatic nudges for clients who settle their debts after the due date"]),
        _t("fi5", ["The {pl} project spent {n} percent beyond its allocation because change requests were approved without a cost check"],
           ["Monitor spending against the sanctioned envelope as scope shifts"]),
        _t("fi6", ["{o} contractors in {pl} were paid gross, and the withholding shortfall of {n} thousand surfaced at filing"],
           ["Make sure levies are deducted properly for freelancers abroad"]),
        _t("fi7", ["A caller posing as {o} asked us to change bank details, and {p} wired {n} thousand before the fraud was caught"],
           ["Introduce a verification step when suppliers alter their account numbers"]),
        _t("fi8", ["Seasonal dips at {pl} were left out of the cash projection, leaving {o} short by {n} thousand in February"],
           ["Anticipate liquidity troughs throughout the calendar"]),
        _t("fi9", ["A {n} thousand machine for {o} was bought without a second quote, and {p} later found it cheaper at {pl}"],
           ["Require competing bids for large equipment purchases"]),
    ],
    "product": [
        _t("pr1", ["{o} pilot users saw the half-finished checkout because the feature toggle defaulted to on in {pl}, and {n} complaints came in",
                   "A switch for the new payment screen was left enabled when moving from staging to production, and {n} customers hit the unfinished page"],
           ["Make sure functionality that is not ready cannot be seen by ordinary people before launch day",
            "Decide how work-in-progress interface changes are hidden from the public during a phased rollout"]),
        _t("pr2", ["Interviews with {n} {o} customers showed nobody used the dashboard export we had spent a month on, and {p} kept the notes",
                   "{p} surveyed {n} users at {pl} and found the export tool we shipped was almost never opened"],
           ["Find out if people would really bother with the analytics extras we are planning before we build them",
            "Ask prospective buyers whether a new reporting add-on is worth the engineering effort"]),
        _t("pr3", ["Raising the {o} subscription by {n} percent led to cancellations within a fortnight, and {p} reversed it at {pl}",
                   "The plan fee increase of {n} percent triggered a wave of churn, so the old tier price came back"],
           ["Work out a tariff adjustment for the premium bundle without upsetting users",
            "Choose how much more to charge for the membership level"]),
        _t("pr4", ["{n} percent of new {o} sign-ups abandoned at the verification email step, which {p} found in the funnel report"],
           ["Reduce attrition during the registration flow for newcomers"]),
        _t("pr5", ["The {feat} page took {n} seconds to load on mobile in {pl}, and reviews mentioned the lag"],
           ["Make the interface feel snappier for people on slow phones"]),
        _t("pr6", ["A screen-reader user at {o} could not complete the {feat} form because buttons lacked labels, and {p} logged {n} similar gaps"],
           ["Make the product usable for blind or motor-impaired customers"]),
        _t("pr7", ["German text overflowed the buttons in the {feat} view since the layout was built around {n}-letter English labels"],
           ["Adapt the visual design for translated languages of varying length"]),
        _t("pr8", ["{p} accepted {n} extra requests from {o} mid-sprint, and the release slipped by a month"],
           ["Resist stakeholders piling more demands onto agreed work once an iteration has started, so dates hold"]),
        _t("pr9", ["A rival shipped the same {feat} idea {n} weeks before us, and {p} had not been tracking {pl} announcements"],
           ["Monitor other firms in our sector for imminent launches so we do not get beaten to it"]),
    ],
    "security": [
        _t("se1", ["A contractor's access key for {o} was pasted into a public repository and scraped within {n} hours, so {p} rotated everything at {pl}",
                   "The secret token of {o} appeared in a shared code gist for {n} days before anyone noticed, and crawlers had already used it"],
           ["Ensure nobody publishes private authentication material online where automated scanners harvest it",
            "Stop sensitive passkeys from being uploaded to open web platforms where strangers can fetch them"]),
        _t("se2", ["{p} at {o} clicked a fake invoice email and the attacker had mailbox rules forwarding messages for {n} days",
                   "A deceptive message impersonating the finance lead tricked staff in {pl}, and {n} people entered their passwords on a spoofed login page"],
           ["Train employees to recognise suspicious inbound correspondence",
            "Reduce the chance that a forged sender convinces someone to hand over access"]),
        _t("se3", ["The {pl} server missed the security update for {n} weeks because nobody owned the maintenance window, and the {o} scanner flagged it",
                   "An unpatched appliance at {o} was exploited after {p} deferred the fix {n} times for uptime reasons"],
           ["Ensure known weaknesses in installed programs are closed soon after the manufacturer announces the remedy",
            "Agree who is accountable for installing vendor corrections promptly"]),
        _t("se4", ["{p} approved a stream of push prompts at {n} at night and the attacker got into the {o} VPN"],
           ["Defend against intruders who spam login confirmations until someone accepts"]),
        _t("se5", ["A former employee of {o} still had working logins {n} weeks after leaving, and {p} found them in the {pl} directory"],
           ["Disable the accounts of staff who quit as soon as their employment ends"]),
        _t("se6", ["{o}, our hosting subcontractor, suffered a breach and we learned of it from the news {n} days later"],
           ["Assess the security posture of the outside providers we rely on"]),
        _t("se7", ["The intrusion at {pl} went unseen because log retention was only {n} days and the traces had rolled off"],
           ["Keep audit trails long enough to investigate old incidents"]),
        _t("se8", ["Marketing at {o} signed up for an unapproved file-sharing app, and {n} customer lists sat there until {p} stumbled on it"],
           ["Find out which software subscriptions employees buy on their own without informing technology staff"]),
        _t("se9", ["A stranger followed {p} through the {pl} door and plugged a device into a spare port for {n} minutes"],
           ["Control who may enter the premises and connect hardware"]),
    ],
    "data": [
        _t("da1", ["An upstream team at {o} renamed a column and the nightly load into the warehouse failed silently for {n} days until {p} found the gaps",
                   "The {pl} pipeline kept running but wrote nulls after the source table changed shape, so reports were wrong for {n} days"],
           ["Ensure downstream analytics notice when a producer modifies its output format",
            "Detect structural drift in feeds before dashboards go stale"]),
        _t("da2", ["The {o} labelling vendor mislabeled {n} percent of the images, and model accuracy looked fine until {p} sampled the batch by hand",
                   "Annotation errors in the {pl} sample went unseen because only aggregate scores were tracked, with {n} percent bad"],
           ["Audit the correctness of human-tagged examples before fitting the classifier",
            "Check ground truth reliability behind our supervised learning set"]),
        _t("da3", ["{o} kept raw customer logs for {n} months beyond the policy, and {p} found them while migrating the {pl} bucket",
                   "Old personal records were never purged from backups at {pl}, {n} months past the legal limit"],
           ["Make sure individuals' details are erased when the statutory storage period ends",
            "Define a schedule for deleting stale client information"]),
        _t("da4", ["Daily totals at {o} were off because logs from {pl} were in local time and not UTC, and {p} spotted {n} hours of drift"],
           ["Standardise timestamps coming from sources around the world"]),
        _t("da5", ["Two teams at {o} reported different active-user counts, {n} apart, because each defined the term its own way"],
           ["Agree a single meaning for key business indicators across departments"]),
        _t("da6", ["The {o} churn model decayed for {n} months after pricing changed, and nobody monitored its input mix at {pl}"],
           ["Watch for predictive systems degrading as the world evolves"]),
        _t("da7", ["{p} could not reproduce the {pl} analysis because the notebook depended on a local file and an unpinned library, {n} weeks on"],
           ["Make sure analytical results can be regenerated by colleagues later"]),
        _t("da8", ["An analyst at {o} exported {n} thousand customer emails to a spreadsheet for a quick check and mailed it around"],
           ["Prevent personal address lists extracted for an informal look from being passed round by colleagues"]),
        _t("da9", ["An unbounded query at {pl} scanned the full archive {n} times and the {o} cloud bill tripled"],
           ["Stop careless searches over huge stored files from inflating our hosting expense"]),
    ],
}

#: A second cue-side sentence for the topics that had only one, so that every C2 cue is two
#: sentences of the topic's cue-side vocabulary (like the C3 cue, which is a task sentence
#: plus a role sentence). Added after the first dev measurement showed one-sentence C2 cues
#: were only weakly similar to their targets.
_EXTRA_B = {
    "lo4": "Reduce breakage claims on delicate goods by changing how boxes are packed onto the vehicle",
    "lo5": "Prevent exhausted chauffeurs from causing accidents because of tight delivery promises",
    "lo6": "Decide who deals with parcels that buyers refuse, and how quickly they go on sale again",
    "lo7": "Make drivers avoid jammed roads when planning late-day timetables so shops are still open",
    "lo8": "Stop the warehouse database drifting away from what is truly on the racks",
    "lo9": "Keep goods moving when stevedores walk out and the nearest terminal is closed",
    "hi4": "Reward and respect the personal networks of our employees as a source of new recruits",
    "hi5": "Rewrite our vacancy listings so they do not discourage female candidates",
    "hi6": "Investigate a newcomer's earlier employment history before the contract is signed",
    "hi7": "Protect against a candidate being lured back by a rival bid after accepting",
    "hi8": "Prevent a forceful senior voice from swaying the rest of the hiring committee",
    "hi9": "Avoid losing valuable consultants because the paperwork to put them on the payroll drags on",
    "fi4": "Improve the collection of receivables from slow-paying buyers before it strains our liquidity",
    "fi5": "Stop initiatives from silently growing past what was originally authorised",
    "fi6": "Avoid unpleasant surprises with the revenue authority over remote workers' pay",
    "fi7": "Defend against impostors who demand payments to be redirected to a different account",
    "fi8": "Make our funds outlook reflect the quiet months so we never run dry",
    "fi9": "Make sure expensive equipment is compared across several sellers before we commit funds",
    "pr4": "Find out why newly registered people give up before activating their account",
    "pr5": "Speed matters for our app store ratings, so tune responsiveness for budget handsets",
    "pr6": "Add support for assistive technology so every control can be understood without sight",
    "pr7": "Make sure our screens still look right when wording gets longer in other tongues",
    "pr8": "Say no, or defer, when customers keep asking for more during a work period",
    "pr9": "Stay aware of upcoming releases by other vendors to protect our differentiation",
    "se4": "Stop repeated sign-in nags at odd hours from wearing down tired employees",
    "se5": "Make sure leavers lose system privileges on their final day",
    "se6": "Require partners who handle our information to tell us immediately when they are compromised",
    "se7": "Preserve event records for longer so slow-burn attacks can still be reconstructed",
    "se8": "Stop departments from storing company data in services that nobody in IT vetted",
    "se9": "Block unauthorised visitors from sneaking behind staff into the building",
    "da4": "Make clocks consistent across regions so that the numbers reported each morning add up",
    "da5": "End the arguments about whose figures are right by writing one shared glossary entry",
    "da6": "Notice early when a forecasting tool stops matching reality after the business shifts",
    "da7": "Capture the environment and inputs of every study so another person can rerun it",
    "da8": "Make it harder for a curious employee to copy people's private information out of the main system",
    "da9": "Impose limits on how much data a single lookup may read",
}
for _domain_topics in TOPICS.values():
    for _topic in _domain_topics:
        if _topic["id"] in _EXTRA_B:
            _topic["B"].append(_EXTRA_B[_topic["id"]])

# Role material: E = event wording (another domain), Q = cue wording (current domain),
# NEG = a lookalike with the opposite outcome (a decoy that must not be applied).
ROLES: dict[str, dict[str, list[str]]] = {
    "unreliable_party": {
        "E": ["{x} swore the handover would be done by the {d} yet turned up {n} days late without a word, so the whole schedule slid",
              "{x} agreed to a hard date, missed it by {n} days, and only admitted it when chased, so we absorbed the delay"],
        "Q": ["{x2} gave us a firm promise for completion on the {d}. Decide what safety margin the timeline needs",
              "An outside supplier named {x2} has pledged to finish its part by the {d}. Work out what buffer we should build in"],
        "NEG": ["{x} handed over {n} days ahead of the agreed date and the schedule held without any chasing"],
    },
    "failed_approach": {
        "E": ["we tried to save time by running the steps in parallel; it produced {n} conflicting results and we went back to the sequential way",
              "the shortcut of skipping the intermediate check backfired after {n} rounds of rework, so the original slow route was restored"],
        "Q": ["{p2} proposes concurrent execution to gain speed on this one. Judge whether that is wise",
              "The plan is to cut corners on early verification so we can wrap up faster. Is that a good idea"],
        "NEG": ["running the steps in parallel worked first time and saved {n} days with no rework"],
    },
    "hard_constraint": {
        "E": ["we found out too late that a fixed ceiling of {n} per week applies and nothing may exceed it, however pressing",
              "an inflexible cap of {n} units sat in the contract fine print and anything above it is refused outright"],
        "Q": ["Stakeholders are pushing for a major scale-up next month. Establish which boundaries are non-negotiable",
              "Leadership expects far more output soon. Spell out the maximum we are actually permitted"],
        "NEG": ["the stated limit proved flexible and {n} extra units were approved on a simple request"],
    },
    "silent_dependency": {
        "E": ["a forgotten link to the old system of {x} broke everything downstream on the {d}, because nobody had written it down",
              "the update collided with an undocumented tie to {x}, and {n} things failed that nobody had listed"],
        "Q": ["We are about to alter a core component. List everything else that quietly relies on it",
              "Before swapping out one of our central modules, map what else is hooked up to it"],
        "NEG": ["the update touched only itself and the review found nothing else attached to the old system of {x}"],
    },
    "estimate_slip": {
        "E": ["every estimate given before kickoff ran about {n} percent short, and the final effort was always bigger than first quoted",
              "the initial sizing was off by roughly {n} percent again, as it is whenever scope is described only verbally"],
        "Q": ["Management wants a duration for a new initiative that has only been sketched in conversation. What should we commit to",
              "Give a timeframe for the proposal everyone just discussed at the meeting"],
        "NEG": ["estimates given before kickoff landed within {n} percent of the actual effort, so no padding was needed"],
    },
    "single_owner": {
        "E": ["only {p} knew how the procedure worked, and when {p} left for {n} weeks nothing could proceed",
              "the knowledge sat with one person, {p}, so an absence of {n} days froze the work"],
        "Q": ["Assess continuity risk if the individual who runs the nightly job is unavailable",
              "Who else must be able to operate this when our usual specialist is on leave? Name the exposure"],
        "NEG": ["the procedure was fully documented, so the absence of {p} for {n} days changed nothing"],
    },
    "late_approval": {
        "E": ["sign-off from {x} took {n} days longer than planned, stalling everything queued behind it",
              "the review by {x} ate {n} extra days because nobody had asked them early"],
        "Q": ["A launch date has been announced. List the gatekeepers who must agree and when to approach each",
              "Sequence the permissions we need from other departments before the cutover"],
        "NEG": ["sign-off from {x} came {n} days sooner than planned and nothing queued behind it"],
    },
    "scale_surprise": {
        "E": ["it ran fine with {n} items but fell over at ten times that volume, which no test had covered",
              "the approach held up in the small trial of {n} cases and collapsed when the full load arrived"],
        "Q": ["We will soon roll this out to every region at once. What could go wrong that a pilot would not reveal",
              "Extend the current practice from one team to the whole organisation and flag the hidden risks"],
        "NEG": ["it handled ten times the usual volume on the first try with {n} items to spare"],
    },
}
ROLE_NAMES = tuple(sorted(ROLES))

#: Event-side scene clauses (the domain where the lesson was learned).
SCENES = {
    "logistics": ["While booking the {pl} freight lane", "On the {goods} run to {pl}",
                  "During the winter reroute through {pl}"],
    "hiring": ["While filling the {role} opening at {o}", "During the autumn graduate intake",
               "On the recruiting drive at {pl}"],
    "finance": ["While closing the accounts for {pl}", "During the budget cycle at {o}",
                "On the year-end reconciliation"],
    "product": ["While shipping the {feat} release", "During the beta of the {o} mobile app",
                "On the redesign sprint for {pl}"],
    "security": ["While hardening the {pl} network segment", "During compliance audit prep at {o}",
                 "On the incident-response drill at {pl}"],
    "data": ["While migrating the {o} reporting tables", "During the analytics rebuild at {pl}",
             "On the churn-model refresh"],
}

#: Cue-side task frames (the current goal's domain).
TASKS = {
    "logistics": ["Plan the spring distribution network expansion for the {pl} region",
                  "Organise the relocation of regional stock to a new site",
                  "Set up the festive-season fulfilment operation"],
    "hiring": ["Staff the new customer-success team in {pl}",
               "Build the hiring plan for the coming fiscal year",
               "Expand the data-engineering group by {n} people"],
    "finance": ["Prepare next year's financial plan for the {pl} subsidiary",
                "Set up the funding round process",
                "Rework how we report monthly results to the board"],
    "product": ["Launch the redesigned mobile app in the {pl} market",
                "Deliver the integrations marketplace",
                "Ship the new onboarding experience"],
    "security": ["Get the {pl} offices ready for the external certification",
                 "Roll out multi-factor login across the company",
                 "Stand up the new endpoint monitoring service"],
    "data": ["Build the customer analytics warehouse for the {pl} business unit",
             "Introduce a feature store for the modelling team",
             "Move the reporting stack to a new platform"],
}

GOALS = {
    "logistics": ["widen distribution coverage while keeping handling costs flat",
                  "restructure how stock moves between sites",
                  "raise on-time shipment performance across every region"],
    "hiring": ["grow the technical organisation while holding the bar",
               "make recruiting more predictable for managers",
               "build a stronger pipeline of junior talent"],
    "finance": ["stay within plan and improve forecast accuracy",
                "make month-end closing faster and less painful",
                "strengthen financial controls ahead of expansion"],
    "product": ["ship a polished version that people enjoy",
                "lift activation and retention for new accounts",
                "simplify the product before adding anything more"],
    "security": ["achieve external certification and close known exposures",
                 "make compromise of our accounts much harder",
                 "raise baseline protection across all offices"],
    "data": ["make company metrics trustworthy and easy to reach",
             "cut the cost of analytics",
             "improve the quality and lineage of shared datasets"],
}

#: Routine filler, per domain (short; lengthened with tails and tags).
ROUTINE = {
    "logistics": ["{o} confirmed the weekly {goods} delivery slot at {pl} for {n} pallets",
                  "{p} updated the route sheet after the {pl} road closure",
                  "The forklift inspection at {pl} passed with {n} minor notes",
                  "The {o} carrier invoice for last month matched the booking list",
                  "The fuel surcharge on the {pl} lane stayed unchanged this week",
                  "{p} counted {n} cartons in the returns cage and logged the totals"],
    "hiring": ["{p} scheduled {n} screening calls for the {role} position",
               "Panel feedback for the {o} referral was collected on the shared sheet",
               "The recruiting calendar for {pl} was refreshed with new interview slots",
               "{p} sent the reference check forms to {n} finalists",
               "The job advert for the {role} post went live on two boards",
               "The headcount table was reconciled with the {pl} office manager"],
    "finance": ["{p} filed the monthly accruals for {o} with {n} lines",
                "The bank statement for {pl} was matched against the cash book",
                "The travel budget for the {o} team was topped up by {n} units",
                "{p} reviewed the aged receivables list and chased {n} accounts",
                "The quarterly VAT return for {pl} was submitted on time",
                "Petty cash at the {pl} office was counted and signed off by {p}"],
    "product": ["{p} groomed the backlog and moved {n} stories into the sprint",
                "The design review for the {feat} screen ended with minor copy edits",
                "The {o} beta group received build {n} on Tuesday",
                "{p} updated the roadmap slide to show the {pl} market in the third phase",
                "Release notes for the {feat} update were drafted and shared",
                "Analytics showed {n} daily active users on the {feat} page"],
    "security": ["{p} renewed the TLS certificate for the {pl} gateway",
                 "The weekly vulnerability scan covered {n} hosts at {o} with no criticals",
                 "The badge reader log for {pl} was reviewed by {p}",
                 "A password policy reminder was sent to the {o} staff list",
                 "The firewall rule review closed {n} stale entries",
                 "{p} ran the quarterly backup restore test and noted {n} minutes"],
    "data": ["{p} refreshed the {o} dashboard and checked {n} tiles against source",
             "The nightly job for {pl} finished in {n} minutes",
             "Data dictionary entries for the {feat} tables were updated by {p}",
             "A new reviewer was added to the {pl} notebook repository",
             "The query cost report for last week showed {n} slow scans",
             "{p} archived the old {o} extracts to cold storage"],
}
CHATTER = [
    "{p} is out on {weekday} so the {pl} sync moves to the afternoon",
    "Office wifi at {pl} was restarted after a short outage and nothing else was affected",
    "The shared calendar for {o} was cleaned up and old invites were removed",
    "{p} circulated a reminder about the {pl} offsite lunch and dietary choices",
    "The team retrospective at {o} produced {n} small action items, all assigned",
    "The printer in the {pl} corridor was replaced and the old toner boxed up",
]
#: Distractors that carry topical words without any content (used for surface decoys
#: and, with random words, for a share of the filler so the frames are not a tell).
PARKED = [
    "Sync notes: {p} asked whether {w1} could wait, and the {w2} question was parked until the {pl} review",
    "{p} mentioned {w1} and {w2} in the {pl} standup but no owner was named",
    "The reading list for the {pl} group covers {w1}, {w2} and a few other themes",
    "A short thread on {w1} versus {w2} ran for {n} messages at {o} with no conclusion",
    "Agenda item for {o}: {w1} and {w2}, to be discussed once {p} is back",
    "Someone at {pl} wondered whether {w1} and {w2} deserve their own page, but nobody volunteered",
]

_ALL_CUE_WORDS = sorted({surface for dom in TOPICS.values() for t in dom for b in t["B"]
                         for surface, _ in content_tokens(b)})


# --------------------------------------------------------------------------- goals


def build_goals(seed: int) -> list[dict[str, Any]]:
    r = stream(seed, "goals")
    domains = list(DOMAINS)
    r.shuffle(domains)
    goals = []
    for i, (lo, hi) in enumerate(PHASES):
        d = domains[i]
        goals.append({"phase": i + 1, "day_from": lo, "day_to": hi, "domain": d,
                      "text": "Current goal: " + r.choice(GOALS[d])})
    return goals


# ----------------------------------------------------------------------- probe specs

_C1_FRAMES = [
    "{b}. Start from the {kws} problem involving {names}.",
    "{b}. Look first at the earlier {kws} trouble around {names}.",
    "{b}. Anything we noted about {names} and {kws} matters here.",
    "{b}. Recall the {kws} episode with {names}.",
]


def _c1_cue(b: str, target: str, fill: Fill, r: Lcg) -> str | None:
    names = [fill[k] for k in ("o", "pl", "p") if k in fill][:2]
    name_stems = stems_of(" ".join(names)) | stems_of(" ".join(fill.values()))
    b_stems = stems_of(b)
    pool, seen = [], set()
    for surface, st in content_tokens(target):
        if (len(surface) >= 5 and st not in b_stems and st not in name_stems
                and st not in seen and not any(ch.isdigit() for ch in surface)):
            seen.add(st)
            pool.append(surface)
    best, best_gap = None, 9.0
    for _ in range(14):
        frame = r.choice(_C1_FRAMES)
        words = r.sample(pool, min(4, len(pool)))
        for k in range(1, len(words) + 1):
            cue = frame.format(b=b, kws=" ".join(words[:k]), names=" and ".join(names))
            ratio = overlap_fraction(cue, target)
            gap = abs(ratio - C1_TARGET_OVERLAP)
            if gap < best_gap:
                best, best_gap = cue, gap
    if best is None:
        return None
    ratio = overlap_fraction(best, target)
    return best if C1_ACCEPT[0] <= ratio <= C1_ACCEPT[1] else None


def _probe_spec(seed: int, index: int, cell: str, topic: dict[str, Any] | None,
                role: str | None, goals: list[dict[str, Any]], used: Used) -> dict[str, Any]:
    r = stream(seed, "probe", index)
    code = used.code(r)
    target_day = TARGET_DAYS[0] + r.below(TARGET_DAYS[1] - TARGET_DAYS[0] + 1)
    lo = max(PHASES[2][0], target_day + MIN_GAP_DAYS)
    cue_day = lo + r.below(N_DAYS - lo + 1)
    d1, d3 = goals[0]["domain"], goals[2]["domain"]
    goal_text = goals[2]["text"]
    for _ in range(120):
        fill = Fill(r, used)
        if cell in ("C1", "C2"):
            assert topic is not None
            body = r.choice(topic["A"]).format_map(fill)
            text = finish(body, code, r)
            if text is None:
                continue
            if cell == "C2":
                bs = list(topic["B"])
                r.shuffle(bs)
                cue = bs[0] + ". " + bs[1] + "."
                if overlap_fraction(cue, text) > 0 or overlap_fraction(goal_text, text) > 0:
                    continue
            else:
                cue = _c1_cue(r.choice(topic["B"]), text, fill, r)
                if cue is None:
                    continue
            label = "topic:" + d3 + ":" + topic["id"]
        else:
            assert role is not None
            scene = r.choice(SCENES[d1]).format_map(fill)
            body = scene + ", " + r.choice(ROLES[role]["E"]).format_map(fill)
            text = finish(body, code, r)
            if text is None:
                continue
            fc = Fill(r, used)
            cue = (r.choice(TASKS[d3]).format_map(fc) + ". "
                   + r.choice(ROLES[role]["Q"]).format_map(fc) + ".")
            if overlap_fraction(cue, text) > 0 or overlap_fraction(goal_text, text) > 0:
                continue
            label = "role:" + role
        if code in cue.lower() or not text:
            continue
        return {
            "cell": cell, "code": code, "target_day": target_day, "cue_day": cue_day,
            "target_text": text, "cue": cue, "question": cue + ASK,
            "concept": label,
            "role": role, "topic": (topic["id"] if topic else None),
            "overlap": round(overlap_fraction(cue, text), 4),
            "goal_overlap": round(overlap_fraction(goal_text, text), 4),
            "domain_target": d1 if cell == "C3" else d3, "domain_cue": d3,
        }
    raise RuntimeError("could not satisfy the %s constraints for seed %d" % (cell, seed))


def build_probe_specs(seed: int, goals: list[dict[str, Any]],
                      used: Used) -> tuple[list[dict[str, Any]], str]:
    """The twelve probes. Independent of every non-probe event. Returns the specs and
    the id of the spare topic (used only by same-domain decoys)."""
    r = stream(seed, "layout")
    d3 = goals[2]["domain"]
    topics = list(TOPICS[d3])
    r.shuffle(topics)
    probe_topics, spare = topics[:8], topics[8]
    # Each world uses four of the eight roles: alternate worlds take alternate halves, so any
    # run of consecutive seeds covers every role (nearly) equally often.
    roles = list(ROLE_NAMES[seed % 2::2])
    r.shuffle(roles)
    cells = [c for c in CELLS for _ in range(PROBES_PER_CELL)]
    r.shuffle(cells)
    topic_iter, role_iter = iter(probe_topics), iter(roles)
    specs = []
    for i, cell in enumerate(cells):
        topic = next(topic_iter) if cell in ("C1", "C2") else None
        role = next(role_iter) if cell == "C3" else None
        spec = _probe_spec(seed, i, cell, topic, role, goals, used)
        spec["probe_id"] = "s%03d-q%02d" % (seed, i)
        specs.append(spec)
    return specs, spare["id"]


# ------------------------------------------------------------------------- history


def _parked_text(r: Lcg, fill: Fill, words: list[str]) -> str:
    frame = r.choice(PARKED)
    return frame.format_map(_Merge(fill, {"w1": words[0], "w2": words[1]}))


class _Merge(dict):
    def __init__(self, fill: Fill, extra: dict[str, str]) -> None:
        super().__init__(extra)
        self.fill = fill

    def __missing__(self, key: str) -> str:
        return self.fill[key]


def _write_time_fields(seed: int, events: list[dict[str, Any]]) -> None:
    """Authored write-time salience: ``consequence`` (0-3) and ``novelty`` (0-1).

    Both are drawn from one stream keyed by (seed) and consumed in time order, so they
    depend on the event's position only: not on its text, kind, probe, or any later
    event. v0.1 computed novelty against earlier events, which made it fall with time
    and favour the early-day targets, and drew consequence by kind; both told the
    forgetting arms which events were targets. The price: write-time importance here is
    uninformative by construction (the spec's 'low-salience target'), so an arm that
    forgets by importance keeps a random subset of the older events."""
    rw = stream(seed, "writetime")
    for e in events:
        e["consequence"] = rw.weighted(CONSEQUENCE_PROBS)
        e["novelty"] = round(rw.uniform(), 4)


def build_history(seed: int, goals: list[dict[str, Any]], specs: list[dict[str, Any]],
                  spare_topic: str, used: Used) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    d1, d3 = goals[0]["domain"], goals[2]["domain"]
    spare = next(t for t in TOPICS[d3] if t["id"] == spare_topic)
    items: list[dict[str, Any]] = []

    def add(text: str, day: int, kind: str, probe: str | None, concepts: list[str],
            r: Lcg) -> None:
        items.append({"text": text, "day": day, "kind": kind, "probe": probe,
                      "concepts": concepts, "order": r.below(10 ** 6)})

    for spec in specs:
        r = stream(seed, "decoys", spec["probe_id"])
        add(spec["target_text"], spec["target_day"], "target", spec["probe_id"],
            [spec["concept"]], r)
        cue_day = spec["cue_day"]
        target_stems = stems_of(spec["target_text"])
        cue_words = []
        seen = set()
        for surface, st in content_tokens(spec["cue"]):
            if st not in target_stems and st not in seen and len(surface) >= 6:
                seen.add(st)
                cue_words.append(surface)
        made = 0
        for _ in range(200):
            if made == 2 and spec["cell"] != "C3":
                break
            if made == 1 and spec["cell"] == "C3":
                break
            if len(cue_words) < 2:
                break
            fill = Fill(r, used)
            text = finish(_parked_text(r, fill, r.sample(cue_words, 2)), stream_code(used, r), r)
            if text is None:
                continue
            add(text, 3 + r.below(cue_day - 3), "decoy_surface", spec["probe_id"], ["noise"], r)
            made += 1
        # same-domain decoy from the spare topic
        use_spare = r.chance(0.5)
        for _ in range(60):
            fill = Fill(r, used)
            template = r.choice(spare["A"] if use_spare else ROUTINE[d3])
            text = finish(template.format_map(fill), stream_code(used, r), r)
            if text is not None:
                add(text, 3 + r.below(cue_day - 3), "decoy_domain", spec["probe_id"],
                    ["topic:" + d3 + ":" + spare_topic] if use_spare else ["routine"], r)
                break
        if spec["cell"] == "C3":
            role = spec["role"]
            for _ in range(80):
                fill = Fill(r, used)
                body = (r.choice(SCENES[d1]).format_map(fill) + ", "
                        + r.choice(ROLES[role]["NEG"]).format_map(fill))
                text = finish(body, stream_code(used, r), r)
                if text is not None:
                    add(text, 3 + r.below(cue_day - 3), "decoy_lookalike", spec["probe_id"],
                        ["role:~" + role], r)
                    break

    rf =stream(seed, "filler")
    n_fill = N_EVENTS - len(items)
    for _ in range(n_fill):
        day = 1 + rf.below(N_DAYS)
        phase_domain = goals[0 if day <= 10 else 1 if day <= 20 else 2]["domain"]
        domain = phase_domain if rf.chance(0.7) else rf.choice(DOMAINS)
        text = None
        for _try in range(40):
            fill = Fill(rf, used)
            x = rf.below(100)
            if x < 12:
                body = rf.choice(CHATTER).format_map(fill)
                kind, concepts = "filler", ["routine"]
            elif x < 28:
                body = _parked_text(rf, fill, rf.sample(_ALL_CUE_WORDS, 2))
                kind, concepts = "noise", ["noise"]
            else:
                body = rf.choice(ROUTINE[domain]).format_map(fill)
                kind, concepts = "filler", ["routine"]
            code = used.code(rf)  # every event carries a code, so the tag says nothing
            text = finish(body, code, rf)
            if text is not None:
                break
        if text is None:
            raise RuntimeError("filler could not be rendered")
        add(text, day, kind, None, concepts, rf)

    items.sort(key=lambda it: (it["day"], it["order"]))
    events, labels = [], {}
    for pos, it in enumerate(items, start=1):
        eid = "e%03d" % pos
        events.append({"event_id": eid, "day": it["day"], "position": pos,
                       "text": it["text"]})
        labels[eid] = {"kind": it["kind"], "probe_id": it["probe"], "concepts": it["concepts"]}
    _write_time_fields(seed, events)
    return events, labels


def stream_code(used: Used, r: Lcg) -> str:
    return used.code(r)


# ---------------------------------------------------------------------------- world


def generate(seed: int, history: bool = True) -> dict[str, Any]:
    """One world. With ``history=False`` only goals and cues (the 'reveal') are built;
    the cue rows are identical to those of the full world."""
    goals = build_goals(seed)
    used = Used()
    specs, spare = build_probe_specs(seed, goals, used)
    cues = [{"probe_id": s["probe_id"], "day": s["cue_day"], "goal": goals[2]["text"],
             "cue": s["cue"], "question": s["question"]} for s in specs]
    world: dict[str, Any] = {"seed": seed, "version": GENERATOR_VERSION, "goals": goals,
                             "cues": cues}
    if not history:
        return world
    events, ev_labels = build_history(seed, goals, specs, spare, used)
    target_of = {eid: lab["probe_id"] for eid, lab in ev_labels.items()
                 if lab["kind"] == "target"}
    by_probe = {pid: eid for eid, pid in target_of.items()}
    probes = []
    for s in specs:
        decoys = sorted(eid for eid, lab in ev_labels.items()
                        if lab["probe_id"] == s["probe_id"] and lab["kind"].startswith("decoy"))
        probes.append({
            "probe_id": s["probe_id"], "cell": s["cell"], "cue_day": s["cue_day"],
            "gold_event_id": by_probe[s["probe_id"]], "gold_answer": s["code"],
            "decoy_ids": decoys, "concept": s["concept"], "role": s["role"],
            "topic": s["topic"], "overlap": s["overlap"], "goal_overlap": s["goal_overlap"],
            "target_day": s["target_day"], "domain_target": s["domain_target"],
            "domain_cue": s["domain_cue"],
        })
    world["events"] = events
    world["labels"] = {"events": ev_labels, "probes": probes}
    return world


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def write_world(world: dict[str, Any], directory: Path) -> None:
    """history.jsonl, cues.jsonl and labels.json (the labels are for scoring only)."""
    directory.mkdir(parents=True, exist_ok=True)

    def dump(name: str, rows: list[dict[str, Any]]) -> None:
        with (directory / name).open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")

    dump("cues.jsonl", world["cues"])
    if "events" in world:
        dump("history.jsonl", world["events"])
        with (directory / "labels.json").open("w", encoding="utf-8", newline="\n") as handle:
            json.dump({"goals": world["goals"], **world["labels"]}, handle, indent=1,
                      sort_keys=True, ensure_ascii=False)
            handle.write("\n")
