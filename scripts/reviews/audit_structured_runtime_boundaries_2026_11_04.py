"""Offline audit counterexamples, NOT a passing capability/regression suite.

Exit zero means the audit completed. `observed` findings describe deficiencies
of the frozen candidate; no model, benchmark label, network or source edit is
used. All generated memory logs live in temporary directories.
"""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from tools.structured_memory_v1 import Source, Claim, Template
from tools.structured_memory_v2 import Memory
import structured_memory_paths_v5 as paths


def proposal(subject, predicate, value, polarity='affirm'):
    return {'subject': subject, 'predicate': predicate, 'object': value,
            'polarity': polarity}


def add(memory, source, *claims, learn=False):
    memory.add_source(source)
    memory.extract(source.id, {'claims': list(claims)},
                   method='supplied-test', learn=learn)


def audit():
    results = []
    template = Template.learn('Mira lives in Koral.',
                             Claim('seed', 'Mira', 'lives_in', 'Koral'))
    texts = ['Mira lives in Koral and works in Atrium.',
             'Mira lives in Koral if the move goes ahead.']
    matched = [template.match(Source(str(i), 'public', t, 1))
               for i, t in enumerate(texts)]
    results.append({'id': 'A01', 'observed': all(c is not None for c in matched),
        'issue': 'Positive cache accepts coordinated/conditional value spans',
        'inputs': texts, 'claims': [asdict(c) if c else None for c in matched],
        'negative_control_rejected': template.match(
            Source('neg', 'public', 'Mira lives in Koral maybe.', 1)) is None})
    with tempfile.TemporaryDirectory() as directory:
        log = Path(directory) / 'memory.jsonl'
        with Memory(log, writable=True) as memory:
            add(memory, Source('early', 'public', 'Mira lives in Koral.', 1),
                proposal('Mira', 'lives_in', 'Koral'), learn=True)
            add(memory, Source('late', 'public',
                'Future codeword NOVA: Mira lives in Zefir.', 10),
                proposal('Mira', 'lives_in', 'Zefir'), learn=True)
            add(memory, Source('private', 'private', 'Nora badge is violet.', 1),
                proposal('Nora', 'secret_badge', 'violet'))
        with paths.Memory(log) as memory:
            plans, _ = paths.options(memory, 'public', 'Where does Mira live?',
                                     valid_at=1, known_at=1)
            packet = paths.messages(memory, 'Where does Mira live?', plans, 'public')
            results.append({'id': 'A02', 'observed': 'NOVA' in json.dumps(packet),
                'issue': 'Historical routing prompt contains a future sentence shell',
                'known_at': 1, 'future_recorded': 10,
                'early_state': memory.resolve('public', 'Mira', 'lives_in',
                                               valid_at=1, known_at=1),
                'routing_user_message': json.loads(packet[1]['content'])})
            def execute(predicate):
                return memory.execute('public', 'Mira', {
                    'anchor': 'Mira', 'steps': [{'predicate': predicate}]},
                    valid_at=1, known_at=1)
            private, absent = execute('secret_badge'), execute('never_exists')
            results.append({'id': 'A03',
                'observed': private['status'] != absent['status'],
                'issue': 'Global predicate validation exposes cross-scope existence',
                'private_predicate_result': private, 'absent_predicate_result': absent,
                'visible_catalog': sorted(memory.visible_catalog('public', known_at=1))})
        second = Path(directory) / 'partial.jsonl'
        with Memory(second, writable=True) as memory:
            add(memory, Source('original', 'public',
                'Mira lives in Koral and works at Atlas.', 1),
                proposal('Mira', 'lives_in', 'Koral'),
                proposal('Mira', 'works_at', 'Atlas'))
            before = memory.resolve('public', 'Mira', 'works_at', valid_at=2, known_at=2)
            add(memory, Source('update', 'public', 'Mira lives in Zefir.', 2,
                               supersedes=('original',)),
                proposal('Mira', 'lives_in', 'Zefir'))
            after = memory.resolve('public', 'Mira', 'works_at', valid_at=2, known_at=2)
            results.append({'id': 'A04', 'observed': before['status'] == 'ok'
                and after['status'] == 'no_evidence',
                'issue': 'Whole-source supersession also removes unchanged properties',
                'classification': 'Documented source granularity; integration hazard',
                'before': before, 'after': after})
            add(memory, Source('denial', 'public', 'Mira does not live in Vela.', 3),
                proposal('Mira', 'lives_in', 'Vela', 'deny'))
            state = memory.resolve('public', 'Mira', 'lives_in', valid_at=3, known_at=3)
            results.append({'id': 'A05', 'observed': state['status'] == 'ok'
                and 'denial' in state['sources'],
                'issue': 'Returned source set also includes a different-value denial',
                'classification': 'Evidence set is broader than minimal positive support',
                'state': state})
    return {'audit_completed': True, 'model_calls': 0,
            'source_logs_modified': False, 'findings': results,
            'interpretation': 'Observed=True reproduces a limitation, not a successful memory task.'}


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=True, indent=2))
