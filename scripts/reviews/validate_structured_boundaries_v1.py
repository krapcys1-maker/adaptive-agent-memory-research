"""Offline frozen-MAB packet compatibility and exact-reuse opportunity audit.

Does not recapture sources, generate answers, change scores or inspect gold.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
import structured_memory_paths_v5 as legacy
from tools.structured_memory_v3 import Memory
from tools.structured_paths_v1 import QueryView, options, messages


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path): return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]
def packed(value): return json.dumps(value, sort_keys=True, ensure_ascii=False)


def validate(store, questions, answers):
    before = sha(store); failures = []; compatibility = []
    events = rows(store)
    template_ids = [r['event']['source'] for r in events if r['event']['kind']=='extract' and r['event']['method']=='template']
    reasons = Counter(); replay_hits = 0
    with Memory(store) as memory:
        scope_set = {s.scope for s in memory.sources.values()}
        if len(scope_set) != 1 or max(s.recorded for s in memory.sources.values()) > 20000:
            raise ValueError('Expected the frozen single-scope MAB view at tick20000.')
        scope = scope_set.pop()
        for sid in template_ids:
            info = memory.cache_info(sid); reasons[info['reason']] += 1
            replay_hits += info['claim'] is not None
    with legacy.Memory(store) as old, QueryView(store) as new:
        for question in rows(questions):
            q = question['question']
            prior, trace = legacy.options(old, scope, q, valid_at=20000, known_at=20000)
            current, current_trace = options(new, scope, q, valid_at=20000, known_at=20000)
            old_packet = legacy.messages(old, q, prior, scope)
            new_packet = messages(new, q, current, scope, valid_at=20000, known_at=20000)
            same = packed([prior,trace,old_packet]) == packed([current,current_trace,new_packet])
            compatibility.append({'id':question['id'],'identical':same})
            if not same: failures.append('packet differs: '+question['id'])
        executed = 0
        qmap = {r['id']:r['question'] for r in rows(questions)}
        for directory in answers:
            for row in rows(directory/'answers.jsonl'):
                value = new.execute(scope, qmap[row['id']], row['plan'], valid_at=20000, known_at=20000)
                if value != row['result']: failures.append('saved execution differs: '+directory.name+':'+row['id'])
                executed += 1
    if sha(store) != before: failures.append('canonical log changed')
    return {'failures':failures,'model_calls':0,'gold_read':False,'store_sha256':before,
        'all_available_query_tick':20000,'packet_comparisons':compatibility,
        'saved_path_executions':executed,'legacy_template_sources':len(template_ids),
        'exact_replay_opportunities_using_existing_model_interpretations':replay_hits,
        'exact_replay_reasons':dict(reasons),
        'cost_interpretation':'Misses require a fresh caller/model decision on recapture. This is opportunity loss, not a measured new extraction run or semantic accuracy.',
        'compatibility_limit':'Only this already-spent all-sources-available snapshot. Legacy claims are preserved, not retroactively revalidated.'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['store','questions','output']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--answers',type=Path,action='append',required=True)
    args=vars(parser.parse_args()); output=args.pop('output'); result=validate(**args)
    with output.open('x',encoding='utf-8') as f: json.dump(result,f,indent=2); f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='packet_comparisons'},indent=2))
    raise SystemExit(bool(result['failures']))
