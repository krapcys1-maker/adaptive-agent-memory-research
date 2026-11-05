"""Boundary and forged-evidence checks; no inference or network access."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/local_model_upgrade_v1.py'
spec = importlib.util.spec_from_file_location('local_upgrade', SOURCE)
U = importlib.util.module_from_spec(spec)
spec.loader.exec_module(U)


@pytest.mark.parametrize('content', ['not json', '{}', '[]', 'null', '{"answer":1}',
                                     '{"answer":"ok","judge":"pass"}'])
def test_invalid_structure_is_not_safe_abstention(content):
    assert U.parse(content, U.SCHEMA) is None


def test_empty_answer_and_schema_minimum_are_distinct():
    assert U.parse('{"answer":""}', U.SCHEMA) == ''
    schema = copy.deepcopy(U.SCHEMA)
    schema['properties']['answer']['minLength'] = 1
    assert U.parse('{"answer":""}', schema) is None


def test_no_memory_removes_all_evidence_preserves_exact_question_and_system():
    query = {'query_id': 'opaque', 'question': 'Where now?', 'asked_on_day': 6}
    request = {'messages': [{'role': 'system', 'content': 'Original role policy'},
                           {'role': 'user', 'content': '[E0] old\nQuestion: inside a note\nQuestion: Where now?'}],
               'format': U.SCHEMA}
    original = copy.deepcopy(request)
    n, m = U.h1_pair('Q0', query, request, ['E0'])
    assert n['messages'][1]['content'] == '\nQuestion: Where now?'
    assert n['messages'][0] == m['messages'][0] == request['messages'][0]
    assert m['messages'] == request['messages'] and n['shown_ids'] == [] and m['shown_ids'] == ['E0']
    assert request == original


@pytest.mark.parametrize('mutation', ['gold', 'wrong_question'])
def test_h1_rejects_gold_or_parent_packet_mismatch(mutation):
    q = {'query_id': 'opaque', 'question': 'Where?', 'asked_on_day': 1}
    req = {'messages': [{'role': 'system', 'content': 'x'},
                       {'role': 'user', 'content': 'notes\nQuestion: Where?'}], 'format': U.SCHEMA}
    if mutation == 'gold':
        q['answer_contains'] = ['secret']
    else:
        req['messages'][1]['content'] += ' changed'
    with pytest.raises(ValueError):
        U.h1_pair('Q0', q, req, [])


def test_native_controls_match_arms_and_preserve_package_specific_penalty():
    p = {'messages': [{'role': 'user', 'content': 'x'}], 'schema': U.SCHEMA}
    model = {'model': 'candidate', 'presence_penalty': 1.5}
    req = U.request_for(model, p, {'values': [True, False], 'default': True})
    assert req['think'] is False and req['options']['num_ctx'] == 8192
    assert req['options']['presence_penalty'] == 1.5 and req['options']['seed'] == 7
    assert 'think' not in U.request_for(model, p, None)
    with pytest.raises(ValueError, match='nonthinking'):
        U.request_for(model, p, {'values': ['high'], 'default': 'high'})


def test_do_not_store_hidden_thinking():
    saved = U.clean_response({'message': {'role': 'assistant', 'content': 'final',
                                         'thinking': 'PRIVATE TRACE', 'tool_calls': ['unused']},
                              'eval_count': 4, 'context': ['private']})
    assert saved['unexpected_thinking_present'] is True
    assert saved['message'] == {'role': 'assistant', 'content': 'final'}
    assert 'PRIVATE TRACE' not in json.dumps(saved) and 'context' not in saved


def test_returned_model_is_not_silently_substituted():
    U.response_identity({'model': 'owned'}, 'owned')
    with pytest.raises(ValueError):
        U.response_identity({'model': 'fallback'}, 'owned')


@pytest.mark.parametrize('models', [[{'name': 'other', 'digest': 'same'}],
                                   [{'name': 'owned', 'digest': 'different'}]])
def test_refuse_other_or_changed_loaded_model(models):
    with pytest.raises(ValueError):
        U.loaded_guard(models, 'owned', 'same')
    U.loaded_guard([], 'owned', 'same')


def test_cap_covers_entire_phase_and_duplicate_attempts_are_rejected(tmp_path, monkeypatch):
    p = tmp_path / 'ledger'
    U.append(p, {'key': 'one'})
    monkeypatch.setattr(U, 'CAP', 3)
    assert len(U.check_ledger(p, 2)) == 1
    with pytest.raises(ValueError):
        U.check_ledger(p, 3)
    U.append(p, {'key': 'one'})
    with pytest.raises(ValueError):
        U.check_ledger(p)


def test_new_artifacts_and_worker_lock_never_overwrite_existing(tmp_path):
    p = tmp_path / 'original.json'
    U.write_new(p, {'original': True})
    with pytest.raises(FileExistsError):
        U.write_new(p, {'original': False})
    assert json.loads(p.read_text()) == {'original': True}
    with U.worker_lease(tmp_path):
        with pytest.raises(FileExistsError):
            with U.worker_lease(tmp_path):
                pass
        assert (tmp_path / 'worker.lock').exists()
    assert not (tmp_path / 'worker.lock').exists()


def fixture_raw(tmp_path, monkeypatch):
    monkeypatch.setattr(U, 'CALLS', 1)
    model = {'model': 'owned', 'digest': 'same', 'presence_penalty': 0}
    packet = {'key': 'h1-Q0-M', 'messages': [{'role': 'user', 'content': 'unchanged'}], 'schema': U.SCHEMA}
    U.append(tmp_path / 'packets.jsonl', packet)
    U.write_new(tmp_path / 'preparation.json', {'packet_sha256': U.sha(tmp_path / 'packets.jsonl'), 'protected_inputs': []})
    out = tmp_path / 'baseline14'
    U.write_new(out / 'manifest.json', {'spec': model, 'thinking_control': None,
                                      'ledger_bytes_before': 0, 'ledger_sha256_before': None})
    request = U.request_for(model, packet, None)
    key = 'baseline14:h1-Q0-M'
    U.append(out / 'attempts.jsonl', {'key': key, 'request': request, 'request_sha256': U.digest(request)})
    U.append(out / 'responses.jsonl', {'key': key, 'error': None, 'native':
             {'model': 'owned', 'message': {'content': '{"answer":"final"}'}, 'done': True, 'done_reason': 'stop'}})
    U.append(out / 'answers.jsonl', {'key': key, 'answer': 'final', 'json_valid': True, 'normal_stop': True})
    U.append(tmp_path / 'local-ledger.jsonl', {'key': key, 'digest': 'same', 'request_sha256': U.digest(request)})
    return out


def bind_freeze(out):
    value = {'complete': True, 'files_sha256': {p.name: U.sha(p) for p in out.iterdir() if p.name != 'raw-freeze.json'}}
    (out / 'raw-freeze.json').write_text(json.dumps(value), encoding='utf-8')


def test_native_replay_accepts_valid_fixture(tmp_path, monkeypatch):
    out = fixture_raw(tmp_path, monkeypatch)
    bind_freeze(out)
    assert U.replay(tmp_path, 'baseline14')['requests_replayed'] == 1


@pytest.mark.parametrize('forgery', ['answer', 'request', 'reservation', 'native_status', 'response_model'])
def test_replay_rejects_forgery_even_with_rebound_file_hashes(tmp_path, monkeypatch, forgery):
    out = fixture_raw(tmp_path, monkeypatch)
    filename = {'answer': 'answers.jsonl', 'request': 'attempts.jsonl',
                'reservation': '../local-ledger.jsonl', 'native_status': 'responses.jsonl',
                'response_model': 'responses.jsonl'}[forgery]
    p = out / filename
    value = U.rows(p)[0]
    if forgery == 'answer':
        value['answer'] = 'forged'
    elif forgery == 'request':
        value['request']['options']['num_ctx'] = 999999
        value['request_sha256'] = U.digest(value['request'])
    elif forgery == 'reservation':
        value['digest'] = 'another-model'
    elif forgery == 'native_status':
        value['native']['done_reason'] = 'length'
    else:
        value['native']['model'] = 'fallback'
    p.write_text(json.dumps(value) + '\n', encoding='utf-8')
    bind_freeze(out)
    with pytest.raises(ValueError):
        U.replay(tmp_path, 'baseline14')
