#!/usr/bin/env python3
"""SAME_CATEGORY_ENTITY_ENUMERATION: read-side, deterministic render transform
for Mechanism E. Targets HARMFUL_SIBLING_DISTRACTION (Ledger Entry C) -- the
one confirmed AAMR case is E1's `gpt4_f420262c` ("Spirit Airlines" named
directly, close in rank to the relevant cluster, wrong answer; correct
answer "Delta" required a harder multi-hop link). External grounding:
arXiv:2606.10388 ("Right Family, Wrong Skill"), harmful-sibling rate ~1/3 of
"correct-looking" retrievals in its own benchmark.

Deterministic category-suffix entity extraction (narrow, template-based, same
discipline as Mechanism B's state-key templates) -- NOT a generic NER, which
is too noisy via bare capitalization heuristics. When >=2 DISTINCT entity
names sharing the same category suffix (Airlines, Museum, Hotel, ...) appear
across retrieved items, render an explicit enumeration note listing them.
Does not indicate which is correct -- purely surfaces the plurality that
already exists in the delivered context. Inert when 0 or 1 distinct entity
found per category (nothing to enumerate).
"""

from __future__ import annotations

import re

CATEGORY_SUFFIXES = [
    "Airlines", "Airways", "Museum", "Hotel", "Restaurant", "University",
    "College", "Hospital", "Church", "Bank", "Corp", "Inc", "Company",
    "Store", "Cafe", "Gym", "Club", "Park", "Theater", "Theatre", "Library",
    "School", "Academy",
]
#: Sentence-initial and common verb capitalization creates false entity-name
#: prefixes ("Flew Delta Airlines" -> "Flew" is not part of the entity).
#: Found live via this module's own tests: a bare capitalization heuristic
#: swept the leading verb into the captured name. A small, fixed stoplist,
#: stripped from the LEFT edge of a match only, is far more robust than
#: trying to build a real part-of-speech tagger for a narrow, deterministic
#: read-side transform.
_LEADING_NON_ENTITY_WORDS = {
    "Flew", "Visited", "Booked", "Attended", "Went", "Took", "Considering",
    "Interested", "Planning", "Adopted", "Curious", "Started", "Stopped",
    "Left", "Joined", "Signed", "Canceled", "Cancelled", "The", "A", "An",
    "Also", "Recently", "Just", "Is", "Was", "Has", "Had",
}
_SUFFIX_PATTERN = re.compile(
    r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+){0,3})\s(" +
    "|".join(CATEGORY_SUFFIXES) + r")\b"
)


def extract_category_entities(text: str) -> list[tuple[str, str]]:
    """[(full_entity_name, category_suffix), ...] found in one item's text.

    The regex over-captures leading capitalized words (sentence-initial
    verbs); this strips any word from the LEFT edge of the match that is in
    the fixed non-entity stoplist, so "Flew Delta Airlines" yields the entity
    "Delta Airlines", not "Flew Delta Airlines".
    """
    found = []
    for m in _SUFFIX_PATTERN.finditer(text):
        words = m.group(1).split()
        while words and words[0] in _LEADING_NON_ENTITY_WORDS:
            words = words[1:]
        if not words:
            continue
        name = " ".join(words) + " " + m.group(2)
        found.append((name, m.group(2)))
    return found


def same_category_entity_enumeration(context_texts: list[str]) -> tuple[list[str], dict]:
    """Returns (rendered_context, trace). Inert unless >=2 distinct entity
    names share a category suffix somewhere in the retrieved set."""
    by_category: dict[str, set[str]] = {}
    for text in context_texts:
        for name, category in extract_category_entities(text):
            by_category.setdefault(category, set()).add(name)

    plural_categories = {cat: sorted(names) for cat, names in by_category.items()
                         if len(names) >= 2}
    trace = {"categories_found": {c: sorted(n) for c, n in by_category.items()},
             "plural_categories": plural_categories, "flagged": bool(plural_categories),
             "inert": not plural_categories}
    if not plural_categories:
        return list(context_texts), trace

    notes = []
    for category, names in sorted(plural_categories.items()):
        notes.append(f"Note: multiple {category} mentioned in this context: "
                     f"{', '.join(names)} — verify which one is actually relevant "
                     f"to the question before answering.")
    return list(context_texts) + notes, trace


def _self_check() -> None:
    ctx1 = ["Curious about Spirit Airlines' baggage policies",
            "Flew Delta Airlines to Boston", "Likes coffee"]
    rendered1, trace1 = same_category_entity_enumeration(ctx1)
    assert trace1["flagged"] is True
    assert "Spirit Airlines" in rendered1[-1] and "Delta Airlines" in rendered1[-1]

    ctx2 = ["Flew Delta Airlines to Boston", "Likes coffee", "Works at Google"]
    rendered2, trace2 = same_category_entity_enumeration(ctx2)
    assert rendered2 == ctx2 and trace2["inert"] is True

    ctx3 = ["Visited the Science Museum", "Also went to the Science Museum again"]
    rendered3, trace3 = same_category_entity_enumeration(ctx3)
    assert trace3["inert"] is True  # same entity repeated, not a plurality

    print("self-check OK: 3/3 cases correct (flag on 2 distinct, inert on 1, "
          "inert on repeated-same-entity)")


if __name__ == "__main__":
    _self_check()
