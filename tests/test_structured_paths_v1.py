"""Whole-packet counterfactual time/scope tests, including positive controls."""
import json

import pytest

from tools.structured_memory_v1 import Source
from tools.structured_memory_v3 import Memory
from tools.structured_paths_v1 import QueryView, options, messages


def add(m, sid, scope, text, subject, predicate, value, recorded=1):
    m.add_source(Source(sid, scope, text, recorded))
    m.extract(sid, {'claims': [{'subject': subject, 'predicate': predicate, 'object': value}]}, learn=True)


def packet(path, entity, known_at):
    with QueryView(path) as m:
        question = f'Where does {entity} live?'
        plans, trace = options(m, 'public', question, valid_at=known_at, known_at=known_at)
        packed = messages(m, question, plans, 'public', valid_at=known_at, known_at=known_at)
        results = [m.execute('public', question, p, valid_at=known_at, known_at=known_at) for p in plans]
        probe = m.execute('public', question, {'anchor': entity, 'steps': [{'predicate': 'hidden_code'}]}, valid_at=known_at, known_at=known_at)
        return json.dumps([plans, trace, packed, results, probe], sort_keys=True)


@pytest.mark.parametrize('number', range(12))
@pytest.mark.parametrize('known_at', [0, 1, 5, 9])
@pytest.mark.parametrize('mode', ['future', 'private', 'both'])
@pytest.mark.parametrize('hidden_first', [False, True])
def test_unavailable_appends_cannot_change_entire_packet(tmp_path, number, known_at, mode, hidden_first):
    entity, value = f'Entity{number}', f'Place{number}'
    reference, contaminated = tmp_path/'reference', tmp_path/'contaminated'
    def visible(m):
        add(m, 'visible', 'public', f'{entity} lives in {value}.', entity, 'lives_in', value)
    def hidden(m):
        for kind in (['future', 'private'] if mode == 'both' else [mode]):
            scope, tick = ('public', 10) if kind == 'future' else ('private', 1)
            add(m, kind+'-shell', scope, f'SecretCANARY{number}: {entity} lives in Hidden{number}.', entity, 'lives_in', f'Hidden{number}', tick)
            add(m, kind+'-code', scope, f'{entity} has code Token{number}.', entity, 'hidden_code', f'Token{number}', tick)
    with Memory(reference, writable=True) as m: visible(m)
    with Memory(contaminated, writable=True) as m:
        if hidden_first: hidden(m)
        visible(m)
        if not hidden_first: hidden(m)
    before = contaminated.read_bytes()
    assert packet(reference, entity, known_at) == packet(contaminated, entity, known_at)
    assert contaminated.read_bytes() == before


def test_future_shell_becomes_visible_at_its_recording_tick(tmp_path):
    path = tmp_path/'memory'
    with Memory(path, writable=True) as m:
        add(m, 'seed', 'public', 'Mira lives in Koral.', 'Mira', 'lives_in', 'Koral')
        add(m, 'future', 'public', 'FutureNOVA: Koral belongs to Country.', 'Koral', 'belongs_to', 'Country', 10)
    assert 'FutureNOVA' not in packet(path, 'Mira', 9)
    assert 'FutureNOVA' in packet(path, 'Mira', 10)
    with QueryView(path) as m:
        assert m.execute('public', 'Mira', {'anchor': 'Mira', 'steps': [{'predicate': 'lives_in'}, {'predicate': 'belongs_to'}]}, valid_at=10, known_at=10)['value'] == 'Country'


def test_manual_unavailable_plan_cannot_be_packed(tmp_path):
    path = tmp_path/'memory'
    with Memory(path, writable=True) as m:
        add(m, 'seed', 'public', 'Mira lives in Koral.', 'Mira', 'lives_in', 'Koral')
        add(m, 'private', 'private', 'Mira has code Token.', 'Mira', 'hidden_code', 'Token')
    with QueryView(path) as m:
        with pytest.raises(ValueError, match='scope/time'):
            messages(m, 'Mira', [{'anchor': 'Mira', 'steps': [{'predicate': 'hidden_code'}]}], 'public', valid_at=1, known_at=1)


def test_resolve_result_cannot_poison_following_queries(tmp_path):
    path = tmp_path/'memory'
    with Memory(path, writable=True) as m:
        add(m, 'seed', 'public', 'Mira lives in Koral.', 'Mira', 'lives_in', 'Koral')
    with QueryView(path) as m:
        m.resolve('public', 'Mira', 'lives_in', valid_at=1, known_at=1)['values'].append('Invented')
        assert m.resolve('public', 'Mira', 'lives_in', valid_at=1, known_at=1)['values'] == ['Koral']
    with pytest.raises(ValueError, match='read-only'):
        QueryView(path, writable=True)
