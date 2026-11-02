# SPDX-License-Identifier: Apache-2.0
"""memory_kernel 0.2.0: a small, deterministic memory for a writing agent. Standard library only; no network, no files, no effects on import.

Each property comes from a result of the lab (AAM = adaptive agent memory research):
  thresholded injection  at most 3 items and only above a threshold; below it nothing is shown (AAM-E5-REPLAY: memory shown always is worse on the tasks that have no
                         related earlier piece and makes the writer refer back to things that do not apply)
  no future              an item dated at or after the task is never shown, and items dated after the index date are rejected when the index is built (benchmark gate G3);
                         a replacement counts only from its own date, so a task before it still sees the old item
  origin classes         account_history, fiction_autobio, world_knowledge; invented autobiography is considered only for the task types a profile names
                         (AAM-E6: the invented past leaks into tasks where it must not appear), and the class never reaches the prompt, only the log
  a channel for names    for the task types a profile names, a rare capitalised word of the query that an item also has passes the gate on its own
                         (AAM-E6: embeddings miss rare names that a lexical match finds)
  injection log          every call can be turned into one log record (keyed hashes, origins, scores, reasons, no text), also when nothing was injected
  reference guard        a deterministic check of the writer's output; a FLOOR signal, not a proof and not a gate: log its flags, do not reject text on them
Embeddings are optional. Without an embedder the kernel is lexical (BM25 plus names); with one it is hybrid (the larger of the two gate ratios; the study WMB-R1 found
that this max-fusion keeps little of the embedder's gain, so fit the weights on your own data before relying on the hybrid profile).

THE LEXICAL GATE (new in 0.2.0). WMB-R1 found the 0.1.0 idf-coverage score the weakest lexical method in every part and BM25 (k1 1.2, b 0.75) better. The score of an item is
BM25 over the stems of the query. Document frequency df, document count N and average length avgdl are those of the items THE CALL MAY SEE (dated before the task, not yet
replaced, invented autobiography only for the task types that allow it), taken in the one pass that finds them, so an item that a call may not see (a flood of invented
autobiography in a note task, the items after a replayed task) can never change what a visible one scores:
    idf(t)   = ln(1 + (N - df + 0.5) / (df + 0.5))
    bm25     = sum over the query stems t that the item has of idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * min(dl, len_cap * avgdl) / avgdl))        (tf, dl: stems of the item, repeats counted)
The length of an item counts at most len_cap (3) times the average: without the cap, BM25 divided by the reference below can never reach the threshold for an item more than
about four times as long as the average, however many query words it holds (an essay in an index of short notes). A raw BM25 score grows with the length of the query, so a
fixed threshold on it would be a threshold on the length. The gate therefore divides it by the largest value that the query's own most informative terms could give:
    reference = (k1 + 1) * sum of idf over the top_terms known stems of the query with the highest idf        (10 by default; ties: the stem that comes first in the query)
    s         = bm25 / reference
The reference is the supremum of the BM25 of any document on those terms; a full match of every reference term, once, in a document of average length, scores 1 / (k1 + 1) = 0.4545,
and in a document of len_cap times the average length 1 / (1 + k1 * (0.25 + 0.75 * len_cap)) = 0.25. Only stems that some item of the call has are known (a word the items never
use cannot tell them apart and must not dilute the reference). The reference stops growing at top_terms, so a long task text does not have to match everything: matching about
45% of the mass of its ten rarest known words passes in a document of average length, as for a short query. The score itself counts the max_terms (20) most informative known
stems, the reference terms and ten more, so a long query gets bounded credit for lesser words (s can exceed 1: up to max_terms / top_terms), and a very long one costs no more
time. An item passes the lexical channel when s >= lex_tau and the idf mass of the query stems it contains is at least min_evidence times the idf of a word seen once (an absolute
floor of evidence). The default min_evidence is 1.4: ONE shared rare word is not enough, two are (or one very rare and one fairly rare); the default of 0.8 that 0.2.0 was first
built with passed an item on a single shared rare word, and unrelated short queries then fired about half the time (see README for the measured rates). Set 0.8 to ask for one
word, and fit lex_tau and min_evidence with calibrate() on labelled data of your own before the first production use. The rank is by strength = s / lex_tau, ties to the item
that sorts first by id. Profile keys: lex_tau (default 0.20, above zero), min_evidence (1.4), k1 (1.2, 0 to 100), b (0.75), len_cap (3; 0 = no cap, plain BM25 length),
top_terms (10; 0 = all known terms, which with max_terms = 0 is plain BM25 ranking), max_terms (20; 0 = no cap), require_zone (false). A key that the profile does not know is an
error (a mistyped threshold must not silently keep its default). channel_scores[i]["lexical"] is s (before 0.2.0: coverage), scores[i] is in units of the gate. calibrate()
uses the same score and the same evidence floor.

Dates: created_at, as_of and now are ISO 8601 strings (or date/datetime objects); a year, a month, a day or a time may be missing from the right, a zone (+hh:mm[:ss]) is
converted to UTC and a time WITHOUT a zone is read as UTC (a naive datetime.now() of a machine that is ahead of UTC is read as a later time than it is, so pass an aware datetime,
or set require_zone in the profile to make retrieve refuse a now without a zone). A date without a time is the start of that day, so an item of the index date itself is in the
index and is shown to no task of that day. Mixed precisions compare correctly (2026-09-10 is before 2026-09-10T08:00); an item is shown only if it is strictly before `now`.
Offsets beyond +-23:59:59 and values that are neither text nor a date are refused. render() shows the date an item was written with (its own precision and zone), the sort and the
log use the UTC key.

Names. A stem is a name when it is written with a capital in the item and never in lower case there, and it is capitalised in the middle of a sentence (or all in capitals, three
letters or more, also as a plural: GPUs) in the item or in the query. A capital at the start of a sentence proves nothing (Meanwhile, However, Today), so a word that is
capitalised only at sentence starts on both sides is not a name; the lexical channel can still find it. A name hit passes the gate alone, comes first and has strength >= 1. Whether
a word is "never in lower case" and how rare it is (rare_df) are read over the items of the call.

Text units. Words are runs of letters and digits and of the combining marks of their script (Hindi, Thai, Arabic with vowel signs, Hebrew with points; the table of marks is
fixed in this file), NFC, split at hyphens; at most MAX_TEXT_CHARS characters of a text are read; soft hyphens and zero-width characters are removed. The stemmer folds plurals
(gpus, llms, apis, bots, apps, laws, processes, biases, boxes, batches, movies, stories, heroes, wolves, quizzes, people) and possessives; the stop lists are tested on the surface
form before stemming (was, has, does, this, its are never stems), except that a few words which are names, months or acronyms when capitalised (US, May, Ono, Co) are kept when
written with a capital inside a sentence or in capitals; contractions (isn't, don't, I'm, can't, it's, with straight or curly apostrophes) leave no stems; the English list holds
function words, the Polish one a moderate set. Which characters count as letters follows the Unicode tables of the interpreter (the log record carries their version).

Items. A trace is {"gist", "angle", "open"} of text. build_index keeps the items as they were passed (retrieve returns the very objects) and counts an item with a trace that
is not a dict, or with a value that is not text, once in index.trace_dropped; render() ignores the bad part. render() shows, per item and oldest first, one line "[date] body"
with the whitespace and control characters of the body collapsed (an item cannot add a line of its own; a lone surrogate becomes U+FFFD) and the body cut at max_item_chars
(4000) at a word; the body is the trace in trace mode when it has a gist and the raw text otherwise. RULE of the shown items: an item is shown exactly when render() emits a line
for it, which needs a text and a date; retrieve() returns only such items, and render, log_record and guard all use this one rule on a result, so what is logged and what the
guard counts as injected is what the writer saw.

API: build_index(items, as_of, embedder=None, vectors=None) -> Index; retrieve(index, query, task_type, now, profile) -> dict; render(result) -> str;
     log_record(result, hmac_fn, key=None, raw_ids=False) -> dict; guard(result, output_text) -> dict; calibrate(index, queries, share, channel) -> float.
retrieve returns {status, items, n_candidates, n_considered, scores, channel_scores, reasons, dates, latency_ms, tokens_est, ...} and never raises: problems are reported in
status (ok, degraded: lexical only because the embedder failed or is missing where the profile wants it, or the items could not all be read; timeout, error). Every public
function returns instead of raising (guard flags guard_error:<type>, log_record and retrieve report status error, calibrate returns None, an unusable write_back_item gives an item
that the index rejects) except build_index with an invalid as_of (fail closed: without it the no-future gate cannot be enforced) and the parser when(), whose contract is
ValueError and nothing else. build_index counts and drops invalid, future and duplicate items (the first of two items with one id wins) and keeps the items read so far when the
iterable of items fails midway (index.source_error). The deadline of a call is checked every 200 items and after the embedder returns; it cannot interrupt an embedder that hangs,
so give the embedder a timeout of its own (timeout_ms may be infinity). A query is read up to MAX_QUERY_CHARS characters.

The guard is a floor. guard(result, text) -> {"ok", "flags", "callbacks"}: callbacks = the number of sentences that explicitly refer back to something the author said, wrote,
posted or covered earlier (English only; a bank of natural sentences, tests/test_wmb_kernel_v2.py, gives precision and recall; references to the text being written - above,
earlier in this note, the previous paragraph - and ordinary AI vocabulary - post-training, previous generation, the last column - are not references, and neither are a bare
"my newsletter", a bare "as I said", "I wrote a script last week" or "welcome back, regular readers"). A reference to the text itself cancels a match clause by clause. flags:
spurious_reference (a reference although nothing of the account's own, that is nothing but world knowledge or nothing, was injected), unsupported_reference (a reference whose
sentence shares with the injected items neither a distinctive term nor three content words; idf-weighted, the words of the reference phrase itself do not count), future_item,
fiction_out_of_scope. ok is True when there is no flag: it says nothing about references the patterns do not see. Log the flags; do not reject or retry on them.

CHANGELOG
0.2.0  lexical channel is BM25 normalised by the top-term reference (finding 5 of the review of 0.1.0; WMB-R1); lex_tau means a share of that reference (default 0.20) and
       new profile keys k1, b, len_cap, top_terms, max_terms, require_zone; the statistics of a call are those of the items it may see (fiction, future and replaced items cannot
       change a score); the length of a long item counts at most len_cap times the average (an essay is not out of reach); min_evidence defaults to 1.4 (two rare words); equally
       rare query words are ranked by position in the query; unknown profile keys, tau or lex_tau at zero or below, k1 above 100 are errors, a deadline may be infinite; plural
       folding for short stems, acronym plurals and -es/-ie/-oes/-ves forms, a few irregular plurals; stop words tested before stemming, contractions leave no stems, longer
       English and Polish stop lists, capitalised US/May/Ono kept; combining marks belong to words, invisible characters are removed, text is cut at MAX_TEXT_CHARS; names need
       an unforced capital (finding 3) and have strength >= 1; traces are counted at build time (index.trace_dropped) and ignored at render time, the items are not rewritten;
       render degrades per item, collapses whitespace and control characters, shows the date as written and cuts long items; log_record scrubs lone surrogates for hmac_fn and
       carries rejected, now_key and unicode; result["now"] and log_record are JSON-safe for date/datetime and task_type of any type; retrieve with a non-Index or an empty
       index with an embedder returns ok/error instead of raising/degrading; dates: offsets validated (seconds allowed), no overflow, ASCII digits, lower case t/z, only text and
       dates accepted, only ValueError raised; supersession counts from an item of the same or a later instant and ignores self and cycles; profile values validated (a bare
       string for a task-type list means one type); the guard recognises references by grammar instead of a phrase list, cancels local references per clause, needs an anchor
       for stance phrases and does not take world knowledge for the account's own text; calibrate returns None instead of a threshold of zero when it cannot calibrate, applies
       min_evidence and the statistics of each pair; write_back_item never raises. Unchanged: names and signatures of the public functions (calibrate and render gained optional
       trailing parameters), the keys of results (retrieve gained rejected, the log record rejected and unicode), the gate scale of embeddings, the 300 ms deadline.
0.1.0  first version (frozen as the instrument of WMB-R1 in scripts/wmb/memory_kernel.py).
"""

