"""Lexical similarity of claims: TF-IDF cosine over words and over word pairs within a window of two (skip-bigrams).

Extracted from the AAMR coordinator (``aamr_coord/lab/textsim.py``, coordinator commit c429d82); the logic is unchanged
and the docstrings are translated into English. The approach follows the verdict-gate and similarity pattern of the MIT-licensed
scaleresearch/hypothesisloop project (``controlplane/storage/graphdb/similar.go``) and was rewritten from scratch.

Explicit blind spot: a paraphrase with synonyms and no shared words is not detected. In a hypothesis ledger that is the
job of the structural fingerprint (mechanism, variable, corpus, direction, metric), not of this module. The registration
threshold of 0.45 is a working value that has not been calibrated on a separate set (methodology document, section 7).

The stop-word list holds English and Polish words because both languages occur in the project's claims.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

_STOP = set("""
a an and are as at be by for from has have in into is it its of on or that the their this to was were will with
than then there these those which who whom whose not no do does did can could should would may might more most less
i w z na do od o że się jest są nie to ten ta te tym tej przez przy po dla jak oraz lub albo czy co który która
które których niż także też już tylko bez pod nad między gdy jeśli więc ale ich jego jej
""".split())


def tokens(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).replace("ł", "l")
    return [w for w in re.findall(r"[a-z0-9]+", t) if w not in _STOP and len(w) > 1]


def features(text: str, reach: int = 2) -> Counter:
    tk = tokens(text)
    f: Counter = Counter(tk)
    for i, a in enumerate(tk):
        for j in range(i + 1, min(len(tk), i + 1 + reach)):
            f[f"{a}|{tk[j]}"] += 1
    return f


def _idf(docs: list[Counter]) -> dict[str, float]:
    n = len(docs)
    df: Counter = Counter()
    for d in docs:
        df.update(d.keys())
    return {k: math.log((n + 1) / (v + 1)) + 1.0 for k, v in df.items()}


def _vec(f: Counter, idf: dict[str, float]) -> dict[str, float]:
    return {k: v * idf.get(k, 1.0) for k, v in f.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def most_similar(text: str, existing: dict[str, str]) -> list[tuple[str, float]]:
    """List of (id, similarity) in descending order. IDF is computed over the existing claims and the new one."""
    if not existing:
        return []
    feats = {k: features(v) for k, v in existing.items()}
    new = features(text)
    idf = _idf([*feats.values(), new])
    nv = _vec(new, idf)
    out = [(k, round(cosine(nv, _vec(f, idf)), 4)) for k, f in feats.items()]
    return sorted(out, key=lambda x: (-x[1], x[0]))
