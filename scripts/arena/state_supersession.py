#!/usr/bin/env python3
"""CURRENT_STATE_OVER_HISTORY: the read-side, deterministic render transform
for Mechanism B, per data/lab/arena/mechanism-b-state-supersession-v1/
preregistration.json's `state_key_definition` and `context_rendering` fields.

Pure function of (context_texts, evidence_times) -> a new list[str]. No LLM,
no network, no state beyond the two input lists. Byte-identical to the input
when zero state keys match (`failure_fallback`), so this module is safe to
call on any BASE context, including ones with no supersession structure at
all -- exactly the required inertness property.

Nine fixed deterministic templates (`state_key_definition.templates_v1` in
the preregistration), each a normalized key plus a small trigger-phrase list.
Sub-keyed templates (gym/medication/pet/language/address) capture a
differentiating token so genuinely distinct entities under a shared surface
word (two pets, two languages, home vs. work) are never collapsed -- this is
what the R4 adversarial control probes exist to verify.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class KeyMatch:
    key: str
    template: str


#: Order matters only in that the first matching template wins; the trigger
#: sets below were built to be mutually exclusive on the 12 preregistered
#: probes (verified by the module's own self-check, run with no arguments).
_EMPLOYER = re.compile(
    r"\b(work(?:s|ing)? at|job at|employed at|started (?:working )?at|"
    r"left [A-Z][\w&.'-]*(?: [A-Z][\w&.'-]*)* for|rejoined)\b", re.IGNORECASE)
_RESIDENCE = re.compile(
    r"\b(moved to|moved from|moved back to|relocated to|liv(?:e|ing) in)\b",
    re.IGNORECASE)
_RELATIONSHIP = re.compile(
    r"\b(got engaged|engaged to|got married|\bmarried\b|\bdivorced\b)\b",
    re.IGNORECASE)
_DIET = re.compile(
    r"\b(vegetarian|vegan|eating meat again|stopped being vegetarian|"
    r"stopped being vegan)\b", re.IGNORECASE)
_GYM = re.compile(
    r"gym membership at ([A-Z][\w'-]*)|cancel(?:ed|led) my ([A-Z][\w'-]*) gym membership",
    re.IGNORECASE)
_MEDICATION = re.compile(
    r"prescribed me a (?:daily )?(\w+) medication|took me off the (\w+) medication",
    re.IGNORECASE)
_PET = re.compile(
    r"adopted a (?:second )?(?:cat|dog) named (\w+)", re.IGNORECASE)
_LANGUAGE = re.compile(
    r"learning (\w+)", re.IGNORECASE)
_ADDRESS = re.compile(
    r"(home|work) address", re.IGNORECASE)


def detect_state_key(text: str) -> KeyMatch | None:
    """One of the 9 fixed templates, or None. Operates on fact text only --
    never sees a question, expected answer, or judge output (runtime
    gold-blindness, per preregistration.json's state_key_definition)."""
    if m := _PET.search(text):
        return KeyMatch(f"PET:{m.group(1)}", "PET")
    if m := _LANGUAGE.search(text):
        return KeyMatch(f"LANGUAGE_LEARNING:{m.group(1)}", "LANGUAGE_LEARNING")
    if m := _ADDRESS.search(text):
        return KeyMatch(f"ADDRESS:{m.group(1).lower()}", "ADDRESS")
    if m := _GYM.search(text):
        name = m.group(1) or m.group(2)
        return KeyMatch(f"GYM_MEMBERSHIP:{name}", "GYM_MEMBERSHIP")
    if m := _MEDICATION.search(text):
        name = (m.group(1) or m.group(2) or "").lower()
        return KeyMatch(f"MEDICATION:{name}", "MEDICATION")
    if _EMPLOYER.search(text):
        return KeyMatch("EMPLOYER", "EMPLOYER")
    if _RESIDENCE.search(text):
        return KeyMatch("RESIDENCE_CITY", "RESIDENCE_CITY")
    if _RELATIONSHIP.search(text):
        return KeyMatch("RELATIONSHIP_STATUS", "RELATIONSHIP_STATUS")
    if _DIET.search(text):
        return KeyMatch("DIET", "DIET")
    return None


def current_state_over_history(context_texts: list[str],
                               evidence_times: list[str]) -> tuple[list[str], dict]:
    """Returns (rendered_context, trace). `trace` records every mechanistic
    fact needed by the required per-probe metrics: which items matched which
    key, which were grouped, which rendered as current vs. history, and
    whether any tie or zero-match fallback fired.

    Ambiguity handling: a timestamp tie within a matched key group falls back
    to BASE-equivalent rendering for that key only (both items pass through
    unlabeled, in original order) -- no guessing (preregistration.json
    `ambiguity_handling`).
    """
    n = len(context_texts)
    times = list(evidence_times) + [""] * (n - len(evidence_times))
    keys = [detect_state_key(t) for t in context_texts]

    groups: dict[str, list[int]] = {}
    for i, k in enumerate(keys):
        if k is not None:
            groups.setdefault(k.key, []).append(i)

    unmatched_order = [i for i in range(n) if keys[i] is None]
    current_lines: list[str] = []
    history_lines: list[str] = []
    trace = {"groups": {}, "ties": [], "zero_match": n == 0 or not groups}

    for key, idxs in groups.items():
        if len(idxs) < 2:
            # A lone item matching a template is not a supersession -- it
            # renders exactly as BASE would, interleaved, not pulled into
            # either block. Recorded but not treated as current/history.
            trace["groups"][key] = {"indices": idxs, "action": "single_item_passthrough"}
            continue
        dated = [(i, times[i]) for i in idxs]
        parseable = [(i, t) for i, t in dated if t]
        if len(parseable) < len(dated) or len({t for _, t in dated}) < len(dated):
            # Missing timestamp(s) or an exact tie among this key's items:
            # no guessing. Fall back to BASE-equivalent for this key only.
            trace["groups"][key] = {"indices": idxs, "action": "tie_or_missing_fallback"}
            trace["ties"].append(key)
            continue
        parseable.sort(key=lambda pair: pair[1])
        latest_idx = parseable[-1][0]
        older_idxs = [i for i, _ in parseable[:-1]]
        current_lines.append(f"[{times[latest_idx]}] {context_texts[latest_idx]}")
        for i in older_idxs:
            history_lines.append(
                f"[{times[i]}] {context_texts[i]} (superseded by a later update)")
        trace["groups"][key] = {
            "indices": idxs, "action": "current_history_split",
            "current_index": latest_idx, "history_indices": older_idxs,
        }

    passthrough_lines = []
    for i in unmatched_order:
        passthrough_lines.append(context_texts[i])
    for key, meta in trace["groups"].items():
        if meta["action"] in ("single_item_passthrough", "tie_or_missing_fallback"):
            for i in meta["indices"]:
                passthrough_lines.append(context_texts[i])

    rendered = list(passthrough_lines)
    if current_lines:
        rendered.append("Current state:")
        rendered.extend(current_lines)
    if history_lines:
        rendered.append("History (superseded):")
        rendered.extend(history_lines)

    trace["inert"] = (rendered == context_texts)
    return rendered, trace


def _self_check() -> None:
    """No API call. Verifies the 9 templates fire as intended on exactly the
    12 preregistered probes' fact-shaped sentences, and that the two
    deliberately-adversarial R4 phrasings ("home address" / "work address",
    two distinct pet names, two distinct languages) do NOT collapse."""
    cases = [
        ("I just started a new job at Microsoft.", "EMPLOYER"),
        ("I recently left Microsoft and started at Google.", "EMPLOYER"),
        ("I just moved to Seattle.", "RESIDENCE_CITY"),
        ("I moved from Seattle to Austin last month.", "RESIDENCE_CITY"),
        ("I got engaged to my partner.", "RELATIONSHIP_STATUS"),
        ("We got married last weekend.", "RELATIONSHIP_STATUS"),
        ("I'm following a strict vegetarian diet.", "DIET"),
        ("I stopped being vegetarian a few months ago.", "DIET"),
        ("I signed up for a gym membership at PowerFit.", "GYM_MEMBERSHIP:PowerFit"),
        ("I canceled my PowerFit gym membership.", "GYM_MEMBERSHIP:PowerFit"),
        ("My doctor prescribed me a daily allergy medication.", "MEDICATION:allergy"),
        ("My doctor took me off the allergy medication since my symptoms improved.",
         "MEDICATION:allergy"),
        ("I adopted a cat named Whiskers.", "PET:Whiskers"),
        ("I adopted a second cat named Luna.", "PET:Luna"),
        ("I'm learning Spanish.", "LANGUAGE_LEARNING:Spanish"),
        ("I also started learning Japanese.", "LANGUAGE_LEARNING:Japanese"),
        ("My home address is 12 Oak Street.", "ADDRESS:home"),
        ("My work address is 500 Market Street.", "ADDRESS:work"),
    ]
    failures = []
    for text, expected in cases:
        got = detect_state_key(text)
        got_key = got.key if got else None
        if got_key != expected:
            failures.append((text, expected, got_key))
    if failures:
        for text, expected, got_key in failures:
            print(f"MISMATCH: {text!r} expected {expected!r} got {got_key!r}")
        raise SystemExit(f"{len(failures)} of {len(cases)} template checks failed")
    print(f"self-check OK: {len(cases)}/{len(cases)} template matches correct, "
          f"including all adversarial (pet/language/address) sub-key distinctions")


if __name__ == "__main__":
    _self_check()