from __future__ import annotations

import hashlib
import math
import re
import time
import unicodedata
from array import array
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from functools import lru_cache
from operator import mul
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

__version__ = VERSION = "0.2.0"
KINDS = ("note", "reply", "comment", "event")
ORIGINS = ("account_history", "fiction_autobio", "world_knowledge")
TRACE_KEYS = ("gist", "angle", "open")
MAX_QUERY_CHARS = 20000
MAX_TEXT_CHARS = 50000                 # an item (or any text that analyse reads) is cut here; normalising a long run of combining marks is quadratic
MAX_GUARD_CHARS = 50000                # the writer's output is read up to here
LONG_TOKEN = 48                        # a longer token is not worth a place in the caches of the stemmer
DISTINCT = 0.5                       # a term is distinctive when its idf is at least this share of the idf of a word seen once (the guard's support test)
APOSTROPHES = "".join(map(chr, (0x2019, 0x2018, 0x02BC, 0x00B4, 0x2032, 0x60)))          # right and left single quotation mark, modifier letter apostrophe, acute accent, prime, grave
APOSTROPHE_TABLE = {ord(c): "'" for c in APOSTROPHES}
# Mn and Mc (marks that belong to the letter before them: vowel signs, points, accents) of Unicode 15.0.0, fixed here so that a word is cut the same way on every interpreter
_MARK_RANGES = (
    "0300-036f 0483-0487 0591-05bd 05bf 05c1-05c2 05c4-05c5 05c7 0610-061a 064b-065f 0670 06d6-06dc 06df-06e4 06e7-06e8 06ea-06ed 0711 0730-074a 07a6-07b0 "
    "07eb-07f3 07fd 0816-0819 081b-0823 0825-0827 0829-082d 0859-085b 0898-089f 08ca-08e1 08e3-0903 093a-093c 093e-094f 0951-0957 0962-0963 0981-0983 09bc "
    "09be-09c4 09c7-09c8 09cb-09cd 09d7 09e2-09e3 09fe 0a01-0a03 0a3c 0a3e-0a42 0a47-0a48 0a4b-0a4d 0a51 0a70-0a71 0a75 0a81-0a83 0abc 0abe-0ac5 0ac7-0ac9 "
    "0acb-0acd 0ae2-0ae3 0afa-0aff 0b01-0b03 0b3c 0b3e-0b44 0b47-0b48 0b4b-0b4d 0b55-0b57 0b62-0b63 0b82 0bbe-0bc2 0bc6-0bc8 0bca-0bcd 0bd7 0c00-0c04 0c3c "
    "0c3e-0c44 0c46-0c48 0c4a-0c4d 0c55-0c56 0c62-0c63 0c81-0c83 0cbc 0cbe-0cc4 0cc6-0cc8 0cca-0ccd 0cd5-0cd6 0ce2-0ce3 0cf3 0d00-0d03 0d3b-0d3c 0d3e-0d44 "
    "0d46-0d48 0d4a-0d4d 0d57 0d62-0d63 0d81-0d83 0dca 0dcf-0dd4 0dd6 0dd8-0ddf 0df2-0df3 0e31 0e34-0e3a 0e47-0e4e 0eb1 0eb4-0ebc 0ec8-0ece 0f18-0f19 0f35 "
    "0f37 0f39 0f3e-0f3f 0f71-0f84 0f86-0f87 0f8d-0f97 0f99-0fbc 0fc6 102b-103e 1056-1059 105e-1060 1062-1064 1067-106d 1071-1074 1082-108d 108f 109a-109d "
    "135d-135f 1712-1715 1732-1734 1752-1753 1772-1773 17b4-17d3 17dd 180b-180d 180f 1885-1886 18a9 1920-192b 1930-193b 1a17-1a1b 1a55-1a5e 1a60-1a7c 1a7f "
    "1ab0-1abd 1abf-1ace 1b00-1b04 1b34-1b44 1b6b-1b73 1b80-1b82 1ba1-1bad 1be6-1bf3 1c24-1c37 1cd0-1cd2 1cd4-1ce8 1ced 1cf4 1cf7-1cf9 1dc0-1dff 20d0-20dc "
    "20e1 20e5-20f0 2cef-2cf1 2d7f 2de0-2dff 302a-302f 3099-309a a66f a674-a67d a69e-a69f a6f0-a6f1 a802 a806 a80b a823-a827 a82c a880-a881 a8b4-a8c5 "
    "a8e0-a8f1 a8ff a926-a92d a947-a953 a980-a983 a9b3-a9c0 a9e5 aa29-aa36 aa43 aa4c-aa4d aa7b-aa7d aab0 aab2-aab4 aab7-aab8 aabe-aabf aac1 aaeb-aaef "
    "aaf5-aaf6 abe3-abea abec-abed fb1e fe00-fe0f fe20-fe2f 101fd 102e0 10376-1037a 10a01-10a03 10a05-10a06 10a0c-10a0f 10a38-10a3a 10a3f 10ae5-10ae6 "
    "10d24-10d27 10eab-10eac 10efd-10eff 10f46-10f50 10f82-10f85 11000-11002 11038-11046 11070 11073-11074 1107f-11082 110b0-110ba 110c2 11100-11102 "
    "11127-11134 11145-11146 11173 11180-11182 111b3-111c0 111c9-111cc 111ce-111cf 1122c-11237 1123e 11241 112df-112ea 11300-11303 1133b-1133c 1133e-11344 "
    "11347-11348 1134b-1134d 11357 11362-11363 11366-1136c 11370-11374 11435-11446 1145e 114b0-114c3 115af-115b5 115b8-115c0 115dc-115dd 11630-11640 "
    "116ab-116b7 1171d-1172b 1182c-1183a 11930-11935 11937-11938 1193b-1193e 11940 11942-11943 119d1-119d7 119da-119e0 119e4 11a01-11a0a 11a33-11a39 "
    "11a3b-11a3e 11a47 11a51-11a5b 11a8a-11a99 11c2f-11c36 11c38-11c3f 11c92-11ca7 11ca9-11cb6 11d31-11d36 11d3a 11d3c-11d3d 11d3f-11d45 11d47 11d8a-11d8e "
    "11d90-11d91 11d93-11d97 11ef3-11ef6 11f00-11f01 11f03 11f34-11f3a 11f3e-11f42 13440 13447-13455 16af0-16af4 16b30-16b36 16f4f 16f51-16f87 16f8f-16f92 "
    "16fe4 16ff0-16ff1 1bc9d-1bc9e 1cf00-1cf2d 1cf30-1cf46 1d165-1d169 1d16d-1d172 1d17b-1d182 1d185-1d18b 1d1aa-1d1ad 1d242-1d244 1da00-1da36 1da3b-1da6c "
    "1da75 1da84 1da9b-1da9f 1daa1-1daaf 1e000-1e006 1e008-1e018 1e01b-1e021 1e023-1e024 1e026-1e02a 1e08f 1e130-1e136 1e2ae 1e2ec-1e2ef 1e4ec-1e4ef "
    "1e8d0-1e8d6 1e944-1e94a e0100-e01ef "
)
def _mark_class() -> str:
    out = []
    for part in _MARK_RANGES.split():
        low, _, high = part.partition("-")
        out.append("\\U%08x" % int(low, 16) + ("-\\U%08x" % int(high, 16) if high else ""))
    return "".join(out)


_LETTER = r"(?:[^\W_]|[" + _mark_class() + r"])"
WORD = re.compile(r"[^\W_]" + _LETTER + r"*(?:['" + APOSTROPHES + r"][^\W_]" + _LETTER + r"*)*", re.UNICODE)
WORD_PLAIN = re.compile(r"[^\W_]+(?:['" + APOSTROPHES + r"][^\W_]+)*", re.UNICODE)                           # the same without marks: faster, for ASCII texts
_INVISIBLE = dict.fromkeys((0x00AD, 0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF))                  # soft hyphen, zero-width space, non-joiner, joiner, word joiner, zero-width no-break space
_CONTROLS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SURROGATES = re.compile(r"[\ud800-\udfff]")
REPLACEMENT = chr(0xFFFD)                                                                     # what a lone surrogate becomes in the prompt
WRITTEN = re.compile(r"\s*([0-9]{4}(?:-[0-9]{2}(?:-[0-9]{2})?)?)")
SENTENCE_END = re.compile(r"[.!?\n:;" + chr(0x2026) + "]")                                  # the ellipsis character ends a sentence too
SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")
WHEN = re.compile(r"^([0-9]{4})(?:-([0-9]{2})(?:-([0-9]{2})(?:[Tt ]([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:[.,][0-9]+)?)?\s*(Z|z|[+-][0-9]{2}(?::?[0-9]{2}(?::?[0-9]{2})?)?)?)?)?)?$")
STOP = frozenset((
    # English: articles, pronouns, auxiliaries, prepositions, conjunctions, determiners, adverbs of degree and time that carry no topic
    "a about above across after again against all almost along already also although always am among an and another any anyone anything are aren around as at "
    "be because been before behind being below beside besides between beyond both but by can cannot could couldn did didn do does doesn doing done down during "
    "each either else enough even ever every everyone everything few for from further had hadn has hasn have haven having he her here hers herself him himself his how however "
    "i if in indeed instead into is isn it its itself just least less let like many may maybe me might mightn mine more most much must mustn my myself near neither never no nobody none nor not nothing now "
    "of off often on once one only onto or other others otherwise our ours ourselves out over own per perhaps quite rather really same shall she should shouldn since so some somebody someone something "
    "sometimes still such than that the their theirs them themselves then there therefore these they this those though through throughout thus to too toward towards under unless until up upon us "
    "very via was wasn we were weren what whatever when whenever where whereas whether which while who whom whose why will with within without would wouldn yes yet you your yours yourself yourselves "
    # Polish: the first line is the 0.1.0 list, the rest is the moderate extension
    "w z na to nie jest się że do po od za o i a ale lub oraz "
    "czy jak co tak już też są być ten ta te tego tej tym ze bez dla przez przy pod nad przed który która które którzy których którym którego którą "
    "tylko jeszcze więc bo gdy gdzie kiedy jako ich jego jej ma mają może można będzie było była były byli był tu tam by aby żeby lecz ani albo "
    "ja ty on ona ono my wy oni one mnie ciebie sobie siebie mój moja moje twój twoja nasz wasz swój "
    "bardzo także również nawet kto kogo komu kim czym czego wśród między około jednak choć chociaż więcej mniej każdy wszystko wszyscy inny taki tyle ile jaki jaka jakie niż poza "
    "przeciw wobec dzięki według podczas ponieważ zatem dlatego natomiast ponadto zaś czyli").split())
