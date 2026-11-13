"""Isolated, counted local model-package comparison. No paid client or model judge.

Historical readers, evaluators, gold and ledgers are read-only inputs. Prepare
copies their packets; run requires committed source and refuses overwrite/retry.
The new ledger counts attempts before transport, including failures and controls.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/lab/local-model-upgrade-v1'
API = 'http://127.0.0.1:11434'
CAP = 2000
CALLS = 655
SCHEMA = {'type': 'object', 'properties': {'answer': {'type': 'string'}},
          'required': ['answer'], 'additionalProperties': False}
COMMON = {'temperature': 0, 'seed': 7, 'num_ctx': 8192, 'num_predict': 512,
          'top_p': 1, 'top_k': 0, 'repeat_penalty': 1, 'frequency_penalty': 0}


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def append(path, value):
    with Path(path).open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')
        stream.flush()
        # Keep a durable reservation before submitting inference.
        import os
        os.fsync(stream.fileno())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def api(path, body=None, timeout=20):
    request = urllib.request.Request(API + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def parse(content, schema):
    try:
        obj = json.loads(content)
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict) or set(obj) != {'answer'} or not isinstance(obj['answer'], str):
        return None
    if len(obj['answer']) < schema['properties']['answer'].get('minLength', 0):
        return None
    return obj['answer']


def check_ledger(path, extra=0):
    found = rows(path) if Path(path).exists() else []
    keys = [r['key'] for r in found]
    if len(keys) != len(set(keys)) or len(keys) + extra > CAP:
        raise ValueError('Duplicate reservations or entire phase does not fit cap2000.')
    return found


def checked_history(preparation):
    for entry in preparation['protected_inputs']:
        if sha(entry['path']) != entry['sha256']:
            raise ValueError('Historical input or ledger changed: ' + entry['name'])


def h1_pair(qid, query, request, shown):
    if set(query) != {'query_id', 'question', 'asked_on_day'}:
        raise ValueError('H1 questions must be gold-free.')
    suffix = '\nQuestion: ' + query['question']
    original = deepcopy(request['messages'])
    if len(original) != 2 or original[1]['role'] != 'user' or not original[1]['content'].endswith(suffix):
        raise ValueError('Parent packet does not end with the unchanged question.')
    absent = deepcopy(original)
    absent[1]['content'] = suffix
    return [{'dataset': 'h1', 'id': qid, 'query_id': query['query_id'], 'arm': arm,
             'phase': 'primary', 'key': f'h1-{qid}-{arm}', 'schema': deepcopy(request['format']),
             'messages': message, 'shown_ids': list(shown) if arm == 'M' else []}
            for arm, message in [('N', absent), ('M', original)]]


def prepare(raw, historical, beam):
    raw = Path(raw)
    raw.mkdir(parents=True, exist_ok=False)
    historical, beam = Path(historical), Path(beam)
    parent = historical / 'h1-v5-valid-reader'
    freeze = json.loads((parent / 'raw-freeze.json').read_text())
    for name, expected in freeze['files_sha256'].items():
        if sha(parent / name) != expected:
            raise ValueError('Frozen H1 reader has changed.')
    bf = json.loads((beam / 'reader-evidence-v1/raw-freeze.json').read_text())
    for name, expected in bf['files_sha256'].items():
        if sha(beam / 'reader-evidence-v1' / name) != expected:
            raise ValueError('Frozen BEAM reader has changed.')
    request_of = {r['key']: r['request'] for r in rows(parent / 'attempts.jsonl')}
    shown_of = {r['id']: r['shown_ids'] for r in rows(parent / 'answers.jsonl') if r['arm'] == 'chains'}
    corpus = ROOT / 'data/lab/corpus-h1/valid-b'
    qs = rows(corpus / 'reveal/queries.jsonl')
    if len(qs) != 84 or set(shown_of) != {f'Q{i:06d}' for i in range(84)}:
        raise ValueError('Full valid84 roster required.')
    controls = [('marker', 'Return the exact answer UPGRADE-CONTROL.', 'UPGRADE-CONTROL'),
                ('arithmetic', 'What is 2 + 2? Return the digit only.', '4'),
                ('absence', 'No history is supplied. What is my private vault code? Answer exactly I do not know.', 'I do not know')]
    packets = [{'dataset': 'control', 'id': name, 'arm': 'control', 'phase': 'control',
                'key': 'control-' + name, 'schema': SCHEMA, 'expected': expected,
                'messages': [{'role': 'system', 'content': 'Return JSON {"answer":"concise answer"}. Follow the user request.'},
                             {'role': 'user', 'content': question}], 'shown_ids': []}
               for name, question, expected in controls]
    h1 = []
    for i, query in enumerate(qs):
        qid = f'Q{i:06d}'
        pair = h1_pair(qid, query, request_of['read-chains-' + qid], shown_of[qid])
        h1.extend(pair)
        packets.extend(pair if i % 2 == 0 else pair[::-1])
    bp = rows(beam / 'reader-evidence-v1/packets.jsonl')
    bp = [p for p in bp if p['type'] == 'primary' and p['arm'] in ('N', 'B')]
    ids = list(dict.fromkeys(p['id'] for p in bp))
    if len(ids) != 200 or len(bp) != 400:
        raise ValueError('Full BEAM200 N/B roster required.')
    by_key = {(p['id'], p['arm']): p for p in bp}
    for i, qid in enumerate(ids):
        pair = []
        for old_arm, arm in [('N', 'N'), ('B', 'M')]:
            p = by_key[qid, old_arm]
            pair.append({'dataset': 'beam', 'id': qid, 'conversation_id': p['conversation_id'],
                         'arm': arm, 'phase': 'primary', 'key': f'beam-{qid}-{arm}',
                         'schema': p['schema'], 'messages': p['messages'], 'aliases': p['aliases'],
                         'shown_ids': p['shown_ids']})
        packets.extend(pair if i % 2 == 0 else pair[::-1])
    for packet in h1:
        if packet['arm'] == 'M':
            repeat = deepcopy(packet)
            repeat.update(phase='repeat', key='repeat-' + packet['key'])
            packets.append(repeat)
    if len(packets) != CALLS or len({p['key'] for p in packets}) != CALLS:
        raise ValueError('Incomplete/duplicate packet matrix.')
    for packet in packets:
        append(raw / 'packets.jsonl', packet)
    protected = {
        'h1-ledger': historical / 'h1-local-ledger.jsonl',
        'api-ledger': historical / 'api-ledger.jsonl',
        'beam-ledger': beam / 'beam-local-ledger-v1.jsonl',
        'h1-parent-freeze': parent / 'raw-freeze.json',
        'beam-parent-freeze': beam / 'reader-evidence-v1/raw-freeze.json',
        'beam-packets': beam / 'reader-evidence-v1/packets.jsonl',
        'h1-history': corpus / 'prefix/history.jsonl',
        'h1-gold': corpus / 'reveal/gold.jsonl',
        'h1-questions': corpus / 'reveal/queries.jsonl',
        'h1-scorer': ROOT / 'scripts/run_corpus_h1_reader.py',
    }
    prep = {'schema': 'local-model-upgrade-v1', 'cases': {'h1': 84, 'beam': 200},
            'primary_per_model': 568, 'repeat_per_model': 84, 'controls_per_model': 3,
            'calls_per_model': CALLS, 'task_cap': CAP, 'maximum_models': 3,
            'packet_sha256': sha(raw / 'packets.jsonl'), 'config_sha256': sha(DATA / 'config.json'),
            'protected_inputs': [{'name': n, 'path': str(p), 'sha256': sha(p)} for n, p in protected.items()],
            'gold_values_read_during_preparation': False,
            'past_counts': {'pr105_local': 4361, 'pr105_paid_attempts': 463,
                            'h1': 3262, 'beam': 605},
            'messages_max_utf8_bytes': max(len(json.dumps(p['messages'], ensure_ascii=False).encode()) for p in packets)}
    write_new(raw / 'preparation.json', prep)
    public = deepcopy(prep)
    for entry in public['protected_inputs']:
        entry.pop('path')
    write_new(DATA / 'preparation.json', public)
    return public


def request_for(spec, packet, thinking):
    options = {**COMMON, 'presence_penalty': spec['presence_penalty']}
    # Native Gemma draft is part of the practical model package, not a new judge.
    if 'draft_num_predict' in spec:
        options['draft_num_predict'] = spec['draft_num_predict']
    request = {'model': spec['model'], 'messages': packet['messages'], 'stream': False,
               'format': packet['schema'], 'keep_alive': '10m', 'options': options}
    if thinking and False in thinking.get('values', []):
        request['think'] = False
    elif thinking and thinking.get('default') not in (None, False):
        raise ValueError('Cannot establish nonthinking mode; do not silently change treatment.')
    return request


def clean_response(native):
    """Retain final output/usage, never hidden reasoning traces."""
    keep = ('model', 'created_at', 'done', 'done_reason', 'total_duration', 'load_duration',
            'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration', 'error')
    saved = {k: native[k] for k in keep if k in native}
    message = native.get('message', {})
    saved['message'] = {k: message[k] for k in ('role', 'content') if k in message}
    saved['unexpected_thinking_present'] = bool(message.get('thinking'))
    return saved


def loaded_guard(models, model, expected_digest):
    for loaded in models:
        if loaded.get('name', loaded.get('model')) != model or loaded.get('digest') != expected_digest:
            raise ValueError('Another model/task has taken the Ollama worker.')


def response_identity(native, model):
    if native.get('model') != model:
        raise ValueError('Native response model differs from the requested subject.')


def client_guard():
    # Best-effort detection, not an exclusive lease over arbitrary external apps.
    try:
        import os
        import psutil
        other = [c.pid for c in psutil.net_connections(kind='tcp')
                 if c.raddr and c.raddr.port == 11434 and c.status == 'ESTABLISHED'
                 and c.pid not in (None, os.getpid())]
        if other:
            raise ValueError('Another process is connected to Ollama: ' + str(sorted(set(other))))
    except ImportError:
        pass


class Sampler:
    def __init__(self, path):
        self.path = path
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)

    def loop(self):
        while not self.stop.is_set():
            sample = {'monotonic': time.monotonic(), 'utc': time.time()}
            try:
                import psutil
                mem = psutil.virtual_memory()
                sample.update(ram_total=mem.total, ram_available=mem.available, ram_used=mem.used)
                sample['ollama_rss'] = sum(p.info['memory_info'].rss for p in
                    psutil.process_iter(['name', 'memory_info'])
                    if 'ollama' in (p.info['name'] or '').lower() and p.info['memory_info'])
            except Exception as exc:
                sample['ram_error'] = type(exc).__name__
            try:
                output = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used,memory.total,utilization.gpu',
                    '--format=csv,noheader,nounits'], text=True, timeout=5)
                vals = [float(v.strip()) for v in output.splitlines()[0].split(',')]
                sample.update(gpu_used_mib=vals[0], gpu_total_mib=vals[1], gpu_utilization=vals[2])
            except Exception as exc:
                sample['gpu_error'] = type(exc).__name__
            append(self.path, sample)
            self.stop.wait(2.5)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join(timeout=7)


@contextmanager
def worker_lease(raw):
    """Exclusive local runner lease. Never guess away another worker's lock."""
    import os
    lock = Path(raw) / 'worker.lock'
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    try:
        yield
    finally:
        lock.unlink()


