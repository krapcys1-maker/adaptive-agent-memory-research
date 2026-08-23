"""E2-A: derive a memory address from raw text, deterministically. No model.

What an address is
------------------
One slot: ``(entity, property, scope)``. Records sharing a slot form one
supersession chain, so ``service.billing / staging / endpoint.host`` is separate
from ``service.billing / prod / endpoint.host`` and from
``service.billing / — / test.command``.

The canonical string is **generated** from those three fields and never authored
freely. Free naming produces fragmentation by construction — ``billing.host``,
``billing.staging.host`` and ``billing.endpoint.staging`` are three chains for
one state, and the version history simply falls apart.

The honest limit of this arm
-----------------------------
These patterns were written by someone who has read the development corpus. Its
score on ``dev-a`` is therefore **optimistic by construction**, and that is
precisely why ``valid-b`` and the committed ``sealed-c`` exist. A deterministic
extractor tuned on data it has seen tells you what rules *can* express, not what
they will generalise to.

Two failure modes matter more than accuracy, and both are reported:

``collision``      two distinct slots receiving one address. That rebuilds the
                   48-near-clone problem inside a single drawer, where it is
                   harder to see.
``fragmentation``  one slot split across several addresses. Collision at least
                   keeps the chain together; fragmentation destroys it.

Abstention is deliberate
------------------------
When no rule matches confidently the extractor returns ``None`` rather than
guessing. A wrong entity opens someone else's drawer, which is worse than
opening none — so abstention is reported separately and, per the frozen
preregistration, is never a denominator.
"""

from __future__ import annotations

import re
from typing import Any, NamedTuple


class Address(NamedTuple):
    entity: str
    prop: str
    scope: str

    @property
    def canonical(self) -> str:
        """Generated, never authored. Scope is explicit even when absent."""
        return f"{self.entity}/{self.scope or '-'}/{self.prop}"


# Entity appears in a small number of grammatical positions. Each pattern names
# the construction it matches rather than being a bare regex, because the next
# person needs to know which sentence shape it was written for.
_ENTITY_PATTERNS = (
    # "Staging for billing deploys to ..." / "Correction: billing staging is now ..."
    re.compile(r"\b(?:staging|production|prod)\s+for\s+([a-z][a-z-]{2,})\b", re.I),
    re.compile(r"\bcorrection:\s*([a-z][a-z-]{2,})\s+(?:staging|production|prod)\b", re.I),
    # "Deploy log for billing: ..." / "Confirmed the billing staging target ..."
    re.compile(r"\bdeploy log for\s+([a-z][a-z-]{2,})\b", re.I),
    re.compile(r"\bconfirmed the\s+([a-z][a-z-]{2,})\s+(?:staging|production|prod)\b", re.I),
    # "the billing-fuzz suite" / "tests/billing-fuzz"
    re.compile(r"\btests/([a-z][a-z-]*?)-[a-z0-9]+\b", re.I),
    re.compile(r"\bthe\s+([a-z][a-z-]*?)-[a-z0-9]+\s+suite\b", re.I),
    # "pool exhausted under load in billing"
    re.compile(r"\bunder load in\s+([a-z][a-z-]{2,})\b", re.I),
    # "the billing retry loop"
    re.compile(r"\bthe\s+([a-z][a-z-]{2,})\s+retry loop\b", re.I),
    # "the audit for billing is mandatory"
    re.compile(r"\bfor\s+([a-z][a-z-]{2,})\s+is mandatory\b", re.I),
    # "klucz wdrozeniowy dla billing" / "the billing deployment key"
    re.compile(r"\bdla\s+([a-z][a-z-]{2,})\b", re.I),
    re.compile(r"\bthe\s+([a-z][a-z-]{2,})\s+deployment key\b", re.I),
    # "src/util/billing_text.py"
    re.compile(r"\bsrc/util/([a-z][a-z-]*?)_[a-z]+\.py\b", re.I),
)