CLITICS = frozenset(("s", "m", "re", "ve", "ll", "d", "t"))
# Words of the stop lists that are names, months or acronyms when written with a capital inside a sentence or in capitals (the US, in May, Yoko Ono, Acme Co): kept then.
AMBIGUOUS = frozenset(("us", "may", "ten", "co", "ma", "ono", "ale", "bo"))
# Singular words that end in s: kept as they are, and their -es plural folds back to them (biases -> bias).
S_SINGULAR = frozenset((
    "bias gas atlas canvas alias lens news series species means status virus focus bonus campus census consensus corpus bus plus minus genus radius stimulus surplus nucleus syllabus "
    "apparatus prospectus nexus locus lotus cactus fungus hiatus chorus walrus genius analysis basis thesis hypothesis synthesis diagnosis crisis emphasis axis oasis parenthesis "
    "paralysis tennis iris chaos kudos ethos pathos cosmos").split())
CHE_SINGULAR = frozenset("cache niche headache ache apache avalanche moustache mustache cliche psyche quiche tranche panache creche brioche".split())
IRREGULAR = {"children": "child", "indices": "index", "matrices": "matrix", "vertices": "vertex", "appendices": "appendix", "criteria": "criterion", "phenomena": "phenomenon",
             "analyses": "analysis", "hypotheses": "hypothesis", "theses": "thesis", "syntheses": "synthesis", "crises": "crisis", "axes": "axis", "diagnoses": "diagnosis",
             "emphases": "emphasis", "oases": "oasis", "mice": "mouse", "corpora": "corpus",
             "quizzes": "quiz", "heroes": "hero", "potatoes": "potato", "tomatoes": "tomato", "echoes": "echo", "vetoes": "veto", "embargoes": "embargo", "volcanoes": "volcano",
             "wolves": "wolf", "knives": "knife", "wives": "wife", "shelves": "shelf", "halves": "half", "thieves": "thief", "calves": "calf", "loaves": "loaf", "scarves": "scarf",
             "elves": "elf", "selves": "self", "people": "person", "men": "man", "women": "woman", "teeth": "tooth", "feet": "foot", "geese": "goose"}
# Profile keys. lex_tau: the share of the query's reference mass (see the module docstring) an item's BM25 score must reach (above 0); min_evidence: the idf mass of the query stems
# the item has, at least, as a share of the idf of a word seen once among the items of the call (1.4: two rare words); k1, b: BM25; len_cap: an item counts as at most this many
# times the average length (0 = no cap); top_terms: how many of the most informative known query stems make the reference (0 = all); max_terms: how many are scored at all
# (0 = all); tau: cosine of the embedder (above 0); embed: auto (when the index has an embedder), off, required (degraded without one); names: the channel for rare capitalised
# words, only for the task types in name_task_types, rare = document frequency up to rare_df; persona_task_types: the task types for which invented autobiography is considered;
# require_zone: refuse a now that has no zone; timeout_ms: infinity switches the deadline off. A key that is not in this list is an error.
_BASE = {"k": 3, "lex_tau": 0.20, "min_evidence": 1.4, "k1": 1.2, "b": 0.75, "len_cap": 3.0, "top_terms": 10, "max_terms": 20, "tau": 0.57, "names": True,
         "name_task_types": ("personal",), "rare_df": 2, "persona_task_types": ("personal",), "timeout_ms": 300, "require_zone": False}
PROFILES: Dict[str, Dict] = {"kernel": dict(_BASE, embed="auto"), "lexical": dict(_BASE, embed="off"), "hybrid": dict(_BASE, embed="required")}
PROFILE_KEYS = frozenset(PROFILES["kernel"]) | {"name"}
Embedder = Callable[[List[str]], List[List[float]]]


@dataclass(frozen=True)
class Item:
    id: str
    kind: str                                  # note | reply | comment | event
    origin: str                                # account_history | fiction_autobio | world_knowledge
    created_at: str                            # ISO 8601; see the module docstring
    text: str                                  # the account's own text only
    trace: Optional[Dict[str, str]] = None     # {"gist", "angle", "open"}, each text
    meta: Dict = field(default_factory=dict)   # meta["supersedes"] = the id of an earlier item this one replaces


@dataclass
class Index:
    as_of: str
    as_of_key: str
    items: Dict[str, Item]
    keys: Dict[str, str]                       # id -> created_at as a canonical UTC key
    toks: Dict[str, frozenset]                 # id -> content stems
    names: Dict[str, frozenset]                # id -> stems written with a capital and never in lower case in the item
    lower: Set[str]                            # stems written in lower case somewhere in the index
    df: Dict[str, int]
    vectors: Dict[str, array]                  # id -> unit vector
    dim: int
    embedder: Optional[Embedder]
    superseded_by: Dict[str, str]              # id -> the earliest key of a later item that replaces it
    rejected: Dict[str, int]                   # future, invalid, duplicate
    degraded: str = ""
    built_ms: float = 0.0
    tf: Dict[str, Dict[str, int]] = field(default_factory=dict)       # id -> stem -> count in the item
    dl: Dict[str, int] = field(default_factory=dict)                  # id -> number of content stems (repeats counted)
    avgdl: float = 0.0
    unforced: Dict[str, frozenset] = field(default_factory=dict)      # id -> stems capitalised in the middle of a sentence or in capitals (read together with names)
    trace_dropped: int = 0                                            # items whose trace is not usable as it was given (render ignores the bad part); the items are kept as they are
    source_error: str = ""                                            # set when the iterable of items failed midway: the index holds the items read so far
    post: Dict[str, List[str]] = field(default_factory=dict)          # stem -> ids of the items that have it (the postings that retrieve reads for the stems of a query)


def _show(value) -> str:
    """A short, safe text of any value, for messages."""
    try:
        return repr(value)[:40]
    except Exception:
        return "<%s>" % type(value).__name__


def _when(value) -> Tuple[str, bool]:
    """(the canonical key, whether the value carried a zone). ValueError, and only ValueError, when the value is not a date."""
    try:
        if isinstance(value, str):
            text = value
        elif hasattr(value, "isoformat"):
            text = value.isoformat()
        else:
            raise ValueError("not an ISO 8601 date: %s" % _show(value))
        if not isinstance(text, str):
            raise ValueError("not an ISO 8601 date: %s" % _show(value))
    except ValueError:
        raise
    except Exception:
        raise ValueError("not an ISO 8601 date: %s" % _show(value)) from None
    match = WHEN.match(text.strip())
    if not match:
        raise ValueError("not an ISO 8601 date: %s" % _show(text))
    year, month, day, hour, minute, second, zone = match.groups()
    try:
        moment = datetime(int(year), int(month or 1), int(day or 1), int(hour or 0), int(minute or 0), int(second or 0))
        if zone and zone not in ("Z", "z"):
            digits = zone[1:].replace(":", "")
            hours, minutes, seconds = int(digits[:2]), int(digits[2:4] or 0), int(digits[4:6] or 0)
            if hours > 23 or minutes > 59 or seconds > 59:
                raise ValueError("zone offset out of range")
            moment -= (-1 if zone[0] == "-" else 1) * timedelta(hours=hours, minutes=minutes, seconds=seconds)
    except OverflowError:
        raise ValueError("date out of range: %s" % _show(text)) from None
    return moment.isoformat(), zone is not None


def when(value) -> str:
    """The canonical key 'YYYY-MM-DDTHH:MM:SS' (UTC) of an ISO 8601 date or datetime, a year, month, day or time missing from the right allowed; ValueError otherwise.

    Only text and date/datetime objects are accepted, and only ValueError is ever raised. A time without a zone is UTC. The zone offset (hours, minutes and seconds) must be
    within +-23:59:59."""
    return _when(value)[0]


def _singular(w: str) -> str:
    """Fold the plural of a lower-case word to its singular; a few singulars that end in s are kept, a final -ie becomes -y on both forms (movies, movie -> movy)."""
    n = len(w)
    if w in IRREGULAR:
        return IRREGULAR[w]
    if n < 4 or w[-1] != "s":
        return w[:-2] + "y" if n >= 5 and w.endswith("ie") else w
    if w in S_SINGULAR:
        return w
    if w.endswith("ies"):
        return w[:-3] + "y" if n > 4 else w[:-1]
    if w.endswith("ss") or w.endswith("ous"):
        return w
    if w.endswith(("sses", "shes", "xes", "zzes")):
        return w[:-2]
    if w.endswith("ches"):
        return w[:-1] if w[:-1] in CHE_SINGULAR else w[:-2]
    if w.endswith("ses"):
        return w[:-2] if w[:-2] in S_SINGULAR else w[:-1]
    return w[:-1]


def _stem_raw(word: str) -> str:
    w = word.translate(APOSTROPHE_TABLE)
    if len(w) >= 3 and w.endswith("s") and w[:-1].isupper():          # an acronym in the plural: GPUs, LLMs, IDs, H100s
        return w[:-1].lower()
    w = w.lower()
    if w.endswith("'s"):
        w = w[:-2]
    return _singular(w)


_stem = lru_cache(maxsize=1 << 16)(_stem_raw)


def stem(word: str) -> str:
    """Lower case, possessive removed, plural folded: gpus, GPUs -> gpu; ferries -> ferry; processes -> process; biases -> bias; Imre's -> imre. '' for what is not text."""
    if not isinstance(word, str):
        return ""
    return _stem(word) if len(word) <= LONG_TOKEN else _stem_raw(word)            # a very long token is not worth a place in the cache


def _root_raw(surface: str, keep: bool = False) -> str:
    """The content stem of a word as written, or '' when it is a stop word, a contraction of function words, or a single letter. `keep`: the word is written with a capital
    in the middle of a sentence (or in capitals), which saves the few words that are names, acronyms or months in capitals (US, May, Ono) from the stop list."""
    word = surface.translate(APOSTROPHE_TABLE)
    low = word.lower()
    if low in STOP and not (keep and low in AMBIGUOUS):
        return ""
    if "'" in low:
        parts = low.split("'")
        if all(p in CLITICS for p in parts[1:]):                       # isn't, I'm, they've, it's, Alice's, couldn't've
            if parts[0] in STOP or ("t" in parts[1:] and parts[0].endswith("n")):
                return ""
            word = word[:len(parts[0])]
    root = stem(word)
    if root in STOP and not (keep and root in AMBIGUOUS):
        return ""
    return "" if len(root) < 2 else root