def run(raw, profile):
    with worker_lease(raw):
        return run_owned(raw, profile)


def run_owned(raw, profile):
    raw = Path(raw)
    if git('status', '--porcelain'):
        raise ValueError('Commit code/config/preparation before generation.')
    prep = json.loads((raw / 'preparation.json').read_text())
    if sha(raw / 'packets.jsonl') != prep['packet_sha256'] or sha(DATA / 'config.json') != prep['config_sha256']:
        raise ValueError('Prepared inputs drifted.')
    checked_history(prep)
    config = json.loads((DATA / 'config.json').read_text())
    spec = deepcopy(config['models'][profile])
    tags = api('/api/tags')
    installed = next(m for m in tags['models'] if m['name'] == spec['model'])
    if spec.get('digest'):
        if installed['digest'] != spec['digest']:
            raise ValueError('Pinned digest changed.')
    elif not installed['digest'].startswith(spec['expected_manifest_prefix']):
        raise ValueError('Official manifest prefix changed.')
    spec['digest'] = installed['digest']
    if api('/api/ps')['models']:
        raise ValueError('Ollama must be idle before taking a worker.')
    client_guard()
    output = raw / profile
    output.mkdir(exist_ok=False)
    show = api('/api/show', {'model': spec['model'], 'verbose': True})
    packets = rows(raw / 'packets.jsonl')
    if len(packets) != CALLS:
        raise ValueError('Entire matrix required.')
    ledger = raw / 'local-ledger.jsonl'
    prior = check_ledger(ledger, CALLS)
    source = {'head': git('rev-parse', 'HEAD'), 'clean_tree': True,
              'files': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in
                        [Path(__file__), DATA / 'PLAN.md', DATA / 'config.json', DATA / 'preparation.json']}}
    write_new(output / 'manifest.json', {'source': source, 'spec': spec, 'details': show,
        'installed': installed, 'python': platform.python_version(), 'ollama_version': api('/api/version'),
        'preparation_sha256': sha(raw / 'preparation.json'), 'ledger_before': len(prior),
        'ledger_sha256_before': sha(ledger) if ledger.exists() else None,
        'ledger_bytes_before': ledger.stat().st_size if ledger.exists() else 0,
        'thinking_control': show.get('thinking'), 'common_options': COMMON, 'no_retry': True})
    write_new(output / 'preflight.json', {'active': api('/api/ps'), 'started_utc': time.time()})
    started = time.monotonic()
    count = 0
    success = False
    failure = None
    walls = []
    timed_out = False
    try:
        with Sampler(output / 'resources.jsonl'):
            for packet in packets:
                if time.monotonic() - started > config['model_deadline_seconds']:
                    raise TimeoutError('Model wall-clock cap reached.')
                loaded = api('/api/ps')['models']
                loaded_guard(loaded, spec['model'], spec['digest'])
                client_guard()
                if len(check_ledger(ledger)) >= CAP:
                    raise ValueError('Task call cap reached.')
                request = request_for(spec, packet, show.get('thinking'))
                key = profile + ':' + packet['key']
                if any(r['key'] == key for r in check_ledger(ledger)):
                    raise ValueError('No duplicate attempt or retry.')
                request_sha = digest(request)
                append(output / 'attempts.jsonl', {'key': key, 'packet_key': packet['key'],
                       'request_sha256': request_sha, 'request': request})
                append(ledger, {'key': key, 'model': spec['model'], 'digest': spec['digest'],
                       'request_sha256': request_sha, 'utc': time.time()})
                count += 1
                t0 = time.monotonic()
                native = None
                error = None
                try:
                    native = api('/api/chat', request, timeout=config['request_timeout_seconds'])
                    if 'error' in native:
                        error = str(native['error'])
                    else:
                        response_identity(native, spec['model'])
                except Exception as exc:
                    error = type(exc).__name__ + ': ' + str(exc)
                    timed_out = isinstance(exc, (TimeoutError,)) or 'timed out' in str(exc).lower()
                wall = time.monotonic() - t0
                walls.append(wall)
                saved = clean_response(native) if native else {}
                append(output / 'responses.jsonl', {'key': key, 'native': saved, 'error': error, 'wall_seconds': wall})
                content = saved.get('message', {}).get('content', '')
                answer = parse(content, packet['schema']) if not error else None
                normal = saved.get('done') is True and saved.get('done_reason') == 'stop'
                append(output / 'answers.jsonl', {'key': key, 'packet_key': packet['key'],
                       'phase': packet['phase'], 'dataset': packet['dataset'], 'id': packet['id'],
                       'arm': packet['arm'], 'answer': answer, 'json_valid': answer is not None,
                       'normal_stop': normal, 'error': error, 'wall_seconds': wall})
                append(output / 'residency.jsonl', {'key': key, 'active': api('/api/ps'), 'utc': time.time()})
                if packet['phase'] == 'control' and (error or not normal or saved.get('unexpected_thinking_present') or answer is None or
                        answer.strip().lower() != packet['expected'].lower()):
                    raise ValueError('Transport control failed; no retry and no primary continuation.')
                if saved.get('unexpected_thinking_present'):
                    raise ValueError('Unexpected thinking mode; stop affected model without a retry.')
                if timed_out:
                    raise TimeoutError('Native request timed out; stop affected worker to avoid overlapping calls.')
                if count % 20 == 0 or count == CALLS:
                    print(json.dumps({'profile': profile, 'attempts': count, 'planned': CALLS,
                          'elapsed_seconds': round(time.monotonic() - started, 2),
                          'recent_median_wall': round(statistics.median(walls[-20:]), 3)}), flush=True)
            checked_history(prep)
            final = next(m for m in api('/api/tags')['models'] if m['name'] == spec['model'])
            if final['digest'] != spec['digest']:
                raise ValueError('Model digest drifted during generation.')
            success = True
    except Exception as exc:
        failure = type(exc).__name__ + ': ' + str(exc)
    finally:
        unload = {'attempted': False, 'reason': 'worker not safely owned or request timed out'}
        if not timed_out:
            try:
                client_guard()
                loaded_guard(api('/api/ps')['models'], spec['model'], spec['digest'])
                unload = {'attempted': True, 'response': api('/api/generate',
                          {'model': spec['model'], 'keep_alive': 0})}
                unload['active_after'] = api('/api/ps')
            except Exception as exc:
                unload = {'attempted': False, 'error': type(exc).__name__ + ': ' + str(exc)}
        write_new(output / 'finished.json', {'complete': success, 'attempts': count,
                  'planned': CALLS, 'failure': failure, 'elapsed_seconds': time.monotonic() - started,
                  'unload': unload, 'ledger_after': len(check_ledger(ledger))})
        names = ['manifest.json', 'preflight.json', 'attempts.jsonl', 'responses.jsonl',
                 'answers.jsonl', 'resources.jsonl', 'residency.jsonl', 'finished.json']
        write_new(output / 'raw-freeze.json', {'complete': success, 'source': source,
                  'files_sha256': {n: sha(output / n) for n in names if (output / n).exists()},
                  'packet_sha256': prep['packet_sha256'], 'model_digest': spec['digest'],
                  'scoring_has_not_run': True})
    print(json.dumps({'profile': profile, 'complete': success, 'attempts': count, 'failure': failure}), flush=True)
    if not success:
        raise RuntimeError(failure)


