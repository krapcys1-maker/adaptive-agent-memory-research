"""E2-A2: map surface forms of one property onto a single identifier. No model.

Status: **post-hoc mechanistic follow-up, preregistered before execution.**

This arm did not exist when the thresholds were frozen. It was proposed after
E2-A failed, because the failure had a specific shape: rules written against the
*assertion* form records use — "the deployment key rotates" — did not match the
*interrogative* form questions use — "how long does the old key work after
rotation". Entity resolved on 0.571 of questions and property on 0.286.

That ordering is recorded rather than smoothed over. An arm proposed after seeing
a result is a different kind of evidence from one registered before, and the only
thing that makes it usable is saying so.

What this adds, and what it deliberately does not
--------------------------------------------------
One mapping from surface forms to property identifiers, applied to records and
questions alike. Nothing else changes: same entity rules, same scope rules, same
canonical address construction, same thresholds, same denominators.

It does **not** add a synonym for every phrase in the corpus. A dictionary
written until the development set passes is a dictionary of that development
set, and its number would mean nothing. Each entry below names a *linguistic
alternation* — assertion against question, verb against noun, English against
Polish — rather than a string that happened to appear.

Why the transfer test is the real one
--------------------------------------
The mapping is written with the development corpus visible, so its development
score is a development result and not evidence of generalisation. `valid-b` uses
twelve entirely different subject nouns and is the first run that says whether
these are alternations or just this corpus's wording.

    DEV-A2 high, VALID-A2 high   property normalisation generalises without a model
    DEV-A2 high, VALID-A2 low    a dictionary was written for one corpus
"""

from __future__ import annotations

import re
from typing import Any

# Each key is a property identifier; each value is the set of alternations that
# denote it. Ordered most specific first, because "rotation" alone would swallow
# phrases that a longer pattern classifies better.
#
# The test of an entry is not "does it appear in the corpus" but "is it a form
# the same property genuinely takes". Anything failing that is a lookup table
# fitted to a test set.
_PROPERTY_FORMS: dict[str, tuple[str, ...]] = {
    "credential.rotation": (
        r"\bkey rotates?\b",
        r"\brotat\w*\s+(?:the\s+)?(?:deployment\s+)?key\b",
        r"\bafter\s+rotation\b",
        r"\bold\s+(?:deployment\s+)?key\b",
        r"\bprevious\s+key\b",
        r"\bklucz\s+wdro\w+\b",          # Polish: deployment key, any inflection
        r"\bpo\s+rotacji\b",             # Polish: after rotation
        r"\brotujemy\b",
    ),
    "endpoint.host": (
        r"https?://[a-z0-9.-]+:\d+",
        r"\bstaging\s+host\b",
        r"\bdeploy\s+target\b",
        r"\bwhich\s+host\b",
        r"\bmoved\s+to\b.*\binternal\b",
        r"\bis now\s+https?://",
    ),
    "test.command": (
        r"\bpytest\b",
        r"\bhow\s+should\s+the\s+\S+\s+suite\s+be\s+run\b",
        r"\brun\s+the\s+\S+\s+suite\b",
        r"\bsuite\s+be\s+run\b",
        r"\b--[a-z-]+(?:=\w+)?\b",
    ),
    "db.pool_size": (
        r"\bpool\s+exhaust\w*\b",
        r"\bpool\s+was\s+sized\b",
        r"\bconnection\s+pool\b",
    ),
    "reliability.retry_policy": (
        r"\bretry\s+loop\b",
        r"\bremoved\s+instead\s+of\b.*\btimeout\b",
        r"\blonger\s+timeout\b",
        r"\bsocket\s+timeout\b",
    ),
    "module.exports": (
        r"\bexports?\s+\w+\s+functions?\b",
        r"\bhow\s+many\s+functions\b",
    ),
    "release.gate": (
        r"\b(?:audit|signature check|licence scan|policy gate)\b",
        r"\bbefore\s+(?:any\s+)?deploy\w*\b",
        r"\bmandatory\s+before\b",
    ),
}

_COMPILED: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile("|".join(forms), re.I))
    for name, forms in _PROPERTY_FORMS.items()
)


def canonical_property(text: str) -> str | None:
    """The property identifier this text concerns, or None.

    First match wins and the order is the declaration order above, so a more
    specific family is tried before a broader one. Ties are not resolved by
    scoring: a scored tie-break would be a third mechanism smuggled into an arm
    that claims to be a lookup.
    """
    for name, pattern in _COMPILED:
        if pattern.search(text):
            return name
    return None


def describe() -> dict[str, Any]:
    return {
        "arm": "E2-A2 deterministic + property canonicalisation",
        "status": "post-hoc mechanistic follow-up, preregistered before execution",
        "proposed_after": "E2-A, which resolved entity on 0.571 of questions and property on 0.286",
        "model": None,
        "api_cost_usd": 0.0,
        "properties": len(_PROPERTY_FORMS),
        "surface_forms": sum(len(v) for v in _PROPERTY_FORMS.values()),
        "written_against": "dev-a, which is visible; its dev-a score is a development result",
        "transfer_test": "valid-b, twelve different subject nouns, run once after this file is frozen",
        "entry_criterion": (
            "each form names a linguistic alternation — assertion against question, verb against "
            "noun, English against Polish — not a string observed in the corpus. A dictionary "
            "written until the development set passes is a dictionary of that development set"
        ),
    }
