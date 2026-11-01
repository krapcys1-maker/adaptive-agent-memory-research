# SPDX-License-Identifier: Apache-2.0
"""memory_kernel: a small, deterministic memory for a writing agent. Standard library only; no network, no files, no effects on import.

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
  reference guard        a deterministic check of the writer's output; a floor, not a proof: the regular expressions find about half of the references a person marks (AAM-E6E)
Embeddings are optional. Without an embedder the kernel is lexical (idf-weighted coverage of the query, with a floor of evidence) plus names; with one it is hybrid.

Dates: created_at, as_of and now are ISO 8601 strings (or date/datetime objects); a year, a month, a day or a time may be missing from the right, a zone is converted to UTC.
Mixed precisions compare correctly (2026-09-10 is before 2026-09-10T08:00); an item is shown only if it is strictly before `now`.

API: build_index(items, as_of, embedder=None, vectors=None) -> Index; retrieve(index, query, task_type, now, profile) -> dict; render(result) -> str;
     log_record(result, hmac_fn, key=None, raw_ids=False) -> dict; guard(result, output_text) -> dict; calibrate(index, queries, share, channel) -> float.
retrieve returns {status, items, n_candidates, n_considered, scores, channel_scores, reasons, dates, latency_ms, tokens_est, ...} and never raises: problems are reported in
status (ok, degraded: lexical only because the embedder failed or is missing where the profile wants it, timeout, error). build_index raises ValueError only for an invalid as_of
(fail closed: without it the no-future gate cannot be enforced); it counts and drops invalid, future and duplicate items.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from array import array
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from operator import mul
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

__version__ = VERSION = "0.1.0"
KINDS = ("note", "reply", "comment", "event")
ORIGINS = ("account_history", "fiction_autobio", "world_knowledge")
MAX_QUERY_CHARS = 20000
WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
SENTENCE_END = re.compile(r"[.!?\n]")
SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")
WHEN = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?\s*(Z|[+-]\d{2}(?::?\d{2})?)?)?)?)?$")
STOP = frozenset(
    "the a an and or of to in on at is are was were be been it its this that these those for with as by from but not no yes i you he she we they my your our their me him her "
    "them what who when where which how why do did does done have has had so if than then there here about into over also just very can could would should will "
    "w z na to nie jest się że do po od za o i a ale lub oraz".split())
CALLBACKS = tuple(re.compile(p, re.I) for p in (
    r"\bas (?:i|we) (?:wrote|said|noted|mentioned|argued|described|discussed|covered|explained|told you)\b",
    r"\b(?:i|we) (?:wrote|noted|mentioned|argued|described|admitted|said|posted|shared|told you)\b[^.!?]{0,60}\b(?:earlier|before|previously|recently|last (?:week|month|time|year)|(?:days?|weeks?|months?) ago)\b",
    r"\b(?:my|our) (?:earlier|previous|last|recent|first) (?:entry|entries|column|columns|post|posts|note|notes|piece|pieces|article|articles|newsletter|reply|comment)\b",
    r"\b(?:earlier|previous|last) (?:entry|column|post|newsletter)\b",
    r"\bwhen i (?:first |last )?wrote\b",
    r"\bi(?:'ve| have) (?:written|mentioned|noted|argued|said) (?:about |on )?(?:this|that|it)\b",
    r"\b(?:regular readers|longtime readers|you may remember|you might remember|you will remember|as you may recall)\b",
    r"\b(?:remember|recall) (?:when|how) i\b",
))
PROFILES: Dict[str, Dict] = {
    # lex_tau: share of the query's idf mass an item must cover; min_evidence: the idf mass it must cover at least, as a share of the idf of a word seen once in the index;
    # tau: cosine of the embedder; embed: auto (when the index has an embedder), off, required (degraded without one); names: the channel for rare capitalised words,
    # only for the task types in name_task_types; persona_task_types: the task types for which invented autobiography is considered
    "kernel": {"k": 3, "lex_tau": 0.30, "min_evidence": 0.8, "tau": 0.57, "embed": "auto", "names": True, "name_task_types": ("personal",), "rare_df": 2,
               "persona_task_types": ("personal",), "timeout_ms": 300},
    "lexical": {"k": 3, "lex_tau": 0.30, "min_evidence": 0.8, "tau": 0.57, "embed": "off", "names": True, "name_task_types": ("personal",), "rare_df": 2,
                "persona_task_types": ("personal",), "timeout_ms": 300},
    "hybrid": {"k": 3, "lex_tau": 0.30, "min_evidence": 0.8, "tau": 0.57, "embed": "required", "names": True, "name_task_types": ("personal",), "rare_df": 2,
               "persona_task_types": ("personal",), "timeout_ms": 300},
}
Embedder = Callable[[List[str]], List[List[float]]]


@dataclass(frozen=True)
class Item:
    id: str
    kind: str                                  # note | reply | comment | event
    origin: str                                # account_history | fiction_autobio | world_knowledge
    created_at: str                            # ISO 8601; see the module docstring
    text: str                                  # the account's own text only
    trace: Optional[Dict[str, str]] = None     # {"gist", "angle", "open"}
    meta: Dict = field(default_factory=dict)   # meta["supersedes"] = the id of an item this one replaces


@dataclass
class Index:
    as_of: str
    as_of_key: str
    items: Dict[str, Item]
    keys: Dict[str, str]                       # id -> created_at as a canonical UTC key
    toks: Dict[str, frozenset]                 # id -> content stems
    names: Dict[str, frozenset]                # id -> stems written with a capital
    lower: Set[str]                            # stems written in lower case somewhere in the index
    df: Dict[str, int]
    vectors: Dict[str, array]                  # id -> unit vector
    dim: int
    embedder: Optional[Embedder]
    superseded_by: Dict[str, str]              # id -> the earliest key of an item that replaces it
    rejected: Dict[str, int]
    degraded: str = ""
    built_ms: float = 0.0


def when(value) -> str:
    """The canonical key 'YYYY-MM-DDTHH:MM:SS' (UTC) of an ISO 8601 date or datetime, a year, month, day or time missing from the right allowed; ValueError otherwise."""
    if hasattr(value, "isoformat"):
        value = value.isoformat()
    match = WHEN.match(str(value).strip())
    if not match:
        raise ValueError("not an ISO 8601 date: %r" % (value,))
    year, month, day, hour, minute, second, zone = match.groups()
    moment = datetime(int(year), int(month or 1), int(day or 1), int(hour or 0), int(minute or 0), int(second or 0))
    if zone and zone != "Z":
        digits = zone[1:].replace(":", "")
        moment -= (-1 if zone[0] == "-" else 1) * timedelta(hours=int(digits[:2]), minutes=int(digits[2:4] or 0))
    return moment.isoformat()


def stem(word: str) -> str:
    word = word.lower().replace("’", "'")
    if word.endswith("'s"):
        word = word[:-2]
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    return word[:-1] if len(word) > 4 and word.endswith("s") and not word.endswith("ss") else word


def analyse(text: str) -> Tuple[List[str], Set[str], Set[str], Set[str]]:
    """(content stems in order, stems written with a capital, stems capitalised inside a sentence or in capitals, stems written in lower case)."""
    stems: List[str] = []
    capital: Set[str] = set()
    inside: Set[str] = set()
    lower: Set[str] = set()
    previous_end: Optional[int] = None
    for match in WORD.finditer(text):
        surface, root = match.group(), stem(match.group())
        initial = previous_end is None or SENTENCE_END.search(text, previous_end, match.start()) is not None
        previous_end = match.end()
        if root in STOP or len(root) < 2:
            continue
        stems.append(root)
        if surface[0].isupper():
            capital.add(root)
            if not initial or (surface.isupper() and len(surface) >= 3):
                inside.add(root)
        else:
            lower.add(root)
    return stems, capital, inside, lower


def tokens(text: str) -> List[str]:
    return analyse(text)[0]


def item_id(kind: str, created_at: str, text: str) -> str:
    return "%s-%s-%s" % (kind, str(created_at)[:10], hashlib.sha256(text.encode("utf-8")).hexdigest()[:8])


def write_back_item(text: str, created_at: str, about: str = "") -> Item:
    """A personal detail that the persona improvised, as an invented-autobiography event with a deterministic id, to be added to the next index."""
    body = ("%s %s" % (about, text)).strip()
    return Item(item_id("event", created_at, body), "event", "fiction_autobio", created_at, body)


def _unit(vector: Sequence[float]) -> array:
    out = array("d", (float(x) for x in vector))
    norm = math.sqrt(sum(map(mul, out, out)))
    if not math.isfinite(norm):
        raise ValueError("a vector is not finite")
    if norm > 0:
        for i in range(len(out)):
            out[i] /= norm
    return out


def build_index(items: Sequence[Item], as_of: str, embedder: Optional[Embedder] = None, vectors: Optional[Dict[str, Sequence[float]]] = None) -> Index:
    """Index the items dated up to as_of; later, invalid and duplicate items are dropped and counted in index.rejected. vectors maps ids to ready embeddings (a cache)."""
    started = time.perf_counter()
    idx = Index(as_of=str(as_of), as_of_key=when(as_of), items={}, keys={}, toks={}, names={}, lower=set(), df={}, vectors={}, dim=0, embedder=None, superseded_by={},
                rejected={"future": 0, "invalid": 0, "duplicate": 0})
    kept: List[Item] = []
    for it in items:
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
                idx.items[it.id], idx.keys[it.id] = it, key
                kept.append(it)
        except Exception:
            idx.rejected["invalid"] += 1
    for it in kept:
        stems, capital, _, lower = analyse(it.text)
        idx.toks[it.id], idx.names[it.id] = frozenset(stems), frozenset(capital)
        idx.lower |= lower
        for root in idx.toks[it.id]:
            idx.df[root] = idx.df.get(root, 0) + 1
        old = it.meta.get("supersedes") if isinstance(it.meta, dict) else None
        if old and (str(old) not in idx.superseded_by or idx.keys[it.id] < idx.superseded_by[str(old)]):
            idx.superseded_by[str(old)] = idx.keys[it.id]
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
    except Exception as exc:                                 # the index stays usable, lexically
        idx.vectors, idx.dim, idx.embedder, idx.degraded = {}, 0, None, "embedder failed at build: %s" % type(exc).__name__
    idx.built_ms = (time.perf_counter() - started) * 1000.0
    return idx


def _profile(profile: Union[str, Dict, None]) -> Dict:
    if isinstance(profile, dict):
        return dict(PROFILES["kernel"], name=str(profile.get("name", "custom")), **{k: v for k, v in profile.items() if k != "name"})
    name = "kernel" if profile is None else profile
    if name not in PROFILES:
        raise KeyError("unknown profile %r" % (profile,))
    return dict(PROFILES[name], name=name)


def _blank(status: str, query: str, prof: Dict, task_type: str, now: Optional[str], started: float, error: str = "", index: Optional[Index] = None) -> Dict:
    return {"status": status, "items": [], "n_candidates": 0, "n_considered": 0, "scores": [], "channel_scores": [], "reasons": [], "dates": [], "keys": [], "latency_ms":
            round((time.perf_counter() - started) * 1000.0, 3), "tokens_est": 0, "profile": prof.get("name", ""), "task_type": task_type, "now": now, "now_key": "",
            "as_of": index.as_of if index else None, "n_index": len(index.items) if index else 0, "k": prof.get("k"), "tau": prof.get("tau"), "lex_tau": prof.get("lex_tau"),
            "min_evidence": prof.get("min_evidence"), "persona_task_types": list(prof.get("persona_task_types", ())), "error": error, "_query": query}


def retrieve(index: Index, query: str, task_type: str = "note", now: Optional[str] = None, profile: Union[str, Dict, None] = "kernel") -> Dict:
    """The items (at most k) that pass a gate for this query, dated strictly before now, best first (names first). Nothing below the thresholds. Never raises.

    scores are in units of the gate (1.0 = exactly at the threshold of the channel that likes the item most); channel_scores keep the raw lexical coverage and cosine.
    """
    started = time.perf_counter()
    prof: Dict = {}
    try:
        prof = _profile(profile)
        query = query[:MAX_QUERY_CHARS]
        now = index.as_of if now is None else now
        now_key = when(now)
        deadline = started + prof["timeout_ms"] / 1000.0
        stems, capital, inside, lower = analyse(query)
        q = sorted(set(stems))
        n_docs = max(1, len(index.items))
        idf = {t: math.log(1.0 + (n_docs - index.df.get(t, 0) + 0.5) / (index.df.get(t, 0) + 0.5)) for t in q}
        mass = sum(idf.values()) or 1.0
        floor = prof["min_evidence"] * math.log(1.0 + (n_docs - 0.5) / 1.5)
        rare: List[str] = []
        if prof["names"] and task_type in prof["name_task_types"]:
            named = set(inside) | {t for t in capital if t not in index.lower and t not in lower}
            rare = sorted(t for t in named if 0 < index.df.get(t, 0) <= prof["rare_df"] and len(t) >= 3)
        status, error, qv = "ok", "", None
        if prof["embed"] != "off":
            if index.degraded:
                status, error = "degraded", index.degraded
            elif index.embedder is None:
                if prof["embed"] == "required":
                    status, error = "degraded", "no embedder"
            else:
                try:
                    qv = _unit(index.embedder([query])[0])
                    if len(qv) != index.dim:
                        raise ValueError("query vector of another size")
                except Exception as exc:
                    status, error, qv = "degraded", "embedder failed at query: %s" % type(exc).__name__, None
        lex_tau, tau = max(prof["lex_tau"], 1e-9), max(prof["tau"] or 0.0, 1e-9)
        persona_ok = task_type in prof["persona_task_types"]
        found: List[Tuple[int, float, str, Item, List[str], Dict]] = []
        considered = 0
        for n, (ident, it) in enumerate(index.items.items()):
            if n % 200 == 0 and time.perf_counter() > deadline:
                return _blank("timeout", query, prof, task_type, now, started, "deadline exceeded", index)
            if index.keys[ident] >= now_key or (ident in index.superseded_by and index.superseded_by[ident] < now_key) or (it.origin == "fiction_autobio" and not persona_ok):
                continue
            considered += 1
            have = index.toks[ident]
            gained = sum(idf[t] for t in q if t in have)
            cover = gained / mass
            cos = sum(map(mul, qv, index.vectors[ident])) if qv is not None and ident in index.vectors else None
            reasons = []
            if rare and any(t in index.names[ident] for t in rare):
                reasons.append("name")
            if gained >= floor and cover >= lex_tau:
                reasons.append("lexical")
            if cos is not None and cos >= tau:
                reasons.append("embedding")
            if reasons:
                strength = max(cover / lex_tau, (cos / tau) if cos is not None else 0.0)
                found.append((0 if "name" in reasons else 1, -strength, ident, it, reasons, {"lexical": round(cover, 4), "embedding": None if cos is None else round(cos, 4)}))
        found.sort(key=lambda row: (row[0], row[1], row[2]))
        top = found[: int(prof["k"])]
        result = _blank(status, query, prof, task_type, now, started, error, index)
        result.update({"items": [row[3] for row in top], "n_candidates": len(found), "n_considered": considered, "scores": [round(-row[1], 4) for row in top],
                       "channel_scores": [row[5] for row in top], "reasons": [row[4] for row in top], "keys": [index.keys[row[2]] for row in top],
                       "dates": [index.keys[row[2]][:10] for row in top], "now_key": now_key})
        result["tokens_est"] = (len(render(result)) + 3) // 4
        result["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        return result
    except Exception as exc:
        return _blank("error", query if isinstance(query, str) else "", prof, task_type, None if now is None else str(now), started, "%s: %s" % (type(exc).__name__, str(exc)[:80]), index)


def render(result, mode: str = "trace") -> str:
    """Text for the prompt: one line per item, oldest first, with its date and no label of origin; an empty result is the empty string.

    mode "trace" uses the item's trace (gist, angle, what was left open) when it has one, "raw" always the text.
    """
    try:
        items = result.get("items", []) if isinstance(result, dict) else list(result)
        keys = result.get("keys") if isinstance(result, dict) and len(result.get("keys", [])) == len(items) else [when(i.created_at) for i in items]
        lines = []
        for key, it in sorted(zip(keys, items), key=lambda pair: (pair[0], pair[1].id)):
            body = it.text
            if mode == "trace" and it.trace and it.trace.get("gist"):
                body = " ".join(x for x in (it.trace["gist"], ("Angle: " + it.trace["angle"]) if it.trace.get("angle") else "",
                                            ("Left open: " + it.trace["open"]) if it.trace.get("open") else "") if x)
            lines.append("[%s] %s" % (key[:10], body))
        return "\n".join(lines)
    except Exception:
        return ""


def log_record(result: Dict, hmac_fn: Callable[[str], str], key: Optional[str] = None, raw_ids: bool = False) -> Dict:
    """One record for the injection log: keyed hashes of the query (or of `key`) and of the item ids, kinds, origins, dates, scores, reasons, counts; never any text.

    The result carries the query privately (_query) only to be hashed here; do not log the result itself. raw_ids adds the ids as they are.
    """
    try:
        items = result.get("items", [])
        record = {"kernel_version": VERSION, "status": result.get("status"), "profile": result.get("profile"), "task_type": result.get("task_type"), "now": result.get("now"),
                  "as_of": result.get("as_of"), "query_hmac": hmac_fn(key if key is not None else result.get("_query", "")), "item_hmacs": [hmac_fn(i.id) for i in items],
                  "kinds": [i.kind for i in items], "origins": [i.origin for i in items], "dates": list(result.get("dates", [])), "scores": list(result.get("scores", [])),
                  "channel_scores": [dict(c) for c in result.get("channel_scores", [])], "reasons": [list(r) for r in result.get("reasons", [])],
                  "n_candidates": result.get("n_candidates"), "n_considered": result.get("n_considered"), "n_index": result.get("n_index"), "k": result.get("k"),
                  "tau": result.get("tau"), "lex_tau": result.get("lex_tau"), "min_evidence": result.get("min_evidence"), "latency_ms": result.get("latency_ms"),
                  "tokens_est": result.get("tokens_est"), "error": result.get("error", "")}
        if raw_ids:
            record["ids"] = [i.id for i in items]
        return record
    except Exception as exc:
        return {"kernel_version": VERSION, "status": "error", "error": "log_record: %s" % type(exc).__name__}


def guard(result: Dict, output_text: str) -> Dict:
    """Deterministic check of the writer's output against what was injected: {"ok", "flags", "callbacks"}.

    spurious_reference     an explicit reference to an earlier piece although nothing was injected
    unsupported_reference  an explicit reference whose sentence shares fewer than two content words with the injected items
    future_item            an injected item dated at or after the task (impossible unless the result was altered)
    fiction_out_of_scope   an invented-autobiography item injected for a task type that the profile does not allow
    A floor, not a proof: it recognises explicit phrases only.
    """
    try:
        items = result.get("items", [])
        refs = [s for s in SENTENCES.split(output_text or "") if any(p.search(s) for p in CALLBACKS)]
        flags: List[str] = []
        if refs and not items:
            flags.append("spurious_reference")
        elif refs:
            pool: Set[str] = set()
            for it in items:
                pool |= set(tokens(it.text)) | set(tokens(" ".join(str(v) for v in (it.trace or {}).values())))
            if any(len(set(tokens(s)) & pool) < 2 for s in refs):
                flags.append("unsupported_reference")
        if result.get("now_key") and any(k >= result["now_key"] for k in result.get("keys", [])):
            flags.append("future_item")
        if any(i.origin == "fiction_autobio" for i in items) and result.get("task_type") not in result.get("persona_task_types", ()):
            flags.append("fiction_out_of_scope")
        return {"ok": not flags, "flags": flags, "callbacks": len(refs)}
    except Exception as exc:
        return {"ok": False, "flags": ["guard_error:%s" % type(exc).__name__], "callbacks": 0}


def calibrate(index: Index, queries: Sequence[Tuple[str, str]], share: float = 0.2, channel: str = "lexical") -> Optional[float]:
    """The threshold above which `share` of the (query, date) pairs have an item dated before them, on one channel: "lexical" (coverage) or "embedding" (cosine)."""
    best_scores: List[float] = []
    for query, date in queries:
        key = when(date)
        stems = sorted(set(tokens(query[:MAX_QUERY_CHARS])))
        n_docs = max(1, len(index.items))
        idf = {t: math.log(1.0 + (n_docs - index.df.get(t, 0) + 0.5) / (index.df.get(t, 0) + 0.5)) for t in stems}
        mass = sum(idf.values()) or 1.0
        qv = _unit(index.embedder([query])[0]) if channel == "embedding" and index.embedder is not None else None
        best = 0.0
        for ident in index.items:
            if index.keys[ident] >= key:
                continue
            if qv is not None:
                best = max(best, sum(map(mul, qv, index.vectors[ident])) if ident in index.vectors else 0.0)
            elif channel == "lexical":
                best = max(best, sum(idf[t] for t in stems if t in index.toks[ident]) / mass)
        best_scores.append(best)
    if not best_scores:
        return None
    ordered = sorted(best_scores)
    return math.floor(ordered[min(len(ordered) - 1, max(0, int(math.floor((1 - share) * len(ordered)))))] * 1e4) / 1e4