# Words that occupy an entity position without being an entity. Without this the
# extractor confidently returns "the" or "staging" as a service name.
_NOT_AN_ENTITY = frozenset({
    "the", "a", "an", "this", "that", "our", "your", "its", "their", "all",
    "staging", "production", "prod", "test", "tests", "suite", "deploy",
    "release", "host", "port", "client", "log", "key", "and", "for", "with",
})

# Property is decided by what the sentence asserts, not by where it sits. Order
# matters: the first match wins, so the most specific shapes come first.
_PROPERTY_RULES = (
    (re.compile(r"https?://[a-z0-9.-]+:\d+", re.I), "endpoint.host"),
    (re.compile(r"\bpytest\b.*?\b(--[a-z-]+(?:=\w+)?|-p\s+\S+)", re.I | re.S), "test.command"),
    (re.compile(r"\bpool was sized\s+\d+|\bconnection pool exhausted\b", re.I), "db.pool_size"),
    (re.compile(r"\bretry loop\b", re.I), "reliability.retry_policy"),
    (re.compile(r"\bkey rotates\b|\bklucz wdro\w+ rotujemy\b", re.I), "credential.rotation"),
    (re.compile(r"\bexports\s+\w+\s+functions\b", re.I), "module.exports"),
    (re.compile(r"\b(audit|signature check|licence scan|policy gate)\b", re.I), "release.gate"),
)

_SCOPE_RULES = (
    (re.compile(r"\bstaging\b", re.I), "staging"),
    (re.compile(r"\b(production|prod)\b", re.I), "production"),
)


def _entity(text: str) -> str | None:
    for pattern in _ENTITY_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        candidate = match.group(1).lower().strip("-")
        if candidate and candidate not in _NOT_AN_ENTITY and not candidate.isdigit():
            return f"service.{candidate}"
    return None


def _property(text: str) -> str | None:
    for pattern, name in _PROPERTY_RULES:
        if pattern.search(text):
            return name
    return None


def _scope(text: str) -> str:
    for pattern, name in _SCOPE_RULES:
        if pattern.search(text):
            return name
    return ""


def extract(text: str, canonicalise: bool = False) -> Address | None:
    """The address this record concerns, or None when no rule is confident.

    Both an entity and a property are required. An entity alone cannot name a
    slot — `service.billing` is a drawer with no shelf — and a property alone
    belongs to everyone, which is precisely the collision the metrics watch for.
    """
    entity = _entity(text)
    if entity is None and canonicalise:
        # E2-A3. Frozen by digest before execution, labelled post-hoc: proposed
        # after A2 moved the bottleneck from property to entity.
        from corpus.entity_canon import canonical_entity
        entity = canonical_entity(text)
    if entity is None:
        return None
    prop = _property(text)
    if prop is None and canonicalise:
        # E2-A2 only. Frozen by digest before execution, and labelled post-hoc:
        # this arm was proposed after E2-A's failure, not registered alongside it.
        from corpus.property_canon import canonical_property
        prop = canonical_property(text)
    if prop is None:
        return None
    return Address(entity, prop, _scope(text))


def extract_query(question: str, canonicalise: bool = False) -> Address | None:
    """The slot a question asks about.

    The same rules, because a question that cannot be addressed by the rules that
    addressed the records would silently open a different drawer than the one the
    records went into.
    """
    return extract(question, canonicalise)


def describe() -> dict[str, Any]:
    return {
        "arm": "E2-A deterministic",
        "model": None,
        "api_cost_usd": 0.0,
        "entity_patterns": len(_ENTITY_PATTERNS),
        "property_rules": len(_PROPERTY_RULES),
        "stoplist": len(_NOT_AN_ENTITY),
        "canonical_form": "entity/scope/property, generated from the fields, never authored",
        "abstains": "when either entity or property is unmatched; a wrong entity opens someone else's drawer",
        "honest_limit": (
            "written by an author who has read dev-a, so its dev-a score is optimistic by "
            "construction. valid-b and the committed sealed-c exist for exactly this reason"
        ),
    }
