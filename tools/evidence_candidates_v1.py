"""Bounded source-first recovery when derived metadata fragments or fails.

Candidate subjects come from visible metadata/query overlap. Original notes,
including notes rejected by metadata extraction, remain eligible. No domain
relation list, construction label or gold answer is used.
"""
from collections import deque
import re

from tools.structured_memory_v1 import key

FUNCTION_WORDS=frozenset('a an the of for in on at to is are was were by with and or '
                         'do does did what which how why when where i you my your '
                         'w z na do dla i jest to'.split())


def literal(text,entity):
    return re.search(r'(?<!\w)'+re.escape(key(entity))+r'(?!\w)',key(text)) is not None


def candidates(view,scope,question,day,mk,stamp):
    visible={s.id:s for s in view.sources.values() if s.scope==scope and s.recorded<=day}
    entities={a.subject for a in view.claims if a.source in visible}
    anchors={e for e in entities if literal(question,e) and key(e) not in FUNCTION_WORDS}
    if not anchors:
        anchors={word for e in entities for word in re.findall(r'[\w][\w.-]*',e)
                 if len(word)>1 and not word.isnumeric() and key(word) not in FUNCTION_WORDS and literal(question,word)}
    frequency={e:sum(literal(s.text,e) for s in visible.values()) for e in anchors}
    anchors=sorted((e for e in anchors if frequency[e]),key=lambda e:(frequency[e],-len(e),e))[:2]
    if not anchors: anchors=[None]
    queues=[]; pools=[]
    for anchor in anchors:
        pool=[s for s in visible.values() if anchor is None or literal(s.text,anchor)]
        items=[mk.Item(s.id,'event','account_history',stamp(s.recorded),s.text) for s in pool]
        profile=dict(mk.PROFILES['lexical'],k=8,names=False,lex_tau=1e-9,min_evidence=0.0,
                     timeout_ms=float('inf'),name='source-first-evidence-v1')
        found=mk.retrieve(mk.build_index(items,stamp(day)[:10]),question,'note',stamp(day),profile)
        if found.get('error') or found.get('status')=='degraded': raise ValueError('Candidate ranking did not complete.')
        lexical=[i.id for i in found['items']][:4]
        recent=[s.id for s in sorted(pool,key=lambda s:(-s.recorded,s.id))[:4]]
        merged=[]
        for i in range(max(len(lexical),len(recent))):
            for group in [lexical,recent]:
                if i<len(group) and group[i] not in merged: merged.append(group[i])
        queues.append(deque(merged)); pools.append({'anchor':anchor,'available_sources':len(pool)})
    result=[]
    while any(queues) and len(result)<16:
        for queue in queues:
            if queue:
                sid=queue.popleft()
                if sid not in result: result.append(sid)
                if len(result)==16: break
    return result,{'pools':pools,'candidate_count_before_transport_budget':len(result)}
