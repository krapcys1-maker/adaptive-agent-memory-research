"""Independent artifact checks; no generation, gold file or semantic model judge."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.structured_memory_v1 import Memory, Source, Claim, Template


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def audit(archive, store, capture, answer_dirs, questions, scope, valid_at, known_at, cache_version=1):
    failures = []
    def check(condition, message):
        if not condition:
            failures.append(message)
    raw = rows(archive)
    original = {r['id']: r for r in raw}
    qs = {r['id']: r['question'] for r in rows(questions)}
    with Memory(store) as m:
        check(set(m.sources) == set(original), 'source roster differs from archive')
        check(all(s.text == original[sid]['text'] and s.recorded == original[sid]['ordinal']
                  and s.scope == scope for sid,s in m.sources.items()), 'raw provenance mismatch')
        check(all(c.subject in m.sources[c.source].text and c.object in m.sources[c.source].text
                  for c in m.claims), 'ungrounded span')
        capture_rows = rows(capture/'captures.jsonl')
        check(len(capture_rows) == len(raw) and {r['id'] for r in capture_rows} == set(original),
              'incomplete capture attempts')
        quarantine = {r['id'] for r in capture_rows if r['status']=='quarantined'}
        declared = {r['id'] for r in rows(capture/'rejections.jsonl')} if (capture/'rejections.jsonl').exists() else set()
        check(quarantine == declared and all(r['status'] in ('accepted','quarantined') for r in capture_rows),
              'unreported capture rejection')
        # Reconstruct the cache from earlier events. Every cached fact must be
        # reproducible from a previously learned literal shell, not a future event.
        sources, learned, cached = {}, [], 0
        for row in rows(store):
            e = row['event']
            if e['kind'] == 'source':
                sources[e['source']['id']] = Source(**e['source'])
                continue
            source = sources[e['source']]
            claims = [Claim(source.id, **c) for c in e['proposal']['claims']]
            if e['method'] == 'template':
                candidates = [(t,c) for t in learned if (c := t.match(source))]
                if cache_version == 2:
                    from tools.structured_memory_v2 import informative, specificity
                    candidates = [(t,c) for t,c in candidates if informative(t)]
                    best = max((specificity(t) for t,c in candidates), default=0)
                    candidates = [(t,c) for t,c in candidates if specificity(t) == best]
                hits = {c.subject+'\0'+c.predicate+'\0'+c.object for t,c in candidates}
                check(len(claims) == 1 and len(hits) == 1 and
                      claims[0].subject+'\0'+claims[0].predicate+'\0'+claims[0].object in hits,
                      'non-causal template provenance: '+source.id)
                cached += 1
            if e.get('learn') and len(claims) == 1:
                t = Template.learn(source.text, claims[0])
                if t and t not in learned:
                    learned.append(t)
        for directory in [capture, *answer_dirs]:
            freeze = json.loads((directory/'raw-freeze.json').read_text(encoding='utf-8'))
            check(all(sha(directory/name) == h for name,h in freeze['files_sha256'].items()),
                  'raw freeze changed: '+directory.name)
            attempts, responses = rows(directory/'attempts.jsonl'), rows(directory/'responses.jsonl')
            ak, rk = [r['key'] for r in attempts], [r['key'] for r in responses]
            check(len(ak) == len(set(ak)) and set(ak) == set(rk) and len(ak) == len(rk),
                  'unmatched or duplicate calls: '+directory.name)
            controls = rows(directory/'controls.jsonl')
            check(len(controls) == 3 and all(c['correct'] for c in controls), 'failed transport controls')
            for r in attempts:
                import nie_reader_pilot as P
                check(P.sha(r['request']) == r['request_sha256'], 'request hash mismatch')
                check('reasoning_content' not in json.dumps(r), 'thinking content persisted')
            if directory == capture:
                continue
            answers = rows(directory/'answers.jsonl')
            check(len(answers) == len(qs) and {a['id'] for a in answers} == set(qs), 'incomplete question run')
            for a in answers:
                recalculated = m.execute(scope, qs[a['id']], a['plan'], valid_at=valid_at, known_at=known_at)
                check(recalculated == a['result'], 'non-reproducible graph result: '+a['id'])
                for path in a['result'].get('paths', []):
                    check(all(hop['sources'] and set(hop['sources']) <= set(m.sources) for hop in path),
                          'missing source path')
        return {'failures': failures, 'sources': len(m.sources), 'claims': len(m.claims),
                'templates': len(learned), 'cached_claims_reproduced': cached,
                'quarantined_sources': len(quarantine),
                'capture_methods': dict(Counter(r['method'] for r in capture_rows)),
                'answer_runs_checked': len(answer_dirs), 'store_sha256': sha(store),
                'semantic_extraction_accuracy': 'not established by span and replay checks'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['archive','store','capture','questions','output']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--answers', type=Path, action='append', required=True)
    p.add_argument('--scope', required=True)
    p.add_argument('--valid-at', type=int, required=True)
    p.add_argument('--known-at', type=int, required=True)
    p.add_argument('--cache-version', type=int, choices=[1,2], default=1)
    args = vars(p.parse_args())
    output = args.pop('output')
    args['answer_dirs'] = args.pop('answers')
    result = audit(**args)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(json.dumps(result,indent=2))
    return bool(result['failures'])


if __name__ == '__main__':
    raise SystemExit(main())