_root = lru_cache(maxsize=1 << 17)(_root_raw)


def _acronym(surface: str) -> bool:
    return len(surface) >= 3 and (surface.isupper() or (len(surface) >= 4 and surface.endswith("s") and surface[:-1].isupper()))


def analyse(text: str) -> Tuple[List[str], Set[str], Set[str], Set[str]]:
    """(content stems in order, stems written with a capital, stems capitalised inside a sentence or in capitals, stems written in lower case).

    At most MAX_TEXT_CHARS characters are read; invisible characters (soft hyphen, zero-width space, joiners) are removed before the words are cut."""
    if not isinstance(text, str):
        return [], set(), set(), set()
    text = unicodedata.normalize("NFC", text[:MAX_TEXT_CHARS].translate(_INVISIBLE))
    stems: List[str] = []
    capital: Set[str] = set()
    inside: Set[str] = set()
    lower: Set[str] = set()
    previous_end: Optional[int] = None
    for match in (WORD_PLAIN if text.isascii() else WORD).finditer(text):                # marks can only be in a text that is not ASCII
        surface = match.group()
        initial = previous_end is None or SENTENCE_END.search(text, previous_end, match.start()) is not None
        previous_end = match.end()
        capitalised = surface[0].isupper()
        root_of = _root if len(surface) <= LONG_TOKEN else _root_raw
        root = root_of(surface, capitalised and (not initial or (len(surface) >= 2 and surface.isupper())))
        if not root:
            continue
        stems.append(root)
        if capitalised:
            capital.add(root)
            if not initial or _acronym(surface):
                inside.add(root)
        else:
            lower.add(root)
    return stems, capital, inside, lower


def tokens(text: str) -> List[str]:
    return analyse(text)[0]


def item_id(kind: str, created_at: str, text: str) -> str:
    """kind-date-hash of the text: stable across processes. '' when the text cannot be hashed (not text, or not encodable)."""
    try:
        return "%s-%s-%s" % (kind, str(created_at)[:10], hashlib.sha256(text.encode("utf-8")).hexdigest()[:8])
    except Exception:
        return ""


def write_back_item(text: str, created_at: str, about: str = "") -> Item:
    """A personal detail that the persona improvised, as an invented-autobiography event with a deterministic id, to be added to the next index.

    Never raises: input that cannot be turned into an item gives an item with an empty id, which build_index rejects as invalid."""
    try:
        body = ("%s %s" % (about, text)).strip()
        return Item(item_id("event", created_at, body), "event", "fiction_autobio", created_at, body)
    except Exception:
        return Item("", "event", "fiction_autobio", "", "")


def _unit(vector: Sequence[float]) -> array:
    out = array("d", (float(x) for x in vector))
    norm = math.sqrt(sum(map(mul, out, out)))
    if not math.isfinite(norm):
        raise ValueError("a vector is not finite")
    if norm > 0:
        for i in range(len(out)):
            out[i] /= norm
    return out


def _trace_broken(trace) -> bool:
    """Whether a trace has a part that render() will ignore: it is not a dict, or one of gist, angle, open is neither text nor missing."""
    if trace is None:
        return False
    if not isinstance(trace, dict):
        return True
    return any(trace.get(name) is not None and not isinstance(trace.get(name), str) for name in TRACE_KEYS)


def build_index(items: Sequence[Item], as_of: str, embedder: Optional[Embedder] = None, vectors: Optional[Dict[str, Sequence[float]]] = None) -> Index:
    """Index the items dated up to as_of; later, invalid and duplicate items are dropped and counted in index.rejected (future, invalid, duplicate). vectors maps ids to
    ready embeddings (a cache).

    The items are kept as they were passed (retrieve returns the very objects). A trace that is not a dict, or has a value that is not text, is counted once in
    index.trace_dropped; the item stays and render() ignores the bad part. If the iterable of items fails midway, the items read so far are indexed and index.source_error says
    so (retrieve then reports status degraded)."""
    started = time.perf_counter()
    as_of_key = when(as_of)
    idx = Index(as_of=_text_of(as_of) or "", as_of_key=as_of_key, items={}, keys={}, toks={}, names={}, lower=set(), df={}, vectors={}, dim=0, embedder=None, superseded_by={},
                rejected={"future": 0, "invalid": 0, "duplicate": 0})
    kept: List[Item] = []
    listed: List = []
    try:
        for it in items:
            listed.append(it)
    except Exception as exc:
        idx.rejected["invalid"] += 1
        idx.source_error = "items could not be read: %s" % type(exc).__name__
    for it in listed:
        try:
            if it.kind not in KINDS or it.origin not in ORIGINS or not isinstance(it.id, str) or not it.id or not isinstance(it.text, str) or not it.text.strip():
                idx.rejected["invalid"] += 1
                continue
            key = when(it.created_at)
            if key > idx.as_of_key:
                idx.rejected["future"] += 1
            elif it.id in idx.items:
                idx.rejected["duplicate"] += 1
            else:
                if _trace_broken(getattr(it, "trace", None)):
                    idx.trace_dropped += 1
                idx.items[it.id], idx.keys[it.id] = it, key
                kept.append(it)
        except Exception:
            idx.rejected["invalid"] += 1
    total = 0
    for it in kept:
        stems, capital, inside, lower = analyse(it.text)
        counts = Counter(stems)
        idx.tf[it.id], idx.dl[it.id], total = dict(counts), len(stems), total + len(stems)
        idx.toks[it.id], idx.names[it.id], idx.unforced[it.id] = frozenset(counts), frozenset(capital - lower), frozenset(inside)
        idx.lower |= lower
        for root in counts:
            idx.df[root] = idx.df.get(root, 0) + 1
            listed = idx.post.get(root)
            if listed is None:
                idx.post[root] = [it.id]
            else:
                listed.append(it.id)
    idx.avgdl = total / len(kept) if kept else 0.0
    replaces = {}
    for it in kept:
        meta = getattr(it, "meta", None)
        if isinstance(meta, dict) and meta.get("supersedes"):
            replaces[it.id] = str(meta.get("supersedes"))

    def closes_cycle(new: str, old: str) -> bool:
        """Whether `old` already replaces `new`, through items of the same instant (so that the link new -> old would be a cycle)."""
        node = old
        for _ in range(len(replaces) + 1):
            target = replaces.get(node)
            if target is None or idx.keys.get(target) != idx.keys[old]:
                return False
            if target == new:
                return True
            node = target
        return True

    for it in kept:                                                  # a replacement counts from its own date, and only an item of the same or a later instant can replace
        old = replaces.get(it.id, "")
        if not old or old == it.id or old not in idx.keys or idx.keys[old] > idx.keys[it.id]:
            continue
        if idx.keys[old] == idx.keys[it.id] and closes_cycle(it.id, old):
            continue
        if old not in idx.superseded_by or idx.keys[it.id] < idx.superseded_by[old]:
            idx.superseded_by[old] = idx.keys[it.id]
    try:
        for ident, vector in (vectors or {}).items():
            if ident in idx.items:
                idx.vectors[ident] = _unit(vector)
        missing = [it for it in kept if it.id not in idx.vectors]
        if embedder is not None and missing:
            produced = embedder([it.text for it in missing])
            if len(produced) != len(missing):
                raise ValueError("%d vectors for %d texts" % (len(produced), len(missing)))
            for it, vector in zip(missing, produced):
                idx.vectors[it.id] = _unit(vector)
        sizes = {len(v) for v in idx.vectors.values()}
        if len(sizes) > 1:
            raise ValueError("vectors of different sizes")
        idx.dim, idx.embedder = (sizes.pop() if sizes else 0), embedder
    except Exception as exc:                                         # the index stays usable, lexically
        idx.vectors, idx.dim, idx.embedder, idx.degraded = {}, 0, None, "embedder failed at build: %s" % type(exc).__name__
    idx.built_ms = (time.perf_counter() - started) * 1000.0
    return idx


def _as_types(value) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def _number(prof: Dict, key: str, low: float = 0.0, high: float = math.inf) -> float:
    try:
        value = float(prof[key])
    except (TypeError, ValueError):
        raise ValueError("profile %s is not a number: %r" % (key, prof[key])) from None
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("profile %s out of range: %r" % (key, prof[key]))
    return value


def _profile(profile: Union[str, Dict, None]) -> Dict:
    if isinstance(profile, dict):
        unknown = [str(k) for k in profile if k not in PROFILE_KEYS]
        if unknown:                                                  # a mistyped key must not silently leave a threshold at its default
            raise ValueError("unknown profile key: %s" % ", ".join(sorted(unknown))[:60])
        prof = dict(PROFILES["kernel"], name=str(profile.get("name", "custom")), **{k: v for k, v in profile.items() if k != "name"})
    else:
        name = "kernel" if profile is None else profile
        if name not in PROFILES:
            raise KeyError("unknown profile %r" % (profile,))
        prof = dict(PROFILES[name], name=name)
    if prof["embed"] not in ("auto", "off", "required"):
        raise ValueError("profile embed must be auto, off or required: %r" % (prof["embed"],))
    prof["name_task_types"], prof["persona_task_types"] = _as_types(prof["name_task_types"]), _as_types(prof["persona_task_types"])
    prof["k"] = max(0, int(prof["k"]))
    prof["top_terms"], prof["max_terms"], prof["rare_df"] = (max(0, int(prof[key])) for key in ("top_terms", "max_terms", "rare_df"))
    prof["lex_tau"], prof["min_evidence"], prof["b"] = _number(prof, "lex_tau"), _number(prof, "min_evidence"), _number(prof, "b", 0.0, 1.0)
    prof["k1"], prof["len_cap"] = _number(prof, "k1", 0.0, 100.0), _number(prof, "len_cap")
    if prof["lex_tau"] <= 0.0:
        raise ValueError("profile lex_tau must be above zero: %r" % (prof["lex_tau"],))
    timeout = float(prof["timeout_ms"])
    if math.isnan(timeout):
        raise ValueError("profile timeout_ms is not a number")
    prof["timeout_ms"] = timeout                                     # infinity switches the deadline off
    if prof["tau"] is None and prof["embed"] != "off":
        raise ValueError("profile tau is needed when the embedding channel is on")
    prof["tau"] = None if prof["tau"] is None else _number(prof, "tau", 0.0)
    if prof["tau"] is not None and prof["tau"] <= 0.0:
        raise ValueError("profile tau must be above zero: %r" % (prof["tau"],))
    prof["names"], prof["require_zone"] = bool(prof["names"]), bool(prof["require_zone"])
    return prof


def _text_of(value) -> Optional[str]:
    if value is None:
        return None
    try:
        return str(value)
    except Exception:
        return "?"


