"""Literal source-lead/heading dependencies for immutable windows.

Structural context only: no semantic mode detection, truth or event authority.
The limited heading grammar is declared here, not claimed to be CommonMark.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import re

from tools import source_windows_v1 as W

POLICY = 'source-context-v1'
ATX = re.compile(r'^ {0,3}(#{1,6})(?:[ \t]+(.*)|[ \t]*)$')
OPEN_FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')


@dataclass(frozen=True)
class Dependency:
    kind: str
    char_start: int
    char_end: int
    byte_start: int
    byte_end: int
    text: str
    level: int | None = None
    section_end: int | None = None


def _dependency(source, kind, start, end, *, level=None, section_end=None):
    return Dependency(kind, start, end, len(source.text[:start].encode()),
                      len(source.text[:end].encode()), source.text[start:end], level, section_end)


def dependencies(source: W.Source, window: W.Window):
    """Revalidate the immutable slice; return exact lead and active headings.

    The lead is the complete first nonblank paragraph, never a cropped prefix.
    ATX headings outside unindented/<=3space backtick/tilde fenced blocks form
    nested sections until an equal/shallower heading or EOF. Blockquotes,
    indented blocks, setext headings and prose scope are not interpreted.
    Include headings governing any part of the window, including transitions.
    """
    if (window.source_id, window.scope, window.role, window.known_sequence,
        window.time_anchor_raw) != (source.id, source.scope, source.role,
                                   source.known_sequence, source.time_anchor_raw):
        raise ValueError('Window/source provenance mismatch.')
    expected = next((w for w in W.split(source, max_text_bytes=window.max_text_bytes,
                                      overlap_bytes=window.overlap_bytes) if w.id == window.id), None)
    if expected != window:
        raise ValueError('Window differs from canonical original source.')
    lines = source.text.splitlines(keepends=True)
    offsets = []; offset = 0
    for line in lines:
        offsets.append(offset); offset += len(line)
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None:
        raise ValueError('No source paragraph.')
    last = first
    while last < len(lines) and lines[last].strip():
        last += 1
    end = offsets[last] if last < len(lines) else len(source.text)
    result = [_dependency(source, 'source_lead', offsets[first], end)]
    headings = []; active = []; fence = None
    for line, start in zip(lines, offsets, strict=True):
        body = line.rstrip('\r\n')
        if fence:
            # Closing fence must use the same character and >=opening length.
            closing = re.fullmatch(r' {0,3}(' + re.escape(fence[0]) + '{' + str(fence[1]) + r',})[ \t]*', body)
            if closing:
                fence = None
            continue
        opened = OPEN_FENCE.fullmatch(body)
        if opened and not (opened[1][0] == '`' and '`' in opened[2]):
            fence = (opened[1][0], len(opened[1])); continue
        match = ATX.fullmatch(body)
        if not match:
            continue
        level = len(match[1])
        while active and headings[active[-1]]['level'] >= level:
            headings[active.pop()]['section_end'] = start
        headings.append({'start': start, 'end': start + len(line), 'level': level,
                         'section_end': len(source.text)})
        active.append(len(headings) - 1)
    for h in headings:
        if h['start'] < window.char_end and h['section_end'] > window.char_start:
            result.append(_dependency(source, 'atx_heading', h['start'], h['end'],
                                      level=h['level'], section_end=h['section_end']))
    return tuple(result)


def context_record(source: W.Source, window: W.Window):
    deps = dependencies(source, window)
    value = {'policy': POLICY, 'source_fingerprint': source.fingerprint,
             'dependencies': [asdict(d) for d in deps],
             'semantic_status': 'unresolved; literal context is not event or truth validation',
             'unrepresented_source_context': window.char_start != 0 or window.char_end != len(source.text)}
    return value | {'context_id': 'C1-' + W.digest({'window': window.id, **value})}


def verify_context(source, window, context):
    if context_record(source, window) != context:
        raise ValueError('Context dependency differs from full original source.')
    return True


def render_packet(question, pairs, *, scope, known_at, system=W.SYSTEM, max_message_bytes=6000):
    """Package only requested visible windows, attaching literal dependencies.

    No ranking or label input. A unit whose complete dependency envelope does
    not fit is omitted whole, never cropped. Canonical IDs stay in private
    alias mappings. Unknown semantics remain unknown even for a full source.
    """
    W.integer(known_at, 'availability cutoff')
    W.integer(max_message_bytes, 'message budget', 128, 1_000_000)
    if not isinstance(question, str) or not question.strip() or not isinstance(system, str) or not system.strip():
        raise ValueError('Question/system required.')
    pairs = list(pairs)
    if len(pairs) > 50 or len({w.id for s, w in pairs}) != len(pairs):
        raise ValueError('Too many or duplicate context windows.')
    if any(s.scope != scope or w.scope != scope or s.known_sequence > known_at or w.known_sequence > known_at for s, w in pairs):
        raise ValueError('Context outside visible scope/cutoff.')
    contexts = {w.id: context_record(s, w) for s, w in pairs}

    def build(selected):
        evidence = []; aliases = {}
        for i, (source, w) in enumerate(selected):
            alias = 'E' + str(i); aliases[alias] = w.id
            evidence.append({'window': alias, 'source': w.source_id, 'origin_role': w.role,
                'available_sequence': w.known_sequence, 'time_anchor_raw': w.time_anchor_raw,
                'source_sha256': w.source_sha256, 'char_span': [w.char_start, w.char_end],
                'utf8_span': [w.byte_start, w.byte_end], 'source_bytes': w.source_bytes,
                'partial_source': w.char_start != 0 or w.char_end != w.source_chars,
                'text': w.text, 'source_context': contexts[w.id]})
        body = {'question': question, 'history': {'scope': scope, 'coverage': 'retrieved excerpts only',
            'omitted_candidates': len(pairs) - len(selected), 'evidence': evidence}}
        messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': W.canonical(body)}]
        return messages, aliases

    if max(W.message_bytes(build([])[0]).values()) > max_message_bytes:
        raise ValueError('Question/system alone exceed message cap.')
    selected = []; omitted = []
    for pair in pairs:
        if max(W.message_bytes(build(selected + [pair])[0]).values()) <= max_message_bytes:
            selected.append(pair)
        else:
            alone_fits = max(W.message_bytes(build([pair])[0]).values()) <= max_message_bytes
            omitted.append({'window': pair[1].id, 'reason': 'remaining_message_budget' if alone_fits else 'unit_exceeds_message_budget'})
    messages, aliases = build(selected)
    return {'policy': POLICY, 'messages': messages, 'aliases': aliases,
            'shown_ids': [w.id for s, w in selected], 'omissions': omitted,
            'message_bytes': W.message_bytes(messages),
            'source_read_bytes': sum(len(s.text.encode()) for s in {s.id: s for s, w in pairs}.values()),
            'literal_dependency_bytes_shown': sum(len(d['text'].encode()) for s, w in selected for d in contexts[w.id]['dependencies']),
            'semantic_mode_validated': False}
