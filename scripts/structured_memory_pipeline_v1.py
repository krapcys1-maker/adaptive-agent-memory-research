"""Gold-blind capture and query execution, then a separately invoked scorer.

New development candidate for issue #47. Never imports the frozen domain adapter
or changes the kernel, persona or production agent. Raw artifacts stay external.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import flash_reader_client_v1 as F
import nie_reader_pilot as P
import reader_model_compare_v1 as R
from tools.structured_memory_v1 import (Memory, Source, extraction_messages,
                                        planning_messages)

DATA = ROOT/'data/lab/structured-memory-v1'


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity():
    files = [Path(__file__), ROOT/'tools/structured_memory_v1.py', DATA/'PLAN.md', DATA/'config.json',
             Path(F.__file__), Path(P.__file__), Path(R.__file__)]
    return {'git_head': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
            'clean_tree': not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),
            'sha256': {p.relative_to(ROOT).as_posix(): file_sha(p) for p in files}}


def client(backend, output, ledger):
    config = json.loads((DATA/'config.json').read_text(encoding='utf-8'))
    if backend == 'flash':
        if ledger is None:
            raise ValueError('Explicit new-task cumulative API ledger required.')
        return F.FlashReader(config, output, ledger, output.name)
    config = R.local_config(config)
    config['options']['num_predict'] = 512
    return P.LocalReader(config, output)


def ask(reader, backend, name, messages):
    row = (reader.ask(name, messages, 7, max_tokens=512) if backend == 'flash' else
           reader.ask(name, messages, 7))
    try:
        return json.loads(row['text'])
    except (TypeError, json.JSONDecodeError):
        return {'invalid_json': True}


def controls(reader, backend, output):
    config = json.loads((R.REFERENCE/'manifest.json').read_text(encoding='utf-8'))['config']
    for i, token in enumerate(('cobalt-47', 'juniper-83', 'marble-29')):
        messages = P.reader_messages(config, 'control_value', 'What is the control_value?',
                                    {'context': f'The control_value is {token}.'}, [])
        value = ask(reader, backend, f'control-{i}', messages)
        correct = value.get('value') == token
        P.append(output/'controls.jsonl', {'key': f'control-{i}', 'correct': correct})
        if not correct:
            raise ValueError('Transport control failed; no primary execution or hidden retry.')


def start(output, backend, inputs):
    output.mkdir(parents=True, exist_ok=False)
    source = identity()
    if not source['clean_tree']:
        raise ValueError('Commit source before model execution.')
    P.write(output/'manifest.json', {'source': source, 'backend': backend,
            'started_utc': datetime.now(timezone.utc).isoformat(),
            'input_sha256': {str(p.resolve()): file_sha(p) for p in inputs}})


def finish(reader, output):
    P.write(output/'finished.json', reader.finish())
    files = ['manifest.json', 'finished.json', 'attempts.jsonl', 'responses.jsonl',
             'controls.jsonl', 'captures.jsonl', 'answers.jsonl']
    P.write(output/'raw-freeze.json', {'files_sha256': {name: file_sha(output/name)
            for name in files if (output/name).exists()},
            'source': identity(), 'scoring_has_not_run': True})


def ingest(archive, store, output, backend, ledger, scope, policy):
    start(output, backend, [archive])
    rows = P.read_rows(archive)
    if not rows or any(set(row) != {'id','text','ordinal'} for row in rows):
        raise ValueError('Archive must contain only source id, text and source order, never gold.')
    if len({r['id'] for r in rows}) != len(rows) or [r['ordinal'] for r in rows] != sorted(set(r['ordinal'] for r in rows)):
        raise ValueError('Unique source IDs and strictly increasing source order required.')
    reader = client(backend, output, ledger)
    counts = Counter()
    try:
        P.write(output/'preflight.json', reader.preflight())
        controls(reader, backend, output)
        with Memory(store, writable=True) as memory:
            if memory.sources:
                raise ValueError('Fresh canonical store required; no mixing or resume.')
            # Capture the entire raw archive before attempting semantic extraction.
            for row in rows:
                memory.add_source(Source(row['id'], scope, row['text'], row['ordinal'], policy=policy))
            for row in rows:
                cached = memory.cached(row['id'])
                if cached is not None:
                    proposal = {'claims': [{k: v for k, v in asdict(cached).items() if k != 'source'}]}
                    method, learn = 'template', False
                else:
                    if counts['model'] >= 80:
                        raise RuntimeError('Unmatched-source model cap reached; raw archive remains recoverable.')
                    proposal = ask(reader, backend, 'extract-'+row['id'], extraction_messages(row['text'], memory.catalog))
                    method = 'model'
                    learn = proposal.get('learn_template') is True
                counts[method] += 1
                try:
                    claims = memory.extract(row['id'], proposal, method=method, learn=learn)
                    counts['claims'] += len(claims)
                    counts['empty'] += not claims
                    status = 'accepted'
                except ValueError as exc:
                    status = 'quarantined'
                    counts['quarantined'] += 1
                    P.append(output/'rejections.jsonl', {'id': row['id'], 'reason': str(exc)})
                P.append(output/'captures.jsonl', {'id': row['id'], 'method': method, 'status': status})
            P.write(output/'capture-summary.json', {'counts': dict(counts), 'sources': len(memory.sources),
                'claims': len(memory.claims), 'templates': len(memory.templates), 'catalog': sorted(memory.catalog),
                'store_sha256': file_sha(store), 'scope': scope, 'policy': policy})
        finish(reader, output)
    finally:
        reader.release()


def answer(questions, store, output, backend, ledger, scope, valid_at, known_at):
    start(output, backend, [questions, store])
    rows = P.read_rows(questions)
    if not rows or any(set(r) != {'id','question'} for r in rows) or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Unique questions without gold, family or expected evidence are required.')
    reader = client(backend, output, ledger)
    before = file_sha(store)
    try:
        P.write(output/'preflight.json', reader.preflight())
        controls(reader, backend, output)
        with Memory(store) as memory:
            catalog = memory.visible_catalog(scope, known_at=known_at)
            for row in rows:
                anchors = memory.anchors(scope, row['question'], known_at=known_at)
                plan = ask(reader, backend, 'plan-'+row['id'], planning_messages(row['question'], anchors, catalog))
                start_time = time.monotonic()
                result = memory.execute(scope, row['question'], plan, valid_at=valid_at, known_at=known_at)
                P.append(output/'answers.jsonl', {'id': row['id'], 'plan': plan, 'result': result,
                    'execution_seconds': time.monotonic()-start_time})
        if before != file_sha(store):
            raise RuntimeError('Query mutated canonical memory.')
        finish(reader, output)
    finally:
        reader.release()


def score(output, gold, destination):
    freeze = json.loads((output/'raw-freeze.json').read_text(encoding='utf-8'))
    for name, sha in freeze['files_sha256'].items():
        if file_sha(output/name) != sha:
            raise ValueError('Frozen raw output changed.')
    rows, expected = P.read_rows(output/'answers.jsonl'), P.read_rows(gold)
    by_id = {r['id']: r for r in rows}
    if len(by_id) != len(rows) or set(by_id) != {r['id'] for r in expected}:
        raise ValueError('Incomplete/duplicate answers; no partial credit aggregate.')
    result = []
    for row in expected:
        answer = by_id[row['id']]['result']
        value = answer.get('value')
        correct = isinstance(value, str) and value.casefold().strip() in {v.casefold().strip() for v in row['answers']}
        result.append({'id': row['id'], 'correct': correct, 'status': answer['status'],
                       'hops': len(by_id[row['id']]['plan'].get('steps', []))})
    P.write(destination, {'n': len(result), 'exact': sum(r['correct'] for r in result),
            'statuses': dict(Counter(r['status'] for r in result)), 'records': result,
            'raw_freeze_sha256': file_sha(output/'raw-freeze.json'), 'gold_sha256': file_sha(gold),
            'claim': 'Development only. System-computed graph values, not raw reader answers or a leaderboard replication.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('ingest', 'answer'):
        p = sub.add_parser(name)
        p.add_argument('--store', type=Path, required=True)
        p.add_argument('--output', type=Path, required=True)
        p.add_argument('--backend', choices=['local14b','flash'], required=True)
        p.add_argument('--ledger', type=Path)
        p.add_argument('--scope', required=True)
        if name == 'ingest':
            p.add_argument('--archive', type=Path, required=True)
            p.add_argument('--policy', choices=['conservative','ordered_single'], default='conservative')
        else:
            p.add_argument('--questions', type=Path, required=True)
            p.add_argument('--valid-at', type=int, required=True)
            p.add_argument('--known-at', type=int, required=True)
    p = sub.add_parser('score')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--gold', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop('command')
    globals()[command](**args)


if __name__ == '__main__':
    main()