def _blank(status: str, query: str, prof: Dict, task_type: str, now: Optional[str], started: float, error: str = "", index: Optional[Index] = None) -> Dict:
    return {"status": status, "items": [], "n_candidates": 0, "n_considered": 0, "scores": [], "channel_scores": [], "reasons": [], "dates": [], "keys": [], "latency_ms":
            round((time.perf_counter() - started) * 1000.0, 3), "tokens_est": 0, "profile": prof.get("name", ""), "task_type": task_type, "now": now, "now_key": "",
            "as_of": index.as_of if isinstance(index, Index) else None, "n_index": len(index.items) if isinstance(index, Index) else 0, "k": prof.get("k"), "tau": prof.get("tau"),
            "lex_tau": prof.get("lex_tau"), "min_evidence": prof.get("min_evidence"), "persona_task_types": list(prof.get("persona_task_types", ())), "error": error,
            "rejected": dict(index.rejected) if isinstance(index, Index) else {}, "_query": query}


def _idf(n_docs: int, df: int) -> float:
    return math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))


def _lexical_terms(df: Dict[str, int], n_docs: int, stems: Sequence[str], prof: Dict) -> Tuple[List[str], Dict[str, float], float]:
    """(the scored stems best first, their idf, the reference mass): stems that some item of the call has, at most max_terms, rarest first and, among equally rare ones, in the
    order of the query; the reference covers the top_terms with the highest idf. df and n_docs are those of the items the call may see."""
    docs = max(1, n_docs)
    first: Dict[str, int] = {}
    for position, t in enumerate(stems):
        first.setdefault(t, position)
    weights = {t: _idf(docs, df[t]) for t in first if df.get(t, 0) > 0}
    terms = sorted(weights, key=lambda t: (-weights[t], first[t]))
    if prof["max_terms"]:
        terms = terms[: prof["max_terms"]]
    head = terms[: prof["top_terms"]] if prof["top_terms"] else terms
    return terms, weights, (prof["k1"] + 1.0) * sum(weights[t] for t in head)


def _lexical(index: Index, seen: Dict[str, Item], df: Dict[str, int], n_docs: int, avgdl: float, stems: Sequence[str], prof: Dict):
    """(terms, weights, reference, floor, scores, gained): the scored stems, their idf, the reference mass, the evidence floor, and for every item of the call that has a scored
    stem its BM25 score and the idf mass of the scored stems it has. The postings of the scored stems (the rarest ones) are read term by term, so that the cost depends on how
    many items share those stems, not on the size of the index. The length of an item counts at most len_cap times the average length of the call."""
    terms, weights, reference = _lexical_terms(df, n_docs, stems, prof)
    floor = prof["min_evidence"] * _idf(max(1, n_docs), 1)
    cap = prof["len_cap"] * avgdl if prof["len_cap"] > 0 else math.inf
    k1, b = prof["k1"], prof["b"]
    base = 1.0 - b
    post = _postings(index)
    scores: Dict[str, float] = {}
    gained: Dict[str, float] = {}
    for t in terms:                                                  # in the order of the terms: the same order of summation for every item, in every process
        w = weights[t]
        for ident in post.get(t, ()):
            if ident in seen:
                f = index.tf[ident][t]
                norm = k1 * (base + b * min(index.dl[ident], cap) / (avgdl or 1.0))
                scores[ident] = scores.get(ident, 0.0) + w * f * (k1 + 1.0) / (f + norm)
                gained[ident] = gained.get(ident, 0.0) + w
    return terms, weights, reference, floor, scores, gained


def _postings(index: Index) -> Dict[str, List[str]]:
    """stem -> ids of the items that have it, in the order of the index (made on first use for an Index that was not built by build_index)."""
    if not index.post and index.toks:
        for ident, stems in index.toks.items():
            for t in stems:
                index.post.setdefault(t, []).append(ident)
    return index.post


def _survey(index: Index, wanted: Set[str], now_key: str, persona_ok: bool, qv=None, deadline: Optional[float] = None):
    """One pass over the items that a call may see (dated before now_key, not yet replaced, invented autobiography only when persona_ok).

    Returns (seen, df, cosines, n_docs, avgdl) or None when the deadline passes: the items of the call by id, the document frequency of each wanted stem among them, the cosine of
    each of them that has a vector (when qv is given), their number and their average length. df, n_docs and avgdl are the statistics of exactly those items, so that what a call
    may not see (fiction in a task that does not allow it, items from the future of the task, replaced items) cannot change the idf of what it may: such an item takes its stems
    out of the document frequencies of the index."""
    seen: Dict[str, Item] = {}
    cosines: Dict[str, float] = {}
    df = {t: index.df[t] for t in wanted if t in index.df}
    total = 0
    for n, (ident, it) in enumerate(index.items.items()):
        if deadline is not None and n % 200 == 0 and time.perf_counter() > deadline:
            return None
        if index.keys[ident] >= now_key or (ident in index.superseded_by and index.superseded_by[ident] < now_key) or (it.origin == "fiction_autobio" and not persona_ok):
            for t in wanted.intersection(index.toks[ident]):
                df[t] -= 1
            continue
        seen[ident] = it
        total += index.dl[ident]
        if qv is not None and ident in index.vectors:
            cosines[ident] = sum(map(mul, qv, index.vectors[ident]))
    return seen, df, cosines, len(seen), (total / len(seen) if seen else 0.0)


