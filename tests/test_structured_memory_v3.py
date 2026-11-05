"""Behavioral checks of exact reuse and visible-plan boundaries; no inference."""
from dataclasses import asdict
import json

import pytest

from tools.structured_memory_v1 import Source
from tools.structured_memory_v3 import Memory


def extracted(memory, sid='seed', text='Mira lives in Koral.', recorded=1,
              scope='public', predicate='lives_in', polarity='affirm', method='model'):
    memory.add_source(Source(sid, scope, text, recorded))
    memory.extract(sid, {'claims': [{'subject': 'Mira', 'predicate': predicate,
                                    'object': 'Koral', 'polarity': polarity}]},
                   method=method, learn=True)


@pytest.mark.parametrize('text', [
    'Mira lives in Koral if the move goes ahead.',
    'Mira lives in Koral and works in Atrium.',
    'Mira lives in Koral. She works in Atrium.',
    'Mira might live in Koral.', 'Mira does not live in Koral.',
    '"Mira lives in Koral."', 'Does Mira live in Koral?',
    'Mira lives in Koral \u200bif the move goes ahead.',
    'Mira lives in Koral unless the plan fails.',
    'Mira lives in Koral, according to an unverified rumor.',
])
def test_unseen_text_never_gets_generalized_assertion(tmp_path, text):
    path = tmp_path/'memory'
    with Memory(path, writable=True) as m:
        extracted(m)
        m.add_source(Source('target', 'public', text, 2))
        before = path.read_bytes()
        assert m.cached('target') is None
        assert path.read_bytes() == before
        assert m.sources['target'].text == text


def test_exact_replay_is_persistent_and_has_origin_proof(tmp_path):
    path = tmp_path/'memory'
    with Memory(path, writable=True) as m:
        extracted(m)
        m.add_source(Source('repeat', 'public', 'Mira lives in Koral.', 2))
        claim = m.cached('repeat'); assert claim.source == 'repeat'
        assert m.cache_info('repeat')['derived_from'] == ['seed']
        row = asdict(claim); row.pop('source')
        m.extract('repeat', {'claims': [row]}, method='template')
    event = json.loads(path.read_text(encoding='utf-8').splitlines()[-1])['event']
    assert event['derived_from'] == ['seed']
    before = path.read_bytes()
    with Memory(path) as m:
        result = m.resolve('public', 'Mira', 'lives_in', valid_at=2, known_at=2)
        assert result['values'] == ['Koral']
        assert result['sources'] == ['repeat', 'seed']
    assert path.read_bytes() == before


@pytest.mark.parametrize('recorded,scope', [(10, 'public'), (1, 'private')])
def test_unavailable_or_private_model_does_not_seed_cache(tmp_path, recorded, scope):
    with Memory(tmp_path/'memory', writable=True) as m:
        extracted(m, recorded=recorded, scope=scope)
        m.add_source(Source('repeat', 'public', 'Mira lives in Koral.', 2))
        assert m.cached('repeat') is None


@pytest.mark.parametrize('variant', ['predicate', 'denial', 'empty', 'multiple'])
def test_disagreement_rejects_replay_instead_of_choosing_one_model(tmp_path, variant):
    with Memory(tmp_path/'memory', writable=True) as m:
        extracted(m)
        m.add_source(Source('other', 'public', 'Mira lives in Koral.', 2))
        claims = [{'subject': 'Mira', 'predicate': 'lives_in', 'object': 'Koral'}]
        if variant == 'predicate': claims[0]['predicate'] = 'visits_city'
        elif variant == 'denial': claims[0]['polarity'] = 'deny'
        elif variant == 'empty': claims = []
        else: claims.append({'subject': 'Mira', 'predicate': 'visits_city', 'object': 'Koral'})
        m.extract('other', {'claims': claims})
        m.add_source(Source('repeat', 'public', 'Mira lives in Koral.', 3))
        assert m.cached('repeat') is None
        assert m.cache_info('repeat')['reason'] == 'ambiguous_model_interpretations'


def test_supplied_test_and_legacy_template_do_not_become_model_origins(tmp_path):
    from tools.structured_memory_v2 import Memory as Legacy
    path = tmp_path/'memory'
    with Legacy(path, writable=True) as m:
        extracted(m, method='supplied-test')
        extracted(m, sid='legacy', method='template')
    with Memory(path, writable=True) as m:
        m.add_source(Source('repeat', 'public', 'Mira lives in Koral.', 2))
        assert m.cached('repeat') is None


def test_forged_template_proposal_rejected_before_append(tmp_path):
    path = tmp_path/'memory'
    with Memory(path, writable=True) as m:
        extracted(m)
        m.add_source(Source('target', 'public', 'Mira lives in Koral if the move goes ahead.', 2))
        before = path.read_bytes()
        with pytest.raises(ValueError, match='Exact replay'):
            m.extract('target', {'claims': [{'subject': 'Mira', 'predicate': 'lives_in',
                      'object': 'Koral if the move goes ahead'}]}, method='template')
        assert path.read_bytes() == before
        assert 'target' not in m.extracted


@pytest.mark.parametrize('predicate', ['private_only', 'future_only', 'absent', [], {}])
def test_invalid_plan_is_identical_for_hidden_or_absent_relation(tmp_path, predicate):
    with Memory(tmp_path/'memory', writable=True) as m:
        extracted(m)
        extracted(m, sid='private', scope='private', predicate='private_only')
        extracted(m, sid='future', recorded=10, predicate='future_only')
        result = m.execute('public', 'Mira', {'anchor': 'Mira', 'steps': [{'predicate': predicate}]}, valid_at=2, known_at=2)
        assert result == {'status': 'invalid_plan', 'value': None, 'paths': []}


@pytest.mark.parametrize('tick', [True, False, 1.5, '2', None])
def test_noninteger_query_clock_rejected(tmp_path, tick):
    with Memory(tmp_path/'memory') as m:
        with pytest.raises(ValueError, match='integer ticks'):
            m.resolve('public', 'Mira', 'lives_in', valid_at=2, known_at=tick)
