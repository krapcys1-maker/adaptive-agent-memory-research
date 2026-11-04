"""Opt-in typed fictional facts and a narrow memory-output contract.

This does not extract facts from free prose, infer query slots, resolve revisions,
verify real-world truth or change a production agent. Values stay fictional.
"""
from __future__ import annotations

import json
import re
import unicodedata

SLOT = re.compile(r'[a-z][a-z0-9_]{0,63}\Z')


def folded(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def validate_claim(claim, source_text):
    if not isinstance(claim, dict) or set(claim) != {'slot', 'value'}:
        raise ValueError('typed_claim requires exactly slot and value.')
    slot, value = claim['slot'], claim['value']
    if not isinstance(slot, str) or not SLOT.fullmatch(slot):
        raise ValueError('Invalid typed-claim slot ID.')
    if (not isinstance(value, str) or not value.strip() or len(value) > 160
            or any(ord(c) < 32 for c in value) or folded(value) == 'unknown'
            or not any(c.isalnum() for c in value)):
        raise ValueError('Invalid or reserved typed-claim value.')
    pattern = r'(?<!\w)' + re.escape(folded(value)) + r'(?!\w)'
    if not re.search(pattern, folded(source_text)):
        raise ValueError('Typed value must occur as a whole phrase in source text.')
    return {'slot': slot, 'value': value.strip()}


def parse_value(text):
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or set(value) != {'value'}:
        return None
    answer = value['value']
    return answer.strip() if isinstance(answer, str) and answer.strip() and len(answer) <= 160 else None


def guard_answer(slot, candidate_text, shown_items, *, task_type='personal'):
    """Use only retrieved typed evidence; no expected/gold value argument exists."""
    def out(value, resolution, sources=()):
        return {'value': value, 'resolution': resolution, 'source_ids': sorted(set(sources))}
    if task_type != 'personal':
        return out('UNKNOWN', 'unsupported_task')
    if not isinstance(slot, str) or not SLOT.fullmatch(slot):
        raise ValueError('A valid explicit slot ID is required; routing is external.')
    matches = {}
    source_ids = []
    for item in shown_items:
        if not isinstance(item, dict):
            return out('UNKNOWN', 'invalid_evidence')
        if item.get('origin') != 'fiction_autobio':
            continue
        meta = item.get('meta') or {}
        if not isinstance(meta, dict):
            return out('UNKNOWN', 'invalid_evidence')
        if 'typed_claim' not in meta:
            continue
        try:
            claim = validate_claim(meta['typed_claim'], item.get('text', ''))
        except (ValueError, TypeError):
            return out('UNKNOWN', 'invalid_evidence')
        if claim['slot'] != slot:
            continue
        if not isinstance(item.get('id'), str) or not item['id']:
            return out('UNKNOWN', 'invalid_evidence')
        key = folded(claim['value'])
        matches.setdefault(key, claim['value'])
        source_ids.append(item['id'])
    if not matches:
        return out('UNKNOWN', 'no_evidence')
    if len(matches) != 1:
        return out('UNKNOWN', 'conflicting_evidence', source_ids)
    expected = next(iter(matches.values()))
    candidate = parse_value(candidate_text)
    accepted = candidate is not None and folded(candidate) == folded(expected)
    return out(expected, 'accepted' if accepted else 'corrected', source_ids)