def retrieve(index: Index, query: str, task_type: str = "note", now: Optional[str] = None, profile: Union[str, Dict, None] = "kernel") -> Dict:
    """The items (at most k) that pass a gate for this query, dated strictly before now, best first (names first). Nothing below the thresholds. Never raises.

    scores are in units of the gate (1.0 = exactly at the threshold of the channel that likes the item most); channel_scores keep the raw lexical score s and cosine.
    result["now"] is text (never the object that was passed) and result["now_key"] the canonical UTC key. A query is read up to MAX_QUERY_CHARS characters.
    """
    started = time.perf_counter()
    prof: Dict = {}
    if isinstance(query, str):
        query = query[:MAX_QUERY_CHARS]
    if not (task_type is None or isinstance(task_type, str)):
        task_type = "<%s>" % type(task_type).__name__                 # the result and the log hold JSON types only
    shown_now, now_key = _text_of(now), ""
    try:
        if not isinstance(index, Index):
            raise TypeError("not an Index")
        prof = _profile(profile)
        if not isinstance(query, str):
            raise TypeError("query is not text")
        if now is None:
            now, shown_now = index.as_of, index.as_of
        now_key, zoned = _when(now)
        if prof["require_zone"] and not zoned:
            raise ValueError("now has no zone")
        deadline = started + prof["timeout_ms"] / 1000.0
        stems, capital, inside, lower = analyse(query)
        status, error, qv = "ok", "", None
        if index.source_error:
            status, error = "degraded", index.source_error
        if prof["embed"] != "off":
            if index.degraded:
                status, error = "degraded", index.degraded
            elif index.embedder is None:
                if prof["embed"] == "required":
                    status, error = "degraded", "no embedder"
            elif index.vectors:                                      # nothing to compare with in an empty index: the embedder is not called
                try:
                    qv = _unit(index.embedder([query])[0])
                    if len(qv) != index.dim:
                        raise ValueError("query vector of another size")
                except Exception as exc:
                    status, error, qv = "degraded", "embedder failed at query: %s" % type(exc).__name__, None
        lex_tau, tau = prof["lex_tau"], prof["tau"]
        persona_ok = task_type in prof["persona_task_types"]
        survey = _survey(index, set(stems), now_key, persona_ok, qv, deadline)
        if survey is None:
            return dict(_blank("timeout", query, prof, task_type, shown_now, started, "deadline exceeded", index), now_key=now_key)
        seen, df, cosines, n_docs, avgdl = survey
        terms, weights, reference, floor, scores, gained = _lexical(index, seen, df, n_docs, avgdl, stems, prof)
        post = _postings(index)
        rare: List[str] = []
        if prof["names"] and task_type in prof["name_task_types"]:
            only_capital = {t for t in capital if t not in lower}
            lowered: Set[str] = set()
            for t in sorted(only_capital):                           # a capitalised word that some item of this call writes in lower case is an ordinary word
                for ident in post.get(t, ()):
                    if ident in seen and t not in index.names[ident]:        # it is in the postings of t, so it has t; not a name there: written in lower case somewhere
                        lowered.add(t)
                        break
            named = set(inside) | (only_capital - lowered)
            rare = sorted(t for t in named if 0 < df.get(t, 0) <= prof["rare_df"] and len(t) >= 3)
        named_hits: Set[str] = set()
        for t in rare:
            for ident in post.get(t, ()):
                if ident in seen and t in index.names[ident] and (t in inside or t in index.unforced[ident]):
                    named_hits.add(ident)
        candidates = set(scores) | named_hits
        if qv is not None:
            candidates.update(ident for ident, cos in cosines.items() if cos >= tau)
        found: List[Tuple[int, float, str, Item, List[str], Dict]] = []
        for ident in candidates:
            it = seen[ident]
            s = scores.get(ident, 0.0) / reference if reference > 0 else 0.0
            cos = cosines.get(ident)
            reasons = []
            if ident in named_hits:
                reasons.append("name")
            if gained.get(ident, 0.0) >= floor and s >= lex_tau:
                reasons.append("lexical")
            if cos is not None and cos >= tau:
                reasons.append("embedding")
            if reasons:
                strength = max(s / lex_tau, (cos / tau) if cos is not None else 0.0)
                if "name" in reasons:
                    strength = max(strength, 1.0)
                found.append((0 if "name" in reasons else 1, -strength, ident, it, reasons, {"lexical": round(s, 4), "embedding": None if cos is None else round(cos, 4)}))
        found.sort(key=lambda row: (row[0], row[1], row[2]))
        top = found[: int(prof["k"])]
        result = _blank(status, query, prof, task_type, shown_now, started, error, index)
        result.update({"items": [row[3] for row in top], "n_candidates": len(found), "n_considered": n_docs, "scores": [round(-row[1], 4) for row in top],
                       "channel_scores": [row[5] for row in top], "reasons": [row[4] for row in top], "keys": [index.keys[row[2]] for row in top],
                       "dates": [index.keys[row[2]][:10] for row in top], "now_key": now_key,
                       "_df": {t: index.df[t] for t in sorted({t for row in top for t in index.toks[row[2]]})}})        # private: the guard weighs shared words with it
        result["tokens_est"] = (len(render(result)) + 3) // 4
        result["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        return result
    except Exception as exc:
        return dict(_blank("error", query if isinstance(query, str) else "", prof, task_type, shown_now, started, "%s: %s" % (type(exc).__name__, str(exc)[:80]),
                           index if isinstance(index, Index) else None), now_key=now_key)


def _body(item, mode: str, limit: int = 0) -> Optional[str]:
    """The text of one item for the prompt on one line, or None when the item has nothing to show. Control characters become spaces, lone surrogates U+FFFD."""
    text = getattr(item, "text", None)
    if not isinstance(getattr(item, "id", None), str) or not isinstance(text, str) or not text.strip():
        return None
    body = text
    trace = getattr(item, "trace", None)
    if mode == "trace" and isinstance(trace, dict) and isinstance(trace.get("gist"), str) and trace["gist"].strip():
        parts = [trace["gist"]]
        for label, name in (("Angle: ", "angle"), ("Left open: ", "open")):
            if isinstance(trace.get(name), str) and trace[name].strip():
                parts.append(label + trace[name])
        body = " ".join(parts)
    body = " ".join(_CONTROLS.sub(" ", _SURROGATES.sub(REPLACEMENT, body)).split())
    if limit and len(body) > limit:
        cut = body[:limit]
        space = cut.rfind(" ")
        body = (cut[:space] if space > limit // 2 else cut) + " ..."
    return body


def _label(item, key: str) -> str:
    """The date shown for an item: the one it was written with (to the precision it has, in its own zone) when the key agrees with it, else the UTC day of the key."""
    try:
        raw = item.created_at
        text = raw if isinstance(raw, str) else raw.isoformat()
        if when(text) == key:
            written = WRITTEN.match(text)
            if written:
                return written.group(1)
    except Exception:
        pass
    return key[:10]


def _lines(result, mode: str, limit: int = 0) -> List[Tuple[int, str, str, str, str]]:
    """(position in result["items"], date key, item id, body, date label) of every item that is shown, oldest first. THE rule of the shown items: a text and a date."""
    items = result.get("items", []) if isinstance(result, dict) else list(result)
    keys = result.get("keys") if isinstance(result, dict) else None
    keys = keys if isinstance(keys, (list, tuple)) and len(keys) == len(items) else [None] * len(items)
    rows = []
    for position, item in enumerate(items):
        try:
            body = _body(item, mode, limit)
            key = keys[position] if isinstance(keys[position], str) else when(item.created_at)
            if body is not None:
                rows.append((position, key, item.id, body, _label(item, key)))
        except Exception:
            continue
    return sorted(rows, key=lambda row: (row[1], row[2], row[0]))


def render(result, mode: str = "trace", max_item_chars: int = 4000) -> str:
    """Text for the prompt: one line per item, oldest first, with its date and no label of origin; an empty result is the empty string.

    mode "trace" uses the item's trace (gist, angle, what was left open) when it has a gist, "raw" always the text. Whitespace and control characters inside an item are
    collapsed, so an item can never add a line of its own (a date-like text inside a line stays inline text). The date is the one the item was written with. An item longer than
    max_item_chars (0 = no limit) is cut at a word and ends in ' ...'. A broken item falls back to its raw text, or is skipped when it has no text or no date; the others are
    still shown."""
    try:
        return "\n".join("[%s] %s" % (label, body) for _, _, _, body, label in _lines(result, mode, max_item_chars))
    except Exception:
        return ""


def _shown(result) -> Tuple[List[Item], List[int]]:
    """The items of a result that render() shows, in the order of result["items"], and their positions there (the same rule for render, log_record and guard)."""
    positions = sorted(row[0] for row in _lines(result, "raw"))
    return [result["items"][p] for p in positions], positions


def _safe_error(error) -> str:
    return str(error or "").split(":", 1)[0][:60]


def _scrub(text):
    """The text as hmac_fn can encode it: a lone surrogate becomes its backslash escape, so that the record of such an input is not lost."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8") if isinstance(text, str) else text


def log_record(result: Dict, hmac_fn: Callable[[str], str], key: Optional[str] = None, raw_ids: bool = False) -> Dict:
    """One record for the injection log: keyed hashes of the query (or of `key`) and of the item ids, kinds, origins, dates, scores, reasons, counts; never any text.

    The record holds only JSON types: now is text and now_key the canonical UTC key; error keeps only the part of the message before the first colon; rejected holds the
    counters of the index (future, invalid, duplicate), so that a feed that was rejected whole shows in the log; unicode is the version of the Unicode tables that cut the words.
    The items of the record are the ones render() shows. The result carries the query privately (_query) only to be hashed here; do not log the result itself. raw_ids adds
    the ids as they are.
    """
    try:
        items, positions = _shown(result)

        def pick(name: str) -> list:
            values = result.get(name, [])
            return [values[p] for p in positions if p < len(values)]

        def keyed(text: str) -> str:
            digest = hmac_fn(_scrub(text))
            if not isinstance(digest, str):
                raise TypeError("hmac_fn must return text")
            return digest

        rejected = result.get("rejected")
        record = {"kernel_version": VERSION, "unicode": unicodedata.unidata_version, "status": result.get("status"), "profile": result.get("profile"),
                  "task_type": result.get("task_type"), "now": result.get("now") if result.get("now_key") else None, "now_key": result.get("now_key"), "as_of": result.get("as_of"),
                  "query_hmac": keyed(key if key is not None else result.get("_query", "")), "item_hmacs": [keyed(i.id) for i in items], "kinds": [i.kind for i in items],
                  "origins": [i.origin for i in items], "dates": pick("dates"), "scores": pick("scores"), "channel_scores": [dict(c) for c in pick("channel_scores")],
                  "reasons": [list(r) for r in pick("reasons")], "n_candidates": result.get("n_candidates"), "n_considered": result.get("n_considered"),
                  "n_index": result.get("n_index"), "rejected": {str(k): v for k, v in rejected.items() if isinstance(v, int)} if isinstance(rejected, dict) else {},
                  "k": result.get("k"), "tau": result.get("tau"), "lex_tau": result.get("lex_tau"), "min_evidence": result.get("min_evidence"),
                  "latency_ms": result.get("latency_ms"), "tokens_est": result.get("tokens_est"), "error": _safe_error(result.get("error", ""))}
        if raw_ids:
            record["ids"] = [i.id for i in items]
        return record
    except Exception as exc:
        return {"kernel_version": VERSION, "status": "error", "error": "log_record: %s" % type(exc).__name__}


# ---- the reference guard -------------------------------------------------------------------------------------------------------------------------------------------------
# A reference is recognised by grammar, not by a list of phrases: a first-person subject with a verb of saying or writing and a past anchor outside the text being written
# (last week, two months ago, earlier, before, already, in my last post), a verb of writing with a topic (wrote about), a possessive with a qualifier or a past verb or a
# previous-issue noun (my last post, my newsletter covered, an earlier issue, last week's newsletter), a stance phrase with an anchor (as I said last month, as I wrote earlier),
# a habit of saying (I keep saying), readers who are said to remember (regular readers will remember). A bare possessive (subscribe to my newsletter), a bare stance (as I said,
# this is hard), a first-person act of making (I wrote a script last week) and a greeting (welcome back, regular readers) are not references.
# References to the text itself (above, earlier in this note, the previous paragraph) cancel a match, clause by clause, unless that clause also has an anchor outside the text.
_ZERO_WIDTH = dict.fromkeys((0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD))             # zero-width space, non-joiner, joiner, word joiner, no-break space of zero width, soft hyphen
_CONFUSABLES = {ord(a): b for a, b in zip("\u0430\u0441\u0435\u043e\u0440\u0445\u0443\u0456\u0458\u0455\u043a\u03b1\u03bf\u03b5\u03c1\u03c7\u03ba\u03bd\u03b9\u03c5\u03c4",
                                           "aceopxyijskaoepxkviut")}                       # Cyrillic and Greek letters that look like Latin ones
_MARKUP = re.compile(r"[*_~]+")
_SPACES = re.compile(r"\s+")
_MONTH = r"(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
_DAY = r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
_SEASON = r"(?:spring|summer|autumn|fall|winter)"
_UNIT = r"(?:days?|weeks?|months?|years?|issues?|editions?|posts?|quarters?|sessions?|episodes?)"
_NUM = r"(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|twelve|several|many|few|a few|a couple of|couple of|some|\d+)"
_EXTERNAL = (r"(?:last (?:week|month|year|time|quarter|season|night|weekend|" + _DAY + "|" + _MONTH + "|" + _SEASON + r"|issue|edition)"
             r"|" + _NUM + " " + _UNIT + r" (?:ago|back|earlier)|(?:days|weeks|months|years) ago"
             r"|(?:a|some) (?:while|time) (?:ago|back)|a long time ago|long ago|ages ago|the other day|yesterday|at the time|back then"
             r"|(?:back )?in " + _MONTH + r"\b|in the " + _SEASON + r"\b|in (?:19|20)\d\d\b"
             r"|earlier this (?:week|month|year|quarter|season|" + _SEASON + r")|earlier in the (?:year|week|month)"
             r"|on " + _DAY + r"|this past " + _DAY + r"|on the weekend)")
_EARLIER = (r"(?:earlier|previously|already|formerly|originally|recently|lately|many times|several times|a few times|a hundred times|more than once|time and again|again and again"
            r"|over and over|repeatedly|for (?:months|weeks|years)|in the past|beforehand|before(?= (?:that|but|so|though|too|now|again|here)\b|[.,;:!?)]|$))")
_STRONG = r"(?:previously|formerly|originally|many times|several times|a few times|more than once|time and again|again and again|over and over|repeatedly|for (?:months|weeks|years)|in the past)"
_SELF = r"(?:i|we)(?:'ve|'d| have| had)?"
_ADV = (r"(?: (?:already|also|once|previously|first|even|just|briefly|only|really|actually|often|always|repeatedly|then|again|too|long|originally|later|recently|never|ever|still"
        r"|have|had|been|did|do|kept|keep|keeps|constantly|consistently|forever|so))*")
_OUT_CORE = r"(?:posts?|newsletters?|columns?|threads?|essays?|articles?|tweets?|blog ?posts?|blogs?|write-?ups?|coverage)"
_OUT = (r"(?:posts?|notes?|pieces?|articles?|newsletters?|issues?|columns?|threads?|essays?|entries|tweets?|blogs?|blog ?posts?|write-?ups?|coverage|series|episodes?|editions?|digests?"
        r"|roundups?|stories|story|explainers?|reports?|deep dives?|dives?)")                                                          # needs a qualifier: my last note, my note from May
_OUT_WEAK = r"(?:thoughts|views|musings|position|stance|predictions?|arguments?|points?|claims?|takes?|forecasts?|analys[ie]s|updates?|reviews?|comments?|repl(?:y|ies)|rundowns?|breakdowns?|writings?|coverage|reporting|commentary)"
_ADJ = r"(?:earlier|previous|prior|last|older|first|recent|latest|original|other|old|past)"
_END = r"(?![\w-])"
_NOT_OUT = (r"(?! (?:of the (?:day|week|month|year|night)|to (?:self|myself)|pools?|safety|count|dump|id|local|trackers?|numbers?|queues?|boards?|templates?|labels?|types?|lists?"
            r"|tickets?|office|box|code|card|mortem)\b)")                                                              # an issue tracker, the thread pool, a note to self: other things of the same name
_OEND = _END + _NOT_OUT
_IN_PUB = r"in (?:(?:my|our|an?) (?:" + _ADJ + " )?|the " + _ADJ + " )" + _OUT + r"\b"       # in my last post, in a note: an earlier piece of the author's own
_SAYS = (r"(?:said|argued|mentioned|covered(?! for\b)|flagged|explained|described|discussed|noted|predicted|claimed|warned|stressed|stated|reported(?! (?:the |a |an |this |that |our |my )?(?:bugs?|issues?|problems?|incidents?|outages?|vulnerabilit(?:y|ies)|crimes?|thefts?|errors?|defects?|faults?|failures?)\b)|suggested|insisted|promised|admitted|conceded"
         r"|told (?:you|readers|everyone)|talked about|spoke about|touched on|pointed out|brought (?:this |it |that )?up|went through|walked through|broke down|laid out|set out|spelled out|outlined"
         r"|reviewed(?! (?:the |a |an |my |this |that |your |their )?(?:pull requests?|prs?|code|diffs?|patch(?:es)?|merge requests?|commits?|contracts?|applications?|resumes?|cvs?"
         r"|budgets?|files?|logs?|invoices?|drafts?|proposals?|tickets?|changes?)\b)"
         r"|returned to|revisited|wrote (?:it |this |that |them )?up|reported on|been over|gone over|gone through|been through|maintained"
         r"|raised (?:the same|a similar|a|this|that|the)(?: [a-z-]+)? (?:question|concern|point|worry|issue|objection|problem|possibility|doubt)"
         r"|shared (?:an?|the|my|our|this|that|some)(?: [a-z-]+){0,2} (?:chart|graph|thread|post|link|piece|note|story|table|numbers|results|take|thoughts|screenshot|diagram|figure|plot|summary|update|list)"
         r"|made (?:the|this|that|a|an|my)(?: [a-z-]+){0,2} (?:point|case|argument|prediction|claim|observation|remark|comparison)"
         r"|did (?:a|an|the)(?: [a-z-]+)? (?:deep dive|piece|thread|post|write-?up|series|breakdown|explainer|rundown|review|analysis|story|segment|dive))")
_WRITES = r"(?:wrote|written|write|blogged|tweeted|posted|published)"
_NUMBER = r"(?:\d[\d.,]*|one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|half|a dozen)"
_ABOUT = r"about(?! " + _NUMBER + r"\b(?!\s+(?:years?|months?|weeks?|days?|hours?|times?)\b))"        # wrote about 40 lines: not a subject; wrote about two years ago: one
_ON = r"on(?= (?:this|that|these|those|exactly|precisely|the (?:topic|subject|question|issue|problem|matter|theme))\b)"                   # wrote on this; not wrote on Monday, on the whiteboard
_WRITES_ABOUT = (_WRITES + r"(?: (?:extensively|at length|a lot|more|often|repeatedly|briefly|elsewhere|previously|before|earlier|already))? "
                 r"(?:" + _ABOUT + r"|" + _ON + r"|that|how|why|whether|regarding)\b")
_WTOPIC = _WRITES + r" (?:" + _ABOUT + r"|" + _ON + r"|that|how|why|whether|regarding|this|these|those|something|more|much|the same|as much|so|at length)\b"     # writing with a subject
_WRITES_NOUN = _WRITES + r" (?:an?|the|my|our|some|several|many|one|two|\d+)(?: [a-z-]+){0,2} " + _OUT + _END
_PRIVATE = (r"\b(?:mentioned|explained|described|said|shared|raised|told|talked|spoke|argued|reported|discussed|covered|noted)\b(?: [a-z']+){0,5} (?:to|with) "
            r"(?:the|a|an|my|our|his|her|their|him|them|me|us|one|two|three|four|five|several|some|many|few|both|each|every|all|colleagues?|friends?|maintainers?|team|customers?|vendors?|"
            r"finance|legal|management|hr|sales|marketing|engineering|operations|procurement|accounting|security|support|someone|somebody|anyone|people|folks|[a-z]+ (?:colleagues|friends|users|customers|clients|vendors|researchers|engineers|students|universities|teams))\b")
_LOCAL = re.compile(
    r"(?<![\w-])(?:above|below|(?:earlier|later|elsewhere|further|more) (?:in|on) (?:this|the|that) [a-z]+"
    r"|(?:in|of|at|from|throughout|within|to) (?:this|that) (?:note|post|piece|article|thread|reply|essay|text|draft|document|write-?up|message|answer|response|conversation|discussion|exchange|chat|section|paragraph)"
    r"|(?:in|of|at|from|throughout|within|to) the (?:section|paragraph|introduction|intro|preface|beginning|start|opening|top|end|conclusion|summary|abstract|chapter|page|table|figure|chart|appendix|thread|conversation|discussion)"
    r"|(?:previous|preceding|prior|last|first|second|third|next|following|opening|closing|final) (?:paragraph|section|sentence|chapter|bullet|part|passage|line|step|stage|slide)"
    r"|so far|at the (?:start|beginning|top|outset|end))" + _END)
_OUTSIDE = re.compile(_EXTERNAL)
_CLAUSE = re.compile(r"[,;:()\u2014\u2013]| - |\b(?:and|but|while|which|whereas|because|since|though|although|yet)\b")
_RULES: List[Tuple["re.Pattern[str]", bool]] = []


def _rule(pattern: str, private: bool = False) -> None:
    _RULES.append((re.compile(pattern, re.IGNORECASE), private))


_STANCE = (r"(?:said|wrote|written|noted|mentioned|argued|described|discussed|covered|explained|stated|stressed|pointed out|put it|reported|promised|predicted|warned|flagged|told you)")
_ANCHOR = "(?:" + _EXTERNAL + "|" + _EARLIER + "|" + _IN_PUB + ")"
_LEAD = r"(?:previously|already|once|earlier|before|originally|recently|repeatedly|often|always|long ago|many times)"
_KNOW = (r"(?:(?:will|may|might|would|already|surely|probably|no doubt|can|should|certainly)(?: (?:also|well|surely|certainly))? )?"
         r"(?:remember|recall|know|notice|recognise|recognize|have (?:seen|noticed|read|heard|guessed|followed)|be familiar|are (?:familiar|aware))\b")
_READERS = r"(?:readers|followers|subscribers|viewers)"
_rule(r"\b(?:as|like) " + _SELF + r"(?: [a-z']+){0,2}? " + _LEAD + " " + _STANCE + r"\b")
_rule(r"\b(?:as|like) " + _SELF + _ADV + " (?:" + _STANCE + r"|was saying)\b(?: (?:again|here|too|myself))?,? " + _ANCHOR)
_rule(r"\bas (?:previously|already|once) (?:mentioned|noted|discussed|covered|reported|stated|explained|argued|said|promised)\b")
_rule(r"\bas (?:mentioned|noted|discussed|covered|reported|stated|explained|argued|said|promised|shown) (?:previously|before|last (?:time|week|month|year|issue)|" + _NUM + " " + _UNIT
      + r" (?:ago|back)|in (?:my|our|an?|the) " + _ADJ + r" [a-z-]+)")
_rule(r"\b" + _SELF + r" (?:long|always|often|repeatedly|consistently|constantly|forever|keep|kept|keeps|continue to|never tire of|have been|'ve been|been)(?: (?:long|always|often|repeatedly"
      r"|consistently|constantly|forever|keep|kept|keeps|been))*(?: on)? (?:saying|arguing|repeating|reminding|insisting|stressing|maintaining|pointing out|mentioning|noting|claiming|warning"
      r"|predicting|writing (?:about|on|that|how|why)|telling (?:you|readers|everyone|people|folks))\b")
_rule(r"\b" + _SELF + r"(?: (?:have|had))?(?: (?:long|always|often|repeatedly|consistently|constantly|forever))+ (?:say|argue|tell you|write|maintain) (?:that|this|it|so|the same)\b")
_rule(r"\b" + _SELF + r"(?: (?:have|had))?(?: (?:long|always|often|repeatedly|consistently|constantly|forever))+ (?:" + _SAYS + "|" + _WRITES + r")\b")
_rule(r"\b" + _SELF + _ADV + " " + _WRITES_ABOUT)
_rule(r"\b" + _SELF + _ADV + " " + _WRITES_NOUN)
_rule(r"\b" + _SELF + _ADV + " " + _SAYS + r"\b[^.!?;]{0,80}?\b" + _ANCHOR, private=True)
_rule(r"\b" + _SELF + _ADV + " " + _WRITES + r" (?:this|that|these|those|something|more|much|the same|as much|so)\b[^.!?;]{0,60}?\b" + _EXTERNAL)
_rule(r"\b" + _SELF + r"(?: (?:have|had))?(?: (?:already|previously|originally|recently|earlier|first))+ (?:" + _SAYS + "|" + _WTOPIC + r")", private=True)
_rule(r"\b" + _SELF + _ADV + " " + _WRITES + r",? " + _EXTERNAL + r",?(?: (?:that|about|on|how|why|whether|this|these|those|more|the same|as much)\b|[.!?\"]*$)")
_rule(r"\b(?:" + _EXTERNAL + "|" + _STRONG + r")\b[^.!?;]{0,60}?\b" + _SELF + _ADV + " (?:" + _SAYS + "|" + _WTOPIC + r")", private=True)
_rule(r"\b" + _SELF + _ADV + " " + _SAYS + r" (?:this|that|it|so|as much|the same|similar)(?: [a-z]+)? ?(?:before|many times)", private=True)
_rule(r"\b(?:my|our) " + _OUT_CORE + r"(?: [a-z'-]+){0,5}? (?:argued|covered|said|explained|noted|mentioned|described|discussed|predicted|claimed|warned|stated|reported|suggested|showed|promised"
      r"|asked|pointed out|compared|flagged|raised|outlined|detailed|examined|looked at|walked through|went through|broke down|laid out|made the case|made the point|was wrong|got it wrong"
      r"|aged|held up|turned out)\b")
_rule(r"\bin (?:my|our) " + _OUT_CORE + r",? " + _SELF + _ADV + " (?:" + _SAYS + "|" + _WTOPIC + r")")
_rule(r"\b(?:my|our) (?:" + _ADJ + "|" + _MONTH + "|" + _DAY + "|" + _SEASON + ")(?: " + _NUM + r")? " + _OUT + _OEND)
_rule(r"\b(?:my|our) " + _OUT + r" (?:(?:from|of|in|on|dated|written|published|posted|sent|back in) )?(?:" + _EXTERNAL + "|the " + _SEASON + "|" + _MONTH + r")\b")
_rule(r"\b(?:my|our) " + _ADJ + " " + _OUT_WEAK + _END)
_rule(r"\b(?:(?:an?|the|in) (?:earlier|previous|prior|older|last|past) (?:posts?|notes?|pieces?|issues?|editions?|newsletters?|threads?|essays?|tweets?|articles?|stories|episodes?)" + _OEND
      + r"|(?:in|from|of) the (?:" + _MONTH + "|" + _DAY + "|" + _SEASON + r") (?:issue|edition|newsletter|post|column|thread|essay|episode|piece)" + _OEND
      + r"|(?:past|earlier|previous|prior|older) (?:issues|editions|posts|columns|episodes|instalments|installments) of (?:this|my|our) [a-z]+)")
_rule(r"\b(?:last (?:week|month|year)|" + _DAY + "|" + _MONTH + r")'s (?:issue|post|newsletter|thread|note|column|piece|edition|episode|essay)" + _OEND)
_rule(r"\b(?:the|an?|this|that|my|our) (?:[a-z-]+ )?(?:post|thread|piece|note|newsletter|column|article|essay|issue|tweet|story|write-?up|explainer|series) (?:that |which )?(?:i|we) "
      r"(?:wrote|posted|did|shared|published|sent|ran|put out|made|started|opened|began|drafted|compiled|released|launched|mentioned|linked)\b")
_rule(r"\bwhat " + _SELF + r" (?:wrote|written|said|argued|noted|mentioned|covered|posted|described|predicted|explained|promised)\b[^.!?;]{0,40}?\b" + _ANCHOR, private=True)
_rule(r"\b(?:the|this|that|same|similar|an?|my) (?:[a-z-]+ )?(?:argument|point|case|prediction|claim|observation|remark|comparison|chart|take|forecast) (?:that |which )?(?:i|we) "
      r"(?:made|raised|noted|offered|posted|shared|gave)\b[^.!?;]{0,60}?\b" + _EXTERNAL)
_rule(r"\b(?:regular|long-?time|long time|loyal|returning|faithful|frequent|veteran) " + _READERS + r"(?: of (?:this|my|our|the) [a-z]+)? " + _KNOW)
_rule(r"\b" + _READERS + r" of this (?:account|newsletter|feed|blog|column) " + _KNOW)
_rule(r"\b(?:" + _READERS + r"|those) who (?:follow|read|subscribe to) (?:this|my|our) [a-z]+ " + _KNOW)
_rule(r"\b(?:you(?:'ll| will| may| might)?|(?:some|many|most|a few|those|several) of you(?: will| may| might)?) (?:remember|recall)\b[^.!?;]{0,60}?\b(?:i|we|my|our)\b")
_rule(r"\b(?:remember|recall) (?:when|how|that|what) " + _SELF + _ADV + " (?:" + _SAYS + "|" + _WRITES + r")\b")
_rule(r"\b(?:as you (?:may|might|will|'ll|can) (?:well )?(?:remember|recall)\b|you (?:may|might|will|'ll) (?:well )?(?:remember|recall) (?:the|those|these|our|my) )")
_rule(r"\b(?:(?:(?:follow-?ups?|sequel|response|reply|continuation|update|addendum|companion piece|part (?:two|2)) (?:to|of|on|for)|in (?:response|reply) to|building on|picking up (?:from|on)|"
      r"(?:more|details?|background|context|see|read)(?: (?:in|on|at))?|(?:after|following|since)(?= (?:my|our) " + _OUT_CORE + r" (?:on|about|from|of|last|earlier|yesterday)\b)) (?:my|our) " + _OUT_CORE + _OEND
      + r"|previously on (?:this|my|our) (?:newsletter|blog|column|feed|show|podcast)\b)")
CALLBACKS = tuple(pattern for pattern, _ in _RULES)           # the patterns of references (case-insensitive; the guard applies them to normalised sentences)
_PRIVATE_RE = re.compile(_PRIVATE)


def _normal(raw: str) -> str:
    """A sentence made comparable: compatibility forms (non-breaking space, full-width letters), zero-width characters and markup removed, apostrophes straight, lower case,
    Cyrillic and Greek look-alikes of Latin letters written as the Latin letter."""
    raw = raw.replace("&nbsp;", " ").replace("&#160;", " ").replace("&#xa0;", " ")                 # the entity of a non-breaking space, as it stands in markup that was copied as text
    text = unicodedata.normalize("NFKC", raw).translate(_ZERO_WIDTH).translate(APOSTROPHE_TABLE)
    return _SPACES.sub(" ", _MARKUP.sub("", text)).strip().lower().translate(_CONFUSABLES)


def _cancelled(sentence: str, start: int) -> bool:
    """Whether the clause in which a match starts refers to the text being written (above, earlier in this note) and has no anchor outside it."""
    low = max(0, start - 200)
    left = low
    for found in _CLAUSE.finditer(sentence, low, start):
        left = found.end()
    end = min(len(sentence), start + 300)
    right = _CLAUSE.search(sentence, start + 1, end)
    clause = sentence[left: right.start() if right else end]
    return bool(_LOCAL.search(clause)) and not _OUTSIDE.search(clause)


def _is_reference(sentence: str) -> bool:
    """Whether a normalised sentence explicitly refers back to something the author said, wrote, posted or covered earlier, outside the text being written."""
    if not sentence:
        return False
    private = bool(_PRIVATE_RE.search(sentence))
    for pattern, soft in _RULES:
        if soft and private:
            continue
        for match in pattern.finditer(sentence):
            if not _cancelled(sentence, match.start()):
                return True
    return False


REFERENCE_STEMS = frozenset(tokens(
    "wrote written write said say argued argue mentioned mention covered cover flagged flag explained explain described describe discussed discuss noted note raised raise shared share "
    "predicted predict claimed warned stressed stated reported suggested insisted promised admitted conceded told talked spoke touched pointed brought went walked broke laid outlined "
    "reviewed returned revisited posted post published blogged tweeted earlier previous previously prior older last week weeks month months year years day days ago back time times issue "
    "issues edition newsletter column thread piece article essay tweet story entry readers follower subscriber regular remember recall already before again once many several few couple "
    "yesterday recently lately spring summer autumn fall winter january february march april may june july august september october november december monday tuesday wednesday thursday friday "
    "saturday sunday weekend account feed blog"))


def _support(sentence: str, pool: Set[str], dfs: Dict[str, int], n_docs: int) -> Optional[bool]:
    """Whether the injected items back a reference sentence: it shares a distinctive term (idf at least DISTINCT of the idf of a word seen once) or three content words with
    them, not counting the words of the reference phrase itself. None: the sentence has no content word to check."""
    content = set(tokens(sentence)) - REFERENCE_STEMS
    if not content:
        return None
    shared = content & pool
    if len(shared) >= 3:
        return True
    hapax = _idf(n_docs, 1)
    return any(t in dfs and _idf(n_docs, dfs[t]) >= DISTINCT * hapax for t in shared)


def guard(result: Dict, output_text: str) -> Dict:
    """Deterministic check of the writer's output against what was injected: {"ok", "flags", "callbacks"}. A FLOOR signal: log it, do not reject text on it.

    callbacks              the number of sentences that explicitly refer back to something the author said, wrote, posted or covered earlier (English only; at most
                           MAX_GUARD_CHARS characters are read)
    spurious_reference     an explicit reference to an earlier piece although nothing of the account's own was injected (world knowledge does not count as the account's own)
    unsupported_reference  an explicit reference whose sentence shares with the injected items no distinctive term and fewer than three content words (the words of the
                           reference phrase itself, as wrote, last week, earlier, post, do not count); the document frequencies come from the private key _df of the result of
                           retrieve, and a result without it is judged by the count of shared words alone
    future_item            an injected item dated at or after the task (impossible unless the result was altered)
    fiction_out_of_scope   an invented-autobiography item injected for a task type that the profile does not allow
    ok means that no flag was raised, not that the text has no unsupported reference: the grammar recognises explicit references only, and no figure of its precision or
    recall is a figure for your account (see the banks in the tests). Items are the ones render() shows.
    """
    try:
        items, positions = _shown(result)
        text = output_text or ""
        if isinstance(text, str):
            text = text[:MAX_GUARD_CHARS]
        refs = [s for s in (_normal(raw) for raw in SENTENCES.split(text)) if _is_reference(s)]
        flags: List[str] = []
        own = [i for i in items if getattr(i, "origin", None) != "world_knowledge"]
        if refs and not own:
            flags.append("spurious_reference")
        elif refs:
            pool: Set[str] = set()
            for it in own:
                trace = it.trace if isinstance(getattr(it, "trace", None), dict) else {}
                pool |= set(tokens(it.text)) | set(tokens(" ".join(v for v in trace.values() if isinstance(v, str))))
            dfs = result.get("_df") or {}
            n_docs = max(1, int(result.get("n_index") or 1))
            if any(_support(s, pool, dfs, n_docs) is False for s in refs):
                flags.append("unsupported_reference")
        keys = result.get("keys", [])
        if result.get("now_key") and any(isinstance(keys[p], str) and keys[p] >= result["now_key"] for p in positions if p < len(keys)):
            flags.append("future_item")
        if any(i.origin == "fiction_autobio" for i in items) and result.get("task_type") not in result.get("persona_task_types", ()):
            flags.append("fiction_out_of_scope")
        return {"ok": not flags, "flags": flags, "callbacks": len(refs)}
    except Exception as exc:
        return {"ok": False, "flags": ["guard_error:%s" % type(exc).__name__], "callbacks": 0}


def calibrate(index: Index, queries: Sequence[Tuple[str, str]], share: float = 0.2, channel: str = "lexical", profile: Union[str, Dict, None] = "kernel",
              task_type: Optional[str] = None) -> Optional[float]:
    """The threshold above which `share` (0 to 1) of the (query, date) pairs have an item dated before them, on one channel: "lexical" (the score s of retrieve, with the
    evidence floor min_evidence of the profile) or "embedding" (cosine).

    The lexical score uses the BM25 settings of `profile` (k1, b, len_cap, top_terms, max_terms) and, like retrieve, the statistics of the items that the pair may see;
    task_type (None: all origins) says whether invented autobiography counts. None when there is nothing to calibrate (no queries, no candidate for any query, a channel
    that needs an embedder the index lacks, a channel that does not exist, a share outside 0 to 1, a malformed query or date); never raises."""
    try:
        share = float(share)
        if not 0.0 <= share <= 1.0 or channel not in ("lexical", "embedding") or not isinstance(index, Index):
            return None
        prof = _profile(profile)
        if channel == "embedding" and (index.embedder is None or not index.vectors):
            return None
        persona_ok = task_type is None or task_type in prof["persona_task_types"]
        best_scores: List[float] = []
        for query, date in queries:
            key = when(date)
            if not isinstance(query, str):
                raise TypeError("query is not text")
            query = query[:MAX_QUERY_CHARS]
            stems = tokens(query)
            qv = None
            if channel == "embedding":
                qv = _unit(index.embedder([query])[0])
                if len(qv) != index.dim:
                    raise ValueError("query vector of another size")
            seen, df, cosines, n_docs, avgdl = _survey(index, set(stems), key, persona_ok, qv)
            best = 0.0
            if channel == "embedding":
                best = max(list(cosines.values()) + [0.0])
            else:
                terms, weights, reference, floor, scores, gained = _lexical(index, seen, df, n_docs, avgdl, stems, prof)
                if reference > 0:
                    for ident, score in scores.items():
                        if gained[ident] >= floor:
                            best = max(best, score / reference)
            best_scores.append(best)
        if not best_scores:
            return None
        ordered = sorted(best_scores)
        threshold = math.floor(ordered[min(len(ordered) - 1, max(0, int(math.floor((1 - share) * len(ordered)))))] * 1e4) / 1e4
        return threshold if threshold > 0.0 else None
    except Exception:
        return None
