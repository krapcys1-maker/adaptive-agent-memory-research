"""Reject forged source/spec/reference bindings, including rebound raw hashes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/reviews/local_model_upgrade_review_v2.py'
spec = importlib.util.spec_from_file_location('upgrade_review_v2', SOURCE)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
U = R.U


def bind(out):
    value = {'complete': True, 'files_sha256': {p.name: U.sha(p) for p in out.iterdir()
             if p.name != 'raw-freeze.json'}}
    (out / 'raw-freeze.json').write_text(json.dumps(value), encoding='utf-8')


def fixture(tmp_path, monkeypatch):
    raw = tmp_path / 'task/v2'
    raw.mkdir(parents=True)
    monkeypatch.setattr(U, 'CALLS', 1)
    model = {'model': 'baseline', 'digest': 'original-digest', 'presence_penalty': 0}
    paths = ['scripts/local_model_upgrade_v2.py', 'data/lab/local-model-upgrade-v2/PLAN.md',
             'data/lab/local-model-upgrade-v2/config.json', 'data/lab/local-model-upgrade-v2/preparation.json']
    blobs = {p: ('committed:' + p).encode() for p in paths}
    blobs[paths[2]] = json.dumps({'models': {'baseline14': model}}).encode()
    monkeypatch.setattr(R, 'committed', lambda path, head='HEAD': blobs[path])
    (raw.parent / 'baseline14').mkdir()
    for i in range(3):
        old = {'key': 'baseline14:control-' + str(i)}
        U.append(raw.parent / 'baseline14/attempts.jsonl', old)
        U.append(raw.parent / 'local-ledger.jsonl', old)
    prefix_bytes = (raw.parent / 'local-ledger.jsonl').stat().st_size
    prefix_sha = U.sha(raw.parent / 'local-ledger.jsonl')
    old_dir = raw.parent / 'baseline14'
    U.write_new(old_dir / 'raw-freeze.json', {'complete': False,
        'files_sha256': {'attempts.jsonl': U.sha(old_dir / 'attempts.jsonl')}})
    original_failure = {'raw_freeze_sha256': U.sha(old_dir / 'raw-freeze.json'),
        'task_ledger_prefix_bytes': prefix_bytes, 'task_ledger_prefix_sha256': prefix_sha}
    packet = {'key': 'synthetic', 'messages': [{'role': 'user', 'content': 'No benchmark gold'}], 'schema': U.SCHEMA}
    U.append(raw / 'packets.jsonl', packet)
    U.write_new(raw / 'preparation.json', {'packet_sha256': U.sha(raw / 'packets.jsonl'), 'protected_inputs': []})
    out = raw / 'baseline14'
    U.write_new(out / 'manifest.json', {'spec': model, 'thinking_control': None, 'common_options': U.COMMON,
        'ledger_bytes_before': prefix_bytes, 'ledger_sha256_before': prefix_sha,
        'source': {'head': R.SOURCE, 'clean_tree': True,
                   'files': {p: hashlib.sha256(b).hexdigest() for p, b in blobs.items()}}})
    blobs['data/lab/local-model-upgrade-v1/failure.json'] = json.dumps(original_failure).encode()
    req = U.request_for(model, packet, None)
    key = 'v2:baseline14:synthetic'
    U.append(out / 'attempts.jsonl', {'key': key, 'request': req, 'request_sha256': U.digest(req)})
    U.append(out / 'responses.jsonl', {'key': key, 'error': None, 'native':
             {'model': 'baseline', 'message': {'content': '{"answer":"ok"}'}, 'done': True, 'done_reason': 'stop'}})
    U.append(out / 'answers.jsonl', {'key': key, 'answer': 'ok', 'json_valid': True, 'normal_stop': True})
    U.append(raw.parent / 'local-ledger.jsonl', {'key': key, 'digest': 'original-digest', 'request_sha256': U.digest(req)})
    bind(out)
    return raw, out


def test_full_new_and_retained_old_ledger_union(tmp_path, monkeypatch):
    raw, out = fixture(tmp_path, monkeypatch)
    assert R.audit(raw, ['baseline14'])['actual_attempts'] == 4


@pytest.mark.parametrize('forgery', ['missing_source', 'forged_source', 'changed_penalty', 'unregistered_call'])
def test_native_audit_rejects_rebound_metadata_forgery(tmp_path, monkeypatch, forgery):
    raw, out = fixture(tmp_path, monkeypatch)
    manifest = json.loads((out / 'manifest.json').read_text())
    if forgery == 'missing_source':
        manifest['source']['files'].pop('data/lab/local-model-upgrade-v2/PLAN.md')
    elif forgery == 'forged_source':
        manifest['source']['files']['scripts/local_model_upgrade_v2.py'] = 'forged-sha'
    elif forgery == 'changed_penalty':
        manifest['spec']['presence_penalty'] = 9
        row = U.rows(out / 'attempts.jsonl')[0]
        row['request']['options']['presence_penalty'] = 9
        row['request_sha256'] = U.digest(row['request'])
        (out / 'attempts.jsonl').write_text(json.dumps(row) + '\n')
        ledger = U.rows(raw.parent / 'local-ledger.jsonl')
        ledger[-1]['request_sha256'] = row['request_sha256']
        # Preserve the exact already-bound first3reservation bytes.
        p = raw.parent / 'local-ledger.jsonl'
        original_prefix = p.read_bytes()[:manifest['ledger_bytes_before']]
        p.write_bytes(original_prefix + (json.dumps(ledger[-1]) + '\n').encode())
    else:
        U.append(raw.parent / 'local-ledger.jsonl', {'key': 'unauthorized-extra'})
    (out / 'manifest.json').write_text(json.dumps(manifest))
    bind(out)
    with pytest.raises(ValueError):
        R.audit(raw, ['baseline14'])


def test_uncommitted_or_mismatched_complete_receipt_blocks_reference_join(monkeypatch):
    monkeypatch.setattr(R, 'public_raw_receipt', lambda *a: {'native_verified': True})
    monkeypatch.setattr(R, 'committed', lambda *a: b'{"native_verified":false}')
    with pytest.raises(ValueError, match='Commit the complete'):
        R.require_committed_raw(Path('unused'), ['baseline14'])


def test_forged_prior_reference_manifest_is_rejected_before_opening_labels(tmp_path, monkeypatch):
    monkeypatch.setattr(R, 'require_committed_raw', lambda *a: {})
    actual_tool = Path(R.__file__).read_bytes()
    monkeypatch.setattr(R, 'committed', lambda path, head='HEAD': actual_tool
                        if path.endswith('local_model_upgrade_review_v2.py')
                        else b'{"review_packet_manifest_sha256":"original-unmodified-manifest"}')
    prior = tmp_path / 'prior'
    prior.mkdir()
    (prior / 'manifest.json').write_text('{"labels_sha256":"forged"}')
    with pytest.raises(ValueError, match='published result'):
        R.prepare_review(Path('unused'), ['baseline14'], prior, tmp_path / 'missing-labels', tmp_path / 'review')


def test_same_answer_other_question_is_never_a_reused_verdict():
    assert R.B.candidate_id('case1', 'UNKNOWN') != R.B.candidate_id('case2', 'UNKNOWN')


def test_incomplete_authored_verdicts_cannot_be_scored(tmp_path):
    U.append(tmp_path / 'packet.jsonl', {'id': 'case', 'candidates': [{'candidate_id': 'new', 'text': 'text'}]})
    U.append(tmp_path / 'reused-verdicts.jsonl', {'id': 'case', 'reference_status': 'usable',
             'reference_note': '', 'candidates': []})
    with pytest.raises(ValueError, match='Every deduplicated'):
        R.combine_verdicts(tmp_path)
