"""Conservative exact-text replay and scope/time-visible plan validation.

This successor does not generalize a learned shell to unseen prose. Replaying
an interpretation is not validation of its semantics. Legacy claims remain
unchanged when read; their previous extraction errors are not repaired here.
"""
from collections import defaultdict
from dataclasses import asdict, replace

from tools.structured_memory_v1 import checked_proposal
from tools.structured_memory_v2 import Memory as MemoryV2

CACHE_POLICY = 'exact-text-v3'


def clock(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError('Query times must be integer ticks in the source clock.')


def signature(claims):
    return tuple(sorted((c.subject, c.predicate, c.object, c.polarity) for c in claims))


class Memory(MemoryV2):
    def __init__(self, *args, **kwargs):
        self._exact_model = defaultdict(list)
        super().__init__(*args, **kwargs)

    def _replay(self, sid):
        source = self.sources[sid]
        entries = [(origin, claims) for origin, claims in self._exact_model.get(
            (source.scope, source.text, source.policy), ())
            if origin != sid and self.sources[origin].recorded <= source.recorded]
        if not entries:
            return None, (), 'no_available_exact_model_interpretation'
        if len({signature(cs) for _, cs in entries}) != 1:
            return None, (), 'ambiguous_model_interpretations'
        claims = entries[0][1]
        if len(claims) != 1 or claims[0].polarity != 'affirm':
            return None, (), 'not_one_positive_claim'
        return replace(claims[0], source=sid), tuple(sorted(s for s, _ in entries)), 'exact_replay'

    def cache_info(self, sid):
        claim, origins, reason = self._replay(sid)
        return {'policy': CACHE_POLICY, 'reason': reason, 'derived_from': list(origins),
                'claim': asdict(claim) if claim else None}

    def cached(self, sid):
        return self._replay(sid)[0]

    def _check_replay(self, event):
        sid = event['source']
        claim, origins, _ = self._replay(sid)
        proposed = checked_proposal(self.sources[sid], event['proposal'], self.catalog)
        if (event.get('method') != 'template' or event.get('learn') is not False or
                claim is None or proposed != [claim] or event.get('derived_from') != list(origins)):
            raise ValueError('Exact replay requires the available original model derivations.')

    def _apply(self, event):
        if 'cache_policy' in event:
            if event.get('kind') != 'extract' or event['cache_policy'] != CACHE_POLICY:
                raise ValueError('Unknown cache derivation contract.')
            self._check_replay(event)
        super()._apply(event)
        if event['kind'] == 'extract' and event.get('method') == 'model':
            source = self.sources[event['source']]
            claims = checked_proposal(source, event['proposal'], self.catalog)
            self._exact_model[(source.scope, source.text, source.policy)].append((source.id, claims))

    def extract(self, sid, proposal, *, method='model', learn=False):
        if method != 'template':
            return super().extract(sid, proposal, method=method, learn=learn)
        if sid in self.extracted:
            raise ValueError('Already extracted; preserve history rather than overwrite.')
        _, origins, _ = self._replay(sid)
        event = {'kind': 'extract', 'source': sid, 'proposal': proposal, 'method': method,
                 'learn': learn, 'cache_policy': CACHE_POLICY, 'derived_from': list(origins)}
        self._check_replay(event)  # Validate before any canonical append.
        self._append(event)
        return checked_proposal(self.sources[sid], proposal, self.catalog)

    def resolve(self, scope, subject, predicate, *, valid_at, known_at):
        clock(valid_at); clock(known_at)
        return super().resolve(scope, subject, predicate, valid_at=valid_at, known_at=known_at)

    def anchors(self, scope, question, *, known_at):
        clock(known_at)
        return super().anchors(scope, question, known_at=known_at)

    def visible_catalog(self, scope, *, known_at):
        clock(known_at)
        return super().visible_catalog(scope, known_at=known_at)

    def execute(self, scope, question, plan, *, valid_at, known_at):
        clock(valid_at); clock(known_at)
        if not isinstance(plan, dict) or plan.get('anchor') not in self.anchors(scope, question, known_at=known_at):
            return {'status': 'unknown_subject', 'value': None, 'paths': []}
        steps = plan.get('steps')
        visible = self.visible_catalog(scope, known_at=known_at)
        if (not isinstance(steps, list) or not 1 <= len(steps) <= 6 or
                any(not isinstance(step, dict) or not isinstance(step.get('predicate'), str)
                    or step['predicate'] not in visible
                    or step.get('direction', 'out') not in ('out', 'in') for step in steps)):
            return {'status': 'invalid_plan', 'value': None, 'paths': []}
        return super().execute(scope, question, plan, valid_at=valid_at, known_at=known_at)
