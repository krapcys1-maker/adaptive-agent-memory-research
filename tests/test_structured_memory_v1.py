"""Behavioral boundaries of the new candidate, without model/API dependencies."""
from dataclasses import asdict
import json

import pytest

from tools.structured_memory_v1 import Claim, Memory, Source, Template


def put(m, sid, s, p, o, t=1, **kwargs):
    scope = kwargs.pop('scope', 'test')
    polarity = kwargs.pop('polarity', 'affirm')
    source = Source(sid, scope, f'{s} has {p} {o}.', t, **kwargs)
    m.add_source(source)
    m.extract(sid, {'claims': [{'subject': s, 'predicate': p, 'object': o, 'polarity': polarity}]},
              method='supplied-test')


def state(m, t=10, known=10, scope='test'):
    return m.resolve(scope, 'Mira', 'lives_in', valid_at=t, known_at=known)


def test_restart_and_read_only_multihop_with_provenance(tmp_path):
    path = tmp_path/'memory.jsonl'
    with Memory(path, writable=True) as m:
        put(m, 'a', 'Mira', 'lives_in', 'Koral')
        put(m, 'b', 'Koral', 'located_in', 'Zefir')
    before = path.read_bytes()
    with Memory(path) as m:
        result = m.execute('test', 'Where is Mira located?', {'anchor': 'Mira', 'steps': [
            {'predicate': 'lives_in'}, {'predicate': 'located_in'}]}, valid_at=5, known_at=5)
        assert result['value'] == 'Zefir'
        assert [p['sources'] for p in result['paths'][0]] == [['a'], ['b']]
        with pytest.raises(ValueError, match='Read-only'):
            m.add_source(Source('c', 'test', 'A source.', 1))
    assert path.read_bytes() == before


def test_unresolved_conflict_does_not_become_latest_wins(tmp_path):
    with Memory(tmp_path/'m', writable=True) as m:
        put(m, 'a', 'Mira', 'lives_in', 'Koral')
        put(m, 'b', 'Mira', 'lives_in', 'Zefir', 2)
        assert state(m)['status'] == 'conflict'


def test_explicit_source_replacement_preserves_history(tmp_path):
    with Memory(tmp_path/'m', writable=True) as m:
        put(m, 'a', 'Mira', 'lives_in', 'Koral')
        put(m, 'b', 'Mira', 'lives_in', 'Zefir', 2, valid_from=5, supersedes=('a',))
        assert state(m, 3)['values'] == ['Koral']
        assert state(m, 6)['values'] == ['Zefir']
        assert state(m, 6, 1)['values'] == ['Koral']


def test_ordered_contract_future_and_expired_winner(tmp_path):
    with Memory(tmp_path/'m', writable=True) as m:
        put(m, 'a', 'Mira', 'lives_in', 'Koral', policy='ordered_single')
        put(m, 'b', 'Mira', 'lives_in', 'Zefir', 2, valid_from=5, valid_to=8, policy='ordered_single')
        assert state(m, 3)['values'] == ['Koral']
        assert state(m, 6)['values'] == ['Zefir']
        assert state(m, 9)['status'] == 'no_evidence'


def test_tied_ordered_records_decline_conflict(tmp_path):
    with Memory(tmp_path/'m', writable=True) as m:
        put(m, 'a', 'Mira', 'lives_in', 'Koral', policy='ordered_single')
        put(m, 'b', 'Mira', 'lives_in', 'Zefir', policy='ordered_single')
        assert state(m)['status'] == 'conflict'


def test_negation_not_positive_and_disagreement_visible(tmp_path):
    with Memory(tmp_path/'m', writable=True) as m:
        put(m, 'a', 'Mira', 'lives_in', 'Koral', polarity='deny')
        assert state(m)['status'] == 'no_evidence'
        put(m, 'b', 'Mira', 'lives_in', 'Koral', 2)
        assert state(m)['status'] == 'conflict'


