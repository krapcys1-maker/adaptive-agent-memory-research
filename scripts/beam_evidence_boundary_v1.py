"""Evaluator-only source-ID coverage and gold-free source-context packaging.

No inference, expected-answer matching or semantic sufficiency estimator.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from tools import source_context_v1 as C
import beam_reader_evidence_v1 as B
import prepare_beam_windows_v1 as A
W = C.W
DATA = ROOT / 'data/lab/beam-evidence-boundary-v1'
LIMIT_SECONDS = 600
LIMIT_BYTES = 256_000_000
STATES = ('not_in_source_archive', 'not_retrieved', 'retrieved_not_shown', 'shown_partial', 'shown_full')


def load(path): return json.loads(path.read_text(encoding='utf-8'))


def raw_id(value):
    if type(value) is int and value >= 0: return value
    if isinstance(value, str) and value.isascii() and value.isdigit(): return int(value)
    raise ValueError('Explicit nonnegative integer source ID required; no guessed references.')


def reference_ids(value):
    if value is None: return []
    if isinstance(value, dict): items = value.values()
    elif isinstance(value, list): items = value
    else: return [raw_id(value)]
    return sorted({i for v in items for i in reference_ids(v)})


def covered_chars(spans, length):
    merged = []; total = 0
    for a, b in sorted(spans):
        if type(a) is not int or type(b) is not int or not 0 <= a < b <= length:
            raise ValueError('Invalid exact character coverage interval.')
        if merged and a <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b)
        else: merged.append([a, b])
    for a, b in merged: total += b - a
    return total


def classify(target, candidates, shown):
    if target is None: return 'not_in_source_archive', 0
    sid = target['id']
    if not any(w.source_id == sid for w in candidates): return 'not_retrieved', 0
    spans = [(w.char_start, w.char_end) for w in shown if w.source_id == sid]
    if not spans: return 'retrieved_not_shown', 0
    chars = covered_chars(spans, target['chars'])
    return ('shown_full' if chars == target['chars'] else 'shown_partial'), chars


def summarize(cases):
    annotated = [r for r in cases if r['annotation_state'] == 'nonempty']
    counts = Counter(k for r in cases for k, n in r['target_states'].items() for _ in range(n))
    return {'cases': len(cases), 'nonempty_annotation_cases': len(annotated),
        'no_annotation_cases': sum(r['annotation_state'] == 'missing' for r in cases),
        'empty_annotation_cases': sum(r['annotation_state'] == 'empty' for r in cases),
        'declared_targets': sum(r['declared_targets'] for r in cases), 'target_states': {k: counts[k] for k in STATES},
        'any_candidate_target_cases': sum(r['candidate_targets'] > 0 for r in annotated),
        'all_candidate_target_cases': sum(r['candidate_targets'] == r['declared_targets'] for r in annotated),
        'any_shown_target_cases': sum(r['shown_targets'] > 0 for r in annotated),
        'all_shown_target_cases': sum(r['shown_targets'] == r['declared_targets'] for r in annotated),
        'all_shown_full_source_cases': sum(r['target_states']['shown_full'] == r['declared_targets'] for r in annotated),
        'all_new_context_target_cases': sum(r['context_targets'] == r['declared_targets'] for r in annotated),
        'old_shown_windows': sum(r['old_windows'] for r in cases), 'new_shown_windows': sum(r['new_windows'] for r in cases),
        'context_empty_cases': sum(r['new_windows'] == 0 for r in cases)}


def inputs(prepared, access, reader, review, legacy, beam_ledger):
    paths = [prepared / n for n in ['manifest.json', 'reader/history.jsonl', 'reader/questions.jsonl',
        'audit/message-provenance.jsonl', 'evaluation/labels.jsonl']]
    paths += [access / n for n in ['manifest.json', 'query-packets.jsonl']]
    paths += [reader / n for n in ['raw-freeze.json', 'packets.jsonl', 'answers.jsonl', 'preparation.json']]
    paths += [review / n for n in ['manifest.json', 'verdicts.jsonl', 'mapping.jsonl']]
    paths += [legacy / 'h1-local-ledger.jsonl', legacy / 'api-ledger.jsonl', beam_ledger,
              ROOT / 'data/lab/beam-reader-evidence-v1/score.json']
    manifest = load(access / 'manifest.json')
    paths += [access / r['file'] for r in manifest['indexes']]
    return {str(p): A.sha(p) for p in paths}


def validate_inputs(prepared, access, reader, review):
    public = ROOT / 'data/lab/beam-reader-evidence-v1'
    if (reader / 'raw-freeze.json').read_bytes() != (public / 'raw-freeze.json').read_bytes():
        raise ValueError('The original committed605call freeze changed.')
    freeze = load(reader / 'raw-freeze.json')
    for name, h in freeze['files_sha256'].items():
        if Path(name).name != name or A.sha(reader / name) != h: raise ValueError('Frozen reader artifact differs.')
    fmt = load(prepared / 'manifest.json')
    for rel in ['reader/history.jsonl', 'reader/questions.jsonl', 'audit/message-provenance.jsonl', 'evaluation/labels.jsonl']:
        if A.sha(prepared / rel) != fmt['output_files_sha256'][rel]: raise ValueError('Prepared format/evaluator sidecar changed.')
    access_meta = load(access / 'manifest.json'); prep = load(reader / 'preparation.json')
    if A.sha(access / 'manifest.json') != prep['access_manifest_sha256'] or A.sha(access / 'query-packets.jsonl') != prep['access_packet_sha256']:
        raise ValueError('Frozen lexical access differs.')
    for row in access_meta['indexes']:
        if A.sha(access / row['file']) != row['sha256']: raise ValueError('Frozen source snapshot changed.')
    score = load(public / 'score.json'); rm = load(review / 'manifest.json')
    if A.sha(review / 'verdicts.jsonl') != score['verdicts_sha256'] or A.sha(review / 'mapping.jsonl') != rm['mapping_sha256']:
        raise ValueError('Original authored decisions/mapping changed.')
    if A.sha(prepared / 'evaluation/labels.jsonl') != prep['labels_sha256']: raise ValueError('Original annotations changed.')


def analyze(prepared, access, reader, review, *, started):
    archive = {}; ids = {}; messages = 0; role_counts = Counter()
    # This evaluator mapping never enters the context builder or its retrieval.
    with (prepared / 'reader/history.jsonl').open(encoding='utf-8') as history, (prepared / 'audit/message-provenance.jsonl').open(encoding='utf-8') as provenance:
        for h, a in zip(history, provenance, strict=True):
            row = json.loads(h); meta = json.loads(a)
            if row['id'] != meta['id']: raise ValueError('Source/metadata alignment differs.')
            rid = raw_id(meta['metadata']['id']); key = (row['conversation_id'], rid)
            if key in archive or row['id'] in ids: raise ValueError('Ambiguous duplicate original source ID.')
            info = {'id': row['id'], 'chars': len(row['text']), 'role': row['role']}
            archive[key] = info; ids[row['id']] = info; messages += 1; role_counts[row['role']] += 1
    if messages != 187734: raise ValueError('Full source archive required.')
    refs = list(A.rows(prepared / 'evaluation/labels.jsonl')); queries = list(A.rows(access / 'query-packets.jsonl'))
    if len(refs) != 200 or len(queries) != 200 or [r['id'] for r in refs] != [r['id'] for r in queries]:
        raise ValueError('Full ordered200case roster required.')
    primaries = [r for r in A.rows(reader / 'packets.jsonl') if r['type'] == 'primary' and r['arm'] == 'B']
    by_case = {r['id']: r for r in primaries}
    if len(by_case) != 200: raise ValueError('Full unique original Bmatrix required.')
    cases = []; packets = []; target_roles = Counter(); new_budgets = []; omission_reasons = Counter(); loaded = {}
    verdicts = {r['id']: r for r in A.rows(review / 'verdicts.jsonl')}
    maps = {r['id']: r['mapping'] for r in A.rows(review / 'mapping.jsonl')}
    cross_tabs = Counter(); target_details = []; known_frame = None
    index_meta = load(access / 'manifest.json')['indexes']
    with ExitStack() as stack:
        dbs = {r['scope']: stack.enter_context(W.Snapshot(access / r['file'], scope=r['scope'], known_at=r['known_at'])) for r in index_meta}
        for ref, q in zip(refs, queries, strict=True):
            if time.monotonic() - started > LIMIT_SECONDS: raise TimeoutError('Offline diagnostic deadline exceeded.')
            case_id = q['id']; scope = q['conversation_id']; row = by_case[case_id]
            if ref['conversation_id'] != scope or row['conversation_id'] != scope: raise ValueError('Case scope changed.')
            candidates = [W.Window(**w) for w in q['candidate_windows']]; windows = {w.id: w for w in candidates}
            shown = [windows[w] for w in row['shown_ids']]
            # Reconstruct the frozen Bselection before packaging a new variant.
            replay = B.paired_packets(q)['B']
            if row['messages'] != replay['messages'] or row['aliases'] != replay['aliases'] or row['shown_ids'] != replay['shown_ids']:
                raise ValueError('Original matched Bselection differs.')
            pairs = []
            for w in shown:
                if w.source_id not in loaded:
                    raw = dbs[scope].connection.execute('SELECT body FROM sources WHERE id=?', (w.source_id,)).fetchone()
                    if raw is None: raise ValueError('Missing full selected source.')
                    loaded[w.source_id] = W.Source(**json.loads(raw[0]))
                pairs.append((loaded[w.source_id], w))
            # No annotations, rubric, target IDs or authored outcomes are passed.
            packet = C.render_packet(q['question'], pairs, scope=scope, known_at=q['known_at'], system=B.B_SYSTEM)
            packets.append({'id': case_id, 'conversation_id': scope, 'packet': packet})
            new_budgets.append(max(packet['message_bytes'].values()))
            omission_reasons.update(x['reason'] for x in packet['omissions'])
            context_windows = [windows[w] for w in packet['shown_ids']]
            value = ref['annotations'].get('source_chat_ids'); targets = reference_ids(value)
            annotation_state = 'missing' if value is None else ('nonempty' if targets else 'empty')
            states = Counter(); candidate_count = 0; shown_count = 0; context_count = 0; chars_shown = 0; chars_available = 0
            for rid in targets:
                target = archive.get((scope, rid)); state, chars = classify(target, candidates, shown)
                cstate, _ = classify(target, candidates, context_windows)
                states[state] += 1; chars_shown += chars
                candidate_count += state not in {'not_in_source_archive', 'not_retrieved'}
                shown_count += state in {'shown_partial', 'shown_full'}
                context_count += cstate in {'shown_partial', 'shown_full'}
                if target: target_roles[target['role']] += 1; chars_available += target['chars']
                target_details.append({'case_id': case_id, 'original_source_id': rid, 'source': target['id'] if target else None,
                    'state': state, 'context_state': cstate, 'shown_chars': chars,
                    'source_chars': target['chars'] if target else None})
            case = {'id': case_id, 'conversation_id': scope, 'ability': ref['ability'], 'annotation_state': annotation_state,
                'declared_targets': len(targets), 'target_states': {k: states[k] for k in STATES},
                'candidate_targets': candidate_count, 'shown_targets': shown_count, 'context_targets': context_count,
                'resolved_target_chars': chars_available, 'shown_target_chars': chars_shown,
                'old_windows': len(shown), 'new_windows': len(packet['shown_ids']),
                'new_max_message_bytes': max(packet['message_bytes'].values()), 'literal_dependency_bytes': packet['literal_dependency_bytes_shown']}
            cases.append(case)
            v = verdicts[case_id]; vm = {x['candidate_id']: x for x in v['candidates']}; bm = maps[case_id]['B']
            passed = bm['valid_output'] and v['reference_status'] == 'usable' and vm[bm['candidate_id']]['pass'] is True
            stage = 'no_annotation' if not targets else ('all_shown' if shown_count == len(targets) else ('some_shown' if shown_count else 'none_shown'))
            cross_tabs[(stage, 'Bpass' if passed else 'Bfail')] += 1
            if case_id == 'BEAM10M-7-Q0000':
                needed = 'BEAM10M-7-M007239'
                notes = json.loads(packet['messages'][1]['content'])['history']['evidence']
                old_note = next(e for e in json.loads(row['messages'][1]['content'])['history']['evidence'] if e['source'] == needed)
                selected = next((e for e in notes if e['source'] == needed), None)
                known_frame = {'case_id': case_id, 'source': needed, 'old_text_has_heading': '### Example Scenarios' in old_note['text'],
                    'new_same_source_shown': selected is not None,
                    'literal_heading_retained': bool(selected and any('### Example Scenarios' in d['text'] for d in selected['source_context']['dependencies'])),
                    'semantic_event_validated': False}
    total = summarize(cases)
    return cases, packets, target_details, {'complete_source_messages': messages, 'original_source_roles': dict(role_counts),
        'overall': total, 'declared_target_roles': dict(target_roles),
        'by_ability': {k: summarize([r for r in cases if r['ability'] == k]) for k in sorted({r['ability'] for r in cases})},
        'by_history': {k: summarize([r for r in cases if r['conversation_id'] == k]) for k in sorted({r['conversation_id'] for r in cases})},
        'original_Bpass_annotation_stage': {stage: {outcome: cross_tabs[(stage, outcome)] for outcome in ['Bpass', 'Bfail']} for stage in ['all_shown', 'some_shown', 'none_shown', 'no_annotation']},
        'context_packet_max_message_bytes': max(new_budgets), 'context_omission_reasons': dict(omission_reasons),
        'context_changed_packet_cases': sum(r['old_windows'] != r['new_windows'] for r in cases),
        'literal_dependency_text_bytes': sum(r['literal_dependency_bytes'] for r in cases),
        'full_selected_sources_loaded': len(loaded), 'full_selected_source_bytes_loaded': sum(len(s.text.encode()) for s in loaded.values()),
        'known_example_frame': known_frame, 'new_model_calls': 0, 'semantic_evidence_completeness_measured': False,
        'claim': 'Post-freeze annotation-source coverage proxy and structural context only; no semantic recall ceiling, model score or adoption.'}


def run(prepared, access, reader, review, legacy, beam_ledger, output):
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(): raise ValueError('Freeze code and plan before corpus processing.')
    if output.resolve().is_relative_to(ROOT) or output.exists(): raise ValueError('New exclusive private output directory required.')
    started = time.monotonic(); before = inputs(prepared, access, reader, review, legacy, beam_ledger)
    validate_inputs(prepared, access, reader, review)
    source = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'clean_tree': True,
        'sha256': {p.relative_to(ROOT).as_posix(): A.sha(p) for p in [Path(__file__), Path(C.__file__), Path(W.__file__), Path(B.__file__), DATA / 'PLAN.md']}}
    output.mkdir(parents=True, exist_ok=False); A.write(output / 'started.json', {'source': source, 'input_sha256': before})
    try:
        cases, packets, details, result = analyze(prepared, access, reader, review, started=started)
        for name, rows in [('cases.jsonl', cases), ('context-packets.jsonl', packets), ('target-details.jsonl', details)]:
            for row in rows: A.append(output / name, row)
        after = inputs(prepared, access, reader, review, legacy, beam_ledger)
        if before != after: raise ValueError('Original inputs/snapshots or cumulative ledgers changed.')
        total_bytes = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        elapsed = time.monotonic() - started
        if elapsed > LIMIT_SECONDS or total_bytes > LIMIT_BYTES: raise RuntimeError('Offline resource cap exceeded; preserve partial outputs.')
        manifest = {'source': source, 'input_sha256': before, 'input_hashes_unchanged': True,
            'case_count': len(cases), 'packet_count': len(packets), 'targets_count': len(details),
            'output_sha256': {p.name: A.sha(p) for p in sorted(output.iterdir()) if p.is_file()},
            'elapsed_seconds': elapsed, 'output_bytes_before_manifest': total_bytes, 'model_calls': 0,
            'result': result}
        A.write(output / 'manifest.json', manifest)
        print(json.dumps({'head': source['head'], 'elapsed_seconds': elapsed, 'output_bytes': total_bytes,
                          'overall': result['overall'], 'known_example_frame': result['known_example_frame']}, indent=2))
    except BaseException as e:
        A.write(output / 'failure.json', {'error_type': type(e).__name__, 'error': str(e), 'model_calls': 0}); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['prepared', 'access', 'reader', 'review', 'legacy', 'beam-ledger', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    run(**vars(p.parse_args()))