def replay(raw, profile):
    raw = Path(raw)
    output = raw / profile
    freeze = json.loads((output / 'raw-freeze.json').read_text())
    for name, expected in freeze['files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Raw evidence drift: ' + name)
    prep = json.loads((raw / 'preparation.json').read_text())
    if sha(raw / 'packets.jsonl') != prep['packet_sha256']:
        raise ValueError('Packet drift.')
    checked_history(prep)
    manifest = json.loads((output / 'manifest.json').read_text())
    prefix = (raw / 'local-ledger.jsonl').read_bytes()[:manifest['ledger_bytes_before']]
    if manifest['ledger_bytes_before'] and hashlib.sha256(prefix).hexdigest() != manifest['ledger_sha256_before']:
        raise ValueError('Earlier task ledger prefix changed.')
    packets = rows(raw / 'packets.jsonl')
    requests, responses, answers = [rows(output / n) for n in ['attempts.jsonl', 'responses.jsonl', 'answers.jsonl']]
    if not freeze['complete'] or not (len(requests) == len(responses) == len(answers) == len(packets) == CALLS):
        raise ValueError('Incomplete matrix; no complete-result score.')
    ledger = {r['key']: r for r in check_ledger(raw / 'local-ledger.jsonl')}
    for p, req, response, answer in zip(packets, requests, responses, answers, strict=True):
        expected = request_for(manifest['spec'], p, manifest['thinking_control'])
        key = profile + ':' + p['key']
        if req['key'] != key or response['key'] != key or answer['key'] != key:
            raise ValueError('Request/response/packet identity mismatch.')
        if req['request'] != expected or req['request_sha256'] != digest(expected):
            raise ValueError('Native request differs from frozen protocol.')
        if ledger[key]['request_sha256'] != digest(expected) or ledger[key]['digest'] != manifest['spec']['digest']:
            raise ValueError('Reservation differs from native request/model.')
        actual = parse(response['native'].get('message', {}).get('content', ''), p['schema']) if not response['error'] else None
        if not response['error']:
            response_identity(response['native'], manifest['spec']['model'])
        normal = response['native'].get('done') is True and response['native'].get('done_reason') == 'stop'
        if actual != answer['answer'] or normal != answer['normal_stop'] or (actual is not None) != answer['json_valid']:
            raise ValueError('Derived answer/status differs from native response.')
    return {'profile': profile, 'requests_replayed': CALLS, 'failures': 0,
            'raw_freeze_sha256': sha(output / 'raw-freeze.json'), 'model_digest': manifest['spec']['digest']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'run', 'replay'])
    parser.add_argument('--raw', required=True, type=Path)
    parser.add_argument('--historical', type=Path)
    parser.add_argument('--beam', type=Path)
    parser.add_argument('--profile', choices=['baseline14', 'qwen35_9', 'gemma4_12'])
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.raw, args.historical, args.beam)
    elif args.command == 'run':
        result = run(args.raw, args.profile)
    else:
        result = replay(args.raw, args.profile)
    if result:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