def test_scopes_and_two_properties_do_not_collapse(tmp_path):
    with Memory(tmp_path/'m', writable=True) as m:
        put(m, 'a', 'Mira', 'lives_in', 'Koral')
        put(m, 'b', 'Mira', 'works_in', 'Zefir')
        put(m, 'c', 'Mira', 'lives_in', 'Sekret', scope='private')
        assert state(m)['values'] == ['Koral']
        assert m.anchors('test', 'Sekret', known_at=10) == []
        assert m.execute('test', 'Where is Mira?', {'anchor': 'Sekret', 'steps': [
            {'predicate': 'lives_in'}]}, valid_at=10, known_at=10)['status'] == 'unknown_subject'


def test_model_invented_spans_rejected_but_original_saved(tmp_path):
    path = tmp_path/'m'
    with Memory(path, writable=True) as m:
        m.add_source(Source('a', 'test', 'Mira lives in Koral.', 1))
        with pytest.raises(ValueError, match='exact source'):
            m.extract('a', {'claims': [{'subject': 'Mira', 'predicate': 'lives_in', 'object': 'Zefir'}]})
    with Memory(path) as m:
        assert m.sources['a'].text == 'Mira lives in Koral.'
        assert not m.claims


def test_learned_shell_is_literal_and_not_domain_specific():
    source = Source('a', 'test', '3. Orbita [A] carries the label of Red (B).', 1)
    template = Template.learn(source.text, Claim('a', 'Orbita [A]', 'label', 'Red (B)'))
    assert template.match(Source('b', 'test', '4. Teal + 2 carries the label of Zefir.', 2)).object == 'Zefir'
    assert template.match(Source('c', 'test', 'Mira does not carries the label of Zefir.', 3)) is None
    assert template.match(Source('d', 'test', 'Mira carries the label of Zefir?', 3)) is None
    assert template.match(Source('e', 'test', 'Mira carries the label of maybe Zefir.', 3)) is None


def test_object_before_subject_shell():
    template = Template.learn('The curator of Atrium is Mira.', Claim('a', 'Atrium', 'curator', 'Mira'))
    assert template.match(Source('b', 'test', 'The curator of Zefir is Koral.', 2)).subject == 'Zefir'
    reverse = Template.learn('Mira is the curator of Atrium.', Claim('a', 'Atrium', 'curator', 'Mira'))
    claim = reverse.match(Source('b', 'test', 'Koral is the curator of Zefir.', 2))
    assert (claim.subject, claim.object) == ('Zefir', 'Koral')


def test_source_identity_and_scope_policy_cannot_be_rewritten(tmp_path):
    with Memory(tmp_path/'m', writable=True) as m:
        a = Source('a', 'test', 'One.', 1)
        assert m.add_source(a)
        assert not m.add_source(a)
        with pytest.raises(ValueError, match='collision'):
            m.add_source(Source('a', 'test', 'Two.', 1))
        with pytest.raises(ValueError, match='policy'):
            m.add_source(Source('b', 'test', 'Two.', 2, policy='ordered_single'))


def test_single_writer_and_corruption_stop_without_erasing(tmp_path):
    path = tmp_path/'m'
    with Memory(path, writable=True) as m:
        put(m, 'a', 'Mira', 'lives_in', 'Koral')
        with pytest.raises(FileExistsError):
            Memory(path, writable=True)
    data = path.read_text(encoding='utf-8').replace('Koral', 'Zefir')
    path.write_text(data, encoding='utf-8')
    with pytest.raises(ValueError, match='Corrupt'):
        Memory(path, writable=True)
    assert not path.with_suffix('.lock').exists()
    assert 'Zefir' in path.read_text(encoding='utf-8')


@pytest.mark.parametrize('kwargs', [{'valid_to': 1}, {'recorded': True}, {'policy': 'magic'}])
def test_invalid_source_metadata(kwargs):
    args = dict(id='a', scope='test', text='Text.', recorded=1)
    args.update(kwargs)
    with pytest.raises(ValueError):
        Source(**args)
