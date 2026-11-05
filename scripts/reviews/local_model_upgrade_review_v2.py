"""Post-freeze upgrade audit and authored-review preparation; never a model judge.

Reuses the unchanged historical H1 scorer and BEAM grouping/validation/outcome
functions. New verdicts must be supplied by Codex; no semantic auto-grading.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT)]
import local_model_upgrade_v2 as U
import run_corpus_h1_reader as H

spec = importlib.util.spec_from_file_location('prior_beam_authored_review',
    ROOT / 'scripts/reviews/beam_reader_authored_review_v1.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
DATA = ROOT / 'data/lab/local-model-upgrade-v2'
SOURCE = 'a71765fa9a31008e0535f75208b9f813950861b3'
PROFILES = ('baseline14', 'qwen35_9', 'gemma4_12')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def committed(path, head='HEAD'):
    return subprocess.check_output(['git', 'show', head + ':' + path], cwd=ROOT)


def audit_retained_partial(raw, profile, config, ledger):
    """Replay an aborted prefix without converting it into a complete result."""
    output = raw / profile
    freeze = load(output / 'raw-freeze.json')
    finished = load(output / 'finished.json')
    if freeze['complete'] or finished['complete']:
        raise ValueError('Expected explicitly incomplete retained phase.')
    for name, expected in freeze['files_sha256'].items():
        if U.sha(output / name) != expected:
            raise ValueError('Incomplete evidence drifted.')
    m = load(output / 'manifest.json')
    expected = dict(config['models'][profile])
    expected['digest'] = m['spec']['digest']
    if m['spec'] != expected or not m['spec']['digest'].startswith(expected['expected_manifest_prefix']):
        raise ValueError('Incomplete model config drifted.')
    if m['source']['head'] != SOURCE or not m['source']['clean_tree']:
        raise ValueError('Incomplete source identity differs.')
    for path, expected_sha in m['source']['files'].items():
        if hashlib.sha256(committed(path, SOURCE)).hexdigest() != expected_sha:
            raise ValueError('Incomplete phase source changed.')
    attempts, responses, answers = [U.rows(output / n) for n in ('attempts.jsonl', 'responses.jsonl', 'answers.jsonl')]
    count = len(attempts)
    if not (0 < count < U.CALLS and count == len(responses) == len(answers) == finished['attempts']):
        raise ValueError('Incomplete prefix counts differ.')
    by_key = {r['key']: r for r in ledger}
    packets = U.rows(raw / 'packets.jsonl')[:count]
    for p, a, r, answer in zip(packets, attempts, responses, answers, strict=True):
        key = 'v2:' + profile + ':' + p['key']
        request = U.request_for(m['spec'], p, m['thinking_control'])
        if (a['key'] != key or r['key'] != key or answer['key'] != key or a['request'] != request
                or a['request_sha256'] != U.digest(request) or by_key[key]['request_sha256'] != U.digest(request)
                or by_key[key]['digest'] != m['spec']['digest']):
            raise ValueError('Incomplete prefix request/reservation binding differs.')
        if not r['error']:
            U.response_identity(r['native'], m['spec']['model'])
        parsed = U.parse(r['native'].get('message', {}).get('content', ''), p['schema']) if not r['error'] else None
        normal = r['native'].get('done') is True and r['native'].get('done_reason') == 'stop'
        if parsed != answer['answer'] or normal != answer['normal_stop'] or (parsed is not None) != answer['json_valid']:
            raise ValueError('Incomplete native parse/status differs.')
    return {'profile': profile, 'complete': False, 'attempts_replayed': count, 'planned': U.CALLS,
        'failure': finished['failure'], 'raw_freeze_sha256': U.sha(output / 'raw-freeze.json'),
        'no_primary_full_matrix_score': True}, {a['key'] for a in attempts}


def audit(raw, profiles):
    """No reference/gold values are opened by this native evidence audit."""
    config = json.loads(committed('data/lab/local-model-upgrade-v2/config.json', SOURCE))
    result = []
    expected_keys = set()
    for profile in profiles:
        replay = U.replay(raw, profile)
        manifest = load(raw / profile / 'manifest.json')
        if manifest['source']['head'] != SOURCE:
            raise ValueError('Unexpected executed source head.')
        expected_files = {'scripts/local_model_upgrade_v2.py',
            'data/lab/local-model-upgrade-v2/PLAN.md', 'data/lab/local-model-upgrade-v2/config.json',
            'data/lab/local-model-upgrade-v2/preparation.json'}
        if set(manifest['source']['files']) != expected_files or not manifest['source']['clean_tree']:
            raise ValueError('Incomplete executed-source binding.')
        for name, sha in manifest['source']['files'].items():
            if hashlib.sha256(committed(name, SOURCE)).hexdigest() != sha:
                raise ValueError('Native manifest source is not the committed experiment.')
        expected = dict(config['models'][profile])
        if 'digest' not in expected:
            if not manifest['spec']['digest'].startswith(expected['expected_manifest_prefix']):
                raise ValueError('Conditional native model digest differs.')
            expected['digest'] = manifest['spec']['digest']
        if manifest['spec'] != expected or manifest['common_options'] != U.COMMON:
            raise ValueError('Native model/sampling manifest differs from prior config.')
        expected_keys.update(r['key'] for r in U.rows(raw / profile / 'attempts.jsonl'))
        result.append(replay)
    ledger = U.check_ledger(raw.parent / 'local-ledger.jsonl')
    incomplete = []
    for profile in PROFILES:
        if profile not in profiles and (raw / profile / 'raw-freeze.json').exists():
            partial, keys = audit_retained_partial(raw, profile, config, ledger)
            incomplete.append(partial)
            expected_keys.update(keys)
    original_failure = json.loads(committed('data/lab/local-model-upgrade-v1/failure.json', SOURCE))
    old_dir = raw.parent / 'baseline14'
    old_freeze = load(old_dir / 'raw-freeze.json')
    if U.sha(old_dir / 'raw-freeze.json') != original_failure['raw_freeze_sha256']:
        raise ValueError('Failed V1 raw freeze changed.')
    for name, expected_sha in old_freeze['files_sha256'].items():
        if U.sha(old_dir / name) != expected_sha:
            raise ValueError('Retained failed V1 evidence changed.')
    ledger_prefix = (raw.parent / 'local-ledger.jsonl').read_bytes()[:original_failure['task_ledger_prefix_bytes']]
    if hashlib.sha256(ledger_prefix).hexdigest() != original_failure['task_ledger_prefix_sha256']:
        raise ValueError('Failed V1 reservation prefix changed.')
    old = {r['key'] for r in U.rows(raw.parent / 'baseline14/attempts.jsonl')}
    if len(old) != 3 or {r['key'] for r in ledger} != expected_keys | old:
        raise ValueError('Task ledger does not exactly equal retained V1 plus full new matrices.')
    return {'schema': 'local-upgrade-native-audit-v2', 'profiles': result,
            'retained_incomplete_profiles': incomplete,
            'source_head': SOURCE, 'retained_v1_attempts': 3, 'actual_attempts': len(ledger),
            'task_cap': U.CAP, 'paid_attempts': 0, 'failures': 0,
            'task_ledger_sha256': U.sha(raw.parent / 'local-ledger.jsonl')}


def public_raw_receipt(raw, profiles):
    report = audit(raw, profiles)
    report['raw_freezes'] = {p: load(raw / p / 'raw-freeze.json') for p in profiles}
    report['preparation_sha256'] = U.sha(raw / 'preparation.json')
    report['packet_sha256'] = U.sha(raw / 'packets.jsonl')
    return report


def require_committed_raw(raw, profiles):
    expected = public_raw_receipt(raw, profiles)
    recorded = json.loads(committed('data/lab/local-model-upgrade-v2/raw-freezes.json'))
    if recorded != expected:
        raise ValueError('Commit the complete native raw receipt before any reference join.')
    return expected


def prepare_review(raw, profiles, prior, labels, destination):
    checked = require_committed_raw(raw, profiles)
    if committed(Path(__file__).relative_to(ROOT).as_posix()) != Path(__file__).read_bytes():
        raise ValueError('Commit the review tool before opening references.')
    prior_manifest = load(prior / 'manifest.json')
    original_score = json.loads(committed('data/lab/beam-reader-evidence-v1/score.json', SOURCE))
    if U.sha(prior / 'manifest.json') != original_score['review_packet_manifest_sha256']:
        raise ValueError('Prior reference/packet manifest differs from the published result.')
    if U.sha(labels) != prior_manifest['labels_sha256']:
        raise ValueError('Original reference identity differs.')
    if U.sha(prior / 'packet.jsonl') != prior_manifest['packet_sha256']:
        raise ValueError('Prior authored question/reference/answer packets drifted.')
    if U.sha(prior / 'verdicts.jsonl') != original_score['verdicts_sha256']:
        raise ValueError('Prior verdict identity differs from published result.')
    old_packets = U.rows(prior / 'packet.jsonl')
    old_verdicts = B.validate_verdicts(old_packets, U.rows(prior / 'verdicts.jsonl'))
    old_by_id = {p['id']: p for p in old_packets}
    old_reference = {p['id']: p for p in U.rows(prior / 'verdicts.jsonl')}
    references = U.rows(labels)
    native_packets = [p for p in U.rows(raw / 'packets.jsonl') if p['dataset'] == 'beam']
    questions = {p['id']: json.loads(p['messages'][1]['content'])['question'] for p in native_packets}
    answers = {profile: {(a['id'], a['arm']): a for a in U.rows(raw / profile / 'answers.jsonl')
                       if a['dataset'] == 'beam' and a['phase'] == 'primary'} for profile in profiles}
    if len(references) != 200 or len(questions) != 200:
        raise ValueError('Full BEAM200 required.')
    destination.mkdir(parents=True, exist_ok=False)
    reused = pending = 0
    for ref in references:
        qid = ref['id']
        old = old_by_id[qid]
        if old['reference_annotations'] != ref['annotations'] or old['question'] != questions[qid]:
            raise ValueError('Reference/question differs; do not reuse any old verdict.')
        targets = {}
        for profile in profiles:
            for arm in ('N', 'M'):
                a = answers[profile][qid, arm]
                valid = a['json_valid'] and a['normal_stop'] and not a['error']
                targets[profile + ':' + arm] = {'valid_output': valid, 'delivered_answer': a['answer']}
        candidates, mapping = B.group_answers(qid, targets)
        packet = {k: old[k] for k in ('id', 'conversation_id', 'ability', 'question', 'reference_annotations')}
        packet['candidates'] = candidates
        U.append(destination / 'packet.jsonl', packet)
        U.append(destination / 'mapping.jsonl', {'id': qid, 'mapping': mapping})
        old_text = {c['candidate_id']: c['text'] for c in old['candidates']}
        reused_candidates = []
        new_candidates = []
        for c in candidates:
            cid = c['candidate_id']
            if old_text.get(cid) == c['text'] and cid in old_verdicts[qid]['candidates']:
                reused_candidates.append(old_verdicts[qid]['candidates'][cid])
                U.append(destination / 'provenance.jsonl', {'id': qid, 'candidate_id': cid,
                    'source': 'exact_same_question_reference_and_answer_prior_authored_verdict',
                    'prior_verdicts_sha256': U.sha(prior / 'verdicts.jsonl')})
                reused += 1
            else:
                new_candidates.append(c)
                pending += 1
        U.append(destination / 'reused-verdicts.jsonl', {'id': qid,
            'reference_status': old_reference[qid]['reference_status'],
            'reference_note': old_reference[qid]['reference_note'], 'candidates': reused_candidates})
        if new_candidates:
            U.append(destination / 'pending.jsonl', {**packet, 'candidates': new_candidates})
    U.write_new(destination / 'manifest.json', {'raw_receipt_sha256': U.sha(DATA / 'raw-freezes.json'),
        'labels_sha256': U.sha(labels), 'cases': 200, 'profiles': profiles,
        'exact_prior_verdicts_reused': reused, 'new_candidate_verdicts_required': pending,
        'packet_sha256': U.sha(destination / 'packet.jsonl'),
        'mapping_sha256': U.sha(destination / 'mapping.jsonl'),
        'reused_verdicts_sha256': U.sha(destination / 'reused-verdicts.jsonl'),
        'source_head_at_reference_join': U.git('rev-parse', 'HEAD'),
        'review_tool_sha256': U.sha(Path(__file__)),
        'reviewer': 'Codex authored; model/arm masked; design known; not independent or fully blind'})
    return {'cases': 200, 'exact_prior_reused': reused, 'new_candidate_verdicts_required': pending}


def combine_verdicts(review):
    packets = U.rows(review / 'packet.jsonl')
    reused = {r['id']: r for r in U.rows(review / 'reused-verdicts.jsonl')}
    supplied = U.rows(review / 'new-verdicts.jsonl') if (review / 'new-verdicts.jsonl').exists() else []
    seen = set()
    for row in supplied:
        qid = row['id']
        c = {k: row[k] for k in ('candidate_id', 'pass', 'material_contradiction', 'reason')}
        key = qid, c['candidate_id']
        if key in seen or any(x['candidate_id'] == c['candidate_id'] for x in reused[qid]['candidates']):
            raise ValueError('Duplicate authored/reused verdict.')
        seen.add(key)
        reused[qid]['candidates'].append(c)
    ordered = [reused[p['id']] for p in packets]
    return B.validate_verdicts(packets, ordered), ordered


def h1_scores(raw, profiles):
    # Call only after require_committed_raw, exactly as for BEAM reference join.
    base = ROOT / 'data/lab/corpus-h1/valid-b'
    gold = {g['query_id']: g for g in U.rows(base / 'reveal/gold.jsonl')}
    packets = {(p['id'], p['arm']): p for p in U.rows(raw / 'packets.jsonl')
               if p['dataset'] == 'h1' and p['phase'] == 'primary'}
    source_id = {r['event_id']: f'E{i:06d}' for i, r in enumerate(U.rows(base / 'prefix/history.jsonl'))}
    result = {}
    detail = []
    for profile in profiles:
        native_of = {r['key']: r['native'] for r in U.rows(raw / profile / 'responses.jsonl')}
        for row in U.rows(raw / profile / 'answers.jsonl'):
            if row['dataset'] != 'h1':
                continue
            p = packets[row['id'], row['arm']]
            g = gold[p['query_id']]
            text = row['answer'] if row['answer'] is not None else native_of[row['key']].get('message', {}).get('content', '')
            score = H.score(text, g)
            eligible = row['json_valid'] and row['normal_stop'] and not row['error']
            detail.append({'profile': profile, 'id': row['id'], 'arm': row['arm'], 'phase': row['phase'],
                'family': g['case_id'].rsplit('-', 1)[0], 'answered': bool(score['answered'] and eligible),
                'leaked': bool(score['leaked']), 'clean': bool(score['answered'] and eligible and not score['leaked']),
                'target_source_shown': source_id.get(g['gold_event_id']) in p['shown_ids'],
                'forbidden_source_shown': source_id.get(g.get('forbidden_event_id')) in p['shown_ids']})
        result[profile] = {}
        for phase, arm in [('primary', 'N'), ('primary', 'M'), ('repeat', 'M')]:
            selected = [r for r in detail if r['profile'] == profile and r['phase'] == phase and r['arm'] == arm]
            if len(selected) != 84:
                raise ValueError('Full H1 roster required in every scored condition.')
            result[profile][phase + ':' + arm] = {'cases': 84, **{key: sum(r[key] for r in selected)
                for key in ('answered', 'leaked', 'clean', 'target_source_shown', 'forbidden_source_shown')},
                'by_family': {family: {'cases': sum(r['family'] == family for r in selected),
                    **{key: sum(r[key] for r in selected if r['family'] == family) for key in ('answered', 'leaked', 'clean')}}
                    for family in sorted({r['family'] for r in selected})}}
    return result, detail


def technical_summary(raw, profiles):
    result = {}
    for profile in profiles:
        answer_rows = U.rows(raw / profile / 'answers.jsonl')
        native = {r['key']: r for r in U.rows(raw / profile / 'responses.jsonl')}

        def stats(selected):
            selected_native = [native[r['key']] for r in selected]
            tps = [r['native']['eval_count'] / (r['native']['eval_duration'] / 1e9)
                   for r in selected_native if r['native'].get('eval_duration', 0) > 0]
            return {'calls': len(selected), 'median_wall_seconds': statistics.median(r['wall_seconds'] for r in selected),
                'total_wall_seconds': sum(r['wall_seconds'] for r in selected),
                'median_generation_tps': statistics.median(tps) if tps else None,
                'prompt_tokens': sum(r['native'].get('prompt_eval_count', 0) for r in selected_native),
                'generated_tokens': sum(r['native'].get('eval_count', 0) for r in selected_native),
                'prompt_tokens_max': max(r['native'].get('prompt_eval_count', 0) for r in selected_native),
                'native_errors': sum(bool(r['error']) for r in selected),
                'invalid_json': sum(not r['json_valid'] for r in selected),
                'abnormal_stops': sum(not r['normal_stop'] for r in selected)}
        per_group = {dataset + ':' + arm: stats([r for r in answer_rows
                     if r['phase'] == 'primary' and r['dataset'] == dataset and r['arm'] == arm])
                     for dataset in ('h1', 'beam') for arm in ('N', 'M')}
        primary = stats([r for r in answer_rows if r['phase'] == 'primary'])
        resource = U.rows(raw / profile / 'resources.jsonl')
        residency = [m for r in U.rows(raw / profile / 'residency.jsonl') for m in r['active']['models']]
        original = {r['id']: r for r in answer_rows if r['dataset'] == 'h1' and r['phase'] == 'primary' and r['arm'] == 'M'}
        repeated = {r['id']: r for r in answer_rows if r['dataset'] == 'h1' and r['phase'] == 'repeat'}
        result[profile] = {'all_calls': stats(answer_rows), 'primary': primary, 'by_group': per_group,
            'cold_control_load_seconds': native[answer_rows[0]['key']]['native'].get('load_duration', 0) / 1e9,
            'same_seed_repeat': {'cases': 84, 'exact_answer_matches': sum(original[q]['answer'] == repeated[q]['answer'] for q in original)},
            'resources': {'samples': len(resource),
                'gpu_used_mib_peak': max(r.get('gpu_used_mib', 0) for r in resource),
                'gpu_used_mib_median': statistics.median(r['gpu_used_mib'] for r in resource if 'gpu_used_mib' in r),
                'ram_used_bytes_peak': max(r.get('ram_used', 0) for r in resource),
                'ram_available_bytes_min': min(r['ram_available'] for r in resource if 'ram_available' in r),
                'ollama_process_rss_bytes_peak': max(r.get('ollama_rss', 0) for r in resource),
                'native_allocated_bytes_peak': max(m['size'] for m in residency),
                'native_vram_bytes_peak': max(m['size_vram'] for m in residency),
                'native_full_gpu_samples': sum(m['size_vram'] == m['size'] for m in residency),
                'native_partial_gpu_samples': sum(m['size_vram'] < m['size'] for m in residency),
                'resource_scope': 'whole GPU/host and summed Ollama RSS; native allocation separate; GUI background load retained'}}
    return result


def score_result(raw, profiles, review):
    checked = require_committed_raw(raw, profiles)
    manifest = load(review / 'manifest.json')
    if U.sha(Path(__file__)) != manifest['review_tool_sha256']:
        raise ValueError('Review tool changed after opening references.')
    for name, field in [('packet.jsonl', 'packet_sha256'), ('mapping.jsonl', 'mapping_sha256'),
                        ('reused-verdicts.jsonl', 'reused_verdicts_sha256')]:
        if U.sha(review / name) != manifest[field]:
            raise ValueError('Review evidence changed.')
    verdicts, ordered = combine_verdicts(review)
    maps = U.rows(review / 'mapping.jsonl')
    packets = U.rows(review / 'packet.jsonl')
    if [m['id'] for m in maps] != [p['id'] for p in packets] or len(maps) != 200:
        raise ValueError('Full200 aligned review required.')
    details = [{**{k: p[k] for k in ('id', 'conversation_id', 'ability')},
                'outcomes': {target: B.outcome(verdicts[p['id']], mapping)
                             for target, mapping in m['mapping'].items()}}
               for p, m in zip(packets, maps, strict=True)]
    beam = {}
    for profile in profiles:
        beam[profile] = {}
        for arm in ('N', 'M'):
            key = profile + ':' + arm
            selected = [r['outcomes'][key] for r in details]
            beam[profile][arm] = {'cases': 200, 'passes': sum(r['pass'] for r in selected),
                'uncertain': sum(r['uncertain'] for r in selected),
                'upper_pass_bound': sum(r['pass'] or r['uncertain'] for r in selected),
                'material_contradictions': sum(r['material_contradiction'] is True for r in selected),
                'format_failures': sum(r['format_failure'] for r in selected),
                'unresolved_contradiction': sum(r['material_contradiction'] is None and not r['format_failure'] for r in selected),
                'by_ability': {a: {'cases': sum(r['ability'] == a for r in details),
                    'passes': sum(r['outcomes'][key]['pass'] for r in details if r['ability'] == a)}
                    for a in sorted({r['ability'] for r in details})},
                'by_history': {a: {'cases': sum(r['conversation_id'] == a for r in details),
                    'passes': sum(r['outcomes'][key]['pass'] for r in details if r['conversation_id'] == a)}
                    for a in sorted({r['conversation_id'] for r in details})}}
        beam[profile]['memory_benefit_pp'] = (beam[profile]['M']['passes'] - beam[profile]['N']['passes']) / 2
        beam[profile]['paired'] = {
            'gains': sum(not r['outcomes'][profile + ':N']['pass'] and r['outcomes'][profile + ':M']['pass'] for r in details),
            'losses': sum(r['outcomes'][profile + ':N']['pass'] and not r['outcomes'][profile + ':M']['pass'] for r in details)}
    h1, h1_detail = h1_scores(raw, profiles)
    technical = technical_summary(raw, profiles)
    for profile in profiles:
        h1[profile]['memory_benefit_pp'] = 100 * (h1[profile]['primary:M']['clean'] - h1[profile]['primary:N']['clean']) / 84
        selected = [r for r in h1_detail if r['profile'] == profile]
        h1[profile]['leaked_case_ids'] = sorted({r['id'] for r in selected if r['leaked']})
        primary = {r['id']: r for r in selected if r['phase'] == 'primary' and r['arm'] == 'M'}
        repeat = {r['id']: r for r in selected if r['phase'] == 'repeat'}
        h1[profile]['repeat_clean_metric_matches'] = sum(primary[q]['clean'] == repeat[q]['clean'] for q in primary)
    screens = {}
    base = 'baseline14'
    for profile in profiles:
        if profile == base:
            continue
        ratio = technical[profile]['primary']['median_wall_seconds'] / technical[base]['primary']['median_wall_seconds']
        conditions = {
            'h1_primary_clean_not_lower': h1[profile]['primary:M']['clean'] >= h1[base]['primary:M']['clean'],
            'h1_repeat_clean_not_lower': h1[profile]['repeat:M']['clean'] >= h1[base]['repeat:M']['clean'],
            'no_additional_h1_leaked_case': not (set(h1[profile]['leaked_case_ids']) - set(h1[base]['leaked_case_ids'])),
            'beam_memory_passes_not_lower': beam[profile]['M']['passes'] >= beam[base]['M']['passes'],
            'beam_memory_contradiction_count_not_higher': beam[profile]['M']['material_contradictions'] <= beam[base]['M']['material_contradictions'],
            'no_more_invalid_json': technical[profile]['all_calls']['invalid_json'] <= technical[base]['all_calls']['invalid_json'],
            'no_more_native_errors': technical[profile]['all_calls']['native_errors'] <= technical[base]['all_calls']['native_errors'],
            'faster20percent_or_beam_gain5pp': ratio <= .8 or beam[profile]['M']['passes'] - beam[base]['M']['passes'] >= 10}
        screens[profile] = {'conditions': conditions, 'median_primary_wall_ratio_to_baseline': ratio,
            'decision': 'additional-experimental-option-only' if all(conditions.values()) else 'reject-promotion'}
    return {'schema': 'local-model-upgrade-v2-result', 'actual_attempts': checked['actual_attempts'], 'paid_attempts': 0,
        'h1': h1, 'beam': beam, 'technical': technical, 'screens': screens,
        'reference_status': dict(Counter(v['reference_status'] for v in ordered)),
        'review_manifest_sha256': U.sha(review / 'manifest.json'),
        'new_authored_verdicts_sha256': U.sha(review / 'new-verdicts.jsonl') if (review / 'new-verdicts.jsonl').exists() else None,
        'evaluation': 'Unchanged mechanical H1; unchanged BEAM outcome/validation with Codex authored rubric review. Not official, independent or fully blind.',
        'limits': 'Spent public development; fixed imperfect retrieval; shared history clusters; package-specific penalty/draft; one seed and fixed sequence. No general memory improvement/vendor ranking.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['audit', 'prepare-review', 'score'])
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--profiles', nargs='+', choices=PROFILES, required=True)
    p.add_argument('--prior', type=Path)
    p.add_argument('--labels', type=Path)
    p.add_argument('--destination', type=Path, required=True)
    a = p.parse_args()
    if a.command == 'audit':
        result = public_raw_receipt(a.raw, a.profiles)
        U.write_new(a.destination, result)
    elif a.command == 'prepare-review':
        result = prepare_review(a.raw, a.profiles, a.prior, a.labels, a.destination)
    else:
        result = score_result(a.raw, a.profiles, a.prior)
        U.write_new(a.destination, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
